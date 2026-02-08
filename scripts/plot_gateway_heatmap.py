#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot heatmaps for gateway sweep results (e2e PDR, CH->BS PDR, gateway->BS PDR, etc.).
"""

import argparse
import json
import os
from typing import Dict, List, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

mpl.rcParams.update(
    {
        "font.family": "Palatino Linotype",
        "font.size": 11,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)

METRIC_LABELS = {
    "pdr_end2end": "End-to-end PDR",
    "ch_to_bs_pdr": "CH→BS PDR",
    "gateway_uplink_pdr": "Gateway→BS PDR",
    "energy": "Energy (J)",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Plot gateway sweep heatmaps.")
    parser.add_argument("--input", required=True, help="Path to gateway_sweep JSON.")
    parser.add_argument(
        "--metrics",
        default="pdr_end2end,ch_to_bs_pdr,gateway_uplink_pdr",
        help="Comma-separated list of metrics to plot.",
    )
    parser.add_argument("--output-prefix", default=None, help="Prefix for output files.")
    return parser.parse_args()


def load_data(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def parse_key(key: str) -> Tuple[int, float]:
    # keys look like k2_wd-0.5
    parts = key.split("_")
    k = int(parts[0].replace("k", ""))
    wd = float(parts[1].replace("wd", ""))
    return k, wd


def build_matrix(data: Dict, metric: str):
    counts = sorted({parse_key(key)[0] for key in data})
    wds = sorted({parse_key(key)[1] for key in data})
    matrix = np.full((len(wds), len(counts)), np.nan)
    for key, entry in data.items():
        k, wd = parse_key(key)
        stats = entry["stats"].get(metric)
        if not stats:
            continue
        value = stats.get("mean")
        if value is None:
            continue
        i = wds.index(wd)
        j = counts.index(k)
        matrix[i, j] = value
    return counts, wds, matrix


def plot_heatmaps(data: Dict, metrics: List[str], output_prefix: str):
    out_dir = os.path.dirname(output_prefix)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    for metric in metrics:
        counts, wds, matrix = build_matrix(data, metric)
        fig, ax = plt.subplots(figsize=(6, 4))
        im = ax.imshow(matrix, aspect="auto", origin="lower", cmap="viridis")
        ax.set_xticks(np.arange(len(counts)))
        ax.set_yticks(np.arange(len(wds)))
        ax.set_xticklabels(counts)
        ax.set_yticklabels(wds)
        ax.set_xlabel("Number of gateways (k)")
        ax.set_ylabel("Distance weight $w_{dist}$")
        ax.set_title(METRIC_LABELS.get(metric, metric))
        for i in range(len(wds)):
            for j in range(len(counts)):
                val = matrix[i, j]
                if np.isnan(val):
                    continue
                ax.text(j, i, f"{val:.3f}", ha="center", va="center", color="white" if val > np.nanmax(matrix) / 2 else "black", fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        fname_pdf = f"{output_prefix}_{metric}.pdf"
        fname_svg = f"{output_prefix}_{metric}.svg"
        fig.savefig(fname_pdf, bbox_inches="tight")
        fig.savefig(fname_svg, bbox_inches="tight")
        plt.close(fig)
        print(f"[PLOT] Saved {fname_pdf}")


if __name__ == "__main__":
    args = parse_args()
    data = load_data(args.input)
    metrics = [m.strip() for m in args.metrics.split(",") if m.strip()]
    if args.output_prefix:
        output_prefix = args.output_prefix
    else:
        output_prefix = os.path.join("results", "plots", os.path.splitext(os.path.basename(args.input))[0])
    plot_heatmaps(data, metrics, output_prefix)
