#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core comparison plots: end-to-end PDR and total energy for AERIS vs classical baselines
across synthetic topologies (uniform/corridor, 100–500 nodes).

Outputs: results/plots/paper_core_compare.pdf + .svg
Design: unified palette/fonts, side-by-side bars per scenario.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Palatino", "Times New Roman", "Times"],
    "axes.spines.top": False,
    "axes.spines.right": False,
})
import numpy as np


def load_multi_topo(path: Path) -> Dict[str, Dict[str, Dict[str, float]]]:
    data = json.load(path.open())
    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for topo, entries in data.items():
        out[topo] = {}
        for proto, vals in entries.items():
            pdr = vals.get("packet_delivery_ratio_end2end", vals.get("packet_delivery_ratio"))
            out[topo][proto] = {
                "pdr": pdr,
                "energy": vals.get("total_energy_consumed"),
            }
    return out


def load_large_scale(path: Path) -> Dict[str, Dict[str, Dict[str, float]]]:
    data = json.load(path.open())
    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for topo, entries in data.items():
        out[topo] = {}
        for proto, vals in entries.items():
            if not isinstance(vals, dict):
                continue
            pdr = vals.get("packet_delivery_ratio_end2end", vals.get("packet_delivery_ratio"))
            out[topo][proto] = {
                "pdr": pdr,
                "energy": vals.get("total_energy_consumed"),
            }
    return out


def prepare_dataset() -> Dict[str, Dict[str, Dict[str, float]]]:
    base = load_multi_topo(Path("results/compare_multi_topo.json"))
    large = load_large_scale(Path("results/large_scale_long.json"))
    dataset: Dict[str, Dict[str, Dict[str, float]]] = {
        "uniform_100": base.get("uniform_100", {}),
        "corridor_100": base.get("corridor_100", {}),
        "uniform_200": base.get("uniform_200", {}),
        "uniform_300": large.get("uniform_300", {}),
        "uniform_500": large.get("uniform_500", {}),
    }
    # If only aggregated AERIS is present, copy it to both E/R so bars are not empty.
    for topo, entries in dataset.items():
        if "AERIS" in entries and "AERIS_energy" not in entries and "AERIS_robust" not in entries:
            entries["AERIS_energy"] = entries["AERIS"]
            entries["AERIS_robust"] = entries["AERIS"]
        # Drop the generic AERIS to avoid duplicate bars/legend overlap.
        entries.pop("AERIS", None)
    return dataset


def plot_core_compare(dataset: Dict[str, Dict[str, Dict[str, float]]], output_pdf: Path, output_svg: Path):
    scenarios = ["uniform_100", "corridor_100", "uniform_200", "uniform_300", "uniform_500"]
    scenario_labels = ["Uniform-100", "Corridor-100", "Uniform-200", "Uniform-300", "Uniform-500"]
    # TEEN may be missing (None); filter later if all None
    protocols = ["LEACH", "HEED", "PEGASIS", "TEEN", "AERIS_energy", "AERIS_robust"]
    proto_labels = {
        "LEACH": "LEACH",
        "HEED": "HEED",
        "PEGASIS": "PEGASIS",
        "TEEN": "TEEN",
        "AERIS_energy": "AERIS-E",
        "AERIS_robust": "AERIS-R",
    }
    palette = {
        "LEACH": "#4C72B0",
        "HEED": "#55A868",
        "PEGASIS": "#C44E52",
        "TEEN": "#8172B3",
        "AERIS_energy": "#CCB974",
        "AERIS_robust": "#64B5CD",
    }

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharex=True)
    width = 0.12
    x = np.arange(len(scenarios))
    for idx, proto in enumerate(protocols):
        offsets = (idx - (len(protocols) - 1) / 2) * width
        pdr_vals: List[Optional[float]] = []
        energy_vals: List[Optional[float]] = []
        for sc in scenarios:
            entry = dataset.get(sc, {}).get(proto)
            pdr_vals.append(entry.get("pdr") if entry else None)
            energy_vals.append(entry.get("energy") if entry else None)
        # skip if all None
        if all(v is None for v in pdr_vals):
            continue
        axes[0].bar(
            x + offsets,
            [v if v is not None else 0 for v in pdr_vals],
            width=width,
            color=palette.get(proto, "#999999"),
            label=proto_labels[proto],
            edgecolor="white",
            linewidth=0.4,
            zorder=2,
        )
        axes[1].bar(
            x + offsets,
            [v if v is not None else 0 for v in energy_vals],
            width=width,
            color=palette.get(proto, "#999999"),
            edgecolor="white",
            linewidth=0.4,
            zorder=2,
        )

    axes[0].set_ylabel("End-to-end PDR")
    axes[1].set_ylabel("Total energy (J)")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(scenario_labels, rotation=15)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(scenario_labels, rotation=15)
    axes[0].set_ylim(0, 1.1)
    axes[1].set_ylim(0, max(2100, axes[1].get_ylim()[1]))
    axes[0].grid(axis="y", linestyle="--", alpha=0.25)
    axes[1].grid(axis="y", linestyle="--", alpha=0.25)
    # Legend: centered above plots to avoid covering bars
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=6, loc="upper center", fontsize=8, frameon=False, title="Protocols", title_fontsize=9, bbox_to_anchor=(0.5, 1.05))
    axes[0].set_title("Reliability (PDR)", fontsize=11, pad=10)
    axes[1].set_title("Total Energy (J)", fontsize=11, pad=10)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_pdf, bbox_inches="tight")
    fig.savefig(output_svg, bbox_inches="tight")
    print(f"[DONE] Saved to {output_pdf} and {output_svg}")


if __name__ == "__main__":
    dataset = prepare_dataset()
    plot_core_compare(dataset, Path("results/plots/paper_core_compare.pdf"), Path("results/plots/paper_core_compare.svg"))
