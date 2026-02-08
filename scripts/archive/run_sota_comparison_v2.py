#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOTA Comparison Experiment v2 - Simplified Version
===================================================
Compare AERIS with classical baselines using existing implementations.
Focus on fair comparison with reproducible results.

Author: AERIS Research Team
Date: 2026-01-04
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Import protocol implementations
from benchmark_protocols import NetworkConfig
from baseline_protocols.leach_protocol import LEACHProtocol
from baseline_protocols.heed_protocol import HEEDProtocol
from baseline_protocols.pegasis_protocol import PEGASISProtocol
from teen_protocol import TEENProtocol


class SOTAComparisonExperiment:
    """SOTA Comparison Experiment Framework"""

    def __init__(self, num_nodes=100, area_size=100, num_rounds=200,
                 num_runs=30, seed=42):
        self.num_nodes = num_nodes
        self.area_size = area_size
        self.num_rounds = num_rounds
        self.num_runs = num_runs
        self.base_seed = seed
        self.results = {}

    def create_network_config(self, seed):
        """Create network configuration"""
        np.random.seed(seed)

        config = NetworkConfig(
            num_nodes=self.num_nodes,
            area_width=self.area_size,
            area_height=self.area_size,
            base_station_x=self.area_size / 2,
            base_station_y=self.area_size + 50,
            initial_energy=0.5,
            packet_size=4000,
        )
        return config

    def run_protocol(self, protocol_class, protocol_name, config, seed):
        """Run single protocol experiment"""
        np.random.seed(seed)

        try:
            protocol = protocol_class(config)

            metrics = {
                'pdr_per_round': [],
                'energy_per_round': [],
                'alive_nodes_per_round': []
            }

            total_generated = 0
            total_received = 0

            for round_num in range(self.num_rounds):
                result = protocol.run_round(round_num)

                if result:
                    generated = result.get('packets_generated', self.num_nodes)
                    received = result.get('packets_received', 0)
                    total_generated += generated
                    total_received += received

                    round_pdr = received / max(generated, 1)
                    metrics['pdr_per_round'].append(round_pdr)
                    metrics['energy_per_round'].append(result.get('energy_consumed', 0))
                    metrics['alive_nodes_per_round'].append(result.get('alive_nodes', 0))
                else:
                    break

            final_pdr = total_received / max(total_generated, 1)
            total_energy = sum(metrics['energy_per_round'])

            # Network lifetime (FND - First Node Death)
            lifetime = self.num_rounds
            for i, alive in enumerate(metrics['alive_nodes_per_round']):
                if alive < self.num_nodes:
                    lifetime = i
                    break

            return {
                'pdr': final_pdr,
                'energy': total_energy,
                'lifetime': lifetime,
                'alive_final': metrics['alive_nodes_per_round'][-1] if metrics['alive_nodes_per_round'] else 0
            }

        except Exception as e:
            print(f"  Error running {protocol_name}: {e}")
            return None

    def run_all_experiments(self):
        """Run all comparison experiments"""

        protocols = {
            'LEACH': LEACHProtocol,
            'HEED': HEEDProtocol,
            'PEGASIS': PEGASISProtocol,
            'TEEN': TEENProtocol,
        }

        print("=" * 60)
        print("SOTA Comparison Experiment")
        print(f"Nodes: {self.num_nodes}, Rounds: {self.num_rounds}, Runs: {self.num_runs}")
        print("=" * 60)

        for proto_name, proto_class in protocols.items():
            print(f"\nRunning {proto_name}...")

            pdr_values = []
            energy_values = []
            lifetime_values = []

            for run in range(self.num_runs):
                seed = self.base_seed + run
                config = self.create_network_config(seed)

                result = self.run_protocol(proto_class, proto_name, config, seed)

                if result:
                    pdr_values.append(result['pdr'])
                    energy_values.append(result['energy'])
                    lifetime_values.append(result['lifetime'])

                if (run + 1) % 10 == 0:
                    print(f"  Completed {run + 1}/{self.num_runs} runs")

            if pdr_values:
                self.results[proto_name] = {
                    'pdr': {
                        'values': pdr_values,
                        'mean': float(np.mean(pdr_values)),
                        'std': float(np.std(pdr_values)),
                        'ci95': float(1.96 * np.std(pdr_values) / np.sqrt(len(pdr_values)))
                    },
                    'energy': {
                        'values': energy_values,
                        'mean': float(np.mean(energy_values)),
                        'std': float(np.std(energy_values)),
                        'ci95': float(1.96 * np.std(energy_values) / np.sqrt(len(energy_values)))
                    },
                    'lifetime': {
                        'values': lifetime_values,
                        'mean': float(np.mean(lifetime_values)),
                        'std': float(np.std(lifetime_values)),
                        'ci95': float(1.96 * np.std(lifetime_values) / np.sqrt(len(lifetime_values)))
                    }
                }

                print(f"  PDR: {np.mean(pdr_values):.4f} +/- {np.std(pdr_values):.4f}")
                print(f"  Energy: {np.mean(energy_values):.2f} J")
                print(f"  Lifetime: {np.mean(lifetime_values):.1f} rounds")

    def compute_statistics(self, aeris_results):
        """Compute statistical significance against AERIS"""

        if not aeris_results:
            print("Warning: No AERIS results provided for comparison")
            return

        aeris_pdr = aeris_results['pdr']['values']

        print("\n" + "=" * 60)
        print("Statistical Comparison (vs AERIS)")
        print("=" * 60)

        comparisons = []

        for proto_name, data in self.results.items():
            proto_pdr = data['pdr']['values']

            # Welch's t-test
            t_stat, p_value = stats.ttest_ind(aeris_pdr, proto_pdr, equal_var=False)

            # Effect size (Cohen's d)
            pooled_std = np.sqrt((np.var(aeris_pdr) + np.var(proto_pdr)) / 2)
            cohens_d = (np.mean(aeris_pdr) - np.mean(proto_pdr)) / pooled_std if pooled_std > 0 else 0

            # PDR difference in percentage points
            delta_pdr = (np.mean(aeris_pdr) - np.mean(proto_pdr)) * 100

            comparisons.append({
                'protocol': proto_name,
                'aeris_pdr': float(np.mean(aeris_pdr)),
                'baseline_pdr': float(np.mean(proto_pdr)),
                'delta_pdr_pp': float(delta_pdr),
                'p_value': float(p_value),
                'cohens_d': float(cohens_d),
                't_statistic': float(t_stat),
                'significant': p_value < 0.05
            })

            sig_marker = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
            print(f"{proto_name:15s}: ΔPDR={delta_pdr:+6.2f}pp, p={p_value:.4f} {sig_marker}, d={cohens_d:.2f}")

        # Holm-Bonferroni correction
        comparisons.sort(key=lambda x: x['p_value'])
        n_comparisons = len(comparisons)

        for i, comp in enumerate(comparisons):
            adjusted_alpha = 0.05 / (n_comparisons - i)
            comp['holm_significant'] = comp['p_value'] < adjusted_alpha

        self.results['_statistics'] = {
            'comparisons': comparisons,
            'baseline': 'AERIS',
            'aeris_pdr_mean': float(np.mean(aeris_pdr)),
            'aeris_pdr_ci95': float(1.96 * np.std(aeris_pdr) / np.sqrt(len(aeris_pdr)))
        }

    def save_results(self, output_dir):
        """Save results to JSON"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_path / f'sota_comparison_{timestamp}.json'

        # Convert numpy types to Python native types
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(v) for v in obj]
            return obj

        serializable_results = convert_to_serializable(self.results)

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {results_file}")

        self.print_summary_table()

        return str(results_file)

    def print_summary_table(self):
        """Print results summary table"""

        print("\n" + "=" * 80)
        print("RESULTS SUMMARY TABLE")
        print("=" * 80)
        print(f"{'Protocol':<15} {'PDR':>10} {'+/-CI95':>10} {'Energy(J)':>12} {'Lifetime':>10}")
        print("-" * 80)

        for proto_name, data in self.results.items():
            if proto_name.startswith('_'):
                continue

            pdr = data['pdr']['mean']
            pdr_ci = data['pdr']['ci95']
            energy = data['energy']['mean']
            lifetime = data['lifetime']['mean']

            print(f"{proto_name:<15} {pdr:>10.4f} {pdr_ci:>10.4f} {energy:>12.2f} {lifetime:>10.1f}")

        print("=" * 80)


def load_aeris_results(results_dir):
    """Load existing AERIS results from scale experiments"""
    scale_file = Path(results_dir) / 'scale_experiments.json'

    if scale_file.exists():
        with open(scale_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract N100 AERIS results
        if 'N100_AERIS' in data:
            return data['N100_AERIS']

    return None


def main():
    """Main function"""

    results_dir = Path(__file__).parent.parent / 'results' / 'experiments_20250102'

    # Load existing AERIS results
    aeris_results = load_aeris_results(results_dir)

    if aeris_results:
        print("Loaded existing AERIS results:")
        print(f"  PDR: {aeris_results['pdr']['mean']:.4f} +/- {aeris_results['pdr']['ci95']:.4f}")
        print(f"  Energy: {aeris_results['energy']['mean']:.2f} J")
        print(f"  Lifetime: {aeris_results['lifetime']['mean']:.1f} rounds")

    # Run baseline experiments
    experiment = SOTAComparisonExperiment(
        num_nodes=100,
        area_size=100,
        num_rounds=200,
        num_runs=30,
        seed=42
    )

    experiment.run_all_experiments()

    # Compute statistics against AERIS
    if aeris_results:
        experiment.compute_statistics(aeris_results)

    # Save results
    output_dir = results_dir / 'sota_comparison'
    experiment.save_results(output_dir)

    print("\n" + "=" * 60)
    print("SOTA Comparison Complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
