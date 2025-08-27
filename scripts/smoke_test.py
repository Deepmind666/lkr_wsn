#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol

if __name__ == '__main__':
    cfg = NetworkConfig(num_nodes=25, area_width=100.0, area_height=100.0, initial_energy=2.0, packet_size=1024)
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True)
    res = proto.run_simulation(100)
    print({k: res[k] for k in ('packet_delivery_ratio','total_energy_consumed','network_lifetime','final_alive_nodes')})

