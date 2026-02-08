#!/usr/bin/env python3
"""
Lightweight effect size calculator (no external deps).

Features:
- Cohen's d (unpaired, pooled SD) and Hedges' g (small-sample bias corrected)
- Glass's Δ (using control SD)
- Cliff's δ (nonparametric)
- Rank-biserial correlation (via Mann–Whitney U formulation)
- Common Language Effect Size (CLES)
- Paired Cohen's d (on differences)

CLI:
  python scripts/compute_effect_sizes.py --input1 results/a.json --input2 results/b.json \
      --label1 AERIS --label2 LEACH --outdir results

Input formats:
- JSON: either a list of numbers, or an object with the key pointing to a list
- CSV/TSV: first numeric column (header ignored)
- TXT: one number per line
"""

from __future__ import annotations

import argparse
import json
import math
import os
from typing import List, Dict, Any, Tuple


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else float('nan')


def _var_sample(xs: List[float]) -> float:
    n = len(xs)
    if n < 2:
        return float('nan')
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (n - 1)


def _std_sample(xs: List[float]) -> float:
    v = _var_sample(xs)
    return math.sqrt(v) if not math.isnan(v) else float('nan')


def cohen_d(a: List[float], b: List[float]) -> float:
    """Unpaired Cohen's d using pooled SD."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return float('nan')
    s1, s2 = _std_sample(a), _std_sample(b)
    sp = math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2))
    if sp == 0:
        return float('nan')
    return (_mean(a) - _mean(b)) / sp


def hedges_g(a: List[float], b: List[float]) -> float:
    """Hedges' g = d * J, J = 1 - 3/(4N - 9)."""
    d = cohen_d(a, b)
    n = len(a) + len(b)
    if n <= 9:
        return float('nan')
    J = 1.0 - 3.0 / (4.0 * n - 9.0)
    return d * J


def glass_delta(a: List[float], b: List[float], reference: str = 'b') -> float:
    """Glass's delta: difference in means divided by SD of reference group."""
    ref = b if reference == 'b' else a
    s_ref = _std_sample(ref)
    if s_ref == 0:
        return float('nan')
    return (_mean(a) - _mean(b)) / s_ref


def cliffs_delta(a: List[float], b: List[float]) -> float:
    """Cliff's delta: (concordant - discordant) / (n1 * n2)."""
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return float('nan')
    concordant = 0
    discordant = 0
    ties = 0
    for x in a:
        for y in b:
            if x > y:
                concordant += 1
            elif x < y:
                discordant += 1
            else:
                ties += 1
    return (concordant - discordant) / float(n1 * n2)


def rank_biserial(a: List[float], b: List[float]) -> float:
    """Rank-biserial correlation via U statistic: r_rb = 1 - 2U/(n1*n2).
    We approximate U by pairwise comparisons with 0.5 for ties.
    """
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return float('nan')
    u = 0.0
    for x in a:
        for y in b:
            if x > y:
                u += 1.0
            elif x == y:
                u += 0.5
            # else x < y contributes 0
    return 1.0 - 2.0 * (u / (n1 * n2))


def cles(a: List[float], b: List[float]) -> float:
    """Common Language Effect Size: P(X > Y) + 0.5 * P(X == Y)."""
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return float('nan')
    wins = 0
    ties = 0
    for x in a:
        for y in b:
            if x > y:
                wins += 1
            elif x == y:
                ties += 1
    return (wins + 0.5 * ties) / float(n1 * n2)


def paired_cohen_d(a: List[float], b: List[float]) -> float:
    """Paired Cohen's d on differences (requires equal length)."""
    if len(a) != len(b) or len(a) < 2:
        return float('nan')
    diffs = [x - y for x, y in zip(a, b)]
    m = _mean(diffs)
    s = _std_sample(diffs)
    if s == 0:
        return float('nan')
    return m / s


def summarize_two_groups(a: List[float], b: List[float], paired: bool = False) -> Dict[str, Any]:
    return {
        'n1': len(a),
        'n2': len(b),
        'mean1': _mean(a),
        'mean2': _mean(b),
        'std1': _std_sample(a),
        'std2': _std_sample(b),
        'cohen_d': paired_cohen_d(a, b) if paired else cohen_d(a, b),
        'hedges_g': hedges_g(a, b) if not paired else None,
        'glass_delta_b': glass_delta(a, b, reference='b') if not paired else None,
        'cliffs_delta': cliffs_delta(a, b),
        'rank_biserial': rank_biserial(a, b),
        'cles': cles(a, b)
    }


def _to_float_list(vals: List[Any]) -> List[float]:
    out = []
    for v in vals:
        try:
            out.append(float(v))
        except Exception:
            pass
    return out


def read_series(path: str, key: str | None = None) -> List[float]:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return _to_float_list(data)
        elif isinstance(data, dict):
            if key is None:
                # try to find first list value
                for k, v in data.items():
                    if isinstance(v, list):
                        return _to_float_list(v)
                raise ValueError('JSON object requires --key to select list')
            return _to_float_list(data.get(key, []))
        else:
            raise ValueError('Unsupported JSON structure')
    elif ext in ('.csv', '.tsv'):
        sep = ',' if ext == '.csv' else '\t'
        out = []
        with open(path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                parts = line.strip().split(sep)
                if not parts:
                    continue
                # skip header row if first token not numeric
                try:
                    val = float(parts[0])
                    out.append(val)
                except Exception:
                    if i == 0:
                        continue
                    # skip malformed rows
                    continue
        return out
    elif ext == '.txt':
        out = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(float(line))
                except Exception:
                    continue
        return out
    else:
        raise ValueError(f'Unsupported file extension: {ext}')


def write_outputs(outdir: str, label1: str, label2: str, stats: Dict[str, Any]) -> Tuple[str, str]:
    os.makedirs(outdir, exist_ok=True)
    stem = f'effect_sizes_{label1}_{label2}'
    jpath = os.path.join(outdir, stem + '.json')
    mpath = os.path.join(outdir, stem + '.md')
    with open(jpath, 'w', encoding='utf-8') as fj:
        json.dump(stats, fj, ensure_ascii=False, indent=2)
    with open(mpath, 'w', encoding='utf-8') as fm:
        fm.write(f'# Effect Sizes: {label1} vs {label2}\n\n')
        fm.write(f'- n1: {stats["n1"]}, n2: {stats["n2"]}\n')
        fm.write(f'- mean1: {stats["mean1"]:.6f}, mean2: {stats["mean2"]:.6f}\n')
        fm.write(f'- std1: {stats["std1"]:.6f}, std2: {stats["std2"]:.6f}\n')
        fm.write(f'- cohen_d: {stats["cohen_d"]}\n')
        fm.write(f'- hedges_g: {stats.get("hedges_g")}\n')
        fm.write(f'- glass_delta_b: {stats.get("glass_delta_b")}\n')
        fm.write(f'- cliffs_delta: {stats["cliffs_delta"]}\n')
        fm.write(f'- rank_biserial: {stats["rank_biserial"]}\n')
        fm.write(f'- cles: {stats["cles"]}\n')
    return jpath, mpath


def main() -> None:
    ap = argparse.ArgumentParser(description='Compute effect sizes for two groups.')
    ap.add_argument('--input1', required=True, help='Path to first series (json/csv/tsv/txt)')
    ap.add_argument('--input2', required=True, help='Path to second series (json/csv/tsv/txt)')
    ap.add_argument('--key1', default=None, help='JSON key for first series (if object)')
    ap.add_argument('--key2', default=None, help='JSON key for second series (if object)')
    ap.add_argument('--label1', default='group1', help='Label for first group')
    ap.add_argument('--label2', default='group2', help='Label for second group')
    ap.add_argument('--paired', action='store_true', help='Use paired Cohen\'s d')
    ap.add_argument('--outdir', default='results', help='Output directory (default results)')
    args = ap.parse_args()

    a = read_series(args.input1, args.key1)
    b = read_series(args.input2, args.key2)

    if not a or not b:
        raise SystemExit('Empty input series; please check your files and keys.')

    stats = summarize_two_groups(a, b, paired=args.paired)
    jpath, mpath = write_outputs(args.outdir, args.label1, args.label2, stats)
    print(f'Wrote JSON: {jpath}')
    print(f'Wrote Markdown: {mpath}')


if __name__ == '__main__':
    main()