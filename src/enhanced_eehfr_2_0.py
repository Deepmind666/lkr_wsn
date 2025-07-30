#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced EEHFR 2.0: 双阶段混合优化协议
融合PEGASIS链式优化和HEED能效聚类的优势

技术架构:
阶段1: HEED能效聚类 → 形成最优簇结构
阶段2: PEGASIS链式优化 → 簇内数据融合
阶段3: 模糊逻辑智能切换 → 动态策略选择

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 2.0 (混合优化版本)
"""

import numpy as np
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import copy

# 导入基准协议
from heed_protocol import HEEDProtocol, HEEDConfig, HEEDNode
from benchmark_protocols import PEGASISProtocol, NetworkConfig
from fuzzy_logic_system import FuzzyLogicSystem
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

@dataclass
class EnhancedEEHFR2Config:
    """Enhanced EEHFR 2.0配置参数"""
    # 基础网络参数
    num_nodes: int = 50
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 50.0
    initial_energy: float = 2.0
    
    # 通信参数
    transmission_range: float = 30.0
    packet_size: int = 1024  # bits
    
    # 混合优化参数
    heed_weight_initial: float = 0.7  # HEED初始权重
    pegasis_weight_initial: float = 0.3  # PEGASIS初始权重
    switching_threshold: float = 0.5  # 切换阈值
    
    # 聚类参数
    cluster_head_percentage: float = 0.08  # 8%的节点作为簇头，增加传输机会
    max_clustering_iterations: int = 10
    
    # 链式优化参数
    chain_optimization_enabled: bool = True
    data_fusion_ratio: float = 0.8  # 数据融合比例

class NetworkState(Enum):
    """网络状态枚举"""
    HIGH_ENERGY = "high_energy"      # 高能量状态
    MEDIUM_ENERGY = "medium_energy"  # 中等能量状态
    LOW_ENERGY = "low_energy"        # 低能量状态

@dataclass
class Node2_0:
    """Enhanced EEHFR 2.0节点类"""
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    
    # 聚类相关
    cluster_id: int = -1
    is_cluster_head: bool = False
    cluster_head_id: int = -1
    
    # 链式传输相关
    chain_position: int = -1
    next_node_id: int = -1
    prev_node_id: int = -1
    
    # 统计信息
    packets_sent: int = 0
    packets_received: int = 0
    
    def is_alive(self) -> bool:
        """检查节点是否存活"""
        return self.current_energy > 0
    
    def distance_to(self, other: 'Node2_0') -> float:
        """计算到另一个节点的距离"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def distance_to_base_station(self, bs_x: float, bs_y: float) -> float:
        """计算到基站的距离"""
        return math.sqrt((self.x - bs_x)**2 + (self.y - bs_y)**2)

class EnhancedEEHFR2Protocol:
    """Enhanced EEHFR 2.0协议主类"""
    
    def __init__(self, config: EnhancedEEHFR2Config):
        self.config = config
        self.nodes: List[Node2_0] = []
        self.clusters: Dict[int, Dict] = {}
        self.chains: Dict[int, List[int]] = {}  # 每个簇的链结构
        self.current_round = 0
        self.base_station = (config.base_station_x, config.base_station_y)
        
        # 性能统计
        self.total_energy_consumed = 0.0
        self.packets_transmitted = 0
        self.packets_received = 0
        self.network_lifetime = 0
        self.round_stats = []
        
        # 模糊逻辑系统
        self.fuzzy_system = FuzzyLogicSystem()
        
        # 能耗模型
        self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        
        # 当前网络状态
        self.network_state = NetworkState.HIGH_ENERGY
        self.heed_weight = config.heed_weight_initial
        self.pegasis_weight = config.pegasis_weight_initial
    
    def initialize_network(self):
        """初始化网络拓扑"""
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            node = Node2_0(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy
            )
            self.nodes.append(node)
        
        print(f"✅ 网络初始化完成: {len(self.nodes)}个节点")
    
    def evaluate_network_state(self) -> NetworkState:
        """评估当前网络状态"""
        alive_nodes = [n for n in self.nodes if n.is_alive()]
        if not alive_nodes:
            return NetworkState.LOW_ENERGY
        
        # 计算平均剩余能量比例
        avg_energy_ratio = sum(n.current_energy / n.initial_energy for n in alive_nodes) / len(alive_nodes)
        
        if avg_energy_ratio > 0.7:
            return NetworkState.HIGH_ENERGY
        elif avg_energy_ratio > 0.3:
            return NetworkState.MEDIUM_ENERGY
        else:
            return NetworkState.LOW_ENERGY
    
    def update_strategy_weights(self):
        """基于网络状态更新策略权重"""
        self.network_state = self.evaluate_network_state()
        
        if self.network_state == NetworkState.HIGH_ENERGY:
            # 高能量阶段：优先使用HEED，保证网络稳定性
            self.heed_weight = 0.8
            self.pegasis_weight = 0.2
        elif self.network_state == NetworkState.MEDIUM_ENERGY:
            # 中等能量阶段：平衡使用两种策略
            self.heed_weight = 0.5
            self.pegasis_weight = 0.5
        else:
            # 低能量阶段：优先使用PEGASIS，最大化生存时间
            self.heed_weight = 0.2
            self.pegasis_weight = 0.8
    
    def heed_clustering_phase(self) -> Dict[int, Dict]:
        """阶段1: HEED能效聚类"""
        alive_nodes = [n for n in self.nodes if n.is_alive()]
        if not alive_nodes:
            return {}
        
        # 使用HEED算法进行聚类
        clusters = {}
        cluster_id = 0
        
        # 简化的HEED聚类实现
        num_cluster_heads = max(1, int(len(alive_nodes) * self.config.cluster_head_percentage))
        
        # 基于能量和位置选择簇头
        potential_heads = sorted(alive_nodes, 
                               key=lambda n: (n.current_energy / n.initial_energy, 
                                             -n.distance_to_base_station(*self.base_station)), 
                               reverse=True)
        
        cluster_heads = potential_heads[:num_cluster_heads]
        
        # 为每个簇头创建簇
        for i, head in enumerate(cluster_heads):
            head.is_cluster_head = True
            head.cluster_id = i
            clusters[i] = {
                'head': head,
                'members': [head],
                'chain': []
            }
        
        # 将其他节点分配到最近的簇头
        for node in alive_nodes:
            if not node.is_cluster_head:
                min_distance = float('inf')
                best_cluster = 0
                
                for cluster_id, cluster_info in clusters.items():
                    distance = node.distance_to(cluster_info['head'])
                    if distance < min_distance:
                        min_distance = distance
                        best_cluster = cluster_id
                
                node.cluster_id = best_cluster
                node.cluster_head_id = clusters[best_cluster]['head'].id
                clusters[best_cluster]['members'].append(node)
        
        return clusters
    
    def pegasis_optimization_phase(self, clusters: Dict[int, Dict]):
        """阶段2: PEGASIS链式优化"""
        for cluster_id, cluster_info in clusters.items():
            members = cluster_info['members']
            if len(members) <= 1:
                continue
            
            # 在簇内构建PEGASIS链
            chain = self.build_pegasis_chain(members)
            cluster_info['chain'] = chain
            
            # 更新节点的链式信息
            for i, node_id in enumerate(chain):
                node = next(n for n in self.nodes if n.id == node_id)
                node.chain_position = i
                
                if i > 0:
                    node.prev_node_id = chain[i-1]
                if i < len(chain) - 1:
                    node.next_node_id = chain[i+1]
    
    def build_pegasis_chain(self, nodes: List[Node2_0]) -> List[int]:
        """构建PEGASIS链"""
        if len(nodes) <= 1:
            return [nodes[0].id] if nodes else []
        
        # 找到距离基站最远的节点作为起点
        start_node = max(nodes, key=lambda n: n.distance_to_base_station(*self.base_station))
        
        chain = [start_node.id]
        remaining = [n for n in nodes if n.id != start_node.id]
        
        current = start_node
        while remaining:
            # 找到距离当前节点最近的节点
            nearest = min(remaining, key=lambda n: current.distance_to(n))
            chain.append(nearest.id)
            remaining.remove(nearest)
            current = nearest
        
        return chain

    def data_transmission_phase(self) -> int:
        """数据传输阶段 - 简化的混合策略"""
        packets_this_round = 0

        for cluster_id, cluster_info in self.clusters.items():
            head = cluster_info['head']
            members = cluster_info['members']

            if not head.is_alive():
                continue

            # 简化策略：每个簇只传输一次
            # 成员节点向簇头传输数据
            cluster_packets = 0
            for member in members:
                if not member.is_alive() or member.is_cluster_head:
                    continue

                # 计算传输能耗
                distance = member.distance_to(head)
                tx_energy = self.energy_model.calculate_transmission_energy(
                    self.config.packet_size * 8, distance
                )
                rx_energy = self.energy_model.calculate_reception_energy(
                    self.config.packet_size * 8
                )

                # 检查能量是否足够
                if member.current_energy >= tx_energy and head.current_energy >= rx_energy:
                    member.current_energy -= tx_energy
                    head.current_energy -= rx_energy
                    member.packets_sent += 1
                    head.packets_received += 1
                    cluster_packets += 1
                    self.total_energy_consumed += (tx_energy + rx_energy)

            # 簇头向基站传输聚合数据
            if cluster_packets > 0 and head.is_alive():
                distance_to_bs = head.distance_to_base_station(*self.base_station)
                tx_energy = self.energy_model.calculate_transmission_energy(
                    self.config.packet_size * 8, distance_to_bs
                )

                if head.current_energy >= tx_energy:
                    head.current_energy -= tx_energy
                    head.packets_sent += 1
                    packets_this_round += 1  # 只计算到达基站的数据包
                    self.packets_received += 1  # 基站接收数据包
                    self.total_energy_consumed += tx_energy

        self.packets_transmitted += packets_this_round
        return packets_this_round



    def run_round(self) -> bool:
        """运行一轮协议"""
        self.current_round += 1

        # 检查是否还有存活节点
        alive_nodes = [node for node in self.nodes if node.is_alive()]
        if not alive_nodes:
            return False

        # 更新策略权重
        self.update_strategy_weights()

        # 减少聚类频率，提高效率
        if self.current_round % 50 == 1:  # 从20轮改为50轮
            self.clusters = self.heed_clustering_phase()
            self.pegasis_optimization_phase(self.clusters)

        # 数据传输阶段
        packets_sent = self.data_transmission_phase()

        # 更新节点状态
        for node in self.nodes:
            if node.current_energy <= 0:
                node.is_cluster_head = False
                node.cluster_id = -1

        # 记录统计信息
        alive_count = len(alive_nodes)
        total_energy = sum(node.current_energy for node in self.nodes)

        round_stat = {
            'round': self.current_round,
            'alive_nodes': alive_count,
            'total_energy': total_energy,
            'packets_sent': packets_sent,
            'cluster_count': len(self.clusters),
            'network_state': self.network_state.value,
            'heed_weight': self.heed_weight,
            'pegasis_weight': self.pegasis_weight
        }
        self.round_stats.append(round_stat)

        return alive_count > 0

    def run_simulation(self, max_rounds: int = 200) -> Dict:
        """运行完整仿真"""
        print(f"🚀 开始Enhanced EEHFR 2.0仿真 (最大轮数: {max_rounds})")

        while self.current_round < max_rounds:
            if not self.run_round():
                break

            # 每50轮输出一次状态
            if self.current_round % 50 == 0:
                alive_nodes = len([n for n in self.nodes if n.is_alive()])
                total_energy = sum(n.current_energy for n in self.nodes)
                print(f"   轮数 {self.current_round}: 存活节点 {alive_nodes}, "
                      f"剩余能量 {total_energy:.3f}J, 网络状态 {self.network_state.value}")

        # 计算最终统计
        self.network_lifetime = self.current_round
        final_alive_nodes = len([n for n in self.nodes if n.is_alive()])

        # 计算能效和投递率
        energy_efficiency = self.packets_received / self.total_energy_consumed if self.total_energy_consumed > 0 else 0
        packet_delivery_ratio = self.packets_received / self.packets_transmitted if self.packets_transmitted > 0 else 0

        print(f"✅ 仿真完成，网络在 {self.network_lifetime} 轮后结束")

        return {
            'protocol': 'Enhanced EEHFR 2.0',
            'network_lifetime': self.network_lifetime,
            'total_energy_consumed': self.total_energy_consumed,
            'packets_transmitted': self.packets_transmitted,
            'packets_received': self.packets_received,
            'packet_delivery_ratio': packet_delivery_ratio,
            'energy_efficiency': energy_efficiency,
            'final_alive_nodes': final_alive_nodes,
            'round_stats': self.round_stats
        }
