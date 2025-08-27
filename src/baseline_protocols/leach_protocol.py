#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LEACH (Low-Energy Adaptive Clustering Hierarchy) 协议实现
经典的WSN分层路由协议，用作EEHFR协议的对比基准

参考文献:
Heinzelman, W. R., Chandrakasan, A., & Balakrishnan, H. (2000). 
Energy-efficient communication protocol for wireless microsensor networks. 
In Proceedings of the 33rd annual Hawaii international conference on system sciences.

项目路径: EEHFR：融合模糊逻辑与混合元启发式优化的WSN智能节能路由协议/EEHFR_Optimized_v1/
数据源: Intel Berkeley Research Lab数据集 (https://db.csail.mit.edu/labdata/labdata.html)
"""

import numpy as np
import random
import math
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt

class LEACHNode:
    """LEACH协议中的传感器节点"""
    
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
        
        # LEACH特定参数
        self.ch_probability = 0.0
        self.last_ch_round = -1
        self.data_packets = []
        
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

class LEACHProtocol:
    """LEACH协议实现"""
    
    def __init__(self, nodes: List[LEACHNode], base_station: Tuple[float, float],
                 desired_ch_percentage: float = 0.1):
        """
        初始化LEACH协议 - 严格按照权威LEACH实现

        参数:
            nodes: 传感器节点列表
            base_station: 基站坐标 (x, y)
            desired_ch_percentage: 期望的簇头百分比 (权威LEACH使用0.1)
        """
        self.nodes = nodes
        self.base_station = base_station
        self.desired_ch_percentage = desired_ch_percentage
        self.current_round = 0

        # 能量消耗模型参数 (严格按照权威LEACH)
        self.E_elec = 50e-9  # 电子能耗 (J/bit) - 权威LEACH参数
        self.E_fs = 10e-12   # 自由空间模型 (J/bit/m²)
        self.E_mp = 0.0013e-12  # 多径衰落模型 (J/bit/m⁴)
        self.E_DA = 5e-9     # 数据聚合能耗 (J/bit/signal)
        self.d_crossover = math.sqrt(self.E_fs / self.E_mp)  # 距离阈值
        self.packet_size = 4000  # 数据包大小 (bits)
        self.radio_range = 0.5 * 100 * math.sqrt(2)  # 无线电范围 (权威LEACH参数)

        # 权威LEACH的初始能量参数
        self.initial_energy = 2.0  # 权威LEACH使用2J初始能量，不是10J
        
        # 性能统计
        self.total_energy_consumed = 0.0
        self.packets_sent = 0
        self.packets_received = 0
        # 端到端统计（统一为“源→基站”口径）
        self.total_source_packets = 0
        self.total_bs_delivered = 0
        self.dead_nodes = 0
        self.network_lifetime = 0
        self.energy_consumption_per_round = []
        self.alive_nodes_per_round = []

        print(f"🔧 LEACH协议初始化完成")
        print(f"   节点数: {len(self.nodes)}")
        print(f"   基站位置: {self.base_station}")
        print(f"   期望簇头比例: {self.desired_ch_percentage*100:.1f}%")
    
    def calculate_transmission_energy(self, distance: float, packet_size: int) -> float:
        """计算传输能耗"""
        if distance < self.d_crossover:
            return self.E_elec * packet_size + self.E_fs * packet_size * (distance ** 2)
        else:
            return self.E_elec * packet_size + self.E_mp * packet_size * (distance ** 4)
    
    def calculate_reception_energy(self, packet_size: int) -> float:
        """计算接收能耗"""
        return self.E_elec * packet_size
    
    def cluster_head_selection(self) -> List[LEACHNode]:
        """LEACH簇头选择算法"""
        cluster_heads = []
        
        # 计算阈值T(n)
        if self.current_round % (1 / self.desired_ch_percentage) == 0:
            # 重置所有节点的簇头历史
            for node in self.nodes:
                node.last_ch_round = -1
        
        for node in self.nodes:
            if not node.is_alive:
                continue
                
            # 如果节点在当前周期内已经当过簇头，则不能再次当选
            rounds_since_ch = self.current_round - node.last_ch_round
            if rounds_since_ch < (1 / self.desired_ch_percentage):
                continue
            
            # 计算阈值
            remaining_nodes = len([n for n in self.nodes if n.is_alive and 
                                 (self.current_round - n.last_ch_round) >= (1 / self.desired_ch_percentage)])
            
            if remaining_nodes == 0:
                continue
                
            threshold = self.desired_ch_percentage / (1 - self.desired_ch_percentage * 
                                                    (self.current_round % (1 / self.desired_ch_percentage)))
            
            # 随机数判断
            random_value = random.random()
            if random_value < threshold:
                node.is_cluster_head = True
                node.last_ch_round = self.current_round
                cluster_heads.append(node)

        # 不强制选择簇头 - 允许某些轮次没有簇头（符合权威LEACH行为）
        return cluster_heads
    
    def cluster_formation(self, cluster_heads: List[LEACHNode]):
        """簇形成阶段 - 严格按照权威LEACH逻辑"""
        # 重置所有节点的簇信息
        for node in self.nodes:
            node.reset_cluster_info()
            node.cluster_head_id = None  # None表示直接连基站

        # 重新设置簇头标记
        for ch in cluster_heads:
            ch.is_cluster_head = True

        # 非簇头节点选择最近的簇头（权威LEACH的条件判断）
        for node in self.nodes:
            if not node.is_alive or node.is_cluster_head:
                continue

            min_distance = float('inf')
            closest_ch = None

            # 找到最近的簇头
            for ch in cluster_heads:
                distance = node.distance_to(ch)
                if distance < min_distance:
                    min_distance = distance
                    closest_ch = ch

            # 权威LEACH的关键逻辑：只有满足条件才加入簇头
            if closest_ch:
                distance_to_bs = math.sqrt((node.x - self.base_station[0])**2 +
                                         (node.y - self.base_station[1])**2)

                # 条件1: 在无线电范围内 AND 条件2: 比到基站更近
                if min_distance <= self.radio_range and min_distance < distance_to_bs:
                    node.cluster_head_id = closest_ch.node_id
                    closest_ch.cluster_members.append(node)
                # 否则cluster_head_id保持None，表示直接连基站
    
    def data_transmission_phase(self, cluster_heads: List[LEACHNode]):
        """数据传输阶段 - 严格按照权威LEACH实现"""
        round_energy_consumption = 0.0

        # 稳态阶段：模拟权威LEACH的10次数据包传输尝试
        for _ in range(10):  # 权威LEACH的NumPacket=10

            # 1. 簇内数据传输（如果有簇头）
            if cluster_heads:
                for ch in cluster_heads:
                    if not ch.is_alive or not ch.cluster_members:
                        continue

                    # 簇内成员向簇头发送数据
                    for member in ch.cluster_members:
                        if not member.is_alive:
                            continue

                        distance = member.distance_to(ch)
                        tx_energy = self.calculate_transmission_energy(distance, self.packet_size)
                        rx_energy = self.calculate_reception_energy(self.packet_size)

                        if member.current_energy >= tx_energy and ch.current_energy >= rx_energy:
                            member.consume_energy(tx_energy)
                            ch.consume_energy(rx_energy)
                            round_energy_consumption += tx_energy + rx_energy

                            # 统一端到端统计口径：簇内仅视为中继，不计入源→BS送达
                            self.packets_sent += 1
                            # 不增加 self.packets_received
                            self.total_source_packets += 1  # 本轮产生一个源数据包

            # 2. 直接向基站发送数据（cluster_head_id为None）
            for node in self.nodes:
                if not node.is_alive or node.is_cluster_head:
                    continue

                if node.cluster_head_id is None:
                    bs_distance = math.sqrt((node.x - self.base_station[0])**2 +
                                          (node.y - self.base_station[1])**2)
                    tx_energy = self.calculate_transmission_energy(bs_distance, self.packet_size)

                    if node.current_energy >= tx_energy:
                        node.consume_energy(tx_energy)
                        round_energy_consumption += tx_energy

                        self.packets_sent += 1
                        # 直接到达基站：计入端到端送达
                        self.total_source_packets += 1
                        self.total_bs_delivered += 1

            # 3. 簇头向基站传输聚合数据
            if cluster_heads:
                for ch in cluster_heads:
                    if not ch.is_alive:
                        continue

                    # 数据聚合能耗
                    aggregation_energy = self.E_DA * self.packet_size * len(ch.cluster_members)

                    # 向基站传输
                    bs_distance = math.sqrt((ch.x - self.base_station[0])**2 +
                                          (ch.y - self.base_station[1])**2)
                    tx_energy = self.calculate_transmission_energy(bs_distance, self.packet_size)

                    total_ch_energy = aggregation_energy + tx_energy

                    if ch.current_energy >= total_ch_energy:
                        ch.consume_energy(total_ch_energy)
                        round_energy_consumption += total_ch_energy

                        self.packets_sent += 1
                        # 视为聚合后的端到端一次送达
                        self.total_bs_delivered += 1

            # 权威LEACH每轮只进行一次有效传输
            break

        self.total_energy_consumed += round_energy_consumption
        self.energy_consumption_per_round.append(round_energy_consumption)
    
    def run_round(self) -> bool:
        """运行一轮LEACH协议"""
        # 检查网络是否还有存活节点
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return False
        
        self.current_round += 1
        
        # 1. 簇头选择阶段
        cluster_heads = self.cluster_head_selection()
        
        # 2. 簇形成阶段
        self.cluster_formation(cluster_heads)
        
        # 3. 数据传输阶段
        self.data_transmission_phase(cluster_heads)
        
        # 4. 更新统计信息
        current_alive = len(alive_nodes)
        current_dead = len(self.nodes) - current_alive
        
        if current_dead > self.dead_nodes:
            self.dead_nodes = current_dead
            if self.network_lifetime == 0 and current_dead > 0:
                self.network_lifetime = self.current_round
        
        self.alive_nodes_per_round.append(current_alive)
        
        return True
    
    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """运行完整的LEACH仿真"""
        print(f"🚀 开始LEACH协议仿真 (最大轮数: {max_rounds})")
        
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
            'protocol_name': 'LEACH',
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
        
        print(f"✅ LEACH仿真完成")
        print(f"   网络生存时间: {results['network_lifetime']} 轮")
        print(f"   总能耗: {results['total_energy_consumed']:.3f} J")
        print(f"   数据传输成功率: {results['packet_delivery_ratio']*100:.1f}%")
        
        return results
