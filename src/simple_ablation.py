#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的消融实验 - 分析Enhanced EEHFR性能问题

目的: 快速识别性能瓶颈，找出为什么Enhanced EEHFR表现不如PEGASIS
方法: 对比分析关键参数和决策逻辑

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
"""

import numpy as np
import json
import time
from typing import Dict, List

from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol

def analyze_protocol_behavior():
    """分析各协议的行为特征"""
    
    print("🔍 分析协议行为特征")
    print("=" * 50)
    
    # 创建标准测试配置
    config = NetworkConfig(
        num_nodes=20,
        area_width=50,
        area_height=50,
        initial_energy=1.0
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 测试各协议的单轮行为
    protocols = {
        'LEACH': LEACHProtocol(config, energy_model),
        'PEGASIS': PEGASISProtocol(config, energy_model),
        'Enhanced_EEHFR': IntegratedEnhancedEEHFRProtocol(config)
    }
    
    results = {}
    
    for name, protocol in protocols.items():
        print(f"\n🧪 分析 {name} 协议:")
        
        # 运行5轮测试
        result = protocol.run_simulation(max_rounds=5)
        results[name] = result
        
        print(f"   5轮后存活节点: {result['final_alive_nodes']}")
        print(f"   总能耗: {result['total_energy_consumed']*1000:.3f} mJ")
        print(f"   发送包数: {result.get('additional_metrics', {}).get('total_packets_sent', 'N/A')}")
        print(f"   接收包数: {result.get('additional_metrics', {}).get('total_packets_received', 'N/A')}")
        print(f"   投递率: {result['packet_delivery_ratio']:.3f}")
        print(f"   能效: {result['energy_efficiency']:.1f} packets/J")
    
    return results

def analyze_energy_consumption_pattern():
    """分析能耗模式"""
    
    print("\n🔋 分析能耗模式")
    print("=" * 50)
    
    config = NetworkConfig(
        num_nodes=10,  # 更小规模，便于分析
        area_width=30,
        area_height=30,
        initial_energy=0.5
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 分析单次传输的能耗
    distances = [5, 10, 20, 30, 40, 50]  # 不同距离
    packet_size = 1024 * 8  # bits
    
    print("\n📊 单次传输能耗分析:")
    print("距离(m)  传输能耗(mJ)  接收能耗(mJ)  总能耗(mJ)")
    print("-" * 50)
    
    for distance in distances:
        tx_energy = energy_model.calculate_transmission_energy(packet_size, distance, 0.0)
        rx_energy = energy_model.calculate_reception_energy(packet_size)
        total_energy = tx_energy + rx_energy
        
        print(f"{distance:6.0f}   {tx_energy*1000:10.3f}   {rx_energy*1000:10.3f}   {total_energy*1000:8.3f}")
    
    # 分析不同功率下的能耗
    print("\n📊 不同功率下的能耗分析 (距离=30m):")
    print("功率(dBm)  传输能耗(mJ)  总能耗(mJ)")
    print("-" * 35)
    
    powers = [-5, 0, 5, 8]
    for power in powers:
        tx_energy = energy_model.calculate_transmission_energy(packet_size, 30, power)
        rx_energy = energy_model.calculate_reception_energy(packet_size)
        total_energy = tx_energy + rx_energy
        
        print(f"{power:8.0f}   {tx_energy*1000:10.3f}   {total_energy*1000:8.3f}")

def compare_clustering_strategies():
    """对比分簇策略"""
    
    print("\n🎯 对比分簇策略")
    print("=" * 50)
    
    config = NetworkConfig(
        num_nodes=15,
        area_width=40,
        area_height=40,
        initial_energy=0.8
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 创建协议实例
    leach = LEACHProtocol(config, energy_model)
    enhanced_eehfr = IntegratedEnhancedEEHFRProtocol(config)
    
    print("\n📊 分簇特征对比:")
    print("协议           簇头数量  平均簇大小  簇头能耗(mJ)  成员能耗(mJ)")
    print("-" * 65)
    
    # 运行单轮分析
    for name, protocol in [("LEACH", leach), ("Enhanced_EEHFR", enhanced_eehfr)]:
        result = protocol.run_simulation(max_rounds=1)
        
        if 'additional_metrics' in result:
            cluster_heads = result['additional_metrics'].get('average_cluster_heads', 0)
            avg_cluster_size = config.num_nodes / cluster_heads if cluster_heads > 0 else 0
            total_energy = result['total_energy_consumed'] * 1000  # mJ
            
            print(f"{name:12} {cluster_heads:8.1f} {avg_cluster_size:10.1f} {total_energy:12.3f} {'N/A':12}")

def identify_performance_bottlenecks():
    """识别性能瓶颈"""
    
    print("\n⚠️ 识别性能瓶颈")
    print("=" * 50)
    
    config = NetworkConfig(
        num_nodes=20,
        area_width=50,
        area_height=50,
        initial_energy=1.0
    )
    
    # 运行较长时间的测试
    protocols = {}
    
    # PEGASIS (最佳性能)
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    pegasis = PEGASISProtocol(config, energy_model)
    pegasis_result = pegasis.run_simulation(max_rounds=100)
    protocols['PEGASIS'] = pegasis_result
    
    # Enhanced EEHFR (待分析)
    enhanced_eehfr = IntegratedEnhancedEEHFRProtocol(config)
    eehfr_result = enhanced_eehfr.run_simulation(max_rounds=100)
    protocols['Enhanced_EEHFR'] = eehfr_result
    
    print("\n📊 性能对比分析:")
    print("指标                    PEGASIS    Enhanced_EEHFR    差异")
    print("-" * 60)
    
    # 网络生存时间
    pegasis_lifetime = pegasis_result['network_lifetime']
    eehfr_lifetime = eehfr_result['network_lifetime']
    lifetime_diff = eehfr_lifetime - pegasis_lifetime
    print(f"网络生存时间(轮)        {pegasis_lifetime:8d}    {eehfr_lifetime:13d}    {lifetime_diff:+4d}")
    
    # 总能耗
    pegasis_energy = pegasis_result['total_energy_consumed']
    eehfr_energy = eehfr_result['total_energy_consumed']
    energy_diff = (eehfr_energy - pegasis_energy) / pegasis_energy * 100
    print(f"总能耗(J)               {pegasis_energy:8.3f}    {eehfr_energy:13.3f}    {energy_diff:+4.1f}%")
    
    # 能效
    pegasis_efficiency = pegasis_result['energy_efficiency']
    eehfr_efficiency = eehfr_result['energy_efficiency']
    efficiency_diff = (eehfr_efficiency - pegasis_efficiency) / pegasis_efficiency * 100
    print(f"能效(packets/J)         {pegasis_efficiency:8.1f}    {eehfr_efficiency:13.1f}    {efficiency_diff:+4.1f}%")
    
    # 投递率
    pegasis_pdr = pegasis_result['packet_delivery_ratio']
    eehfr_pdr = eehfr_result['packet_delivery_ratio']
    pdr_diff = (eehfr_pdr - pegasis_pdr) * 100
    print(f"投递率                  {pegasis_pdr:8.3f}    {eehfr_pdr:13.3f}    {pdr_diff:+4.1f}pp")
    
    # 分析可能的原因
    print("\n🔍 可能的性能瓶颈:")
    
    if eehfr_lifetime < pegasis_lifetime:
        print("❌ Enhanced EEHFR网络生存时间较短")
        print("   可能原因: 能耗过高、负载不均衡、簇头选择不当")
    
    if eehfr_efficiency < pegasis_efficiency:
        print("❌ Enhanced EEHFR能效较低")
        print("   可能原因: 传输功率过高、路由开销大、决策复杂度高")
    
    if eehfr_energy > pegasis_energy:
        print("❌ Enhanced EEHFR总能耗较高")
        print("   可能原因: 环境分类错误、模糊逻辑开销、多层优化冲突")
    
    return protocols

def generate_optimization_recommendations():
    """生成优化建议"""
    
    print("\n💡 优化建议")
    print("=" * 50)
    
    recommendations = [
        "1. 简化环境分类逻辑，减少计算开销",
        "2. 优化模糊逻辑规则，避免过度复杂的决策",
        "3. 调整传输功率控制策略，避免不必要的高功率传输",
        "4. 学习PEGASIS的负载均衡策略，改进簇头选择",
        "5. 减少协议开销，专注于最有效的优化组件",
        "6. 进行参数调优，针对不同网络规模优化参数",
        "7. 考虑混合策略，在适当场景下使用不同算法"
    ]
    
    for rec in recommendations:
        print(f"   {rec}")
    
    print("\n🎯 下一步行动:")
    print("   1. 实施参数调优实验")
    print("   2. 简化协议复杂度")
    print("   3. 重新测试性能")
    print("   4. 与PEGASIS进行详细对比")

def main():
    """主函数"""
    
    print("🚀 Enhanced EEHFR性能分析与优化")
    print("=" * 60)
    
    # 1. 分析协议行为
    protocol_results = analyze_protocol_behavior()
    
    # 2. 分析能耗模式
    analyze_energy_consumption_pattern()
    
    # 3. 对比分簇策略
    compare_clustering_strategies()
    
    # 4. 识别性能瓶颈
    bottleneck_results = identify_performance_bottlenecks()
    
    # 5. 生成优化建议
    generate_optimization_recommendations()
    
    # 保存分析结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"../results/performance_analysis_{timestamp}.json"
    
    analysis_results = {
        'protocol_comparison': protocol_results,
        'bottleneck_analysis': bottleneck_results,
        'timestamp': timestamp
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 分析结果已保存: {results_file}")
    print("\n✅ 性能分析完成！")

if __name__ == "__main__":
    main()
