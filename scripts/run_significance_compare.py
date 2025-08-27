#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random, math, statistics
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from experiment_logger import ExperimentLogger
from topology_generators import corridor

random.seed(42)

# Welch's t-test (two-sample, unequal variances)
def welch_ttest(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    va = statistics.pvariance(a) if len(a) > 1 else 0.0
    vb = statistics.pvariance(b) if len(b) > 1 else 0.0
    na, nb = len(a), len(b)
    se = math.sqrt((va/na) + (vb/nb)) if na>0 and nb>0 else float('inf')
    t = (ma - mb) / se if se > 0 else 0.0
    # approximate dof (Welch–Satterthwaite)
    num = (va/na + vb/nb)**2
    den = 0.0
    if na>1: den += (va/na)**2 / (na-1)
    if nb>1: den += (vb/nb)**2 / (nb-1)
    df = num/den if den>0 else float('inf')
    # two-sided p-value via survival function approximation (using Student's t asymptotics)
    # Without SciPy, provide t, df; consumer can compute p-value externally
    return {'t_stat': t, 'df': df}

if __name__ == '__main__':
    # Scenario
    w,h = 300.0,100.0
    cfg = NetworkConfig(num_nodes=50, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)

    repeats = 5
    logger = ExperimentLogger()

    def run_proto(robust: bool, seed: int):
        random.seed(seed)
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False)
        for i,(x,y) in enumerate(pts):
            proto.nodes[i].x = x
            proto.nodes[i].y = y
        if robust:
            # Robust configuration: crisis fallback (redundant + small power bump)
            proto.safety_fallback_enabled = True
            proto.safety_T = 1
            proto.safety_theta = 0.1
            proto.safety_redundant_uplink = True
            proto.safety_redundant_prob = 1.0
            proto.safety_power_bump = True
            proto.safety_power_bump_delta = 1.0
        else:
            proto.safety_fallback_enabled = False
        res = proto.run_simulation(200)
        # compute per-round end2end
        rounds = res.get('round_statistics', [])
        pr = []
        for r in rounds:
            sp = r.get('source_packets_round', 0) or 0
            bd = r.get('bs_delivered_round', 0) or 0
            pr.append((bd/sp) if sp>0 else 0.0)
        p05 = sorted(pr)[int(0.05*(len(pr)-1))] if pr else 0.0
        out = {
            'total_energy_consumed': res.get('total_energy_consumed'),
            'pdr_end2end_mean': res.get('packet_delivery_ratio_end2end'),
            'pdr_end2end_p05': p05,
            'pdr_hop': res.get('packet_delivery_ratio'),
            'lifetime': res.get('network_lifetime')
        }
        logger.log('signif_compare_50x200', {'robust': robust, 'seed': seed}, out)
        return out

    base, robust = [], []
    for k in range(repeats):
        seed = 3000 + 133*k
        base.append(run_proto(False, seed))
        robust.append(run_proto(True, seed))

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

    out_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'significance_compare_50x200.json')
    json.dump(report, open(path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', path)

