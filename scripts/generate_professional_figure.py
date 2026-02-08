#!/usr/bin/env python3
"""
AERIS Publication Figure - Professional Redesign

Design principles:
1. CONSISTENCY: All panels use same chart type where possible
2. SIMPLICITY: Only 2 colors (LEACH blue, AERIS red)
3. CLARITY: Large fonts, clear labels
4. PROFESSIONALISM: Grid lines, unified axes ranges
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from pathlib import Path
from scipy import stats

# Professional style - IEEE/Nature standard
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
    'axes.linewidth': 1.0,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.5,
})

# Primary colors
C_LEACH = '#2166AC'  # Deep blue
C_AERIS = '#B2182B'  # Deep red

# Multi-protocol palette (colorblind-friendly)
COLORS = {
    'AERIS': '#B2182B',
    'LEACH': '#2166AC',
    'HEED': '#1B9E77',
    'PEGASIS': '#D95F02',
    'TEEN': '#7570B3',
    'SEP': '#E7298A',
    'AERIS_energy': '#B2182B',
    'AERIS_robust': '#E66101',
}
MARKERS = {
    'AERIS': 'X',
    'LEACH': 'o',
    'HEED': 's',
    'PEGASIS': 'D',
    'TEEN': '^',
    'SEP': 'v',
    'AERIS_energy': 'o',
    'AERIS_robust': 's',
}


def load_data():
    base = Path(__file__).parent.parent / 'results'
    pub_path = base / 'publication_experiments.json'
    sota_path = base / 'sota_comparison.json'
    scale_path = base / 'scalability_experiment.json'
    ablation_path = base / 'intel_ablation.json'
    sens_path = base / 'intel_sensitivity.json'

    for p in (pub_path, sota_path, scale_path, ablation_path, sens_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing required data file: {p}")

    with open(pub_path) as f:
        pub = json.load(f)['data']
    with open(sota_path) as f:
        sota = json.load(f)
    with open(scale_path) as f:
        scale = json.load(f)
    with open(ablation_path) as f:
        ablation = json.load(f)
    with open(sens_path) as f:
        sensitivity = json.load(f)
    return {
        'publication': pub,
        'sota': sota,
        'scale': scale,
        'ablation': ablation,
        'sensitivity': sensitivity,
    }


def create_figure():
    data = load_data()
    pub = data['publication']
    sota = data['sota']
    scale = data['scale']
    ablation = data['ablation']

    # Create 3x4 grid (12 panels)
    fig = plt.figure(figsize=(14, 11))
    gs = GridSpec(3, 4, figure=fig, hspace=0.35, wspace=0.35)

    # ========== ROW 1: Core Comparison ==========

    # (a) PDR Comparison - Bar chart
    ax1 = fig.add_subplot(gs[0, 0])
    protocols = ['LEACH', 'HEED', 'PEGASIS', 'SEP', 'AERIS']
    means = [sota['protocols'][p]['pdr_mean'] * 100 for p in protocols]
    cis = [sota['protocols'][p]['pdr_ci95'] * 100 for p in protocols]
    bars = ax1.bar(range(len(protocols)), means, yerr=cis, capsize=4, width=0.65,
                   color=[COLORS[p] for p in protocols], edgecolor='black', linewidth=1)
    ax1.set_xticks(range(len(protocols)))
    ax1.set_xticklabels(protocols, rotation=20)
    ax1.set_ylabel('PDR (%)')
    ax1.set_ylim(max(80, min(means) - 6), min(100, max(means) + 6))
    ax1.set_title('(a) Protocol PDR Comparison', fontweight='bold')

    # (b) Energy Comparison - Bar chart (same style)
    ax2 = fig.add_subplot(gs[0, 1])
    means_e = [sota['protocols'][p]['energy_mean'] for p in protocols]
    stds_e = [sota['protocols'][p]['energy_std'] for p in protocols]
    ax2.bar(range(len(protocols)), means_e, yerr=stds_e, capsize=4, width=0.65,
            color=[COLORS[p] for p in protocols], edgecolor='black', linewidth=1)
    ax2.set_xticks(range(len(protocols)))
    ax2.set_xticklabels(protocols, rotation=20)
    ax2.set_ylabel('Energy (J)')
    ax2.set_title('(b) Energy Consumption', fontweight='bold')

    # (c) Scalability - Line chart
    ax3 = fig.add_subplot(gs[0, 2])
    sizes = sorted(int(s) for s in scale['summary'].keys())
    plot_protocols = ['LEACH', 'HEED', 'PEGASIS', 'TEEN', 'AERIS_energy', 'AERIS_robust']
    for proto in plot_protocols:
        means = [scale['summary'][str(s)].get(proto, {}).get('pdr_mean', np.nan) * 100 for s in sizes]
        stds = [scale['summary'][str(s)].get(proto, {}).get('pdr_std', np.nan) * 100 for s in sizes]
        label = proto.replace('AERIS_energy', 'AERIS-E').replace('AERIS_robust', 'AERIS-R')
        ax3.errorbar(sizes, means, yerr=stds, fmt=f"{MARKERS.get(proto, 'o')}-",
                     color=COLORS.get(proto, '#333333'), capsize=3,
                     markersize=5, linewidth=1.3, label=label)
    ax3.set_xlabel('Number of Nodes')
    ax3.set_ylabel('PDR (%)')
    ax3.set_title('(c) Network Scalability', fontweight='bold')
    ax3.legend(loc='lower left', ncol=2, frameon=True, fancybox=False, edgecolor='black')

    # (d) Area Size - Line chart (same style)
    ax4 = fig.add_subplot(gs[0, 3])
    areas = sorted([int(k) for k in pub['area'].keys()])
    l_area = [np.mean(pub['area'][str(a)]['L'])*100 for a in areas]
    a_area = [np.mean(pub['area'][str(a)]['A'])*100 for a in areas]
    ax4.plot(areas, l_area, 'o-', color=C_LEACH, markersize=6, linewidth=1.5, label='LEACH')
    ax4.plot(areas, a_area, 's-', color=C_AERIS, markersize=6, linewidth=1.5, label='AERIS')
    ax4.fill_between(areas, l_area, a_area, alpha=0.15, color=C_AERIS)
    ax4.set_xlabel('Area Size (m)')
    ax4.set_ylabel('PDR (%)')
    ax4.set_title('(d) Area Size Effect', fontweight='bold')
    ax4.legend(loc='lower left', frameon=True, fancybox=False, edgecolor='black')

    # ========== ROW 2: Ablation & Sensitivity ==========

    # (e) Ablation Study - Energy impact (Horizontal bar chart)
    ax5 = fig.add_subplot(gs[1, 0])
    configs = ['Full AERIS', 'w/o Gateway', 'w/o Fairness', 'w/o Safety', 'w/o CAS']
    abl_means = [
        np.mean(ablation['FULL']['energy']['values']),
        np.mean(ablation['-GW']['energy']['values']),
        np.mean(ablation['-FAIR']['energy']['values']),
        np.mean(ablation['-SAFETY']['energy']['values']),
        np.mean(ablation['-CAS']['energy']['values']),
    ]
    colors = [C_AERIS, C_AERIS, C_AERIS, C_AERIS, C_AERIS]
    alphas = [1.0, 0.7, 0.7, 0.7, 1.0]
    y_pos = np.arange(len(configs))
    for i, (m, c, a) in enumerate(zip(abl_means, colors, alphas)):
        ax5.barh(y_pos[i], m, color=c, alpha=a, edgecolor='black', linewidth=1)
    ax5.set_yticks(y_pos)
    ax5.set_yticklabels(configs)
    ax5.set_xlabel('Energy (J)')
    ax5.set_title('(e) Ablation Energy Impact', fontweight='bold')
    ax5.axvline(x=abl_means[0], color='gray', linestyle='--', linewidth=1, alpha=0.7)

    # (f) Component Contribution - Energy penalty vs Full
    ax6 = fig.add_subplot(gs[1, 1])
    full_energy = np.mean(ablation['FULL']['energy']['values'])
    gw_c = np.mean(ablation['-GW']['energy']['values']) - full_energy
    fair_c = np.mean(ablation['-FAIR']['energy']['values']) - full_energy
    safety_c = np.mean(ablation['-SAFETY']['energy']['values']) - full_energy
    cas_c = np.mean(ablation['-CAS']['energy']['values']) - full_energy
    components = ['Gateway', 'Fairness', 'Safety', 'CAS']
    contribs = [gw_c, fair_c, safety_c, cas_c]
    colors_c = [C_AERIS, C_AERIS, C_AERIS, '#333333']
    for i, (c, col) in enumerate(zip(contribs, colors_c[:len(contribs)])):
        ax6.bar(i, c, color=col, edgecolor='black', linewidth=1, alpha=0.8 if i < 3 else 1.0)
    ax6.set_xticks(range(len(components)))
    ax6.set_xticklabels(components, rotation=20)
    ax6.set_ylabel('Energy Penalty (J)')
    ax6.set_title('(f) Component Energy Penalty', fontweight='bold')
    for i, v in enumerate(contribs):
        ax6.text(i, v + (0.5 if v >= 0 else -0.8), f'{v:+.2f} J', ha='center', fontsize=8)

    # (g) CH Probability Sensitivity - Line chart
    ax7 = fig.add_subplot(gs[1, 2])
    probs = sorted([float(k) for k in pub['prob'].keys()])
    l_prob = [np.mean(pub['prob'][str(p)]['L'])*100 for p in probs]
    a_prob = [np.mean(pub['prob'][str(p)]['A'])*100 for p in probs]
    ax7.plot([p*100 for p in probs], l_prob, 'o-', color=C_LEACH, markersize=6, linewidth=1.5, label='LEACH')
    ax7.plot([p*100 for p in probs], a_prob, 's-', color=C_AERIS, markersize=6, linewidth=1.5, label='AERIS')
    ax7.set_xlabel('CH Probability (%)')
    ax7.set_ylabel('PDR (%)')
    ax7.set_title('(g) CH Probability Effect', fontweight='bold')
    ax7.legend(loc='lower right', frameon=True, fancybox=False, edgecolor='black')

    # (h) Retry Sensitivity - Dual axis line chart
    ax8 = fig.add_subplot(gs[1, 3])
    retries = sorted([int(k) for k in pub['retry'].keys()])
    pdr_ret = [np.mean(pub['retry'][str(r)]['pdr'])*100 for r in retries]
    e_ret = [np.mean(pub['retry'][str(r)]['e']) for r in retries]
    ax8.plot(retries, pdr_ret, 's-', color=C_AERIS, markersize=7, linewidth=2, label='PDR')
    ax8.set_xlabel('Max Retries')
    ax8.set_ylabel('PDR (%)', color=C_AERIS)
    ax8.tick_params(axis='y', labelcolor=C_AERIS)
    ax8b = ax8.twinx()
    ax8b.plot(retries, e_ret, 'o--', color='gray', markersize=5, linewidth=1.5, label='Energy')
    ax8b.set_ylabel('Energy (J)', color='gray')
    ax8b.tick_params(axis='y', labelcolor='gray')
    ax8.set_title('(h) Retry Count Trade-off', fontweight='bold')

    # ========== ROW 3: Environment & Statistics ==========

    # (i) Environment Types - Grouped bar chart
    ax9 = fig.add_subplot(gs[2, 0])
    envs = list(pub['env'].keys())
    x = np.arange(len(envs))
    width = 0.35
    l_env = [np.mean(pub['env'][e]['L'])*100 for e in envs]
    a_env = [np.mean(pub['env'][e]['A'])*100 for e in envs]
    ax9.bar(x - width/2, l_env, width, color=C_LEACH, edgecolor='black', linewidth=1, label='LEACH')
    ax9.bar(x + width/2, a_env, width, color=C_AERIS, edgecolor='black', linewidth=1, label='AERIS')
    ax9.set_xticks(x)
    ax9.set_xticklabels(envs)
    ax9.set_ylabel('PDR (%)')
    ax9.set_title('(i) Environment Comparison', fontweight='bold')
    ax9.legend(frameon=True, fancybox=False, edgecolor='black')

    # (j) PDR Evolution - Line chart
    ax10 = fig.add_subplot(gs[2, 1])
    rounds = pub['evol']['rd']
    l_evol = [p*100 for p in pub['evol']['L']]
    a_evol = [p*100 for p in pub['evol']['A']]
    ax10.plot(rounds, l_evol, '-', color=C_LEACH, linewidth=2, label='LEACH')
    ax10.plot(rounds, a_evol, '-', color=C_AERIS, linewidth=2, label='AERIS')
    ax10.fill_between(rounds, l_evol, a_evol, alpha=0.15, color=C_AERIS)
    ax10.set_xlabel('Round')
    ax10.set_ylabel('Cumulative PDR (%)')
    ax10.set_title('(j) PDR Evolution', fontweight='bold')
    ax10.legend(loc='lower right', frameon=True, fancybox=False, edgecolor='black')

    # (k) PDR-Energy Trade-off - Scatter plot
    ax11 = fig.add_subplot(gs[2, 2])
    for p in protocols:
        pdr_vals = np.array(sota['protocols'][p]['pdr_values']) * 100
        energy_vals = np.array(sota['protocols'][p]['energy_values'])
        ax11.scatter(energy_vals, pdr_vals, c=COLORS[p], s=26, alpha=0.6,
                     edgecolors='none', label=p)
        ax11.scatter([np.mean(energy_vals)], [np.mean(pdr_vals)], c=COLORS[p],
                     s=90, marker=MARKERS[p], edgecolors='black', linewidth=1.0, zorder=5)
    ax11.set_xlabel('Energy (J)')
    ax11.set_ylabel('PDR (%)')
    ax11.set_title('(k) PDR-Energy Trade-off', fontweight='bold')
    ax11.legend(ncol=2, frameon=True, fancybox=False, edgecolor='black')

    # (l) Effect Size Forest Plot - Professional visualization
    ax12 = fig.add_subplot(gs[2, 3])

    # Calculate effect sizes for each comparison
    comparisons = ['LEACH', 'HEED', 'PEGASIS', 'SEP']
    effect_sizes = []
    ci_lows = []
    ci_highs = []

    for baseline in comparisons:
        stat = sota['statistics'][f'AERIS_vs_{baseline}']
        effect_sizes.append(stat['cohens_d'])
        ci_lows.append(stat['cohens_d_ci_low'])
        ci_highs.append(stat['cohens_d_ci_high'])

    y_pos = np.arange(len(comparisons))
    for i, (es, lo, hi) in enumerate(zip(effect_sizes, ci_lows, ci_highs)):
        color = COLORS['AERIS'] if es > 0 else '#888888'
        ax12.errorbar(es, y_pos[i], xerr=[[es - lo], [hi - es]], fmt='D', color=color,
                     markersize=7, capsize=4, capthick=1.2, linewidth=1.2)

    ax12.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax12.axvline(x=0.8, color='green', linestyle=':', linewidth=1, alpha=0.5)
    ax12.axvline(x=-0.8, color='green', linestyle=':', linewidth=1, alpha=0.5)
    ax12.set_yticks(y_pos)
    ax12.set_yticklabels(comparisons)
    ax12.set_xlabel("Cohen's d (AERIS − baseline)")
    ax12.set_title('(l) Effect Size Analysis', fontweight='bold')

    # Main title
    fig.suptitle('AERIS: Comprehensive Experimental Analysis (n=30–60 per condition)',
                 fontsize=14, fontweight='bold', y=0.98)

    # Save
    out_dirs = [
        Path(__file__).parent.parent / 'results' / 'publication_figures',
        Path(__file__).parent.parent / 'for_submission' / 'figures',
    ]
    for out_dir in out_dirs:
        out_dir.mkdir(exist_ok=True)
        for fmt in ['pdf', 'png', 'svg']:
            out_path = out_dir / f'aeris_professional_12panel.{fmt}'
            fig.savefig(out_path, format=fmt, bbox_inches='tight', dpi=300,
                       facecolor='white', edgecolor='none')
            print(f"Saved: {out_path}")

    plt.close()
    print("\nProfessional figure generation complete!")


if __name__ == '__main__':
    create_figure()
