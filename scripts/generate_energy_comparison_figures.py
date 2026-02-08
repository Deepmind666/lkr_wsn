#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Energy Efficiency Comparison Figures

This script creates detailed energy consumption comparison charts
highlighting AERIS protocol efficiency advantages.

Author: AERIS Research Team
Date: 2026-01-12
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

# Publication-quality settings
plt.rcParams.update({
    'font.size': 10,
    'font.family': 'serif',
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

# Color scheme
COLORS = {
    'AERIS': '#2E86AB',      # Blue
    'LEACH': '#A23B72',      # Magenta
    'PEGASIS': '#F18F01',    # Orange
    'HEED': '#C73E1D',       # Red
}

MARKERS = {
    'AERIS': 'o',
    'LEACH': 's',
    'PEGASIS': '^',
    'HEED': 'd',
}


def load_results():
    """Load experiment results"""
    results_path = os.path.join(os.path.dirname(__file__), '..', 'results',
                                'comprehensive_dynamic_experiments.json')
    with open(results_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_energy_churn_comparison(results, output_dir):
    """Generate energy consumption vs churn rate figure"""
    data = results.get('churn_experiment', {})
    if not data:
        return

    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    churn_rates = [0, 5, 10, 15, 20, 25, 30]

    fig, ax = plt.subplots(figsize=(8, 5))

    for protocol in protocols:
        if protocol not in data:
            continue
        energies = []
        for rate in churn_rates:
            key = f"churn_{rate}pct"
            if key in data[protocol]:
                energies.append(data[protocol][key]['energy_mean'])
            else:
                energies.append(np.nan)

        ax.plot(churn_rates, energies,
                marker=MARKERS[protocol],
                color=COLORS[protocol],
                label=protocol,
                linewidth=2,
                markersize=8)

    ax.set_xlabel('Node Churn Rate (%)')
    ax.set_ylabel('Total Energy Consumption (mJ)')
    ax.set_title('Energy Efficiency Under Node Churn')
    ax.legend(loc='upper right')
    ax.set_xlim(-1, 31)

    # Add efficiency annotation
    aeris_0 = data.get('AERIS', {}).get('churn_0pct', {}).get('energy_mean', 0)
    leach_0 = data.get('LEACH', {}).get('churn_0pct', {}).get('energy_mean', 0)
    if aeris_0 > 0 and leach_0 > 0:
        improvement = (leach_0 - aeris_0) / leach_0 * 100
        ax.annotate(f'AERIS: {improvement:.1f}% more efficient than LEACH',
                    xy=(15, aeris_0 - 5), fontsize=9, style='italic')

    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'fig_energy_vs_churn.{fmt}')
        fig.savefig(filepath, format=fmt)
    plt.close(fig)
    print(f"Saved: fig_energy_vs_churn.{{pdf,svg,png}}")


def generate_scalability_energy_comparison(results, output_dir):
    """Generate energy consumption vs network size"""
    data = results.get('scalability_experiment', {})
    if not data:
        return

    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    node_counts = [50, 100, 150, 200, 250, 300, 400, 500]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Left: Energy consumption
    ax = axes[0]
    for protocol in protocols:
        if protocol not in data:
            continue
        energies = []
        for n in node_counts:
            key = f"nodes_{n}"
            if key in data[protocol]:
                energies.append(data[protocol][key]['energy_mean'])
            else:
                energies.append(np.nan)

        ax.plot(node_counts, energies,
                marker=MARKERS[protocol],
                color=COLORS[protocol],
                label=protocol,
                linewidth=2,
                markersize=7)

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Total Energy Consumption (mJ)')
    ax.set_title('(a) Energy Consumption vs Network Size')
    ax.legend(loc='upper left')

    # Right: PDR comparison
    ax = axes[1]
    for protocol in protocols:
        if protocol not in data:
            continue
        pdrs = []
        for n in node_counts:
            key = f"nodes_{n}"
            if key in data[protocol]:
                pdrs.append(data[protocol][key]['pdr_mean'] * 100)
            else:
                pdrs.append(np.nan)

        ax.plot(node_counts, pdrs,
                marker=MARKERS[protocol],
                color=COLORS[protocol],
                label=protocol,
                linewidth=2,
                markersize=7)

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Packet Delivery Ratio (%)')
    ax.set_title('(b) PDR vs Network Size')
    ax.set_ylim(98, 100.5)
    ax.legend(loc='lower left')

    # Add annotation for LEACH degradation
    ax.annotate('LEACH degrades\nat scale',
                xy=(450, 98.8), xytext=(350, 99.3),
                arrowprops=dict(arrowstyle='->', color='gray'),
                fontsize=8, style='italic')

    plt.tight_layout()

    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'fig_scalability_combined.{fmt}')
        fig.savefig(filepath, format=fmt)
    plt.close(fig)
    print(f"Saved: fig_scalability_combined.{{pdf,svg,png}}")


def generate_energy_per_node_comparison(results, output_dir):
    """Generate energy per node efficiency figure"""
    data = results.get('scalability_experiment', {})
    if not data:
        return

    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    node_counts = [50, 100, 150, 200, 250, 300, 400, 500]

    fig, ax = plt.subplots(figsize=(8, 5))

    bar_width = 0.2
    x = np.arange(len(node_counts))

    for i, protocol in enumerate(protocols):
        if protocol not in data:
            continue
        energy_per_node = []
        for n in node_counts:
            key = f"nodes_{n}"
            if key in data[protocol]:
                total_energy = data[protocol][key]['energy_mean']
                energy_per_node.append(total_energy / n)
            else:
                energy_per_node.append(np.nan)

        ax.bar(x + i * bar_width, energy_per_node,
               width=bar_width,
               color=COLORS[protocol],
               label=protocol,
               alpha=0.85)

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Energy per Node (mJ)')
    ax.set_title('Energy Efficiency per Node at Different Scales')
    ax.set_xticks(x + bar_width * 1.5)
    ax.set_xticklabels(node_counts)
    ax.legend(loc='upper right')

    plt.tight_layout()

    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'fig_energy_per_node.{fmt}')
        fig.savefig(filepath, format=fmt)
    plt.close(fig)
    print(f"Saved: fig_energy_per_node.{{pdf,svg,png}}")


def generate_summary_heatmap(results, output_dir):
    """Generate summary heatmap of all experiments"""
    fig, ax = plt.subplots(figsize=(10, 6))

    metrics = [
        ('Churn 0%', 'churn_experiment', 'churn_0pct', 'pdr_mean'),
        ('Churn 20%', 'churn_experiment', 'churn_20pct', 'pdr_mean'),
        ('Churn 30%', 'churn_experiment', 'churn_30pct', 'pdr_mean'),
        ('Regional 30m', 'regional_failure_experiment', 'radius_30m', 'pdr_mean'),
        ('Regional 50m', 'regional_failure_experiment', 'radius_50m', 'pdr_mean'),
        ('Scale 300', 'scalability_experiment', 'nodes_300', 'pdr_mean'),
        ('Scale 500', 'scalability_experiment', 'nodes_500', 'pdr_mean'),
        ('Duty 60%', 'intermittent_experiment', 'duty_60pct', 'pdr_mean'),
        ('Duty 50%', 'intermittent_experiment', 'duty_50pct', 'pdr_mean'),
    ]

    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']

    data_matrix = []
    for protocol in protocols:
        row = []
        for _, exp_key, cond_key, metric in metrics:
            if exp_key in results and protocol in results[exp_key]:
                if cond_key in results[exp_key][protocol]:
                    val = results[exp_key][protocol][cond_key].get(metric, 0) * 100
                    row.append(val)
                else:
                    row.append(np.nan)
            else:
                row.append(np.nan)
        data_matrix.append(row)

    data_matrix = np.array(data_matrix)

    im = ax.imshow(data_matrix, cmap='RdYlGn', aspect='auto', vmin=98, vmax=100.1)

    ax.set_xticks(np.arange(len(metrics)))
    ax.set_yticks(np.arange(len(protocols)))
    ax.set_xticklabels([m[0] for m in metrics], rotation=45, ha='right')
    ax.set_yticklabels(protocols)

    # Add text annotations
    for i in range(len(protocols)):
        for j in range(len(metrics)):
            val = data_matrix[i, j]
            if not np.isnan(val):
                color = 'white' if val < 99.5 else 'black'
                ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                       color=color, fontsize=8)

    ax.set_title('Protocol PDR Performance Summary (%)')
    cbar = plt.colorbar(im, ax=ax, label='PDR (%)')

    plt.tight_layout()

    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'fig_summary_heatmap.{fmt}')
        fig.savefig(filepath, format=fmt)
    plt.close(fig)
    print(f"Saved: fig_summary_heatmap.{{pdf,svg,png}}")


def main():
    print("=" * 60)
    print("GENERATING ENERGY COMPARISON FIGURES")
    print("=" * 60)

    results = load_results()

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'publication_figures')
    os.makedirs(output_dir, exist_ok=True)

    generate_energy_churn_comparison(results, output_dir)
    generate_scalability_energy_comparison(results, output_dir)
    generate_energy_per_node_comparison(results, output_dir)
    generate_summary_heatmap(results, output_dir)

    print("=" * 60)
    print("ENERGY COMPARISON FIGURES COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
