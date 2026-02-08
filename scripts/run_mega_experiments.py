#!/usr/bin/env python3
"""
12小时大规模实验脚本
设备: Intel Core Ultra 9 285K (24核), 95GB RAM, RTX 5090
目标: 充分利用算力，保留2核供日常办公
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

# 保留2核供日常办公
MAX_WORKERS = max(1, cpu_count() - 2)  # 22核

SEEDS_100 = list(range(42001, 42101))  # n=100
SEEDS_50 = list(range(42001, 42051))   # n=50
SEEDS_30 = list(range(42001, 42031))   # n=30

ABLATION_CONFIGS = {
    'AERIS_full': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_gateway': {'enable_gateway': False, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_cas': {'enable_gateway': True, 'enable_cas': False, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_skeleton': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': False, 'safety_fallback_enabled': True},
    'AERIS_no_safety': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': False},
    'AERIS_baseline': {'enable_gateway': False, 'enable_cas': False, 'enable_skeleton': False, 'safety_fallback_enabled': False},
}

SCENARIOS = {
    'default': {'num_nodes': 100, 'area_size': 200.0, 'tx_power_dbm': 10.0, 'environment': 'indoor_office'},
    'sparse_lowpower': {'num_nodes': 200, 'area_size': 400.0, 'tx_power_dbm': 5.0, 'environment': 'outdoor_suburban'},
    'dense_indoor': {'num_nodes': 300, 'area_size': 200.0, 'tx_power_dbm': 10.0, 'environment': 'indoor_factory'},
    'ultra_sparse': {'num_nodes': 100, 'area_size': 500.0, 'tx_power_dbm': 3.0, 'environment': 'outdoor_suburban'},
    'mega_dense': {'num_nodes': 500, 'area_size': 200.0, 'tx_power_dbm': 10.0, 'environment': 'indoor_factory'},
}

ENVIRONMENTS = ['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban']
POWER_LEVELS = [0, 3, 5, 7, 10, 15, 20]
NODE_COUNTS = [100, 200, 300, 500]


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
        result['error'] = f"{str(e)}\n{traceback.format_exc()}"

    return result


def run_phase1_ablation(workers):
    """Phase 1: 多场景消融实验 (5场景×6配置×n=100)"""
    print("\n" + "="*60)
    print("Phase 1: 多场景消融实验 (n=100 seeds)")
    print("="*60)

    tasks = []
    for scenario_name, scfg in SCENARIOS.items():
        for config_name, ablation_cfg in ABLATION_CONFIGS.items():
            for seed in SEEDS_100:
                tasks.append((
                    config_name, ablation_cfg, scfg['num_nodes'], 300, seed,
                    scfg['area_size'], scfg['tx_power_dbm'], scfg['environment']
                ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'ablation_multi_scenario', 'results': results}


def run_phase2_power(workers):
    """Phase 2: 功率敏感性实验 (7功率×3场景×n=50)"""
    print("\n" + "="*60)
    print("Phase 2: 功率敏感性实验")
    print("="*60)

    base_scenarios = ['default', 'sparse_lowpower', 'dense_indoor']
    tasks = []
    for scenario_name in base_scenarios:
        scfg = SCENARIOS[scenario_name]
        for tx_power in POWER_LEVELS:
            for config_name, ablation_cfg in ABLATION_CONFIGS.items():
                for seed in SEEDS_50:
                    tasks.append((
                        config_name, ablation_cfg, scfg['num_nodes'], 300, seed,
                        scfg['area_size'], tx_power, scfg['environment']
                    ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'power_sensitivity', 'results': results}


def run_phase3_environment(workers):
    """Phase 3: 环境敏感性实验 (4环境×4规模×n=50)"""
    print("\n" + "="*60)
    print("Phase 3: 环境敏感性实验")
    print("="*60)

    tasks = []
    for env_name in ENVIRONMENTS:
        for num_nodes in NODE_COUNTS:
            area_size = 200.0 if num_nodes <= 300 else 300.0
            for config_name, ablation_cfg in ABLATION_CONFIGS.items():
                for seed in SEEDS_50:
                    tasks.append((
                        config_name, ablation_cfg, num_nodes, 300, seed,
                        area_size, 10.0, env_name
                    ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'environment_sensitivity', 'results': results}


def run_phase4_lifetime(workers):
    """Phase 4: 长轮次网络寿命实验 (R=1000×3场景×n=50)"""
    print("\n" + "="*60)
    print("Phase 4: 长轮次网络寿命实验 (R=1000)")
    print("="*60)

    base_scenarios = ['default', 'sparse_lowpower', 'dense_indoor']
    tasks = []
    for scenario_name in base_scenarios:
        scfg = SCENARIOS[scenario_name]
        for config_name, ablation_cfg in ABLATION_CONFIGS.items():
            for seed in SEEDS_50:
                tasks.append((
                    config_name, ablation_cfg, scfg['num_nodes'], 1000, seed,
                    scfg['area_size'], scfg['tx_power_dbm'], scfg['environment']
                ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'long_lifetime', 'results': results}


def run_phase5_ultra_scale(workers):
    """Phase 5: 超大规模实验 (N=1000×n=30)"""
    print("\n" + "="*60)
    print("Phase 5: 超大规模实验 (N=1000)")
    print("="*60)

    tasks = []
    for config_name, ablation_cfg in ABLATION_CONFIGS.items():
        for seed in SEEDS_30:
            tasks.append((
                config_name, ablation_cfg, 1000, 500, seed,
                400.0, 10.0, 'indoor_factory'
            ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'ultra_scale', 'results': results}


def save_results(phase_data, output_dir):
    """保存单个阶段结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    phase_name = phase_data['phase']

    try:
        import subprocess
        git_commit = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=os.path.dirname(__file__)
        ).decode().strip()[:8]
    except Exception:
        git_commit = 'unknown'

    output = {
        'timestamp': timestamp,
        'git_commit': git_commit,
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


def main():
    parser = argparse.ArgumentParser(description='12小时大规模实验')
    parser.add_argument('--phase', type=str, default='all',
                        choices=['all', '1', '2', '3', '4', '5'],
                        help='运行哪个阶段')
    parser.add_argument('--workers', type=int, default=0,
                        help='并行数(0=auto, 保留2核)')
    args = parser.parse_args()

    workers = args.workers if args.workers > 0 else MAX_WORKERS
    output_dir = 'results/mega_experiments'
    os.makedirs(output_dir, exist_ok=True)

    print(f"12小时大规模实验启动")
    print(f"并行核数: {workers}")
    print(f"输出目录: {output_dir}")
    start_time = datetime.now()

    saved_files = []

    if args.phase in ['all', '1']:
        data = run_phase1_ablation(workers)
        saved_files.append(save_results(data, output_dir))

    if args.phase in ['all', '2']:
        data = run_phase2_power(workers)
        saved_files.append(save_results(data, output_dir))

    if args.phase in ['all', '3']:
        data = run_phase3_environment(workers)
        saved_files.append(save_results(data, output_dir))

    if args.phase in ['all', '4']:
        data = run_phase4_lifetime(workers)
        saved_files.append(save_results(data, output_dir))

    if args.phase in ['all', '5']:
        data = run_phase5_ultra_scale(workers)
        saved_files.append(save_results(data, output_dir))

    elapsed = datetime.now() - start_time
    print(f"\n总耗时: {elapsed}")
    print(f"保存文件: {saved_files}")


if __name__ == "__main__":
    main()
