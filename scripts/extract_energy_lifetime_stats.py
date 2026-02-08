"""
Extract energy, lifetime, and FND statistics from existing env_sensitivity JSON.
Data source: env_sensitivity_20260207_205317.json (publication-tier, n=30)

Output:
  - results/mega_experiments/energy_lifetime_stats.csv
  - results/mega_experiments/energy_lifetime_stats.md
"""
import json
import csv
import sys
import os
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import stats

def main():
    print(f"[{datetime.now():%H:%M:%S}] 开始提取能耗/生存期/FND统计")

    src = Path(r"c:\AERIS-WSN-Protocol\results\mega_experiments"
               r"\env_sensitivity_20260207_205317.json")
    if not src.exists():
        print(f"ERROR: {src} not found")
        sys.exit(1)

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    raw = data["raw_results"]
    print(f"[{datetime.now():%H:%M:%S}] 加载 {len(raw)} 条记录")

    # Group by (environment, protocol)
    groups = {}
    for r in raw:
        if r.get("error"):
            continue
        key = (r["environment"], r["protocol"])
        if key not in groups:
            groups[key] = {"energy": [], "lifetime": [], "fnd": [], "pdr": []}
        groups[key]["energy"].append(r.get("total_energy_consumed", 0))
        groups[key]["lifetime"].append(r.get("total_rounds", 0))
        groups[key]["fnd"].append(r.get("first_node_death_round", 0))
        groups[key]["pdr"].append(r.get("pdr_expected", 0))

    envs = ["indoor_office", "indoor_factory", "outdoor_urban", "outdoor_suburban"]
    protocols = ["AERIS", "LEACH", "PEGASIS", "HEED", "TEEN"]

    # Build rows
    rows = []
    for env in envs:
        for proto in protocols:
            key = (env, proto)
            if key not in groups:
                continue
            g = groups[key]
            n = len(g["energy"])
            row = {
                "environment": env,
                "protocol": proto,
                "n": n,
                "energy_mean": np.mean(g["energy"]),
                "energy_std": np.std(g["energy"], ddof=1),
                "lifetime_mean": np.mean(g["lifetime"]),
                "lifetime_std": np.std(g["lifetime"], ddof=1),
                "fnd_mean": np.mean(g["fnd"]),
                "fnd_std": np.std(g["fnd"], ddof=1),
                "pdr_mean": np.mean(g["pdr"]),
            }
            rows.append(row)

    # Welch t-test: AERIS vs each baseline for energy and lifetime
    sig_rows = []
    for env in envs:
        aeris_key = (env, "AERIS")
        if aeris_key not in groups:
            continue
        for baseline in ["LEACH", "PEGASIS", "HEED", "TEEN"]:
            bl_key = (env, baseline)
            if bl_key not in groups:
                continue
            for metric in ["energy", "lifetime", "fnd"]:
                a = groups[aeris_key][metric]
                b = groups[bl_key][metric]
                t_stat, p_val = stats.ttest_ind(a, b, equal_var=False)
                diff = np.mean(a) - np.mean(b)
                sig_rows.append({
                    "environment": env,
                    "baseline": baseline,
                    "metric": metric,
                    "aeris_mean": np.mean(a),
                    "baseline_mean": np.mean(b),
                    "diff": diff,
                    "t": t_stat,
                    "p": p_val,
                    "sig": "YES" if p_val < 0.05 else "no",
                })

    # Write CSV
    out_dir = Path(r"c:\AERIS-WSN-Protocol\results\mega_experiments")
    csv_path = out_dir / "energy_lifetime_stats.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[{datetime.now():%H:%M:%S}] CSV 已保存: {csv_path}")

    # Write significance CSV
    sig_csv = out_dir / "energy_lifetime_significance.csv"
    with open(sig_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sig_rows[0].keys()))
        w.writeheader()
        w.writerows(sig_rows)
    print(f"[{datetime.now():%H:%M:%S}] 显著性 CSV: {sig_csv}")

    # Write markdown summary
    md_path = out_dir / "energy_lifetime_stats.md"
    write_markdown(md_path, rows, sig_rows, envs, protocols)
    print(f"[{datetime.now():%H:%M:%S}] Markdown: {md_path}")
    print(f"[{datetime.now():%H:%M:%S}] 完成")


def write_markdown(md_path, rows, sig_rows, envs, protocols):
    lines = []
    lines.append("# Energy, Lifetime, FND Statistics (n=30)")
    lines.append("")
    lines.append(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}")
    lines.append(f"Source: env_sensitivity_20260207_205317.json")
    lines.append("")

    # Energy table
    lines.append("## Table: Total Energy Consumed (J, mean +/- std)")
    lines.append("")
    hdr = "| Environment | " + " | ".join(protocols) + " |"
    sep = "|---|" + "|".join(["---"] * len(protocols)) + "|"
    lines.append(hdr)
    lines.append(sep)
    for env in envs:
        cells = [env]
        for proto in protocols:
            r = next((x for x in rows
                       if x["environment"] == env and x["protocol"] == proto), None)
            if r:
                cells.append(f"{r['energy_mean']:.2f}+/-{r['energy_std']:.2f}")
            else:
                cells.append("-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # Lifetime table
    lines.append("## Table: Network Lifetime (rounds, mean +/- std)")
    lines.append("")
    lines.append(hdr)
    lines.append(sep)
    for env in envs:
        cells = [env]
        for proto in protocols:
            r = next((x for x in rows
                       if x["environment"] == env and x["protocol"] == proto), None)
            if r:
                cells.append(f"{r['lifetime_mean']:.1f}+/-{r['lifetime_std']:.1f}")
            else:
                cells.append("-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # FND table
    lines.append("## Table: First Node Death Round (mean +/- std)")
    lines.append("")
    lines.append(hdr)
    lines.append(sep)
    for env in envs:
        cells = [env]
        for proto in protocols:
            r = next((x for x in rows
                       if x["environment"] == env and x["protocol"] == proto), None)
            if r:
                cells.append(f"{r['fnd_mean']:.1f}+/-{r['fnd_std']:.1f}")
            else:
                cells.append("-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # Significance summary
    lines.append("## Significance: AERIS vs Baselines (Welch t-test)")
    lines.append("")
    lines.append("| Env | Baseline | Metric | AERIS | Baseline | Diff | p | Sig |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for sr in sig_rows:
        lines.append(
            f"| {sr['environment']} | {sr['baseline']} | {sr['metric']} "
            f"| {sr['aeris_mean']:.2f} | {sr['baseline_mean']:.2f} "
            f"| {sr['diff']:+.2f} | {sr['p']:.2e} | {sr['sig']} |"
        )
    lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
