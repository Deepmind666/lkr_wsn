#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate publication-grade comparison figures for dynamic/dropout/moving/large-scale
scenarios, each including LEACH/PEGASIS/HEED/TEEN and AERIS profiles.

Outputs SVG/PDF to results/plots and results/Sensors_figures.
"""

import json
import os
from typing import Dict, List, Optional, Tuple

import matplotlib as mpl
from cycler import cycler
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
SENSORS_DIR = os.path.join(RESULTS_DIR, "Sensors_figures")

PROTOCOL_ORDER = [
    "LEACH",
    "HEED",
    "PEGASIS",
    "TEEN",
    "AERIS-E",
    "AERIS-R",
]

DISPLAY_NAMES = {
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

PALETTE = [
    "#1b9e77",
    "#d95f02",
    "#7570b3",
    "#e7298a",
    "#66a61e",
    "#e6ab02",
]

MARKERS = {
    "LEACH": "o",
    "HEED": "s",
    "PEGASIS": "D",
    "TEEN": "^",
    "AERIS-E": "v",
    "AERIS-R": "P",
    # Fallback for old naming
    "AERIS_energy": "v",
    "AERIS_robust": "P",
}

COLORS = {
    proto: PALETTE[idx % len(PALETTE)]
    for idx, proto in enumerate(PROTOCOL_ORDER)
}

mpl.rcParams.update({
    "font.family": "Palatino Linotype",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "figure.dpi": 300,
    "axes.grid": True,
    "grid.linestyle": "--",
    "grid.alpha": 0.4,
    "axes.prop_cycle": cycler(color=PALETTE),
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})

SCENARIOS: Dict[str, Dict] = {
    "dynamic_corridor": {
        "files": [
            os.path.join(RESULTS_DIR, "dynamic_corridor_compare_r8.json"),
            os.path.join(RESULTS_DIR, "dynamic_corridor_compare_reps.json"),
            os.path.join(RESULTS_DIR, "dynamic_corridor_compare.json"),
        ],
        "phases": ["phase1", "phase2", "phase3", "phase4"],
        "phase_labels": {
            "phase1": "Shift 0 m",
            "phase2": "Shift 20 m",
            "phase3": "Shift 40 m",
            "phase4": "Shift 60 m",
        },
        "title": "Dynamic Corridor (80 nodes, Intel-driven shadowing)",
        "output": "paper_dynamic_corridor_compare",
        "pdr_ylim": (0.35, 1.02),
    },
    "dynamic_moving_bs": {
        "files": [
            os.path.join(RESULTS_DIR, "dynamic_moving_bs_compare_r8.json"),
            os.path.join(RESULTS_DIR, "dynamic_moving_bs_compare_reps.json"),
            os.path.join(RESULTS_DIR, "dynamic_moving_bs_compare.json"),
        ],
        "phases": ["bs_phase1", "bs_phase2", "bs_phase3", "bs_phase4"],
        "phase_labels": {
            "bs_phase1": "BS @ 260 m",
            "bs_phase2": "BS @ 300 m",
            "bs_phase3": "BS @ 340 m",
            "bs_phase4": "BS @ 380 m",
        },
        "title": "Moving Base Station Corridor (80 nodes)",
        "output": "paper_dynamic_moving_bs_compare",
        "pdr_ylim": (0.35, 1.02),
    },
    "dynamic_dropout": {
        "files": [
            os.path.join(RESULTS_DIR, "dynamic_dropout_compare_r8.json"),
            os.path.join(RESULTS_DIR, "dynamic_dropout_compare_reps.json"),
            os.path.join(RESULTS_DIR, "dynamic_dropout_compare.json"),
        ],
        "phases": ["drop0", "drop10", "drop20", "drop30"],
        "phase_labels": {
            "drop0": "Drop 0%",
            "drop10": "Drop 10%",
            "drop20": "Drop 20%",
            "drop30": "Drop 30%",
        },
        "title": "Random Dropout Stress Test (120->84 nodes)",
        "output": "paper_dynamic_dropout_compare",
        "pdr_ylim": (0.35, 1.02),
    },
    "large_scale": {
        "files": [os.path.join(RESULTS_DIR, "large_scale_long.json")],
        "phases": ["uniform_300", "uniform_500"],
        "phase_labels": {
            "uniform_300": "300 nodes",
            "uniform_500": "500 nodes",
        },
        "title": "Large-Scale, 1000-Round Runs",
        "output": "paper_large_scale_compare",
        "pdr_ylim": (0.0, 1.02),
    },
}


def load_json_from_candidates(paths: List[str]) -> Dict:
    for path in paths:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
    raise FileNotFoundError(f"No available files among {paths}")


def is_replicate_bundle(data: Dict) -> bool:
    if not data:
        return False
    keys = list(data.keys())
    return keys and all(isinstance(k, str) and k.startswith("rep_") for k in keys)


def aggregate_metric(samples: List[Dict], metric: str):
    values: List[float] = [
        sample[metric]
        for sample in samples
        if sample and metric in sample and sample[metric] is not None
    ]
    if not values:
        return None
    arr = np.array(values, dtype=float)
    mean_val = float(arr.mean())
    std_val = float(arr.std(ddof=1 if arr.size > 1 else 0))
    return mean_val, std_val


def aggregate_entry(samples: List[Dict]) -> Dict:
    entry: Dict[str, float] = {}
    for metric in [
        "packet_delivery_ratio_end2end",
        "packet_delivery_ratio",
        "total_energy_consumed",
        "final_alive_nodes",
        "network_lifetime",
    ]:
        stats = aggregate_metric(samples, metric)
        if stats:
            mean_val, std_val = stats
            entry[metric] = mean_val
            entry[f"{metric}_std"] = std_val
    return entry


def aggregate_replicates(data: Dict, phases: Optional[List[str]]) -> Dict:
    rep_keys = sorted(k for k in data if k.startswith("rep_"))
    if not rep_keys:
        return data
    if not phases:
        # fall back to keys from the first replicate dictionary
        for key in rep_keys:
            phases = list(data[key].keys())
            if phases:
                break
    aggregated: Dict[str, Dict] = {phase: {} for phase in phases}
    for phase in phases:
        for proto in PROTOCOL_ORDER:
            samples = []
            for rep_key in rep_keys:
                phase_dict = data[rep_key]
                entry = phase_dict.get(phase, {}).get(proto)
                if entry:
                    samples.append(entry)
            if samples:
                aggregated[phase][proto] = aggregate_entry(samples)
    return aggregated


def ensure_dirs():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(SENSORS_DIR, exist_ok=True)


def metric_series(
    phase_data: Dict[str, Dict],
    phases: List[str],
    protocol: str,
    metric: str,
    fallback: str = None,
) -> Tuple[np.ndarray, np.ndarray]:
    means: List[float] = []
    stds: List[float] = []
    for phase in phases:
        entry = phase_data.get(phase, {}).get(protocol)
        value = np.nan
        std_val = 0.0
        if entry:
            value = entry.get(metric, np.nan)
            std_val = entry.get(f"{metric}_std", 0.0)
            if (value is None or np.isnan(value)) and fallback:
                value = entry.get(fallback, np.nan)
                std_val = entry.get(f"{fallback}_std", 0.0)
        means.append(value if value is not None else np.nan)
        stds.append(std_val if std_val is not None else 0.0)
    return np.array(means, dtype=float), np.array(stds, dtype=float)


def has_variation(stds: np.ndarray) -> bool:
    finite = stds[np.isfinite(stds)]
    return finite.size > 0 and np.max(finite) > 0


def ensure_dirs():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(SENSORS_DIR, exist_ok=True)


def plot_scenario(cfg: Dict):
    files = cfg.get("files") or [cfg["file"]]
    data = load_json_from_candidates(files)
    if is_replicate_bundle(data):
        data = aggregate_replicates(data, cfg.get("phases"))

    phases: List[str] = cfg.get("phases") or list(data.keys())
    # Keep only protocols that appear in at least one phase
    protocols = [
        p for p in PROTOCOL_ORDER
        if any(p in data.get(phase, {}) for phase in phases)
    ]

    # Decide whether every protocol exposes end-to-end PDR; if not, fall back to hop-level PDR
    use_end_to_end = True
    for phase in phases:
        phase_data = data.get(phase, {})
        for protocol in protocols:
            node = phase_data.get(protocol)
            if not node:
                continue
            if "packet_delivery_ratio_end2end" not in node:
                use_end_to_end = False
                break
        if not use_end_to_end:
            break
    pdr_key = "packet_delivery_ratio_end2end" if use_end_to_end else "packet_delivery_ratio"

    x = np.arange(len(phases))
    # Wider/taller canvas to reduce text/legend collisions (esp. dropout plots)
    fig, axes = plt.subplots(2, 1, figsize=(8.6, 6.2), sharex=True)

    for protocol in protocols:
        pdr_vals, pdr_stds = metric_series(data, phases, protocol, pdr_key, "packet_delivery_ratio")
        energy_vals, energy_stds = metric_series(data, phases, protocol, "total_energy_consumed")

        color = COLORS.get(protocol, "#000000")
        label = DISPLAY_NAMES.get(protocol, protocol)

        axes[0].plot(
            x,
            pdr_vals,
            marker=MARKERS.get(protocol, "o"),
            color=color,
            linewidth=0.9,
            markersize=4,
            label=label,
        )
        if has_variation(pdr_stds):
            axes[0].fill_between(
                x,
                pdr_vals - pdr_stds,
                pdr_vals + pdr_stds,
                color=color,
                alpha=0.0,
                linewidth=0,
            )

        axes[1].plot(
            x,
            energy_vals,
            marker=MARKERS.get(protocol, "o"),
            color=color,
            linewidth=0.9,
            markersize=4,
            label=label,
        )
        if has_variation(energy_stds):
            axes[1].fill_between(
                x,
                energy_vals - energy_stds,
                energy_vals + energy_stds,
                color=color,
                alpha=0.0,
                linewidth=0,
            )

    pdr_label = "End-to-End PDR" if use_end_to_end else "Hop-level PDR"
    axes[0].set_ylabel(pdr_label)
    if "pdr_ylim" in cfg:
        axes[0].set_ylim(*cfg["pdr_ylim"])
    axes[0].grid(True, linestyle="--", linewidth=0.5, alpha=0.6)

    axes[1].set_ylabel("Total Energy (J)")
    axes[1].grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
    axes[1].set_xlabel("Scenario Phase")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(
        [cfg.get("phase_labels", {}).get(phase, phase) for phase in phases],
        rotation=0,
    )

    # 预留更大顶部空间：图例最上，标题居中放在图例下方、曲线区域上方
    fig.suptitle(cfg["title"], fontsize=11.5, fontweight="bold", y=0.95)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=min(len(protocols), 3),
        frameon=False,
        fontsize=9,
        bbox_to_anchor=(0.5, 1.08),
    )
    # 顶部留白用于图例+标题，子图下移
    fig.tight_layout(rect=[0, 0.05, 1, 0.72])

    ensure_dirs()
    base = cfg["output"]
    svg_path = os.path.join(PLOTS_DIR, f"{base}.svg")
    pdf_path = os.path.join(PLOTS_DIR, f"{base}.pdf")
    fig.savefig(svg_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(os.path.join(SENSORS_DIR, f"{base}.svg"), bbox_inches="tight")
    fig.savefig(os.path.join(SENSORS_DIR, f"{base}.pdf"), bbox_inches="tight")
    print(f"[SAVED] {svg_path}")
    plt.close(fig)


def main():
    ensure_dirs()
    for scenario, cfg in SCENARIOS.items():
        print(f"[PLOT] {scenario}")
        plot_scenario(cfg)


if __name__ == "__main__":
    main()
