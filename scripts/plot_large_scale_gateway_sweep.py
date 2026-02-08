#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot: Large-scale multi-gateway PDR (AERIS robust)
Inputs: results/large_scale_long_gateway_sweep_n10_300.json, n10_500.json, n2_1000.json, n1_2000.json
Outputs: results/plots/paper_large_scale_gateway_sweep.(pdf|svg)
"""
import json, os, statistics
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

FILES = [
    ("300 nodes", "800 rounds", "results/large_scale_long_gateway_sweep_n10_300.json"),
    ("500 nodes", "800 rounds", "results/large_scale_long_gateway_sweep_n10_500.json"),
    ("1000 nodes", "500 rounds", "results/large_scale_long_gateway_sweep_n5_1000.json"),
    ("2000 nodes", "400 rounds", "results/large_scale_long_gateway_sweep_n3_2000.json"),
]

LABELS = {"cluster_ch": "Cluster→CH", "ch_bs": "CH→BS", "e2e": "End-to-End"}
COLORS = {"cluster_ch": "#55A868", "ch_bs": "#F5A524", "e2e": "#4C8EDA"}


def load_stats(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pdr = []
    chbs = []
    cluster = []
    for v in data.values():
        p = v.get("packet_delivery_ratio_end2end", v.get("packet_delivery_ratio"))
        am = v.get("additional_metrics", {})
        pdr.append(p)
        chbs.append(am.get("ch_to_bs_pdr_total"))
        cluster.append(am.get("cluster_to_ch_pdr_total"))

    def summary(arr):
        return statistics.mean(arr), min(arr), max(arr)

    return {
        "n": len(pdr),
        "e2e": summary(pdr),
        "ch_bs": summary(chbs),
        "cluster_ch": summary(cluster),
    }


def main():
    stats = []
    for label, rounds, path in FILES:
        st = load_stats(path)
        ntext = f"n={st['n']}"
        stats.append((label, rounds, ntext, st))
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    bar_width = 0.22
    order = ["cluster_ch", "ch_bs", "e2e"]

    for i, (label, rounds, ntext, st) in enumerate(stats):
        for j, key in enumerate(order):
            mean, mn, mx = st[key]
            xpos = i + (j - 1) * bar_width
            ax.bar(xpos, mean, width=bar_width * 0.9, color=COLORS[key], label=LABELS[key] if i == 0 else None, zorder=3)
            if st["n"] > 1:
                yneg = mean - mn
                ypos = mx - mean
                min_err = 0.003
                yneg = max(yneg, min_err)
                ypos = max(ypos, min_err)
                ax.errorbar(
                    xpos,
                    mean,
                    yerr=[[yneg], [ypos]],
                    fmt="none",
                    ecolor="#333333",
                    elinewidth=0.9,
                    capsize=3.5,
                    zorder=4,
                )
            ax.text(xpos, mean + 0.012, f"{mean:.3f}", ha="center", va="bottom", fontsize=7, color="#222222")

    ax.set_xticks(range(len(stats)))
    ax.set_xticklabels([f"{label}\n({rounds}, {ntext})" for label, rounds, ntext, _ in stats])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Packet Delivery Ratio")
    ax.set_title("Large-scale multi-gateway (AERIS robust)")
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.6, zorder=0)
    ax.legend(frameon=False, ncol=3, loc="upper right")
    plt.tight_layout()

    out_dir = os.path.join("results", "plots")
    os.makedirs(out_dir, exist_ok=True)
    fig.savefig(os.path.join(out_dir, "paper_large_scale_gateway_sweep.pdf"), bbox_inches="tight", dpi=300)
    fig.savefig(os.path.join(out_dir, "paper_large_scale_gateway_sweep.svg"), bbox_inches="tight", dpi=300)
    print(f"[DONE] wrote {out_dir}/paper_large_scale_gateway_sweep.pdf")


if __name__ == "__main__":
    main()
