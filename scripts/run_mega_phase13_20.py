#!/usr/bin/env python3
"""
超大规模追加实验 Phase 13-20
目标: 填充至10-14小时总运行时间
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import argparse
import traceback
import numpy as np
from datetime import datetime
from multiprocessing import Pool, cpu_count

MAX_WORKERS = max(1, cpu_count() - 2)

SEEDS_100 = list(range(42001, 42101))
SEEDS_50 = list(range(42001, 42051))

ABLATION_CONFIGS = {
    'AERIS_full': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_gateway': {'enable_gateway': False, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_cas': {'enable_gateway': True, 'enable_cas': False, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_skeleton': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': False, 'safety_fallback_enabled': True},
    'AERIS_no_safety': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': False},
    'AERIS_baseline': {'enable_gateway': False, 'enable_cas': False, 'enable_skeleton': False, 'safety_fallback_enabled': False},
}

ENVIRONMENTS = ['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban']


def run_single_experiment(args):
    """单次实验执行"""
    import random
    config_name, ablation_cfg, num_nodes, num_rounds, seed, area_size, tx_power, env_name = args

    random.seed(seed)
    np.random.seed(seed)

    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol
    from realistic_channel_model import RealisticChannelModel, EnvironmentType

    env_map = {
        'indoor_office': EnvironmentType.INDOOR_OFFICE,
        'indoor_factory': EnvironmentType.INDOOR_FACTORY,
        'outdoor_urban': EnvironmentType.OUTDOOR_URBAN,
        'outdoor_suburban': EnvironmentType.OUTDOOR_SUBURBAN,
    }

    positions = [(np.random.uniform(0, area_size), np.random.uniform(0, area_size))
                 for _ in range(num_nodes)]
    channel = RealisticChannelModel(env_map.get(env_name, EnvironmentType.INDOOR_OFFICE))
    channel.reset_rng(seed)

    result = {
        'config_name': config_name, 'num_nodes': num_nodes, 'num_rounds': num_rounds,
        'seed': seed, 'area_size': area_size, 'tx_power_dbm': tx_power, 'environment': env_name,
        'pdr_expected': 0.0, 'total_energy_mj': 0.0, 'error': None,
    }

    try:
        config = NetworkConfig()
        config.num_nodes = num_nodes
        config.area_width = config.area_height = area_size
        config.base_station_x = area_size / 2
        config.base_station_y = area_size
        config.tx_power_dbm = tx_power
        config.positions = positions
        config.force_environment = env_name
        config.external_channel_model = channel

        proto = AerisProtocol(
            config, seed=seed, verbose=False,
            enable_gateway=ablation_cfg.get('enable_gateway', True),
            enable_cas=ablation_cfg.get('enable_cas', True),
            enable_skeleton=ablation_cfg.get('enable_skeleton', True),
        )
        proto.safety_fallback_enabled = ablation_cfg.get('safety_fallback_enabled', True)
        proto.run_simulation(max_rounds=num_rounds)

        result['pdr_expected'] = proto.get_pdr_expected()
        result['total_energy_mj'] = proto.get_total_energy_consumed()
    except Exception as e:
        result['error'] = f"{str(e)}"

    return result


def save_results(phase_data, output_dir):
    """保存单个阶段结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    phase_name = phase_data['phase']

    output = {
        'timestamp': timestamp,
        'experiment_type': phase_name,
        'run_tier': 'publication',
        'primary_metric': 'pdr_expected',
        'raw_results': phase_data['results']
    }

    outfile = os.path.join(output_dir, f"{phase_name}_{timestamp}.json")
    with open(outfile, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"已保存: {outfile}")
    return outfile


def run_phase13(workers):
    """Phase 13: 超长寿命 R=5000 (4环境×6配置×n=50) = 1200任务"""
    print("\n" + "="*60)
    print("Phase 13: 超长寿命实验 (R=5000)")
    print("="*60)

    tasks = []
    for env in ENVIRONMENTS:
        for cfg_name, cfg in ABLATION_CONFIGS.items():
            for seed in SEEDS_50:
                tasks.append((cfg_name, cfg, 100, 5000, seed, 200.0, 10.0, env))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)
    return {'phase': 'ultra_lifetime_r5000', 'results': results}


def run_phase14(workers):
    """Phase 14: 超大规模 N=3000 (4环境×6配置×n=30) = 720任务"""
    print("\n" + "="*60)
    print("Phase 14: 超大规模实验 (N=3000)")
    print("="*60)

    seeds_30 = list(range(42001, 42031))
    tasks = []
    for env in ENVIRONMENTS:
        for cfg_name, cfg in ABLATION_CONFIGS.items():
            for seed in seeds_30:
                tasks.append((cfg_name, cfg, 3000, 300, seed, 600.0, 10.0, env))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)
    return {'phase': 'mega_scale_n3000', 'results': results}


def run_phase15(workers):
    """Phase 15: 密集功率扫描 (15功率×4环境×6配置×n=50) = 18000任务"""
    print("\n" + "="*60)
    print("Phase 15: 密集功率扫描实验")
    print("="*60)

    power_levels = list(range(-5, 21, 2))  # -5 to 20, step 2 = 13 levels
    tasks = []
    for tx_power in power_levels:
        for env in ENVIRONMENTS:
            for cfg_name, cfg in ABLATION_CONFIGS.items():
                for seed in SEEDS_50:
                    tasks.append((cfg_name, cfg, 100, 300, seed, 200.0, tx_power, env))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)
    return {'phase': 'dense_power_sweep', 'results': results}


def run_phase16(workers):
    """Phase 16: 节点密度扫描 (12密度×4环境×6配置×n=50) = 14400任务"""
    print("\n" + "="*60)
    print("Phase 16: 节点密度扫描实验")
    print("="*60)

    node_counts = [50, 100, 150, 200, 300, 400, 500, 700, 1000, 1500, 2000, 2500]
    tasks = []
    for num_nodes in node_counts:
        area = 200.0 + num_nodes * 0.15
        for env in ENVIRONMENTS:
            for cfg_name, cfg in ABLATION_CONFIGS.items():
                for seed in SEEDS_50:
                    tasks.append((cfg_name, cfg, num_nodes, 300, seed, area, 10.0, env))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)
    return {'phase': 'node_density_sweep', 'results': results}


def run_phase17(workers):
    """Phase 17: 区域尺寸扫描 (10尺寸×4环境×6配置×n=50) = 12000任务"""
    print("\n" + "="*60)
    print("Phase 17: 区域尺寸扫描实验")
    print("="*60)

    area_sizes = [100, 150, 200, 250, 300, 400, 500, 600, 800, 1000]
    tasks = []
    for area in area_sizes:
        for env in ENVIRONMENTS:
            for cfg_name, cfg in ABLATION_CONFIGS.items():
                for seed in SEEDS_50:
                    tasks.append((cfg_name, cfg, 100, 300, seed, float(area), 10.0, env))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)
    return {'phase': 'area_size_sweep', 'results': results}


def run_phase18(workers):
    """Phase 18: 轮次敏感性扩展 (8轮次×4环境×6配置×n=100) = 19200任务"""
    print("\n" + "="*60)
    print("Phase 18: 轮次敏感性扩展实验")
    print("="*60)

    round_counts = [50, 100, 200, 500, 1000, 2000, 3000, 5000]
    tasks = []
    for num_rounds in round_counts:
        for env in ENVIRONMENTS:
            for cfg_name, cfg in ABLATION_CONFIGS.items():
                for seed in SEEDS_100:
                    tasks.append((cfg_name, cfg, 100, num_rounds, seed, 200.0, 10.0, env))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)
    return {'phase': 'round_sensitivity_extended', 'results': results}


def run_phase19(workers):
    """Phase 19: 极端条件组合 (20组合×6配置×n=100) = 12000任务"""
    print("\n" + "="*60)
    print("Phase 19: 极端条件组合实验")
    print("="*60)

    extreme_combos = [
        (500, 600.0, 3.0, 'outdoor_suburban'),
        (1000, 400.0, 5.0, 'indoor_factory'),
        (200, 800.0, 0.0, 'outdoor_urban'),
        (800, 300.0, 7.0, 'indoor_office'),
        (1500, 500.0, 10.0, 'outdoor_suburban'),
        (300, 700.0, 2.0, 'outdoor_urban'),
        (600, 350.0, 8.0, 'indoor_factory'),
        (2000, 600.0, 15.0, 'indoor_office'),
        (400, 900.0, 1.0, 'outdoor_suburban'),
        (1200, 450.0, 6.0, 'indoor_factory'),
        (250, 550.0, 4.0, 'outdoor_urban'),
        (700, 250.0, 12.0, 'indoor_office'),
        (900, 650.0, 9.0, 'outdoor_suburban'),
        (350, 400.0, 11.0, 'indoor_factory'),
        (1100, 350.0, 3.0, 'outdoor_urban'),
        (450, 500.0, 7.0, 'indoor_office'),
        (1300, 550.0, 5.0, 'outdoor_suburban'),
        (550, 300.0, 14.0, 'indoor_factory'),
        (1600, 700.0, 8.0, 'outdoor_urban'),
        (650, 450.0, 10.0, 'indoor_office'),
    ]

    tasks = []
    for (num_nodes, area, tx_power, env) in extreme_combos:
        for cfg_name, cfg in ABLATION_CONFIGS.items():
            for seed in SEEDS_100:
                tasks.append((cfg_name, cfg, num_nodes, 500, seed, area, tx_power, env))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)
    return {'phase': 'extreme_combinations', 'results': results}


def run_phase20(workers):
    """Phase 20: 统计显著性增强 (4环境×6配置×n=200) = 4800任务"""
    print("\n" + "="*60)
    print("Phase 20: 统计显著性增强实验")
    print("="*60)

    seeds_200 = list(range(42001, 42201))
    tasks = []
    for env in ENVIRONMENTS:
        for cfg_name, cfg in ABLATION_CONFIGS.items():
            for seed in seeds_200:
                tasks.append((cfg_name, cfg, 100, 300, seed, 200.0, 10.0, env))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)
    return {'phase': 'statistical_significance', 'results': results}


def main():
    parser = argparse.ArgumentParser(description='超大规模追加实验 Phase 13-20')
    parser.add_argument('--phase', type=str, default='all',
                        choices=['all', '13', '14', '15', '16', '17', '18', '19', '20'])
    parser.add_argument('--workers', type=int, default=0)
    args = parser.parse_args()

    workers = args.workers if args.workers > 0 else MAX_WORKERS
    output_dir = 'results/mega_experiments'
    os.makedirs(output_dir, exist_ok=True)

    print(f"超大规模追加实验 Phase 13-20")
    print(f"并行核数: {workers}")
    start_time = datetime.now()

    saved_files = []
    phases = {
        '13': run_phase13, '14': run_phase14, '15': run_phase15,
        '16': run_phase16, '17': run_phase17, '18': run_phase18,
        '19': run_phase19, '20': run_phase20,
    }

    if args.phase == 'all':
        for p in ['13', '14', '15', '16', '17', '18', '19', '20']:
            data = phases[p](workers)
            saved_files.append(save_results(data, output_dir))
    else:
        data = phases[args.phase](workers)
        saved_files.append(save_results(data, output_dir))

    elapsed = datetime.now() - start_time
    print(f"\n总耗时: {elapsed}")
    print(f"保存文件: {saved_files}")


if __name__ == "__main__":
    main()
