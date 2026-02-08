#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot phase-wise PDR breakdown (cluster->CH, CH->BS, end-to-end)
for dynamic scenarios using replicate JSON outputs.

Outputs SVG/PDF for inclusion in the manuscript.
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

SCENARIOS = [
    {
        "name": "Corridor shifts",
        "file": os.path.join(RESULTS_DIR, "dynamic_corridor_compare_reps.json"),
        "phases": ["phase1", "phase2", "phase3", "phase4"],
        "labels": ["Shift 0", "Shift 20", "Shift 40", "Shift 60"],
    },
    {
        "name": "Moving BS",
        "file": os.path.join(RESULTS_DIR, "dynamic_moving_bs_compare_reps.json"),
        "phases": ["bs_phase1", "bs_phase2", "bs_phase3", "bs_phase4"],
        "labels": ["BS 260", "BS 300", "BS 340", "BS 380"],
    },
    {
        "name": "Random dropout",
        "file": os.path.join(RESULTS_DIR, "dynamic_dropout_compare_reps.json"),
        "phases": ["drop0", "drop10", "drop20", "drop30"],
        "labels": ["Drop 0%", "Drop 10%", "Drop 20%", "Drop 30%"],
    },
]

PROFILES = ["AERIS_energy", "AERIS_robust"]
COLORS = {"cluster": "#5DA5DA", "uplink": "#FAA43A", "end2end": "#60BD68"}

mpl.rcParams.update(
    {
        "font.family": "Palatino Linotype",
        "font.size": 11,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    }
)


def load_replicates(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if data and all(k.startswith("rep_") for k in data.keys()):
        reps = [data[k] for k in sorted(data.keys())]
    else:
        reps = [data]
    return reps


def aggregate_phase_metrics(reps: List[Dict], phases: List[str]) -> Dict[str, Dict[str, Dict[str, float]]]:
    summary: Dict[str, Dict[str, Dict[str, float]]] = {profile: {} for profile in PROFILES}
    for profile in PROFILES:
        for phase in phases:
            cluster_vals: List[float] = []
            uplink_vals: List[float] = []
            end_vals: List[float] = []
            for rep in reps:
                phase_results = rep.get(phase, {})
                entry = phase_results.get(profile)
                if not entry:
                    continue
                am = entry.get("additional_metrics", {})
                cluster_vals.append(am.get("cluster_to_ch_pdr_total"))
                uplink_vals.append(am.get("ch_to_bs_pdr_total"))
                end_vals.append(entry.get("packet_delivery_ratio_end2end"))
            summary[profile][phase] = {
                "cluster": np.nanmean(cluster_vals) if cluster_vals else np.nan,
                "uplink": np.nanmean(uplink_vals) if uplink_vals else np.nan,
                "end2end": np.nanmean(end_vals) if end_vals else np.nan,
            }
    return summary


def plot_breakdown():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(SENSORS_DIR, exist_ok=True)

    fig, axes = plt.subplots(len(SCENARIOS), len(PROFILES), figsize=(10, 7), sharey=True)
    if len(SCENARIOS) == 1:
        axes = np.array([axes])
    if len(PROFILES) == 1:
        axes = axes[:, np.newaxis]

    for row_idx, scenario in enumerate(SCENARIOS):
        reps = load_replicates(scenario["file"])
        summary = aggregate_phase_metrics(reps, scenario["phases"])
        phase_labels = scenario["labels"]
        x = np.arange(len(phase_labels))
        for col_idx, profile in enumerate(PROFILES):
            ax = axes[row_idx][col_idx]
            metrics = summary[profile]
            cluster_series = [metrics[ph]["cluster"] for ph in scenario["phases"]]
            uplink_series = [metrics[ph]["uplink"] for ph in scenario["phases"]]
            end_series = [metrics[ph]["end2end"] for ph in scenario["phases"]]
            ax.plot(x, cluster_series, marker="o", color=COLORS["cluster"], label="Cluster->CH")
            ax.plot(x, uplink_series, marker="s", color=COLORS["uplink"], label="CH->BS")
            ax.plot(x, end_series, marker="^", color=COLORS["end2end"], label="End-to-end")
            ax.set_xticks(x)
            ax.set_xticklabels(phase_labels, rotation=30)
            ax.set_ylim(0, 1.05)
            ax.grid(True, linestyle="--", alpha=0.4)
            if row_idx == 0:
                ax.set_title(profile.replace("AERIS_", "AERIS "), fontsize=12, fontweight="bold")
            if col_idx == 0:
                ax.set_ylabel(f"{scenario['name']}\nPDR")
            if row_idx == len(SCENARIOS) - 1:
                ax.set_xlabel("Phase")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False)
    fig.suptitle("Dynamic scenarios: PDR breakdown per phase", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    base = "paper_dynamic_phase_breakdown"
    for folder in (PLOTS_DIR, SENSORS_DIR):
        fig.savefig(os.path.join(folder, f"{base}.svg"), bbox_inches="tight")
        fig.savefig(os.path.join(folder, f"{base}.pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"[PLOT] Saved dynamic phase breakdown to {os.path.join(PLOTS_DIR, base + '.pdf')}")


if __name__ == "__main__":
    plot_breakdown()
