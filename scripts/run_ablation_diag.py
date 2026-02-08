#!/usr/bin/env python3
"""
AERIS Ablation Experiment with Diagnostic Fields - RULES.md §5 Compliant

Required diagnostic fields:
- diag_flags: module enable/disable states
- diag_cas_modes: DIRECT/CHAIN/TWO_HOP counts
- diag_safety_overrides
- gateway_uplink_attempts / gateway_uplink_success
- skeleton_backbone_size / skeleton_assignments
- cas_total_decisions
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import gc
import psutil
import subprocess
import hashlib
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


def get_git_dirty():
    try:
        status = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            cwd=os.path.dirname(__file__)
        ).decode().strip()
        return bool(status)
    except:
        return True


def get_git_diff_stat():
    try:
        unstaged = subprocess.check_output(
            ['git', 'diff', '--shortstat'],
            cwd=os.path.dirname(__file__)
        ).decode().strip()
        staged = subprocess.check_output(
            ['git', 'diff', '--cached', '--shortstat'],
            cwd=os.path.dirname(__file__)
        ).decode().strip()
        return {
            'unstaged': unstaged if unstaged else 'clean',
            'staged': staged if staged else 'clean'
        }
    except:
        return {'unstaged': 'unknown', 'staged': 'unknown'}


def get_script_sha256(script_path):
    try:
        with open(script_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return 'unknown'


def get_config_hash(config_obj):
    try:
        canonical = json.dumps(config_obj, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    except:
        return 'unknown'


def check_memory_gb():
    return psutil.virtual_memory().used / (1024**3)


def generate_positions(seed, num_nodes, area_size):
    np.random.seed(seed)
    return [(np.random.uniform(0, area_size),
             np.random.uniform(0, area_size))
            for _ in range(num_nodes)]


def run_aeris_ablation(args):
    """Run AERIS with specific module configuration and collect diagnostics."""
    seed, positions, num_rounds, area_size, tx_power, env_name, ablation_config = args

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

    # Extract ablation flags
    enable_gateway = ablation_config.get('gateway', True)
    enable_cas = ablation_config.get('cas', True)
    enable_skeleton = ablation_config.get('skeleton', True)
    enable_safety = ablation_config.get('safety', True)
    config_name = ablation_config.get('name', 'unknown')

    result = {
        'protocol': 'AERIS',
        'ablation_config': config_name,
        'seed': seed,
        'environment': env_name,
        'pdr_expected': 0.0,
        'error': None,
        # Diagnostic fields per RULES.md §5
        'diag_flags': {
            'gateway': enable_gateway,
            'cas': enable_cas,
            'skeleton': enable_skeleton,
            'safety': enable_safety
        },
        'diag_cas_modes': {'DIRECT': 0, 'CHAIN': 0, 'TWO_HOP': 0},
        'diag_safety_overrides': 0,
        'gateway_uplink_attempts': 0,
        'gateway_uplink_success': 0,
        'skeleton_backbone_size': 0,
        'skeleton_assignments': 0,
        'cas_total_decisions': 0
    }

    try:
        config = NetworkConfig()
        config.num_nodes = len(positions)
        config.area_width = config.area_height = area_size
        config.base_station_x = area_size / 2
        config.base_station_y = area_size
        config.tx_power_dbm = tx_power
        config.positions = positions
        config.force_environment = env_name
        config.external_channel_model = channel

        proto = AerisProtocol(
            config, seed=seed, verbose=False,
            enable_gateway=enable_gateway,
            enable_cas=enable_cas,
            enable_skeleton=enable_skeleton
        )
        proto.safety_fallback_enabled = enable_safety
        proto.run_simulation(max_rounds=num_rounds)

        # Collect PDR
        if proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.bs_delivered_total / proto.source_packets_expected

        # Collect diagnostic fields
        if hasattr(proto, 'cas_mode_usage_stats'):
            stats = proto.cas_mode_usage_stats
            result['diag_cas_modes'] = {
                'DIRECT': stats.get('DIRECT', 0),
                'CHAIN': stats.get('CHAIN', 0),
                'TWO_HOP': stats.get('TWO_HOP', 0)
            }
            result['diag_safety_overrides'] = stats.get('safety_override', 0)
            result['cas_total_decisions'] = sum([
                stats.get('DIRECT', 0),
                stats.get('CHAIN', 0),
                stats.get('TWO_HOP', 0)
            ])

        if hasattr(proto, 'gateway_uplink_attempts_total'):
            result['gateway_uplink_attempts'] = proto.gateway_uplink_attempts_total
        if hasattr(proto, 'gateway_uplink_success_total'):
            result['gateway_uplink_success'] = proto.gateway_uplink_success_total

        # Skeleton diagnostics (use actual attribute names from skeleton_selector.py)
        # Note: skeleton_selector only created when far_ratio >= 0.3
        # skeleton_selector_created = object exists; actual effect shown by backbone_size/total_assignments
        result['skeleton_selector_created'] = hasattr(proto, 'skeleton_selector')
        if hasattr(proto, 'skeleton_selector'):
            if hasattr(proto.skeleton_selector, 'backbone_size'):
                result['skeleton_backbone_size'] = proto.skeleton_selector.backbone_size
            if hasattr(proto.skeleton_selector, 'total_assignments'):
                result['skeleton_assignments'] = proto.skeleton_selector.total_assignments

    except Exception as e:
        result['error'] = str(e)

    return result


def run_batch(tasks):
    all_results = []
    for i in range(0, len(tasks), BATCH_SIZE):
        if check_memory_gb() > MAX_MEMORY_GB:
            gc.collect()
        batch = tasks[i:i+BATCH_SIZE]
        print(f"  Batch {i//BATCH_SIZE + 1}: {len(batch)} tasks")
        with Pool(MAX_WORKERS) as pool:
            results = pool.map(run_aeris_ablation, batch)
        all_results.extend(results)
        gc.collect()
    return all_results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Smoke test mode')
    parser.add_argument('--env', type=str, default='indoor_office',
                        choices=['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban'],
                        help='Environment to run (default: indoor_office)')
    parser.add_argument('--multi-env', action='store_true',
                        help='Run all 4 environments')
    args = parser.parse_args()

    output_dir = 'results/mega_experiments'
    os.makedirs(output_dir, exist_ok=True)

    # Parameters per RULES.md §2.1
    num_nodes = 100
    num_rounds = 300
    area_size = 200.0
    tx_power = 10.0

    # Environment selection
    ALL_ENVIRONMENTS = ['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban']
    envs_to_run = ALL_ENVIRONMENTS if args.multi_env else [args.env]

    seeds = SEEDS[:5] if args.smoke else SEEDS
    run_tier = 'diagnostic' if args.smoke else 'publication'

    git_commit = get_git_commit()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ablation configurations
    ablation_configs = [
        {'name': 'full', 'gateway': True, 'cas': True, 'skeleton': True, 'safety': True},
        {'name': 'no_gateway', 'gateway': False, 'cas': True, 'skeleton': True, 'safety': True},
        {'name': 'no_cas', 'gateway': True, 'cas': False, 'skeleton': True, 'safety': True},
        {'name': 'no_skeleton', 'gateway': True, 'cas': True, 'skeleton': False, 'safety': True},
        {'name': 'no_safety', 'gateway': True, 'cas': True, 'skeleton': True, 'safety': False},
        {'name': 'minimal', 'gateway': False, 'cas': False, 'skeleton': False, 'safety': False},
    ]

    print(f"AERIS Ablation Experiment with Diagnostics")
    print(f"Mode: {'SMOKE' if args.smoke else 'FULL'}, Envs: {len(envs_to_run)}")
    print(f"Seeds: {len(seeds)}, Configs: {len(ablation_configs)}")

    # Pre-generate positions
    all_positions = {seed: generate_positions(seed, num_nodes, area_size)
                     for seed in seeds}

    all_results = []
    for env_name in envs_to_run:
        print(f"\n{'='*50}")
        print(f"Environment: {env_name}")
        for cfg in ablation_configs:
            print(f"  Running config: {cfg['name']}...")
            tasks = [(seed, all_positions[seed], num_rounds, area_size, tx_power, env_name, cfg)
                     for seed in seeds]
            results = run_batch(tasks)
            all_results.extend(results)

    # Build output with metadata per RULES.md §4
    env_field = 'multiple' if args.multi_env else envs_to_run[0]
    exp_type = 'ablation_env_sensitivity' if args.multi_env else 'ablation'
    config_obj = {
        'seeds': seeds,
        'node_counts': [num_nodes],
        'round_counts': [num_rounds],
        'dropout_rates': [0.0],
        'ablation_configs': [c['name'] for c in ablation_configs],
        'environments': envs_to_run,
        'area_size': area_size,
        'base_station': [area_size/2, area_size]
    }

    output = {
        'timestamp': timestamp,
        'git_commit': git_commit,
        'git_dirty': get_git_dirty(),
        'git_diff_stat': get_git_diff_stat(),
        'script_sha256': get_script_sha256(__file__),
        'experiment_type': exp_type,
        'run_tier': run_tier,
        'primary_metric': 'pdr_expected',
        'environment': env_field,
        'tx_power_dbm': tx_power,
        'config_hash': get_config_hash(config_obj),
        'config': config_obj,
        'raw_results': all_results
    }

    suffix = '_smoke' if args.smoke else ''
    env_suffix = '_multi' if args.multi_env else f'_{envs_to_run[0]}'
    outfile = os.path.join(output_dir, f"ablation_diag{env_suffix}{suffix}_{timestamp}.json")
    with open(outfile, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {outfile}")

    # Summary
    print("\n" + "="*60)
    print("Ablation Summary:")
    for cfg_name in [c['name'] for c in ablation_configs]:
        cfg_results = [r for r in all_results if r['ablation_config'] == cfg_name]
        errors = [r for r in cfg_results if r.get('error')]
        pdrs = [r['pdr_expected'] for r in cfg_results if not r.get('error')]
        if pdrs:
            # Aggregate diagnostics
            cas_decisions = sum(r['cas_total_decisions'] for r in cfg_results if not r.get('error'))
            safety_overrides = sum(r['diag_safety_overrides'] for r in cfg_results if not r.get('error'))
            gw_attempts = sum(r['gateway_uplink_attempts'] for r in cfg_results if not r.get('error'))
            gw_success = sum(r['gateway_uplink_success'] for r in cfg_results if not r.get('error'))
            gw_pdr = gw_success / gw_attempts if gw_attempts > 0 else 0.0

            print(f"  {cfg_name:12s}: PDR={np.mean(pdrs):.4f}+/-{np.std(pdrs):.4f}")
            print(f"               CAS decisions={cas_decisions}, safety_overrides={safety_overrides}")
            print(f"               GW attempts={gw_attempts}, success={gw_success}, PDR={gw_pdr:.4f}")
        else:
            print(f"  {cfg_name:12s}: ALL ERRORS ({len(errors)})")


if __name__ == "__main__":
    main()
