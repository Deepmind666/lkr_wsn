#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone redraw of the random dropout figure (Fig.7) with clearer legend/title separation.
Uses results/dynamic_dropout_compare.json and overwrites results/plots/paper_dynamic_dropout_compare.pdf/.svg
"""
import json
import os
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Prefer r8 file, fallback to older versions
DATA_CANDIDATES = [
    PROJECT_ROOT / "results" / "dynamic_dropout_compare_r8.json",
    PROJECT_ROOT / "results" / "dynamic_dropout_compare_reps.json",
    PROJECT_ROOT / "results" / "dynamic_dropout_compare.json",
]
OUT_DIR = PROJECT_ROOT / "results" / "plots"
OUT_PDF = OUT_DIR / "paper_dynamic_dropout_compare.pdf"
OUT_SVG = OUT_DIR / "paper_dynamic_dropout_compare.svg"

# Palette consistent with other dynamic figures
PALETTE = [
    "#1b9e77",  # LEACH
    "#d95f02",  # HEED
    "#7570b3",  # PEGASIS
    "#e7298a",  # TEEN
    "#66a61e",  # AERIS_energy
    "#e6ab02",  # AERIS_robust
]
PROTOCOL_ORDER = ["LEACH", "HEED", "PEGASIS", "TEEN", "AERIS-E", "AERIS-R"]
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
MARKERS = {
    "LEACH": "o",
    "HEED": "s",
    "PEGASIS": "D",
    "TEEN": "^",
    "AERIS-E": "v",
    "AERIS-R": "P",
    "AERIS_energy": "v",
    "AERIS_robust": "P",
}
# 线型帮助区分重叠的高 PDR 曲线
LINESTYLES = {
    "LEACH": "-",
    "HEED": "--",
    "PEGASIS": "-.",
    "TEEN": ":",
    "AERIS-E": "-",
    "AERIS-R": "-",
    "AERIS_energy": "-",
    "AERIS_robust": "-",
}


def load_data() -> Dict:
    """Load JSON and aggregate across replicates if present."""
    # Find first available data file
    data_path = None
    for candidate in DATA_CANDIDATES:
        if candidate.exists():
            data_path = candidate
            break
    if data_path is None:
        raise FileNotFoundError(f"No data file found among {DATA_CANDIDATES}")

    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    rep_keys = [k for k in raw.keys() if k.startswith("rep_")]
    if not rep_keys:
        return raw

    # Aggregate mean across replicates for each phase/protocol.
    agg: Dict[str, Dict[str, Dict[str, List[float]]]] = {}
    for rep in rep_keys:
        phases = raw[rep]
        for ph, results in phases.items():
            agg.setdefault(ph, {})
            for proto, metrics in results.items():
                agg[ph].setdefault(proto, {"pdr": [], "energy": []})
                pdr_val = metrics.get("packet_delivery_ratio_end2end", metrics.get("packet_delivery_ratio"))
                energy_val = metrics.get("total_energy_consumed")
                agg[ph][proto]["pdr"].append(0.0 if pdr_val is None else pdr_val)
                agg[ph][proto]["energy"].append(0.0 if energy_val is None else energy_val)

    averaged: Dict[str, Dict[str, Dict[str, float]]] = {}
    for ph, protos in agg.items():
        averaged[ph] = {}
        for proto, vals in protos.items():
            pdr_list = vals["pdr"]
            energy_list = vals["energy"]
            averaged[ph][proto] = {
                "packet_delivery_ratio_end2end": float(np.mean(pdr_list)) if pdr_list else 0.0,
                "total_energy_consumed": float(np.mean(energy_list)) if energy_list else 0.0,
            }
    return averaged


def main():
    data = load_data()
    phases = ["drop0", "drop10", "drop20", "drop30"]
    phase_labels = ["Drop 0%", "Drop 10%", "Drop 20%", "Drop 30%"]
    x = np.arange(len(phases))

    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10.5,
        "axes.grid": True,
        "grid.alpha": 0.28,
        "grid.linestyle": "--",
        "axes.spines.top": True,
        "axes.spines.right": True,
        "legend.frameon": False,
        "axes.linewidth": 0.9,
    })

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.0), sharex=True, gridspec_kw={"hspace": 0.04})

    min_pdr = 1.0
    max_pdr = 0.0
    for idx, proto in enumerate(PROTOCOL_ORDER):
        color = PALETTE[idx % len(PALETTE)]
        marker = MARKERS.get(proto, "o")

        pdr = []
        energy = []
        for ph in phases:
            node = data.get(ph, {}).get(proto, {})
            val = node.get("packet_delivery_ratio_end2end", node.get("packet_delivery_ratio"))
            # 如果缺失，用 0 代替以保证线条长度一致
            pdr.append(0.0 if val is None else val)
            energy.append(0.0 if node.get("total_energy_consumed") is None else node.get("total_energy_consumed"))
        # track ylim
        pdr_clean = [v for v in pdr if v is not None]
        if pdr_clean:
            min_pdr = min(min_pdr, min(pdr_clean))
            max_pdr = max(max_pdr, max(pdr_clean))

        axes[0].plot(
            x,
            pdr,
            marker=marker,
            color=color,
            linewidth=1.1,
            markersize=5.5,
            linestyle=LINESTYLES.get(proto, "-"),
            markeredgecolor="white",
            markeredgewidth=0.8,
            label=DISPLAY.get(proto, proto),
        )
        axes[1].plot(
            x,
            energy,
            marker=marker,
            color=color,
            linewidth=1.1,
            markersize=5.5,
            linestyle=LINESTYLES.get(proto, "-"),
            markeredgecolor="white",
            markeredgewidth=0.8,
        )

    axes[0].set_ylabel("End-to-End PDR")
    axes[1].set_ylabel("Total Energy (J)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(phase_labels)
    bottom = max(0.0, min_pdr - 0.05)
    top = min(1.05, max_pdr + 0.02)
    axes[0].set_ylim(bottom, top)
    axes[1].set_ylim(bottom=0)

    fig.legend(
        loc="upper center",
        ncol=3,
        fontsize=10,
        bbox_to_anchor=(0.5, 1.01),
        columnspacing=1.6,
        handlelength=2.0,
    )
    fig.suptitle("Random Dropout Stress Test (120→84 nodes)", fontsize=11.8, fontweight="bold", y=0.92)
    fig.tight_layout(rect=[0, 0.04, 1, 0.82])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PDF, bbox_inches="tight")
    fig.savefig(OUT_SVG, bbox_inches="tight")
    print(f"[SAVED] {OUT_PDF}")


if __name__ == "__main__":
    main()
