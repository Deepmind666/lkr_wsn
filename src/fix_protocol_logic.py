#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复协议逻辑不一致问题

目的：确保三个协议在相同条件下进行公平比较
问题：LEACH/PEGASIS在单轮测试中没有发送数据包，但Enhanced EEHFR发送了
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def analyze_protocol_differences():
    """分析三个协议的逻辑差异"""
    
    print("🔍 分析协议逻辑差异")
    print("=" * 40)
    
    # 创建测试配置
    config = NetworkConfig(
        num_nodes=5,
        area_width=50,
        area_height=50,
        initial_energy=1.0,
        packet_size=1024,
        base_station_x=25,
        base_station_y=25
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 创建协议实例
    leach = LEACHProtocol(config, energy_model)
    pegasis = PEGASISProtocol(config, energy_model)
    eehfr = IntegratedEnhancedEEHFRProtocol(config)
    
    print("📊 协议初始状态对比:")
    print(f"LEACH节点数: {len(leach.nodes)}")
    print(f"PEGASIS节点数: {len(pegasis.nodes)}")
    print(f"Enhanced EEHFR节点数: {len(eehfr.nodes)}")
    
    # 分析LEACH的第一轮
    print(f"\n🔍 LEACH第一轮分析:")
    leach_initial_energy = sum(node.current_energy for node in leach.nodes)
    print(f"初始总能量: {leach_initial_energy:.6f}J")
    
    # 手动执行LEACH的一轮
    alive_nodes = [node for node in leach.nodes if node.is_alive]
    print(f"存活节点: {len(alive_nodes)}")
    
    # 检查簇头选择
    cluster_heads = leach._select_cluster_heads()
    print(f"选择的簇头数: {len(cluster_heads)}")
    
    # 检查簇形成
    leach._form_clusters(cluster_heads)
    print(f"簇数量: {len(leach.clusters)}")
    
    # 检查稳态通信前的状态
    print(f"稳态通信前的簇信息:")
    for cluster_id, cluster_info in leach.clusters.items():
        ch = cluster_info['head']
        members = cluster_info['members']
        print(f"  簇{cluster_id}: 簇头节点{ch.id}, 成员{len(members)}个")
    
    # 执行稳态通信
    print(f"执行稳态通信...")
    leach._steady_state_communication()
    
    leach_final_energy = sum(node.current_energy for node in leach.nodes)
    leach_energy_consumed = leach_initial_energy - leach_final_energy
    print(f"LEACH能耗: {leach_energy_consumed:.6f}J")
    print(f"LEACH发送包数: {leach.stats['packets_transmitted']}")
    print(f"LEACH接收包数: {leach.stats['packets_received']}")
    
    # 分析Enhanced EEHFR的第一轮
    print(f"\n🔍 Enhanced EEHFR第一轮分析:")
    eehfr_initial_energy = sum(node.current_energy for node in eehfr.nodes)
    print(f"初始总能量: {eehfr_initial_energy:.6f}J")
    
    # 手动执行Enhanced EEHFR的一轮
    eehfr._select_cluster_heads()
    cluster_heads_eehfr = [node for node in eehfr.nodes if node.is_cluster_head]
    print(f"选择的簇头数: {len(cluster_heads_eehfr)}")
    
    eehfr._form_clusters()
    
    # 执行数据传输
    packets_sent, packets_received, energy_consumed = eehfr._perform_data_transmission()
    
    eehfr_final_energy = sum(node.current_energy for node in eehfr.nodes)
    eehfr_actual_energy = eehfr_initial_energy - eehfr_final_energy
    
    print(f"Enhanced EEHFR能耗: {eehfr_actual_energy:.6f}J")
    print(f"Enhanced EEHFR发送包数: {packets_sent}")
    print(f"Enhanced EEHFR接收包数: {packets_received}")
    
    # 对比分析
    print(f"\n📊 对比分析:")
    print(f"LEACH vs Enhanced EEHFR:")
    print(f"  能耗比: {leach_energy_consumed/eehfr_actual_energy:.2f}:1")
    print(f"  发送包数比: {leach.stats['packets_transmitted']}:{packets_sent}")
    
    # 问题诊断
    print(f"\n⚠️ 问题诊断:")
    if leach.stats['packets_transmitted'] == 0:
        print("❌ LEACH没有发送数据包，可能的原因:")
        print("   1. 没有选择到簇头")
        print("   2. 簇头没有成员节点")
        print("   3. 稳态通信逻辑有问题")
    
    if packets_sent > 0 and eehfr_actual_energy < leach_energy_consumed * 0.5:
        print("❌ Enhanced EEHFR能耗异常低，可能的原因:")
        print("   1. 能耗计算有bug")
        print("   2. 协议逻辑过于简化")
        print("   3. 距离计算有问题")

def check_energy_calculation_consistency():
    """检查能耗计算的一致性"""
    
    print(f"\n🔋 检查能耗计算一致性")
    print("=" * 40)
    
    # 使用相同的能耗模型
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 测试相同条件下的能耗计算
    packet_size = 1024
    distance = 50
    tx_power = 0
    
    tx_energy = energy_model.calculate_transmission_energy(packet_size, distance, tx_power)
    rx_energy = energy_model.calculate_reception_energy(packet_size)
    
    print(f"标准能耗计算 (1024 bits, 50m, 0dBm):")
    print(f"  发射能耗: {tx_energy*1000:.3f} mJ")
    print(f"  接收能耗: {rx_energy*1000:.3f} mJ")
    print(f"  总能耗: {(tx_energy + rx_energy)*1000:.3f} mJ")
    
    # 如果10个节点都发送1个包，总能耗应该是多少？
    expected_total_energy = 10 * (tx_energy + rx_energy)  # 假设每个节点都发送和接收
    print(f"\n预期10节点总能耗: {expected_total_energy*1000:.3f} mJ")
    
    return expected_total_energy

def propose_fix():
    """提出修复方案"""
    
    print(f"\n🔧 修复方案")
    print("=" * 40)
    
    print("问题根源:")
    print("1. LEACH/PEGASIS可能在第一轮没有正确执行数据传输")
    print("2. Enhanced EEHFR的能耗计算可能有问题")
    print("3. 三个协议的数据传输逻辑不一致")
    
    print(f"\n修复方案:")
    print("1. 统一数据传输逻辑:")
    print("   - 确保所有协议都在每轮发送数据")
    print("   - 使用相同的能耗计算方法")
    print("   - 统一数据包大小和传输距离")
    
    print("2. 修复Enhanced EEHFR:")
    print("   - 检查能耗累加是否正确")
    print("   - 确保所有传输都被计算")
    print("   - 验证距离计算的准确性")
    
    print("3. 修复LEACH/PEGASIS:")
    print("   - 确保第一轮就开始数据传输")
    print("   - 检查簇头选择和成员分配")
    print("   - 验证稳态通信的执行")
    
    print("4. 统一实验条件:")
    print("   - 使用相同的网络配置")
    print("   - 使用相同的能耗模型")
    print("   - 使用相同的统计方法")

def main():
    """主函数"""
    
    print("🔧 修复协议逻辑不一致问题")
    print("=" * 60)
    print("目的: 确保三个协议公平比较，修复能耗异常问题")
    print()
    
    # 1. 分析协议差异
    analyze_protocol_differences()
    
    # 2. 检查能耗计算一致性
    expected_energy = check_energy_calculation_consistency()
    
    # 3. 提出修复方案
    propose_fix()
    
    print(f"\n📋 总结:")
    print("=" * 30)
    print("发现的主要问题:")
    print("1. LEACH在第一轮没有发送数据包")
    print("2. Enhanced EEHFR能耗异常低")
    print("3. 协议逻辑不一致导致不公平比较")
    
    print(f"\n下一步行动:")
    print("1. 修复LEACH/PEGASIS的数据传输逻辑")
    print("2. 检查Enhanced EEHFR的能耗计算")
    print("3. 重新进行公平的对比实验")
    print("4. 实事求是地报告真实性能")

if __name__ == "__main__":
    main()
