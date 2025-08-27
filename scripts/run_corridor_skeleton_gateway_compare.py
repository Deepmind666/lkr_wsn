#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from experiment_logger import ExperimentLogger
from topology_generators import corridor
from gateway_selector import GatewaySelector, GatewayConfig
from skeleton_selector import SkeletonSelector, SkeletonConfig

random.seed(42)

if __name__ == '__main__':
    w,h = 300.0,100.0
    cfg = NetworkConfig(num_nodes=50, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    scenarios = []

    def prepare_nodes(proto):
        pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)
        for i,(x,y) in enumerate(pts):
            proto.nodes[i].x = x
            proto.nodes[i].y = y

    # baseline
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=False, enable_skeleton=False)
    prepare_nodes(proto)
    res_base = proto.run_simulation(200)

    # gateway K=1
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False)
    prepare_nodes(proto)
    proto.gateway_selector = GatewaySelector(GatewayConfig(k=1))
    res_gw = proto.run_simulation(200)

    # skeleton k=1
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=False, enable_skeleton=True)
    prepare_nodes(proto)
    proto.skeleton_selector = SkeletonSelector(SkeletonConfig(k=1))
    res_sk = proto.run_simulation(200)

    # skeleton+gateway
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=True)
    prepare_nodes(proto)
    proto.gateway_selector = GatewaySelector(GatewayConfig(k=1))
    proto.skeleton_selector = SkeletonSelector(SkeletonConfig(k=1))
    res_both = proto.run_simulation(200)

    out = {
        'BASE': {k: res_base.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes')},
        'GW_K1': {k: res_gw.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes')},
        'SK_K1': {k: res_sk.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes')},
        'BOTH': {k: res_both.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes')},
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'corridor_skeleton_gateway_compare_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

