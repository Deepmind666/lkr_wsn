#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random, itertools, statistics
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from experiment_logger import ExperimentLogger
from topology_generators import corridor

random.seed(42)

def run_once(r_prob, delta_dbm, seed):
    random.seed(seed)
    w,h = 300.0,100.0
    cfg = NetworkConfig(num_nodes=50, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False)
    for i,(x,y) in enumerate(pts): proto.nodes[i].x, proto.nodes[i].y = x,y
    proto.safety_fallback_enabled = True
    proto.safety_T = 1
    proto.safety_theta = 0.1
    proto.safety_redundant_uplink = True
    proto.safety_redundant_prob = r_prob
    proto.safety_power_bump = True
    proto.safety_power_bump_delta = delta_dbm
    res = proto.run_simulation(200)
    rounds = res.get('round_statistics', [])
    per_round = []
    for r in rounds:
        sp = r.get('source_packets_round', 0) or 0
        bd = r.get('bs_delivered_round', 0) or 0
        per_round.append((bd/sp) if sp>0 else 0.0)
    p05 = sorted(per_round)[int(0.05*(len(per_round)-1))] if per_round else 0.0
    return {
        'total_energy_consumed': res.get('total_energy_consumed'),
        'pdr_end2end_mean': res.get('packet_delivery_ratio_end2end'),
        'pdr_end2end_p05': p05,
        'pdr_hop': res.get('packet_delivery_ratio'),
        'lifetime': res.get('network_lifetime')
    }

if __name__ == '__main__':
    r_probs = [0.25, 0.5, 1.0]
    deltas = [1.0, 2.0]
    repeats = 5
    grid = list(itertools.product(r_probs, deltas))
    logger = ExperimentLogger()
    rows = []
    for r_prob, delta in grid:
        vals = []
        for k in range(repeats):
            seed = 1000 + 97*k
            res = run_once(r_prob, delta, seed)
            vals.append(res)
            logger.log('safety_tradeoff_50x200', {'r_prob': r_prob, 'delta': delta, 'rep': k}, res)
        # aggregate
        def mean_ci(x):
            m = statistics.mean(x)
            sd = statistics.pstdev(x)
            # 粗略95%CI（正态近似且n小）：±1.96*sd/sqrt(n)
            ci = 1.96 * (sd / (len(x)**0.5)) if len(x)>1 else 0.0
            return m, ci
        e = [v['total_energy_consumed'] for v in vals]
        m_e, ci_e = mean_ci(e)
        p = [v['pdr_end2end_mean'] for v in vals]
        m_p, ci_p = mean_ci(p)
        q = [v['pdr_end2end_p05'] for v in vals]
        m_q, ci_q = mean_ci(q)
        rows.append({
            'r_prob': r_prob,
            'delta_dbm': delta,
            'energy_mean': m_e, 'energy_ci95': ci_e,
            'pdr_end2end_mean': m_p, 'pdr_end2end_ci95': ci_p,
            'pdr_end2end_p05_mean': m_q, 'pdr_end2end_p05_ci95': ci_q
        })
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results')
    os.makedirs(out_path, exist_ok=True)
    json.dump(rows, open(os.path.join(out_path,'safety_tradeoff_grid_50x200.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    # write CSV
    csv_path = os.path.join(out_path, 'safety_tradeoff_grid_50x200.csv')
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write('r_prob,delta_dbm,energy_mean,energy_ci95,pdr_end2end_mean,pdr_end2end_ci95,pdr_end2end_p05_mean,pdr_end2end_p05_ci95\n')
        for r in rows:
            f.write(f"{r['r_prob']},{r['delta_dbm']},{r['energy_mean']:.4f},{r['energy_ci95']:.4f},{r['pdr_end2end_mean']:.4f},{r['pdr_end2end_ci95']:.4f},{r['pdr_end2end_p05_mean']:.4f},{r['pdr_end2end_p05_ci95']:.4f}\n")
    print('Saved', os.path.join(out_path,'safety_tradeoff_grid_50x200.json'), 'and', csv_path)

