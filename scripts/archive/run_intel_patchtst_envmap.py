#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run PatchTST-style Transformer baseline on Intel Lab dataset for environment mapping (humidity prediction -> env parameters),
writing outputs compatible with plotting alongside LSTM/TCN/Transformer baselines.
"""
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
from pytorch_patchtst_env import train_patchtst_env, roll_forecast
from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol

if __name__ == '__main__':
    # Load dataset (real Intel Lab)
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    s = loader.sensor_data.dropna(subset=['humidity','temperature'])
    print(f"[PatchTST] Loaded Intel dataset: {len(s)} rows")
    series = np.stack([
        s['humidity'].values.astype(np.float32),
        s['temperature'].values.astype(np.float32)
    ], axis=1)

    # Device and training hyperparams
    # Device selection: support CUDA/CPU, and optional DirectML (Windows GPU)
    dev_cfg = os.environ.get('PATCHTST_DEVICE', os.environ.get('DEVICE', 'auto')).strip().lower()
    if dev_cfg == 'dml' and _HAS_DML:
        device = torch_directml.device()
        print(f"[PatchTST] Using DirectML device: {device}")
    else:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        if dev_cfg in ('cpu', 'cuda'):
            device = torch.device('cuda' if (dev_cfg == 'cuda' and torch.cuda.is_available()) else 'cpu')
        if device.type == 'cuda':
            try:
                # tiny CUDA op to catch kernel image issues
                torch.zeros(1, device=device).sin_()
            except Exception as e:
                print(f"[PatchTST] CUDA device probe failed: {e}. Falling back to CPU.")
                device = torch.device('cpu')

    SEQ_LEN = int(os.environ.get('PATCHTST_SEQ_LEN', '128'))
    EPOCHS = int(os.environ.get('PATCHTST_EPOCHS', '320'))  # stronger default
    BATCH = int(os.environ.get('PATCHTST_BATCH', '1024'))
    try:
        LR = float(os.environ.get('PATCHTST_LR', '8e-4'))
    except ValueError:
        # allow formats like '8e-4'
        LR = float(eval(os.environ.get('PATCHTST_LR', '8e-4')))
    STRIDE = int(os.environ.get('PATCHTST_STRIDE', '8'))

    # Optional model-size hyperparams
    DMODEL = int(os.environ.get('PATCHTST_DMODEL', '256'))
    NHEAD = int(os.environ.get('PATCHTST_NHEAD', '8'))
    NLAYER = int(os.environ.get('PATCHTST_LAYERS', '4'))
    DIM_FF = int(os.environ.get('PATCHTST_DIMFF', '512'))
    DROPOUT = float(os.environ.get('PATCHTST_DROPOUT', '0.1'))
    PATCH_LEN = int(os.environ.get('PATCHTST_PATCH_LEN', '16'))

    print(f"[PatchTST] Device={device}, epochs={EPOCHS}, batch={BATCH}, seq_len={SEQ_LEN}, stride={STRIDE}, d_model={DMODEL}, layers={NLAYER}, nhead={NHEAD}, dim_ff={DIM_FF}, dropout={DROPOUT}, patch_len={PATCH_LEN}")

    # Train PatchTST env forecaster
    model, scaler = train_patchtst_env(
        series, seq_len=SEQ_LEN, pred_h=1, epochs=EPOCHS, batch_size=BATCH, lr=LR,
        val_split=0.1, device=device, seed=42, stride=STRIDE,
        d_model=DMODEL, nhead=NHEAD, num_layers=NLAYER, dim_ff=DIM_FF, dropout=DROPOUT, patch_len=PATCH_LEN
    )

    # Build network configuration from Intel node positions
    locs = loader.locations_data.sort_values('node_id')
    xs, ys = locs['x'].to_list(), locs['y'].to_list()
    n = len(xs)
    w = max(xs) - min(xs) if max(xs)>min(xs) else 40.0
    h = max(ys) - min(ys) if max(ys)>min(ys) else 30.0

    # Use the same NetworkConfig fields as other scripts (area_width/height, num_nodes, etc.)
    cfg = NetworkConfig(num_nodes=n, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)

    # Forecast humidity over simulation horizon from last seq_len
    H = 200
    seed_seq = series[-SEQ_LEN:]
    hum_pred = roll_forecast(model, seed_seq, horizon=H, scaler=scaler, patch_len=PATCH_LEN, stride=STRIDE)

    # Environment provider: return (temperature_c, humidity_ratio)
    hum_clamped = np.clip(hum_pred, 0.0, 100.0)
    def env_provider(t: int):
        h = float(hum_clamped[min(t, len(hum_clamped)-1)])
        temp_c = 25.0
        hum_ratio = h / 100.0
        return (temp_c, hum_ratio)

    # Instantiate protocols and set node coordinates to Intel layout
    proto_energy = AerisProtocol(cfg, profile='energy', enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, verbose=False)
    proto_robust = AerisProtocol(cfg, profile='robust', enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, verbose=False)

    minx, miny = min(xs), min(ys)
    for i, (x, y) in enumerate(zip(xs, ys)):
        # Normalize positions to [0,w]/[0,h] region used by NetworkConfig
        proto_energy.nodes[i].x = float(x) - minx
        proto_energy.nodes[i].y = float(y) - miny
        proto_robust.nodes[i].x = float(x) - minx
        proto_robust.nodes[i].y = float(y) - miny

    res_energy = proto_energy.run_simulation(max_rounds=200, env_provider=env_provider)
    res_robust = proto_robust.run_simulation(max_rounds=200, env_provider=env_provider)

    out = {
        'AETHER_energy': {k: res_energy.get(k) for k in ('total_energy_consumed', 'packet_delivery_ratio', 'packet_delivery_ratio_end2end', 'final_alive_nodes')},
        'AETHER_robust': {k: res_robust.get(k) for k in ('total_energy_consumed', 'packet_delivery_ratio', 'packet_delivery_ratio_end2end', 'final_alive_nodes')},
        'meta': {
            'model': 'PatchTST', 'device': str(next(model.parameters()).device),
            'seq_len': SEQ_LEN, 'epochs': EPOCHS, 'batch': BATCH, 'lr': LR, 'stride': STRIDE,
            'd_model': DMODEL, 'layers': NLAYER, 'nhead': NHEAD, 'dim_ff': DIM_FF, 'dropout': DROPOUT, 'patch_len': PATCH_LEN,
            'train_rows': int(len(s))
        }
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_patchtst_envmap_compare.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('Saved', out_path)