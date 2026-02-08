#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compute Welch's t-test and descriptive statistics for the Monte Carlo study
stored in results/monte_carlo_uniform50.json.
Outputs markdown table under results/for_submission/monte_carlo_stats.md.
"""

import json
import math
import os
from statistics import mean, pstdev

try:
    from scipy import stats  # type: ignore
    SCIPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SCIPY_AVAILABLE = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
OUTPUT_DIR = os.path.join(RESULTS_DIR, "for_submission")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "monte_carlo_stats.md")

DATA_PATH = os.path.join(RESULTS_DIR, "monte_carlo_uniform50.json")


def load_runs():
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    runs = data["runs"]
    energy = [entry["pdr_end2end"] for entry in runs["energy"]]
    robust = [entry["pdr_end2end"] for entry in runs["robust"]]
    return energy, robust


def welch_stats(x, y):
    n1, n2 = len(x), len(y)
    mean1, mean2 = mean(x), mean(y)
    std1 = pstdev(x)
    std2 = pstdev(y)
    var1 = std1 ** 2
    var2 = std2 ** 2
    t_num = mean2 - mean1
    t_den = math.sqrt(var1 / n1 + var2 / n2)
    t_value = t_num / t_den if t_den else float("nan")
    df_num = (var1 / n1 + var2 / n2) ** 2
    df_den = ((var1 / n1) ** 2) / (n1 - 1) + ((var2 / n2) ** 2) / (n2 - 1)
    dof = df_num / df_den if df_den else float("nan")
    p_value = float("nan")
    if SCIPY_AVAILABLE and not math.isnan(t_value) and not math.isnan(dof):
        p_value = stats.t.sf(abs(t_value), dof) * 2
    cohen_d = (mean2 - mean1) / math.sqrt((var1 + var2) / 2) if (var1 + var2) else float("nan")
    return {
        "mean_energy": mean1,
        "std_energy": std1,
        "mean_robust": mean2,
        "std_robust": std2,
        "t_value": t_value,
        "p_value": p_value,
        "dof": dof,
        "cohen_d": cohen_d,
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    energy, robust = load_runs()
    stats_dict = welch_stats(energy, robust)
    lines = [
        "### Monte Carlo Welch t-test (50×100, 100 seeds)",
        "| Metric | Energy profile | Robust profile |",
        "| --- | --- | --- |",
        f"| Mean $\\mathrm{{PDR}}_{{e2e}}$ | {stats_dict['mean_energy']:.3f} ± {stats_dict['std_energy']:.3f} | "
        f"{stats_dict['mean_robust']:.3f} ± {stats_dict['std_robust']:.3f} |",
        "",
        "| Statistic | Value |",
        "| --- | --- |",
        f"| Welch $t$ | {stats_dict['t_value']:.3f} |",
        f"| dof | {stats_dict['dof']:.1f} |",
        f"| two-sided $p$ | {'{:.3e}'.format(stats_dict['p_value']) if not math.isnan(stats_dict['p_value']) else 'n/a'} |",
        f"| Cohen's $d$ | {stats_dict['cohen_d']:.3f} |",
        "",
    ]
    content = "\n".join(lines)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(content)
    print(f"[SAVED] Monte Carlo stats written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
