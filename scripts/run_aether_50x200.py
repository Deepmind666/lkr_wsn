#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol

if __name__ == '__main__':
    cfg = NetworkConfig(num_nodes=50, area_width=100.0, area_height=100.0, initial_energy=2.0, packet_size=1024)
    aether = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True)
    res = aether.run_simulation(200)
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'aether_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"Saved results to {out_path}")

