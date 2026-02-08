#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDR Breakdown Diagnostic Plot for Large-Scale Scenarios
Publication-ready for MDPI Sensors: Clean layout, no overlaps, professional aesthetics.
"""

import json
import os
import statistics
from typing import Dict, List

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
SENSORS_DIR = os.path.join(RESULTS_DIR, "Sensors_figures")

# Robust profile, multi-gateway sweep (extended scales)
FILES = [
    ("300 nodes", "800 rounds", "results/large_scale_long_gateway_sweep_n10_300.json"),
    ("500 nodes", "800 rounds", "results/large_scale_long_gateway_sweep_n10_500.json"),
    ("1000 nodes", "500 rounds", "results/large_scale_long_gateway_sweep_n5_1000.json"),
    ("2000 nodes", "400 rounds", "results/large_scale_long_gateway_sweep_n3_2000.json"),
]

# Refined Color Palette (Accessible, High Contrast)
BAR_COLORS = {
    "cluster": "#4A90D9",   # Blue
    "uplink":  "#F5A623",   # Orange
    "end2end": "#7ED321",   # Green
}

# Publication-grade matplotlib settings
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


def load_multi(path: str) -> Dict[str, float]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    pdr = []
    cluster = []
    uplink = []
    for entry in data.values():
        am = entry.get("additional_metrics", {})
        pdr.append(entry.get("packet_delivery_ratio_end2end", entry.get("packet_delivery_ratio", 0.0)))
        cluster.append(am.get("cluster_to_ch_pdr_total", float("nan")))
        uplink.append(am.get("ch_to_bs_pdr_total", float("nan")))

    def summary(arr: List[float]):
        return statistics.mean(arr), min(arr), max(arr), len(arr)

    m_end, mn_end, mx_end, n = summary(pdr)
    m_cluster, mn_cluster, mx_cluster, _ = summary(cluster)
    m_uplink, mn_uplink, mx_uplink, _ = summary(uplink)

    return {
        "n": n,
        "cluster": (m_cluster, mn_cluster, mx_cluster),
        "uplink": (m_uplink, mn_uplink, mx_uplink),
        "end2end": (m_end, mn_end, mx_end),
    }


def plot_breakdown():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(SENSORS_DIR, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.0, 3.4))

    width = 0.22
    x_positions = np.arange(len(FILES))
    offsets = {"cluster": -width, "uplink": 0.0, "end2end": width}

    stats = []
    for label, rounds, path in FILES:
        st = load_multi(path)
        stats.append((label, rounds, st))

    for idx, (label, rounds, st) in enumerate(stats):
        for metric in ["cluster", "uplink", "end2end"]:
            mean, mn, mx = st[metric]
            bars = ax.bar(
                x_positions[idx] + offsets[metric],
                mean,
                width=width * 0.9,
                color=BAR_COLORS[metric],
                edgecolor="none",
                alpha=0.92,
                zorder=3
            )
            # error bars only if n>1
            if st["n"] > 1:
                yneg = max(mean - mn, 0.003)
                ypos = max(mx - mean, 0.003)
                ax.errorbar(
                    x_positions[idx] + offsets[metric],
                    mean,
                    yerr=[[yneg], [ypos]],
                    fmt="none",
                    ecolor="#333333",
                    elinewidth=0.9,
                    capsize=3.5,
                    zorder=4
                )
            # label
            ax.text(
                x_positions[idx] + offsets[metric],
                mean + 0.018,
                f"{mean:.3f}",
                ha="center", va="bottom",
                fontsize=7, color="#333333"
            )

    ax.set_xticks(x_positions)
    ax.set_xticklabels([f"{label}\n({rounds}, n={st['n']})" for label, rounds, st in stats])
    ax.set_ylim(0, 1.08)
    ax.set_title("Large-scale PDR breakdown (AERIS robust, multi-gateway)", pad=8)
    ax.set_ylabel("Packet Delivery Ratio")
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.55, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", pad=6)

    legend_patches = [
        mpatches.Patch(color=BAR_COLORS["cluster"], label="Cluster → CH"),
        mpatches.Patch(color=BAR_COLORS["uplink"], label="CH → BS"),
        mpatches.Patch(color=BAR_COLORS["end2end"], label="End-to-End"),
    ]
    fig.legend(
        handles=legend_patches,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=3,
        frameon=False,
        fontsize=8,
        columnspacing=1.6,
        handlelength=1.5
    )

    plt.tight_layout(rect=[0, 0.08, 1, 1])

    base = "paper_pdr_breakdown_large_scale"
    for folder in (PLOTS_DIR, SENSORS_DIR):
        fig.savefig(os.path.join(folder, f"{base}.svg"), bbox_inches="tight", dpi=300)
        fig.savefig(os.path.join(folder, f"{base}.pdf"), bbox_inches="tight", dpi=300)

    plt.close(fig)
    print(f"[SUCCESS] PDR breakdown saved to {os.path.join(PLOTS_DIR, base + '.pdf')}")


if __name__ == "__main__":
    plot_breakdown()
