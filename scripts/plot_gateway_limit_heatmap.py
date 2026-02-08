#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Heatmap for gateway load-limit experiments."""
import argparse
import json
import os
from typing import Dict, Tuple

import matplotlib as mpl
mpl.rcParams.update(
    {
        "font.family": "Palatino Linotype",
        "font.size": 10,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
SENSORS_DIR = os.path.join(RESULTS_DIR, "Sensors_figures")


def parse_args():
    parser = argparse.ArgumentParser(description="Gateway limit heatmap")
    parser.add_argument("--limits", type=str, default="1,2,3,4", help="Comma-separated limits")
    parser.add_argument("--scenario", action="append", metavar="LABEL=PATTERN", help="Label=results/...limit{}.json")
    parser.add_argument("--metric", choices=["e2e", "ch"], default="e2e")
    parser.add_argument("--output", type=str, default="paper_gateway_limit_heatmap")
    return parser.parse_args()


def load_best(path: str, metric: str) -> float:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    best = None
    for entry in data.values():
        stats = entry.get("stats", {})
        if metric == "e2e":
            val = stats.get("pdr_end2end", {}).get("mean")
        else:
            val = stats.get("ch_to_bs_pdr", {}).get("mean")
        if val is None:
            continue
        if best is None or val > best:
            best = val
    return best if best is not None else float("nan")


def main():
    args = parse_args()
    limits = [int(x.strip()) for x in args.limits.split(",") if x.strip()]
    scenarios = args.scenario or []
    if not scenarios:
        raise SystemExit("At least one --scenario")
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(SENSORS_DIR, exist_ok=True)

    values = []
    labels = []
    for sc in scenarios:
        label, pattern = sc.split("=", 1)
        row = []
        for limit in limits:
            path = pattern.format(limit)
            if not os.path.isabs(path):
                path = os.path.join(PROJECT_ROOT, path)
            row.append(load_best(path, args.metric))
        values.append(row)
        labels.append(label)
    arr = np.array(values)

    fig, ax = plt.subplots(figsize=(6.4, 2.5))
    im = ax.imshow(arr, cmap="viridis", aspect="auto", vmin=0, vmax=np.nanmax(arr) * 1.05)
    ax.set_xticks(range(len(limits)))
    ax.set_xticklabels(limits)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    metric_name = "$\\mathrm{PDR}_{e2e}$" if args.metric == "e2e" else "$\\mathrm{PDR}_{\\text{CH}\\rightarrow\\text{BS}}$"
    ax.set_xlabel("Gateway load limit ($L_{gw}$)")
    ax.set_ylabel("Scenario")
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, f"{arr[i,j]:.3f}", ha="center", va="center", color="white", fontsize=9)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(f"Best {metric_name}")
    fig.tight_layout()

    base = args.output
    for folder in (PLOTS_DIR, SENSORS_DIR):
        fig.savefig(os.path.join(folder, f"{base}.pdf"), bbox_inches="tight")
        fig.savefig(os.path.join(folder, f"{base}.svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"[PLOT] Saved heatmap to {os.path.join(PLOTS_DIR, base + '.pdf')}")


if __name__ == '__main__':
    main()
