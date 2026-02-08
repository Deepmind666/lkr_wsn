#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
import torch
try:
    import torch_directml  # optional DirectML backend for Windows GPU
    _HAS_DML = True
except Exception:
    _HAS_DML = False
from intel_dataset_loader import IntelLabDataLoader
from pytorch_transformer_env import train_transformer_env, roll_forecast
from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol

if __name__ == '__main__':
    # Load Intel dataset
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    s = loader.sensor_data.dropna(subset=['humidity','temperature']).iloc[:100000]
    series = np.stack([
        s['humidity'].values.astype(np.float32),
        s['temperature'].values.astype(np.float32)
    ], axis=1)

    # Train Transformer to predict next-step humidity
    # Device selection: support CUDA/CPU, and optional DirectML (Windows GPU)
    dev_cfg = os.environ.get('TRANSFORMER_DEVICE', os.environ.get('DEVICE', 'auto')).strip().lower()
    if dev_cfg == 'dml' and _HAS_DML:
        device = torch_directml.device()
        print(f"[Transformer] Using DirectML device: {device}")
    else:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        if dev_cfg in ('cpu', 'cuda'):
            device = torch.device('cuda' if (dev_cfg == 'cuda' and torch.cuda.is_available()) else 'cpu')
        if device.type == 'cuda':
            try:
                # Try a tiny CUDA op to catch kernel image issues
                torch.zeros(1, device=device).sin_()
            except Exception as e:
                print(f"[Transformer] CUDA device probe failed: {e}. Falling back to CPU.")
                device = torch.device('cpu')

    SEQ_LEN = int(os.environ.get('TRANSFORMER_SEQ_LEN', '128'))
    EPOCHS = int(os.environ.get('TRANSFORMER_EPOCHS', '120'))
    BATCH = int(os.environ.get('TRANSFORMER_BATCH', '1024'))
    try:
        LR = float(os.environ.get('TRANSFORMER_LR', '6e-4'))
    except ValueError:
        LR = float(eval(os.environ.get('TRANSFORMER_LR', '6e-4')))
    STRIDE = int(os.environ.get('TRANSFORMER_STRIDE', '8'))

    # Model size knobs
    DMODEL = int(os.environ.get('TRANSFORMER_DMODEL', '128'))
    NHEAD = int(os.environ.get('TRANSFORMER_NHEAD', '8'))
    NLAYER = int(os.environ.get('TRANSFORMER_LAYERS', '4'))
    DIM_FF = int(os.environ.get('TRANSFORMER_DIMFF', '256'))
    DROPOUT = float(os.environ.get('TRANSFORMER_DROPOUT', '0.1'))

    print(f"[Transformer] Device={device}, epochs={EPOCHS}, batch={BATCH}, seq_len={SEQ_LEN}, stride={STRIDE}, d_model={DMODEL}, layers={NLAYER}, nhead={NHEAD}, dim_ff={DIM_FF}, dropout={DROPOUT}")

    model, scaler = train_transformer_env(series, seq_len=SEQ_LEN, pred_h=1, epochs=EPOCHS, batch_size=BATCH, lr=LR, val_split=0.1, device=device, stride=STRIDE,
                                          d_model=DMODEL, nhead=NHEAD, num_layers=NLAYER, dim_ff=DIM_FF, dropout=DROPOUT)

    # Build topology from mote_locs
    locs = loader.locations_data.sort_values('node_id')
    xs, ys = locs['x'].to_list(), locs['y'].to_list()
    n = len(xs)
    w = max(xs) - min(xs) if max(xs)>min(xs) else 40.0
    h = max(ys) - min(ys) if max(ys)>min(ys) else 30.0
    cfg = NetworkConfig(num_nodes=n, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)

    # Prepare seed and forecast 200 rounds
    seed_norm = scaler.transform(series[-SEQ_LEN:])
    hum_pred = roll_forecast(model, seed_norm, horizon=200, scaler=scaler)

    # Map predicted humidity to environment (provide (temp_c, humidity_ratio))
    def env_provider_builder(proto: AerisProtocol):
        import numpy as _np
        hp = _np.clip(hum_pred, 0, 100)
        def env_provider(t: int):
            idx = min(t, len(hp) - 1)
            temp_c = 25.0
            hum_ratio = float(hp[idx]) / 100.0
            return (temp_c, hum_ratio)
        return env_provider

    # Run AETHER profiles on predicted env
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
        'transformer': {
            'device': str(device),
            'seq_len': SEQ_LEN,
            'epochs': EPOCHS,
        }
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_transformer_envmap_compare.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)