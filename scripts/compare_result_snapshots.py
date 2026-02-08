#!/usr/bin/env python3
"""
Compare two publication JSON snapshots and emit a compact Markdown diff report.

Supported experiment_type:
- env_sensitivity / fair_5protocol
- ablation_env_sensitivity / ablation
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime

import numpy as np
from scipy.stats import ttest_ind


def _mean_std(vals):
    if not vals:
        return 0.0, 0.0
    arr = np.array(vals, dtype=float)
    return float(np.mean(arr)), float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def aggregate_env(data):
    rows = [r for r in data.get("raw_results", []) if not r.get("error")]
    g = defaultdict(list)
    for r in rows:
        g[(r.get("environment"), r.get("protocol"))].append(float(r.get("pdr_expected", 0.0)))
    out = {}
    for k, v in g.items():
        out[k] = {"mean": _mean_std(v)[0], "std": _mean_std(v)[1], "n": len(v)}
    return out


def aggregate_ablation(data):
    rows = [r for r in data.get("raw_results", []) if not r.get("error")]
    g = defaultdict(list)
    for r in rows:
        g[(r.get("environment"), r.get("ablation_config"))].append(float(r.get("pdr_expected", 0.0)))
    out = {}
    for k, v in g.items():
        out[k] = {"mean": _mean_std(v)[0], "std": _mean_std(v)[1], "n": len(v), "vals": v}
    return out


def write_report(old_path, new_path, out_path):
    old = load_json(old_path)
    new = load_json(new_path)

    old_type = old.get("experiment_type", "unknown")
    new_type = new.get("experiment_type", "unknown")

    lines = []
    lines.append("# Snapshot Diff Report")
    lines.append("")
    lines.append(f"- generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- old_file: {old_path}")
    lines.append(f"- new_file: {new_path}")
    lines.append(f"- old_type: {old_type}")
    lines.append(f"- new_type: {new_type}")
    lines.append("")
    lines.append("## Metadata")
    lines.append("")
    for key in ["git_commit", "git_dirty", "run_tier", "primary_metric", "config_hash"]:
        lines.append(f"- {key}: old={old.get(key)} | new={new.get(key)}")
    lines.append("")

    if "ablation" in new_type:
        a_old = aggregate_ablation(old)
        a_new = aggregate_ablation(new)
        envs = sorted({k[0] for k in a_new.keys()})
        cfgs = sorted({k[1] for k in a_new.keys()})

        lines.append("## Mean PDR Delta (new - old)")
        lines.append("")
        lines.append("| Environment | Config | old_mean | new_mean | delta |")
        lines.append("|---|---:|---:|---:|---:|")
        for e in envs:
            for c in cfgs:
                o = a_old.get((e, c), {}).get("mean", np.nan)
                n = a_new.get((e, c), {}).get("mean", np.nan)
                d = n - o if not (np.isnan(o) or np.isnan(n)) else np.nan
                lines.append(f"| {e} | {c} | {o:.4f} | {n:.4f} | {d:.4f} |")
        lines.append("")

        lines.append("## New Snapshot Significance (full vs no_gateway/no_cas)")
        lines.append("")
        lines.append("| Environment | comparison | diff(other-full) | p_value |")
        lines.append("|---|---|---:|---:|")
        for e in envs:
            full = a_new.get((e, "full"), {}).get("vals", [])
            for other in ["no_gateway", "no_cas"]:
                oth = a_new.get((e, other), {}).get("vals", [])
                if full and oth:
                    _, p = ttest_ind(full, oth, equal_var=False)
                    diff = np.mean(oth) - np.mean(full)
                    lines.append(f"| {e} | full vs {other} | {diff:.4f} | {p:.6g} |")
        lines.append("")
    else:
        e_old = aggregate_env(old)
        e_new = aggregate_env(new)
        envs = sorted({k[0] for k in e_new.keys()})
        protos = sorted({k[1] for k in e_new.keys()})

        lines.append("## Mean PDR Delta (new - old)")
        lines.append("")
        lines.append("| Environment | Protocol | old_mean | new_mean | delta |")
        lines.append("|---|---:|---:|---:|---:|")
        for e in envs:
            for p in protos:
                o = e_old.get((e, p), {}).get("mean", np.nan)
                n = e_new.get((e, p), {}).get("mean", np.nan)
                d = n - o if not (np.isnan(o) or np.isnan(n)) else np.nan
                lines.append(f"| {e} | {p} | {o:.4f} | {n:.4f} | {d:.4f} |")
        lines.append("")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Compare two result snapshots.")
    parser.add_argument("--old", required=True, help="Old JSON result file")
    parser.add_argument("--new", required=True, help="New JSON result file")
    parser.add_argument("--out", required=True, help="Output markdown report path")
    args = parser.parse_args()

    write_report(args.old, args.new, args.out)
    print(f"Saved report: {args.out}")


if __name__ == "__main__":
    main()

