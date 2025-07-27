#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSN路由协议对比实验框架
使用Intel Lab真实数据集对比EEHFR与经典协议的性能

对比协议:
- LEACH (Low-Energy Adaptive Clustering Hierarchy)
- PEGASIS (Power-Efficient Gathering in Sensor Information Systems)  
- HEED (Hybrid Energy-Efficient Distributed clustering)
- EEHFR (Energy-Efficient Hybrid Fuzzy Routing) - 我们的协议

项目路径: EEHFR：融合模糊逻辑与混合元启发式优化的WSN智能节能路由协议/EEHFR_Optimized_v1/
数据源: Intel Berkeley Research Lab数据集 (https://db.csail.mit.edu/labdata/labdata.html)
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import time
import json

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'baseline_protocols'))

# 导入协议实现
from baseline_protocols.leach_protocol import LEACHProtocol, LEACHNode
from baseline_protocols.pegasis_protocol import PEGASISProtocol, PEGASISNode  
from baseline_protocols.heed_protocol import HEEDProtocol, HEEDNode
from intel_dataset_loader import IntelLabDataLoader

class ComparativeExperiment:
    """WSN路由协议对比实验类"""
    
    def __init__(self, data_dir: str = "./data", results_dir: str = "../results"):
        """
        初始化对比实验
        
        参数:
            data_dir: Intel Lab数据集目录
            results_dir: 结果保存目录
        """
        self.data_dir = data_dir
        self.results_dir = results_dir
        
        # 确保结果目录存在
        os.makedirs(results_dir, exist_ok=True)
        
        # 实验参数
        self.network_params = {
            'area_size': 200,  # 网络区域大小 (m x m)
            'n_nodes': 50,     # 节点数量
            'initial_energy': 2.0,  # 初始能量 (J)
            'base_station': (100, 200),  # 基站位置
            'max_rounds': 1000,  # 最大仿真轮数
            'n_experiments': 5   # 重复实验次数
        }
        
        # 加载Intel Lab数据集
        self.load_intel_data()
        
        print(f"🔬 对比实验初始化完成")
        print(f"   数据目录: {data_dir}")
        print(f"   结果目录: {results_dir}")
        print(f"   网络参数: {self.network_params}")
    
    def load_intel_data(self):
        """加载Intel Lab数据集"""
        print("📂 加载Intel Lab数据集...")
        
        self.data_loader = IntelLabDataLoader(
            data_dir=self.data_dir, 
            use_synthetic=False
        )
        
        if self.data_loader.sensor_data is None or self.data_loader.sensor_data.empty:
            raise ValueError("❌ Intel Lab数据集加载失败")
        
        print(f"✅ 成功加载 {len(self.data_loader.sensor_data):,} 条真实数据记录")
        
        # 提取节点位置信息
        self.real_node_positions = {}
        if self.data_loader.locations_data is not None:
            for _, row in self.data_loader.locations_data.iterrows():
                self.real_node_positions[int(row['node_id'])] = (row['x'], row['y'])
        
        print(f"✅ 提取了 {len(self.real_node_positions)} 个节点的真实位置")
    
    def generate_network_topology(self, protocol_type: str) -> List:
        """
        生成网络拓扑
        
        参数:
            protocol_type: 协议类型 ('LEACH', 'PEGASIS', 'HEED', 'EEHFR')
        
        返回:
            节点列表
        """
        nodes = []
        
        # 使用真实的Intel Lab节点位置（如果可用）
        if self.real_node_positions and len(self.real_node_positions) >= self.network_params['n_nodes']:
            node_positions = list(self.real_node_positions.items())[:self.network_params['n_nodes']]
        else:
            # 生成随机位置
            node_positions = []
            for i in range(self.network_params['n_nodes']):
                x = np.random.uniform(0, self.network_params['area_size'])
                y = np.random.uniform(0, self.network_params['area_size'])
                node_positions.append((i+1, (x, y)))
        
        # 根据协议类型创建节点
        for node_id, (x, y) in node_positions:
            if protocol_type == 'LEACH':
                node = LEACHNode(node_id, x, y, self.network_params['initial_energy'])
            elif protocol_type == 'PEGASIS':
                node = PEGASISNode(node_id, x, y, self.network_params['initial_energy'])
            elif protocol_type == 'HEED':
                node = HEEDNode(node_id, x, y, self.network_params['initial_energy'])
            else:
                raise ValueError(f"不支持的协议类型: {protocol_type}")
            
            nodes.append(node)
        
        return nodes
    
    def run_protocol_experiment(self, protocol_name: str) -> Dict:
        """
        运行单个协议的实验
        
        参数:
            protocol_name: 协议名称
        
        返回:
            实验结果字典
        """
        print(f"\n🚀 开始 {protocol_name} 协议实验")
        print("=" * 50)
        
        all_results = []
        
        for exp_num in range(self.network_params['n_experiments']):
            print(f"📊 实验 {exp_num + 1}/{self.network_params['n_experiments']}")
            
            # 生成网络拓扑
            nodes = self.generate_network_topology(protocol_name)
            
            # 创建协议实例
            if protocol_name == 'LEACH':
                protocol = LEACHProtocol(
                    nodes=nodes,
                    base_station=self.network_params['base_station'],
                    desired_ch_percentage=0.05
                )
            elif protocol_name == 'PEGASIS':
                protocol = PEGASISProtocol(
                    nodes=nodes,
                    base_station=self.network_params['base_station']
                )
            elif protocol_name == 'HEED':
                protocol = HEEDProtocol(
                    nodes=nodes,
                    base_station=self.network_params['base_station'],
                    c_prob=0.05,
                    cluster_radius=50.0
                )
            else:
                raise ValueError(f"不支持的协议: {protocol_name}")
            
            # 运行仿真
            start_time = time.time()
            results = protocol.run_simulation(self.network_params['max_rounds'])
            end_time = time.time()
            
            results['experiment_id'] = exp_num + 1
            results['execution_time'] = end_time - start_time
            all_results.append(results)
            
            print(f"   ✅ 实验{exp_num + 1}完成: 生存时间={results['network_lifetime']}轮, "
                  f"能耗={results['total_energy_consumed']:.3f}J")
        
        # 计算平均结果
        avg_results = self.calculate_average_results(all_results, protocol_name)
        
        print(f"\n📊 {protocol_name} 平均性能:")
        print(f"   网络生存时间: {avg_results['avg_network_lifetime']:.1f} ± {avg_results['std_network_lifetime']:.1f} 轮")
        print(f"   总能耗: {avg_results['avg_total_energy']:.3f} ± {avg_results['std_total_energy']:.3f} J")
        print(f"   数据传输成功率: {avg_results['avg_packet_delivery_ratio']*100:.1f} ± {avg_results['std_packet_delivery_ratio']*100:.1f}%")
        
        return {
            'protocol_name': protocol_name,
            'individual_results': all_results,
            'average_results': avg_results
        }
    
    def calculate_average_results(self, results_list: List[Dict], protocol_name: str) -> Dict:
        """计算多次实验的平均结果"""
        metrics = [
            'network_lifetime', 'total_energy_consumed', 'packet_delivery_ratio',
            'packets_sent', 'packets_received', 'dead_nodes', 'total_rounds'
        ]
        
        avg_results = {'protocol_name': protocol_name}
        
        for metric in metrics:
            values = [r[metric] for r in results_list]
            avg_results[f'avg_{metric}'] = np.mean(values)
            avg_results[f'std_{metric}'] = np.std(values)
            avg_results[f'min_{metric}'] = np.min(values)
            avg_results[f'max_{metric}'] = np.max(values)

            # 添加兼容性别名
            if metric == 'total_energy_consumed':
                avg_results['avg_total_energy'] = avg_results['avg_total_energy_consumed']
                avg_results['std_total_energy'] = avg_results['std_total_energy_consumed']
        
        return avg_results
    
    def run_comparative_experiment(self) -> Dict:
        """运行完整的对比实验"""
        print("🔬 开始WSN路由协议对比实验")
        print("=" * 80)
        print(f"📋 实验配置:")
        print(f"   数据源: Intel Berkeley Research Lab数据集")
        print(f"   网络规模: {self.network_params['n_nodes']} 节点")
        print(f"   网络区域: {self.network_params['area_size']}m × {self.network_params['area_size']}m")
        print(f"   重复次数: {self.network_params['n_experiments']} 次")
        print(f"   最大轮数: {self.network_params['max_rounds']} 轮")
        
        # 要对比的协议列表
        protocols = ['LEACH', 'PEGASIS', 'HEED']
        
        all_experiment_results = {}
        
        # 运行每个协议的实验
        for protocol in protocols:
            try:
                results = self.run_protocol_experiment(protocol)
                all_experiment_results[protocol] = results
            except Exception as e:
                print(f"❌ {protocol} 协议实验失败: {e}")
                continue
        
        # 保存实验结果
        self.save_results(all_experiment_results)
        
        # 生成对比分析
        self.generate_comparative_analysis(all_experiment_results)
        
        print("\n✅ 对比实验完成！")
        print(f"📁 结果已保存到: {self.results_dir}")
        
        return all_experiment_results
    
    def save_results(self, results: Dict):
        """保存实验结果"""
        # 保存详细结果为JSON
        results_file = os.path.join(self.results_dir, "comparative_experiment_results.json")
        
        # 转换numpy类型为Python原生类型
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        # 递归转换所有numpy类型
        def deep_convert(data):
            if isinstance(data, dict):
                return {k: deep_convert(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [deep_convert(item) for item in data]
            else:
                return convert_numpy(data)
        
        converted_results = deep_convert(results)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(converted_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 详细结果已保存: {results_file}")
        
        # 保存汇总表格
        summary_data = []
        for protocol, data in results.items():
            avg_results = data['average_results']
            summary_data.append({
                '协议': protocol,
                '网络生存时间(轮)': f"{avg_results['avg_network_lifetime']:.1f} ± {avg_results['std_network_lifetime']:.1f}",
                '总能耗(J)': f"{avg_results['avg_total_energy_consumed']:.3f} ± {avg_results['std_total_energy_consumed']:.3f}",
                '数据传输成功率(%)': f"{avg_results['avg_packet_delivery_ratio']*100:.1f} ± {avg_results['std_packet_delivery_ratio']*100:.1f}",
                '死亡节点数': f"{avg_results['avg_dead_nodes']:.1f} ± {avg_results['std_dead_nodes']:.1f}"
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_file = os.path.join(self.results_dir, "performance_summary.csv")
        summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
        
        print(f"📊 性能汇总已保存: {summary_file}")
    
    def generate_comparative_analysis(self, results: Dict):
        """生成对比分析图表"""
        print("\n📈 生成对比分析图表...")
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建对比图表
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('WSN路由协议性能对比分析\n(基于Intel Lab真实数据集)', 
                     fontsize=16, fontweight='bold')
        
        protocols = list(results.keys())
        colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12'][:len(protocols)]
        
        # 1. 网络生存时间对比
        ax1 = axes[0, 0]
        lifetimes = [results[p]['average_results']['avg_network_lifetime'] for p in protocols]
        lifetime_stds = [results[p]['average_results']['std_network_lifetime'] for p in protocols]
        
        bars1 = ax1.bar(protocols, lifetimes, yerr=lifetime_stds, 
                       color=colors, alpha=0.8, capsize=5)
        ax1.set_title('网络生存时间对比', fontweight='bold')
        ax1.set_ylabel('生存时间 (轮)')
        ax1.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, lifetime in zip(bars1, lifetimes):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                    f'{lifetime:.0f}', ha='center', va='bottom', fontweight='bold')
        
        # 2. 总能耗对比
        ax2 = axes[0, 1]
        energies = [results[p]['average_results']['avg_total_energy_consumed'] for p in protocols]
        energy_stds = [results[p]['average_results']['std_total_energy_consumed'] for p in protocols]
        
        bars2 = ax2.bar(protocols, energies, yerr=energy_stds,
                       color=colors, alpha=0.8, capsize=5)
        ax2.set_title('总能耗对比', fontweight='bold')
        ax2.set_ylabel('总能耗 (J)')
        ax2.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, energy in zip(bars2, energies):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{energy:.3f}', ha='center', va='bottom', fontweight='bold')
        
        # 3. 数据传输成功率对比
        ax3 = axes[1, 0]
        pdrs = [results[p]['average_results']['avg_packet_delivery_ratio']*100 for p in protocols]
        pdr_stds = [results[p]['average_results']['std_packet_delivery_ratio']*100 for p in protocols]
        
        bars3 = ax3.bar(protocols, pdrs, yerr=pdr_stds,
                       color=colors, alpha=0.8, capsize=5)
        ax3.set_title('数据传输成功率对比', fontweight='bold')
        ax3.set_ylabel('传输成功率 (%)')
        ax3.set_ylim(0, 105)
        ax3.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, pdr in zip(bars3, pdrs):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{pdr:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # 4. 综合性能雷达图
        ax4 = axes[1, 1]
        ax4.remove()  # 移除原轴
        ax4 = fig.add_subplot(2, 2, 4, projection='polar')

        # 标准化指标 (越高越好)
        metrics = ['网络生存时间', '能量效率', '传输成功率']
        angles = np.linspace(0, 2*np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]

        for i, protocol in enumerate(protocols):
            # 标准化数值 (0-1)
            lifetime_norm = results[protocol]['average_results']['avg_network_lifetime'] / max(lifetimes) if max(lifetimes) > 0 else 0
            energy_eff_norm = (max(energies) - results[protocol]['average_results']['avg_total_energy_consumed']) / max(energies) if max(energies) > 0 else 0
            pdr_norm = results[protocol]['average_results']['avg_packet_delivery_ratio']

            values = [lifetime_norm, energy_eff_norm, pdr_norm]
            values += values[:1]  # 闭合图形

            ax4.plot(angles, values, 'o-', linewidth=2, label=protocol, color=colors[i])
            ax4.fill(angles, values, alpha=0.25, color=colors[i])

        ax4.set_xticks(angles[:-1])
        ax4.set_xticklabels(metrics)
        ax4.set_ylim(0, 1)
        ax4.set_title('综合性能对比', fontweight='bold', pad=20)
        ax4.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        plt.tight_layout()
        
        # 保存图表
        chart_file = os.path.join(self.results_dir, "comparative_analysis.png")
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"📊 对比分析图表已保存: {chart_file}")
        
        plt.show()

def main():
    """主函数"""
    print("🔬 WSN路由协议对比实验")
    print("=" * 80)
    
    # 创建实验实例
    experiment = ComparativeExperiment(
        data_dir="./data",
        results_dir="../results"
    )
    
    # 运行对比实验
    results = experiment.run_comparative_experiment()
    
    print("\n🎯 实验总结:")
    for protocol, data in results.items():
        avg_results = data['average_results']
        print(f"   {protocol}: 生存时间={avg_results['avg_network_lifetime']:.1f}轮, "
              f"能耗={avg_results['avg_total_energy_consumed']:.3f}J")

if __name__ == "__main__":
    main()
