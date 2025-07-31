#!/usr/bin/env python3
"""
调试基准协议的简单测试脚本
"""

import sys
import os

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from enhanced_eehfr_2_0_redesigned import EnhancedEEHFR2Protocol, EnhancedEEHFR2Config

def debug_baseline():
    """调试基准协议"""
    print("🔧 调试基准Enhanced EEHFR 2.0协议")
    print("=" * 50)
    
    # 使用更宽松的配置
    config = EnhancedEEHFR2Config(
        num_nodes=20,  # 减少节点数
        area_width=50,  # 减少区域大小
        area_height=50,
        base_station_x=25,
        base_station_y=60,  # 较近的基站
        initial_energy=10.0,  # 更高的初始能量
        packet_size=1000  # 更小的数据包
    )
    
    print(f"📊 测试配置:")
    print(f"   - 节点数: {config.num_nodes}")
    print(f"   - 区域: {config.area_width}×{config.area_height}m²")
    print(f"   - 基站: ({config.base_station_x}, {config.base_station_y})")
    print(f"   - 初始能量: {config.initial_energy}J")
    print(f"   - 数据包大小: {config.packet_size} bytes")
    print()
    
    # 初始化协议
    protocol = EnhancedEEHFR2Protocol(config)
    
    print("🚀 开始仿真...")
    result = protocol.run_simulation(max_rounds=10)
    
    print("\n📈 仿真结果:")
    print(f"   - 运行轮数: {result['network_lifetime']}")
    print(f"   - 传输数据包: {result['packets_transmitted']}")
    print(f"   - 基站接收: {result['packets_received']}")
    print(f"   - 投递率: {result['packet_delivery_ratio']:.3f}")
    print(f"   - 能效: {result['energy_efficiency']:.2f} packets/J")
    print(f"   - 总能耗: {result['total_energy_consumed']:.3f}J")
    
    # 详细分析每轮
    print("\n🔍 轮次详细分析:")
    for i, round_stat in enumerate(protocol.round_stats):
        print(f"   轮{round_stat['round']}: "
              f"存活{round_stat['alive_nodes']}节点, "
              f"簇头{round_stat['cluster_heads']}个, "
              f"发送{round_stat['packets_sent']}包, "
              f"剩余能量{round_stat['remaining_energy']:.2f}J")

    # 检查簇结构
    print("\n🏗️ 簇结构分析:")
    print(f"   - 簇数量: {len(protocol.clusters)}")
    for cluster_id, cluster_info in protocol.clusters.items():
        head = cluster_info['head']
        members = cluster_info['members']
        print(f"   - 簇{cluster_id}: 簇头节点{head.id}, 成员{len(members)}个")
        if len(members) == 0:
            print(f"     ⚠️  簇{cluster_id}没有成员节点！")
        else:
            # 检查第一个成员的传输能耗 (修复参数顺序)
            member = members[0]
            distance = member.distance_to(head)
            tx_energy = protocol.energy_model.calculate_transmission_energy(config.packet_size * 8, distance)
            rx_energy = protocol.energy_model.calculate_reception_energy(config.packet_size * 8)
            print(f"     📡 成员{member.id}→簇头{head.id}: 距离{distance:.1f}m, "
                  f"发送能耗{tx_energy:.6f}J, 接收能耗{rx_energy:.6f}J")
            print(f"     🔋 成员能量{member.current_energy:.3f}J, 簇头能量{head.current_energy:.3f}J")
            if member.current_energy < tx_energy or head.current_energy < rx_energy:
                print(f"     ❌ 能量不足！无法传输")
    
    # 检查节点状态
    print("\n🔋 节点能量状态:")
    alive_nodes = [n for n in protocol.nodes if n.is_alive()]
    dead_nodes = [n for n in protocol.nodes if not n.is_alive()]
    
    print(f"   - 存活节点: {len(alive_nodes)}")
    print(f"   - 死亡节点: {len(dead_nodes)}")
    
    if alive_nodes:
        avg_energy = sum(n.current_energy for n in alive_nodes) / len(alive_nodes)
        print(f"   - 平均剩余能量: {avg_energy:.3f}J")
    
    if dead_nodes:
        print(f"   - 首个死亡节点: 第{min(n.death_round for n in dead_nodes if n.death_round)}轮")
    
    return result

if __name__ == "__main__":
    debug_baseline()
