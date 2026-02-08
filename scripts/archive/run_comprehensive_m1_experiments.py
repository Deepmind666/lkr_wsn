#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS Comprehensive Experiments for M1 Milestone
==============================================
Plan v1 Section M1: 规模扩展实验

实验设计:
- 节点规模: 50, 100, 150, 200
- 仿真轮次: 100, 200, 300, 500
- 初始能量: 0.25, 0.5, 1.0, 2.0 J
- 拓扑类型: uniform, corridor31, corridor41
- 协议对比: AERIS, LEACH, HEED, PEGASIS, TEEN
- 每配置30次独立运行

作者: Claude (AI Assistant)
日期: 2025-01-02
"""

import os
import sys
import json
import math
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import numpy as np

BASE_SEED = int(os.environ.get('AERIS_SEED', '50001'))

def compute_ci95(values):
    """计算95%置信区间"""
    arr = np.array(values)
    n = len(arr)
    if n < 2:
        return 0.0
    return float(1.96 * np.std(arr, ddof=1) / math.sqrt(n))

def hedges_g(g1, g2):
    """计算Hedges' g效应量"""
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2:
        return 0.0
    m1, m2 = np.mean(g1), np.mean(g2)
    s1, s2 = np.var(g1, ddof=1), np.var(g2, ddof=1)
    sp = np.sqrt(((n1-1)*s1 + (n2-1)*s2) / (n1+n2-2))
    if sp == 0:
        return 0.0
    d = (m1 - m2) / sp
    j = 1 - 3 / (4*(n1+n2) - 9)
    return d * j

def generate_uniform_positions(num_nodes, width, height, seed):
    """生成均匀分布节点位置"""
    rng = random.Random(seed)
    return [(rng.uniform(0, width), rng.uniform(0, height)) for _ in range(num_nodes)]

def generate_corridor_positions(num_nodes, width, height, corridor_ratio, seed):
    """生成走廊型分布节点位置"""
    rng = random.Random(seed)
    positions = []
    corridor_width = width * corridor_ratio
    start_x = (width - corridor_width) / 2
    for _ in range(num_nodes):
        x = rng.uniform(start_x, start_x + corridor_width)
        y = rng.uniform(0, height)
        positions.append((x, y))
    return positions

def run_single_experiment(args):
    """运行单次实验"""
    from benchmark_protocols import (
        NetworkConfig, LEACHProtocol, PEGASISProtocol,
        HEEDProtocolWrapper, TEENProtocolWrapper
    )
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
    from aeris_protocol import AerisProtocol

    exp_config, seed = args

    random.seed(seed)
    np.random.seed(seed)

    # 解析配置
    num_nodes = exp_config['num_nodes']
    num_rounds = exp_config['num_rounds']
    initial_energy = exp_config['initial_energy']
    topology = exp_config['topology']
    protocol = exp_config['protocol']
    area_width = exp_config.get('area_width', 100.0)
    area_height = exp_config.get('area_height', 100.0)

    # 生成节点位置
    if topology == 'uniform':
        positions = generate_uniform_positions(num_nodes, area_width, area_height, seed)
    elif topology == 'corridor31':
        positions = generate_corridor_positions(num_nodes, area_width, area_height, 0.31, seed)
    elif topology == 'corridor41':
        positions = generate_corridor_positions(num_nodes, area_width, area_height, 0.41, seed)
    else:
        positions = generate_uniform_positions(num_nodes, area_width, area_height, seed)

    # 创建网络配置 (启用真实信道模型)
    config = NetworkConfig(
        num_nodes=num_nodes,
        area_width=area_width,
        area_height=area_height,
        initial_energy=initial_energy,
        packet_size=1024,
        positions=positions,
        enable_channel=True,
        channel_env='indoor_office',
        tx_power_dbm=0.0,
        temperature_c=25.0,
        humidity_ratio=0.5
    )
    # 禁用force_ctp_reliable以获得真实PDR
    config.force_ctp_reliable = False

    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    try:
        # 根据协议类型创建实例并运行
        if protocol == 'LEACH':
            proto = LEACHProtocol(config, energy_model)
            result = proto.run_simulation(num_rounds)
        elif protocol == 'HEED':
            proto = HEEDProtocolWrapper(config, energy_model)
            result = proto.run_simulation(num_rounds)
        elif protocol == 'PEGASIS':
            proto = PEGASISProtocol(config, energy_model)
            result = proto.run_simulation(num_rounds)
        elif protocol == 'TEEN':
            proto = TEENProtocolWrapper(config, energy_model)
            result = proto.run_simulation(num_rounds)
        elif protocol == 'AERIS':
            proto = AerisProtocol(
                config,
                enable_cas=True,
                enable_fairness=True,
                enable_gateway=True,
                enable_skeleton=False,
                profile='robust',
                verbose=False,
                seed=seed
            )
            result = proto.run_simulation(num_rounds)
        else:
            return None, seed, exp_config

        # 提取结果
        pdr = result.get('packet_delivery_ratio_end2end', 0.0)
        energy = result.get('total_energy_consumed', 0.0)
        lifetime = result.get('network_lifetime', 0)

        return {
            'pdr': float(pdr),
            'energy': float(energy),
            'lifetime': int(lifetime),
            'seed': seed
        }, seed, exp_config

    except Exception as e:
        print(f"[ERROR] {protocol} seed={seed}: {e}")
        return None, seed, exp_config

def run_scale_experiments(workers=8, runs_per_config=30):
    """M1.1: 规模扩展实验 (50/100/150/200节点)"""
    print("\n" + "="*60)
    print("M1.1: 规模扩展实验 (50/100/150/200节点)")
    print("="*60)

    node_counts = [50, 100, 150, 200]
    protocols = ['AERIS', 'LEACH', 'HEED', 'PEGASIS', 'TEEN']

    all_tasks = []
    task_id = 0

    for num_nodes in node_counts:
        for protocol in protocols:
            for run_idx in range(runs_per_config):
                seed = BASE_SEED + task_id
                exp_config = {
                    'num_nodes': num_nodes,
                    'num_rounds': 200,
                    'initial_energy': 0.5,
                    'topology': 'uniform',
                    'protocol': protocol,
                    'experiment': 'scale'
                }
                all_tasks.append((exp_config, seed))
                task_id += 1

    results = {}
    completed = 0
    total = len(all_tasks)

    print(f"总任务数: {total} ({len(node_counts)} scales × {len(protocols)} protocols × {runs_per_config} runs)")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, task): task for task in all_tasks}

        for future in as_completed(futures):
            completed += 1
            result, seed, config = future.result()

            key = f"N{config['num_nodes']}_{config['protocol']}"
            if key not in results:
                results[key] = {'pdr': [], 'energy': [], 'lifetime': []}

            if result:
                results[key]['pdr'].append(result['pdr'])
                results[key]['energy'].append(result['energy'])
                results[key]['lifetime'].append(result['lifetime'])

            if completed % 50 == 0 or completed == total:
                print(f"[进度] {completed}/{total} ({100*completed/total:.1f}%)")

    # 计算统计信息
    summary = {}
    for key, data in results.items():
        if data['pdr']:
            summary[key] = {
                'pdr': {
                    'mean': float(np.mean(data['pdr'])),
                    'ci95': compute_ci95(data['pdr']),
                    'values': data['pdr']
                },
                'energy': {
                    'mean': float(np.mean(data['energy'])),
                    'ci95': compute_ci95(data['energy']),
                    'values': data['energy']
                },
                'lifetime': {
                    'mean': float(np.mean(data['lifetime'])),
                    'ci95': compute_ci95(data['lifetime']),
                    'values': data['lifetime']
                },
                'n': len(data['pdr'])
            }

    return summary

def run_rounds_experiments(workers=8, runs_per_config=30):
    """M1.2: 轮次扩展实验 (100/200/300/500轮)"""
    print("\n" + "="*60)
    print("M1.2: 轮次扩展实验 (100/200/300/500轮)")
    print("="*60)

    round_counts = [100, 200, 300, 500]
    protocols = ['AERIS', 'LEACH', 'HEED', 'PEGASIS', 'TEEN']

    all_tasks = []
    task_id = 10000  # 不同的seed范围

    for num_rounds in round_counts:
        for protocol in protocols:
            for run_idx in range(runs_per_config):
                seed = BASE_SEED + task_id
                exp_config = {
                    'num_nodes': 100,
                    'num_rounds': num_rounds,
                    'initial_energy': 0.5,
                    'topology': 'uniform',
                    'protocol': protocol,
                    'experiment': 'rounds'
                }
                all_tasks.append((exp_config, seed))
                task_id += 1

    results = {}
    completed = 0
    total = len(all_tasks)

    print(f"总任务数: {total} ({len(round_counts)} rounds × {len(protocols)} protocols × {runs_per_config} runs)")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, task): task for task in all_tasks}

        for future in as_completed(futures):
            completed += 1
            result, seed, config = future.result()

            key = f"R{config['num_rounds']}_{config['protocol']}"
            if key not in results:
                results[key] = {'pdr': [], 'energy': [], 'lifetime': []}

            if result:
                results[key]['pdr'].append(result['pdr'])
                results[key]['energy'].append(result['energy'])
                results[key]['lifetime'].append(result['lifetime'])

            if completed % 50 == 0 or completed == total:
                print(f"[进度] {completed}/{total} ({100*completed/total:.1f}%)")

    # 计算统计信息
    summary = {}
    for key, data in results.items():
        if data['pdr']:
            summary[key] = {
                'pdr': {
                    'mean': float(np.mean(data['pdr'])),
                    'ci95': compute_ci95(data['pdr']),
                    'values': data['pdr']
                },
                'energy': {
                    'mean': float(np.mean(data['energy'])),
                    'ci95': compute_ci95(data['energy']),
                    'values': data['energy']
                },
                'lifetime': {
                    'mean': float(np.mean(data['lifetime'])),
                    'ci95': compute_ci95(data['lifetime']),
                    'values': data['lifetime']
                },
                'n': len(data['pdr'])
            }

    return summary

def run_energy_experiments(workers=8, runs_per_config=30):
    """M1.3: 能量敏感度实验 (0.25/0.5/1.0/2.0 J)"""
    print("\n" + "="*60)
    print("M1.3: 能量敏感度实验 (0.25/0.5/1.0/2.0 J)")
    print("="*60)

    energy_levels = [0.25, 0.5, 1.0, 2.0]
    protocols = ['AERIS', 'LEACH', 'HEED', 'PEGASIS', 'TEEN']

    all_tasks = []
    task_id = 20000  # 不同的seed范围

    for energy in energy_levels:
        for protocol in protocols:
            for run_idx in range(runs_per_config):
                seed = BASE_SEED + task_id
                exp_config = {
                    'num_nodes': 100,
                    'num_rounds': 200,
                    'initial_energy': energy,
                    'topology': 'uniform',
                    'protocol': protocol,
                    'experiment': 'energy'
                }
                all_tasks.append((exp_config, seed))
                task_id += 1

    results = {}
    completed = 0
    total = len(all_tasks)

    print(f"总任务数: {total} ({len(energy_levels)} energies × {len(protocols)} protocols × {runs_per_config} runs)")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, task): task for task in all_tasks}

        for future in as_completed(futures):
            completed += 1
            result, seed, config = future.result()

            key = f"E{config['initial_energy']}_{config['protocol']}"
            if key not in results:
                results[key] = {'pdr': [], 'energy': [], 'lifetime': []}

            if result:
                results[key]['pdr'].append(result['pdr'])
                results[key]['energy'].append(result['energy'])
                results[key]['lifetime'].append(result['lifetime'])

            if completed % 50 == 0 or completed == total:
                print(f"[进度] {completed}/{total} ({100*completed/total:.1f}%)")

    # 计算统计信息
    summary = {}
    for key, data in results.items():
        if data['pdr']:
            summary[key] = {
                'pdr': {
                    'mean': float(np.mean(data['pdr'])),
                    'ci95': compute_ci95(data['pdr']),
                    'values': data['pdr']
                },
                'energy': {
                    'mean': float(np.mean(data['energy'])),
                    'ci95': compute_ci95(data['energy']),
                    'values': data['energy']
                },
                'lifetime': {
                    'mean': float(np.mean(data['lifetime'])),
                    'ci95': compute_ci95(data['lifetime']),
                    'values': data['lifetime']
                },
                'n': len(data['pdr'])
            }

    return summary

def run_topology_experiments(workers=8, runs_per_config=30):
    """M1.4: 拓扑泛化实验"""
    print("\n" + "="*60)
    print("M1.4: 拓扑泛化实验 (uniform/corridor31/corridor41)")
    print("="*60)

    topologies = ['uniform', 'corridor31', 'corridor41']
    protocols = ['AERIS', 'LEACH', 'HEED', 'PEGASIS', 'TEEN']

    all_tasks = []
    task_id = 30000

    for topo in topologies:
        for protocol in protocols:
            for run_idx in range(runs_per_config):
                seed = BASE_SEED + task_id
                exp_config = {
                    'num_nodes': 100,
                    'num_rounds': 200,
                    'initial_energy': 0.5,
                    'topology': topo,
                    'protocol': protocol,
                    'experiment': 'topology'
                }
                all_tasks.append((exp_config, seed))
                task_id += 1

    results = {}
    completed = 0
    total = len(all_tasks)

    print(f"总任务数: {total} ({len(topologies)} topos × {len(protocols)} protocols × {runs_per_config} runs)")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, task): task for task in all_tasks}

        for future in as_completed(futures):
            completed += 1
            result, seed, config = future.result()

            key = f"{config['topology']}_{config['protocol']}"
            if key not in results:
                results[key] = {'pdr': [], 'energy': [], 'lifetime': []}

            if result:
                results[key]['pdr'].append(result['pdr'])
                results[key]['energy'].append(result['energy'])
                results[key]['lifetime'].append(result['lifetime'])

            if completed % 50 == 0 or completed == total:
                print(f"[进度] {completed}/{total} ({100*completed/total:.1f}%)")

    # 计算统计信息
    summary = {}
    for key, data in results.items():
        if data['pdr']:
            summary[key] = {
                'pdr': {
                    'mean': float(np.mean(data['pdr'])),
                    'ci95': compute_ci95(data['pdr']),
                    'values': data['pdr']
                },
                'energy': {
                    'mean': float(np.mean(data['energy'])),
                    'ci95': compute_ci95(data['energy']),
                    'values': data['energy']
                },
                'lifetime': {
                    'mean': float(np.mean(data['lifetime'])),
                    'ci95': compute_ci95(data['lifetime']),
                    'values': data['lifetime']
                },
                'n': len(data['pdr'])
            }

    return summary

def main():
    import argparse
    parser = argparse.ArgumentParser(description='AERIS M1 Comprehensive Experiments')
    parser.add_argument('--workers', type=int, default=8, help='Number of parallel workers')
    parser.add_argument('--runs', type=int, default=30, help='Runs per configuration')
    parser.add_argument('--experiments', type=str, default='all',
                       help='Experiments to run: all, scale, rounds, energy, topology')
    args = parser.parse_args()

    results_dir = Path(__file__).parent.parent / 'results' / 'experiments_20250102'
    results_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    print(f"\n{'='*60}")
    print(f"AERIS M1 综合实验")
    print(f"Workers: {args.workers}, Runs per config: {args.runs}")
    print(f"{'='*60}")

    experiments_to_run = args.experiments.lower().split(',')

    all_results = {}

    if 'all' in experiments_to_run or 'scale' in experiments_to_run:
        scale_results = run_scale_experiments(args.workers, args.runs)
        all_results['scale'] = scale_results

        # 保存规模实验结果
        with open(results_dir / 'scale_experiments.json', 'w', encoding='utf-8') as f:
            json.dump(scale_results, f, ensure_ascii=False, indent=2)
        print(f"[保存] scale_experiments.json")

    if 'all' in experiments_to_run or 'rounds' in experiments_to_run:
        rounds_results = run_rounds_experiments(args.workers, args.runs)
        all_results['rounds'] = rounds_results

        with open(results_dir / 'rounds_experiments.json', 'w', encoding='utf-8') as f:
            json.dump(rounds_results, f, ensure_ascii=False, indent=2)
        print(f"[保存] rounds_experiments.json")

    if 'all' in experiments_to_run or 'energy' in experiments_to_run:
        energy_results = run_energy_experiments(args.workers, args.runs)
        all_results['energy'] = energy_results

        with open(results_dir / 'energy_experiments.json', 'w', encoding='utf-8') as f:
            json.dump(energy_results, f, ensure_ascii=False, indent=2)
        print(f"[保存] energy_experiments.json")

    if 'all' in experiments_to_run or 'topology' in experiments_to_run:
        topology_results = run_topology_experiments(args.workers, args.runs)
        all_results['topology'] = topology_results

        with open(results_dir / 'topology_experiments.json', 'w', encoding='utf-8') as f:
            json.dump(topology_results, f, ensure_ascii=False, indent=2)
        print(f"[保存] topology_experiments.json")

    # 保存汇总结果
    with open(results_dir / 'm1_all_results.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"M1实验完成!")
    print(f"总耗时: {elapsed/3600:.2f} 小时")
    print(f"结果保存至: {results_dir}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
