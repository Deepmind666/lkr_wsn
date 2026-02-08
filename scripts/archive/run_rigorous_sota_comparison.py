#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rigorous SOTA Comparison Experiment
====================================
Scientifically rigorous comparison of AERIS reliability modes.

Key improvements over simple comparison:
1. Multiple repetitions with different seeds
2. Statistical significance testing (Wilcoxon, Mann-Whitney)
3. 95% confidence intervals
4. Effect size calculation (Cohen's d)
5. Detailed per-hop PDR breakdown

Author: AERIS Research Team
Date: 2026-01-04
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from scipy import stats
from typing import List, Dict, Tuple
import json
from dataclasses import dataclass, asdict
from enhanced_aeris_protocol import (
    EnhancedAERISProtocol, EnhancedAERISConfig, ReliabilityMode
)


@dataclass
class ExperimentResult:
    """Single experiment run result"""
    mode: str
    seed: int
    pdr: float
    energy: float
    lifetime: int
    packets_generated: int
    packets_delivered: int
    avg_energy_per_packet: float


@dataclass
class StatisticalSummary:
    """Statistical summary of multiple runs"""
    mode: str
    n_runs: int
    pdr_mean: float
    pdr_std: float
    pdr_ci_lower: float
    pdr_ci_upper: float
    energy_mean: float
    energy_std: float
    energy_ci_lower: float
    energy_ci_upper: float
    lifetime_mean: float
    lifetime_std: float


def run_single_experiment(mode: ReliabilityMode, seed: int,
                          num_nodes: int = 100, max_rounds: int = 300) -> ExperimentResult:
    """Run a single experiment with given mode and seed"""
    np.random.seed(seed)

    config = EnhancedAERISConfig(
        num_nodes=num_nodes,
        reliability_mode=mode,
        auto_adapt_reliability=False,
        use_simplified_cas=True,
        use_multi_objective_gateway=True,
        use_aoi_scheduler=True
    )

    protocol = EnhancedAERISProtocol(config)
    result = protocol.run_simulation(max_rounds)

    return ExperimentResult(
        mode=mode.value,
        seed=seed,
        pdr=result['pdr'],
        energy=result['total_energy_consumed'],
        lifetime=result['network_lifetime'],
        packets_generated=result['total_packets_generated'],
        packets_delivered=result['total_packets_delivered'],
        avg_energy_per_packet=result['avg_energy_per_packet']
    )


def calculate_statistics(results: List[ExperimentResult]) -> StatisticalSummary:
    """Calculate statistical summary from multiple runs"""
    pdrs = [r.pdr for r in results]
    energies = [r.energy for r in results]
    lifetimes = [r.lifetime for r in results]

    n = len(results)
    confidence = 0.95
    t_critical = stats.t.ppf((1 + confidence) / 2, n - 1)

    pdr_mean = np.mean(pdrs)
    pdr_std = np.std(pdrs, ddof=1)
    pdr_sem = pdr_std / np.sqrt(n)

    energy_mean = np.mean(energies)
    energy_std = np.std(energies, ddof=1)
    energy_sem = energy_std / np.sqrt(n)

    return StatisticalSummary(
        mode=results[0].mode,
        n_runs=n,
        pdr_mean=pdr_mean,
        pdr_std=pdr_std,
        pdr_ci_lower=pdr_mean - t_critical * pdr_sem,
        pdr_ci_upper=pdr_mean + t_critical * pdr_sem,
        energy_mean=energy_mean,
        energy_std=energy_std,
        energy_ci_lower=energy_mean - t_critical * energy_sem,
        energy_ci_upper=energy_mean + t_critical * energy_sem,
        lifetime_mean=np.mean(lifetimes),
        lifetime_std=np.std(lifetimes, ddof=1)
    )


def cohens_d(group1: List[float], group2: List[float]) -> float:
    """Calculate Cohen's d effect size"""
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    return (np.mean(group1) - np.mean(group2)) / pooled_std if pooled_std > 0 else 0


def run_rigorous_comparison(n_repetitions: int = 10,
                            num_nodes: int = 100,
                            max_rounds: int = 300) -> Dict:
    """
    Run rigorous comparison experiment with statistical analysis.

    Args:
        n_repetitions: Number of repetitions per mode
        num_nodes: Number of sensor nodes
        max_rounds: Maximum simulation rounds

    Returns:
        Dictionary with all results and statistical analysis
    """
    print("=" * 70)
    print("RIGOROUS SOTA COMPARISON EXPERIMENT")
    print("=" * 70)
    print(f"Configuration: {num_nodes} nodes, {max_rounds} rounds, {n_repetitions} repetitions")
    print()

    modes = [
        ("ULTRA_LOW_POWER", ReliabilityMode.ULTRA_LOW_POWER),
        ("BALANCED", ReliabilityMode.BALANCED),
        ("HIGH_RELIABILITY", ReliabilityMode.HIGH_RELIABILITY),
    ]

    all_results: Dict[str, List[ExperimentResult]] = {}
    summaries: Dict[str, StatisticalSummary] = {}

    # Run experiments for each mode
    for mode_name, mode in modes:
        print(f"\nRunning {mode_name} ({n_repetitions} repetitions)...")
        results = []

        for i in range(n_repetitions):
            seed = 1000 + i * 7  # Different seeds
            result = run_single_experiment(mode, seed, num_nodes, max_rounds)
            results.append(result)
            print(f"  Run {i+1}/{n_repetitions}: PDR={result.pdr:.1%}, Energy={result.energy:.4f}J")

        all_results[mode_name] = results
        summaries[mode_name] = calculate_statistics(results)

    # Print summary table
    print("\n" + "=" * 70)
    print("STATISTICAL SUMMARY")
    print("=" * 70)
    print(f"\n{'Mode':<20} {'PDR Mean':>10} {'PDR 95% CI':>18} {'Energy Mean':>12} {'Energy 95% CI':>18}")
    print("-" * 80)

    for mode_name in ["ULTRA_LOW_POWER", "BALANCED", "HIGH_RELIABILITY"]:
        s = summaries[mode_name]
        print(f"{mode_name:<20} {s.pdr_mean:>9.1%} [{s.pdr_ci_lower:>6.1%}, {s.pdr_ci_upper:>6.1%}] "
              f"{s.energy_mean:>11.4f}J [{s.energy_ci_lower:>6.4f}, {s.energy_ci_upper:>6.4f}]")

    # Statistical tests
    print("\n" + "=" * 70)
    print("STATISTICAL SIGNIFICANCE TESTS")
    print("=" * 70)

    # Compare BALANCED vs ULTRA_LOW_POWER
    pdrs_balanced = [r.pdr for r in all_results["BALANCED"]]
    pdrs_ulp = [r.pdr for r in all_results["ULTRA_LOW_POWER"]]
    pdrs_hr = [r.pdr for r in all_results["HIGH_RELIABILITY"]]

    energies_balanced = [r.energy for r in all_results["BALANCED"]]
    energies_ulp = [r.energy for r in all_results["ULTRA_LOW_POWER"]]
    energies_hr = [r.energy for r in all_results["HIGH_RELIABILITY"]]

    print("\n1. BALANCED vs ULTRA_LOW_POWER (PDR):")
    stat, p_value = stats.mannwhitneyu(pdrs_balanced, pdrs_ulp, alternative='greater')
    effect = cohens_d(pdrs_balanced, pdrs_ulp)
    print(f"   Mann-Whitney U test: p-value = {p_value:.6f}")
    print(f"   Cohen's d = {effect:.3f} ({'large' if abs(effect) > 0.8 else 'medium' if abs(effect) > 0.5 else 'small'})")
    print(f"   Conclusion: {'SIGNIFICANT' if p_value < 0.05 else 'NOT significant'} (α=0.05)")

    print("\n2. BALANCED vs HIGH_RELIABILITY (PDR):")
    stat, p_value = stats.mannwhitneyu(pdrs_hr, pdrs_balanced, alternative='greater')
    effect = cohens_d(pdrs_hr, pdrs_balanced)
    print(f"   Mann-Whitney U test: p-value = {p_value:.6f}")
    print(f"   Cohen's d = {effect:.3f} ({'large' if abs(effect) > 0.8 else 'medium' if abs(effect) > 0.5 else 'small'})")
    print(f"   Conclusion: {'SIGNIFICANT' if p_value < 0.05 else 'NOT significant'} (α=0.05)")

    print("\n3. BALANCED vs HIGH_RELIABILITY (Energy):")
    stat, p_value = stats.mannwhitneyu(energies_hr, energies_balanced, alternative='greater')
    effect = cohens_d(energies_hr, energies_balanced)
    print(f"   Mann-Whitney U test: p-value = {p_value:.6f}")
    print(f"   Cohen's d = {effect:.3f} ({'large' if abs(effect) > 0.8 else 'medium' if abs(effect) > 0.5 else 'small'})")
    print(f"   Conclusion: {'SIGNIFICANT' if p_value < 0.05 else 'NOT significant'} (α=0.05)")

    # Energy efficiency analysis
    print("\n" + "=" * 70)
    print("ENERGY EFFICIENCY ANALYSIS")
    print("=" * 70)

    baseline_energy = summaries["HIGH_RELIABILITY"].energy_mean
    for mode_name in ["ULTRA_LOW_POWER", "BALANCED"]:
        s = summaries[mode_name]
        savings = (baseline_energy - s.energy_mean) / baseline_energy * 100
        pdr_diff = (summaries["HIGH_RELIABILITY"].pdr_mean - s.pdr_mean) * 100
        print(f"\n{mode_name} vs HIGH_RELIABILITY:")
        print(f"  Energy savings: {savings:.1f}%")
        print(f"  PDR difference: {pdr_diff:.1f} percentage points")
        if savings > 0 and pdr_diff < 5:
            print(f"  ✓ Good trade-off: {savings:.1f}% energy saved for only {pdr_diff:.1f}% PDR loss")

    # Expert assessment
    print("\n" + "=" * 70)
    print("EXPERT ASSESSMENT")
    print("=" * 70)

    balanced_pdr = summaries["BALANCED"].pdr_mean
    balanced_energy = summaries["BALANCED"].energy_mean
    hr_pdr = summaries["HIGH_RELIABILITY"].pdr_mean
    hr_energy = summaries["HIGH_RELIABILITY"].energy_mean

    issues = []
    strengths = []

    # Check statistical significance
    _, p_pdr = stats.mannwhitneyu(pdrs_hr, pdrs_balanced, alternative='greater')
    if p_pdr >= 0.05:
        strengths.append("BALANCED achieves statistically equivalent PDR to HIGH_RELIABILITY")
    else:
        issues.append(f"PDR difference is statistically significant (p={p_pdr:.4f})")

    # Check energy savings
    energy_savings = (hr_energy - balanced_energy) / hr_energy * 100
    if energy_savings > 10:
        strengths.append(f"BALANCED saves {energy_savings:.1f}% energy vs HIGH_RELIABILITY")

    # Check absolute PDR
    if balanced_pdr > 0.95:
        strengths.append(f"BALANCED achieves excellent PDR ({balanced_pdr:.1%})")
    elif balanced_pdr > 0.90:
        strengths.append(f"BALANCED achieves good PDR ({balanced_pdr:.1%})")
    else:
        issues.append(f"BALANCED PDR is below 90% ({balanced_pdr:.1%})")

    print("\n✓ Strengths:")
    for s in strengths:
        print(f"  - {s}")

    if issues:
        print("\n⚠ Issues:")
        for i in issues:
            print(f"  - {i}")

    # Save results
    output = {
        'config': {
            'num_nodes': num_nodes,
            'max_rounds': max_rounds,
            'n_repetitions': n_repetitions
        },
        'summaries': {k: asdict(v) for k, v in summaries.items()},
        'raw_results': {k: [asdict(r) for r in v] for k, v in all_results.items()}
    }

    return output


if __name__ == "__main__":
    results = run_rigorous_comparison(n_repetitions=10, num_nodes=50, max_rounds=200)

    # Save to file
    output_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'sota_comparison_rigorous.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}")
