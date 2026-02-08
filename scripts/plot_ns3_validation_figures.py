#!/usr/bin/env python3
"""
NS-3 Cross-Validation Publication Figures
Generates high-quality figures for AERIS paper

Author: AERIS Project
Date: 2026-01-19
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# Publication-quality settings
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
    'lines.linewidth': 1.5,
    'lines.markersize': 6,
})

# Color scheme (colorblind-friendly)
COLORS = {
    'AERIS': '#2166AC',      # Blue
    'LEACH': '#B2182B',      # Red
    'AERIS-FULL': '#2166AC',
    'AERIS-noCAS': '#67A9CF',
    'AERIS-noFair': '#D1E5F0',
    'AERIS-noGW': '#FDDBC7',
}

HATCHES = {
    'AERIS': '',
    'LEACH': '///',
    'AERIS-FULL': '',
    'AERIS-noCAS': '...',
    'AERIS-noFair': '\\\\\\',
    'AERIS-noGW': 'xxx',
}


def load_results():
    """Load NS-3 validation results"""
    results_path = Path(__file__).parent.parent / 'ns3_validation' / 'results' / 'ns3_ablation_results.json'
    with open(results_path, 'r') as f:
        return json.load(f)


def compute_statistics(data, protocol, metric='pdr'):
    """Compute mean and std for a protocol across seeds"""
    values = [d[metric] for d in data if d['protocol'] == protocol]
    if not values:
        return 0, 0
    return np.mean(values), np.std(values)


def plot_scalability_comparison(data, output_dir):
    """
    Figure 1: Scalability Comparison (PDR vs Network Size)
    """
    fig, ax = plt.subplots(figsize=(4.5, 3.5))

    node_counts = [50, 100, 200]

    # Compute statistics for each protocol and node count
    aeris_means, aeris_stds = [], []
    leach_means, leach_stds = [], []

    for nodes in node_counts:
        subset = [d for d in data if d['num_nodes'] == nodes]

        aeris_vals = [d['pdr'] * 100 for d in subset if d['protocol'] == 'AERIS']
        leach_vals = [d['pdr'] * 100 for d in subset if d['protocol'] == 'LEACH']

        aeris_means.append(np.mean(aeris_vals))
        aeris_stds.append(np.std(aeris_vals))
        leach_means.append(np.mean(leach_vals))
        leach_stds.append(np.std(leach_vals))

    x = np.arange(len(node_counts))
    width = 0.35

    # Bar chart with error bars
    bars1 = ax.bar(x - width/2, aeris_means, width, yerr=aeris_stds,
                   label='AERIS', color=COLORS['AERIS'],
                   edgecolor='black', linewidth=0.8,
                   capsize=3, error_kw={'linewidth': 1})

    bars2 = ax.bar(x + width/2, leach_means, width, yerr=leach_stds,
                   label='LEACH', color=COLORS['LEACH'], hatch='///',
                   edgecolor='black', linewidth=0.8,
                   capsize=3, error_kw={'linewidth': 1})

    # Add improvement annotations
    for i, (a, l) in enumerate(zip(aeris_means, leach_means)):
        improvement = (a - l) / l * 100
        ax.annotate(f'+{improvement:.1f}%',
                   xy=(x[i], a + aeris_stds[i] + 1),
                   ha='center', va='bottom', fontsize=8,
                   fontweight='bold', color=COLORS['AERIS'])

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Packet Delivery Ratio (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(node_counts)
    ax.set_ylim([70, 105])
    ax.legend(loc='lower left', framealpha=0.9)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Add subtle background
    ax.set_facecolor('#FAFAFA')

    plt.tight_layout()

    # Save in multiple formats
    for fmt in ['pdf', 'svg', 'png']:
        fig.savefig(output_dir / f'fig_ns3_scalability.{fmt}',
                   format=fmt, bbox_inches='tight')

    plt.close()
    print(f"  ✓ Scalability comparison saved")


def plot_ablation_study(data, output_dir):
    """
    Figure 2: Ablation Study Bar Chart
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.5))

    # Extract ablation data
    protocols = ['AERIS-FULL', 'AERIS-noCAS', 'AERIS-noFair', 'AERIS-noGW', 'LEACH']
    labels = ['Full\nAERIS', 'w/o\nCAS', 'w/o\nFairness', 'w/o\nGateway', 'LEACH\n(baseline)']

    pdr_means, pdr_stds = [], []
    survival_means, survival_stds = [], []

    for proto in protocols:
        if proto == 'LEACH':
            # Use scalability data for LEACH (100 nodes)
            subset = [d for d in data['scalability_experiments']
                     if d['protocol'] == 'LEACH' and d['num_nodes'] == 100]
            pdr_vals = [d['pdr'] * 100 for d in subset]
            survival_vals = [d['alive_nodes'] / 100 * 100 for d in subset]
        else:
            subset = [d for d in data['ablation_experiments'] if d['protocol'] == proto]
            pdr_vals = [d['pdr'] * 100 for d in subset]
            survival_vals = [d['alive_nodes'] / 100 * 100 for d in subset]

        pdr_means.append(np.mean(pdr_vals))
        pdr_stds.append(np.std(pdr_vals))
        survival_means.append(np.mean(survival_vals))
        survival_stds.append(np.std(survival_vals))

    x = np.arange(len(protocols))

    # PDR subplot
    colors = [COLORS.get(p, '#888888') for p in protocols]
    hatches = [HATCHES.get(p, '') for p in protocols]

    bars1 = ax1.bar(x, pdr_means, yerr=pdr_stds,
                    color=colors, edgecolor='black', linewidth=0.8,
                    capsize=3, error_kw={'linewidth': 1})

    for bar, hatch in zip(bars1, hatches):
        bar.set_hatch(hatch)

    ax1.set_ylabel('Packet Delivery Ratio (%)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_ylim([65, 105])
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_axisbelow(True)
    ax1.set_title('(a) PDR Comparison', fontsize=10, fontweight='bold')

    # Add value labels on bars
    for i, (m, s) in enumerate(zip(pdr_means, pdr_stds)):
        ax1.text(i, m + s + 1, f'{m:.1f}%', ha='center', va='bottom', fontsize=7)

    # Survival rate subplot
    bars2 = ax2.bar(x, survival_means, yerr=survival_stds,
                    color=colors, edgecolor='black', linewidth=0.8,
                    capsize=3, error_kw={'linewidth': 1})

    for bar, hatch in zip(bars2, hatches):
        bar.set_hatch(hatch)

    ax2.set_ylabel('Node Survival Rate (%)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.set_ylim([60, 95])
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    ax2.set_axisbelow(True)
    ax2.set_title('(b) Node Survival Comparison', fontsize=10, fontweight='bold')

    # Add value labels on bars
    for i, (m, s) in enumerate(zip(survival_means, survival_stds)):
        ax2.text(i, m + s + 1, f'{m:.1f}%', ha='center', va='bottom', fontsize=7)

    # Set background
    ax1.set_facecolor('#FAFAFA')
    ax2.set_facecolor('#FAFAFA')

    plt.tight_layout()

    # Save in multiple formats
    for fmt in ['pdf', 'svg', 'png']:
        fig.savefig(output_dir / f'fig_ns3_ablation.{fmt}',
                   format=fmt, bbox_inches='tight')

    plt.close()
    print(f"  ✓ Ablation study saved")


def plot_combined_validation(data, output_dir):
    """
    Figure 3: Combined 2x2 Validation Panel
    """
    fig, axes = plt.subplots(2, 2, figsize=(8, 6.5))

    node_counts = [50, 100, 200]

    # === Panel (a): PDR Scalability ===
    ax = axes[0, 0]
    aeris_pdr, leach_pdr = [], []
    aeris_std, leach_std = [], []

    for nodes in node_counts:
        subset = [d for d in data['scalability_experiments'] if d['num_nodes'] == nodes]
        aeris_vals = [d['pdr'] * 100 for d in subset if d['protocol'] == 'AERIS']
        leach_vals = [d['pdr'] * 100 for d in subset if d['protocol'] == 'LEACH']
        aeris_pdr.append(np.mean(aeris_vals))
        aeris_std.append(np.std(aeris_vals))
        leach_pdr.append(np.mean(leach_vals))
        leach_std.append(np.std(leach_vals))

    ax.errorbar(node_counts, aeris_pdr, yerr=aeris_std, marker='o',
                color=COLORS['AERIS'], label='AERIS', capsize=4, linewidth=2, markersize=8)
    ax.errorbar(node_counts, leach_pdr, yerr=leach_std, marker='s',
                color=COLORS['LEACH'], label='LEACH', capsize=4, linewidth=2, markersize=8)

    ax.fill_between(node_counts,
                    [a-s for a,s in zip(aeris_pdr, aeris_std)],
                    [a+s for a,s in zip(aeris_pdr, aeris_std)],
                    alpha=0.2, color=COLORS['AERIS'])

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('PDR (%)')
    ax.set_ylim([75, 102])
    ax.legend(loc='lower left')
    ax.grid(alpha=0.3, linestyle='--')
    ax.set_title('(a) PDR vs Network Scale', fontweight='bold')
    ax.set_facecolor('#FAFAFA')

    # === Panel (b): Node Survival ===
    ax = axes[0, 1]
    aeris_surv, leach_surv = [], []

    for nodes in node_counts:
        subset = [d for d in data['scalability_experiments'] if d['num_nodes'] == nodes]
        aeris_vals = [d['alive_nodes'] / nodes * 100 for d in subset if d['protocol'] == 'AERIS']
        leach_vals = [d['alive_nodes'] / nodes * 100 for d in subset if d['protocol'] == 'LEACH']
        aeris_surv.append(np.mean(aeris_vals))
        leach_surv.append(np.mean(leach_vals))

    x = np.arange(len(node_counts))
    width = 0.35

    ax.bar(x - width/2, aeris_surv, width, label='AERIS', color=COLORS['AERIS'], edgecolor='black')
    ax.bar(x + width/2, leach_surv, width, label='LEACH', color=COLORS['LEACH'],
           edgecolor='black', hatch='///')

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Survival Rate (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(node_counts)
    ax.set_ylim([60, 95])
    ax.legend(loc='lower left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_title('(b) Node Survival Rate', fontweight='bold')
    ax.set_facecolor('#FAFAFA')

    # === Panel (c): Ablation PDR ===
    ax = axes[1, 0]
    protocols = ['AERIS-FULL', 'AERIS-noCAS', 'AERIS-noFair', 'AERIS-noGW']
    labels = ['Full', 'w/o CAS', 'w/o Fair', 'w/o GW']

    pdr_means = []
    for proto in protocols:
        subset = [d for d in data['ablation_experiments'] if d['protocol'] == proto]
        pdr_means.append(np.mean([d['pdr'] * 100 for d in subset]))

    colors = [COLORS[p] for p in protocols]
    bars = ax.bar(labels, pdr_means, color=colors, edgecolor='black', linewidth=0.8)

    # Highlight the significant drop
    ax.axhline(y=pdr_means[0], color='gray', linestyle='--', alpha=0.5, linewidth=1)

    # Annotate the drop for Gateway
    drop = pdr_means[0] - pdr_means[3]
    ax.annotate(f'↓{drop:.1f}%', xy=(3, pdr_means[3] + 2), ha='center',
               fontsize=9, color='red', fontweight='bold')

    ax.set_ylabel('PDR (%)')
    ax.set_ylim([70, 102])
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_title('(c) Ablation Study: PDR', fontweight='bold')
    ax.set_facecolor('#FAFAFA')

    # === Panel (d): Ablation Survival ===
    ax = axes[1, 1]

    survival_means = []
    for proto in protocols:
        subset = [d for d in data['ablation_experiments'] if d['protocol'] == proto]
        survival_means.append(np.mean([d['alive_nodes'] for d in subset]))

    bars = ax.bar(labels, survival_means, color=colors, edgecolor='black', linewidth=0.8)

    # Highlight the drop for Fairness
    ax.axhline(y=survival_means[0], color='gray', linestyle='--', alpha=0.5, linewidth=1)

    # Annotate the drop for Fairness
    drop = survival_means[0] - survival_means[2]
    ax.annotate(f'↓{drop:.1f}', xy=(2, survival_means[2] + 1), ha='center',
               fontsize=9, color='red', fontweight='bold')

    ax.set_ylabel('Alive Nodes (of 100)')
    ax.set_ylim([70, 90])
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_title('(d) Ablation Study: Node Survival', fontweight='bold')
    ax.set_facecolor('#FAFAFA')

    plt.tight_layout()

    # Save in multiple formats
    for fmt in ['pdf', 'svg', 'png']:
        fig.savefig(output_dir / f'fig_ns3_combined_panel.{fmt}',
                   format=fmt, bbox_inches='tight')

    plt.close()
    print(f"  ✓ Combined validation panel saved")


def plot_channel_model_diagram(output_dir):
    """
    Figure 4: Channel Model Visualization
    """
    fig, ax = plt.subplots(figsize=(5, 4))

    # Draw schematic of channel model
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)

    # TX node
    tx = plt.Circle((1.5, 4), 0.4, color=COLORS['AERIS'], ec='black', linewidth=2)
    ax.add_patch(tx)
    ax.text(1.5, 4, 'TX', ha='center', va='center', fontsize=9, color='white', fontweight='bold')

    # RX node (BS)
    rx = plt.Circle((8.5, 4), 0.5, color='#4DAF4A', ec='black', linewidth=2)
    ax.add_patch(rx)
    ax.text(8.5, 4, 'BS', ha='center', va='center', fontsize=9, color='white', fontweight='bold')

    # Arrow for signal path
    ax.annotate('', xy=(7.9, 4), xytext=(2, 4),
               arrowprops=dict(arrowstyle='->', color='gray', lw=2))

    # Channel effects boxes
    boxes = [
        (3.2, 6, 'Path Loss\nPL(d) = PL₀ + 10n·log(d/d₀)', '#E6F5E6'),
        (3.2, 4, 'Shadow Fading\nX ~ N(0, σ²), σ=3dB', '#FFF5E6'),
        (3.2, 2, 'Multipath Fading\nRician (K=6dB)', '#E6E6FF'),
    ]

    for x, y, text, color in boxes:
        box = mpatches.FancyBboxPatch((x, y-0.6), 3.5, 1.2,
                                       boxstyle='round,pad=0.05',
                                       facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(box)
        ax.text(x + 1.75, y, text, ha='center', va='center', fontsize=7)

    # Connect boxes with arrows
    for y in [6, 4, 2]:
        ax.annotate('', xy=(6.8, y), xytext=(6.7, y),
                   arrowprops=dict(arrowstyle='->', color='gray', lw=1.5))

    # Title and parameters
    ax.text(5, 7.5, 'Realistic Channel Model (IEEE 802.15.4)',
           ha='center', fontsize=11, fontweight='bold')

    ax.text(5, 0.5, 'TX Power: 0 dBm | Sensitivity: -95 dBm | n=2.5 (Indoor LOS)',
           ha='center', fontsize=8, style='italic', color='gray')

    ax.axis('off')
    ax.set_aspect('equal')

    plt.tight_layout()

    # Save
    for fmt in ['pdf', 'svg', 'png']:
        fig.savefig(output_dir / f'fig_channel_model.{fmt}',
                   format=fmt, bbox_inches='tight')

    plt.close()
    print(f"  ✓ Channel model diagram saved")


def main():
    print("=" * 50)
    print("NS-3 Validation Figure Generation")
    print("=" * 50)

    # Load results
    data = load_results()
    print(f"Loaded {len(data['scalability_experiments'])} scalability experiments")
    print(f"Loaded {len(data['ablation_experiments'])} ablation experiments")

    # Create output directory
    output_dir = Path(__file__).parent.parent / 'results' / 'ns3_figures'
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    # Generate figures
    print("\nGenerating publication-quality figures...")
    plot_scalability_comparison(data['scalability_experiments'], output_dir)
    plot_ablation_study(data, output_dir)
    plot_combined_validation(data, output_dir)
    plot_channel_model_diagram(output_dir)

    print("\n" + "=" * 50)
    print("All figures generated successfully!")
    print("=" * 50)

    # Print summary statistics
    print("\n--- Experiment Summary ---")

    # Scalability
    for nodes in [50, 100, 200]:
        subset = [d for d in data['scalability_experiments'] if d['num_nodes'] == nodes]
        aeris_pdr = np.mean([d['pdr'] for d in subset if d['protocol'] == 'AERIS'])
        leach_pdr = np.mean([d['pdr'] for d in subset if d['protocol'] == 'LEACH'])
        improvement = (aeris_pdr - leach_pdr) / leach_pdr * 100
        print(f"  {nodes} nodes: AERIS {aeris_pdr*100:.1f}% vs LEACH {leach_pdr*100:.1f}% (+{improvement:.1f}%)")

    # Ablation
    print("\n--- Ablation Summary ---")
    for proto, info in data['ablation_summary'].items():
        print(f"  {proto}: PDR={info['avg_pdr']*100:.1f}%, Survival={info['avg_survival']*100:.1f}%")


if __name__ == '__main__':
    main()
