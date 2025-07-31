#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正版LEACH协议 - 严格匹配权威LEACH行为

基于权威LEACH-PY实现的关键发现：
1. 协议开销巨大：Hello消息广播消耗大量能量
2. 快速节点死亡：2J初始能量快速耗尽
3. 低传输率：~1包/轮，大部分轮次无簇头
4. 直接传输：无簇头时直接向基站传输

修正要点：
- 增加Hello消息广播的协议开销
- 实现正确的能耗累积模式
- 匹配权威LEACH的节点死亡模式
- 实现真实的传输概率控制

作者: Enhanced EEHFR Research Team
日期: 2025-01-31
版本: 3.0 (Corrected Implementation)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import copy

@dataclass
class Node:
    """WSN节点类"""
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    is_alive: bool = True
    is_cluster_head: bool = False
    cluster_id: int = -1
    
    # 权威LEACH特有属性
    my_cluster_head: int = -1  # MCH属性
    round_as_ch: int = -1      # 上次作为簇头的轮次

@dataclass
class NetworkConfig:
    """网络配置参数 - 严格匹配权威LEACH"""
    num_nodes: int = 50
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 175.0
    initial_energy: float = 2.0      # 2J (权威LEACH标准)
    data_packet_size: int = 4000     # 4000 bits
    hello_packet_size: int = 100     # 100 bits (协议开销)
    num_packet_attempts: int = 10    # 每轮传输尝试次数

class CorrectedLEACHProtocol:
    """修正版LEACH协议 - 严格匹配权威行为"""
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        self.nodes = []
        self.round_number = 0
        self.cluster_heads = []
        self.clusters = {}
        
        # 权威LEACH参数
        self.p = 0.1  # 簇头概率
        
        # 严格匹配权威LEACH的能耗参数
        self.ETX = 50e-9         # 50 nJ/bit (发送电路能耗)
        self.ERX = 50e-9         # 50 nJ/bit (接收电路能耗)
        self.EDA = 5e-9          # 5 nJ/bit (数据聚合能耗) - 关键缺失参数!
        self.Efs = 10e-12        # 10 pJ/bit/m² (自由空间放大器)
        self.Emp = 0.0013e-12    # 0.0013 pJ/bit/m⁴ (多径放大器)
        self.d_crossover = math.sqrt(self.Efs / self.Emp)  # ~87.7m
        
        # 统计信息
        self.stats = {
            'total_packets_sent': 0,
            'total_packets_received': 0,
            'total_transmission_attempts': 0,
            'total_energy_consumed': 0.0,
            'hello_messages_sent': 0,
            'protocol_overhead_energy': 0.0,
            'data_transmission_energy': 0.0,
            'round_stats': []
        }
        
        # 初始化网络
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
    
    def _calculate_transmission_energy(self, packet_size_bits: int, distance: float) -> float:
        """
        严格匹配权威LEACH的能耗计算
        基于权威LEACH-PY源码实现
        """
        # 权威LEACH能耗公式
        if distance > self.d_crossover:
            # 多径衰落模型 (distance > do)
            tx_energy = self.ETX * packet_size_bits + self.Emp * packet_size_bits * (distance ** 4)
        else:
            # 自由空间模型 (distance <= do)
            tx_energy = self.ETX * packet_size_bits + self.Efs * packet_size_bits * (distance ** 2)

        return tx_energy

    def _calculate_reception_energy(self, packet_size_bits: int) -> float:
        """
        严格匹配权威LEACH的接收能耗计算
        包含数据聚合能耗EDA
        """
        return (self.ERX + self.EDA) * packet_size_bits
    
    def _broadcast_hello_messages(self) -> float:
        """
        严格匹配权威LEACH的Hello消息广播模式

        权威LEACH有两个关键广播阶段：
        1. 基站向所有节点广播Hello消息
        2. 每个簇头向范围内节点广播Hello消息

        这是导致快速节点死亡的主要原因！
        """
        total_hello_energy = 0.0
        hello_messages_sent = 0

        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return 0.0

        # 阶段1: 基站向所有节点广播Hello消息 (权威LEACH第227-247行)
        # 基站发送Hello给所有活跃节点
        bs_to_nodes_energy = 0.0
        for node in alive_nodes:
            distance_to_bs = self._calculate_distance_to_bs(node)

            # 基站发送能耗 (基站能量无限，不计算)
            # 节点接收能耗
            rx_energy = self._calculate_reception_energy(self.config.hello_packet_size)
            node.current_energy -= rx_energy
            bs_to_nodes_energy += rx_energy
            hello_messages_sent += 1

            # 检查节点是否因接收Hello而死亡
            if node.current_energy <= 0:
                node.is_alive = False
                node.current_energy = 0

        total_hello_energy += bs_to_nodes_energy

        # 阶段2: 每个簇头向范围内节点广播Hello消息 (权威LEACH第376-408行)
        # 注意：这发生在簇头选择之后
        ch_broadcast_energy = 0.0
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue

            # 找到在簇头通信范围内的节点
            receivers_in_range = []
            for node in self.nodes:
                if node.is_alive and node.id != ch.id:
                    distance = self._calculate_distance(ch, node)
                    # 假设通信范围为50m (可调整)
                    if distance <= 50.0:
                        receivers_in_range.append(node)

            # 簇头向范围内每个节点发送Hello消息
            for receiver in receivers_in_range:
                distance = self._calculate_distance(ch, receiver)

                # 簇头发送能耗
                tx_energy = self._calculate_transmission_energy(
                    self.config.hello_packet_size, distance
                )
                ch.current_energy -= tx_energy
                ch_broadcast_energy += tx_energy

                # 接收节点接收能耗
                rx_energy = self._calculate_reception_energy(self.config.hello_packet_size)
                receiver.current_energy -= rx_energy
                ch_broadcast_energy += rx_energy

                hello_messages_sent += 1

                # 检查节点是否死亡
                if ch.current_energy <= 0:
                    ch.is_alive = False
                    ch.current_energy = 0
                    break  # 簇头死亡，停止发送

                if receiver.current_energy <= 0:
                    receiver.is_alive = False
                    receiver.current_energy = 0

        total_hello_energy += ch_broadcast_energy

        # 更新统计
        self.stats['hello_messages_sent'] += hello_messages_sent
        self.stats['protocol_overhead_energy'] += total_hello_energy

        return total_hello_energy
    
    def _select_cluster_heads(self) -> List[Node]:
        """
        权威LEACH簇头选择算法
        严格匹配原始论文的阈值计算
        """
        cluster_heads = []
        
        for node in self.nodes:
            if not node.is_alive:
                continue
            
            # 权威LEACH阈值计算
            # T(n) = P / (1 - P * (r mod (1/P))) if n ∈ G
            # 其中G是在过去1/P轮中没有当过簇头的节点集合
            
            if self.round_number % int(1/self.p) == 0:
                # 新周期开始，重置所有节点的簇头历史
                node.round_as_ch = -1
            
            # 检查节点是否在当前周期内当过簇头
            current_cycle_start = (self.round_number // int(1/self.p)) * int(1/self.p)
            if node.round_as_ch >= current_cycle_start:
                continue  # 本周期已当过簇头，跳过
            
            # 计算阈值
            threshold = self.p / (1 - self.p * (self.round_number % int(1/self.p)))
            
            # 随机选择
            if random.random() < threshold:
                node.is_cluster_head = True
                node.round_as_ch = self.round_number
                cluster_heads.append(node)
            else:
                node.is_cluster_head = False
        
        return cluster_heads
    
    def _form_clusters(self, cluster_heads: List[Node]):
        """形成簇结构"""
        self.clusters = {}
        
        # 初始化簇
        for ch in cluster_heads:
            self.clusters[ch.id] = []
            ch.my_cluster_head = ch.id  # 簇头的MCH是自己
        
        # 非簇头节点加入最近的簇头
        for node in self.nodes:
            if not node.is_alive or node.is_cluster_head:
                continue
            
            if not cluster_heads:
                # 没有簇头，直接连接基站
                node.cluster_id = -1
                node.my_cluster_head = -1  # -1表示基站
                continue
            
            # 找到最近的簇头
            best_ch = None
            min_distance = float('inf')
            
            for ch in cluster_heads:
                distance = self._calculate_distance(node, ch)
                if distance < min_distance:
                    min_distance = distance
                    best_ch = ch
            
            if best_ch:
                node.cluster_id = best_ch.id
                node.my_cluster_head = best_ch.id
                self.clusters[best_ch.id].append(node)
    
    def _data_transmission_phase(self) -> Tuple[int, int, int, float]:
        """
        严格匹配权威LEACH的数据传输阶段

        权威LEACH模式：
        1. 每个簇头找到发送者节点
        2. 发送者向簇头发送数据包
        3. 簇头聚合数据后向基站发送
        4. NumPacket=10控制每轮传输尝试次数

        Returns:
            (packets_sent, packets_received, transmission_attempts, energy_consumed)
        """
        packets_sent = 0
        packets_received = 0
        transmission_attempts = 0
        energy_consumed = 0.0

        # 权威LEACH的关键逻辑：基于簇头进行数据传输
        # 参考权威LEACH第416-450行的steady_state_phase

        for _ in range(self.config.num_packet_attempts):
            transmission_attempts += 1

            # 如果没有活跃的簇头，随机选择节点直接向基站传输
            alive_cluster_heads = [ch for ch in self.cluster_heads if ch.is_alive]

            if not alive_cluster_heads:
                # 没有簇头，随机选择节点直接向基站传输
                alive_nodes = [n for n in self.nodes if n.is_alive]
                if not alive_nodes:
                    break

                sender = random.choice(alive_nodes)
                distance = self._calculate_distance_to_bs(sender)

                # 计算传输能耗
                tx_energy = self._calculate_transmission_energy(self.config.data_packet_size, distance)

                if sender.current_energy >= tx_energy:
                    sender.current_energy -= tx_energy
                    energy_consumed += tx_energy
                    packets_sent += 1
                    packets_received += 1  # 假设基站成功接收

                    if sender.current_energy <= 0:
                        sender.is_alive = False
                        sender.current_energy = 0

                continue

            # 权威LEACH模式：为每个簇头找到发送者
            selected_ch = random.choice(alive_cluster_heads)

            # 找到该簇头的成员节点作为发送者
            cluster_members = []
            if selected_ch.id in self.clusters:
                cluster_members = [n for n in self.clusters[selected_ch.id] if n.is_alive]

            if cluster_members:
                # 簇内有成员，成员向簇头发送数据
                sender = random.choice(cluster_members)
                distance = self._calculate_distance(sender, selected_ch)

                # 成员节点发送能耗
                tx_energy = self._calculate_transmission_energy(self.config.data_packet_size, distance)

                if sender.current_energy >= tx_energy:
                    sender.current_energy -= tx_energy
                    energy_consumed += tx_energy

                    # 簇头接收能耗
                    rx_energy = self._calculate_reception_energy(self.config.data_packet_size)
                    if selected_ch.current_energy >= rx_energy:
                        selected_ch.current_energy -= rx_energy
                        energy_consumed += rx_energy
                        packets_sent += 1
                        packets_received += 1

                        # 簇头向基站转发聚合数据
                        bs_distance = self._calculate_distance_to_bs(selected_ch)
                        bs_tx_energy = self._calculate_transmission_energy(self.config.data_packet_size, bs_distance)

                        if selected_ch.current_energy >= bs_tx_energy:
                            selected_ch.current_energy -= bs_tx_energy
                            energy_consumed += bs_tx_energy
                        else:
                            selected_ch.is_alive = False
                            selected_ch.current_energy = 0
                    else:
                        selected_ch.is_alive = False
                        selected_ch.current_energy = 0

                    if sender.current_energy <= 0:
                        sender.is_alive = False
                        sender.current_energy = 0
            else:
                # 簇头没有成员，簇头直接向基站发送数据
                distance = self._calculate_distance_to_bs(selected_ch)
                tx_energy = self._calculate_transmission_energy(self.config.data_packet_size, distance)

                if selected_ch.current_energy >= tx_energy:
                    selected_ch.current_energy -= tx_energy
                    energy_consumed += tx_energy
                    packets_sent += 1
                    packets_received += 1

                    if selected_ch.current_energy <= 0:
                        selected_ch.is_alive = False
                        selected_ch.current_energy = 0

        return packets_sent, packets_received, transmission_attempts, energy_consumed

    def run_round(self) -> Dict:
        """运行一轮LEACH协议 - 严格匹配权威行为"""
        self.round_number += 1

        # 初始化轮次统计
        round_stats = {
            'round': self.round_number,
            'alive_nodes_start': sum(1 for n in self.nodes if n.is_alive),
            'cluster_heads': 0,
            'packets_sent': 0,
            'packets_received': 0,
            'transmission_attempts': 0,
            'hello_energy': 0.0,
            'data_energy': 0.0,
            'total_energy': 0.0,
            'alive_nodes_end': 0
        }

        # 检查网络是否还活着
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if len(alive_nodes) == 0:
            return round_stats

        energy_before = sum(n.current_energy for n in self.nodes)

        # 1. 协议开销阶段：Hello消息广播
        hello_energy = self._broadcast_hello_messages()
        round_stats['hello_energy'] = hello_energy

        # 2. 簇头选择阶段
        cluster_heads = self._select_cluster_heads()
        self.cluster_heads = cluster_heads
        round_stats['cluster_heads'] = len(cluster_heads)

        # 3. 簇形成阶段
        self._form_clusters(cluster_heads)

        # 4. 数据传输阶段
        packets_sent, packets_received, transmission_attempts, data_energy = self._data_transmission_phase()

        round_stats['packets_sent'] = packets_sent
        round_stats['packets_received'] = packets_received
        round_stats['transmission_attempts'] = transmission_attempts
        round_stats['data_energy'] = data_energy

        # 计算总能耗
        energy_after = sum(n.current_energy for n in self.nodes)
        total_energy_consumed = energy_before - energy_after
        round_stats['total_energy'] = total_energy_consumed

        # 更新全局统计
        self.stats['total_packets_sent'] += packets_sent
        self.stats['total_packets_received'] += packets_received
        self.stats['total_transmission_attempts'] += transmission_attempts
        self.stats['total_energy_consumed'] += total_energy_consumed
        self.stats['data_transmission_energy'] += data_energy

        # 最终存活节点数
        round_stats['alive_nodes_end'] = sum(1 for n in self.nodes if n.is_alive)

        # 保存轮次统计
        self.stats['round_stats'].append(round_stats)

        return round_stats

    def get_network_statistics(self) -> Dict:
        """获取网络统计信息"""
        alive_nodes = sum(1 for n in self.nodes if n.is_alive)

        # 计算真实的PDR和传输率
        pdr = (self.stats['total_packets_received'] /
               self.stats['total_packets_sent']) if self.stats['total_packets_sent'] > 0 else 0

        transmission_rate = (self.stats['total_packets_sent'] /
                           self.stats['total_transmission_attempts']) if self.stats['total_transmission_attempts'] > 0 else 0

        packets_per_round = self.stats['total_packets_sent'] / self.round_number if self.round_number > 0 else 0

        # 计算能耗分布
        protocol_overhead_ratio = (self.stats['protocol_overhead_energy'] /
                                 self.stats['total_energy_consumed']) if self.stats['total_energy_consumed'] > 0 else 0

        data_transmission_ratio = (self.stats['data_transmission_energy'] /
                                 self.stats['total_energy_consumed']) if self.stats['total_energy_consumed'] > 0 else 0

        return {
            'total_rounds': self.round_number,
            'alive_nodes': alive_nodes,
            'network_lifetime': self.round_number if alive_nodes > 0 else self._find_network_death_round(),
            'total_packets_sent': self.stats['total_packets_sent'],
            'total_packets_received': self.stats['total_packets_received'],
            'total_transmission_attempts': self.stats['total_transmission_attempts'],
            'packet_delivery_ratio': pdr,
            'transmission_rate': transmission_rate,
            'packets_per_round': packets_per_round,
            'total_energy_consumed': self.stats['total_energy_consumed'],
            'protocol_overhead_energy': self.stats['protocol_overhead_energy'],
            'data_transmission_energy': self.stats['data_transmission_energy'],
            'protocol_overhead_ratio': protocol_overhead_ratio,
            'data_transmission_ratio': data_transmission_ratio,
            'hello_messages_sent': self.stats['hello_messages_sent'],
            'initial_total_energy': self.config.num_nodes * self.config.initial_energy,
            'remaining_energy': sum(n.current_energy for n in self.nodes),
            'energy_efficiency': self.stats['total_packets_sent'] / self.stats['total_energy_consumed'] if self.stats['total_energy_consumed'] > 0 else 0
        }

    def _find_network_death_round(self) -> int:
        """找到网络死亡的轮次"""
        for i, round_stat in enumerate(self.stats['round_stats']):
            if round_stat['alive_nodes_end'] == 0:
                return i + 1
        return self.round_number

    def get_node_energy_distribution(self) -> Dict:
        """获取节点能量分布"""
        alive_energies = [n.current_energy for n in self.nodes if n.is_alive]
        dead_nodes = sum(1 for n in self.nodes if not n.is_alive)

        return {
            'alive_nodes': len(alive_energies),
            'dead_nodes': dead_nodes,
            'min_energy': min(alive_energies) if alive_energies else 0,
            'max_energy': max(alive_energies) if alive_energies else 0,
            'avg_energy': np.mean(alive_energies) if alive_energies else 0,
            'std_energy': np.std(alive_energies) if alive_energies else 0,
            'total_remaining_energy': sum(alive_energies)
        }
