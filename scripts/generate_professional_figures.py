#!/usr/bin/env python3
"""
Generate Publication-Quality Figures for AERIS Paper
3 separate high-quality figures instead of cramped mega-panel
Following Nature/Science figure standards
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

# Set professional style
plt.rcParams.update({
    'font.family': 'Arial',
    'font.size': 10,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 8,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'axes.linewidth': 1.2,
    'lines.linewidth': 1.5,
    'lines.markersize': 6,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': False,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'pdf.fonttype': 42,  # TrueType fonts for editability
    'ps.fonttype': 42,
})

# Nature-inspired color palette (colorblind-safe)
COLORS = {
    'AERIS': '#D55E00',      # Vermillion (warm, stands out)
    'LEACH': '#0072B2',      # Blue
    'HEED': '#009E73',       # Bluish green
    'PEGASIS': '#CC79A7',    # Reddish purple
    'TEEN': '#56B4E9',       # Sky blue
    'FULL': '#D55E00',
    '-CAS': '#0072B2',
    '-FAIR': '#009E73',
    '-GW': '#E69F00',        # Orange
    '-SAFETY': '#CC79A7',
}

def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def get_ablation_values(data, config, metric='pdr_end2end'):
    if config in data and isinstance(data[config], dict):
        if metric in data[config]:
            return data[config][metric].get('values', [])
    return []

def get_baseline_values(data, proto, metric='packet_delivery_ratio_end2end'):
    if proto in data and isinstance(data[proto], dict):
        if metric in data[proto]:
            d = data[proto][metric]
            if isinstance(d, dict):
                return d.get('values', [d.get('mean', 0)])
            elif isinstance(d, list):
                return d
            elif isinstance(d, (int, float)):
                return [d]  # Wrap single value in list
    return []

def get_sensitivity_values(data, key, metric='pdr_end2end'):
    if key in data and isinstance(data[key], dict):
        if metric in data[key]:
            d = data[key][metric]
            return d.get('values', []) if isinstance(d, dict) else d
    return []

def hedges_g(g1, g2):
    n1, n2 = len(g1), len(g2)
    m1, m2 = np.mean(g1), np.mean(g2)
    s1, s2 = np.var(g1, ddof=1), np.var(g2, ddof=1)
    sp = np.sqrt(((n1-1)*s1 + (n2-1)*s2) / (n1+n2-2))
    d = (m1 - m2) / sp if sp > 0 else 0
    j = 1 - 3 / (4*(n1+n2) - 9)
    return d * j

def compute_ci95(values):
    arr = np.array(values)
    return 1.96 * np.std(arr, ddof=1) / np.sqrt(len(arr))


def figure1_ablation(ablation_data, output_dir):
    """Figure 1: Ablation Study - 2x2 panels, 180mm wide"""

    fig, axes = plt.subplots(2, 2, figsize=(7.1, 6))  # ~180mm x 152mm
    fig.subplots_adjust(hspace=0.35, wspace=0.35)

    configs = ['FULL', '-CAS', '-FAIR', '-GW', '-SAFETY']
    labels = ['Full\nAERIS', 'w/o\nCAS', 'w/o\nFair', 'w/o\nGW', 'w/o\nSafety']
    colors = [COLORS[c] for c in configs]

    # (a) PDR Distribution
    ax = axes[0, 0]
    pdr_data = [get_ablation_values(ablation_data, c, 'pdr_end2end') or [0] for c in configs]

    bp = ax.boxplot(pdr_data, tick_labels=labels, patch_artist=True,
                    widths=0.6, showfliers=False)
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
        patch.set_linewidth(1.5)
    for element in ['whiskers', 'caps', 'medians']:
        plt.setp(bp[element], linewidth=1.5)
    plt.setp(bp['medians'], color='black', linewidth=2)

    ax.set_ylabel('Packet Delivery Ratio (PDR)')
    ax.set_title('(a) PDR Distribution by Configuration', fontweight='bold', pad=10)
    ax.set_ylim(0.3, 0.6)

    # (b) Energy Distribution
    ax = axes[0, 1]
    energy_data = [get_ablation_values(ablation_data, c, 'energy') or [0] for c in configs]

    bp = ax.boxplot(energy_data, tick_labels=labels, patch_artist=True,
                    widths=0.6, showfliers=False)
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
        patch.set_linewidth(1.5)
    for element in ['whiskers', 'caps', 'medians']:
        plt.setp(bp[element], linewidth=1.5)
    plt.setp(bp['medians'], color='black', linewidth=2)

    ax.set_ylabel('Total Energy Consumed (J)')
    ax.set_title('(b) Energy Consumption by Configuration', fontweight='bold', pad=10)

    # (c) Effect Sizes - Forest Plot
    ax = axes[1, 0]
    full_pdrs = get_ablation_values(ablation_data, 'FULL', 'pdr_end2end')

    effect_configs = ['-GW', '-SAFETY', '-CAS', '-FAIR']
    effect_labels = ['w/o Gateway', 'w/o Safety', 'w/o CAS', 'w/o Fairness']
    effect_sizes = []
    effect_colors = []

    for cfg in effect_configs:
        cfg_pdrs = get_ablation_values(ablation_data, cfg, 'pdr_end2end')
        if full_pdrs and cfg_pdrs:
            g = hedges_g(full_pdrs, cfg_pdrs)
            effect_sizes.append(g)
            effect_colors.append(COLORS[cfg])

    y_pos = np.arange(len(effect_sizes))
    bars = ax.barh(y_pos, effect_sizes, color=effect_colors, height=0.6, alpha=0.85)

    # Add value labels
    for i, (bar, g) in enumerate(zip(bars, effect_sizes)):
        ax.text(g + 0.1, i, f'{g:.2f}', va='center', fontsize=9, fontweight='bold')

    ax.axvline(x=0.8, color='#666666', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.text(0.82, len(effect_sizes)-0.3, 'Large\neffect', fontsize=8, color='#666666')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(effect_labels)
    ax.set_xlabel("Hedges' g (Effect Size)")
    ax.set_title("(c) Component Contribution (Effect Size)", fontweight='bold', pad=10)
    ax.set_xlim(-0.5, 5.5)

    # (d) PDR Change Percentage
    ax = axes[1, 1]
    full_mean = np.mean(full_pdrs) if full_pdrs else 0

    changes = []
    change_labels = []
    change_colors = []
    for cfg, label in zip(effect_configs, ['Gateway', 'Safety', 'CAS', 'Fairness']):
        cfg_pdrs = get_ablation_values(ablation_data, cfg, 'pdr_end2end')
        if cfg_pdrs and full_mean > 0:
            cfg_mean = np.mean(cfg_pdrs)
            pct_change = (cfg_mean - full_mean) / full_mean * 100
            changes.append(pct_change)
            change_labels.append(label)
            change_colors.append(COLORS[cfg])

    x_pos = np.arange(len(changes))
    bars = ax.bar(x_pos, changes, color=change_colors, width=0.6, alpha=0.85)

    # Add value labels
    for i, (bar, pct) in enumerate(zip(bars, changes)):
        ypos = pct - 1.5 if pct < 0 else pct + 0.5
        ax.text(i, ypos, f'{pct:.1f}%', ha='center', fontsize=9, fontweight='bold')

    ax.axhline(y=0, color='black', linewidth=1)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(change_labels)
    ax.set_ylabel('PDR Change (%)')
    ax.set_title('(d) Performance Impact of Removing Components', fontweight='bold', pad=10)
    ax.set_ylim(-30, 5)

    # Save
    for fmt in ['pdf', 'png', 'svg']:
        fig.savefig(output_dir / f'fig1_ablation.{fmt}', format=fmt,
                   bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"Saved: fig1_ablation (PDF/PNG/SVG)")


def figure2_protocol(ablation_data, baselines_data, output_dir):
    """Figure 2: Protocol Comparison - 1x2 panels, 180mm wide"""

    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.5))  # ~180mm x 89mm
    fig.subplots_adjust(wspace=0.4)

    protocols = ['AERIS', 'LEACH', 'HEED', 'PEGASIS', 'TEEN']
    colors = [COLORS[p] for p in protocols]

    # Get data
    pdr_means, pdr_cis = [], []
    energy_means, energy_cis = [], []

    # AERIS from ablation FULL
    full_pdrs = get_ablation_values(ablation_data, 'FULL', 'pdr_end2end')
    full_energies = get_ablation_values(ablation_data, 'FULL', 'energy')

    if full_pdrs:
        pdr_means.append(np.mean(full_pdrs))
        pdr_cis.append(compute_ci95(full_pdrs))
    else:
        pdr_means.append(0)
        pdr_cis.append(0)

    if full_energies:
        energy_means.append(np.mean(full_energies))
        energy_cis.append(compute_ci95(full_energies))
    else:
        energy_means.append(0)
        energy_cis.append(0)

    # Baselines
    for proto in ['LEACH', 'HEED', 'PEGASIS', 'TEEN']:
        pdrs = get_baseline_values(baselines_data, proto, 'packet_delivery_ratio_end2end')
        energies = get_baseline_values(baselines_data, proto, 'total_energy_consumed')

        if pdrs:
            pdr_means.append(np.mean(pdrs))
            pdr_cis.append(compute_ci95(pdrs))
        else:
            pdr_means.append(0)
            pdr_cis.append(0)

        if energies:
            energy_means.append(np.mean(energies))
            energy_cis.append(compute_ci95(energies))
        else:
            energy_means.append(0)
            energy_cis.append(0)

    x = np.arange(len(protocols))

    # (a) PDR Comparison
    ax = axes[0]
    bars = ax.bar(x, pdr_means, yerr=pdr_cis, capsize=4, color=colors,
                  width=0.65, alpha=0.85, error_kw={'linewidth': 1.5})

    # Highlight AERIS
    bars[0].set_edgecolor('black')
    bars[0].set_linewidth(2)

    # Add significance markers
    for i in range(1, len(protocols)):
        if pdr_means[0] > pdr_means[i]:
            ax.text(i, pdr_means[i] + pdr_cis[i] + 0.02, '***',
                   ha='center', fontsize=10, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(protocols)
    ax.set_ylabel('Packet Delivery Ratio (PDR)')
    ax.set_title('(a) End-to-End PDR Comparison', fontweight='bold', pad=10)
    ax.set_ylim(0, max(pdr_means) * 1.25)

    # Add legend for significance
    ax.text(0.98, 0.02, '*** p < 0.001', transform=ax.transAxes,
           fontsize=8, ha='right', style='italic')

    # (b) Energy Comparison
    ax = axes[1]
    bars = ax.bar(x, energy_means, yerr=energy_cis, capsize=4, color=colors,
                  width=0.65, alpha=0.85, error_kw={'linewidth': 1.5})

    bars[0].set_edgecolor('black')
    bars[0].set_linewidth(2)

    ax.set_xticks(x)
    ax.set_xticklabels(protocols)
    ax.set_ylabel('Total Energy Consumed (J)')
    ax.set_title('(b) Energy Consumption Comparison', fontweight='bold', pad=10)

    # Save
    for fmt in ['pdf', 'png', 'svg']:
        fig.savefig(output_dir / f'fig2_protocol.{fmt}', format=fmt,
                   bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"Saved: fig2_protocol (PDF/PNG/SVG)")


def figure3_sensitivity(sensitivity_data, output_dir):
    """Figure 3: Parameter Sensitivity - 2x2 panels, 180mm wide"""

    fig, axes = plt.subplots(2, 2, figsize=(7.1, 6))
    fig.subplots_adjust(hspace=0.4, wspace=0.35)

    gw_counts = [1, 2, 3]
    packet_sizes = [256, 512, 1024]

    # Line styles for different conditions
    markers = ['o', 's', '^']
    line_colors = ['#D55E00', '#0072B2', '#009E73']

    # (a) PDR vs Gateway Count (lines for packet sizes)
    ax = axes[0, 0]
    for i, ps in enumerate(packet_sizes):
        pdrs, cis = [], []
        for gw in gw_counts:
            key = f'E1.0_P{ps}_G{gw}'
            vals = get_sensitivity_values(sensitivity_data, key, 'pdr_end2end')
            if vals:
                pdrs.append(np.mean(vals))
                cis.append(compute_ci95(vals))
            else:
                pdrs.append(np.nan)
                cis.append(0)

        ax.errorbar(gw_counts, pdrs, yerr=cis, marker=markers[i],
                   color=line_colors[i], linewidth=2, markersize=8,
                   capsize=4, label=f'{ps} bits', markerfacecolor='white',
                   markeredgewidth=2)

    ax.set_xlabel('Number of Gateway Nodes')
    ax.set_ylabel('PDR')
    ax.set_title('(a) PDR vs. Gateway Count', fontweight='bold', pad=10)
    ax.set_xticks(gw_counts)
    ax.legend(title='Packet Size', loc='best', framealpha=0.9)
    ax.set_ylim(0.4, 0.65)

    # (b) PDR vs Packet Size (lines for gateway counts)
    ax = axes[0, 1]
    for i, gw in enumerate(gw_counts):
        pdrs, cis = [], []
        for ps in packet_sizes:
            key = f'E1.0_P{ps}_G{gw}'
            vals = get_sensitivity_values(sensitivity_data, key, 'pdr_end2end')
            if vals:
                pdrs.append(np.mean(vals))
                cis.append(compute_ci95(vals))
            else:
                pdrs.append(np.nan)
                cis.append(0)

        ax.errorbar(packet_sizes, pdrs, yerr=cis, marker=markers[i],
                   color=line_colors[i], linewidth=2, markersize=8,
                   capsize=4, label=f'k={gw}', markerfacecolor='white',
                   markeredgewidth=2)

    ax.set_xlabel('Packet Size (bits)')
    ax.set_ylabel('PDR')
    ax.set_title('(b) PDR vs. Packet Size', fontweight='bold', pad=10)
    ax.legend(title='Gateways', loc='best', framealpha=0.9)
    ax.set_ylim(0.4, 0.65)

    # (c) Energy vs Gateway Count
    ax = axes[1, 0]
    for i, ps in enumerate(packet_sizes):
        energies, cis = [], []
        for gw in gw_counts:
            key = f'E1.0_P{ps}_G{gw}'
            vals = get_sensitivity_values(sensitivity_data, key, 'energy')
            if vals:
                energies.append(np.mean(vals))
                cis.append(compute_ci95(vals))
            else:
                energies.append(np.nan)
                cis.append(0)

        ax.errorbar(gw_counts, energies, yerr=cis, marker=markers[i],
                   color=line_colors[i], linewidth=2, markersize=8,
                   capsize=4, label=f'{ps} bits', markerfacecolor='white',
                   markeredgewidth=2)

    ax.set_xlabel('Number of Gateway Nodes')
    ax.set_ylabel('Energy (J)')
    ax.set_title('(c) Energy vs. Gateway Count', fontweight='bold', pad=10)
    ax.set_xticks(gw_counts)
    ax.legend(title='Packet Size', loc='best', framealpha=0.9)

    # (d) PDR-Energy Tradeoff Scatter
    ax = axes[1, 1]

    for i, gw in enumerate(gw_counts):
        all_pdrs, all_energies = [], []
        for ps in packet_sizes:
            key = f'E1.0_P{ps}_G{gw}'
            pdrs = get_sensitivity_values(sensitivity_data, key, 'pdr_end2end')
            energies = get_sensitivity_values(sensitivity_data, key, 'energy')
            if pdrs and energies:
                all_pdrs.extend(pdrs)
                all_energies.extend(energies[:len(pdrs)])

        if all_pdrs and all_energies:
            ax.scatter(all_energies, all_pdrs, c=line_colors[i],
                      marker=markers[i], s=50, alpha=0.6, label=f'k={gw}',
                      edgecolors='white', linewidths=0.5)

    ax.set_xlabel('Energy (J)')
    ax.set_ylabel('PDR')
    ax.set_title('(d) PDR-Energy Trade-off', fontweight='bold', pad=10)
    ax.legend(title='Gateways', loc='best', framealpha=0.9)

    # Save
    for fmt in ['pdf', 'png', 'svg']:
        fig.savefig(output_dir / f'fig3_sensitivity.{fmt}', format=fmt,
                   bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"Saved: fig3_sensitivity (PDF/PNG/SVG)")


def main():
    results_dir = Path('results')
    output_dir = Path('for_submission')
    output_dir.mkdir(exist_ok=True)

    # Also save to publication_figures
    pub_dir = results_dir / 'publication_figures'
    pub_dir.mkdir(exist_ok=True)

    # Load data
    print("Loading experimental data...")
    ablation_data = load_json(results_dir / 'intel_ablation.json')
    sensitivity_data = load_json(results_dir / 'intel_sensitivity.json')
    baselines_data = load_json(results_dir / 'intel_baselines_all.json')

    print("\nGenerating publication-quality figures...")
    print("=" * 50)

    # Generate figures
    figure1_ablation(ablation_data, output_dir)
    figure2_protocol(ablation_data, baselines_data, output_dir)
    figure3_sensitivity(sensitivity_data, output_dir)

    # Copy to publication_figures
    import shutil
    for fig_name in ['fig1_ablation', 'fig2_protocol', 'fig3_sensitivity']:
        for fmt in ['pdf', 'png', 'svg']:
            src = output_dir / f'{fig_name}.{fmt}'
            dst = pub_dir / f'{fig_name}.{fmt}'
            if src.exists():
                shutil.copy(src, dst)

    print("=" * 50)
    print("\n✓ All figures generated successfully!")
    print("\nFigure specifications:")
    print("  - Figure 1: Ablation Study (180×152mm, 4 panels)")
    print("  - Figure 2: Protocol Comparison (180×89mm, 2 panels)")
    print("  - Figure 3: Parameter Sensitivity (180×152mm, 4 panels)")
    print("  - Resolution: 300 DPI")
    print("  - Fonts: Arial, minimum 8pt")
    print("  - Format: PDF (vector), PNG (raster), SVG")


if __name__ == '__main__':
    main()
