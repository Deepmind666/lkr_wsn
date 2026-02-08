#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compute round-level Welch t-tests between AERIS energy and robust profiles
for dynamic scenarios (corridor, moving BS, dropout).
Outputs markdown summary under results/for_submission/aeris_round_significance.md
"""

import json
import math
import os
from statistics import mean, pstdev
from typing import Dict, List

try:
    from scipy import stats  # type: ignore
    SCIPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SCIPY_AVAILABLE = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
OUTPUT_DIR = os.path.join(RESULTS_DIR, "for_submission")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "aeris_round_significance.md")

SCENARIOS: Dict[str, List[str]] = {
    "Corridor (phase shifts)": [
        "dynamic_corridor_compare_r8.json",
        "dynamic_corridor_compare_reps.json",
        "dynamic_corridor_compare.json",
    ],
    "Moving BS corridor": [
        "dynamic_moving_bs_compare_r8.json",
        "dynamic_moving_bs_compare_reps.json",
        "dynamic_moving_bs_compare.json",
    ],
    "Random dropout": [
        "dynamic_dropout_compare_r8.json",
        "dynamic_dropout_compare_reps.json",
        "dynamic_dropout_compare.json",
    ],
}


def round_pdr(entry: Dict) -> List[float]:
    stats_list = entry.get("round_statistics", [])
    samples: List[float] = []
    for record in stats_list:
        src = record.get("source_packets_round")
        delivered = record.get("bs_delivered_round")
        if not src:
            continue
        samples.append(delivered / src)
    return samples


def welch(x: List[float], y: List[float]):
    n1, n2 = len(x), len(y)
    if n1 < 2 or n2 < 2:
        return float("nan"), float("nan"), float("nan"), float("nan"), float("nan"), float("nan")
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
        p_val = float("nan")
    cohen_d = (m2 - m1) / math.sqrt((var1 + var2) / 2) if (var1 + var2) else float("nan")
    return m1, s1, m2, s2, t_value, dof, p_val, cohen_d


def fmt(value: float) -> str:
    if math.isnan(value):
        return "n/a"
    if abs(value) < 1e-3:
        return "{:.2e}".format(value)
    return "{:.3f}".format(value)


def load_data(paths: List[str]) -> Dict:
    for rel_path in paths:
        full_path = os.path.join(RESULTS_DIR, rel_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    raise FileNotFoundError(f"None of {paths} exist")


def iter_phase_dicts(data: Dict) -> List[Dict]:
    keys = list(data.keys())
    if keys and all(isinstance(k, str) and k.startswith("rep_") for k in keys):
        return [data[k] for k in keys]
    return [data]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    blocks: List[str] = []

    for label, path_list in SCENARIOS.items():
        data = load_data(path_list)
        energy_samples: List[float] = []
        robust_samples: List[float] = []
        for phase_dict in iter_phase_dicts(data):
            for phase in phase_dict:
                # Support both old (AERIS_energy/AERIS_robust) and new (AERIS-E/AERIS-R) naming
                energy_entry = phase_dict[phase].get("AERIS-E") or phase_dict[phase].get("AERIS_energy")
                robust_entry = phase_dict[phase].get("AERIS-R") or phase_dict[phase].get("AERIS_robust")
                if energy_entry:
                    energy_samples.extend(round_pdr(energy_entry))
                if robust_entry:
                    robust_samples.extend(round_pdr(robust_entry))
        m1, s1, m2, s2, t_value, dof, p_val, cohen_d = welch(energy_samples, robust_samples)
        block = [
            f"### {label}",
            f"- Energy profile mean ± std: {fmt(m1)} ± {fmt(s1)}",
            f"- Robust profile mean ± std: {fmt(m2)} ± {fmt(s2)}",
            f"- Welch $t$ = {fmt(t_value)}, dof = {fmt(dof)}, $p$ = {fmt(p_val)}, Cohen's $d$ = {fmt(cohen_d)}",
            "",
        ]
        blocks.append("\n".join(block))

    content = "\n".join(blocks)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(content)
    print(f"[SAVED] Round-level significance written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
