#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMERGENCY FIGURE GENERATOR
This script ONLY generates the 3 specific figures the user is angry about.
It uses distinct filenames to bypass any caching.
"""

import json
import os
import shutil
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, FancyArrow

# ------------------------------------------------------------------------------
# SETUP
# ------------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
SENSORS_DIR = os.path.join(RESULTS_DIR, "Sensors_figures")
os.makedirs(PLOTS_DIR, exist_ok=True)
os.makedirs(SENSORS_DIR, exist_ok=True)

mpl.rcParams.update({
    "font.family": "Palatino Linotype",
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "legend.fontsize": 9,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

OKABE_ITO = {
    'sky': '#56B4E9',
    'orange': '#E69F00',
    'green': '#009E73',
    'blue': '#0072B2',
    'red': '#D55E00',
    'purple': '#CC79A7',
}

# ------------------------------------------------------------------------------
# FIGURE 1: FLOWCHART (vFINAL)
# ------------------------------------------------------------------------------
def generate_flowchart_vfinal():
    print("Generating Figure 1 (Flowchart)...")
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.axis('off')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Professional Flat UI Colors
    C_INPUT = "#34495E"  # Dark Blue-Grey
    C_PROC = "#27AE60"   # Emerald Green
    C_OUT = "#D35400"    # Pumpkin Orange
    C_TEXT = "white"

    def draw_box(x, y, w, h, title, subtitle, color):
        # Shadow (using FancyBboxPatch for rounded corners, or simple Rectangle if failing)
        # Simpler approach: Just use Rectangle with no rounding if FancyBboxPatch is complex in this env
        # Or use boxstyle only for text or distinct patches.
        # Let's use standard Rectangle which is robust, but sharp corners.
        # To get rounded corners we need FancyBboxPatch
        from matplotlib.patches import FancyBboxPatch

        # Shadow
        rect_shadow = FancyBboxPatch((x+0.005, y-0.005), w, h, 
                              facecolor='black', alpha=0.2, edgecolor='none', zorder=1,
                              boxstyle="Round,pad=0.01,rounding_size=0.02")
        ax.add_patch(rect_shadow)
        # Main box
        rect = FancyBboxPatch((x, y), w, h, 
                         facecolor=color, edgecolor='none', zorder=2,
                         boxstyle="Round,pad=0.01,rounding_size=0.02")
        ax.add_patch(rect)
        
        # Title (Bold)
        ax.text(x + w/2, y + 0.7*h, title, 
                ha='center', va='center', fontsize=10, fontweight='bold', color=C_TEXT, zorder=3)
        # Subtitle (Normal)
        ax.text(x + w/2, y + 0.3*h, subtitle, 
                ha='center', va='center', fontsize=8.5, color=C_TEXT, zorder=3)
        
        # Return connection points
        return {
            'top': (x + w/2, y + h),
            'bottom': (x + w/2, y),
            'left': (x, y + h/2),
            'right': (x + w, y + h/2)
        }

    # 3 Columns layout
    col1_x = 0.02
    col2_x = 0.36
    col3_x = 0.70
    box_w = 0.26
    box_h = 0.18
    
    row1_y = 0.75
    row2_y = 0.45
    
    # --- INPUTS ---
    b_trace = draw_box(col1_x, row1_y, box_w, box_h, 
                      "Intel Traces", "Traffic / Channel / Env", C_INPUT)
    
    # --- PROCESSING (Row 1) ---
    b_map = draw_box(col2_x, row1_y, box_w, box_h,
                    "Environment Mapper", "ML Forecaster / History", C_PROC)
    
    b_policy = draw_box(col3_x, row1_y, box_w, box_h,
                       "Policy Selector", "Energy vs Robust Profile", C_PROC)

    # --- PROCESSING (Row 2) ---
    b_sched = draw_box(col2_x, row2_y, box_w, box_h,
                      "WSN Scheduler", "Cluster / Routes / Duty", C_PROC)
    
    # --- OUTPUTS ---
    b_out = draw_box(col3_x, row2_y, box_w, box_h,
                    "Outcomes", "PDR / Energy / Safety", C_OUT)

    # --- CONNECTIONS (Orthogonal) ---
    def connect(p1, p2):
        # Simple straight line with arrow
        ax.annotate("", xy=p2, xytext=p1,
                    arrowprops=dict(arrowstyle="->", color="#2C3E50", lw=1.5, shrinkA=0, shrinkB=0),
                    zorder=1)

    connect(b_trace['right'], b_map['left'])
    connect(b_map['right'], b_policy['left'])
    connect(b_policy['bottom'], (b_policy['bottom'][0], b_sched['top'][1] + 0.1)) # Visual guide
    
    # Complex connection: Policy -> Scheduler (Down and Left)
    # Drawing manual elbow arrow
    ax.plot([b_policy['bottom'][0], b_policy['bottom'][0]], [b_policy['bottom'][1], b_sched['right'][1]], 
            color="#2C3E50", lw=1.5, zorder=1)
    ax.plot([b_policy['bottom'][0], b_sched['right'][0]], [b_sched['right'][1], b_sched['right'][1]], 
            color="#2C3E50", lw=1.5, zorder=1)
    # Arrow head
    ax.arrow(b_sched['right'][0]+0.01, b_sched['right'][1], -0.01, 0, 
             head_width=0.02, head_length=0.02, fc="#2C3E50", ec="#2C3E50", zorder=1)

    connect(b_sched['right'], b_out['left'])
    
    # Title
    ax.text(0.5, 0.98, "AERIS Coordination Stack", ha='center', va='top', fontsize=12, fontweight='bold', color="#2C3E50")

    # Save
    fname = "paper_method_flowchart_vFINAL"
    fig.savefig(os.path.join(PLOTS_DIR, fname + ".pdf"), bbox_inches='tight', dpi=300)
    shutil.copy(os.path.join(PLOTS_DIR, fname + ".pdf"), os.path.join(SENSORS_DIR, fname + ".pdf"))
    print(f"Saved {fname}.pdf")
    plt.close(fig)


# ------------------------------------------------------------------------------
# FIGURE 2: BASELINES (vFINAL) - NO 'b' TAG
# ------------------------------------------------------------------------------
def generate_baselines_vfinal():
    print("Generating Figure 2 (Baselines, NO tags)...")
    
    # Load Data
    p_aether = os.path.join(RESULTS_DIR, 'intel_replay_compare.json')
    p_base = os.path.join(RESULTS_DIR, 'intel_baselines_all.json')
    
    if not (os.path.exists(p_aether) and os.path.exists(p_base)):
        print("Error: Missing data files for Figure 2")
        return

    a = json.load(open(p_aether, 'r', encoding='utf-8'))
    b = json.load(open(p_base, 'r', encoding='utf-8'))

    methods = ['AETHER_energy','AETHER_robust','LEACH','HEED','PEGASIS','TEEN']
    rows = []
    for m in methods:
        src = a if m in a else b
        if m in src:
            label_map = {
                'AETHER_energy': 'AERIS-E', 'AETHER_robust': 'AERIS-R',
                'LEACH': 'LEACH', 'HEED': 'HEED', 'PEGASIS': 'PEGASIS', 'TEEN': 'TEEN'
            }
            color_map = {
                'AETHER_energy': OKABE_ITO['green'], 'AETHER_robust': OKABE_ITO['red'],
                'LEACH': OKABE_ITO['blue'], 'HEED': OKABE_ITO['orange'],
                'PEGASIS': OKABE_ITO['purple'], 'TEEN': OKABE_ITO['sky']
            }
            rows.append({
                'm': m,
                'label': label_map.get(m, m),
                'energy': src[m]['total_energy_consumed'],
                'pdr': src[m]['packet_delivery_ratio_end2end'],
                'color': color_map.get(m, 'gray')
            })
            
    # Sort by PDR descending
    rows.sort(key=lambda r: r['pdr'], reverse=True)
    
    labels = [r['label'] for r in rows]
    energy = [r['energy'] for r in rows]
    pdr = [r['pdr'] for r in rows]
    colors = [r['color'] for r in rows]

    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.5), sharey=True)
    
    # --- Panel 1: Energy ---
    ax = axes[0]
    y = np.arange(len(labels))
    ax.hlines(y, xmin=0, xmax=energy, color='#D0D0D0', linewidth=1.0, zorder=1)
    for yi, (val, c) in enumerate(zip(energy, colors)):
        ax.plot([val], [yi], 'o', color=c, markersize=6, zorder=2)
        ax.text(val + 2, yi, f"{val:.1f}", va='center', ha='left', fontsize=8, color='#555')
        
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel('Energy (J) — lower is better')
    ax.set_title('Energy Consumption', fontweight='bold')
    ax.grid(axis='x', linestyle=':', alpha=0.5)
    # CRITICAL: NO PANEL TAG CODE HERE

    # --- Panel 2: PDR ---
    ax = axes[1]
    ax.hlines(y, xmin=0, xmax=pdr, color='#D0D0D0', linewidth=1.0, zorder=1)
    for yi, (val, c) in enumerate(zip(pdr, colors)):
        ax.plot([val], [yi], 'o', color=c, markersize=6, zorder=2)
        ax.text(val + 0.02, yi, f"{val:.2f}", va='center', ha='left', fontsize=8, color='#555')

    ax.set_yticks(y)
    ax.set_yticklabels([]) # Share Y
    ax.invert_yaxis()
    ax.set_xlim(0, 1.15) # Room for labels
    ax.set_xlabel('End-to-end PDR — higher is better')
    ax.set_title('Packet Delivery Ratio', fontweight='bold')
    ax.grid(axis='x', linestyle=':', alpha=0.5)
    # CRITICAL: NO PANEL TAG CODE HERE

    plt.tight_layout()
    
    fname = "paper_intel_baselines_panels_vFINAL"
    fig.savefig(os.path.join(PLOTS_DIR, fname + ".pdf"), bbox_inches='tight', dpi=300)
    shutil.copy(os.path.join(PLOTS_DIR, fname + ".pdf"), os.path.join(SENSORS_DIR, fname + ".pdf"))
    print(f"Saved {fname}.pdf")
    plt.close(fig)


# ------------------------------------------------------------------------------
# FIGURE 8: PDR BREAKDOWN (vFINAL) - CLEAN LAYOUT
# ------------------------------------------------------------------------------
def generate_breakdown_vfinal():
    print("Generating Figure 8 (Breakdown, vFINAL)...")
    data = json.load(open(os.path.join(RESULTS_DIR, "large_scale_long.json"), "r", encoding="utf-8"))
    
    SCENARIOS = ["uniform_300", "uniform_500"]
    PROFILES = ["AERIS_energy", "AERIS_robust"]
    
    BAR_COLORS = {
        "cluster": "#5DADE2",  # Soft Blue
        "uplink": "#F5B041",   # Soft Orange
        "end2end": "#58D68D",  # Soft Green
    }

    fig, axes = plt.subplots(1, 2, figsize=(8.5, 4.2), sharey=True)
    # Increased bottom margin for legend
    plt.subplots_adjust(top=0.85, bottom=0.25, wspace=0.1, left=0.1, right=0.95)

    width = 0.25
    x_pos = np.arange(len(SCENARIOS))

    for i, profile in enumerate(PROFILES):
        ax = axes[i]
        profile_data = [data[s][profile] for s in SCENARIOS]
        
        # Extract
        v_cluster = []
        v_uplink = []
        v_e2e = []
        
        for entry in profile_data:
            am = entry.get("additional_metrics", {})
            v_cluster.append(am.get("cluster_to_ch_pdr_total", 0))
            v_uplink.append(am.get("ch_to_bs_pdr_total", 0))
            v_e2e.append(entry.get("packet_delivery_ratio_end2end", 0))

        # Plot
        r1 = ax.bar(x_pos - width, v_cluster, width, color=BAR_COLORS['cluster'], label='Cluster->CH', zorder=3)
        r2 = ax.bar(x_pos, v_uplink, width, color=BAR_COLORS['uplink'], label='CH->BS', zorder=3)
        r3 = ax.bar(x_pos + width, v_e2e, width, color=BAR_COLORS['end2end'], label='End-to-End', zorder=3)

        # Labels
        def label_bars(rects):
            for rect in rects:
                h = rect.get_height()
                ax.text(rect.get_x() + rect.get_width()/2, h + 0.01, f"{h:.2f}", 
                        ha='center', va='bottom', fontsize=8)

        label_bars(r1)
        label_bars(r2)
        label_bars(r3)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(["Uniform-300", "Uniform-500"])
        ax.set_ylim(0, 1.15)
        ax.set_title(f"{'AERIS (Energy)' if 'energy' in profile else 'AERIS (Robust)'}", fontweight='bold')
        ax.grid(axis='y', linestyle=':', alpha=0.5, zorder=0)

        if i == 0:
            ax.set_ylabel("Packet Delivery Ratio (PDR)")
            
    # Legend - completely separate at bottom
    patches = [
        mpatches.Patch(color=BAR_COLORS['cluster'], label='Cluster $\\rightarrow$ CH'),
        mpatches.Patch(color=BAR_COLORS['uplink'], label='CH $\\rightarrow$ BS'),
        mpatches.Patch(color=BAR_COLORS['end2end'], label='End-to-End'),
    ]
    fig.legend(handles=patches, loc='lower center', bbox_to_anchor=(0.5, 0.02), 
               ncol=3, frameon=False, fontsize=10)
    
    fname = "paper_pdr_breakdown_large_scale_vFINAL"
    fig.savefig(os.path.join(PLOTS_DIR, fname + ".pdf"), bbox_inches='tight', dpi=300)
    shutil.copy(os.path.join(PLOTS_DIR, fname + ".pdf"), os.path.join(SENSORS_DIR, fname + ".pdf"))
    print(f"Saved {fname}.pdf")
    plt.close(fig)

if __name__ == "__main__":
    print("--- STARTING EMERGENCY PLOT GENERATION ---")
    try:
        generate_flowchart_vfinal()
        generate_baselines_vfinal()
        generate_breakdown_vfinal()
        print("--- SUCCESS ---")
    except Exception as e:
        print(f"--- FAILED: {e} ---")

