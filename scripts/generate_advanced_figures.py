#!/usr/bin/env python3
"""
Generate advanced figures for AERIS paper:
1. Radar chart - Multi-dimensional performance comparison
2. Pareto frontier plot - Static vs Dynamic performance trade-off

Based on expert review recommendations for enhanced visualization.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import json
import os
from pathlib import Path

# Set publication-quality style
plt.rcParams.update({
    'font.family': 'Arial',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'legend.fontsize': 9,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
})

# ============================================================
# Data helpers (no synthetic data)
# ============================================================
DATA_DIR = Path(__file__).parent.parent / 'results'
DROPOUT_PATH = DATA_DIR / 'dynamic_dropout_compare_reps.json'

DISPLAY_PROTOCOLS = {
    'AERIS-E': 'AERIS_energy',
    'AERIS-R': 'AERIS_robust',
    'LEACH': 'LEACH',
    'HEED': 'HEED',
    'PEGASIS': 'PEGASIS',
    'TEEN': 'TEEN',
}


def _drop_key_value(key: str) -> float:
    if key.startswith('drop'):
        try:
            return float(key.replace('drop', ''))
        except ValueError:
            return 0.0
    return 0.0


def _sorted_drop_keys(data: dict) -> list:
    keys = set()
    for rep in data.values():
        keys.update(rep.keys())
    return sorted(keys, key=_drop_key_value)


def load_dropout_summary():
    """Summarize dropout experiment results for plotting (real data only)."""
    with open(DROPOUT_PATH, 'r') as f:
        data = json.load(f)

    drop_keys = _sorted_drop_keys(data)
    if not drop_keys:
        raise ValueError("No dropout phases found in results.")
    drop0_key = drop_keys[0]
    drop_max_key = drop_keys[-1]
    nonzero_keys = [k for k in drop_keys if k != drop0_key]
    summary = {}

    for label, proto in DISPLAY_PROTOCOLS.items():
        pdr_by_drop = {k: [] for k in drop_keys}
        energy_vals = []
        eff_vals = []
        pdr_drop0_vals = []
        pdr_drop_max_vals = []

        for rep in data.values():
            drop0_block = rep.get(drop0_key, {})
            dropmax_block = rep.get(drop_max_key, {})
            if proto in drop0_block and proto in dropmax_block:
                pdr_drop0_vals.append(
                    drop0_block[proto].get('packet_delivery_ratio_end2end')
                )
                pdr_drop_max_vals.append(
                    dropmax_block[proto].get('packet_delivery_ratio_end2end')
                )
            for drop_key in drop_keys:
                block = rep.get(drop_key, {})
                if proto not in block:
                    continue
                metrics = block[proto]
                pdr_by_drop[drop_key].append(metrics.get('packet_delivery_ratio_end2end'))
                energy_vals.append(metrics.get('total_energy_consumed'))
                eff_vals.append(metrics.get('energy_efficiency'))

        dynamic_vals = []
        for k in nonzero_keys:
            dynamic_vals.extend(pdr_by_drop.get(k, []))
        if not dynamic_vals:
            dynamic_vals = pdr_by_drop.get(drop0_key, [])

        summary[label] = {
            'drop_keys': drop_keys,
            'drop0_key': drop0_key,
            'drop_max_key': drop_max_key,
            'pdr_drop0': float(np.mean(pdr_by_drop[drop0_key])),
            'pdr_drop_max': float(np.mean(pdr_by_drop[drop_max_key])),
            'pdr_dynamic': float(np.mean(dynamic_vals)),
            'energy_mean': float(np.mean(energy_vals)),
            'eff_mean': float(np.mean(eff_vals)),
            'pdr_drop0_vals': pdr_drop0_vals,
            'pdr_drop_max_vals': pdr_drop_max_vals,
        }

    return summary


def normalize(values):
    vmin = min(values)
    vmax = max(values)
    if vmax == vmin:
        return [0.5 for _ in values]
    return [(v - vmin) / (vmax - vmin) for v in values]


def generate_radar_chart(output_dir):
    """
    Generate radar chart comparing protocols using real dropout data.
    Dimensions: Static PDR (drop0), Dynamic PDR (avg drop>0),
                Stress PDR (max drop), Energy Efficiency, Energy (inverse).
    """
    summary = load_dropout_summary()
    protocols = list(summary.keys())

    categories = [
        'Static PDR\n(drop0)',
        'Dynamic PDR\n(avg drop>0)',
        'Stress PDR\n(drop_max)',
        'Energy\nEfficiency',
        'Energy\n(Inv)'
    ]
    N = len(categories)

    eff_vals = [summary[p]['eff_mean'] for p in protocols]
    energy_vals = [summary[p]['energy_mean'] for p in protocols]
    eff_norm = normalize(eff_vals)
    energy_norm = normalize(energy_vals)
    energy_inv = [1.0 - n for n in energy_norm]

    protocols_normalized = {}
    for idx, name in enumerate(protocols):
        protocols_normalized[name] = [
            summary[name]['pdr_drop0'],
            summary[name]['pdr_dynamic'],
            summary[name]['pdr_drop_max'],
            eff_norm[idx],
            energy_inv[idx],
        ]

    # Compute angle for each axis
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Complete the loop

    # Initialize figure
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    # Colors for each protocol
    colors = {
        'AERIS-E': '#2E86AB',
        'AERIS-R': '#1B998B',
        'LEACH': '#A23B72',
        'PEGASIS': '#F18F01',
        'HEED': '#C73E1D',
        'TEEN': '#7B6D8D',
    }

    # Plot each protocol
    for name, values in protocols_normalized.items():
        values += values[:1]  # Complete the loop
        ax.plot(angles, values, 'o-', linewidth=2, label=name, color=colors[name])
        ax.fill(angles, values, alpha=0.15, color=colors[name])

    # Set category labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)

    # Set y-axis range
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'])

    # Add legend
    ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1.1))

    # Title
    ax.set_title('Multi-Dimensional Protocol Performance Comparison\n(Dropout stress test, higher = better)',
                 fontsize=13, fontweight='bold', pad=20)

    # Save figure
    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'radar_performance_comparison.{fmt}')
        plt.savefig(filepath, format=fmt, bbox_inches='tight', dpi=300)
        print(f"Saved: {filepath}")

    plt.close()


def generate_pareto_frontier(output_dir):
    """
    Generate Pareto frontier plot showing static vs stress PDR.
    Uses dropout experiments (drop0 vs max drop).
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    summary = load_dropout_summary()
    protocols = {
        name: (summary[name]['pdr_drop0'], summary[name]['pdr_drop_max'])
        for name in summary.keys()
    }

    colors = {
        'AERIS-E': '#2E86AB',
        'AERIS-R': '#1B998B',
        'LEACH': '#A23B72',
        'PEGASIS': '#F18F01',
        'HEED': '#C73E1D',
        'TEEN': '#7B6D8D',
    }

    markers = {
        'AERIS-E': 's',
        'AERIS-R': 'P',
        'LEACH': 'o',
        'PEGASIS': '^',
        'HEED': 'D',
        'TEEN': 'v',
    }

    # Plot each protocol
    for name, (static, dynamic) in protocols.items():
        ax.scatter(
            summary[name]['pdr_drop0_vals'],
            summary[name]['pdr_drop_max_vals'],
            s=35,
            c=colors[name],
            alpha=0.25,
            edgecolors='none',
            zorder=2,
        )
        ax.scatter(static, dynamic, s=150, c=colors[name], marker=markers[name],
                  label=name, zorder=5, edgecolors='black', linewidths=1)
        # Add annotation
        offset = (10, 10) if name != 'PEGASIS' else (10, -20)
        ax.annotate(name, (static, dynamic), xytext=offset,
                   textcoords='offset points', fontsize=10, fontweight='bold')

    # Compute Pareto frontier (non-dominated points)
    all_points = list(protocols.values())
    pareto_points = []
    for p in all_points:
        dominated = False
        for q in all_points:
            if (q[0] >= p[0] and q[1] > p[1]) or (q[0] > p[0] and q[1] >= p[1]):
                dominated = True
                break
        if not dominated:
            pareto_points.append(p)

    pareto_points = sorted(pareto_points, key=lambda x: x[0])
    if len(pareto_points) > 1:
        pareto_x, pareto_y = zip(*pareto_points)
        ax.plot(pareto_x, pareto_y, '-', color='#2E86AB', linewidth=2.2,
                label='Pareto Frontier', zorder=3)

    # Labels and title
    ax.set_xlabel('Static PDR (drop0)', fontsize=11)
    ax.set_ylabel('Stress PDR (max drop)', fontsize=11)
    ax.set_title('Static vs Stress PDR Trade-off (Dropout Scenario, replicate scatter)',
                fontsize=12, fontweight='bold')

    # Set axis limits
    ax.set_xlim(0.75, 1.02)
    ax.set_ylim(0.75, 1.02)

    # Grid
    ax.grid(True, alpha=0.3)

    # Legend
    ax.legend(loc='lower left', fontsize=9)

    # Keep annotation minimal to avoid over-claiming

    # Save figure
    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'pareto_frontier_tradeoff.{fmt}')
        plt.savefig(filepath, format=fmt, bbox_inches='tight', dpi=300)
        print(f"Saved: {filepath}")

    plt.close()


def generate_combined_figure(output_dir):
    """
    Generate combined figure with both radar and Pareto plots side by side.
    """
    fig = plt.figure(figsize=(14, 6))

    # ---- Left: Radar Chart ----
    ax1 = fig.add_subplot(121, polar=True)

    summary = load_dropout_summary()
    protocols = list(summary.keys())

    categories = [
        'Static PDR\n(drop0)',
        'Dynamic PDR\n(avg drop>0)',
        'Stress PDR\n(drop_max)',
        'Energy\nEfficiency',
        'Energy\n(Inv)'
    ]
    N = len(categories)

    eff_vals = [summary[p]['eff_mean'] for p in protocols]
    energy_vals = [summary[p]['energy_mean'] for p in protocols]
    eff_norm = normalize(eff_vals)
    energy_norm = normalize(energy_vals)
    energy_inv = [1.0 - n for n in energy_norm]

    protocols_normalized = {}
    for idx, name in enumerate(protocols):
        protocols_normalized[name] = [
            summary[name]['pdr_drop0'],
            summary[name]['pdr_dynamic'],
            summary[name]['pdr_drop_max'],
            eff_norm[idx],
            energy_inv[idx],
        ]

    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    colors = {
        'AERIS-E': '#2E86AB',
        'AERIS-R': '#1B998B',
        'LEACH': '#A23B72',
        'PEGASIS': '#F18F01',
        'HEED': '#C73E1D',
        'TEEN': '#7B6D8D',
    }

    for name, values in protocols_normalized.items():
        values += values[:1]
        ax1.plot(angles, values, 'o-', linewidth=2, label=name, color=colors[name])
        ax1.fill(angles, values, alpha=0.15, color=colors[name])

    ax1.set_xticks(angles[:-1])
    ax1.set_xticklabels(categories, fontsize=8)
    ax1.set_ylim(0, 1.1)
    ax1.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax1.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0), fontsize=8)
    ax1.set_title('(a) Multi-Dimensional Performance', fontsize=11, fontweight='bold', pad=15)

    # ---- Right: Pareto Frontier ----
    ax2 = fig.add_subplot(122)

    protocols = {
        name: (summary[name]['pdr_drop0'], summary[name]['pdr_drop_max'])
        for name in summary.keys()
    }

    markers = {
        'AERIS-E': 's',
        'AERIS-R': 'P',
        'LEACH': 'o',
        'PEGASIS': '^',
        'HEED': 'D',
        'TEEN': 'v'
    }

    for name, (static, dynamic) in protocols.items():
        ax2.scatter(
            summary[name]['pdr_drop0_vals'],
            summary[name]['pdr_drop_max_vals'],
            s=30,
            c=colors[name],
            alpha=0.25,
            edgecolors='none',
            zorder=2,
        )
        ax2.scatter(static, dynamic, s=120, c=colors[name], marker=markers[name],
                   label=name, zorder=5, edgecolors='black', linewidths=1)
        offset = (8, 8) if name != 'PEGASIS' else (8, -15)
        ax2.annotate(name, (static, dynamic), xytext=offset,
                    textcoords='offset points', fontsize=9, fontweight='bold')

    # Pareto frontier
    all_points = list(protocols.values())
    pareto_points = []
    for p in all_points:
        dominated = False
        for q in all_points:
            if (q[0] >= p[0] and q[1] > p[1]) or (q[0] > p[0] and q[1] >= p[1]):
                dominated = True
                break
        if not dominated:
            pareto_points.append(p)
    pareto_points = sorted(pareto_points, key=lambda x: x[0])
    if len(pareto_points) > 1:
        px, py = zip(*pareto_points)
        ax2.plot(px, py, '-', color='#2E86AB', linewidth=2.2, label='Pareto Frontier')

    ax2.set_xlabel('Static PDR (drop0)', fontsize=10)
    ax2.set_ylabel('Stress PDR (max drop)', fontsize=10)
    ax2.set_xlim(0.75, 1.02)
    ax2.set_ylim(0.75, 1.02)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='lower left', fontsize=8)
    ax2.set_title('(b) Pareto Frontier (replicate scatter)', fontsize=11, fontweight='bold')

    plt.tight_layout()

    # Save combined figure
    for fmt in ['pdf', 'svg', 'png']:
        filepath = os.path.join(output_dir, f'fig_advanced_analysis.{fmt}')
        plt.savefig(filepath, format=fmt, bbox_inches='tight', dpi=300)
        print(f"Saved: {filepath}")

    plt.close()


def main():
    """Generate all advanced figures."""
    # Output directories
    output_dirs = [
        'results/publication_figures',
        'for_submission/figures'
    ]

    for output_dir in output_dirs:
        os.makedirs(output_dir, exist_ok=True)

        print(f"\nGenerating figures to: {output_dir}")

        # Generate individual figures
        generate_radar_chart(output_dir)
        generate_pareto_frontier(output_dir)

        # Generate combined figure
        generate_combined_figure(output_dir)

    print("\n=== Advanced Figure Generation Complete ===")
    print("Generated figures:")
    print("  - radar_performance_comparison.{pdf,svg,png}")
    print("  - pareto_frontier_tradeoff.{pdf,svg,png}")
    print("  - fig_advanced_analysis.{pdf,svg,png}")


if __name__ == '__main__':
    main()
