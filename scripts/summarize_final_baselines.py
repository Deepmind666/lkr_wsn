#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
import csv
import matplotlib as mpl
import matplotlib.pyplot as plt

# IEEE/ACM-friendly rcParams
mpl.rcParams.update({
    'font.family': 'Times New Roman',
    'font.size': 11,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'legend.fontsize': 10,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'axes.linewidth': 1.0,
    'grid.linestyle': ':',
    'grid.alpha': 0.3,
    'legend.frameon': False,
    'axes.axisbelow': True,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'svg.fonttype': 'none',
})

PAPER_MODE = os.getenv('PAPER_MODE', '0').strip() in ['1','true','True','yes','YES']

# Visual-only mapping for labels
DISPLAY_LABELS = {
    'LEACH': 'LEACH',
    'PEGASIS': 'PEGASIS',
    'HEED': 'HEED',
    'AETHER_energy': 'AERIS-E',
    'AETHER_robust': 'AERIS-R'
}


def maybe_remove_titles(fig):
    if PAPER_MODE:
        try:
            fig.suptitle('')
        except Exception:
            pass
        for ax in fig.get_axes():
            try:
                ax.set_title('')
            except Exception:
                pass

def save_figure(fig, out_path):
    maybe_remove_titles(fig)
    plt.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close()

if __name__ == '__main__':
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    in_path = os.path.join(repo, 'results', 'final_baseline_compare.json')
    with open(in_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # flatten to CSV
    rows = []
    for scenario, result in data.items():
        for method, metrics in result.items():
            rows.append({
                'scenario': scenario,
                'method': method,
                'total_energy_consumed': metrics.get('total_energy_consumed'),
                'pdr_hop': metrics.get('packet_delivery_ratio'),
                'pdr_end2end': metrics.get('packet_delivery_ratio_end2end'),
                'lifetime': metrics.get('network_lifetime'),
            })

    out_dir = os.path.join(repo, 'results')
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, 'final_baseline_compare.csv')
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['scenario','method','total_energy_consumed','pdr_hop','pdr_end2end','lifetime'])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('Saved CSV', csv_path)

    # Plots per scenario
    plot_dir = os.path.join(out_dir, 'plots')
    os.makedirs(plot_dir, exist_ok=True)

    methods_order = ['AETHER_energy','AETHER_robust','LEACH','PEGASIS','HEED']
    # Okabe–Ito palette
    colors = {
        'AETHER_energy': '#009E73',  # green
        'AETHER_robust': '#D55E00',  # red
        'LEACH': '#0072B2',          # blue
        'PEGASIS': '#CC79A7',        # purple
        'HEED': '#E69F00',           # orange
    }

    for scenario, result in data.items():
        methods = [m for m in methods_order if m in result]
        labels = [DISPLAY_LABELS.get(m, m.replace('AETHER', 'AERIS')) for m in methods]
        energy = [result[m]['total_energy_consumed'] for m in methods]
        pdr = [result[m]['packet_delivery_ratio_end2end'] for m in methods]

        # Energy bar
        fig, ax = plt.subplots(figsize=(5.5, 3.5))
        xs = range(len(methods))
        ax.bar(xs, energy, color=[colors.get(m, '#888') for m in methods], edgecolor='black', linewidth=0.6)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, rotation=20)
        ax.set_ylabel('Energy (J)')
        ax.set_title(f'Energy by Method - {scenario}')
        ax.grid(axis='y', alpha=0.3)
        outp = os.path.join(plot_dir, f'baseline_energy_{scenario}.svg')
        save_figure(fig, outp)
        print('Saved', outp)

        # PDR bar
        fig, ax = plt.subplots(figsize=(5.5, 3.5))
        ax.bar(xs, pdr, color=[colors.get(m, '#888') for m in methods], edgecolor='black', linewidth=0.6)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, rotation=20)
        ax.set_ylabel('End-to-End PDR')
        ax.set_ylim(0,1.05)
        ax.set_title(f'End-to-End PDR by Method - {scenario}')
        ax.grid(axis='y', alpha=0.3)
        outp = os.path.join(plot_dir, f'baseline_pdr_{scenario}.svg')
        save_figure(fig, outp)
        print('Saved', outp)

