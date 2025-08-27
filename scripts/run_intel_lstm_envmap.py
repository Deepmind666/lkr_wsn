#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
import torch
from intel_dataset_loader import IntelLabDataLoader
from pytorch_lstm_env import train_lstm_env, roll_forecast
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol

if __name__ == '__main__':
    # Load Intel dataset
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    s = loader.sensor_data.dropna(subset=['humidity','temperature'])
    # Use a continuous segment (simple approach): sample first 100k rows
    s = s.iloc[:100000]
    hum = s['humidity'].values.astype(np.float32)
    tmp = s['temperature'].values.astype(np.float32)
    series = np.stack([hum, tmp], axis=1)

    # Train LSTM to predict next-step humidity (normalized 0..100 preserved via scaler)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model, scaler = train_lstm_env(series, seq_len=64, pred_h=1, epochs=10, batch_size=512, lr=1e-3, val_split=0.1, num_workers=0, device=device)

    # Build topology from mote_locs
    locs = loader.locations_data.sort_values('node_id')
    xs, ys = locs['x'].to_list(), locs['y'].to_list()
    n = len(xs)
    w = max(xs) - min(xs) if max(xs)>min(xs) else 40.0
    h = max(ys) - min(ys) if max(ys)>min(ys) else 30.0
    cfg = NetworkConfig(num_nodes=n, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)

    # Prepare seed for forecast (take last 64 steps from training segment)
    seed_norm = scaler.transform(series[-64:])
    # Forecast 200 steps humidity (per-round)
    hum_pred = roll_forecast(model, seed_norm, horizon=200, scaler=scaler, device=device)

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
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile=profile, verbose=False)
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
            'seq_len': 64,
            'epochs': 10,
        }
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_lstm_envmap_compare.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

