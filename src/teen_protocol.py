#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEEN (Threshold sensitive Energy Efficient sensor Network) Protocol Implementation

基于Manjeshwar & Agrawal经典论文实现:
"TEEN: A Routing Protocol for Enhanced Efficiency in Wireless Sensor Networks"
IEEE IPDPS 2001

TEEN协议特点:
- 阈值敏感的反应式协议
- 硬阈值(Hard Threshold)和软阈值(Soft Threshold)机制
- 适用于时间关键应用
- 基于LEACH的分层聚类结构

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0 (基于原始论文实现)
"""

import numpy as np
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import copy

@dataclass
class TEENConfig:
    """TEEN协议配置参数"""
    # 基本网络参数
    num_nodes: int = 50
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 175.0
    
    # 能量参数
    initial_energy: float = 2.0
    
    # 通信参数
    transmission_range: float = 30.0
    packet_size: int = 1024  # bits
    
    # TEEN特有参数
    hard_threshold: float = 70.0    # 硬阈值 - 感知属性的绝对阈值
    soft_threshold: float = 2.0     # 软阈值 - 感知属性的变化阈值
    max_time_interval: int = 10     # 最大时间间隔(轮数)
    
    # 聚类参数(继承自LEACH)
    cluster_head_percentage: float = 0.05  # 5%的节点作为簇头
    
    # 感知参数
    sensing_range: float = 15.0
    min_sensor_value: float = 20.0
    max_sensor_value: float = 100.0

class TEENNodeState(Enum):
    """TEEN节点状态"""
    NORMAL = "normal"           # 普通节点
    CLUSTER_HEAD = "cluster_head"  # 簇头节点
    DEAD = "dead"              # 死亡节点

@dataclass
class TEENNode:
    """TEEN协议节点类"""
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    state: TEENNodeState = TEENNodeState.NORMAL
    
    # 聚类相关
    cluster_id: int = -1
    is_cluster_head: bool = False
    cluster_head_id: int = -1
    
    # TEEN特有属性
    last_sensed_value: float = 0.0      # 上次感知值
    last_transmitted_value: float = 0.0  # 上次传输值
    last_transmission_time: int = 0      # 上次传输时间
    hard_threshold: float = 70.0         # 硬阈值
    soft_threshold: float = 2.0          # 软阈值
    
    # 统计信息
    packets_sent: int = 0
    packets_received: int = 0
    
    def __post_init__(self):
        if self.current_energy is None:
            self.current_energy = self.initial_energy
    
    def is_alive(self) -> bool:
        """检查节点是否存活"""
        return self.current_energy > 0 and self.state != TEENNodeState.DEAD
    
    def distance_to(self, other_node: 'TEENNode') -> float:
        """计算到另一个节点的距离"""
        return math.sqrt((self.x - other_node.x)**2 + (self.y - other_node.y)**2)
    
    def distance_to_base_station(self, bs_x: float, bs_y: float) -> float:
        """计算到基站的距离"""
        return math.sqrt((self.x - bs_x)**2 + (self.y - bs_y)**2)
    
    def sense_environment(self) -> float:
        """模拟环境感知 - 返回感知值"""
        # 改进的环境模拟：更容易触发阈值的温度感知
        base_temp = 65.0  # 提高基础温度
        location_factor = (self.x + self.y) / 200.0 * 20.0  # 增加位置影响
        time_factor = random.uniform(-5.0, 15.0)  # 时间变化因子
        noise = random.gauss(0, 3.0)  # 增加噪声
        sensed_value = base_temp + location_factor + time_factor + noise

        # 限制在合理范围内
        sensed_value = max(20.0, min(100.0, sensed_value))
        self.last_sensed_value = sensed_value
        return sensed_value
    
    def should_transmit(self, current_time: int, max_time_interval: int) -> bool:
        """TEEN核心逻辑：判断是否应该传输数据"""
        current_value = self.sense_environment()

        # 条件1：硬阈值检查
        if current_value < self.hard_threshold:
            return False

        # 首次传输：如果从未传输过，直接传输
        if self.last_transmission_time == 0:
            self.last_transmitted_value = current_value
            self.last_transmission_time = current_time
            return True

        # 条件2：软阈值检查
        value_change = abs(current_value - self.last_transmitted_value)
        if value_change >= self.soft_threshold:
            # 软阈值满足，可以传输
            self.last_transmitted_value = current_value
            self.last_transmission_time = current_time
            return True

        # 条件3：时间间隔检查 - 即使软阈值不满足，如果时间间隔过长也要传输
        time_since_last = current_time - self.last_transmission_time
        if time_since_last >= max_time_interval:
            self.last_transmitted_value = current_value
            self.last_transmission_time = current_time
            return True

        # 不满足传输条件
        return False

class TEENProtocol:
    """TEEN协议主类"""
    
    def __init__(self, config: TEENConfig):
        self.config = config
        self.nodes: List[TEENNode] = []
        self.clusters: Dict[int, Dict] = {}
        self.current_round = 0
        self.base_station = (config.base_station_x, config.base_station_y)
        
        # 统计信息
        self.total_energy_consumed = 0.0
        self.packets_transmitted = 0
        self.packets_received = 0
        self.network_lifetime = 0
        self.round_stats = []
        
    def initialize_network(self, node_positions: List[Tuple[float, float]]):
        """初始化网络节点"""
        self.nodes = []
        for i, (x, y) in enumerate(node_positions):
            node = TEENNode(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy,
                hard_threshold=self.config.hard_threshold,
                soft_threshold=self.config.soft_threshold
            )
            self.nodes.append(node)
    
    def _form_clusters(self):
        """形成簇结构 - 基于LEACH的聚类算法"""
        # 重置所有节点的簇头状态
        for node in self.nodes:
            if node.is_alive():
                node.is_cluster_head = False
                node.cluster_id = -1
                node.cluster_head_id = -1
                node.state = TEENNodeState.NORMAL
        
        # 选择簇头
        alive_nodes = [node for node in self.nodes if node.is_alive()]
        if not alive_nodes:
            return
        
        # 计算期望的簇头数量
        expected_cluster_heads = max(1, int(len(alive_nodes) * self.config.cluster_head_percentage))
        
        # 随机选择簇头
        cluster_heads = random.sample(alive_nodes, min(expected_cluster_heads, len(alive_nodes)))
        
        # 设置簇头
        self.clusters = {}
        for i, ch in enumerate(cluster_heads):
            ch.is_cluster_head = True
            ch.cluster_id = i
            ch.cluster_head_id = ch.id
            ch.state = TEENNodeState.CLUSTER_HEAD
            
            self.clusters[i] = {
                'head': ch,
                'members': [],
                'hard_threshold': self.config.hard_threshold,
                'soft_threshold': self.config.soft_threshold
            }
        
        # 为每个非簇头节点分配到最近的簇头
        for node in alive_nodes:
            if not node.is_cluster_head:
                min_distance = float('inf')
                best_cluster = -1
                
                for cluster_id, cluster_info in self.clusters.items():
                    ch = cluster_info['head']
                    distance = node.distance_to(ch)
                    if distance < min_distance:
                        min_distance = distance
                        best_cluster = cluster_id
                
                if best_cluster != -1:
                    node.cluster_id = best_cluster
                    node.cluster_head_id = self.clusters[best_cluster]['head'].id
                    self.clusters[best_cluster]['members'].append(node)
    
    def _broadcast_thresholds(self):
        """簇头广播阈值参数给成员节点"""
        for cluster_id, cluster_info in self.clusters.items():
            ch = cluster_info['head']
            hard_threshold = cluster_info['hard_threshold']
            soft_threshold = cluster_info['soft_threshold']
            
            # 广播给所有成员节点
            for member in cluster_info['members']:
                member.hard_threshold = hard_threshold
                member.soft_threshold = soft_threshold
                
                # 消耗通信能量
                distance = ch.distance_to(member)
                energy_cost = self._calculate_transmission_energy(distance, self.config.packet_size)
                ch.current_energy -= energy_cost
                self.total_energy_consumed += energy_cost
    
    def _data_transmission_phase(self):
        """数据传输阶段 - TEEN的核心"""
        packets_this_round = 0
        
        for cluster_id, cluster_info in self.clusters.items():
            ch = cluster_info['head']
            if not ch.is_alive():
                continue
            
            # 成员节点根据TEEN规则决定是否传输
            for member in cluster_info['members']:
                if not member.is_alive():
                    continue
                
                # TEEN核心逻辑：检查是否满足传输条件
                if member.should_transmit(self.current_round, self.config.max_time_interval):
                    # 传输数据到簇头
                    distance = member.distance_to(ch)
                    energy_cost = self._calculate_transmission_energy(distance, self.config.packet_size)
                    
                    if member.current_energy >= energy_cost:
                        member.current_energy -= energy_cost
                        member.packets_sent += 1
                        packets_this_round += 1
                        self.total_energy_consumed += energy_cost
                        
                        # 簇头接收数据
                        if ch.is_alive():
                            reception_energy = self._calculate_reception_energy(self.config.packet_size)
                            ch.current_energy -= reception_energy
                            ch.packets_received += 1
                            self.total_energy_consumed += reception_energy
            
            # 簇头聚合数据并传输到基站
            if ch.packets_received > 0 and ch.is_alive():
                distance_to_bs = ch.distance_to_base_station(self.base_station[0], self.base_station[1])
                energy_cost = self._calculate_transmission_energy(distance_to_bs, self.config.packet_size)
                
                if ch.current_energy >= energy_cost:
                    ch.current_energy -= energy_cost
                    ch.packets_sent += 1
                    packets_this_round += 1
                    self.total_energy_consumed += energy_cost
                    self.packets_received += 1  # 基站接收
        
        self.packets_transmitted += packets_this_round
        return packets_this_round
    
    def _calculate_transmission_energy(self, distance: float, packet_size: int) -> float:
        """计算传输能耗"""
        # 简化的能耗模型
        E_elec = 50e-9  # 电子能耗 50nJ/bit
        E_amp = 100e-12  # 放大器能耗 100pJ/bit/m²
        
        if distance < 87:  # 自由空间模型
            energy = E_elec * packet_size + E_amp * packet_size * (distance ** 2)
        else:  # 多径衰落模型
            energy = E_elec * packet_size + E_amp * packet_size * (distance ** 4)
        
        return energy
    
    def _calculate_reception_energy(self, packet_size: int) -> float:
        """计算接收能耗"""
        E_elec = 50e-9  # 电子能耗 50nJ/bit
        return E_elec * packet_size
    
    def run_round(self) -> bool:
        """运行一轮协议"""
        self.current_round += 1
        
        # 检查是否还有存活节点
        alive_nodes = [node for node in self.nodes if node.is_alive()]
        if not alive_nodes:
            return False
        
        # 每隔一定轮数重新形成簇
        if self.current_round % 20 == 1:  # 每20轮重新聚类
            self._form_clusters()
            self._broadcast_thresholds()
        
        # 数据传输阶段
        packets_sent = self._data_transmission_phase()
        
        # 更新节点状态
        for node in self.nodes:
            if node.current_energy <= 0:
                node.state = TEENNodeState.DEAD
        
        # 记录统计信息
        alive_count = len(alive_nodes)
        total_energy = sum(node.current_energy for node in self.nodes)
        
        round_stat = {
            'round': self.current_round,
            'alive_nodes': alive_count,
            'total_energy': total_energy,
            'packets_sent': packets_sent,
            'cluster_count': len(self.clusters)
        }
        self.round_stats.append(round_stat)
        
        return alive_count > 0
    
    def run_simulation(self, max_rounds: int = 200) -> Dict:
        """运行完整仿真"""
        print(f"🚀 开始TEEN协议仿真 (最大轮数: {max_rounds})")
        
        while self.current_round < max_rounds:
            if not self.run_round():
                break
            
            # 每100轮输出一次状态
            if self.current_round % 100 == 0:
                alive_nodes = len([n for n in self.nodes if n.is_alive()])
                total_energy = sum(n.current_energy for n in self.nodes)
                print(f"   轮数 {self.current_round}: 存活节点 {alive_nodes}, 剩余能量 {total_energy:.3f}J")
        
        # 计算最终统计
        self.network_lifetime = self.current_round
        final_alive_nodes = len([n for n in self.nodes if n.is_alive()])
        
        # 计算能效和投递率
        energy_efficiency = self.packets_received / self.total_energy_consumed if self.total_energy_consumed > 0 else 0
        packet_delivery_ratio = self.packets_received / self.packets_transmitted if self.packets_transmitted > 0 else 0
        
        print(f"✅ 仿真完成，网络在 {self.network_lifetime} 轮后结束")
        
        return {
            'protocol': 'TEEN',
            'network_lifetime': self.network_lifetime,
            'total_energy_consumed': self.total_energy_consumed,
            'packets_transmitted': self.packets_transmitted,
            'packets_received': self.packets_received,
            'packet_delivery_ratio': packet_delivery_ratio,
            'energy_efficiency': energy_efficiency,
            'final_alive_nodes': final_alive_nodes,
            'average_cluster_heads_per_round': len(self.clusters) if self.clusters else 0,
            'additional_metrics': {
                'hard_threshold': self.config.hard_threshold,
                'soft_threshold': self.config.soft_threshold,
                'max_time_interval': self.config.max_time_interval,
                'total_rounds': self.current_round
            }
        }
    
    def get_statistics(self) -> Dict:
        """获取当前统计信息"""
        alive_nodes = [n for n in self.nodes if n.is_alive()]
        return {
            'round': self.current_round,
            'alive_nodes': len(alive_nodes),
            'total_energy_consumed': self.total_energy_consumed,
            'packets_transmitted': self.packets_transmitted,
            'packets_received': self.packets_received,
            'cluster_heads': [n.id for n in self.nodes if n.is_cluster_head and n.is_alive()]
        }
    
    def get_final_statistics(self) -> Dict:
        """获取最终统计信息"""
        return self.run_simulation(0)  # 不运行，只返回当前状态
