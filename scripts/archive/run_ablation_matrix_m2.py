#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS Full Ablation Matrix Experiments for M2 Milestone
========================================================
Plan v1 Section M2: 完整消融矩阵

消融配置（9种）:
- FULL: 完整系统
- -GW: 无Gateway
- -SAFETY: 无Safety
- -CAS: 无CAS
- -FAIR: 无Fairness
- -GW-SAFETY: 无Gateway和Safety
- -GW-CAS: 无Gateway和CAS
- ALL_GW_ONLY: 仅Gateway
- BASE: 最小基线

每配置30次独立运行

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

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import numpy as np

BASE_SEED = int(os.environ.get('AERIS_SEED', '60001'))

# 完整消融矩阵配置
ABLATION_CONFIGS = {
    'FULL': {
        'enable_cas': True,
        'enable_fairness': True,
        'enable_gateway': True,
        'safety': 'robust',
        'description': '完整AERIS系统'
    },
    '-GW': {
        'enable_cas': True,
        'enable_fairness': True,
        'enable_gateway': False,
        'safety': 'robust',
        'description': '无Gateway中继'
    },
    '-SAFETY': {
        'enable_cas': True,
        'enable_fairness': True,
        'enable_gateway': True,
        'safety': 'energy',
        'description': '无Safety阈值'
    },
    '-CAS': {
        'enable_cas': False,
        'enable_fairness': True,
        'enable_gateway': True,
        'safety': 'robust',
        'description': '无CAS模块'
    },
    '-FAIR': {
        'enable_cas': True,
        'enable_fairness': False,
        'enable_gateway': True,
        'safety': 'robust',
        'description': '无Fairness策略'
    },
    '-GW-SAFETY': {
        'enable_cas': True,
        'enable_fairness': True,
        'enable_gateway': False,
        'safety': 'energy',
        'description': '无Gateway和Safety'
    },
    '-GW-CAS': {
        'enable_cas': False,
        'enable_fairness': True,
        'enable_gateway': False,
        'safety': 'robust',
        'description': '无Gateway和CAS'
    },
    'GW_ONLY': {
        'enable_cas': False,
        'enable_fairness': False,
        'enable_gateway': True,
        'safety': 'energy',
        'description': '仅Gateway'
    },
    'BASE': {
        'enable_cas': False,
        'enable_fairness': False,
        'enable_gateway': False,
        'safety': 'energy',
        'description': '最小基线'
    }
}

def compute_ci95(values):
    arr = np.array(values)
    n = len(arr)
    if n < 2:
        return 0.0
    return float(1.96 * np.std(arr, ddof=1) / math.sqrt(n))

def hedges_g(g1, g2):
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

def welch_ttest(g1, g2):
    """Welch's t-test"""
    from scipy import stats
    t_stat, p_value = stats.ttest_ind(g1, g2, equal_var=False)
    return float(t_stat), float(p_value)

def run_single_ablation(args):
    """运行单次消融实验"""
    from benchmark_protocols import NetworkConfig
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
    from aeris_protocol import AerisProtocol
    from intel_dataset_loader import IntelLabDataLoader

    config_name, ablation_config, seed, use_intel = args

    random.seed(seed)
    np.random.seed(seed)

    try:
        if use_intel:
            # 使用Intel Lab真实数据
            data_dir = Path(__file__).parent.parent / 'data'
            loader = IntelLabDataLoader(data_dir=str(data_dir), use_synthetic=False)
            locs = loader.locations_data.sort_values('node_id')
            xs = locs['x'].to_list()
            ys = locs['y'].to_list()
            minx, maxx = min(xs), max(xs)
            miny, maxy = min(ys), max(ys)
            width = maxx - minx if maxx > minx else 50.0
            height = maxy - miny if maxy > miny else 50.0
            n = len(locs)

            net_config = NetworkConfig(
                num_nodes=n,
                area_width=width,
                area_height=height,
                initial_energy=2.0,
                packet_size=1024,
                enable_channel=True,
                channel_env='indoor_office',
                tx_power_dbm=0.0,
                temperature_c=25.0,
                humidity_ratio=0.5
            )
            # 禁用force_ctp_reliable以获得真实PDR
            net_config.force_ctp_reliable = False

            proto = AerisProtocol(
                net_config,
                enable_cas=ablation_config['enable_cas'],
                enable_fairness=ablation_config['enable_fairness'],
                enable_gateway=ablation_config['enable_gateway'],
                enable_skeleton=False,
                profile=ablation_config['safety'],
                verbose=False,
                seed=seed
            )

            # 设置真实几何坐标
            for i, (x, y) in enumerate(zip(xs, ys)):
                proto.nodes[i].x = float(x) - minx
                proto.nodes[i].y = float(y) - miny

            # 构建环境提供者
            s = loader.sensor_data.dropna(subset=['humidity', 'temperature'])
            if not s.empty:
                h_vals = s['humidity'].values
                t_vals = s['temperature'].values
                h_p33 = float(np.percentile(h_vals, 33))
                h_p66 = float(np.percentile(h_vals, 66))
                t_med = float(np.percentile(t_vals, 50))
                regimes = [
                    {'name': 'low', 'h': h_p33, 'shadow': 3.5},
                    {'name': 'mid', 'h': (h_p33 + h_p66) / 2, 'shadow': 7.0},
                    {'name': 'high', 'h': h_p66, 'shadow': 12.0},
                ]

                def env_provider(round_idx: int):
                    r = regimes[round_idx % 3]
                    humidity_ratio = max(0.0, min(1.0, r['h'] / 100.0))
                    temperature_c = t_med
                    nf = -96.0 + (0.5 if r['name'] == 'mid' else (1.0 if r['name'] == 'high' else 0.0))
                    proto.channel_model.set_env_mapping(shadowing_std=r['shadow'], noise_floor_dbm=nf)
                    return (temperature_c, humidity_ratio)

                result = proto.run_simulation(200, env_provider=env_provider)
            else:
                result = proto.run_simulation(200)
        else:
            # 使用合成数据
            net_config = NetworkConfig(
                num_nodes=100,
                area_width=100.0,
                area_height=100.0,
                initial_energy=0.5,
                packet_size=1024,
                enable_channel=True,
                channel_env='indoor_office',
                tx_power_dbm=0.0,
                temperature_c=25.0,
                humidity_ratio=0.5
            )
            # 禁用force_ctp_reliable以获得真实PDR
            net_config.force_ctp_reliable = False

            proto = AerisProtocol(
                net_config,
                enable_cas=ablation_config['enable_cas'],
                enable_fairness=ablation_config['enable_fairness'],
                enable_gateway=ablation_config['enable_gateway'],
                enable_skeleton=False,
                profile=ablation_config['safety'],
                verbose=False,
                seed=seed
            )

            result = proto.run_simulation(200)

        pdr = result.get('packet_delivery_ratio_end2end', 0.0)
        energy = result.get('total_energy_consumed', 0.0)
        lifetime = result.get('network_lifetime', 0)

        return {
            'config': config_name,
            'pdr': float(pdr),
            'energy': float(energy),
            'lifetime': int(lifetime),
            'seed': seed
        }, seed, config_name

    except Exception as e:
        print(f"[ERROR] {config_name} seed={seed}: {e}")
        return None, seed, config_name

def run_ablation_matrix(workers=8, runs_per_config=30, use_intel=True):
    """运行完整消融矩阵"""
    print("\n" + "=" * 60)
    print("M2: 完整消融矩阵实验 (9配置)")
    print("=" * 60)

    all_tasks = []
    task_id = 0

    for config_name, config in ABLATION_CONFIGS.items():
        for run_idx in range(runs_per_config):
            seed = BASE_SEED + task_id
            all_tasks.append((config_name, config, seed, use_intel))
            task_id += 1

    results = {name: {'pdr': [], 'energy': [], 'lifetime': []} for name in ABLATION_CONFIGS}
    completed = 0
    total = len(all_tasks)

    print(f"总任务数: {total} ({len(ABLATION_CONFIGS)} configs × {runs_per_config} runs)")
    print(f"使用Intel Lab数据: {use_intel}")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_ablation, task): task for task in all_tasks}

        for future in as_completed(futures):
            completed += 1
            result, seed, config_name = future.result()

            if result:
                results[config_name]['pdr'].append(result['pdr'])
                results[config_name]['energy'].append(result['energy'])
                results[config_name]['lifetime'].append(result['lifetime'])

            if completed % 20 == 0 or completed == total:
                print(f"[进度] {completed}/{total} ({100 * completed / total:.1f}%)")

    # 计算统计信息和效应量
    summary = {}
    full_pdrs = results['FULL']['pdr']

    for name, data in results.items():
        if data['pdr']:
            # 基础统计
            summary[name] = {
                'description': ABLATION_CONFIGS[name]['description'],
                'pdr': {
                    'mean': float(np.mean(data['pdr'])),
                    'std': float(np.std(data['pdr'], ddof=1)),
                    'ci95': compute_ci95(data['pdr']),
                    'values': data['pdr']
                },
                'energy': {
                    'mean': float(np.mean(data['energy'])),
                    'std': float(np.std(data['energy'], ddof=1)),
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

            # 计算相对于FULL的效应量
            if name != 'FULL' and full_pdrs:
                g = hedges_g(full_pdrs, data['pdr'])
                try:
                    t_stat, p_value = welch_ttest(full_pdrs, data['pdr'])
                except:
                    t_stat, p_value = 0.0, 1.0

                pdr_change = (np.mean(data['pdr']) - np.mean(full_pdrs)) / np.mean(full_pdrs) * 100

                summary[name]['vs_full'] = {
                    'hedges_g': float(g),
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'pdr_change_pct': float(pdr_change),
                    'significant': p_value < 0.05,
                    'effect_size_interpretation': 'large' if abs(g) > 0.8 else ('medium' if abs(g) > 0.5 else 'small')
                }

    return summary

def generate_ablation_report(summary):
    """生成消融分析报告"""
    report = []
    report.append("=" * 60)
    report.append("AERIS 消融研究分析报告")
    report.append("=" * 60)
    report.append("")

    # 表格头
    report.append(f"{'配置':<15} {'PDR':>10} {'±CI95':>8} {'效应量':>8} {'p值':>10} {'变化%':>8}")
    report.append("-" * 60)

    for name in ['FULL', '-GW', '-SAFETY', '-CAS', '-FAIR', '-GW-SAFETY', '-GW-CAS', 'GW_ONLY', 'BASE']:
        if name in summary:
            data = summary[name]
            pdr_mean = data['pdr']['mean']
            pdr_ci = data['pdr']['ci95']

            if 'vs_full' in data:
                g = data['vs_full']['hedges_g']
                p = data['vs_full']['p_value']
                pct = data['vs_full']['pdr_change_pct']
                sig = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else ''))
                report.append(f"{name:<15} {pdr_mean:>10.4f} {pdr_ci:>8.4f} {g:>8.2f} {p:>10.4f} {pct:>+7.1f}% {sig}")
            else:
                report.append(f"{name:<15} {pdr_mean:>10.4f} {pdr_ci:>8.4f} {'--':>8} {'--':>10} {'--':>8}")

    report.append("-" * 60)
    report.append("")
    report.append("显著性标记: *** p<0.001, ** p<0.01, * p<0.05")
    report.append("效应量解读: |g|>0.8 大效应, |g|>0.5 中效应, |g|<0.5 小效应")
    report.append("")

    # 关键发现
    report.append("关键发现:")
    if 'FULL' in summary and '-GW' in summary:
        g = summary['-GW'].get('vs_full', {}).get('hedges_g', 0)
        report.append(f"  - Gateway机制贡献: Hedges' g = {g:.2f}")
    if 'FULL' in summary and '-SAFETY' in summary:
        g = summary['-SAFETY'].get('vs_full', {}).get('hedges_g', 0)
        report.append(f"  - Safety机制贡献: Hedges' g = {g:.2f}")
    if 'FULL' in summary and '-CAS' in summary:
        g = summary['-CAS'].get('vs_full', {}).get('hedges_g', 0)
        report.append(f"  - CAS模块贡献: Hedges' g = {g:.2f}")
    if 'FULL' in summary and '-FAIR' in summary:
        g = summary['-FAIR'].get('vs_full', {}).get('hedges_g', 0)
        report.append(f"  - Fairness策略贡献: Hedges' g = {g:.2f}")

    return "\n".join(report)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='AERIS M2 Full Ablation Matrix')
    parser.add_argument('--workers', type=int, default=8, help='Number of parallel workers')
    parser.add_argument('--runs', type=int, default=30, help='Runs per configuration')
    parser.add_argument('--use-intel', action='store_true', default=True, help='Use Intel Lab data')
    parser.add_argument('--synthetic', action='store_true', help='Use synthetic data instead')
    args = parser.parse_args()

    use_intel = not args.synthetic

    results_dir = Path(__file__).parent.parent / 'results' / 'experiments_20250102'
    results_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    print(f"\n{'=' * 60}")
    print(f"AERIS M2 完整消融矩阵")
    print(f"Workers: {args.workers}, Runs per config: {args.runs}")
    print(f"数据源: {'Intel Lab' if use_intel else 'Synthetic'}")
    print(f"{'=' * 60}")

    summary = run_ablation_matrix(args.workers, args.runs, use_intel)

    # 保存结果
    with open(results_dir / 'ablation_matrix_full.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[保存] ablation_matrix_full.json")

    # 生成并保存报告
    report = generate_ablation_report(summary)
    with open(results_dir / 'ablation_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"[保存] ablation_report.txt")

    print(report)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"M2消融实验完成!")
    print(f"总耗时: {elapsed / 60:.1f} 分钟")
    print(f"结果保存至: {results_dir}")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()
