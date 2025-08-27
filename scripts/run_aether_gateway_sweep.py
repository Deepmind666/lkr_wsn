#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, time, concurrent.futures as fut
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol

def run_once(k:int)->dict:
    cfg = NetworkConfig(num_nodes=50, area_width=100.0, area_height=100.0, initial_energy=2.0, packet_size=1024)
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True)
    # 动态设置 gateway k
    if not hasattr(proto, 'gateway_selector'):
        from gateway_selector import GatewaySelector, GatewayConfig
        proto.gateway_selector = GatewaySelector(GatewayConfig(k=k))
    else:
        proto.gateway_selector.cfg.k = k
    res = proto.run_simulation(200)
    keep = ['total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes','network_lifetime']
    return {'k': k, **{k1: res.get(k1) for k1 in keep}}

if __name__ == '__main__':
    ks = [1,2,3]
    out_items = []
    with fut.ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for item in ex.map(run_once, ks):
            out_items.append(item)
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'aether_gateway_sweep_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path,'w',encoding='utf-8') as f:
        json.dump(out_items, f, ensure_ascii=False, indent=2)
    print('Saved', out_path)

