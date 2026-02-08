#!/usr/bin/env python3
"""
Fair 5-Protocol Comparison - RULES.md Compliant
AERIS vs LEACH/PEGASIS/HEED/TEEN

Key fixes:
1. Unified positions (np.random for all)
2. Unified channel_model for all protocols
3. Unified tx_power_dbm
4. Complete metadata per RULES.md §4
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

# Memory control
MAX_MEMORY_GB = 45
MAX_WORKERS = 4
BATCH_SIZE = 25

SEEDS = list(range(42001, 42031))  # n=30
ENVIRONMENTS = ['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban']


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
    """Generate unified positions for all protocols."""
    np.random.seed(seed)
    return [(np.random.uniform(0, area_size),
             np.random.uniform(0, area_size))
            for _ in range(num_nodes)]


def run_aeris(args):
    """Run AERIS protocol."""
    seed, positions, num_rounds, area_size, tx_power, env_name = args

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
        'protocol': 'AERIS', 'seed': seed, 'environment': env_name,
        'pdr_expected': 0.0, 'error': None,
        'total_energy_consumed': 0.0,
        'total_rounds': 0,
        'first_node_death_round': 0
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

        proto = AerisProtocol(config, seed=seed, verbose=False,
                              enable_gateway=True, enable_cas=True,
                              enable_skeleton=True)
        proto.safety_fallback_enabled = True
        proto.run_simulation(max_rounds=num_rounds)

        if proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.bs_delivered_total / proto.source_packets_expected

        # Energy and lifetime metrics
        if hasattr(proto, 'total_energy_consumed'):
            result['total_energy_consumed'] = proto.total_energy_consumed
        if hasattr(proto, 'round_statistics') and proto.round_statistics:
            result['total_rounds'] = len(proto.round_statistics)
            for i, rs in enumerate(proto.round_statistics):
                if rs.get('alive_nodes', 100) < len(positions):
                    result['first_node_death_round'] = i + 1
                    break
    except Exception as e:
        result['error'] = str(e)

    return result


def run_leach(args):
    """Run LEACH protocol with unified channel."""
    seed, positions, num_rounds, area_size, tx_power, env_name = args

    np.random.seed(seed)
    random.seed(seed)

    from baseline_protocols import LEACHProtocol
    from baseline_protocols.leach_protocol import LEACHNode
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
        'protocol': 'LEACH', 'seed': seed, 'environment': env_name,
        'pdr_expected': 0.0, 'error': None,
        'total_energy_consumed': 0.0,
        'total_rounds': 0,
        'first_node_death_round': 0
    }

    try:
        nodes = [LEACHNode(i, pos[0], pos[1], initial_energy=2.0)
                 for i, pos in enumerate(positions)]
        base_station = (area_size / 2, area_size)

        proto = LEACHProtocol(nodes, base_station,
                              tx_power_dbm=tx_power,
                              channel_model=channel,
                              use_unified_energy_model=True)
        proto.run_simulation(max_rounds=num_rounds)

        if proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.total_bs_delivered / proto.source_packets_expected

        # Energy metrics
        if hasattr(proto, 'total_energy_consumed'):
            result['total_energy_consumed'] = proto.total_energy_consumed
        # Lifetime: first_node_death_round from proto.network_lifetime
        if hasattr(proto, 'network_lifetime') and proto.network_lifetime > 0:
            result['first_node_death_round'] = proto.network_lifetime
        if hasattr(proto, 'current_round'):
            result['total_rounds'] = proto.current_round
    except Exception as e:
        result['error'] = str(e)

    return result


def run_pegasis(args):
    """Run PEGASIS protocol with unified channel."""
    seed, positions, num_rounds, area_size, tx_power, env_name = args

    np.random.seed(seed)
    random.seed(seed)

    from baseline_protocols import PEGASISProtocol
    from baseline_protocols.pegasis_protocol import PEGASISNode
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
        'protocol': 'PEGASIS', 'seed': seed, 'environment': env_name,
        'pdr_expected': 0.0, 'error': None,
        'total_energy_consumed': 0.0,
        'total_rounds': 0,
        'first_node_death_round': 0
    }

    try:
        nodes = [PEGASISNode(i, pos[0], pos[1], initial_energy=2.0)
                 for i, pos in enumerate(positions)]
        base_station = (area_size / 2, area_size)

        proto = PEGASISProtocol(nodes, base_station,
                                tx_power_dbm=tx_power,
                                channel_model=channel,
                                use_unified_energy_model=True)
        proto.run_simulation(max_rounds=num_rounds)

        if hasattr(proto, 'source_packets_expected') and proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.total_bs_delivered / proto.source_packets_expected
        elif hasattr(proto, 'packets_sent') and proto.packets_sent > 0:
            result['pdr_expected'] = proto.packets_received / proto.packets_sent

        # Energy metrics
        if hasattr(proto, 'total_energy_consumed'):
            result['total_energy_consumed'] = proto.total_energy_consumed
        # Lifetime: first_node_death_round from proto.network_lifetime
        if hasattr(proto, 'network_lifetime') and proto.network_lifetime > 0:
            result['first_node_death_round'] = proto.network_lifetime
        if hasattr(proto, 'current_round'):
            result['total_rounds'] = proto.current_round
    except Exception as e:
        result['error'] = str(e)

    return result


def run_heed(args):
    """Run HEED protocol with unified channel."""
    seed, positions, num_rounds, area_size, tx_power, env_name = args

    np.random.seed(seed)
    random.seed(seed)

    from baseline_protocols import HEEDProtocol
    from baseline_protocols.heed_protocol import HEEDNode
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
        'protocol': 'HEED', 'seed': seed, 'environment': env_name,
        'pdr_expected': 0.0, 'error': None,
        'total_energy_consumed': 0.0,
        'total_rounds': 0,
        'first_node_death_round': 0
    }

    try:
        nodes = [HEEDNode(i, pos[0], pos[1], initial_energy=2.0)
                 for i, pos in enumerate(positions)]
        base_station = (area_size / 2, area_size)

        proto = HEEDProtocol(nodes, base_station,
                             tx_power_dbm=tx_power,
                             channel_model=channel,
                             use_unified_energy_model=True)
        proto.run_simulation(max_rounds=num_rounds)

        if hasattr(proto, 'source_packets_expected') and proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.total_bs_delivered / proto.source_packets_expected
        elif hasattr(proto, 'packets_sent') and proto.packets_sent > 0:
            result['pdr_expected'] = proto.packets_received / proto.packets_sent

        # Energy metrics
        if hasattr(proto, 'total_energy_consumed'):
            result['total_energy_consumed'] = proto.total_energy_consumed
        # Lifetime: first_node_death_round from proto.network_lifetime
        if hasattr(proto, 'network_lifetime') and proto.network_lifetime > 0:
            result['first_node_death_round'] = proto.network_lifetime
        if hasattr(proto, 'current_round'):
            result['total_rounds'] = proto.current_round
    except Exception as e:
        result['error'] = str(e)

    return result


def run_teen(args):
    """Run TEEN protocol with unified channel."""
    seed, positions, num_rounds, area_size, tx_power, env_name = args

    np.random.seed(seed)
    random.seed(seed)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from teen_protocol import TEENProtocol, TEENConfig
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
        'protocol': 'TEEN', 'seed': seed, 'environment': env_name,
        'pdr_expected': 0.0, 'error': None,
        'total_energy_consumed': 0.0,
        'total_rounds': 0,
        'first_node_death_round': 0
    }

    try:
        config = TEENConfig()
        config.num_nodes = len(positions)
        config.area_width = config.area_height = area_size
        config.base_station_x = area_size / 2
        config.base_station_y = area_size
        config.tx_power_dbm = tx_power
        config.enable_channel = True
        config.channel_env = env_name

        proto = TEENProtocol(config, use_unified_energy_model=True)
        proto.initialize_network(positions)
        proto.channel_model = channel
        proto.run_simulation(max_rounds=num_rounds)

        if proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.bs_delivered_total / proto.source_packets_expected

        # Energy metrics
        if hasattr(proto, 'total_energy_consumed'):
            result['total_energy_consumed'] = proto.total_energy_consumed
        # Lifetime: first_node_death_round from proto.network_lifetime
        if hasattr(proto, 'network_lifetime') and proto.network_lifetime > 0:
            result['first_node_death_round'] = proto.network_lifetime
        if hasattr(proto, 'current_round'):
            result['total_rounds'] = proto.current_round
    except Exception as e:
        result['error'] = str(e)

    return result


def run_batch(func, tasks):
    """Run tasks in batches with memory control."""
    all_results = []
    for i in range(0, len(tasks), BATCH_SIZE):
        if check_memory_gb() > MAX_MEMORY_GB:
            gc.collect()
        batch = tasks[i:i+BATCH_SIZE]
        print(f"  Batch {i//BATCH_SIZE + 1}: {len(batch)} tasks")
        with Pool(MAX_WORKERS) as pool:
            results = pool.map(func, batch)
        all_results.extend(results)
        gc.collect()
    return all_results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Smoke test mode')
    parser.add_argument('--multi-env', action='store_true', help='Run all 4 environments')
    args = parser.parse_args()

    output_dir = 'results/mega_experiments'
    os.makedirs(output_dir, exist_ok=True)

    # Parameters per RULES.md §2.1
    num_nodes = 100
    num_rounds = 300
    area_size = 200.0
    tx_power = 10.0

    # Environment selection
    envs_to_run = ENVIRONMENTS if args.multi_env else ['indoor_office']

    seeds = SEEDS[:5] if args.smoke else SEEDS
    run_tier = 'diagnostic' if args.smoke else 'publication'

    git_commit = get_git_commit()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"Fair 5-Protocol Comparison")
    print(f"Mode: {'SMOKE' if args.smoke else 'FULL'}, Envs: {len(envs_to_run)}")
    print(f"Seeds: {len(seeds)}, Memory limit: {MAX_MEMORY_GB}GB")

    # Pre-generate positions for all seeds
    all_positions = {seed: generate_positions(seed, num_nodes, area_size)
                     for seed in seeds}

    all_results = []
    protocols = [
        ('AERIS', run_aeris),
        ('LEACH', run_leach),
        ('PEGASIS', run_pegasis),
        ('HEED', run_heed),
        ('TEEN', run_teen),
    ]

    for env_name in envs_to_run:
        print(f"\n{'='*50}")
        print(f"Environment: {env_name}")
        for proto_name, proto_func in protocols:
            print(f"\nRunning {proto_name}...")
            tasks = [(seed, all_positions[seed], num_rounds, area_size, tx_power, env_name)
                     for seed in seeds]
            results = run_batch(proto_func, tasks)
            all_results.extend(results)

    # Build output with complete metadata per RULES.md §4
    env_field = 'multiple' if args.multi_env else envs_to_run[0]
    config_obj = {
        'seeds': seeds,
        'node_counts': [num_nodes],
        'round_counts': [num_rounds],
        'dropout_rates': [0.0],
        'protocols': ['AERIS', 'LEACH', 'PEGASIS', 'HEED', 'TEEN'],
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
        'experiment_type': 'env_sensitivity' if args.multi_env else 'fair_5protocol',
        'run_tier': run_tier,
        'primary_metric': 'pdr_expected',
        'environment': env_field,
        'tx_power_dbm': tx_power,
        'config_hash': get_config_hash(config_obj),
        'config': config_obj,
        'raw_results': all_results
    }

    suffix = '_smoke' if args.smoke else ''
    exp_type = 'env_sensitivity' if args.multi_env else 'fair_5protocol'
    outfile = os.path.join(output_dir, f"{exp_type}{suffix}_{timestamp}.json")
    with open(outfile, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {outfile}")

    # Summary
    print("\n" + "="*50)
    print("Summary:")
    for env in envs_to_run:
        if args.multi_env:
            print(f"\n  [{env}]")
        for proto in ['AERIS', 'LEACH', 'PEGASIS', 'HEED', 'TEEN']:
            proto_results = [r for r in all_results
                           if r['protocol'] == proto and r.get('environment', envs_to_run[0]) == env]
            errors = [r for r in proto_results if r.get('error')]
            pdrs = [r['pdr_expected'] for r in proto_results if not r.get('error')]
            if pdrs:
                print(f"    {proto}: PDR={np.mean(pdrs):.4f}+/-{np.std(pdrs):.4f}, errors={len(errors)}/{len(proto_results)}")
            else:
                print(f"    {proto}: ALL ERRORS ({len(errors)})")


if __name__ == "__main__":
    main()
