#!/usr/bin/env python3
"""
Multi-Environment Publication Figures for AERIS Paper

Generates high-quality figures from P0/P1 experiment results:
- Fig.1: Multi-env 5-protocol PDR comparison (grouped bar)
- Fig.2: Ablation heatmap (environment x config)
- Fig.3: Gateway negative effect visualization

Data sources:
- env_sensitivity_20260206_013048.json (n=30, 4 envs, 5 protocols)
- ablation_diag_multi_20260206_020002.json (n=30, 4 envs, 6 configs)

Usage:
    python scripts/plot_multienv_figures.py
    python scripts/plot_multienv_figures.py --suffix 20260206_120000
    python scripts/plot_multienv_figures.py --env-file <path> --ablation-file <path>
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Publication-quality settings
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.linewidth': 0.8,
    'axes.grid': False,
    'grid.alpha': 0.3,
})

# Color schemes
PROTOCOL_COLORS = {
    'AERIS': '#2E86AB',      # Blue
    'LEACH': '#E94F37',      # Red
    'PEGASIS': '#F39C12',    # Orange
    'HEED': '#8E44AD',       # Purple
    'TEEN': '#27AE60',       # Green
}

ENV_LABELS = {
    'indoor_office': 'Indoor Office',
    'indoor_factory': 'Indoor Factory',
    'outdoor_urban': 'Outdoor Urban',
    'outdoor_suburban': 'Outdoor Suburban',
}

ABLATION_LABELS = {
    'full': 'Full AERIS',
    'no_gateway': 'No Gateway',
    'no_cas': 'No CAS',
    'no_skeleton': 'No Skeleton',
    'no_safety': 'No Safety',
    'minimal': 'Minimal',
}


def load_json(filepath):
    """Load JSON file with error handling."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def aggregate_results(raw_results, group_keys, metric='pdr_expected'):
    """Aggregate raw results by group keys, compute mean and std."""
    from collections import defaultdict
    groups = defaultdict(list)

    for r in raw_results:
        if r.get('error'):
            continue
        key = tuple(r.get(k) for k in group_keys)
        val = r.get(metric, 0.0)
        if val is not None:
            groups[key].append(val)

    agg = {}
    for key, vals in groups.items():
        agg[key] = {
            'mean': np.mean(vals),
            'std': np.std(vals),
            'n': len(vals),
        }
    return agg


def plot_fig1_multienv_protocol_comparison(data, output_dir, suffix):
    """
    Fig.1: Multi-environment 5-protocol PDR comparison
    Grouped bar chart with error bars
    """
    raw = data['raw_results']
    agg = aggregate_results(raw, ['protocol', 'environment'])

    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED', 'TEEN']
    envs = ['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban']

    fig, ax = plt.subplots(figsize=(10, 5))

    x = np.arange(len(envs))
    width = 0.15
    offsets = np.arange(len(protocols)) - (len(protocols) - 1) / 2

    for i, proto in enumerate(protocols):
        means = []
        stds = []
        for env in envs:
            key = (proto, env)
            if key in agg:
                means.append(agg[key]['mean'])
                stds.append(agg[key]['std'])
            else:
                means.append(0)
                stds.append(0)

        bars = ax.bar(x + offsets[i] * width, means, width,
                      yerr=stds, capsize=2, label=proto,
                      color=PROTOCOL_COLORS[proto],
                      edgecolor='black', linewidth=0.5,
                      error_kw={'linewidth': 0.8})

    ax.set_xlabel('Environment')
    ax.set_ylabel('Packet Delivery Ratio (PDR)')
    ax.set_title('Multi-Environment Protocol Comparison (n=30)')
    ax.set_xticks(x)
    ax.set_xticklabels([ENV_LABELS[e] for e in envs], rotation=15, ha='right')
    ax.set_ylim(0, 1.05)
    ax.legend(loc='upper right', ncol=5, framealpha=0.9)
    ax.axhline(y=0.9, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

    # Add grid for readability
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    # Note: error bars show std for n=30
    fig.text(0.5, -0.02, 'Error bars = std (n=30)', ha='center', fontsize=8)
    plt.tight_layout()

    # Save in multiple formats
    for fmt in ['pdf', 'png', 'svg']:
        outpath = output_dir / f'fig1_multienv_protocol_comparison_{suffix}.{fmt}'
        fig.savefig(outpath)
        print(f"  Saved: {outpath}")

    plt.close(fig)
    return True


def plot_fig2_ablation_heatmap(data, output_dir, suffix):
    """
    Fig.2: Ablation heatmap (environment x config)
    Shows PDR for each combination
    """
    raw = data['raw_results']
    agg = aggregate_results(raw, ['ablation_config', 'environment'])

    configs = ['full', 'no_gateway', 'no_cas', 'no_skeleton', 'no_safety', 'minimal']
    envs = ['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban']

    # Build matrix
    matrix = np.zeros((len(configs), len(envs)))
    for i, cfg in enumerate(configs):
        for j, env in enumerate(envs):
            key = (cfg, env)
            if key in agg:
                matrix[i, j] = agg[key]['mean']

    fig, ax = plt.subplots(figsize=(8, 5))

    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)

    # Add colorbar
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('PDR', rotation=270, labelpad=15)

    # Labels
    ax.set_xticks(np.arange(len(envs)))
    ax.set_yticks(np.arange(len(configs)))
    ax.set_xticklabels([ENV_LABELS[e].replace(' ', '\n') for e in envs])
    ax.set_yticklabels([ABLATION_LABELS[c] for c in configs])

    # Add text annotations
    for i in range(len(configs)):
        for j in range(len(envs)):
            val = matrix[i, j]
            color = 'white' if val < 0.5 else 'black'
            ax.text(j, i, f'{val:.3f}', ha='center', va='center',
                    color=color, fontsize=8, fontweight='bold')

    ax.set_title('Ablation Study: PDR by Environment and Configuration (n=30)')

    # Note: values are mean PDR (pdr_expected)
    fig.text(0.5, -0.02, 'Cell values = mean PDR (pdr_expected)', ha='center', fontsize=8)
    plt.tight_layout()

    for fmt in ['pdf', 'png', 'svg']:
        outpath = output_dir / f'fig2_ablation_heatmap_{suffix}.{fmt}'
        fig.savefig(outpath)
        print(f"  Saved: {outpath}")

    plt.close(fig)
    return True


def plot_fig3_gateway_effect(data, output_dir, suffix):
    """
    Fig.3: Gateway negative effect visualization
    Shows PDR difference (no_gateway - full) per environment
    """
    raw = data['raw_results']
    agg = aggregate_results(raw, ['ablation_config', 'environment'])

    envs = ['indoor_office', 'indoor_factory', 'outdoor_urban', 'outdoor_suburban']

    # Calculate differences
    diffs = []
    full_pdrs = []
    no_gw_pdrs = []

    for env in envs:
        full_key = ('full', env)
        no_gw_key = ('no_gateway', env)

        full_pdr = agg.get(full_key, {}).get('mean', 0)
        no_gw_pdr = agg.get(no_gw_key, {}).get('mean', 0)

        full_pdrs.append(full_pdr)
        no_gw_pdrs.append(no_gw_pdr)
        diffs.append(no_gw_pdr - full_pdr)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    # Left: Grouped bar comparison
    ax1 = axes[0]
    x = np.arange(len(envs))
    width = 0.35

    bars1 = ax1.bar(x - width/2, full_pdrs, width, label='Full AERIS',
                    color='#2E86AB', edgecolor='black', linewidth=0.5)
    bars2 = ax1.bar(x + width/2, no_gw_pdrs, width, label='No Gateway',
                    color='#E94F37', edgecolor='black', linewidth=0.5)

    ax1.set_xlabel('Environment')
    ax1.set_ylabel('PDR')
    ax1.set_title('(a) PDR Comparison: Full vs No Gateway')
    ax1.set_xticks(x)
    ax1.set_xticklabels([ENV_LABELS[e].replace(' ', '\n') for e in envs])
    ax1.set_ylim(0, 1.05)
    ax1.legend(loc='upper right')
    ax1.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax1.set_axisbelow(True)

    # Right: Difference bar chart
    ax2 = axes[1]
    colors = ['#27AE60' if d > 0 else '#E94F37' for d in diffs]
    bars3 = ax2.bar(x, [d * 100 for d in diffs], color=colors,
                    edgecolor='black', linewidth=0.5)

    ax2.set_xlabel('Environment')
    ax2.set_ylabel('PDR Improvement (%)')
    ax2.set_title('(b) PDR Gain When Gateway Disabled')
    ax2.set_xticks(x)
    ax2.set_xticklabels([ENV_LABELS[e].replace(' ', '\n') for e in envs])
    ax2.axhline(y=0, color='black', linewidth=0.8)
    ax2.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax2.set_axisbelow(True)

    # Add value labels
    for bar, val in zip(bars3, diffs):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, height + 0.5,
                 f'+{val*100:.1f}%', ha='center', va='bottom',
                 fontsize=9, fontweight='bold')

    # Note: differences shown as (no_gateway - full)
    fig.text(0.5, -0.02, 'PDR gain = (no_gateway - full)', ha='center', fontsize=8)
    plt.tight_layout()

    for fmt in ['pdf', 'png', 'svg']:
        outpath = output_dir / f'fig3_gateway_effect_{suffix}.{fmt}'
        fig.savefig(outpath)
        print(f"  Saved: {outpath}")

    plt.close(fig)
    return True


def main():
    parser = argparse.ArgumentParser(description='Generate multi-environment figures')
    parser.add_argument('--env-file', type=str, default='',
                        help='Path to env_sensitivity JSON file')
    parser.add_argument('--ablation-file', type=str, default='',
                        help='Path to ablation multi JSON file')
    parser.add_argument('--out-dir', type=str, default='',
                        help='Output directory for figures')
    parser.add_argument('--suffix', type=str, default='',
                        help='Suffix for output filenames (default: timestamp)')
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    output_dir = Path(args.out_dir) if args.out_dir else (project_root / 'for_submission' / 'figures')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Data files
    env_file = Path(args.env_file) if args.env_file else (project_root / 'results' / 'mega_experiments' / 'env_sensitivity_20260206_013048.json')
    ablation_file = Path(args.ablation_file) if args.ablation_file else (project_root / 'results' / 'mega_experiments' / 'ablation_diag_multi_20260206_020002.json')
    suffix = args.suffix.strip() if args.suffix else datetime.now().strftime('%Y%m%d_%H%M%S')

    print("=" * 60)
    print("AERIS Multi-Environment Figure Generation")
    print("=" * 60)

    # Load data
    print("\nLoading data...")
    env_data = load_json(env_file)
    ablation_data = load_json(ablation_file)
    print(f"  env_sensitivity: {len(env_data['raw_results'])} records")
    print(f"  ablation_multi: {len(ablation_data['raw_results'])} records")
    print(f"  output_suffix: {suffix}")

    # Generate figures
    print("\nGenerating Fig.1: Multi-env protocol comparison...")
    plot_fig1_multienv_protocol_comparison(env_data, output_dir, suffix)

    print("\nGenerating Fig.2: Ablation heatmap...")
    plot_fig2_ablation_heatmap(ablation_data, output_dir, suffix)

    print("\nGenerating Fig.3: Gateway effect...")
    plot_fig3_gateway_effect(ablation_data, output_dir, suffix)

    print("\n" + "=" * 60)
    print("All figures generated successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
