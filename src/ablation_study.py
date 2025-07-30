#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced EEHFR消融实验分析

目的: 分析各个优化组件的独立贡献，识别性能瓶颈
方法: 逐步移除/简化各个组件，观察性能变化

组件分析:
1. 基础版本 (仅基本分簇)
2. +环境分类
3. +模糊逻辑
4. +自适应传输功率
5. 完整版本

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0 (消融实验)
"""

import numpy as np
import json
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import statistics
import os

from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig, Node
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from realistic_channel_model import EnvironmentType, LogNormalShadowingModel
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol

class SimplifiedEEHFRProtocol:
    """简化版Enhanced EEHFR协议 - 用于消融实验"""
    
    def __init__(self, network_config: NetworkConfig, 
                 enable_environment_classification: bool = False,
                 enable_fuzzy_logic: bool = False,
                 enable_adaptive_power: bool = False):
        
        self.config = network_config
        self.enable_environment_classification = enable_environment_classification
        self.enable_fuzzy_logic = enable_fuzzy_logic
        self.enable_adaptive_power = enable_adaptive_power
        
        # 初始化节点
        self.nodes = self._initialize_nodes()
        self.base_station = (network_config.area_width/2, network_config.area_height/2)

        # 环境设置
        if self.enable_environment_classification:
            self.current_environment = self._classify_environment()
        else:
            self.current_environment = EnvironmentType.OUTDOOR_OPEN  # 默认环境

        # 初始化组件
        self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        self.channel_model = LogNormalShadowingModel(self.current_environment)

        # 统计信息
        self.total_energy_consumed = 0.0
        self.total_packets_sent = 0
        self.total_packets_received = 0
        self.round_statistics = []
    
    def _initialize_nodes(self) -> List[Node]:
        """初始化网络节点"""
        nodes = []
        np.random.seed(42)  # 固定种子确保可重复性
        
        for i in range(self.config.num_nodes):
            x = np.random.uniform(0, self.config.area_width)
            y = np.random.uniform(0, self.config.area_height)
            
            node = Node(
                node_id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                transmission_range=50.0  # 固定传输范围
            )
            nodes.append(node)
        
        return nodes
    
    def _classify_environment(self) -> EnvironmentType:
        """环境分类 (如果启用)"""
        if not self.enable_environment_classification:
            return EnvironmentType.OUTDOOR_OPEN
        
        # 简化的环境分类逻辑
        node_density = len(self.nodes) / (self.config.area_width * self.config.area_height / 10000)
        
        if node_density > 0.8:
            return EnvironmentType.INDOOR_OFFICE
        elif node_density > 0.5:
            return EnvironmentType.OUTDOOR_SUBURBAN
        else:
            return EnvironmentType.OUTDOOR_OPEN
    
    def _calculate_cluster_head_probability(self, node: Node) -> float:
        """计算簇头概率"""
        if not self.enable_fuzzy_logic:
            # 基础版本：基于LEACH的概率计算
            optimal_cluster_heads = int(0.05 * len(self.nodes))  # 5%的节点作为簇头
            return optimal_cluster_heads / len(self.nodes)
        
        # 模糊逻辑版本：考虑能量和位置
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return 0.0
        
        max_energy = max(n.current_energy for n in alive_nodes)
        energy_factor = node.current_energy / max_energy if max_energy > 0 else 0
        
        # 计算到基站的距离因子
        distance_to_bs = np.sqrt((node.x - self.base_station[0])**2 + 
                                (node.y - self.base_station[1])**2)
        max_distance = np.sqrt(self.config.area_width**2 + self.config.area_height**2)
        distance_factor = 1.0 - (distance_to_bs / max_distance)
        
        # 模糊逻辑规则
        if energy_factor > 0.7 and distance_factor > 0.5:
            return 0.9
        elif energy_factor > 0.5:
            return 0.6
        elif distance_factor > 0.7:
            return 0.4
        else:
            return 0.1
    
    def _get_transmission_power(self, distance: float) -> float:
        """获取传输功率"""
        if not self.enable_adaptive_power:
            # 基础版本：固定功率
            return 0.0  # 0 dBm
        
        # 自适应功率版本
        if distance < 20:
            return -5.0  # -5 dBm for short distance
        elif distance < 50:
            return 0.0   # 0 dBm for medium distance
        else:
            return 5.0   # 5 dBm for long distance
    
    def _form_clusters(self) -> Dict:
        """形成簇结构"""
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return {}
        
        # 选择簇头
        cluster_heads = []
        for node in alive_nodes:
            probability = self._calculate_cluster_head_probability(node)
            if np.random.random() < probability:
                cluster_heads.append(node)
        
        # 确保至少有一个簇头
        if not cluster_heads:
            cluster_heads = [max(alive_nodes, key=lambda n: n.current_energy)]
        
        # 分配节点到簇
        clusters = {}
        for ch in cluster_heads:
            clusters[ch.node_id] = {
                'head': ch,
                'members': []
            }
        
        # 非簇头节点加入最近的簇
        for node in alive_nodes:
            if node not in cluster_heads:
                min_distance = float('inf')
                best_cluster = None
                
                for ch in cluster_heads:
                    distance = np.sqrt((node.x - ch.x)**2 + (node.y - ch.y)**2)
                    if distance < min_distance:
                        min_distance = distance
                        best_cluster = ch.node_id
                
                if best_cluster is not None:
                    clusters[best_cluster]['members'].append(node)
        
        return clusters
    
    def _simulate_round(self, round_num: int) -> Dict:
        """模拟一轮通信"""
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return {'cluster_heads': 0, 'packets_sent': 0, 'packets_received': 0, 'energy_consumed': 0}
        
        # 形成簇
        clusters = self._form_clusters()
        
        packets_sent = 0
        packets_received = 0
        round_energy = 0.0
        
        # 簇内通信
        for cluster_id, cluster_info in clusters.items():
            ch = cluster_info['head']
            members = cluster_info['members']
            
            # 成员节点向簇头发送数据
            for member in members:
                if member.is_alive:
                    distance = np.sqrt((member.x - ch.x)**2 + (member.y - ch.y)**2)
                    power = self._get_transmission_power(distance)
                    
                    # 计算能耗
                    tx_energy = self.energy_model.calculate_transmission_energy(
                        self.config.packet_size * 8, distance, power
                    )
                    rx_energy = self.energy_model.calculate_reception_energy(
                        self.config.packet_size * 8
                    )
                    
                    # 消耗能量
                    member.consume_energy(tx_energy)
                    ch.consume_energy(rx_energy)
                    
                    round_energy += tx_energy + rx_energy
                    packets_sent += 1
                    
                    # 简单的传输成功率模型
                    success_rate = 0.95 if distance < 30 else 0.85
                    if np.random.random() < success_rate:
                        packets_received += 1
        
        # 簇头向基站发送数据
        for cluster_id, cluster_info in clusters.items():
            ch = cluster_info['head']
            if ch.is_alive:
                distance_to_bs = np.sqrt((ch.x - self.base_station[0])**2 + 
                                       (ch.y - self.base_station[1])**2)
                power = self._get_transmission_power(distance_to_bs)
                
                # 计算能耗
                tx_energy = self.energy_model.calculate_transmission_energy(
                    self.config.packet_size * 8, distance_to_bs, power
                )
                
                ch.consume_energy(tx_energy)
                round_energy += tx_energy
                packets_sent += 1
                
                # 基站接收成功率
                success_rate = 0.98 if distance_to_bs < 50 else 0.90
                if np.random.random() < success_rate:
                    packets_received += 1
        
        return {
            'cluster_heads': len(clusters),
            'packets_sent': packets_sent,
            'packets_received': packets_received,
            'energy_consumed': round_energy
        }
    
    def run_simulation(self, max_rounds: int) -> Dict:
        """运行仿真"""
        print(f"🚀 开始简化Enhanced EEHFR仿真")
        print(f"   环境分类: {'启用' if self.enable_environment_classification else '禁用'}")
        print(f"   模糊逻辑: {'启用' if self.enable_fuzzy_logic else '禁用'}")
        print(f"   自适应功率: {'启用' if self.enable_adaptive_power else '禁用'}")
        
        start_time = time.time()
        
        for round_num in range(max_rounds):
            alive_nodes = [n for n in self.nodes if n.is_alive]
            if not alive_nodes:
                break
            
            round_stats = self._simulate_round(round_num)
            
            self.total_energy_consumed += round_stats['energy_consumed']
            self.total_packets_sent += round_stats['packets_sent']
            self.total_packets_received += round_stats['packets_received']
            self.round_statistics.append(round_stats)
            
            if round_num % 100 == 0:
                total_energy = sum(n.initial_energy - n.current_energy for n in self.nodes)
                print(f"   轮数 {round_num}: 存活节点 {len(alive_nodes)}, 总能耗 {total_energy:.3f}J")
        
        # 计算最终统计
        network_lifetime = len(self.round_statistics)
        final_alive_nodes = len([n for n in self.nodes if n.is_alive])
        execution_time = time.time() - start_time
        
        if self.total_packets_sent > 0:
            energy_efficiency = self.total_packets_sent / self.total_energy_consumed
            packet_delivery_ratio = self.total_packets_received / self.total_packets_sent
        else:
            energy_efficiency = 0
            packet_delivery_ratio = 0
        
        print(f"✅ 仿真完成，网络在 {network_lifetime} 轮后结束")
        
        return {
            'protocol': f'Simplified_EEHFR_env{self.enable_environment_classification}_fuzzy{self.enable_fuzzy_logic}_power{self.enable_adaptive_power}',
            'network_lifetime': network_lifetime,
            'total_energy_consumed': self.total_energy_consumed,
            'final_alive_nodes': final_alive_nodes,
            'energy_efficiency': energy_efficiency,
            'packet_delivery_ratio': packet_delivery_ratio,
            'execution_time': execution_time,
            'config': {
                'num_nodes': len(self.nodes),
                'initial_energy': self.config.initial_energy,
                'area_size': f"{self.config.area_width}x{self.config.area_height}",
                'packet_size': self.config.packet_size
            },
            'additional_metrics': {
                'total_packets_sent': self.total_packets_sent,
                'total_packets_received': self.total_packets_received,
                'average_cluster_heads': sum(stats['cluster_heads'] for stats in self.round_statistics) / len(self.round_statistics) if self.round_statistics else 0
            }
        }

def run_ablation_study():
    """运行消融实验"""
    
    print("🔬 开始Enhanced EEHFR消融实验")
    print("=" * 60)
    
    # 实验配置
    network_config = NetworkConfig(
        num_nodes=20,  # 较小规模，快速测试
        area_width=50,
        area_height=50,
        initial_energy=1.0
    )
    
    # 定义实验变体
    variants = [
        ("基础版本", False, False, False),
        ("基础+环境分类", True, False, False),
        ("基础+模糊逻辑", False, True, False),
        ("基础+自适应功率", False, False, True),
        ("环境+模糊", True, True, False),
        ("环境+功率", True, False, True),
        ("模糊+功率", False, True, True),
        ("完整版本", True, True, True),
    ]
    
    results = {}
    
    for name, env, fuzzy, power in variants:
        print(f"\n🧪 测试变体: {name}")
        
        protocol = SimplifiedEEHFRProtocol(
            network_config,
            enable_environment_classification=env,
            enable_fuzzy_logic=fuzzy,
            enable_adaptive_power=power
        )
        
        result = protocol.run_simulation(max_rounds=500)
        results[name] = result
        
        print(f"   生存时间: {result['network_lifetime']}轮")
        print(f"   能效: {result['energy_efficiency']:.1f} packets/J")
        print(f"   投递率: {result['packet_delivery_ratio']:.3f}")
    
    # 保存结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"../results/ablation_study_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 消融实验结果已保存: {results_file}")
    
    # 生成分析报告
    _generate_ablation_report(results, timestamp)
    
    return results

def _generate_ablation_report(results: Dict, timestamp: str):
    """生成消融实验分析报告"""
    
    report_file = f"../results/ablation_analysis_{timestamp}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Enhanced EEHFR消融实验分析报告\n\n")
        f.write(f"**实验时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**网络规模**: 20节点，50×50米\n")
        f.write(f"**最大轮数**: 500轮\n\n")
        
        f.write("## 实验结果对比\n\n")
        f.write("| 变体 | 网络生存时间(轮) | 能效(packets/J) | 投递率 |\n")
        f.write("|------|------------------|-----------------|--------|\n")
        
        for name, result in results.items():
            f.write(f"| {name} | {result['network_lifetime']} | "
                   f"{result['energy_efficiency']:.1f} | "
                   f"{result['packet_delivery_ratio']:.3f} |\n")
        
        f.write("\n## 组件贡献分析\n\n")
        
        # 分析各组件的贡献
        baseline = results["基础版本"]
        
        f.write("### 单组件影响\n\n")
        for component, key in [("环境分类", "基础+环境分类"), 
                              ("模糊逻辑", "基础+模糊逻辑"), 
                              ("自适应功率", "基础+自适应功率")]:
            if key in results:
                variant = results[key]
                lifetime_change = variant['network_lifetime'] - baseline['network_lifetime']
                efficiency_change = variant['energy_efficiency'] - baseline['energy_efficiency']
                
                f.write(f"**{component}**:\n")
                f.write(f"- 生存时间变化: {lifetime_change:+d}轮\n")
                f.write(f"- 能效变化: {efficiency_change:+.1f} packets/J\n\n")
    
    print(f"📊 消融实验分析报告已保存: {report_file}")

if __name__ == "__main__":
    run_ablation_study()
