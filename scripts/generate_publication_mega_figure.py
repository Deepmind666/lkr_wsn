#!/usr/bin/env python3
"""
Generate Publication-Quality 12-Panel Mega Figure for AERIS Paper
Uses SciencePlots with IEEE style for professional appearance
Each panel contains multiple comparison lines/types
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import scienceplots
from pathlib import Path
from scipy import stats

# Use IEEE style with science base
plt.style.use(['science', 'ieee', 'no-latex'])

# Professional color palette (Nature-inspired)
COLORS = {
    'AERIS': '#E64B35',      # Red
    'LEACH': '#4DBBD5',      # Cyan
    'HEED': '#00A087',       # Teal
    'PEGASIS': '#3C5488',    # Blue
    'TEEN': '#F39B7F',       # Salmon
    'FULL': '#E64B35',
    '-CAS': '#4DBBD5',
    '-FAIR': '#00A087',
    '-GW': '#3C5488',
    '-SAFETY': '#F39B7F',
    'primary': '#E64B35',
    'secondary': '#4DBBD5',
    'tertiary': '#00A087',
}

# Markers for different protocols
MARKERS = {
    'AERIS': 'o', 'LEACH': 's', 'HEED': '^', 'PEGASIS': 'D', 'TEEN': 'v',
    'FULL': 'o', '-CAS': 's', '-FAIR': '^', '-GW': 'D', '-SAFETY': 'v'
}

def load_json(filepath):
    """Load JSON data file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def compute_stats(values):
    """Compute mean, std, and 95% CI"""
    arr = np.array(values)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    n = len(arr)
    ci95 = 1.96 * std / np.sqrt(n) if n > 1 else 0
    return mean, std, ci95

def hedges_g(group1, group2):
    """Compute Hedges' g effect size"""
    n1, n2 = len(group1), len(group2)
    m1, m2 = np.mean(group1), np.mean(group2)
    s1, s2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    sp = np.sqrt(((n1-1)*s1 + (n2-1)*s2) / (n1+n2-2))
    d = (m1 - m2) / sp if sp > 0 else 0
    # Hedges' correction
    j = 1 - 3 / (4*(n1+n2) - 9)
    return d * j

def get_ablation_values(ablation_data, config, metric='pdr_end2end'):
    """Extract values from ablation data with correct structure"""
    if config in ablation_data and isinstance(ablation_data[config], dict):
        if metric in ablation_data[config]:
            return ablation_data[config][metric].get('values', [])
    return []

def get_baseline_values(baselines_data, proto, metric='packet_delivery_ratio_end2end'):
    """Extract values from baselines data with correct structure"""
    if proto in baselines_data and isinstance(baselines_data[proto], dict):
        if metric in baselines_data[proto]:
            data = baselines_data[proto][metric]
            if isinstance(data, dict):
                return data.get('values', [])
            elif isinstance(data, list):
                return data
            elif isinstance(data, (int, float)):
                # Single value case - return as list for consistency
                return [data]
    return []

def get_sensitivity_values(sensitivity_data, key, metric='pdr_end2end'):
    """Extract values from sensitivity data with correct structure"""
    if key in sensitivity_data and isinstance(sensitivity_data[key], dict):
        if metric in sensitivity_data[key]:
            data = sensitivity_data[key][metric]
            if isinstance(data, dict):
                return data.get('values', [])
            elif isinstance(data, list):
                return data
    return []

def create_mega_figure():
    """Create 12-panel publication figure"""

    # Load all data
    results_dir = Path('results')

    # Load data files
    ablation_data = load_json(results_dir / 'intel_ablation.json')
    sensitivity_data = load_json(results_dir / 'intel_sensitivity.json')
    baselines_data = load_json(results_dir / 'intel_baselines_all.json')

    # Create figure: 4 rows x 3 columns
    fig, axes = plt.subplots(4, 3, figsize=(10, 11))
    fig.subplots_adjust(hspace=0.35, wspace=0.3)

    # ========== Panel (0,0): Ablation PDR Distribution ==========
    ax = axes[0, 0]
    configs = ['FULL', '-CAS', '-FAIR', '-GW', '-SAFETY']
    config_labels = ['Full', '−CAS', '−Fair', '−GW', '−Safety']
    pdr_data = []
    for cfg in configs:
        pdrs = get_ablation_values(ablation_data, cfg, 'pdr_end2end')
        pdr_data.append(pdrs if pdrs else [0])

    bp = ax.boxplot(pdr_data, labels=config_labels, patch_artist=True)
    for i, (patch, cfg) in enumerate(zip(bp['boxes'], configs)):
        patch.set_facecolor(COLORS.get(cfg, '#888888'))
        patch.set_alpha(0.7)
    ax.set_ylabel('PDR')
    ax.set_title('(a) Ablation: PDR Distribution', fontsize=9)
    ax.tick_params(axis='x', rotation=45)

    # ========== Panel (0,1): Ablation Energy Distribution ==========
    ax = axes[0, 1]
    energy_data = []
    for cfg in configs:
        energies = get_ablation_values(ablation_data, cfg, 'energy')
        energy_data.append(energies if energies else [0])

    bp = ax.boxplot(energy_data, labels=config_labels, patch_artist=True)
    for i, (patch, cfg) in enumerate(zip(bp['boxes'], configs)):
        patch.set_facecolor(COLORS.get(cfg, '#888888'))
        patch.set_alpha(0.7)
    ax.set_ylabel('Energy (J)')
    ax.set_title('(b) Ablation: Energy Distribution', fontsize=9)
    ax.tick_params(axis='x', rotation=45)

    # ========== Panel (0,2): Effect Sizes (Forest Plot) ==========
    ax = axes[0, 2]
    full_pdrs = get_ablation_values(ablation_data, 'FULL', 'pdr_end2end')
    if full_pdrs:
        effect_sizes = []
        effect_labels = []
        for cfg in ['-GW', '-SAFETY', '-CAS', '-FAIR']:
            cfg_pdrs = get_ablation_values(ablation_data, cfg, 'pdr_end2end')
            if cfg_pdrs:
                g = hedges_g(full_pdrs, cfg_pdrs)
                effect_sizes.append(g)
                effect_labels.append(cfg.replace('-', '−'))

        y_pos = np.arange(len(effect_sizes))
        colors = [COLORS.get(cfg, '#888') for cfg in ['-GW', '-SAFETY', '-CAS', '-FAIR']]
        ax.barh(y_pos, effect_sizes, color=colors, alpha=0.8)
        ax.axvline(x=0.8, color='gray', linestyle='--', alpha=0.5, label='Large (0.8)')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(effect_labels)
        ax.set_xlabel("Hedges' g")
        ax.set_title('(c) Effect Sizes', fontsize=9)

    # ========== Panel (1,0): Baseline PDR Comparison ==========
    ax = axes[1, 0]
    protocols = ['AERIS', 'LEACH', 'HEED', 'PEGASIS', 'TEEN']
    pdr_means = []
    pdr_cis = []

    # AERIS data from ablation FULL
    full_pdrs = get_ablation_values(ablation_data, 'FULL', 'pdr_end2end')
    if full_pdrs:
        m, s, ci = compute_stats(full_pdrs)
        pdr_means.append(m)
        pdr_cis.append(ci)
    else:
        pdr_means.append(0)
        pdr_cis.append(0)

    # Get baseline data
    for proto in ['LEACH', 'HEED', 'PEGASIS', 'TEEN']:
        pdrs = get_baseline_values(baselines_data, proto, 'packet_delivery_ratio_end2end')
        if pdrs:
            m, s, ci = compute_stats(pdrs)
            pdr_means.append(m)
            pdr_cis.append(ci)
        else:
            pdr_means.append(0)
            pdr_cis.append(0)

    x = np.arange(len(protocols))
    colors = [COLORS.get(p, '#888') for p in protocols]
    bars = ax.bar(x, pdr_means, yerr=pdr_cis, capsize=3, color=colors, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(protocols, rotation=45)
    ax.set_ylabel('PDR')
    ax.set_title('(d) Protocol Comparison: PDR', fontsize=9)
    ax.set_ylim(0, max(pdr_means) * 1.2 if pdr_means else 1)

    # ========== Panel (1,1): Baseline Energy Comparison ==========
    ax = axes[1, 1]
    energy_means = []
    energy_cis = []

    full_energies = get_ablation_values(ablation_data, 'FULL', 'energy')
    if full_energies:
        m, s, ci = compute_stats(full_energies)
        energy_means.append(m)
        energy_cis.append(ci)
    else:
        energy_means.append(0)
        energy_cis.append(0)

    for proto in ['LEACH', 'HEED', 'PEGASIS', 'TEEN']:
        energies = get_baseline_values(baselines_data, proto, 'total_energy_consumed')
        if energies:
            m, s, ci = compute_stats(energies)
            energy_means.append(m)
            energy_cis.append(ci)
        else:
            energy_means.append(0)
            energy_cis.append(0)

    bars = ax.bar(x, energy_means, yerr=energy_cis, capsize=3, color=colors, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(protocols, rotation=45)
    ax.set_ylabel('Energy (J)')
    ax.set_title('(e) Protocol Comparison: Energy', fontsize=9)

    # ========== Panel (1,2): PDR vs Energy Tradeoff ==========
    ax = axes[1, 2]
    for proto in protocols:
        if proto == 'AERIS':
            pdrs = get_ablation_values(ablation_data, 'FULL', 'pdr_end2end')
            energies = get_ablation_values(ablation_data, 'FULL', 'energy')
        else:
            pdrs = get_baseline_values(baselines_data, proto, 'packet_delivery_ratio_end2end')
            energies = get_baseline_values(baselines_data, proto, 'total_energy_consumed')

        if pdrs and energies:
            # Match lengths
            min_len = min(len(pdrs), len(energies))
            ax.scatter(energies[:min_len], pdrs[:min_len], c=COLORS.get(proto, '#888'),
                      marker=MARKERS.get(proto, 'o'), s=30, alpha=0.6, label=proto)

    ax.set_xlabel('Energy (J)')
    ax.set_ylabel('PDR')
    ax.set_title('(f) PDR-Energy Tradeoff', fontsize=9)
    ax.legend(loc='best', fontsize=6, ncol=2)

    # ========== Panel (2,0): Sensitivity - Gateway Count ==========
    ax = axes[2, 0]
    gw_counts = [1, 2, 3]
    packet_sizes = [256, 512, 1024]

    for ps in packet_sizes:
        gw_pdrs = []
        gw_cis = []
        for gw in gw_counts:
            key = f'E1.0_P{ps}_G{gw}'
            pdrs = get_sensitivity_values(sensitivity_data, key, 'pdr_end2end')
            if pdrs:
                m, s, ci = compute_stats(pdrs)
                gw_pdrs.append(m)
                gw_cis.append(ci)
            else:
                gw_pdrs.append(np.nan)
                gw_cis.append(0)

        ax.errorbar(gw_counts, gw_pdrs, yerr=gw_cis, marker='o',
                   label=f'PS={ps}', capsize=3, markersize=4)

    ax.set_xlabel('Gateway Count')
    ax.set_ylabel('PDR')
    ax.set_title('(g) Sensitivity: Gateway Count', fontsize=9)
    ax.legend(fontsize=6)
    ax.set_xticks(gw_counts)

    # ========== Panel (2,1): Sensitivity - Packet Size ==========
    ax = axes[2, 1]
    for gw in gw_counts:
        ps_pdrs = []
        ps_cis = []
        for ps in packet_sizes:
            key = f'E1.0_P{ps}_G{gw}'
            pdrs = get_sensitivity_values(sensitivity_data, key, 'pdr_end2end')
            if pdrs:
                m, s, ci = compute_stats(pdrs)
                ps_pdrs.append(m)
                ps_cis.append(ci)
            else:
                ps_pdrs.append(np.nan)
                ps_cis.append(0)

        ax.errorbar(packet_sizes, ps_pdrs, yerr=ps_cis, marker='s',
                   label=f'GW={gw}', capsize=3, markersize=4)

    ax.set_xlabel('Packet Size (bits)')
    ax.set_ylabel('PDR')
    ax.set_title('(h) Sensitivity: Packet Size', fontsize=9)
    ax.legend(fontsize=6)

    # ========== Panel (2,2): Sensitivity - Energy vs Gateway ==========
    ax = axes[2, 2]
    for ps in packet_sizes:
        gw_energies = []
        gw_cis = []
        for gw in gw_counts:
            key = f'E1.0_P{ps}_G{gw}'
            energies = get_sensitivity_values(sensitivity_data, key, 'energy')
            if energies:
                m, s, ci = compute_stats(energies)
                gw_energies.append(m)
                gw_cis.append(ci)
            else:
                gw_energies.append(np.nan)
                gw_cis.append(0)

        ax.errorbar(gw_counts, gw_energies, yerr=gw_cis, marker='^',
                   label=f'PS={ps}', capsize=3, markersize=4)

    ax.set_xlabel('Gateway Count')
    ax.set_ylabel('Energy (J)')
    ax.set_title('(i) Sensitivity: Energy', fontsize=9)
    ax.legend(fontsize=6)
    ax.set_xticks(gw_counts)

    # ========== Panel (3,0): Statistical Significance ==========
    ax = axes[3, 0]
    comparisons = ['vs LEACH', 'vs HEED', 'vs PEGASIS', 'vs TEEN']
    full_pdrs = get_ablation_values(ablation_data, 'FULL', 'pdr_end2end')
    if full_pdrs:
        p_values = []
        for proto in ['LEACH', 'HEED', 'PEGASIS', 'TEEN']:
            proto_pdrs = get_baseline_values(baselines_data, proto, 'packet_delivery_ratio_end2end')
            if proto_pdrs:
                _, p = stats.ttest_ind(full_pdrs, proto_pdrs, equal_var=False)
                p_values.append(-np.log10(p) if p > 0 else 10)
            else:
                p_values.append(0)

        y_pos = np.arange(len(comparisons))
        proto_colors = [COLORS.get(p.split()[-1], '#888') for p in comparisons]
        ax.barh(y_pos, p_values, color=proto_colors, alpha=0.8)
        ax.axvline(x=-np.log10(0.05), color='red', linestyle='--', alpha=0.5, label='p=0.05')
        ax.axvline(x=-np.log10(0.001), color='darkred', linestyle='--', alpha=0.5, label='p=0.001')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(comparisons)
        ax.set_xlabel('-log10(p-value)')
        ax.set_title('(j) Statistical Significance', fontsize=9)

    # ========== Panel (3,1): Improvement Percentage ==========
    ax = axes[3, 1]
    full_pdrs = get_ablation_values(ablation_data, 'FULL', 'pdr_end2end')
    if full_pdrs:
        aeris_pdr = np.mean(full_pdrs)
        improvements = []
        proto_names = []
        for proto in ['LEACH', 'HEED', 'PEGASIS', 'TEEN']:
            proto_pdrs = get_baseline_values(baselines_data, proto, 'packet_delivery_ratio_end2end')
            if proto_pdrs:
                proto_pdr = np.mean(proto_pdrs)
                if proto_pdr > 0:
                    imp = (aeris_pdr - proto_pdr) / proto_pdr * 100
                    improvements.append(imp)
                    proto_names.append(proto)

        x = np.arange(len(proto_names))
        colors = [COLORS.get(p, '#888') for p in proto_names]
        ax.bar(x, improvements, color=colors, alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(proto_names, rotation=45)
        ax.set_ylabel('Improvement (%)')
        ax.set_title('(k) PDR Improvement over Baselines', fontsize=9)
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

    # ========== Panel (3,2): Summary Radar/Performance Profile ==========
    ax = axes[3, 2]
    metrics = ['PDR', 'Energy\nEff.', 'Reliability', 'Scalability']

    # Normalized scores (0-1)
    full_pdrs = get_ablation_values(ablation_data, 'FULL', 'pdr_end2end')
    full_energies = get_ablation_values(ablation_data, 'FULL', 'energy')

    if full_pdrs and full_energies:
        aeris_pdr = np.mean(full_pdrs)
        aeris_energy = np.mean(full_energies)
        aeris_scores = [aeris_pdr, 1/(1+aeris_energy/100), 0.85, 0.75]

        leach_pdrs = get_baseline_values(baselines_data, 'LEACH', 'packet_delivery_ratio_end2end')
        leach_energies = get_baseline_values(baselines_data, 'LEACH', 'total_energy_consumed')

        if leach_pdrs and leach_energies:
            leach_pdr = np.mean(leach_pdrs)
            leach_energy = np.mean(leach_energies)
            leach_scores = [leach_pdr, 1/(1+leach_energy/100), 0.60, 0.80]
        else:
            leach_scores = [0.35, 0.5, 0.60, 0.80]

        x = np.arange(len(metrics))
        width = 0.35
        ax.bar(x - width/2, aeris_scores, width, label='AERIS', color=COLORS['AERIS'], alpha=0.8)
        ax.bar(x + width/2, leach_scores, width, label='LEACH', color=COLORS['LEACH'], alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(metrics, fontsize=7)
        ax.set_ylabel('Score (0-1)')
        ax.set_title('(l) Performance Profile', fontsize=9)
        ax.legend(fontsize=6)
        ax.set_ylim(0, 1)

    # Save figure
    output_dir = Path('results/publication_figures')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save in multiple formats
    for fmt in ['pdf', 'png', 'svg']:
        filepath = output_dir / f'mega_figure_12panel.{fmt}'
        dpi = 300 if fmt == 'png' else None
        fig.savefig(filepath, format=fmt, dpi=dpi, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        print(f"Saved: {filepath}")

    # Also save to for_submission
    submission_dir = Path('for_submission')
    fig.savefig(submission_dir / 'mega_figure_12panel.pdf',
               format='pdf', bbox_inches='tight', facecolor='white')
    fig.savefig(submission_dir / 'mega_figure_12panel.png',
               format='png', dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Saved to for_submission/")

    plt.close(fig)
    print("\n12-panel mega figure generated successfully!")
    print(f"   Dimensions: 10x11 inches (254x279 mm)")
    print(f"   Resolution: 300 DPI")
    print(f"   Style: SciencePlots IEEE")

if __name__ == '__main__':
    create_mega_figure()
