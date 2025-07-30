#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试LEACH协议为什么不发送数据包

问题：LEACH消耗能量但packets_transmitted=0
目标：找到根本原因并修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_protocols import LEACHProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def debug_leach_single_round():
    """调试LEACH单轮执行过程"""
    
    print("🔍 调试LEACH协议单轮执行")
    print("=" * 50)
    
    # 创建小规模网络便于调试
    config = NetworkConfig(
        num_nodes=5,
        area_width=100,
        area_height=100,
        initial_energy=2.0,
        packet_size=1024,
        base_station_x=50,
        base_station_y=50
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    protocol = LEACHProtocol(config, energy_model)
    
    print(f"网络配置:")
    print(f"- 节点数: {config.num_nodes}")
    print(f"- 区域: {config.area_width}×{config.area_height}m")
    print(f"- 基站位置: ({config.base_station_x}, {config.base_station_y})")
    print(f"- 数据包大小: {config.packet_size} bytes")
    
    print(f"\n节点初始状态:")
    for i, node in enumerate(protocol.nodes):
        print(f"  节点{i}: 位置({node.x:.1f}, {node.y:.1f}), 能量{node.current_energy:.3f}J")
    
    # 第1步：簇头选择
    print(f"\n🔸 第1步：簇头选择")
    cluster_heads = protocol._select_cluster_heads()
    print(f"选中的簇头数量: {len(cluster_heads)}")
    
    for ch in cluster_heads:
        ch_index = protocol.nodes.index(ch)
        print(f"  簇头{ch_index}: 位置({ch.x:.1f}, {ch.y:.1f}), 能量{ch.current_energy:.3f}J")
    
    if not cluster_heads:
        print("❌ 没有选中任何簇头！这可能是问题所在")
        return
    
    # 第2步：簇形成
    print(f"\n🔸 第2步：簇形成")
    protocol._form_clusters(cluster_heads)
    
    print(f"形成的簇数量: {len(protocol.clusters)}")
    for cluster_id, cluster_info in protocol.clusters.items():
        ch = cluster_info['head']
        members = cluster_info['members']
        ch_index = protocol.nodes.index(ch)
        member_indices = [protocol.nodes.index(m) for m in members]
        print(f"  簇{cluster_id}: 簇头{ch_index}, 成员{member_indices}")
    
    # 第3步：稳态通信
    print(f"\n🔸 第3步：稳态通信")
    
    # 记录通信前的能量
    energy_before = {i: node.current_energy for i, node in enumerate(protocol.nodes)}
    
    # 手动执行稳态通信并记录详细过程
    total_energy_consumed = 0.0
    packets_transmitted = 0
    packets_received = 0
    
    print("簇内通信过程:")
    
    # 簇内通信：成员节点向簇头发送数据
    for cluster_id, cluster_info in protocol.clusters.items():
        ch = cluster_info['head']
        members = cluster_info['members']
        ch_index = protocol.nodes.index(ch)
        
        print(f"  处理簇{cluster_id} (簇头{ch_index}):")
        
        if not ch.is_alive:
            print(f"    ❌ 簇头{ch_index}已死亡，跳过")
            continue
        
        if not members:
            print(f"    ⚠️ 簇{cluster_id}没有成员节点")
            continue
        
        for member in members:
            member_index = protocol.nodes.index(member)
            
            if not member.is_alive:
                print(f"    ❌ 成员{member_index}已死亡，跳过")
                continue
            
            # 计算传输距离
            distance = protocol._calculate_distance(member, ch)
            
            # 计算传输能耗
            tx_energy = energy_model.calculate_transmission_energy(
                config.packet_size * 8,  # 转换为bits
                distance
            )
            
            # 计算接收能耗
            rx_energy = energy_model.calculate_reception_energy(
                config.packet_size * 8
            )
            
            print(f"    📡 成员{member_index}→簇头{ch_index}: 距离{distance:.1f}m, 发射{tx_energy*1000:.3f}mJ, 接收{rx_energy*1000:.3f}mJ")
            
            # 更新节点能量
            member.current_energy -= tx_energy
            ch.current_energy -= rx_energy
            
            total_energy_consumed += (tx_energy + rx_energy)
            packets_transmitted += 1
            packets_received += 1
            
            # 检查节点是否耗尽能量
            if member.current_energy <= 0:
                member.is_alive = False
                member.current_energy = 0
                print(f"    💀 成员{member_index}能量耗尽")
    
    print(f"\n簇头向基站通信过程:")
    
    # 簇头向基站发送聚合数据
    for cluster_id, cluster_info in protocol.clusters.items():
        ch = cluster_info['head']
        ch_index = protocol.nodes.index(ch)
        
        if not ch.is_alive:
            print(f"    ❌ 簇头{ch_index}已死亡，跳过")
            continue
        
        # 计算到基站的距离
        distance_to_bs = protocol._calculate_distance_to_bs(ch)
        
        # 计算传输能耗 (聚合后的数据包)
        tx_energy = energy_model.calculate_transmission_energy(
            config.packet_size * 8,
            distance_to_bs,
            tx_power_dbm=5.0  # 向基站传输使用更高功率
        )
        
        print(f"    📡 簇头{ch_index}→基站: 距离{distance_to_bs:.1f}m, 发射{tx_energy*1000:.3f}mJ")
        
        ch.current_energy -= tx_energy
        total_energy_consumed += tx_energy
        packets_transmitted += 1
        
        # 检查簇头是否耗尽能量
        if ch.current_energy <= 0:
            ch.is_alive = False
            ch.current_energy = 0
            print(f"    💀 簇头{ch_index}能量耗尽")
    
    # 记录通信后的能量
    energy_after = {i: node.current_energy for i, node in enumerate(protocol.nodes)}
    
    print(f"\n📊 通信结果统计:")
    print(f"发送数据包: {packets_transmitted}")
    print(f"接收数据包: {packets_received}")
    print(f"总能耗: {total_energy_consumed*1000:.3f} mJ")
    
    print(f"\n节点能量变化:")
    for i, node in enumerate(protocol.nodes):
        energy_change = energy_before[i] - energy_after[i]
        print(f"  节点{i}: {energy_before[i]:.6f}J → {energy_after[i]:.6f}J (消耗{energy_change*1000:.3f}mJ)")
    
    # 与官方run_simulation对比
    print(f"\n🔸 对比官方run_simulation结果:")
    
    # 重新创建协议实例
    protocol2 = LEACHProtocol(config, energy_model)
    result = protocol2.run_simulation(max_rounds=1)
    
    print(f"官方结果:")
    print(f"- 总能耗: {result['total_energy_consumed']*1000:.3f} mJ")
    print(f"- 网络生存时间: {result['network_lifetime']} 轮")
    print(f"- 发送包数: {result.get('additional_metrics', {}).get('total_packets_sent', 'N/A')}")
    print(f"- 接收包数: {result.get('additional_metrics', {}).get('total_packets_received', 'N/A')}")
    
    # 分析差异
    if packets_transmitted == 0:
        print(f"\n❌ 问题确认：手动执行也没有发送数据包")
        print("可能原因:")
        print("1. 簇头选择失败")
        print("2. 簇形成失败") 
        print("3. 成员节点为空")
        print("4. 节点状态异常")
    else:
        print(f"\n✅ 手动执行成功发送了{packets_transmitted}个数据包")
        print("问题可能在run_simulation的统计逻辑中")

def analyze_cluster_formation():
    """分析簇形成过程"""
    
    print(f"\n🔍 详细分析簇形成过程")
    print("=" * 50)
    
    config = NetworkConfig(num_nodes=5, area_width=100, area_height=100)
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    protocol = LEACHProtocol(config, energy_model)
    
    # 强制设置一个簇头用于测试
    protocol.nodes[0].is_cluster_head = True
    print(f"强制设置节点0为簇头")
    
    # 执行簇形成
    cluster_heads = [protocol.nodes[0]]  # 使用强制设置的簇头
    protocol._form_clusters(cluster_heads)
    
    print(f"簇形成结果:")
    print(f"- 簇数量: {len(protocol.clusters)}")
    
    for cluster_id, cluster_info in protocol.clusters.items():
        ch = cluster_info['head']
        members = cluster_info['members']
        ch_index = protocol.nodes.index(ch)
        member_indices = [protocol.nodes.index(m) for m in members]
        
        print(f"- 簇{cluster_id}: 簇头{ch_index}, 成员{member_indices}")
        
        # 检查成员是否包含簇头自己
        if ch in members:
            print(f"  ⚠️ 警告：簇头{ch_index}也在成员列表中")
        
        if not members:
            print(f"  ❌ 问题：簇{cluster_id}没有成员节点！")

def main():
    """主函数"""
    
    print("🔧 LEACH协议调试分析")
    print("=" * 60)
    print("目的：找出LEACH为什么不发送数据包的根本原因")
    print()
    
    # 1. 调试单轮执行
    debug_leach_single_round()
    
    # 2. 分析簇形成
    analyze_cluster_formation()
    
    print(f"\n📋 调试总结:")
    print("=" * 30)
    print("通过详细调试，我们可以确定LEACH协议的具体问题")
    print("然后针对性地修复代码")

if __name__ == "__main__":
    main()
