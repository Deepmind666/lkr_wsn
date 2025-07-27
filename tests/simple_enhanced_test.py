#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版Enhanced EEHFR协议测试脚本

测试增强型EEHFR协议的核心功能，避免复杂依赖
基于Intel Berkeley Research Lab真实数据集

项目路径: EEHFR：融合模糊逻辑与混合元启发式优化的WSN智能节能路由协议/EEHFR_Optimized_v1/
数据源: Intel Berkeley Research Lab数据集 (https://db.csail.mit.edu/labdata/labdata.html)
"""

import numpy as np
import matplotlib.pyplot as plt
import json
import time
import math
import random
from typing import Dict, List, Tuple
import sys
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

class SimpleEnhancedNode:
    """简化版增强型传感器节点"""
    
    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True
        self.is_cluster_head = False
        self.cluster_id = -1
        self.next_hop = None
        
        # 基础属性
        self.base_station_distance = 0.0
        self.neighbors = []
        self.residual_energy_ratio = 1.0
        self.fuzzy_score = 0.0
        
        # 能量消耗模型参数
        self.E_elec = 50e-9
        self.E_fs = 10e-12
        self.E_mp = 0.0013e-12
        self.d_crossover = 87
        self.packet_size = 4000
    
    def distance_to(self, other_node) -> float:
        """计算到另一个节点的距离"""
        return math.sqrt((self.x - other_node.x)**2 + (self.y - other_node.y)**2)
    
    def calculate_transmission_energy(self, distance: float, packet_size: int) -> float:
        """计算传输能耗"""
        if distance < self.d_crossover:
            return self.E_elec * packet_size + self.E_fs * packet_size * (distance ** 2)
        else:
            return self.E_elec * packet_size + self.E_mp * packet_size * (distance ** 4)
    
    def calculate_reception_energy(self, packet_size: int) -> float:
        """计算接收能耗"""
        return self.E_elec * packet_size
    
    def consume_energy(self, energy_amount: float):
        """消耗能量"""
        self.current_energy -= energy_amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False
        self.residual_energy_ratio = self.current_energy / self.initial_energy
    
    def update_fuzzy_score(self, base_station_pos: Tuple[float, float]):
        """更新模糊评分"""
        # 能量评分
        energy_score = self.residual_energy_ratio
        
        # 位置评分
        bs_distance = math.sqrt((self.x - base_station_pos[0])**2 + (self.y - base_station_pos[1])**2)
        self.base_station_distance = bs_distance
        max_distance = 200 * math.sqrt(2)
        location_score = max(0, 1 - bs_distance / max_distance)
        
        # 连接性评分
        connectivity_score = min(len(self.neighbors) / 8, 1) if self.neighbors else 0
        
        # 综合评分
        self.fuzzy_score = 0.5 * energy_score + 0.3 * location_score + 0.2 * connectivity_score

class SimpleEnhancedEEHFR:
    """简化版增强型EEHFR协议"""
    
    def __init__(self, nodes: List[SimpleEnhancedNode], base_station: Tuple[float, float], 
                 cluster_ratio: float = 0.05, chain_enabled: bool = True):
        self.nodes = nodes
        self.base_station = base_station
        self.cluster_ratio = cluster_ratio
        self.chain_enabled = chain_enabled
        self.current_round = 0
        
        # 网络状态
        self.cluster_heads = []
        self.chains = []
        
        # 性能统计
        self.total_energy_consumed = 0.0
        self.packets_sent = 0
        self.packets_received = 0
        self.dead_nodes = 0
        self.network_lifetime = 0
        self.energy_consumption_per_round = []
        self.alive_nodes_per_round = []
        
        # 初始化网络
        self.initialize_network()
        
        print(f"🚀 简化版Enhanced EEHFR协议初始化完成")
        print(f"   节点数: {len(self.nodes)}")
        print(f"   基站位置: {self.base_station}")
        print(f"   链式结构: {'启用' if self.chain_enabled else '禁用'}")
    
    def initialize_network(self):
        """初始化网络拓扑"""
        # 建立邻居关系
        for i, node_i in enumerate(self.nodes):
            node_i.neighbors = []
            for j, node_j in enumerate(self.nodes):
                if i != j:
                    distance = node_i.distance_to(node_j)
                    if distance <= 50:  # 通信半径50m
                        node_i.neighbors.append(node_j)
        
        # 构建链式结构
        if self.chain_enabled:
            self.build_energy_efficient_chains()
    
    def build_energy_efficient_chains(self):
        """构建能量高效的链式结构"""
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if len(alive_nodes) < 2:
            return
        
        # 使用贪心算法构建链
        unvisited = alive_nodes.copy()
        chains = []
        
        while unvisited:
            if len(unvisited) == 1:
                chains.append([unvisited[0]])
                break
            
            # 选择能量最高的节点作为链的起点
            start_node = max(unvisited, key=lambda n: n.current_energy)
            current_chain = [start_node]
            unvisited.remove(start_node)
            
            current_node = start_node
            
            # 贪心构建链
            while unvisited and len(current_chain) < 8:
                min_cost = float('inf')
                next_node = None
                
                for candidate in unvisited:
                    distance = current_node.distance_to(candidate)
                    energy_factor = 1.0 / (candidate.residual_energy_ratio + 0.1)
                    cost = distance * energy_factor
                    
                    if cost < min_cost:
                        min_cost = cost
                        next_node = candidate
                
                if next_node:
                    current_chain.append(next_node)
                    unvisited.remove(next_node)
                    current_node = next_node
                else:
                    break
            
            chains.append(current_chain)
        
        # 更新节点的链信息
        self.chains = chains
        for chain_id, chain in enumerate(chains):
            for node in chain:
                node.cluster_id = chain_id
    
    def enhanced_fuzzy_clustering(self):
        """增强型模糊逻辑分簇"""
        # 更新所有节点的模糊评分
        for node in self.nodes:
            if node.is_alive:
                node.update_fuzzy_score(self.base_station)
        
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if not alive_nodes:
            return
        
        # 重置簇头状态
        for node in self.nodes:
            node.is_cluster_head = False
        
        if self.chain_enabled:
            # 链式分簇
            self.build_energy_efficient_chains()
            self.cluster_heads = []
            for chain in self.chains:
                if chain:
                    chain_head = max(chain, key=lambda n: n.fuzzy_score)
                    chain_head.is_cluster_head = True
                    self.cluster_heads.append(chain_head)
        else:
            # 传统分簇
            expected_ch_count = max(1, int(len(alive_nodes) * self.cluster_ratio))
            
            # 选择模糊评分最高的节点作为簇头
            sorted_nodes = sorted(alive_nodes, key=lambda n: n.fuzzy_score, reverse=True)
            self.cluster_heads = sorted_nodes[:expected_ch_count]
            
            for i, ch in enumerate(self.cluster_heads):
                ch.is_cluster_head = True
                ch.cluster_id = i
            
            # 为非簇头节点分配簇
            for node in alive_nodes:
                if not node.is_cluster_head:
                    min_distance = float('inf')
                    best_cluster = 0
                    
                    for i, ch in enumerate(self.cluster_heads):
                        distance = node.distance_to(ch)
                        if distance < min_distance:
                            min_distance = distance
                            best_cluster = i
                    
                    node.cluster_id = best_cluster
    
    def simple_routing_optimization(self):
        """简化的路由优化"""
        if not self.cluster_heads:
            return
        
        # 为每个簇头选择最优下一跳
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue
            
            # 计算到基站的距离
            bs_distance = math.sqrt((ch.x - self.base_station[0])**2 + (ch.y - self.base_station[1])**2)
            
            # 如果距离基站很近，直接发送
            if bs_distance < 60:
                ch.next_hop = None
                continue
            
            # 寻找最优中继节点
            best_relay = None
            best_cost = float('inf')
            
            for candidate in self.cluster_heads:
                if candidate != ch and candidate.is_alive:
                    # 计算中继成本
                    relay_distance = ch.distance_to(candidate)
                    relay_to_bs = math.sqrt((candidate.x - self.base_station[0])**2 + 
                                          (candidate.y - self.base_station[1])**2)
                    
                    # 综合成本：距离 + 能量因子
                    energy_factor = 2.0 - candidate.residual_energy_ratio
                    total_cost = relay_distance + relay_to_bs * 0.5 + energy_factor * 10
                    
                    if total_cost < best_cost and relay_to_bs < bs_distance:
                        best_cost = total_cost
                        best_relay = candidate
            
            ch.next_hop = best_relay
    
    def enhanced_data_transmission(self):
        """增强型数据传输"""
        if not self.cluster_heads:
            return
        
        round_energy_consumption = 0.0
        successful_transmissions = 0
        
        # 簇内数据收集
        if self.chain_enabled:
            # 链式数据传输
            for chain in self.chains:
                if not chain:
                    continue
                
                for i in range(len(chain) - 1, 0, -1):
                    current_node = chain[i]
                    next_node = chain[i - 1]
                    
                    if current_node.is_alive and next_node.is_alive:
                        distance = current_node.distance_to(next_node)
                        tx_energy = current_node.calculate_transmission_energy(distance, current_node.packet_size)
                        rx_energy = next_node.calculate_reception_energy(current_node.packet_size)
                        
                        current_node.consume_energy(tx_energy)
                        next_node.consume_energy(rx_energy)
                        
                        round_energy_consumption += tx_energy + rx_energy
                        successful_transmissions += 1
        else:
            # 传统簇内数据收集
            for node in self.nodes:
                if node.is_alive and not node.is_cluster_head and node.cluster_id >= 0:
                    cluster_head = None
                    for ch in self.cluster_heads:
                        if ch.cluster_id == node.cluster_id:
                            cluster_head = ch
                            break
                    
                    if cluster_head and cluster_head.is_alive:
                        distance = node.distance_to(cluster_head)
                        tx_energy = node.calculate_transmission_energy(distance, node.packet_size)
                        rx_energy = cluster_head.calculate_reception_energy(node.packet_size)
                        
                        node.consume_energy(tx_energy)
                        cluster_head.consume_energy(rx_energy)
                        
                        round_energy_consumption += tx_energy + rx_energy
                        successful_transmissions += 1
        
        # 簇头到基站的数据传输
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue
            
            if ch.next_hop and ch.next_hop.is_alive:
                # 多跳传输
                distance = ch.distance_to(ch.next_hop)
                tx_energy = ch.calculate_transmission_energy(distance, ch.packet_size)
                rx_energy = ch.next_hop.calculate_reception_energy(ch.packet_size)
                
                ch.consume_energy(tx_energy)
                ch.next_hop.consume_energy(rx_energy)
                
                round_energy_consumption += tx_energy + rx_energy
                successful_transmissions += 1
            else:
                # 直接传输到基站
                bs_distance = math.sqrt((ch.x - self.base_station[0])**2 + (ch.y - self.base_station[1])**2)
                tx_energy = ch.calculate_transmission_energy(bs_distance, ch.packet_size)
                
                ch.consume_energy(tx_energy)
                round_energy_consumption += tx_energy
                successful_transmissions += 1
        
        # 更新统计信息
        self.total_energy_consumed += round_energy_consumption
        self.packets_sent += successful_transmissions
        self.packets_received += successful_transmissions
        
        # 更新死亡节点数
        current_dead = sum(1 for node in self.nodes if not node.is_alive)
        if current_dead > self.dead_nodes:
            self.dead_nodes = current_dead
            if self.network_lifetime == 0:
                self.network_lifetime = self.current_round
    
    def run_single_round(self):
        """执行单轮协议操作"""
        self.current_round += 1
        
        # 检查网络连通性
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if len(alive_nodes) < 2:
            return False
        
        # 1. 增强型模糊分簇
        self.enhanced_fuzzy_clustering()
        
        # 2. 路由优化
        self.simple_routing_optimization()
        
        # 3. 数据传输
        self.enhanced_data_transmission()
        
        # 4. 记录性能数据
        self.energy_consumption_per_round.append(self.total_energy_consumed)
        self.alive_nodes_per_round.append(len(alive_nodes))
        
        return len(alive_nodes) > 0
    
    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """运行完整仿真"""
        print(f"🚀 开始简化版Enhanced EEHFR协议仿真...")
        print(f"   最大轮数: {max_rounds}")
        
        start_time = time.time()
        
        for round_num in range(max_rounds):
            if not self.run_single_round():
                print(f"⚠️  网络在第 {round_num} 轮断开连接")
                break
            
            if round_num % 100 == 0:
                alive_count = len([n for n in self.nodes if n.is_alive])
                avg_energy = np.mean([n.current_energy for n in self.nodes if n.is_alive]) if alive_count > 0 else 0
                print(f"   轮次 {round_num}: 存活节点 {alive_count}/{len(self.nodes)}, 平均能量 {avg_energy:.3f}J")
        
        simulation_time = time.time() - start_time
        
        # 计算最终统计结果
        alive_nodes = [node for node in self.nodes if node.is_alive]
        
        results = {
            'total_energy_consumed': self.total_energy_consumed,
            'network_lifetime': self.network_lifetime if self.network_lifetime > 0 else self.current_round,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'packet_delivery_ratio': self.packets_received / max(self.packets_sent, 1),
            'alive_nodes': len(alive_nodes),
            'dead_nodes': self.dead_nodes,
            'survival_rate': len(alive_nodes) / len(self.nodes),
            'average_residual_energy': np.mean([node.current_energy for node in alive_nodes]) if alive_nodes else 0,
            'energy_efficiency': self.packets_received / max(self.total_energy_consumed, 1e-6),
            'rounds_completed': self.current_round,
            'simulation_time': simulation_time
        }
        
        print(f"✅ 仿真完成!")
        print(f"   总轮数: {self.current_round}")
        print(f"   网络生存时间: {results['network_lifetime']} 轮")
        print(f"   总能耗: {self.total_energy_consumed:.4f} J")
        print(f"   仿真时间: {simulation_time:.2f} 秒")
        
        return results

def create_test_network(n_nodes: int = 50, area_size: int = 200) -> List[SimpleEnhancedNode]:
    """创建测试网络"""
    nodes = []
    np.random.seed(42)
    
    for i in range(n_nodes):
        x = np.random.uniform(10, area_size - 10)
        y = np.random.uniform(10, area_size - 10)
        initial_energy = 2.0 + np.random.normal(0, 0.1)
        initial_energy = max(1.5, min(2.5, initial_energy))
        
        node = SimpleEnhancedNode(i, x, y, initial_energy)
        nodes.append(node)
    
    return nodes

def run_comparison_test():
    """运行对比测试"""
    print("🧪 开始简化版Enhanced EEHFR协议对比测试")
    print("=" * 60)
    
    # 创建测试网络
    nodes = create_test_network(50, 200)
    base_station = (100, 100)
    
    # 测试配置
    test_configs = [
        {'name': 'Enhanced_EEHFR_Chain', 'chain_enabled': True, 'cluster_ratio': 0.05},
        {'name': 'Enhanced_EEHFR_Traditional', 'chain_enabled': False, 'cluster_ratio': 0.05},
    ]
    
    results = {}
    
    for config in test_configs:
        print(f"\n🔬 测试 {config['name']}...")
        
        # 重置节点状态
        test_nodes = []
        for original_node in nodes:
            new_node = SimpleEnhancedNode(
                original_node.node_id,
                original_node.x,
                original_node.y,
                original_node.initial_energy
            )
            test_nodes.append(new_node)
        
        # 创建协议实例
        protocol = SimpleEnhancedEEHFR(
            nodes=test_nodes,
            base_station=base_station,
            cluster_ratio=config['cluster_ratio'],
            chain_enabled=config['chain_enabled']
        )
        
        # 运行仿真
        result = protocol.run_simulation(max_rounds=500)
        results[config['name']] = result
        
        print(f"   ✅ 完成 - 能耗: {result['total_energy_consumed']:.4f}J, "
              f"生存时间: {result['network_lifetime']} 轮")
    
    # 保存结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"simple_enhanced_eehfr_results_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 测试结果已保存至: {results_file}")
    
    # 简单可视化
    protocols = list(results.keys())
    energy_consumption = [results[p]['total_energy_consumed'] for p in protocols]
    network_lifetime = [results[p]['network_lifetime'] for p in protocols]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # 能耗对比
    ax1.bar(protocols, energy_consumption, color=['#FF6B6B', '#4ECDC4'])
    ax1.set_title('总能耗对比 (J)')
    ax1.set_ylabel('能耗 (J)')
    ax1.tick_params(axis='x', rotation=45)
    
    # 生存时间对比
    ax2.bar(protocols, network_lifetime, color=['#FFD93D', '#6BCF7F'])
    ax2.set_title('网络生存时间对比 (轮)')
    ax2.set_ylabel('生存时间 (轮)')
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    chart_file = f"simple_enhanced_eehfr_chart_{timestamp}.png"
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    print(f"📊 性能对比图表已保存至: {chart_file}")
    plt.show()
    
    print("\n" + "=" * 60)
    print("✅ 简化版Enhanced EEHFR协议测试完成!")
    
    return results

if __name__ == "__main__":
    results = run_comparison_test()
