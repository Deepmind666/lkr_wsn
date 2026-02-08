#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import numpy as np
import matplotlib.pyplot as plt

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "results", "large_scale_long.json")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "plots")
SENSORS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "Sensors_figures")
OUT_NAME_SVG = "paper_large_scale_long.svg"
OUT_NAME_PDF = "paper_large_scale_long.pdf"

plt.rcParams.update(
    {
        "font.size": 11,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "legend.fontsize": 10,
        "figure.dpi": 300,
    }
)

PALETTE = {
    "LEACH": "#0b8a8f",
    "HEED": "#d2691e",
    "PEGASIS": "#6c5ce7",
    "TEEN": "#ff4fa3",
    "AERIS_energy": "#f5b900",
    "AERIS_robust": "#0077cc",
}

PROTOS = ["LEACH", "HEED", "PEGASIS", "TEEN", "AERIS_energy", "AERIS_robust"]


def mean_pdr(entries):
    if isinstance(entries, dict):
        entries = [entries]
    vals = []
    for e in entries:
        vals.append(e.get("packet_delivery_ratio_end2end", e.get("packet_delivery_ratio", 0.0)))
    return float(np.mean(vals))


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    setups = sorted(data.keys())
    x = np.arange(len(setups))
    width = 0.12

    fig, ax = plt.subplots(figsize=(7.2, 3.8))

    for idx, proto in enumerate(PROTOS):
        offsets = (idx - (len(PROTOS) - 1) / 2) * width
        pdr_vals = [mean_pdr(data[s][proto]) for s in setups]
        ax.bar(x + offsets, pdr_vals, width=width, label=proto.replace("_", " "), color=PALETTE.get(proto))

    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", " ") for s in setups])
    ax.set_ylabel("End-to-end PDR")
    ax.set_ylim(0.9, 1.02)
    ax.set_title("300/500-node, 1000-round simulations")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.18), loc="center")
    fig.tight_layout()

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path_svg = os.path.join(OUT_DIR, OUT_NAME_SVG)
    out_path_pdf = os.path.join(OUT_DIR, OUT_NAME_PDF)
    fig.savefig(out_path_svg, bbox_inches="tight")
    fig.savefig(out_path_pdf, bbox_inches="tight")
    os.makedirs(SENSORS_DIR, exist_ok=True)
    fig.savefig(os.path.join(SENSORS_DIR, OUT_NAME_SVG), bbox_inches="tight")
    fig.savefig(os.path.join(SENSORS_DIR, OUT_NAME_PDF), bbox_inches="tight")
    print(f"[DONE] Saved large-scale plot to {out_path_svg} and {out_path_pdf}")


if __name__ == "__main__":
    main()
