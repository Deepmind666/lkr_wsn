#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from experiment_logger import ExperimentLogger
from topology_generators import corridor
from skeleton_selector import SkeletonSelector, SkeletonConfig
from gateway_selector import GatewaySelector, GatewayConfig

random.seed(42)

if __name__ == '__main__':
    w,h = 400.0,100.0  # 4:1 corridor
    cfg = NetworkConfig(num_nodes=50, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    logger = ExperimentLogger()
    pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=4.0)

    # GW K=1
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False)
    for i,(x,y) in enumerate(pts): proto.nodes[i].x, proto.nodes[i].y = x,y
    gw = proto.run_simulation(200)
    logger.log('corridor41_compare', {'method':'GW_K1'}, gw)

    # BOTH conditional (skeleton as candidates only when far_ratio high)
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=True)
    for i,(x,y) in enumerate(pts): proto.nodes[i].x, proto.nodes[i].y = x,y
    proto.skeleton_selector = SkeletonSelector(SkeletonConfig(k=2, d_threshold_ratio=0.15, q_far=0.75))
    proto.gateway_selector = GatewaySelector(GatewayConfig(k=1))
    both = proto.run_simulation(200)
    logger.log('corridor41_compare', {'method':'BOTH_conditional'}, both)

    out = {
        'GW_K1': {k: gw.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes')},
        'BOTH_conditional': {k: both.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes')},
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'corridor41_compare_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

