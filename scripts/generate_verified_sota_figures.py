#!/usr/bin/env python3
"""
Generate Publication-Quality SOTA Comparison Figures
Using verified large_scale_scalability data

Author: AERIS Research Team
Date: 2026-01-26
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from pathlib import Path
from scipy import stats

# Publication style
plt.rcParams.update({
    'font.family': 'Arial',
    'font.size': 10,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'axes.linewidth': 0.8,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.5,
})

# Color palette
COLORS = {
    'AERIS': '#E45756',    # Red (emphasized)
    'PEGASIS': '#4C78A8',  # Blue
    'LEACH': '#72B7B2',    # Teal
    'HEED': '#F1CE63',     # Gold
}

MARKERS = {
    'AERIS': 'o',
    'PEGASIS': 's',
    'LEACH': '^',
    'HEED': 'D',
}

PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / 'results'
FIGURES_DIR = PROJECT_ROOT / 'for_submission' / 'figures'


def load_verified_data():
    """Load verified scalability data."""
    path = RESULTS_DIR / 'large_scale_scalability_verified.json'
    with open(path) as f:
        return json.load(f)


def create_pdr_vs_scale_figure(data):
    """Create PDR vs Network Scale figure."""
    summary = data.get('summary', {})

    fig, ax = plt.subplots(figsize=(8, 5))

    nodes = [100, 200, 300, 500]
    protocols = ['AERIS', 'PEGASIS', 'LEACH', 'HEED']

    for proto in protocols:
        pdrs = []
        cis = []
        for n in nodes:
            s = summary.get(str(n), {}).get(proto, {})
            pdrs.append(s.get('pdr_mean', 0) * 100)
            cis.append(s.get('pdr_ci95', 0) * 100)

        ax.errorbar(nodes, pdrs, yerr=cis,
                   label=proto, color=COLORS[proto],
                   marker=MARKERS[proto], markersize=8,
                   linewidth=2, capsize=4)

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Packet Delivery Ratio (%)')
    ax.set_title('PDR vs Network Scale (60 replicates, 1000 rounds)')
    ax.legend(loc='lower left')
    ax.set_ylim(30, 105)
    ax.set_xticks(nodes)

    # Add improvement annotations
    for i, n in enumerate(nodes):
        aeris_pdr = summary.get(str(n), {}).get('AERIS', {}).get('pdr_mean', 0) * 100
        pegasis_pdr = summary.get(str(n), {}).get('PEGASIS', {}).get('pdr_mean', 0) * 100
        improvement = aeris_pdr - pegasis_pdr
        ax.annotate(f'+{improvement:.1f}%',
                   xy=(n, aeris_pdr + 2),
                   ha='center', fontsize=8, color='#E45756')

    plt.tight_layout()
    return fig


def create_bar_comparison_figure(data):
    """Create bar chart comparison at different scales."""
    summary = data.get('summary', {})

    fig, axes = plt.subplots(1, 4, figsize=(14, 4), sharey=True)

    nodes_list = ['100', '200', '300', '500']
    protocols = ['AERIS', 'PEGASIS', 'LEACH', 'HEED']

    for idx, nodes in enumerate(nodes_list):
        ax = axes[idx]
        node_data = summary.get(nodes, {})

        pdrs = []
        cis = []
        colors = []

        for proto in protocols:
            s = node_data.get(proto, {})
            pdrs.append(s.get('pdr_mean', 0) * 100)
            cis.append(s.get('pdr_ci95', 0) * 100)
            colors.append(COLORS[proto])

        bars = ax.bar(protocols, pdrs, yerr=cis, capsize=4,
                     color=colors, edgecolor='black', linewidth=0.5)

        ax.set_title(f'{nodes} Nodes')
        ax.set_ylim(0, 110)

        # Add value labels
        for bar, pdr in zip(bars, pdrs):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                   f'{pdr:.1f}%', ha='center', va='bottom', fontsize=8)

        if idx == 0:
            ax.set_ylabel('PDR (%)')

        ax.tick_params(axis='x', rotation=45)

    plt.suptitle('Protocol Comparison at Different Network Scales', y=1.02)
    plt.tight_layout()
    return fig


def create_improvement_heatmap(data):
    """Create heatmap showing AERIS improvement over baselines."""
    summary = data.get('summary', {})

    nodes_list = ['100', '200', '300', '500']
    baselines = ['PEGASIS', 'LEACH', 'HEED']

    improvements = np.zeros((len(baselines), len(nodes_list)))

    for i, baseline in enumerate(baselines):
        for j, nodes in enumerate(nodes_list):
            aeris_pdr = summary.get(nodes, {}).get('AERIS', {}).get('pdr_mean', 0)
            baseline_pdr = summary.get(nodes, {}).get(baseline, {}).get('pdr_mean', 0)
            improvements[i, j] = (aeris_pdr - baseline_pdr) * 100

    fig, ax = plt.subplots(figsize=(8, 4))

    im = ax.imshow(improvements, cmap='RdYlGn', aspect='auto', vmin=0, vmax=50)

    ax.set_xticks(range(len(nodes_list)))
    ax.set_xticklabels([f'{n} nodes' for n in nodes_list])
    ax.set_yticks(range(len(baselines)))
    ax.set_yticklabels([f'vs {b}' for b in baselines])

    # Add text annotations
    for i in range(len(baselines)):
        for j in range(len(nodes_list)):
            text = ax.text(j, i, f'+{improvements[i, j]:.1f}%',
                          ha='center', va='center', fontsize=10, fontweight='bold')

    ax.set_title('AERIS PDR Improvement Over Baselines (%)')
    plt.colorbar(im, ax=ax, label='Improvement (%)')
    plt.tight_layout()
    return fig


def create_statistical_summary_table(data):
    """Create statistical summary figure."""
    summary = data.get('summary', {})

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axis('off')

    # Prepare table data
    columns = ['Nodes', 'Protocol', 'PDR Mean', '95% CI', 'Std Dev', 'n']
    rows = []

    for nodes in ['100', '200', '300', '500']:
        for proto in ['AERIS', 'PEGASIS', 'LEACH', 'HEED']:
            s = summary.get(nodes, {}).get(proto, {})
            rows.append([
                nodes,
                proto,
                f"{s.get('pdr_mean', 0)*100:.2f}%",
                f"±{s.get('pdr_ci95', 0)*100:.2f}%",
                f"{s.get('pdr_std', 0)*100:.2f}%",
                str(s.get('n_samples', 0))
            ])

    table = ax.table(cellText=rows, colLabels=columns, loc='center',
                    cellLoc='center', colColours=['#f0f0f0']*6)
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)

    # Highlight AERIS rows
    for i, row in enumerate(rows):
        if row[1] == 'AERIS':
            for j in range(len(columns)):
                table[(i+1, j)].set_facecolor('#ffe6e6')

    ax.set_title('Statistical Summary of PDR Results\n(60 replicates per configuration)',
                fontsize=12, pad=20)
    plt.tight_layout()
    return fig


def create_6panel_figure(data):
    """Create comprehensive 6-panel figure for publication."""
    summary = data.get('summary', {})

    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)

    nodes = [100, 200, 300, 500]
    protocols = ['AERIS', 'PEGASIS', 'LEACH', 'HEED']

    # Panel A: PDR vs Scale (line plot)
    ax1 = fig.add_subplot(gs[0, 0])
    for proto in protocols:
        pdrs = [summary.get(str(n), ).get(proto, {}).get('pdr_mean', 0) * 100 for n in nodes]
        cis = [summary.get(str(n), {}).get(proto, {}).get('pdr_ci95', 0) * 100 for n in nodes]
        ax1.errorbar(nodes, pdrs, yerr=cis, label=proto, color=COLORS[proto],
                    marker=MARKERS[proto], markersize=6, linewidth=1.5, capsize=3)
    ax1.set_xlabel('Number of Nodes')
    ax1.set_ylabel('PDR (%)')
    ax1.set_title('(a) PDR vs Network Scale')
    ax1.legend(loc='lower left', fontsize=8)
    ax1.set_ylim(30, 105)
    ax1.set_xticks(nodes)

    # Panel B: Bar chart at 100 nodes
    ax2 = fig.add_subplot(gs[0, 1])
    node_data = summary.get('100', {})
    pdrs = [node_data.get(p, {}).get('pdr_mean', 0) * 100 for p in protocols]
    cis = [node_data.get(p, {}).get('pdr_ci95', 0) * 100 for p in protocols]
    colors = [COLORS[p] for p in protocols]
    bars = ax2.bar(protocols, pdrs, yerr=cis, capsize=3, color=colors, edgecolor='black', linewidth=0.5)
    ax2.set_ylabel('PDR (%)')
    ax2.set_title('(b) 100 Nodes')
    ax2.set_ylim(0, 110)
    for bar, pdr in zip(bars, pdrs):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{pdr:.1f}', ha='center', va='bottom', fontsize=8)

    # Panel C: Bar chart at 500 nodes
    ax3 = fig.add_subplot(gs[0, 2])
    node_data = summary.get('500', {})
    pdrs = [node_data.get(p, {}).get('pdr_mean', 0) * 100 for p in protocols]
    cis = [node_data.get(p, {}).get('pdr_ci95', 0) * 100 for p in protocols]
    bars = ax3.bar(protocols, pdrs, yerr=cis, capsize=3, color=colors, edgecolor='black', linewidth=0.5)
    ax3.set_ylabel('PDR (%)')
    ax3.set_title('(c) 500 Nodes')
    ax3.set_ylim(0, 110)
    for bar, pdr in zip(bars, pdrs):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{pdr:.1f}', ha='center', va='bottom', fontsize=8)

    # Panel D: Improvement over PEGASIS
    ax4 = fig.add_subplot(gs[1, 0])
    improvements = []
    for n in nodes:
        aeris = summary.get(str(n), {}).get('AERIS', {}).get('pdr_mean', 0) * 100
        pegasis = summary.get(str(n), {}).get('PEGASIS', {}).get('pdr_mean', 0) * 100
        improvements.append(aeris - pegasis)
    ax4.bar([str(n) for n in nodes], improvements, color='#E45756', edgecolor='black', linewidth=0.5)
    ax4.set_xlabel('Number of Nodes')
    ax4.set_ylabel('PDR Improvement (%)')
    ax4.set_title('(d) AERIS vs PEGASIS')
    for i, imp in enumerate(improvements):
        ax4.text(i, imp + 0.5, f'+{imp:.1f}%', ha='center', fontsize=9)

    # Panel E: Scalability degradation
    ax5 = fig.add_subplot(gs[1, 1])
    for proto in protocols:
        pdr_100 = summary.get('100', {}).get(proto, {}).get('pdr_mean', 0) * 100
        degradation = []
        for n in nodes:
            pdr_n = summary.get(str(n), {}).get(proto, {}).get('pdr_mean', 0) * 100
            degradation.append(pdr_100 - pdr_n)
        ax5.plot(nodes, degradation, label=proto, color=COLORS[proto],
                marker=MARKERS[proto], markersize=6, linewidth=1.5)
    ax5.set_xlabel('Number of Nodes')
    ax5.set_ylabel('PDR Degradation from 100 nodes (%)')
    ax5.set_title('(e) Scalability Degradation')
    ax5.legend(loc='upper left', fontsize=8)
    ax5.set_xticks(nodes)

    # Panel F: Statistical summary text
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis('off')

    # Create summary text
    text = "Statistical Summary\n" + "="*30 + "\n\n"
    text += "AERIS Advantages:\n"
    for n in nodes:
        aeris = summary.get(str(n), {}).get('AERIS', {}).get('pdr_mean', 0) * 100
        pegasis = summary.get(str(n), {}).get('PEGASIS', {}).get('pdr_mean', 0) * 100
        text += f"  {n} nodes: +{aeris-pegasis:.1f}% vs PEGASIS\n"

    text += f"\nExperimental Setup:\n"
    text += f"  Replicates: 60 per config\n"
    text += f"  Rounds: 1000\n"
    text += f"  Channel: Log-normal (σ=8dB)\n"
    text += f"  Energy: CC2420 model\n"

    ax6.text(0.1, 0.9, text, transform=ax6.transAxes, fontsize=9,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    ax6.set_title('(f) Summary')

    plt.suptitle('AERIS Protocol Performance Comparison', fontsize=14, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


def main():
    """Generate all figures."""
    print("Loading verified data...")
    data = load_verified_data()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating PDR vs Scale figure...")
    fig1 = create_pdr_vs_scale_figure(data)
    fig1.savefig(FIGURES_DIR / 'verified_pdr_vs_scale.pdf', bbox_inches='tight')
    fig1.savefig(FIGURES_DIR / 'verified_pdr_vs_scale.png', bbox_inches='tight')
    plt.close(fig1)

    print("Generating bar comparison figure...")
    fig2 = create_bar_comparison_figure(data)
    fig2.savefig(FIGURES_DIR / 'verified_bar_comparison.pdf', bbox_inches='tight')
    fig2.savefig(FIGURES_DIR / 'verified_bar_comparison.png', bbox_inches='tight')
    plt.close(fig2)

    print("Generating improvement heatmap...")
    fig3 = create_improvement_heatmap(data)
    fig3.savefig(FIGURES_DIR / 'verified_improvement_heatmap.pdf', bbox_inches='tight')
    fig3.savefig(FIGURES_DIR / 'verified_improvement_heatmap.png', bbox_inches='tight')
    plt.close(fig3)

    print("Generating statistical summary...")
    fig4 = create_statistical_summary_table(data)
    fig4.savefig(FIGURES_DIR / 'verified_statistical_summary.pdf', bbox_inches='tight')
    fig4.savefig(FIGURES_DIR / 'verified_statistical_summary.png', bbox_inches='tight')
    plt.close(fig4)

    print("Generating 6-panel figure...")
    fig5 = create_6panel_figure(data)
    fig5.savefig(FIGURES_DIR / 'verified_sota_6panel.pdf', bbox_inches='tight')
    fig5.savefig(FIGURES_DIR / 'verified_sota_6panel.png', bbox_inches='tight')
    plt.close(fig5)

    print(f"\nAll figures saved to {FIGURES_DIR}")

    # Print summary
    summary = data.get('summary', {})
    print("\n" + "="*50)
    print("VERIFIED DATA SUMMARY")
    print("="*50)
    for nodes in ['100', '200', '300', '500']:
        print(f"\n{nodes} Nodes:")
        for proto in ['AERIS', 'PEGASIS', 'LEACH', 'HEED']:
            s = summary.get(nodes, {}).get(proto, {})
            print(f"  {proto}: {s.get('pdr_mean',0)*100:.2f}% ± {s.get('pdr_ci95',0)*100:.2f}%")


if __name__ == '__main__':
    main()
