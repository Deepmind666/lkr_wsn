#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Advanced Experiment Figures for AERIS Paper

Creates publication-quality figures for:
1. Dynamic adaptability comparison (node churn)
2. Regional failure resilience
3. Scalability analysis
4. Intermittent connectivity performance
5. Multi-dimensional radar chart
6. Pareto frontier with new data

Author: AERIS Research Team
Date: 2026-01-12
"""

import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import matplotlib.patches as mpatches

# Publication-quality style
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'legend.fontsize': 9,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
})

# Color scheme for protocols
PROTOCOL_COLORS = {
    'AERIS': '#2E86AB',
    'AERIS_ENERGY': '#1A5276',
    'LEACH': '#A23B72',
    'PEGASIS': '#F18F01',
    'HEED': '#C73E1D',
    'TEEN': '#6C3483'
}

PROTOCOL_MARKERS = {
    'AERIS': 's',
    'AERIS_ENERGY': 'D',
    'LEACH': 'o',
    'PEGASIS': '^',
    'HEED': 'v',
    'TEEN': 'p'
}


def load_results(results_path):
    """Load experiment results from JSON file"""
    if os.path.exists(results_path):
        with open(results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def plot_churn_comparison(results, output_dir):
    """Plot PDR vs node churn rate comparison"""
    if not results or 'churn_experiment' not in results:
        print("No churn experiment data found")
        return

    data = results['churn_experiment']
    protocols = [p for p in data.keys() if p != 'config']

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Extract churn rates
    churn_rates = data['config']['churn_rates']
    x_labels = [f"{int(r*100)}%" for r in churn_rates]

    # Plot PDR
    ax1 = axes[0]
    for protocol in protocols:
        if protocol in data:
            pdrs = []
            stds = []
            for rate in churn_rates:
                key = f"churn_{int(rate*100)}pct"
                if key in data[protocol]:
                    pdrs.append(data[protocol][key]['pdr_mean'])
                    stds.append(data[protocol][key].get('pdr_std', 0))
                else:
                    pdrs.append(np.nan)
                    stds.append(0)

            ax1.errorbar(range(len(churn_rates)), pdrs,
                        yerr=stds, label=protocol,
                        color=PROTOCOL_COLORS.get(protocol, 'gray'),
                        marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                        linewidth=2, markersize=8, capsize=3)

    ax1.set_xlabel('Node Churn Rate')
    ax1.set_ylabel('Packet Delivery Ratio (PDR)')
    ax1.set_title('(a) PDR Degradation Under Node Churn')
    ax1.set_xticks(range(len(churn_rates)))
    ax1.set_xticklabels(x_labels)
    ax1.legend(loc='lower left')
    ax1.set_ylim(0, 1.05)
    ax1.grid(True, alpha=0.3)

    # Plot energy consumption
    ax2 = axes[1]
    for protocol in protocols:
        if protocol in data:
            energies = []
            for rate in churn_rates:
                key = f"churn_{int(rate*100)}pct"
                if key in data[protocol]:
                    energies.append(data[protocol][key]['energy_mean'])
                else:
                    energies.append(np.nan)

            ax2.plot(range(len(churn_rates)), energies,
                    label=protocol,
                    color=PROTOCOL_COLORS.get(protocol, 'gray'),
                    marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                    linewidth=2, markersize=8)

    ax2.set_xlabel('Node Churn Rate')
    ax2.set_ylabel('Total Energy Consumed (J)')
    ax2.set_title('(b) Energy Consumption Under Node Churn')
    ax2.set_xticks(range(len(churn_rates)))
    ax2.set_xticklabels(x_labels)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'fig_churn_comparison.{fmt}')
        plt.savefig(filepath, format=fmt, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: fig_churn_comparison.{{pdf,svg,png}}")


def plot_regional_failure(results, output_dir):
    """Plot regional failure resilience"""
    if not results or 'regional_failure_experiment' not in results:
        print("No regional failure experiment data found")
        return

    data = results['regional_failure_experiment']
    protocols = [p for p in data.keys() if p != 'config']

    fig, ax = plt.subplots(figsize=(8, 6))

    failure_radii = data['config']['failure_radii']

    for protocol in protocols:
        if protocol in data:
            pdrs = []
            failure_rates = []
            for radius in failure_radii:
                key = f"radius_{int(radius)}m"
                if key in data[protocol]:
                    pdrs.append(data[protocol][key]['pdr_mean'])
                    failure_rates.append(data[protocol][key]['failure_rate_mean'])
                else:
                    pdrs.append(np.nan)
                    failure_rates.append(0)

            ax.plot(failure_radii, pdrs,
                   label=protocol,
                   color=PROTOCOL_COLORS.get(protocol, 'gray'),
                   marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                   linewidth=2, markersize=8)

    ax.set_xlabel('Failure Region Radius (m)')
    ax.set_ylabel('Packet Delivery Ratio (PDR)')
    ax.set_title('Protocol Resilience to Regional Failures\n(Failure centered at network midpoint)')
    ax.legend(loc='lower left')
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'fig_regional_failure.{fmt}')
        plt.savefig(filepath, format=fmt, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: fig_regional_failure.{{pdf,svg,png}}")


def plot_scalability(results, output_dir):
    """Plot scalability analysis"""
    if not results or 'scalability_experiment' not in results:
        print("No scalability experiment data found")
        return

    data = results['scalability_experiment']
    protocols = [p for p in data.keys() if p != 'config']

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    node_counts = data['config']['node_counts']

    # Plot PDR vs node count
    ax1 = axes[0]
    for protocol in protocols:
        if protocol in data:
            pdrs = []
            stds = []
            for n in node_counts:
                key = f"nodes_{n}"
                if key in data[protocol]:
                    pdrs.append(data[protocol][key]['pdr_mean'])
                    stds.append(data[protocol][key].get('pdr_std', 0))
                else:
                    pdrs.append(np.nan)
                    stds.append(0)

            ax1.errorbar(node_counts, pdrs, yerr=stds,
                        label=protocol,
                        color=PROTOCOL_COLORS.get(protocol, 'gray'),
                        marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                        linewidth=2, markersize=6, capsize=3)

    ax1.set_xlabel('Number of Nodes')
    ax1.set_ylabel('Packet Delivery Ratio (PDR)')
    ax1.set_title('(a) PDR vs Network Size')
    ax1.legend(loc='lower left')
    ax1.set_ylim(0, 1.05)
    ax1.grid(True, alpha=0.3)

    # Plot energy vs node count
    ax2 = axes[1]
    for protocol in protocols:
        if protocol in data:
            energies = []
            for n in node_counts:
                key = f"nodes_{n}"
                if key in data[protocol]:
                    energies.append(data[protocol][key]['energy_mean'])
                else:
                    energies.append(np.nan)

            ax2.plot(node_counts, energies,
                    label=protocol,
                    color=PROTOCOL_COLORS.get(protocol, 'gray'),
                    marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                    linewidth=2, markersize=6)

    ax2.set_xlabel('Number of Nodes')
    ax2.set_ylabel('Total Energy Consumed (J)')
    ax2.set_title('(b) Energy Consumption vs Network Size')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)

    # Plot execution time vs node count (scalability)
    ax3 = axes[2]
    for protocol in protocols:
        if protocol in data:
            times = []
            for n in node_counts:
                key = f"nodes_{n}"
                if key in data[protocol]:
                    times.append(data[protocol][key].get('exec_time_mean', 0))
                else:
                    times.append(np.nan)

            ax3.plot(node_counts, times,
                    label=protocol,
                    color=PROTOCOL_COLORS.get(protocol, 'gray'),
                    marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                    linewidth=2, markersize=6)

    ax3.set_xlabel('Number of Nodes')
    ax3.set_ylabel('Execution Time (s)')
    ax3.set_title('(c) Computational Complexity')
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()

    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'fig_scalability_analysis.{fmt}')
        plt.savefig(filepath, format=fmt, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: fig_scalability_analysis.{{pdf,svg,png}}")


def plot_intermittent_connectivity(results, output_dir):
    """Plot intermittent connectivity performance"""
    if not results or 'intermittent_experiment' not in results:
        print("No intermittent connectivity experiment data found")
        return

    data = results['intermittent_experiment']
    protocols = [p for p in data.keys() if p != 'config']

    fig, ax = plt.subplots(figsize=(8, 6))

    duty_cycles = data['config']['duty_cycles']
    x_labels = [f"{int(d*100)}%" for d in duty_cycles]

    for protocol in protocols:
        if protocol in data:
            pdrs = []
            stds = []
            for duty in duty_cycles:
                key = f"duty_{int(duty*100)}pct"
                if key in data[protocol]:
                    pdrs.append(data[protocol][key]['pdr_mean'])
                    stds.append(data[protocol][key].get('pdr_std', 0))
                else:
                    pdrs.append(np.nan)
                    stds.append(0)

            ax.errorbar(range(len(duty_cycles)), pdrs, yerr=stds,
                       label=protocol,
                       color=PROTOCOL_COLORS.get(protocol, 'gray'),
                       marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                       linewidth=2, markersize=8, capsize=3)

    ax.set_xlabel('Active Node Ratio (Duty Cycle)')
    ax.set_ylabel('Packet Delivery Ratio (PDR)')
    ax.set_title('Protocol Performance Under Intermittent Connectivity\n(Simulating Periodic Sleep/Wake Cycles)')
    ax.set_xticks(range(len(duty_cycles)))
    ax.set_xticklabels(x_labels)
    ax.legend(loc='lower left')
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'fig_intermittent_connectivity.{fmt}')
        plt.savefig(filepath, format=fmt, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: fig_intermittent_connectivity.{{pdf,svg,png}}")


def plot_comprehensive_4panel(results, output_dir):
    """Create a comprehensive 4-panel figure for the paper"""
    if not results:
        print("No results to plot")
        return

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Panel (a): Churn comparison
    ax1 = axes[0, 0]
    if 'churn_experiment' in results:
        data = results['churn_experiment']
        protocols = [p for p in data.keys() if p != 'config']
        churn_rates = data['config']['churn_rates']

        for protocol in protocols:
            if protocol in data:
                pdrs = []
                for rate in churn_rates:
                    key = f"churn_{int(rate*100)}pct"
                    if key in data[protocol]:
                        pdrs.append(data[protocol][key]['pdr_mean'])
                    else:
                        pdrs.append(np.nan)

                ax1.plot([r*100 for r in churn_rates], pdrs,
                        label=protocol,
                        color=PROTOCOL_COLORS.get(protocol, 'gray'),
                        marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                        linewidth=2, markersize=6)

    ax1.set_xlabel('Node Churn Rate (%)')
    ax1.set_ylabel('PDR')
    ax1.set_title('(a) Dynamic Adaptability: Node Churn')
    ax1.legend(loc='lower left', fontsize=8)
    ax1.set_ylim(0, 1.05)
    ax1.grid(True, alpha=0.3)

    # Panel (b): Regional failure
    ax2 = axes[0, 1]
    if 'regional_failure_experiment' in results:
        data = results['regional_failure_experiment']
        protocols = [p for p in data.keys() if p != 'config']
        failure_radii = data['config']['failure_radii']

        for protocol in protocols:
            if protocol in data:
                pdrs = []
                for radius in failure_radii:
                    key = f"radius_{int(radius)}m"
                    if key in data[protocol]:
                        pdrs.append(data[protocol][key]['pdr_mean'])
                    else:
                        pdrs.append(np.nan)

                ax2.plot(failure_radii, pdrs,
                        label=protocol,
                        color=PROTOCOL_COLORS.get(protocol, 'gray'),
                        marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                        linewidth=2, markersize=6)

    ax2.set_xlabel('Failure Radius (m)')
    ax2.set_ylabel('PDR')
    ax2.set_title('(b) Failure Isolation: Regional Failures')
    ax2.legend(loc='lower left', fontsize=8)
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, alpha=0.3)

    # Panel (c): Scalability
    ax3 = axes[1, 0]
    if 'scalability_experiment' in results:
        data = results['scalability_experiment']
        protocols = [p for p in data.keys() if p != 'config']
        node_counts = data['config']['node_counts']

        for protocol in protocols:
            if protocol in data:
                pdrs = []
                for n in node_counts:
                    key = f"nodes_{n}"
                    if key in data[protocol]:
                        pdrs.append(data[protocol][key]['pdr_mean'])
                    else:
                        pdrs.append(np.nan)

                ax3.plot(node_counts, pdrs,
                        label=protocol,
                        color=PROTOCOL_COLORS.get(protocol, 'gray'),
                        marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                        linewidth=2, markersize=6)

    ax3.set_xlabel('Number of Nodes')
    ax3.set_ylabel('PDR')
    ax3.set_title('(c) Scalability Analysis')
    ax3.legend(loc='lower left', fontsize=8)
    ax3.set_ylim(0, 1.05)
    ax3.grid(True, alpha=0.3)

    # Panel (d): Intermittent connectivity
    ax4 = axes[1, 1]
    if 'intermittent_experiment' in results:
        data = results['intermittent_experiment']
        protocols = [p for p in data.keys() if p != 'config']
        duty_cycles = data['config']['duty_cycles']

        for protocol in protocols:
            if protocol in data:
                pdrs = []
                for duty in duty_cycles:
                    key = f"duty_{int(duty*100)}pct"
                    if key in data[protocol]:
                        pdrs.append(data[protocol][key]['pdr_mean'])
                    else:
                        pdrs.append(np.nan)

                ax4.plot([d*100 for d in duty_cycles], pdrs,
                        label=protocol,
                        color=PROTOCOL_COLORS.get(protocol, 'gray'),
                        marker=PROTOCOL_MARKERS.get(protocol, 'o'),
                        linewidth=2, markersize=6)

    ax4.set_xlabel('Duty Cycle (%)')
    ax4.set_ylabel('PDR')
    ax4.set_title('(d) Intermittent Connectivity')
    ax4.legend(loc='lower left', fontsize=8)
    ax4.set_ylim(0, 1.05)
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'fig_comprehensive_4panel.{fmt}')
        plt.savefig(filepath, format=fmt, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: fig_comprehensive_4panel.{{pdf,svg,png}}")


def main():
    """Main function to generate all figures"""
    print("=" * 60)
    print("GENERATING ADVANCED EXPERIMENT FIGURES")
    print("=" * 60)

    # Load results
    results_path = os.path.join(os.path.dirname(__file__), '..', 'results',
                                'comprehensive_dynamic_experiments.json')

    results = load_results(results_path)

    if results is None:
        print(f"WARNING: Results file not found at {results_path}")
        print("Please run run_comprehensive_dynamic_experiments.py first")
        return

    # Output directories
    output_dirs = [
        os.path.join(os.path.dirname(__file__), '..', 'results', 'publication_figures'),
        os.path.join(os.path.dirname(__file__), '..', 'for_submission', 'figures')
    ]

    for output_dir in output_dirs:
        os.makedirs(output_dir, exist_ok=True)
        print(f"\nGenerating figures to: {output_dir}")

        # Generate individual figures
        plot_churn_comparison(results, output_dir)
        plot_regional_failure(results, output_dir)
        plot_scalability(results, output_dir)
        plot_intermittent_connectivity(results, output_dir)

        # Generate comprehensive 4-panel figure
        plot_comprehensive_4panel(results, output_dir)

    print("\n" + "=" * 60)
    print("FIGURE GENERATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
