#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
import torch
from intel_dataset_loader import IntelLabDataLoader
from pytorch_lstm_env import train_lstm_env, roll_forecast
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol

if __name__ == '__main__':
    t0 = time.time()
    print('[EXTENDED] Starting Intel LSTM training with full dataset and extended epochs...')
    
    # Load Intel dataset - use FULL dataset (not just 100k)
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    s = loader.sensor_data.dropna(subset=['humidity','temperature'])
    print(f'[EXTENDED] Using full dataset: {len(s)} samples')
    
    # Use full time series for training
    hum = s['humidity'].values.astype(np.float32)
    tmp = s['temperature'].values.astype(np.float32)
    series = np.stack([hum, tmp], axis=1)

    # Extended training: longer sequences, more epochs, larger batch
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'[EXTENDED] Training on device: {device}')

    # Hyper-params for long training (tuned for strong CPU)
    SEQ_LEN = 128
    EPOCHS = 150
    BATCH = 1024
    LR = 6e-4
    STRIDE = 8
    NUM_WORKERS = max(0, min(8, (os.cpu_count() or 8) - 2))

    # Ultra9 285K can handle this easily - let's use its full power
    model, scaler = train_lstm_env(
        series,
        seq_len=SEQ_LEN,
        pred_h=1,
        epochs=EPOCHS,
        batch_size=BATCH,
        lr=LR,
        val_split=0.1,
        num_workers=NUM_WORKERS,
        device=device,
        stride=STRIDE
    )

    print(f'[EXTENDED] Training completed in {time.time()-t0:.1f}s')

    # Build topology from mote_locs
    locs = loader.locations_data.sort_values('node_id')
    xs, ys = locs['x'].to_list(), locs['y'].to_list()
    n = len(xs)
    w = max(xs) - min(xs) if max(xs)>min(xs) else 40.0
    h = max(ys) - min(ys) if max(ys)>min(ys) else 30.0
    cfg = NetworkConfig(num_nodes=n, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)

    # Prepare seed for forecast (take last 128 steps from training segment)
    seed_norm = scaler.transform(series[-128:])
    
    # Forecast longer horizon (500 rounds instead of 200)
    print('[EXTENDED] Generating 500-round humidity forecast...')
    hum_pred = roll_forecast(model, seed_norm, horizon=500, scaler=scaler, device=torch.device('cpu'))

    # Map predicted humidity to conservative shadowing_std/noise_floor
    def env_provider_builder(proto):
        def env_provider(round_idx: int):
            h = float(hum_pred[min(round_idx, len(hum_pred)-1)])
            p33 = float(np.percentile(hum_pred, 33))
            p66 = float(np.percentile(hum_pred, 66))
            if h < p33:
                shadow, nf = 4.5, -96.0
            elif h < p66:
                shadow, nf = 7.0, -95.5
            else:
                shadow, nf = 9.5, -95.0
            proto.channel_model.set_env_mapping(shadowing_std=shadow, noise_floor_dbm=nf)
            return (25.0, h/100.0)
        return env_provider

    # Run AETHER (energy/robust) on predicted environment - longer simulation
    def run_profile(profile: str):
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile=profile, verbose=False)
        minx, miny = min(xs), min(ys)
        for i,(x,y) in enumerate(zip(xs, ys)):
            proto.nodes[i].x = float(x) - minx
            proto.nodes[i].y = float(y) - miny
        envp = env_provider_builder(proto)
        return proto.run_simulation(500, env_provider=envp)  # 500 rounds

    print('[EXTENDED] Running extended simulations (500 rounds each)...')
    res_energy = run_profile('energy')
    res_robust = run_profile('robust')

    # Analyze round-by-round statistics for deeper insights
    def analyze_rounds(res, name):
        rounds = res.get('round_statistics', [])
        if not rounds:
            return {}
        
        # Extract per-round metrics
        end2end_per_round = []
        energy_per_round = []
        safety_actions = {'forced_direct': 0, 'extra_uplink': 0}
        
        for r in rounds:
            sp = r.get('source_packets_round', 0) or 0
            bd = r.get('bs_delivered_round', 0) or 0
            end2end_per_round.append((bd/sp) if sp>0 else 0.0)
            energy_per_round.append(r.get('energy_consumed', 0))
            
            if r.get('safety_forced_direct', False):
                safety_actions['forced_direct'] += 1
            if r.get('safety_extra_uplink_used', False):
                safety_actions['extra_uplink'] += 1
        
        # Compute percentiles and stability metrics
        end2end_arr = np.array(end2end_per_round)
        return {
            'end2end_mean': float(np.mean(end2end_arr)),
            'end2end_std': float(np.std(end2end_arr)),
            'end2end_p05': float(np.percentile(end2end_arr, 5)),
            'end2end_p25': float(np.percentile(end2end_arr, 25)),
            'end2end_p75': float(np.percentile(end2end_arr, 75)),
            'end2end_p95': float(np.percentile(end2end_arr, 95)),
            'safety_actions': safety_actions,
            'total_rounds': len(rounds)
        }

    energy_analysis = analyze_rounds(res_energy, 'energy')
    robust_analysis = analyze_rounds(res_robust, 'robust')

    out = {
        'AETHER_energy': {k: res_energy.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes','network_lifetime')},
        'AETHER_robust': {k: res_robust.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes','network_lifetime')},
        'lstm_extended': {
            'device': str(device),
            'seq_len': 128,
            'epochs': 50,
            'batch_size': 1024,
            'training_samples': len(series),
            'forecast_horizon': 500,
            'training_time_s': time.time() - t0
        },
        'detailed_analysis': {
            'energy': energy_analysis,
            'robust': robust_analysis
        }
    }
    
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_lstm_envmap_extended.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'[EXTENDED] Saved {out_path}')
    print(f'[EXTENDED] Total time: {time.time()-t0:.1f}s')
