#!/usr/bin/env python3
"""
第一性原理验证脚本
验证Enhanced EEHFR 2.0 vs PEGASIS的能效和投递率差异的本质原因
"""

import math
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple
import json

class FirstPrinciplesAnalyzer:
    """第一性原理分析器"""
    
    def __init__(self):
        # 网络参数
        self.num_nodes = 50
        self.area_size = 100  # 100m x 100m
        self.base_station = (50, 50)
        self.initial_energy = 2.0  # J
        
        # 能耗参数 (CC2420)
        self.E_circuit = 50e-9  # 50 nJ/bit
        self.E_amp = 100e-12    # 100 pJ/bit/m²
        self.packet_size = 1024 * 8  # 1024 bytes = 8192 bits
        
        # 协议参数
        self.cluster_head_percentage = 0.15  # 15%簇头比例
        self.pegasis_success_rate = 0.98
        self.enhanced_success_rate = 0.95
        
    def generate_random_topology(self, seed: int = 42) -> List[Tuple[float, float]]:
        """生成随机网络拓扑"""
        np.random.seed(seed)
        nodes = []
        for _ in range(self.num_nodes):
            x = np.random.uniform(0, self.area_size)
            y = np.random.uniform(0, self.area_size)
            nodes.append((x, y))
        return nodes
    
    def calculate_distance(self, node1: Tuple[float, float], node2: Tuple[float, float]) -> float:
        """计算两点间距离"""
        return math.sqrt((node1[0] - node2[0])**2 + (node1[1] - node2[1])**2)
    
    def calculate_transmission_energy(self, distance: float) -> float:
        """计算传输能耗"""
        return self.E_circuit * self.packet_size + self.E_amp * self.packet_size * (distance ** 2)
    
    def analyze_pegasis_energy(self, nodes: List[Tuple[float, float]]) -> dict:
        """分析PEGASIS协议的能耗特征"""
        # 构建PEGASIS链
        remaining = nodes.copy()
        
        # 找到距离基站最远的节点作为起点
        start_node = max(remaining, key=lambda n: self.calculate_distance(n, self.base_station))
        chain = [start_node]
        remaining.remove(start_node)
        
        # 贪心构建链
        current = start_node
        while remaining:
            nearest = min(remaining, key=lambda n: self.calculate_distance(current, n))
            chain.append(nearest)
            remaining.remove(nearest)
            current = nearest
        
        # 计算链式传输能耗
        total_energy = 0.0
        transmission_distances = []
        
        # 链内传输
        for i in range(len(chain) - 1):
            distance = self.calculate_distance(chain[i], chain[i + 1])
            energy = self.calculate_transmission_energy(distance)
            total_energy += energy
            transmission_distances.append(distance)
        
        # 领导者到基站传输
        leader_index = len(chain) // 2
        leader = chain[leader_index]
        bs_distance = self.calculate_distance(leader, self.base_station)
        bs_energy = self.calculate_transmission_energy(bs_distance)
        total_energy += bs_energy
        
        return {
            'total_energy': total_energy,
            'chain_length': len(chain),
            'transmission_count': len(chain),  # 包括到基站的传输
            'avg_chain_distance': np.mean(transmission_distances),
            'max_chain_distance': max(transmission_distances),
            'bs_distance': bs_distance,
            'bs_energy': bs_energy,
            'chain_energy': total_energy - bs_energy,
            'expected_packets_received': self.num_nodes * self.pegasis_success_rate
        }
    
    def analyze_enhanced_eehfr_energy(self, nodes: List[Tuple[float, float]]) -> dict:
        """分析Enhanced EEHFR 2.0协议的能耗特征"""
        # 计算每个节点的簇头概率
        node_probabilities = []
        for node in nodes:
            # 能量因子 (假设所有节点初始能量相同)
            energy_factor = 1.0
            
            # 位置因子
            distance_to_bs = self.calculate_distance(node, self.base_station)
            max_distance = math.sqrt(2) * self.area_size
            position_factor = 1.0 - (distance_to_bs / max_distance)
            
            # 中心性因子
            avg_distance = np.mean([self.calculate_distance(node, other) for other in nodes if other != node])
            max_avg_distance = max_distance / 2
            centrality_factor = 1.0 - (avg_distance / max_avg_distance)
            
            # 综合概率
            probability = 0.4 * energy_factor + 0.3 * position_factor + 0.3 * centrality_factor
            node_probabilities.append((node, probability, distance_to_bs))
        
        # 选择簇头
        num_cluster_heads = max(1, int(self.num_nodes * self.cluster_head_percentage))
        sorted_nodes = sorted(node_probabilities, key=lambda x: x[1], reverse=True)
        cluster_heads = sorted_nodes[:num_cluster_heads]
        
        # 计算簇内传输能耗
        total_energy = 0.0
        intra_cluster_distances = []
        inter_cluster_distances = []
        
        # 为每个非簇头节点分配到最近的簇头
        non_cluster_heads = [node for node, _, _ in sorted_nodes[num_cluster_heads:]]
        
        for member in non_cluster_heads:
            # 找到最近的簇头
            nearest_head = min(cluster_heads, key=lambda ch: self.calculate_distance(member, ch[0]))
            distance = self.calculate_distance(member, nearest_head[0])
            energy = self.calculate_transmission_energy(distance)
            total_energy += energy
            intra_cluster_distances.append(distance)
        
        # 簇头到基站传输
        for head, _, bs_distance in cluster_heads:
            energy = self.calculate_transmission_energy(bs_distance)
            total_energy += energy
            inter_cluster_distances.append(bs_distance)
        
        return {
            'total_energy': total_energy,
            'num_cluster_heads': num_cluster_heads,
            'transmission_count': len(non_cluster_heads) + num_cluster_heads,
            'bs_transmission_count': num_cluster_heads,
            'avg_intra_distance': np.mean(intra_cluster_distances) if intra_cluster_distances else 0,
            'avg_inter_distance': np.mean(inter_cluster_distances),
            'max_inter_distance': max(inter_cluster_distances),
            'min_inter_distance': min(inter_cluster_distances),
            'intra_cluster_energy': total_energy - sum(self.calculate_transmission_energy(d) for d in inter_cluster_distances),
            'inter_cluster_energy': sum(self.calculate_transmission_energy(d) for d in inter_cluster_distances),
            'expected_packets_received': num_cluster_heads * self.enhanced_success_rate
        }
    
    def run_comparative_analysis(self) -> dict:
        """运行对比分析"""
        print("🔬 开始第一性原理验证分析...")
        
        # 生成网络拓扑
        nodes = self.generate_random_topology()
        
        # 分析PEGASIS
        print("📊 分析PEGASIS协议...")
        pegasis_results = self.analyze_pegasis_energy(nodes)
        
        # 分析Enhanced EEHFR 2.0
        print("📊 分析Enhanced EEHFR 2.0协议...")
        enhanced_results = self.analyze_enhanced_eehfr_energy(nodes)
        
        # 计算性能指标
        pegasis_efficiency = self.num_nodes / pegasis_results['total_energy']
        enhanced_efficiency = self.num_nodes / enhanced_results['total_energy']
        
        pegasis_pdr = pegasis_results['expected_packets_received'] / self.num_nodes
        enhanced_pdr = enhanced_results['expected_packets_received'] / self.num_nodes
        
        # 计算提升幅度
        efficiency_improvement = (enhanced_efficiency - pegasis_efficiency) / pegasis_efficiency * 100
        pdr_change = (enhanced_pdr - pegasis_pdr) / pegasis_pdr * 100
        
        results = {
            'pegasis': pegasis_results,
            'enhanced': enhanced_results,
            'comparison': {
                'pegasis_efficiency': pegasis_efficiency,
                'enhanced_efficiency': enhanced_efficiency,
                'efficiency_improvement_percent': efficiency_improvement,
                'pegasis_pdr': pegasis_pdr,
                'enhanced_pdr': enhanced_pdr,
                'pdr_change_percent': pdr_change
            }
        }
        
        return results
    
    def print_analysis_results(self, results: dict):
        """打印分析结果"""
        print("\n" + "="*80)
        print("🎯 第一性原理验证结果")
        print("="*80)
        
        pegasis = results['pegasis']
        enhanced = results['enhanced']
        comp = results['comparison']
        
        print(f"\n📊 PEGASIS协议分析:")
        print(f"   总能耗: {pegasis['total_energy']:.6f} J")
        print(f"   传输次数: {pegasis['transmission_count']}")
        print(f"   平均链距离: {pegasis['avg_chain_distance']:.2f} m")
        print(f"   基站距离: {pegasis['bs_distance']:.2f} m")
        print(f"   能效: {comp['pegasis_efficiency']:.2f} packets/J")
        print(f"   投递率: {comp['pegasis_pdr']:.3f}")
        
        print(f"\n📊 Enhanced EEHFR 2.0协议分析:")
        print(f"   总能耗: {enhanced['total_energy']:.6f} J")
        print(f"   簇头数量: {enhanced['num_cluster_heads']}")
        print(f"   基站传输次数: {enhanced['bs_transmission_count']}")
        print(f"   平均簇内距离: {enhanced['avg_intra_distance']:.2f} m")
        print(f"   平均簇间距离: {enhanced['avg_inter_distance']:.2f} m")
        print(f"   能效: {comp['enhanced_efficiency']:.2f} packets/J")
        print(f"   投递率: {comp['enhanced_pdr']:.3f}")
        
        print(f"\n🎯 性能对比:")
        print(f"   能效提升: {comp['efficiency_improvement_percent']:+.2f}%")
        print(f"   投递率变化: {comp['pdr_change_percent']:+.2f}%")
        
        print(f"\n🔍 本质原因分析:")
        print(f"   传输次数对比: {pegasis['transmission_count']} vs {enhanced['bs_transmission_count']} (到基站)")
        print(f"   能耗分布: PEGASIS链式传输 vs Enhanced两阶段传输")
        print(f"   距离优化: Enhanced平均簇间距离 {enhanced['avg_inter_distance']:.1f}m")
        
        # 验证与实际实验结果的一致性
        print(f"\n✅ 与实际实验结果对比:")
        print(f"   理论能效提升: {comp['efficiency_improvement_percent']:+.2f}% vs 实际: +5.54%")
        print(f"   理论投递率变化: {comp['pdr_change_percent']:+.2f}% vs 实际: -3.95%")

def main():
    """主函数"""
    analyzer = FirstPrinciplesAnalyzer()
    results = analyzer.run_comparative_analysis()
    analyzer.print_analysis_results(results)
    
    # 保存结果
    with open('first_principles_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 详细结果已保存到: first_principles_analysis_results.json")

if __name__ == "__main__":
    main()
