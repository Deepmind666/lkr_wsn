#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compose a publication-ready vector comparison figure by directly drawing
both analyses on a single canvas (no raster embedding).

Outputs:
 - results/publication_figures/LEACH_comparison_vector.svg (primary)
 - results/publication_figures/LEACH_comparison_vector.png
 - results/publication_figures/LEACH_comparison_vector.pdf

Requires: matplotlib, numpy
"""

import os
import sys

try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import Rectangle
except Exception as e:
    print(f"[ERROR] matplotlib/numpy not available: {e}")
    sys.exit(1)


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ensure_import_path():
    root = _project_root()
    if root not in sys.path:
        sys.path.insert(0, root)


def _run_realistic():
    _ensure_import_path()
    # Import from src package
    try:
        from src.test_realistic_leach import run_realistic_leach_experiment, EnvironmentType
    except Exception as e:
        print(f"[ERROR] Unable to import realistic test: {e}")
        raise
    results = run_realistic_leach_experiment(num_rounds=200, environment=EnvironmentType.OUTDOOR_OPEN)
    return results


def _run_corrected():
    _ensure_import_path()
    try:
        from src.test_corrected_leach import run_corrected_leach_experiment
    except Exception as e:
        print(f"[ERROR] Unable to import corrected test: {e}")
        raise
    results = run_corrected_leach_experiment(num_rounds=200)
    return results


def _draw_realistic(gs, fig, results):
    rr = results['round_results']
    rounds = [r['round'] for r in rr]
    alive_nodes = [r['alive_nodes'] for r in rr]
    cluster_heads = [r['cluster_heads'] for r in rr]
    packets_sent = [r['packets_sent'] for r in rr]
    packets_received = [r['packets_received'] for r in rr]
    avg_pdr = [r['avg_pdr'] for r in rr]
    avg_rssi = [r['avg_rssi'] for r in rr]
    avg_sinr = [r['avg_sinr'] for r in rr]
    cumulative_sent = np.cumsum(packets_sent)
    cumulative_received = np.cumsum(packets_received)

    ax00 = fig.add_subplot(gs[0, 0])
    ax01 = fig.add_subplot(gs[0, 1])
    ax02 = fig.add_subplot(gs[0, 2])
    ax10 = fig.add_subplot(gs[1, 0])
    ax11 = fig.add_subplot(gs[1, 1])
    ax12 = fig.add_subplot(gs[1, 2])

    ax00.plot(rounds, alive_nodes, 'b-', linewidth=2, label='Alive nodes')
    ax00.plot(rounds, cluster_heads, 'r--', linewidth=2, label='Cluster heads')
    ax00.set_xlabel('Rounds')
    ax00.set_ylabel('Node count')
    ax00.set_title('[Realistic] Network clustering evolution')
    ax00.legend(); ax00.grid(True, alpha=0.3)

    ax01.plot(rounds, packets_sent, 'g-', linewidth=2, label='Packets sent')
    ax01.plot(rounds, packets_received, 'orange', linewidth=2, label='Packets received')
    ax01.set_xlabel('Rounds')
    ax01.set_ylabel('Packets')
    ax01.set_title('[Realistic] Packet transmission statistics')
    ax01.legend(); ax01.grid(True, alpha=0.3)

    ax02.plot(rounds, avg_pdr, 'purple', linewidth=2)
    ax02.set_xlabel('Rounds')
    ax02.set_ylabel('PDR')
    ax02.set_title('[Realistic] Packet delivery ratio (PDR)')
    ax02.set_ylim(0, 1)
    ax02.grid(True, alpha=0.3)

    ax10.plot(rounds, avg_rssi, 'brown', linewidth=2)
    ax10.set_xlabel('Rounds')
    ax10.set_ylabel('RSSI (dBm)')
    ax10.set_title('[Realistic] Average received signal strength')
    ax10.grid(True, alpha=0.3)

    ax11.plot(rounds, avg_sinr, 'teal', linewidth=2)
    ax11.set_xlabel('Rounds')
    ax11.set_ylabel('SINR (dB)')
    ax11.set_title('[Realistic] SINR distribution')
    ax11.grid(True, alpha=0.3)

    ax12.plot(rounds, cumulative_sent, 'g-', linewidth=2, label='Cumulative sent')
    ax12.plot(rounds, cumulative_received, 'orange', linewidth=2, label='Cumulative received')
    ax12.set_xlabel('Rounds')
    ax12.set_ylabel('Cumulative packets')
    ax12.set_title('[Realistic] Cumulative transmission')
    ax12.legend(); ax12.grid(True, alpha=0.3)


def _draw_corrected(gs, fig, results):
    rr = results['round_results']
    rounds = [r['round'] for r in rr]
    alive_nodes = [r['alive_nodes_end'] for r in rr]
    cluster_heads = [r['cluster_heads'] for r in rr]
    packets_sent = [r['packets_sent'] for r in rr]
    hello_energy = [r['hello_energy'] for r in rr]
    data_energy = [r['data_energy'] for r in rr]
    total_energy = [r['total_energy'] for r in rr]
    cumulative_packets = np.cumsum(packets_sent)
    protocol_ratio = [h / (h + d) if (h + d) > 0 else 0 for h, d in zip(hello_energy, data_energy)]
    packets_per_round = [p for p in packets_sent]

    ax00 = fig.add_subplot(gs[0, 3])
    ax01 = fig.add_subplot(gs[0, 4])
    ax02 = fig.add_subplot(gs[0, 5])
    ax10 = fig.add_subplot(gs[1, 3])
    ax11 = fig.add_subplot(gs[1, 4])
    ax12 = fig.add_subplot(gs[1, 5])

    ax00.plot(rounds, alive_nodes, 'b-', linewidth=2, label='Alive Nodes')
    ax00.plot(rounds, cluster_heads, 'r--', linewidth=2, label='Cluster Heads')
    ax00.set_xlabel('Round'); ax00.set_ylabel('Number of Nodes')
    ax00.set_title('[Corrected] Network Topology Evolution')
    ax00.legend(); ax00.grid(True, alpha=0.3)

    ax01.plot(rounds, packets_sent, 'g-', linewidth=2)
    ax01.set_xlabel('Round'); ax01.set_ylabel('Packets Sent')
    ax01.set_title('[Corrected] Data Packet Transmission')
    ax01.grid(True, alpha=0.3)

    ax02.plot(rounds, hello_energy, 'orange', linewidth=2, label='Hello Energy')
    ax02.plot(rounds, data_energy, 'purple', linewidth=2, label='Data Energy')
    ax02.plot(rounds, total_energy, 'red', linewidth=2, label='Total Energy')
    ax02.set_xlabel('Round'); ax02.set_ylabel('Energy (J)')
    ax02.set_title('[Corrected] Energy Consumption Analysis')
    ax02.legend(); ax02.grid(True, alpha=0.3)

    ax10.plot(rounds, cumulative_packets, 'g-', linewidth=2)
    ax10.set_xlabel('Round'); ax10.set_ylabel('Cumulative Packets')
    ax10.set_title('[Corrected] Cumulative Data Transmission')
    ax10.grid(True, alpha=0.3)

    ax11.plot(rounds, protocol_ratio, 'brown', linewidth=2)
    ax11.set_xlabel('Round'); ax11.set_ylabel('Protocol Overhead Ratio')
    ax11.set_title('[Corrected] Protocol Overhead vs Data')
    ax11.set_ylim(0, 1); ax11.grid(True, alpha=0.3)

    ax12.plot(rounds, packets_per_round, 'teal', linewidth=2)
    ax12.axhline(y=1.005, color='red', linestyle='--', linewidth=2, label='Auth LEACH (1.005)')
    ax12.set_xlabel('Round'); ax12.set_ylabel('Packets per Round')
    ax12.set_title('[Corrected] Packets per Round vs Baseline')
    ax12.legend(); ax12.grid(True, alpha=0.3)


def _read_intel_mote_positions() -> list:
    """Read Intel Lab mote positions from data/Intel_Lab_Data/mote_locs.txt.
    Returns list of (x, y) floats. If file missing or parse fails, returns []."""
    try:
        root = _project_root()
        loc_path = os.path.join(root, 'data', 'Intel_Lab_Data', 'mote_locs.txt')
        if not os.path.exists(loc_path):
            return []
        pts = []
        with open(loc_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3:
                    try:
                        # format: id x y
                        x = float(parts[1]); y = float(parts[2])
                        pts.append((x, y))
                    except Exception:
                        continue
        return pts
    except Exception:
        return []


def _draw_intel_mapping_inset(fig,
                              area_width: float = 100.0,
                              area_height: float = 100.0,
                              bs_x: float = 50.0,
                              bs_y: float = 175.0):
    """Draw a small inset showing Intel Lab positions mapped to the simulation area.
    Placed at the top-right corner of the canvas.
    """
    pts = _read_intel_mote_positions()
    # Create inset axes in figure coordinates (left, bottom, width, height)
    # position chosen to sit in the top-right margin without occluding panels
    inset_ax = fig.add_axes([0.805, 0.64, 0.18, 0.28])
    inset_ax.set_title('Intel positions → sim area', fontsize=10)
    inset_ax.set_xlim(0, area_width)
    inset_ax.set_ylim(0, area_height)
    inset_ax.set_aspect('equal')
    inset_ax.axis('off')

    # Draw simulation area boundary
    inset_ax.add_patch(Rectangle((0, 0), area_width, area_height,
                                 fill=False, edgecolor='#666666', linewidth=1.0))

    if pts:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        # Avoid division by zero
        span_x = max(1e-6, (max_x - min_x))
        span_y = max(1e-6, (max_y - min_y))
        # Scale Intel coordinates to the simulation area
        scaled_x = [((x - min_x) / span_x) * area_width for x in xs]
        scaled_y = [((y - min_y) / span_y) * area_height for y in ys]
        inset_ax.scatter(scaled_x, scaled_y,
                         s=18, c='#4E79A7', alpha=0.9,
                         edgecolors='white', linewidths=0.35)
    else:
        # Fallback: synthetic positions
        rng = np.random.default_rng(42)
        sx = rng.uniform(0, area_width, size=50)
        sy = rng.uniform(0, area_height, size=50)
        inset_ax.scatter(sx, sy, s=18, c='#4E79A7', alpha=0.9,
                         edgecolors='white', linewidths=0.35)

    # Draw base station indicator at top-center, with annotation
    bs_plot_y = area_height  # show at boundary with upward note
    inset_ax.plot([bs_x], [bs_plot_y], marker='*', markersize=12, color='#FF6B6B')
    inset_ax.text(bs_x, bs_plot_y, ' BS (y=175, outside area)',
                  fontsize=9, color='#FF6B6B', va='bottom', ha='center')


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_dir = os.path.join(project_root, 'results')
    pub_dir = os.path.join(results_dir, 'publication_figures')
    os.makedirs(pub_dir, exist_ok=True)

    # Run both experiments to get fresh results for plotting
    print('[RUN] Simulating realistic environment LEACH ...')
    realistic = _run_realistic()

    print('[RUN] Simulating corrected LEACH ...')
    corrected = _run_corrected()

    # Compose figure with GridSpec (2 rows x 6 cols)
    fig = plt.figure(figsize=(24, 10))
    gs = GridSpec(2, 6, figure=fig)
    fig.suptitle('LEACH Protocol Comparison (Vector, Single Canvas)', fontsize=16, fontweight='bold')

    _draw_realistic(gs, fig, realistic)
    _draw_corrected(gs, fig, corrected)

    # Inset: Intel Lab positions mapping to simulation area (top-right)
    try:
        _draw_intel_mapping_inset(fig,
                                  area_width=100.0,
                                  area_height=100.0,
                                  bs_x=50.0,
                                  bs_y=175.0)
    except Exception as _e:
        print(f"[WARN] Inset drawing failed: {_e}")

    plt.tight_layout()

    out_svg = os.path.join(pub_dir, 'LEACH_comparison_vector.svg')
    out_png = os.path.join(pub_dir, 'LEACH_comparison_vector.png')
    out_pdf = os.path.join(pub_dir, 'LEACH_comparison_vector.pdf')
    plt.savefig(out_svg, format='svg', bbox_inches='tight')
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.savefig(out_pdf, dpi=300, bbox_inches='tight')
    print(f'[SAVED] Vector comparison (SVG): {out_svg}')
    print(f'[SAVED] Vector comparison (PNG): {out_png}')
    print(f'[SAVED] Vector comparison (PDF): {out_pdf}')


if __name__ == '__main__':
    main()