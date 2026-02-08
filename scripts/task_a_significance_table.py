#!/usr/bin/env python3
"""
Task A: Generate scalability significance table.
Welch t-test (AERIS vs each baseline) + Hedges' g effect size + Holm-Bonferroni.
Output: CSV + Markdown summary.

Important:
All statistics are computed directly from raw per-replicate pdr_expected values.
No synthetic sample reconstruction from summary stats is used.
"""

import argparse
import json
import math
import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from scipy import stats
import numpy as np

DEFAULT_OVERNIGHT_DIR = Path(
    r"C:\AERIS-WSN-Protocol\results\mega_experiments"
    r"\overnight_scalability_20260208_005918"
)

ENVS = ["indoor_office", "indoor_factory", "outdoor_urban", "outdoor_suburban"]
NODE_COUNTS = [100, 200, 300, 500, 800, 1000]
BASELINES = ["LEACH", "PEGASIS", "HEED", "TEEN"]
ALPHA = 0.05


def load_experiment(env: str, overnight_dir: Path) -> Dict:
    pattern = list(overnight_dir.glob(f"scalability_{env}_*.json"))
    if not pattern:
        print(f"[ERROR] No file for {env}")
        sys.exit(1)
    with open(pattern[0], "r", encoding="utf-8-sig") as f:
        return json.load(f)


def welch_t(a: np.ndarray, b: np.ndarray) -> Tuple[float, float]:
    """Welch's t-test using raw samples. Returns (t_stat, p_value)."""
    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan")
    result = stats.ttest_ind(a, b, equal_var=False, nan_policy="omit")
    return float(result.statistic), float(result.pvalue)


def hedges_g(a: np.ndarray, b: np.ndarray) -> float:
    """Hedges' g (bias-corrected standardized mean difference)."""
    n1 = len(a)
    n2 = len(b)
    if n1 < 2 or n2 < 2:
        return 0.0
    m1 = float(np.mean(a))
    m2 = float(np.mean(b))
    s1 = float(np.std(a, ddof=1))
    s2 = float(np.std(b, ddof=1))
    sp = math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / max(n1 + n2 - 2, 1))
    if sp < 1e-15:
        return 0.0
    d = (m1 - m2) / sp
    # Hedges' correction factor
    df = n1 + n2 - 2
    j = 1 - 3 / (4 * df - 1) if df > 1 else 1.0
    return d * j


def holm_bonferroni(pvalues: List[float]) -> Tuple[List[bool], List[float]]:
    """
    Holm-Bonferroni correction.
    Returns:
      - reject flags
      - adjusted p-values in original order
    """
    n = len(pvalues)
    indexed = sorted(enumerate(pvalues), key=lambda x: (math.isnan(x[1]), x[1]))
    reject = [False] * n
    p_adj = [float("nan")] * n

    running_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        if math.isnan(p):
            p_adj[orig_idx] = float("nan")
            continue
        raw_adj = (n - rank) * p
        running_max = max(running_max, raw_adj)
        p_adj[orig_idx] = min(1.0, running_max)

    for i, val in enumerate(p_adj):
        reject[i] = (not math.isnan(val)) and val < ALPHA
    return reject, p_adj


def extract_protocol_samples(raw_results: List[Dict], node_count: int, protocol: str) -> np.ndarray:
    vals = []
    for row in raw_results:
        if row.get("protocol") != protocol:
            continue
        if int(row.get("num_nodes", -1)) != int(node_count):
            continue
        metrics = row.get("metrics", {})
        pdr = metrics.get("pdr_expected")
        if pdr is not None:
            vals.append(float(pdr))
    return np.array(vals, dtype=float)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate scalability significance tables from raw results.")
    parser.add_argument(
        "--overnight-dir",
        type=Path,
        default=DEFAULT_OVERNIGHT_DIR,
        help="Directory containing scalability_<env>_*.json files",
    )
    parser.add_argument(
        "--out-prefix",
        type=str,
        default="scalability_significance",
        help="Output filename prefix under results/mega_experiments",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    overnight_dir = args.overnight_dir
    rows = []
    all_pvalues = []
    all_row_indices = []

    for env in ENVS:
        data = load_experiment(env, overnight_dir)
        raw_results = data.get("raw_results", [])
        for nc in NODE_COUNTS:
            a = extract_protocol_samples(raw_results, nc, "AERIS")
            if len(a) == 0:
                continue
            am = float(np.mean(a))
            astd = float(np.std(a, ddof=1))
            an = int(len(a))

            for bl in BASELINES:
                b = extract_protocol_samples(raw_results, nc, bl)
                if len(b) == 0:
                    continue
                bm = float(np.mean(b))
                bstd = float(np.std(b, ddof=1))
                bn = int(len(b))

                t, p = welch_t(a, b)
                g = hedges_g(a, b)
                diff = am - bm

                row_idx = len(rows)
                rows.append({
                    "environment": env,
                    "node_count": nc,
                    "baseline": bl,
                    "aeris_pdr_mean": round(am, 6),
                    "aeris_pdr_std": round(astd, 6),
                    "aeris_n": an,
                    "baseline_pdr_mean": round(bm, 6),
                    "baseline_pdr_std": round(bstd, 6),
                    "baseline_n": bn,
                    "diff": round(diff, 6),
                    "t_stat": round(t, 4),
                    "p_value": p,
                    "hedges_g": round(g, 4),
                    "aeris_wins": am > bm,
                })
                all_pvalues.append(p)
                all_row_indices.append(row_idx)

    # Holm-Bonferroni correction
    sig_flags, p_holm = holm_bonferroni(all_pvalues)
    for i, row_idx in enumerate(all_row_indices):
        rows[row_idx]["holm_significant"] = sig_flags[i]
        rows[row_idx]["p_value_holm"] = p_holm[i]

    # Write CSV
    out_dir = Path(r"C:\AERIS-WSN-Protocol\results\mega_experiments")
    csv_path = out_dir / f"{args.out_prefix}_table.csv"
    fieldnames = [
        "environment", "node_count", "baseline",
        "aeris_n", "baseline_n",
        "aeris_pdr_mean", "baseline_pdr_mean", "diff",
        "aeris_pdr_std", "baseline_pdr_std",
        "t_stat", "p_value", "p_value_holm", "hedges_g",
        "aeris_wins", "holm_significant",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            r_out = dict(r)
            r_out["p_value"] = "nan" if math.isnan(r_out["p_value"]) else f"{r_out['p_value']:.2e}"
            r_out["p_value_holm"] = "nan" if math.isnan(r_out["p_value_holm"]) else f"{r_out['p_value_holm']:.2e}"
            writer.writerow(r_out)

    print(f"[OK] CSV written: {csv_path}")

    # Write Markdown summary
    md_path = out_dir / f"{args.out_prefix}_summary.md"
    write_markdown(rows, md_path, overnight_dir.name)
    print(f"[OK] MD written: {md_path}")
    return 0


def write_markdown(rows, md_path, source_dir_name: str):
    lines = [
        "# Scalability Significance Summary",
        "",
        f"Source: {source_dir_name} (6 node counts, 4 environments)",
        "",
        "Metric: pdr_expected | Test: Welch's t-test on raw replicates | Effect size: Hedges' g | Correction: Holm-Bonferroni",
        "",
    ]

    # Can claim / cannot claim
    lines.append("## Can Claim")
    lines.append("")

    can_claim = []
    cannot_claim = []

    for env in ENVS:
        env_rows = [r for r in rows if r["environment"] == env]
        for nc in NODE_COUNTS:
            nc_rows = [r for r in env_rows if r["node_count"] == nc]
            all_win = all(r["aeris_wins"] and r["holm_significant"] for r in nc_rows)
            any_lose = any(not r["aeris_wins"] for r in nc_rows)

            if all_win:
                can_claim.append(
                    f"- AERIS ranks first in {env} at {nc} nodes "
                    f"(all baselines p < 0.05 after Holm correction)"
                )
            elif any_lose:
                losers = [r for r in nc_rows if not r["aeris_wins"]]
                for r in losers:
                    cannot_claim.append(
                        f"- {env}@{nc}: {r['baseline']} ({r['baseline_pdr_mean']:.4f}) "
                        f"> AERIS ({r['aeris_pdr_mean']:.4f}), "
                        f"Hedges' g = {r['hedges_g']:.2f}"
                    )

    for c in can_claim:
        lines.append(c)

    lines.append("")
    lines.append("## Cannot Claim (AERIS not first)")
    lines.append("")

    if cannot_claim:
        for c in cannot_claim:
            lines.append(c)
    else:
        lines.append("- None: AERIS ranks first in all tested conditions.")

    lines.append("")
    lines.append("## Detailed Table (top-level)")
    lines.append("")
    lines.append("| Environment | Nodes | Baseline | AERIS PDR | Baseline PDR | Diff | t | p | g | Sig |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")

    for r in rows:
        sig = "YES" if r["holm_significant"] else "no"
        win = "+" if r["aeris_wins"] else "-"
        lines.append(
            f"| {r['environment']} | {r['node_count']} | {r['baseline']} "
            f"| {r['aeris_pdr_mean']:.4f} | {r['baseline_pdr_mean']:.4f} "
            f"| {r['diff']:+.4f} | {r['t_stat']:.2f} | {r['p_value']:.2e} "
            f"| {r['hedges_g']:.2f} | {sig}{win} |"
        )

    lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
