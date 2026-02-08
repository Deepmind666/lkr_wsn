#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot gateway load-limit effects for dual-BS experiments."""
import argparse
import json
import os
from typing import Dict, Tuple, List

import matplotlib as mpl
mpl.rcParams.update(
    {
        "font.family": "Palatino Linotype",
        "font.size": 11,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
SENSORS_DIR = os.path.join(RESULTS_DIR, "Sensors_figures")


def parse_args():
    parser = argparse.ArgumentParser(description="Plot gateway limit sweep results")
    parser.add_argument("--limits", type=str, default="1,2,3,4", help="Comma-separated list of limits")
    parser.add_argument(
        "--dataset",
        action="append",
        metavar="LABEL=PATH_TEMPLATE",
        help="Dataset definition, e.g., 'Uniform-300=results/..._limit{}.json'",
    )
    parser.add_argument("--output", type=str, default="paper_gateway_limit_effect.pdf")
    return parser.parse_args()


def load_best_metrics(path: str) -> Tuple[float, float]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    best = None
    for _, entry in data.items():
        stats = entry.get("stats", {})
        ch = stats.get("ch_to_bs_pdr", {}).get("mean")
        e2e = stats.get("pdr_end2end", {}).get("mean")
        if ch is None or e2e is None:
            continue
        if best is None or e2e > best[1]:
            best = (ch, e2e)
    if best is None:
        return float("nan"), float("nan")
    return best


def main():
    args = parse_args()
    limits = [int(x.strip()) for x in args.limits.split(",") if x.strip()]
    datasets = args.dataset or []
    if not datasets:
        raise SystemExit("At least one --dataset must be provided")
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(SENSORS_DIR, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    for ds in datasets:
        if "=" not in ds:
            raise SystemExit(f"Invalid dataset format: {ds}")
        label, template = ds.split("=", 1)
        e2e_values: List[float] = []
        ch_values: List[float] = []
        for limit in limits:
            path = template.format(limit)
            if not os.path.isabs(path):
                if path.startswith("results"):
                    path = os.path.join(PROJECT_ROOT, path)
                else:
                    path = os.path.join(PROJECT_ROOT, path)
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            ch, e2e = load_best_metrics(path)
            ch_values.append(ch)
            e2e_values.append(e2e)
        ax.plot(limits, e2e_values, marker="o", linewidth=2.0, label=f"{label} (e2e)")
    ax.set_xlabel("Gateway load limit ($L_{gw}$)")
    ax.set_ylabel(r"Best $\mathrm{PDR}_{e2e}$")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.set_xticks(limits)
    ax.set_ylim(0, max(ax.get_ylim()[1], 0.12))
    ax.legend(frameon=False)
    fig.tight_layout()

    out_name = args.output
    base = os.path.splitext(out_name)[0]
    for folder in (PLOTS_DIR, SENSORS_DIR):
        fig.savefig(os.path.join(folder, f"{base}.pdf"), bbox_inches="tight")
        fig.savefig(os.path.join(folder, f"{base}.svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"[PLOT] Saved gateway limit plot to {os.path.join(PLOTS_DIR, base + '.pdf')}")


if __name__ == "__main__":
    main()
