#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
import matplotlib as mpl
import matplotlib.pyplot as plt

PLOT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'plots')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')

# Paper-style rcParams
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
})

COLORS = {
    'AETHER_energy': '#4CAF50',
    'AETHER_robust': '#FF9800',
    'LEACH': '#2196F3',
    'PEGASIS': '#9C27B0',
    'HEED': '#607D8B',
}

os.makedirs(PLOT_DIR, exist_ok=True)

# Figure 1: Safety tradeoff (from grid json)
def fig_safety_tradeoff():
    path = os.path.join(DATA_DIR, 'safety_tradeoff_grid_50x200.json')
    if not os.path.exists(path):
        print('Skip safety tradeoff: missing', path)
        return
    data = json.load(open(path, 'r', encoding='utf-8'))
    # Scatter: energy vs pdr_mean; marker shape for delta; color by r_prob; annotate p05
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    markers = {1.0: 'o', 2.0: 's'}
    cmap = {0.25: '#81D4FA', 0.5: '#29B6F6', 1.0: '#0277BD'}
    for row in data:
        ax.scatter(row['energy_mean'], row['pdr_end2end_mean'],
                   s=70, marker=markers.get(row['delta_dbm'], 'o'),
                   c=cmap.get(row['r_prob'], '#555'))
        ax.annotate(f"r={row['r_prob']},δ={row['delta_dbm']},p05={row['pdr_end2end_p05_mean']:.2f}",
                    (row['energy_mean'], row['pdr_end2end_mean']),
                    textcoords='offset points', xytext=(5,5), fontsize=9)
    ax.set_xlabel('Energy (J)')
    ax.set_ylabel('PDR End-to-End (mean)')
    ax.set_title('Safety Tradeoff (Corridor 3:1, 50×200, n=5)')
    ax.grid(True)
    outp_png = os.path.join(PLOT_DIR, 'paper_safety_tradeoff.png')
    outp_pdf = os.path.join(PLOT_DIR, 'paper_safety_tradeoff.pdf')
    plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
    print('Saved', outp_png, 'and', outp_pdf)

# Figure 2: Baseline bar charts per scenario
def fig_baseline_bars():
    path = os.path.join(DATA_DIR, 'final_baseline_compare.json')
    if not os.path.exists(path):
        print('Skip baseline bars: missing', path)
        return
    data = json.load(open(path, 'r', encoding='utf-8'))
    methods_order = ['AETHER_energy','AETHER_robust','LEACH','PEGASIS','HEED']
    for scenario, result in data.items():
        methods = [m for m in methods_order if m in result]
        energy = [result[m]['total_energy_consumed'] for m in methods]
        pdr = [result[m].get('packet_delivery_ratio_end2end', result[m].get('packet_deliveryy_ratio_end2end', 0.0)) for m in methods]
        # Energy
        fig, ax = plt.subplots(figsize=(5.5, 3.5))
        xs = range(len(methods))
        ax.bar(xs, energy, color=[COLORS.get(m, '#888') for m in methods])
        ax.set_xticks(list(xs))
        ax.set_xticklabels(methods, rotation=20)
        ax.set_ylabel('Energy (J)')
        ax.set_title(f'Energy by Method - {scenario}')
        ax.grid(axis='y')
        outp_png = os.path.join(PLOT_DIR, f'paper_baseline_energy_{scenario}.png')
        outp_pdf = os.path.join(PLOT_DIR, f'paper_baseline_energy_{scenario}.pdf')
        plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
        print('Saved', outp_png, 'and', outp_pdf)
        # PDR
        fig, ax = plt.subplots(figsize=(5.5, 3.5))
        ax.bar(xs, pdr, color=[COLORS.get(m, '#888') for m in methods])
        ax.set_xticks(list(xs))
        ax.set_xticklabels(methods, rotation=20)
        ax.set_ylabel('PDR End-to-End')
        ax.set_ylim(0, 1.05)
        ax.set_title(f'PDR End-to-End by Method - {scenario}')
        ax.grid(axis='y')
        outp_png = os.path.join(PLOT_DIR, f'paper_baseline_pdr_{scenario}.png')
        outp_pdf = os.path.join(PLOT_DIR, f'paper_baseline_pdr_{scenario}.pdf')
        plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
        print('Saved', outp_png, 'and', outp_pdf)

def _bar(ax, labels, values, colors, ylabel, title, ylim=None):
    xs = range(len(labels))
    ax.bar(xs, values, color=colors, edgecolor='black', linewidth=0.6)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, rotation=15)
    ax.set_ylabel(ylabel)
    if ylim is not None:
        ax.set_ylim(*ylim)
    ax.set_title(title)
    ax.grid(axis='y')

# AETHER (energy/robust) only – Intel
def fig_intel_bars():
    path = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    if not os.path.exists(path):
        print('Skip intel bars: missing', path)
        return
    data = json.load(open(path, 'r', encoding='utf-8'))
    methods = ['AETHER_energy','AETHER_robust']
    colors = [COLORS.get(m,'#888') for m in methods]
    energy = [data[m]['total_energy_consumed'] for m in methods]
    pdr = [data[m]['packet_delivery_ratio_end2end'] for m in methods]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    _bar(ax, methods, energy, colors, 'Energy (J)', 'Intel Lab: Energy (200 rounds)')
    outp_png = os.path.join(PLOT_DIR, 'paper_intel_energy.png')
    outp_pdf = os.path.join(PLOT_DIR, 'paper_intel_energy.pdf')
    plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
    print('Saved', outp_png, 'and', outp_pdf)
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    _bar(ax, methods, pdr, colors, 'PDR End-to-End', 'Intel Lab: PDR End-to-End', ylim=(0,1.05))
    outp_png = os.path.join(PLOT_DIR, 'paper_intel_pdr.png')
    outp_pdf = os.path.join(PLOT_DIR, 'paper_intel_pdr.pdf')
    plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
    print('Saved', outp_png, 'and', outp_pdf)

# Intel: Baselines vs AETHER (LEACH/HEED/PEGASIS + AETHER_energy/robust)
def fig_intel_baselines_vs_aether():
    p_aether = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    p_base = os.path.join(DATA_DIR, 'intel_baselines_all.json')
    if not (os.path.exists(p_aether) and os.path.exists(p_base)):
        print('Skip intel baselines vs aether: missing files')
        return
    a = json.load(open(p_aether, 'r', encoding='utf-8'))
    b = json.load(open(p_base, 'r', encoding='utf-8'))
    methods = ['AETHER_energy','AETHER_robust','LEACH','HEED','PEGASIS']
    colors = [COLORS.get(m,'#888') for m in methods]
    energy = [a[m]['total_energy_consumed'] if m in a else b[m]['total_energy_consumed'] for m in methods]
    pdr = [a[m]['packet_delivery_ratio_end2end'] if m in a else b[m]['packet_delivery_ratio_end2end'] for m in methods]
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    _bar(ax, methods, energy, colors, 'Energy (J)', 'Intel Lab: Energy – AETHER vs Baselines')
    outp_png = os.path.join(PLOT_DIR, 'paper_intel_baselines_energy.png')
    outp_pdf = os.path.join(PLOT_DIR, 'paper_intel_baselines_energy.pdf')
    plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
    print('Saved', outp_png, 'and', outp_pdf)
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    _bar(ax, methods, pdr, colors, 'PDR End-to-End', 'Intel Lab: PDR – AETHER vs Baselines', ylim=(0,1.05))
    outp_png = os.path.join(PLOT_DIR, 'paper_intel_baselines_pdr.png')
    outp_pdf = os.path.join(PLOT_DIR, 'paper_intel_baselines_pdr.pdf')
    plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
    print('Saved', outp_png, 'and', outp_pdf)

# Intel: Predicted env (LSTM/TCN) vs conservative mapping
def fig_intel_predenv_vs_conservative():
    p_cons = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    p_lstm = os.path.join(DATA_DIR, 'intel_lstm_envmap_compare.json')
    p_tcn  = os.path.join(DATA_DIR, 'intel_tcn_envmap_compare.json')
    if not (os.path.exists(p_cons) and os.path.exists(p_lstm) and os.path.exists(p_tcn)):
        print('Skip intel pred-env vs conservative: missing files')
        return
    cons = json.load(open(p_cons, 'r', encoding='utf-8'))
    lstm = json.load(open(p_lstm, 'r', encoding='utf-8'))
    tcn  = json.load(open(p_tcn,  'r', encoding='utf-8'))
    rows = [
        ('Cons_AETHER_energy', cons['AETHER_energy']),
        ('Cons_AETHER_robust', cons['AETHER_robust']),
        ('LSTM_AETHER_energy', lstm['AETHER_energy']),
        ('LSTM_AETHER_robust', lstm['AETHER_robust']),
        ('TCN_AETHER_energy',  tcn['AETHER_energy']),
        ('TCN_AETHER_robust',  tcn['AETHER_robust']),
    ]
    colors = ['#8D6E63','#795548','#4CAF50','#FF9800','#66BB6A','#FFA726']
    labels = [r[0] for r in rows]
    energy = [r[1]['total_energy_consumed'] for r in rows]
    pdr = [r[1]['packet_delivery_ratio_end2end'] for r in rows]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    _bar(ax, labels, energy, colors, 'Energy (J)', 'Intel: Predicted env vs Conservative – Energy')
    outp_png = os.path.join(PLOT_DIR, 'paper_intel_predenv_energy.png')
    outp_pdf = os.path.join(PLOT_DIR, 'paper_intel_predenv_energy.pdf')
    plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
    print('Saved', outp_png, 'and', outp_pdf)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    _bar(ax, labels, pdr, colors, 'PDR End-to-End', 'Intel: Predicted env vs Conservative – PDR', ylim=(0,1.05))
    outp_png = os.path.join(PLOT_DIR, 'paper_intel_predenv_pdr.png')
    outp_pdf = os.path.join(PLOT_DIR, 'paper_intel_predenv_pdr.pdf')
    plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
    print('Saved', outp_png, 'and', outp_pdf)

def _sig_label(p):
    if p is None: return ''
    if p < 1e-4: return '****'
    if p < 1e-3: return '***'
    if p < 1e-2: return '**'
    if p < 5e-2: return '*'
    return 'ns'

# Intel: significance bars with 95% CI (repeats=50)
def fig_intel_significance_bars():
    path = os.path.join(DATA_DIR, 'significance_compare_intel_parallel.json')
    if not os.path.exists(path):
        print('Skip intel significance bars: missing', path)
        return
    js = json.load(open(path, 'r', encoding='utf-8'))
    # PDR
    labels = ['AETHER_energy','AETHER_robust']
    vals = [js['pdr_end2end_mean']['BASE']['mean'], js['pdr_end2end_mean']['ROBUST']['mean']]
    ci   = [js['pdr_end2end_mean']['BASE']['ci95'], js['pdr_end2end_mean']['ROBUST']['ci95']]
    colors = [COLORS['AETHER_energy'], COLORS['AETHER_robust']]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    xs = range(len(labels))
    ax.bar(xs, vals, yerr=ci, capsize=4, color=colors, edgecolor='black', linewidth=0.6)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels, rotation=15)
    ax.set_ylabel('PDR End-to-End'); ax.set_ylim(0, 1.05); ax.set_title('Intel: PDR with 95% CI (n=50)')
    ax.grid(axis='y')
    # significance annotation
    p = js['pdr_end2end_mean']['welch_t'].get('p_approx', None)
    y = max(vals[i]+ci[i] for i in range(2)) + 0.03
    ax.plot([0,0,1,1], [y-0.005,y,y,y-0.005], color='black', linewidth=1.0)
    ax.text(0.5, y+0.01, _sig_label(p), ha='center', va='bottom')
    outp_png = os.path.join(PLOT_DIR, 'paper_intel_sig_pdr.png')
    outp_pdf = os.path.join(PLOT_DIR, 'paper_intel_sig_pdr.pdf')
    plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
    print('Saved', outp_png, 'and', outp_pdf)
    # Energy
    labels = ['AETHER_energy','AETHER_robust']
    vals = [js['total_energy_consumed']['BASE']['mean'], js['total_energy_consumed']['ROBUST']['mean']]
    ci   = [js['total_energy_consumed']['BASE']['ci95'], js['total_energy_consumed']['ROBUST']['ci95']]
    colors = [COLORS['AETHER_energy'], COLORS['AETHER_robust']]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    xs = range(len(labels))
    ax.bar(xs, vals, yerr=ci, capsize=4, color=colors, edgecolor='black', linewidth=0.6)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels, rotation=15)
    ax.set_ylabel('Energy (J)'); ax.set_title('Intel: Energy with 95% CI (n=50)')
    ax.grid(axis='y')
    p = js['total_energy_consumed']['welch_t'].get('p_approx', None)
    y = max(vals[i]+ci[i] for i in range(2)) + 0.1
    ax.plot([0,0,1,1], [y-0.02,y,y,y-0.02], color='black', linewidth=1.0)
    ax.text(0.5, y+0.04, _sig_label(p), ha='center', va='bottom')
    outp_png = os.path.join(PLOT_DIR, 'paper_intel_sig_energy.png')
    outp_pdf = os.path.join(PLOT_DIR, 'paper_intel_sig_energy.pdf')
    plt.tight_layout(); fig.savefig(outp_png, dpi=300, bbox_inches='tight'); fig.savefig(outp_pdf, bbox_inches='tight'); plt.close()
    print('Saved', outp_png, 'and', outp_pdf)

if __name__ == '__main__':
    fig_safety_tradeoff()
    fig_baseline_bars()
    fig_intel_bars()
    fig_intel_baselines_vs_aether()
    fig_intel_predenv_vs_conservative()
    fig_intel_significance_bars()

