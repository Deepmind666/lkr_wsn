#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
import torch
from intel_dataset_loader import IntelLabDataLoader
from pytorch_tcn_env import train_tcn_env, roll_forecast
from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol

def _export_onnx(model: torch.nn.Module, x: torch.Tensor, onnx_path: Path, use_dynamic_axes: bool = True):
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import torch.onnx
        kwargs = {
            'export_params': True,
            'opset_version': 17,
            'do_constant_folding': True,
            'input_names': ['input'],
            'output_names': ['output'],
        }
        if use_dynamic_axes:
            kwargs['dynamic_axes'] = {'input': {0: 'batch', 1: 'seq'}, 'output': {0: 'batch'}}
        torch.onnx.export(model.eval(), x, str(onnx_path), **kwargs)
        return onnx_path
    except Exception as e:
        raise RuntimeError(f"ONNX export failed: {e}")

def _forecast_ort(onnx_path: Path, seed_seq_norm: np.ndarray, horizon: int) -> np.ndarray:
    try:
        import onnxruntime as ort
    except Exception:
        raise RuntimeError("onnxruntime not installed")
    avail = ort.get_available_providers()
    providers = []
    pref = os.environ.get('INFER_PROVIDERS', 'auto').strip().lower()
    order = ('CUDAExecutionProvider','DmlExecutionProvider','OpenVINOExecutionProvider','CPUExecutionProvider')
    if pref != 'auto':
        mapping = {
            'cuda':'CUDAExecutionProvider','gpu':'CUDAExecutionProvider','cpu':'CPUExecutionProvider',
            'dml':'DmlExecutionProvider','openvino':'OpenVINOExecutionProvider'
        }
        for p in [x.strip() for x in pref.split(',') if x.strip()]:
            ep = mapping.get(p);
            if ep and ep in avail: providers.append(ep)
    if not providers:
        for ep in order:
            if ep in avail: providers.append(ep)
    so = ort.SessionOptions(); so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess = ort.InferenceSession(str(onnx_path), sess_options=so, providers=providers)
    seq = seed_seq_norm.copy()
    preds = []
    _ = sess.run(['output'], {'input': seq[None, ...].astype(np.float32)})
    for _ in range(horizon):
        out = sess.run(['output'], {'input': seq[None, ...].astype(np.float32)})[0]
        y_n = float(out[0,0])
        next_step = seq[-1].copy(); next_step[0] = y_n
        seq = np.vstack([seq[1:], next_step])
        preds.append(y_n)
    return np.array(preds, dtype=np.float32)

def _forecast_openvino(onnx_path: Path, seed_seq_norm: np.ndarray, horizon: int, device: str = 'AUTO') -> np.ndarray:
    try:
        from openvino.runtime import Core
    except Exception:
        raise RuntimeError("openvino not installed")
    core = Core()
    model = core.read_model(model=str(onnx_path))
    compiled = core.compile_model(model=model, device_name=device)
    infer = compiled.create_infer_request()
    seq = seed_seq_norm.copy()
    preds = []
    _ = infer.infer({'input': seq[None, ...].astype(np.float32)})
    for _ in range(horizon):
        out = infer.infer({'input': seq[None, ...].astype(np.float32)})
        y_n = float(out['output'][0,0])
        next_step = seq[-1].copy(); next_step[0] = y_n
        seq = np.vstack([seq[1:], next_step])
        preds.append(y_n)
    return np.array(preds, dtype=np.float32)

def forecast_with_backend(model: torch.nn.Module, seed_seq_norm: np.ndarray, scaler, horizon: int):
    backend = os.environ.get('INFER_BACKEND', '').strip().lower()  # '', 'ort', 'openvino'
    ov_dev = os.environ.get('OV_DEVICE', os.environ.get('OPENVINO_DEVICE','AUTO')).strip()
    if backend in ('ort','onnx','onnxruntime'):
        onnx_path = Path(__file__).parent.parent / 'results' / 'tcn_infer_tmp.onnx'
        _export_onnx(model.to('cpu'), torch.tensor(seed_seq_norm[None, ...], dtype=torch.float32), onnx_path, use_dynamic_axes=True)
        preds_n = _forecast_ort(onnx_path, seed_seq_norm, horizon=horizon)
    elif backend in ('openvino','ov'):
        if ov_dev.upper() == 'NPU':
            onnx_path = Path(__file__).parent.parent / 'results' / 'tcn_infer_npu_static.onnx'
            _export_onnx(model.to('cpu'), torch.tensor(seed_seq_norm[None, ...], dtype=torch.float32), onnx_path, use_dynamic_axes=False)
        else:
            onnx_path = Path(__file__).parent.parent / 'results' / 'tcn_infer_tmp.onnx'
            _export_onnx(model.to('cpu'), torch.tensor(seed_seq_norm[None, ...], dtype=torch.float32), onnx_path, use_dynamic_axes=True)
        preds_n = _forecast_openvino(onnx_path, seed_seq_norm, horizon=horizon, device=ov_dev)
    else:
        return roll_forecast(model, seed_seq_norm, horizon=horizon, scaler=scaler)
    hum_pred = scaler.inverse_transform(np.column_stack([preds_n, np.zeros_like(preds_n)]))[:,0]
    return np.clip(hum_pred, 0.0, 100.0)

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    s = loader.sensor_data.dropna(subset=['humidity','temperature'])  # use FULL dataset
    print(f"[TCN] Loaded Intel dataset: {len(s)} rows")
    series = np.stack([s['humidity'].values.astype(np.float32), s['temperature'].values.astype(np.float32)], axis=1)

    # Device selection with env override and safe fallback
    dev_env = os.environ.get('TCN_DEVICE', os.environ.get('DEVICE', 'auto')).lower()
    if dev_env not in ('auto','cuda','cpu'):
        dev_env = 'auto'
    if dev_env == 'cuda':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    elif dev_env == 'cpu':
        device = torch.device('cpu')
    else:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[TCN] Training on device(requested={dev_env}): {device}")

    # Long training hyper-params with env override
    SEQ_LEN = int(os.environ.get('TCN_SEQ_LEN', '128'))
    EPOCHS = int(os.environ.get('TCN_EPOCHS','200'))
    BATCH = int(os.environ.get('TCN_BATCH','1024'))
    try:
        LR = float(os.environ.get('TCN_LR', '6e-4'))
    except ValueError:
        LR = float(eval(os.environ.get('TCN_LR', '6e-4')))
    STRIDE = int(os.environ.get('TCN_STRIDE', '8'))

    def do_train(dev):
        return train_tcn_env(series, seq_len=SEQ_LEN, pred_h=1, epochs=EPOCHS, batch_size=BATCH, lr=LR, val_split=0.1, device=dev, stride=STRIDE)

    try:
        model, scaler = do_train(device)
        actual_device = str(next(model.parameters()).device)
    except Exception as e:
        msg = str(e)
        if 'no kernel image is available for execution on the device' in msg or 'cudaErrorNoKernelImageForDevice' in msg:
            print('[TCN][WARN] CUDA kernel image mismatch, auto fallback to CPU for this script only...')
            model, scaler = do_train(torch.device('cpu'))
            actual_device = str(next(model.parameters()).device)
        else:
            raise

    locs = loader.locations_data.sort_values('node_id')
    xs, ys = locs['x'].to_list(), locs['y'].to_list()
    n = len(xs)
    w = max(xs) - min(xs) if max(xs)>min(xs) else 40.0
    h = max(ys) - min(ys) if max(ys)>min(ys) else 30.0
    cfg = NetworkConfig(num_nodes=n, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)

    # Rolling forecast for 200 rounds
    seed_norm = scaler.transform(series[-SEQ_LEN:])
    hum_pred = forecast_with_backend(model, seed_norm, scaler, horizon=200)

    # Build env_provider to map humidity to channel parameters, and set node coordinates
    def env_provider_builder(proto):
        def env_provider(round_idx: int):
            h = float(hum_pred[min(round_idx, len(hum_pred)-1)])
            p33 = float(np.percentile(hum_pred, 33)); p66 = float(np.percentile(hum_pred, 66))
            if h < p33:
                shadow, nf = 4.5, -96.0
            elif h < p66:
                shadow, nf = 7.0, -95.5
            else:
                shadow, nf = 9.5, -95.0
            proto.channel_model.set_env_mapping(shadowing_std=shadow, noise_floor_dbm=nf)
            return (25.0, h/100.0)
        return env_provider

    def run_profile(profile: str):
        proto = AerisProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile=profile, verbose=False)
        minx, miny = min(xs), min(ys)
        for i,(x,y) in enumerate(zip(xs, ys)):
            proto.nodes[i].x = float(x) - minx
            proto.nodes[i].y = float(y) - miny
        envp = env_provider_builder(proto)
        return proto.run_simulation(200, env_provider=envp)

    res_energy = run_profile('energy')
    res_robust = run_profile('robust')

    out = {
        'AETHER_energy': {k: res_energy.get(k) for k in ('total_energy_consumed', 'packet_delivery_ratio', 'packet_delivery_ratio_end2end', 'final_alive_nodes')},
        'AETHER_robust': {k: res_robust.get(k) for k in ('total_energy_consumed', 'packet_delivery_ratio', 'packet_delivery_ratio_end2end', 'final_alive_nodes')},
        'meta': {
            'model': 'TCN', 'device': actual_device,
            'seq_len': SEQ_LEN, 'epochs': EPOCHS, 'batch': BATCH, 'lr': LR, 'stride': STRIDE,
            'train_rows': int(len(s)),
            'infer_backend': os.environ.get('INFER_BACKEND', '').strip().lower(),
            'providers_pref': os.environ.get('INFER_PROVIDERS','auto'),
            'ov_device': os.environ.get('OV_DEVICE', os.environ.get('OPENVINO_DEVICE',''))
        }
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_tcn_envmap_compare.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('Saved', out_path)

