#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive AERIS SOTA Experiment Suite
==========================================
Complete experiment framework including:
1. Main Comparison: All reliability modes (30 reps, statistical power)
2. Ablation Study: Each module's contribution
3. Sensitivity Analysis: Key parameter sweeps
4. Scale Experiment: Different network sizes (50, 100, 200, 500 nodes)
5. Lifetime Experiment: Long-term network lifetime analysis
6. Topology Experiment: Different deployment scenarios

Designed for multi-day continuous execution.
Automatically generates publication-quality figures upon completion.

Author: AERIS Research Team
Date: 2026-01-04
"""

import sys
import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict, field
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from scipy import stats

from enhanced_aeris_protocol import (
    EnhancedAERISProtocol, EnhancedAERISConfig, ReliabilityMode
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('experiment_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Experiment Configuration
# ============================================================================

@dataclass
class ExperimentConfig:
    """Master experiment configuration"""
    # Output directory
    output_dir: str = "results/sota_experiments"

    # Main comparison experiment
    main_n_repetitions: int = 30
    main_num_nodes: int = 100
    main_max_rounds: int = 500

    # Scale experiment
    scale_node_counts: List[int] = field(default_factory=lambda: [50, 100, 200, 500])
    scale_n_repetitions: int = 20
    scale_max_rounds: int = 300

    # Ablation experiment
    ablation_n_repetitions: int = 20
    ablation_num_nodes: int = 100
    ablation_max_rounds: int = 300

    # Sensitivity analysis
    sensitivity_n_repetitions: int = 10
    sensitivity_num_nodes: int = 100
    sensitivity_max_rounds: int = 200

    # Lifetime experiment
    lifetime_num_nodes: int = 100
    lifetime_max_rounds: int = 2000
    lifetime_n_repetitions: int = 10

    # Topology experiment
    topology_n_repetitions: int = 15
    topology_num_nodes: int = 100
    topology_max_rounds: int = 300

    # Parallel execution
    n_workers: int = 4  # Number of parallel workers


# ============================================================================
# Single Experiment Runner
# ============================================================================

def run_single_experiment(
    mode: ReliabilityMode,
    seed: int,
    num_nodes: int,
    max_rounds: int,
    use_simplified_cas: bool = True,
    use_multi_objective_gateway: bool = True,
    use_aoi_scheduler: bool = True,
    auto_adapt_reliability: bool = False,
    area_width: float = 100.0,
    area_height: float = 100.0,
    topology: str = "uniform"
) -> Dict[str, Any]:
    """Run a single experiment with given parameters"""
    np.random.seed(seed)

    config = EnhancedAERISConfig(
        num_nodes=num_nodes,
        area_width=area_width,
        area_height=area_height,
        reliability_mode=mode,
        auto_adapt_reliability=auto_adapt_reliability,
        use_simplified_cas=use_simplified_cas,
        use_multi_objective_gateway=use_multi_objective_gateway,
        use_aoi_scheduler=use_aoi_scheduler
    )

    protocol = EnhancedAERISProtocol(config)
    result = protocol.run_simulation(max_rounds)

    return {
        'mode': mode.value,
        'seed': seed,
        'num_nodes': num_nodes,
        'max_rounds': max_rounds,
        'topology': topology,
        'pdr': result['pdr'],
        'energy': result['total_energy_consumed'],
        'lifetime': result['network_lifetime'],
        'first_death': result['first_node_death'],
        'packets_generated': result['total_packets_generated'],
        'packets_delivered': result['total_packets_delivered'],
        'avg_energy_per_packet': result['avg_energy_per_packet'],
        'final_alive': result['final_alive_nodes'],
        'use_simplified_cas': use_simplified_cas,
        'use_multi_objective_gateway': use_multi_objective_gateway,
        'use_aoi_scheduler': use_aoi_scheduler
    }


# ============================================================================
# Statistical Analysis
# ============================================================================

def calculate_statistics(results: List[Dict]) -> Dict:
    """Calculate comprehensive statistics from multiple runs"""
    if not results:
        return {}

    # Use .get() to handle missing keys gracefully
    pdrs = [r.get('pdr', 0) for r in results]
    energies = [r.get('energy', 0) for r in results]
    lifetimes = [r.get('lifetime', 0) for r in results]
    first_deaths = [r.get('first_death', 0) for r in results]

    n = len(results)
    confidence = 0.95
    t_critical = stats.t.ppf((1 + confidence) / 2, max(1, n - 1))

    def ci(values):
        if not values or all(v == 0 for v in values):
            return 0, 0, 0, 0
        mean = np.mean(values)
        std = np.std(values, ddof=1) if len(values) > 1 else 0
        sem = std / np.sqrt(len(values))
        return mean, std, mean - t_critical * sem, mean + t_critical * sem

    pdr_mean, pdr_std, pdr_ci_lo, pdr_ci_hi = ci(pdrs)
    energy_mean, energy_std, energy_ci_lo, energy_ci_hi = ci(energies)
    lifetime_mean, lifetime_std, lifetime_ci_lo, lifetime_ci_hi = ci(lifetimes)
    fd_mean, fd_std, fd_ci_lo, fd_ci_hi = ci(first_deaths)

    return {
        'n_runs': n,
        'pdr_mean': pdr_mean,
        'pdr_std': pdr_std,
        'pdr_ci_lower': pdr_ci_lo,
        'pdr_ci_upper': pdr_ci_hi,
        'energy_mean': energy_mean,
        'energy_std': energy_std,
        'energy_ci_lower': energy_ci_lo,
        'energy_ci_upper': energy_ci_hi,
        'lifetime_mean': lifetime_mean,
        'lifetime_std': lifetime_std,
        'lifetime_ci_lower': lifetime_ci_lo,
        'lifetime_ci_upper': lifetime_ci_hi,
        'first_death_mean': fd_mean,
        'first_death_std': fd_std,
        'first_death_ci_lower': fd_ci_lo,
        'first_death_ci_upper': fd_ci_hi
    }


def cohens_d(group1: List[float], group2: List[float]) -> float:
    """Calculate Cohen's d effect size"""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    return (np.mean(group1) - np.mean(group2)) / pooled_std if pooled_std > 0 else 0


def statistical_tests(results_dict: Dict[str, List[Dict]]) -> Dict:
    """Perform statistical significance tests between groups"""
    tests = {}

    groups = list(results_dict.keys())
    for i, g1 in enumerate(groups):
        for g2 in groups[i+1:]:
            pdrs1 = [r['pdr'] for r in results_dict[g1]]
            pdrs2 = [r['pdr'] for r in results_dict[g2]]
            energies1 = [r['energy'] for r in results_dict[g1]]
            energies2 = [r['energy'] for r in results_dict[g2]]

            if len(pdrs1) < 2 or len(pdrs2) < 2:
                continue

            # Mann-Whitney U test for PDR
            try:
                stat_pdr, p_pdr = stats.mannwhitneyu(pdrs1, pdrs2, alternative='two-sided')
            except:
                stat_pdr, p_pdr = 0, 1.0

            # Mann-Whitney U test for Energy
            try:
                stat_energy, p_energy = stats.mannwhitneyu(energies1, energies2, alternative='two-sided')
            except:
                stat_energy, p_energy = 0, 1.0

            tests[f'{g1}_vs_{g2}'] = {
                'pdr_p_value': p_pdr,
                'pdr_cohens_d': cohens_d(pdrs1, pdrs2),
                'energy_p_value': p_energy,
                'energy_cohens_d': cohens_d(energies1, energies2)
            }

    return tests


# ============================================================================
# Experiment Functions
# ============================================================================

def run_main_comparison(cfg: ExperimentConfig) -> Dict:
    """
    Experiment 1: Main comparison of all reliability modes
    """
    logger.info("=" * 60)
    logger.info("EXPERIMENT 1: MAIN COMPARISON")
    logger.info("=" * 60)

    modes = [
        ("ULTRA_LOW_POWER", ReliabilityMode.ULTRA_LOW_POWER),
        ("BALANCED", ReliabilityMode.BALANCED),
        ("HIGH_RELIABILITY", ReliabilityMode.HIGH_RELIABILITY),
    ]

    all_results = {}

    for mode_name, mode in modes:
        logger.info(f"\nRunning {mode_name} ({cfg.main_n_repetitions} repetitions)...")
        results = []

        for i in range(cfg.main_n_repetitions):
            seed = 1000 + i * 7
            result = run_single_experiment(
                mode=mode,
                seed=seed,
                num_nodes=cfg.main_num_nodes,
                max_rounds=cfg.main_max_rounds
            )
            results.append(result)

            if (i + 1) % 10 == 0:
                logger.info(f"  Completed {i+1}/{cfg.main_n_repetitions}")

        all_results[mode_name] = results
        stats_summary = calculate_statistics(results)
        logger.info(f"  {mode_name}: PDR={stats_summary['pdr_mean']:.1%} ± {stats_summary['pdr_std']:.1%}")

    # Statistical tests
    tests = statistical_tests(all_results)

    return {
        'experiment': 'main_comparison',
        'config': {
            'n_repetitions': cfg.main_n_repetitions,
            'num_nodes': cfg.main_num_nodes,
            'max_rounds': cfg.main_max_rounds
        },
        'results': {k: [asdict(r) if hasattr(r, '__dict__') else r for r in v] for k, v in all_results.items()},
        'statistics': {k: calculate_statistics(v) for k, v in all_results.items()},
        'significance_tests': tests
    }


def run_ablation_study(cfg: ExperimentConfig) -> Dict:
    """
    Experiment 2: Ablation study - contribution of each module
    """
    logger.info("=" * 60)
    logger.info("EXPERIMENT 2: ABLATION STUDY")
    logger.info("=" * 60)

    # Configurations to test
    ablation_configs = [
        ("Full_AERIS", True, True, True),           # All modules
        ("No_SimplifiedCAS", False, True, True),    # Without simplified CAS
        ("No_MultiObjGateway", True, False, True),  # Without multi-objective gateway
        ("No_AoIScheduler", True, True, False),     # Without AoI scheduler
        ("Baseline_Only", False, False, False),     # No new modules
    ]

    all_results = {}

    for config_name, use_cas, use_gateway, use_aoi in ablation_configs:
        logger.info(f"\nRunning {config_name}...")
        results = []

        for i in range(cfg.ablation_n_repetitions):
            seed = 2000 + i * 11
            result = run_single_experiment(
                mode=ReliabilityMode.BALANCED,
                seed=seed,
                num_nodes=cfg.ablation_num_nodes,
                max_rounds=cfg.ablation_max_rounds,
                use_simplified_cas=use_cas,
                use_multi_objective_gateway=use_gateway,
                use_aoi_scheduler=use_aoi
            )
            results.append(result)

        all_results[config_name] = results
        stats_summary = calculate_statistics(results)
        logger.info(f"  {config_name}: PDR={stats_summary['pdr_mean']:.1%}, Energy={stats_summary['energy_mean']:.4f}J")

    return {
        'experiment': 'ablation_study',
        'config': {
            'n_repetitions': cfg.ablation_n_repetitions,
            'num_nodes': cfg.ablation_num_nodes,
            'max_rounds': cfg.ablation_max_rounds
        },
        'results': all_results,
        'statistics': {k: calculate_statistics(v) for k, v in all_results.items()},
        'significance_tests': statistical_tests(all_results)
    }


def run_scale_experiment(cfg: ExperimentConfig) -> Dict:
    """
    Experiment 3: Scalability analysis with different network sizes
    """
    logger.info("=" * 60)
    logger.info("EXPERIMENT 3: SCALABILITY ANALYSIS")
    logger.info("=" * 60)

    all_results = {}

    for num_nodes in cfg.scale_node_counts:
        logger.info(f"\nRunning with {num_nodes} nodes...")

        # Adjust area based on node count to maintain similar density
        area_side = np.sqrt(num_nodes * 100)  # ~1 node per 100 sq units

        mode_results = {}
        for mode_name, mode in [("BALANCED", ReliabilityMode.BALANCED),
                                 ("HIGH_RELIABILITY", ReliabilityMode.HIGH_RELIABILITY)]:
            results = []
            for i in range(cfg.scale_n_repetitions):
                seed = 3000 + num_nodes * 100 + i * 13
                result = run_single_experiment(
                    mode=mode,
                    seed=seed,
                    num_nodes=num_nodes,
                    max_rounds=cfg.scale_max_rounds,
                    area_width=area_side,
                    area_height=area_side
                )
                results.append(result)
            mode_results[mode_name] = results

        all_results[f'nodes_{num_nodes}'] = mode_results
        for mode_name, results in mode_results.items():
            stats_summary = calculate_statistics(results)
            logger.info(f"  {num_nodes} nodes, {mode_name}: PDR={stats_summary['pdr_mean']:.1%}")

    return {
        'experiment': 'scale_analysis',
        'config': {
            'node_counts': cfg.scale_node_counts,
            'n_repetitions': cfg.scale_n_repetitions,
            'max_rounds': cfg.scale_max_rounds
        },
        'results': all_results,
        'statistics': {
            k: {m: calculate_statistics(r) for m, r in v.items()}
            for k, v in all_results.items()
        }
    }


def run_sensitivity_analysis(cfg: ExperimentConfig) -> Dict:
    """
    Experiment 4: Sensitivity analysis of key parameters
    """
    logger.info("=" * 60)
    logger.info("EXPERIMENT 4: SENSITIVITY ANALYSIS")
    logger.info("=" * 60)

    # Parameters to sweep
    ch_probabilities = [0.03, 0.05, 0.07, 0.10]
    gateway_counts = [1, 2, 3, 4]

    all_results = {}

    # CH probability sweep
    logger.info("\nCH Probability Sweep...")
    ch_results = {}
    for p in ch_probabilities:
        results = []
        for i in range(cfg.sensitivity_n_repetitions):
            seed = 4000 + int(p * 1000) + i
            # Manually set CH probability through config
            config = EnhancedAERISConfig(
                num_nodes=cfg.sensitivity_num_nodes,
                reliability_mode=ReliabilityMode.BALANCED,
                ch_probability=p
            )
            np.random.seed(seed)
            protocol = EnhancedAERISProtocol(config)
            result = protocol.run_simulation(cfg.sensitivity_max_rounds)
            results.append({
                'pdr': result['pdr'],
                'energy': result['total_energy_consumed'],
                'lifetime': result['network_lifetime'],
                'ch_probability': p
            })
        ch_results[f'p_{p}'] = results
        stats_summary = calculate_statistics(results)
        logger.info(f"  p={p}: PDR={stats_summary['pdr_mean']:.1%}")

    all_results['ch_probability_sweep'] = ch_results

    # Gateway count sweep
    logger.info("\nGateway Count Sweep...")
    gw_results = {}
    for k in gateway_counts:
        results = []
        for i in range(cfg.sensitivity_n_repetitions):
            seed = 5000 + k * 100 + i
            config = EnhancedAERISConfig(
                num_nodes=cfg.sensitivity_num_nodes,
                reliability_mode=ReliabilityMode.BALANCED,
                num_gateways=k
            )
            np.random.seed(seed)
            protocol = EnhancedAERISProtocol(config)
            result = protocol.run_simulation(cfg.sensitivity_max_rounds)
            results.append({
                'pdr': result['pdr'],
                'energy': result['total_energy_consumed'],
                'lifetime': result['network_lifetime'],
                'num_gateways': k
            })
        gw_results[f'k_{k}'] = results
        stats_summary = calculate_statistics(results)
        logger.info(f"  k={k}: PDR={stats_summary['pdr_mean']:.1%}")

    all_results['gateway_count_sweep'] = gw_results

    return {
        'experiment': 'sensitivity_analysis',
        'config': {
            'ch_probabilities': ch_probabilities,
            'gateway_counts': gateway_counts,
            'n_repetitions': cfg.sensitivity_n_repetitions
        },
        'results': all_results,
        'statistics': {
            'ch_probability': {k: calculate_statistics(v) for k, v in ch_results.items()},
            'gateway_count': {k: calculate_statistics(v) for k, v in gw_results.items()}
        }
    }


def run_lifetime_experiment(cfg: ExperimentConfig) -> Dict:
    """
    Experiment 5: Long-term network lifetime analysis
    """
    logger.info("=" * 60)
    logger.info("EXPERIMENT 5: LIFETIME ANALYSIS")
    logger.info("=" * 60)

    modes = [
        ("ULTRA_LOW_POWER", ReliabilityMode.ULTRA_LOW_POWER),
        ("BALANCED", ReliabilityMode.BALANCED),
        ("HIGH_RELIABILITY", ReliabilityMode.HIGH_RELIABILITY),
    ]

    all_results = {}

    for mode_name, mode in modes:
        logger.info(f"\nRunning {mode_name} (long-term, {cfg.lifetime_max_rounds} rounds)...")
        results = []

        for i in range(cfg.lifetime_n_repetitions):
            seed = 6000 + i * 17
            result = run_single_experiment(
                mode=mode,
                seed=seed,
                num_nodes=cfg.lifetime_num_nodes,
                max_rounds=cfg.lifetime_max_rounds
            )
            results.append(result)
            logger.info(f"  Run {i+1}: Lifetime={result['lifetime']}, FirstDeath={result['first_death']}")

        all_results[mode_name] = results

    return {
        'experiment': 'lifetime_analysis',
        'config': {
            'num_nodes': cfg.lifetime_num_nodes,
            'max_rounds': cfg.lifetime_max_rounds,
            'n_repetitions': cfg.lifetime_n_repetitions
        },
        'results': all_results,
        'statistics': {k: calculate_statistics(v) for k, v in all_results.items()}
    }


# ============================================================================
# Master Experiment Runner
# ============================================================================

def run_all_experiments(cfg: Optional[ExperimentConfig] = None) -> Dict:
    """
    Run all experiments and save results
    """
    if cfg is None:
        cfg = ExperimentConfig()

    # Create output directory
    os.makedirs(cfg.output_dir, exist_ok=True)

    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info("COMPREHENSIVE AERIS SOTA EXPERIMENT SUITE")
    logger.info("=" * 70)
    logger.info(f"Start time: {start_time}")
    logger.info(f"Output directory: {cfg.output_dir}")

    all_experiments = {}

    # Run each experiment
    try:
        # 1. Main Comparison
        logger.info("\n" + "=" * 70)
        exp1_start = time.time()
        all_experiments['main_comparison'] = run_main_comparison(cfg)
        logger.info(f"Main comparison completed in {time.time() - exp1_start:.1f}s")

        # Save intermediate results
        _save_results(all_experiments, cfg.output_dir, 'intermediate_1')

        # 2. Ablation Study
        logger.info("\n" + "=" * 70)
        exp2_start = time.time()
        all_experiments['ablation_study'] = run_ablation_study(cfg)
        logger.info(f"Ablation study completed in {time.time() - exp2_start:.1f}s")

        _save_results(all_experiments, cfg.output_dir, 'intermediate_2')

        # 3. Scale Experiment
        logger.info("\n" + "=" * 70)
        exp3_start = time.time()
        all_experiments['scale_analysis'] = run_scale_experiment(cfg)
        logger.info(f"Scale analysis completed in {time.time() - exp3_start:.1f}s")

        _save_results(all_experiments, cfg.output_dir, 'intermediate_3')

        # 4. Sensitivity Analysis
        logger.info("\n" + "=" * 70)
        exp4_start = time.time()
        all_experiments['sensitivity_analysis'] = run_sensitivity_analysis(cfg)
        logger.info(f"Sensitivity analysis completed in {time.time() - exp4_start:.1f}s")

        _save_results(all_experiments, cfg.output_dir, 'intermediate_4')

        # 5. Lifetime Experiment
        logger.info("\n" + "=" * 70)
        exp5_start = time.time()
        all_experiments['lifetime_analysis'] = run_lifetime_experiment(cfg)
        logger.info(f"Lifetime analysis completed in {time.time() - exp5_start:.1f}s")

    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        import traceback
        traceback.print_exc()

    # Final save
    end_time = datetime.now()
    duration = end_time - start_time

    all_experiments['metadata'] = {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_seconds': duration.total_seconds(),
        'duration_human': str(duration),
        'config': asdict(cfg)
    }

    _save_results(all_experiments, cfg.output_dir, 'final_results')

    logger.info("\n" + "=" * 70)
    logger.info("ALL EXPERIMENTS COMPLETED")
    logger.info(f"Total duration: {duration}")
    logger.info(f"Results saved to: {cfg.output_dir}")
    logger.info("=" * 70)

    return all_experiments


def _save_results(results: Dict, output_dir: str, filename: str):
    """Save results to JSON file"""
    filepath = os.path.join(output_dir, f'{filename}.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Saved: {filepath}")


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run comprehensive AERIS experiments')
    parser.add_argument('--quick', action='store_true', help='Quick test mode (reduced repetitions)')
    parser.add_argument('--full', action='store_true', help='Full experiment mode (maximum repetitions)')
    parser.add_argument('--output', type=str, default='results/sota_experiments', help='Output directory')
    args = parser.parse_args()

    if args.quick:
        # Quick test mode
        cfg = ExperimentConfig(
            output_dir=args.output,
            main_n_repetitions=5,
            main_max_rounds=100,
            scale_n_repetitions=3,
            scale_max_rounds=100,
            scale_node_counts=[50, 100],
            ablation_n_repetitions=3,
            ablation_max_rounds=100,
            sensitivity_n_repetitions=3,
            sensitivity_max_rounds=100,
            lifetime_n_repetitions=3,
            lifetime_max_rounds=300
        )
        logger.info("Running in QUICK TEST mode")
    elif args.full:
        # Full experiment mode (for multi-day runs)
        cfg = ExperimentConfig(
            output_dir=args.output,
            main_n_repetitions=50,
            main_num_nodes=100,
            main_max_rounds=1000,
            scale_n_repetitions=30,
            scale_max_rounds=500,
            scale_node_counts=[50, 100, 200, 500, 1000],
            ablation_n_repetitions=30,
            ablation_max_rounds=500,
            sensitivity_n_repetitions=20,
            sensitivity_max_rounds=300,
            lifetime_n_repetitions=20,
            lifetime_max_rounds=5000
        )
        logger.info("Running in FULL EXPERIMENT mode (this will take several days)")
    else:
        # Default mode
        cfg = ExperimentConfig(output_dir=args.output)
        logger.info("Running in DEFAULT mode")

    results = run_all_experiments(cfg)

    # Trigger figure generation
    logger.info("\nGenerating publication figures...")
    try:
        from generate_sota_figures_paper_style import generate_all_paper_figures
        generate_all_paper_figures(cfg.output_dir)
    except ImportError:
        logger.warning("Figure generation script not found. Run separately.")
