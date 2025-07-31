#!/usr/bin/env python3
"""
最终调试TEEN协议的能耗问题
对比节点实际能量消耗与协议统计
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from teen_protocol import TEENProtocol, TEENConfig
from benchmark_protocols import LEACHProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def compare_teen_vs_leach_energy():
    """对比TEEN和LEACH的实际能量消耗"""
    print("🔬 对比TEEN和LEACH的实际能量消耗...")
    
    # 相同的网络配置
    num_nodes = 20
    max_rounds = 50
    
    print(f"📊 测试配置: {num_nodes}节点, {max_rounds}轮")
    
    # 测试TEEN协议
    print(f"\n🔍 测试TEEN协议...")
    teen_config = TEENConfig(
        num_nodes=num_nodes,
        initial_energy=2.0,
        hard_threshold=45.0,
        soft_threshold=0.5,
        max_time_interval=3
    )
    
    teen = TEENProtocol(teen_config)
    node_positions = [(i*5, j*5) for i in range(4) for j in range(5)]
    teen.initialize_network(node_positions)
    
    # 记录初始能量
    teen_initial_energy = sum(n.current_energy for n in teen.nodes)
    print(f"   TEEN初始总能量: {teen_initial_energy:.6f}J")
    
    # 运行TEEN仿真
    teen_result = teen.run_simulation(max_rounds=max_rounds)
    
    # 记录最终能量
    teen_final_energy = sum(n.current_energy for n in teen.nodes)
    teen_actual_consumption = teen_initial_energy - teen_final_energy
    
    print(f"   TEEN最终总能量: {teen_final_energy:.6f}J")
    print(f"   TEEN实际消耗: {teen_actual_consumption:.6f}J")
    print(f"   TEEN协议统计: {teen_result['total_energy_consumed']:.6f}J")
    print(f"   TEEN数据包: {teen_result['packets_received']}")
    print(f"   TEEN能效: {teen_result['energy_efficiency']:.2f} packets/J")
    
    # 测试LEACH协议
    print(f"\n🔍 测试LEACH协议...")
    leach_config = NetworkConfig(
        num_nodes=num_nodes,
        initial_energy=2.0,
        packet_size=4000
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    leach = LEACHProtocol(leach_config, energy_model)
    
    # 记录初始能量
    leach_initial_energy = sum(n.current_energy for n in leach.nodes)
    print(f"   LEACH初始总能量: {leach_initial_energy:.6f}J")
    
    # 运行LEACH仿真
    leach_result = leach.run_simulation(max_rounds=max_rounds)
    
    # 记录最终能量
    leach_final_energy = sum(n.current_energy for n in leach.nodes)
    leach_actual_consumption = leach_initial_energy - leach_final_energy
    
    print(f"   LEACH最终总能量: {leach_final_energy:.6f}J")
    print(f"   LEACH实际消耗: {leach_actual_consumption:.6f}J")
    print(f"   LEACH协议统计: {leach_result['total_energy_consumed']:.6f}J")
    print(f"   LEACH数据包: {leach_result.get('packets_received', leach_result.get('total_packets_received', 0))}")
    print(f"   LEACH能效: {leach_result.get('energy_efficiency', 0):.2f} packets/J")
    
    # 对比分析
    print(f"\n📈 对比分析:")
    print(f"   TEEN vs LEACH 实际能耗比: {teen_actual_consumption/leach_actual_consumption:.3f}x")
    print(f"   TEEN vs LEACH 统计能耗比: {teen_result['total_energy_consumed']/leach_result['total_energy_consumed']:.3f}x")
    leach_packets = leach_result.get('packets_received', leach_result.get('total_packets_received', 1))
    leach_efficiency = leach_result.get('energy_efficiency', 1)
    print(f"   TEEN vs LEACH 数据包比: {teen_result['packets_received']/leach_packets:.3f}x")
    print(f"   TEEN vs LEACH 能效比: {teen_result['energy_efficiency']/leach_efficiency:.3f}x")
    
    # 检查统计一致性
    teen_stat_error = abs(teen_actual_consumption - teen_result['total_energy_consumed']) / teen_actual_consumption
    leach_stat_error = abs(leach_actual_consumption - leach_result['total_energy_consumed']) / leach_actual_consumption
    
    print(f"\n🎯 统计一致性检查:")
    print(f"   TEEN统计误差: {teen_stat_error:.1%}")
    print(f"   LEACH统计误差: {leach_stat_error:.1%}")
    
    if teen_stat_error > 0.1:
        print("⚠️  TEEN协议统计误差过大")
    if leach_stat_error > 0.1:
        print("⚠️  LEACH协议统计误差过大")
    
    # 分析TEEN能效异常的原因
    if teen_result['energy_efficiency'] > leach_efficiency * 5:
        print(f"\n🚨 TEEN能效异常分析:")
        print(f"   TEEN能效是LEACH的{teen_result['energy_efficiency']/leach_efficiency:.1f}倍")

        if teen_actual_consumption < leach_actual_consumption * 0.2:
            print("   原因：TEEN实际能耗过低")
        elif teen_result['packets_received'] > leach_packets * 2:
            print("   原因：TEEN数据包数量过多")
        else:
            print("   原因：未知，需要进一步调查")

def analyze_teen_per_packet_energy():
    """分析TEEN协议的每包能耗"""
    print("\n🔬 分析TEEN协议每包能耗...")
    
    config = TEENConfig(num_nodes=10, initial_energy=2.0)
    teen = TEENProtocol(config)
    node_positions = [(i*10, i*10) for i in range(10)]
    teen.initialize_network(node_positions)
    
    # 运行短期仿真
    result = teen.run_simulation(max_rounds=20)
    
    if result['packets_received'] > 0:
        energy_per_packet = result['total_energy_consumed'] / result['packets_received']
        print(f"   TEEN每包能耗: {energy_per_packet:.9f}J")
        
        # 对比理论值
        avg_distance = 50.0
        theoretical_energy = teen._calculate_transmission_energy(avg_distance, 4000) + teen._calculate_reception_energy(4000)
        print(f"   理论每包能耗: {theoretical_energy:.9f}J")
        print(f"   实际/理论比: {energy_per_packet/theoretical_energy:.3f}x")
        
        if energy_per_packet < theoretical_energy * 0.5:
            print("⚠️  TEEN实际每包能耗过低")

def main():
    """主函数"""
    print("🚀 TEEN协议最终调试")
    print("=" * 60)
    
    # 1. 对比TEEN和LEACH的能量消耗
    compare_teen_vs_leach_energy()
    
    # 2. 分析TEEN每包能耗
    analyze_teen_per_packet_energy()
    
    print(f"\n🎯 调试结论:")
    print(f"   如果TEEN统计误差小但能效异常高，说明TEEN协议确实更节能")
    print(f"   如果TEEN统计误差大，说明能耗计算有问题")
    print(f"   如果TEEN每包能耗过低，说明能耗模型有问题")

if __name__ == "__main__":
    main()
