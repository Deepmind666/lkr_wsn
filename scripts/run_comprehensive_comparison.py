#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS vs Baselines Comprehensive Comparison
- Protocols: AERIS, LEACH, PEGASIS, HEED, TEEN
- Scenarios: uniform, corridor
- Scales: 100, 200 nodes
- Seeds: 30 per configuration
"""
import os
import sys
import json
import time
import platform
import multiprocessing as mp
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

MAX_WORKERS = 19
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', f'comparison_{TIMESTAMP}')


def get_environment_info() -> Dict:
    import subprocess
    env_info = {
        'python_version': platform.python_version(),
        'platform': platform.platform(),
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


def run_aeris(params: Dict) -> Dict:
    import random
    import numpy as np
    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol

    random.seed(params['seed'])
    np.random.seed(params['seed'])

    cfg = NetworkConfig(**params['config'])
    proto = AerisProtocol(cfg, verbose=False, seed=params['seed'],
                          enable_cas=True, enable_fairness=True, enable_gateway=True)
    result = proto.run_simulation(max_rounds=params['max_rounds'])
    am = result.get('additional_metrics', {})
    usage = am.get('cas_mode_usage_stats', {})

    return {
        'protocol': 'AERIS',
        'seed': params['seed'],
        'scenario': params['scenario'],
        'num_nodes': params['config']['num_nodes'],
        'pdr_end2end': result.get('packet_delivery_ratio_end2end', 0),
        'total_energy': result.get('total_energy_consumed', 0),
        'rounds_completed': result.get('rounds_completed', 0),
        'cas_direct': usage.get('DIRECT', 0),
        'cas_chain': usage.get('CHAIN', 0),
        'cas_twohop': usage.get('TWO_HOP', 0),
    }


def run_leach(params: Dict) -> Dict:
    import random
    import numpy as np
    from benchmark_protocols import NetworkConfig, LEACHProtocol
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

    random.seed(params['seed'])
    np.random.seed(params['seed'])

    cfg = NetworkConfig(**params['config'])
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    proto = LEACHProtocol(cfg, em)
    result = proto.run_simulation(max_rounds=params['max_rounds'])

    return {
        'protocol': 'LEACH',
        'seed': params['seed'],
        'scenario': params['scenario'],
        'num_nodes': params['config']['num_nodes'],
        'pdr_end2end': result.get('packet_delivery_ratio_end2end', result.get('packet_delivery_ratio', 0)),
        'total_energy': result.get('total_energy_consumed', 0),
        'rounds_completed': result.get('rounds_completed', 0),
    }


def run_pegasis(params: Dict) -> Dict:
    import random
    import numpy as np
    from benchmark_protocols import NetworkConfig, PEGASISProtocol
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

    random.seed(params['seed'])
    np.random.seed(params['seed'])

    cfg = NetworkConfig(**params['config'])
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    proto = PEGASISProtocol(cfg, em)
    result = proto.run_simulation(max_rounds=params['max_rounds'])

    return {
        'protocol': 'PEGASIS',
        'seed': params['seed'],
        'scenario': params['scenario'],
        'num_nodes': params['config']['num_nodes'],
        'pdr_end2end': result.get('packet_delivery_ratio_end2end', result.get('packet_delivery_ratio', 0)),
        'total_energy': result.get('total_energy_consumed', 0),
        'rounds_completed': result.get('rounds_completed', 0),
    }


def run_heed(params: Dict) -> Dict:
    import random
    import numpy as np
    from benchmark_protocols import NetworkConfig, HEEDProtocolWrapper
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

    random.seed(params['seed'])
    np.random.seed(params['seed'])

    cfg = NetworkConfig(**params['config'])
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    proto = HEEDProtocolWrapper(cfg, em)
    result = proto.run_simulation(max_rounds=params['max_rounds'])

    return {
        'protocol': 'HEED',
        'seed': params['seed'],
        'scenario': params['scenario'],
        'num_nodes': params['config']['num_nodes'],
        'pdr_end2end': result.get('packet_delivery_ratio_end2end', result.get('packet_delivery_ratio', 0)),
        'total_energy': result.get('total_energy_consumed', 0),
        'rounds_completed': result.get('rounds_completed', 0),
    }


def run_teen(params: Dict) -> Dict:
    import random
    import numpy as np
    from benchmark_protocols import NetworkConfig, TEENProtocolWrapper
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

    random.seed(params['seed'])
    np.random.seed(params['seed'])

    cfg = NetworkConfig(**params['config'])
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    proto = TEENProtocolWrapper(cfg, em)
    result = proto.run_simulation(max_rounds=params['max_rounds'])

    return {
        'protocol': 'TEEN',
        'seed': params['seed'],
        'scenario': params['scenario'],
        'num_nodes': params['config']['num_nodes'],
        'pdr_end2end': result.get('packet_delivery_ratio_end2end', result.get('packet_delivery_ratio', 0)),
        'total_energy': result.get('total_energy_consumed', 0),
        'rounds_completed': result.get('rounds_completed', 0),
    }


PROTOCOL_RUNNERS = {
    'AERIS': run_aeris,
    'LEACH': run_leach,
    'PEGASIS': run_pegasis,
    'HEED': run_heed,
    'TEEN': run_teen,
}


def run_single_experiment(task: Dict) -> Dict:
    protocol = task['protocol']
    runner = PROTOCOL_RUNNERS.get(protocol)
    if runner is None:
        return {'error': f'Unknown protocol: {protocol}'}
    try:
        return runner(task)
    except Exception as e:
        return {
            'protocol': protocol,
            'seed': task.get('seed'),
            'scenario': task.get('scenario'),
            'error': str(e),
        }


def generate_tasks() -> List[Dict]:
    tasks = []
    scenarios = {
        'uniform': {'area_width': 200, 'area_height': 200},
        'corridor': {'area_width': 400, 'area_height': 100},
    }
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED', 'TEEN']
    node_counts = [100, 200]
    seeds = range(1, 31)  # 30 seeds
    max_rounds = 200

    for scenario, area in scenarios.items():
        for num_nodes in node_counts:
            for protocol in protocols:
                for seed in seeds:
                    tasks.append({
                        'protocol': protocol,
                        'seed': seed,
                        'scenario': scenario,
                        'max_rounds': max_rounds,
                        'config': {
                            'num_nodes': num_nodes,
                            'area_width': area['area_width'],
                            'area_height': area['area_height'],
                            'initial_energy': 2.0,
                            'packet_size': 512,
                            'enable_channel': True,
                            'channel_env': 'indoor_office',
                            'tx_power_dbm': 0.0,
                            'link_retx': 1,
                            'link_retx_power_step': 1.0,
                        }
                    })
    return tasks


def main():
    print("=" * 60)
    print("AERIS vs Baselines Comprehensive Comparison")
    print(f"Timestamp: {TIMESTAMP}")
    print(f"Workers: {MAX_WORKERS}")
    print("=" * 60)

    os.makedirs(OUT_DIR, exist_ok=True)
    tasks = generate_tasks()
    print(f"Total tasks: {len(tasks)}")

    results = []
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_single_experiment, t): t for t in tasks}
        for i, future in enumerate(as_completed(futures)):
            try:
                res = future.result()
                results.append(res)
                if (i + 1) % 50 == 0:
                    elapsed = time.time() - start_time
                    print(f"Progress: {i+1}/{len(tasks)}, Elapsed: {elapsed:.1f}s")
            except Exception as e:
                print(f"Error: {e}")

    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed/60:.1f} minutes")

    # Save results
    out_path = os.path.join(OUT_DIR, 'comparison_results.json')
    with open(out_path, 'w') as f:
        json.dump({
            'timestamp': TIMESTAMP,
            'environment': get_environment_info(),
            'elapsed_seconds': elapsed,
            'results': results,
        }, f, indent=2)
    print(f"Results saved: {out_path}")

    # Generate summary
    generate_summary(results)


def generate_summary(results: List[Dict]):
    import numpy as np

    summary = {}
    for r in results:
        if 'error' in r:
            continue
        key = (r['protocol'], r['scenario'], r['num_nodes'])
        if key not in summary:
            summary[key] = {'pdr': [], 'energy': []}
        summary[key]['pdr'].append(r.get('pdr_end2end', 0))
        summary[key]['energy'].append(r.get('total_energy', 0))

    print("\n" + "=" * 70)
    print("Summary (PDR mean +/- std)")
    print("=" * 70)
    print(f"{'Protocol':<10} {'Scenario':<10} {'Nodes':<6} {'PDR%':<15} {'Energy(J)':<15}")
    print("-" * 70)

    for (proto, scenario, nodes), data in sorted(summary.items()):
        pdr_mean = np.mean(data['pdr']) * 100
        pdr_std = np.std(data['pdr']) * 100
        e_mean = np.mean(data['energy'])
        print(f"{proto:<10} {scenario:<10} {nodes:<6} {pdr_mean:5.1f} +/- {pdr_std:4.1f}  {e_mean:10.2f}")

    # Save summary
    summary_data = {}
    for (proto, scenario, nodes), data in summary.items():
        key = f"{proto}_{scenario}_{nodes}"
        summary_data[key] = {
            'pdr_mean': float(np.mean(data['pdr'])),
            'pdr_std': float(np.std(data['pdr'])),
            'energy_mean': float(np.mean(data['energy'])),
            'n_runs': len(data['pdr']),
        }

    out_path = os.path.join(OUT_DIR, 'summary.json')
    with open(out_path, 'w') as f:
        json.dump(summary_data, f, indent=2)
    print(f"\nSummary saved: {out_path}")


if __name__ == '__main__':
    mp.freeze_support()
    main()
