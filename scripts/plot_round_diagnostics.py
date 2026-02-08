#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot round-level diagnostic densities for large-scale scenarios using
cluster->CH vs CH->BS success rates from dynamic JSON outputs.

Outputs paper_round_diagnostics_large_scale.{svg,pdf}.
"""

import json
import os
from typing import Dict, List

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
SENSORS_DIR = os.path.join(RESULTS_DIR, "Sensors_figures")

LARGE_SCALE_FILE = os.path.join(RESULTS_DIR, "large_scale_long.json")
SCENARIOS = ["uniform_300", "uniform_500"]
PROFILE = "AERIS_robust"

mpl.rcParams.update(
    {
        "font.family": "Palatino Linotype",
        "font.size": 11,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def load_large_scale_rounds() -> Dict[str, List[Dict]]:
    with open(LARGE_SCALE_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    round_data: Dict[str, List[Dict]] = {}
    for scenario in SCENARIOS:
        entry = data[scenario][PROFILE]
        round_data[scenario] = entry.get("round_statistics", [])
    return round_data


def extract_series(round_stats: List[Dict], key_attempts: str, key_success: str) -> np.ndarray:
    series: List[float] = []
    for stats in round_stats:
        attempts = stats.get(key_attempts, 0)
        success = stats.get(key_success, 0)
        if attempts > 0:
            series.append(success / attempts)
    return np.array(series, dtype=float)


def plot_round_density(round_data: Dict[str, List[Dict]]):
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(SENSORS_DIR, exist_ok=True)

    fig, axes = plt.subplots(1, len(SCENARIOS), figsize=(8.5, 3.6), sharex=True, sharey=True)
    bins = np.linspace(0, 1, 40)

    for ax, scenario in zip(axes, SCENARIOS):
        rounds = round_data[scenario]
        cluster_series = extract_series(rounds, "cluster_to_ch_attempts", "cluster_to_ch_success")
        uplink_series = extract_series(rounds, "ch_to_bs_attempts", "ch_to_bs_success")
        ax.hist(
            cluster_series,
            bins=bins,
            alpha=0.6,
            label="Cluster->CH",
            density=True,
            color="#5DA5DA",
        )
        ax.hist(
            uplink_series,
            bins=bins,
            alpha=0.6,
            label="CH->BS",
            density=True,
            color="#FAA43A",
        )
        ax.set_title(f"{scenario.replace('_', ' ').title()}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Per-round success probability")
        ax.grid(True, linestyle="--", alpha=0.4)

    axes[0].set_ylabel("Density")
    axes[0].legend(loc="upper left")
    fig.suptitle("Round-level PDR distributions (AERIS robust)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    base = "paper_round_diagnostics_large_scale"
    for folder in (PLOTS_DIR, SENSORS_DIR):
        fig.savefig(os.path.join(folder, f"{base}.svg"), bbox_inches="tight")
        fig.savefig(os.path.join(folder, f"{base}.pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"[PLOT] Saved round diagnostics to {os.path.join(PLOTS_DIR, base + '.pdf')}")


if __name__ == "__main__":
    data = load_large_scale_rounds()
    plot_round_density(data)
