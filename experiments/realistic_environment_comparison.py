#!/usr/bin/env python3
"""
基于真实环境建模的WSN协议对比实验

对比协议:
1. Enhanced EEHFR (Realistic) - 我们的改进协议
2. LEACH - 经典分层协议
3. PEGASIS - 链式协议
4. HEED - 混合能效协议

实验环境:
- 基于文献的Log-Normal Shadowing信道模型
- IEEE 802.15.4链路质量评估
- 环境干扰建模 (WiFi, 工业设备)
- 温湿度影响建模

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import random
import json
import os
from datetime import datetime
import logging

# 导入协议实现
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from enhanced_eehfr_realistic import EnhancedEEHFRRealistic, WSNNode
from realistic_channel_model import EnvironmentType
# from baseline_protocols.leach_protocol import LEACHProtocol
# from baseline_protocols.pegasis_protocol import PEGASISProtocol
# from baseline_protocols.heed_protocol import HEEDProtocol

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealisticEnvironmentExperiment:
    """基于真实环境建模的WSN协议对比实验"""
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.INDOOR_FACTORY):
        self.environment = environment
        self.results = {}
        
        # 实验参数
        self.network_sizes = [25, 50, 75, 100]
        self.num_runs = 10  # 每个配置运行10次
        self.max_rounds = 500
        
        # 环境参数
        self.interference_scenarios = {
            'low': [
                {'power': -30, 'distance': 50, 'type': 'wifi'}
            ],
            'medium': [
                {'power': -25, 'distance': 30, 'type': 'wifi'},
                {'power': -20, 'distance': 40, 'type': 'bluetooth'}
            ],
            'high': [
                {'power': -20, 'distance': 20, 'type': 'wifi'},
                {'power': -15, 'distance': 25, 'type': 'motor'},
                {'power': -18, 'distance': 35, 'type': 'welding'}
            ]
        }
        
        logger.info(f"Initialized realistic environment experiment for {environment.value}")
    
    def create_realistic_network(self, num_nodes: int, interference_level: str = 'medium') -> List[WSNNode]:
        """创建具有真实环境特性的网络"""
        nodes = []
        
        for i in range(num_nodes):
            # 随机部署位置
            x = random.uniform(10, 90)
            y = random.uniform(10, 90)
            
            # 模拟真实环境条件
            if self.environment == EnvironmentType.INDOOR_FACTORY:
                # 工厂环境：温度较高，湿度中等
                temperature = random.uniform(25, 45)
                humidity = random.uniform(0.3, 0.7)
            elif self.environment == EnvironmentType.OUTDOOR_OPEN:
                # 室外环境：温度变化大，湿度变化大
                temperature = random.uniform(-10, 40)
                humidity = random.uniform(0.2, 0.9)
            else:
                # 默认室内环境
                temperature = random.uniform(18, 28)
                humidity = random.uniform(0.4, 0.6)
            
            node = WSNNode(
                node_id=i,
                x=x, y=y,
                initial_energy=2.0,  # 2J初始能量
                temperature=temperature,
                humidity=humidity
            )
            nodes.append(node)
        
        logger.info(f"Created network with {num_nodes} nodes in {self.environment.value} environment")
        return nodes
    
    def run_protocol_experiment(self, protocol_class, protocol_name: str, 
                              nodes: List[WSNNode], interference_level: str) -> Dict:
        """运行单个协议的实验"""
        logger.info(f"Running {protocol_name} experiment...")
        
        # 创建协议实例
        if protocol_name == "Enhanced EEHFR":
            protocol = protocol_class(self.environment)
            # 添加干扰源
            protocol.add_interference_sources(self.interference_scenarios[interference_level])
        else:
            # 基准协议需要适配真实环境建模
            protocol = protocol_class()
        
        # 重置节点状态
        for node in nodes:
            node.current_energy = node.initial_energy
            node.is_alive = True
            node.is_cluster_head = False
            node.cluster_id = -1
            node.rssi_history.clear()
            node.lqi_history.clear()
            node.pdr_history.clear()
        
        # 运行仿真
        round_stats = []
        for round_num in range(self.max_rounds):
            if protocol_name == "Enhanced EEHFR":
                stats = protocol.run_round(nodes)
            else:
                # 基准协议的运行方法 (需要适配)
                stats = self._run_baseline_protocol_round(protocol, nodes, round_num)
            
            round_stats.append(stats)
            
            # 检查网络是否还活着
            alive_nodes = sum(1 for node in nodes if node.is_alive)
            if alive_nodes == 0:
                logger.info(f"{protocol_name}: All nodes died at round {round_num}")
                break
        
        # 计算关键指标
        network_lifetime = len(round_stats)
        total_energy = sum(stats['energy_consumed_this_round'] for stats in round_stats)
        avg_pdr = np.mean([stats.get('packet_delivery_ratio', 0.8) for stats in round_stats])
        
        # 计算第一个节点死亡时间 (FND)
        fnd = network_lifetime
        for i, stats in enumerate(round_stats):
            if stats['alive_nodes'] < len(nodes):
                fnd = i + 1
                break
        
        # 计算一半节点死亡时间 (HND)
        hnd = network_lifetime
        for i, stats in enumerate(round_stats):
            if stats['alive_nodes'] < len(nodes) // 2:
                hnd = i + 1
                break
        
        result = {
            'protocol': protocol_name,
            'network_lifetime': network_lifetime,
            'total_energy_consumed': total_energy,
            'average_pdr': avg_pdr,
            'first_node_death': fnd,
            'half_nodes_death': hnd,
            'final_alive_nodes': round_stats[-1]['alive_nodes'] if round_stats else 0,
            'round_stats': round_stats
        }
        
        logger.info(f"{protocol_name} completed: Lifetime={network_lifetime}, "
                   f"Energy={total_energy:.6f}J, PDR={avg_pdr:.3f}")
        
        return result
    
    def _run_baseline_protocol_round(self, protocol, nodes: List[WSNNode], round_num: int) -> Dict:
        """运行基准协议的一轮 (简化实现)"""
        # 这里需要根据具体的基准协议实现来适配
        # 为了演示，我们使用简化的能耗模型
        
        alive_nodes = [node for node in nodes if node.is_alive]
        if not alive_nodes:
            return {
                'round': round_num,
                'alive_nodes': 0,
                'total_nodes': len(nodes),
                'energy_consumed_this_round': 0,
                'packet_delivery_ratio': 0
            }
        
        # 简化的能耗计算
        round_energy = 0
        for node in alive_nodes:
            # 基准协议的典型能耗 (基于文献数据)
            if hasattr(protocol, 'protocol_name'):
                if protocol.protocol_name == 'LEACH':
                    energy_consumption = 0.001  # 1mJ per round
                elif protocol.protocol_name == 'PEGASIS':
                    energy_consumption = 0.0008  # 0.8mJ per round
                elif protocol.protocol_name == 'HEED':
                    energy_consumption = 0.0012  # 1.2mJ per round
                else:
                    energy_consumption = 0.001
            else:
                energy_consumption = 0.001
            
            node.consume_energy(energy_consumption)
            round_energy += energy_consumption
        
        return {
            'round': round_num,
            'alive_nodes': len([node for node in nodes if node.is_alive]),
            'total_nodes': len(nodes),
            'energy_consumed_this_round': round_energy,
            'packet_delivery_ratio': 0.85  # 基准协议的典型PDR
        }
    
    def run_comprehensive_experiment(self):
        """运行综合对比实验"""
        logger.info("Starting comprehensive realistic environment experiment...")
        
        protocols = [
            (EnhancedEEHFRRealistic, "Enhanced EEHFR"),
            # 注意: 基准协议需要适配真实环境建模
            # (LEACHProtocol, "LEACH"),
            # (PEGASISProtocol, "PEGASIS"),
            # (HEEDProtocol, "HEED")
        ]
        
        all_results = []
        
        for network_size in self.network_sizes:
            for interference_level in ['low', 'medium', 'high']:
                logger.info(f"Testing network size: {network_size}, interference: {interference_level}")
                
                for run_id in range(self.num_runs):
                    logger.info(f"Run {run_id + 1}/{self.num_runs}")
                    
                    # 创建网络
                    nodes = self.create_realistic_network(network_size, interference_level)
                    
                    for protocol_class, protocol_name in protocols:
                        # 为每个协议创建独立的节点副本
                        nodes_copy = [
                            WSNNode(
                                node_id=node.node_id,
                                x=node.x, y=node.y,
                                initial_energy=node.initial_energy,
                                temperature=node.temperature,
                                humidity=node.humidity
                            ) for node in nodes
                        ]
                        
                        result = self.run_protocol_experiment(
                            protocol_class, protocol_name, nodes_copy, interference_level
                        )
                        
                        result.update({
                            'network_size': network_size,
                            'interference_level': interference_level,
                            'run_id': run_id,
                            'environment': self.environment.value
                        })
                        
                        all_results.append(result)
        
        self.results = all_results
        logger.info("Comprehensive experiment completed!")
        
        return all_results
    
    def analyze_results(self) -> pd.DataFrame:
        """分析实验结果"""
        if not self.results:
            logger.error("No results to analyze. Run experiment first.")
            return pd.DataFrame()
        
        # 转换为DataFrame
        df_results = []
        for result in self.results:
            df_results.append({
                'Protocol': result['protocol'],
                'Network_Size': result['network_size'],
                'Interference_Level': result['interference_level'],
                'Run_ID': result['run_id'],
                'Environment': result['environment'],
                'Network_Lifetime': result['network_lifetime'],
                'Total_Energy_Consumed': result['total_energy_consumed'],
                'Average_PDR': result['average_pdr'],
                'First_Node_Death': result['first_node_death'],
                'Half_Nodes_Death': result['half_nodes_death'],
                'Final_Alive_Nodes': result['final_alive_nodes']
            })
        
        df = pd.DataFrame(df_results)
        
        # 计算统计摘要
        summary = df.groupby(['Protocol', 'Network_Size', 'Interference_Level']).agg({
            'Network_Lifetime': ['mean', 'std'],
            'Total_Energy_Consumed': ['mean', 'std'],
            'Average_PDR': ['mean', 'std'],
            'First_Node_Death': ['mean', 'std'],
            'Half_Nodes_Death': ['mean', 'std']
        }).round(4)
        
        logger.info("Results analysis completed")
        return df, summary
    
    def save_results(self, filename: str = None):
        """保存实验结果"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"realistic_environment_results_{timestamp}.json"
        
        filepath = os.path.join("d:/lkr_wsn/Enhanced-EEHFR-WSN-Protocol/results", filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 保存结果
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filepath}")
        return filepath
    
    def create_visualization(self):
        """创建可视化图表"""
        if not self.results:
            logger.error("No results to visualize. Run experiment first.")
            return
        
        df, summary = self.analyze_results()
        
        # 设置图表样式
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'WSN Protocol Performance in {self.environment.value.title()} Environment', 
                    fontsize=16, fontweight='bold')
        
        # 1. 网络生存时间对比
        sns.boxplot(data=df, x='Network_Size', y='Network_Lifetime', 
                   hue='Protocol', ax=axes[0,0])
        axes[0,0].set_title('Network Lifetime vs Network Size')
        axes[0,0].set_ylabel('Rounds')
        
        # 2. 能耗对比
        sns.boxplot(data=df, x='Network_Size', y='Total_Energy_Consumed', 
                   hue='Protocol', ax=axes[0,1])
        axes[0,1].set_title('Energy Consumption vs Network Size')
        axes[0,1].set_ylabel('Energy (J)')
        
        # 3. PDR对比
        sns.boxplot(data=df, x='Interference_Level', y='Average_PDR', 
                   hue='Protocol', ax=axes[1,0])
        axes[1,0].set_title('Packet Delivery Ratio vs Interference Level')
        axes[1,0].set_ylabel('PDR')
        
        # 4. 第一个节点死亡时间
        sns.boxplot(data=df, x='Network_Size', y='First_Node_Death', 
                   hue='Protocol', ax=axes[1,1])
        axes[1,1].set_title('First Node Death vs Network Size')
        axes[1,1].set_ylabel('Rounds')
        
        plt.tight_layout()
        
        # 保存图表
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_path = f"d:/lkr_wsn/Enhanced-EEHFR-WSN-Protocol/results/realistic_environment_charts_{timestamp}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        logger.info(f"Charts saved to {chart_path}")
        
        plt.show()

# 使用示例
if __name__ == "__main__":
    # 创建实验实例
    experiment = RealisticEnvironmentExperiment(EnvironmentType.INDOOR_FACTORY)
    
    # 运行实验 (简化版本，只测试Enhanced EEHFR)
    logger.info("Starting realistic environment experiment...")
    
    # 创建测试网络
    test_nodes = experiment.create_realistic_network(50, 'medium')
    
    # 测试Enhanced EEHFR协议
    result = experiment.run_protocol_experiment(
        EnhancedEEHFRRealistic, 
        "Enhanced EEHFR", 
        test_nodes, 
        'medium'
    )
    
    print("\n=== Realistic Environment Test Results ===")
    print(f"Protocol: {result['protocol']}")
    print(f"Network Lifetime: {result['network_lifetime']} rounds")
    print(f"Total Energy Consumed: {result['total_energy_consumed']:.6f} J")
    print(f"Average PDR: {result['average_pdr']:.3f}")
    print(f"First Node Death: {result['first_node_death']} rounds")
    print(f"Half Nodes Death: {result['half_nodes_death']} rounds")
    
    # 保存结果
    experiment.results = [result]
    experiment.save_results("realistic_test_result.json")
    
    print("\nRealistic environment modeling test completed!")
    print("Key improvements over idealized simulation:")
    print("1. Log-Normal Shadowing path loss model")
    print("2. IEEE 802.15.4 RSSI/LQI link quality assessment")
    print("3. Environmental interference modeling")
    print("4. Temperature/humidity effects on battery and signal")
    print("5. Packet delivery rate based on realistic channel conditions")
