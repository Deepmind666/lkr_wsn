#!/usr/bin/env python3
"""
分析TEEN协议为什么能耗异常低
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from teen_protocol import TEENProtocol, TEENConfig
from benchmark_protocols import NetworkConfig, TEENProtocolWrapper
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def analyze_teen_transmission_frequency():
    """分析TEEN协议的传输频率"""
    print("🔍 分析TEEN协议传输频率...")
    
    config = TEENConfig(
        num_nodes=10,
        hard_threshold=45.0,
        soft_threshold=0.5,
        max_time_interval=3
    )
    
    teen = TEENProtocol(config)
    node_positions = [(i*10, i*10) for i in range(10)]
    teen.initialize_network(node_positions)
    
    print(f"📊 运行10轮，统计传输情况:")
    
    total_possible_transmissions = 0
    total_actual_transmissions = 0
    
    for round_num in range(1, 11):
        # 统计本轮可能的传输次数
        possible_transmissions = len([n for n in teen.nodes if n.is_alive()])
        total_possible_transmissions += possible_transmissions
        
        # 运行一轮
        packets_sent = teen.run_round()
        if isinstance(packets_sent, bool):
            packets_sent = teen.packets_transmitted - total_actual_transmissions
        
        total_actual_transmissions = teen.packets_transmitted
        
        print(f"   轮{round_num}: 可能传输{possible_transmissions}, 实际传输{packets_sent}")
    
    transmission_rate = total_actual_transmissions / total_possible_transmissions if total_possible_transmissions > 0 else 0
    print(f"\n📈 传输统计:")
    print(f"   总可能传输: {total_possible_transmissions}")
    print(f"   总实际传输: {total_actual_transmissions}")
    print(f"   传输率: {transmission_rate:.1%}")
    
    if transmission_rate < 0.5:
        print("⚠️  TEEN协议传输率过低，这可能解释了低能耗")
    
    return transmission_rate

def compare_teen_with_standard_protocols():
    """对比TEEN与标准协议的能耗差异"""
    print("\n🔬 对比TEEN与标准协议...")
    
    # TEEN协议配置
    teen_config = TEENConfig(
        num_nodes=20,
        hard_threshold=45.0,
        soft_threshold=0.5,
        max_time_interval=3
    )
    
    teen = TEENProtocol(teen_config)
    node_positions = [(i*5, j*5) for i in range(4) for j in range(5)]
    teen.initialize_network(node_positions)
    
    # 运行TEEN协议
    teen_result = teen.run_simulation(max_rounds=50)
    
    print(f"📊 TEEN协议 (50轮):")
    print(f"   发送数据包: {teen_result['packets_transmitted']}")
    print(f"   接收数据包: {teen_result['packets_received']}")
    print(f"   总能耗: {teen_result['total_energy_consumed']:.6f}J")
    print(f"   能效: {teen_result['energy_efficiency']:.2f} packets/J")
    
    # 计算理论最小能耗
    print(f"\n🧮 理论能耗计算:")
    
    # 假设每轮每个节点都传输一次
    avg_distance = 50.0  # 假设平均距离
    tx_energy = teen._calculate_transmission_energy(avg_distance, 4000)
    rx_energy = teen._calculate_reception_energy(4000)
    per_transmission_energy = tx_energy + rx_energy
    
    theoretical_total_transmissions = 20 * 50  # 20节点 × 50轮
    theoretical_total_energy = theoretical_total_transmissions * per_transmission_energy
    
    print(f"   每次传输能耗: {per_transmission_energy:.9f}J")
    print(f"   理论总传输: {theoretical_total_transmissions}")
    print(f"   理论总能耗: {theoretical_total_energy:.6f}J")
    print(f"   理论能效: {theoretical_total_transmissions/theoretical_total_energy:.2f} packets/J")
    
    # 对比分析
    energy_ratio = teen_result['total_energy_consumed'] / theoretical_total_energy
    transmission_ratio = teen_result['packets_transmitted'] / theoretical_total_transmissions
    
    print(f"\n📈 对比分析:")
    print(f"   实际/理论能耗: {energy_ratio:.3f}x")
    print(f"   实际/理论传输: {transmission_ratio:.3f}x")
    
    if energy_ratio < 0.1:
        print("⚠️  TEEN实际能耗远低于理论值")
    if transmission_ratio < 0.5:
        print("⚠️  TEEN实际传输远少于理论值")

def analyze_teen_clustering_overhead():
    """分析TEEN协议的聚类开销"""
    print("\n🔧 分析TEEN协议聚类开销...")
    
    config = TEENConfig(num_nodes=10)
    teen = TEENProtocol(config)
    node_positions = [(i*10, i*10) for i in range(10)]
    teen.initialize_network(node_positions)
    
    # 手动运行聚类阶段
    print(f"📊 聚类阶段分析:")
    
    initial_energy = sum(n.current_energy for n in teen.nodes)
    print(f"   聚类前总能量: {initial_energy:.6f}J")
    
    # 运行聚类
    teen._form_clusters()
    
    after_clustering_energy = sum(n.current_energy for n in teen.nodes)
    clustering_energy = initial_energy - after_clustering_energy
    
    print(f"   聚类后总能量: {after_clustering_energy:.6f}J")
    print(f"   聚类能耗: {clustering_energy:.9f}J")
    print(f"   簇数量: {len(teen.clusters)}")
    
    if clustering_energy < 1e-6:
        print("⚠️  聚类能耗过低，可能没有正确计算聚类开销")

def main():
    """主函数"""
    print("🚀 分析TEEN协议低能耗原因")
    print("=" * 60)
    
    # 1. 分析传输频率
    transmission_rate = analyze_teen_transmission_frequency()
    
    # 2. 对比标准协议
    compare_teen_with_standard_protocols()
    
    # 3. 分析聚类开销
    analyze_teen_clustering_overhead()
    
    print(f"\n🎯 分析总结:")
    if transmission_rate < 0.3:
        print(f"   TEEN协议传输率过低({transmission_rate:.1%})，这是低能耗的主要原因")
        print(f"   建议：调整阈值参数或增加强制传输频率")
    else:
        print(f"   TEEN协议传输率正常({transmission_rate:.1%})")
        print(f"   低能耗可能由于其他原因，需要进一步调查")

if __name__ == "__main__":
    main()
