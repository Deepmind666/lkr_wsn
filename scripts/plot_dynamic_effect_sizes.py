#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Produce Gardner–Altman style charts plus Cliff's delta bars for the dynamic
scenarios. The plot highlights (i) paired differences between AERIS energy and
robust profiles and (ii) Cliff's delta between classical baselines and AERIS
profiles. Output: paper_dynamic_effect_sizes.{pdf,svg}.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Sequence, Tuple

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
    },
    {
        "name": "Moving BS corridor",
        "file": os.path.join(RESULTS_DIR, "dynamic_moving_bs_compare_reps.json"),
        "phases": ["bs_phase1", "bs_phase2", "bs_phase3", "bs_phase4"],
    },
    {
        "name": "Random dropout",
        "file": os.path.join(RESULTS_DIR, "dynamic_dropout_compare_reps.json"),
        "phases": ["drop0", "drop10", "drop20", "drop30"],
    },
]

PROFILES = ["AERIS_energy", "AERIS_robust"]
PROFILE_LABELS = {"AERIS_energy": "AERIS (energy)", "AERIS_robust": "AERIS (robust)"}
PROFILE_COLORS = {"AERIS_energy": "#1b9e77", "AERIS_robust": "#d95f02"}
BASELINES = ["LEACH", "HEED", "PEGASIS", "TEEN"]
BASELINE_COLOR = "#555555"

mpl.rcParams.update(
    {
        "font.family": "Palatino Linotype",
        "font.size": 11,
        "axes.titlesize": 12,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    }
)


def _load_entries(path: str) -> List[Dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and all(k.startswith("rep_") for k in data):
        return [data[k] for k in sorted(data.keys())]
    if isinstance(data, list):
        return data
    return [data]


def _extract_series(
    entries: Sequence[Dict], phases: Sequence[str], protocol: str
) -> List[float]:
    series: List[float] = []
    for rep in entries:
        for phase in phases:
            block = rep.get(phase, {})
            entry = block.get(protocol)
            if not entry:
                continue
            value = entry.get(
                "packet_delivery_ratio_end2end",
                entry.get("packet_delivery_ratio"),
            )
            if value is not None:
                series.append(float(value))
    return series


def _extract_pairs(
    entries: Sequence[Dict], phases: Sequence[str]
) -> List[Tuple[float, float]]:
    pairs: List[Tuple[float, float]] = []
    for rep in entries:
        for phase in phases:
            block = rep.get(phase, {})
            e = block.get("AERIS_energy", {})
            r = block.get("AERIS_robust", {})
            val_e = e.get("packet_delivery_ratio_end2end", e.get("packet_delivery_ratio"))
            val_r = r.get("packet_delivery_ratio_end2end", r.get("packet_delivery_ratio"))
            if val_e is None or val_r is None:
                continue
            pairs.append((float(val_e), float(val_r)))
    return pairs


def _cliffs_delta(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return float("nan")
    wins = 0
    losses = 0
    for x in a:
        for y in b:
            if x > y:
                wins += 1
            elif x < y:
                losses += 1
    n_pairs = len(a) * len(b)
    return (wins - losses) / n_pairs if n_pairs else float("nan")


def _bootstrap_ci(samples: Sequence[float], rng: np.random.Generator, iters: int = 5000):
    if not samples:
        return float("nan"), float("nan")
    arr = np.asarray(samples)
    boot = np.empty(iters)
    for i in range(iters):
        picked = rng.choice(arr, size=len(arr), replace=True)
        boot[i] = picked.mean()
    low = np.percentile(boot, 2.5)
    high = np.percentile(boot, 97.5)
    return float(low), float(high)


def plot():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(SENSORS_DIR, exist_ok=True)

    fig, axes = plt.subplots(len(SCENARIOS), 2, figsize=(10.5, 10.0))
    rng = np.random.default_rng(2025)

    for idx, scenario in enumerate(SCENARIOS):
        entries = _load_entries(scenario["file"])
        pairs = _extract_pairs(entries, scenario["phases"])
        energy = [p[0] for p in pairs]
        robust = [p[1] for p in pairs]
        diffs = [r - e for e, r in pairs]
        mean_diff = float(np.mean(diffs)) if diffs else float("nan")
        ci_low, ci_high = _bootstrap_ci(diffs, rng)

        # Gardner–Altman style (paired scatter + difference axis)
        ax_left = axes[idx][0]
        x_positions = [0, 1]
        for xpos, data, key in zip(x_positions, [energy, robust], PROFILES):
            jitter = rng.normal(0, 0.03, size=len(data))
            ax_left.scatter(
                np.full(len(data), xpos) + jitter,
                data,
                s=26,
                color=PROFILE_COLORS[key],
                alpha=0.85,
                edgecolor="#333333",
                linewidth=0.35,
                label=PROFILE_LABELS[key],
            )
            ax_left.hlines(
                np.mean(data),
                xpos - 0.15,
                xpos + 0.15,
                colors=PROFILE_COLORS[key],
                linewidth=2.5,
            )
        ax_left.set_xlim(-0.5, 1.5)
        ax_left.set_xticks([0, 1], ["AERIS energy", "AERIS robust"])
        ax_left.set_ylim(0.0, 1.05)
        ax_left.set_ylabel("End-to-end PDR")
        if idx == 0:
            ax_left.legend(frameon=False, loc="upper right")
        ax_left.set_title(f"{scenario['name']} (n=20)")

        ax_diff = ax_left.twinx()
        jitter = rng.normal(0, 0.02, size=len(diffs))
        ax_diff.scatter(
            np.full(len(diffs), 0) + jitter,
            diffs,
            s=24,
            color="#6c5ce7",
            alpha=0.75,
            edgecolor="#333333",
            linewidth=0.3,
        )
        ax_diff.errorbar(
            0.25,
            mean_diff,
            yerr=[[mean_diff - ci_low], [ci_high - mean_diff]],
            fmt="s",
            color="#6c5ce7",
            ecolor="#6c5ce7",
            capsize=4,
            label="Mean Δ ±95% CI",
        )
        ax_diff.axhline(0.0, linestyle="--", color="#888888", linewidth=1.0)
        ax_diff.set_ylim(min(-0.25, min(diffs, default=0.0) - 0.05), max(0.25, max(diffs, default=0.0) + 0.05))
        ax_diff.set_ylabel("Δ Robust - Energy")
        if idx == 0:
            ax_diff.legend(frameon=False, loc="lower right")

        # Cliff's delta bars (classical vs AERIS profiles)
        ax_right = axes[idx][1]
        bars = []
        labels = []
        y_positions = []
        for baseline in BASELINES:
            baseline_samples = _extract_series(entries, scenario["phases"], baseline)
            for offset, profile in enumerate(PROFILES):
                target_samples = energy if profile == "AERIS_energy" else robust
                delta = _cliffs_delta(baseline_samples, target_samples)
                bars.append(delta)
                labels.append(f"{baseline} vs {profile.split('_')[1]}")
                y_positions.append(len(labels) - 1)
        colors = [PROFILE_COLORS["AERIS_energy"], PROFILE_COLORS["AERIS_robust"]] * len(BASELINES)
        ax_right.barh(y_positions, bars, color=colors, alpha=0.85)
        ax_right.axvline(0.0, color="#333333", linewidth=1.0)
        ax_right.set_yticks(y_positions, labels)
        ax_right.set_xlim(-1.0, 1.0)
        ax_right.set_xlabel("Cliff's δ (vs AERIS)")
        ax_right.set_title(f"{scenario['name']} effect sizes")

    fig.tight_layout()
    base = "paper_dynamic_effect_sizes"
    for folder in (PLOTS_DIR, SENSORS_DIR):
        fig.savefig(os.path.join(folder, f"{base}.pdf"), bbox_inches="tight")
        fig.savefig(os.path.join(folder, f"{base}.svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"[PLOT] Saved dynamic effect sizes to {os.path.join(PLOTS_DIR, base + '.pdf')}")


if __name__ == "__main__":
    plot()
