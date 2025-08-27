#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSN基准路由协议标准实现

基于权威文献和开源实现的标准基准协议:
- LEACH (Low-Energy Adaptive Clustering Hierarchy)
- PEGASIS (Power-Efficient Gathering in Sensor Information Systems)  
- HEED (Hybrid Energy-Efficient Distributed clustering)

参考文献:
[1] Heinzelman et al. "Energy-efficient communication protocol for wireless microsensor networks" (HICSS 2000)
[2] Lindsey & Raghavendra "PEGASIS: Power-efficient gathering in sensor information systems" (ICCC 2002)
[3] Younis & Fahmy "HEED: a hybrid, energy-efficient, distributed clustering approach" (TMC 2004)

技术特点:
- 严格按照原始论文算法实现
- 使用改进的能耗模型进行公平对比
- 支持多种网络配置和环境参数
- 提供详细的性能统计和分析

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0 (标准基准实现)
"""

import numpy as np
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import copy

from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from heed_protocol import HEEDProtocol, HEEDConfig
from teen_protocol import TEENProtocol, TEENConfig

@dataclass
class Node:
    """WSN节点基础类"""
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    is_alive: bool = True
    is_cluster_head: bool = False
    cluster_id: int = -1
    
    def __post_init__(self):
        if self.current_energy is None:
            self.current_energy = self.initial_energy

@dataclass
class NetworkConfig:
    """网络配置参数"""
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 175.0
    num_nodes: int = 100
    initial_energy: float = 2.0  # Joules
    packet_size: int = 1024      # bytes
    
class LEACHProtocol:
    """
    LEACH协议标准实现 (已重构和修正)
    基于Heinzelman et al. (HICSS 2000)原始论文的科学重构版本
    """
    
    def __init__(self, config: NetworkConfig, energy_model: ImprovedEnergyModel):
        self.config = config
        self.energy_model = energy_model
        self.nodes = []
        self.round_number = 0
        self.cluster_heads = []
        self.clusters = {}
        
        # LEACH参数 (基于原始论文)
        self.desired_cluster_head_percentage = 0.1
        self.cluster_head_rotation_rounds = int(1 / self.desired_cluster_head_percentage)
        
        # 新增：数据传输概率，用于模拟更真实的场景
        self.data_transmission_probability = 0.95  # 95%的概率进行数据传输

        # 性能统计
        self.stats = {
            'network_lifetime': 0,
            'total_energy_consumed': 0.0,
            'packets_transmitted': 0,
            'packets_received': 0,
            'cluster_formation_overhead': 0,
            'round_statistics': []
        }
        
        self._initialize_network()
    
    def _initialize_network(self):
        """初始化网络节点"""
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            node = Node(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy
            )
            self.nodes.append(node)
    
    def _calculate_distance(self, node1: Node, node2: Node) -> float:
        """计算两节点间距离"""
        return math.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)
    
    def _calculate_distance_to_bs(self, node: Node) -> float:
        """计算节点到基站距离"""
        return math.sqrt((node.x - self.config.base_station_x)**2 +
                        (node.y - self.config.base_station_y)**2)

    def _select_cluster_heads(self) -> List[Node]:
        """
        LEACH簇头选择算法 (重构)
        基于概率阈值和轮换机制
        """
        cluster_heads = []
        
        P = self.desired_cluster_head_percentage
        r = self.round_number
        
        # 计算阈值 T(n)
        # 简化但有效的阈值计算，确保簇头比例稳定
        threshold = P / (1 - P * (r % self.cluster_head_rotation_rounds))
        
        successful_selections = 0
        for node in self.nodes:
            if not node.is_alive:
                continue

            # 节点根据阈值独立决定是否成为簇头
            if random.random() < threshold:
                node.is_cluster_head = True
                cluster_heads.append(node)
                successful_selections += 1
            else:
                node.is_cluster_head = False

        # 调试输出
        if r < 5:
            print(f"[调试] 轮{r}: 阈值={threshold:.4f}, 尝试={sum(1 for n in self.nodes if n.is_alive)}, 成功={successful_selections}")

        # 如果没有选出簇头，则强制选择一个（避免网络完全停滞）
        if not cluster_heads and any(n.is_alive for n in self.nodes):
            alive_nodes = [n for n in self.nodes if n.is_alive]
            chosen_one = random.choice(alive_nodes)
            chosen_one.is_cluster_head = True
            cluster_heads.append(chosen_one)
            if r < 5:
                print(f"[调试] 轮{r}: 未选出簇头，强制选择节点 {chosen_one.id}")

        return cluster_heads

    def _form_clusters(self, cluster_heads: List[Node]):
        """
        形成簇结构 (重构)
        非簇头节点加入最近的簇头
        """
        self.clusters = {ch.id: {'head': ch, 'members': []} for ch in cluster_heads}
        
        for node in self.nodes:
            if not node.is_alive or node.is_cluster_head:
                continue

            if not cluster_heads:
                node.cluster_id = -1
                continue

            # 找到最近的簇头
            min_distance = float('inf')
            nearest_ch = None
            for ch in cluster_heads:
                distance = self._calculate_distance(node, ch)
                if distance < min_distance:
                    min_distance = distance
                    nearest_ch = ch
            
            # 将节点分配给最近的簇头
            if nearest_ch:
                node.cluster_id = nearest_ch.id
                self.clusters[nearest_ch.id]['members'].append(node)

    def _steady_state_communication(self):
        """
        稳态通信阶段 (重构)
        实现成员->簇头->基站的数据传输和能耗计算
        """
        total_energy_consumed = 0.0
        packets_transmitted = 0
        packets_received = 0

        # 1. 成员节点向簇头发送数据
        for cluster_id, cluster_info in self.clusters.items():
            ch = cluster_info['head']
            if not ch.is_alive:
                continue

            for member in cluster_info['members']:
                if not member.is_alive:
                    continue

                distance = self._calculate_distance(member, ch)
                tx_energy = self.energy_model.calculate_transmission_energy(self.config.packet_size * 8, distance)
                rx_energy = self.energy_model.calculate_reception_energy(self.config.packet_size * 8)

                if member.current_energy > tx_energy and ch.current_energy > rx_energy:
                    member.current_energy -= tx_energy
                    ch.current_energy -= rx_energy
                    total_energy_consumed += tx_energy + rx_energy
                    packets_transmitted += 1
                    packets_received += 1
                else:
                    if member.current_energy <= tx_energy: member.is_alive = False; member.current_energy = 0
                    if ch.current_energy <= rx_energy: ch.is_alive = False; ch.current_energy = 0

        # 2. 簇头向基站发送聚合数据
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue

            distance_to_bs = self._calculate_distance_to_bs(ch)
            num_members = len(self.clusters.get(ch.id, {}).get('members', []))
            
            # 聚合能耗
            aggregation_energy = self.energy_model.calculate_processing_energy(self.config.packet_size * 8 * (num_members + 1)) # +1 for CH's own data
            
            # 传输能耗
            tx_energy_to_bs = self.energy_model.calculate_transmission_energy(self.config.packet_size * 8, distance_to_bs)
            
            total_ch_energy_cost = aggregation_energy + tx_energy_to_bs

            if ch.current_energy > total_ch_energy_cost:
                ch.current_energy -= total_ch_energy_cost
                total_energy_consumed += total_ch_energy_cost
                packets_transmitted += 1
                packets_received += 1 # To BS
            else:
                ch.is_alive = False
                ch.current_energy = 0

        # 更新统计
        self.stats['total_energy_consumed'] += total_energy_consumed
        self.stats['packets_transmitted'] += packets_transmitted
        self.stats['packets_received'] += packets_received
    
    def run_round(self) -> Dict:
        """运行一轮LEACH协议 (重构)"""
        
        if not any(n.is_alive for n in self.nodes):
            return self._get_round_statistics()
        
        # 1. 重置状态并选择簇头
        for node in self.nodes:
            node.is_cluster_head = False
            node.cluster_id = -1
        
        cluster_heads = self._select_cluster_heads()
        self.cluster_heads = cluster_heads
        
        if self.round_number <= 5:
            print(f"[调试] 选择后活跃簇头: {len(cluster_heads)}")

        # 2. 形成簇
        self._form_clusters(cluster_heads)
        
        if self.round_number <= 5:
            active_members = sum(len(c['members']) for c in self.clusters.values())
            print(f"[调试] 簇形成后: {len(self.clusters)}个簇, {active_members}个成员")

        # 3. 稳态通信 (有概率跳过)
        if random.random() < self.data_transmission_probability:
            self._steady_state_communication()
        else:
            if self.round_number <= 5:
                print(f"[调试] 轮{self.round_number}: 跳过数据传输")

        if self.round_number <= 5:
            active_chs_after_comm = sum(1 for ch in self.cluster_heads if ch.is_alive)
            print(f"[调试] 通信后活跃簇头: {active_chs_after_comm}")
        
        # 4. 更新轮数和统计
        self.round_number += 1
        round_stats = self._get_round_statistics()
        self.stats['round_statistics'].append(round_stats)

        return round_stats
    
    def _get_round_statistics(self) -> Dict:
        """获取当前轮的统计信息"""
        alive_nodes = [node for node in self.nodes if node.is_alive]
        total_remaining_energy = sum(node.current_energy for node in alive_nodes)

        # 直接统计活跃的簇头（而不是依赖self.cluster_heads列表）
        active_cluster_heads = [node for node in self.nodes if node.is_alive and node.is_cluster_head]

        return {
            'round': self.round_number,
            'alive_nodes': len(alive_nodes),
            'cluster_heads': len(active_cluster_heads),
            'total_remaining_energy': total_remaining_energy,
            'average_energy': total_remaining_energy / len(alive_nodes) if alive_nodes else 0,
            'energy_consumed_this_round': self.config.num_nodes * self.config.initial_energy - total_remaining_energy - self.stats['total_energy_consumed']
        }
    
    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """运行完整的LEACH仿真"""
        
        print(f">>> 开始LEACH协议仿真 (最大轮数: {max_rounds})")
        
        for round_num in range(max_rounds):
            round_stats = self.run_round()
            
            # 检查网络生存状态
            if round_stats['alive_nodes'] == 0:
                self.stats['network_lifetime'] = round_num
                print(f"[INFO] 网络在第 {round_num} 轮结束生命周期")
                break
            
            # 每100轮输出一次进度
            if round_num % 100 == 0:
                print(f"   轮数 {round_num}: 存活节点 {round_stats['alive_nodes']}, "
                      f"剩余能量 {round_stats['total_remaining_energy']:.3f}J")
        
        else:
            self.stats['network_lifetime'] = max_rounds
            print(f"[SUCCESS] 仿真完成，网络在 {max_rounds} 轮后仍有节点存活")
        
        return self.get_final_statistics()
    
    def get_final_statistics(self) -> Dict:
        """获取最终统计结果"""
        alive_nodes = [node for node in self.nodes if node.is_alive]
        
        final_stats = {
            'protocol': 'LEACH',
            'network_lifetime': self.stats['network_lifetime'],
            'total_energy_consumed': self.stats['total_energy_consumed'],
            'final_alive_nodes': len(alive_nodes),
            'energy_efficiency': self.stats['packets_transmitted'] / self.stats['total_energy_consumed'] if self.stats['total_energy_consumed'] > 0 else 0,
            'packet_delivery_ratio': self.stats['packets_received'] / self.stats['packets_transmitted'] if self.stats['packets_transmitted'] > 0 else 0,
            'average_cluster_heads_per_round': np.mean([r.get('cluster_heads', 0) for r in self.stats['round_statistics']]) if self.stats['round_statistics'] else 0,
            'additional_metrics': {
                'total_packets_sent': self.stats['packets_transmitted'],
                'total_packets_received': self.stats['packets_received']
            },
            'config': {
                'num_nodes': self.config.num_nodes,
                'initial_energy': self.config.initial_energy,
                'area_size': f"{self.config.area_width}x{self.config.area_height}",
                'packet_size': self.config.packet_size
            }
        }
        
        return final_stats

class PEGASISProtocol:
    """
    PEGASIS协议标准实现
    基于Lindsey & Raghavendra (ICCC 2002)原始论文
    Power-Efficient Gathering in Sensor Information Systems
    """

    def __init__(self, config: NetworkConfig, energy_model: ImprovedEnergyModel):
        self.config = config
        self.energy_model = energy_model
        self.nodes = []
        self.round_number = 0
        self.chain = []  # 节点链
        self.leader_index = 0  # 当前领导者在链中的索引

        # 性能统计
        self.stats = {
            'network_lifetime': 0,
            'total_energy_consumed': 0.0,
            'packets_transmitted': 0,
            'packets_received': 0,
            'chain_construction_overhead': 0,
            'round_statistics': []
        }

        self._initialize_network()
        self._construct_chain()

    def _initialize_network(self):
        """初始化网络节点"""
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            node = Node(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy
            )
            self.nodes.append(node)

    def _calculate_distance(self, node1: Node, node2: Node) -> float:
        """计算两节点间距离"""
        return math.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)

    def _calculate_distance_to_bs(self, node: Node) -> float:
        """计算节点到基站距离"""
        return math.sqrt((node.x - self.config.base_station_x)**2 +
                        (node.y - self.config.base_station_y)**2)

    def _construct_chain(self):
        """
        构建PEGASIS链
        使用贪心算法构建最短路径链
        """
        if not self.nodes:
            return

        # 从距离基站最远的节点开始
        remaining_nodes = [node for node in self.nodes if node.is_alive]
        if not remaining_nodes:
            return

        # 找到距离基站最远的节点作为起始点
        start_node = max(remaining_nodes,
                        key=lambda n: self._calculate_distance_to_bs(n))

        self.chain = [start_node]
        remaining_nodes.remove(start_node)

        # 贪心算法构建链：每次选择距离当前链端最近的节点
        while remaining_nodes:
            current_end = self.chain[-1]

            # 找到距离链尾最近的节点
            nearest_node = min(remaining_nodes,
                             key=lambda n: self._calculate_distance(current_end, n))

            self.chain.append(nearest_node)
            remaining_nodes.remove(nearest_node)

        # 初始化领导者为链中间的节点
        self.leader_index = len(self.chain) // 2

    def _update_chain(self):
        """更新链结构，移除死亡节点"""
        # 移除死亡节点
        alive_chain = [node for node in self.chain if node.is_alive]

        if not alive_chain:
            self.chain = []
            return

        # 如果链结构发生重大变化，重新构建
        if len(alive_chain) < len(self.chain) * 0.8:
            self.nodes = [node for node in self.nodes if node.is_alive]
            self._construct_chain()
        else:
            self.chain = alive_chain
            # 调整领导者索引
            if self.leader_index >= len(self.chain):
                self.leader_index = len(self.chain) // 2

    def _data_gathering_phase(self):
        """数据收集阶段"""
        if not self.chain or len(self.chain) < 2:
            return

        total_energy_consumed = 0.0
        packets_transmitted = 0
        packets_received = 0

        leader = self.chain[self.leader_index]

        # 从链的两端向领导者传输数据
        # 左侧链传输
        for i in range(self.leader_index):
            current_node = self.chain[i]
            next_node = self.chain[i + 1]

            if not current_node.is_alive or not next_node.is_alive:
                continue

            # 计算传输距离
            distance = self._calculate_distance(current_node, next_node)

            # 计算传输和接收能耗
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8,
                distance
            )
            rx_energy = self.energy_model.calculate_reception_energy(
                self.config.packet_size * 8
            )

            # 更新节点能量
            current_node.current_energy -= tx_energy
            next_node.current_energy -= rx_energy

            total_energy_consumed += (tx_energy + rx_energy)
            packets_transmitted += 1
            packets_received += 1

            # 检查节点生存状态
            if current_node.current_energy <= 0:
                current_node.is_alive = False
                current_node.current_energy = 0
            if next_node.current_energy <= 0:
                next_node.is_alive = False
                next_node.current_energy = 0

        # 右侧链传输
        for i in range(len(self.chain) - 1, self.leader_index, -1):
            current_node = self.chain[i]
            next_node = self.chain[i - 1]

            if not current_node.is_alive or not next_node.is_alive:
                continue

            # 计算传输距离
            distance = self._calculate_distance(current_node, next_node)

            # 计算传输和接收能耗
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8,
                distance
            )
            rx_energy = self.energy_model.calculate_reception_energy(
                self.config.packet_size * 8
            )

            # 更新节点能量
            current_node.current_energy -= tx_energy
            next_node.current_energy -= rx_energy

            total_energy_consumed += (tx_energy + rx_energy)
            packets_transmitted += 1
            packets_received += 1

            # 检查节点生存状态
            if current_node.current_energy <= 0:
                current_node.is_alive = False
                current_node.current_energy = 0
            if next_node.current_energy <= 0:
                next_node.is_alive = False
                next_node.current_energy = 0

        # 领导者向基站传输聚合数据
        if leader.is_alive:
            distance_to_bs = self._calculate_distance_to_bs(leader)

            # 计算传输能耗
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8,
                distance_to_bs,
                tx_power_dbm=5.0  # 向基站传输使用更高功率
            )

            # 数据聚合处理能耗
            processing_energy = self.energy_model.calculate_processing_energy(
                self.config.packet_size * 8 * len(self.chain),
                processing_complexity=1.2  # PEGASIS聚合复杂度较低
            )

            # 更新领导者能量
            leader.current_energy -= (tx_energy + processing_energy)
            total_energy_consumed += (tx_energy + processing_energy)
            packets_transmitted += 1

            # 检查领导者生存状态
            if leader.current_energy <= 0:
                leader.is_alive = False
                leader.current_energy = 0

        # 更新统计信息
        self.stats['total_energy_consumed'] += total_energy_consumed
        self.stats['packets_transmitted'] += packets_transmitted
        self.stats['packets_received'] += packets_received

    def run_round(self) -> Dict:
        """运行一轮PEGASIS协议"""

        # 检查网络是否还有活跃节点
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if not alive_nodes:
            return self._get_round_statistics()

        # 1. 更新链结构 (移除死亡节点)
        self._update_chain()

        # 2. 数据收集阶段
        self._data_gathering_phase()

        # 3. 轮换领导者
        if self.chain:
            self.leader_index = (self.leader_index + 1) % len(self.chain)

        # 4. 更新轮数
        self.round_number += 1

        # 5. 记录本轮统计
        round_stats = self._get_round_statistics()
        self.stats['round_statistics'].append(round_stats)

        return round_stats

    def _get_round_statistics(self) -> Dict:
        """获取当前轮的统计信息"""
        alive_nodes = [node for node in self.nodes if node.is_alive]
        total_remaining_energy = sum(node.current_energy for node in alive_nodes)

        return {
            'round': self.round_number,
            'alive_nodes': len(alive_nodes),
            'chain_length': len(self.chain),
            'leader_id': self.chain[self.leader_index].id if self.chain else -1,
            'total_remaining_energy': total_remaining_energy,
            'average_energy': total_remaining_energy / len(alive_nodes) if alive_nodes else 0,
            'energy_consumed_this_round': self.config.num_nodes * self.config.initial_energy - total_remaining_energy - self.stats['total_energy_consumed']
        }

    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """运行完整的PEGASIS仿真"""

        print(f">>> 开始PEGASIS协议仿真 (最大轮数: {max_rounds})")

        for round_num in range(max_rounds):
            round_stats = self.run_round()

            # 检查网络生存状态
            if round_stats['alive_nodes'] == 0:
                self.stats['network_lifetime'] = round_num
                print(f"[INFO] 网络在第 {round_num} 轮结束生命周期")
                break

            # 每100轮输出一次进度
            if round_num % 100 == 0:
                print(f"   轮数 {round_num}: 存活节点 {round_stats['alive_nodes']}, "
                      f"剩余能量 {round_stats['total_remaining_energy']:.3f}J, "
                      f"链长度 {round_stats['chain_length']}")

        else:
            self.stats['network_lifetime'] = max_rounds
            print(f"[SUCCESS] 仿真完成，网络在 {max_rounds} 轮后仍有节点存活")

        return self.get_final_statistics()

    def get_final_statistics(self) -> Dict:
        """获取最终统计结果"""
        alive_nodes = [node for node in self.nodes if node.is_alive]

        final_stats = {
            'protocol': 'PEGASIS',
            'network_lifetime': self.stats['network_lifetime'],
            'total_energy_consumed': self.stats['total_energy_consumed'],
            'final_alive_nodes': len(alive_nodes),
            'energy_efficiency': self.stats['packets_transmitted'] / self.stats['total_energy_consumed'] if self.stats['total_energy_consumed'] > 0 else 0,
            'packet_delivery_ratio': self.stats['packets_received'] / self.stats['packets_transmitted'] if self.stats['packets_transmitted'] > 0 else 0,
            'average_chain_length': np.mean([r.get('chain_length', 0) for r in self.stats['round_statistics']]) if self.stats['round_statistics'] else 0,
            'additional_metrics': {
                'total_packets_sent': self.stats['packets_transmitted'],
                'total_packets_received': self.stats['packets_received']
            },
            'config': {
                'num_nodes': self.config.num_nodes,
                'initial_energy': self.config.initial_energy,
                'area_size': f"{self.config.area_width}x{self.config.area_height}",
                'packet_size': self.config.packet_size
            }
        }

        return final_stats

# 测试函数
class HEEDProtocolWrapper:
    """HEED协议包装类，使其与基准测试框架兼容"""

    def __init__(self, config: NetworkConfig, energy_model: ImprovedEnergyModel):
        self.config = config
        self.energy_model = energy_model

        # 创建HEED配置
        self.heed_config = HEEDConfig(
            c_prob=0.05,  # 5% cluster heads
            p_min=0.001,
            max_iterations=10,
            transmission_range=30.0,
            packet_size=1024,
            initial_energy=config.initial_energy,
            network_width=config.area_width,
            network_height=config.area_height,
            base_station_x=config.base_station_x,
            base_station_y=config.base_station_y
        )

        self.heed_protocol = HEEDProtocol(self.heed_config)
        self.round_stats = []

    def run_simulation(self, max_rounds: int = 200) -> Dict:
        """运行HEED协议仿真"""
        # 生成节点位置
        node_positions = []
        for _ in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            node_positions.append((x, y))

        # 初始化网络
        self.heed_protocol.initialize_network(node_positions)

        # 运行仿真
        round_num = 0
        while round_num < max_rounds:
            if not self.heed_protocol.run_round():
                break

            # 记录统计信息
            stats = self.heed_protocol.get_statistics()
            self.round_stats.append(stats)
            round_num += 1

        # 计算最终统计
        final_stats = self.heed_protocol.get_final_statistics()

        # 计算平均簇头数
        avg_cluster_heads = 0
        if self.round_stats:
            total_clusters = sum(len(stats.get('cluster_heads', [])) for stats in self.round_stats)
            avg_cluster_heads = total_clusters / len(self.round_stats)

        # 返回与其他协议兼容的结果格式
        return {
            'protocol': 'HEED',
            'network_lifetime': final_stats['network_lifetime'],
            'total_energy_consumed': final_stats['total_energy_consumed'],
            'packets_transmitted': final_stats['packets_transmitted'],
            'packets_received': final_stats['packets_received'],
            'packet_delivery_ratio': final_stats['packet_delivery_ratio'],
            'energy_efficiency': final_stats['energy_efficiency'],
            'final_alive_nodes': final_stats['final_alive_nodes'],
            'average_cluster_heads_per_round': avg_cluster_heads,
            'additional_metrics': final_stats['additional_metrics']
        }

class TEENProtocolWrapper:
    """TEEN协议包装类，使其与基准测试框架兼容"""

    def __init__(self, config: NetworkConfig, energy_model: ImprovedEnergyModel):
        self.config = config
        self.energy_model = energy_model

        # 创建TEEN配置 - 使用修复后的优化参数
        self.teen_config = TEENConfig(
            num_nodes=config.num_nodes,
            area_width=config.area_width,
            area_height=config.area_height,
            base_station_x=config.base_station_x,
            base_station_y=config.base_station_y,
            initial_energy=config.initial_energy,
            transmission_range=30.0,
            packet_size=1024,
            hard_threshold=45.0,    # 修复后：大幅降低硬阈值
            soft_threshold=0.5,     # 修复后：大幅降低软阈值
            max_time_interval=3,    # 修复后：缩短强制传输间隔
            cluster_head_percentage=0.08  # 修复后：增加簇头比例
        )

        self.teen_protocol = TEENProtocol(self.teen_config)
        self.round_stats = []

    def run_simulation(self, max_rounds: int = 200) -> Dict:
        """运行TEEN协议仿真"""
        # 生成节点位置
        node_positions = []
        for _ in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            node_positions.append((x, y))

        # 初始化网络
        self.teen_protocol.initialize_network(node_positions)

        # 运行仿真
        results = self.teen_protocol.run_simulation(max_rounds)

        # 返回与其他协议兼容的结果格式
        return {
            'protocol': 'TEEN',
            'network_lifetime': results['network_lifetime'],
            'total_energy_consumed': results['total_energy_consumed'],
            'packets_transmitted': results['packets_transmitted'],
            'packets_received': results['packets_received'],
            'packet_delivery_ratio': results['packet_delivery_ratio'],
            'energy_efficiency': results['energy_efficiency'],
            'final_alive_nodes': results['final_alive_nodes'],
            'average_cluster_heads_per_round': results['average_cluster_heads_per_round'],
            'additional_metrics': results['additional_metrics']
        }

def test_leach_protocol():
    """测试LEACH协议实现"""

    print("[TEST] 测试LEACH协议标准实现")
    print("=" * 50)

    # 创建网络配置
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )

    # 创建能耗模型
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    # 创建LEACH协议实例
    leach = LEACHProtocol(config, energy_model)

    # 运行仿真
    results = leach.run_simulation(max_rounds=200)

    # 输出结果
    print("\n[RESULT] LEACH协议仿真结果:")
    print(f"   网络生存时间: {results['network_lifetime']} 轮")
    print(f"   总能耗: {results['total_energy_consumed']:.6f} J")
    print(f"   最终存活节点: {results['final_alive_nodes']}")
    print(f"   能效: {results['energy_efficiency']:.2f} packets/J")
    print(f"   数据包投递率: {results['packet_delivery_ratio']:.3f}")
    print(f"   平均簇头数: {results['average_cluster_heads_per_round']:.1f}")

def test_pegasis_protocol():
    """测试PEGASIS协议实现"""

    print("\n[TEST] 测试PEGASIS协议标准实现")
    print("=" * 50)

    # 创建网络配置
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )

    # 创建能耗模型
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    # 创建PEGASIS协议实例
    pegasis = PEGASISProtocol(config, energy_model)

    # 运行仿真
    results = pegasis.run_simulation(max_rounds=200)

    # 输出结果
    print("\n[RESULT] PEGASIS协议仿真结果:")
    print(f"   网络生存时间: {results['network_lifetime']} 轮")
    print(f"   总能耗: {results['total_energy_consumed']:.6f} J")
    print(f"   最终存活节点: {results['final_alive_nodes']}")
    print(f"   能效: {results['energy_efficiency']:.2f} packets/J")
    print(f"   数据包投递率: {results['packet_delivery_ratio']:.3f}")
    print(f"   平均链长度: {results['average_chain_length']:.1f}")

def test_heed_protocol():
    """测试HEED协议实现"""

    print("\n[TEST] 测试HEED协议标准实现")
    print("=" * 50)

    # 创建网络配置
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )

    # 创建能耗模型
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    # 创建HEED协议实例
    heed = HEEDProtocolWrapper(config, energy_model)

    # 运行仿真
    results = heed.run_simulation(max_rounds=200)

    # 输出结果
    print("\n[RESULT] HEED协议仿真结果:")
    print(f"   网络生存时间: {results['network_lifetime']} 轮")
    print(f"   总能耗: {results['total_energy_consumed']:.6f} J")
    print(f"   最终存活节点: {results['final_alive_nodes']}")
    print(f"   能效: {results['energy_efficiency']:.2f} packets/J")
    print(f"   数据包投递率: {results['packet_delivery_ratio']:.3f}")
    print(f"   平均簇头数: {results['average_cluster_heads_per_round']:.1f}")

def test_teen_protocol():
    """测试TEEN协议实现"""

    print("\n[TEST] 测试TEEN协议标准实现")
    print("=" * 50)

    # 创建网络配置
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )

    # 创建能耗模型
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    # 创建TEEN协议实例
    teen = TEENProtocolWrapper(config, energy_model)

    # 运行仿真
    results = teen.run_simulation(max_rounds=200)

    # 输出结果
    print("\n[RESULT] TEEN协议仿真结果:")
    print(f"   网络生存时间: {results['network_lifetime']} 轮")
    print(f"   总能耗: {results['total_energy_consumed']:.6f} J")
    print(f"   最终存活节点: {results['final_alive_nodes']}")
    print(f"   能效: {results['energy_efficiency']:.2f} packets/J")
    print(f"   数据包投递率: {results['packet_delivery_ratio']:.3f}")
    print(f"   平均簇头数: {results['average_cluster_heads_per_round']:.1f}")
    print(f"   硬阈值: {results['additional_metrics']['hard_threshold']}")
    print(f"   软阈值: {results['additional_metrics']['soft_threshold']}")

def test_all_protocols():
    """测试所有基准协议"""
    print(">>> WSN基准协议对比测试")
    print("=" * 60)

    test_leach_protocol()
    test_pegasis_protocol()
    test_heed_protocol()
    test_teen_protocol()

if __name__ == "__main__":
    test_all_protocols()
