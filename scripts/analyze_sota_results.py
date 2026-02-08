#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Analysis of SOTA Experiment Results
=========================================
Comprehensive analysis and publication-quality figure generation.

Author: AERIS Research Team
Date: 2026-01-06
"""

import os
import sys
import json
import numpy as np
from typing import Dict, List, Any
from scipy import stats

# Matplotlib setup
import matplotlib as mpl
mpl.use('Agg')
from cycler import cycler
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import PercentFormatter

# Paper style configuration
PALETTE = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02"]

OKABE_ITO = {
    'green': '#009E73',
    'orange': '#E69F00',
    'blue': '#0072B2',
    'red': '#D55E00',
    'purple': '#CC79A7',
    'sky': '#56B4E9',
}

MODE_COLORS = {
    'ULTRA_LOW_POWER': '#009E73',
    'BALANCED': '#0072B2',
    'HIGH_RELIABILITY': '#D55E00',
}

MODE_LABELS = {
    'ULTRA_LOW_POWER': 'Ultra Low Power',
    'BALANCED': 'Balanced',
    'HIGH_RELIABILITY': 'High Reliability',
}

ABLATION_COLORS = ['#4E79A7', '#A0CBE8', '#F28E2B', '#59A14F', '#E15759']
ABLATION_LABELS = {
    'Full_AERIS': 'Full AERIS',
    'No_SimplifiedCAS': '-CAS',
    'No_MultiObjGateway': '-Gateway',
    'No_AoIScheduler': '-AoI',
    'Baseline_Only': 'Baseline',
}

def apply_paper_style():
    """Apply publication-grade matplotlib style"""
    mpl.rcParams.update({
        'font.family': 'Palatino Linotype',
        'font.size': 11,
        'axes.titlesize': 12,
        'axes.labelsize': 11,
        'legend.fontsize': 10,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'axes.linewidth': 1.0,
        'axes.grid': True,
        'grid.linestyle': '--',
        'grid.alpha': 0.3,
        'svg.fonttype': 'none',
        'figure.dpi': 300,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'savefig.facecolor': 'white',
        'pdf.fonttype': 42,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.prop_cycle': cycler(color=PALETTE),
    })

apply_paper_style()


def load_results(results_dir: str) -> Dict:
    """Load experiment results from JSON file"""
    path = os.path.join(results_dir, 'final_results.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_figure(fig, path: str):
    """Save figure in SVG and PDF formats"""
    try:
        plt.tight_layout()
    except:
        pass

    for fmt in ['svg', 'pdf']:
        out_path = f"{path}.{fmt}"
        fig.savefig(out_path, bbox_inches='tight', format=fmt)
        print(f"  Saved: {out_path}")
    plt.close(fig)


# ============================================================================
# Analysis Functions
# ============================================================================

def print_main_comparison_analysis(data: Dict):
    """Print detailed analysis of main comparison results"""
    stats = data['main_comparison']['statistics']
    sig = data['main_comparison']['significance_tests']

    print("\n" + "=" * 70)
    print("MAIN COMPARISON ANALYSIS (50 repetitions, 100 nodes, 1000 rounds)")
    print("=" * 70)

    print("\n[Performance Summary]")
    print("-" * 70)
    print(f"{'Mode':<25} {'PDR (%)':<20} {'Energy (J)':<20}")
    print("-" * 70)

    for mode in ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']:
        s = stats[mode]
        pdr = f"{s['pdr_mean']*100:.1f} +/- {s['pdr_std']*100:.1f}"
        energy = f"{s['energy_mean']:.3f} +/- {s['energy_std']:.3f}"
        print(f"{MODE_LABELS[mode]:<25} {pdr:<20} {energy:<20}")

    print("\n[Statistical Significance]")
    print("-" * 70)

    # BALANCED vs HIGH_RELIABILITY
    bvh = sig['BALANCED_vs_HIGH_RELIABILITY']
    print(f"\nBALANCED vs HIGH_RELIABILITY:")
    print(f"  PDR: p = {bvh['pdr_p_value']:.2e}, Cohen's d = {bvh['pdr_cohens_d']:.2f}")
    print(f"  Energy: p = {bvh['energy_p_value']:.2e}, Cohen's d = {bvh['energy_cohens_d']:.2f}")

    # Effect size interpretation
    d = abs(bvh['pdr_cohens_d'])
    if d >= 0.8:
        effect = "LARGE"
    elif d >= 0.5:
        effect = "MEDIUM"
    else:
        effect = "SMALL"
    print(f"  Effect size: {effect}")

    # Key insight
    pdr_diff = (stats['HIGH_RELIABILITY']['pdr_mean'] - stats['BALANCED']['pdr_mean']) * 100
    energy_diff = (stats['HIGH_RELIABILITY']['energy_mean'] - stats['BALANCED']['energy_mean'])
    energy_pct = energy_diff / stats['BALANCED']['energy_mean'] * 100

    print(f"\n[Key Insight]")
    print(f"  BALANCED achieves {stats['BALANCED']['pdr_mean']*100:.1f}% PDR")
    print(f"  HIGH_RELIABILITY gains +{pdr_diff:.1f}% PDR but costs +{energy_pct:.1f}% energy")
    print(f"  Trade-off ratio: {pdr_diff/energy_pct:.2f}% PDR per 1% energy")


def print_ablation_analysis(data: Dict):
    """Print ablation study analysis"""
    stats = data['ablation_study']['statistics']

    print("\n" + "=" * 70)
    print("ABLATION STUDY ANALYSIS (30 repetitions, 100 nodes, 500 rounds)")
    print("=" * 70)

    print("\n[Component Contribution]")
    print("-" * 70)

    baseline = stats['Full_AERIS']

    configs = ['Full_AERIS', 'No_SimplifiedCAS', 'No_MultiObjGateway',
               'No_AoIScheduler', 'Baseline_Only']

    print(f"{'Configuration':<25} {'PDR (%)':<15} {'Delta PDR':<12} {'Energy (J)':<12}")
    print("-" * 70)

    for cfg in configs:
        s = stats[cfg]
        pdr = s['pdr_mean'] * 100
        delta = (s['pdr_mean'] - baseline['pdr_mean']) * 100
        energy = s['energy_mean']

        delta_str = f"{delta:+.2f}%" if cfg != 'Full_AERIS' else "-"
        print(f"{ABLATION_LABELS[cfg]:<25} {pdr:.1f}%{'':<8} {delta_str:<12} {energy:.4f}")

    print("\n[Component Impact Summary]")

    # Calculate impact of each component
    full_pdr = stats['Full_AERIS']['pdr_mean']

    components = {
        'SimplifiedCAS': stats['No_SimplifiedCAS']['pdr_mean'] - full_pdr,
        'MultiObjGateway': stats['No_MultiObjGateway']['pdr_mean'] - full_pdr,
        'AoIScheduler': stats['No_AoIScheduler']['pdr_mean'] - full_pdr,
    }

    for comp, impact in sorted(components.items(), key=lambda x: abs(x[1]), reverse=True):
        impact_pct = impact * 100
        direction = "+" if impact > 0 else ""
        print(f"  {comp}: {direction}{impact_pct:.2f}% PDR when removed")


def print_scale_analysis(data: Dict):
    """Print scalability analysis"""
    stats = data['scale_analysis']['statistics']

    print("\n" + "=" * 70)
    print("SCALABILITY ANALYSIS (30 repetitions, 500 rounds)")
    print("=" * 70)

    print("\n[PDR vs Network Size]")
    print("-" * 70)
    print(f"{'Nodes':<10} {'BALANCED PDR':<20} {'HIGH_RELIABILITY PDR':<20}")
    print("-" * 70)

    for key in sorted(stats.keys()):
        if key.startswith('nodes_'):
            n = key.split('_')[1]
            if 'BALANCED' in stats[key] and 'HIGH_RELIABILITY' in stats[key]:
                bal = stats[key]['BALANCED']['pdr_mean'] * 100
                hr = stats[key]['HIGH_RELIABILITY']['pdr_mean'] * 100
                print(f"{n:<10} {bal:.1f}%{'':<15} {hr:.1f}%")


def print_lifetime_analysis(data: Dict):
    """Print lifetime analysis"""
    stats = data['lifetime_analysis']['statistics']

    print("\n" + "=" * 70)
    print("LIFETIME ANALYSIS (20 repetitions, 5000 rounds)")
    print("=" * 70)

    print("\n[Long-term Performance]")
    print("-" * 70)

    for mode in ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']:
        s = stats[mode]
        print(f"\n{MODE_LABELS[mode]}:")
        print(f"  PDR: {s['pdr_mean']*100:.1f}% +/- {s['pdr_std']*100:.1f}%")
        print(f"  Energy: {s['energy_mean']:.2f}J +/- {s['energy_std']:.2f}J")
        print(f"  Lifetime: {s['lifetime_mean']:.0f} rounds")


# ============================================================================
# Figure Generation
# ============================================================================

def fig_main_comparison_combined(data: Dict, output_dir: str):
    """Create combined PDR-Energy comparison figure"""
    stats = data['main_comparison']['statistics']

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    modes = ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']
    labels = [MODE_LABELS[m] for m in modes]
    colors = [MODE_COLORS[m] for m in modes]

    # PDR subplot
    ax = axes[0]
    pdrs = [stats[m]['pdr_mean'] * 100 for m in modes]
    pdr_errors = [(stats[m]['pdr_ci_upper'] - stats[m]['pdr_ci_lower']) / 2 * 100 for m in modes]

    x = np.arange(len(modes))
    bars = ax.bar(x, pdrs, yerr=pdr_errors, capsize=5, color=colors,
                  edgecolor='black', linewidth=0.5)

    for i, (bar, pdr) in enumerate(zip(bars, pdrs)):
        ax.annotate(f'{pdr:.1f}%', xy=(bar.get_x() + bar.get_width()/2, pdr),
                   xytext=(0, 5), textcoords='offset points',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylabel('Packet Delivery Ratio (%)')
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace(' ', '\n') for l in labels])
    ax.set_ylim(60, 105)
    ax.set_title('(a) PDR Comparison')

    # Energy subplot
    ax = axes[1]
    energies = [stats[m]['energy_mean'] for m in modes]
    energy_errors = [(stats[m]['energy_ci_upper'] - stats[m]['energy_ci_lower']) / 2 for m in modes]

    bars = ax.bar(x, energies, yerr=energy_errors, capsize=5, color=colors,
                  edgecolor='black', linewidth=0.5)

    # Add savings annotation
    baseline_energy = energies[2]
    for i, (bar, energy) in enumerate(zip(bars, energies)):
        if i < 2:
            savings = (baseline_energy - energy) / baseline_energy * 100
            ax.annotate(f'-{savings:.0f}%', xy=(bar.get_x() + bar.get_width()/2, energy/2),
                       ha='center', va='center', fontsize=9, fontweight='bold', color='white')

    ax.set_ylabel('Total Energy Consumption (J)')
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace(' ', '\n') for l in labels])
    ax.set_title('(b) Energy Comparison')

    # Add legend
    handles = [mpatches.Patch(color=c, label=l) for c, l in zip(colors, labels)]
    fig.legend(handles, labels, loc='upper center', ncol=3, bbox_to_anchor=(0.5, 1.02))

    save_figure(fig, os.path.join(output_dir, 'fig_main_comparison'))


def fig_tradeoff_pareto(data: Dict, output_dir: str):
    """Create PDR-Energy trade-off Pareto front figure"""
    results = data['main_comparison']['results']
    stats = data['main_comparison']['statistics']

    fig, ax = plt.subplots(figsize=(7, 5))

    modes = ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']
    markers = ['s', 'o', '^']

    for mode, marker in zip(modes, markers):
        raw = results[mode]
        pdrs = [r['pdr'] * 100 for r in raw]
        energies = [r['energy'] for r in raw]

        ax.scatter(energies, pdrs, c=MODE_COLORS[mode], marker=marker,
                  s=30, alpha=0.4, label=MODE_LABELS[mode])

        # Mean point with error bars
        s = stats[mode]
        ax.errorbar(s['energy_mean'], s['pdr_mean'] * 100,
                   xerr=(s['energy_ci_upper'] - s['energy_ci_lower']) / 2,
                   yerr=(s['pdr_ci_upper'] - s['pdr_ci_lower']) / 2 * 100,
                   fmt=marker, c=MODE_COLORS[mode], markersize=12,
                   capsize=4, markeredgecolor='black', markeredgewidth=1.5,
                   zorder=10)

    # Draw Pareto front line
    means = [(stats[m]['energy_mean'], stats[m]['pdr_mean'] * 100) for m in modes]
    means.sort()
    ax.plot([m[0] for m in means], [m[1] for m in means],
           'k--', alpha=0.5, linewidth=1.5, label='Trade-off Frontier')

    ax.set_xlabel('Total Energy Consumption (J)')
    ax.set_ylabel('Packet Delivery Ratio (%)')
    ax.set_ylim(55, 105)
    ax.legend(loc='lower right', frameon=True)
    ax.grid(True, alpha=0.3)

    # Annotate optimal region
    ax.annotate('Optimal\nRegion', xy=(1.3, 97), fontsize=10,
               ha='center', style='italic', color='#666')

    save_figure(fig, os.path.join(output_dir, 'fig_tradeoff_pareto'))


def fig_ablation_forest(data: Dict, output_dir: str):
    """Create ablation study forest plot"""
    stats = data['ablation_study']['statistics']

    fig, ax = plt.subplots(figsize=(8, 5))

    configs = ['Full_AERIS', 'No_SimplifiedCAS', 'No_MultiObjGateway',
               'No_AoIScheduler', 'Baseline_Only']

    baseline_pdr = stats['Full_AERIS']['pdr_mean']

    y_positions = np.arange(len(configs))[::-1]

    for i, cfg in enumerate(configs):
        s = stats[cfg]
        pdr = s['pdr_mean']
        ci_low = s['pdr_ci_lower']
        ci_high = s['pdr_ci_upper']

        delta = (pdr - baseline_pdr) * 100
        delta_low = (ci_low - baseline_pdr) * 100
        delta_high = (ci_high - baseline_pdr) * 100

        color = ABLATION_COLORS[i]
        y = y_positions[i]

        # Plot point and CI
        ax.errorbar(delta, y, xerr=[[delta - delta_low], [delta_high - delta]],
                   fmt='o', color=color, markersize=10, capsize=5,
                   markeredgecolor='black', markeredgewidth=1)

        # Add label
        ax.annotate(f'{delta:+.2f}%', xy=(delta, y), xytext=(5, 0),
                   textcoords='offset points', va='center', fontsize=9)

    # Reference line at 0
    ax.axvline(x=0, color='gray', linestyle='--', linewidth=1)

    ax.set_yticks(y_positions)
    ax.set_yticklabels([ABLATION_LABELS[c] for c in configs])
    ax.set_xlabel('PDR Change vs Full AERIS (percentage points)')
    ax.set_xlim(-3, 2)
    ax.grid(True, alpha=0.3, axis='x')

    save_figure(fig, os.path.join(output_dir, 'fig_ablation_forest'))


def fig_scalability_lines(data: Dict, output_dir: str):
    """Create scalability analysis line plot"""
    stats = data['scale_analysis']['statistics']

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Extract data
    node_counts = []
    bal_pdr, bal_pdr_err = [], []
    hr_pdr, hr_pdr_err = [], []
    bal_energy, hr_energy = [], []

    for key in sorted(stats.keys()):
        if key.startswith('nodes_'):
            n = int(key.split('_')[1])
            if 'BALANCED' in stats[key]:
                node_counts.append(n)
                bal_pdr.append(stats[key]['BALANCED']['pdr_mean'] * 100)
                bal_pdr_err.append((stats[key]['BALANCED']['pdr_ci_upper'] -
                                   stats[key]['BALANCED']['pdr_ci_lower']) / 2 * 100)
                hr_pdr.append(stats[key]['HIGH_RELIABILITY']['pdr_mean'] * 100)
                hr_pdr_err.append((stats[key]['HIGH_RELIABILITY']['pdr_ci_upper'] -
                                  stats[key]['HIGH_RELIABILITY']['pdr_ci_lower']) / 2 * 100)
                bal_energy.append(stats[key]['BALANCED']['energy_mean'])
                hr_energy.append(stats[key]['HIGH_RELIABILITY']['energy_mean'])

    # PDR subplot
    ax = axes[0]
    ax.errorbar(node_counts, bal_pdr, yerr=bal_pdr_err, marker='o',
               label='BALANCED', color=MODE_COLORS['BALANCED'], capsize=3)
    ax.errorbar(node_counts, hr_pdr, yerr=hr_pdr_err, marker='^',
               label='HIGH_RELIABILITY', color=MODE_COLORS['HIGH_RELIABILITY'], capsize=3)
    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('PDR (%)')
    ax.set_ylim(70, 105)
    ax.legend(loc='lower left')
    ax.set_title('(a) PDR vs Network Size')
    ax.grid(True, alpha=0.3)

    # Energy subplot
    ax = axes[1]
    ax.plot(node_counts, bal_energy, marker='o', label='BALANCED',
           color=MODE_COLORS['BALANCED'])
    ax.plot(node_counts, hr_energy, marker='^', label='HIGH_RELIABILITY',
           color=MODE_COLORS['HIGH_RELIABILITY'])
    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Energy (J)')
    ax.legend(loc='upper left')
    ax.set_title('(b) Energy vs Network Size')
    ax.grid(True, alpha=0.3)

    save_figure(fig, os.path.join(output_dir, 'fig_scalability'))


def fig_sensitivity_heatmap(data: Dict, output_dir: str):
    """Create sensitivity analysis heatmap"""
    stats = data['sensitivity_analysis']['statistics']

    if 'ch_probability' not in stats or 'gateway_count' not in stats:
        print("  Skipping sensitivity heatmap: missing data")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # CH Probability
    ax = axes[0]
    ch_stats = stats['ch_probability']
    probs = sorted([float(k.split('_')[1]) for k in ch_stats.keys()])
    pdrs = [ch_stats[f'p_{p}']['pdr_mean'] * 100 for p in probs]
    energies = [ch_stats[f'p_{p}']['energy_mean'] for p in probs]

    ax2 = ax.twinx()
    l1 = ax.bar(np.arange(len(probs)) - 0.15, pdrs, width=0.3,
               label='PDR', color=OKABE_ITO['blue'], alpha=0.8)
    l2 = ax2.bar(np.arange(len(probs)) + 0.15, energies, width=0.3,
                label='Energy', color=OKABE_ITO['orange'], alpha=0.8)

    ax.set_xticks(np.arange(len(probs)))
    ax.set_xticklabels([f'{p:.2f}' for p in probs])
    ax.set_xlabel('CH Probability')
    ax.set_ylabel('PDR (%)', color=OKABE_ITO['blue'])
    ax2.set_ylabel('Energy (J)', color=OKABE_ITO['orange'])
    ax.set_ylim(98, 100.5)
    ax.set_title('(a) CH Probability Sensitivity')

    # Gateway Count
    ax = axes[1]
    gw_stats = stats['gateway_count']
    counts = sorted([int(k.split('_')[1]) for k in gw_stats.keys()])
    pdrs = [gw_stats[f'k_{k}']['pdr_mean'] * 100 for k in counts]
    energies = [gw_stats[f'k_{k}']['energy_mean'] for k in counts]

    ax2 = ax.twinx()
    ax.bar(np.arange(len(counts)) - 0.15, pdrs, width=0.3,
          label='PDR', color=OKABE_ITO['blue'], alpha=0.8)
    ax2.bar(np.arange(len(counts)) + 0.15, energies, width=0.3,
           label='Energy', color=OKABE_ITO['orange'], alpha=0.8)

    ax.set_xticks(np.arange(len(counts)))
    ax.set_xticklabels([str(k) for k in counts])
    ax.set_xlabel('Number of Gateways')
    ax.set_ylabel('PDR (%)', color=OKABE_ITO['blue'])
    ax2.set_ylabel('Energy (J)', color=OKABE_ITO['orange'])
    ax.set_ylim(98, 100.5)
    ax.set_title('(b) Gateway Count Sensitivity')

    save_figure(fig, os.path.join(output_dir, 'fig_sensitivity'))


def fig_lifetime_comparison(data: Dict, output_dir: str):
    """Create lifetime analysis comparison figure"""
    stats = data['lifetime_analysis']['statistics']

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    modes = ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']
    labels = [MODE_LABELS[m] for m in modes]
    colors = [MODE_COLORS[m] for m in modes]

    x = np.arange(len(modes))

    # PDR after 5000 rounds
    ax = axes[0]
    pdrs = [stats[m]['pdr_mean'] * 100 for m in modes]
    pdr_errors = [stats[m]['pdr_std'] * 100 for m in modes]

    bars = ax.bar(x, pdrs, yerr=pdr_errors, capsize=5, color=colors,
                  edgecolor='black', linewidth=0.5)
    ax.set_ylabel('PDR after 5000 rounds (%)')
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace(' ', '\n') for l in labels])
    ax.set_ylim(60, 105)
    ax.set_title('(a) Long-term PDR')

    # Energy consumption over 5000 rounds
    ax = axes[1]
    energies = [stats[m]['energy_mean'] for m in modes]
    energy_errors = [stats[m]['energy_std'] for m in modes]

    bars = ax.bar(x, energies, yerr=energy_errors, capsize=5, color=colors,
                  edgecolor='black', linewidth=0.5)
    ax.set_ylabel('Total Energy (J)')
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace(' ', '\n') for l in labels])
    ax.set_title('(b) Long-term Energy')

    save_figure(fig, os.path.join(output_dir, 'fig_lifetime'))


def generate_latex_tables(data: Dict, output_dir: str):
    """Generate LaTeX tables for paper"""

    # Main comparison table
    stats = data['main_comparison']['statistics']
    sig = data['main_comparison']['significance_tests']

    latex = r"""
\begin{table}[h]
\centering
\caption{Performance Comparison of AERIS Reliability Modes (n=50, 100 nodes, 1000 rounds)}
\label{tab:main-comparison}
\begin{tabular}{lccc}
\toprule
\textbf{Mode} & \textbf{PDR (\%)} & \textbf{Energy (J)} & \textbf{95\% CI PDR} \\
\midrule
"""

    for mode in ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']:
        s = stats[mode]
        name = MODE_LABELS[mode]
        pdr = f"{s['pdr_mean']*100:.1f} $\\pm$ {s['pdr_std']*100:.1f}"
        energy = f"{s['energy_mean']:.3f} $\\pm$ {s['energy_std']:.3f}"
        ci = f"[{s['pdr_ci_lower']*100:.1f}, {s['pdr_ci_upper']*100:.1f}]"
        latex += f"{name} & {pdr} & {energy} & {ci} \\\\\n"

    latex += r"""
\bottomrule
\end{tabular}
\end{table}
"""

    # Significance table
    latex += r"""
\begin{table}[h]
\centering
\caption{Statistical Significance of Pairwise Comparisons}
\label{tab:significance}
\begin{tabular}{lcccc}
\toprule
\textbf{Comparison} & \textbf{PDR p-value} & \textbf{PDR Cohen's d} & \textbf{Energy p-value} & \textbf{Energy Cohen's d} \\
\midrule
"""

    for pair in ['ULTRA_LOW_POWER_vs_BALANCED', 'ULTRA_LOW_POWER_vs_HIGH_RELIABILITY',
                 'BALANCED_vs_HIGH_RELIABILITY']:
        s = sig[pair]
        name = pair.replace('_vs_', ' vs ').replace('_', ' ')
        pdr_p = f"$<$0.001" if s['pdr_p_value'] < 0.001 else f"{s['pdr_p_value']:.3f}"
        energy_p = f"$<$0.001" if s['energy_p_value'] < 0.001 else f"{s['energy_p_value']:.3f}"
        latex += f"{name} & {pdr_p} & {s['pdr_cohens_d']:.2f} & {energy_p} & {s['energy_cohens_d']:.2f} \\\\\n"

    latex += r"""
\bottomrule
\end{tabular}
\end{table}
"""

    output_path = os.path.join(output_dir, 'paper_tables.tex')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(latex)
    print(f"  Saved: {output_path}")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main analysis and figure generation"""
    print("\n" + "=" * 70)
    print("DEEP ANALYSIS OF SOTA EXPERIMENT RESULTS")
    print("=" * 70)

    # Load results
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'sota_experiments_full')

    if not os.path.exists(os.path.join(results_dir, 'final_results.json')):
        results_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'sota_experiments_quick')

    print(f"\nLoading results from: {results_dir}")
    data = load_results(results_dir)

    # Print analysis
    print_main_comparison_analysis(data)
    print_ablation_analysis(data)
    print_scale_analysis(data)
    print_lifetime_analysis(data)

    # Generate figures
    output_dir = os.path.join(results_dir, 'paper_figures')
    os.makedirs(output_dir, exist_ok=True)

    print("\n" + "=" * 70)
    print("GENERATING PUBLICATION FIGURES")
    print("=" * 70)

    print("\n[Main Comparison]")
    fig_main_comparison_combined(data, output_dir)

    print("\n[Trade-off Pareto]")
    fig_tradeoff_pareto(data, output_dir)

    print("\n[Ablation Forest]")
    fig_ablation_forest(data, output_dir)

    print("\n[Scalability]")
    fig_scalability_lines(data, output_dir)

    print("\n[Sensitivity]")
    fig_sensitivity_heatmap(data, output_dir)

    print("\n[Lifetime]")
    fig_lifetime_comparison(data, output_dir)

    print("\n[LaTeX Tables]")
    generate_latex_tables(data, output_dir)

    # Copy to publication_figures
    pub_dir = os.path.join(os.path.dirname(results_dir), 'publication_figures')
    os.makedirs(pub_dir, exist_ok=True)

    import shutil
    for f in os.listdir(output_dir):
        src = os.path.join(output_dir, f)
        dst = os.path.join(pub_dir, f)
        try:
            shutil.copy2(src, dst)
        except:
            pass

    print(f"\nFigures copied to: {pub_dir}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
