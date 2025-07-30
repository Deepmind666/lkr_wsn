#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四协议基准对比测试

对比测试LEACH、PEGASIS、HEED、TEEN四种经典WSN路由协议
为Enhanced EEHFR协议提供全面的性能基准

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_protocols import (
    LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, TEENProtocolWrapper,
    NetworkConfig
)
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
import numpy as np
import time

def run_protocol_comparison():
    """运行四协议对比测试"""
    print("🚀 WSN四协议基准对比测试")
    print("=" * 80)
    print("📋 测试协议: LEACH, PEGASIS, HEED, TEEN")
    print("🎯 测试目标: 为Enhanced EEHFR提供性能基准")
    print("=" * 80)
    
    # 统一网络配置
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100,
        base_station_x=50.0,
        base_station_y=175.0
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    results = {}
    
    # 1. 测试LEACH协议
    print("\n1️⃣ 测试LEACH协议")
    print("-" * 50)
    start_time = time.time()
    
    leach = LEACHProtocol(config, energy_model)
    leach_results = leach.run_simulation(max_rounds=200)
    
    leach_time = time.time() - start_time
    results['LEACH'] = leach_results
    results['LEACH']['execution_time'] = leach_time
    
    print(f"✅ LEACH测试完成 (耗时: {leach_time:.2f}s)")
    print(f"   网络生存时间: {leach_results['network_lifetime']} 轮")
    print(f"   能效: {leach_results['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {leach_results['packet_delivery_ratio']:.3f}")
    
    # 2. 测试PEGASIS协议
    print("\n2️⃣ 测试PEGASIS协议")
    print("-" * 50)
    start_time = time.time()
    
    pegasis = PEGASISProtocol(config, energy_model)
    pegasis_results = pegasis.run_simulation(max_rounds=200)
    
    pegasis_time = time.time() - start_time
    results['PEGASIS'] = pegasis_results
    results['PEGASIS']['execution_time'] = pegasis_time
    
    print(f"✅ PEGASIS测试完成 (耗时: {pegasis_time:.2f}s)")
    print(f"   网络生存时间: {pegasis_results['network_lifetime']} 轮")
    print(f"   能效: {pegasis_results['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {pegasis_results['packet_delivery_ratio']:.3f}")
    
    # 3. 测试HEED协议
    print("\n3️⃣ 测试HEED协议")
    print("-" * 50)
    start_time = time.time()
    
    heed = HEEDProtocolWrapper(config, energy_model)
    heed_results = heed.run_simulation(max_rounds=200)
    
    heed_time = time.time() - start_time
    results['HEED'] = heed_results
    results['HEED']['execution_time'] = heed_time
    
    print(f"✅ HEED测试完成 (耗时: {heed_time:.2f}s)")
    print(f"   网络生存时间: {heed_results['network_lifetime']} 轮")
    print(f"   能效: {heed_results['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {heed_results['packet_delivery_ratio']:.3f}")
    
    # 4. 测试TEEN协议
    print("\n4️⃣ 测试TEEN协议")
    print("-" * 50)
    start_time = time.time()
    
    teen = TEENProtocolWrapper(config, energy_model)
    teen_results = teen.run_simulation(max_rounds=200)
    
    teen_time = time.time() - start_time
    results['TEEN'] = teen_results
    results['TEEN']['execution_time'] = teen_time
    
    print(f"✅ TEEN测试完成 (耗时: {teen_time:.2f}s)")
    print(f"   网络生存时间: {teen_results['network_lifetime']} 轮")
    print(f"   能效: {teen_results['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {teen_results['packet_delivery_ratio']:.3f}")
    
    return results

def analyze_results(results):
    """分析对比结果"""
    print("\n📊 四协议性能对比分析")
    print("=" * 80)
    
    # 性能指标对比表
    print("📈 关键性能指标对比:")
    print("-" * 100)
    print(f"{'协议':<10} {'生存时间':<10} {'总能耗(J)':<12} {'能效':<15} {'投递率':<10} {'存活节点':<10} {'执行时间(s)':<12}")
    print("-" * 100)
    
    for protocol, result in results.items():
        print(f"{protocol:<10} {result['network_lifetime']:<10} "
              f"{result['total_energy_consumed']:<12.6f} "
              f"{result['energy_efficiency']:<15.2f} "
              f"{result['packet_delivery_ratio']:<10.3f} "
              f"{result['final_alive_nodes']:<10} "
              f"{result['execution_time']:<12.2f}")
    
    # 性能排名分析
    print("\n🏆 性能排名分析:")
    print("-" * 50)
    
    # 按能效排序
    energy_efficiency_ranking = sorted(results.items(), 
                                     key=lambda x: x[1]['energy_efficiency'], 
                                     reverse=True)
    print("🔋 能效排名 (packets/J):")
    for i, (protocol, result) in enumerate(energy_efficiency_ranking, 1):
        print(f"   {i}. {protocol}: {result['energy_efficiency']:.2f} packets/J")
    
    # 按投递率排序
    pdr_ranking = sorted(results.items(), 
                        key=lambda x: x[1]['packet_delivery_ratio'], 
                        reverse=True)
    print("\n📦 投递率排名:")
    for i, (protocol, result) in enumerate(pdr_ranking, 1):
        print(f"   {i}. {protocol}: {result['packet_delivery_ratio']:.3f}")
    
    # 按网络生存时间排序
    lifetime_ranking = sorted(results.items(), 
                             key=lambda x: x[1]['network_lifetime'], 
                             reverse=True)
    print("\n⏱️ 网络生存时间排名:")
    for i, (protocol, result) in enumerate(lifetime_ranking, 1):
        print(f"   {i}. {protocol}: {result['network_lifetime']} 轮")
    
    # 协议特性分析
    print("\n🔍 协议特性分析:")
    print("-" * 50)
    
    print("📋 LEACH协议:")
    print("   ✓ 分布式聚类，随机簇头选择")
    print("   ✓ 簇头轮换机制，负载均衡")
    print("   ✓ 适用于周期性数据收集")
    
    print("\n📋 PEGASIS协议:")
    print("   ✓ 链式拓扑，贪心链构建")
    print("   ✓ 领导者轮换，数据融合")
    print("   ✓ 减少长距离传输")
    
    print("\n📋 HEED协议:")
    print("   ✓ 混合能效分布式聚类")
    print("   ✓ 概率性簇头选择")
    print("   ✓ 考虑剩余能量和通信代价")
    
    print("\n📋 TEEN协议:")
    print("   ✓ 阈值敏感反应式传输")
    print("   ✓ 硬阈值和软阈值机制")
    print("   ✓ 适用于事件驱动应用")
    
    return energy_efficiency_ranking[0][0]  # 返回最佳协议

def generate_benchmark_summary(results, best_protocol):
    """生成基准测试总结"""
    print("\n📝 基准测试总结")
    print("=" * 80)
    
    print(f"🏆 最佳协议: {best_protocol}")
    best_result = results[best_protocol]
    print(f"   能效: {best_result['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {best_result['packet_delivery_ratio']:.3f}")
    print(f"   网络生存时间: {best_result['network_lifetime']} 轮")
    
    print("\n📊 Enhanced EEHFR目标基准:")
    print(f"   目标能效: > {best_result['energy_efficiency']:.2f} packets/J")
    print(f"   目标投递率: > {best_result['packet_delivery_ratio']:.3f}")
    print(f"   目标生存时间: > {best_result['network_lifetime']} 轮")
    
    print("\n🎯 改进建议:")
    print("   1. 结合HEED的能效聚类机制")
    print("   2. 采用PEGASIS的链式数据融合")
    print("   3. 集成TEEN的阈值敏感传输")
    print("   4. 优化LEACH的负载均衡策略")
    
    print("\n✅ Week 1任务完成状态:")
    print("   ✅ LEACH协议实现完成")
    print("   ✅ PEGASIS协议实现完成")
    print("   ✅ HEED协议实现完成")
    print("   ✅ TEEN协议实现完成")
    print("   ✅ 四协议基准对比完成")
    print("   🎯 为Enhanced EEHFR提供了完整的性能基准")

def main():
    """主函数"""
    print("🚀 启动WSN四协议基准测试")
    
    # 运行对比测试
    results = run_protocol_comparison()
    
    # 分析结果
    best_protocol = analyze_results(results)
    
    # 生成总结
    generate_benchmark_summary(results, best_protocol)
    
    print("\n🎉 四协议基准测试完成!")
    print("📈 Enhanced EEHFR现在有了完整的性能基准参考")

if __name__ == "__main__":
    main()
