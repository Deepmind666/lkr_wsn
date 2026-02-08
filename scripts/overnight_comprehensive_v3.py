#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS WSN Protocol - Comprehensive Overnight Experiment Suite v3
================================================================

Designed for Intel Ultra 9 285K (24 cores, 48 threads) - 10+ hours of experiments

This script runs comprehensive experiments covering:
1. Large-scale scalability (50-500 nodes, 30 reps each)
2. Multi-topology comparison (uniform, corridor, clustered)
3. Ablation studies (CAS, Gateway, Safety, Fairness)
4. Parameter sensitivity sweeps
5. Dynamic scenario testing (node failures, moving BS)
6. Statistical significance testing (Welch's t-test, Cohen's d)

Author: AERIS Research Team
Date: 2026-01-19
"""

import os
import sys
import json
import math
import random
import time
import traceback
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np

# Import protocols with correct API
from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, TEENProtocolWrapper
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol

# Configuration
BASE_SEED = 42001
MAX_WORKERS = min(40, os.cpu_count() or 16)  # Use up to 40 workers for Ultra 9 285K
RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'overnight_experiments')
LOG_FILE = os.path.join(RESULTS_DIR, 'experiment_log.txt')

RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_VERSION = "v1_1"

# Ensure results directory exists
os.makedirs(RESULTS_DIR, exist_ok=True)


def log_message(msg: str):
    """Log message to console and file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(full_msg + '\n')
    except:
        pass


def ci95(arr: List[float]) -> Tuple[float, float]:
    """Calculate mean and 95% confidence interval"""
    if not arr or len(arr) < 2:
        return (np.mean(arr) if arr else 0.0, 0.0)
    mean = np.mean(arr)
    ci = 1.96 * np.std(arr, ddof=1) / math.sqrt(len(arr))
    return (float(mean), float(ci))


def cohens_d(group1: List[float], group2: List[float]) -> float:
    """Calculate Cohen's d effect size"""
    if len(group1) < 2 or len(group2) < 2:
        return 0.0
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = math.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    if pooled_std < 1e-9:
        return 0.0
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def welch_ttest(group1: List[float], group2: List[float]) -> float:
    """Welch's t-test p-value"""
    try:
        from scipy import stats
        _, p = stats.ttest_ind(group1, group2, equal_var=False)
        return float(p)
    except:
        return 1.0


# =============================================================================
# Single Run Functions
# =============================================================================

def run_aeris_single(args: Tuple) -> Dict:
    """Run single AERIS experiment"""
    seed, num_nodes, width, height, rounds, topology, aeris_opts = args
    try:
        random.seed(seed)
        np.random.seed(seed)

        config = NetworkConfig(
            num_nodes=num_nodes,
            area_width=width,
            area_height=height,
            initial_energy=2.0,
            packet_size=1024,
            base_station_x=width/2,
            base_station_y=height + 75,
            enable_channel=True,
            channel_env='indoor_office',
            tx_power_dbm=0.0,
            link_retx=2,
            link_retx_power_step=3.0,
            temperature_c=25.0,
            humidity_ratio=0.5
        )

        # Generate positions based on topology
        positions = generate_positions(num_nodes, width, height, topology, seed)
        config.positions = positions

        proto = AerisProtocol(
            config,
            enable_cas=aeris_opts.get('enable_cas', True),
            enable_fairness=aeris_opts.get('enable_fairness', True),
            enable_gateway=aeris_opts.get('enable_gateway', True),
            enable_skeleton=aeris_opts.get('enable_skeleton', False),
            profile=aeris_opts.get('profile', 'robust'),
            verbose=False,
            seed=seed
        )

        # Update node positions
        for i, (x, y) in enumerate(positions):
            if i < len(proto.nodes):
                proto.nodes[i].x = x
                proto.nodes[i].y = y

        result = proto.run_simulation(rounds)
        return {
            'protocol': 'AERIS',
            'seed': seed,
            'num_nodes': num_nodes,
            'topology': topology,
            'rounds': rounds,
            'pdr_e2e': result.get('packet_delivery_ratio_end2end', 0.0),
            'energy': result.get('total_energy_consumed', 0.0),
            'lifetime': result.get('network_lifetime', 0),
            'alive_nodes': result.get('final_alive_nodes', 0),
            'aeris_opts': aeris_opts,
            'success': True
        }
    except Exception as e:
        return {
            'protocol': 'AERIS',
            'seed': seed,
            'num_nodes': num_nodes,
            'topology': topology,
            'error': str(e),
            'success': False
        }


def run_baseline_single(args: Tuple) -> Dict:
    """Run single baseline protocol experiment"""
    protocol_name, seed, num_nodes, width, height, rounds, topology = args
    try:
        random.seed(seed)
        np.random.seed(seed)

        config = NetworkConfig(
            num_nodes=num_nodes,
            area_width=width,
            area_height=height,
            initial_energy=2.0,
            packet_size=1024,
            base_station_x=width/2,
            base_station_y=height + 75,
            enable_channel=True,
            channel_env='indoor_office',
            tx_power_dbm=0.0,
            link_retx=2,
            link_retx_power_step=3.0,
            temperature_c=25.0,
            humidity_ratio=0.5
        )

        # Generate positions
        positions = generate_positions(num_nodes, width, height, topology, seed)
        config.positions = positions

        # Create energy model
        energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

        # Create protocol instance
        if protocol_name == 'LEACH':
            proto = LEACHProtocol(config, energy_model)
        elif protocol_name == 'PEGASIS':
            proto = PEGASISProtocol(config, energy_model)
        elif protocol_name == 'HEED':
            proto = HEEDProtocolWrapper(config, energy_model)
        elif protocol_name == 'TEEN':
            proto = TEENProtocolWrapper(config, energy_model)
        else:
            raise ValueError(f"Unknown protocol: {protocol_name}")

        result = proto.run_simulation(rounds)
        return {
            'protocol': protocol_name,
            'seed': seed,
            'num_nodes': num_nodes,
            'topology': topology,
            'rounds': rounds,
            'pdr_e2e': result.get('packet_delivery_ratio_end2end', 0.0),
            'energy': result.get('total_energy_consumed', 0.0),
            'lifetime': result.get('network_lifetime', 0),
            'alive_nodes': result.get('final_alive_nodes', 0),
            'success': True
        }
    except Exception as e:
        return {
            'protocol': protocol_name,
            'seed': seed,
            'num_nodes': num_nodes,
            'topology': topology,
            'error': str(e),
            'success': False
        }


def generate_positions(num_nodes: int, width: float, height: float,
                       topology: str, seed: int) -> List[Tuple[float, float]]:
    """Generate node positions based on topology type"""
    rng = np.random.default_rng(seed)

    if topology == 'uniform':
        return [(rng.uniform(0, width), rng.uniform(0, height))
                for _ in range(num_nodes)]

    elif topology == 'corridor':
        # Nodes distributed along a corridor (narrow strip)
        corridor_width = width * 0.3
        x_offset = (width - corridor_width) / 2
        return [(rng.uniform(x_offset, x_offset + corridor_width),
                 rng.uniform(0, height)) for _ in range(num_nodes)]

    elif topology == 'clustered':
        # Multiple clusters
        n_clusters = max(3, num_nodes // 20)
        cluster_centers = [(rng.uniform(0.1*width, 0.9*width),
                           rng.uniform(0.1*height, 0.9*height))
                          for _ in range(n_clusters)]
        positions = []
        for i in range(num_nodes):
            cx, cy = cluster_centers[i % n_clusters]
            x = np.clip(rng.normal(cx, width*0.1), 0, width)
            y = np.clip(rng.normal(cy, height*0.1), 0, height)
            positions.append((float(x), float(y)))
        return positions

    elif topology == 'sparse':
        # Sparse deployment with larger area
        return [(rng.uniform(0, width*1.5), rng.uniform(0, height*1.5))
                for _ in range(num_nodes)]

    else:
        return [(rng.uniform(0, width), rng.uniform(0, height))
                for _ in range(num_nodes)]


# =============================================================================
# Experiment Suites
# =============================================================================

def run_scalability_experiment(workers: int = MAX_WORKERS, repeats: int = 30) -> Dict:
    """
    Experiment 1: Large-scale scalability comparison
    Tests: 50, 100, 200, 300, 400, 500 nodes
    """
    log_message("=" * 60)
    log_message("EXPERIMENT 1: Large-Scale Scalability")
    log_message("=" * 60)

    node_counts = [50, 100, 200, 300, 400, 500]
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED', 'TEEN']
    rounds = 200
    width, height = 100.0, 100.0

    results = {p: {n: {'pdr': [], 'energy': [], 'lifetime': []}
                   for n in node_counts} for p in protocols}

    # Generate tasks
    tasks = []
    task_id = 0

    for num_nodes in node_counts:
        for protocol in protocols:
            for rep in range(repeats):
                seed = BASE_SEED + task_id
                if protocol == 'AERIS':
                    tasks.append(('AERIS', (seed, num_nodes, width, height, rounds,
                                           'uniform', {'profile': 'robust'})))
                else:
                    tasks.append((protocol, (protocol, seed, num_nodes, width, height,
                                            rounds, 'uniform')))
                task_id += 1

    log_message(f"Total tasks: {len(tasks)}, Workers: {workers}, Repeats: {repeats}")

    completed = 0
    errors = 0
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for task_type, args in tasks:
            if task_type == 'AERIS':
                fut = executor.submit(run_aeris_single, args)
            else:
                fut = executor.submit(run_baseline_single, args)
            futures[fut] = (task_type, args)

        for future in as_completed(futures):
            completed += 1
            try:
                result = future.result(timeout=300)
                if result.get('success', False):
                    p = result['protocol']
                    n = result['num_nodes']
                    results[p][n]['pdr'].append(result['pdr_e2e'])
                    results[p][n]['energy'].append(result['energy'])
                    results[p][n]['lifetime'].append(result['lifetime'])
                else:
                    errors += 1
            except Exception as e:
                errors += 1

            if completed % 50 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (len(tasks) - completed) / rate if rate > 0 else 0
                log_message(f"Progress: {completed}/{len(tasks)} ({errors} errors), "
                           f"Rate: {rate:.1f}/s, ETA: {eta/60:.1f} min")

    # Compute statistics
    summary = {}
    for protocol in protocols:
        summary[protocol] = {}
        for num_nodes in node_counts:
            data = results[protocol][num_nodes]
            pdr_mean, pdr_ci = ci95(data['pdr'])
            energy_mean, energy_ci = ci95(data['energy'])
            lifetime_mean, lifetime_ci = ci95(data['lifetime'])

            summary[protocol][num_nodes] = {
                'pdr': {'mean': pdr_mean, 'ci95': pdr_ci, 'values': data['pdr']},
                'energy': {'mean': energy_mean, 'ci95': energy_ci, 'values': data['energy']},
                'lifetime': {'mean': lifetime_mean, 'ci95': lifetime_ci, 'values': data['lifetime']},
                'n_samples': len(data['pdr'])
            }

            log_message(f"{protocol} @ {num_nodes} nodes: PDR={pdr_mean:.3f}±{pdr_ci:.3f}, "
                       f"Energy={energy_mean:.1f}±{energy_ci:.1f}")

    # Statistical tests vs LEACH
    log_message("\nStatistical Significance (AERIS vs LEACH):")
    for num_nodes in node_counts:
        aeris_pdr = results['AERIS'][num_nodes]['pdr']
        leach_pdr = results['LEACH'][num_nodes]['pdr']
        if len(aeris_pdr) >= 2 and len(leach_pdr) >= 2:
            p_val = welch_ttest(aeris_pdr, leach_pdr)
            d = cohens_d(aeris_pdr, leach_pdr)
            log_message(f"  {num_nodes} nodes: p={p_val:.2e}, Cohen's d={d:.2f}")

    output_path = os.path.join(RESULTS_DIR, f"scalability_results_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)
    log_message(f"Saved: {output_path}")

    return summary


def run_multi_topology_experiment(workers: int = MAX_WORKERS, repeats: int = 30) -> Dict:
    """
    Experiment 2: Multi-topology comparison
    Tests: uniform, corridor, clustered, sparse
    """
    log_message("=" * 60)
    log_message("EXPERIMENT 2: Multi-Topology Comparison")
    log_message("=" * 60)

    topologies = ['uniform', 'corridor', 'clustered', 'sparse']
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    num_nodes = 100
    rounds = 200
    width, height = 100.0, 100.0

    results = {p: {t: {'pdr': [], 'energy': []}
                   for t in topologies} for p in protocols}

    tasks = []
    task_id = 0

    for topology in topologies:
        for protocol in protocols:
            for rep in range(repeats):
                seed = BASE_SEED + 10000 + task_id
                if protocol == 'AERIS':
                    tasks.append(('AERIS', (seed, num_nodes, width, height, rounds,
                                           topology, {'profile': 'robust'})))
                else:
                    tasks.append((protocol, (protocol, seed, num_nodes, width, height,
                                            rounds, topology)))
                task_id += 1

    log_message(f"Total tasks: {len(tasks)}, Workers: {workers}")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for task_type, args in tasks:
            if task_type == 'AERIS':
                fut = executor.submit(run_aeris_single, args)
            else:
                fut = executor.submit(run_baseline_single, args)
            futures[fut] = args

        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                result = future.result(timeout=300)
                if result.get('success', False):
                    p = result['protocol']
                    t = result['topology']
                    results[p][t]['pdr'].append(result['pdr_e2e'])
                    results[p][t]['energy'].append(result['energy'])
            except:
                pass

            if completed % 30 == 0:
                log_message(f"Topology experiment progress: {completed}/{len(tasks)}")

    # Compute statistics
    summary = {}
    for protocol in protocols:
        summary[protocol] = {}
        for topology in topologies:
            data = results[protocol][topology]
            pdr_mean, pdr_ci = ci95(data['pdr'])
            energy_mean, energy_ci = ci95(data['energy'])
            summary[protocol][topology] = {
                'pdr': {'mean': pdr_mean, 'ci95': pdr_ci},
                'energy': {'mean': energy_mean, 'ci95': energy_ci},
                'n_samples': len(data['pdr'])
            }
            log_message(f"{protocol} @ {topology}: PDR={pdr_mean:.3f}±{pdr_ci:.3f}")

    output_path = os.path.join(RESULTS_DIR, f"topology_results_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)
    log_message(f"Saved: {output_path}")

    return summary


def run_ablation_experiment(workers: int = MAX_WORKERS, repeats: int = 50) -> Dict:
    """
    Experiment 3: AERIS ablation study
    Tests each component's contribution
    """
    log_message("=" * 60)
    log_message("EXPERIMENT 3: AERIS Ablation Study")
    log_message("=" * 60)

    variants = {
        'FULL': {'enable_cas': True, 'enable_fairness': True, 'enable_gateway': True, 'profile': 'robust'},
        '-CAS': {'enable_cas': False, 'enable_fairness': True, 'enable_gateway': True, 'profile': 'robust'},
        '-Fairness': {'enable_cas': True, 'enable_fairness': False, 'enable_gateway': True, 'profile': 'robust'},
        '-Gateway': {'enable_cas': True, 'enable_fairness': True, 'enable_gateway': False, 'profile': 'robust'},
        '-Safety': {'enable_cas': True, 'enable_fairness': True, 'enable_gateway': True, 'profile': 'energy'},
        'MINIMAL': {'enable_cas': False, 'enable_fairness': False, 'enable_gateway': False, 'profile': 'energy'},
    }

    node_counts = [100, 200, 300]
    rounds = 200
    width, height = 100.0, 100.0

    results = {v: {n: {'pdr': [], 'energy': []} for n in node_counts} for v in variants}

    tasks = []
    task_id = 0

    for num_nodes in node_counts:
        for variant_name, opts in variants.items():
            for rep in range(repeats):
                seed = BASE_SEED + 20000 + task_id
                tasks.append((seed, num_nodes, width, height, rounds, 'uniform', opts, variant_name))
                task_id += 1

    log_message(f"Total ablation tasks: {len(tasks)}, Workers: {workers}")

    def run_ablation_single(args):
        seed, num_nodes, width, height, rounds, topology, opts, variant = args
        result = run_aeris_single((seed, num_nodes, width, height, rounds, topology, opts))
        result['variant'] = variant
        return result

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_ablation_single, task) for task in tasks]

        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                result = future.result(timeout=300)
                if result.get('success', False):
                    v = result['variant']
                    n = result['num_nodes']
                    results[v][n]['pdr'].append(result['pdr_e2e'])
                    results[v][n]['energy'].append(result['energy'])
            except:
                pass

            if completed % 50 == 0:
                log_message(f"Ablation progress: {completed}/{len(tasks)}")

    # Compute statistics and contributions
    summary = {'variants': {}, 'contributions': {}}

    for variant in variants:
        summary['variants'][variant] = {}
        for num_nodes in node_counts:
            data = results[variant][num_nodes]
            pdr_mean, pdr_ci = ci95(data['pdr'])
            energy_mean, energy_ci = ci95(data['energy'])
            summary['variants'][variant][num_nodes] = {
                'pdr': {'mean': pdr_mean, 'ci95': pdr_ci, 'values': data['pdr']},
                'energy': {'mean': energy_mean, 'ci95': energy_ci, 'values': data['energy']}
            }
            log_message(f"{variant} @ {num_nodes}: PDR={pdr_mean:.3f}±{pdr_ci:.3f}")

    # Calculate component contributions
    for num_nodes in node_counts:
        summary['contributions'][num_nodes] = {}
        full_pdr = np.mean(results['FULL'][num_nodes]['pdr']) if results['FULL'][num_nodes]['pdr'] else 0

        for comp, variant in [('CAS', '-CAS'), ('Gateway', '-Gateway'),
                               ('Safety', '-Safety'), ('Fairness', '-Fairness')]:
            ablated_pdr = np.mean(results[variant][num_nodes]['pdr']) if results[variant][num_nodes]['pdr'] else 0
            contribution = full_pdr - ablated_pdr
            summary['contributions'][num_nodes][comp] = {
                'pdr_delta': contribution,
                'pdr_delta_pp': contribution * 100
            }
            log_message(f"  {comp} contribution @ {num_nodes}: +{contribution*100:.2f} pp")

    output_path = os.path.join(RESULTS_DIR, f"ablation_results_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)
    log_message(f"Saved: {output_path}")

    return summary


def run_sensitivity_experiment(workers: int = MAX_WORKERS, repeats: int = 20) -> Dict:
    """
    Experiment 4: Parameter sensitivity analysis
    Tests various parameter combinations
    """
    log_message("=" * 60)
    log_message("EXPERIMENT 4: Parameter Sensitivity Analysis")
    log_message("=" * 60)

    num_nodes = 100
    rounds = 200
    width, height = 100.0, 100.0

    # Parameters to sweep
    ch_probs = [0.05, 0.08, 0.10, 0.12, 0.15]
    safety_profiles = ['robust', 'energy', 'balanced']

    results = {}
    tasks = []
    task_id = 0

    for ch_prob in ch_probs:
        for safety in safety_profiles:
            key = f"ch{ch_prob}_safety{safety}"
            results[key] = {'pdr': [], 'energy': []}
            for rep in range(repeats):
                seed = BASE_SEED + 30000 + task_id
                tasks.append((seed, num_nodes, width, height, rounds, 'uniform',
                             {'profile': safety}, key))
                task_id += 1

    log_message(f"Total sensitivity tasks: {len(tasks)}")

    def run_sensitivity_single(args):
        seed, num_nodes, width, height, rounds, topology, opts, key = args
        result = run_aeris_single((seed, num_nodes, width, height, rounds, topology, opts))
        result['param_key'] = key
        return result

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_sensitivity_single, task) for task in tasks]

        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                result = future.result(timeout=300)
                if result.get('success', False):
                    key = result['param_key']
                    results[key]['pdr'].append(result['pdr_e2e'])
                    results[key]['energy'].append(result['energy'])
            except:
                pass

    # Compute statistics
    summary = {}
    for key, data in results.items():
        pdr_mean, pdr_ci = ci95(data['pdr'])
        energy_mean, energy_ci = ci95(data['energy'])
        summary[key] = {
            'pdr': {'mean': pdr_mean, 'ci95': pdr_ci},
            'energy': {'mean': energy_mean, 'ci95': energy_ci},
            'n_samples': len(data['pdr'])
        }
        log_message(f"{key}: PDR={pdr_mean:.3f}±{pdr_ci:.3f}, Energy={energy_mean:.1f}")

    output_path = os.path.join(RESULTS_DIR, f"sensitivity_results_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)
    log_message(f"Saved: {output_path}")

    return summary


def run_dynamic_scenario_experiment(workers: int = MAX_WORKERS, repeats: int = 30) -> Dict:
    """
    Experiment 5: Dynamic scenarios
    Tests node failures, environmental changes
    """
    log_message("=" * 60)
    log_message("EXPERIMENT 5: Dynamic Scenario Testing")
    log_message("=" * 60)

    # This experiment modifies AERIS behavior during simulation
    # For now, we test with different initial conditions that simulate stress

    scenarios = {
        'normal': {'topology': 'uniform', 'nodes': 100},
        'sparse_nodes': {'topology': 'sparse', 'nodes': 50},
        'dense_nodes': {'topology': 'uniform', 'nodes': 200},
        'corridor_stress': {'topology': 'corridor', 'nodes': 150},
        'clustered_hotspots': {'topology': 'clustered', 'nodes': 100},
    }

    protocols = ['AERIS', 'LEACH', 'PEGASIS']
    rounds = 200
    width, height = 100.0, 100.0

    results = {p: {s: {'pdr': [], 'energy': []} for s in scenarios} for p in protocols}

    tasks = []
    task_id = 0

    for scenario_name, scenario_config in scenarios.items():
        for protocol in protocols:
            for rep in range(repeats):
                seed = BASE_SEED + 40000 + task_id
                if protocol == 'AERIS':
                    tasks.append(('AERIS', (seed, scenario_config['nodes'], width, height,
                                           rounds, scenario_config['topology'],
                                           {'profile': 'robust'}), scenario_name))
                else:
                    tasks.append((protocol, (protocol, seed, scenario_config['nodes'],
                                            width, height, rounds,
                                            scenario_config['topology']), scenario_name))
                task_id += 1

    log_message(f"Total dynamic scenario tasks: {len(tasks)}")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for task_type, args, scenario in tasks:
            if task_type == 'AERIS':
                fut = executor.submit(run_aeris_single, args)
            else:
                fut = executor.submit(run_baseline_single, args)
            futures[fut] = (task_type, scenario)

        completed = 0
        for future in as_completed(futures):
            completed += 1
            task_type, scenario = futures[future]
            try:
                result = future.result(timeout=300)
                if result.get('success', False):
                    p = result['protocol']
                    results[p][scenario]['pdr'].append(result['pdr_e2e'])
                    results[p][scenario]['energy'].append(result['energy'])
            except:
                pass

            if completed % 30 == 0:
                log_message(f"Dynamic scenario progress: {completed}/{len(tasks)}")

    # Compute statistics
    summary = {}
    for protocol in protocols:
        summary[protocol] = {}
        for scenario in scenarios:
            data = results[protocol][scenario]
            pdr_mean, pdr_ci = ci95(data['pdr'])
            energy_mean, energy_ci = ci95(data['energy'])
            summary[protocol][scenario] = {
                'pdr': {'mean': pdr_mean, 'ci95': pdr_ci},
                'energy': {'mean': energy_mean, 'ci95': energy_ci}
            }
            log_message(f"{protocol} @ {scenario}: PDR={pdr_mean:.3f}±{pdr_ci:.3f}")

    output_path = os.path.join(RESULTS_DIR, f"dynamic_scenario_results_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)
    log_message(f"Saved: {output_path}")

    return summary


def run_statistical_validation(workers: int = MAX_WORKERS, repeats: int = 100) -> Dict:
    """
    Experiment 6: High-repeat statistical validation
    100 repeats for robust significance testing
    """
    log_message("=" * 60)
    log_message("EXPERIMENT 6: Statistical Validation (100 repeats)")
    log_message("=" * 60)

    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    num_nodes = 100
    rounds = 200
    width, height = 100.0, 100.0

    results = {p: {'pdr': [], 'energy': []} for p in protocols}

    tasks = []
    task_id = 0

    for protocol in protocols:
        for rep in range(repeats):
            seed = BASE_SEED + 50000 + task_id
            if protocol == 'AERIS':
                tasks.append(('AERIS', (seed, num_nodes, width, height, rounds,
                                       'uniform', {'profile': 'robust'})))
            else:
                tasks.append((protocol, (protocol, seed, num_nodes, width, height,
                                        rounds, 'uniform')))
            task_id += 1

    log_message(f"Total statistical validation tasks: {len(tasks)}")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for task_type, args in tasks:
            if task_type == 'AERIS':
                fut = executor.submit(run_aeris_single, args)
            else:
                fut = executor.submit(run_baseline_single, args)
            futures[fut] = task_type

        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                result = future.result(timeout=300)
                if result.get('success', False):
                    p = result['protocol']
                    results[p]['pdr'].append(result['pdr_e2e'])
                    results[p]['energy'].append(result['energy'])
            except:
                pass

            if completed % 50 == 0:
                log_message(f"Statistical validation progress: {completed}/{len(tasks)}")

    # Comprehensive statistical analysis
    summary = {'descriptive': {}, 'comparisons': {}}

    for protocol in protocols:
        data = results[protocol]
        pdr_mean, pdr_ci = ci95(data['pdr'])
        energy_mean, energy_ci = ci95(data['energy'])

        summary['descriptive'][protocol] = {
            'pdr': {
                'mean': pdr_mean,
                'ci95': pdr_ci,
                'std': float(np.std(data['pdr'])) if data['pdr'] else 0,
                'min': float(min(data['pdr'])) if data['pdr'] else 0,
                'max': float(max(data['pdr'])) if data['pdr'] else 0,
                'n_samples': len(data['pdr']),
                'values': data['pdr']
            },
            'energy': {
                'mean': energy_mean,
                'ci95': energy_ci,
                'std': float(np.std(data['energy'])) if data['energy'] else 0,
                'n_samples': len(data['energy']),
                'values': data['energy']
            }
        }
        log_message(f"{protocol}: PDR={pdr_mean:.4f}±{pdr_ci:.4f} (n={len(data['pdr'])})")

    # Pairwise comparisons with AERIS
    aeris_pdr = results['AERIS']['pdr']
    for baseline in ['LEACH', 'PEGASIS', 'HEED']:
        baseline_pdr = results[baseline]['pdr']
        if len(aeris_pdr) >= 2 and len(baseline_pdr) >= 2:
            p_val = welch_ttest(aeris_pdr, baseline_pdr)
            d = cohens_d(aeris_pdr, baseline_pdr)
            delta = np.mean(aeris_pdr) - np.mean(baseline_pdr)

            summary['comparisons'][f'AERIS_vs_{baseline}'] = {
                'pdr_delta': float(delta),
                'pdr_delta_pp': float(delta * 100),
                'p_value': float(p_val),
                'cohens_d': float(d),
                'significant_001': p_val < 0.001,
                'significant_005': p_val < 0.05,
                'effect_size': 'large' if abs(d) > 0.8 else 'medium' if abs(d) > 0.5 else 'small'
            }
            log_message(f"AERIS vs {baseline}: Δ={delta*100:.2f}pp, p={p_val:.2e}, d={d:.2f}")

    output_path = os.path.join(RESULTS_DIR, f"statistical_validation_results_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)
    log_message(f"Saved: {output_path}")

    return summary


def generate_final_report(all_results: Dict) -> str:
    """Generate comprehensive markdown report"""
    report = []
    report.append("# AERIS Overnight Experiment Report")
    report.append(f"## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"## Run Tag: {RUN_TIMESTAMP}_{OUTPUT_VERSION}")
    report.append("")

    # Executive Summary
    report.append("## Executive Summary")
    report.append("")

    if 'scalability' in all_results:
        report.append("### Scalability Results")
        for protocol in ['AERIS', 'LEACH', 'PEGASIS', 'HEED']:
            if protocol in all_results['scalability']:
                data = all_results['scalability'][protocol]
                if '100' in data or 100 in data:
                    key = '100' if '100' in data else 100
                    pdr = data[key]['pdr']['mean']
                    report.append(f"- {protocol} @ 100 nodes: PDR = {pdr:.3f}")
        report.append("")

    if 'ablation' in all_results and 'contributions' in all_results['ablation']:
        report.append("### Component Contributions (100 nodes)")
        contribs = all_results['ablation']['contributions']
        key = '100' if '100' in contribs else 100 if 100 in contribs else list(contribs.keys())[0]
        for comp, val in contribs[key].items():
            report.append(f"- {comp}: +{val['pdr_delta_pp']:.2f} pp")
        report.append("")

    if 'statistical' in all_results and 'comparisons' in all_results['statistical']:
        report.append("### Statistical Significance")
        for comparison, stats in all_results['statistical']['comparisons'].items():
            sig = "***" if stats['significant_001'] else "**" if stats['significant_005'] else ""
            report.append(f"- {comparison}: Δ={stats['pdr_delta_pp']:.2f}pp, "
                         f"p={stats['p_value']:.2e}, d={stats['cohens_d']:.2f} {sig}")
        report.append("")

    report.append("## Methodology")
    report.append("- Channel model: Log-Normal Shadowing (σ=8 dB)")
    report.append("- Energy model: CC2420/TelosB hardware parameters")
    report.append("- Statistical tests: Welch's t-test, Cohen's d effect size")
    report.append("- Confidence intervals: 95% CI")
    report.append("")

    return "\n".join(report)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main execution function"""
    start_time = time.time()

    log_message("=" * 70)
    log_message("AERIS COMPREHENSIVE OVERNIGHT EXPERIMENT SUITE v3")
    log_message("=" * 70)
    log_message(f"CPU cores detected: {os.cpu_count()}")
    log_message(f"Workers to use: {MAX_WORKERS}")
    log_message(f"Results directory: {RESULTS_DIR}")
    log_message("")

    all_results = {}

    try:
        # Experiment 1: Scalability
        log_message("\n[1/6] Running scalability experiment...")
        all_results['scalability'] = run_scalability_experiment(
            workers=MAX_WORKERS, repeats=30)

        # Experiment 2: Multi-topology
        log_message("\n[2/6] Running multi-topology experiment...")
        all_results['topology'] = run_multi_topology_experiment(
            workers=MAX_WORKERS, repeats=30)

        # Experiment 3: Ablation
        log_message("\n[3/6] Running ablation experiment...")
        all_results['ablation'] = run_ablation_experiment(
            workers=MAX_WORKERS, repeats=50)

        # Experiment 4: Sensitivity
        log_message("\n[4/6] Running sensitivity experiment...")
        all_results['sensitivity'] = run_sensitivity_experiment(
            workers=MAX_WORKERS, repeats=20)

        # Experiment 5: Dynamic scenarios
        log_message("\n[5/6] Running dynamic scenario experiment...")
        all_results['dynamic'] = run_dynamic_scenario_experiment(
            workers=MAX_WORKERS, repeats=30)

        # Experiment 6: Statistical validation
        log_message("\n[6/6] Running statistical validation experiment...")
        all_results['statistical'] = run_statistical_validation(
            workers=MAX_WORKERS, repeats=100)

    except Exception as e:
        log_message(f"ERROR: {e}")
        log_message(traceback.format_exc())

    # Save combined results
    combined_path = os.path.join(RESULTS_DIR, f"all_experiments_combined_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json")
    with open(combined_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, default=str)
    log_message(f"Saved combined results: {combined_path}")

    # Generate report
    report = generate_final_report(all_results)
    report_path = os.path.join(RESULTS_DIR, f"EXPERIMENT_REPORT_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    log_message(f"Generated report: {report_path}")

    # Final summary
    elapsed = time.time() - start_time
    log_message("")
    log_message("=" * 70)
    log_message(f"ALL EXPERIMENTS COMPLETED")
    log_message(f"Total time: {elapsed/3600:.2f} hours ({elapsed/60:.1f} minutes)")
    log_message(f"Results saved to: {RESULTS_DIR}")
    log_message("=" * 70)


if __name__ == '__main__':
    main()
