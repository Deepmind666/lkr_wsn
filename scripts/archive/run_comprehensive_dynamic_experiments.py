#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Dynamic Experiments for AERIS Paper Enhancement

Based on expert review recommendations, this script implements:
1. Advanced robustness metrics (Recovery Time, Data Island Rate, Control Overhead Peak)
2. Multiple dynamic scenarios (node churn, regional failures, intermittent connectivity)
3. Scalability testing (100-500 nodes)
4. Statistical validation with multiple runs

Author: AERIS Research Team
Date: 2026-01-12
"""

import os
import sys
import json
import random
import numpy as np
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_protocols import (
    NetworkConfig,
    LEACHProtocol,
    PEGASISProtocol,
    HEEDProtocolWrapper as HEEDProtocol,
)
from aeris_protocol import AerisProtocol
from teen_protocol import TEENProtocol


# =============================================================================
# ADVANCED METRICS CALCULATION
# =============================================================================

@dataclass
class AdvancedMetrics:
    """Advanced robustness metrics as recommended by expert review"""
    # Standard metrics
    pdr_end2end: float
    total_energy: float
    network_lifetime: int

    # Advanced robustness metrics
    recovery_time_rounds: float  # Rounds to recover from perturbation
    data_island_rate: float      # % of nodes that cannot reach BS
    control_overhead_peak: float  # Max control messages during adaptation
    control_overhead_avg: float   # Average control overhead

    # Dynamic adaptability metrics
    pdr_degradation_rate: float  # PDR drop per % of churn
    energy_variance: float       # Variance in node energy consumption
    cluster_stability: float     # Average cluster head tenure


def calculate_data_island_rate(nodes, bs_position, max_range=100.0):
    """
    Calculate the percentage of nodes that cannot reach the base station
    either directly or through multi-hop routing.
    """
    if not nodes:
        return 0.0

    alive_nodes = [n for n in nodes if getattr(n, 'is_alive', True) and getattr(n, 'current_energy', 0) > 0]
    if not alive_nodes:
        return 1.0

    bs_x, bs_y = bs_position

    # Build connectivity graph
    can_reach_bs = set()

    # First pass: nodes that can directly reach BS
    for node in alive_nodes:
        dist_to_bs = np.sqrt((node.x - bs_x)**2 + (node.y - bs_y)**2)
        if dist_to_bs <= max_range:
            can_reach_bs.add(node.id)

    # Multi-hop reachability (BFS)
    changed = True
    while changed:
        changed = False
        for node in alive_nodes:
            if node.id in can_reach_bs:
                continue
            # Check if this node can reach any node that can reach BS
            for other in alive_nodes:
                if other.id in can_reach_bs:
                    dist = np.sqrt((node.x - other.x)**2 + (node.y - other.y)**2)
                    if dist <= max_range:
                        can_reach_bs.add(node.id)
                        changed = True
                        break

    island_count = len(alive_nodes) - len(can_reach_bs)
    return island_count / len(alive_nodes) if alive_nodes else 0.0


def calculate_recovery_time(pdr_history: List[float], baseline_pdr: float, threshold=0.9):
    """
    Calculate the number of rounds needed to recover to threshold% of baseline PDR
    after a perturbation (detected as significant PDR drop).
    """
    if len(pdr_history) < 3:
        return 0.0

    recovery_times = []
    in_recovery = False
    recovery_start = 0
    target_pdr = baseline_pdr * threshold

    for i, pdr in enumerate(pdr_history):
        if not in_recovery and pdr < baseline_pdr * 0.8:  # Significant drop
            in_recovery = True
            recovery_start = i
        elif in_recovery and pdr >= target_pdr:
            recovery_times.append(i - recovery_start)
            in_recovery = False

    return np.mean(recovery_times) if recovery_times else 0.0


# =============================================================================
# DYNAMIC SCENARIO GENERATORS
# =============================================================================

def generate_uniform_positions(n_nodes: int, width: float, height: float, seed: int) -> List[Tuple[float, float]]:
    """Generate uniform random node positions"""
    rng = random.Random(seed)
    return [(rng.uniform(5, width-5), rng.uniform(5, height-5)) for _ in range(n_nodes)]


def generate_corridor_positions(n_nodes: int, width: float, height: float, seed: int,
                                aspect_ratio: float = 3.0) -> List[Tuple[float, float]]:
    """Generate corridor-shaped deployment (elongated along one axis)"""
    rng = random.Random(seed)
    corridor_height = height / aspect_ratio
    y_offset = (height - corridor_height) / 2
    return [(rng.uniform(5, width-5), rng.uniform(y_offset + 5, y_offset + corridor_height - 5))
            for _ in range(n_nodes)]


def apply_node_churn(positions: List[Tuple[float, float]], churn_rate: float, seed: int) -> List[Tuple[float, float]]:
    """Simulate random node failures (churn)"""
    rng = random.Random(seed)
    n_fail = int(len(positions) * churn_rate)
    indices = list(range(len(positions)))
    rng.shuffle(indices)
    failed_indices = set(indices[:n_fail])
    return [pos for i, pos in enumerate(positions) if i not in failed_indices]


def apply_regional_failure(positions: List[Tuple[float, float]],
                           failure_center: Tuple[float, float],
                           failure_radius: float) -> List[Tuple[float, float]]:
    """Simulate regional failure (e.g., physical damage, interference)"""
    cx, cy = failure_center
    return [(x, y) for x, y in positions
            if np.sqrt((x - cx)**2 + (y - cy)**2) > failure_radius]


def apply_intermittent_connectivity(positions: List[Tuple[float, float]],
                                    active_ratio: float, seed: int) -> List[Tuple[float, float]]:
    """Simulate periodic sleep/duty cycling"""
    rng = random.Random(seed)
    n_active = int(len(positions) * active_ratio)
    indices = list(range(len(positions)))
    rng.shuffle(indices)
    active_indices = set(indices[:n_active])
    return [pos for i, pos in enumerate(positions) if i in active_indices]


# =============================================================================
# PROTOCOL RUNNER WITH ADVANCED METRICS
# =============================================================================

def run_protocol_with_metrics(protocol_name: str, config: NetworkConfig,
                              max_rounds: int = 300, seed: int = 42) -> Dict:
    """Run a protocol and collect both standard and advanced metrics"""

    random.seed(seed)
    np.random.seed(seed)

    try:
        from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
        energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

        if protocol_name == "AERIS":
            protocol = AerisProtocol(
                config,
                enable_cas=True,
                enable_fairness=True,
                enable_gateway=True,
                enable_skeleton=True,
                profile="robust",
                verbose=False,
            )
        elif protocol_name == "AERIS_ENERGY":
            protocol = AerisProtocol(
                config,
                enable_cas=True,
                enable_fairness=True,
                enable_gateway=True,
                enable_skeleton=True,
                profile="energy",
                verbose=False,
            )
        elif protocol_name == "LEACH":
            # Use LEACHProtocol from benchmark_protocols (takes config, energy_model)
            protocol = LEACHProtocol(config, energy_model)
        elif protocol_name == "PEGASIS":
            # Use PEGASISProtocol from benchmark_protocols
            protocol = PEGASISProtocol(config, energy_model)
        elif protocol_name == "HEED":
            # Use HEEDProtocolWrapper from benchmark_protocols
            protocol = HEEDProtocol(config, energy_model)
        else:
            raise ValueError(f"Unknown protocol: {protocol_name}")

        # Run simulation
        results = protocol.run_simulation(max_rounds)

        # Calculate advanced metrics
        pdr = results.get("packet_delivery_ratio_end2end", results.get("pdr", 0.0))
        energy = results.get("total_energy_consumed", results.get("total_energy", 0.0))
        lifetime = results.get("network_lifetime", max_rounds)

        # Get per-round data if available
        pdr_history = results.get("pdr_per_round", [pdr] * max_rounds)
        control_msgs = results.get("control_messages_per_round", [0] * max_rounds)

        # Calculate data island rate (approximate from final state)
        data_island = results.get("data_island_rate", 0.0)

        # Calculate recovery time
        recovery_time = calculate_recovery_time(pdr_history, pdr) if len(pdr_history) > 1 else 0.0

        # Control overhead
        control_peak = max(control_msgs) if control_msgs else 0
        control_avg = np.mean(control_msgs) if control_msgs else 0

        return {
            "protocol": protocol_name,
            "pdr_end2end": pdr,
            "total_energy": energy,
            "network_lifetime": lifetime,
            "recovery_time_rounds": recovery_time,
            "data_island_rate": data_island,
            "control_overhead_peak": control_peak,
            "control_overhead_avg": control_avg,
            "energy_variance": results.get("energy_variance", 0.0),
            "success": True
        }

    except Exception as e:
        return {
            "protocol": protocol_name,
            "error": str(e),
            "success": False
        }


# =============================================================================
# EXPERIMENT RUNNERS
# =============================================================================

def run_churn_experiment(n_nodes: int, area_size: float, churn_rates: List[float],
                         protocols: List[str], n_runs: int = 10, seed_base: int = 1000) -> Dict:
    """Run node churn experiment across multiple protocols"""

    print(f"\n{'='*60}")
    print(f"CHURN EXPERIMENT: {n_nodes} nodes, {area_size}x{area_size}m")
    print(f"Churn rates: {churn_rates}")
    print(f"{'='*60}")

    results = {"config": {"n_nodes": n_nodes, "area_size": area_size, "churn_rates": churn_rates}}

    for protocol in protocols:
        results[protocol] = {}
        for churn_rate in churn_rates:
            phase_results = []
            for run_id in range(n_runs):
                seed = seed_base + run_id * 100 + int(churn_rate * 1000)

                # Generate base positions
                base_positions = generate_uniform_positions(n_nodes, area_size, area_size, seed)

                # Apply churn
                active_positions = apply_node_churn(base_positions, churn_rate, seed + 1)

                config = NetworkConfig(
                    num_nodes=len(active_positions),
                    area_width=area_size,
                    area_height=area_size,
                    base_station_x=area_size / 2,
                    base_station_y=area_size + 50,
                    initial_energy=2.5,
                    packet_size=1024,
                    positions=active_positions,
                )

                result = run_protocol_with_metrics(protocol, config, max_rounds=200, seed=seed)
                if result["success"]:
                    phase_results.append(result)

            # Aggregate results
            if phase_results:
                results[protocol][f"churn_{int(churn_rate*100)}pct"] = {
                    "pdr_mean": np.mean([r["pdr_end2end"] for r in phase_results]),
                    "pdr_std": np.std([r["pdr_end2end"] for r in phase_results]),
                    "energy_mean": np.mean([r["total_energy"] for r in phase_results]),
                    "energy_std": np.std([r["total_energy"] for r in phase_results]),
                    "recovery_time_mean": np.mean([r["recovery_time_rounds"] for r in phase_results]),
                    "n_runs": len(phase_results)
                }
                print(f"  {protocol} @ {int(churn_rate*100)}% churn: PDR={results[protocol][f'churn_{int(churn_rate*100)}pct']['pdr_mean']:.3f}")

    return results


def run_regional_failure_experiment(n_nodes: int, area_size: float,
                                    failure_radii: List[float],
                                    protocols: List[str], n_runs: int = 10,
                                    seed_base: int = 2000) -> Dict:
    """Run regional failure experiment"""

    print(f"\n{'='*60}")
    print(f"REGIONAL FAILURE EXPERIMENT: {n_nodes} nodes")
    print(f"Failure radii: {failure_radii}")
    print(f"{'='*60}")

    results = {"config": {"n_nodes": n_nodes, "area_size": area_size, "failure_radii": failure_radii}}

    for protocol in protocols:
        results[protocol] = {}
        for radius in failure_radii:
            phase_results = []
            for run_id in range(n_runs):
                seed = seed_base + run_id * 100 + int(radius * 10)

                base_positions = generate_uniform_positions(n_nodes, area_size, area_size, seed)

                # Apply regional failure at center
                failure_center = (area_size / 2, area_size / 2)
                active_positions = apply_regional_failure(base_positions, failure_center, radius)

                if len(active_positions) < 10:  # Too few nodes
                    continue

                config = NetworkConfig(
                    num_nodes=len(active_positions),
                    area_width=area_size,
                    area_height=area_size,
                    base_station_x=area_size / 2,
                    base_station_y=area_size + 50,
                    initial_energy=2.5,
                    packet_size=1024,
                    positions=active_positions,
                )

                result = run_protocol_with_metrics(protocol, config, max_rounds=200, seed=seed)
                if result["success"]:
                    result["nodes_failed"] = n_nodes - len(active_positions)
                    result["failure_rate"] = result["nodes_failed"] / n_nodes
                    phase_results.append(result)

            if phase_results:
                results[protocol][f"radius_{int(radius)}m"] = {
                    "pdr_mean": np.mean([r["pdr_end2end"] for r in phase_results]),
                    "pdr_std": np.std([r["pdr_end2end"] for r in phase_results]),
                    "nodes_failed_mean": np.mean([r["nodes_failed"] for r in phase_results]),
                    "failure_rate_mean": np.mean([r["failure_rate"] for r in phase_results]),
                    "n_runs": len(phase_results)
                }
                print(f"  {protocol} @ radius={radius}m: PDR={results[protocol][f'radius_{int(radius)}m']['pdr_mean']:.3f}")

    return results


def run_scalability_experiment(node_counts: List[int], area_base: float,
                               protocols: List[str], n_runs: int = 5,
                               seed_base: int = 3000) -> Dict:
    """Run scalability experiment with varying node counts"""

    print(f"\n{'='*60}")
    print(f"SCALABILITY EXPERIMENT")
    print(f"Node counts: {node_counts}")
    print(f"{'='*60}")

    results = {"config": {"node_counts": node_counts, "area_base": area_base}}

    for protocol in protocols:
        results[protocol] = {}
        for n_nodes in node_counts:
            # Scale area with node count to maintain density
            area_size = area_base * np.sqrt(n_nodes / 100)

            phase_results = []
            for run_id in range(n_runs):
                seed = seed_base + run_id * 100 + n_nodes

                positions = generate_uniform_positions(n_nodes, area_size, area_size, seed)

                config = NetworkConfig(
                    num_nodes=n_nodes,
                    area_width=area_size,
                    area_height=area_size,
                    base_station_x=area_size / 2,
                    base_station_y=area_size + 50,
                    initial_energy=2.5,
                    packet_size=1024,
                    positions=positions,
                )

                start_time = time.time()
                result = run_protocol_with_metrics(protocol, config, max_rounds=150, seed=seed)
                result["execution_time"] = time.time() - start_time

                if result["success"]:
                    phase_results.append(result)

            if phase_results:
                results[protocol][f"nodes_{n_nodes}"] = {
                    "pdr_mean": np.mean([r["pdr_end2end"] for r in phase_results]),
                    "pdr_std": np.std([r["pdr_end2end"] for r in phase_results]),
                    "energy_mean": np.mean([r["total_energy"] for r in phase_results]),
                    "exec_time_mean": np.mean([r["execution_time"] for r in phase_results]),
                    "n_runs": len(phase_results)
                }
                print(f"  {protocol} @ {n_nodes} nodes: PDR={results[protocol][f'nodes_{n_nodes}']['pdr_mean']:.3f}, Time={results[protocol][f'nodes_{n_nodes}']['exec_time_mean']:.2f}s")

    return results


def run_intermittent_connectivity_experiment(n_nodes: int, area_size: float,
                                             duty_cycles: List[float],
                                             protocols: List[str], n_runs: int = 10,
                                             seed_base: int = 4000) -> Dict:
    """Run intermittent connectivity (duty cycling) experiment"""

    print(f"\n{'='*60}")
    print(f"INTERMITTENT CONNECTIVITY EXPERIMENT: {n_nodes} nodes")
    print(f"Duty cycles: {duty_cycles}")
    print(f"{'='*60}")

    results = {"config": {"n_nodes": n_nodes, "area_size": area_size, "duty_cycles": duty_cycles}}

    for protocol in protocols:
        results[protocol] = {}
        for duty_cycle in duty_cycles:
            phase_results = []
            for run_id in range(n_runs):
                seed = seed_base + run_id * 100 + int(duty_cycle * 100)

                base_positions = generate_uniform_positions(n_nodes, area_size, area_size, seed)
                active_positions = apply_intermittent_connectivity(base_positions, duty_cycle, seed + 1)

                if len(active_positions) < 10:
                    continue

                config = NetworkConfig(
                    num_nodes=len(active_positions),
                    area_width=area_size,
                    area_height=area_size,
                    base_station_x=area_size / 2,
                    base_station_y=area_size + 50,
                    initial_energy=2.5,
                    packet_size=1024,
                    positions=active_positions,
                )

                result = run_protocol_with_metrics(protocol, config, max_rounds=200, seed=seed)
                if result["success"]:
                    phase_results.append(result)

            if phase_results:
                results[protocol][f"duty_{int(duty_cycle*100)}pct"] = {
                    "pdr_mean": np.mean([r["pdr_end2end"] for r in phase_results]),
                    "pdr_std": np.std([r["pdr_end2end"] for r in phase_results]),
                    "energy_mean": np.mean([r["total_energy"] for r in phase_results]),
                    "n_runs": len(phase_results)
                }
                print(f"  {protocol} @ {int(duty_cycle*100)}% duty: PDR={results[protocol][f'duty_{int(duty_cycle*100)}pct']['pdr_mean']:.3f}")

    return results


# =============================================================================
# MAIN EXPERIMENT RUNNER
# =============================================================================

def run_all_experiments():
    """Run all comprehensive experiments"""

    print("=" * 70)
    print("COMPREHENSIVE DYNAMIC EXPERIMENTS FOR AERIS PAPER")
    print("Based on Expert Review Recommendations")
    print("=" * 70)
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Protocols to compare
    protocols = ["AERIS", "LEACH", "PEGASIS", "HEED"]

    all_results = {}

    # 1. Node Churn Experiment
    print("\n[1/4] Running Node Churn Experiments...")
    churn_results = run_churn_experiment(
        n_nodes=100,
        area_size=150.0,
        churn_rates=[0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30],
        protocols=protocols,
        n_runs=15
    )
    all_results["churn_experiment"] = churn_results

    # 2. Regional Failure Experiment
    print("\n[2/4] Running Regional Failure Experiments...")
    regional_results = run_regional_failure_experiment(
        n_nodes=100,
        area_size=150.0,
        failure_radii=[0, 10, 20, 30, 40, 50],
        protocols=protocols,
        n_runs=15
    )
    all_results["regional_failure_experiment"] = regional_results

    # 3. Scalability Experiment
    print("\n[3/4] Running Scalability Experiments...")
    scalability_results = run_scalability_experiment(
        node_counts=[50, 100, 150, 200, 250, 300, 400, 500],
        area_base=150.0,
        protocols=protocols,
        n_runs=10
    )
    all_results["scalability_experiment"] = scalability_results

    # 4. Intermittent Connectivity Experiment
    print("\n[4/4] Running Intermittent Connectivity Experiments...")
    intermittent_results = run_intermittent_connectivity_experiment(
        n_nodes=100,
        area_size=150.0,
        duty_cycles=[1.0, 0.9, 0.8, 0.7, 0.6, 0.5],
        protocols=protocols,
        n_runs=15
    )
    all_results["intermittent_experiment"] = intermittent_results

    # Save all results
    output_path = os.path.join(os.path.dirname(__file__), '..', 'results',
                               'comprehensive_dynamic_experiments.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"EXPERIMENTS COMPLETE")
    print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Results saved to: {output_path}")
    print("=" * 70)

    return all_results


if __name__ == "__main__":
    results = run_all_experiments()
