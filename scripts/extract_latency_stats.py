"""
Extract latency (hop-count) statistics from 4 latency experiment JSONs.
Data source: latency_*.json (publication-tier, n=30, 4 environments)

Output:
  - results/mega_experiments/latency_hop_stats.csv
  - results/mega_experiments/latency_hop_stats.md
"""
import json
import csv
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import stats

RESULT_DIR = Path(r"c:\AERIS-WSN-Protocol\results\mega_experiments")

FILES = {
    "indoor_office": RESULT_DIR / "latency_indoor_office_20260208_234902.json",
    "indoor_factory": RESULT_DIR / "latency_indoor_factory_20260208_234929.json",
    "outdoor_urban": RESULT_DIR / "latency_outdoor_urban_20260208_234952.json",
    "outdoor_suburban": RESULT_DIR / "latency_outdoor_suburban_20260209_071707.json",
}

ENVS = ["indoor_office", "indoor_factory", "outdoor_urban", "outdoor_suburban"]
PROTOCOLS = ["AERIS", "LEACH", "PEGASIS", "HEED", "TEEN"]


def load_all():
    """Load and merge raw results from all 4 environment files."""
    all_runs = []
    for env, path in FILES.items():
        if not path.exists():
            print(f"ERROR: {path} not found")
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for r in data["raw_results"]:
            r["environment"] = env  # ensure consistent key
            all_runs.append(r)
    return all_runs


def group_by_env_proto(runs):
    groups = {}
    for r in runs:
        if not r.get("success", True):
            continue
        key = (r["environment"], r["protocol"])
        if key not in groups:
            groups[key] = {"hops": [], "pdr": [], "energy": []}
        m = r["metrics"]
        if m["avg_hops_to_bs"] > 0:
            groups[key]["hops"].append(m["avg_hops_to_bs"])
        if m["pdr_expected"] >= 0:
            groups[key]["pdr"].append(m["pdr_expected"])
        groups[key]["energy"].append(m["energy"])
    return groups


def build_rows(groups):
    rows = []
    for env in ENVS:
        for proto in PROTOCOLS:
            key = (env, proto)
            if key not in groups:
                continue
            g = groups[key]
            n = len(g["hops"])
            row = {
                "environment": env,
                "protocol": proto,
                "n": n,
                "hops_mean": float(np.mean(g["hops"])) if g["hops"] else 0,
                "hops_std": float(np.std(g["hops"], ddof=1)) if len(g["hops"]) > 1 else 0,
                "pdr_mean": float(np.mean(g["pdr"])) if g["pdr"] else 0,
                "pdr_std": float(np.std(g["pdr"], ddof=1)) if len(g["pdr"]) > 1 else 0,
            }
            rows.append(row)
    return rows


def build_significance(groups):
    sig_rows = []
    for env in ENVS:
        aeris_key = (env, "AERIS")
        if aeris_key not in groups or not groups[aeris_key]["hops"]:
            continue
        for baseline in ["LEACH", "PEGASIS", "HEED", "TEEN"]:
            bl_key = (env, baseline)
            if bl_key not in groups or not groups[bl_key]["hops"]:
                continue
            a = groups[aeris_key]["hops"]
            b = groups[bl_key]["hops"]
            t_stat, p_val = stats.ttest_ind(a, b, equal_var=False)
            sig_rows.append({
                "environment": env,
                "baseline": baseline,
                "aeris_hops": float(np.mean(a)),
                "baseline_hops": float(np.mean(b)),
                "diff": float(np.mean(a) - np.mean(b)),
                "t": float(t_stat),
                "p": float(p_val),
                "sig": "YES" if p_val < 0.05 else "no",
            })
    return sig_rows


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_markdown(md_path, rows, sig_rows):
    lines = []
    lines.append("# Latency (Hop Count) Statistics (n=30)")
    lines.append("")
    lines.append(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}")
    lines.append("Source: latency_*.json (4 environments)")
    lines.append("")

    # Hop count table
    lines.append("## Table: Average Hop Count to BS (mean +/- std)")
    lines.append("")
    hdr = "| Environment | " + " | ".join(PROTOCOLS) + " |"
    sep = "|---|" + "|".join(["---"] * len(PROTOCOLS)) + "|"
    lines.append(hdr)
    lines.append(sep)
    for env in ENVS:
        cells = [env]
        for proto in PROTOCOLS:
            r = next((x for x in rows
                       if x["environment"] == env and x["protocol"] == proto), None)
            if r:
                cells.append(f"{r['hops_mean']:.2f}+/-{r['hops_std']:.2f}")
            else:
                cells.append("-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # PDR cross-check table
    lines.append("## Table: PDR Cross-Check (mean +/- std)")
    lines.append("")
    lines.append(hdr)
    lines.append(sep)
    for env in ENVS:
        cells = [env]
        for proto in PROTOCOLS:
            r = next((x for x in rows
                       if x["environment"] == env and x["protocol"] == proto), None)
            if r:
                cells.append(f"{r['pdr_mean']:.4f}+/-{r['pdr_std']:.4f}")
            else:
                cells.append("-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # Significance
    lines.append("## Significance: AERIS vs Baselines Hop Count (Welch t-test)")
    lines.append("")
    lines.append("| Env | Baseline | AERIS hops | Baseline hops | Diff | p | Sig |")
    lines.append("|---|---|---|---|---|---|---|")
    for sr in sig_rows:
        lines.append(
            f"| {sr['environment']} | {sr['baseline']} "
            f"| {sr['aeris_hops']:.2f} | {sr['baseline_hops']:.2f} "
            f"| {sr['diff']:+.2f} | {sr['p']:.2e} | {sr['sig']} |"
        )
    lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    print(f"[{datetime.now():%H:%M:%S}] 开始提取延迟(hop count)统计")

    runs = load_all()
    print(f"[{datetime.now():%H:%M:%S}] 加载 {len(runs)} 条记录")

    groups = group_by_env_proto(runs)
    rows = build_rows(groups)
    sig_rows = build_significance(groups)

    csv_path = RESULT_DIR / "latency_hop_stats.csv"
    write_csv(rows, csv_path)
    print(f"[{datetime.now():%H:%M:%S}] CSV: {csv_path}")

    sig_csv = RESULT_DIR / "latency_hop_significance.csv"
    write_csv(sig_rows, sig_csv)
    print(f"[{datetime.now():%H:%M:%S}] 显著性 CSV: {sig_csv}")

    md_path = RESULT_DIR / "latency_hop_stats.md"
    write_markdown(md_path, rows, sig_rows)
    print(f"[{datetime.now():%H:%M:%S}] Markdown: {md_path}")

    print(f"[{datetime.now():%H:%M:%S}] 完成")


if __name__ == "__main__":
    main()
