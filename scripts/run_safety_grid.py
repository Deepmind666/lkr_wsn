#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random, itertools
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from experiment_logger import ExperimentLogger
from topology_generators import corridor

random.seed(42)

if __name__ == '__main__':
    w,h = 300.0,100.0
    cfg = NetworkConfig(num_nodes=50, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    grid = list(itertools.product([1,2], [0.1,0.2]))  # (T, theta)
    logger = ExperimentLogger()
    out = []
    pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)
    for T, th in grid:
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False)
        for i,(x,y) in enumerate(pts):
            proto.nodes[i].x = x
            proto.nodes[i].y = y
        proto.safety_fallback_enabled = True
        proto.safety_T = T
        proto.safety_theta = th
        res = proto.run_simulation(200)
        # summarize
        rounds = res.get('round_statistics', [])
        per_round = []
        for r in rounds:
            sp = r.get('source_packets_round', 0) or 0
            bd = r.get('bs_delivered_round', 0) or 0
            per_round.append((bd / sp) if sp > 0 else 0.0)
        per_round_sorted = sorted(per_round)
        p05 = per_round_sorted[int(0.05*(len(per_round_sorted)-1))] if per_round_sorted else 0.0
        out.append({
            'T': T,
            'theta': th,
            'total_energy_consumed': res.get('total_energy_consumed'),
            'pdr_end2end_mean': res.get('packet_delivery_ratio_end2end'),
            'pdr_end2end_p05': p05,
            'pdr_hop': res.get('packet_delivery_ratio'),
            'lifetime': res.get('network_lifetime')
        })
        logger.log('corridor_safety_grid_50x200', {'T':T, 'theta':th}, out[-1])
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'corridor_safety_grid_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

