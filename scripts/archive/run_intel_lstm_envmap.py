#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, time
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
import torch
from intel_dataset_loader import IntelLabDataLoader
from pytorch_lstm_env import train_lstm_env, roll_forecast
from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol

# Optional ONNX/ORT/OpenVINO imports are handled lazily inside functions

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
    # warmup
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
    # warmup
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
        # export and run ORT
        onnx_path = Path(__file__).parent.parent / 'results' / 'lstm_infer_tmp.onnx'
        _export_onnx(model.to('cpu'), torch.tensor(seed_seq_norm[None, ...], dtype=torch.float32), onnx_path, use_dynamic_axes=True)
        preds_n = _forecast_ort(onnx_path, seed_seq_norm, horizon=horizon)
    elif backend in ('openvino','ov'):
        # For NPU target, export ONNX with static axes to satisfy sequence length constraint
        if ov_dev.upper() == 'NPU':
            onnx_path = Path(__file__).parent.parent / 'results' / 'lstm_infer_npu_static.onnx'
            _export_onnx(model.to('cpu'), torch.tensor(seed_seq_norm[None, ...], dtype=torch.float32), onnx_path, use_dynamic_axes=False)
        else:
            onnx_path = Path(__file__).parent.parent / 'results' / 'lstm_infer_tmp.onnx'
            _export_onnx(model.to('cpu'), torch.tensor(seed_seq_norm[None, ...], dtype=torch.float32), onnx_path, use_dynamic_axes=True)
        preds_n = _forecast_openvino(onnx_path, seed_seq_norm, horizon=horizon, device=ov_dev)
    else:
        return roll_forecast(model, seed_seq_norm, horizon=horizon, scaler=scaler)
    hum_pred = scaler.inverse_transform(np.column_stack([preds_n, np.zeros_like(preds_n)]))[:,0]
    return np.clip(hum_pred, 0.0, 100.0)

if __name__ == '__main__':
    # Load Intel dataset
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    s = loader.sensor_data.dropna(subset=['humidity','temperature'])
    # Optional cap via env; by default use full dataset
    cap = int(os.environ.get('LSTM_ROWS', '0'))
    if cap > 0:
        s = s.iloc[:cap]
    hum = s['humidity'].values.astype(np.float32)
    tmp = s['temperature'].values.astype(np.float32)
    series = np.stack([hum, tmp], axis=1)

    # Hyper-params with env overrides + device override/probe
    dev_cfg = os.environ.get('LSTM_DEVICE', os.environ.get('DEVICE', 'auto')).strip().lower()
    if dev_cfg == 'cuda':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    elif dev_cfg == 'cpu':
        device = torch.device('cpu')
    else:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type == 'cuda':
        try:
            # tiny CUDA op to catch kernel image issues
            torch.zeros(1, device=device).sin_()
        except Exception as e:
            print(f"[LSTM] CUDA device probe failed: {e}. Falling back to CPU.")
            device = torch.device('cpu')
    SEQ_LEN = int(os.environ.get('LSTM_SEQ_LEN', '64'))
    EPOCHS  = int(os.environ.get('LSTM_EPOCHS', '10'))
    BATCH   = int(os.environ.get('LSTM_BATCH', '512'))
    model, scaler = train_lstm_env(series, seq_len=SEQ_LEN, pred_h=1, epochs=EPOCHS, batch_size=BATCH, lr=1e-3, val_split=0.1, num_workers=0, device=device)

    # Build topology from mote_locs
    locs = loader.locations_data.sort_values('node_id')
    xs, ys = locs['x'].to_list(), locs['y'].to_list()
    n = len(xs)
    w = max(xs) - min(xs) if max(xs)>min(xs) else 40.0
    h = max(ys) - min(ys) if max(ys)>min(ys) else 30.0
    cfg = NetworkConfig(num_nodes=n, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)

    # Prepare seed for forecast (take last SEQ_LEN steps)
    seed_norm = scaler.transform(series[-SEQ_LEN:])
    # Forecast 200 steps humidity (per-round)
    hum_pred = forecast_with_backend(model, seed_norm, scaler, horizon=200)

    # Map predicted humidity to conservative shadowing_std/noise_floor
    def env_provider_builder(proto):
        def env_provider(round_idx: int):
            h = float(hum_pred[min(round_idx, len(hum_pred)-1)])
            if h < np.percentile(hum_pred, 33):
                shadow, nf = 4.5, -96.0
            elif h < np.percentile(hum_pred, 66):
                shadow, nf = 7.0, -95.5
            else:
                shadow, nf = 9.5, -95.0
            proto.channel_model.set_env_mapping(shadowing_std=shadow, noise_floor_dbm=nf)
            return (25.0, h/100.0)
        return env_provider

    # Run AETHER (energy/robust) on predicted environment
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
        'AETHER_energy': {k: res_energy.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes')},
        'AETHER_robust': {k: res_robust.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes')},
        'lstm': {
            'device': str(device),
            'seq_len': SEQ_LEN,
            'epochs': EPOCHS,
            'batch': BATCH,
            'train_rows': int(len(s)),
            'infer_backend': os.environ.get('INFER_BACKEND', '').strip().lower(),
            'providers_pref': os.environ.get('INFER_PROVIDERS','auto'),
            'ov_device': os.environ.get('OV_DEVICE', os.environ.get('OPENVINO_DEVICE',''))
        }
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_lstm_envmap_compare.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

