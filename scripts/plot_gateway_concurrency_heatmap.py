#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heatmap-style summary for gateway concurrency + adaptive load limit sweeps.

Rows: scenarios (Uniform-300 dual BS, Uniform-500 dual BS)
Columns: concurrency configurations (labels provided via CLI)
Color: best end-to-end PDR from each JSON
Annotation: CH->BS PDR / avg L_gw / frac(L_gw=1)
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Palatino", "Times New Roman", "Times"],
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def parse_label_path(items: List[str]) -> List[Tuple[str, Path]]:
    pairs: List[Tuple[str, Path]] = []
    for item in items:
        if ":" not in item:
            raise ValueError(f"Expected label:path, got '{item}'")
        label, fp = item.split(":", 1)
        path = Path(fp.strip()).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        pairs.append((label.strip(), path))
    return pairs


def summarize(path: Path) -> Dict[str, float]:
    data = json.load(path.open("r", encoding="utf-8"))
    best_key = None
    best_pdr = -1.0
    for key, entry in data.items():
        pdr = entry.get("stats", {}).get("pdr_end2end", {}).get("mean")
        if pdr is None:
            continue
        if pdr > best_pdr:
            best_pdr = float(pdr)
            best_key = key
    if best_key is None:
        raise RuntimeError(f"No valid entries in {path}")
    entry = data[best_key]
    runs = entry["runs"]

    def avg(field: str) -> float:
        vals = [r.get(field) for r in runs if r.get(field) is not None]
        return float(sum(vals) / len(vals)) if vals else 0.0

    def avg_trace(func) -> float:
        vals = []
        for r in runs:
            tr = r.get("gateway_limit_trace")
            if tr:
                vals.append(func(tr))
        return float(sum(vals) / len(vals)) if vals else 0.0

    def frac_one(trace):
        return sum(1 for v in trace if v <= 1) / len(trace) if trace else 0.0

    return {
        "pdr_e2e": float(entry["stats"]["pdr_end2end"]["mean"]),
        "ch_bs": float(entry["stats"]["ch_to_bs_pdr"]["mean"]),
        "avg_limit": avg_trace(lambda t: sum(t) / len(t)),
        "frac_one": avg_trace(frac_one),
    }


def main():
    parser = argparse.ArgumentParser(description="Gateway concurrency heatmap summary.")
    parser.add_argument(
        "--uniform300",
        nargs="+",
        default=[
            "conc2:results/gateway_sweep_uniform300_dualbs_concurrency2.json",
            "conc4:results/gateway_sweep_uniform300_dualbs_concurrency4.json",
            "relaxed:results/gateway_sweep_uniform300_dualbs_conc4_relaxed.json",
        ],
        help="label:path pairs for Uniform-300 dual-BS concurrency sweeps",
    )
    parser.add_argument(
        "--uniform500",
        nargs="+",
        default=[
            "conc2:results/gateway_sweep_uniform500_dualbs_concurrency2.json",
            "conc4:results/gateway_sweep_uniform500_dualbs_concurrency4.json",
            "relaxed:results/gateway_sweep_uniform500_dualbs_conc4_relaxed.json",
        ],
        help="label:path pairs for Uniform-500 dual-BS concurrency sweeps",
    )
    parser.add_argument(
        "--output-pdf",
        type=str,
        default="results/plots/paper_gateway_concurrency_heatmap.pdf",
    )
    parser.add_argument(
        "--output-svg",
        type=str,
        default="results/plots/paper_gateway_concurrency_heatmap.svg",
    )
    args = parser.parse_args()

    scenarios = [("Uniform-300", parse_label_path(args.uniform300)), ("Uniform-500", parse_label_path(args.uniform500))]
    labels = [lp[0] for lp in scenarios[0][1]]

    data_matrix = np.zeros((len(scenarios), len(labels)))
    ann_matrix = np.empty((len(scenarios), len(labels)), dtype=object)

    for i, (sc_name, case_list) in enumerate(scenarios):
        for j, (label, path) in enumerate(case_list):
            summary = summarize(path)
            data_matrix[i, j] = summary["pdr_e2e"]
            ann_matrix[i, j] = (
                f"PDR {summary['pdr_e2e']:.3f}\n"
                f"CH→BS {summary['ch_bs']:.3f}\n"
                f"avg $L_{{gw}}$ {summary['avg_limit']:.2f}\n"
                f"$L=1$ {summary['frac_one']:.2f}"
            )

    fig, ax = plt.subplots(figsize=(9, 3.5))
    sns.heatmap(
        data_matrix,
        annot=ann_matrix,
        fmt="",
        cmap="YlGnBu",
        cbar_kws={"label": "Best $\\mathrm{PDR}_{e2e}$"},
        xticklabels=labels,
        yticklabels=[s[0] for s in scenarios],
        ax=ax,
        linewidths=0.5,
        linecolor="white",
    )
    ax.set_xlabel("Concurrency config (label)")
    ax.set_ylabel("Scenario")
    ax.set_title("Gateway concurrency + adaptive limit summary (dual BS)")
    fig.tight_layout()
    out_pdf = Path(args.output_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(Path(args.output_svg), bbox_inches="tight")
    print(f"[DONE] Saved heatmap to {out_pdf}")


if __name__ == "__main__":
    main()
