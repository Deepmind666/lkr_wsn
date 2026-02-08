#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze nonparametric significance on Intel parallel results.
Computes Mann–Whitney U, AUC, Cliff's delta, and Cohen's d (pooled SD) for:
- total_energy_consumed (BASE vs ROBUST)
- pdr_end2end_mean (BASE vs ROBUST)
Outputs JSON to results/significance_nonparam_intel_parallel.json and prints a summary.
"""
import os, json, math, statistics
from typing import List, Dict

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IN_PATH = os.path.join(REPO, 'results', 'significance_compare_intel_parallel.json')
OUT_PATH = os.path.join(REPO, 'results', 'significance_nonparam_intel_parallel.json')


def cliffs_delta(x: List[float], y: List[float]) -> float:
    """Cliff's delta: P(X>Y) - P(Y>X) over all pairs.
    """
    nx, ny = len(x), len(y)
    gt = lt = 0
    for xi in x:
        for yj in y:
            if xi > yj:
                gt += 1
            elif xi < yj:
                lt += 1
    return (gt - lt) / (nx * ny)


def mann_whitney_u(x: List[float], y: List[float]) -> Dict[str, float]:
    """Compute Mann–Whitney U using rank sums, with normal approximation z.
    Ties are handled via average ranks; tie correction applied for z.
    Returns dict with U, U_alt, z_approx (two-sided), and auc.
    """
    n1, n2 = len(x), len(y)
    pooled = [(v, 0) for v in x] + [(v, 1) for v in y]
    # Sort by value
    pooled.sort(key=lambda t: t[0])

    # Assign ranks with tie averaging
    ranks = [0.0] * (n1 + n2)
    i = 0
    while i < n1 + n2:
        j = i
        while j + 1 < n1 + n2 and pooled[j + 1][0] == pooled[i][0]:
            j += 1
        avg_rank = (i + j + 2) / 2.0  # ranks start at 1
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        i = j + 1

    # Rank sums
    R1 = sum(ranks[idx] for idx, (_, g) in enumerate(pooled) if g == 0)
    U1 = R1 - n1 * (n1 + 1) / 2.0
    U2 = n1 * n2 - U1

    # Tie correction for z approximation
    # Compute tie groups sizes (for tie correction in variance)
    tie_counts = []
    i = 0
    while i < n1 + n2:
        j = i
        while j + 1 < n1 + n2 and pooled[j + 1][0] == pooled[i][0]:
            j += 1
        t = j - i + 1
        if t > 1:
            tie_counts.append(t)
        i = j + 1

    # Variance with tie correction
    mu_U = n1 * n2 / 2.0
    sigma2 = n1 * n2 * (n1 + n2 + 1) / 12.0
    if tie_counts:
        T = sum(t * (t * t - 1) for t in tie_counts)
        sigma2 -= (n1 * n2 * T) / (12.0 * (n1 + n2) * (n1 + n2 - 1))
    sigma = math.sqrt(sigma2) if sigma2 > 0 else float('nan')

    # Continuity correction
    z = (U1 - mu_U - 0.5 * math.copysign(1, U1 - mu_U)) / sigma if sigma > 0 else float('nan')
    auc = U1 / (n1 * n2)
    return {
        'U': U1,
        'U_alt': U2,
        'z_approx': z,
        'auc': auc,
    }


def cohens_d(x: List[float], y: List[float]) -> float:
    """Compute Cohen's d using pooled SD."""
    n1, n2 = len(x), len(y)
    m1, m2 = statistics.mean(x), statistics.mean(y)
    # Sample variances
    s1 = statistics.pvariance(x) * n1 / (n1 - 1) if n1 > 1 else 0.0
    s2 = statistics.pvariance(y) * n2 / (n2 - 1) if n2 > 1 else 0.0
    sp = math.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2)) if (n1 + n2 - 2) > 0 else float('nan')
    return (m1 - m2) / sp if sp and sp > 0 else float('nan')


def main():
    with open(IN_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    out = {'meta': {'input': os.path.relpath(IN_PATH, REPO)}}
    for key in ['total_energy_consumed', 'pdr_end2end_mean']:
        base_vals = data[key]['BASE']['values']
        robust_vals = data[key]['ROBUST']['values']

        stats_u = mann_whitney_u(base_vals, robust_vals)
        delta = cliffs_delta(base_vals, robust_vals)
        d = cohens_d(base_vals, robust_vals)

        out[key] = {
            'n_base': len(base_vals),
            'n_robust': len(robust_vals),
            'mann_whitney': stats_u,
            'cliffs_delta': delta,
            'cohens_d': d,
            'means': {
                'BASE': data[key]['BASE']['mean'],
                'ROBUST': data[key]['ROBUST']['mean'],
            },
            'ci95': {
                'BASE': data[key]['BASE'].get('ci95'),
                'ROBUST': data[key]['ROBUST'].get('ci95'),
            }
        }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Print compact summary
    print('Nonparametric summary written to', OUT_PATH)
    for k in ['total_energy_consumed', 'pdr_end2end_mean']:
        s = out[k]
        print(f"{k}: n={s['n_base']} vs {s['n_robust']}, U={s['mann_whitney']['U']:.2f}, auc={s['mann_whitney']['auc']:.3f}, delta={s['cliffs_delta']:.3f}, d={s['cohens_d']:.3f}")


if __name__ == '__main__':
    main()