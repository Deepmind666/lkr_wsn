#!/usr/bin/env python3
"""
基线协议对比实验 - 符合RULES.md §4元数据规范
AERIS vs LEACH/PEGASIS/HEED/TEEN
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import gc
import psutil
import subprocess
import numpy as np
from datetime import datetime
from multiprocessing import Pool

# 内存限制：系统总内存96GB，预留50GB给系统，实验用45GB
MAX_MEMORY_GB = 45
MAX_WORKERS = 4
BATCH_SIZE = 30

SEEDS = list(range(42001, 42031))  # n=30 满足统计要求
ENVIRONMENTS = ['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban']


def get_git_commit():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=os.path.dirname(__file__)
        ).decode().strip()[:8]
    except:
        return 'unknown'


def check_memory_gb():
    return psutil.virtual_memory().used / (1024**3)


def wait_for_memory():
    import time
    while check_memory_gb() > MAX_MEMORY_GB:
        gc.collect()
        time.sleep(5)
        print(f"内存: {check_memory_gb():.1f}GB, 等待...")


def run_aeris(args):
    """运行AERIS协议"""
    seed, env_name, num_nodes, num_rounds, area_size, tx_power = args
    import random
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
        'protocol': 'AERIS', 'seed': seed, 'environment': env_name,
        'num_nodes': num_nodes, 'num_rounds': num_rounds,
        'tx_power_dbm': tx_power, 'pdr_expected': 0.0, 'error': None
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

        proto = AerisProtocol(config, seed=seed, verbose=False,
                              enable_gateway=True, enable_cas=True, enable_skeleton=True)
        proto.safety_fallback_enabled = True
        proto.run_simulation(max_rounds=num_rounds)

        if proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.bs_delivered_total / proto.source_packets_expected
    except Exception as e:
        result['error'] = str(e)

    return result


def run_leach(args):
    """运行LEACH协议"""
    seed, env_name, num_nodes, num_rounds, area_size, tx_power = args
    import random
    random.seed(seed)
    np.random.seed(seed)

    from final_corrected_leach import FinalCorrectedLEACH, NetworkConfig

    result = {
        'protocol': 'LEACH', 'seed': seed, 'environment': env_name,
        'num_nodes': num_nodes, 'num_rounds': num_rounds,
        'tx_power_dbm': tx_power, 'pdr_expected': 0.0, 'error': None
    }

    try:
        config = NetworkConfig()
        config.num_nodes = num_nodes
        config.area_width = config.area_height = area_size
        config.base_station_x = area_size / 2
        config.base_station_y = area_size

        proto = FinalCorrectedLEACH(config, seed=seed, verbose=False)
        proto.run_simulation(max_rounds=num_rounds)

        if proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.bs_delivered_total / proto.source_packets_expected
    except Exception as e:
        result['error'] = str(e)

    return result


def run_batch(func, tasks):
    """分批运行"""
    all_results = []
    for i in range(0, len(tasks), BATCH_SIZE):
        if check_memory_gb() > MAX_MEMORY_GB:
            wait_for_memory()
        batch = tasks[i:i+BATCH_SIZE]
        print(f"批次 {i//BATCH_SIZE + 1}: {len(batch)}任务, 内存{check_memory_gb():.1f}GB")
        with Pool(MAX_WORKERS) as pool:
            results = pool.map(func, batch)
        all_results.extend(results)
        gc.collect()
    return all_results


def main():
    output_dir = 'results/mega_experiments'
    os.makedirs(output_dir, exist_ok=True)

    num_nodes = 100
    num_rounds = 300
    area_size = 200.0
    tx_power = 10.0

    git_commit = get_git_commit()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"基线对比实验")
    print(f"内存限制: {MAX_MEMORY_GB}GB, 当前: {check_memory_gb():.1f}GB")

    tasks = []
    for env in ENVIRONMENTS:
        for seed in SEEDS:
            tasks.append((seed, env, num_nodes, num_rounds, area_size, tx_power))

    all_results = []

    print(f"\n运行AERIS ({len(tasks)}任务)")
    aeris_results = run_batch(run_aeris, tasks)
    all_results.extend(aeris_results)

    print(f"\n运行LEACH ({len(tasks)}任务)")
    leach_results = run_batch(run_leach, tasks)
    all_results.extend(leach_results)

    output = {
        'timestamp': timestamp,
        'git_commit': git_commit,
        'experiment_type': 'baseline_compare',
        'run_tier': 'publication',
        'primary_metric': 'pdr_expected',
        'environment': 'multiple',
        'tx_power_dbm': tx_power,
        'config': {
            'seeds': SEEDS,
            'environments': ENVIRONMENTS,
            'num_nodes': num_nodes,
            'num_rounds': num_rounds,
            'protocols': ['AERIS', 'LEACH']
        },
        'raw_results': all_results
    }

    outfile = os.path.join(output_dir, f"baseline_compare_{timestamp}.json")
    with open(outfile, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n保存: {outfile}")


if __name__ == "__main__":
    main()