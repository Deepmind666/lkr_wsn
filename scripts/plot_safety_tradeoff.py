#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

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
    data_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'safety_tradeoff_grid_50x200.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract data
    r_probs = [d['r_prob'] for d in data]
    deltas = [d['delta_dbm'] for d in data]
    energies = [d['energy_mean'] for d in data]
    energy_cis = [d['energy_ci95'] for d in data]
    pdr_means = [d['pdr_end2end_mean'] for d in data]
    pdr_cis = [d['pdr_end2end_ci95'] for d in data]
    p05s = [d['pdr_end2end_p05_mean'] for d in data]
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(10, 7.2))
    
    # Plot 1: Energy vs r_prob (grouped by delta)
    delta1_mask = [d == 1.0 for d in deltas]
    delta2_mask = [d == 2.0 for d in deltas]
    
    r1 = [r for r, mask in zip(r_probs, delta1_mask) if mask]
    e1 = [e for e, mask in zip(energies, delta1_mask) if mask]
    ec1 = [ec for ec, mask in zip(energy_cis, delta1_mask) if mask]
    
    r2 = [r for r, mask in zip(r_probs, delta2_mask) if mask]
    e2 = [e for e, mask in zip(energies, delta2_mask) if mask]
    ec2 = [ec for ec, mask in zip(energy_cis, delta2_mask) if mask]
    
    ax1.errorbar(r1, e1, yerr=ec1, marker='o', label='δ=1dBm', capsize=5)
    ax1.errorbar(r2, e2, yerr=ec2, marker='s', label='δ=2dBm', capsize=5)
    ax1.set_xlabel('Redundancy Probability (r)')
    ax1.set_ylabel('Energy (J)')
    ax1.set_title('Energy vs Redundancy Probability')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: End-to-End PDR mean vs r_prob
    p1 = [p for p, mask in zip(pdr_means, delta1_mask) if mask]
    pc1 = [pc for pc, mask in zip(pdr_cis, delta1_mask) if mask]
    
    p2 = [p for p, mask in zip(pdr_means, delta2_mask) if mask]
    pc2 = [pc for pc, mask in zip(pdr_cis, delta2_mask) if mask]
    
    ax2.errorbar(r1, p1, yerr=pc1, marker='o', label='δ=1dBm', capsize=5)
    ax2.errorbar(r2, p2, yerr=pc2, marker='s', label='δ=2dBm', capsize=5)
    ax2.set_xlabel('Redundancy Probability (r)')
    ax2.set_ylabel('End-to-End PDR (mean)')
    ax2.set_title('End-to-End PDR Mean vs Redundancy Probability')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: P05 vs r_prob
    p05_1 = [p for p, mask in zip(p05s, delta1_mask) if mask]
    p05_2 = [p for p, mask in zip(p05s, delta2_mask) if mask]
    
    ax3.plot(r1, p05_1, marker='o', label='δ=1dBm', linewidth=2)
    ax3.plot(r2, p05_2, marker='s', label='δ=2dBm', linewidth=2)
    ax3.set_xlabel('Redundancy Probability (r)')
    ax3.set_ylabel('End-to-End PDR (5% quantile)')
    ax3.set_title('End-to-End PDR P05 vs Redundancy Probability')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Energy-PDR tradeoff scatter
    colors = ['#D55E00' if p == 0.0 else '#E69F00' if p < 1.0 else '#009E73' for p in p05s]
    sizes = [50 + 100*r for r in r_probs]
    
    scatter = ax4.scatter(energies, pdr_means, c=colors, s=sizes, alpha=0.7)
    ax4.set_xlabel('Energy (J)')
    ax4.set_ylabel('End-to-End PDR (mean)')
    ax4.set_title('Energy–PDR Tradeoff\n(Color: P05, Size: r_prob)')
    ax4.grid(True, alpha=0.3)
    
    # Add text annotations
    for i, (e, p, r, d, p05) in enumerate(zip(energies, pdr_means, r_probs, deltas, p05s)):
        ax4.annotate(f'r={r},δ={d:.0f}', (e, p), xytext=(5, 5), 
                    textcoords='offset points', fontsize=8)
    
    # Add legend for colors
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='#D55E00', label='P05=0'),
                      Patch(facecolor='#E69F00', label='0<P05<1'),
                      Patch(facecolor='#009E73', label='P05=1')]
    ax4.legend(handles=legend_elements, loc='lower right')
    
    # Save plot
    plot_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'plots')
    os.makedirs(plot_dir, exist_ok=True)
    plot_path = os.path.join(plot_dir, 'safety_tradeoff.svg')
    save_figure(fig, plot_path)
    print(f'Saved plot to {plot_path}')
    
    # Show plot (optional, comment out if running headless)
    # plt.show()
