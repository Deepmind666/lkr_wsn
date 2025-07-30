#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成版Enhanced EEHFR协议 (Integrated Enhanced EEHFR)

基于诚实验证后的项目现状，集成所有优化组件：
1. 改进的能耗模型 (ImprovedEnergyModel)
2. 现实信道模型 (RealisticChannelModel)  
3. 环境感知机制 (EnvironmentClassifier)
4. 模糊逻辑系统 (FuzzyLogicSystem)

目标：创建完整、可靠、高性能的WSN路由协议

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 2.0 (Integrated)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import math
import random
import time
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

# 导入所有优化组件
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform, EnergyParameters
from realistic_channel_model import RealisticChannelModel, EnvironmentType, LogNormalShadowingModel
from benchmark_protocols import Node, NetworkConfig

@dataclass
class EnhancedNode(Node):
    """增强节点类，扩展基础节点功能"""
    
    # 环境感知属性
    environment_type: Optional[EnvironmentType] = None
    rssi_history: List[float] = None
    lqi_history: List[float] = None
    
    # 模糊逻辑决策属性
    fuzzy_score: float = 0.0
    cluster_head_probability: float = 0.0
    
    # 自适应参数
    transmission_power: float = 0.0  # dBm
    retransmission_count: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        if self.rssi_history is None:
            self.rssi_history = []
        if self.lqi_history is None:
            self.lqi_history = []

class EnvironmentClassifier:
    """环境分类器"""
    
    def __init__(self):
        self.classification_history = []
    
    def classify_environment(self, nodes: List[EnhancedNode]) -> EnvironmentType:
        """
        基于节点分布和信号特征自动分类环境
        简化版实现，基于节点密度和区域大小
        """
        
        if not nodes:
            return EnvironmentType.INDOOR_OFFICE
        
        # 计算节点密度
        area = 100 * 100  # 假设100x100区域
        density = len(nodes) / area
        
        # 基于密度简单分类
        if density > 0.01:  # 高密度
            return EnvironmentType.INDOOR_OFFICE
        elif density > 0.005:  # 中密度
            return EnvironmentType.INDOOR_RESIDENTIAL
        else:  # 低密度
            return EnvironmentType.OUTDOOR_OPEN

class FuzzyLogicSystem:
    """模糊逻辑决策系统"""
    
    def __init__(self):
        self.rules = self._initialize_fuzzy_rules()
    
    def _initialize_fuzzy_rules(self) -> Dict:
        """初始化模糊规则"""
        return {
            'cluster_head_selection': {
                'high_energy_high_centrality': 0.9,
                'high_energy_low_centrality': 0.6,
                'low_energy_high_centrality': 0.4,
                'low_energy_low_centrality': 0.1
            }
        }
    
    def calculate_cluster_head_probability(self, node: EnhancedNode, nodes: List[EnhancedNode]) -> float:
        """计算节点成为簇头的概率"""
        
        # 能量因子 (0-1)
        max_energy = max(n.current_energy for n in nodes if n.is_alive)
        energy_factor = node.current_energy / max_energy if max_energy > 0 else 0
        
        # 中心性因子 (基于到其他节点的平均距离)
        distances = []
        for other_node in nodes:
            if other_node.is_alive and other_node.id != node.id:
                dist = math.sqrt((node.x - other_node.x)**2 + (node.y - other_node.y)**2)
                distances.append(dist)
        
        avg_distance = sum(distances) / len(distances) if distances else 0
        max_distance = 100 * math.sqrt(2)  # 对角线距离
        centrality_factor = 1 - (avg_distance / max_distance) if max_distance > 0 else 0
        
        # 模糊逻辑决策
        if energy_factor > 0.7 and centrality_factor > 0.7:
            return self.rules['cluster_head_selection']['high_energy_high_centrality']
        elif energy_factor > 0.7 and centrality_factor <= 0.7:
            return self.rules['cluster_head_selection']['high_energy_low_centrality']
        elif energy_factor <= 0.7 and centrality_factor > 0.7:
            return self.rules['cluster_head_selection']['low_energy_high_centrality']
        else:
            return self.rules['cluster_head_selection']['low_energy_low_centrality']

class IntegratedEnhancedEEHFRProtocol:
    """
    集成版Enhanced EEHFR协议
    整合所有优化组件的完整实现
    """
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        
        # 初始化所有组件
        self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        self.environment_classifier = EnvironmentClassifier()
        self.fuzzy_system = FuzzyLogicSystem()

        # 先进行环境分类，然后初始化信道模型
        self.current_environment = EnvironmentType.INDOOR_OFFICE  # 默认环境
        self.channel_model = None  # 稍后初始化
        
        # 网络状态
        self.nodes: List[EnhancedNode] = []
        self.current_round = 0
        self.current_environment = EnvironmentType.INDOOR_OFFICE
        
        # 统计信息
        self.round_statistics = []
        self.total_energy_consumed = 0.0
        self.total_packets_sent = 0
        self.total_packets_received = 0
        
        # 初始化网络
        self._initialize_network()
    
    def _initialize_network(self):
        """初始化网络节点"""
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            
            node = EnhancedNode(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy,
                is_alive=True,
                is_cluster_head=False,
                cluster_id=-1,
                rssi_history=[],
                lqi_history=[],
                transmission_power=0.0  # dBm, 将根据环境调整
            )
            self.nodes.append(node)
        
        # 环境分类
        self.current_environment = self.environment_classifier.classify_environment(self.nodes)

        # 现在可以初始化信道模型
        from realistic_channel_model import RealisticChannelModel
        self.channel_model = RealisticChannelModel(self.current_environment)

        # 根据环境调整初始参数
        self._adapt_to_environment()
    
    def _adapt_to_environment(self):
        """根据环境类型调整协议参数"""
        
        # 根据环境类型设置传输功率
        power_settings = {
            EnvironmentType.INDOOR_OFFICE: -5.0,      # 低功率
            EnvironmentType.INDOOR_RESIDENTIAL: -3.0,  # 中低功率
            EnvironmentType.INDOOR_FACTORY: 0.0,      # 中功率
            EnvironmentType.OUTDOOR_OPEN: 3.0,        # 中高功率
            EnvironmentType.OUTDOOR_SUBURBAN: 5.0,    # 高功率
            EnvironmentType.OUTDOOR_URBAN: 8.0        # 最高功率
        }
        
        default_power = power_settings.get(self.current_environment, 0.0)
        
        for node in self.nodes:
            if node.is_alive:
                node.transmission_power = default_power
                node.environment_type = self.current_environment
    
    def _select_cluster_heads(self):
        """使用模糊逻辑选择簇头"""
        
        # 重置所有节点的簇头状态
        for node in self.nodes:
            node.is_cluster_head = False
            node.cluster_id = -1
        
        # 计算每个节点的簇头概率
        alive_nodes = [node for node in self.nodes if node.is_alive]
        
        for node in alive_nodes:
            node.cluster_head_probability = self.fuzzy_system.calculate_cluster_head_probability(
                node, alive_nodes
            )
        
        # 基于概率选择簇头
        target_cluster_heads = max(1, int(len(alive_nodes) * 0.1))  # 10%的节点作为簇头
        
        # 按概率排序，选择前N个作为簇头
        sorted_nodes = sorted(alive_nodes, key=lambda n: n.cluster_head_probability, reverse=True)
        
        for i in range(min(target_cluster_heads, len(sorted_nodes))):
            sorted_nodes[i].is_cluster_head = True
            sorted_nodes[i].cluster_id = i
    
    def _form_clusters(self):
        """形成簇结构"""
        
        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]
        member_nodes = [node for node in self.nodes if not node.is_cluster_head and node.is_alive]
        
        # 为每个成员节点分配最近的簇头
        for member in member_nodes:
            if not cluster_heads:
                continue
                
            # 找到最近的簇头
            min_distance = float('inf')
            best_cluster_head = None
            
            for ch in cluster_heads:
                distance = math.sqrt((member.x - ch.x)**2 + (member.y - ch.y)**2)
                if distance < min_distance:
                    min_distance = distance
                    best_cluster_head = ch
            
            if best_cluster_head:
                member.cluster_id = best_cluster_head.cluster_id
    
    def _perform_data_transmission(self):
        """执行数据传输"""
        
        packets_sent = 0
        packets_received = 0
        energy_consumed = 0.0
        
        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]
        
        # 簇内数据收集
        for ch in cluster_heads:
            cluster_members = [node for node in self.nodes 
                             if node.cluster_id == ch.cluster_id and not node.is_cluster_head and node.is_alive]
            
            # 成员节点向簇头发送数据
            for member in cluster_members:
                if member.current_energy > 0:
                    # 计算传输距离
                    distance = math.sqrt((member.x - ch.x)**2 + (member.y - ch.y)**2)
                    
                    # 使用改进的能耗模型计算能耗 (packet_size从bytes转换为bits)
                    tx_energy = self.energy_model.calculate_transmission_energy(
                        self.config.packet_size * 8, distance, member.transmission_power
                    )

                    rx_energy = self.energy_model.calculate_reception_energy(self.config.packet_size * 8)
                    
                    # 更新能耗
                    member.current_energy -= tx_energy
                    ch.current_energy -= rx_energy
                    
                    energy_consumed += tx_energy + rx_energy
                    packets_sent += 1
                    
                    # 使用信道模型计算成功率
                    link_metrics = self.channel_model.calculate_link_metrics(
                        member.transmission_power, distance
                    )
                    success_rate = link_metrics['pdr']
                    
                    if random.random() < success_rate:
                        packets_received += 1
        
        # 簇头向基站发送数据
        for ch in cluster_heads:
            if ch.current_energy > 0:
                # 计算到基站的距离
                distance_to_bs = math.sqrt(
                    (ch.x - self.config.base_station_x)**2 + 
                    (ch.y - self.config.base_station_y)**2
                )
                
                # 计算传输能耗 (packet_size从bytes转换为bits)
                tx_energy = self.energy_model.calculate_transmission_energy(
                    self.config.packet_size * 8, distance_to_bs, ch.transmission_power
                )
                
                ch.current_energy -= tx_energy
                energy_consumed += tx_energy
                packets_sent += 1
                
                # 计算成功率
                link_metrics = self.channel_model.calculate_link_metrics(
                    ch.transmission_power, distance_to_bs
                )
                success_rate = link_metrics['pdr']
                
                if random.random() < success_rate:
                    packets_received += 1
        
        # 更新统计信息
        self.total_energy_consumed += energy_consumed
        self.total_packets_sent += packets_sent
        self.total_packets_received += packets_received
        
        return packets_sent, packets_received, energy_consumed
    
    def _update_node_status(self):
        """更新节点状态"""
        for node in self.nodes:
            if node.current_energy <= 0:
                node.is_alive = False
                node.is_cluster_head = False
    
    def _collect_round_statistics(self, round_num: int, packets_sent: int, 
                                packets_received: int, energy_consumed: float):
        """收集轮次统计信息"""
        
        alive_nodes = sum(1 for node in self.nodes if node.is_alive)
        cluster_heads = sum(1 for node in self.nodes if node.is_cluster_head and node.is_alive)
        remaining_energy = sum(node.current_energy for node in self.nodes if node.is_alive)
        
        round_stats = {
            'round': round_num,
            'alive_nodes': alive_nodes,
            'cluster_heads': cluster_heads,
            'remaining_energy': remaining_energy,
            'packets_sent': packets_sent,
            'packets_received': packets_received,
            'energy_consumed': energy_consumed,
            'pdr': packets_received / packets_sent if packets_sent > 0 else 0
        }
        
        self.round_statistics.append(round_stats)
    
    def run_simulation(self, max_rounds: int) -> Dict[str, Any]:
        """运行Enhanced EEHFR仿真"""
        
        print(f"🚀 开始Integrated Enhanced EEHFR协议仿真 (最大轮数: {max_rounds})")
        print(f"   环境类型: {self.current_environment.value}")
        print(f"   节点数量: {len(self.nodes)}")
        
        start_time = time.time()
        
        for round_num in range(max_rounds):
            # 检查是否还有存活节点
            alive_nodes = [node for node in self.nodes if node.is_alive]
            if not alive_nodes:
                print(f"💀 网络在第 {round_num} 轮结束生命周期")
                break
            
            # 选择簇头
            self._select_cluster_heads()
            
            # 形成簇
            self._form_clusters()
            
            # 数据传输
            packets_sent, packets_received, energy_consumed = self._perform_data_transmission()
            
            # 更新节点状态
            self._update_node_status()
            
            # 收集统计信息
            self._collect_round_statistics(round_num, packets_sent, packets_received, energy_consumed)
            
            # 定期输出进度
            if round_num % 100 == 0:
                remaining_energy = sum(node.current_energy for node in self.nodes if node.is_alive)
                print(f"   轮数 {round_num}: 存活节点 {len(alive_nodes)}, 剩余能量 {remaining_energy:.3f}J")
        
        execution_time = time.time() - start_time
        
        # 生成最终结果
        final_alive_nodes = sum(1 for node in self.nodes if node.is_alive)
        network_lifetime = len(self.round_statistics)
        
        if self.total_packets_sent > 0:
            energy_efficiency = self.total_packets_received / self.total_energy_consumed
            packet_delivery_ratio = self.total_packets_received / self.total_packets_sent
        else:
            energy_efficiency = 0
            packet_delivery_ratio = 0
        
        print(f"✅ 仿真完成，网络在 {network_lifetime} 轮后结束")
        
        return {
            'protocol': 'Integrated_Enhanced_EEHFR',
            'network_lifetime': network_lifetime,
            'total_energy_consumed': self.total_energy_consumed,
            'final_alive_nodes': final_alive_nodes,
            'energy_efficiency': energy_efficiency,
            'packet_delivery_ratio': packet_delivery_ratio,
            'execution_time': execution_time,
            'environment_type': self.current_environment.value,
            'round_statistics': self.round_statistics,
            'additional_metrics': {
                'total_packets_sent': self.total_packets_sent,
                'total_packets_received': self.total_packets_received,
                'average_cluster_heads': sum(stats['cluster_heads'] for stats in self.round_statistics) / len(self.round_statistics) if self.round_statistics else 0
            }
        }
