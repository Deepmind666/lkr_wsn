#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, math, statistics
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from intel_dataset_loader import IntelLabDataLoader

# Welch t-test helper

def welch(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    va = statistics.pvariance(a) if len(a) > 1 else 0.0
    vb = statistics.pvariance(b) if len(b) > 1 else 0.0
    na, nb = len(a), len(b)
    se = math.sqrt((va/na) + (vb/nb)) if na>0 and nb>0 else float('inf')
    t = (ma - mb) / se if se > 0 else 0.0
    num = (va/na + vb/nb)**2
    den = 0.0
    if na>1: den += (va/na)**2 / (na-1)
    if nb>1: den += (vb/nb)**2 / (nb-1)
    df = num/den if den>0 else float('inf')
    # normal approx p-value
    x = abs(t)/math.sqrt(2)
    p = 2 * (1 - (1 + math.erf(x))/2)
    return {'t_stat': t, 'df': df, 'p_approx': max(0.0, min(1.0, p))}

if __name__ == '__main__':
    # Load Intel dataset
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    locs = loader.locations_data.sort_values('node_id')
    xs, ys = locs['x'].to_list(), locs['y'].to_list()
    n = len(xs)
    w = max(xs) - min(xs) if max(xs)>min(xs) else 40.0
    h = max(ys) - min(ys) if max(ys)>min(ys) else 30.0
    cfg = NetworkConfig(num_nodes=n, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)

    # Build env provider (conservative mapping)
    s = loader.sensor_data.dropna(subset=['humidity','temperature'])
    h_vals = s['humidity'].values
    t_vals = s['temperature'].values
    h_p33 = float(np.percentile(h_vals, 33))
    h_p66 = float(np.percentile(h_vals, 66))
    t_med = float(np.percentile(t_vals, 50))
    regimes = [
        {'name':'low', 'h': h_p33, 'shadow': 4.5},
        {'name':'mid', 'h': (h_p33+h_p66)/2, 'shadow': 7.0},
        {'name':'high','h': h_p66, 'shadow': 9.5},
    ]

    def make_env_provider(proto):
        def env_provider(round_idx: int):
            r = regimes[round_idx % 3]
            humidity_ratio = max(0.0, min(1.0, r['h']/100.0))
            temperature_c = t_med
            nf = -96.0 + (0.5 if r['name']=='mid' else (1.0 if r['name']=='high' else 0.0))
            proto.channel_model.set_env_mapping(shadowing_std=r['shadow'], noise_floor_dbm=nf)
            return (temperature_c, humidity_ratio)
        return env_provider

    def run(profile, seed):
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile=profile, verbose=False)
        minx, miny = min(xs), min(ys)
        for i,(x,y) in enumerate(zip(xs, ys)):
            proto.nodes[i].x = float(x) - minx
            proto.nodes[i].y = float(y) - miny
        envp = make_env_provider(proto)
        res = proto.run_simulation(200, env_provider=envp)
        rounds = res.get('round_statistics', [])
        pr = []
        for r in rounds:
            sp = r.get('source_packets_round', 0) or 0
            bd = r.get('bs_delivered_round', 0) or 0
            pr.append((bd/sp) if sp>0 else 0.0)
        p05 = sorted(pr)[int(0.05*(len(pr)-1))] if pr else 0.0
        return {
            'total_energy_consumed': res.get('total_energy_consumed'),
            'pdr_end2end_mean': res.get('packet_delivery_ratio_end2end'),
            'pdr_end2end_p05': p05,
            'pdr_hop': res.get('packet_delivery_ratio'),
            'lifetime': res.get('network_lifetime')
        }

    # repeats
    repeats = 5
    seeds = [9000+31*k for k in range(repeats)]
    base, robust = [], []
    for ssd in seeds:
        base.append(run('energy', ssd))
        robust.append(run('robust', ssd))

    def agg(rows, key):
        xs = [r[key] for r in rows]
        m = statistics.mean(xs)
        sd = statistics.pstdev(xs)
        ci = 1.96 * (sd / (len(xs)**0.5)) if len(xs)>1 else 0.0
        return m, ci, xs

    report = {}
    metrics = ['total_energy_consumed','pdr_end2end_mean','pdr_end2end_p05','lifetime']
    for m in metrics:
        b = agg(base, m)
        r = agg(robust, m)
        t = welch(b[2], r[2])
        report[m] = {'BASE': {'mean': b[0], 'ci95': b[1], 'values': b[2]}, 'ROBUST': {'mean': r[0], 'ci95': r[1], 'values': r[2]}, 'welch_t': t}

    out = os.path.join(os.path.dirname(__file__), '..', 'results', 'significance_compare_intel.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(report, open(out,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out)

