#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
import torch
from intel_dataset_loader import IntelLabDataLoader
from pytorch_tcn_env import train_tcn_env, roll_forecast
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    s = loader.sensor_data.dropna(subset=['humidity','temperature']).iloc[:100000]
    series = np.stack([s['humidity'].values.astype(np.float32), s['temperature'].values.astype(np.float32)], axis=1)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    # Long training hyper-params
    SEQ_LEN=128; EPOCHS=120; BATCH=1024; LR=6e-4; STRIDE=8
    model, scaler = train_tcn_env(series, seq_len=SEQ_LEN, pred_h=1, epochs=EPOCHS, batch_size=BATCH, lr=LR, val_split=0.1, device=device, stride=STRIDE)
    actual_device = str(next(model.parameters()).device)

    locs = loader.locations_data.sort_values('node_id')
    xs, ys = locs['x'].to_list(), locs['y'].to_list()
    n = len(xs)
    w = max(xs) - min(xs) if max(xs)>min(xs) else 40.0
    h = max(ys) - min(ys) if max(ys)>min(ys) else 30.0
    cfg = NetworkConfig(num_nodes=n, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)

    seed_norm = scaler.transform(series[-64:])
    hum_pred = roll_forecast(model, seed_norm, horizon=200, scaler=scaler)

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
        'tcn': {
            'device': str(device),
            'seq_len': 64,
            'epochs': 8,
        }
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_tcn_envmap_compare.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

