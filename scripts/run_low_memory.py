#!/usr/bin/env python3
"""
低内存模式实验 - 控制内存使用不超过70%
串行执行，每批次完成后释放内存
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import gc
import psutil
import numpy as np
from datetime import datetime
from multiprocessing import Pool

MAX_MEMORY_GB = 75  # 不超过80GB，留5GB余量
MAX_WORKERS = 4  # 低并行数
BATCH_SIZE = 50  # 每批50任务

ABLATION_CONFIGS = {
    'AERIS_full': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_gateway': {'enable_gateway': False, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_cas': {'enable_gateway': True, 'enable_cas': False, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_skeleton': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': False, 'safety_fallback_enabled': True},
    'AERIS_no_safety': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': False},
    'AERIS_baseline': {'enable_gateway': False, 'enable_cas': False, 'enable_skeleton': False, 'safety_fallback_enabled': False},
}

ENVIRONMENTS = ['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban']


def check_memory_gb():
    """检查内存使用量(GB)"""
    mem = psutil.virtual_memory()
    return mem.used / (1024**3)


def wait_for_memory(threshold_gb=MAX_MEMORY_GB):
    """等待内存降到阈值以下"""
    import time
    while check_memory_gb() > threshold_gb:
        gc.collect()
        time.sleep(5)
        print(f"内存: {check_memory_gb():.1f}GB, 等待...")


def run_single(args):
    """单次实验"""
    import random
    cfg_name, ablation_cfg, num_nodes, num_rounds, seed, area_size, tx_power, env_name = args

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

    result = {'config_name': cfg_name, 'seed': seed, 'pdr_expected': 0.0, 'error': None}

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

        proto = AerisProtocol(config, seed=seed, verbose=False,
                              enable_gateway=ablation_cfg.get('enable_gateway', True),
                              enable_cas=ablation_cfg.get('enable_cas', True),
                              enable_skeleton=ablation_cfg.get('enable_skeleton', True))
        proto.safety_fallback_enabled = ablation_cfg.get('safety_fallback_enabled', True)
        proto.run_simulation(max_rounds=num_rounds)

        # 正确计算PDR
        if proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.bs_delivered_total / proto.source_packets_expected
        else:
            result['pdr_expected'] = 0.0
        result['total_energy_mj'] = getattr(proto, 'total_energy_consumed', 0.0)
    except Exception as e:
        result['error'] = str(e)

    return result


def run_batch(tasks, batch_size=BATCH_SIZE):
    """分批运行，控制内存"""
    all_results = []
    total = len(tasks)

    for i in range(0, total, batch_size):
        mem_gb = check_memory_gb()
        if mem_gb > MAX_MEMORY_GB:
            print(f"内存 {mem_gb:.1f}GB > {MAX_MEMORY_GB}GB, 等待...")
            wait_for_memory()

        batch = tasks[i:i+batch_size]
        print(f"批次 {i//batch_size + 1}: {len(batch)} 任务, 内存 {check_memory_gb():.1f}GB")

        with Pool(MAX_WORKERS) as pool:
            results = pool.map(run_single, batch)

        all_results.extend(results)
        gc.collect()

    return all_results


def save_results(phase_name, results, output_dir):
    """保存结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        'timestamp': timestamp,
        'experiment_type': phase_name,
        'run_tier': 'publication',
        'primary_metric': 'pdr_expected',
        'raw_results': results
    }
    outfile = os.path.join(output_dir, f"{phase_name}_{timestamp}.json")
    with open(outfile, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"已保存: {outfile}")
    return outfile


def main():
    output_dir = 'results/mega_experiments'
    os.makedirs(output_dir, exist_ok=True)

    seeds_30 = list(range(42001, 42031))

    print(f"低内存模式实验")
    print(f"内存限制: {MAX_MEMORY_GB}GB")
    print(f"并行数: {MAX_WORKERS}")
    print(f"当前内存: {check_memory_gb():.1f}GB")

    # Phase 15: 密集功率扫描 (简化版)
    print("\n" + "="*50)
    print("Phase 15: 密集功率扫描 (简化版)")
    print("="*50)

    power_levels = [0, 5, 10, 15, 20]  # 简化为5个功率
    tasks = []
    for tx_power in power_levels:
        for env in ENVIRONMENTS:
            for cfg_name, cfg in ABLATION_CONFIGS.items():
                for seed in seeds_30:
                    tasks.append((cfg_name, cfg, 100, 300, seed, 200.0, tx_power, env))

    print(f"任务数: {len(tasks)}")
    results = run_batch(tasks, batch_size=50)
    save_results('dense_power_sweep', results, output_dir)
    gc.collect()

    # Phase 16: 节点密度扫描 (简化版)
    print("\n" + "="*50)
    print("Phase 16: 节点密度扫描 (简化版)")
    print("="*50)

    node_counts = [100, 300, 500, 1000]  # 简化为4个规模
    tasks = []
    for num_nodes in node_counts:
        area = 200.0 + num_nodes * 0.15
        for env in ENVIRONMENTS:
            for cfg_name, cfg in ABLATION_CONFIGS.items():
                for seed in seeds_30:
                    tasks.append((cfg_name, cfg, num_nodes, 300, seed, area, 10.0, env))

    print(f"任务数: {len(tasks)}")
    results = run_batch(tasks, batch_size=50)
    save_results('node_density_sweep', results, output_dir)
    gc.collect()

    # Phase 18: 轮次敏感性 (简化版)
    print("\n" + "="*50)
    print("Phase 18: 轮次敏感性 (简化版)")
    print("="*50)

    round_counts = [100, 500, 1000, 2000]  # 简化为4个轮次
    tasks = []
    for num_rounds in round_counts:
        for env in ENVIRONMENTS:
            for cfg_name, cfg in ABLATION_CONFIGS.items():
                for seed in seeds_30:
                    tasks.append((cfg_name, cfg, 100, num_rounds, seed, 200.0, 10.0, env))

    print(f"任务数: {len(tasks)}")
    results = run_batch(tasks, batch_size=50)
    save_results('round_sensitivity_extended', results, output_dir)
    gc.collect()

    print("\n完成!")
    print(f"最终内存: {check_memory():.1f}%")


if __name__ == "__main__":
    main()
