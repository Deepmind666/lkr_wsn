#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot replicate-level hop-level PDR distributions for the three dynamic scenarios.
Each box summarizes the mean hop-level PDR of one protocol across replicates (averaged over phases).
Outputs SVG/PDF suitable for the MDPI manuscript.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
SENSORS_DIR = os.path.join(RESULTS_DIR, "Sensors_figures")

SCENARIOS = [
    (["dynamic_corridor_compare_r8.json", "dynamic_corridor_compare_reps.json", "dynamic_corridor_compare.json"], "Corridor shifts"),
    (["dynamic_moving_bs_compare_r8.json", "dynamic_moving_bs_compare_reps.json", "dynamic_moving_bs_compare.json"], "Moving BS"),
    (["dynamic_dropout_compare_r8.json", "dynamic_dropout_compare_reps.json", "dynamic_dropout_compare.json"], "Random dropout"),
]

PDR_KEY = "packet_delivery_ratio"

PROTOCOLS = ["LEACH", "HEED", "PEGASIS", "TEEN", "AERIS-E", "AERIS-R"]
DISPLAY = {
    "LEACH": "LEACH",
    "HEED": "HEED",
    "PEGASIS": "PEGASIS",
    "TEEN": "TEEN",
    "AERIS-E": "AERIS-E",
    "AERIS-R": "AERIS-R",
    # Fallback for old naming
    "AERIS_energy": "AERIS-E",
    "AERIS_robust": "AERIS-R",
}

PALETTE = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02"]
COLORS = {proto: PALETTE[idx % len(PALETTE)] for idx, proto in enumerate(PROTOCOLS)}

mpl.rcParams.update(
    {
        "font.family": "Palatino Linotype",
        "font.size": 11,
        "axes.prop_cycle": cycler(color=PALETTE),
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def load_replicate_means(path_candidates: List[str]) -> Dict[str, List[float]]:
    """Load data from first available file in candidates list."""
    # Find first available file
    full_path = None
    for rel_path in path_candidates:
        candidate = os.path.join(RESULTS_DIR, rel_path)
        if os.path.exists(candidate):
            full_path = candidate
            break
    if full_path is None:
        raise FileNotFoundError(f"No file found among {path_candidates}")

    with open(full_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    proto_values: Dict[str, List[float]] = {proto: [] for proto in PROTOCOLS}

    rep_keys = [k for k in data.keys() if k.startswith("rep_")]
    reps = rep_keys if rep_keys else ["_single"]

    for rep_key in reps:
        phase_dict = data[rep_key] if rep_key != "_single" else data
        for proto in PROTOCOLS:
            phase_values: List[float] = []
            for phase in phase_dict.values():
                # Try new naming first, then fallback
                entry = phase.get(proto)
                if not entry and proto == "AERIS-E":
                    entry = phase.get("AERIS_energy")
                if not entry and proto == "AERIS-R":
                    entry = phase.get("AERIS_robust")
                if not entry:
                    continue
                value = entry.get(PDR_KEY)
                if value is not None:
                    phase_values.append(value)
            if phase_values:
                proto_values[proto].append(float(np.mean(phase_values)))
    return proto_values


def plot_boxplots():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(SENSORS_DIR, exist_ok=True)

    fig, axes = plt.subplots(1, len(SCENARIOS), figsize=(10, 3.4), sharey=True)
    for ax, (path_candidates, title) in zip(axes, SCENARIOS):
        proto_values = load_replicate_means(path_candidates)
        positions = np.arange(1, len(PROTOCOLS) + 1)
        box_data = [proto_values[proto] for proto in PROTOCOLS]

        bp = ax.boxplot(
            box_data,
            positions=positions,
            widths=0.5,
            patch_artist=True,
            showmeans=True,
            meanline=True,
        )

        for patch, proto in zip(bp["boxes"], PROTOCOLS):
            patch.set_facecolor(COLORS[proto])
            patch.set_alpha(0.55)
        for whisker in bp["whiskers"]:
            whisker.set_color("#1f2933")
        for cap in bp["caps"]:
            cap.set_color("#1f2933")
        for median in bp["medians"]:
            median.set_color("#111111")
        for mean in bp["means"]:
            mean.set_color("#111111")
            mean.set_linewidth(1.2)

        # overlay individual points
        for idx, proto in enumerate(PROTOCOLS, start=1):
            values = proto_values[proto]
            jitter = (np.random.rand(len(values)) - 0.5) * 0.15
            ax.scatter(
                np.full_like(values, idx) + jitter,
                values,
                color=COLORS[proto],
                edgecolor="#111111",
                linewidth=0.4,
                s=18,
                alpha=0.9,
                zorder=3,
            )

        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xticks(positions)
        ax.set_xticklabels([DISPLAY[p] for p in PROTOCOLS], rotation=45, ha="right")
        ax.set_ylim(0.0, 1.05)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.set_ylabel("Mean hop-level PDR" if ax is axes[0] else "")

    fig.suptitle("Replicate-level hop-level PDR distributions (mean over phases)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    base = "paper_dynamic_pdr_boxplots"
    svg_path = os.path.join(PLOTS_DIR, f"{base}.svg")
    pdf_path = os.path.join(PLOTS_DIR, f"{base}.pdf")
    fig.savefig(svg_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(os.path.join(SENSORS_DIR, f"{base}.svg"), bbox_inches="tight")
    fig.savefig(os.path.join(SENSORS_DIR, f"{base}.pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"[BOXPLOT] Saved to {svg_path}")


if __name__ == "__main__":
    plot_boxplots()
