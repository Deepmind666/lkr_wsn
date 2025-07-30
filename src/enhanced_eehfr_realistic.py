#!/usr/bin/env python3
"""
Enhanced EEHFR Protocol with Realistic Environmental Modeling

基于文献调研的真实环境建模的增强型EEHFR协议实现
集成了Log-Normal Shadowing信道模型、IEEE 802.15.4链路质量评估和环境干扰建模

参考文献:
[1] Rappaport, T. S. (2002). Wireless communications: principles and practice
[2] Srinivasan, K., & Levis, P. (2006). RSSI is under appreciated
[3] Zuniga, M., & Krishnamachari, B. (2004). Analyzing the transitional region

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 2.0 (Realistic Environment)
"""

import numpy as np
import math
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

# 导入我们的真实信道模型
from realistic_channel_model import (
    RealisticChannelModel, 
    EnvironmentType,
    EnvironmentalFactors
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WSNNode:
    """WSN节点类 - 集成真实环境建模"""
    node_id: int
    x: float
    y: float
    initial_energy: float = 2.0  # J (焦耳)
    current_energy: float = field(init=False)
    is_alive: bool = field(default=True, init=False)
    is_cluster_head: bool = field(default=False, init=False)
    cluster_id: int = field(default=-1, init=False)
    
    # 新增：环境相关属性
    temperature: float = 25.0      # °C
    humidity: float = 0.5          # 相对湿度 (0-1)
    interference_level: float = 0.1 # 干扰水平 (0-1)
    
    # 链路质量历史记录
    rssi_history: List[float] = field(default_factory=list, init=False)
    lqi_history: List[int] = field(default_factory=list, init=False)
    pdr_history: List[float] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        self.current_energy = self.initial_energy
        
    def distance_to(self, other: 'WSNNode') -> float:
        """计算到另一个节点的距离"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def consume_energy(self, amount: float):
        """消耗能量"""
        self.current_energy = max(0, self.current_energy - amount)
        if self.current_energy <= 0:
            self.is_alive = False
            logger.info(f"Node {self.node_id} died due to energy depletion")
    
    def get_residual_energy_ratio(self) -> float:
        """获取剩余能量比例"""
        return self.current_energy / self.initial_energy if self.initial_energy > 0 else 0
    
    def update_link_quality_history(self, rssi: float, lqi: int, pdr: float):
        """更新链路质量历史记录"""
        self.rssi_history.append(rssi)
        self.lqi_history.append(lqi)
        self.pdr_history.append(pdr)
        
        # 保持历史记录长度不超过100
        if len(self.rssi_history) > 100:
            self.rssi_history.pop(0)
            self.lqi_history.pop(0)
            self.pdr_history.pop(0)
    
    def get_average_link_quality(self) -> Dict[str, float]:
        """获取平均链路质量"""
        if not self.rssi_history:
            return {'rssi': -85.0, 'lqi': 50, 'pdr': 0.5}
        
        return {
            'rssi': np.mean(self.rssi_history),
            'lqi': np.mean(self.lqi_history),
            'pdr': np.mean(self.pdr_history)
        }

class RealisticEnergyModel:
    """
    基于文献的真实能耗模型
    参考: Heinzelman, W. R., et al. (2000). Energy-efficient communication protocol
    """
    
    def __init__(self):
        # IEEE 802.15.4典型参数 (基于文献)
        self.E_elec = 50e-9      # J/bit, 电路能耗
        self.E_amp_fs = 10e-12   # J/bit/m², 自由空间放大器
        self.E_amp_mp = 0.0013e-12  # J/bit/m⁴, 多径放大器
        self.d_crossover = 87    # m, 交叉距离
        
        # 接收和发送的基础能耗
        self.E_rx = 50e-9        # J/bit, 接收能耗
        self.E_tx_elec = 50e-9   # J/bit, 发送电路能耗
        
    def calculate_transmission_energy(self, data_size_bits: int, distance: float, 
                                    pdr: float = 1.0, max_retries: int = 3) -> float:
        """
        计算传输能耗 (考虑重传)
        
        Args:
            data_size_bits: 数据大小 (bits)
            distance: 传输距离 (m)
            pdr: 包投递率
            max_retries: 最大重传次数
            
        Returns:
            总传输能耗 (J)
        """
        # 基础传输能耗
        if distance < self.d_crossover:
            # 自由空间模型
            E_tx = (self.E_tx_elec + self.E_amp_fs * distance**2) * data_size_bits
        else:
            # 多径模型
            E_tx = (self.E_tx_elec + self.E_amp_mp * distance**4) * data_size_bits
        
        # 考虑重传的期望能耗
        if pdr > 0:
            expected_transmissions = min(max_retries, 1 / pdr)
        else:
            expected_transmissions = max_retries
            
        return E_tx * expected_transmissions
    
    def calculate_reception_energy(self, data_size_bits: int) -> float:
        """计算接收能耗"""
        return self.E_rx * data_size_bits
    
    def calculate_sensing_energy(self, sensing_duration: float = 0.001) -> float:
        """计算感知能耗"""
        # 典型传感器功耗: 1mW
        sensing_power = 1e-3  # W
        return sensing_power * sensing_duration
    
    def calculate_processing_energy(self, operations: int = 1000) -> float:
        """计算处理能耗"""
        # 典型MCU: 1mW @ 8MHz
        energy_per_operation = 1e-9  # J/operation
        return energy_per_operation * operations

class FuzzyLogicClusterHead:
    """
    基于模糊逻辑的簇头选择 (集成环境感知)
    """
    
    def __init__(self):
        self.weight_energy = 0.4      # 能量权重
        self.weight_centrality = 0.3  # 中心性权重
        self.weight_link_quality = 0.3 # 链路质量权重
    
    def calculate_centrality(self, node: WSNNode, neighbors: List[WSNNode]) -> float:
        """计算节点中心性"""
        if not neighbors:
            return 0.0
        
        total_distance = sum(node.distance_to(neighbor) for neighbor in neighbors)
        avg_distance = total_distance / len(neighbors)
        
        # 归一化 (距离越小，中心性越高)
        max_distance = 100.0  # 假设最大通信距离
        centrality = 1.0 - min(avg_distance / max_distance, 1.0)
        
        return centrality
    
    def calculate_link_quality_score(self, node: WSNNode) -> float:
        """计算链路质量得分"""
        avg_quality = node.get_average_link_quality()
        
        # 归一化RSSI (-85 to -20 dBm)
        rssi_normalized = (avg_quality['rssi'] + 85) / 65
        rssi_normalized = max(0, min(1, rssi_normalized))
        
        # 归一化LQI (0 to 255)
        lqi_normalized = avg_quality['lqi'] / 255
        
        # 综合链路质量得分
        link_quality_score = 0.5 * rssi_normalized + 0.3 * lqi_normalized + 0.2 * avg_quality['pdr']
        
        return max(0, min(1, link_quality_score))
    
    def calculate_cluster_head_probability(self, node: WSNNode, neighbors: List[WSNNode]) -> float:
        """计算成为簇头的概率"""
        if not node.is_alive:
            return 0.0
        
        # 能量因子
        energy_factor = node.get_residual_energy_ratio()
        
        # 中心性因子
        centrality_factor = self.calculate_centrality(node, neighbors)
        
        # 链路质量因子
        link_quality_factor = self.calculate_link_quality_score(node)
        
        # 环境适应性因子
        battery_capacity_factor = EnvironmentalFactors.temperature_effect_on_battery(node.temperature)
        
        # 综合概率计算
        probability = (
            self.weight_energy * energy_factor +
            self.weight_centrality * centrality_factor +
            self.weight_link_quality * link_quality_factor
        ) * battery_capacity_factor
        
        return max(0, min(1, probability))

class EnhancedEEHFRRealistic:
    """
    基于真实环境建模的增强型EEHFR协议
    """
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.INDOOR_FACTORY):
        self.environment = environment
        self.channel_model = RealisticChannelModel(environment)
        self.energy_model = RealisticEnergyModel()
        self.fuzzy_ch_selector = FuzzyLogicClusterHead()
        
        # 协议参数
        self.communication_range = 50.0  # m
        self.tx_power_dbm = 0.0         # dBm
        self.packet_size_bits = 2000    # bits
        self.max_retries = 3
        
        # 统计信息
        self.total_energy_consumed = 0.0
        self.total_packets_sent = 0
        self.total_packets_received = 0
        self.round_number = 0
        
        logger.info(f"Enhanced EEHFR initialized with {environment.value} environment")
    
    def add_interference_sources(self, sources: List[Dict]):
        """添加干扰源"""
        for source in sources:
            self.channel_model.interference.add_interference_source(
                source['power'], source['distance'], source['type']
            )
    
    def calculate_link_metrics(self, sender: WSNNode, receiver: WSNNode) -> Dict:
        """计算两节点间的链路指标"""
        distance = sender.distance_to(receiver)
        
        # 使用真实信道模型计算链路指标
        metrics = self.channel_model.calculate_link_metrics(
            tx_power_dbm=self.tx_power_dbm,
            distance=distance,
            temperature_c=sender.temperature,
            humidity_ratio=sender.humidity
        )
        
        return metrics
    
    def can_communicate(self, sender: WSNNode, receiver: WSNNode) -> bool:
        """判断两节点是否可以通信"""
        if not sender.is_alive or not receiver.is_alive:
            return False
        
        distance = sender.distance_to(receiver)
        if distance > self.communication_range:
            return False
        
        # 基于链路质量判断
        metrics = self.calculate_link_metrics(sender, receiver)
        return metrics['pdr'] > 0.1  # 最低PDR阈值
    
    def transmit_packet(self, sender: WSNNode, receiver: WSNNode, 
                       packet_type: str = "data") -> bool:
        """传输数据包"""
        if not self.can_communicate(sender, receiver):
            return False
        
        # 计算链路指标
        metrics = self.calculate_link_metrics(sender, receiver)
        distance = sender.distance_to(receiver)
        
        # 更新节点的链路质量历史
        sender.update_link_quality_history(
            metrics['rssi_dbm'], metrics['lqi'], metrics['pdr']
        )
        
        # 计算传输能耗
        tx_energy = self.energy_model.calculate_transmission_energy(
            self.packet_size_bits, distance, metrics['pdr'], self.max_retries
        )
        
        # 计算接收能耗
        rx_energy = self.energy_model.calculate_reception_energy(self.packet_size_bits)
        
        # 消耗能量
        sender.consume_energy(tx_energy)
        receiver.consume_energy(rx_energy)
        
        # 更新统计信息
        self.total_energy_consumed += (tx_energy + rx_energy)
        self.total_packets_sent += 1
        
        # 基于PDR判断传输是否成功
        success = random.random() < metrics['pdr']
        if success:
            self.total_packets_received += 1
        
        logger.debug(f"Packet transmission from {sender.node_id} to {receiver.node_id}: "
                    f"Success={success}, PDR={metrics['pdr']:.3f}, "
                    f"RSSI={metrics['rssi_dbm']:.1f}dBm, Energy={tx_energy*1e6:.2f}μJ")
        
        return success
    
    def select_cluster_heads(self, nodes: List[WSNNode]) -> List[WSNNode]:
        """选择簇头节点"""
        cluster_heads = []
        
        for node in nodes:
            if not node.is_alive:
                continue
            
            # 获取邻居节点
            neighbors = [n for n in nodes if n != node and self.can_communicate(node, n)]
            
            # 计算成为簇头的概率
            ch_probability = self.fuzzy_ch_selector.calculate_cluster_head_probability(node, neighbors)
            
            # 基于概率决定是否成为簇头
            if random.random() < ch_probability:
                node.is_cluster_head = True
                cluster_heads.append(node)
                logger.debug(f"Node {node.node_id} selected as cluster head "
                           f"(probability={ch_probability:.3f})")
        
        return cluster_heads
    
    def form_clusters(self, nodes: List[WSNNode], cluster_heads: List[WSNNode]):
        """形成簇结构"""
        # 重置所有节点的簇信息
        for node in nodes:
            node.cluster_id = -1
            if not node.is_cluster_head:
                node.is_cluster_head = False
        
        # 为每个非簇头节点分配最佳簇头
        for node in nodes:
            if node.is_cluster_head or not node.is_alive:
                continue
            
            best_ch = None
            best_score = -1
            
            for ch in cluster_heads:
                if not self.can_communicate(node, ch):
                    continue
                
                # 计算链路质量得分
                metrics = self.calculate_link_metrics(node, ch)
                distance = node.distance_to(ch)
                
                # 综合评分 (PDR权重最高，距离次之)
                score = 0.6 * metrics['pdr'] + 0.4 * (1 - distance / self.communication_range)
                
                if score > best_score:
                    best_score = score
                    best_ch = ch
            
            if best_ch:
                node.cluster_id = best_ch.node_id
                logger.debug(f"Node {node.node_id} joined cluster {best_ch.node_id} "
                           f"(score={best_score:.3f})")
    
    def run_round(self, nodes: List[WSNNode]) -> Dict:
        """运行一轮协议"""
        self.round_number += 1
        round_start_energy = sum(node.current_energy for node in nodes if node.is_alive)
        
        logger.info(f"Starting round {self.round_number}")
        
        # 1. 选择簇头
        cluster_heads = self.select_cluster_heads(nodes)
        
        if not cluster_heads:
            logger.warning("No cluster heads selected!")
            return self._get_round_statistics(nodes, round_start_energy)
        
        # 2. 形成簇
        self.form_clusters(nodes, cluster_heads)
        
        # 3. 数据收集阶段
        successful_transmissions = 0
        
        for node in nodes:
            if not node.is_alive or node.is_cluster_head:
                continue
            
            # 找到对应的簇头
            cluster_head = next((ch for ch in cluster_heads if ch.node_id == node.cluster_id), None)
            if cluster_head and cluster_head.is_alive:
                # 感知数据
                sensing_energy = self.energy_model.calculate_sensing_energy()
                node.consume_energy(sensing_energy)
                
                # 发送数据到簇头
                if self.transmit_packet(node, cluster_head, "data"):
                    successful_transmissions += 1
        
        # 4. 簇头向基站发送聚合数据
        base_station = WSNNode(node_id=-1, x=50, y=50)  # 假设基站位置
        
        for ch in cluster_heads:
            if ch.is_alive:
                # 数据聚合处理
                processing_energy = self.energy_model.calculate_processing_energy(1000)
                ch.consume_energy(processing_energy)
                
                # 发送聚合数据到基站
                self.transmit_packet(ch, base_station, "aggregated")
        
        return self._get_round_statistics(nodes, round_start_energy)
    
    def _get_round_statistics(self, nodes: List[WSNNode], round_start_energy: float) -> Dict:
        """获取轮次统计信息"""
        alive_nodes = [node for node in nodes if node.is_alive]
        round_end_energy = sum(node.current_energy for node in alive_nodes)
        
        stats = {
            'round': self.round_number,
            'alive_nodes': len(alive_nodes),
            'total_nodes': len(nodes),
            'energy_consumed_this_round': round_start_energy - round_end_energy,
            'total_energy_consumed': self.total_energy_consumed,
            'remaining_energy': round_end_energy,
            'packets_sent': self.total_packets_sent,
            'packets_received': self.total_packets_received,
            'packet_delivery_ratio': self.total_packets_received / max(self.total_packets_sent, 1),
            'average_rssi': np.mean([np.mean(node.rssi_history) for node in alive_nodes if node.rssi_history]),
            'average_pdr': np.mean([np.mean(node.pdr_history) for node in alive_nodes if node.pdr_history])
        }
        
        logger.info(f"Round {self.round_number} completed: "
                   f"{len(alive_nodes)}/{len(nodes)} nodes alive, "
                   f"PDR={stats['packet_delivery_ratio']:.3f}, "
                   f"Energy consumed={stats['energy_consumed_this_round']:.6f}J")
        
        return stats

# 使用示例
if __name__ == "__main__":
    # 创建工厂环境的Enhanced EEHFR协议
    protocol = EnhancedEEHFRRealistic(EnvironmentType.INDOOR_FACTORY)
    
    # 添加干扰源
    protocol.add_interference_sources([
        {'power': -20, 'distance': 10, 'type': 'wifi'},
        {'power': -15, 'distance': 20, 'type': 'motor'}
    ])
    
    # 创建节点网络
    nodes = []
    for i in range(50):
        x = random.uniform(0, 100)
        y = random.uniform(0, 100)
        # 模拟不同的环境条件
        temperature = random.uniform(20, 40)
        humidity = random.uniform(0.4, 0.9)
        
        node = WSNNode(
            node_id=i, x=x, y=y, 
            temperature=temperature, 
            humidity=humidity
        )
        nodes.append(node)
    
    # 运行仿真
    print("Starting Enhanced EEHFR simulation with realistic environment modeling...")
    
    round_stats = []
    for round_num in range(100):
        stats = protocol.run_round(nodes)
        round_stats.append(stats)
        
        # 如果所有节点都死亡，停止仿真
        if stats['alive_nodes'] == 0:
            print(f"All nodes died at round {round_num}")
            break
    
    # 输出最终统计
    final_stats = round_stats[-1]
    print(f"\nSimulation completed:")
    print(f"  Network lifetime: {len(round_stats)} rounds")
    print(f"  Total energy consumed: {final_stats['total_energy_consumed']:.6f} J")
    print(f"  Average PDR: {final_stats['packet_delivery_ratio']:.3f}")
    print(f"  Final alive nodes: {final_stats['alive_nodes']}/{final_stats['total_nodes']}")
