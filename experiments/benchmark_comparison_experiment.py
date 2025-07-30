#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSN基准协议综合对比实验

对比LEACH、PEGASIS、HEED和Enhanced EEHFR协议的性能
包括多种网络规模和环境条件的测试

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List
import time

from benchmark_protocols import LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, NetworkConfig
from integrated_enhanced_eehfr import EnhancedEEHFRProtocol, EEHFRConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

class BenchmarkExperiment:
    """基准协议对比实验类"""
    
    def __init__(self):
        self.results = []
        self.protocols = ['LEACH', 'PEGASIS', 'HEED', 'Enhanced EEHFR']
        
    def run_single_experiment(self, protocol_name: str, config: NetworkConfig, 
                            energy_model: ImprovedEnergyModel, max_rounds: int = 200) -> Dict:
        """运行单个协议实验"""
        
        print(f"🔬 运行 {protocol_name} 协议实验...")
        start_time = time.time()
        
        if protocol_name == 'LEACH':
            protocol = LEACHProtocol(config, energy_model)
            results = protocol.run_simulation(max_rounds)
            
        elif protocol_name == 'PEGASIS':
            protocol = PEGASISProtocol(config, energy_model)
            results = protocol.run_simulation(max_rounds)
            
        elif protocol_name == 'HEED':
            protocol = HEEDProtocolWrapper(config, energy_model)
            results = protocol.run_simulation(max_rounds)
            
        elif protocol_name == 'Enhanced EEHFR':
            # 创建Enhanced EEHFR配置
            eehfr_config = EEHFRConfig(
                num_nodes=config.num_nodes,
                area_width=config.area_width,
                area_height=config.area_height,
                base_station_x=config.base_station_x,
                base_station_y=config.base_station_y,
                initial_energy=config.initial_energy,
                transmission_range=30.0,
                packet_size=1024
            )
            protocol = EnhancedEEHFRProtocol(eehfr_config, energy_model)
            results = protocol.run_simulation(max_rounds)
        else:
            raise ValueError(f"Unknown protocol: {protocol_name}")
        
        execution_time = time.time() - start_time
        results['execution_time'] = execution_time
        results['protocol'] = protocol_name
        
        print(f"   ✅ 完成，耗时 {execution_time:.2f}s")
        return results
    
    def run_network_size_experiment(self, node_counts: List[int] = [25, 50, 75, 100]):
        """不同网络规模实验"""
        
        print("\n🧪 网络规模对比实验")
        print("=" * 60)
        
        for num_nodes in node_counts:
            print(f"\n📊 测试网络规模: {num_nodes} 节点")
            
            # 创建网络配置
            config = NetworkConfig(
                num_nodes=num_nodes,
                initial_energy=2.0,
                area_width=100,
                area_height=100
            )
            
            # 创建能耗模型
            energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
            
            # 测试所有协议
            for protocol in self.protocols:
                try:
                    result = self.run_single_experiment(protocol, config, energy_model)
                    result['num_nodes'] = num_nodes
                    result['experiment_type'] = 'network_size'
                    self.results.append(result)
                except Exception as e:
                    print(f"   ❌ {protocol} 协议测试失败: {e}")
    
    def run_energy_level_experiment(self, energy_levels: List[float] = [1.0, 1.5, 2.0, 2.5]):
        """不同初始能量实验"""
        
        print("\n🧪 初始能量对比实验")
        print("=" * 60)
        
        for energy in energy_levels:
            print(f"\n🔋 测试初始能量: {energy} J")
            
            # 创建网络配置
            config = NetworkConfig(
                num_nodes=50,
                initial_energy=energy,
                area_width=100,
                area_height=100
            )
            
            # 创建能耗模型
            energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
            
            # 测试所有协议
            for protocol in self.protocols:
                try:
                    result = self.run_single_experiment(protocol, config, energy_model)
                    result['initial_energy'] = energy
                    result['experiment_type'] = 'energy_level'
                    self.results.append(result)
                except Exception as e:
                    print(f"   ❌ {protocol} 协议测试失败: {e}")
    
    def analyze_results(self):
        """分析实验结果"""
        
        if not self.results:
            print("❌ 没有实验结果可分析")
            return
        
        # 转换为DataFrame
        df = pd.DataFrame(self.results)
        
        print("\n📈 实验结果分析")
        print("=" * 60)
        
        # 按协议分组统计
        protocol_stats = df.groupby('protocol').agg({
            'network_lifetime': ['mean', 'std'],
            'total_energy_consumed': ['mean', 'std'],
            'packet_delivery_ratio': ['mean', 'std'],
            'energy_efficiency': ['mean', 'std'],
            'execution_time': ['mean', 'std']
        }).round(3)
        
        print("\n📊 协议性能统计 (均值 ± 标准差):")
        print(protocol_stats)
        
        # 网络规模实验分析
        if 'network_size' in df['experiment_type'].values:
            print("\n📊 网络规模实验结果:")
            size_results = df[df['experiment_type'] == 'network_size']
            size_pivot = size_results.pivot_table(
                values=['network_lifetime', 'energy_efficiency', 'packet_delivery_ratio'],
                index='num_nodes',
                columns='protocol',
                aggfunc='mean'
            ).round(3)
            print(size_pivot)
        
        # 能量水平实验分析
        if 'energy_level' in df['experiment_type'].values:
            print("\n🔋 初始能量实验结果:")
            energy_results = df[df['experiment_type'] == 'energy_level']
            energy_pivot = energy_results.pivot_table(
                values=['network_lifetime', 'energy_efficiency', 'packet_delivery_ratio'],
                index='initial_energy',
                columns='protocol',
                aggfunc='mean'
            ).round(3)
            print(energy_pivot)
        
        return df
    
    def save_results(self, filename: str = "benchmark_results.csv"):
        """保存实验结果"""
        if self.results:
            df = pd.DataFrame(self.results)
            filepath = os.path.join(os.path.dirname(__file__), '..', 'results', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            df.to_csv(filepath, index=False)
            print(f"\n💾 结果已保存到: {filepath}")
        else:
            print("❌ 没有结果可保存")

def main():
    """主函数"""
    
    print("🚀 WSN基准协议综合对比实验")
    print("=" * 80)
    print("对比协议: LEACH, PEGASIS, HEED, Enhanced EEHFR")
    print("实验内容: 网络规模对比、初始能量对比")
    print("=" * 80)
    
    # 创建实验实例
    experiment = BenchmarkExperiment()
    
    # 运行网络规模实验
    experiment.run_network_size_experiment([25, 50, 75])
    
    # 运行能量水平实验
    experiment.run_energy_level_experiment([1.5, 2.0, 2.5])
    
    # 分析结果
    df = experiment.analyze_results()
    
    # 保存结果
    experiment.save_results("benchmark_comparison_2025_01_30.csv")
    
    print("\n🎉 实验完成！")

if __name__ == "__main__":
    main()
