#!/usr/bin/env python3
"""
深度分析TEEN和HEED协议的能耗问题
找出能效异常高的根本原因
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from teen_protocol import TEENProtocol, TEENConfig
from benchmark_protocols import HEEDProtocolWrapper, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def analyze_teen_energy_breakdown():
    """详细分析TEEN协议的能耗分解"""
    print("🔍 TEEN协议能耗分解分析...")
    
    # 创建小规模网络便于分析
    config = TEENConfig(
        num_nodes=5,
        area_width=100,
        area_height=100,
        base_station_x=50,
        base_station_y=175,
        initial_energy=2.0,
        hard_threshold=30.0,
        soft_threshold=0.1,
        max_time_interval=2
    )
    
    teen = TEENProtocol(config)
    node_positions = [(25, 25), (75, 25), (25, 75), (75, 75), (50, 50)]
    teen.initialize_network(node_positions)
    
    print(f"📊 初始状态:")
    print(f"   节点数: {len(teen.nodes)}")
    print(f"   初始总能量: {sum(n.current_energy for n in teen.nodes):.6f}J")
    
    # 手动计算一轮的理论能耗
    print(f"\n🧮 理论能耗计算:")
    
    # 假设每个节点都传输一次
    total_theoretical_energy = 0
    for i, node in enumerate(teen.nodes):
        # 计算到基站的距离
        distance_to_bs = ((node.x - config.base_station_x)**2 + (node.y - config.base_station_y)**2)**0.5
        
        # 计算传输能耗
        tx_energy = teen._calculate_transmission_energy(distance_to_bs, 1024)
        rx_energy = teen._calculate_reception_energy(1024)
        
        total_theoretical_energy += tx_energy + rx_energy
        
        print(f"   节点{i}: 距离={distance_to_bs:.1f}m, 传输={tx_energy:.9f}J, 接收={rx_energy:.9f}J")
    
    print(f"   理论总能耗: {total_theoretical_energy:.9f}J")
    
    # 运行实际仿真
    print(f"\n🚀 运行实际仿真...")
    result = teen.run_simulation(max_rounds=5)
    
    print(f"📊 实际仿真结果:")
    print(f"   实际总能耗: {result['total_energy_consumed']:.9f}J")
    print(f"   发送数据包: {result['packets_transmitted']}")
    print(f"   接收数据包: {result['packets_received']}")
    print(f"   能效: {result['energy_efficiency']:.2f} packets/J")
    
    # 对比分析
    if result['total_energy_consumed'] > 0:
        energy_ratio = total_theoretical_energy / result['total_energy_consumed']
        print(f"\n📈 能耗对比:")
        print(f"   理论/实际能耗比: {energy_ratio:.2f}x")
        
        if energy_ratio > 10:
            print("⚠️  实际能耗远低于理论值，可能存在计算错误")
        elif energy_ratio < 0.1:
            print("⚠️  实际能耗远高于理论值，可能存在重复计算")
        else:
            print("✅ 能耗计算在合理范围内")

def analyze_heed_energy_model():
    """分析HEED协议的能耗模型"""
    print("\n🔍 HEED协议能耗模型分析...")
    
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
    
    print(f"📊 HEED配置:")
    print(f"   节点数: {config.num_nodes}")
    print(f"   数据包大小: {config.packet_size} bits")
    print(f"   初始能量: {config.initial_energy}J/节点")
    
    # 计算理论最小能耗
    print(f"\n🧮 理论能耗计算:")
    
    # 假设平均距离50m，每轮每节点发送一个包
    avg_distance = 50.0
    tx_energy_per_packet = energy_model.calculate_transmission_energy(config.packet_size, avg_distance)
    rx_energy_per_packet = energy_model.calculate_reception_energy(config.packet_size)
    
    print(f"   平均传输能耗: {tx_energy_per_packet:.9f}J/packet")
    print(f"   平均接收能耗: {rx_energy_per_packet:.9f}J/packet")
    print(f"   总通信能耗: {(tx_energy_per_packet + rx_energy_per_packet):.9f}J/packet")
    
    # 运行短期仿真
    print(f"\n🚀 运行HEED仿真...")
    result = heed_wrapper.run_simulation(max_rounds=10)
    
    print(f"📊 HEED仿真结果:")
    print(f"   发送数据包: {result['packets_transmitted']}")
    print(f"   接收数据包: {result['packets_received']}")
    print(f"   总能耗: {result['total_energy_consumed']:.6f}J")
    print(f"   能效: {result['energy_efficiency']:.2f} packets/J")
    
    # 计算每包平均能耗
    if result['packets_received'] > 0:
        avg_energy_per_packet = result['total_energy_consumed'] / result['packets_received']
        theoretical_energy_per_packet = tx_energy_per_packet + rx_energy_per_packet
        
        print(f"\n📈 能耗对比:")
        print(f"   实际每包能耗: {avg_energy_per_packet:.9f}J")
        print(f"   理论每包能耗: {theoretical_energy_per_packet:.9f}J")
        print(f"   实际/理论比: {avg_energy_per_packet/theoretical_energy_per_packet:.2f}x")
        
        if avg_energy_per_packet < theoretical_energy_per_packet * 0.5:
            print("⚠️  HEED实际能耗过低，可能存在计算错误")
        elif avg_energy_per_packet > theoretical_energy_per_packet * 2:
            print("⚠️  HEED实际能耗过高，可能存在重复计算")
        else:
            print("✅ HEED能耗计算在合理范围内")

def compare_energy_models_detailed():
    """详细对比不同协议的能耗模型"""
    print("\n🔬 详细对比协议能耗模型...")
    
    # 测试条件
    distance = 50.0
    packet_size = 1024
    
    print(f"📏 测试条件: 距离={distance}m, 数据包={packet_size}bits")
    
    # TEEN协议能耗
    teen_config = TEENConfig()
    teen = TEENProtocol(teen_config)
    teen_tx = teen._calculate_transmission_energy(distance, packet_size)
    teen_rx = teen._calculate_reception_energy(packet_size)
    
    # 改进能耗模型
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    improved_tx = energy_model.calculate_transmission_energy(packet_size, distance)
    improved_rx = energy_model.calculate_reception_energy(packet_size)
    
    print(f"\n📊 能耗模型对比:")
    print(f"   TEEN传输: {teen_tx:.9f}J")
    print(f"   TEEN接收: {teen_rx:.9f}J")
    print(f"   TEEN总计: {teen_tx + teen_rx:.9f}J")
    print(f"")
    print(f"   改进传输: {improved_tx:.9f}J")
    print(f"   改进接收: {improved_rx:.9f}J")
    print(f"   改进总计: {improved_tx + improved_rx:.9f}J")
    
    # 计算比例
    tx_ratio = teen_tx / improved_tx if improved_tx > 0 else float('inf')
    rx_ratio = teen_rx / improved_rx if improved_rx > 0 else float('inf')
    total_ratio = (teen_tx + teen_rx) / (improved_tx + improved_rx)
    
    print(f"\n📈 能耗比例:")
    print(f"   传输比例: {tx_ratio:.2f}x")
    print(f"   接收比例: {rx_ratio:.2f}x")
    print(f"   总体比例: {total_ratio:.2f}x")
    
    if total_ratio < 0.5:
        print("⚠️  TEEN能耗模型过低，这解释了异常高的能效")
        return True
    else:
        print("✅ TEEN能耗模型在合理范围内")
        return False

def main():
    """主函数"""
    print("🚀 深度能耗分析开始")
    print("=" * 60)
    
    # 1. 分析TEEN协议能耗分解
    analyze_teen_energy_breakdown()
    
    # 2. 分析HEED协议能耗模型
    analyze_heed_energy_model()
    
    # 3. 详细对比能耗模型
    teen_energy_too_low = compare_energy_models_detailed()
    
    print(f"\n🎯 分析总结:")
    if teen_energy_too_low:
        print(f"   TEEN协议能耗模型需要修正到与改进模型一致")
    print(f"   HEED协议需要验证实现逻辑")
    print(f"   目标：所有协议能效在30-100 packets/J范围内")

if __name__ == "__main__":
    main()
