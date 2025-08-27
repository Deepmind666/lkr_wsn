#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random, concurrent.futures as fut
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from experiment_logger import ExperimentLogger
from topology_generators import corridor

random.seed(42)

def run_once(k:int)->dict:
    w,h = 300.0,100.0  # 走廊：3:1
    cfg = NetworkConfig(num_nodes=50, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    # override node placement by monkey-patching init (simple for now)
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True)
    # re-place nodes in corridor
    pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)
    for i,(x,y) in enumerate(pts):
        proto.nodes[i].x = x
        proto.nodes[i].y = y
    # set gateway K
    from gateway_selector import GatewaySelector, GatewayConfig
    proto.gateway_selector = GatewaySelector(GatewayConfig(k=k))
    res = proto.run_simulation(200)
    keep = ['total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes','network_lifetime']
    return {'k': k, **{k1: res.get(k1) for k1 in keep}}

if __name__ == '__main__':
    ks = [1,2,3]
    logger = ExperimentLogger()
    out_items = []
    with fut.ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for item in ex.map(run_once, ks):
            out_items.append(item)
            logger.log('corridor_gateway_sweep_50x200', {'k': item['k']}, item)
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'corridor_gateway_sweep_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path,'w',encoding='utf-8') as f:
        json.dump(out_items, f, ensure_ascii=False, indent=2)
    print('Saved', out_path)

