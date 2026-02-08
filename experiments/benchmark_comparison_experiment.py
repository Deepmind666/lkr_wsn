#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSN基准协议综合对比实验

对比 LEACH、PEGASIS、HEED 与 AERIS 协议的性能，
覆盖多种网络规模和环境条件的测试。

作者: AERIS Research Team
日期: 2025-01-30
版本: 1.1 (EEHFR 引用移除)
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
import tracemalloc
import random
import numpy as np
import concurrent.futures as cf

from benchmark_protocols import LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, NetworkConfig
from aeris_protocol import AerisProtocol
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

# 模块级并行子任务（Windows spawn 可pickle）
def _run_task(task: Dict) -> Dict:
    protocol_name: str = task['protocol']
    num_nodes: int = task['num_nodes']
    seed: int = task['seed']
    max_rounds: int = task.get('max_rounds', 800)

    # 设定随机种子，确保可复现（在子进程内独立设置）
    random.seed(seed)
    np.random.seed(seed)

    # 创建网络配置与能耗模型
    config = NetworkConfig(
        num_nodes=num_nodes,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    # 运行单个协议实验（与原逻辑保持一致）
    start_time = time.time()
    tracemalloc.start()

    if protocol_name == 'LEACH':
        protocol = LEACHProtocol(config, energy_model)
        results = protocol.run_simulation(max_rounds)
    elif protocol_name == 'PEGASIS':
        protocol = PEGASISProtocol(config, energy_model)
        results = protocol.run_simulation(max_rounds)
    elif protocol_name == 'HEED':
        protocol = HEEDProtocolWrapper(config, energy_model)
        results = protocol.run_simulation(max_rounds)
    elif protocol_name == 'AERIS-E':
        protocol = AerisProtocol(
            config, profile='energy', enable_cas=True, enable_fairness=True,
            enable_gateway=True, enable_skeleton=False, verbose=False
        )
        results = protocol.run_simulation(max_rounds)
    elif protocol_name == 'AERIS-R':
        protocol = AerisProtocol(
            config, profile='robust', enable_cas=True, enable_fairness=True,
            enable_gateway=True, enable_skeleton=False, verbose=False
        )
        results = protocol.run_simulation(max_rounds)
    else:
        tracemalloc.stop()
        raise ValueError(f"Unknown protocol: {protocol_name}")

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    execution_time = time.time() - start_time
    results['execution_time'] = execution_time
    results['peak_memory_bytes'] = int(peak)
    results['protocol'] = protocol_name

    # 标注实验元数据（供聚合分析使用）
    results['num_nodes'] = num_nodes
    results['seed'] = seed
    results['experiment_type'] = 'network_size'

    return results

class BenchmarkExperiment:
    """基准协议对比实验类"""
    
    def __init__(self):
        self.results = []
        # 统一命名：基线 + 我们方法的两种运行姿态（AERIS-E/AERIS-R）
        self.protocols = ['LEACH', 'PEGASIS', 'HEED', 'AERIS-E', 'AERIS-R']
        
    def run_single_experiment(self, protocol_name: str, config: NetworkConfig, 
                            energy_model: ImprovedEnergyModel, max_rounds: int = 800) -> Dict:
        """运行单个协议实验"""
        
        print(f"🔬 运行 {protocol_name} 协议实验（max_rounds={max_rounds}）...")
        start_time = time.time()
        tracemalloc.start()
        
        if protocol_name == 'LEACH':
            protocol = LEACHProtocol(config, energy_model)
            results = protocol.run_simulation(max_rounds)
            
        elif protocol_name == 'PEGASIS':
            protocol = PEGASISProtocol(config, energy_model)
            results = protocol.run_simulation(max_rounds)
            
        elif protocol_name == 'HEED':
            protocol = HEEDProtocolWrapper(config, energy_model)
            results = protocol.run_simulation(max_rounds)
            
        elif protocol_name == 'AERIS-E':
            # 我们方法（能耗优先）
            protocol = AerisProtocol(
                config, profile='energy', enable_cas=True, enable_fairness=True,
                enable_gateway=True, enable_skeleton=False, verbose=False
            )
            results = protocol.run_simulation(max_rounds)
            
        elif protocol_name == 'AERIS-R':
            # 我们方法（鲁棒优先）
            protocol = AerisProtocol(
                config, profile='robust', enable_cas=True, enable_fairness=True,
                enable_gateway=True, enable_skeleton=False, verbose=False
            )
            results = protocol.run_simulation(max_rounds)
        else:
            tracemalloc.stop()
            raise ValueError(f"Unknown protocol: {protocol_name}")
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        execution_time = time.time() - start_time
        results['execution_time'] = execution_time
        results['peak_memory_bytes'] = int(peak)
        results['protocol'] = protocol_name
        
        print(f"   ✅ 完成，耗时 {execution_time:.2f}s，峰值内存 {peak/1024/1024:.2f} MB")
        return results
    
    def run_network_size_experiment(self, node_counts: List[int] = [50, 100, 150],
                                    seeds: List[int] = [11, 22, 33],
                                    max_rounds: int = 800):
        """不同网络规模实验（多随机种子以增强可信度）"""
        
        print("\n🧪 网络规模对比实验（多随机种子）")
        print("=" * 60)
        print(f"节点数量: {node_counts} | 种子: {seeds} | 轮数上限: {max_rounds}")

        # 组装任务列表
        tasks = []
        for num_nodes in node_counts:
            for seed in seeds:
                for protocol in self.protocols:
                    tasks.append({
                        'protocol': protocol,
                        'num_nodes': num_nodes,
                        'seed': seed,
                        'max_rounds': max_rounds,
                    })
        print(f"⚙️ 计划总任务数: {len(tasks)}，并行度: {os.cpu_count()} (ProcessPool)")

        # 并行执行（使用模块级_worker函数，避免NameError/不可pickle）
        with cf.ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
            futures = [ex.submit(_run_task, t) for t in tasks]
            for i, fut in enumerate(cf.as_completed(futures), 1):
                try:
                    result = fut.result()
                    self.results.append(result)
                    print(f"   ✅ 完成任务 {i}/{len(tasks)}: {result['protocol']} | N={result['num_nodes']} | seed={result['seed']} | 耗时 {result['execution_time']:.2f}s")
                except Exception as e:
                    print(f"   ❌ 任务失败: {e}")
    
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
            'execution_time': ['mean', 'std'],
            'peak_memory_bytes': ['mean', 'std']
        }).round(3)
        
        print("\n📊 协议性能统计 (均值 ± 标准差):")
        print(protocol_stats)
        
        # 网络规模实验分析
        if 'network_size' in df['experiment_type'].values:
            print("\n📊 网络规模实验结果:")
            size_results = df[df['experiment_type'] == 'network_size']
            size_pivot = size_results.pivot_table(
                values=['network_lifetime', 'energy_efficiency', 'packet_delivery_ratio', 'execution_time', 'peak_memory_bytes'],
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
                values=['network_lifetime', 'energy_efficiency', 'packet_delivery_ratio', 'execution_time', 'peak_memory_bytes'],
                index='initial_energy',
                columns='protocol',
                aggfunc='mean'
            ).round(3)
            print(energy_pivot)
        
        return df
    
    def save_results(self, filename: str = "scalability_minimal_results.csv"):
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
    print("对比协议: LEACH, PEGASIS, HEED, AERIS-E, AERIS-R")
    print("实验内容: 网络规模对比 (N=50/100/150), 多随机种子(3)，每组最大800轮")
    print("=" * 80)
    
    # 创建实验实例
    experiment = BenchmarkExperiment()
    
    # 运行网络规模实验（800轮，3个随机种子）
    experiment.run_network_size_experiment([50, 100, 150], seeds=[11, 22, 33], max_rounds=800)
    
    # 分析结果
    df = experiment.analyze_results()
    
    # 保存结果（带有设定标识，避免混淆）
    experiment.save_results("scalability_aeris_800_3seeds.csv")
    
    print("\n🎉 实验完成！")

if __name__ == "__main__":
    main()
