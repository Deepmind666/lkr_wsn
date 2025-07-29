#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced EEHFR协议测试脚本

测试增强型EEHFR协议与基准协议的性能对比
基于Intel Berkeley Research Lab真实数据集

项目路径: EEHFR：融合模糊逻辑与混合元启发式优化的WSN智能节能路由协议/EEHFR_Optimized_v1/
数据源: Intel Berkeley Research Lab数据集 (https://db.csail.mit.edu/labdata/labdata.html)
"""

import numpy as np
import matplotlib.pyplot as plt
import json
import time
from typing import Dict, List
import sys
import os

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, 'src')
sys.path.append(src_dir)

from enhanced_eehfr_protocol import EnhancedNode, EnhancedEEHFR
from intel_dataset_loader import IntelLabDataLoader

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

class EnhancedEEHFRTester:
    """Enhanced EEHFR协议测试器"""
    
    def __init__(self, use_real_data: bool = True):
        """
        初始化测试器
        
        参数:
            use_real_data: 是否使用真实Intel Lab数据集
        """
        self.use_real_data = use_real_data
        self.results = {}
        
        # 测试参数
        self.network_configs = [
            {'n_nodes': 50, 'area_size': 200, 'cluster_ratio': 0.05},
            {'n_nodes': 100, 'area_size': 200, 'cluster_ratio': 0.05},
            {'n_nodes': 150, 'area_size': 300, 'cluster_ratio': 0.04}
        ]
        
        # 加载真实数据
        if self.use_real_data:
            try:
                self.data_loader = IntelLabDataLoader()
                self.real_data = self.data_loader.load_sensor_data(sample_size=1000)
                print(f"✅ 成功加载Intel Lab数据集: {len(self.real_data)} 条记录")
            except Exception as e:
                print(f"⚠️  无法加载真实数据集: {e}")
                print("   将使用模拟数据进行测试")
                self.use_real_data = False
    
    def create_network_from_real_data(self, n_nodes: int = 54) -> List[EnhancedNode]:
        """基于真实Intel Lab数据创建网络节点"""
        if not self.use_real_data:
            return self.create_synthetic_network(n_nodes)
        
        # 获取真实节点位置（Intel Lab有54个传感器节点）
        unique_nodes = {}
        for record in self.real_data[:1000]:  # 使用前1000条记录获取节点信息
            node_id = record['node_id']
            if node_id not in unique_nodes and len(unique_nodes) < n_nodes:
                # 基于节点ID生成确定性位置（模拟真实部署）
                np.random.seed(node_id)
                x = np.random.uniform(10, 190)
                y = np.random.uniform(10, 190)
                unique_nodes[node_id] = (x, y)
        
        # 创建节点对象
        nodes = []
        for i, (node_id, (x, y)) in enumerate(unique_nodes.items()):
            # 基于真实数据的初始能量（考虑节点类型差异）
            initial_energy = 2.0 + np.random.normal(0, 0.1)  # 2J ± 0.1J
            initial_energy = max(1.5, min(2.5, initial_energy))  # 限制范围
            
            node = EnhancedNode(i, x, y, initial_energy)
            nodes.append(node)
        
        print(f"📍 基于真实数据创建了 {len(nodes)} 个网络节点")
        return nodes
    
    def create_synthetic_network(self, n_nodes: int, area_size: int = 200) -> List[EnhancedNode]:
        """创建合成网络节点"""
        nodes = []
        np.random.seed(42)  # 确保可重复性
        
        for i in range(n_nodes):
            x = np.random.uniform(10, area_size - 10)
            y = np.random.uniform(10, area_size - 10)
            initial_energy = 2.0  # 标准初始能量
            
            node = EnhancedNode(i, x, y, initial_energy)
            nodes.append(node)
        
        print(f"🔧 创建了 {n_nodes} 个合成网络节点")
        return nodes
    
    def test_enhanced_eehfr_variants(self, nodes: List[EnhancedNode]) -> Dict:
        """测试Enhanced EEHFR的不同变体"""
        base_station = (100, 100)
        test_results = {}
        
        # 测试配置
        test_configs = [
            {
                'name': 'Enhanced_EEHFR_Chain',
                'description': '增强型EEHFR（启用链式结构）',
                'chain_enabled': True,
                'cluster_ratio': 0.05
            },
            {
                'name': 'Enhanced_EEHFR_Traditional',
                'description': '增强型EEHFR（传统分簇）',
                'chain_enabled': False,
                'cluster_ratio': 0.05
            },
            {
                'name': 'Enhanced_EEHFR_Adaptive',
                'description': '增强型EEHFR（自适应参数）',
                'chain_enabled': True,
                'cluster_ratio': 0.03  # 更低的初始簇头比例
            }
        ]
        
        for config in test_configs:
            print(f"\n🧪 测试 {config['description']}...")
            
            # 重置节点状态
            test_nodes = []
            for original_node in nodes:
                new_node = EnhancedNode(
                    original_node.node_id, 
                    original_node.x, 
                    original_node.y, 
                    original_node.initial_energy
                )
                test_nodes.append(new_node)
            
            # 创建协议实例
            protocol = EnhancedEEHFR(
                nodes=test_nodes,
                base_station=base_station,
                cluster_ratio=config['cluster_ratio'],
                chain_enabled=config['chain_enabled']
            )
            
            # 运行仿真
            start_time = time.time()
            results = protocol.run_simulation(max_rounds=500)
            simulation_time = time.time() - start_time
            
            # 记录结果
            results['config'] = config
            results['simulation_time'] = simulation_time
            test_results[config['name']] = results
            
            print(f"   ✅ 完成 - 能耗: {results['total_energy_consumed']:.4f}J, "
                  f"生存时间: {results['network_lifetime']} 轮")
        
        return test_results
    
    def compare_with_baselines(self, nodes: List[EnhancedNode]) -> Dict:
        """与基准协议对比"""
        print(f"\n📊 开始与基准协议对比测试...")
        
        # 导入基准协议
        try:
            from baseline_protocols.leach_protocol import LEACHProtocol, LEACHNode
            from baseline_protocols.pegasis_protocol import PEGASISProtocol, PEGASISNode
            from baseline_protocols.heed_protocol import HEEDProtocol, HEEDNode
        except ImportError as e:
            print(f"⚠️  无法导入基准协议: {e}")
            return {}
        
        comparison_results = {}
        base_station = (100, 100)
        
        # 测试基准协议
        baseline_configs = [
            {'name': 'LEACH', 'protocol_class': LEACHProtocol, 'node_class': LEACHNode},
            {'name': 'PEGASIS', 'protocol_class': PEGASISProtocol, 'node_class': PEGASISNode},
            {'name': 'HEED', 'protocol_class': HEEDProtocol, 'node_class': HEEDNode}
        ]
        
        for config in baseline_configs:
            print(f"   测试 {config['name']}...")
            
            # 重置节点状态（转换为基准协议格式）
            test_nodes = []
            node_class = config['node_class']
            for original_node in nodes:
                # 创建基准协议兼容的节点
                new_node = node_class(
                    original_node.node_id,
                    original_node.x,
                    original_node.y,
                    initial_energy=original_node.initial_energy
                )
                test_nodes.append(new_node)
            
            # 运行基准协议
            try:
                protocol = config['protocol_class'](test_nodes, base_station)
                results = protocol.run_simulation(max_rounds=500)
                comparison_results[config['name']] = results
                
                print(f"     ✅ {config['name']} - 能耗: {results['total_energy_consumed']:.4f}J, "
                      f"生存时间: {results['network_lifetime']} 轮")
            except Exception as e:
                print(f"     ❌ {config['name']} 测试失败: {e}")
        
        # 测试Enhanced EEHFR
        print(f"   测试 Enhanced EEHFR...")
        test_nodes = []
        for original_node in nodes:
            new_node = EnhancedNode(
                original_node.node_id,
                original_node.x,
                original_node.y,
                original_node.initial_energy
            )
            test_nodes.append(new_node)
        
        enhanced_protocol = EnhancedEEHFR(
            nodes=test_nodes,
            base_station=base_station,
            cluster_ratio=0.05,
            chain_enabled=True
        )
        
        enhanced_results = enhanced_protocol.run_simulation(max_rounds=500)
        comparison_results['Enhanced_EEHFR'] = enhanced_results
        
        print(f"     ✅ Enhanced EEHFR - 能耗: {enhanced_results['total_energy_consumed']:.4f}J, "
              f"生存时间: {enhanced_results['network_lifetime']} 轮")
        
        return comparison_results
    
    def visualize_results(self, results: Dict, save_path: str = None):
        """可视化测试结果"""
        if not results:
            print("⚠️  没有结果数据可供可视化")
            return
        
        # 创建子图
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Enhanced EEHFR协议性能对比分析', fontsize=16, fontweight='bold')
        
        protocols = list(results.keys())
        
        # 1. 总能耗对比
        energy_consumption = [results[p]['total_energy_consumed'] for p in protocols]
        axes[0, 0].bar(protocols, energy_consumption, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
        axes[0, 0].set_title('总能耗对比 (J)', fontweight='bold')
        axes[0, 0].set_ylabel('能耗 (J)')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 添加数值标签
        for i, v in enumerate(energy_consumption):
            axes[0, 0].text(i, v + max(energy_consumption) * 0.01, f'{v:.3f}', 
                           ha='center', va='bottom', fontweight='bold')
        
        # 2. 网络生存时间对比
        network_lifetime = [results[p]['network_lifetime'] for p in protocols]
        axes[0, 1].bar(protocols, network_lifetime, color=['#FFD93D', '#6BCF7F', '#4D96FF', '#9B59B6'])
        axes[0, 1].set_title('网络生存时间对比 (轮)', fontweight='bold')
        axes[0, 1].set_ylabel('生存时间 (轮)')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 添加数值标签
        for i, v in enumerate(network_lifetime):
            axes[0, 1].text(i, v + max(network_lifetime) * 0.01, f'{v}', 
                           ha='center', va='bottom', fontweight='bold')
        
        # 3. 数据包传输成功率对比
        pdr = [results[p]['packet_delivery_ratio'] * 100 for p in protocols]
        axes[1, 0].bar(protocols, pdr, color=['#FF8A80', '#80CBC4', '#81C784', '#FFB74D'])
        axes[1, 0].set_title('数据包传输成功率对比 (%)', fontweight='bold')
        axes[1, 0].set_ylabel('成功率 (%)')
        axes[1, 0].set_ylim(0, 105)
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 添加数值标签
        for i, v in enumerate(pdr):
            axes[1, 0].text(i, v + 1, f'{v:.1f}%', 
                           ha='center', va='bottom', fontweight='bold')
        
        # 4. 能量效率对比 (计算能量效率：包数/能耗)
        energy_efficiency = []
        for p in protocols:
            if 'energy_efficiency' in results[p]:
                energy_efficiency.append(results[p]['energy_efficiency'])
            else:
                # 计算能量效率：包数/能耗
                packets = results[p]['packets_sent']
                energy = results[p]['total_energy_consumed']
                efficiency = packets / energy if energy > 0 else 0
                energy_efficiency.append(efficiency)

        axes[1, 1].bar(protocols, energy_efficiency, color=['#FFAB91', '#A5D6A7', '#90CAF9', '#CE93D8'])
        axes[1, 1].set_title('能量效率对比 (包/J)', fontweight='bold')
        axes[1, 1].set_ylabel('能量效率 (包/J)')
        axes[1, 1].tick_params(axis='x', rotation=45)

        # 添加数值标签
        for i, v in enumerate(energy_efficiency):
            axes[1, 1].text(i, v + max(energy_efficiency) * 0.01, f'{v:.2f}',
                           ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        
        # 保存图表
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 性能对比图表已保存至: {save_path}")
        
        plt.show()
    
    def save_results(self, results: Dict, filename: str = None):
        """保存测试结果"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_eehfr_test_results_{timestamp}.json"
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        # 转换numpy类型为Python原生类型
        def convert_numpy_types(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj
        
        converted_results = convert_numpy_types(results)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(converted_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 测试结果已保存至: {filepath}")
        return filepath
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("🚀 开始Enhanced EEHFR协议综合性能测试")
        print("=" * 60)
        
        all_results = {}
        
        # 测试不同网络规模
        for i, config in enumerate(self.network_configs):
            print(f"\n📋 测试配置 {i+1}/{len(self.network_configs)}: {config}")
            
            # 创建网络
            if self.use_real_data and config['n_nodes'] <= 54:
                nodes = self.create_network_from_real_data(config['n_nodes'])
            else:
                nodes = self.create_synthetic_network(config['n_nodes'], config['area_size'])
            
            # 测试Enhanced EEHFR变体
            variant_results = self.test_enhanced_eehfr_variants(nodes)
            
            # 与基准协议对比
            comparison_results = self.compare_with_baselines(nodes)
            
            # 合并结果
            config_results = {**variant_results, **comparison_results}
            all_results[f"Config_{i+1}_{config['n_nodes']}nodes"] = {
                'config': config,
                'results': config_results
            }
        
        # 保存结果
        results_file = self.save_results(all_results)
        
        # 可视化最佳配置的结果
        if all_results:
            best_config_key = list(all_results.keys())[0]  # 使用第一个配置进行可视化
            best_results = all_results[best_config_key]['results']
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            chart_path = f"enhanced_eehfr_performance_chart_{timestamp}.png"
            self.visualize_results(best_results, chart_path)
        
        print("\n" + "=" * 60)
        print("✅ Enhanced EEHFR协议综合测试完成!")
        print(f"📊 详细结果请查看: {results_file}")
        
        return all_results

if __name__ == "__main__":
    # 运行测试
    tester = EnhancedEEHFRTester(use_real_data=True)
    results = tester.run_comprehensive_test()
