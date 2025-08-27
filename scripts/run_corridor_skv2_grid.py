#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random, itertools
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from experiment_logger import ExperimentLogger
from topology_generators import corridor
from skeleton_selector import SkeletonSelector, SkeletonConfig

random.seed(42)

if __name__ == '__main__':
    w,h = 300.0,100.0
    cfg = NetworkConfig(num_nodes=50, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    grid = list(itertools.product([2], [0.10, 0.15, 0.20], [0.70, 0.75, 0.80]))
    items = []
    logger = ExperimentLogger()
    for k, d_ratio, q_far in grid:
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=False, enable_skeleton=True)
        # place corridor nodes
        pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)
        for i,(x,y) in enumerate(pts):
            proto.nodes[i].x = x
            proto.nodes[i].y = y
        # configure skeleton v2
        proto.skeleton_selector = SkeletonSelector(SkeletonConfig(k=k, d_threshold_ratio=d_ratio, q_far=q_far))
        res = proto.run_simulation(200)
        row = {
            'k': k, 'd_ratio': d_ratio, 'q_far': q_far,
            'total_energy_consumed': res.get('total_energy_consumed'),
            'pdr_end2end': res.get('packet_delivery_ratio_end2end'),
            'pdr_hop': res.get('packet_delivery_ratio'),
            'lifetime': res.get('network_lifetime')
        }
        items.append(row)
        logger.log('corridor_skv2_grid_50x200', {'k':k, 'd_ratio':d_ratio, 'q_far':q_far}, row)
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'corridor_skv2_grid_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(items, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

