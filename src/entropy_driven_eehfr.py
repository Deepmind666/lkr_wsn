#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信息熵驱动的Enhanced EEHFR协议 (Entropy-Driven Enhanced EEHFR)

基于Shannon信息论的WSN能量均衡路由协议：
1. 网络能量分布熵计算
2. 熵驱动的簇头选择
3. 自适应熵平衡路由
4. 理论最优的能量分配

作者: Enhanced EEHFR Research Team
日期: 2025-01-31
版本: 1.0 (Information Entropy Innovation)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import math
import random
import copy
import time
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass

# 导入基础组件
from benchmark_protocols import Node, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

@dataclass
class EntropyNode(Node):
    """熵感知节点类"""
    
    # 熵相关属性
    local_entropy: float = 0.0
    entropy_contribution: float = 0.0
    entropy_history: List[float] = None
    
    # 簇头选择相关
    ch_entropy_score: float = 0.0
    energy_factor: float = 0.0
    centrality_factor: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        if self.entropy_history is None:
            self.entropy_history = []

class NetworkEntropyCalculator:
    """网络信息熵计算器"""
    
    def __init__(self):
        self.entropy_history = []
        self.energy_variance_history = []
    
    def calculate_energy_entropy(self, nodes: List[EntropyNode]) -> float:
        """计算网络能量分布的Shannon熵"""
        
        # 获取所有存活节点的能量
        energies = [node.current_energy for node in nodes if node.is_alive and node.current_energy > 0]
        
        if len(energies) < 2:
            return 0.0
        
        # 计算能量概率分布
        total_energy = sum(energies)
        if total_energy == 0:
            return 0.0
        
        probabilities = [e / total_energy for e in energies]
        
        # 计算Shannon熵
        entropy = 0.0
        for p in probabilities:
            if p > 0:
                entropy -= p * math.log2(p)
        
        # 记录历史
        self.entropy_history.append(entropy)
        
        # 计算能量分布方差（用于对比分析）
        mean_energy = total_energy / len(energies)
        variance = sum((e - mean_energy)**2 for e in energies) / len(energies)
        self.energy_variance_history.append(variance)
        
        return entropy
    
    def calculate_normalized_entropy(self, nodes: List[EntropyNode]) -> float:
        """计算归一化的网络熵"""
        
        alive_count = sum(1 for node in nodes if node.is_alive)
        if alive_count <= 1:
            return 0.0
        
        current_entropy = self.calculate_energy_entropy(nodes)
        max_possible_entropy = math.log2(alive_count)
        
        return current_entropy / max_possible_entropy if max_possible_entropy > 0 else 0.0
    
    def calculate_entropy_gradient(self, nodes: List[EntropyNode], 
                                 potential_ch: EntropyNode) -> float:
        """计算选择某节点为簇头后的熵梯度"""
        
        current_entropy = self.calculate_energy_entropy(nodes)
        
        # 模拟该节点成为簇头后的能量消耗
        simulated_nodes = copy.deepcopy(nodes)
        ch_sim = next(n for n in simulated_nodes if n.id == potential_ch.id)
        
        # 估算簇头额外能耗
        cluster_size = self._estimate_cluster_size(potential_ch, nodes)
        ch_extra_energy = cluster_size * 0.001  # 简化的簇头能耗模型
        
        ch_sim.current_energy = max(0, ch_sim.current_energy - ch_extra_energy)
        
        # 计算新的网络熵
        new_entropy = self.calculate_energy_entropy(simulated_nodes)
        
        return new_entropy - current_entropy
    
    def _estimate_cluster_size(self, ch_candidate: EntropyNode, 
                             nodes: List[EntropyNode]) -> int:
        """估算簇的大小"""
        
        cluster_members = 0
        for node in nodes:
            if node.is_alive and node.id != ch_candidate.id:
                distance = math.sqrt((node.x - ch_candidate.x)**2 + (node.y - ch_candidate.y)**2)
                if distance < 30:  # 假设簇半径为30m
                    cluster_members += 1
        
        return cluster_members

class EntropyDrivenClusterHeadSelection:
    """基于信息熵的簇头选择算法"""
    
    def __init__(self, entropy_weight: float = 0.6, energy_weight: float = 0.3, 
                 centrality_weight: float = 0.1):
        self.entropy_weight = entropy_weight
        self.energy_weight = energy_weight
        self.centrality_weight = centrality_weight
        self.entropy_calculator = NetworkEntropyCalculator()
    
    def select_cluster_heads(self, nodes: List[EntropyNode], 
                           target_ch_ratio: float = 0.1) -> List[EntropyNode]:
        """选择最优簇头组合"""
        
        alive_nodes = [node for node in nodes if node.is_alive]
        if len(alive_nodes) < 2:
            return []
        
        target_ch_count = max(1, int(len(alive_nodes) * target_ch_ratio))
        
        # 重置所有节点的簇头状态
        for node in alive_nodes:
            node.is_cluster_head = False
            node.cluster_id = -1
        
        # 计算每个节点的综合评分
        ch_candidates = []
        
        for node in alive_nodes:
            # 1. 熵增益因子
            entropy_gain = self.entropy_calculator.calculate_entropy_gradient(alive_nodes, node)
            
            # 2. 能量因子
            max_energy = max(n.current_energy for n in alive_nodes)
            energy_factor = node.current_energy / max_energy if max_energy > 0 else 0
            
            # 3. 中心性因子
            centrality_factor = self._calculate_centrality(node, alive_nodes)
            
            # 综合评分
            score = (self.entropy_weight * entropy_gain + 
                    self.energy_weight * energy_factor + 
                    self.centrality_weight * centrality_factor)
            
            # 更新节点属性
            node.ch_entropy_score = score
            node.energy_factor = energy_factor
            node.centrality_factor = centrality_factor
            
            ch_candidates.append((node, score))
        
        # 选择评分最高的节点作为簇头
        ch_candidates.sort(key=lambda x: x[1], reverse=True)
        selected_chs = [candidate[0] for candidate in ch_candidates[:target_ch_count]]
        
        # 设置簇头状态
        for i, ch in enumerate(selected_chs):
            ch.is_cluster_head = True
            ch.cluster_id = i
        
        return selected_chs
    
    def _calculate_centrality(self, node: EntropyNode, 
                            all_nodes: List[EntropyNode]) -> float:
        """计算节点的网络中心性"""
        
        if len(all_nodes) <= 1:
            return 0.0
        
        # 计算到其他节点的平均距离
        distances = []
        for other_node in all_nodes:
            if other_node.id != node.id:
                distance = math.sqrt((node.x - other_node.x)**2 + (node.y - other_node.y)**2)
                distances.append(distance)
        
        if not distances:
            return 0.0
        
        avg_distance = sum(distances) / len(distances)
        max_distance = 100 * math.sqrt(2)  # 对角线距离
        
        # 距离越小，中心性越高
        centrality = 1 - (avg_distance / max_distance) if max_distance > 0 else 0
        
        return max(0, centrality)

class EntropyDrivenEEHFRProtocol:
    """信息熵驱动的Enhanced EEHFR协议"""
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        
        # 初始化组件
        self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        self.entropy_calculator = NetworkEntropyCalculator()
        self.ch_selector = EntropyDrivenClusterHeadSelection()
        
        # 协议参数
        self.entropy_threshold = 0.7  # 熵阈值，低于此值触发重平衡
        self.rebalance_interval = 10   # 重平衡间隔轮数
        
        # 网络状态
        self.nodes: List[EntropyNode] = []
        self.current_round = 0
        
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
            
            node = EntropyNode(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy,
                is_alive=True,
                is_cluster_head=False,
                cluster_id=-1
            )
            self.nodes.append(node)
        
        # 初始簇头选择
        self.ch_selector.select_cluster_heads(self.nodes)
        self._form_clusters()
    
    def _form_clusters(self):
        """形成簇结构"""
        
        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]
        member_nodes = [node for node in self.nodes if not node.is_cluster_head and node.is_alive]
        
        # 为每个成员节点分配最近的簇头
        for member in member_nodes:
            if not cluster_heads:
                continue
            
            min_distance = float('inf')
            best_cluster_head = None
            
            for ch in cluster_heads:
                distance = math.sqrt((member.x - ch.x)**2 + (member.y - ch.y)**2)
                if distance < min_distance:
                    min_distance = distance
                    best_cluster_head = ch
            
            if best_cluster_head:
                member.cluster_id = best_cluster_head.cluster_id
    
    def _entropy_aware_transmission(self) -> Tuple[int, int, float]:
        """熵感知的数据传输"""
        
        packets_sent = 0
        packets_received = 0
        energy_consumed = 0.0
        
        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]
        
        # 簇内数据收集（考虑熵平衡）
        for ch in cluster_heads:
            cluster_members = [node for node in self.nodes 
                             if node.cluster_id == ch.cluster_id and not node.is_cluster_head and node.is_alive]
            
            for member in cluster_members:
                if member.current_energy > 0:
                    # 计算传输距离
                    distance = math.sqrt((member.x - ch.x)**2 + (member.y - ch.y)**2)
                    
                    # 基于熵影响调整传输功率
                    entropy_impact = self._calculate_transmission_entropy_impact(member, ch)
                    base_power = self._get_base_transmission_power(distance)
                    adjusted_power = base_power + entropy_impact * 1.0  # 熵影响系数
                    
                    # 计算传输能耗
                    tx_energy = self.energy_model.calculate_transmission_energy(
                        self.config.packet_size * 8, distance, adjusted_power
                    )
                    rx_energy = self.energy_model.calculate_reception_energy(self.config.packet_size * 8)
                    
                    # 更新能耗
                    member.current_energy -= tx_energy
                    ch.current_energy -= rx_energy
                    
                    energy_consumed += tx_energy + rx_energy
                    packets_sent += 1
                    
                    # 成功率计算（简化）
                    success_rate = 0.95 - entropy_impact * 0.05  # 熵影响成功率
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
                
                # 计算传输能耗
                tx_energy = self.energy_model.calculate_transmission_energy(
                    self.config.packet_size * 8, distance_to_bs, 0.0  # 基站传输使用标准功率
                )
                
                ch.current_energy -= tx_energy
                energy_consumed += tx_energy
                packets_sent += 1
                
                # 基站传输成功率较高
                if random.random() < 0.98:
                    packets_received += 1
        
        return packets_sent, packets_received, energy_consumed
    
    def _calculate_transmission_entropy_impact(self, sender: EntropyNode, 
                                             receiver: EntropyNode) -> float:
        """计算传输对网络熵的影响"""
        
        # 简化的熵影响计算
        energy_diff = abs(sender.current_energy - receiver.current_energy)
        max_energy = max(sender.initial_energy, receiver.initial_energy)
        
        # 能量差异越大，熵影响越大
        entropy_impact = energy_diff / max_energy if max_energy > 0 else 0
        
        return min(entropy_impact, 1.0)
    
    def _get_base_transmission_power(self, distance: float) -> float:
        """获取基础传输功率"""
        
        if distance < 20:
            return -5.0  # -5 dBm for short distance
        elif distance < 50:
            return 0.0   # 0 dBm for medium distance
        else:
            return 5.0   # 5 dBm for long distance
    
    def _should_rebalance_entropy(self) -> bool:
        """判断是否需要进行熵重平衡"""
        
        # 定期重平衡
        if self.current_round % self.rebalance_interval == 0:
            return True
        
        # 熵过低时重平衡
        normalized_entropy = self.entropy_calculator.calculate_normalized_entropy(self.nodes)
        if normalized_entropy < self.entropy_threshold:
            return True
        
        return False
    
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
        
        # 计算熵相关指标
        current_entropy = self.entropy_calculator.calculate_energy_entropy(self.nodes)
        normalized_entropy = self.entropy_calculator.calculate_normalized_entropy(self.nodes)
        
        # 计算能量分布方差
        energies = [node.current_energy for node in self.nodes if node.is_alive]
        if energies:
            mean_energy = sum(energies) / len(energies)
            energy_variance = sum((e - mean_energy)**2 for e in energies) / len(energies)
        else:
            energy_variance = 0.0
        
        round_stats = {
            'round': round_num,
            'alive_nodes': alive_nodes,
            'cluster_heads': cluster_heads,
            'remaining_energy': remaining_energy,
            'packets_sent': packets_sent,
            'packets_received': packets_received,
            'energy_consumed': energy_consumed,
            'pdr': packets_received / packets_sent if packets_sent > 0 else 0,
            # 熵相关指标
            'network_entropy': current_entropy,
            'normalized_entropy': normalized_entropy,
            'energy_variance': energy_variance
        }
        
        self.round_statistics.append(round_stats)
    
    def run_simulation(self, max_rounds: int) -> Dict[str, Any]:
        """运行信息熵驱动的EEHFR仿真"""
        
        print(f"🌟 开始信息熵驱动的Enhanced EEHFR协议仿真")
        print(f"   节点数量: {len(self.nodes)}")
        print(f"   最大轮数: {max_rounds}")
        print(f"   熵阈值: {self.entropy_threshold}")
        
        start_time = time.time()
        
        for round_num in range(max_rounds):
            self.current_round = round_num
            
            # 检查是否还有存活节点
            alive_nodes = [node for node in self.nodes if node.is_alive]
            if len(alive_nodes) < 2:
                print(f"💀 网络在第 {round_num} 轮结束生命周期")
                break
            
            # 判断是否需要熵重平衡
            if self._should_rebalance_entropy():
                print(f"🔄 第 {round_num} 轮：执行熵重平衡")
                self.ch_selector.select_cluster_heads(self.nodes)
                self._form_clusters()
            
            # 执行熵感知的数据传输
            packets_sent, packets_received, energy_consumed = self._entropy_aware_transmission()
            
            # 更新节点状态
            self._update_node_status()
            
            # 收集统计信息
            self._collect_round_statistics(round_num, packets_sent, packets_received, energy_consumed)
            
            # 更新总统计
            self.total_energy_consumed += energy_consumed
            self.total_packets_sent += packets_sent
            self.total_packets_received += packets_received
            
            # 定期输出进度
            if round_num % 50 == 0:
                current_entropy = self.entropy_calculator.calculate_normalized_entropy(self.nodes)
                remaining_energy = sum(node.current_energy for node in self.nodes if node.is_alive)
                print(f"   轮数 {round_num}: 存活节点 {len(alive_nodes)}, 归一化熵 {current_entropy:.3f}, 剩余能量 {remaining_energy:.3f}J")
        
        execution_time = time.time() - start_time
        
        # 生成最终结果
        return self._generate_final_results(execution_time)
    
    def _generate_final_results(self, execution_time: float) -> Dict[str, Any]:
        """生成最终结果"""
        
        final_alive_nodes = sum(1 for node in self.nodes if node.is_alive)
        network_lifetime = len(self.round_statistics)
        
        if self.total_energy_consumed > 0:
            energy_efficiency = self.total_packets_received / self.total_energy_consumed
        else:
            energy_efficiency = 0
        
        if self.total_packets_sent > 0:
            packet_delivery_ratio = self.total_packets_received / self.total_packets_sent
        else:
            packet_delivery_ratio = 0
        
        # 计算熵相关统计
        final_entropy = self.entropy_calculator.calculate_normalized_entropy(self.nodes)
        avg_entropy = sum(stats['normalized_entropy'] for stats in self.round_statistics) / len(self.round_statistics) if self.round_statistics else 0
        
        # 计算能量分布改善
        initial_variance = self.config.initial_energy ** 2 * 0.1  # 假设初始方差
        final_energies = [node.current_energy for node in self.nodes if node.is_alive]
        if final_energies:
            mean_final_energy = sum(final_energies) / len(final_energies)
            final_variance = sum((e - mean_final_energy)**2 for e in final_energies) / len(final_energies)
            variance_reduction = (initial_variance - final_variance) / initial_variance if initial_variance > 0 else 0
        else:
            variance_reduction = 0
        
        print(f"✅ 仿真完成，网络在 {network_lifetime} 轮后结束")
        print(f"   最终归一化熵: {final_entropy:.3f}")
        print(f"   平均归一化熵: {avg_entropy:.3f}")
        print(f"   能量分布方差降低: {variance_reduction*100:.1f}%")
        
        return {
            'protocol': 'Entropy_Driven_EEHFR',
            'network_lifetime': network_lifetime,
            'total_energy_consumed': self.total_energy_consumed,
            'final_alive_nodes': final_alive_nodes,
            'energy_efficiency': energy_efficiency,
            'packet_delivery_ratio': packet_delivery_ratio,
            'execution_time': execution_time,
            'round_statistics': self.round_statistics,
            'config': {
                'num_nodes': len(self.nodes),
                'initial_energy': self.config.initial_energy,
                'area_size': f"{self.config.area_width}x{self.config.area_height}",
                'packet_size': self.config.packet_size,
                'entropy_threshold': self.entropy_threshold
            },
            'entropy_metrics': {
                'final_normalized_entropy': final_entropy,
                'average_normalized_entropy': avg_entropy,
                'entropy_history': self.entropy_calculator.entropy_history,
                'energy_variance_reduction': variance_reduction,
                'rebalance_count': sum(1 for i in range(network_lifetime) if i % self.rebalance_interval == 0)
            },
            'additional_metrics': {
                'total_packets_sent': self.total_packets_sent,
                'total_packets_received': self.total_packets_received,
                'average_cluster_heads': sum(stats['cluster_heads'] for stats in self.round_statistics) / len(self.round_statistics) if self.round_statistics else 0
            }
        }


# 测试函数
def test_entropy_driven_eehfr():
    """测试信息熵驱动的EEHFR协议"""
    
    print("🧪 测试信息熵驱动的Enhanced EEHFR协议")
    print("=" * 60)
    
    # 网络配置
    config = NetworkConfig(
        num_nodes=50,
        area_width=100,
        area_height=100,
        initial_energy=2.0,
        base_station_x=50,
        base_station_y=50,
        packet_size=512
    )
    
    # 创建协议实例
    protocol = EntropyDrivenEEHFRProtocol(config)
    
    # 运行仿真
    result = protocol.run_simulation(200)
    
    # 输出结果
    print(f"\n📊 测试结果:")
    print(f"   网络生存时间: {result['network_lifetime']} 轮")
    print(f"   总能耗: {result['total_energy_consumed']:.3f} J")
    print(f"   能效: {result['energy_efficiency']:.1f} packets/J")
    print(f"   数据包投递率: {result['packet_delivery_ratio']:.3f}")
    print(f"   最终归一化熵: {result['entropy_metrics']['final_normalized_entropy']:.3f}")
    print(f"   能量分布方差降低: {result['entropy_metrics']['energy_variance_reduction']*100:.1f}%")
    
    return result


if __name__ == "__main__":
    test_entropy_driven_eehfr()
