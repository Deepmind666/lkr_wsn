#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random, math, statistics
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from experiment_logger import ExperimentLogger
from topology_generators import uniform, corridor

random.seed(42)

# Welch t-test

def welch_ttest(a, b):
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
    return {'t_stat': t, 'df': df}


def run_once(toponame, pts):
    w = max(x for x,_ in pts)
    h = max(y for _,y in pts)
    cfg = NetworkConfig(num_nodes=len(pts), area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    def run_profile(profile, seed):
        random.seed(seed)
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile=profile)
        for i,(x,y) in enumerate(pts):
            proto.nodes[i].x = x
            proto.nodes[i].y = y
        res = proto.run_simulation(200)
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
    base, robust = [], []
    for k in range(5):
        seed = 5000 + 101*k
        base.append(run_profile('energy', seed))
        robust.append(run_profile('robust', seed))
    # aggregate
    def agg(rows, key):
        xs = [r[key] for r in rows]
        m = statistics.mean(xs)
        sd = statistics.pstdev(xs)
        ci = 1.96 * (sd / (len(xs)**0.5)) if len(xs)>1 else 0.0
        return m, ci, xs
    metrics = ['total_energy_consumed','pdr_end2end_mean','pdr_end2end_p05','lifetime']
    report = {}
    for m in metrics:
        m_base = agg(base, m)
        m_rob = agg(robust, m)
        t = welch_ttest(m_base[2], m_rob[2])
        report[m] = {
            'BASE': {'mean': m_base[0], 'ci95': m_base[1], 'values': m_base[2]},
            'ROBUST': {'mean': m_rob[0], 'ci95': m_rob[1], 'values': m_rob[2]},
            'welch_t': t
        }
    return report

if __name__ == '__main__':
    # topologies
    pts_uniform = uniform(50, 100.0, 100.0)
    pts_corridor41 = corridor(50, 400.0, 100.0, ratio=4.0)
    results = {
        'uniform_50x200': run_once('uniform', pts_uniform),
        'corridor41_50x200': run_once('corridor41', pts_corridor41)
    }
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'significance_compare_multi_topo_50x200.json')
    json.dump(results, open(path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', path)

