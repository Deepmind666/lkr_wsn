#!/usr/bin/env python3
"""
深度调试协议能耗计算
分析TEEN和HEED协议的异常能效问题
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from teen_protocol import TEENProtocol, TEENConfig
from benchmark_protocols import HEEDProtocolWrapper, TEENProtocolWrapper, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def debug_teen_energy_calculation():
    """调试TEEN协议能耗计算"""
    print("🔍 调试TEEN协议能耗计算...")
    
    # 创建简单的TEEN配置
    config = TEENConfig(
        num_nodes=10,  # 小网络便于调试
        area_width=100,
        area_height=100,
        base_station_x=50,
        base_station_y=175,
        initial_energy=2.0,
        transmission_range=30.0,
        packet_size=1024,
        hard_threshold=45.0,
        soft_threshold=0.5,
        max_time_interval=3,
        cluster_head_percentage=0.2  # 20%簇头
    )
    
    teen = TEENProtocol(config)
    
    # 手动创建节点位置
    node_positions = [
        (25, 25), (75, 25), (25, 75), (75, 75), (50, 50),
        (10, 10), (90, 10), (10, 90), (90, 90), (50, 25)
    ]
    teen.initialize_network(node_positions)
    
    print(f"📊 初始状态:")
    print(f"   节点数: {len(teen.nodes)}")
    print(f"   初始总能量: {sum(n.current_energy for n in teen.nodes):.6f}J")
    
    # 运行几轮并详细跟踪能耗
    for round_num in range(1, 6):
        print(f"\n🔄 轮次 {round_num}:")
        
        energy_before = sum(n.current_energy for n in teen.nodes)
        packets_before = teen.packets_transmitted
        
        teen.run_round()
        
        energy_after = sum(n.current_energy for n in teen.nodes)
        packets_after = teen.packets_transmitted
        
        energy_consumed_this_round = energy_before - energy_after
        packets_this_round = packets_after - packets_before
        
        print(f"   轮前能量: {energy_before:.6f}J")
        print(f"   轮后能量: {energy_after:.6f}J")
        print(f"   本轮能耗: {energy_consumed_this_round:.6f}J")
        print(f"   协议统计能耗: {teen.total_energy_consumed:.6f}J")
        print(f"   本轮数据包: {packets_this_round}")
        print(f"   能耗差异: {abs(energy_consumed_this_round - teen.total_energy_consumed):.6f}J")
        
        if packets_this_round > 0:
            round_efficiency = packets_this_round / energy_consumed_this_round if energy_consumed_this_round > 0 else float('inf')
            print(f"   本轮能效: {round_efficiency:.2f} packets/J")

def debug_heed_energy_calculation():
    """调试HEED协议能耗计算"""
    print("\n🔍 调试HEED协议能耗计算...")
    
    # 创建网络配置
    config = NetworkConfig(
        num_nodes=10,
        area_width=100,
        area_height=100,
        base_station_x=50,
        base_station_y=175,
        initial_energy=2.0,
        packet_size=4000
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    heed_wrapper = HEEDProtocolWrapper(config, energy_model)
    
    print(f"📊 HEED初始配置:")
    print(f"   节点数: {config.num_nodes}")
    print(f"   初始能量: {config.initial_energy}J/节点")
    print(f"   数据包大小: {config.packet_size} bits")
    
    # 运行短期仿真并跟踪
    result = heed_wrapper.run_simulation(max_rounds=10)
    
    print(f"\n📊 HEED 10轮仿真结果:")
    print(f"   发送数据包: {result['packets_transmitted']}")
    print(f"   接收数据包: {result['packets_received']}")
    print(f"   总能耗: {result['total_energy_consumed']:.6f}J")
    print(f"   能效: {result['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {result['packet_delivery_ratio']:.3f}")
    
    # 计算理论能耗
    theoretical_energy = config.num_nodes * config.initial_energy
    actual_remaining = theoretical_energy - result['total_energy_consumed']
    
    print(f"\n🧮 能耗验证:")
    print(f"   理论总能量: {theoretical_energy:.6f}J")
    print(f"   消耗能量: {result['total_energy_consumed']:.6f}J")
    print(f"   剩余能量: {actual_remaining:.6f}J")
    print(f"   能耗比例: {result['total_energy_consumed']/theoretical_energy*100:.1f}%")

def compare_energy_models():
    """比较不同协议的能耗模型"""
    print("\n🔬 比较不同协议的能耗模型...")
    
    # 测试相同距离和数据包大小的能耗
    distance = 50.0  # 50米
    packet_size = 1024  # 1024 bits
    
    print(f"📏 测试条件:")
    print(f"   距离: {distance}m")
    print(f"   数据包大小: {packet_size} bits")
    
    # TEEN协议能耗模型
    teen_config = TEENConfig()
    teen = TEENProtocol(teen_config)
    teen_tx_energy = teen._calculate_transmission_energy(distance, packet_size)
    teen_rx_energy = teen._calculate_reception_energy(packet_size)
    
    print(f"\n📡 TEEN协议能耗:")
    print(f"   传输能耗: {teen_tx_energy:.9f}J")
    print(f"   接收能耗: {teen_rx_energy:.9f}J")
    print(f"   总能耗: {teen_tx_energy + teen_rx_energy:.9f}J")
    
    # 改进的能耗模型
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    improved_tx_energy = energy_model.calculate_transmission_energy(packet_size, distance)
    improved_rx_energy = energy_model.calculate_reception_energy(packet_size)
    
    print(f"\n📡 改进能耗模型:")
    print(f"   传输能耗: {improved_tx_energy:.9f}J")
    print(f"   接收能耗: {improved_rx_energy:.9f}J")
    print(f"   总能耗: {improved_tx_energy + improved_rx_energy:.9f}J")
    
    # 计算差异
    tx_ratio = teen_tx_energy / improved_tx_energy if improved_tx_energy > 0 else float('inf')
    rx_ratio = teen_rx_energy / improved_rx_energy if improved_rx_energy > 0 else float('inf')
    
    print(f"\n📊 能耗模型对比:")
    print(f"   传输能耗比例: {tx_ratio:.2f}x")
    print(f"   接收能耗比例: {rx_ratio:.2f}x")
    
    if tx_ratio < 0.1 or rx_ratio < 0.1:
        print("⚠️  TEEN协议能耗模型可能过低！")
    elif tx_ratio > 10 or rx_ratio > 10:
        print("⚠️  TEEN协议能耗模型可能过高！")
    else:
        print("✅ 能耗模型在合理范围内")

def main():
    """主函数"""
    print("🚀 协议能耗计算深度调试")
    print("=" * 60)
    
    # 1. 调试TEEN协议能耗
    debug_teen_energy_calculation()
    
    # 2. 调试HEED协议能耗
    debug_heed_energy_calculation()
    
    # 3. 比较能耗模型
    compare_energy_models()
    
    print(f"\n🎯 调试总结:")
    print(f"   如果TEEN协议能耗过低，需要修复能耗模型")
    print(f"   如果HEED协议能效过高，需要检查实现逻辑")
    print(f"   目标：所有协议能效在合理范围内(30-100 packets/J)")

if __name__ == "__main__":
    main()
