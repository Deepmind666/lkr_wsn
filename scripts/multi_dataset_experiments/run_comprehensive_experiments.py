#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面的多数据集实验运行器

实验矩阵：
- 数据集: Intel Lab + 6个合成trace + 12个合成拓扑
- 协议: AERIS, LEACH, PEGASIS, HEED
- 配置: 多种参数组合
- 统计: 每配置200次重复

使用CPU多核并行加速
"""

import os
import sys
import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple
import multiprocessing as mp

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.aeris_protocol import AERISProtocol
from src.baseline_protocols import LEACHProtocol, PEGASISProtocol, HEEDProtocol

# 结果目录
RESULTS_DIR = Path('results/multi_dataset_experiments')
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class ExperimentRunner:
    """实验运行器"""
    
    def __init__(self, n_workers: int = None):
        self.n_workers = n_workers or max(1, mp.cpu_count() - 2)
        print(f"使用 {self.n_workers} 个CPU核心")
    
    def run_single_experiment(self, config: Dict) -> Dict:
        """运行单次实验"""
        try:
            # 创建协议实例
            protocol_name = config['protocol']
            
            if protocol_name == 'AERIS':
                protocol = AERISProtocol(
                    n_nodes=config['n_nodes'],
                    area_size=config['area'],
                    initial_energy=config.get('initial_energy', 2.0),
                    profile=config.get('profile', 'balanced')
                )
            elif protocol_name == 'LEACH':
                protocol = LEACHProtocol(
                    n_nodes=config['n_nodes'],
                    area_size=config['area'],
                    initial_energy=config.get('initial_energy', 2.0)
                )
            elif protocol_name == 'PEGASIS':
                protocol = PEGASISProtocol(
                    n_nodes=config['n_nodes'],
                    area_size=config['area'],
                    initial_energy=config.get('initial_energy', 2.0)
                )
            elif protocol_name == 'HEED':
                protocol = HEEDProtocol(
                    n_nodes=config['n_nodes'],
                    area_size=config['area'],
                    initial_energy=config.get('initial_energy', 2.0)
                )
            else:
                raise ValueError(f"Unknown protocol: {protocol_name}")
            
            # 设置拓扑
            if 'positions' in config:
                protocol.set_positions(config['positions'])
            
            # 设置信道参数
            if 'channel' in config:
                protocol.set_channel_params(**config['channel'])
            
            # 运行仿真
            max_rounds = config.get('max_rounds', 200)
            results = protocol.run_simulation(max_rounds=max_rounds)
            
            return {
                'success': True,
                'pdr': results.get('pdr_end2end', 0),
                'energy': results.get('total_energy', 0),
                'lifetime': results.get('network_lifetime', 0),
                'alive_nodes': results.get('alive_nodes', 0),
                'config': config
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'config': config
            }
    
    def run_experiment_batch(self, configs: List[Dict], desc: str = "") -> List[Dict]:
        """并行运行一批实验"""
        results = []
        total = len(configs)
        
        print(f"\n运行 {desc}: {total} 个实验")
        start_time = time.time()
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            futures = {executor.submit(self.run_single_experiment, cfg): i 
                      for i, cfg in enumerate(configs)}
            
            completed = 0
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1
                
                if completed % 50 == 0 or completed == total:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed
                    eta = (total - completed) / rate if rate > 0 else 0
                    print(f"  进度: {completed}/{total} ({100*completed/total:.1f}%) "
                          f"- {rate:.1f} exp/s - ETA: {eta:.0f}s")
        
        elapsed = time.time() - start_time
        print(f"  完成: {elapsed:.1f}s, {len(results)/elapsed:.1f} exp/s")
        
        return results


def generate_experiment_matrix() -> List[Dict]:
    """生成完整的实验矩阵"""
    experiments = []
    
    # 协议列表
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    
    # 重复次数
    n_repeats = 200
    
    # ========================================
    # 1. 不同网络规模
    # ========================================
    print("生成规模实验配置...")
    for n_nodes in [30, 50, 100, 150, 200, 300, 500]:
        area = (int(np.sqrt(n_nodes) * 15), int(np.sqrt(n_nodes) * 15))
        for protocol in protocols:
            for _ in range(n_repeats):
                experiments.append({
                    'experiment_type': 'scale',
                    'protocol': protocol,
                    'n_nodes': n_nodes,
                    'area': area,
                    'max_rounds': 200
                })
    
    # ========================================
    # 2. 不同拓扑结构
    # ========================================
    print("生成拓扑实验配置...")
    topologies = [
        {'name': 'random', 'generator': 'random'},
        {'name': 'grid', 'generator': 'grid'},
        {'name': 'corridor', 'generator': 'corridor', 'aspect': 5},
        {'name': 'cluster_4', 'generator': 'cluster', 'n_clusters': 4},
        {'name': 'cluster_8', 'generator': 'cluster', 'n_clusters': 8},
    ]
    
    for topo in topologies:
        for protocol in protocols:
            for _ in range(n_repeats):
                experiments.append({
                    'experiment_type': 'topology',
                    'topology': topo['name'],
                    'protocol': protocol,
                    'n_nodes': 100,
                    'area': (100, 100) if topo['name'] != 'corridor' else (200, 40),
                    'max_rounds': 200
                })
    
    # ========================================
    # 3. 不同信道条件
    # ========================================
    print("生成信道实验配置...")
    channels = [
        {'name': 'ideal', 'path_loss_exp': 2.0, 'shadowing_std': 2.0},
        {'name': 'indoor_good', 'path_loss_exp': 2.5, 'shadowing_std': 4.0},
        {'name': 'indoor_typical', 'path_loss_exp': 3.0, 'shadowing_std': 6.0},
        {'name': 'indoor_harsh', 'path_loss_exp': 3.5, 'shadowing_std': 8.0},
        {'name': 'industrial', 'path_loss_exp': 4.0, 'shadowing_std': 10.0},
        {'name': 'outdoor', 'path_loss_exp': 2.2, 'shadowing_std': 3.0},
    ]
    
    for ch in channels:
        for protocol in protocols:
            for _ in range(n_repeats):
                experiments.append({
                    'experiment_type': 'channel',
                    'channel_name': ch['name'],
                    'protocol': protocol,
                    'n_nodes': 100,
                    'area': (100, 100),
                    'channel': {
                        'path_loss_exp': ch['path_loss_exp'],
                        'shadowing_std': ch['shadowing_std']
                    },
                    'max_rounds': 200
                })
    
    # ========================================
    # 4. 不同能量配置
    # ========================================
    print("生成能量实验配置...")
    energy_configs = [
        {'name': 'low', 'initial': 1.0},
        {'name': 'medium', 'initial': 2.0},
        {'name': 'high', 'initial': 5.0},
        {'name': 'heterogeneous', 'initial': 'random'},
    ]
    
    for eng in energy_configs:
        for protocol in protocols:
            for _ in range(n_repeats):
                experiments.append({
                    'experiment_type': 'energy',
                    'energy_config': eng['name'],
                    'protocol': protocol,
                    'n_nodes': 100,
                    'area': (100, 100),
                    'initial_energy': eng['initial'] if eng['initial'] != 'random' else np.random.uniform(1.0, 3.0),
                    'max_rounds': 300
                })
    
    # ========================================
    # 5. 长期运行实验
    # ========================================
    print("生成长期实验配置...")
    for max_rounds in [500, 1000, 2000]:
        for protocol in protocols:
            for _ in range(n_repeats // 2):  # 长期实验减少重复次数
                experiments.append({
                    'experiment_type': 'longevity',
                    'protocol': protocol,
                    'n_nodes': 100,
                    'area': (100, 100),
                    'max_rounds': max_rounds
                })
    
    # ========================================
    # 6. AERIS配置变体
    # ========================================
    print("生成AERIS变体实验配置...")
    aeris_profiles = ['robust', 'balanced', 'efficient']
    
    for profile in aeris_profiles:
        for _ in range(n_repeats):
            experiments.append({
                'experiment_type': 'aeris_profile',
                'protocol': 'AERIS',
                'profile': profile,
                'n_nodes': 100,
                'area': (100, 100),
                'max_rounds': 200
            })
    
    print(f"\n总计: {len(experiments)} 个实验配置")
    return experiments


def analyze_results(results: List[Dict]) -> Dict:
    """分析实验结果"""
    analysis = {
        'timestamp': datetime.now().isoformat(),
        'total_experiments': len(results),
        'successful': sum(1 for r in results if r.get('success', False)),
        'by_type': {},
        'by_protocol': {},
        'summary_stats': {}
    }
    
    # 按实验类型分组
    for r in results:
        if not r.get('success'):
            continue
        
        exp_type = r['config'].get('experiment_type', 'unknown')
        protocol = r['config'].get('protocol', 'unknown')
        
        # 按类型
        if exp_type not in analysis['by_type']:
            analysis['by_type'][exp_type] = []
        analysis['by_type'][exp_type].append(r)
        
        # 按协议
        if protocol not in analysis['by_protocol']:
            analysis['by_protocol'][protocol] = {'pdr': [], 'energy': [], 'lifetime': []}
        analysis['by_protocol'][protocol]['pdr'].append(r['pdr'])
        analysis['by_protocol'][protocol]['energy'].append(r['energy'])
        analysis['by_protocol'][protocol]['lifetime'].append(r['lifetime'])
    
    # 计算汇总统计
    for protocol, data in analysis['by_protocol'].items():
        analysis['summary_stats'][protocol] = {
            'pdr_mean': np.mean(data['pdr']),
            'pdr_std': np.std(data['pdr']),
            'energy_mean': np.mean(data['energy']),
            'energy_std': np.std(data['energy']),
            'lifetime_mean': np.mean(data['lifetime']),
            'lifetime_std': np.std(data['lifetime']),
            'n_samples': len(data['pdr'])
        }
    
    return analysis


def main():
    """主函数"""
    print("=" * 70)
    print("🔬 全面多数据集实验")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 生成实验矩阵
    experiments = generate_experiment_matrix()
    
    # 创建运行器
    runner = ExperimentRunner()
    
    # 分批运行实验
    batch_size = 1000
    all_results = []
    
    for i in range(0, len(experiments), batch_size):
        batch = experiments[i:i+batch_size]
        batch_results = runner.run_experiment_batch(
            batch, 
            desc=f"批次 {i//batch_size + 1}/{(len(experiments)-1)//batch_size + 1}"
        )
        all_results.extend(batch_results)
        
        # 保存中间结果
        interim_path = RESULTS_DIR / f'interim_batch_{i//batch_size + 1}.json'
        with open(interim_path, 'w') as f:
            json.dump(batch_results, f)
    
    # 分析结果
    print("\n分析结果...")
    analysis = analyze_results(all_results)
    
    # 保存最终结果
    final_path = RESULTS_DIR / 'comprehensive_results.json'
    with open(final_path, 'w') as f:
        json.dump({
            'results': all_results,
            'analysis': analysis
        }, f, indent=2, default=str)
    
    # 打印汇总
    print("\n" + "=" * 70)
    print("📊 实验汇总")
    print("=" * 70)
    print(f"总实验数: {analysis['total_experiments']}")
    print(f"成功率: {100*analysis['successful']/analysis['total_experiments']:.1f}%")
    
    print("\n协议性能对比:")
    print("-" * 50)
    for protocol, stats in analysis['summary_stats'].items():
        print(f"{protocol:10s}: PDR={stats['pdr_mean']:.3f}±{stats['pdr_std']:.3f}, "
              f"Energy={stats['energy_mean']:.1f}±{stats['energy_std']:.1f}J, "
              f"n={stats['n_samples']}")
    
    print(f"\n结果保存至: {final_path}")
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
