#!/usr/bin/env python3
"""验证Python仿真与NS-3结果对齐"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import random
import numpy as np
from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol

print("=== Python vs NS-3 PDR验证 ===\n")

# 运行多个seed取平均
results = []
for seed in [42, 123, 456, 789, 1024]:
    random.seed(seed)
    np.random.seed(seed)

    cfg = NetworkConfig(
        num_nodes=100,
        area_width=200,
        area_height=200,
        initial_energy=2.0,
        packet_size=512,
        enable_channel=True,
        channel_env='indoor_office',
        tx_power_dbm=0.0,
    )

    proto = AerisProtocol(cfg, verbose=False, seed=seed,
                          enable_cas=True, enable_fairness=True, enable_gateway=True)

    result = proto.run_simulation(max_rounds=50)
    pdr = result.get('packet_delivery_ratio_end2end', 0) * 100
    results.append(pdr)
    print(f"Seed {seed}: PDR = {pdr:.2f}%")

avg_pdr = sum(results) / len(results)
std_pdr = (sum((x - avg_pdr)**2 for x in results) / len(results))**0.5

print(f"\n=== 汇总结果 ===")
print(f"Python AERIS PDR: {avg_pdr:.2f}% ± {std_pdr:.2f}%")
print(f"NS-3 AERIS PDR:   99.98% (参考值)")
print(f"差距: {99.98 - avg_pdr:.2f}%")
