#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9小时大规模实验 - CAS权重优化与多配置对比

目标:
1. 测试多组CAS权重配置，找到最优平衡点
2. 对比有/无信道模型的性能差异
3. 收集详细的CAS模式分布和PDR数据

配置:
- 并行度: 12 workers (50% of 24 cores)
- 内存保留: 30GB给系统
- 预估时间: 8-9小时
"""
import os
import sys
import json
import time
import random
import platform
import hashlib
import multiprocessing as mp
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple
from copy import deepcopy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 并行配置 - 保守设置，避免卡顿
MAX_WORKERS = 12  # 50% of 24 cores
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', f'overnight_9h_{TIMESTAMP}')


def get_environment_info() -> Dict:
    import subprocess
    env_info = {
        'python_version': platform.python_version(),
        'platform': platform.platform(),
        'max_workers': MAX_WORKERS,
        'start_time': TIMESTAMP,
    }
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                               capture_output=True, text=True, timeout=5,
                               cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            env_info['git_commit'] = result.stdout.strip()
    except Exception:
        env_info['git_commit'] = 'unknown'
    return env_info


# CAS权重配置组 - 测试不同的平衡策略
CAS_WEIGHT_CONFIGS = {
    'baseline': {
        'w_direct_dist_bs': -0.60,
        'w_chain_dist_bs': 0.25,
        'w_twohop_dist_bs': 0.40,
    },
    'balanced_v1': {
        'w_direct_dist_bs': -0.50,
        'w_chain_dist_bs': 0.30,
        'w_twohop_dist_bs': 0.20,
    },
    'balanced_v2': {
        'w_direct_dist_bs': -0.40,
        'w_direct_link': 0.55,
        'w_chain_dist_bs': 0.25,
        'w_twohop_dist_bs': 0.15,
    },
    'balanced_v3': {
        'w_direct_dist_bs': -0.35,
        'w_direct_link': 0.50,
        'w_chain_dist_bs': 0.30,
        'w_twohop_dist_bs': 0.05,
    },
    'direct_favor': {
        'w_direct_dist_bs': -0.30,
        'w_direct_link': 0.60,
        'w_chain_dist_bs': 0.20,
        'w_twohop_dist_bs': 0.10,
    },
    'direct_strong': {
        'w_direct_dist_bs': -0.20,
        'w_direct_link': 0.65,
        'w_direct_energy': 0.50,
        'w_chain_dist_bs': 0.15,
        'w_twohop_dist_bs': 0.05,
    },
    'chain_favor': {
        'w_direct_dist_bs': -0.50,
        'w_chain_dist_bs': 0.40,
        'w_chain_link': 0.30,
        'w_twohop_dist_bs': 0.10,
    },
    'chain_strong': {
        'w_direct_dist_bs': -0.45,
        'w_chain_dist_bs': 0.50,
        'w_chain_link': 0.35,
        'w_chain_radius': 0.25,
        'w_twohop_dist_bs': 0.05,
    },
}


def run_aeris_with_weights(params: Dict) -> Dict:
    """运行AERIS实验，支持自定义CAS权重"""
    import numpy as np
    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol
    from cas_selector import CASSelector, CASConfig

    random.seed(params['seed'])
    np.random.seed(params['seed'])

    cfg = NetworkConfig(**params['config'])

    proto = AerisProtocol(
        cfg, verbose=False, seed=params['seed'],
        enable_cas=True, enable_fairness=True, enable_gateway=True
    )

    # 预先创建CAS选择器并应用自定义权重
    weight_overrides = params.get('cas_weights', {})
    cas_cfg = CASConfig()
    for key, val in weight_overrides.items():
        if hasattr(cas_cfg, key):
            setattr(cas_cfg, key, val)
    proto.cas_selector = CASSelector(cas_cfg)

    result = proto.run_simulation(max_rounds=params['max_rounds'])

    am = result.get('additional_metrics', {})
    usage = am.get('cas_mode_usage_stats', {})
    total = am.get('cas_total_decisions', 1)

    return {
        'protocol': 'AERIS',
        'weight_config': params.get('weight_config_name', 'default'),
        'seed': params['seed'],
        'scenario': params['scenario'],
        'num_nodes': params['config']['num_nodes'],
        'enable_channel': params['config'].get('enable_channel', False),
        'pdr_end2end': result.get('packet_delivery_ratio_end2end', 0),
        'total_energy': result.get('total_energy_consumed', 0),
        'rounds_completed': result.get('rounds_completed', 0),
        'cas_direct': usage.get('DIRECT', 0),
        'cas_chain': usage.get('CHAIN', 0),
        'cas_twohop': usage.get('TWO_HOP', 0),
        'cas_total': total,
        'direct_ratio': usage.get('DIRECT', 0) / max(1, total),
        'chain_ratio': usage.get('CHAIN', 0) / max(1, total),
        'twohop_ratio': usage.get('TWO_HOP', 0) / max(1, total),
    }


def run_baseline(params: Dict) -> Dict:
    """运行基线协议"""
    import numpy as np
    from benchmark_protocols import NetworkConfig
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

    random.seed(params['seed'])
    np.random.seed(params['seed'])

    cfg = NetworkConfig(**params['config'])
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    protocol = params['protocol']

    if protocol == 'LEACH':
        from benchmark_protocols import LEACHProtocol
        proto = LEACHProtocol(cfg, em)
    elif protocol == 'PEGASIS':
        from benchmark_protocols import PEGASISProtocol
        proto = PEGASISProtocol(cfg, em)
    elif protocol == 'HEED':
        from benchmark_protocols import HEEDProtocolWrapper
        proto = HEEDProtocolWrapper(cfg, em)
    else:
        return {'error': f'Unknown protocol: {protocol}'}

    result = proto.run_simulation(max_rounds=params['max_rounds'])

    return {
        'protocol': protocol,
        'weight_config': 'N/A',
        'seed': params['seed'],
        'scenario': params['scenario'],
        'num_nodes': params['config']['num_nodes'],
        'enable_channel': params['config'].get('enable_channel', False),
        'pdr_end2end': result.get('packet_delivery_ratio_end2end',
                                   result.get('packet_delivery_ratio', 0)),
        'total_energy': result.get('total_energy_consumed', 0),
        'rounds_completed': result.get('rounds_completed', 0),
    }


def run_single_task(task: Dict) -> Dict:
    """执行单个实验任务"""
    try:
        if task['protocol'] == 'AERIS':
            return run_aeris_with_weights(task)
        else:
            return run_baseline(task)
    except Exception as e:
        return {
            'protocol': task.get('protocol'),
            'seed': task.get('seed'),
            'scenario': task.get('scenario'),
            'error': str(e),
        }


def generate_tasks() -> List[Dict]:
    """生成所有实验任务"""
    tasks = []

    scenarios = {
        'uniform': {'area_width': 200, 'area_height': 200},
        'corridor': {'area_width': 400, 'area_height': 100},
    }

    node_counts = [50, 100, 150, 200, 250, 300, 400]
    seeds = range(1, 151)  # 150 seeds per config
    max_rounds = 500

    # 基础配置（无信道模型）
    base_config = {
        'initial_energy': 2.0,
        'packet_size': 512,
        'enable_channel': False,
    }

    # 信道模型配置
    channel_config = {
        'initial_energy': 2.0,
        'packet_size': 512,
        'enable_channel': True,
        'channel_env': 'indoor_office',
        'tx_power_dbm': 0.0,
        'link_retx': 1,
        'link_retx_power_step': 1.0,
    }

    # Part 1: AERIS with different CAS weights (with channel)
    for weight_name, weights in CAS_WEIGHT_CONFIGS.items():
        for scenario, area in scenarios.items():
            for num_nodes in node_counts:
                for seed in seeds:
                    cfg = {**channel_config, **area, 'num_nodes': num_nodes}
                    tasks.append({
                        'protocol': 'AERIS',
                        'weight_config_name': weight_name,
                        'cas_weights': weights,
                        'seed': seed,
                        'scenario': scenario,
                        'max_rounds': max_rounds,
                        'config': cfg,
                    })

    # Part 2: AERIS without channel model (baseline comparison)
    for scenario, area in scenarios.items():
        for num_nodes in node_counts:
            for seed in seeds:
                cfg = {**base_config, **area, 'num_nodes': num_nodes}
                tasks.append({
                    'protocol': 'AERIS',
                    'weight_config_name': 'no_channel',
                    'cas_weights': CAS_WEIGHT_CONFIGS['balanced_v2'],
                    'seed': seed,
                    'scenario': scenario,
                    'max_rounds': max_rounds,
                    'config': cfg,
                })

    # Part 3: Baseline protocols (with channel)
    baselines = ['LEACH', 'PEGASIS', 'HEED']
    for protocol in baselines:
        for scenario, area in scenarios.items():
            for num_nodes in node_counts:
                for seed in seeds:
                    cfg = {**channel_config, **area, 'num_nodes': num_nodes}
                    tasks.append({
                        'protocol': protocol,
                        'seed': seed,
                        'scenario': scenario,
                        'max_rounds': max_rounds,
                        'config': cfg,
                    })

    # Part 4: Baseline protocols (without channel)
    for protocol in baselines:
        for scenario, area in scenarios.items():
            for num_nodes in node_counts:
                for seed in seeds:
                    cfg = {**base_config, **area, 'num_nodes': num_nodes}
                    tasks.append({
                        'protocol': protocol,
                        'seed': seed,
                        'scenario': scenario,
                        'max_rounds': max_rounds,
                        'config': cfg,
                    })

    return tasks


def save_checkpoint(results: List[Dict], checkpoint_num: int):
    """保存检查点"""
    path = os.path.join(OUT_DIR, f'checkpoint_{checkpoint_num}.json')
    with open(path, 'w') as f:
        json.dump(results, f)
    print(f"  Checkpoint {checkpoint_num} saved: {len(results)} results")


def generate_summary(results: List[Dict]):
    """生成汇总报告"""
    import numpy as np

    summary = {}
    for r in results:
        if 'error' in r:
            continue

        key = (r['protocol'], r.get('weight_config', 'N/A'),
               r['scenario'], r['num_nodes'], r.get('enable_channel', False))

        if key not in summary:
            summary[key] = {'pdr': [], 'energy': [],
                          'direct_ratio': [], 'chain_ratio': [], 'twohop_ratio': []}

        summary[key]['pdr'].append(r.get('pdr_end2end', 0))
        summary[key]['energy'].append(r.get('total_energy', 0))

        if 'direct_ratio' in r:
            summary[key]['direct_ratio'].append(r['direct_ratio'])
            summary[key]['chain_ratio'].append(r['chain_ratio'])
            summary[key]['twohop_ratio'].append(r['twohop_ratio'])

    # 生成表格
    print("\n" + "=" * 100)
    print("Summary Results")
    print("=" * 100)

    header = f"{'Protocol':<10} {'Weights':<15} {'Scenario':<10} {'Nodes':<6} {'Channel':<8} {'PDR%':<12} {'Energy':<10} {'D/C/T%':<20}"
    print(header)
    print("-" * 100)

    summary_data = {}
    for key, data in sorted(summary.items()):
        proto, weights, scenario, nodes, channel = key
        pdr_mean = np.mean(data['pdr']) * 100
        pdr_std = np.std(data['pdr']) * 100
        e_mean = np.mean(data['energy'])

        dct_str = "N/A"
        if data['direct_ratio']:
            d = np.mean(data['direct_ratio']) * 100
            c = np.mean(data['chain_ratio']) * 100
            t = np.mean(data['twohop_ratio']) * 100
            dct_str = f"{d:.0f}/{c:.0f}/{t:.0f}"

        ch_str = "Yes" if channel else "No"
        print(f"{proto:<10} {weights:<15} {scenario:<10} {nodes:<6} {ch_str:<8} "
              f"{pdr_mean:5.1f}±{pdr_std:4.1f} {e_mean:10.1f} {dct_str:<20}")

        # 保存到JSON
        key_str = f"{proto}_{weights}_{scenario}_{nodes}_ch{channel}"
        summary_data[key_str] = {
            'pdr_mean': float(np.mean(data['pdr'])),
            'pdr_std': float(np.std(data['pdr'])),
            'energy_mean': float(e_mean),
            'n_runs': len(data['pdr']),
        }
        if data['direct_ratio']:
            summary_data[key_str]['cas_distribution'] = {
                'direct': float(np.mean(data['direct_ratio'])),
                'chain': float(np.mean(data['chain_ratio'])),
                'twohop': float(np.mean(data['twohop_ratio'])),
            }

    # 保存汇总
    out_path = os.path.join(OUT_DIR, 'summary.json')
    with open(out_path, 'w') as f:
        json.dump(summary_data, f, indent=2)
    print(f"\nSummary saved: {out_path}")


def main():
    print("=" * 60)
    print("9-Hour Overnight Experiment")
    print(f"Start time: {TIMESTAMP}")
    print(f"Workers: {MAX_WORKERS} (conservative for stability)")
    print("=" * 60)

    os.makedirs(OUT_DIR, exist_ok=True)

    # 保存环境信息
    env_info = get_environment_info()
    with open(os.path.join(OUT_DIR, 'environment.json'), 'w') as f:
        json.dump(env_info, f, indent=2)

    tasks = generate_tasks()
    print(f"Total tasks: {len(tasks)}")

    # 估算时间
    est_time_per_task = 3  # seconds
    est_total = len(tasks) * est_time_per_task / MAX_WORKERS / 3600
    print(f"Estimated time: {est_total:.1f} hours")

    results = []
    errors = []
    start_time = time.time()
    checkpoint_interval = 500

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_single_task, t): t for t in tasks}

        for i, future in enumerate(as_completed(futures)):
            try:
                res = future.result(timeout=300)
                if 'error' in res:
                    errors.append(res)
                else:
                    results.append(res)
            except Exception as e:
                task = futures[future]
                errors.append({
                    'protocol': task.get('protocol'),
                    'seed': task.get('seed'),
                    'error': str(e),
                })

            # 进度报告
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                remaining = (len(tasks) - i - 1) / rate / 3600
                print(f"Progress: {i+1}/{len(tasks)}, "
                      f"Elapsed: {elapsed/3600:.2f}h, "
                      f"Remaining: {remaining:.2f}h, "
                      f"Errors: {len(errors)}")

            # 检查点
            if (i + 1) % checkpoint_interval == 0:
                save_checkpoint(results, (i + 1) // checkpoint_interval)

    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed/3600:.2f} hours")
    print(f"Successful: {len(results)}, Errors: {len(errors)}")

    # 保存完整结果
    out_path = os.path.join(OUT_DIR, 'full_results.json')
    with open(out_path, 'w') as f:
        json.dump({
            'timestamp': TIMESTAMP,
            'environment': env_info,
            'elapsed_hours': elapsed / 3600,
            'total_tasks': len(tasks),
            'successful': len(results),
            'errors': len(errors),
            'results': results,
            'error_details': errors[:100],  # 只保存前100个错误
        }, f, indent=2)
    print(f"Full results saved: {out_path}")

    # 生成汇总
    generate_summary(results)

    print("\n" + "=" * 60)
    print("Experiment Complete!")
    print(f"Output directory: {OUT_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    mp.freeze_support()
    main()
