#!/usr/bin/env python3
"""
多环境WSN实验数据收集与验证脚本
基于文献调研的现实环境建模参数验证

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0

功能:
1. 收集多种环境下的WSN性能数据
2. 验证现实信道模型的准确性
3. 生成环境对比分析报告
4. 为协议优化提供数据支撑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import json
from datetime import datetime
from typing import Dict

# 直接导入避免__init__.py的依赖问题
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from realistic_channel_model import (
    LogNormalShadowingModel,
    IEEE802154LinkQuality,
    InterferenceModel,
    EnvironmentalFactors,
    RealisticChannelModel,
    EnvironmentType
)

class MultiEnvironmentDataCollector:
    """多环境WSN数据收集器"""
    
    def __init__(self):
        self.environments = [
            EnvironmentType.INDOOR_OFFICE,
            EnvironmentType.INDOOR_FACTORY, 
            EnvironmentType.INDOOR_RESIDENTIAL,
            EnvironmentType.OUTDOOR_OPEN,
            EnvironmentType.OUTDOOR_SUBURBAN,
            EnvironmentType.OUTDOOR_URBAN
        ]
        
        self.distance_range = np.linspace(1, 50, 50)  # 1-50米
        self.results = {}
        
    def collect_environment_data(self, env_type: EnvironmentType, num_samples: int = 1000) -> Dict:
        """收集特定环境的实验数据"""
        print(f"📊 收集 {env_type.value} 环境数据...")
        
        # 初始化模型
        channel_model = RealisticChannelModel(env_type)
        
        # 数据收集
        data = {
            'distances': [],
            'rssi_values': [],
            'lqi_values': [],
            'pdr_values': [],
            'path_loss': [],
            'sinr_values': []  # 修正为sinr_values
        }
        
        for distance in self.distance_range:
            for _ in range(num_samples // len(self.distance_range)):
                # 计算信道指标
                metrics = channel_model.calculate_link_metrics(
                    tx_power_dbm=0.0,  # 标准发射功率
                    distance=distance,
                    temperature_c=25.0,  # 标准温度
                    humidity_ratio=0.5   # 标准湿度
                )
                
                data['distances'].append(distance)
                data['rssi_values'].append(metrics['rssi_dbm'])
                data['lqi_values'].append(metrics['lqi'])
                data['pdr_values'].append(metrics['pdr'])
                data['path_loss'].append(metrics['path_loss_db'])
                data['sinr_values'].append(metrics['sinr_db'])  # 修正为sinr_db
        
        return data
    
    def collect_all_environments(self) -> Dict:
        """收集所有环境的数据"""
        print("🔬 开始多环境数据收集实验...")
        
        for env_type in self.environments:
            self.results[env_type.value] = self.collect_environment_data(env_type)
            
        print("✅ 数据收集完成!")
        return self.results
    
    def analyze_environment_differences(self) -> Dict:
        """分析环境间的性能差异"""
        print("📈 分析环境性能差异...")
        
        analysis = {}
        
        for env_name, data in self.results.items():
            # 计算统计指标
            analysis[env_name] = {
                'mean_rssi': np.mean(data['rssi_values']),
                'std_rssi': np.std(data['rssi_values']),
                'mean_pdr': np.mean(data['pdr_values']),
                'std_pdr': np.std(data['pdr_values']),
                'mean_path_loss': np.mean(data['path_loss']),
                'communication_range': self._estimate_communication_range(data),
                'reliability_score': self._calculate_reliability_score(data)
            }
        
        return analysis
    
    def _estimate_communication_range(self, data: Dict) -> float:
        """估算通信范围（PDR > 0.8的最大距离）"""
        df = pd.DataFrame(data)
        reliable_links = df[df['pdr_values'] > 0.8]
        return reliable_links['distances'].max() if len(reliable_links) > 0 else 0.0
    
    def _calculate_reliability_score(self, data: Dict) -> float:
        """计算可靠性评分（0-100）"""
        df = pd.DataFrame(data)
        # 基于PDR和RSSI的综合评分
        pdr_score = np.mean(df['pdr_values']) * 50
        rssi_score = min(50, max(0, (np.mean(df['rssi_values']) + 80) / 2 * 50))
        return pdr_score + rssi_score
    
    def generate_comparison_plots(self, save_dir: str = "results"):
        """生成环境对比图表"""
        print("📊 生成环境对比图表...")
        
        os.makedirs(save_dir, exist_ok=True)
        
        # 设置图表样式
        plt.style.use('default')
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        
        # 1. RSSI vs Distance 对比
        plt.figure(figsize=(12, 8))
        for env_name, data in self.results.items():
            df = pd.DataFrame(data)
            # 按距离分组计算平均值
            grouped = df.groupby('distances').mean()
            plt.plot(grouped.index, grouped['rssi_values'], 
                    label=env_name.replace('_', ' ').title(), 
                    linewidth=2, marker='o', markersize=4)
        
        plt.xlabel('Distance (m)', fontsize=12)
        plt.ylabel('RSSI (dBm)', fontsize=12)
        plt.title('RSSI vs Distance: Multi-Environment Comparison', fontsize=14, fontweight='bold')
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"{save_dir}/rssi_distance_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. PDR vs Distance 对比
        plt.figure(figsize=(12, 8))
        for env_name, data in self.results.items():
            df = pd.DataFrame(data)
            grouped = df.groupby('distances').mean()
            plt.plot(grouped.index, grouped['pdr_values'], 
                    label=env_name.replace('_', ' ').title(),
                    linewidth=2, marker='s', markersize=4)
        
        plt.xlabel('Distance (m)', fontsize=12)
        plt.ylabel('Packet Delivery Rate', fontsize=12)
        plt.title('PDR vs Distance: Multi-Environment Comparison', fontsize=14, fontweight='bold')
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.ylim(0, 1)
        plt.tight_layout()
        plt.savefig(f"{save_dir}/pdr_distance_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 图表已保存到 {save_dir}/ 目录")
    
    def save_results(self, filename: str = None):
        """保存实验结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results/multi_environment_data_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # 转换numpy数组为列表以便JSON序列化
        serializable_results = {}
        for env_name, data in self.results.items():
            serializable_results[env_name] = {
                key: [float(x) for x in values] if isinstance(values, np.ndarray) else values
                for key, values in data.items()
            }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'experiment_info': {
                    'description': '多环境WSN性能数据收集实验',
                    'environments': [env.value for env in self.environments],
                    'distance_range': f"1-{max(self.distance_range)}m",
                    'samples_per_distance': 1000 // len(self.distance_range)
                },
                'results': serializable_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"💾 实验结果已保存到: {filename}")

def main():
    """主函数"""
    print("🚀 启动多环境WSN数据收集实验")
    print("=" * 60)
    
    # 创建数据收集器
    collector = MultiEnvironmentDataCollector()
    
    # 收集数据
    results = collector.collect_all_environments()
    
    # 分析差异
    analysis = collector.analyze_environment_differences()
    
    # 打印分析结果
    print("\n📊 环境性能分析结果:")
    print("-" * 60)
    for env_name, metrics in analysis.items():
        print(f"\n🏢 {env_name.replace('_', ' ').title()}:")
        print(f"  平均RSSI: {metrics['mean_rssi']:.1f} ± {metrics['std_rssi']:.1f} dBm")
        print(f"  平均PDR: {metrics['mean_pdr']:.3f} ± {metrics['std_pdr']:.3f}")
        print(f"  通信范围: {metrics['communication_range']:.1f} m")
        print(f"  可靠性评分: {metrics['reliability_score']:.1f}/100")
    
    # 生成图表
    collector.generate_comparison_plots()
    
    # 保存结果
    collector.save_results()
    
    print("\n✅ 多环境数据收集实验完成!")
    print("📈 请查看生成的图表和数据文件")

if __name__ == "__main__":
    main()
