#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random, statistics
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from topology_generators import corridor

random.seed(42)

def bootstrap_ci(xs, n_boot=2000, conf=0.95):
    if not xs: return (0.0, 0.0)
    import math
    rng = random.Random(12345)
    samples = []
    for _ in range(n_boot):
        s = [xs[rng.randrange(len(xs))] for _ in xs]
        samples.append(statistics.mean(s))
    samples.sort()
    lo = samples[int(((1-conf)/2)*len(samples))]
    hi = samples[int((1-(1-conf)/2)*len(samples))-1]
    return lo, hi

if __name__ == '__main__':
    # Compare Energy vs Robust with bootstrap CI
    w,h = 300.0,100.0
    cfg = NetworkConfig(50, w, h, 2.0, 1024)
    pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)
    def run(profile, seed):
        random.seed(seed)
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile=profile, verbose=False)
        for i,(x,y) in enumerate(pts): proto.nodes[i].x, proto.nodes[i].y = x,y
        res = proto.run_simulation(200)
        rounds = res.get('round_statistics', [])
        per_round = [(r.get('bs_delivered_round',0)/(r.get('source_packets_round',1) or 1)) for r in rounds]
        return res['total_energy_consumed'], res['packet_delivery_ratio_end2end'], statistics.mean(per_round), min(per_round)
    seeds = [7000+37*k for k in range(10)]
    e_energy, e_pdr, e_pdr_round, e_min = [], [], [], []
    r_energy, r_pdr, r_pdr_round, r_min = [], [], [], []
    for s in seeds:
        E = run('energy', s)
        R = run('robust', s)
        e_energy.append(E[0]); e_pdr.append(E[1]); e_pdr_round.append(E[2]); e_min.append(E[3])
        r_energy.append(R[0]); r_pdr.append(R[1]); r_pdr_round.append(R[2]); r_min.append(R[3])
    report = {
        'energy': {
            'energy': {'mean': statistics.mean(e_energy), 'ci': bootstrap_ci(e_energy)},
            'pdr_mean': {'mean': statistics.mean(e_pdr), 'ci': bootstrap_ci(e_pdr)},
            'pdr_round_mean': {'mean': statistics.mean(e_pdr_round), 'ci': bootstrap_ci(e_pdr_round)},
            'pdr_round_min': {'mean': statistics.mean(e_min), 'ci': bootstrap_ci(e_min)},
        },
        'robust': {
            'energy': {'mean': statistics.mean(r_energy), 'ci': bootstrap_ci(r_energy)},
            'pdr_mean': {'mean': statistics.mean(r_pdr), 'ci': bootstrap_ci(r_pdr)},
            'pdr_round_mean': {'mean': statistics.mean(r_pdr_round), 'ci': bootstrap_ci(r_pdr_round)},
            'pdr_round_min': {'mean': statistics.mean(r_min), 'ci': bootstrap_ci(r_min)},
        }
    }
    out = os.path.join(os.path.dirname(__file__), '..', 'results', 'bootstrap_compare_50x200.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(report, open(out,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out)

