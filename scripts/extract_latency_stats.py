#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract latency statistics from latency_<env>_<timestamp>.json files.

Outputs:
- latency_hop_stats.csv
- latency_hop_significance.csv
- latency_hop_stats.md
"""

import argparse
import csv
import glob
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy import stats


ENVS = ["indoor_office", "indoor_factory", "outdoor_urban", "outdoor_suburban"]
PROTOCOLS = ["AERIS", "LEACH", "PEGASIS", "HEED", "TEEN"]
BASELINES = ["LEACH", "PEGASIS", "HEED", "TEEN"]


def hedges_g(x: List[float], y: List[float]) -> float:
    nx = len(x)
    ny = len(y)
    if nx < 2 or ny < 2:
        return 0.0
    vx = np.var(x, ddof=1)
    vy = np.var(y, ddof=1)
    pooled = ((nx - 1) * vx + (ny - 1) * vy) / max(1, nx + ny - 2)
    if pooled <= 0:
        return 0.0
    d = (np.mean(x) - np.mean(y)) / np.sqrt(pooled)
    correction = 1.0 - (3.0 / max(1.0, 4.0 * (nx + ny) - 9.0))
    return float(d * correction)


def holm_bonferroni(p_values: List[float]) -> List[float]:
    indexed = sorted(enumerate(p_values), key=lambda t: t[1])
    m = len(p_values)
    corrected = [0.0] * m
    running_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed, start=1):
        value = (m - rank + 1) * p
        running_max = max(running_max, value)
        corrected[orig_idx] = min(1.0, running_max)
    return corrected


def _pick_latest_for_env(result_dir: Path, env: str) -> Path:
    pattern = str(result_dir / f"latency_{env}_*.json")
    files = [Path(p) for p in glob.glob(pattern)]
    if not files:
        raise FileNotFoundError(f"No latency file found for {env}: {pattern}")
    return max(files, key=lambda p: p.stat().st_mtime)


def load_runs(paths: Dict[str, Path]) -> List[Dict]:
    all_runs: List[Dict] = []
    for env, path in paths.items():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("raw_results", []):
            row = dict(item)
            row["environment"] = env
            all_runs.append(row)
    return all_runs


def group(runs: List[Dict]) -> Dict[Tuple[str, str], Dict[str, List[float]]]:
    groups: Dict[Tuple[str, str], Dict[str, List[float]]] = {}
    for r in runs:
        if r.get("error"):
            continue
        env = r.get("environment")
        proto = r.get("protocol")
        key = (env, proto)
        if key not in groups:
            groups[key] = {"hops": [], "pdr": []}
        hops = float(r.get("avg_hops_to_bs", 0.0))
        pdr = float(r.get("pdr_expected", -1.0))
        if hops > 0:
            groups[key]["hops"].append(hops)
        if pdr >= 0:
            groups[key]["pdr"].append(pdr)
    return groups


def build_rows(groups: Dict[Tuple[str, str], Dict[str, List[float]]]) -> List[Dict]:
    rows: List[Dict] = []
    for env in ENVS:
        for proto in PROTOCOLS:
            g = groups.get((env, proto))
            if not g:
                continue
            hops = g["hops"]
            pdr = g["pdr"]
            rows.append(
                {
                    "environment": env,
                    "protocol": proto,
                    "n_hops": len(hops),
                    "hops_mean": float(np.mean(hops)) if hops else 0.0,
                    "hops_std": float(np.std(hops, ddof=1)) if len(hops) > 1 else 0.0,
                    "n_pdr": len(pdr),
                    "pdr_mean": float(np.mean(pdr)) if pdr else 0.0,
                    "pdr_std": float(np.std(pdr, ddof=1)) if len(pdr) > 1 else 0.0,
                }
            )
    return rows


def build_significance(groups: Dict[Tuple[str, str], Dict[str, List[float]]]) -> List[Dict]:
    raw_rows: List[Dict] = []
    pvals: List[float] = []
    for env in ENVS:
        aeris = groups.get((env, "AERIS"), {}).get("hops", [])
        if not aeris:
            continue
        for baseline in BASELINES:
            base = groups.get((env, baseline), {}).get("hops", [])
            if not base:
                continue
            t_stat, p_val = stats.ttest_ind(aeris, base, equal_var=False)
            raw_rows.append(
                {
                    "environment": env,
                    "baseline": baseline,
                    "aeris_hops_mean": float(np.mean(aeris)),
                    "baseline_hops_mean": float(np.mean(base)),
                    "diff": float(np.mean(aeris) - np.mean(base)),
                    "hedges_g": hedges_g(aeris, base),
                    "t_stat": float(t_stat),
                    "p_value_raw": float(p_val),
                }
            )
            pvals.append(float(p_val))

    corrected = holm_bonferroni(pvals) if pvals else []
    for i, row in enumerate(raw_rows):
        p_corr = corrected[i] if corrected else row["p_value_raw"]
        row["p_value_holm"] = p_corr
        row["sig_holm_0_05"] = "YES" if p_corr < 0.05 else "no"
    return raw_rows


def write_csv(path: Path, rows: List[Dict]):
    if not rows:
        raise RuntimeError(f"No rows to write: {path}")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, input_files: Dict[str, Path], rows: List[Dict], sig_rows: List[Dict]):
    lines: List[str] = []
    lines.append("# Latency (Hop Count) Statistics")
    lines.append("")
    lines.append(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}")
    lines.append("Input files:")
    for env in ENVS:
        lines.append(f"- {env}: {input_files[env]}")
    lines.append("")
    lines.append("## Average Hop Count to BS (mean +/- std)")
    lines.append("")
    header = "| Environment | " + " | ".join(PROTOCOLS) + " |"
    sep = "|---|" + "|".join(["---"] * len(PROTOCOLS)) + "|"
    lines.append(header)
    lines.append(sep)
    for env in ENVS:
        cells = [env]
        for proto in PROTOCOLS:
            row = next((r for r in rows if r["environment"] == env and r["protocol"] == proto), None)
            if row:
                cells.append(f"{row['hops_mean']:.2f}+/-{row['hops_std']:.2f}")
            else:
                cells.append("-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## PDR Cross-Check (same latency runs)")
    lines.append("")
    lines.append(header)
    lines.append(sep)
    for env in ENVS:
        cells = [env]
        for proto in PROTOCOLS:
            row = next((r for r in rows if r["environment"] == env and r["protocol"] == proto), None)
            if row:
                cells.append(f"{row['pdr_mean']:.4f}+/-{row['pdr_std']:.4f}")
            else:
                cells.append("-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## Welch t-test + Hedges g + Holm correction (AERIS vs baseline)")
    lines.append("")
    lines.append("| Env | Baseline | AERIS hops | Baseline hops | Diff | Hedges g | p_raw | p_holm | Sig |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in sig_rows:
        lines.append(
            f"| {r['environment']} | {r['baseline']} | "
            f"{r['aeris_hops_mean']:.2f} | {r['baseline_hops_mean']:.2f} | "
            f"{r['diff']:+.2f} | {r['hedges_g']:+.2f} | {r['p_value_raw']:.2e} | "
            f"{r['p_value_holm']:.2e} | {r['sig_holm_0_05']} |"
        )
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def parse_args():
    ap = argparse.ArgumentParser(description="Extract latency stats from latency json files.")
    ap.add_argument("--dir", default="results/mega_experiments", help="Directory containing latency_*.json files")
    ap.add_argument("--prefix", default="latency_hop", help="Output file prefix")
    return ap.parse_args()


def main():
    args = parse_args()
    result_dir = Path(args.dir).resolve()
    input_files = {env: _pick_latest_for_env(result_dir, env) for env in ENVS}
    runs = load_runs(input_files)
    groups = group(runs)
    rows = build_rows(groups)
    sig_rows = build_significance(groups)

    stats_csv = result_dir / f"{args.prefix}_stats.csv"
    sig_csv = result_dir / f"{args.prefix}_significance.csv"
    stats_md = result_dir / f"{args.prefix}_stats.md"

    write_csv(stats_csv, rows)
    write_csv(sig_csv, sig_rows)
    write_markdown(stats_md, input_files, rows, sig_rows)

    print(f"stats_csv={stats_csv}")
    print(f"sig_csv={sig_csv}")
    print(f"stats_md={stats_md}")


if __name__ == "__main__":
    main()
