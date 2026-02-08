#!/usr/bin/env python3
"""测试信道模型PDR值 - 不同发射功率"""
import sys
sys.path.insert(0, 'src')
from realistic_channel_model import RealisticChannelModel, EnvironmentType

channel = RealisticChannelModel(EnvironmentType.INDOOR_OFFICE)

print("=== 发射功率 0dBm ===")
for dist in [10, 50, 100, 150, 200]:
    metrics = channel.calculate_link_metrics(0.0, dist, 25.0, 0.5)
    print(f"d={dist}m: PDR={metrics['pdr']:.4f}")

print("\n=== 发射功率 10dBm ===")
for dist in [10, 50, 100, 150, 200]:
    metrics = channel.calculate_link_metrics(10.0, dist, 25.0, 0.5)
    print(f"d={dist}m: PDR={metrics['pdr']:.4f}")
