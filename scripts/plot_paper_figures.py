#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, shutil
# Sanitize sys.path to avoid accidental loading from project .venv when running from Conda or system Python
try:
    _root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    _venv_dir = os.path.join(_root_dir, '.venv')
    sys.path = [p for p in sys.path if not (isinstance(p, str) and p.lower().startswith(_venv_dir.lower()))]
except Exception:
    pass
import matplotlib as mpl
mpl.use('Agg')
from cycler import cycler
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow
from matplotlib.lines import Line2D
import numpy as np
import matplotlib.patches as mpatches

PLOT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'plots')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')

# Paper-style rcParams
PALETTE = [
    "#1b9e77",
    "#d95f02",
    "#7570b3",
    "#e7298a",
    "#66a61e",
    "#e6ab02",
    "#a6761d",
    "#666666",
]

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
    # Publication-friendly outputs
    'svg.fonttype': 'none',  # keep text as text in SVG
    'savefig.format': 'svg',
    'figure.dpi': 300,
    'mathtext.fontset': 'stix',
    'axes.unicode_minus': False,
    # Ensure white backgrounds regardless of viewer theme
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'savefig.facecolor': 'white',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'axes.prop_cycle': cycler(color=PALETTE),
})

# Paper mode: remove internal titles to defer to external captions
PAPER_MODE = bool(int(os.environ.get('PAPER_MODE', '1')))
# Publication minimal labeling: 0 disables numeric labels on bars to avoid clutter
# MDPI 风格默认不在柱状图内标注数值，避免拥挤
PAPER_VALUE_LABELS = bool(int(os.environ.get('PAPER_VALUE_LABELS', '0')))

def load_effect_sizes_summary(path: str = None) -> dict:
    """
    读取效应量汇总 JSON（由 run_export 生成的 results/effect_sizes_summary.json）。
    返回字典；若缺失或解析失败则返回空字典并打印提示。
    """
    try:
        if path is None:
            path = os.path.join(DATA_DIR, 'effect_sizes_summary.json')
        if not os.path.exists(path):
            print('Skip effect sizes: missing', path)
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print('Effect sizes load failed:', e)
        return {}

def maybe_remove_titles(fig):
    if not PAPER_MODE:
        return
    for ax in fig.axes:
        try:
            ax.set_title('')
        except Exception:
            pass

# Unified top-margin helper to avoid overlap of stars/brackets/value labels
def _ensure_top_margin(ax, top_y: float, pad_frac: float = 0.06):
    try:
        y0, y1 = ax.get_ylim()
        rng = (y1 - y0) if y1 is not None and y0 is not None else 1.0
        need = top_y + pad_frac * (rng if rng > 0 else 1.0)
        if need > y1:
            ax.set_ylim(y0, need)
    except Exception:
        pass

def save_figure(fig, out_path: str):
    try:
        plt.tight_layout()
    except Exception:
        pass
    maybe_remove_titles(fig)
    # Save primary SVG
    fig.savefig(out_path, bbox_inches='tight')
    # Also export PDF sibling next to SVG
    root, ext = os.path.splitext(out_path)
    out_pdf = root + '.pdf'
    try:
        fig.savefig(out_pdf, bbox_inches='tight')
    except Exception as e:
        print('PDF export failed for', out_pdf, ':', e)
    # Also copy to publication_figures for unified export (both SVG and PDF)
    try:
        base_svg = os.path.basename(out_path)
        base_pdf = os.path.basename(out_pdf)
        pub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results', 'publication_figures'))
        os.makedirs(pub_dir, exist_ok=True)
        fig.savefig(os.path.join(pub_dir, base_svg), bbox_inches='tight')
        fig.savefig(os.path.join(pub_dir, base_pdf), bbox_inches='tight')
    except Exception as e:
        print('Publication export failed:', e)
    plt.close(fig)

# Color palette (Okabe–Ito) and method mapping
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
COLORS = {
    'AETHER_energy': '#009E73',  # vivid green
    'AETHER_robust': '#E67900',  # warmer orange for contrast
    'LEACH': OKABE_ITO['blue'],
    'PEGASIS': OKABE_ITO['purple'],
    'HEED': OKABE_ITO['orange'],
    'TEEN': OKABE_ITO['sky'],
}

# Visual-only renaming: keep data keys but show neutral labels
DISPLAY_LABELS = {
    'AETHER_energy': 'AERIS-E',
    'AETHER_robust': 'AERIS-R',
}

# Friendly topology label mapping for x-axis readability
SCENARIO_LABELS = {
    'corridor41_50x200': 'Corridor-41 (50×200)',
    'corridor_50x200': 'Corridor (50×200)',
    'uniform_50x200': 'Uniform (50×200)',
    'uniform': 'Uniform',
}

def pretty_topo(name: str) -> str:
    try:
        return SCENARIO_LABELS.get(name, name.replace('_', ' ').replace('x', '×'))
    except Exception:
        return name

def method_color(name: str):
    return COLORS.get(name, OKABE_ITO['sky'])


def method_label(name: str) -> str:
    return DISPLAY_LABELS.get(name, name)

# helper: annotate numeric values above bars
def _annotate_bar_values(ax, xs, vals, ylabel, ylim=None):
    # In publication mode, default to no numeric labels to keep visuals clean
    if not PAPER_VALUE_LABELS:
        return
    try:
        if ylim is not None:
            y0, y1 = ylim
            rng = (y1 - y0) if (y1 is not None and y0 is not None) else None
        else:
            y0, y1 = ax.get_ylim()
            rng = (y1 - y0)
    except Exception:
        y0, y1, rng = 0.0, 1.0, 1.0
    dy = 0.025 * (rng if rng else 1.0)
    def fmt(y):
        if isinstance(ylabel, str) and 'PDR' in ylabel:
            return f"{y:.2f}"
        if isinstance(ylabel, str) and 'Energy' in ylabel:
            return f"{y:.1f}"
        return f"{y:.2f}"
    for x, y in zip(xs, vals):
        _ensure_top_margin(ax, y + dy)
        ax.text(x, y + dy, fmt(y), ha='center', va='bottom', fontsize=9)

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
    cmap = {0.25: '#81D4FA', 0.5: '#29B6F3', 1.0: '#0277BD'}
    for row in data:
        ax.scatter(row['energy_mean'], row['pdr_end2end_mean'],
                   s=70, marker=markers.get(row['delta_dbm'], 'o'),
                   c=cmap.get(row['r_prob'], '#555'))
        ax.annotate(f"r={row['r_prob']},δ={row['delta_dbm']},p05={row['pdr_end2end_p05_mean']:.2f}",
                    (row['energy_mean'], row['pdr_end2end_mean']),
                    textcoords='offset points', xytext=(5,5), fontsize=9)
    ax.set_xlabel('Energy (J)')
    ax.set_ylabel('End-to-End PDR (mean)')
    ax.set_title('Safety Tradeoff (Corridor 3:1, 50×200, n=5)')
    ax.grid(True)
    out_base = os.path.join(PLOT_DIR, 'paper_safety_tradeoff')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')

# Figure 2: Baseline bar charts per scenario
def fig_baseline_bars():
    path = os.path.join(DATA_DIR, 'final_baseline_compare.json')
    if not os.path.exists(path):
        print('Skip baseline bars: missing', path)
        return
    data = json.load(open(path, 'r', encoding='utf-8'))
    methods_order = ['AETHER_energy','AETHER_robust','LEACH','PEGASIS','HEED','TEEN']
    for scenario, result in data.items():
        methods = [m for m in methods_order if m in result]
        labels = [method_label(m) for m in methods]
        energy = [result[m]['total_energy_consumed'] for m in methods]
        pdr = [result[m].get('packet_delivery_ratio_end2end', result[m].get('packet_deliveryy_ratio_end2end', 0.0)) for m in methods]
        # Energy
        fig, ax = plt.subplots(figsize=(5.5, 3.5))
        xs = range(len(methods))
        ax.bar(xs, energy, color=[method_color(m) for m in methods])
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, rotation=20)
        ax.set_ylabel('Energy (J)')
        ax.set_title(f'Energy by Method - {scenario}')
        ax.grid(axis='y')
        out_base = os.path.join(PLOT_DIR, f'paper_baseline_energy_{scenario}')
        save_figure(fig, out_base + '.svg')
        print('Saved', out_base + '.svg')
        # PDR
        fig, ax = plt.subplots(figsize=(5.5, 3.5))
        ax.bar(xs, pdr, color=[method_color(m) for m in methods])
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, rotation=20)
        ax.set_ylabel('End-to-End PDR')
        ax.set_ylim(0, 1.05)
        ax.set_title(f'End-to-End PDR by Method - {scenario}')
        ax.grid(axis='y')
        out_base = os.path.join(PLOT_DIR, f'paper_baseline_pdr_{scenario}')
        save_figure(fig, out_base + '.svg')
        print('Saved', out_base + '.svg')

def _bar(ax, labels, values, colors, ylabel, title, ylim=None):
    xs = range(len(labels))
    ax.bar(xs, values, color=colors, edgecolor='none', linewidth=0.0)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, rotation=15)
    ax.set_ylabel(ylabel)
    if ylim is not None:
        ax.set_ylim(*ylim)
    ax.set_title(title)
    ax.grid(False)
    # annotate values for clarity
    _annotate_bar_values(ax, list(xs), list(values), ylabel, ylim)

# AETHER (energy/robust) only – Intel
def fig_intel_bars():
    path = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    if not os.path.exists(path):
        print('Skip intel bars: missing', path)
        return
    data = json.load(open(path, 'r', encoding='utf-8'))
    methods = ['AETHER_energy','AETHER_robust']
    labels = [method_label(m) for m in methods]
    colors = [method_color(m) for m in methods]
    energy = [data[m]['total_energy_consumed'] for m in methods]
    pdr = [data[m]['packet_delivery_ratio_end2end'] for m in methods]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    _bar(ax, labels, energy, colors, 'Energy (J)', 'Intel Lab: Energy (200 rounds)')
    _add_stats_footer(ax, 'mean values; no CI')
    out_base = os.path.join(PLOT_DIR, 'paper_intel_energy')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    _bar(ax, labels, pdr, colors, 'End-to-End PDR', 'Intel Lab: End-to-End PDR', ylim=(0,1.05))
    _add_stats_footer(ax, 'mean values; no CI')
    out_base = os.path.join(PLOT_DIR, 'paper_intel_pdr')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')

# Intel: Baselines vs AETHER (LEACH/HEED/PEGASIS + AETHER_energy/robust)
def fig_intel_baselines_vs_aether():
    p_aether = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    p_base = os.path.join(DATA_DIR, 'intel_baselines_all.json')
    if not (os.path.exists(p_aether) and os.path.exists(p_base)):
        print('Skip intel baselines vs aether: missing files')
        return
    a = json.load(open(p_aether, 'r', encoding='utf-8'))
    b = json.load(open(p_base, 'r', encoding='utf-8'))
    methods = ['AETHER_energy','AETHER_robust','LEACH','HEED','PEGASIS','TEEN']
    rows = []
    for m in methods:
        src = a if m in a else b
        if m in src:
            rows.append({
                'm': m,
                'label': method_label(m),
                'energy': src[m]['total_energy_consumed'],
                'pdr': src[m]['packet_delivery_ratio_end2end'],
            })
    # Sort by PDR descending for consistent ordering across both panels
    rows.sort(key=lambda r: r['pdr'], reverse=True)
    labels = [r['label'] for r in rows]
    colors = [method_color(r['m']) for r in rows]
    energy = [r['energy'] for r in rows]
    pdr = [r['pdr'] for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    _bar(ax, labels, energy, colors, 'Energy (J)', 'Intel Lab: Energy – AERIS vs Baselines')
    _add_stats_footer(ax, 'mean values; no CI; sorted by PDR')
    out_base = os.path.join(PLOT_DIR, 'paper_intel_baselines_energy')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    _bar(ax, labels, pdr, colors, 'End-to-End PDR', 'Intel Lab: PDR – AERIS vs Baselines', ylim=(0,1.05))
    _add_stats_footer(ax, 'mean values; no CI; sorted by PDR')
    out_base = os.path.join(PLOT_DIR, 'paper_intel_baselines_pdr')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')

# Intel: Predicted env (LSTM/TCN) vs conservative mapping
def fig_intel_predenv_vs_conservative():
    p_cons = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    p_lstm = os.path.join(DATA_DIR, 'intel_lstm_envmap_compare.json')
    p_tcn  = os.path.join(DATA_DIR, 'intel_tcn_envmap_compare.json')
    p_trf  = os.path.join(DATA_DIR, 'intel_transformer_envmap_compare.json')
    p_dlin = os.path.join(DATA_DIR, 'intel_dlinear_envmap_compare.json')
    p_ptst = os.path.join(DATA_DIR, 'intel_patchtst_envmap_compare.json')
    if not (os.path.exists(p_cons) and os.path.exists(p_lstm) and os.path.exists(p_tcn)):
        print('Skip intel pred-env vs conservative: missing files')
        return
    cons = json.load(open(p_cons, 'r', encoding='utf-8'))
    lstm = json.load(open(p_lstm, 'r', encoding='utf-8'))
    tcn  = json.load(open(p_tcn,  'r', encoding='utf-8'))
    rows = [
        ('Conservative – Energy', cons['AETHER_energy']),
        ('Conservative – Robust', cons['AETHER_robust']),
        ('LSTM – Energy', lstm['AETHER_energy']),
        ('LSTM – Robust', lstm['AETHER_robust']),
        ('TCN – Energy',  tcn['AETHER_energy']),
        ('TCN – Robust',  tcn['AETHER_robust']),
    ]
    if os.path.exists(p_trf):
        trf = json.load(open(p_trf, 'r', encoding='utf-8'))
        rows.extend([
            ('Transformer – Energy', trf['AETHER_energy']),
            ('Transformer – Robust', trf['AETHER_robust']),
        ])
    if os.path.exists(p_ptst):
        ptst = json.load(open(p_ptst, 'r', encoding='utf-8'))
        rows.extend([
            ('PatchTST – Energy', ptst['AETHER_energy']),
            ('PatchTST – Robust', ptst['AETHER_robust']),
        ])
    if os.path.exists(p_dlin):
        dlin = json.load(open(p_dlin, 'r', encoding='utf-8'))
        rows.extend([
            ('DLinear – Energy', dlin['AETHER_energy']),
            ('DLinear – Robust', dlin['AETHER_robust']),
        ])
    colors = ['#8D6E63','#795548','#4CAF50','#FF9800','#66BB6A','#FFA726']
    if os.path.exists(p_trf):
        colors.extend(['#42A5F5','#AB47BC'])
    if os.path.exists(p_ptst):
        colors.extend(['#26A69A','#EF5350'])
    if os.path.exists(p_dlin):
        colors.extend(['#7E57C2','#5C6BC0'])
    labels = [r[0] for r in rows]
    energy = [r[1]['total_energy_consumed'] for r in rows]
    pdr = [r[1]['packet_delivery_ratio_end2end'] for r in rows]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    _bar(ax, labels, energy, colors, 'Energy (J)', 'Intel: Predicted env vs Conservative – Energy')
    out_base = os.path.join(PLOT_DIR, 'paper_intel_predenv_energy')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    _bar(ax, labels, pdr, colors, 'End-to-End PDR', 'Intel: Predicted env vs Conservative – PDR', ylim=(0,1.05))
    out_base = os.path.join(PLOT_DIR, 'paper_intel_predenv_pdr')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')

def _sig_label(p):
    """Return a clear Welch p-value label instead of star notation."""
    if p is None:
        return ''
    try:
        if p < 1e-6:
            return 'Welch p<1e-6'
        if p < 1e-4:
            return 'Welch p<1e-4'
        if p < 1e-3:
            return 'Welch p<1e-3'
        if p < 1e-2:
            return 'Welch p<0.01'
        if p < 5e-2:
            return 'Welch p<0.05'
        return 'ns'
    except Exception:
        return 'ns'

def _place_above_ax(fig, ax, text: str, y_pad: float = 0.028, fontsize: int = 9):
    """Place annotation text just above an axes in figure coordinates."""
    try:
        bbox = ax.get_position()
        x = bbox.x0 + bbox.width / 2.0
        y = min(0.99, bbox.y1 + y_pad)
        fig.text(x, y, text, ha='center', va='bottom', fontsize=fontsize, color='#333')
    except Exception:
        pass

# Small footer to clarify statistics on plots
def _add_stats_footer(ax, text: str = None):
    if text is None:
        text = 'mean ± 95% CI; Welch\'s t-test'
    try:
        fig = ax.figure
        # Place as a figure-level caption just above the axes to avoid clutter inside the plot
        bbox = ax.get_position()
        y = min(0.98, bbox.y1 + 0.015)
        fig.text(bbox.x0, y, text, ha='left', va='top', fontsize=8, color='#555')
    except Exception:
        pass

# Nonparametric effects helper
def _nonparam_effects_text(metric_key: str):
    try:
        path = os.path.join(DATA_DIR, 'significance_nonparam_intel_parallel.json')
        if not os.path.exists(path):
            return None
        obj = json.load(open(path, 'r', encoding='utf-8'))
        m = obj.get(metric_key, {})
        U = (m.get('mannwhitney', {}) or {}).get('U')
        auc = m.get('auc')
        d = m.get('cohen_d')
        cd = m.get('cliffs_delta')
        if any(v is None for v in [U, auc, d, cd]):
            return None
        return f"Mann–Whitney U={U:.2f} | AUC={auc:.3f} | Cliff's δ={cd:+.3f} | Cohen's d={d:+.3f}"
    except Exception:
        return None

# Intel: significance bars with 95% CI (repeats=50)
def fig_intel_significance_bars():
    path = os.path.join(DATA_DIR, 'significance_compare_intel_parallel.json')
    if not os.path.exists(path):
        print('Skip intel significance bars: missing', path)
        return
    js = json.load(open(path, 'r', encoding='utf-8'))
    # derive sample size n from JSON values if available
    try:
        n_pdr = min(len(js['pdr_end2end_mean']['BASE'].get('values', [])), len(js['pdr_end2end_mean']['ROBUST'].get('values', [])))
    except Exception:
        n_pdr = None
    try:
        n_energy = min(len(js['total_energy_consumed']['BASE'].get('values', [])), len(js['total_energy_consumed']['ROBUST'].get('values', [])))
    except Exception:
        n_energy = None
    # PDR
    labels = [method_label('AETHER_energy'), method_label('AETHER_robust')]
    vals = [js['pdr_end2end_mean']['BASE']['mean'], js['pdr_end2end_mean']['ROBUST']['mean']]
    ci   = [js['pdr_end2end_mean']['BASE']['ci95'], js['pdr_end2end_mean']['ROBUST']['ci95']]
    colors = [COLORS['AETHER_energy'], COLORS['AETHER_robust']]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    xs = range(len(labels))
    ax.bar(xs, vals, yerr=ci, capsize=2, color=colors, edgecolor='none', linewidth=0.0)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels, rotation=0)
    ttl_n = f" (n={n_pdr})" if (isinstance(n_pdr, int) and n_pdr > 0) else ""
    ax.set_ylabel('End-to-End PDR'); ax.set_ylim(0, 1.05); ax.set_title('Intel: PDR with 95% CI'+ttl_n)
    ax.grid(False)
    _annotate_bar_values(ax, list(xs), list(vals), 'End-to-End PDR', (0, 1.05))
    p = js['pdr_end2end_mean']['welch_t'].get('p_approx', None)
    # 将显著性文本移动到坐标轴外部，避免遮挡
    _place_above_ax(fig, ax, _sig_label(p))
    _add_stats_footer(ax, 'mean ± 95% CI' + (('; nonparam: ' + _nonparam_effects_text('pdr_end2end_mean')) if _nonparam_effects_text('pdr_end2end_mean') else ''))

    # Energy
    labels = [method_label('AETHER_energy'), method_label('AETHER_robust')]
    vals = [js['total_energy_consumed']['BASE']['mean'], js['total_energy_consumed']['ROBUST']['mean']]
    ci   = [js['total_energy_consumed']['BASE']['ci95'], js['total_energy_consumed']['ROBUST']['ci95']]
    colors = [COLORS['AETHER_energy'], COLORS['AETHER_robust']]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.bar(xs, vals, yerr=ci, capsize=2, color=colors, edgecolor='none', linewidth=0.0)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels, rotation=15)
    ttl_n = f" (n={n_energy})" if (isinstance(n_energy, int) and n_energy > 0) else ""
    ax.set_ylabel('Energy (J)'); ax.set_title('Intel: Energy with 95% CI'+ttl_n)
    ax.grid(False)
    _annotate_bar_values(ax, list(xs), list(vals), 'Energy (J)')
    p = js['total_energy_consumed']['welch_t'].get('p_approx', None)
    _place_above_ax(fig, ax, _sig_label(p))
    _add_stats_footer(ax, ('mean ± 95% CI; nonparam: ' + _nonparam_effects_text('total_energy_consumed')) if _nonparam_effects_text('total_energy_consumed') else 'mean ± 95% CI; Welch\'s t-test')

    out_basename = 'paper_intel_sig_pdr'
    outp_svg = os.path.join(PLOT_DIR, out_basename + '.svg')
    plt.tight_layout(); fig.savefig(outp_svg, bbox_inches='tight'); plt.close()
    print('Saved', outp_svg)

    # Energy
    labels = [method_label('AETHER_energy'), method_label('AETHER_robust')]
    vals = [js['total_energy_consumed']['BASE']['mean'], js['total_energy_consumed']['ROBUST']['mean']]
    ci   = [js['total_energy_consumed']['BASE']['ci95'], js['total_energy_consumed']['ROBUST']['ci95']]
    colors = [COLORS['AETHER_energy'], COLORS['AETHER_robust']]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.bar(xs, vals, yerr=ci, capsize=2, color=colors, edgecolor='none', linewidth=0.0)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels, rotation=15)
    ttl_n = f" (n={n_energy})" if (isinstance(n_energy, int) and n_energy > 0) else ""
    ax.set_ylabel('Energy (J)'); ax.set_title('Intel: Energy with 95% CI'+ttl_n)
    ax.grid(False)
    _annotate_bar_values(ax, list(xs), list(vals), 'Energy (J)')
    p = js['total_energy_consumed']['welch_t'].get('p_approx', None)
    y = max(vals[i]+ci[i] for i in range(2)) + 0.05
    # 显著性标注移到坐标轴外部，避免与柱顶/边框重叠
    _place_above_ax(fig, ax, _sig_label(p))
    _add_stats_footer(ax, ('mean ± 95% CI; nonparam: ' + _nonparam_effects_text('total_energy_consumed')) if _nonparam_effects_text('total_energy_consumed') else 'mean ± 95% CI; Welch\'s t-test')

    out_basename = 'paper_intel_sig_energy'
    outp_svg = os.path.join(PLOT_DIR, out_basename + '.svg')
    plt.tight_layout(); fig.savefig(outp_svg, bbox_inches='tight'); plt.close()
    print('Saved', outp_svg)

# Intel: Ablation (95% CI)
def fig_intel_ablation():
    # Apply publication-grade styling for cleaner visuals
    try:
        apply_pub_style()
    except Exception:
        pass
    # Use n=100 parallel result if available; fallback to n=50
    p1 = os.path.join(DATA_DIR, 'intel_ablation_parallel.json')
    p2 = os.path.join(DATA_DIR, 'intel_ablation.json')
    path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
    if path is None:
        print('Skip ablation: missing files')
        return
    js = json.load(open(path, 'r', encoding='utf-8'))
    order = ['FULL','-CAS','-FAIR','-GW','-SAFETY']
    labels = order
    colors = ['#4E79A7','#A0CBE8','#F28E2B','#59A14F','#E15759']
    # Energy
    vals = [js[k]['energy']['mean'] for k in order]
    ci   = [js[k]['energy']['ci95'] for k in order]
    base_e = js['FULL']['energy']['mean']
    deltas_e = [v - base_e for v in vals]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    xs = range(len(labels))
    ax.bar(xs, vals, yerr=ci, capsize=5, color=colors, edgecolor='black', linewidth=0.8)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels, rotation=0)
    ax.set_ylabel('Energy (J)')
    ax.grid(axis='y', alpha=0.30)
    ax.set_title('Intel: Ablation – Energy (mean ± 95% CI; Δ vs FULL)')
    # Baseline reference line to reduce cognitive load
    try:
        ax.axhline(base_e, color='#777', linestyle='--', linewidth=0.9, alpha=0.7)
    except Exception:
        pass
    # Annotate delta vs FULL for non-FULL variants only, keep uncluttered
    try:
        y0, y1 = ax.get_ylim()
        rng = (y1 - y0) if (y1 is not None and y0 is not None) else 1.0
    except Exception:
        y0, y1, rng = 0.0, 1.0, 1.0
    dy = 0.02 * (rng if rng else 1.0)
    for i, (x, v, d) in enumerate(zip(xs, vals, deltas_e)):
        if labels[i] == 'FULL':
            # Label FULL once for clarity
            ax.text(x, v + dy, 'baseline', ha='center', va='bottom', fontsize=8)
            continue
        _ensure_top_margin(ax, v + dy)
        ax.text(x, v + dy, f"Δ {d:+.2f} J", ha='center', va='bottom', fontsize=8)
    _add_stats_footer(ax, 'mean ± 95% CI; dashed line: FULL baseline')
    out_base = os.path.join(PLOT_DIR, 'paper_intel_ablation_energy')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')
    # PDR
    vals = [js[k]['pdr_end2end']['mean'] for k in order]
    ci   = [js[k]['pdr_end2end']['ci95'] for k in order]
    base_p = js['FULL']['pdr_end2end']['mean']
    deltas_p = [v - base_p for v in vals]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.bar(xs, vals, yerr=ci, capsize=5, color=colors, edgecolor='black', linewidth=0.8)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels, rotation=0)
    ax.set_ylabel('End-to-End PDR'); ax.set_ylim(0, 1.05); ax.grid(axis='y', alpha=0.35)
    ax.set_title('Intel: Ablation – PDR (mean ± 95% CI; Δ vs FULL)')
    # Baseline reference
    try:
        ax.axhline(base_p, color='#777', linestyle='--', linewidth=0.9, alpha=0.7)
    except Exception:
        pass
    # Delta annotations, non-FULL only
    try:
        y0, y1 = ax.get_ylim()
        rng = (y1 - y0) if (y1 is not None and y0 is not None) else 1.0
    except Exception:
        y0, y1, rng = 0.0, 1.0, 1.0
    dy = 0.02 * (rng if rng else 1.0)
    for i, (x, v, d) in enumerate(zip(xs, vals, deltas_p)):
        if labels[i] == 'FULL':
            ax.text(x, v + dy, 'baseline', ha='center', va='bottom', fontsize=8)
            continue
        _ensure_top_margin(ax, v + dy)
        ax.text(x, v + dy, f"Δ {d:+.3f}", ha='center', va='bottom', fontsize=8)
    _add_stats_footer(ax, 'mean ± 95% CI; dashed line: FULL baseline')
    out_base = os.path.join(PLOT_DIR, 'paper_intel_ablation_pdr')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')

# Intel: Sensitivity (line plots with CI) – use parallel if available
def fig_intel_sensitivity():
    p1 = os.path.join(DATA_DIR, 'intel_sensitivity_parallel.json')
    p2 = os.path.join(DATA_DIR, 'intel_sensitivity.json')
    path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
    if path is None:
        print('Skip sensitivity: missing files')
        return
    js = json.load(open(path, 'r', encoding='utf-8'))
    # extract unique sorted axes
    keys = sorted(js.keys())
    E0s = sorted({ float(js[k]['initial_energy']) for k in keys })
    Ps  = sorted({ int(js[k]['packet_size']) for k in keys })
    Gs  = sorted({ int(js[k]['gateway_k']) for k in keys })
    # helper to get series for a fixed G and E0 across P
    def series(metric, G, E0):
        xs = []; ys = []; ci = []
        for P in Ps:
            key = f'E{E0}_P{P}_G{G}'
            if key in js:
                xs.append(P); ys.append(js[key][metric]['mean']); ci.append(js[key][metric]['ci95'])
        return xs, ys, ci
    # PDR figure with 3 subplots per G
    fig, axes = plt.subplots(1, len(Gs), figsize=(7.2, 3.4), sharey=True)
    if len(Gs) == 1:
        axes = [axes]
    colors = ['#4E79A7','#F28E2B','#59A14F']
    for i,G in enumerate(Gs):
        ax = axes[i]
        for j,E0 in enumerate(E0s):
            xs, ys, ci = series('pdr_end2end', G, E0)
            ax.plot(xs, ys, marker='o', color=colors[j%len(colors)], label=f'E0={E0}J')
            ax.fill_between(xs, [y-c for y,c in zip(ys,ci)], [y+c for y,c in zip(ys,ci)], color=colors[j%len(colors)], alpha=0.2, linewidth=0)
        ax.set_title(f'G={G}')
        ax.set_xlabel('Packet size (Bytes)')
        ax.grid(True, axis='y', alpha=0.35)
        if i == 0:
            ax.set_ylabel('End-to-End PDR')
        ax.set_ylim(0, 1.05)
    handles, labels = axes[-1].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=min(len(labels), 4), frameon=False, bbox_to_anchor=(0.5, 1.02))
    # save SVG
    out_base = os.path.join(PLOT_DIR, 'paper_intel_sens_pdr')
    plt.tight_layout(); fig.savefig(out_base + '.svg', bbox_inches='tight'); plt.close()
    print('Saved', out_base + '.svg')
    # Energy figure
    fig, axes = plt.subplots(1, len(Gs), figsize=(7.2, 3.4), sharey=True)
    if len(Gs) == 1:
        axes = [axes]
    for i,G in enumerate(Gs):
        ax = axes[i]
        for j,E0 in enumerate(E0s):
            xs, ys, ci = series('energy', G, E0)
            ax.plot(xs, ys, marker='o', color=colors[j%len(colors)], label=f'E0={E0}J')
            ax.fill_between(xs, [y-c for y,c in zip(ys,ci)], [y+c for y,c in zip(ys,ci)], color=colors[j%len(colors)], alpha=0.2, linewidth=0)
        ax.set_title(f'G={G}')
        ax.set_xlabel('Packet size (Bytes)')
        ax.grid(True, axis='y', alpha=0.35)
        if i == 0:
            ax.set_ylabel('Energy (J)')
    handles, labels = axes[-1].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=min(len(labels), 4), frameon=False, bbox_to_anchor=(0.5, 1.02))
    out_base = os.path.join(PLOT_DIR, 'paper_intel_sens_energy')
    plt.tight_layout(); fig.savefig(out_base + '.svg', bbox_inches='tight'); plt.close()
    print('Saved', out_base + '.svg')

def fig_intel_sig_combined():
    path = os.path.join(DATA_DIR, 'significance_compare_intel_parallel.json')
    if not os.path.exists(path):
        print('Skip intel combined significance: missing', path)
        return
    js = json.load(open(path, 'r', encoding='utf-8'))
    # derive sample sizes
    try:
        n_pdr = min(len(js['pdr_end2end_mean']['BASE'].get('values', [])), len(js['pdr_end2end_mean']['ROBUST'].get('values', [])))
    except Exception:
        n_pdr = None
    try:
        n_energy = min(len(js['total_energy_consumed']['BASE'].get('values', [])), len(js['total_energy_consumed']['ROBUST'].get('values', [])))
    except Exception:
        n_energy = None

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
    axes = np.array(axes).ravel().tolist()

    # Subplot 1: PDR
    ax = axes[0]
    labels = [method_label('AETHER_energy'), method_label('AETHER_robust')]
    vals = [js['pdr_end2end_mean']['BASE']['mean'], js['pdr_end2end_mean']['ROBUST']['mean']]
    ci   = [js['pdr_end2end_mean']['BASE']['ci95'], js['pdr_end2end_mean']['ROBUST']['ci95']]
    colors = [COLORS['AETHER_energy'], COLORS['AETHER_robust']]
    xs = range(len(labels))
    ax.bar(xs, vals, yerr=ci, capsize=2, color=colors, edgecolor='none', linewidth=0.0)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels, rotation=0)
    ttl_n = f" (n={n_pdr})" if (isinstance(n_pdr, int) and n_pdr > 0) else ""
    ax.set_ylabel('End-to-End PDR'); ax.set_ylim(0, 1.05); ax.set_title('Intel: PDR with 95% CI'+ttl_n)
    ax.grid(False)
    _annotate_bar_values(ax, list(xs), list(vals), 'End-to-End PDR', ylim=(0,1.05))
    p = js['pdr_end2end_mean']['welch_t'].get('p_approx', None)
    y = max(vals[i]+ci[i] for i in range(2)) + 0.02
    _place_above_ax(fig, ax, _sig_label(p))
    _add_stats_footer(ax, 'mean ± 95% CI' + (('; nonparam: ' + _nonparam_effects_text('pdr_end2end_mean')) if _nonparam_effects_text('pdr_end2end_mean') else ''))

    # Subplot 2: Energy
    ax = axes[1]
    labels = [method_label('AETHER_energy'), method_label('AETHER_robust')]
    vals = [js['total_energy_consumed']['BASE']['mean'], js['total_energy_consumed']['ROBUST']['mean']]
    ci   = [js['total_energy_consumed']['BASE']['ci95'], js['total_energy_consumed']['ROBUST']['ci95']]
    colors = [COLORS['AETHER_energy'], COLORS['AETHER_robust']]
    xs = range(len(labels))
    ax.bar(xs, vals, yerr=ci, capsize=2, color=colors, edgecolor='none', linewidth=0.0)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels, rotation=15)
    ttl_n = f" (n={n_energy})" if (isinstance(n_energy, int) and n_energy > 0) else ""
    ax.set_ylabel('Energy (J)'); ax.set_title('Intel: Energy with 95% CI'+ttl_n)
    ax.grid(False)
    _annotate_bar_values(ax, list(xs), list(vals), 'Energy (J)')
    p = js['total_energy_consumed']['welch_t'].get('p_approx', None)
    y = max(vals[i]+ci[i] for i in range(2)) + 0.05
    _ensure_top_margin(ax, y + 0.02)
    ax.text(0.5, y, _sig_label(p), ha='center', va='bottom')
    _add_stats_footer(ax, 'mean ± 95% CI; Welch\'s t-test')

    out_basename = 'paper_intel_sig_combined'
    outp_svg = os.path.join(PLOT_DIR, out_basename + '.svg')
    maybe_remove_titles(fig)
    save_figure(fig, outp_svg)
    print('Saved', outp_svg)

def fig_multi_topo_significance():
    path = os.path.join(DATA_DIR, 'significance_compare_multi_topo_50x200.json')
    if not os.path.exists(path):
        print('Skip multi-topo significance: missing', path)
        return
    js = json.load(open(path, 'r', encoding='utf-8'))
    # Optionally append large-scale points from large_scale_long.json (no CI, few runs)
    try:
        ls_path = os.path.join(DATA_DIR, 'large_scale_long.json')
        if os.path.exists(ls_path):
            ls = json.load(open(ls_path, 'r', encoding='utf-8'))
            for topo in ['uniform_300', 'uniform_500']:
                if topo in ls:
                    e = ls[topo]['AERIS_energy']
                    r = ls[topo]['AERIS_robust']
                    js[topo] = {
                        'pdr_end2end_mean': {
                            'BASE': {'mean': e.get('packet_delivery_ratio_end2end', 0.0), 'ci95': 0.0, 'values': [e.get('packet_delivery_ratio_end2end', 0.0)]},
                            'ROBUST': {'mean': r.get('packet_delivery_ratio_end2end', 0.0), 'ci95': 0.0, 'values': [r.get('packet_delivery_ratio_end2end', 0.0)]},
                            'welch_t': {'t_stat': 0.0, 'df': float('inf')}
                        },
                        'total_energy_consumed': {
                            'BASE': {'mean': e.get('total_energy_consumed', 0.0), 'ci95': 0.0, 'values': [e.get('total_energy_consumed', 0.0)]},
                            'ROBUST': {'mean': r.get('total_energy_consumed', 0.0), 'ci95': 0.0, 'values': [r.get('total_energy_consumed', 0.0)]},
                            'welch_t': {'t_stat': 0.0, 'df': float('inf')}
                        }
                    }
    except Exception as e:
        print('Append large-scale to sig failed:', e)
    # Only small topologies (<=200 nodes) for clean significance bars
    topos = sorted([k for k in js.keys() if '300' not in k and '500' not in k])

    def cohen_d(a, b):
        a = np.array(a, dtype=float)
        b = np.array(b, dtype=float)
        na, nb = len(a), len(b)
        sa, sb = a.std(ddof=1), b.std(ddof=1)
        sp = np.sqrt(((na - 1) * sa**2 + (nb - 1) * sb**2) / (na + nb - 2)) if (na + nb - 2) > 0 else 0.0
        return (a.mean() - b.mean()) / sp if sp > 0 else 0.0

    def p_value_from_t(t, df):
        try:
            from scipy import stats
            return 2 * stats.t.sf(abs(t), df)
        except Exception:
            # fallback approximate using survival function from mpmath if scipy missing
            try:
                import mpmath as mp
                return 2 * mp.qf(t, df)
            except Exception:
                return None

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.4))
    specs = [
        ('pdr_end2end_mean', 'End-to-End PDR', (0, 1.05), 0),
        ('total_energy_consumed', 'Energy (J)', None, 1),
    ]
    width = 0.32
    xs_centers = np.arange(len(topos))
    colors = {
        'BASE': '#009E73',   # vivid green
        'ROBUST': '#E67900', # warm orange
    }
    labels = {'BASE': method_label('AETHER_energy'), 'ROBUST': method_label('AETHER_robust')}

    for metric, ylabel, ylim, col in specs:
        ax = axes[col]
        base_means, robust_means, base_ci, robust_ci, d_vals, p_vals = [], [], [], [], [], []
        for topo in topos:
            base = js[topo][metric]['BASE']
            rob = js[topo][metric]['ROBUST']
            base_means.append(base['mean'])
            robust_means.append(rob['mean'])
            base_ci.append(base['ci95'])
            robust_ci.append(rob['ci95'])
            d_vals.append(cohen_d(base.get('values', []), rob.get('values', [])))
            p_vals.append(p_value_from_t(js[topo][metric]['welch_t'].get('t_stat'), js[topo][metric]['welch_t'].get('df')))

        ax.bar(xs_centers - width/2, base_means, yerr=base_ci, capsize=2,
               color=colors['BASE'], edgecolor='none', linewidth=0.0, label=labels['BASE'],
               width=width, error_kw={'elinewidth':0.8, 'capthick':0.8, 'ecolor':'#666'})
        ax.bar(xs_centers + width/2, robust_means, yerr=robust_ci, capsize=2,
               color=colors['ROBUST'], edgecolor='none', linewidth=0.0, label=labels['ROBUST'],
               width=width, error_kw={'elinewidth':0.8, 'capthick':0.8, 'ecolor':'#666'})
        ax.set_xticks(xs_centers)
        ax.set_xticklabels([pretty_topo(t) for t in topos], rotation=0)
        ax.set_ylabel(ylabel)
        if ylim is not None:
            ax.set_ylim(*ylim)
        ax.set_title(f'{ylabel} (50 runs, mean ± 95% CI)', fontsize=11, fontweight='bold')
        ax.grid(False)

        # annotate significance + effect size
        for i, topo in enumerate(topos):
            local_max = max(base_means[i] + base_ci[i], robust_means[i] + robust_ci[i])
            if ylim is not None:
                y_pair = local_max + 0.04
                top_needed = y_pair + 0.03
            else:
                scale = max(base_means[i], robust_means[i])
                y_pair = local_max + 0.08 * (scale if scale > 0 else 1.0)
                top_needed = y_pair + 0.06 * (scale if scale > 0 else 1.0)
            _ensure_top_margin(ax, top_needed)
            p = p_vals[i]
            sig = _sig_label(p)
            n_runs = len(js[topo][metric]['BASE'].get('values', []))
            ax.text(i, y_pair, f'{sig}  d={d_vals[i]:.2f}', ha='center', va='bottom', fontsize=8, color='#333', alpha=0.9)
            ax.text(i, y_pair - 0.05*(ax.get_ylim()[1]-ax.get_ylim()[0]), f'n={n_runs}', ha='center', va='bottom', fontsize=7, color='#666')

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02))
    _add_stats_footer(axes[0], 'Significance: 50 runs per small topology; Holm/BH-corrected Welch t-tests')
    fig.tight_layout(rect=[0, 0.05, 1, 0.96])
    out_base = os.path.join(PLOT_DIR, 'paper_multi_topo_sig_combo')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')

def fig_multi_topo_delta():
    path = os.path.join(DATA_DIR, 'significance_compare_multi_topo_50x200.json')
    if not os.path.exists(path):
        print('Skip multi-topo delta: missing', path)
        return
    js = json.load(open(path, 'r', encoding='utf-8'))
    topos = sorted(list(js.keys()))
    # Append large-scale points from large_scale_long.json if available
    try:
        ls_path = os.path.join(DATA_DIR, 'large_scale_long.json')
        if os.path.exists(ls_path):
            ls = json.load(open(ls_path, 'r', encoding='utf-8'))
            for topo in ['uniform_300', 'uniform_500']:
                if topo in ls:
                    e = ls[topo]['AERIS_energy']
                    r = ls[topo]['AERIS_robust']
                    js[topo] = {
                        'pdr_end2end_mean': {
                            'BASE': {'mean': e.get('packet_delivery_ratio_end2end', 0.0), 'ci95': 0.0, 'values': [e.get('packet_delivery_ratio_end2end', 0.0)]},
                            'ROBUST': {'mean': r.get('packet_delivery_ratio_end2end', 0.0), 'ci95': 0.0, 'values': [r.get('packet_delivery_ratio_end2end', 0.0)]},
                            'welch_t': {'t_stat': 0.0, 'df': float('inf')}
                        },
                        'total_energy_consumed': {
                            'BASE': {'mean': e.get('total_energy_consumed', 0.0), 'ci95': 0.0, 'values': [e.get('total_energy_consumed', 0.0)]},
                            'ROBUST': {'mean': r.get('total_energy_consumed', 0.0), 'ci95': 0.0, 'values': [r.get('total_energy_consumed', 0.0)]},
                            'welch_t': {'t_stat': 0.0, 'df': float('inf')}
                        }
                    }
            topos = sorted(list(js.keys()))
    except Exception as e:
        print('Append large-scale to delta failed:', e)
    pdr_base = []
    pdr_rob = []
    eng_base = []
    eng_rob = []
    for topo in topos:
        pdr_base.append(js[topo]['pdr_end2end_mean']['BASE']['mean'])
        pdr_rob.append(js[topo]['pdr_end2end_mean']['ROBUST']['mean'])
        eng_base.append(js[topo]['total_energy_consumed']['BASE']['mean'])
        eng_rob.append(js[topo]['total_energy_consumed']['ROBUST']['mean'])
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    for i, topo in enumerate(topos):
        ax.scatter(eng_base[i], pdr_base[i], color='#009E73', marker='o', s=60, label='AERIS-E' if i==0 else "")
        ax.scatter(eng_rob[i], pdr_rob[i], color='#E67900', marker='D', s=70, label='AERIS-R' if i==0 else "")
        ax.arrow(eng_base[i], pdr_base[i],
                 eng_rob[i]-eng_base[i],
                 pdr_rob[i]-pdr_base[i],
                 length_includes_head=True,
                 head_width=0.004,
                 head_length=0.25,
                 fc='#555', ec='#555', alpha=0.8)
        dp = (pdr_rob[i]-pdr_base[i])*100
        de = eng_rob[i]-eng_base[i]
        ax.text( (eng_base[i]+eng_rob[i])/2,
                 (pdr_base[i]+pdr_rob[i])/2 + 0.015,
                 f'{topo}: ΔPDR={dp:.2f}%, ΔE={de:.2f} J',
                 ha='center', va='bottom', fontsize=8, color='#333')
    ax.set_xlabel('Energy (J)')
    ax.set_ylabel('End-to-End PDR')
    ax.set_title('AERIS-R vs AERIS-E (Delta across topologies)', fontsize=11, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(loc='lower left', frameon=False)
    fig.tight_layout()
    out_base = os.path.join(PLOT_DIR, 'paper_multi_topo_delta')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')

def fig_dynamic_corridor_curated():
    """Curated dynamic corridor plot (PDR & Energy) with subset of protocols."""
    path = os.path.join(DATA_DIR, 'dynamic_corridor_compare_reps.json')
    if not os.path.exists(path):
        print('Skip dynamic corridor curated: missing', path)
        return
    data = json.load(open(path, 'r', encoding='utf-8'))
    # phases ordered
    phases = ['phase1', 'phase2', 'phase3', 'phase4']
    phase_labels = ['Shift 0 m', 'Shift 20 m', 'Shift 40 m', 'Shift 60 m']
    protocols = ['LEACH', 'PEGASIS', 'HEED', 'AERIS_energy', 'AERIS_robust']
    # aggregate over reps
    def agg(metric):
        means = {p: [] for p in protocols}
        for repk, repv in data.items():
            for ph in phases:
                for p in protocols:
                    node = repv.get(ph, {}).get(p)
                    if node and metric in node:
                        means[p].append((ph, node[metric]))
        # compute mean/std per phase
        out = {p: {'mean': [], 'std': []} for p in protocols}
        for ph in phases:
            for p in protocols:
                vals = [v for (ph2, v) in means[p] if ph2 == ph]
                m = np.mean(vals) if vals else np.nan
                s = np.std(vals, ddof=1) if len(vals) > 1 else 0.0
                out[p]['mean'].append(m)
                out[p]['std'].append(s)
        return out
    pdr = agg('packet_delivery_ratio_end2end')
    eng = agg('total_energy_consumed')

    # infer replicate count for a truthful title
    n_reps = len(data)
    title = f"Dynamic Corridor (80 nodes, Intel-driven shadowing, {n_reps} replicates)"

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2), sharex=True)
    x = np.arange(len(phases))
    width = 0.12  # tighter bars to avoid overlap
    legend_handles = []
    legend_labels = []
    for idx, p in enumerate(protocols):
        offset = (idx - (len(protocols) - 1) / 2) * width
        lbl = method_label(p)
        bar0 = axes[0].bar(x + offset, pdr[p]['mean'], yerr=pdr[p]['std'], capsize=2,
                           color=COLORS.get(p, '#999999'), edgecolor='white', linewidth=0.2,
                           label=lbl, width=width)
        axes[1].bar(x + offset, eng[p]['mean'], yerr=eng[p]['std'], capsize=2,
                    color=COLORS.get(p, '#999999'), edgecolor='white', linewidth=0.2,
                    label=lbl, width=width)
        legend_handles.append(bar0[0])
        legend_labels.append(lbl)
    axes[0].set_ylabel('End-to-End PDR')
    axes[1].set_ylabel('Total Energy (J)')
    axes[0].set_xticks(x); axes[1].set_xticks(x)
    axes[0].set_xticklabels(phase_labels, rotation=0)
    axes[1].set_xticklabels(phase_labels, rotation=0)
    axes[0].set_ylim(0.0, 1.05)
    axes[1].set_ylim(0, max(eng[p]['mean'][0] for p in protocols if eng[p]['mean']) * 1.2 if protocols else 1)
    axes[0].grid(axis='y', linestyle='--', alpha=0.25)
    axes[1].grid(axis='y', linestyle='--', alpha=0.25)
    # Place legend directly under title, centered
    fig.suptitle(title, fontsize=12, fontweight='bold', y=1.03)
    fig.legend(legend_handles, legend_labels,
               loc='upper center', ncol=min(5, len(legend_handles)), frameon=False, bbox_to_anchor=(0.5, 1.00))
    fig.tight_layout(rect=[0, 0.02, 1, 0.90])
    out_base = os.path.join(PLOT_DIR, 'paper_dynamic_corridor_curated')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')


def fig_dynamic_moving_bs_curated():
    """Curated moving-BS corridor plot (PDR & Energy) with subset of protocols."""
    path = os.path.join(DATA_DIR, 'dynamic_moving_bs_compare_reps.json')
    if not os.path.exists(path):
        print('Skip dynamic moving BS curated: missing', path)
        return
    data = json.load(open(path, 'r', encoding='utf-8'))
    phases = ['bs_phase1', 'bs_phase2', 'bs_phase3', 'bs_phase4']
    phase_labels = ['BS at 260 m', 'BS at 300 m', 'BS at 340 m', 'BS at 380 m']
    protocols = ['LEACH', 'PEGASIS', 'HEED', 'AERIS_energy', 'AERIS_robust']

    def agg(metric):
        means = {p: [] for p in protocols}
        for repv in data.values():
            for ph in phases:
                for p in protocols:
                    node = repv.get(ph, {}).get(p)
                    if node and metric in node:
                        means[p].append((ph, node[metric]))
        out = {p: {'mean': [], 'std': []} for p in protocols}
        for ph in phases:
            for p in protocols:
                vals = [v for (ph2, v) in means[p] if ph2 == ph]
                m = np.mean(vals) if vals else np.nan
                s = np.std(vals, ddof=1) if len(vals) > 1 else 0.0
                out[p]['mean'].append(m)
                out[p]['std'].append(s)
        return out

    pdr = agg('packet_delivery_ratio_end2end')
    eng = agg('total_energy_consumed')
    n_reps = len(data)
    title = f"Moving BS Corridor (80 nodes, {n_reps} replicates)"

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2), sharex=True)
    x = np.arange(len(phases))
    width = 0.12
    legend_handles = []
    legend_labels = []
    for idx, p in enumerate(protocols):
        offset = (idx - (len(protocols) - 1) / 2) * width
        lbl = method_label(p)
        bar0 = axes[0].bar(x + offset, pdr[p]['mean'], yerr=pdr[p]['std'], capsize=2,
                           color=COLORS.get(p, '#999999'), edgecolor='white', linewidth=0.15,
                           label=lbl, width=width)
        axes[1].bar(x + offset, eng[p]['mean'], yerr=eng[p]['std'], capsize=2,
                    color=COLORS.get(p, '#999999'), edgecolor='white', linewidth=0.15,
                    label=lbl, width=width)
        legend_handles.append(bar0[0])
        legend_labels.append(lbl)
    axes[0].set_ylabel('End-to-End PDR')
    axes[1].set_ylabel('Total Energy (J)')
    axes[0].set_xticks(x); axes[1].set_xticks(x)
    axes[0].set_xticklabels(phase_labels, rotation=0)
    axes[1].set_xticklabels(phase_labels, rotation=0)
    axes[0].set_ylim(0.0, 1.05)
    max_eng = max((m for p in protocols for m in eng[p]['mean'] if m == m), default=1)
    axes[1].set_ylim(0, max_eng * 1.25)
    axes[0].grid(axis='y', linestyle='--', alpha=0.25)
    axes[1].grid(axis='y', linestyle='--', alpha=0.25)
    # place legend directly below title
    fig.suptitle(title, fontsize=12, fontweight='bold', y=1.03)
    fig.legend(legend_handles, legend_labels,
               loc='upper center', ncol=min(5, len(legend_handles)), frameon=False, bbox_to_anchor=(0.5, 1.00))
    fig.tight_layout(rect=[0, 0.02, 1, 0.90])
    out_base = os.path.join(PLOT_DIR, 'paper_dynamic_moving_bs_curated')
    save_figure(fig, out_base + '.svg')
    print('Saved', out_base + '.svg')


def fig_uncertainty_grid_heatmap():
    path = os.path.join(DATA_DIR, 'corridor_uncertainty_grid_50x200.json')
    if not os.path.exists(path):
        print('Skip uncertainty grid: missing', path)
        return
    js = json.load(open(path, 'r', encoding='utf-8'))
    # Expect a list of records
    if isinstance(js, dict) and 'results' in js:
        rows = js['results']
    elif isinstance(js, list):
        rows = js
    else:
        rows = []
    if not rows:
        print('Uncertainty grid has no rows')
        return
    lambdas = sorted({ float(r.get('lambda_uncertainty') or r.get('lambda', 0.0)) for r in rows })
    confs   = sorted({ float(r.get('conf_threshold') or r.get('threshold', 0.0)) for r in rows })
    lam_idx = {v:i for i,v in enumerate(lambdas)}
    con_idx = {v:i for i,v in enumerate(confs)}
    P = np.full((len(lambdas), len(confs)), np.nan)
    E = np.full((len(lambdas), len(confs)), np.nan)
    for r in rows:
        lam = float(r.get('lambda_uncertainty') or r.get('lambda', 0.0))
        th  = float(r.get('conf_threshold') or r.get('threshold', 0.0))
        # robustly get metrics
        pdr = r.get('pdr_end2end_mean')
        if pdr is None and isinstance(r.get('pdr_end2end'), dict):
            pdr = r['pdr_end2end'].get('mean')
        energy = r.get('total_energy_consumed_mean')
        if energy is None and isinstance(r.get('total_energy_consumed'), dict):
            energy = r['total_energy_consumed'].get('mean')
        if lam in lam_idx and th in con_idx:
            P[lam_idx[lam], con_idx[th]] = pdr if pdr is not None else np.nan
            E[lam_idx[lam], con_idx[th]] = energy if energy is not None else np.nan
    # Plot 1x2 heatmaps
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    # PDR
    im0 = axes[0].imshow(P, origin='lower', aspect='auto', cmap='viridis', vmin=0.0, vmax=1.0)
    axes[0].set_title('End-to-End PDR')
    axes[0].set_xlabel('conf_threshold')
    axes[0].set_ylabel('lambda_uncertainty')
    axes[0].set_xticks(range(len(confs))); axes[0].set_xticklabels([f'{c:.2f}' for c in confs], rotation=45)
    axes[0].set_yticks(range(len(lambdas))); axes[0].set_yticklabels([f'{l:.2f}' for l in lambdas])
    cbar0 = fig.colorbar(im0, ax=axes[0]); cbar0.set_label('PDR')
    # Energy
    im1 = axes[1].imshow(E, origin='lower', aspect='auto', cmap='magma')
    axes[1].set_title('Energy (J)')
    axes[1].set_xlabel('conf_threshold')
    axes[1].set_ylabel('lambda_uncertainty')
    axes[1].set_xticks(range(len(confs))); axes[1].set_xticklabels([f'{c:.2f}' for c in confs], rotation=45)
    axes[1].set_yticks(range(len(lambdas))); axes[1].set_yticklabels([f'{l:.2f}' for l in lambdas])
    cbar1 = fig.colorbar(im1, ax=axes[1]); cbar1.set_label('Energy (J)')
    plt.tight_layout()
    out_base = os.path.join(PLOT_DIR, 'paper_uncertainty_grid')
    maybe_remove_titles(fig)
    fig.savefig(out_base + '.svg', bbox_inches='tight')
    plt.close()
    print('Saved', out_base + '.svg')

# Intel: classical envmap comparison (SARIMAX/ETS/TBATS)
def fig_intel_classical_envmap():
    p_ets = os.path.join(DATA_DIR, 'intel_ets_envmap_compare.json')
    if not os.path.exists(p_ets):
        print('Skip classical envmap: missing', p_ets)
        return
    js = json.load(open(p_ets, 'r', encoding='utf-8'))

    # The classical runner stores metrics under AETHER_* and metadata under 'classical'
    model_name = str(js.get('classical', {}).get('model', 'ets')).upper()

    energy_node = js.get('AETHER_energy', {})
    robust_node = js.get('AETHER_robust', {})

    # Prepare data for Energy plot
    e_labels = []
    e_colors = []
    e_values = []
    if energy_node:
        e_labels.append(f'{model_name}_energy')
        e_colors.append('#009E73' if model_name == 'ETS' else '#56B4E9')
        e_values.append(energy_node.get('total_energy_consumed', 0.0))

    # Prepare data for PDR plot
    p_labels = []
    p_colors = []
    p_values = []
    if robust_node:
        p_labels.append(f'{model_name}_robust')
        p_colors.append('#D55E00' if model_name == 'ETS' else '#E69F00')
        p_values.append(robust_node.get('packet_delivery_ratio_end2end', robust_node.get('packet_deliveryy_ratio_end2end', 0.0)))

    if not e_labels and not p_labels:
        print('Skip classical envmap: no usable entries in', p_ets)
        return

    # Energy
    if e_labels:
        fig, ax = plt.subplots(figsize=(7.2, 3.4))
        _bar(ax, e_labels, e_values, e_colors, 'Energy (J)', f'Intel: Classical envmap ({model_name}) – Energy')
        out_base = os.path.join(PLOT_DIR, 'paper_intel_classical_envmap_energy')
        save_figure(fig, out_base + '.svg')
        print('Saved', out_base + '.svg')

    # PDR
    if p_labels:
        fig, ax = plt.subplots(figsize=(7.2, 3.4))
        _bar(
            ax,
            p_labels,
            p_values,
            p_colors,
            'End-to-End PDR',
            f'Intel: Classical envmap ({model_name}) – PDR',
            ylim=(0, 1.05),
        )
        out_base = os.path.join(PLOT_DIR, 'paper_intel_classical_envmap_pdr')
        save_figure(fig, out_base + '.svg')
        print('Saved', out_base + '.svg')

def fig_intel_pdr_gardner_altman():
    """Intel PDR – Gardner–Altman paired mean-difference plot
    Inputs: results/significance_compare_intel_parallel.json with keys:
      - pdr_end2end_mean: { BASE: {values:[...]}, ROBUST:{values:[...]} }
    Output:
      - results/plots/paper_intel_pdr_gardner_altman.svg
      - results/publication_figures/pdr_gardner_altman.svg
    """
    import os, json
    import numpy as np
    import matplotlib.pyplot as plt

    path = os.path.join(DATA_DIR, 'significance_compare_intel_parallel.json')
    if not os.path.exists(path):
        print('Skip pdr_gardner_altman: missing', path)
        return
    js = json.load(open(path, 'r', encoding='utf-8'))
    base_vals = js.get('pdr_end2end_mean', {}).get('BASE', {}).get('values', [])
    rob_vals  = js.get('pdr_end2end_mean', {}).get('ROBUST', {}).get('values', [])
    if not base_vals or not rob_vals:
        print('Skip pdr_gardner_altman: missing raw values')
        return
    n = min(len(base_vals), len(rob_vals))
    base = np.asarray(base_vals[:n], dtype=float)
    rob  = np.asarray(rob_vals[:n], dtype=float)
    diffs = rob - base

    def _bootstrap_ci_mean(x, B=10000, alpha=0.05, seed=123):
        rng = np.random.default_rng(seed)
        x = np.asarray(x)
        n = len(x)
        boots = rng.choice(x, size=(B, n), replace=True).mean(axis=1)
        lo, hi = np.percentile(boots, [100*alpha/2, 100*(1-alpha/2)])
        return float(lo), float(hi)

    def _mean_and_ci(x):
        m = float(np.mean(x))
        lo, hi = _bootstrap_ci_mean(x)
        return m, lo, hi

    m_base, lo_base, hi_base = _mean_and_ci(base)
    m_rob,  lo_rob,  hi_rob  = _mean_and_ci(rob)
    m_diff, lo_diff, hi_diff = _mean_and_ci(diffs)

    # 计算效应量（Cohen's d），用于期刊呈现强度
    try:
        sd_base = float(np.std(base, ddof=1))
        sd_rob  = float(np.std(rob, ddof=1))
        # 合并标准差（独立样本近似；配对情况下此数值仅作参考）
        s_pooled = float(np.sqrt(((n-1)*sd_base**2 + (n-1)*sd_rob**2) / max(1, (2*n - 2))))
        cohen_d = float((m_rob - m_base) / s_pooled) if s_pooled > 0 else 0.0
        def _effect_bin(d):
            ad = abs(d)
            if ad >= 0.8: return 'large'
            if ad >= 0.5: return 'medium'
            if ad >= 0.2: return 'small'
            return 'trivial'
        eff_label = _effect_bin(cohen_d)
    except Exception:
        cohen_d, eff_label = 0.0, 'n/a'

    # Colors（尽量沿用已有配色，若无则提供后备）
    try:
        color_e = OKABE_ITO.get('AETHER_energy', '#1b9e77')
        color_r = OKABE_ITO.get('AETHER_robust', '#d95f02')
    except Exception:
        color_e, color_r = '#1b9e77', '#d95f02'

    labels = [method_label('AETHER_energy') if 'method_label' in globals() else 'AERIS-E',
              method_label('AETHER_robust') if 'method_label' in globals() else 'AERIS-R']

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
    axL, axR = axes[0], axes[1]

    # Left: paired raw points + mean±CI
    x0, x1 = 0, 1
    jitter = (np.random.default_rng(0).random(n) - 0.5) * 0.10
    axL.scatter(np.full(n, x0) + jitter, base, s=16, color=color_e, alpha=0.65, edgecolors='none')
    axL.scatter(np.full(n, x1) + jitter, rob,  s=16, color=color_r, alpha=0.65, edgecolors='none')
    for i in range(n):
        axL.plot([x0, x1], [base[i], rob[i]], color='0.82', linewidth=0.6, zorder=0)
    # mean ± 95% bootstrap percentile CI
    axL.errorbar([x0], [m_base], yerr=[[m_base-lo_base],[hi_base-m_base]], fmt='o', color='black', mfc=color_e, mec='black', capsize=4, lw=0.9)
    axL.errorbar([x1], [m_rob],  yerr=[[m_rob-lo_rob],[hi_rob-m_rob]],   fmt='o', color='black', mfc=color_r, mec='black', capsize=4, lw=0.9)
    axL.set_xticks([x0, x1])
    axL.set_xticklabels(labels, rotation=0)
    axL.set_ylabel('End-to-End PDR')
    axL.set_ylim(0, 1.05)
    axL.grid(axis='y', alpha=0.4)
    ttl_n = f" (n={n})" if n else ""
    axL.set_title('Intel: Paired PDR'+ttl_n)

    # Right: Gardner–Altman difference axis（robust - energy）
    xD = 0
    jitterD = (np.random.default_rng(1).random(n) - 0.5) * 0.10
    axR.axhline(0, color='black', lw=0.8, alpha=0.8)
    axR.scatter(np.full(n, xD) + jitterD, diffs, s=16, color='#4C72B0', alpha=0.65, edgecolors='none')
    axR.errorbar([xD+0.18], [m_diff], yerr=[[m_diff-lo_diff],[hi_diff-m_diff]], fmt='s', color='black', mfc='#4C72B0', mec='black', capsize=4, lw=0.9)
    axR.set_xlim(-0.35, 0.55)
    # y-limit padding based on data
    y_min = float(min(np.min(diffs), lo_diff))
    y_max = float(max(np.max(diffs), hi_diff))
    pad = max(0.02, 0.05 * (y_max - y_min if y_max > y_min else 1.0))
    axR.set_ylim(y_min - pad, y_max + pad)
    axR.set_xticks([xD])
    axR.set_xticklabels(['Δ (R − E)'])
    axR.set_ylabel('Absolute difference (percentage points)')
    # 将差值以pp显示刻度说明
    axR_right = axR.secondary_yaxis('right', functions=(lambda v: v*100.0, lambda v: v/100.0))
    # 增加右侧轴标签与图边缘的距离，避免重叠
    axR_right.set_ylabel('Δ (percentage points)', labelpad=12)
    axR.grid(axis='y', alpha=0.4)

    # 注释核心数字
    delta_pp = (m_diff * 100.0)
    # 采用白底圆角框并稍微右移，避免与边框/网格线重叠
    axR.text(xD+0.28, m_diff, f"Δ = {delta_pp:+.1f} pp\n95% CI [{lo_diff*100:.1f}, {hi_diff*100:.1f}] pp\nCohen's d = {cohen_d:.2f} ({eff_label})",
             va='center', ha='left', fontsize=9,
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.2'))

    plt.tight_layout()
    maybe_remove_titles(fig)
    # 保存到原 plots 与 publication_figures 两处
    out1 = os.path.join(PLOT_DIR, 'paper_intel_pdr_gardner_altman.svg')
    save_figure(fig, out1)
    print('Saved', out1)

# [EMERGENCY MINIMAL SET] — Helpers and figures for lean visuals

def _copy_to_sensors(out_paths):
    try:
        base_results = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
        sensors_dir = os.path.join(base_results, 'Sensors_figures')
        os.makedirs(sensors_dir, exist_ok=True)
        copied = []
        for p in out_paths:
            if not p:
                continue
            ap = p if os.path.isabs(p) else os.path.abspath(p)
            if os.path.exists(ap):
                dst = os.path.join(sensors_dir, os.path.basename(ap))
                shutil.copyfile(ap, dst)
                copied.append(dst)
        return copied
    except Exception:
        return []


def fig_intel_minimal_dots():
    """Minimal dot plots (Intel): AERIS-E vs AERIS-R for Energy & PDR."""
    path = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    if not os.path.exists(path):
        print('Skip intel minimal dots: missing', path)
        return []
    data = json.load(open(path, 'r', encoding='utf-8'))
    methods = ['AETHER_energy','AETHER_robust']
    labels = [method_label(m) for m in methods]
    colors = [method_color(m) for m in methods]
    energy = [data[m]['total_energy_consumed'] for m in methods]
    pdr = [data[m]['packet_delivery_ratio_end2end'] for m in methods]

    outs = []
    # Energy dot plot
    fig, ax = plt.subplots(figsize=(5.8, 2.8))
    xs = np.arange(len(labels))
    ax.hlines(y=0, xmin=-0.5, xmax=len(labels)-0.5, colors='#D0D0D0', linewidth=0.8)
    ax.scatter(xs, energy, s=46, color=colors, zorder=3)
    ax.set_xticks(xs); ax.set_xticklabels(labels)
    ax.set_ylabel('Energy (J)')
    ax.grid(axis='y', alpha=0.25)
    ax.set_title('Intel: Energy (lean)')
    out_base = os.path.join(PLOT_DIR, 'paper_intel_energy_minimal')
    save_figure(fig, out_base + '.svg')
    outs.append(out_base + '.svg')

    # PDR dot plot
    fig, ax = plt.subplots(figsize=(5.8, 2.8))
    ax.hlines(y=0, xmin=-0.5, xmax=len(labels)-0.5, colors='#D0D0D0', linewidth=0.8)
    ax.scatter(xs, pdr, s=46, color=colors, zorder=3)
    ax.set_xticks(xs); ax.set_xticklabels(labels)
    ax.set_ylabel('End-to-End PDR')
    ax.set_ylim(0, 1.05)
    ax.grid(axis='y', alpha=0.25)
    ax.set_title('Intel: PDR (lean)')
    out_base = os.path.join(PLOT_DIR, 'paper_intel_pdr_minimal')
    save_figure(fig, out_base + '.svg')
    outs.append(out_base + '.svg')

    copied = _copy_to_sensors(outs)
    print('Copied to Sensors_figures:', copied)
    return outs


def fig_intel_baselines_panels_minimal():
    """Two-panel horizontal lollipop charts for Energy & PDR across methods."""
    p_aether = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    p_base = os.path.join(DATA_DIR, 'intel_baselines_all.json')
    if not (os.path.exists(p_aether) and os.path.exists(p_base)):
        print('Skip baselines panels minimal: missing inputs')
        return []
    a = json.load(open(p_aether, 'r', encoding='utf-8'))
    b = json.load(open(p_base, 'r', encoding='utf-8'))

    methods = ['AETHER_energy','AETHER_robust','LEACH','HEED','PEGASIS','TEEN']
    labels = [method_label(m) for m in methods]
    colors = [method_color(m) for m in methods]
    energy = [a[m]['total_energy_consumed'] if m in a else b[m]['total_energy_consumed'] for m in methods]
    pdr = [a[m]['packet_delivery_ratio_end2end'] if m in a else b[m]['packet_delivery_ratio_end2end'] for m in methods]

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.4))
    # Energy lollipop (horizontal)
    ax = axes[0]
    y = np.arange(len(labels))
    ax.hlines(y, xmin=0, xmax=energy, color='#D0D0D0', linewidth=1.0)
    for yi, ci in enumerate(colors):
        ax.plot([energy[yi]], [yi], 'o', color=ci)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel('Energy (J)')
    ax.set_title('Energy across methods')
    ax.grid(axis='x', alpha=0.25)

    # PDR lollipop (horizontal)
    ax = axes[1]
    y = np.arange(len(labels))
    ax.hlines(y, xmin=0, xmax=pdr, color='#D0D0D0', linewidth=1.0)
    for yi, ci in enumerate(colors):
        ax.plot([pdr[yi]], [yi], 'o', color=ci)
    ax.set_yticks(y); ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel('End-to-End PDR')
    ax.set_title('PDR across methods')
    ax.grid(axis='x', alpha=0.25)

    out_base = os.path.join(PLOT_DIR, 'paper_intel_baselines_panels_minimal')
    save_figure(fig, out_base + '.svg')
    copied = _copy_to_sensors([out_base + '.svg'])
    print('Copied to Sensors_figures:', copied)
    return [out_base + '.svg']


def fig_method_flowchart_minimal():
    """Minimal flowchart for method pipeline."""
    from matplotlib.patches import Rectangle, FancyArrow
    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    ax.axis('off')

    def box(x, y, w, h, text):
        rect = Rectangle((x, y), w, h, linewidth=1.0, edgecolor='black', facecolor='white')
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=10)
        return x + w, y + h/2

    def arrow(x0, y0, x1, y1):
        ax.add_patch(FancyArrow(x0, y0, x1 - x0, y1 - y0, width=0.01, head_width=0.06, length_includes_head=True, color='black'))

    # Layout
    x0, y0 = 0.05, 0.6
    bx1, by1 = box(x0, y0, 0.22, 0.18, 'Intel Traces\n(traffic/channel/env)')
    bx2, by2 = box(0.35, 0.6, 0.22, 0.18, 'Environment Mapper\n(ML forecaster)')
    bx3, by3 = box(0.65, 0.6, 0.25, 0.18, 'AERIS Policy Selector\n(energy / robust)')

    bx4, by4 = box(0.20, 0.22, 0.25, 0.18, 'WSN Scheduler\n(cluster/routes/duty)')
    bx5, by5 = box(0.60, 0.22, 0.28, 0.18, 'Outcomes\nPDR, Energy, Safety')

    arrow(bx1, by1, 0.35, by2)
    arrow(0.35 + 0.22, by2, 0.65, by3)
    arrow(0.65 + 0.25, by3, 0.60, by5)
    arrow(0.35 + 0.11, 0.60, 0.35 + 0.11, 0.22 + 0.18)
    arrow(0.20 + 0.25, 0.22 + 0.09, 0.60, 0.22 + 0.09)

    out_base = os.path.join(PLOT_DIR, 'paper_method_flowchart')
    save_figure(fig, out_base + '.svg')
    copied = _copy_to_sensors([out_base + '.svg'])
    print('Copied to Sensors_figures:', copied)
    return [out_base + '.svg']


def generate_emergency_minimal_set():
    """Generate a lean 7-figure set and copy to Sensors_figures."""
    outs = []
    try:
        outs += fig_intel_minimal_dots() or []
    except Exception as e:
        print('intel_minimal_dots failed:', e)
    try:
        outs += fig_intel_baselines_panels_minimal() or []
    except Exception as e:
        print('baselines_panels_minimal failed:', e)
    # Reuse existing high-value figures
    try:
        fig_intel_sig_combined()
        outs += _copy_to_sensors([os.path.join(PLOT_DIR, 'paper_intel_sig_combined.svg')])
    except Exception as e:
        print('sig_combined failed:', e)
    try:
        fig_intel_ablation()
        outs += _copy_to_sensors([
            os.path.join(PLOT_DIR, 'paper_intel_ablation_energy.svg'),
            os.path.join(PLOT_DIR, 'paper_intel_ablation_pdr.svg'),
        ])
    except Exception as e:
        print('ablation failed:', e)
    try:
        outs += fig_method_flowchart_minimal() or []
    except Exception as e:
        print('flowchart failed:', e)
    print('Emergency minimal set generated/copied:', outs)
    return outs

# Publication-grade global style for all figures

def apply_pub_style():
    mpl.rcParams.update({
        'font.family': 'Palatino Linotype',
        'font.size': 8.5,
        'axes.labelsize': 8.5,
        'axes.titlesize': 9.5,
        'legend.fontsize': 8,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'axes.linewidth': 0.8,
        'lines.linewidth': 0.9,
        'lines.markersize': 4.2,
        'patch.edgecolor': 'none',
        'legend.frameon': False,
        'axes.axisbelow': True,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'xtick.direction': 'out',
        'ytick.direction': 'out',
        'xtick.major.size': 3.0,
        'ytick.major.size': 3.0,
        'xtick.minor.size': 1.5,
        'ytick.minor.size': 1.5,
        'grid.color': '#E6E6E6',
        'grid.linewidth': 0.6,
        'grid.alpha': 0.25,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.03,
        'savefig.dpi': 300,
        'figure.constrained_layout.use': True,
        'svg.fonttype': 'none',
    })

# High-quality dumbbell plots replacing minimal dots

def fig_intel_minimal_dumbbells():
    apply_pub_style()
    path = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    if not os.path.exists(path):
        print('Skip intel dumbbells: missing', path)
        return []
    data = json.load(open(path, 'r', encoding='utf-8'))
    methods = ['AETHER_energy','AETHER_robust']
    labels = [method_label(m) for m in methods]
    colors = [method_color(m) for m in methods]
    energy = [data[m]['total_energy_consumed'] for m in methods]
    pdr = [data[m]['packet_delivery_ratio_end2end'] for m in methods]

    outs = []

    # Energy dumbbell (horizontal, single category)
    fig, ax = plt.subplots(figsize=(3.5, 1.9))
    y = 0
    x0, x1 = energy
    x_min, x_max = min(x0, x1), max(x0, x1)
    pad = 0.06 * (x_max - x_min + 1e-9)
    ax.hlines(y, x_min - pad, x_max + pad, color='#E6E6E6', linewidth=0.8, zorder=1)
    ax.plot([x0, x1], [y, y], '-', color='#B0B0B0', linewidth=1.2, zorder=2)
    ax.plot([x0], [y], 'o', color=colors[0], markersize=4.5, zorder=3)
    ax.plot([x1], [y], 'o', color=colors[1], markersize=4.5, zorder=3)
    ax.text(x0, y+0.12, f"{x0:.1f}", ha='center', va='bottom', fontsize=8)
    ax.text(x1, y-0.12, f"{x1:.1f}", ha='center', va='top', fontsize=8)
    delta = x1 - x0
    ax.text((x0+x1)/2, y+0.32, f"Δ {delta:+.1f} J", ha='center', va='bottom', fontsize=8.2)
    ax.set_yticks([y]); ax.set_yticklabels(['Intel'])
    ax.set_xlabel('Energy (J) — lower is better')
    ax.set_title('AERIS-E vs AERIS-R — Energy')
    ax.grid(axis='x', alpha=0.25)
    out_base = os.path.join(PLOT_DIR, 'paper_intel_energy_minimal')
    save_figure(fig, out_base + '.svg')
    outs.append(out_base + '.svg')

    # PDR dumbbell (horizontal, single category)
    fig, ax = plt.subplots(figsize=(3.5, 1.9))
    y = 0
    x0, x1 = pdr
    x_min, x_max = min(x0, x1), max(x0, x1)
    pad = 0.05 * (x_max - x_min + 1e-9)
    ax.hlines(y, 0, 1.05, color='#EDEDED', linewidth=0.8, zorder=1)
    ax.plot([x0, x1], [y, y], '-', color='#B0B0B0', linewidth=1.2, zorder=2)
    ax.plot([x0], [y], 'o', color=colors[0], markersize=4.5, zorder=3)
    ax.plot([x1], [y], 'o', color=colors[1], markersize=4.5, zorder=3)
    ax.text(x0, y+0.12, f"{x0:.2f}", ha='center', va='bottom', fontsize=8)
    ax.text(x1, y-0.12, f"{x1:.2f}", ha='center', va='top', fontsize=8)
    delta = x1 - x0
    ax.text((x0+x1)/2, y+0.32, f"Δ {delta:+.2f}", ha='center', va='bottom', fontsize=8.2)
    ax.set_xlim(0, 1.05)
    ax.set_yticks([y]); ax.set_yticklabels(['Intel'])
    ax.set_xlabel('End-to-end PDR — higher is better')
    ax.set_title('AERIS-E vs AERIS-R — PDR')
    ax.grid(axis='x', alpha=0.25)
    out_base = os.path.join(PLOT_DIR, 'paper_intel_pdr_minimal')
    save_figure(fig, out_base + '.svg')
    outs.append(out_base + '.svg')

    copied = _copy_to_sensors(outs)
    print('Copied to Sensors_figures:', copied)
    return outs

# Publication-grade baselines comparison (two-panel lollipop)

def fig_intel_baselines_panels_pub():
    apply_pub_style()
    p_aether = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    p_base = os.path.join(DATA_DIR, 'intel_baselines_all.json')
    if not (os.path.exists(p_aether) and os.path.exists(p_base)):
        print('Skip baselines panels pub: missing inputs')
        return []
    a = json.load(open(p_aether, 'r', encoding='utf-8'))
    b = json.load(open(p_base, 'r', encoding='utf-8'))

    methods = ['AETHER_energy','AETHER_robust','LEACH','HEED','PEGASIS','TEEN']
    rows = []
    for m in methods:
        src = a if m in a else b
        if m in src:
            rows.append({
                'm': m,
                'label': method_label(m),
                'energy': src[m]['total_energy_consumed'],
                'pdr': src[m]['packet_delivery_ratio_end2end'],
                'is_aeris': m in ['AETHER_energy','AETHER_robust'],
            })
    if not rows:
        print('Skip baselines panels pub: no methods found')
        return []
    # Sort by PDR descending for consistent ordering across panels
    rows.sort(key=lambda r: r['pdr'], reverse=True)

    labels = [r['label'] for r in rows]
    energy = [r['energy'] for r in rows]
    pdr = [r['pdr'] for r in rows]
    colors = [method_color(r['m']) for r in rows]

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2), sharey=True)

    def panel_tag(ax, tag):
        pass

    # Panel a: Energy (lower is better)
    ax = axes[0]
    y = np.arange(len(labels))
    ax.hlines(y, xmin=0, xmax=energy, color='#D0D0D0', linewidth=1.0)
    for yi, (val, ci) in enumerate(zip(energy, colors)):
        ax.plot([val], [yi], 'o', color=ci, markersize=4.2)
        if PAPER_VALUE_LABELS:
            ax.text(val, yi, f" {val:.1f}", va='center', ha='left', fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel('Energy (J) — lower is better')
    ax.set_title('Energy across methods')
    ax.grid(axis='x', alpha=0.25)
    panel_tag(ax, '')

    # Panel b: PDR (higher is better)
    ax = axes[1]
    y = np.arange(len(labels))
    ax.hlines(y, xmin=0, xmax=pdr, color='#D0D0D0', linewidth=1.0)
    for yi, (val, ci) in enumerate(zip(pdr, colors)):
        ax.plot([val], [yi], 'o', color=ci, markersize=4.2)
        if PAPER_VALUE_LABELS:
            ax.text(val, yi, f" {val:.2f}", va='center', ha='left', fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel('End-to-end PDR — higher is better')
    ax.set_title('PDR across methods')
    ax.grid(axis='x', alpha=0.25)
    panel_tag(ax, '')

    # Legend: explicit protocols
    handles = [
        mpatches.Patch(color=method_color('LEACH'), label='LEACH'),
        mpatches.Patch(color=method_color('HEED'), label='HEED'),
        mpatches.Patch(color=method_color('PEGASIS'), label='PEGASIS'),
        mpatches.Patch(color=method_color('TEEN'), label='TEEN'),
        mpatches.Patch(color=method_color('AETHER_energy'), label='AERIS-E'),
        mpatches.Patch(color=method_color('AETHER_robust'), label='AERIS-R'),
    ]
    fig.legend(
        handles=handles,
        loc='upper center',
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 1.02),
        fontsize=9
    )
    # Figure-level footer removed to avoid overlap
    _add_stats_footer(axes[0], '')

    out_base = os.path.join(PLOT_DIR, 'paper_intel_baselines_panels')
    save_figure(fig, out_base + '.svg')
    copied = _copy_to_sensors([out_base + '.svg'])
    print('Copied to Sensors_figures:', copied)
    return [out_base + '.svg']


def fig_intel_baselines_relative_panels_pub():
    """Publication-grade two-panel lollipop of relative performance vs best baseline.
    PDR is normalized to max among classical baselines; Energy is normalized to min among classical baselines.
    """
    apply_pub_style()
    p_aether = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    p_base = os.path.join(DATA_DIR, 'intel_baselines_all.json')
    if not (os.path.exists(p_aether) and os.path.exists(p_base)):
        print('Skip baselines relative panels pub: missing inputs')
        return []
    a = json.load(open(p_aether, 'r', encoding='utf-8'))
    b = json.load(open(p_base, 'r', encoding='utf-8'))

    methods = ['AETHER_energy','AETHER_robust','LEACH','HEED','PEGASIS','TEEN']
    rows = []
    for m in methods:
        src = a if m in a else b
        if m in src:
            rows.append({
                'm': m,
                'label': method_label(m),
                'energy': src[m]['total_energy_consumed'],
                'pdr': src[m]['packet_delivery_ratio_end2end'],
                'is_aeris': m in ['AETHER_energy','AETHER_robust'],
            })

    # Determine best baselines (exclude AERIS variants)
    baselines = [r for r in rows if not r['is_aeris']]
    if not baselines:
        print('Skip baselines relative panels pub: no baselines found')
        return []
    best_pdr = max(r['pdr'] for r in baselines)
    best_energy = min(r['energy'] for r in baselines)

    # Compute relative values
    for r in rows:
        r['pdr_rel'] = (r['pdr'] / best_pdr) if best_pdr > 0 else 0.0
        r['energy_rel'] = (best_energy / r['energy']) if r['energy'] > 0 else 0.0

    # Sort by relative PDR descending for consistent order across panels
    rows.sort(key=lambda r: r['pdr_rel'], reverse=True)

    labels = [r['label'] for r in rows]
    colors = [method_color(r['m']) for r in rows]
    pdr_rel = [r['pdr_rel'] for r in rows]
    energy_rel = [r['energy_rel'] for r in rows]

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2), sharey=True)
    y = np.arange(len(labels))

    # Panel 1: Relative PDR
    ax = axes[0]
    ax.hlines(y, xmin=0, xmax=pdr_rel, color='#D0D0D0', linewidth=1.0)
    for yi, ci in enumerate(colors):
        ax.plot([pdr_rel[yi]], [yi], 'o', color=ci)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel('Relative End-to-End PDR (best baseline = 1.0)')
    ax.set_title('Relative PDR across methods')
    ax.grid(axis='x', alpha=0.25)

    # Panel 2: Relative Energy
    ax = axes[1]
    ax.hlines(y, xmin=0, xmax=energy_rel, color='#D0D0D0', linewidth=1.0)
    for yi, ci in enumerate(colors):
        ax.plot([energy_rel[yi]], [yi], 'o', color=ci)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel('Relative Energy (best baseline = 1.0)')
    ax.set_title('Relative Energy across methods')
    ax.grid(axis='x', alpha=0.25)

    out_base = os.path.join(PLOT_DIR, 'paper_intel_baselines_relative')
    out_svg = out_base + '.svg'
    save_figure(fig, out_svg)
    print('Saved', out_svg)
    return [out_svg]

# Publication-grade simplified Pred-Env vs Conservative (two-panel)

def fig_intel_predenv_panels_pub():
    apply_pub_style()
    p_cons = os.path.join(DATA_DIR, 'intel_replay_compare.json')
    p_lstm = os.path.join(DATA_DIR, 'intel_lstm_envmap_compare.json')
    p_tcn  = os.path.join(DATA_DIR, 'intel_tcn_envmap_compare.json')
    if not (os.path.exists(p_cons) and os.path.exists(p_lstm) and os.path.exists(p_tcn)):
        print('Skip predenv panels pub: missing inputs')
        return []
    cons = json.load(open(p_cons, 'r', encoding='utf-8'))
    lstm = json.load(open(p_lstm, 'r', encoding='utf-8'))
    tcn  = json.load(open(p_tcn,  'r', encoding='utf-8'))

    labels = ['Conservative', 'LSTM', 'TCN']
    energy = [
        cons['AETHER_energy']['total_energy_consumed'],
        lstm['AETHER_energy']['total_energy_consumed'],
        tcn['AETHER_energy']['total_energy_consumed'],
    ]
    pdr = [
        cons['AETHER_robust']['packet_delivery_ratio_end2end'],
        lstm['AETHER_robust']['packet_delivery_ratio_end2end'],
        tcn['AETHER_robust']['packet_delivery_ratio_end2end'],
    ]
    colors = ['#9E9E9E', OKABE_ITO['blue'], OKABE_ITO['green']]

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.8), sharey=True)

    def panel_tag(ax, tag):
        pass

    # Panel a: Energy (AERIS-E)
    ax = axes[0]
    y = np.arange(len(labels))
    ax.hlines(y, xmin=0, xmax=energy, color='#D0D0D0', linewidth=1.0)
    for yi, (val, c) in enumerate(zip(energy, colors)):
        ax.plot([val], [yi], 'o', color=c, markersize=4.2)
        ax.text(val, yi, f" {val:.1f}", va='center', ha='left', fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel('Energy (J) — lower is better')
    ax.set_title('Env mapping → AERIS-E')
    ax.grid(axis='x', alpha=0.25)
    panel_tag(ax, 'a')

    # Panel b: PDR (AERIS-R)
    ax = axes[1]
    y = np.arange(len(labels))
    ax.hlines(y, xmin=0, xmax=pdr, color='#D0D0D0', linewidth=1.0)
    for yi, (val, c) in enumerate(zip(pdr, colors)):
        ax.plot([val], [yi], 'o', color=c, markersize=4.2)
        ax.text(val, yi, f" {val:.2f}", va='center', ha='left', fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel('End-to-end PDR — higher is better')
    ax.set_title('Env mapping → AERIS-R')
    ax.grid(axis='x', alpha=0.25)
    panel_tag(ax, 'b')

    out_base = os.path.join(PLOT_DIR, 'paper_intel_predenv_panels')
    save_figure(fig, out_base + '.svg')
    copied = _copy_to_sensors([out_base + '.svg'])
    print('Copied to Sensors_figures:', copied)
    return [out_base + '.svg']

# Polished method flowchart

def fig_method_flowchart_pub():
    apply_pub_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    ax.axis('off')

    def box(x, y, w, h, text):
        rect = Rectangle((x, y), w, h, linewidth=0.9, edgecolor='black', facecolor='white')
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=9)
        return x + w, y + h/2

    def arrow(x0, y0, x1, y1):
        ax.add_patch(FancyArrow(x0, y0, x1 - x0, y1 - y0, width=0.008, head_width=0.05, length_includes_head=True, color='black'))

    # Layout (normalized space)
    bx1, by1 = box(0.05, 0.62, 0.22, 0.18, 'Intel Traces\n(traffic/channel/env)')
    bx2, by2 = box(0.35, 0.62, 0.22, 0.18, 'Environment Mapper\n(ML forecaster)')
    bx3, by3 = box(0.65, 0.62, 0.25, 0.18, 'AERIS Policy Selector\n(energy / robust)')

    bx4, by4 = box(0.20, 0.20, 0.25, 0.18, 'WSN Scheduler\n(cluster/routes/duty)')
    bx5, by5 = box(0.60, 0.20, 0.28, 0.18, 'Outcomes\nPDR, Energy, Safety')

    arrow(bx1, by1, 0.35, by2)
    arrow(0.35 + 0.22, by2, 0.65, by3)
    arrow(0.65 + 0.25, by3, 0.60, by5)
    arrow(0.35 + 0.11, 0.62, 0.35 + 0.11, 0.20 + 0.18)
    arrow(0.20 + 0.25, 0.20 + 0.09, 0.60, 0.20 + 0.09)

    out_base = os.path.join(PLOT_DIR, 'paper_method_flowchart')
    save_figure(fig, out_base + '.svg')
    copied = _copy_to_sensors([out_base + '.svg'])
    print('Copied to Sensors_figures:', copied)
    return [out_base + '.svg']

# Orchestrator for publication-grade emergency set

def generate_emergency_pub_set():
    outs = []
    # Deprecated: minimal dumbbells are removed from publication-grade set
    # Rationale: reviewers prefer estimation plots and CI-rich comparisons
    # try:
    #     outs += fig_intel_minimal_dumbbells() or []
    # except Exception as e:
    #     print('intel_dumbbells failed:', e)
    try:
        outs += fig_intel_baselines_panels_pub() or []
    except Exception as e:
        print('baselines_panels_pub failed:', e)
    try:
        outs += fig_intel_predenv_panels_pub() or []
    except Exception as e:
        print('predenv_panels_pub failed:', e)
    try:
        fig_intel_sig_combined()
        outs += _copy_to_sensors([os.path.join(PLOT_DIR, 'paper_intel_sig_combined.svg')])
    except Exception as e:
        print('sig_combined failed:', e)
    try:
        fig_intel_ablation()
        outs += _copy_to_sensors([
            os.path.join(PLOT_DIR, 'paper_intel_ablation_energy.svg'),
            os.path.join(PLOT_DIR, 'paper_intel_ablation_pdr.svg'),
        ])
    except Exception as e:
        print('ablation failed:', e)
    # Add multi-topology significance (PDR & Energy) with BH-FDR footer
    try:
        fig_multi_topo_significance()
        outs += _copy_to_sensors([
            os.path.join(PLOT_DIR, 'paper_multi_topo_sig_pdr.svg'),
            os.path.join(PLOT_DIR, 'paper_multi_topo_sig_energy.svg'),
        ])
    except Exception as e:
        print('multi_topo_sig failed:', e)
    try:
        outs += fig_method_flowchart_pub() or []
    except Exception as e:
        print('flowchart_pub failed:', e)
    print('Publication-grade emergency set generated/copied:', outs)
    return outs

def build_submission_pdf():
    # Merge selected figure PDFs in canonical paper order
    try:
        from PyPDF2 import PdfMerger
    except Exception as e:
        print('PyPDF2 not available, cannot build merged PDF:', e)
        return None
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'results', 'for_submission'), exist_ok=True)
    order = [
        'paper_intel_baselines_panels',
        'paper_intel_predenv_panels',
        'paper_intel_sig_combined',
        'paper_intel_ablation_energy',
        'paper_intel_ablation_pdr',
        'paper_method_flowchart',
        'paper_intel_pdr_gardner_altman',
    ]
    merger = PdfMerger()
    added = []
    for base in order:
        pdf_path = os.path.abspath(os.path.join(PLOT_DIR, base + '.pdf'))
        if os.path.exists(pdf_path):
            try:
                merger.append(pdf_path)
                added.append(pdf_path)
            except Exception as e:
                print('Skip add PDF', pdf_path, '->', e)
        else:
            print('Missing PDF, skip:', pdf_path)
    if not added:
        print('No PDFs to merge. Abort.')
        return None
    out_pdf = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results', 'for_submission', 'submission_figures.pdf'))
    with open(out_pdf, 'wb') as f:
        merger.write(f)
    merger.close()
    # Copy to publication_figures and Sensors_figures for preview
    try:
        pub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results', 'publication_figures'))
        os.makedirs(pub_dir, exist_ok=True)
        shutil.copy2(out_pdf, os.path.join(pub_dir, 'submission_figures.pdf'))
    except Exception as e:
        print('Copy to publication_figures failed:', e)
    try:
        sensors_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results', 'Sensors_figures'))
        shutil.copy2(out_pdf, os.path.join(sensors_dir, 'submission_figures.pdf'))
    except Exception as e:
        print('Copy to Sensors_figures failed:', e)
    print('Built merged submission PDF with pages:', len(added))
    return out_pdf

# Build a simple cover and merge into a manuscript draft PDF

def build_manuscript_with_cover(title=None, authors=None, affiliation=None):
    import os, shutil, datetime
    try:
        from PyPDF2 import PdfMerger
    except Exception as e:
        print('PyPDF2 not available, cannot build manuscript draft:', e)
        return None
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception as e:
        print('matplotlib not available to render cover page:', e)
        return None
    # Defaults
    if title is None:
        title = 'Sensors Manuscript Draft'
    if authors is None:
        authors = 'Author(s)'
    if affiliation is None:
        affiliation = ''
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    out_dir = os.path.join(base_dir, 'results', 'for_submission')
    os.makedirs(out_dir, exist_ok=True)
    cover_pdf = os.path.join(out_dir, 'submission_cover.pdf')
    # Create a simple A4 cover page
    fig = plt.figure(figsize=(8.27, 11.69))  # A4 size in inches
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    ax.text(0.5, 0.78, title, ha='center', va='center', fontsize=24, fontweight='bold')
    if authors:
        ax.text(0.5, 0.68, authors, ha='center', va='center', fontsize=14)
    if affiliation:
        ax.text(0.5, 0.63, affiliation, ha='center', va='center', fontsize=12)
    ax.text(0.5, 0.15, datetime.date.today().isoformat(), ha='center', va='center', fontsize=11)
    ax.text(0.5, 0.10, 'Auto-compiled figures package', ha='center', va='center', fontsize=10)
    fig.savefig(cover_pdf, format='pdf', dpi=300, bbox_inches='tight')
    plt.close(fig)
    # Merge cover + submission_figures
    submission_pdf = os.path.join(out_dir, 'submission_figures.pdf')
    merged_pdf = os.path.join(out_dir, 'manuscript_draft.pdf')
    merger = PdfMerger()
    try:
        merger.append(cover_pdf)
    except Exception as e:
        print('Append cover failed:', e)
    if os.path.exists(submission_pdf):
        try:
            merger.append(submission_pdf)
        except Exception as e:
            print('Append submission failed:', e)
    else:
        print('Warning: submission_figures.pdf not found, only cover will be included.')
    with open(merged_pdf, 'wb') as f:
        merger.write(f)
    merger.close()
    # Copy to publication and sensors preview directories
    try:
        pub_dir = os.path.join(base_dir, 'results', 'publication_figures')
        os.makedirs(pub_dir, exist_ok=True)
        shutil.copy2(merged_pdf, os.path.join(pub_dir, 'manuscript_draft.pdf'))
    except Exception as e:
        print('Copy to publication_figures failed:', e)
    try:
        sensors_dir = os.path.join(base_dir, 'results', 'Sensors_figures')
        os.makedirs(sensors_dir, exist_ok=True)
        shutil.copy2(merged_pdf, os.path.join(sensors_dir, 'manuscript_draft.pdf'))
    except Exception as e:
        print('Copy to Sensors_figures failed:', e)
    print('Built manuscript_draft.pdf')
    return merged_pdf

if __name__ == '__main__':
    # Generate publication-grade emergency set for clean submission-ready visuals
    generate_emergency_pub_set()
    # Optional: include Gardner–Altman plot for stronger effect size presentation
    try:
        fig_intel_pdr_gardner_altman()
        _copy_to_sensors([os.path.join(PLOT_DIR, 'paper_intel_pdr_gardner_altman.svg')])
    except Exception as e:
        print('gardner_altman failed:', e)
    # Build merged submission PDF
    build_submission_pdf()
    # Build draft with a simple MDPI-like cover page for quick sharing
    build_manuscript_with_cover()
