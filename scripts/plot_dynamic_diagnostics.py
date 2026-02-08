#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot dynamic-scenario diagnostics: cluster radius, CH->BS distance, gateway uplink PDR
for AERIS energy / robust profiles across all phases.
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
PROFILE_LABELS = {"AERIS_energy": "AERIS (energy)", "AERIS_robust": "AERIS (robust)"}
COLORS = {"AERIS_energy": "#1b9e77", "AERIS_robust": "#d95f02"}

mpl.rcParams.update(
    {
        "font.family": "Palatino Linotype",
        "font.size": 11,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    }
)


def load_replicate_entries(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if data and all(k.startswith("rep_") for k in data.keys()):
        return [data[k] for k in sorted(data.keys())]
    return [data]


def aggregate_metric(entries: List[Dict], phases: List[str]) -> Dict[str, Dict[str, float]]:
    agg: Dict[str, Dict[str, float]] = {profile: {} for profile in PROFILES}
    for profile in PROFILES:
        for phase in phases:
            values_radius: List[float] = []
            values_distance: List[float] = []
            values_gateway: List[float] = []
            for rep in entries:
                phase_block = rep.get(phase, {})
                entry = phase_block.get(profile)
                if not entry:
                    continue
                am = entry.get("additional_metrics", {})
                radius = am.get("cluster_radius_mean_total")
                distance = am.get("ch_to_bs_distance_mean_total")
                gateway_pdr = am.get("gateway_uplink_pdr_total")
                if radius is not None:
                    values_radius.append(radius)
                if distance is not None:
                    values_distance.append(distance)
                if gateway_pdr is not None:
                    values_gateway.append(gateway_pdr)
            agg[profile][phase] = {
                "radius": np.nanmean(values_radius) if values_radius else np.nan,
                "distance": np.nanmean(values_distance) if values_distance else np.nan,
                "gateway": np.nanmean(values_gateway) if values_gateway else np.nan,
            }
    return agg


def plot():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(SENSORS_DIR, exist_ok=True)

    fig, axes = plt.subplots(len(SCENARIOS), 3, figsize=(11.5, 7.5), sharex=True)

    for row_idx, scenario in enumerate(SCENARIOS):
        entries = load_replicate_entries(scenario["file"])
        metrics = aggregate_metric(entries, scenario["phases"])
        x = np.arange(len(scenario["phases"]))
        labels = scenario["labels"]

        for col_idx, metric_key in enumerate(["radius", "distance", "gateway"]):
            ax = axes[row_idx][col_idx]
            for profile in PROFILES:
                series = [metrics[profile][phase][metric_key] for phase in scenario["phases"]]
                ax.plot(
                    x,
                    series,
                    marker="o",
                    linewidth=2.0,
                    color=COLORS[profile],
                    label=PROFILE_LABELS[profile] if row_idx == 0 and col_idx == 0 else None,
                )
            ax.set_xticks(x)
            if row_idx == len(SCENARIOS) - 1:
                ax.set_xticklabels(labels, rotation=25)
            else:
                ax.set_xticklabels([])
            ax.grid(True, linestyle="--", alpha=0.35)
            if col_idx == 0:
                ax.set_ylabel(scenario["name"])
            if metric_key == "radius":
                ax.set_title("Mean cluster radius (m)")
            elif metric_key == "distance":
                ax.set_title("CH→BS distance (m)")
            else:
                ax.set_title("Gateway→BS PDR")
                ax.set_ylim(0, 1.05)

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False)
    fig.suptitle("Dynamic scenarios: structural and gateway diagnostics", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    base = "paper_dynamic_diagnostics"
    for folder in (PLOTS_DIR, SENSORS_DIR):
        fig.savefig(os.path.join(folder, f"{base}.svg"), bbox_inches="tight")
        fig.savefig(os.path.join(folder, f"{base}.pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"[PLOT] Saved dynamic diagnostics to {os.path.join(PLOTS_DIR, base + '.pdf')}")


if __name__ == "__main__":
    plot()
