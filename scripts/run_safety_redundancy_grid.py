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
    pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)
    grid = list(itertools.product([False, True], [False, True]))  # (redundant, power_bump)
    out = []
    logger = ExperimentLogger()
    for red, bump in grid:
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False)
        for i,(x,y) in enumerate(pts): proto.nodes[i].x, proto.nodes[i].y = x,y
        proto.safety_fallback_enabled = True
        proto.safety_T = 1
        proto.safety_theta = 0.1
        proto.safety_redundant_uplink = red
        proto.safety_power_bump = bump
        proto.safety_power_bump_delta = 2.0
        res = proto.run_simulation(200)
        # summarize p05
        rounds = res.get('round_statistics', [])
        pr = []
        for r in rounds:
            sp = r.get('source_packets_round', 0) or 0
            bd = r.get('bs_delivered_round', 0) or 0
            pr.append((bd/sp) if sp>0 else 0.0)
        pr = sorted(pr)
        p05 = pr[int(0.05*(len(pr)-1))] if pr else 0.0
        out.append({
            'redundant': red,
            'power_bump': bump,
            'total_energy_consumed': res.get('total_energy_consumed'),
            'pdr_end2end_mean': res.get('packet_delivery_ratio_end2end'),
            'pdr_end2end_p05': p05,
            'pdr_hop': res.get('packet_delivery_ratio'),
            'lifetime': res.get('network_lifetime')
        })
        logger.log('corridor_safety_redundancy_grid_50x200', {'redundant': red, 'power_bump': bump}, out[-1])
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'corridor_safety_redundancy_grid_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

