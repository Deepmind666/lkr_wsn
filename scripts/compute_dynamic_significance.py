#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compute Welch t-tests between AERIS (energy/robust) and classical baselines
for dynamic scenarios (corridor, moving BS, dropout) using per-phase averages.
Outputs markdown tables under results/for_submission/dynamic_significance.md.
"""

import json
import math
import os
from statistics import mean, pstdev
from typing import Dict, List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
OUTPUT_DIR = os.path.join(RESULTS_DIR, "for_submission")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "dynamic_significance.md")

SCENARIOS = {
    "Corridor (phase shifts)": [
        os.path.join(RESULTS_DIR, "dynamic_corridor_compare_r8.json"),
        os.path.join(RESULTS_DIR, "dynamic_corridor_compare_reps.json"),
        os.path.join(RESULTS_DIR, "dynamic_corridor_compare.json"),
    ],
    "Moving BS corridor": [
        os.path.join(RESULTS_DIR, "dynamic_moving_bs_compare_r8.json"),
        os.path.join(RESULTS_DIR, "dynamic_moving_bs_compare_reps.json"),
        os.path.join(RESULTS_DIR, "dynamic_moving_bs_compare.json"),
    ],
    "Random dropout": [
        os.path.join(RESULTS_DIR, "dynamic_dropout_compare_r8.json"),
        os.path.join(RESULTS_DIR, "dynamic_dropout_compare_reps.json"),
        os.path.join(RESULTS_DIR, "dynamic_dropout_compare.json"),
    ],
}

BASELINES = ["LEACH", "HEED", "PEGASIS", "TEEN"]
# Support both old and new naming conventions
TARGETS = ["AERIS-E", "AERIS-R"]
TARGETS_FALLBACK = ["AERIS_energy", "AERIS_robust"]

try:
    from scipy import stats  # type: ignore
    SCIPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SCIPY_AVAILABLE = False


def load_data_from_candidates(paths: List[str]) -> Dict:
    for path in paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    raise FileNotFoundError(f"No available files among {paths}")


def iter_phase_dicts(data: Dict) -> List[Dict]:
    keys = list(data.keys())
    if keys and all(isinstance(k, str) and k.startswith("rep_") for k in keys):
        return [data[k] for k in keys]
    return [data]


def load_phase_samples(data: Dict, protocol: str) -> List[float]:
    """Load samples with fallback for old naming conventions."""
    samples = []
    # Map new names to old names for fallback
    fallback_map = {"AERIS-E": "AERIS_energy", "AERIS-R": "AERIS_robust"}
    for phase_dict in iter_phase_dicts(data):
        for phase in phase_dict:
            entry = phase_dict[phase].get(protocol)
            # Try fallback if not found
            if not entry and protocol in fallback_map:
                entry = phase_dict[phase].get(fallback_map[protocol])
            if not entry:
                continue
            samples.append(entry.get("packet_delivery_ratio_end2end", entry.get("packet_delivery_ratio", 0.0)))
    return samples


def welch_t(x: List[float], y: List[float]) -> Tuple[float, float, float, float]:
    n1, n2 = len(x), len(y)
    if n1 < 2 or n2 < 2:
        return float("nan"), float("nan"), float("nan")
    m1, m2 = mean(x), mean(y)
    s1, s2 = pstdev(x), pstdev(y)
    var1, var2 = s1 ** 2, s2 ** 2
    denom = math.sqrt(var1 / n1 + var2 / n2)
    t_value = (m2 - m1) / denom if denom else float("nan")
    df_num = (var1 / n1 + var2 / n2) ** 2
    df_den = ((var1 / n1) ** 2) / (n1 - 1) + ((var2 / n2) ** 2) / (n2 - 1)
    dof = df_num / df_den if df_den else float("nan")
    if SCIPY_AVAILABLE and not math.isnan(t_value) and not math.isnan(dof):
        p_val = stats.t.sf(abs(t_value), dof) * 2
    else:
        try:
            import mpmath  # type: ignore

            x_val = dof / (dof + t_value * t_value)
            p_val = 2 * float(mpmath.betainc(dof / 2, 0.5, 0, x_val, regularized=True))
        except Exception:
            p_val = float("nan")
    cohen_d = (m2 - m1) / math.sqrt((var1 + var2) / 2) if (var1 + var2) else float("nan")
    return t_value, dof, p_val, cohen_d


def format_float(value: float) -> str:
    if math.isnan(value):
        return "n/a"
    if abs(value) < 1e-3:
        return "{:.2e}".format(value)
    return "{:.3f}".format(value)


def adjust_holm(p_values: List[float]) -> List[float]:
    m = len(p_values)
    if m == 0:
        return []
    indexed = list(enumerate(p_values))
    indexed.sort(key=lambda kv: kv[1])
    adjusted = [0.0] * m
    for rank, (idx, p_val) in enumerate(indexed):
        adj = min(1.0, (m - rank) * p_val)
        adjusted[idx] = adj
    # ensure monotonic non-decreasing when mapped back
    for i in range(m - 2, -1, -1):
        idx_i = indexed[i][0]
        idx_next = indexed[i + 1][0]
        adjusted[idx_i] = min(adjusted[idx_i], adjusted[idx_next])
    return adjusted


def adjust_bh(p_values: List[float]) -> List[float]:
    m = len(p_values)
    if m == 0:
        return []
    indexed = list(enumerate(p_values))
    indexed.sort(key=lambda kv: kv[1])
    adjusted = [0.0] * m
    for rank, (idx, p_val) in enumerate(indexed, start=1):
        adj = min(1.0, (m / rank) * p_val)
        adjusted[idx] = adj
    for i in range(m - 2, -1, -1):
        idx_i = indexed[i][0]
        idx_next = indexed[i + 1][0]
        adjusted[idx_i] = min(adjusted[idx_i], adjusted[idx_next])
    return adjusted


def apply_pvalue_corrections(rows: List[Dict]) -> None:
    p_values = [row["p_raw"] for row in rows]
    holm = adjust_holm(p_values)
    bh = adjust_bh(p_values)
    for row, p_holm, p_bh in zip(rows, holm, bh):
        row["p_holm"] = p_holm
        row["p_bh"] = p_bh


def format_row(row: Dict) -> str:
    return (
        f"| {row['baseline']} | {row['target']} | "
        f"{format_float(row['t'])} | {format_float(row['dof'])} | "
        f"{format_float(row['p_raw'])} | {format_float(row['p_holm'])} | "
        f"{format_float(row['p_bh'])} | {format_float(row['cohen_d'])} |"
    )


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    blocks = []

    for scenario, path_list in SCENARIOS.items():
        data = load_data_from_candidates(path_list)
        scenario_lines = [
            f"### {scenario}",
            "| Baseline | Target | $t$ | dof | $p$ | $p_{\\mathrm{Holm}}$ | $p_{\\mathrm{BH}}$ | Cohen's $d$ |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        rows: List[Dict] = []
        for baseline in BASELINES:
            baseline_samples = load_phase_samples(data, baseline)
            if not baseline_samples:
                continue
            for target in TARGETS:
                target_samples = load_phase_samples(data, target)
                if not target_samples:
                    continue
                t_value, dof, p_val, cohen_d = welch_t(baseline_samples, target_samples)
                rows.append(
                    {
                        "baseline": baseline,
                        "target": target.replace("_", "\\_"),
                        "t": t_value,
                        "dof": dof,
                        "p_raw": p_val,
                        "cohen_d": cohen_d,
                    }
                )
        # AERIS energy vs robust comparison (support both naming conventions)
        energy_samples = load_phase_samples(data, "AERIS-E")
        robust_samples = load_phase_samples(data, "AERIS-R")
        if energy_samples and robust_samples:
            t_value, dof, p_val, cohen_d = welch_t(energy_samples, robust_samples)
            rows.append(
                {
                    "baseline": "AERIS-E",
                    "target": "AERIS-R",
                    "t": t_value,
                    "dof": dof,
                    "p_raw": p_val,
                    "cohen_d": cohen_d,
                }
            )

        apply_pvalue_corrections(rows)
        for row in rows:
            scenario_lines.append(format_row(row))
        scenario_lines.append(
            f"*Note:* $n=20$ samples per protocol (5 replicates $\\times$ 4 phases). Holm--Bonferroni controls family-wise error; BH controls FDR."
        )
        scenario_lines.append("")
        blocks.append("\n".join(scenario_lines))

    content = "\n".join(blocks)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(content)
    print(f"[SAVED] Dynamic significance written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
