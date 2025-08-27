#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random, itertools
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from cas_selector import CASConfig, CASSelector
from experiment_logger import ExperimentLogger
from topology_generators import corridor

random.seed(42)

def p05_quantile(vals):
    if not vals: return 0.0
    xs = sorted(vals)
    k = max(0, min(len(xs)-1, int(0.05*(len(xs)-1))))
    return xs[k]

if __name__ == '__main__':
    w,h = 300.0,100.0
    cfg = NetworkConfig(num_nodes=50, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    # grid over (lambda_uncertainty, conf_threshold)
    lambdas = [0.0, 0.2, 0.5]
    cths = [0.3, 0.4]
    grid = list(itertools.product(lambdas, cths))
    logger = ExperimentLogger()
    out = []
    pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)
    for lam, cth in grid:
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False)
        # place nodes
        for i,(x,y) in enumerate(pts):
            proto.nodes[i].x = x
            proto.nodes[i].y = y
        # ensure CAS selector and set uncertainty params
        if not hasattr(proto, 'cas_selector'):
            proto.cas_selector = CASSelector(CASConfig())
        proto.cas_selector.cfg.lambda_uncertainty = lam
        proto.cas_selector.cfg.uncertainty_conf_threshold = cth
        res = proto.run_simulation(200)
        # compute round-wise end2end PDR and its 5% quantile
        rounds = res.get('round_statistics', [])
        per_round = []
        for r in rounds:
            sp = r.get('source_packets_round', 0) or 0
            bd = r.get('bs_delivered_round', 0) or 0
            per_round.append((bd / sp) if sp > 0 else 0.0)
        row = {
            'lambda_uncertainty': lam,
            'conf_threshold': cth,
            'total_energy_consumed': res.get('total_energy_consumed'),
            'pdr_end2end_mean': res.get('packet_delivery_ratio_end2end'),
            'pdr_end2end_p05': p05_quantile(per_round),
            'pdr_hop': res.get('packet_delivery_ratio'),
            'lifetime': res.get('network_lifetime')
        }
        out.append(row)
        logger.log('corridor_uncertainty_grid_50x200', {'lambda_uncertainty': lam, 'conf_th': cth}, row)
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'corridor_uncertainty_grid_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

