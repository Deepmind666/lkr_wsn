#!/usr/bin/env python3
"""
Generate publication-quality scalability comparison figure.

This script creates Figure 1: PDR comparison across network scales
for AERIS, LEACH, PEGASIS, and HEED protocols.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict

# Publication-quality settings
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif', 'Times'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
    'lines.linewidth': 1.5,
    'lines.markersize': 7,
})

def load_data(json_path):
    """Load experiment results from JSON file."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def aggregate_pdr_by_scale(data):
    """
    Aggregate PDR values by protocol and node count.
    Returns dict: {protocol: {num_nodes: [pdr_values]}}
    """
    results = defaultdict(lambda: defaultdict(list))

    for run in data['runs']:
        if run.get('success', True):
            protocol = run['protocol']
            num_nodes = run['num_nodes']
            pdr = run['metrics'].get('pdr_end2end', 0)
            results[protocol][num_nodes].append(pdr)

    return results

def compute_statistics(pdr_data):
    """
    Compute mean and std for each protocol at each scale.
    Returns dict: {protocol: {'scales': [], 'means': [], 'stds': []}}
    """
    stats = {}
    scales = sorted(list(next(iter(pdr_data.values())).keys()))

    for protocol, scale_data in pdr_data.items():
        means = []
        stds = []
        for scale in scales:
            values = scale_data[scale]
            means.append(np.mean(values) * 100)  # Convert to percentage
            stds.append(np.std(values) * 100)
        stats[protocol] = {
            'scales': scales,
            'means': means,
            'stds': stds
        }

    return stats

def create_figure(stats, output_path):
    """Create publication-quality scalability comparison figure."""

    # Figure size for single-column journal figure
    fig, ax = plt.subplots(figsize=(5.5, 4))

    # Color scheme (colorblind-friendly)
    colors = {
        'AERIS': '#2ca02c',    # Green
        'LEACH': '#1f77b4',    # Blue
        'PEGASIS': '#ff7f0e',  # Orange
        'HEED': '#d62728',     # Red
    }

    # Marker styles
    markers = {
        'AERIS': 'o',
        'LEACH': 's',
        'PEGASIS': '^',
        'HEED': 'D',
    }

    # Line styles
    linestyles = {
        'AERIS': '-',
        'LEACH': '--',
        'PEGASIS': '-.',
        'HEED': ':',
    }

    # Plot order (AERIS first for emphasis)
    plot_order = ['AERIS', 'PEGASIS', 'LEACH', 'HEED']

    for protocol in plot_order:
        if protocol not in stats:
            continue
        data = stats[protocol]
        scales = data['scales']
        means = data['means']
        stds = data['stds']

        ax.errorbar(
            scales, means, yerr=stds,
            label=protocol,
            color=colors[protocol],
            marker=markers[protocol],
            linestyle=linestyles[protocol],
            capsize=3,
            capthick=1,
            elinewidth=1,
            markerfacecolor=colors[protocol],
            markeredgecolor='white',
            markeredgewidth=0.5,
        )

    # Axis configuration
    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Packet Delivery Ratio (%)')
    ax.set_xlim(50, 550)
    ax.set_ylim(20, 105)

    # X-axis ticks
    ax.set_xticks([100, 200, 300, 500])
    ax.set_xticklabels(['100', '200', '300', '500'])

    # Y-axis ticks
    ax.set_yticks([20, 40, 60, 80, 100])

    # Grid
    ax.grid(True, linestyle='--', alpha=0.4, linewidth=0.5)
    ax.set_axisbelow(True)

    # Legend
    ax.legend(loc='lower left', framealpha=0.95, edgecolor='gray')

    # Add annotation for AERIS performance
    ax.annotate(
        'AERIS maintains 100% PDR\nacross all scales',
        xy=(400, 100), xytext=(300, 85),
        fontsize=8,
        ha='center',
        arrowprops=dict(arrowstyle='->', color='gray', lw=0.8),
    )

    # Tight layout
    plt.tight_layout()

    # Save figure
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as PDF (vector format for publication)
    plt.savefig(output_path, format='pdf', bbox_inches='tight', pad_inches=0.02)
    print(f"Figure saved to: {output_path}")

    # Also save as PNG for quick preview
    png_path = output_path.with_suffix('.png')
    plt.savefig(png_path, format='png', dpi=300, bbox_inches='tight', pad_inches=0.02)
    print(f"PNG preview saved to: {png_path}")

    plt.close()

def print_summary(stats):
    """Print summary of PDR values for verification."""
    print("\n" + "="*60)
    print("PDR Summary (Mean +/- Std)")
    print("="*60)

    scales = stats['AERIS']['scales']
    print(f"{'Protocol':<10}", end='')
    for scale in scales:
        print(f"{scale:>12} nodes", end='')
    print()
    print("-"*60)

    for protocol in ['AERIS', 'LEACH', 'PEGASIS', 'HEED']:
        if protocol not in stats:
            continue
        print(f"{protocol:<10}", end='')
        for i, scale in enumerate(scales):
            mean = stats[protocol]['means'][i]
            std = stats[protocol]['stds'][i]
            print(f"{mean:>8.1f}+/-{std:<4.1f}", end='')
        print()
    print("="*60)

def main():
    # Paths
    data_path = Path(r"c:\AERIS-WSN-Protocol\results\large_scale_scalability_verified.json")
    output_path = Path(r"c:\AERIS-WSN-Protocol\for_submission\figures\figure1_scale_comparison.pdf")

    print(f"Loading data from: {data_path}")

    # Load and process data
    data = load_data(data_path)
    pdr_data = aggregate_pdr_by_scale(data)
    stats = compute_statistics(pdr_data)

    # Print summary for verification
    print_summary(stats)

    # Create figure
    create_figure(stats, output_path)

    print("\nFigure generation complete!")

if __name__ == "__main__":
    main()
