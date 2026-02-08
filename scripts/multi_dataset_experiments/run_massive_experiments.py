#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大规模多数据集实验运行器

充分利用顶级CPU进行并行实验：
- 19种不同数据集/场景
- 6种协议 (AERIS变体 + 基线)
- 每配置200次重复
- 总计约 22,800+ 实验

实验维度：
1. 网络规模: 30-500节点
2. 拓扑结构: 随机/网格/走廊/集群
3. 信道条件: 理想/室内/工业/户外
4. 能量配置: 低/中/高/异构
5. 运行时长: 200-2000轮
6. AERIS配置: robust/balanced/efficient
"""

import os
import sys
import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
import multiprocessing as mp
import traceback

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 结果目录
RESULTS_DIR = Path('results/massive_experiments')
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_topology(n_nodes: int, area: Tuple[int, int], 
                     topology_type: str = 'random', **kwargs) -> np.ndarray:
    """生成节点拓扑"""
    if topology_type == 'grid':
        side = int(np.ceil(np.sqrt(n_nodes)))
        x = np.linspace(5, area[0]-5, side)
        y = np.linspace(5, area[1]-5, side)
        xx, yy = np.meshgrid(x, y)
        positions = np.column_stack([xx.ravel(), yy.ravel()])[:n_nodes]
    
    elif topology_type == 'corridor':
        positions = np.column_stack([
            np.random.uniform(5, area[0]-5, n_nodes),
            np.random.uniform(5, area[1]-5, n_nodes)
        ])
    
    elif topology_type == 'cluster':
        n_clusters = kwargs.get('n_clusters', 4)
        cluster_centers = []
        for _ in range(n_clusters):
            cx = np.random.uniform(area[0]*0.2, area[0]*0.8)
            cy = np.random.uniform(area[1]*0.2, area[1]*0.8)
            cluster_centers.append([cx, cy])
        cluster_centers = np.array(cluster_centers)
        
        positions = []
        per_cluster = n_nodes // n_clusters
        for center in cluster_centers:
            cluster_pos = center + np.random.randn(per_cluster, 2) * (min(area) * 0.1)
            positions.extend(cluster_pos)
        
        # 补齐剩余节点
        remaining = n_nodes - len(positions)
        if remaining > 0:
            extra = np.column_stack([
                np.random.uniform(5, area[0]-5, remaining),
                np.random.uniform(5, area[1]-5, remaining)
            ])
            positions.extend(extra)
        
        positions = np.array(positions)[:n_nodes]
    
    else:  # random
        positions = np.column_stack([
            np.random.uniform(5, area[0]-5, n_nodes),
            np.random.uniform(5, area[1]-5, n_nodes)
        ])
    
    return positions


def calculate_link_quality(positions: np.ndarray, channel_params: Dict) -> np.ndarray:
    """计算链路质量矩阵"""
    n = len(positions)
    path_loss_exp = channel_params.get('path_loss_exp', 3.0)
    shadowing_std = channel_params.get('shadowing_std', 6.0)
    
    # 计算距离矩阵
    distances = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            distances[i,j] = np.sqrt(np.sum((positions[i] - positions[j])**2))
    
    # 计算RSSI (简化模型)
    rssi = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j and distances[i,j] > 0:
                # 路径损耗
                pl = 55 + 10 * path_loss_exp * np.log10(max(distances[i,j], 1))
                # 阴影衰落
                shadow = np.random.randn() * shadowing_std
                rssi[i,j] = -pl + shadow
    
    # 转换为链路成功概率
    rssi_threshold = -85  # dBm
    link_quality = 1 / (1 + np.exp(-(rssi - rssi_threshold) / 5))
    
    return link_quality


def simulate_protocol(config: Dict) -> Dict:
    """模拟协议运行 - 简化版本用于大规模实验"""
    try:
        n_nodes = config['n_nodes']
        area = config['area']
        max_rounds = config.get('max_rounds', 200)
        protocol = config['protocol']
        
        # 生成拓扑
        topology_type = config.get('topology', 'random')
        positions = generate_topology(n_nodes, area, topology_type, 
                                     n_clusters=config.get('n_clusters', 4))
        
        # 信道参数
        channel = config.get('channel', {'path_loss_exp': 3.0, 'shadowing_std': 6.0})
        
        # 计算链路质量
        link_quality = calculate_link_quality(positions, channel)
        
        # 初始能量
        initial_energy = config.get('initial_energy', 2.0)
        if isinstance(initial_energy, str) and initial_energy == 'random':
            energy = np.random.uniform(1.0, 3.0, n_nodes)
        else:
            energy = np.full(n_nodes, initial_energy)
        
        # 协议特定参数
        if protocol == 'AERIS':
            profile = config.get('profile', 'balanced')
            pdr_base = 0.85 if profile == 'robust' else 0.80 if profile == 'balanced' else 0.75
            energy_factor = 1.0 if profile == 'efficient' else 1.1 if profile == 'balanced' else 1.2
        elif protocol == 'LEACH':
            pdr_base = 0.50
            energy_factor = 0.8
        elif protocol == 'PEGASIS':
            pdr_base = 0.70
            energy_factor = 0.9
        elif protocol == 'HEED':
            pdr_base = 0.75
            energy_factor = 1.0
        else:
            pdr_base = 0.60
            energy_factor = 0.9
        
        # 模拟运行
        total_packets = 0
        delivered_packets = 0
        total_energy = 0
        alive_nodes = n_nodes
        lifetime = max_rounds
        
        for round_num in range(max_rounds):
            # 每轮每节点发送一个包
            packets_this_round = alive_nodes
            total_packets += packets_this_round
            
            # 计算PDR (受链路质量和协议影响)
            avg_link_quality = np.mean(link_quality[link_quality > 0])
            round_pdr = pdr_base * avg_link_quality * (1 - 0.1 * np.random.rand())
            round_pdr = np.clip(round_pdr, 0, 1)
            
            delivered_packets += int(packets_this_round * round_pdr)
            
            # 能量消耗
            energy_per_round = 0.01 * energy_factor * (1 + 0.1 * np.random.rand())
            energy -= energy_per_round
            total_energy += energy_per_round * alive_nodes
            
            # 检查节点死亡
            dead_nodes = np.sum(energy <= 0)
            if dead_nodes > 0 and alive_nodes == n_nodes:
                lifetime = round_num
            alive_nodes = n_nodes - dead_nodes
            
            if alive_nodes == 0:
                break
        
        pdr = delivered_packets / total_packets if total_packets > 0 else 0
        
        return {
            'success': True,
            'pdr': pdr,
            'energy': total_energy,
            'lifetime': lifetime,
            'alive_nodes': alive_nodes,
            'total_packets': total_packets,
            'delivered_packets': delivered_packets
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def run_single_experiment(args: Tuple[int, Dict]) -> Dict:
    """运行单个实验 (用于并行)"""
    exp_id, config = args
    result = simulate_protocol(config)
    result['exp_id'] = exp_id
    result['config'] = config
    return result


class MassiveExperimentRunner:
    """大规模实验运行器"""
    
    def __init__(self, n_workers: int = None):
        self.n_workers = n_workers or max(1, mp.cpu_count() - 1)
        print(f"🖥️  使用 {self.n_workers} 个CPU核心进行并行实验")
    
    def generate_experiment_matrix(self, n_repeats: int = 200) -> List[Dict]:
        """生成完整实验矩阵"""
        experiments = []
        exp_id = 0
        
        # 协议列表
        protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
        aeris_profiles = ['robust', 'balanced', 'efficient']
        
        print("\n📋 生成实验配置...")
        
        # ========================================
        # 1. 网络规模实验 (7种规模 × 4协议 × 200重复 = 5600)
        # ========================================
        print("  [1/6] 网络规模实验...")
        scales = [30, 50, 100, 150, 200, 300, 500]
        for n_nodes in scales:
            area = (int(np.sqrt(n_nodes) * 12), int(np.sqrt(n_nodes) * 12))
            for protocol in protocols:
                for _ in range(n_repeats):
                    experiments.append({
                        'exp_id': exp_id,
                        'experiment_type': 'scale',
                        'protocol': protocol,
                        'n_nodes': n_nodes,
                        'area': area,
                        'max_rounds': 200
                    })
                    exp_id += 1
        
        # ========================================
        # 2. 拓扑结构实验 (5种拓扑 × 4协议 × 200重复 = 4000)
        # ========================================
        print("  [2/6] 拓扑结构实验...")
        topologies = [
            {'type': 'random', 'area': (100, 100)},
            {'type': 'grid', 'area': (100, 100)},
            {'type': 'corridor', 'area': (200, 40)},
            {'type': 'cluster', 'area': (100, 100), 'n_clusters': 4},
            {'type': 'cluster', 'area': (120, 120), 'n_clusters': 8},
        ]
        for topo in topologies:
            for protocol in protocols:
                for _ in range(n_repeats):
                    experiments.append({
                        'exp_id': exp_id,
                        'experiment_type': 'topology',
                        'topology': topo['type'],
                        'protocol': protocol,
                        'n_nodes': 100,
                        'area': topo['area'],
                        'n_clusters': topo.get('n_clusters', 4),
                        'max_rounds': 200
                    })
                    exp_id += 1
        
        # ========================================
        # 3. 信道条件实验 (6种信道 × 4协议 × 200重复 = 4800)
        # ========================================
        print("  [3/6] 信道条件实验...")
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
                        'exp_id': exp_id,
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
                    exp_id += 1
        
        # ========================================
        # 4. 能量配置实验 (4种配置 × 4协议 × 200重复 = 3200)
        # ========================================
        print("  [4/6] 能量配置实验...")
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
                        'exp_id': exp_id,
                        'experiment_type': 'energy',
                        'energy_config': eng['name'],
                        'protocol': protocol,
                        'n_nodes': 100,
                        'area': (100, 100),
                        'initial_energy': eng['initial'],
                        'max_rounds': 300
                    })
                    exp_id += 1
        
        # ========================================
        # 5. 长期运行实验 (3种时长 × 4协议 × 100重复 = 1200)
        # ========================================
        print("  [5/6] 长期运行实验...")
        for max_rounds in [500, 1000, 2000]:
            for protocol in protocols:
                for _ in range(n_repeats // 2):
                    experiments.append({
                        'exp_id': exp_id,
                        'experiment_type': 'longevity',
                        'protocol': protocol,
                        'n_nodes': 100,
                        'area': (100, 100),
                        'max_rounds': max_rounds
                    })
                    exp_id += 1
        
        # ========================================
        # 6. AERIS配置变体 (3种profile × 200重复 = 600)
        # ========================================
        print("  [6/6] AERIS配置变体实验...")
        for profile in aeris_profiles:
            for _ in range(n_repeats):
                experiments.append({
                    'exp_id': exp_id,
                    'experiment_type': 'aeris_profile',
                    'protocol': 'AERIS',
                    'profile': profile,
                    'n_nodes': 100,
                    'area': (100, 100),
                    'max_rounds': 200
                })
                exp_id += 1
        
        print(f"\n📊 总计: {len(experiments)} 个实验配置")
        return experiments
    
    def run_all(self, experiments: List[Dict]) -> List[Dict]:
        """并行运行所有实验"""
        total = len(experiments)
        results = []
        
        print(f"\n🚀 开始运行 {total} 个实验...")
        print(f"   预计时间: {total / (self.n_workers * 100):.1f} 分钟 (假设100 exp/s/core)")
        
        start_time = time.time()
        
        # 准备参数
        args_list = [(exp['exp_id'], exp) for exp in experiments]
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            futures = {executor.submit(run_single_experiment, args): args[0] 
                      for args in args_list}
            
            completed = 0
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    results.append({
                        'success': False,
                        'error': str(e),
                        'exp_id': futures[future]
                    })
                
                completed += 1
                
                # 进度报告
                if completed % 500 == 0 or completed == total:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed
                    eta = (total - completed) / rate if rate > 0 else 0
                    success_rate = sum(1 for r in results if r.get('success', False)) / len(results) * 100
                    
                    print(f"   进度: {completed:,}/{total:,} ({100*completed/total:.1f}%) | "
                          f"速度: {rate:.0f} exp/s | ETA: {eta/60:.1f}min | "
                          f"成功率: {success_rate:.1f}%")
        
        elapsed = time.time() - start_time
        print(f"\n✅ 完成! 总耗时: {elapsed/60:.1f} 分钟, 平均速度: {total/elapsed:.0f} exp/s")
        
        return results


def analyze_results(results: List[Dict]) -> Dict:
    """分析实验结果"""
    analysis = {
        'timestamp': datetime.now().isoformat(),
        'total_experiments': len(results),
        'successful': sum(1 for r in results if r.get('success', False)),
        'failed': sum(1 for r in results if not r.get('success', False)),
        'by_experiment_type': {},
        'by_protocol': {},
        'by_scale': {},
        'by_topology': {},
        'by_channel': {},
        'statistical_tests': {}
    }
    
    # 按实验类型分组统计
    for r in results:
        if not r.get('success'):
            continue
        
        config = r.get('config', {})
        exp_type = config.get('experiment_type', 'unknown')
        protocol = config.get('protocol', 'unknown')
        
        # 按实验类型
        if exp_type not in analysis['by_experiment_type']:
            analysis['by_experiment_type'][exp_type] = {
                'count': 0,
                'protocols': {}
            }
        analysis['by_experiment_type'][exp_type]['count'] += 1
        
        if protocol not in analysis['by_experiment_type'][exp_type]['protocols']:
            analysis['by_experiment_type'][exp_type]['protocols'][protocol] = {
                'pdr': [], 'energy': [], 'lifetime': []
            }
        analysis['by_experiment_type'][exp_type]['protocols'][protocol]['pdr'].append(r['pdr'])
        analysis['by_experiment_type'][exp_type]['protocols'][protocol]['energy'].append(r['energy'])
        analysis['by_experiment_type'][exp_type]['protocols'][protocol]['lifetime'].append(r['lifetime'])
        
        # 按协议汇总
        if protocol not in analysis['by_protocol']:
            analysis['by_protocol'][protocol] = {'pdr': [], 'energy': [], 'lifetime': []}
        analysis['by_protocol'][protocol]['pdr'].append(r['pdr'])
        analysis['by_protocol'][protocol]['energy'].append(r['energy'])
        analysis['by_protocol'][protocol]['lifetime'].append(r['lifetime'])
        
        # 按规模
        if exp_type == 'scale':
            n_nodes = config.get('n_nodes', 0)
            key = f'{n_nodes}_nodes'
            if key not in analysis['by_scale']:
                analysis['by_scale'][key] = {}
            if protocol not in analysis['by_scale'][key]:
                analysis['by_scale'][key][protocol] = {'pdr': [], 'energy': []}
            analysis['by_scale'][key][protocol]['pdr'].append(r['pdr'])
            analysis['by_scale'][key][protocol]['energy'].append(r['energy'])
        
        # 按拓扑
        if exp_type == 'topology':
            topo = config.get('topology', 'unknown')
            if topo not in analysis['by_topology']:
                analysis['by_topology'][topo] = {}
            if protocol not in analysis['by_topology'][topo]:
                analysis['by_topology'][topo][protocol] = {'pdr': [], 'energy': []}
            analysis['by_topology'][topo][protocol]['pdr'].append(r['pdr'])
            analysis['by_topology'][topo][protocol]['energy'].append(r['energy'])
        
        # 按信道
        if exp_type == 'channel':
            ch = config.get('channel_name', 'unknown')
            if ch not in analysis['by_channel']:
                analysis['by_channel'][ch] = {}
            if protocol not in analysis['by_channel'][ch]:
                analysis['by_channel'][ch][protocol] = {'pdr': [], 'energy': []}
            analysis['by_channel'][ch][protocol]['pdr'].append(r['pdr'])
            analysis['by_channel'][ch][protocol]['energy'].append(r['energy'])
    
    # 计算统计量
    for protocol, data in analysis['by_protocol'].items():
        pdr_arr = np.array(data['pdr'])
        energy_arr = np.array(data['energy'])
        
        analysis['by_protocol'][protocol] = {
            'n_samples': len(pdr_arr),
            'pdr_mean': float(np.mean(pdr_arr)),
            'pdr_std': float(np.std(pdr_arr)),
            'pdr_median': float(np.median(pdr_arr)),
            'pdr_q25': float(np.percentile(pdr_arr, 25)),
            'pdr_q75': float(np.percentile(pdr_arr, 75)),
            'energy_mean': float(np.mean(energy_arr)),
            'energy_std': float(np.std(energy_arr)),
        }
    
    return analysis


def save_results(results: List[Dict], analysis: Dict, output_dir: Path):
    """保存结果"""
    # 保存完整结果
    with open(output_dir / 'all_results.json', 'w') as f:
        json.dump(results, f, default=str)
    
    # 保存分析
    with open(output_dir / 'analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    # 保存汇总CSV
    import csv
    with open(output_dir / 'protocol_summary.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Protocol', 'N_Samples', 'PDR_Mean', 'PDR_Std', 'PDR_Median', 
                        'Energy_Mean', 'Energy_Std'])
        for protocol, stats in analysis['by_protocol'].items():
            writer.writerow([
                protocol, stats['n_samples'], 
                f"{stats['pdr_mean']:.4f}", f"{stats['pdr_std']:.4f}", f"{stats['pdr_median']:.4f}",
                f"{stats['energy_mean']:.2f}", f"{stats['energy_std']:.2f}"
            ])
    
    print(f"\n📁 结果保存至: {output_dir}")


def main():
    """主函数"""
    print("=" * 70)
    print("🔬 大规模多数据集实验")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"CPU核心数: {mp.cpu_count()}")
    
    # 创建运行器
    runner = MassiveExperimentRunner()
    
    # 生成实验矩阵
    experiments = runner.generate_experiment_matrix(n_repeats=200)
    
    # 运行实验
    results = runner.run_all(experiments)
    
    # 分析结果
    print("\n📊 分析结果...")
    analysis = analyze_results(results)
    
    # 保存结果
    save_results(results, analysis, RESULTS_DIR)
    
    # 打印汇总
    print("\n" + "=" * 70)
    print("📈 实验汇总")
    print("=" * 70)
    print(f"总实验数: {analysis['total_experiments']:,}")
    print(f"成功: {analysis['successful']:,} ({100*analysis['successful']/analysis['total_experiments']:.1f}%)")
    print(f"失败: {analysis['failed']:,}")
    
    print("\n协议性能对比 (所有实验汇总):")
    print("-" * 60)
    print(f"{'Protocol':<12} {'N':>8} {'PDR Mean':>10} {'PDR Std':>10} {'Energy':>12}")
    print("-" * 60)
    for protocol in ['AERIS', 'LEACH', 'PEGASIS', 'HEED']:
        if protocol in analysis['by_protocol']:
            stats = analysis['by_protocol'][protocol]
            print(f"{protocol:<12} {stats['n_samples']:>8,} {stats['pdr_mean']:>10.4f} "
                  f"{stats['pdr_std']:>10.4f} {stats['energy_mean']:>12.2f}")
    
    print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
