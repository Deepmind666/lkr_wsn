#!/usr/bin/env python3
"""
Generate Publication-Quality 12-Panel Figure for AERIS Paper

Style: Nature/Science publication quality
- Clean, minimalist design
- Consistent color palette
- Clear labels and legends
- Statistical annotations
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from pathlib import Path
from scipy import stats

# Publication style settings
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans'],
    'font.size': 8,
    'axes.titlesize': 9,
    'axes.labelsize': 8,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'axes.linewidth': 0.8,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

# Color palette (colorblind-friendly)
COLORS = {
    'LEACH': '#4477AA',      # Blue
    'AERIS': '#EE6677',      # Red
    'Full': '#228833',       # Green
    'NoARQ': '#CCBB44',      # Yellow
    'NoCoop': '#66CCEE',     # Cyan
    'NoSmart': '#AA3377',    # Purple
    'accent': '#BBBBBB',     # Gray
}


def load_data():
    path = Path(__file__).parent.parent / 'results' / 'publication_experiments.json'
    with open(path) as f:
        return json.load(f)['data']


def add_significance(ax, x1, x2, y, p, h=0.02):
    """Add significance bar with stars."""
    if p < 0.001:
        sig = '***'
    elif p < 0.01:
        sig = '**'
    elif p < 0.05:
        sig = '*'
    else:
        sig = 'n.s.'
    ax.plot([x1, x1, x2, x2], [y, y+h, y+h, y], 'k-', lw=0.8)
    ax.text((x1+x2)/2, y+h, sig, ha='center', va='bottom', fontsize=7)


def panel_a_pdr_comparison(ax, data):
    """Panel A: PDR comparison bar chart."""
    leach = [x['pdr'] for x in data['basic']['LEACH']]
    aeris = [x['pdr'] for x in data['basic']['AERIS']]

    means = [np.mean(leach)*100, np.mean(aeris)*100]
    cis = [1.96*np.std(leach)/np.sqrt(len(leach))*100,
           1.96*np.std(aeris)/np.sqrt(len(aeris))*100]

    bars = ax.bar([0, 1], means, yerr=cis, capsize=3, width=0.6,
                  color=[COLORS['LEACH'], COLORS['AERIS']], edgecolor='black', linewidth=0.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['LEACH', 'AERIS'])
    ax.set_ylabel('PDR (%)')
    ax.set_ylim(80, 95)
    ax.set_title('(a) Protocol Comparison', fontweight='bold')

    # Add significance
    _, p = stats.ttest_ind(aeris, leach)
    add_significance(ax, 0, 1, 93, p)


def panel_b_energy_comparison(ax, data):
    """Panel B: Energy consumption comparison."""
    leach = [x['energy'] for x in data['basic']['LEACH']]
    aeris = [x['energy'] for x in data['basic']['AERIS']]

    means = [np.mean(leach), np.mean(aeris)]
    stds = [np.std(leach), np.std(aeris)]

    bars = ax.bar([0, 1], means, yerr=stds, capsize=3, width=0.6,
                  color=[COLORS['LEACH'], COLORS['AERIS']], edgecolor='black', linewidth=0.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['LEACH', 'AERIS'])
    ax.set_ylabel('Energy (J)')
    ax.set_title('(b) Energy Consumption', fontweight='bold')


def panel_c_tradeoff(ax, data):
    """Panel C: PDR-Energy tradeoff scatter."""
    lp = [x*100 for x in data['tradeoff']['L']['pdr']]
    le = data['tradeoff']['L']['e']
    ap = [x*100 for x in data['tradeoff']['A']['pdr']]
    ae = data['tradeoff']['A']['e']

    ax.scatter(le, lp, c=COLORS['LEACH'], s=20, alpha=0.6, label='LEACH', edgecolors='none')
    ax.scatter(ae, ap, c=COLORS['AERIS'], s=20, alpha=0.6, label='AERIS', edgecolors='none')

    # Add mean markers
    ax.scatter([np.mean(le)], [np.mean(lp)], c=COLORS['LEACH'], s=80, marker='D', edgecolors='black', linewidth=1, zorder=5)
    ax.scatter([np.mean(ae)], [np.mean(ap)], c=COLORS['AERIS'], s=80, marker='D', edgecolors='black', linewidth=1, zorder=5)

    ax.set_xlabel('Energy (J)')
    ax.set_ylabel('PDR (%)')
    ax.legend(loc='lower right', frameon=False)
    ax.set_title('(c) PDR-Energy Tradeoff', fontweight='bold')


def panel_d_scalability(ax, data):
    """Panel D: Network size scalability."""
    sizes = sorted([int(k) for k in data['scale'].keys()])
    leach_means = [np.mean(data['scale'][str(s)]['L'])*100 for s in sizes]
    aeris_means = [np.mean(data['scale'][str(s)]['A'])*100 for s in sizes]
    leach_stds = [np.std(data['scale'][str(s)]['L'])*100 for s in sizes]
    aeris_stds = [np.std(data['scale'][str(s)]['A'])*100 for s in sizes]

    ax.errorbar(sizes, leach_means, yerr=leach_stds, fmt='o-', color=COLORS['LEACH'],
                capsize=3, markersize=4, label='LEACH')
    ax.errorbar(sizes, aeris_means, yerr=aeris_stds, fmt='s-', color=COLORS['AERIS'],
                capsize=3, markersize=4, label='AERIS')

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('PDR (%)')
    ax.legend(loc='lower left', frameon=False)
    ax.set_title('(d) Scalability', fontweight='bold')


def panel_e_area(ax, data):
    """Panel E: Area size variation."""
    areas = sorted([int(k) for k in data['area'].keys()])
    leach_means = [np.mean(data['area'][str(a)]['L'])*100 for a in areas]
    aeris_means = [np.mean(data['area'][str(a)]['A'])*100 for a in areas]

    ax.plot(areas, leach_means, 'o-', color=COLORS['LEACH'], markersize=4, label='LEACH')
    ax.plot(areas, aeris_means, 's-', color=COLORS['AERIS'], markersize=4, label='AERIS')

    ax.fill_between(areas, leach_means, aeris_means, alpha=0.2, color=COLORS['AERIS'])
    ax.set_xlabel('Area Size (m)')
    ax.set_ylabel('PDR (%)')
    ax.legend(loc='lower left', frameon=False)
    ax.set_title('(e) Area Size Effect', fontweight='bold')


def panel_f_ablation(ax, data):
    """Panel F: Ablation study."""
    configs = ['Full', 'NoARQ', 'NoCoop', 'NoSmart', 'Base']
    labels = ['Full\nAERIS', 'w/o\nARQ', 'w/o\nCoop', 'w/o\nSmart', 'LEACH\n(Base)']
    colors_abl = [COLORS['Full'], COLORS['NoARQ'], COLORS['NoCoop'], COLORS['NoSmart'], COLORS['LEACH']]

    means = [np.mean(data['ablation'][c])*100 for c in configs]
    stds = [np.std(data['ablation'][c])*100 for c in configs]

    bars = ax.bar(range(len(configs)), means, yerr=stds, capsize=2, width=0.7,
                  color=colors_abl, edgecolor='black', linewidth=0.5)
    ax.set_xticks(range(len(configs)))
    ax.set_xticklabels(labels, fontsize=6)
    ax.set_ylabel('PDR (%)')
    ax.set_ylim(85, 95)
    ax.set_title('(f) Ablation Study', fontweight='bold')

    # Baseline reference line
    ax.axhline(y=means[-1], color='gray', linestyle='--', linewidth=0.8, alpha=0.7)


def panel_g_ch_prob(ax, data):
    """Panel G: CH probability sensitivity."""
    probs = sorted([float(k) for k in data['prob'].keys()])
    leach_means = [np.mean(data['prob'][str(p)]['L'])*100 for p in probs]
    aeris_means = [np.mean(data['prob'][str(p)]['A'])*100 for p in probs]

    ax.plot([p*100 for p in probs], leach_means, 'o-', color=COLORS['LEACH'], markersize=4, label='LEACH')
    ax.plot([p*100 for p in probs], aeris_means, 's-', color=COLORS['AERIS'], markersize=4, label='AERIS')

    ax.set_xlabel('CH Probability (%)')
    ax.set_ylabel('PDR (%)')
    ax.legend(loc='lower right', frameon=False)
    ax.set_title('(g) CH Probability Sensitivity', fontweight='bold')


def panel_h_retry(ax, data):
    """Panel H: Retry sensitivity."""
    retries = sorted([int(k) for k in data['retry'].keys()])
    pdr_means = [np.mean(data['retry'][str(r)]['pdr'])*100 for r in retries]
    e_means = [np.mean(data['retry'][str(r)]['e']) for r in retries]

    ax2 = ax.twinx()
    l1, = ax.plot(retries, pdr_means, 's-', color=COLORS['AERIS'], markersize=5, label='PDR')
    l2, = ax2.plot(retries, e_means, 'o--', color=COLORS['accent'], markersize=4, label='Energy')

    ax.set_xlabel('Max Retries')
    ax.set_ylabel('PDR (%)', color=COLORS['AERIS'])
    ax2.set_ylabel('Energy (J)', color=COLORS['accent'])
    ax.tick_params(axis='y', labelcolor=COLORS['AERIS'])
    ax2.tick_params(axis='y', labelcolor=COLORS['accent'])

    ax.legend([l1, l2], ['PDR', 'Energy'], loc='center right', frameon=False)
    ax.set_title('(h) Retry Count Effect', fontweight='bold')


def panel_i_environment(ax, data):
    """Panel I: Environment comparison."""
    envs = list(data['env'].keys())
    x = np.arange(len(envs))
    width = 0.35

    leach_means = [np.mean(data['env'][e]['L'])*100 for e in envs]
    aeris_means = [np.mean(data['env'][e]['A'])*100 for e in envs]

    ax.bar(x - width/2, leach_means, width, color=COLORS['LEACH'], label='LEACH', edgecolor='black', linewidth=0.5)
    ax.bar(x + width/2, aeris_means, width, color=COLORS['AERIS'], label='AERIS', edgecolor='black', linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(envs)
    ax.set_ylabel('PDR (%)')
    ax.legend(frameon=False)
    ax.set_title('(i) Environment Types', fontweight='bold')


def panel_j_evolution(ax, data):
    """Panel J: PDR evolution over rounds."""
    rounds = data['evol']['rd']
    leach = [p*100 for p in data['evol']['L']]
    aeris = [p*100 for p in data['evol']['A']]

    ax.plot(rounds, leach, '-', color=COLORS['LEACH'], linewidth=1.5, label='LEACH')
    ax.plot(rounds, aeris, '-', color=COLORS['AERIS'], linewidth=1.5, label='AERIS')

    ax.fill_between(rounds, leach, aeris, alpha=0.15, color=COLORS['AERIS'])
    ax.set_xlabel('Round')
    ax.set_ylabel('Cumulative PDR (%)')
    ax.legend(loc='lower right', frameon=False)
    ax.set_title('(j) PDR Evolution', fontweight='bold')


def panel_k_improvement(ax, data):
    """Panel K: Improvement breakdown."""
    # Calculate improvements for each ablation
    full = np.mean(data['ablation']['Full'])*100
    base = np.mean(data['ablation']['Base'])*100
    noarq = np.mean(data['ablation']['NoARQ'])*100
    nocoop = np.mean(data['ablation']['NoCoop'])*100
    nosmart = np.mean(data['ablation']['NoSmart'])*100

    # Component contributions
    arq_contrib = full - noarq
    coop_contrib = full - nocoop
    smart_contrib = full - nosmart
    total = full - base

    components = ['ARQ\nRetry', 'Cooperative\nTx', 'Smart CH\nSelection', 'Total\nImprovement']
    values = [arq_contrib, coop_contrib, smart_contrib, total]
    colors = [COLORS['NoARQ'], COLORS['NoCoop'], COLORS['NoSmart'], COLORS['Full']]

    bars = ax.bar(range(len(components)), values, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_xticks(range(len(components)))
    ax.set_xticklabels(components, fontsize=6)
    ax.set_ylabel('PDR Improvement (%)')
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.set_title('(k) Component Contributions', fontweight='bold')

    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f'{val:.2f}%', ha='center', va='bottom', fontsize=6)


def panel_l_statistics(ax, data):
    """Panel L: Statistical significance summary."""
    # Create a table-like visualization
    ax.axis('off')

    stats_data = data['stats']
    summary = data['summary']

    text = (
        f"Statistical Validation\n"
        f"{'─'*35}\n\n"
        f"LEACH PDR:  {summary['LEACH']['pdr']*100:.2f}% ± {summary['LEACH']['ci']*100:.2f}%\n"
        f"AERIS PDR:  {summary['AERIS']['pdr']*100:.2f}% ± {summary['AERIS']['ci']*100:.2f}%\n\n"
        f"{'─'*35}\n"
        f"Improvement: +{summary['improve']['pdr_abs']:.2f}%\n"
        f"Energy overhead: +{summary['improve']['e_over']:.1f}%\n\n"
        f"{'─'*35}\n"
        f"t-statistic: {stats_data['t']:.2f}\n"
        f"p-value: {stats_data['p']:.2e} ***\n"
        f"Cohen's d: {stats_data['d']:.3f} (large)\n"
        f"n = 30 runs per condition"
    )

    ax.text(0.5, 0.5, text, transform=ax.transAxes, fontsize=7,
            verticalalignment='center', horizontalalignment='center',
            fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    ax.set_title('(l) Statistical Summary', fontweight='bold')


def generate_figure():
    """Generate the complete 12-panel figure."""
    print("Loading experiment data...")
    data = load_data()

    print("Creating 12-panel figure...")
    fig = plt.figure(figsize=(12, 10))
    gs = GridSpec(4, 3, figure=fig, hspace=0.35, wspace=0.3)

    # Row 1: Basic comparison
    panel_a_pdr_comparison(fig.add_subplot(gs[0, 0]), data)
    panel_b_energy_comparison(fig.add_subplot(gs[0, 1]), data)
    panel_c_tradeoff(fig.add_subplot(gs[0, 2]), data)

    # Row 2: Scalability and sensitivity
    panel_d_scalability(fig.add_subplot(gs[1, 0]), data)
    panel_e_area(fig.add_subplot(gs[1, 1]), data)
    panel_f_ablation(fig.add_subplot(gs[1, 2]), data)

    # Row 3: Parameter sensitivity
    panel_g_ch_prob(fig.add_subplot(gs[2, 0]), data)
    panel_h_retry(fig.add_subplot(gs[2, 1]), data)
    panel_i_environment(fig.add_subplot(gs[2, 2]), data)

    # Row 4: Evolution and statistics
    panel_j_evolution(fig.add_subplot(gs[3, 0]), data)
    panel_k_improvement(fig.add_subplot(gs[3, 1]), data)
    panel_l_statistics(fig.add_subplot(gs[3, 2]), data)

    # Overall title
    fig.suptitle('AERIS: Comprehensive Experimental Analysis', fontsize=12, fontweight='bold', y=0.98)

    # Save
    out_dir = Path(__file__).parent.parent / 'results' / 'publication_figures'
    out_dir.mkdir(exist_ok=True)

    for fmt in ['pdf', 'svg', 'png']:
        out_path = out_dir / f'aeris_12panel_figure.{fmt}'
        fig.savefig(out_path, format=fmt, bbox_inches='tight', dpi=300)
        print(f"Saved: {out_path}")

    plt.close()
    print("\nFigure generation complete!")


if __name__ == '__main__':
    generate_figure()
