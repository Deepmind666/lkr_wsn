#!/usr/bin/env python3
"""
AERIS Ablation for Sparse/Low-Power Scenarios - Trigger CHAIN/TWO_HOP

Goal: Design scenarios where CAS CHAIN/TWO_HOP modes are triggered.
Based on CAS code analysis:
- dist_bs >= 0.5: TWO_HOP advantage (far distance relay)
- 0.3 <= dist_bs < 0.5: Transition zone (CHAIN competes)
- Low link quality favors CHAIN/TWO_HOP

Scenarios:
1. sparse_lowpower: 50 nodes, 400m area, 0 dBm TX (large dist_bs, low link)
2. corridor: 100 nodes, 100x400m area, 5 dBm TX (elongated, far from BS)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import gc
import psutil
import subprocess
import numpy as np
import random
from datetime import datetime
from multiprocessing import Pool

MAX_MEMORY_GB = 45
MAX_WORKERS = 4
BATCH_SIZE = 20

SEEDS = list(range(42001, 42031))  # n=30


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


def generate_sparse_positions(seed, num_nodes, area_size):
    """Uniform random in large area."""
    np.random.seed(seed)
    return [(np.random.uniform(0, area_size),
             np.random.uniform(0, area_size)) for _ in range(num_nodes)]


def generate_corridor_positions(seed, num_nodes, width, height):
    """Corridor: narrow width, long height."""
    np.random.seed(seed)
    return [(np.random.uniform(0, width),
             np.random.uniform(0, height)) for _ in range(num_nodes)]


def run_ablation_config(args):
    """Run single ablation config."""
    (seed, positions, num_rounds, area_width, area_height,
     tx_power, env_name, config_name, enable_gw, enable_cas,
     enable_skeleton, enable_safety) = args

    np.random.seed(seed)
    random.seed(seed)

    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol
    from realistic_channel_model import RealisticChannelModel, EnvironmentType

    env_map = {
        'indoor_office': EnvironmentType.INDOOR_OFFICE,
        'indoor_factory': EnvironmentType.INDOOR_FACTORY,
        'outdoor_urban': EnvironmentType.OUTDOOR_URBAN,
        'outdoor_suburban': EnvironmentType.OUTDOOR_SUBURBAN,
    }

    channel = RealisticChannelModel(env_map.get(env_name, EnvironmentType.INDOOR_OFFICE))
    channel.reset_rng(seed)

    result = {
        'config': config_name,
        'seed': seed,
        'scenario': env_name,
        'area': f'{area_width}x{area_height}',
        'tx_power_dbm': tx_power,
        'num_nodes': len(positions),
        'pdr_expected': 0.0,
        'error': None,
        'diag_flags': {
            'enable_gateway': enable_gw,
            'enable_cas': enable_cas,
            'enable_skeleton': enable_skeleton,
            'safety_fallback_enabled': enable_safety
        },
        'cas_total_decisions': 0,
        'cas_direct': 0,
        'cas_chain': 0,
        'cas_twohop': 0,
        'diag_safety_overrides': 0,
        'gateway_uplink_attempts': 0,
        'gateway_uplink_success': 0,
        'skeleton_selector_created': False,
    }

    try:
        config = NetworkConfig()
        config.num_nodes = len(positions)
        config.area_width = area_width
        config.area_height = area_height
        config.base_station_x = area_width / 2
        config.base_station_y = area_height
        config.tx_power_dbm = tx_power
        config.positions = positions  # Pass positions via config

        proto = AerisProtocol(config, seed=seed, verbose=False,
                              enable_gateway=enable_gw,
                              enable_cas=enable_cas,
                              enable_skeleton=enable_skeleton)
        proto.safety_fallback_enabled = enable_safety
        proto.run_simulation(max_rounds=num_rounds)

        if proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.bs_delivered_total / proto.source_packets_expected

        # CAS diagnostics
        if hasattr(proto, 'cas_mode_usage_stats'):
            stats = proto.cas_mode_usage_stats
            result['cas_direct'] = stats.get('DIRECT', 0)
            result['cas_chain'] = stats.get('CHAIN', 0)
            result['cas_twohop'] = stats.get('TWO_HOP', 0)
            result['diag_safety_overrides'] = stats.get('safety_override', 0)
            result['cas_total_decisions'] = sum([
                stats.get('DIRECT', 0),
                stats.get('CHAIN', 0),
                stats.get('TWO_HOP', 0)
            ])

        # Gateway diagnostics
        if hasattr(proto, 'gateway_uplink_attempts_total'):
            result['gateway_uplink_attempts'] = proto.gateway_uplink_attempts_total
        if hasattr(proto, 'gateway_uplink_success_total'):
            result['gateway_uplink_success'] = proto.gateway_uplink_success_total

        # Skeleton diagnostics
        result['skeleton_selector_created'] = hasattr(proto, 'skeleton_selector')

    except Exception as e:
        result['error'] = str(e)

    return result


def run_batch(tasks):
    """Run tasks sequentially with memory control."""
    results = []
    for i, task in enumerate(tasks):
        if check_memory_gb() > MAX_MEMORY_GB:
            gc.collect()
        results.append(run_ablation_config(task))
        if (i + 1) % 10 == 0:
            print(f"    Progress: {i+1}/{len(tasks)}")
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Smoke test (n=5)')
    args = parser.parse_args()

    output_dir = 'results/mega_experiments'
    os.makedirs(output_dir, exist_ok=True)

    seeds = SEEDS[:5] if args.smoke else SEEDS
    run_tier = 'diagnostic' if args.smoke else 'publication'
    git_commit = get_git_commit()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"AERIS Sparse/Low-Power Ablation")
    print(f"Mode: {'SMOKE' if args.smoke else 'FULL'}")
    print(f"Seeds: {len(seeds)}")

    # Scenario definitions - adjusted for viable network
    scenarios = [
        {
            'name': 'sparse_medium',
            'num_nodes': 50,
            'area_width': 300.0,
            'area_height': 300.0,
            'tx_power': 5.0,  # Medium power
            'env': 'outdoor_suburban',
            'num_rounds': 300,
            'gen_func': lambda s, n, w, h: generate_sparse_positions(s, n, w),
        },
        {
            'name': 'corridor_long',
            'num_nodes': 100,
            'area_width': 150.0,
            'area_height': 350.0,
            'tx_power': 8.0,
            'env': 'indoor_factory',
            'num_rounds': 300,
            'gen_func': lambda s, n, w, h: generate_corridor_positions(s, n, w, h),
        },
    ]

    # Ablation configs
    ablation_configs = [
        ('full', True, True, True, True),
        ('no_gateway', False, True, True, True),
        ('no_cas', True, False, True, True),
        ('no_skeleton', True, True, False, True),
        ('no_safety', True, True, True, False),
        ('minimal', False, False, False, False),
    ]

    all_results = []

    for scenario in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario['name']}")
        print(f"  Nodes: {scenario['num_nodes']}, Area: {scenario['area_width']}x{scenario['area_height']}")
        print(f"  TX Power: {scenario['tx_power']} dBm, Env: {scenario['env']}")

        # Pre-generate positions
        positions_map = {}
        for seed in seeds:
            positions_map[seed] = scenario['gen_func'](
                seed, scenario['num_nodes'],
                scenario['area_width'], scenario['area_height']
            )

        for cfg_name, en_gw, en_cas, en_sk, en_sf in ablation_configs:
            print(f"\n  Config: {cfg_name}")
            tasks = []
            for seed in seeds:
                tasks.append((
                    seed,
                    positions_map[seed],
                    scenario['num_rounds'],
                    scenario['area_width'],
                    scenario['area_height'],
                    scenario['tx_power'],
                    scenario['env'],
                    cfg_name,
                    en_gw, en_cas, en_sk, en_sf
                ))

            results = run_batch(tasks)
            all_results.extend(results)

            # Summary for this config
            pdrs = [r['pdr_expected'] for r in results if not r.get('error')]
            cas_chain = sum(r['cas_chain'] for r in results if not r.get('error'))
            cas_twohop = sum(r['cas_twohop'] for r in results if not r.get('error'))
            cas_direct = sum(r['cas_direct'] for r in results if not r.get('error'))

            if pdrs:
                print(f"    PDR: {np.mean(pdrs):.4f} +/- {np.std(pdrs):.4f}")
                print(f"    CAS: DIRECT={cas_direct}, CHAIN={cas_chain}, TWO_HOP={cas_twohop}")

    # Save results
    output = {
        'timestamp': timestamp,
        'git_commit': git_commit,
        'experiment_type': 'ablation_sparse_lowpower',
        'run_tier': run_tier,
        'primary_metric': 'pdr_expected',
        'config': {
            'seeds': seeds,
            'scenarios': [s['name'] for s in scenarios],
        },
        'raw_results': all_results
    }

    suffix = '_smoke' if args.smoke else ''
    outfile = os.path.join(output_dir, f"ablation_sparse_lowpower{suffix}_{timestamp}.json")
    with open(outfile, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {outfile}")

    # Final summary
    print("\n" + "="*60)
    print("CAS Mode Trigger Summary:")
    for scenario in scenarios:
        print(f"\n  [{scenario['name']}]")
        for cfg_name, _, _, _, _ in ablation_configs:
            cfg_results = [r for r in all_results
                          if r['config'] == cfg_name and scenario['name'] in r.get('scenario', '')]
            # Filter by area to match scenario
            cfg_results = [r for r in cfg_results
                          if r.get('area') == f"{scenario['area_width']}x{scenario['area_height']}"]
            if cfg_results:
                chain = sum(r['cas_chain'] for r in cfg_results)
                twohop = sum(r['cas_twohop'] for r in cfg_results)
                direct = sum(r['cas_direct'] for r in cfg_results)
                total = chain + twohop + direct
                if total > 0:
                    print(f"    {cfg_name}: CHAIN={chain} ({100*chain/total:.1f}%), "
                          f"TWO_HOP={twohop} ({100*twohop/total:.1f}%)")


if __name__ == "__main__":
    main()
