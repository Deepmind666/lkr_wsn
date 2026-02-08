#!/usr/bin/env python3
"""
Smoke test to verify safety_fallback_enabled fix.
Target: ≤50 tasks, error rate = 0%
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import time
import numpy as np
from datetime import datetime
from multiprocessing import Pool

SEEDS = [42001, 42002, 42003, 42004, 42005]
ABLATION_CONFIGS = {
    'AERIS_full': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_gateway': {'enable_gateway': False, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_cas': {'enable_gateway': True, 'enable_cas': False, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_skeleton': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': False, 'safety_fallback_enabled': True},
    'AERIS_no_safety': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': False},
    'AERIS_baseline': {'enable_gateway': False, 'enable_cas': False, 'enable_skeleton': False, 'safety_fallback_enabled': False},
}


def run_single(args):
    config_name, ablation_cfg, seed = args
    import random
    random.seed(seed)
    np.random.seed(seed)

    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol
    from realistic_channel_model import RealisticChannelModel, EnvironmentType

    area_size = 200.0
    num_nodes = 100
    num_rounds = 50

    positions = [(np.random.uniform(0, area_size), np.random.uniform(0, area_size))
                 for _ in range(num_nodes)]
    channel = RealisticChannelModel(EnvironmentType.INDOOR_OFFICE)
    channel.reset_rng(seed)

    result = {'config_name': config_name, 'seed': seed, 'error': None, 'pdr': 0.0}

    try:
        config = NetworkConfig()
        config.num_nodes = num_nodes
        config.area_width = config.area_height = area_size
        config.base_station_x = area_size / 2
        config.base_station_y = area_size
        config.tx_power_dbm = 10.0
        config.positions = positions
        config.force_environment = 'indoor_office'
        config.external_channel_model = channel

        # Fixed: safety_fallback_enabled as instance attribute
        proto = AerisProtocol(config, seed=seed, verbose=False,
                              enable_gateway=ablation_cfg.get('enable_gateway', True),
                              enable_cas=ablation_cfg.get('enable_cas', True),
                              enable_skeleton=ablation_cfg.get('enable_skeleton', True))
        proto.safety_fallback_enabled = ablation_cfg.get('safety_fallback_enabled', True)
        proto.run_simulation(max_rounds=num_rounds)

        if proto.source_packets_expected > 0:
            result['pdr'] = proto.bs_delivered_total / proto.source_packets_expected
    except Exception as e:
        import traceback
        result['error'] = f"{str(e)}\n{traceback.format_exc()}"

    return result


def main():
    tasks = []
    for cfg_name, cfg in ABLATION_CONFIGS.items():
        for seed in SEEDS:
            tasks.append((cfg_name, cfg, seed))

    print(f"Smoke Test: {len(tasks)} tasks (6 configs x 5 seeds)")
    start = time.time()

    with Pool(4) as pool:
        results = pool.map(run_single, tasks)

    elapsed = time.time() - start
    errors = [r for r in results if r.get('error')]
    success = [r for r in results if not r.get('error')]

    print(f"Completed: {len(success)}/{len(tasks)} success")
    print(f"Error rate: {len(errors)/len(tasks)*100:.1f}%")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Avg per task: {elapsed/len(tasks):.2f}s")

    if errors:
        print("\nErrors:")
        for e in errors[:3]:
            print(f"  {e['config_name']}: {e['error'][:100]}")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output = {
        'timestamp': timestamp,
        'experiment_type': 'smoke_test',
        'run_tier': 'diagnostic',
        'task_count': len(tasks),
        'success_count': len(success),
        'error_count': len(errors),
        'error_rate': len(errors)/len(tasks),
        'elapsed_seconds': elapsed,
        'avg_time_per_task': elapsed/len(tasks),
        'results': results
    }

    outfile = f"results/smoke_test_{timestamp}.json"
    with open(outfile, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {outfile}")


if __name__ == "__main__":
    main()
