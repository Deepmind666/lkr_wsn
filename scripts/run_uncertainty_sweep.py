#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from cas_selector import CASConfig
from experiment_logger import ExperimentLogger
from topology_generators import corridor

random.seed(42)

if __name__ == '__main__':
    w,h = 300.0,100.0
    cfg = NetworkConfig(num_nodes=50, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    lambdas = [0.0, 0.2, 0.5]
    logger = ExperimentLogger()
    out = []
    for lam in lambdas:
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False)
        # corridor placement
        pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)
        for i,(x,y) in enumerate(pts):
            proto.nodes[i].x = x
            proto.nodes[i].y = y
        # ensure CAS selector exists and configure uncertainty
        if not hasattr(proto, 'cas_selector'):
            from cas_selector import CASSelector
            proto.cas_selector = CASSelector(CASConfig())
        proto.cas_selector.cfg.lambda_uncertainty = lam
        res = proto.run_simulation(200)
        row = {
            'lambda_uncertainty': lam,
            'total_energy_consumed': res.get('total_energy_consumed'),
            'pdr_end2end': res.get('packet_delivery_ratio_end2end'),
            'pdr_hop': res.get('packet_delivery_ratio'),
            'lifetime': res.get('network_lifetime')
        }
        out.append(row)
        logger.log('corridor_uncertainty_sweep_50x200', {'lambda_uncertainty': lam}, row)
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'corridor_uncertainty_sweep_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

