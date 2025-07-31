#!/usr/bin/env python3
"""
调试TEEN协议的实际能量消耗
检查节点能量是否真的被消耗
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from teen_protocol import TEENProtocol, TEENConfig

def debug_teen_energy_step_by_step():
    """逐步调试TEEN协议的能量消耗"""
    print("🔍 逐步调试TEEN协议能量消耗...")
    
    # 创建简单配置
    config = TEENConfig(
        num_nodes=3,  # 只用3个节点便于调试
        area_width=100,
        area_height=100,
        base_station_x=50,
        base_station_y=175,
        initial_energy=2.0,
        packet_size=1024,
        hard_threshold=30.0,
        soft_threshold=0.1,
        max_time_interval=2
    )
    
    teen = TEENProtocol(config)
    node_positions = [(25, 25), (75, 25), (50, 50)]
    teen.initialize_network(node_positions)
    
    print(f"📊 初始状态:")
    for i, node in enumerate(teen.nodes):
        print(f"   节点{i}: 位置=({node.x}, {node.y}), 能量={node.current_energy:.6f}J")
    
    initial_total_energy = sum(n.current_energy for n in teen.nodes)
    print(f"   初始总能量: {initial_total_energy:.6f}J")
    
    # 运行一轮并详细跟踪
    print(f"\n🔄 运行第1轮...")
    
    # 记录轮前状态
    energy_before = [n.current_energy for n in teen.nodes]
    
    # 运行一轮
    packets_sent = teen.run_round()
    
    # 记录轮后状态
    energy_after = [n.current_energy for n in teen.nodes]
    
    print(f"📊 第1轮结果:")
    print(f"   发送数据包: {packets_sent}")
    print(f"   协议统计能耗: {teen.total_energy_consumed:.9f}J")
    
    total_actual_consumption = 0
    for i, (before, after) in enumerate(zip(energy_before, energy_after)):
        consumption = before - after
        total_actual_consumption += consumption
        print(f"   节点{i}: {before:.6f}J -> {after:.6f}J (消耗: {consumption:.9f}J)")
    
    print(f"   实际总消耗: {total_actual_consumption:.9f}J")
    print(f"   统计/实际比: {teen.total_energy_consumed/total_actual_consumption:.2f}x" if total_actual_consumption > 0 else "N/A")
    
    # 继续运行几轮
    for round_num in range(2, 6):
        print(f"\n🔄 运行第{round_num}轮...")
        
        energy_before_round = sum(n.current_energy for n in teen.nodes)
        packets_sent = teen.run_round()
        energy_after_round = sum(n.current_energy for n in teen.nodes)
        
        round_consumption = energy_before_round - energy_after_round
        
        print(f"   发送数据包: {packets_sent}")
        print(f"   本轮实际消耗: {round_consumption:.9f}J")
        print(f"   累计协议统计: {teen.total_energy_consumed:.9f}J")
        print(f"   累计实际消耗: {initial_total_energy - energy_after_round:.9f}J")

def test_teen_energy_calculation_accuracy():
    """测试TEEN协议能耗计算的准确性"""
    print("\n🧪 测试TEEN协议能耗计算准确性...")
    
    config = TEENConfig(packet_size=1024)
    teen = TEENProtocol(config)
    
    # 测试不同距离的能耗计算
    distances = [10, 50, 100, 150]
    
    print(f"📊 不同距离的能耗计算:")
    for distance in distances:
        tx_energy = teen._calculate_transmission_energy(distance, 1024)
        rx_energy = teen._calculate_reception_energy(1024)
        total_energy = tx_energy + rx_energy
        
        print(f"   距离{distance}m: 传输={tx_energy:.9f}J, 接收={rx_energy:.9f}J, 总计={total_energy:.9f}J")
        
        # 检查能耗是否合理
        if total_energy > 1.0:  # 如果单次通信超过1J，明显不合理
            print(f"   ⚠️  距离{distance}m的能耗过高: {total_energy:.9f}J")
        elif total_energy < 1e-9:  # 如果单次通信低于1nJ，可能过低
            print(f"   ⚠️  距离{distance}m的能耗过低: {total_energy:.9f}J")

def compare_packet_sizes():
    """比较不同数据包大小对能效的影响"""
    print("\n📦 比较不同数据包大小的影响...")
    
    packet_sizes = [1024, 2048, 4000]  # TEEN默认, 中等, HEED默认
    
    for packet_size in packet_sizes:
        config = TEENConfig(
            num_nodes=5,
            packet_size=packet_size,
            hard_threshold=30.0,
            soft_threshold=0.1,
            max_time_interval=2
        )
        
        teen = TEENProtocol(config)
        node_positions = [(25, 25), (75, 25), (25, 75), (75, 75), (50, 50)]
        teen.initialize_network(node_positions)
        
        # 运行短期仿真
        result = teen.run_simulation(max_rounds=3)
        
        print(f"📊 数据包大小 {packet_size} bits:")
        print(f"   能效: {result['energy_efficiency']:.2f} packets/J")
        print(f"   总能耗: {result['total_energy_consumed']:.9f}J")
        print(f"   数据包数: {result['packets_received']}")
        
        if result['packets_received'] > 0:
            energy_per_packet = result['total_energy_consumed'] / result['packets_received']
            print(f"   每包能耗: {energy_per_packet:.9f}J")

def main():
    """主函数"""
    print("🚀 TEEN协议能量消耗调试")
    print("=" * 60)
    
    # 1. 逐步调试能量消耗
    debug_teen_energy_step_by_step()
    
    # 2. 测试能耗计算准确性
    test_teen_energy_calculation_accuracy()
    
    # 3. 比较数据包大小影响
    compare_packet_sizes()
    
    print(f"\n🎯 调试总结:")
    print(f"   如果协议统计与实际消耗差异巨大，说明统计逻辑有问题")
    print(f"   如果单次通信能耗异常，说明能耗模型有问题")
    print(f"   如果数据包大小影响巨大，说明需要统一测试条件")

if __name__ == "__main__":
    main()
