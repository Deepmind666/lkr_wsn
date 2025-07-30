#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的基准协议对比测试

测试LEACH、PEGASIS、HEED协议的基本性能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_protocols import LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def test_protocols():
    """测试所有基准协议"""
    
    print("🚀 WSN基准协议性能对比")
    print("=" * 60)
    
    # 创建网络配置
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )
    
    # 创建能耗模型
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    results = {}
    
    # 测试LEACH协议
    print("\n🧪 测试LEACH协议")
    print("-" * 30)
    leach = LEACHProtocol(config, energy_model)
    leach_results = leach.run_simulation(max_rounds=200)
    results['LEACH'] = leach_results
    print(f"网络生存时间: {leach_results['network_lifetime']} 轮")
    print(f"总能耗: {leach_results['total_energy_consumed']:.3f} J")
    print(f"能效: {leach_results['energy_efficiency']:.2f} packets/J")
    print(f"数据包投递率: {leach_results['packet_delivery_ratio']:.3f}")
    
    # 测试PEGASIS协议
    print("\n🧪 测试PEGASIS协议")
    print("-" * 30)
    pegasis = PEGASISProtocol(config, energy_model)
    pegasis_results = pegasis.run_simulation(max_rounds=200)
    results['PEGASIS'] = pegasis_results
    print(f"网络生存时间: {pegasis_results['network_lifetime']} 轮")
    print(f"总能耗: {pegasis_results['total_energy_consumed']:.3f} J")
    print(f"能效: {pegasis_results['energy_efficiency']:.2f} packets/J")
    print(f"数据包投递率: {pegasis_results['packet_delivery_ratio']:.3f}")
    
    # 测试HEED协议
    print("\n🧪 测试HEED协议")
    print("-" * 30)
    heed = HEEDProtocolWrapper(config, energy_model)
    heed_results = heed.run_simulation(max_rounds=200)
    results['HEED'] = heed_results
    print(f"网络生存时间: {heed_results['network_lifetime']} 轮")
    print(f"总能耗: {heed_results['total_energy_consumed']:.3f} J")
    print(f"能效: {heed_results['energy_efficiency']:.2f} packets/J")
    print(f"数据包投递率: {heed_results['packet_delivery_ratio']:.3f}")
    
    # 性能对比总结
    print("\n📊 性能对比总结")
    print("=" * 60)
    print(f"{'协议':<12} {'生存时间':<10} {'总能耗(J)':<12} {'能效':<15} {'投递率':<10}")
    print("-" * 60)
    
    for protocol, result in results.items():
        print(f"{protocol:<12} {result['network_lifetime']:<10} "
              f"{result['total_energy_consumed']:<12.3f} "
              f"{result['energy_efficiency']:<15.2f} "
              f"{result['packet_delivery_ratio']:<10.3f}")
    
    # 找出最佳协议
    best_energy_efficiency = max(results.items(), key=lambda x: x[1]['energy_efficiency'])
    best_pdr = max(results.items(), key=lambda x: x[1]['packet_delivery_ratio'])
    best_lifetime = max(results.items(), key=lambda x: x[1]['network_lifetime'])
    
    print("\n🏆 最佳性能协议:")
    print(f"   最高能效: {best_energy_efficiency[0]} ({best_energy_efficiency[1]['energy_efficiency']:.2f} packets/J)")
    print(f"   最高投递率: {best_pdr[0]} ({best_pdr[1]['packet_delivery_ratio']:.3f})")
    print(f"   最长生存时间: {best_lifetime[0]} ({best_lifetime[1]['network_lifetime']} 轮)")
    
    return results

if __name__ == "__main__":
    test_protocols()
