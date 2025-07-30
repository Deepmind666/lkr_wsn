#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境感知Enhanced EEHFR协议 (Environment-Aware Enhanced EEHFR)

核心创新:
1. 集成现实环境建模框架，实现环境感知路由
2. 基于RSSI/LQI的动态链路质量评估
3. 环境自适应的簇头选择和参数优化
4. 多环境场景下的智能路由决策

技术特色:
- 实时环境识别与分类 (6种标准环境)
- 动态发射功率调整机制
- 自适应重传和路由更新策略
- 基于现实信道模型的性能预测

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0 (Environment-Aware)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import math
import random
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

# 导入现实环境建模模块
from realistic_channel_model import (
    RealisticChannelModel,
    EnvironmentType,
    LogNormalShadowingModel,
    IEEE802154LinkQuality
)

# 导入基础Enhanced EEHFR协议
from enhanced_eehfr_protocol import EnhancedNode, EnhancedEEHFR

@dataclass
class EnvironmentMetrics:
    """环境性能指标"""
    avg_rssi: float
    avg_lqi: float
    avg_pdr: float
    avg_sinr: float
    communication_range: float
    reliability_score: float
    environment_type: EnvironmentType

class EnvironmentClassifier:
    """环境分类器 - 基于链路质量指标自动识别环境类型"""
    
    def __init__(self):
        # 基于实验数据的环境特征阈值
        self.environment_thresholds = {
            EnvironmentType.INDOOR_RESIDENTIAL: {
                'rssi_range': (-70, -50),
                'pdr_threshold': 0.90,
                'reliability_min': 95.0
            },
            EnvironmentType.OUTDOOR_OPEN: {
                'rssi_range': (-65, -50),
                'pdr_threshold': 0.90,
                'reliability_min': 95.0
            },
            EnvironmentType.INDOOR_OFFICE: {
                'rssi_range': (-75, -55),
                'pdr_threshold': 0.80,
                'reliability_min': 90.0
            },
            EnvironmentType.OUTDOOR_SUBURBAN: {
                'rssi_range': (-85, -65),
                'pdr_threshold': 0.50,
                'reliability_min': 75.0
            },
            EnvironmentType.INDOOR_FACTORY: {
                'rssi_range': (-90, -70),
                'pdr_threshold': 0.35,
                'reliability_min': 25.0
            },
            EnvironmentType.OUTDOOR_URBAN: {
                'rssi_range': (-100, -80),
                'pdr_threshold': 0.25,
                'reliability_min': 10.0
            }
        }
    
    def classify_environment(self, metrics: Dict) -> EnvironmentType:
        """基于链路质量指标分类环境类型"""
        avg_rssi = metrics.get('avg_rssi', -80)
        avg_pdr = metrics.get('avg_pdr', 0.5)
        reliability = metrics.get('reliability_score', 50.0)
        
        # 按优先级匹配环境类型
        for env_type, thresholds in self.environment_thresholds.items():
            rssi_min, rssi_max = thresholds['rssi_range']
            
            if (rssi_min <= avg_rssi <= rssi_max and 
                avg_pdr >= thresholds['pdr_threshold'] and
                reliability >= thresholds['reliability_min']):
                return env_type
        
        # 默认返回最接近的环境类型
        return self._find_closest_environment(avg_rssi, avg_pdr, reliability)
    
    def _find_closest_environment(self, rssi: float, pdr: float, reliability: float) -> EnvironmentType:
        """找到最接近的环境类型"""
        min_distance = float('inf')
        closest_env = EnvironmentType.INDOOR_OFFICE
        
        for env_type, thresholds in self.environment_thresholds.items():
            rssi_center = sum(thresholds['rssi_range']) / 2
            distance = (abs(rssi - rssi_center) + 
                       abs(pdr - thresholds['pdr_threshold']) * 100 +
                       abs(reliability - thresholds['reliability_min']))
            
            if distance < min_distance:
                min_distance = distance
                closest_env = env_type
        
        return closest_env

class EnvironmentAwareEEHFR(EnhancedEEHFR):
    """环境感知的Enhanced EEHFR协议"""
    
    def __init__(self, nodes: List[EnhancedNode], base_station: Tuple[float, float],
                 initial_environment: EnvironmentType = EnvironmentType.INDOOR_OFFICE,
                 cluster_ratio: float = 0.05, chain_enabled: bool = True):
        """
        初始化环境感知EEHFR协议
        
        Args:
            nodes: 传感器节点列表
            base_station: 基站位置
            initial_environment: 初始环境类型
            cluster_ratio: 簇头比例
            chain_enabled: 是否启用链式结构
        """
        # 调用父类初始化
        super().__init__(nodes, base_station, cluster_ratio, chain_enabled)
        
        # 环境感知模块
        self.current_environment = initial_environment
        self.channel_model = RealisticChannelModel(initial_environment)
        self.environment_classifier = EnvironmentClassifier()
        
        # 环境自适应参数
        self.adaptive_tx_power = 0.0  # dBm
        self.adaptive_retransmission_limit = 3
        self.adaptive_update_frequency = 10  # rounds
        
        # 性能监控
        self.environment_history = []
        self.link_quality_history = []
        self.performance_metrics = {}
        
        # 初始化环境参数
        self._initialize_environment_parameters()
    
    def _initialize_environment_parameters(self):
        """根据环境类型初始化自适应参数"""
        env_params = {
            EnvironmentType.INDOOR_RESIDENTIAL: {
                'tx_power': -5.0, 'retrans_limit': 2, 'update_freq': 15
            },
            EnvironmentType.OUTDOOR_OPEN: {
                'tx_power': -3.0, 'retrans_limit': 2, 'update_freq': 15
            },
            EnvironmentType.INDOOR_OFFICE: {
                'tx_power': 0.0, 'retrans_limit': 3, 'update_freq': 10
            },
            EnvironmentType.OUTDOOR_SUBURBAN: {
                'tx_power': 2.0, 'retrans_limit': 4, 'update_freq': 8
            },
            EnvironmentType.INDOOR_FACTORY: {
                'tx_power': 5.0, 'retrans_limit': 5, 'update_freq': 5
            },
            EnvironmentType.OUTDOOR_URBAN: {
                'tx_power': 8.0, 'retrans_limit': 6, 'update_freq': 5
            }
        }
        
        params = env_params.get(self.current_environment, env_params[EnvironmentType.INDOOR_OFFICE])
        self.adaptive_tx_power = params['tx_power']
        self.adaptive_retransmission_limit = params['retrans_limit']
        self.adaptive_update_frequency = params['update_freq']
    
    def update_environment_awareness(self, round_num: int):
        """更新环境感知信息"""
        if round_num % self.adaptive_update_frequency == 0:
            # 收集当前链路质量数据
            link_metrics = self._collect_link_quality_metrics()
            
            # 环境分类
            detected_env = self.environment_classifier.classify_environment(link_metrics)
            
            # 环境变化检测
            if detected_env != self.current_environment:
                print(f"🌍 环境变化检测: {self.current_environment.value} → {detected_env.value}")
                self._adapt_to_environment_change(detected_env)
            
            # 记录环境历史
            self.environment_history.append({
                'round': round_num,
                'environment': detected_env.value,
                'metrics': link_metrics
            })
    
    def _collect_link_quality_metrics(self) -> Dict:
        """收集当前网络的链路质量指标"""
        rssi_values = []
        lqi_values = []
        pdr_values = []
        
        alive_nodes = [node for node in self.nodes if node.is_alive]
        
        for node in alive_nodes:
            for neighbor in node.neighbors:
                if neighbor.is_alive:
                    # 计算节点间距离
                    distance = math.sqrt((node.x - neighbor.x)**2 + (node.y - neighbor.y)**2)
                    
                    # 使用现实信道模型计算链路指标
                    metrics = self.channel_model.calculate_link_metrics(
                        tx_power_dbm=self.adaptive_tx_power,
                        distance=distance,
                        temperature_c=25.0,
                        humidity_ratio=0.5
                    )
                    
                    rssi_values.append(metrics['rssi_dbm'])
                    lqi_values.append(metrics['lqi'])
                    pdr_values.append(metrics['pdr'])
        
        if not rssi_values:
            return {'avg_rssi': -80, 'avg_lqi': 50, 'avg_pdr': 0.5, 'reliability_score': 50.0}
        
        # 计算平均值和可靠性评分
        avg_rssi = np.mean(rssi_values)
        avg_lqi = np.mean(lqi_values)
        avg_pdr = np.mean(pdr_values)
        reliability_score = avg_pdr * 50 + min(50, max(0, (avg_rssi + 80) / 2 * 50))
        
        return {
            'avg_rssi': avg_rssi,
            'avg_lqi': avg_lqi,
            'avg_pdr': avg_pdr,
            'reliability_score': reliability_score
        }
    
    def _adapt_to_environment_change(self, new_environment: EnvironmentType):
        """适应环境变化"""
        self.current_environment = new_environment
        self.channel_model = RealisticChannelModel(new_environment)
        self._initialize_environment_parameters()
        
        print(f"🔧 环境自适应调整:")
        print(f"   发射功率: {self.adaptive_tx_power} dBm")
        print(f"   重传限制: {self.adaptive_retransmission_limit}")
        print(f"   更新频率: {self.adaptive_update_frequency} rounds")
    
    def enhanced_cluster_head_selection(self):
        """环境感知的簇头选择"""
        # 调用父类的分簇方法
        super().enhanced_fuzzy_clustering()

        # 基于环境特征进行簇头质量评估和调整
        if hasattr(self, 'cluster_heads') and self.cluster_heads:
            adjusted_cluster_heads = []

            for ch in self.cluster_heads:
                # 评估簇头在当前环境下的适应性
                adaptability_score = self._evaluate_cluster_head_adaptability(ch)

                if adaptability_score > 0.6:  # 适应性阈值
                    adjusted_cluster_heads.append(ch)
                else:
                    # 寻找更适合的替代簇头
                    alternative = self._find_alternative_cluster_head(ch)
                    if alternative:
                        # 更新簇头状态
                        ch.is_cluster_head = False
                        alternative.is_cluster_head = True
                        adjusted_cluster_heads.append(alternative)
                    else:
                        adjusted_cluster_heads.append(ch)  # 保留原簇头

            self.cluster_heads = adjusted_cluster_heads
    
    def _evaluate_cluster_head_adaptability(self, cluster_head: EnhancedNode) -> float:
        """评估簇头在当前环境下的适应性"""
        # 基于环境特征计算适应性评分
        base_score = cluster_head.residual_energy_ratio * 0.4
        
        # 考虑环境因素
        if self.current_environment in [EnvironmentType.INDOOR_FACTORY, EnvironmentType.OUTDOOR_URBAN]:
            # 恶劣环境下更重视能量和位置
            location_score = self._calculate_location_advantage(cluster_head) * 0.4
            energy_score = cluster_head.current_energy / cluster_head.initial_energy * 0.2
        else:
            # 良好环境下平衡各因素
            location_score = self._calculate_location_advantage(cluster_head) * 0.3
            energy_score = cluster_head.current_energy / cluster_head.initial_energy * 0.3
        
        return base_score + location_score + energy_score
    
    def _calculate_location_advantage(self, node: EnhancedNode) -> float:
        """计算节点位置优势"""
        # 计算到基站距离
        bs_distance = math.sqrt((node.x - self.base_station[0])**2 + 
                               (node.y - self.base_station[1])**2)
        
        # 计算到网络中心的距离
        center_x = np.mean([n.x for n in self.nodes if n.is_alive])
        center_y = np.mean([n.y for n in self.nodes if n.is_alive])
        center_distance = math.sqrt((node.x - center_x)**2 + (node.y - center_y)**2)
        
        # 综合位置评分 (距离基站近且位于网络中心附近更好)
        max_distance = max(bs_distance, center_distance, 1.0)
        location_score = 1.0 - (bs_distance + center_distance) / (2 * max_distance)
        
        return max(0.0, location_score)
    
    def _find_alternative_cluster_head(self, original_ch: EnhancedNode) -> Optional[EnhancedNode]:
        """寻找替代簇头"""
        candidates = [node for node in self.nodes 
                     if node.is_alive and not node.is_cluster_head and 
                     node.current_energy > 0.1]
        
        if not candidates:
            return None
        
        best_candidate = None
        best_score = 0.0
        
        for candidate in candidates:
            score = self._evaluate_cluster_head_adaptability(candidate)
            if score > best_score:
                best_score = score
                best_candidate = candidate
        
        return best_candidate if best_score > 0.7 else None

    def environment_aware_data_transmission(self, source: EnhancedNode,
                                          destination: EnhancedNode,
                                          data_size: float) -> Dict:
        """环境感知的数据传输"""
        # 计算传输距离
        distance = math.sqrt((source.x - destination.x)**2 +
                           (source.y - destination.y)**2)

        # 使用现实信道模型评估链路质量
        link_metrics = self.channel_model.calculate_link_metrics(
            tx_power_dbm=self.adaptive_tx_power,
            distance=distance,
            temperature_c=25.0,
            humidity_ratio=0.5
        )

        # 基于链路质量决定传输策略
        transmission_result = {
            'success': False,
            'energy_consumed': 0.0,
            'transmission_attempts': 0,
            'link_quality': link_metrics
        }

        # 自适应重传机制
        max_attempts = self.adaptive_retransmission_limit
        pdr = link_metrics['pdr']

        for attempt in range(1, max_attempts + 1):
            transmission_result['transmission_attempts'] = attempt

            # 计算传输能耗 (考虑发射功率)
            tx_power_linear = 10**(self.adaptive_tx_power / 10) / 1000  # 转换为瓦特
            energy_per_bit = tx_power_linear * 1e-6  # 假设每bit传输时间1μs
            attempt_energy = data_size * energy_per_bit

            transmission_result['energy_consumed'] += attempt_energy

            # 基于PDR判断传输是否成功
            if random.random() < pdr:
                transmission_result['success'] = True
                break

            # 传输失败，准备重传
            if attempt < max_attempts:
                # 动态调整发射功率 (在恶劣环境下)
                if self.current_environment in [EnvironmentType.INDOOR_FACTORY,
                                              EnvironmentType.OUTDOOR_URBAN]:
                    self.adaptive_tx_power = min(self.adaptive_tx_power + 1.0, 10.0)

        # 更新节点能量
        source.current_energy -= transmission_result['energy_consumed']
        if source.current_energy <= 0:
            source.current_energy = 0
            source.is_alive = False

        return transmission_result

    def run_environment_aware_protocol(self, max_rounds: int = 1000) -> Dict:
        """运行环境感知的EEHFR协议"""
        print(f"🚀 启动环境感知Enhanced EEHFR协议")
        print(f"   初始环境: {self.current_environment.value}")
        print(f"   节点数量: {len(self.nodes)}")
        print(f"   最大轮数: {max_rounds}")
        print("=" * 60)

        # 协议运行统计
        protocol_stats = {
            'rounds_completed': 0,
            'total_energy_consumed': 0.0,
            'total_data_transmitted': 0.0,
            'successful_transmissions': 0,
            'failed_transmissions': 0,
            'environment_changes': 0,
            'alive_nodes_history': [],
            'energy_history': [],
            'environment_history': []
        }

        for round_num in range(1, max_rounds + 1):
            # 检查网络存活性
            alive_nodes = [node for node in self.nodes if node.is_alive]
            if len(alive_nodes) < 2:
                print(f"⚠️  网络失效 (存活节点 < 2) - 轮次 {round_num}")
                break

            # 环境感知更新
            self.update_environment_awareness(round_num)

            # 簇头选择 (环境感知)
            cluster_heads = self.enhanced_cluster_head_selection()

            # 簇形成
            self.form_clusters(cluster_heads)

            # 数据收集和传输
            round_energy = 0.0
            round_transmissions = 0
            round_successes = 0

            # 簇内数据收集
            for cluster_head in cluster_heads:
                cluster_members = [node for node in self.nodes
                                 if node.cluster_id == cluster_head.node_id and
                                 node != cluster_head and node.is_alive]

                for member in cluster_members:
                    # 环境感知的数据传输
                    result = self.environment_aware_data_transmission(
                        member, cluster_head, data_size=1024  # 1KB数据包
                    )

                    round_energy += result['energy_consumed']
                    round_transmissions += result['transmission_attempts']
                    if result['success']:
                        round_successes += 1

            # 簇头到基站的数据传输
            for cluster_head in cluster_heads:
                # 创建虚拟基站节点用于传输计算
                bs_node = EnhancedNode(-1, self.base_station[0], self.base_station[1])

                result = self.environment_aware_data_transmission(
                    cluster_head, bs_node, data_size=2048  # 2KB聚合数据
                )

                round_energy += result['energy_consumed']
                round_transmissions += result['transmission_attempts']
                if result['success']:
                    round_successes += 1

            # 更新统计信息
            protocol_stats['rounds_completed'] = round_num
            protocol_stats['total_energy_consumed'] += round_energy
            protocol_stats['successful_transmissions'] += round_successes
            protocol_stats['failed_transmissions'] += (round_transmissions - round_successes)

            # 记录历史数据
            protocol_stats['alive_nodes_history'].append(len(alive_nodes))
            protocol_stats['energy_history'].append(
                sum(node.current_energy for node in alive_nodes)
            )
            protocol_stats['environment_history'].append(self.current_environment.value)

            # 周期性输出进展
            if round_num % 100 == 0 or round_num <= 10:
                print(f"轮次 {round_num:4d}: 存活节点 {len(alive_nodes):3d}, "
                      f"环境 {self.current_environment.value:15s}, "
                      f"能耗 {round_energy:.4f}J, "
                      f"成功率 {round_successes/max(round_transmissions,1)*100:.1f}%")

        # 计算最终性能指标
        final_alive_nodes = len([node for node in self.nodes if node.is_alive])

        protocol_stats.update({
            'network_lifetime': protocol_stats['rounds_completed'],
            'energy_efficiency': protocol_stats['total_data_transmitted'] /
                               max(protocol_stats['total_energy_consumed'], 0.001),
            'final_alive_nodes': final_alive_nodes,
            'survival_rate': final_alive_nodes / len(self.nodes),
            'transmission_success_rate': protocol_stats['successful_transmissions'] /
                                       max(protocol_stats['successful_transmissions'] +
                                           protocol_stats['failed_transmissions'], 1)
        })

        print("\n" + "=" * 60)
        print("🏁 协议运行完成")
        print(f"   网络生存时间: {protocol_stats['network_lifetime']} 轮")
        print(f"   总能耗: {protocol_stats['total_energy_consumed']:.4f} J")
        print(f"   存活节点: {final_alive_nodes}/{len(self.nodes)}")
        print(f"   传输成功率: {protocol_stats['transmission_success_rate']*100:.2f}%")

        return protocol_stats

    def get_environment_analysis(self) -> Dict:
        """获取环境分析报告"""
        if not self.environment_history:
            return {}

        # 统计环境分布
        env_distribution = {}
        for record in self.environment_history:
            env = record['environment']
            env_distribution[env] = env_distribution.get(env, 0) + 1

        # 计算环境稳定性
        env_changes = 0
        prev_env = self.environment_history[0]['environment']
        for record in self.environment_history[1:]:
            if record['environment'] != prev_env:
                env_changes += 1
                prev_env = record['environment']

        return {
            'environment_distribution': env_distribution,
            'environment_changes': env_changes,
            'environment_stability': 1.0 - (env_changes / max(len(self.environment_history), 1)),
            'dominant_environment': max(env_distribution.items(), key=lambda x: x[1])[0],
            'total_monitoring_rounds': len(self.environment_history)
        }

    def environment_aware_data_transmission(self, source: EnhancedNode,
                                          destination: EnhancedNode,
                                          data_size: float) -> Dict:
        """环境感知的数据传输"""
        # 计算传输距离
        distance = math.sqrt((source.x - destination.x)**2 +
                           (source.y - destination.y)**2)

        # 使用现实信道模型评估链路质量
        link_metrics = self.channel_model.calculate_link_metrics(
            tx_power_dbm=self.adaptive_tx_power,
            distance=distance,
            temperature_c=25.0,
            humidity_ratio=0.5
        )

        # 基于链路质量决定传输策略
        transmission_result = {
            'success': False,
            'energy_consumed': 0.0,
            'transmission_attempts': 0,
            'link_quality': link_metrics
        }

        # 自适应重传机制
        max_attempts = self.adaptive_retransmission_limit
        pdr = link_metrics['pdr']

        for attempt in range(1, max_attempts + 1):
            transmission_result['transmission_attempts'] = attempt

            # 计算传输能耗 (考虑发射功率)
            tx_power_linear = 10**(self.adaptive_tx_power / 10) / 1000  # 转换为瓦特
            energy_per_bit = tx_power_linear * 1e-6  # 假设每bit传输时间1μs
            attempt_energy = data_size * energy_per_bit

            transmission_result['energy_consumed'] += attempt_energy

            # 基于PDR判断传输是否成功
            if random.random() < pdr:
                transmission_result['success'] = True
                break

            # 传输失败，准备重传
            if attempt < max_attempts:
                # 动态调整发射功率 (在恶劣环境下)
                if self.current_environment in [EnvironmentType.INDOOR_FACTORY,
                                              EnvironmentType.OUTDOOR_URBAN]:
                    self.adaptive_tx_power = min(self.adaptive_tx_power + 1.0, 10.0)

        # 更新节点能量
        source.current_energy -= transmission_result['energy_consumed']
        if source.current_energy <= 0:
            source.current_energy = 0
            source.is_alive = False

        return transmission_result

    def run_environment_aware_protocol(self, max_rounds: int = 1000) -> Dict:
        """运行环境感知的EEHFR协议"""
        print(f"🚀 启动环境感知Enhanced EEHFR协议")
        print(f"   初始环境: {self.current_environment.value}")
        print(f"   节点数量: {len(self.nodes)}")
        print(f"   最大轮数: {max_rounds}")
        print("=" * 60)

        # 协议运行统计
        protocol_stats = {
            'rounds_completed': 0,
            'total_energy_consumed': 0.0,
            'total_data_transmitted': 0.0,
            'successful_transmissions': 0,
            'failed_transmissions': 0,
            'environment_changes': 0,
            'alive_nodes_history': [],
            'energy_history': [],
            'environment_history': []
        }

        for round_num in range(1, max_rounds + 1):
            # 检查网络存活性
            alive_nodes = [node for node in self.nodes if node.is_alive]
            if len(alive_nodes) < 2:
                print(f"⚠️  网络失效 (存活节点 < 2) - 轮次 {round_num}")
                break

            # 环境感知更新
            self.update_environment_awareness(round_num)

            # 簇头选择 (环境感知)
            self.enhanced_cluster_head_selection()

            # 数据收集和传输
            round_energy = 0.0
            round_transmissions = 0
            round_successes = 0

            # 簇内数据收集
            if hasattr(self, 'cluster_heads') and self.cluster_heads:
                for cluster_head in self.cluster_heads:
                    cluster_members = [node for node in self.nodes
                                     if node.cluster_id == cluster_head.node_id and
                                     node != cluster_head and node.is_alive]

                    for member in cluster_members:
                        # 环境感知的数据传输
                        result = self.environment_aware_data_transmission(
                            member, cluster_head, data_size=1024  # 1KB数据包
                        )

                        round_energy += result['energy_consumed']
                        round_transmissions += result['transmission_attempts']
                        if result['success']:
                            round_successes += 1

                # 簇头到基站的数据传输
                for cluster_head in self.cluster_heads:
                    # 创建虚拟基站节点用于传输计算
                    bs_node = EnhancedNode(-1, self.base_station[0], self.base_station[1])

                    result = self.environment_aware_data_transmission(
                        cluster_head, bs_node, data_size=2048  # 2KB聚合数据
                    )

                    round_energy += result['energy_consumed']
                    round_transmissions += result['transmission_attempts']
                    if result['success']:
                        round_successes += 1

            # 更新统计信息
            protocol_stats['rounds_completed'] = round_num
            protocol_stats['total_energy_consumed'] += round_energy
            protocol_stats['successful_transmissions'] += round_successes
            protocol_stats['failed_transmissions'] += (round_transmissions - round_successes)

            # 记录历史数据
            protocol_stats['alive_nodes_history'].append(len(alive_nodes))
            protocol_stats['energy_history'].append(
                sum(node.current_energy for node in alive_nodes)
            )
            protocol_stats['environment_history'].append(self.current_environment.value)

            # 周期性输出进展
            if round_num % 100 == 0 or round_num <= 10:
                print(f"轮次 {round_num:4d}: 存活节点 {len(alive_nodes):3d}, "
                      f"环境 {self.current_environment.value:15s}, "
                      f"能耗 {round_energy:.4f}J, "
                      f"成功率 {round_successes/max(round_transmissions,1)*100:.1f}%")

        # 计算最终性能指标
        total_initial_energy = sum(node.initial_energy for node in self.nodes)
        final_alive_nodes = len([node for node in self.nodes if node.is_alive])

        protocol_stats.update({
            'network_lifetime': protocol_stats['rounds_completed'],
            'energy_efficiency': protocol_stats['total_data_transmitted'] /
                               max(protocol_stats['total_energy_consumed'], 0.001),
            'final_alive_nodes': final_alive_nodes,
            'survival_rate': final_alive_nodes / len(self.nodes),
            'transmission_success_rate': protocol_stats['successful_transmissions'] /
                                       max(protocol_stats['successful_transmissions'] +
                                           protocol_stats['failed_transmissions'], 1)
        })

        print("\n" + "=" * 60)
        print("🏁 协议运行完成")
        print(f"   网络生存时间: {protocol_stats['network_lifetime']} 轮")
        print(f"   总能耗: {protocol_stats['total_energy_consumed']:.4f} J")
        print(f"   存活节点: {final_alive_nodes}/{len(self.nodes)}")
        print(f"   传输成功率: {protocol_stats['transmission_success_rate']*100:.2f}%")

        return protocol_stats

    def get_environment_analysis(self) -> Dict:
        """获取环境分析报告"""
        if not self.environment_history:
            return {}

        # 统计环境分布
        env_distribution = {}
        for record in self.environment_history:
            env = record['environment']
            env_distribution[env] = env_distribution.get(env, 0) + 1

        # 计算环境稳定性
        env_changes = 0
        prev_env = self.environment_history[0]['environment']
        for record in self.environment_history[1:]:
            if record['environment'] != prev_env:
                env_changes += 1
                prev_env = record['environment']

        return {
            'environment_distribution': env_distribution,
            'environment_changes': env_changes,
            'environment_stability': 1.0 - (env_changes / max(len(self.environment_history), 1)),
            'dominant_environment': max(env_distribution.items(), key=lambda x: x[1])[0],
            'total_monitoring_rounds': len(self.environment_history)
        }
