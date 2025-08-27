#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HEED (Hybrid Energy-Efficient Distributed clustering) 协议实现
基于能量和通信代价的分布式分簇协议，用作EEHFR协议的对比基准

参考文献:
Younis, O., & Fahmy, S. (2004). 
HEED: a hybrid, energy-efficient, distributed clustering approach for ad hoc sensor networks. 
IEEE Transactions on mobile computing, 3(4), 366-379.

项目路径: EEHFR：融合模糊逻辑与混合元启发式优化的WSN智能节能路由协议/EEHFR_Optimized_v1/
数据源: Intel Berkeley Research Lab数据集 (https://db.csail.mit.edu/labdata/labdata.html)
"""

import numpy as np
import math
import random
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt

class HEEDNode:
    """HEED协议中的传感器节点"""
    
    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True
        self.is_cluster_head = False
        self.cluster_head_id = None
        self.cluster_members = []
        
        # HEED特定参数
        self.ch_probability = 0.0
        self.communication_cost = 0.0
        self.neighbors = []
        self.cluster_radius = 50.0  # 簇半径
        
    def distance_to(self, other_node) -> float:
        """计算到另一个节点的欧几里得距离"""
        return math.sqrt((self.x - other_node.x)**2 + (self.y - other_node.y)**2)
    
    def consume_energy(self, energy_amount: float):
        """消耗能量"""
        self.current_energy -= energy_amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False
    
    def reset_cluster_info(self):
        """重置簇信息"""
        self.is_cluster_head = False
        self.cluster_head_id = None
        self.cluster_members = []
        self.ch_probability = 0.0
        self.communication_cost = 0.0

class HEEDProtocol:
    """HEED协议实现"""
    
    def __init__(self, nodes: List[HEEDNode], base_station: Tuple[float, float], 
                 c_prob: float = 0.05, cluster_radius: float = 50.0):
        """
        初始化HEED协议
        
        参数:
            nodes: 传感器节点列表
            base_station: 基站坐标 (x, y)
            c_prob: 初始簇头概率参数
            cluster_radius: 簇半径
        """
        self.nodes = nodes
        self.base_station = base_station
        self.c_prob = c_prob
        self.cluster_radius = cluster_radius
        self.current_round = 0
        
        # 能量消耗模型参数
        self.E_elec = 50e-9  # 电子能耗 (J/bit)
        self.E_fs = 10e-12   # 自由空间模型 (J/bit/m²)
        self.E_mp = 0.0013e-12  # 多径衰落模型 (J/bit/m⁴)
        self.E_DA = 5e-9     # 数据聚合能耗 (J/bit/signal)
        self.d_crossover = 87  # 距离阈值 (m)
        self.packet_size = 4000  # 数据包大小 (bits)
        
        # 性能统计
        self.total_energy_consumed = 0.0
        self.packets_sent = 0
        self.packets_received = 0
        # 端到端统计（统一为源→BS口径）
        self.total_source_packets = 0
        self.total_bs_delivered = 0
        self.dead_nodes = 0
        self.network_lifetime = 0
        self.energy_consumption_per_round = []
        self.alive_nodes_per_round = []

        # 初始化邻居关系
        self.initialize_neighbors()
        
        print(f"🔧 HEED协议初始化完成")
        print(f"   节点数: {len(self.nodes)}")
        print(f"   基站位置: {self.base_station}")
        print(f"   簇半径: {self.cluster_radius}m")
        print(f"   初始簇头概率: {self.c_prob}")
    
    def initialize_neighbors(self):
        """初始化节点邻居关系"""
        for node in self.nodes:
            node.neighbors = []
            for other_node in self.nodes:
                if node.node_id != other_node.node_id:
                    distance = node.distance_to(other_node)
                    if distance <= self.cluster_radius:
                        node.neighbors.append(other_node)
    
    def calculate_transmission_energy(self, distance: float, packet_size: int) -> float:
        """计算传输能耗"""
        if distance < self.d_crossover:
            return self.E_elec * packet_size + self.E_fs * packet_size * (distance ** 2)
        else:
            return self.E_elec * packet_size + self.E_mp * packet_size * (distance ** 4)
    
    def calculate_reception_energy(self, packet_size: int) -> float:
        """计算接收能耗"""
        return self.E_elec * packet_size
    
    def calculate_communication_cost(self, node: HEEDNode) -> float:
        """计算节点的通信代价"""
        if not node.neighbors:
            return float('inf')
        
        # 计算到所有邻居的平均距离
        total_distance = 0.0
        alive_neighbors = [n for n in node.neighbors if n.is_alive]
        
        if not alive_neighbors:
            return float('inf')
        
        for neighbor in alive_neighbors:
            total_distance += node.distance_to(neighbor)
        
        return total_distance / len(alive_neighbors)
    
    def calculate_ch_probability(self, node: HEEDNode) -> float:
        """计算节点成为簇头的概率"""
        if node.current_energy <= 0:
            return 0.0
        
        # 基于剩余能量的概率
        energy_ratio = node.current_energy / node.initial_energy
        return self.c_prob * energy_ratio
    
    def cluster_head_selection(self) -> List[HEEDNode]:
        """HEED簇头选择算法"""
        cluster_heads = []
        
        # 重置所有节点状态
        for node in self.nodes:
            node.reset_cluster_info()
        
        # 计算每个节点的簇头概率和通信代价
        for node in self.nodes:
            if not node.is_alive:
                continue
            
            node.ch_probability = self.calculate_ch_probability(node)
            node.communication_cost = self.calculate_communication_cost(node)
        
        # 多轮迭代选择簇头
        max_iterations = 5
        for iteration in range(max_iterations):
            new_cluster_heads = []
            
            for node in self.nodes:
                if not node.is_alive or node.cluster_head_id is not None:
                    continue
                
                # 检查是否应该成为簇头
                should_be_ch = False
                
                if iteration == 0:
                    # 第一轮：基于概率随机选择
                    if random.random() < node.ch_probability:
                        should_be_ch = True
                else:
                    # 后续轮次：基于通信代价选择
                    # 如果没有更好的簇头候选，则自己成为簇头
                    better_candidates = []
                    for neighbor in node.neighbors:
                        if (neighbor.is_alive and 
                            neighbor.ch_probability > node.ch_probability and
                            neighbor.communication_cost < node.communication_cost):
                            better_candidates.append(neighbor)
                    
                    if not better_candidates:
                        should_be_ch = True
                
                if should_be_ch:
                    node.is_cluster_head = True
                    new_cluster_heads.append(node)
            
            cluster_heads.extend(new_cluster_heads)
            
            # 为新簇头分配成员
            for ch in new_cluster_heads:
                for neighbor in ch.neighbors:
                    if (neighbor.is_alive and 
                        not neighbor.is_cluster_head and 
                        neighbor.cluster_head_id is None):
                        neighbor.cluster_head_id = ch.node_id
                        ch.cluster_members.append(neighbor)
        
        # 确保所有节点都有簇头
        for node in self.nodes:
            if (node.is_alive and 
                not node.is_cluster_head and 
                node.cluster_head_id is None):
                # 寻找最近的簇头
                min_distance = float('inf')
                closest_ch = None
                
                for ch in cluster_heads:
                    distance = node.distance_to(ch)
                    if distance < min_distance:
                        min_distance = distance
                        closest_ch = ch
                
                if closest_ch:
                    node.cluster_head_id = closest_ch.node_id
                    closest_ch.cluster_members.append(node)
                else:
                    # 如果没有簇头，自己成为簇头
                    node.is_cluster_head = True
                    cluster_heads.append(node)
        
        return cluster_heads
    
    def data_transmission_phase(self, cluster_heads: List[HEEDNode]):
        """数据传输阶段"""
        round_energy_consumption = 0.0
        
        # 1. 簇内数据传输
        for ch in cluster_heads:
            if not ch.is_alive:
                continue
            
            # 成员节点向簇头发送数据
            for member in ch.cluster_members:
                if not member.is_alive:
                    continue
                
                distance = member.distance_to(ch)
                tx_energy = self.calculate_transmission_energy(distance, self.packet_size)
                rx_energy = self.calculate_reception_energy(self.packet_size)
                
                # 成员节点消耗传输能量
                member.consume_energy(tx_energy)
                round_energy_consumption += tx_energy
                
                # 簇头消耗接收能量
                ch.consume_energy(rx_energy)
                round_energy_consumption += rx_energy
                
                self.packets_sent += 1
                if ch.is_alive:
                    self.packets_received += 1
        
        # 2. 簇头向基站传输聚合数据
        for ch in cluster_heads:
            if not ch.is_alive:
                continue

            # 数据聚合能耗
            aggregation_energy = self.E_DA * self.packet_size * len(ch.cluster_members)
            ch.consume_energy(aggregation_energy)
            round_energy_consumption += aggregation_energy

            # 向基站传输
            bs_distance = math.sqrt((ch.x - self.base_station[0])**2 +
                                  (ch.y - self.base_station[1])**2)
            tx_energy = self.calculate_transmission_energy(bs_distance, self.packet_size)
            ch.consume_energy(tx_energy)
            round_energy_consumption += tx_energy

            self.packets_sent += 1
            # 统一端到端口径：聚合成功则按簇成员数+CH自身计一次端到端送达
            delivered = 1 + len([m for m in ch.cluster_members if m.is_alive])
            self.total_bs_delivered += delivered
            # 源包总数累加（本轮所有簇域内成员 + CH 自身）
            self.total_source_packets += delivered

        self.total_energy_consumed += round_energy_consumption
        self.energy_consumption_per_round.append(round_energy_consumption)
    
    def run_round(self) -> bool:
        """运行一轮HEED协议"""
        # 检查网络是否还有存活节点
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return False
        
        self.current_round += 1
        
        # 1. 簇头选择阶段
        cluster_heads = self.cluster_head_selection()
        
        # 2. 数据传输阶段
        self.data_transmission_phase(cluster_heads)
        
        # 3. 更新统计信息
        current_alive = len(alive_nodes)
        current_dead = len(self.nodes) - current_alive
        
        if current_dead > self.dead_nodes:
            self.dead_nodes = current_dead
            if self.network_lifetime == 0 and current_dead > 0:
                self.network_lifetime = self.current_round
        
        self.alive_nodes_per_round.append(current_alive)
        
        return True
    
    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """运行完整的HEED仿真"""
        print(f"🚀 开始HEED协议仿真 (最大轮数: {max_rounds})")
        
        for round_num in range(max_rounds):
            success = self.run_round()
            
            if not success:
                print(f"⚠️ 网络生命周期结束于第 {round_num} 轮")
                break
            
            # 每100轮输出一次状态
            if round_num % 100 == 0:
                alive_count = len([n for n in self.nodes if n.is_alive])
                print(f"   第{round_num}轮: 存活节点={alive_count}, "
                      f"总能耗={self.total_energy_consumed:.3f}J")
        
        # 返回性能结果
        results = {
            'protocol_name': 'HEED',
            'total_rounds': self.current_round,
            'network_lifetime': self.network_lifetime if self.network_lifetime > 0 else self.current_round,
            'total_energy_consumed': self.total_energy_consumed,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'packet_delivery_ratio': self.packets_received / max(self.packets_sent, 1),
                'packet_delivery_ratio_end2end': self.total_bs_delivered / max(self.total_source_packets, 1),
                'bs_delivered': self.total_bs_delivered,
                'source_packets': self.total_source_packets,
            'dead_nodes': self.dead_nodes,
            'alive_nodes': len(self.nodes) - self.dead_nodes,
            'energy_consumption_per_round': self.energy_consumption_per_round,
            'alive_nodes_per_round': self.alive_nodes_per_round,
            'average_energy_per_round': self.total_energy_consumed / max(self.current_round, 1)
        }
        
        print(f"✅ HEED仿真完成")
        print(f"   网络生存时间: {results['network_lifetime']} 轮")
        print(f"   总能耗: {results['total_energy_consumed']:.3f} J")
        print(f"   数据传输成功率: {results['packet_delivery_ratio']*100:.1f}%")
        
        return results
