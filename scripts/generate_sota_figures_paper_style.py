#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Publication-Quality Figures for SOTA Comparison (Paper Style)
==============================================================
Generate figures for comprehensive AERIS experiments matching the paper style.

Uses same styling as plot_paper_figures.py:
- Palatino Linotype font
- Okabe-Ito color palette
- 300 DPI, SVG + PDF output
- Publication-grade formatting

Author: AERIS Research Team
Date: 2026-01-04
"""

import os
import sys
import json
import shutil
from typing import Dict, List, Any, Optional

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import matplotlib as mpl
mpl.use('Agg')
from cycler import cycler
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

# ============================================================================
# Paper-Style Configuration (same as plot_paper_figures.py)
# ============================================================================

PALETTE = [
    "#1b9e77",  # teal green
    "#d95f02",  # orange
    "#7570b3",  # purple
    "#e7298a",  # pink
    "#66a61e",  # green
    "#e6ab02",  # gold
    "#a6761d",  # brown
    "#666666",  # gray
]

OKABE_ITO = {
    'black': '#000000',
    'orange': '#E69F00',
    'sky': '#56B4E9',
    'green': '#009E73',
    'yellow': '#F0E442',
    'blue': '#0072B2',
    'red': '#D55E00',
    'purple': '#CC79A7',
}

# Mode colors for reliability comparison
MODE_COLORS = {
    'ULTRA_LOW_POWER': '#009E73',    # Green - energy focused
    'BALANCED': '#0072B2',           # Blue - balanced
    'HIGH_RELIABILITY': '#D55E00',   # Red/Orange - reliability focused
}

MODE_LABELS = {
    'ULTRA_LOW_POWER': 'Ultra Low Power',
    'BALANCED': 'Balanced (Proposed)',
    'HIGH_RELIABILITY': 'High Reliability',
}

# Apply publication-grade style
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
        'grid.alpha': 0.4,
        'svg.fonttype': 'none',
        'savefig.format': 'svg',
        'figure.dpi': 300,
        'mathtext.fontset': 'stix',
        'axes.unicode_minus': False,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'savefig.facecolor': 'white',
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
        'axes.prop_cycle': cycler(color=PALETTE),
        'axes.spines.top': False,
        'axes.spines.right': False,
    })

apply_paper_style()

# Remove titles in paper mode
PAPER_MODE = True


def save_figure(fig, out_path: str, formats: List[str] = ['svg', 'pdf']):
    """Save figure in multiple formats"""
    try:
        plt.tight_layout()
    except Exception:
        pass

    # Remove titles in paper mode
    if PAPER_MODE:
        for ax in fig.axes:
            try:
                ax.set_title('')
            except Exception:
                pass

    base, ext = os.path.splitext(out_path)

    for fmt in formats:
        out_file = f"{base}.{fmt}"
        try:
            fig.savefig(out_file, bbox_inches='tight', format=fmt)
            print(f"  Saved: {out_file}")
        except Exception as e:
            print(f"  Error saving {out_file}: {e}")

    plt.close(fig)


# ============================================================================
# Figure 1: Main Comparison - PDR Bar Chart with Error Bars
# ============================================================================

def fig_main_pdr_comparison(results: Dict, output_dir: str):
    """Create PDR comparison bar chart with 95% CI error bars"""
    fig, ax = plt.subplots(figsize=(6, 4))

    modes = ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']
    statistics = results.get('statistics', {})

    if not statistics:
        print("  Warning: No statistics found for main comparison")
        return

    labels = [MODE_LABELS[m] for m in modes]
    colors = [MODE_COLORS[m] for m in modes]

    pdrs = []
    errors = []

    for mode in modes:
        s = statistics.get(mode, {})
        pdr_mean = s.get('pdr_mean', 0) * 100
        ci_lo = s.get('pdr_ci_lower', pdr_mean/100) * 100
        ci_hi = s.get('pdr_ci_upper', pdr_mean/100) * 100
        pdrs.append(pdr_mean)
        errors.append((pdr_mean - ci_lo + ci_hi - pdr_mean) / 2)

    x = np.arange(len(modes))
    bars = ax.bar(x, pdrs, yerr=errors, capsize=5, color=colors,
                  edgecolor='black', linewidth=0.5, error_kw={'elinewidth': 0.8})

    # Add value labels on bars
    for bar, pdr, err in zip(bars, pdrs, errors):
        height = bar.get_height()
        ax.annotate(f'{pdr:.1f}%',
                   xy=(bar.get_x() + bar.get_width() / 2, height + err),
                   xytext=(0, 3), textcoords="offset points",
                   ha='center', va='bottom', fontsize=9)

    ax.set_ylabel('Packet Delivery Ratio (%)')
    ax.set_xlabel('Reliability Mode')
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace(' ', '\n') for l in labels])
    ax.set_ylim(0, 110)
    ax.grid(axis='y', alpha=0.3)

    # Add significance bracket if data available
    sig_tests = results.get('significance_tests', {})
    if sig_tests:
        y_max = max(pdrs) + max(errors) + 5
        ax.plot([1, 1, 2, 2], [y_max, y_max + 2, y_max + 2, y_max], 'k-', linewidth=0.8)

        # Get p-value
        bal_vs_hr = sig_tests.get('BALANCED_vs_HIGH_RELIABILITY', {})
        p_val = bal_vs_hr.get('pdr_p_value', 1.0)
        if p_val < 0.001:
            sig_text = 'p < 0.001'
        elif p_val < 0.01:
            sig_text = 'p < 0.01'
        elif p_val < 0.05:
            sig_text = f'p = {p_val:.3f}'
        else:
            sig_text = 'ns'
        ax.text(1.5, y_max + 3, sig_text, ha='center', va='bottom', fontsize=8)

    save_figure(fig, os.path.join(output_dir, 'fig1_pdr_comparison'))


def fig_main_energy_comparison(results: Dict, output_dir: str):
    """Create energy consumption comparison bar chart"""
    fig, ax = plt.subplots(figsize=(6, 4))

    modes = ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']
    statistics = results.get('statistics', {})

    if not statistics:
        return

    labels = [MODE_LABELS[m] for m in modes]
    colors = [MODE_COLORS[m] for m in modes]

    energies = []
    errors = []

    for mode in modes:
        s = statistics.get(mode, {})
        energy_mean = s.get('energy_mean', 0) * 1000  # Convert to mJ
        ci_lo = s.get('energy_ci_lower', energy_mean/1000) * 1000
        ci_hi = s.get('energy_ci_upper', energy_mean/1000) * 1000
        energies.append(energy_mean)
        errors.append((energy_mean - ci_lo + ci_hi - energy_mean) / 2)

    x = np.arange(len(modes))
    bars = ax.bar(x, energies, yerr=errors, capsize=5, color=colors,
                  edgecolor='black', linewidth=0.5, error_kw={'elinewidth': 0.8})

    # Add value labels
    for bar, energy in zip(bars, energies):
        height = bar.get_height()
        ax.annotate(f'{energy:.1f}',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3), textcoords="offset points",
                   ha='center', va='bottom', fontsize=9)

    # Add energy savings annotation
    baseline = energies[2]  # HIGH_RELIABILITY
    for i, energy in enumerate(energies[:2]):
        savings = (baseline - energy) / baseline * 100
        if savings > 0:
            ax.annotate(f'-{savings:.0f}%',
                       xy=(i, energy / 2),
                       ha='center', va='center',
                       fontsize=8, color='white', fontweight='bold')

    ax.set_ylabel('Total Energy Consumption (mJ)')
    ax.set_xlabel('Reliability Mode')
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace(' ', '\n') for l in labels])
    ax.grid(axis='y', alpha=0.3)

    save_figure(fig, os.path.join(output_dir, 'fig2_energy_comparison'))


# ============================================================================
# Figure 3: PDR-Energy Trade-off Scatter Plot
# ============================================================================

def fig_tradeoff_scatter(results: Dict, output_dir: str):
    """Create PDR vs Energy trade-off scatter plot"""
    fig, ax = plt.subplots(figsize=(6, 5))

    modes = ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']
    raw_results = results.get('results', {})
    statistics = results.get('statistics', {})

    markers = {'ULTRA_LOW_POWER': 's', 'BALANCED': 'o', 'HIGH_RELIABILITY': '^'}

    for mode in modes:
        raw = raw_results.get(mode, [])
        if not raw:
            continue

        pdrs = [r['pdr'] * 100 for r in raw]
        energies = [r['energy'] * 1000 for r in raw]  # mJ

        # Plot individual points
        ax.scatter(energies, pdrs, c=MODE_COLORS[mode], marker=markers[mode],
                  s=40, alpha=0.5, label=MODE_LABELS[mode])

        # Plot mean with error bars
        s = statistics.get(mode, {})
        if s:
            ax.errorbar(
                s['energy_mean'] * 1000,
                s['pdr_mean'] * 100,
                xerr=(s['energy_ci_upper'] - s['energy_ci_lower']) / 2 * 1000,
                yerr=(s['pdr_ci_upper'] - s['pdr_ci_lower']) / 2 * 100,
                fmt=markers[mode], c=MODE_COLORS[mode], markersize=10,
                capsize=4, capthick=1.5, markeredgecolor='black', markeredgewidth=1
            )

    ax.set_xlabel('Total Energy Consumption (mJ)')
    ax.set_ylabel('Packet Delivery Ratio (%)')
    ax.legend(loc='lower right', frameon=True, fancybox=False, edgecolor='gray')
    ax.set_ylim(60, 105)
    ax.grid(True, alpha=0.3)

    save_figure(fig, os.path.join(output_dir, 'fig3_pdr_energy_tradeoff'))


# ============================================================================
# Figure 4: Ablation Study Bar Chart
# ============================================================================

def fig_ablation_study(results: Dict, output_dir: str):
    """Create ablation study comparison figure"""
    statistics = results.get('statistics', {})

    if not statistics:
        print("  Warning: No ablation statistics found")
        return

    # Define ablation configurations
    configs = ['Full_AERIS', 'No_SimplifiedCAS', 'No_MultiObjGateway',
               'No_AoIScheduler', 'Baseline_Only']
    labels = ['Full AERIS', '-CAS', '-Gateway', '-AoI', 'Baseline']
    colors = ['#4E79A7', '#A0CBE8', '#F28E2B', '#59A14F', '#E15759']

    # Check which configs exist
    available = [c for c in configs if c in statistics]
    if not available:
        print("  Warning: No ablation configurations found")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # PDR subplot
    ax = axes[0]
    pdrs = [statistics[c]['pdr_mean'] * 100 for c in available]
    pdr_ci = [(statistics[c]['pdr_ci_upper'] - statistics[c]['pdr_ci_lower']) / 2 * 100
              for c in available]

    x = np.arange(len(available))
    used_labels = [labels[configs.index(c)] for c in available]
    used_colors = [colors[configs.index(c)] for c in available]

    bars = ax.bar(x, pdrs, yerr=pdr_ci, capsize=4, color=used_colors,
                  edgecolor='black', linewidth=0.5)

    # Baseline reference line
    if 'Full_AERIS' in statistics:
        base_pdr = statistics['Full_AERIS']['pdr_mean'] * 100
        ax.axhline(base_pdr, color='#777', linestyle='--', linewidth=0.9, alpha=0.7)

    ax.set_ylabel('PDR (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(used_labels, rotation=15)
    ax.set_ylim(0, 110)
    ax.grid(axis='y', alpha=0.3)

    # Energy subplot
    ax = axes[1]
    energies = [statistics[c]['energy_mean'] * 1000 for c in available]
    energy_ci = [(statistics[c]['energy_ci_upper'] - statistics[c]['energy_ci_lower']) / 2 * 1000
                 for c in available]

    bars = ax.bar(x, energies, yerr=energy_ci, capsize=4, color=used_colors,
                  edgecolor='black', linewidth=0.5)

    if 'Full_AERIS' in statistics:
        base_energy = statistics['Full_AERIS']['energy_mean'] * 1000
        ax.axhline(base_energy, color='#777', linestyle='--', linewidth=0.9, alpha=0.7)

    ax.set_ylabel('Energy (mJ)')
    ax.set_xticks(x)
    ax.set_xticklabels(used_labels, rotation=15)
    ax.grid(axis='y', alpha=0.3)

    save_figure(fig, os.path.join(output_dir, 'fig4_ablation_study'))


# ============================================================================
# Figure 5: Scalability Analysis
# ============================================================================

def fig_scalability(results: Dict, output_dir: str):
    """Create scalability analysis figure"""
    statistics = results.get('statistics', {})

    if not statistics:
        print("  Warning: No scale statistics found")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Extract node counts from keys like 'nodes_50', 'nodes_100', etc.
    node_counts = []
    for key in statistics.keys():
        if key.startswith('nodes_'):
            try:
                n = int(key.split('_')[1])
                node_counts.append(n)
            except:
                pass

    node_counts = sorted(node_counts)

    if not node_counts:
        print("  Warning: No node count data found")
        return

    modes = ['BALANCED', 'HIGH_RELIABILITY']
    mode_colors_local = {'BALANCED': OKABE_ITO['blue'], 'HIGH_RELIABILITY': OKABE_ITO['red']}

    # PDR vs Node Count
    ax = axes[0]
    for mode in modes:
        pdrs = []
        errors = []
        valid_counts = []

        for n in node_counts:
            key = f'nodes_{n}'
            if key in statistics and mode in statistics[key]:
                s = statistics[key][mode]
                pdrs.append(s['pdr_mean'] * 100)
                errors.append((s['pdr_ci_upper'] - s['pdr_ci_lower']) / 2 * 100)
                valid_counts.append(n)

        if valid_counts:
            ax.errorbar(valid_counts, pdrs, yerr=errors, marker='o',
                       label=MODE_LABELS[mode], color=mode_colors_local[mode],
                       capsize=3, linewidth=1.5)

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('PDR (%)')
    ax.set_ylim(70, 105)
    ax.legend(loc='lower left', frameon=True)
    ax.grid(True, alpha=0.3)

    # Energy vs Node Count
    ax = axes[1]
    for mode in modes:
        energies = []
        errors = []
        valid_counts = []

        for n in node_counts:
            key = f'nodes_{n}'
            if key in statistics and mode in statistics[key]:
                s = statistics[key][mode]
                energies.append(s['energy_mean'] * 1000)
                errors.append((s['energy_ci_upper'] - s['energy_ci_lower']) / 2 * 1000)
                valid_counts.append(n)

        if valid_counts:
            ax.errorbar(valid_counts, energies, yerr=errors, marker='o',
                       label=MODE_LABELS[mode], color=mode_colors_local[mode],
                       capsize=3, linewidth=1.5)

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Energy (mJ)')
    ax.legend(loc='upper left', frameon=True)
    ax.grid(True, alpha=0.3)

    save_figure(fig, os.path.join(output_dir, 'fig5_scalability'))


# ============================================================================
# Figure 6: Sensitivity Analysis
# ============================================================================

def fig_sensitivity_ch_probability(results: Dict, output_dir: str):
    """Create CH probability sensitivity figure"""
    statistics = results.get('statistics', {})
    ch_stats = statistics.get('ch_probability', {})

    if not ch_stats:
        print("  Warning: No CH probability statistics found")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Extract probabilities from keys like 'p_0.03', 'p_0.05', etc.
    probs = []
    for key in ch_stats.keys():
        if key.startswith('p_'):
            try:
                p = float(key.split('_')[1])
                probs.append(p)
            except:
                pass

    probs = sorted(probs)

    if not probs:
        return

    # PDR vs CH Probability
    ax = axes[0]
    pdrs = [ch_stats[f'p_{p}']['pdr_mean'] * 100 for p in probs]
    pdr_errors = [(ch_stats[f'p_{p}']['pdr_ci_upper'] - ch_stats[f'p_{p}']['pdr_ci_lower']) / 2 * 100
                  for p in probs]

    ax.errorbar(probs, pdrs, yerr=pdr_errors, marker='o', color=OKABE_ITO['blue'],
               capsize=3, linewidth=1.5)
    ax.set_xlabel('CH Probability')
    ax.set_ylabel('PDR (%)')
    ax.set_ylim(80, 105)
    ax.grid(True, alpha=0.3)

    # Energy vs CH Probability
    ax = axes[1]
    energies = [ch_stats[f'p_{p}']['energy_mean'] * 1000 for p in probs]
    energy_errors = [(ch_stats[f'p_{p}']['energy_ci_upper'] - ch_stats[f'p_{p}']['energy_ci_lower']) / 2 * 1000
                     for p in probs]

    ax.errorbar(probs, energies, yerr=energy_errors, marker='o', color=OKABE_ITO['green'],
               capsize=3, linewidth=1.5)
    ax.set_xlabel('CH Probability')
    ax.set_ylabel('Energy (mJ)')
    ax.grid(True, alpha=0.3)

    save_figure(fig, os.path.join(output_dir, 'fig6a_sensitivity_ch_prob'))


def fig_sensitivity_gateway(results: Dict, output_dir: str):
    """Create gateway count sensitivity figure"""
    statistics = results.get('statistics', {})
    gw_stats = statistics.get('gateway_count', {})

    if not gw_stats:
        print("  Warning: No gateway count statistics found")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Extract gateway counts from keys like 'k_1', 'k_2', etc.
    counts = []
    for key in gw_stats.keys():
        if key.startswith('k_'):
            try:
                k = int(key.split('_')[1])
                counts.append(k)
            except:
                pass

    counts = sorted(counts)

    if not counts:
        return

    # PDR vs Gateway Count
    ax = axes[0]
    pdrs = [gw_stats[f'k_{k}']['pdr_mean'] * 100 for k in counts]
    pdr_errors = [(gw_stats[f'k_{k}']['pdr_ci_upper'] - gw_stats[f'k_{k}']['pdr_ci_lower']) / 2 * 100
                  for k in counts]

    ax.bar(counts, pdrs, yerr=pdr_errors, capsize=4, color=OKABE_ITO['blue'],
           edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Number of Gateways')
    ax.set_ylabel('PDR (%)')
    ax.set_ylim(80, 105)
    ax.grid(axis='y', alpha=0.3)

    # Energy vs Gateway Count
    ax = axes[1]
    energies = [gw_stats[f'k_{k}']['energy_mean'] * 1000 for k in counts]
    energy_errors = [(gw_stats[f'k_{k}']['energy_ci_upper'] - gw_stats[f'k_{k}']['energy_ci_lower']) / 2 * 1000
                     for k in counts]

    ax.bar(counts, energies, yerr=energy_errors, capsize=4, color=OKABE_ITO['green'],
           edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Number of Gateways')
    ax.set_ylabel('Energy (mJ)')
    ax.grid(axis='y', alpha=0.3)

    save_figure(fig, os.path.join(output_dir, 'fig6b_sensitivity_gateway'))


# ============================================================================
# Figure 7: Lifetime Analysis
# ============================================================================

def fig_lifetime_analysis(results: Dict, output_dir: str):
    """Create network lifetime comparison figure"""
    statistics = results.get('statistics', {})

    if not statistics:
        print("  Warning: No lifetime statistics found")
        return

    modes = ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']
    available_modes = [m for m in modes if m in statistics]

    if not available_modes:
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Network Lifetime
    ax = axes[0]
    lifetimes = [statistics[m]['lifetime_mean'] for m in available_modes]
    lifetime_errors = [statistics[m].get('lifetime_std', 0) for m in available_modes]

    x = np.arange(len(available_modes))
    colors = [MODE_COLORS[m] for m in available_modes]
    labels = [MODE_LABELS[m].replace(' ', '\n') for m in available_modes]

    bars = ax.bar(x, lifetimes, yerr=lifetime_errors, capsize=4, color=colors,
                  edgecolor='black', linewidth=0.5)

    ax.set_ylabel('Network Lifetime (rounds)')
    ax.set_xlabel('Reliability Mode')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.grid(axis='y', alpha=0.3)

    # First Node Death
    ax = axes[1]
    first_deaths = [statistics[m].get('first_death_mean', 0) for m in available_modes]
    fd_errors = [statistics[m].get('first_death_std', 0) for m in available_modes]

    bars = ax.bar(x, first_deaths, yerr=fd_errors, capsize=4, color=colors,
                  edgecolor='black', linewidth=0.5)

    ax.set_ylabel('First Node Death (round)')
    ax.set_xlabel('Reliability Mode')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.grid(axis='y', alpha=0.3)

    save_figure(fig, os.path.join(output_dir, 'fig7_lifetime_analysis'))


# ============================================================================
# Summary Table Generation
# ============================================================================

def generate_latex_table(results: Dict, output_dir: str):
    """Generate LaTeX table for paper"""
    statistics = results.get('statistics', {})

    if not statistics:
        return

    latex = r"""
\begin{table}[h]
\centering
\caption{Performance Comparison of AERIS Reliability Modes (mean $\pm$ std, 95\% CI)}
\label{tab:reliability-comparison}
\begin{tabular}{lccc}
\toprule
\textbf{Mode} & \textbf{PDR (\%)} & \textbf{Energy (mJ)} & \textbf{Lifetime (rounds)} \\
\midrule
"""

    modes = ['ULTRA_LOW_POWER', 'BALANCED', 'HIGH_RELIABILITY']
    mode_names = ['Ultra Low Power', 'Balanced (Proposed)', 'High Reliability']

    for mode, name in zip(modes, mode_names):
        if mode not in statistics:
            continue
        s = statistics[mode]
        pdr = f"{s['pdr_mean']*100:.1f} $\\pm$ {s['pdr_std']*100:.1f}"
        energy = f"{s['energy_mean']*1000:.1f} $\\pm$ {s['energy_std']*1000:.1f}"
        lifetime = f"{s['lifetime_mean']:.0f} $\\pm$ {s['lifetime_std']:.0f}"
        latex += f"{name} & {pdr} & {energy} & {lifetime} \\\\\n"

    latex += r"""
\bottomrule
\end{tabular}
\end{table}
"""

    output_path = os.path.join(output_dir, 'table_reliability_comparison.tex')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(latex)
    print(f"  Saved: {output_path}")


# ============================================================================
# Master Generation Function
# ============================================================================

def generate_all_paper_figures(results_dir: str):
    """Generate all publication-quality figures from experiment results"""
    print("\n" + "=" * 60)
    print("GENERATING PUBLICATION-QUALITY FIGURES (Paper Style)")
    print("=" * 60)

    # Create output directory
    output_dir = os.path.join(results_dir, 'paper_figures')
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    # Load final results
    results_path = os.path.join(results_dir, 'final_results.json')
    if not os.path.exists(results_path):
        print(f"ERROR: Results file not found: {results_path}")
        return

    with open(results_path, 'r', encoding='utf-8') as f:
        all_results = json.load(f)

    print("\nGenerating figures...")

    # Figure 1-2: Main Comparison
    print("\n[Main Comparison Figures]")
    main_comp = all_results.get('main_comparison', {})
    if main_comp:
        fig_main_pdr_comparison(main_comp, output_dir)
        fig_main_energy_comparison(main_comp, output_dir)
        fig_tradeoff_scatter(main_comp, output_dir)

    # Figure 4: Ablation Study
    print("\n[Ablation Study Figure]")
    ablation = all_results.get('ablation_study', {})
    if ablation:
        fig_ablation_study(ablation, output_dir)

    # Figure 5: Scalability
    print("\n[Scalability Figure]")
    scale = all_results.get('scale_analysis', {})
    if scale:
        fig_scalability(scale, output_dir)

    # Figure 6: Sensitivity Analysis
    print("\n[Sensitivity Analysis Figures]")
    sensitivity = all_results.get('sensitivity_analysis', {})
    if sensitivity:
        fig_sensitivity_ch_probability(sensitivity, output_dir)
        fig_sensitivity_gateway(sensitivity, output_dir)

    # Figure 7: Lifetime Analysis
    print("\n[Lifetime Analysis Figure]")
    lifetime = all_results.get('lifetime_analysis', {})
    if lifetime:
        fig_lifetime_analysis(lifetime, output_dir)

    # LaTeX Table
    print("\n[LaTeX Table]")
    if main_comp:
        generate_latex_table(main_comp, output_dir)

    # Copy to publication_figures for unified access
    pub_dir = os.path.join(os.path.dirname(results_dir), 'publication_figures')
    os.makedirs(pub_dir, exist_ok=True)

    for fname in os.listdir(output_dir):
        src = os.path.join(output_dir, fname)
        dst = os.path.join(pub_dir, fname)
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            print(f"  Warning: Could not copy {fname}: {e}")

    print("\n" + "=" * 60)
    print("FIGURE GENERATION COMPLETE")
    print("=" * 60)
    print(f"\nFigures saved to: {output_dir}")
    print(f"Also copied to: {pub_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate paper-style figures')
    parser.add_argument('--results-dir', type=str,
                        default='results/sota_experiments',
                        help='Directory containing experiment results')
    args = parser.parse_args()

    results_dir = os.path.join(os.path.dirname(__file__), '..', args.results_dir)
    generate_all_paper_figures(results_dir)
