#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS Protocol Flowchart - Publication Quality for MDPI Sensors
Redesigned with TikZ-inspired aesthetics: clean boxes, orthogonal arrows, no overlaps.
"""

from pathlib import Path
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLOTS_DIR = PROJECT_ROOT / "results" / "plots"
SENSORS_DIR = PROJECT_ROOT / "results" / "Sensors_figures"

# Publication-grade settings
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Palatino Linotype", "Palatino", "Times New Roman", "DejaVu Serif"],
    "font.size": 9,
    "axes.linewidth": 0,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

# Muted, accessible palette
COLORS = {
    "input":   "#2F6690",   # Deep blue
    "process": "#77B6EA",   # Sky blue
    "core":    "#E07A5F",   # Coral
    "output":  "#1B263B",   # Slate
    "arrow":   "#4A5568",   # Gray blue
    "text_dark": "#1B263B",
    "text_light": "#FFFFFF",
    "shadow":  "#D9D9D9",
}


def draw_flowchart():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    SENSORS_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    ax.set_xlim(0, 9.5)
    ax.set_ylim(0, 4.2)
    ax.set_aspect('equal')
    ax.axis("off")

    # Box dimensions
    box_w = 1.9
    box_h = 1.15
    
    # Positions (top row flows left->right, bottom row collects safeguards/outputs)
    positions = {
        "input":    (0.6, 2.75),
        "envmap":   (3.0, 2.75),
        "cas":      (5.4, 2.75),
        "gateway":  (7.8, 2.75),
        "safety":   (2.2, 0.6),
        "eval":     (6.4, 0.6),
    }
    
    # Node definitions: (x, y, title, subtitle, color, text_color)
    nodes = {
        "input":   (*positions["input"],  "Inputs", "Intel traces · Topology\nHumidity/Temp logs", COLORS["input"], COLORS["text_light"]),
        "envmap":  (*positions["envmap"], "Env Mapper", "Log-normal params\nSmoothing + drift check", COLORS["process"], COLORS["text_dark"]),
        "cas":     (*positions["cas"],    "CAS + Skeleton", "Mode select (direct/chain/two-hop)\nBackbone build", COLORS["core"], COLORS["text_light"]),
        "gateway": (*positions["gateway"],"Gateway Voting", "Energy vs. robust profile\nSeed-sync aggregation", COLORS["process"], COLORS["text_dark"]),
        "safety":  (*positions["safety"], "Safety & Fairness", "Duty-cycle caps · redundancy alarms\nFairness rotation", COLORS["core"], COLORS["text_light"]),
        "eval":    (*positions["eval"],   "Diagnostics", "PDR · energy · lifetime\nWelch $t$-tests · effect size", COLORS["output"], COLORS["text_light"]),
    }
    
    node_rects = {}
    
    for key, (x, y, title, subtitle, bg_color, txt_color) in nodes.items():
        # Shadow
        shadow = FancyBboxPatch(
            (x + 0.05, y - 0.05), box_w, box_h,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            facecolor=COLORS["shadow"], edgecolor="none", zorder=1
        )
        ax.add_patch(shadow)
        
        # Main box
        box = FancyBboxPatch(
            (x, y), box_w, box_h,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            facecolor=bg_color, edgecolor="none", zorder=2
        )
        ax.add_patch(box)
        node_rects[key] = (x, y, box_w, box_h)
        
        # Title (bold, larger)
        ax.text(x + box_w/2, y + box_h - 0.25, title,
                ha="center", va="center", fontsize=9.5, fontweight="bold",
                color=txt_color, zorder=3)
        
        # Subtitle (smaller, multi-line)
        ax.text(x + box_w/2, y + 0.4, subtitle,
                ha="center", va="center", fontsize=8, linespacing=1.3,
                color=txt_color, alpha=0.9, zorder=3)
    
    # Arrow helper function
    def draw_arrow(start_key, end_key, start_side="right", end_side="left", bend=0):
        """Draw orthogonal arrows between nodes."""
        sx, sy, sw, sh = node_rects[start_key]
        ex, ey, ew, eh = node_rects[end_key]
        
        # Calculate connection points
        if start_side == "right":
            start_pt = (sx + sw, sy + sh/2)
        elif start_side == "bottom":
            start_pt = (sx + sw/2, sy)
        elif start_side == "left":
            start_pt = (sx, sy + sh/2)
        else:  # top
            start_pt = (sx + sw/2, sy + sh)
            
        if end_side == "left":
            end_pt = (ex, ey + eh/2)
        elif end_side == "top":
            end_pt = (ex + ew/2, ey + eh)
        elif end_side == "right":
            end_pt = (ex + ew, ey + eh/2)
        else:  # bottom
            end_pt = (ex + ew/2, ey)
        
        # Determine connection style
        if bend == 0:
            conn_style = "arc3,rad=0"
        else:
            conn_style = f"arc3,rad={bend}"
        
        arrow = FancyArrowPatch(
            start_pt, end_pt,
            arrowstyle="-|>",
            mutation_scale=12,
            color=COLORS["arrow"],
            linewidth=1.5,
            connectionstyle=conn_style,
            zorder=1
        )
        ax.add_patch(arrow)
    
    # Draw connections
    draw_arrow("input", "envmap", "right", "left")
    draw_arrow("envmap", "cas", "right", "left")
    draw_arrow("cas", "gateway", "right", "left")
    draw_arrow("cas", "safety", "bottom", "top")
    draw_arrow("gateway", "eval", "bottom", "top")
    draw_arrow("safety", "eval", "right", "left")
    
    # Stage labels
    stage_labels = [
        (1.6, 3.9, "Sensing"),
        (5.2, 3.9, "Adaptation & Routing"),
        (7.8, 1.95, "Reliability Outputs"),
    ]
    for lx, ly, label in stage_labels:
        ax.text(lx, ly, label, ha="center", va="bottom", fontsize=8.3,
                color="#5C677D", fontweight="bold")
    
    # Save
    plt.tight_layout(pad=0.5)
    
    for folder in (PLOTS_DIR, SENSORS_DIR):
        fig.savefig(folder / "paper_method_flowchart.svg", bbox_inches="tight", dpi=300)
        fig.savefig(folder / "paper_method_flowchart.pdf", bbox_inches="tight", dpi=300)
    
    plt.close(fig)
    print(f"[SUCCESS] Flowchart saved to {PLOTS_DIR / 'paper_method_flowchart.pdf'}")


if __name__ == "__main__":
    draw_flowchart()
