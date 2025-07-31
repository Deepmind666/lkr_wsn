#!/usr/bin/env python3
"""
自适应可靠性增强EEHFR协议

核心创新:
1. 智能可靠性等级调整 - 基于网络状态动态选择传输策略
2. 能效-可靠性平衡优化 - 多目标优化算法
3. 预测性故障检测 - 基于历史数据预测网络状态
4. 自适应阈值调整 - 根据网络演化动态调整决策阈值

设计原则:
- 只在必要时启用高成本可靠性机制
- 基于第一性原理的能量-可靠性权衡
- 使用控制变量法验证每个机制的有效性
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import math

from benchmark_protocols import NetworkConfig
from improved_energy_model import ImprovedEnergyModel
from enhanced_eehfr_2_0_redesigned import EnhancedEEHFR2Protocol, EnhancedEEHFR2Config, EnhancedNode


class ReliabilityLevel(Enum):
    """可靠性等级"""
    MINIMAL = "minimal"      # 最小可靠性 - 直接传输
    STANDARD = "standard"    # 标准可靠性 - 单路径重传
    ENHANCED = "enhanced"    # 增强可靠性 - 双路径传输
    CRITICAL = "critical"    # 关键可靠性 - 多路径+协作传输


class NetworkCondition(Enum):
    """网络状况"""
    EXCELLENT = "excellent"  # 优秀 - PDR>95%, 能量>70%
    GOOD = "good"           # 良好 - PDR>90%, 能量>50%
    MODERATE = "moderate"   # 中等 - PDR>80%, 能量>30%
    POOR = "poor"          # 较差 - PDR>70%, 能量>15%
    CRITICAL = "critical"   # 危急 - PDR<70% or 能量<15%


@dataclass
class AdaptiveConfig:
    """自适应配置参数"""
    # 可靠性阈值
    pdr_excellent_threshold: float = 0.95
    pdr_good_threshold: float = 0.90
    pdr_moderate_threshold: float = 0.80
    pdr_poor_threshold: float = 0.70
    
    # 能量阈值
    energy_excellent_threshold: float = 0.70
    energy_good_threshold: float = 0.50
    energy_moderate_threshold: float = 0.30
    energy_critical_threshold: float = 0.15
    
    # 自适应参数
    history_window_size: int = 10  # 历史窗口大小
    adaptation_frequency: int = 5   # 自适应调整频率(轮数)
    prediction_horizon: int = 20    # 预测时间范围
    
    # 能效权衡参数
    energy_weight: float = 0.6      # 能量权重
    reliability_weight: float = 0.4  # 可靠性权重


class AdaptiveReliabilityEEHFR(EnhancedEEHFR2Protocol):
    """自适应可靠性增强EEHFR协议"""
    
    def __init__(self, config: EnhancedEEHFR2Config, adaptive_config: AdaptiveConfig = None):
        super().__init__(config)
        self.adaptive_config = adaptive_config or AdaptiveConfig()
        
        # 网络状态监测
        self.current_condition = NetworkCondition.EXCELLENT
        self.pdr_history: List[float] = []
        self.energy_history: List[float] = []
        self.transmission_history: List[Dict] = []
        
        # 自适应决策
        self.current_reliability_level = ReliabilityLevel.MINIMAL
        self.adaptive_thresholds = self._initialize_adaptive_thresholds()
        
        # 性能统计
        self.reliability_level_usage = {level: 0 for level in ReliabilityLevel}
        self.energy_savings = 0.0
        self.reliability_improvements = 0.0
        
        # 预测模型
        self.network_predictor = NetworkStatePredictor(self.adaptive_config.history_window_size)

        # 轮次统计
        self.round_stats = []

        print("🧠 自适应可靠性增强EEHFR协议初始化完成")
    
    def _initialize_adaptive_thresholds(self) -> Dict:
        """初始化自适应阈值"""
        return {
            'dual_path_activation': 0.85,      # 双路径激活阈值
            'cooperative_activation': 0.75,    # 协作传输激活阈值
            'energy_conservation': 0.30,       # 能量保护阈值
            'emergency_mode': 0.15             # 紧急模式阈值
        }
    
    def run_simulation(self, max_rounds: int = 200) -> Dict:
        """运行自适应可靠性仿真"""
        print(f"🚀 开始自适应可靠性Enhanced EEHFR仿真 (最大轮数: {max_rounds})")
        
        # 初始化网络
        self.initialize_network()
        
        while self.current_round < max_rounds:
            self.current_round += 1
            
            # 网络状态评估和自适应调整
            if self.current_round % self.adaptive_config.adaptation_frequency == 0:
                self._evaluate_network_condition()
                self._adapt_reliability_strategy()
            
            # 执行一轮通信
            round_stats = self._execute_adaptive_round()
            
            # 更新历史数据
            self._update_history(round_stats)

            # 保存轮次统计
            self.round_stats.append(round_stats)
            
            # 检查网络生存状态
            alive_nodes = [n for n in self.nodes if n.is_alive()]
            if len(alive_nodes) == 0:
                print(f"⚠️ 网络在第{self.current_round}轮全部节点死亡")
                break
            
            # 进度报告
            if self.current_round % 50 == 0:
                self._print_adaptive_progress()
        
        return self._generate_adaptive_results()
    
    def _evaluate_network_condition(self):
        """评估当前网络状况"""
        if len(self.pdr_history) == 0:
            return
        
        # 计算最近的PDR和能量水平
        recent_pdr = np.mean(self.pdr_history[-5:]) if len(self.pdr_history) >= 5 else np.mean(self.pdr_history)
        
        alive_nodes = [n for n in self.nodes if n.is_alive()]
        if not alive_nodes:
            self.current_condition = NetworkCondition.CRITICAL
            return
        
        avg_energy_ratio = sum(n.current_energy / n.initial_energy for n in alive_nodes) / len(alive_nodes)
        
        # 基于PDR和能量水平确定网络状况
        if (recent_pdr >= self.adaptive_config.pdr_excellent_threshold and 
            avg_energy_ratio >= self.adaptive_config.energy_excellent_threshold):
            self.current_condition = NetworkCondition.EXCELLENT
        elif (recent_pdr >= self.adaptive_config.pdr_good_threshold and 
              avg_energy_ratio >= self.adaptive_config.energy_good_threshold):
            self.current_condition = NetworkCondition.GOOD
        elif (recent_pdr >= self.adaptive_config.pdr_moderate_threshold and 
              avg_energy_ratio >= self.adaptive_config.energy_moderate_threshold):
            self.current_condition = NetworkCondition.MODERATE
        elif (recent_pdr >= self.adaptive_config.pdr_poor_threshold and 
              avg_energy_ratio >= self.adaptive_config.energy_critical_threshold):
            self.current_condition = NetworkCondition.POOR
        else:
            self.current_condition = NetworkCondition.CRITICAL
    
    def _adapt_reliability_strategy(self):
        """自适应调整可靠性策略"""
        # 基于网络状况选择可靠性等级
        condition_to_level = {
            NetworkCondition.EXCELLENT: ReliabilityLevel.MINIMAL,
            NetworkCondition.GOOD: ReliabilityLevel.STANDARD,
            NetworkCondition.MODERATE: ReliabilityLevel.ENHANCED,
            NetworkCondition.POOR: ReliabilityLevel.ENHANCED,
            NetworkCondition.CRITICAL: ReliabilityLevel.CRITICAL
        }
        
        new_level = condition_to_level[self.current_condition]
        
        if new_level != self.current_reliability_level:
            print(f"🔄 可靠性等级调整: {self.current_reliability_level.value} → {new_level.value}")
            print(f"   网络状况: {self.current_condition.value}")
            self.current_reliability_level = new_level
        
        # 动态调整阈值
        self._update_adaptive_thresholds()
    
    def _update_adaptive_thresholds(self):
        """动态更新自适应阈值"""
        # 基于网络状况调整阈值
        if self.current_condition == NetworkCondition.EXCELLENT:
            # 优秀状况下提高阈值，减少不必要的可靠性机制
            self.adaptive_thresholds['dual_path_activation'] = 0.90
            self.adaptive_thresholds['cooperative_activation'] = 0.80
        elif self.current_condition == NetworkCondition.CRITICAL:
            # 危急状况下降低阈值，更积极使用可靠性机制
            self.adaptive_thresholds['dual_path_activation'] = 0.70
            self.adaptive_thresholds['cooperative_activation'] = 0.60
        else:
            # 中等状况使用默认阈值
            self.adaptive_thresholds['dual_path_activation'] = 0.85
            self.adaptive_thresholds['cooperative_activation'] = 0.75
    
    def _execute_adaptive_round(self) -> Dict:
        """执行一轮自适应通信"""
        round_stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'energy_consumed': 0.0,
            'reliability_activations': {level.value: 0 for level in ReliabilityLevel},
            'transmission_modes': {'direct': 0, 'direct_with_retry': 0, 'dual_path': 0, 'cooperative': 0}
        }
        
        # 簇头选择和数据聚合
        self.select_cluster_heads()
        self.form_clusters()
        
        # 簇内数据收集
        for cluster_id, cluster_info in self.clusters.items():
            cluster_head = cluster_info['head']
            members = cluster_info['members']
            
            for member in members:
                if member.is_alive() and member != cluster_head:
                    # 自适应传输决策
                    transmission_result = self._adaptive_transmission(member, cluster_head)
                    
                    # 更新统计
                    round_stats['packets_sent'] += 1
                    round_stats['energy_consumed'] += transmission_result['energy_consumed']
                    round_stats['transmission_modes'][transmission_result['mode']] += 1
                    
                    if transmission_result['success']:
                        round_stats['packets_received'] += 1
        
        # 簇头到基站传输
        for cluster_id, cluster_info in self.clusters.items():
            cluster_head = cluster_info['head']
            if cluster_head.is_alive():
                # 自适应基站传输
                bs_result = self._adaptive_base_station_transmission(cluster_head)
                
                round_stats['packets_sent'] += 1
                round_stats['energy_consumed'] += bs_result['energy_consumed']
                round_stats['transmission_modes'][bs_result['mode']] += 1
                
                if bs_result['success']:
                    round_stats['packets_received'] += 1
        
        return round_stats
    
    def _adaptive_transmission(self, source: EnhancedNode, destination: EnhancedNode) -> Dict:
        """自适应传输决策"""
        # 评估传输条件
        distance = source.distance_to(destination)
        source_energy_ratio = source.current_energy / source.initial_energy
        
        # 估计传输成功概率
        estimated_pdr = self._estimate_transmission_pdr(distance, source_energy_ratio)
        
        # 选择传输模式
        transmission_mode = self._select_transmission_mode(estimated_pdr, source_energy_ratio)
        
        # 执行传输
        result = self._execute_transmission(source, destination, transmission_mode)
        
        # 记录可靠性等级使用
        self.reliability_level_usage[self.current_reliability_level] += 1
        
        return result
    
    def _select_transmission_mode(self, estimated_pdr: float, energy_ratio: float) -> str:
        """选择传输模式"""
        # 基于当前可靠性等级和网络状况选择模式
        if self.current_reliability_level == ReliabilityLevel.MINIMAL:
            return "direct"
        elif self.current_reliability_level == ReliabilityLevel.STANDARD:
            if estimated_pdr < 0.9:
                return "direct_with_retry"
            return "direct"
        elif self.current_reliability_level == ReliabilityLevel.ENHANCED:
            if estimated_pdr < self.adaptive_thresholds['dual_path_activation'] and energy_ratio > 0.3:
                return "dual_path"
            return "direct"
        else:  # CRITICAL
            if energy_ratio > 0.2:
                if estimated_pdr < self.adaptive_thresholds['cooperative_activation']:
                    return "cooperative"
                elif estimated_pdr < self.adaptive_thresholds['dual_path_activation']:
                    return "dual_path"
            return "direct"
    
    def _estimate_transmission_pdr(self, distance: float, energy_ratio: float) -> float:
        """估计传输成功概率"""
        # 基于距离的基础PDR
        base_pdr = max(0.7, 1.0 - (distance / 100.0) * 0.3)
        
        # 能量影响
        energy_factor = min(1.0, energy_ratio * 1.2)
        
        # 网络状况影响
        condition_factor = {
            NetworkCondition.EXCELLENT: 1.0,
            NetworkCondition.GOOD: 0.95,
            NetworkCondition.MODERATE: 0.90,
            NetworkCondition.POOR: 0.85,
            NetworkCondition.CRITICAL: 0.80
        }[self.current_condition]
        
        return base_pdr * energy_factor * condition_factor
    
    def _execute_transmission(self, source: EnhancedNode, destination: EnhancedNode, mode: str) -> Dict:
        """执行具体传输"""
        packet_size_bits = self.config.packet_size * 8
        distance = source.distance_to(destination)
        
        result = {
            'success': False,
            'energy_consumed': 0.0,
            'mode': mode,
            'attempts': 1
        }
        
        if mode == "direct":
            # 直接传输
            tx_energy = self.energy_model.calculate_transmission_energy(packet_size_bits, distance)
            rx_energy = self.energy_model.calculate_reception_energy(packet_size_bits)

            source.current_energy = max(0, source.current_energy - tx_energy)
            destination.current_energy = max(0, destination.current_energy - rx_energy)

            result['energy_consumed'] = tx_energy + rx_energy
            result['success'] = random.random() < 0.95  # 95%基础成功率

        elif mode == "direct_with_retry":
            # 直接传输带重传
            tx_energy = self.energy_model.calculate_transmission_energy(packet_size_bits, distance)
            rx_energy = self.energy_model.calculate_reception_energy(packet_size_bits)

            # 第一次尝试
            source.current_energy = max(0, source.current_energy - tx_energy)
            destination.current_energy = max(0, destination.current_energy - rx_energy)

            if random.random() < 0.95:
                result['success'] = True
                result['energy_consumed'] = tx_energy + rx_energy
            else:
                # 重传一次
                source.current_energy = max(0, source.current_energy - tx_energy * 0.5)
                result['energy_consumed'] = tx_energy + rx_energy + tx_energy * 0.5
                result['success'] = random.random() < 0.98  # 重传后98%成功率
                result['attempts'] = 2
            
        elif mode == "dual_path":
            # 双路径传输 - 能耗约2倍，成功率提升
            energy_cost = self._calculate_dual_path_energy(source, destination)
            result['energy_consumed'] = energy_cost
            result['success'] = random.random() < 0.98  # 98%成功率
            
        elif mode == "cooperative":
            # 协作传输 - 能耗约1.5倍，成功率中等提升
            energy_cost = self._calculate_cooperative_energy(source, destination)
            result['energy_consumed'] = energy_cost
            result['success'] = random.random() < 0.97  # 97%成功率
        
        return result
    
    def _calculate_dual_path_energy(self, source: EnhancedNode, destination: EnhancedNode) -> float:
        """计算双路径传输能耗"""
        packet_size_bits = self.config.packet_size * 8
        distance = source.distance_to(destination)
        
        # 主路径能耗
        primary_energy = self.energy_model.calculate_transmission_energy(packet_size_bits, distance)
        
        # 备份路径能耗（假设通过中继，距离增加30%）
        backup_energy = self.energy_model.calculate_transmission_energy(packet_size_bits, distance * 1.3)
        
        total_energy = primary_energy + backup_energy
        source.current_energy = max(0, source.current_energy - total_energy)
        
        return total_energy
    
    def _calculate_cooperative_energy(self, source: EnhancedNode, destination: EnhancedNode) -> float:
        """计算协作传输能耗"""
        packet_size_bits = self.config.packet_size * 8
        distance = source.distance_to(destination)
        
        # 协作传输能耗（1.5倍基础能耗）
        base_energy = self.energy_model.calculate_transmission_energy(packet_size_bits, distance)
        cooperative_energy = base_energy * 1.5
        
        source.current_energy = max(0, source.current_energy - cooperative_energy)
        
        return cooperative_energy

    def _adaptive_base_station_transmission(self, cluster_head: EnhancedNode) -> Dict:
        """自适应基站传输"""
        distance = cluster_head.distance_to_base_station(*self.base_station)
        energy_ratio = cluster_head.current_energy / cluster_head.initial_energy

        # 估计传输成功概率
        estimated_pdr = self._estimate_transmission_pdr(distance, energy_ratio)

        # 选择传输模式
        mode = self._select_transmission_mode(estimated_pdr, energy_ratio)

        # 执行传输
        return self._execute_base_station_transmission(cluster_head, mode)

    def _execute_base_station_transmission(self, cluster_head: EnhancedNode, mode: str) -> Dict:
        """执行基站传输"""
        packet_size_bits = self.config.packet_size * 8
        distance = cluster_head.distance_to_base_station(*self.base_station)

        result = {
            'success': False,
            'energy_consumed': 0.0,
            'mode': mode,
            'attempts': 1
        }

        if mode == "direct":
            tx_energy = self.energy_model.calculate_transmission_energy(packet_size_bits, distance)
            cluster_head.current_energy = max(0, cluster_head.current_energy - tx_energy)
            result['energy_consumed'] = tx_energy
            result['success'] = random.random() < 0.95

        elif mode == "dual_path":
            # 双路径到基站（通过中继节点）
            tx_energy = self.energy_model.calculate_transmission_energy(packet_size_bits, distance)
            relay_energy = tx_energy * 0.8  # 中继传输能耗
            total_energy = tx_energy + relay_energy

            cluster_head.current_energy = max(0, cluster_head.current_energy - total_energy)
            result['energy_consumed'] = total_energy
            result['success'] = random.random() < 0.98

        return result

    def _update_history(self, round_stats: Dict):
        """更新历史数据"""
        # 计算当前轮的PDR
        if round_stats['packets_sent'] > 0:
            current_pdr = round_stats['packets_received'] / round_stats['packets_sent']
        else:
            current_pdr = 1.0

        self.pdr_history.append(current_pdr)

        # 计算当前平均能量比例
        alive_nodes = [n for n in self.nodes if n.is_alive()]
        if alive_nodes:
            avg_energy_ratio = sum(n.current_energy / n.initial_energy for n in alive_nodes) / len(alive_nodes)
        else:
            avg_energy_ratio = 0.0

        self.energy_history.append(avg_energy_ratio)

        # 保持历史窗口大小
        if len(self.pdr_history) > self.adaptive_config.history_window_size:
            self.pdr_history.pop(0)
        if len(self.energy_history) > self.adaptive_config.history_window_size:
            self.energy_history.pop(0)

        # 更新预测器
        self.network_predictor.update_history(current_pdr, avg_energy_ratio)

    def _print_adaptive_progress(self):
        """打印自适应进度"""
        alive_nodes = [n for n in self.nodes if n.is_alive()]
        avg_energy = sum(n.current_energy for n in alive_nodes) / len(alive_nodes) if alive_nodes else 0
        recent_pdr = np.mean(self.pdr_history[-5:]) if len(self.pdr_history) >= 5 else 0

        print(f"📊 第{self.current_round}轮: 存活节点{len(alive_nodes)}, "
              f"平均能量{avg_energy:.3f}J, PDR{recent_pdr:.3f}, "
              f"网络状况{self.current_condition.value}, "
              f"可靠性等级{self.current_reliability_level.value}")

    def _generate_adaptive_results(self) -> Dict:
        """生成自适应仿真结果"""
        alive_nodes = [n for n in self.nodes if n.is_alive()]
        total_energy_consumed = sum(n.initial_energy - n.current_energy for n in self.nodes)

        # 计算总体性能指标
        total_packets_sent = sum(stats['packets_sent'] for stats in self.round_stats)
        total_packets_received = sum(stats['packets_received'] for stats in self.round_stats)

        overall_pdr = total_packets_received / total_packets_sent if total_packets_sent > 0 else 0
        energy_efficiency = total_packets_received / total_energy_consumed if total_energy_consumed > 0 else 0

        results = {
            'network_lifetime': self.current_round,
            'alive_nodes': len(alive_nodes),
            'total_energy_consumed': total_energy_consumed,
            'packets_transmitted': total_packets_sent,
            'packets_received': total_packets_received,
            'packet_delivery_ratio': overall_pdr,
            'energy_efficiency': energy_efficiency,
            'reliability_level_usage': self.reliability_level_usage.copy(),
            'final_condition': self.current_condition.value,
            'adaptive_thresholds': self.adaptive_thresholds.copy()
        }

        print(f"\n✅ 自适应可靠性仿真完成")
        print(f"   网络生存时间: {results['network_lifetime']} 轮")
        print(f"   能量效率: {results['energy_efficiency']:.2f} packets/J")
        print(f"   投递率: {results['packet_delivery_ratio']:.3f}")
        print(f"   最终网络状况: {results['final_condition']}")
        print(f"   可靠性等级使用统计: {results['reliability_level_usage']}")

        return results


class NetworkStatePredictor:
    """网络状态预测器"""

    def __init__(self, window_size: int):
        self.window_size = window_size
        self.pdr_history = []
        self.energy_history = []

    def predict_future_state(self, current_pdr: float, current_energy: float) -> Dict:
        """预测未来网络状态"""
        # 简单的线性预测模型
        if len(self.pdr_history) < 3:
            return {'predicted_pdr': current_pdr, 'predicted_energy': current_energy}

        # PDR趋势预测
        pdr_trend = np.polyfit(range(len(self.pdr_history)), self.pdr_history, 1)[0]
        predicted_pdr = max(0.0, min(1.0, current_pdr + pdr_trend * 5))

        # 能量趋势预测
        energy_trend = np.polyfit(range(len(self.energy_history)), self.energy_history, 1)[0]
        predicted_energy = max(0.0, min(1.0, current_energy + energy_trend * 5))

        return {
            'predicted_pdr': predicted_pdr,
            'predicted_energy': predicted_energy,
            'pdr_trend': pdr_trend,
            'energy_trend': energy_trend
        }

    def update_history(self, pdr: float, energy: float):
        """更新历史数据"""
        self.pdr_history.append(pdr)
        self.energy_history.append(energy)

        # 保持窗口大小
        if len(self.pdr_history) > self.window_size:
            self.pdr_history.pop(0)
        if len(self.energy_history) > self.window_size:
            self.energy_history.pop(0)
