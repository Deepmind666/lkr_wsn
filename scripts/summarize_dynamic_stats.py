#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize mean end-to-end PDR, energy, and alive nodes for dynamic scenarios.
Outputs a markdown summary under results/for_submission/dynamic_stats_summary.md
and prints the same table to stdout.
"""

import json
import os
from statistics import mean
from typing import Dict, List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
SUMMARY_DIR = os.path.join(RESULTS_DIR, "for_submission")
SUMMARY_PATH = os.path.join(SUMMARY_DIR, "dynamic_stats_summary.md")


ScenarioSpec = Tuple[List[str], str]

SCENARIOS: Dict[str, ScenarioSpec] = {
    "Corridor (shifted)": (["dynamic_corridor_compare_r8.json", "dynamic_corridor_compare_reps.json", "dynamic_corridor_compare.json"], "corridor"),
    "Moving BS corridor": (["dynamic_moving_bs_compare_r8.json", "dynamic_moving_bs_compare_reps.json", "dynamic_moving_bs_compare.json"], "moving_bs"),
    "Random dropout": (["dynamic_dropout_compare_r8.json", "dynamic_dropout_compare_reps.json", "dynamic_dropout_compare.json"], "dropout"),
}

LARGE_SCALE_FILE = os.path.join(RESULTS_DIR, "large_scale_long.json")
PROTOCOLS = [
    "LEACH",
    "HEED",
    "PEGASIS",
    "TEEN",
    "AERIS-E",
    "AERIS-R",
]
# Fallback mapping for old naming
PROTOCOL_FALLBACK = {
    "AERIS-E": "AERIS_energy",
    "AERIS-R": "AERIS_robust",
}


def load_json_from_candidates(rel_paths: List[str]) -> Dict:
    for rel_path in rel_paths:
        full_path = os.path.join(RESULTS_DIR, rel_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    raise FileNotFoundError(f"No available files among {rel_paths}")


def mean_metric(entries: List[Dict], field: str, fallback: str = None) -> float:
    values: List[float] = []
    for entry in entries:
        if field in entry:
            values.append(entry[field])
        elif fallback and fallback in entry:
            values.append(entry[fallback])
    return mean(values) if values else float("nan")


def iter_phase_dicts(data: Dict) -> List[Dict]:
    keys = list(data.keys())
    if keys and all(isinstance(k, str) and k.startswith("rep_") for k in keys):
        return [data[k] for k in keys]
    return [data]


def summarize_dynamic() -> Dict[str, Dict[str, Dict[str, float]]]:
    summary: Dict[str, Dict[str, Dict[str, float]]] = {}
    for label, (files, _) in SCENARIOS.items():
        data = load_json_from_candidates(files)
        scenario_summary: Dict[str, Dict[str, float]] = {}
        for proto in PROTOCOLS:
            entries: List[Dict] = []
            for phase_dict in iter_phase_dicts(data):
                for phase in phase_dict:
                    # Try new naming first, then fallback
                    entry = phase_dict[phase].get(proto)
                    if not entry and proto in PROTOCOL_FALLBACK:
                        entry = phase_dict[phase].get(PROTOCOL_FALLBACK[proto])
                    if entry:
                        entries.append(entry)
            if not entries:
                continue
            pdr_mean = mean_metric(entries, "packet_delivery_ratio_end2end", "packet_delivery_ratio")
            energy_mean = mean_metric(entries, "total_energy_consumed")
            alive_mean = mean_metric(entries, "final_alive_nodes")
            scenario_summary[proto] = {
                "pdr": pdr_mean,
                "energy": energy_mean,
                "alive": alive_mean,
            }
        summary[label] = scenario_summary
    return summary


def summarize_large_scale() -> Dict[str, Dict[str, Dict[str, float]]]:
    with open(LARGE_SCALE_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    summary: Dict[str, Dict[str, Dict[str, float]]] = {}
    for setup_name, setup_results in data.items():
        scenario_summary: Dict[str, Dict[str, float]] = {}
        for proto in PROTOCOLS:
            # Try new naming first, then fallback
            entry = setup_results.get(proto)
            if not entry and proto in PROTOCOL_FALLBACK:
                entry = setup_results.get(PROTOCOL_FALLBACK[proto])
            if not entry:
                continue
            pdr = entry.get("packet_delivery_ratio_end2end", entry.get("packet_delivery_ratio"))
            scenario_summary[proto] = {
                "pdr": pdr,
                "energy": entry.get("total_energy_consumed"),
                "alive": entry.get("final_alive_nodes"),
            }
        summary[f"Large-scale {setup_name}"] = scenario_summary
    return summary


def format_table_block(title: str, scenario_summary: Dict[str, Dict[str, float]]) -> str:
    header = ["Protocol", "PDR$_{e2e}$", "Energy (J)", "Alive nodes"]
    lines = [f"### {title}", "| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for proto in PROTOCOLS:
        if proto not in scenario_summary:
            continue
        entry = scenario_summary[proto]
        lines.append(
            f"| {proto.replace('_', '\\_')} | "
            f"{entry['pdr']:.3f} | "
            f"{entry['energy']:.2f} | "
            f"{entry['alive']:.1f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    os.makedirs(SUMMARY_DIR, exist_ok=True)
    blocks: List[str] = []

    dynamic_summary = summarize_dynamic()
    for label, stats_dict in dynamic_summary.items():
        blocks.append(format_table_block(label, stats_dict))

    large_summary = summarize_large_scale()
    for label, stats_dict in large_summary.items():
        blocks.append(format_table_block(label, stats_dict))

    content = "\n".join(blocks)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)

    print(content)
    print(f"[SAVED] Summary written to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
