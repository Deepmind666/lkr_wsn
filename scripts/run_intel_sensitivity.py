#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, math, random
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from intel_dataset_loader import IntelLabDataLoader
from gateway_selector import GatewaySelector, GatewayConfig

# 95% CI helper
_def = lambda arr: (float(np.mean(arr)), float(1.96*np.std(arr, ddof=1)/math.sqrt(max(1,len(arr)))))

def build_env_provider(loader, proto):
    s = loader.sensor_data.dropna(subset=['humidity','temperature'])
    if s.empty:
        return None
    h_vals = s['humidity'].values
    t_vals = s['temperature'].values
    h_p33 = float(np.percentile(h_vals, 33))
    h_p66 = float(np.percentile(h_vals, 66))
    t_med = float(np.percentile(t_vals, 50))
    regimes = [
        {'name':'low', 'h': h_p33, 'shadow': 3.5},
        {'name':'mid', 'h': (h_p33+h_p66)/2, 'shadow': 7.0},
        {'name':'high','h': h_p66, 'shadow': 12.0},
    ]
    def env_provider(round_idx: int):
        r = regimes[round_idx % 3]
        humidity_ratio = max(0.0, min(1.0, r['h']/100.0))
        temperature_c = t_med
        nf = -96.0 + (0.5 if r['name']=='mid' else (1.0 if r['name']=='high' else 0.0))
        proto.channel_model.set_env_mapping(shadowing_std=r['shadow'], noise_floor_dbm=nf)
        return (temperature_c, humidity_ratio)
    return env_provider

if __name__ == '__main__':
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    locs = loader.locations_data.sort_values('node_id')
    xs = locs['x'].to_list(); ys = locs['y'].to_list()
    minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys)
    width = maxx - minx if maxx > minx else 50.0
    height = maxy - miny if maxy > miny else 50.0
    n = len(locs)

    initial_energies = [1.0, 2.0, 5.0]        # Joules
    packet_sizes = [256, 512, 1024]           # Bytes (≈2k/4k/8k bits)
    gateway_counts = [1, 2, 3]

    summary = {}

    for E0 in initial_energies:
        for P in packet_sizes:
            for G in gateway_counts:
                key = f"E{E0}_P{P}_G{G}"
                energies = []
                pdrs = []
                for r in range(repeats):
                    seed = 2000 + r
                    random.seed(seed); np.random.seed(seed)
                    cfg = NetworkConfig(num_nodes=n, area_width=width, area_height=height, initial_energy=E0, packet_size=P)
                    proto = IntegratedEnhancedEEHFRProtocol(cfg,
                        enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False,
                        profile='robust', verbose=False)
                    # place nodes
                    for i,(x,y) in enumerate(zip(xs, ys)):
                        proto.nodes[i].x = float(x) - minx
                        proto.nodes[i].y = float(y) - miny
                    # set gateway count before run
                    try:
                        proto.gateway_selector = GatewaySelector(GatewayConfig(k=G))
                    except Exception:
                        pass
                    env_provider = build_env_provider(loader, proto)
                    res = proto.run_simulation(200, env_provider=env_provider)
                    energies.append(res.get('total_energy_consumed', 0.0))
                    pdrs.append(res.get('packet_delivery_ratio_end2end', 0.0))
                mean_e, ci_e = _def(energies)
                mean_p, ci_p = _def(pdrs)
                summary[key] = {
                    'initial_energy': E0,
                    'packet_size': P,
                    'gateway_k': G,
                    'energy': {'mean': mean_e, 'ci95': ci_e},
                    'pdr_end2end': {'mean': mean_p, 'ci95': ci_p},
                    'repeats': repeats
                }
                print(f"[SENS] {key}: energy={mean_e:.3f}±{ci_e:.3f}, pdr={mean_p:.3f}±{ci_p:.3f}")

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_sensitivity.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print('Saved', out_path)

