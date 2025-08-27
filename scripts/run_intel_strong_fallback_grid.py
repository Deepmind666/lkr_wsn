#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from intel_dataset_loader import IntelLabDataLoader

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    locs = loader.locations_data.sort_values('node_id')
    xs, ys = locs['x'].to_list(), locs['y'].to_list()
    n = len(xs)
    w = max(xs) - min(xs) if max(xs)>min(xs) else 40.0
    h = max(ys) - min(ys) if max(ys)>min(ys) else 30.0
    cfg = NetworkConfig(num_nodes=n, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)

    # build conservative env provider
    s = loader.sensor_data.dropna(subset=['humidity','temperature'])
    h_vals = s['humidity'].values; t_vals = s['temperature'].values
    h_p33 = float(np.percentile(h_vals, 33)); h_p66 = float(np.percentile(h_vals, 66)); t_med = float(np.percentile(t_vals, 50))
    regimes = [
        {'name':'low', 'h': h_p33, 'shadow': 4.5, 'nf': -96.0},
        {'name':'mid', 'h': (h_p33+h_p66)/2, 'shadow': 7.0, 'nf': -95.5},
        {'name':'high','h': h_p66, 'shadow': 9.5, 'nf': -95.0},
    ]

    def make_env_provider(proto):
        def env_provider(round_idx: int):
            r = regimes[round_idx % 3]
            humidity_ratio = max(0.0, min(1.0, r['h']/100.0))
            proto.channel_model.set_env_mapping(shadowing_std=r['shadow'], noise_floor_dbm=r['nf'])
            return (t_med, humidity_ratio)
        return env_provider

    grid = [
        {'redundant_prob': 1.0, 'delta_dbm': 1.0, 'extra_max': 1},
        {'redundant_prob': 1.0, 'delta_dbm': 1.0, 'extra_max': 2},
        {'redundant_prob': 1.0, 'delta_dbm': 2.0, 'extra_max': 1},
        {'redundant_prob': 1.0, 'delta_dbm': 2.0, 'extra_max': 2},
    ]

    out = []
    for g in grid:
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile=None, verbose=False)
        minx, miny = min(xs), min(ys)
        for i,(x,y) in enumerate(zip(xs, ys)):
            proto.nodes[i].x = float(x) - minx
            proto.nodes[i].y = float(y) - miny
        envp = make_env_provider(proto)
        # configure strong fallback
        proto.safety_fallback_enabled = True
        proto.safety_T = 1
        proto.safety_theta = 0.1
        proto.safety_redundant_uplink = True
        proto.safety_redundant_prob = g['redundant_prob']
        proto.safety_extra_uplink_max = g['extra_max']
        proto.safety_power_bump = True
        proto.safety_power_bump_delta = g['delta_dbm']
        res = proto.run_simulation(200, env_provider=envp)
        rounds = res.get('round_statistics', [])
        pr = []
        for r in rounds:
            sp = r.get('source_packets_round', 0) or 0
            bd = r.get('bs_delivered_round', 0) or 0
            pr.append((bd/sp) if sp>0 else 0.0)
        p05 = sorted(pr)[int(0.05*(len(pr)-1))] if pr else 0.0
        out.append({
            'redundant_prob': g['redundant_prob'],
            'delta_dbm': g['delta_dbm'],
            'extra_max': g['extra_max'],
            'total_energy_consumed': res.get('total_energy_consumed'),
            'pdr_end2end_mean': res.get('packet_delivery_ratio_end2end'),
            'pdr_end2end_p05': p05,
            'pdr_hop': res.get('packet_delivery_ratio'),
            'lifetime': res.get('network_lifetime')
        })
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_strong_fallback_grid.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

