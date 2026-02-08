#!/usr/bin/env python3
"""
扩容实验 Phase 6-9
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
SEEDS_30 = list(range(42001, 42031))

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
}

ENVIRONMENTS = ['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban']
POWER_LEVELS = [0, 3, 5, 7, 10, 15, 20]


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


def run_phase6_ultra_long(workers):
    """Phase 6: 超长轮次 R=2000 (3场景×6配置×n=50)"""
    print("\n" + "="*60)
    print("Phase 6: 超长轮次实验 (R=2000)")
    print("="*60)

    tasks = []
    for scenario_name, scfg in SCENARIOS.items():
        for config_name, ablation_cfg in ABLATION_CONFIGS.items():
            for seed in SEEDS_50:
                tasks.append((
                    config_name, ablation_cfg, scfg['num_nodes'], 2000, seed,
                    scfg['area_size'], scfg['tx_power_dbm'], scfg['environment']
                ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'ultra_long_r2000', 'results': results}


def run_phase7_mega_scale(workers):
    """Phase 7: 极大规模 N=2000 (6配置×n=30)"""
    print("\n" + "="*60)
    print("Phase 7: 极大规模实验 (N=2000)")
    print("="*60)

    tasks = []
    for config_name, ablation_cfg in ABLATION_CONFIGS.items():
        for seed in SEEDS_30:
            tasks.append((
                config_name, ablation_cfg, 2000, 500, seed,
                500.0, 10.0, 'indoor_factory'
            ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'mega_scale_n2000', 'results': results}


def run_phase8_full_cross(workers):
    """Phase 8: 全功率×全环境交叉 (7功率×4环境×6配置×n=30)"""
    print("\n" + "="*60)
    print("Phase 8: 全功率×全环境交叉实验")
    print("="*60)

    tasks = []
    for tx_power in POWER_LEVELS:
        for env_name in ENVIRONMENTS:
            for config_name, ablation_cfg in ABLATION_CONFIGS.items():
                for seed in SEEDS_30:
                    tasks.append((
                        config_name, ablation_cfg, 100, 300, seed,
                        200.0, tx_power, env_name
                    ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'full_power_env_cross', 'results': results}


def run_phase9_round_sensitivity(workers):
    """Phase 9: 多轮次敏感性 R=[100,200,500,1000,2000] (5轮次×3场景×6配置×n=30)"""
    print("\n" + "="*60)
    print("Phase 9: 多轮次敏感性实验")
    print("="*60)

    round_counts = [100, 200, 500, 1000, 2000]
    tasks = []
    for num_rounds in round_counts:
        for scenario_name, scfg in SCENARIOS.items():
            for config_name, ablation_cfg in ABLATION_CONFIGS.items():
                for seed in SEEDS_30:
                    tasks.append((
                        config_name, ablation_cfg, scfg['num_nodes'], num_rounds, seed,
                        scfg['area_size'], scfg['tx_power_dbm'], scfg['environment']
                    ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'round_sensitivity', 'results': results}


def run_phase10_node_scaling(workers):
    """Phase 10: 节点规模扩展 N=[50,100,200,300,500,800,1000,1500,2000] (9规模×6配置×n=30)"""
    print("\n" + "="*60)
    print("Phase 10: 节点规模扩展实验")
    print("="*60)

    node_counts = [50, 100, 200, 300, 500, 800, 1000, 1500, 2000]
    tasks = []
    for num_nodes in node_counts:
        area_size = 200.0 + (num_nodes / 10)  # 动态调整区域
        for config_name, ablation_cfg in ABLATION_CONFIGS.items():
            for seed in SEEDS_30:
                tasks.append((
                    config_name, ablation_cfg, num_nodes, 300, seed,
                    area_size, 10.0, 'indoor_office'
                ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'node_scaling', 'results': results}


def run_phase11_area_scaling(workers):
    """Phase 11: 区域规模扩展 Area=[100,200,300,400,500,600] (6区域×3节点数×6配置×n=30)"""
    print("\n" + "="*60)
    print("Phase 11: 区域规模扩展实验")
    print("="*60)

    area_sizes = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0]
    node_counts = [100, 200, 300]
    tasks = []
    for area_size in area_sizes:
        for num_nodes in node_counts:
            for config_name, ablation_cfg in ABLATION_CONFIGS.items():
                for seed in SEEDS_30:
                    tasks.append((
                        config_name, ablation_cfg, num_nodes, 300, seed,
                        area_size, 10.0, 'indoor_office'
                    ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'area_scaling', 'results': results}


def run_phase12_extreme_conditions(workers):
    """Phase 12: 极端条件实验 (低功率+大区域+多节点组合)"""
    print("\n" + "="*60)
    print("Phase 12: 极端条件实验")
    print("="*60)

    extreme_configs = [
        {'num_nodes': 500, 'area_size': 600.0, 'tx_power': 3.0, 'env': 'outdoor_suburban'},
        {'num_nodes': 300, 'area_size': 500.0, 'tx_power': 5.0, 'env': 'outdoor_suburban'},
        {'num_nodes': 1000, 'area_size': 400.0, 'tx_power': 7.0, 'env': 'indoor_factory'},
        {'num_nodes': 200, 'area_size': 600.0, 'tx_power': 0.0, 'env': 'outdoor_urban'},
        {'num_nodes': 800, 'area_size': 300.0, 'tx_power': 10.0, 'env': 'indoor_factory'},
    ]

    tasks = []
    for ext_cfg in extreme_configs:
        for config_name, ablation_cfg in ABLATION_CONFIGS.items():
            for seed in SEEDS_50:
                tasks.append((
                    config_name, ablation_cfg, ext_cfg['num_nodes'], 500, seed,
                    ext_cfg['area_size'], ext_cfg['tx_power'], ext_cfg['env']
                ))

    print(f"任务数: {len(tasks)}, 并行: {workers}核")
    with Pool(workers) as pool:
        results = pool.map(run_single_experiment, tasks)

    return {'phase': 'extreme_conditions', 'results': results}


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
    parser = argparse.ArgumentParser(description='扩容实验 Phase 6-12')
    parser.add_argument('--phase', type=str, default='all',
                        choices=['all', '6', '7', '8', '9', '10', '11', '12'],
                        help='运行哪个阶段')
    parser.add_argument('--workers', type=int, default=0,
                        help='并行数(0=auto, 保留2核)')
    args = parser.parse_args()

    workers = args.workers if args.workers > 0 else MAX_WORKERS
    output_dir = 'results/mega_experiments'
    os.makedirs(output_dir, exist_ok=True)

    print(f"扩容实验 Phase 6-12 启动")
    print(f"并行核数: {workers}")
    print(f"输出目录: {output_dir}")
    start_time = datetime.now()

    saved_files = []

    if args.phase in ['all', '6']:
        data = run_phase6_ultra_long(workers)
        saved_files.append(save_results(data, output_dir))

    if args.phase in ['all', '7']:
        data = run_phase7_mega_scale(workers)
        saved_files.append(save_results(data, output_dir))

    if args.phase in ['all', '8']:
        data = run_phase8_full_cross(workers)
        saved_files.append(save_results(data, output_dir))

    if args.phase in ['all', '9']:
        data = run_phase9_round_sensitivity(workers)
        saved_files.append(save_results(data, output_dir))

    if args.phase in ['all', '10']:
        data = run_phase10_node_scaling(workers)
        saved_files.append(save_results(data, output_dir))

    if args.phase in ['all', '11']:
        data = run_phase11_area_scaling(workers)
        saved_files.append(save_results(data, output_dir))

    if args.phase in ['all', '12']:
        data = run_phase12_extreme_conditions(workers)
        saved_files.append(save_results(data, output_dir))

    elapsed = datetime.now() - start_time
    print(f"\n总耗时: {elapsed}")
    print(f"保存文件: {saved_files}")


if __name__ == "__main__":
    main()
