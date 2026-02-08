#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate comparative plots for rule-based vs distilled CAS evaluations.

Usage:
  python scripts/plot_distilled_summary.py \
      --inputs results/distilled_eval_nodes50.json:50 \
                results/distilled_eval_nodes80.json:80 \
                results/distilled_eval_nodes100.json:100 \
      --output results/publication_figures/distilled_cas_summary.png
"""

import argparse
import json
import os
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_summary(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["summary"]


def parse_inputs(items: List[str]) -> List[Tuple[str, str]]:
    parsed: List[Tuple[str, str]] = []
    for item in items:
        if ":" not in item:
            raise ValueError(f"Input '{item}' must be in format path:label")
        path, label = item.split(":", 1)
        parsed.append((path, label))
    return parsed


def main() -> None:
    ap = argparse.ArgumentParser(description="Plot CAS distilled evaluation summaries.")
    ap.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="List of path:label entries pointing to distilled_eval JSON files.",
    )
    ap.add_argument(
        "--output",
        type=str,
        default=os.path.join("results", "publication_figures", "distilled_cas_summary.png"),
    )
    ap.add_argument(
        "--csv-out",
        type=str,
        default=os.path.join("results", "distilled_cas_summary.csv"),
    )
    args = ap.parse_args()

    entries = parse_inputs(args.inputs)

    records = []
    for path, label in entries:
        summary = load_summary(path)
        for variant in ("baseline", "distilled"):
            rec = {
                "topology": label,
                "variant": variant,
                "pdr_end2end_mean": summary[variant]["pdr_end2end"]["mean"],
                "pdr_end2end_std": summary[variant]["pdr_end2end"]["std"],
                "energy_mean": summary[variant]["energy"]["mean"],
                "energy_std": summary[variant]["energy"]["std"],
                "lifetime_mean": summary[variant]["lifetime"]["mean"],
                "lifetime_std": summary[variant]["lifetime"]["std"],
            }
            records.append(rec)

    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    os.makedirs(os.path.dirname(args.csv_out), exist_ok=True)
    df.to_csv(args.csv_out, index=False)

    # Plot grouped bar charts for end-to-end PDR and energy consumption.
    topologies = df["topology"].unique()
    variants = ["baseline", "distilled"]
    x = np.arange(len(topologies))
    width = 0.35

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=160)

    # PDR plot
    for idx, variant in enumerate(variants):
        subset = df[df["variant"] == variant]
        means = [subset[subset["topology"] == topo]["pdr_end2end_mean"].iloc[0] for topo in topologies]
        stds = [subset[subset["topology"] == topo]["pdr_end2end_std"].iloc[0] for topo in topologies]
        axes[0].bar(x + (idx - 0.5) * width, means, width, yerr=stds, label=variant.capitalize(), capsize=4)
    axes[0].set_ylabel("End-to-End PDR")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(topologies)
    axes[0].set_ylim(0.0, 1.05)
    axes[0].grid(True, axis="y", linestyle="--", alpha=0.3)
    axes[0].set_title("CAS Mode PDR Comparison")

    # Energy plot
    for idx, variant in enumerate(variants):
        subset = df[df["variant"] == variant]
        means = [subset[subset["topology"] == topo]["energy_mean"].iloc[0] for topo in topologies]
        stds = [subset[subset["topology"] == topo]["energy_std"].iloc[0] for topo in topologies]
        axes[1].bar(x + (idx - 0.5) * width, means, width, yerr=stds, label=variant.capitalize(), capsize=4)
    axes[1].set_ylabel("Total Energy (J)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(topologies)
    axes[1].grid(True, axis="y", linestyle="--", alpha=0.3)
    axes[1].set_title("Energy Consumption Comparison")

    axes[0].legend()
    fig.tight_layout()
    fig.savefig(args.output, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
