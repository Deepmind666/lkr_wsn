#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, math, statistics

# Holm-Bonferroni step-down adjustment for multiple comparisons
# Given a dict of {name: [samples_group_A], name: [samples_group_B]}, produce adjusted thresholds

def welch_t_pvalue(a, b):
    # Compute Welch t-stat and approximate two-sided p-value using Student's t asymptotics
    ma, mb = statistics.mean(a), statistics.mean(b)
    va = statistics.pvariance(a) if len(a) > 1 else 0.0
    vb = statistics.pvariance(b) if len(b) > 1 else 0.0
    na, nb = len(a), len(b)
    se = math.sqrt((va/na) + (vb/nb)) if na>0 and nb>0 else float('inf')
    t = (ma - mb) / se if se > 0 else 0.0
    # approximate df
    num = (va/na + vb/nb)**2
    den = 0.0
    if na>1: den += (va/na)**2 / (na-1)
    if nb>1: den += (vb/nb)**2 / (nb-1)
    df = num/den if den>0 else float('inf')
    # approximate p via survival function for large df -> normal
    # p ≈ 2 * (1 - Phi(|t|)), where Phi is std normal CDF
    # A quick erf-based approximation:
    x = abs(t) / math.sqrt(2)
    # erf approximation
    erf = math.erf(x)
    p = 2 * (1 - (1 + erf) / 2)
    return max(0.0, min(1.0, p)), t, df

if __name__ == '__main__':
    # Load significance tables
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    paths = [
        os.path.join(repo, 'results', 'significance_compare_50x200.json'),
        os.path.join(repo, 'results', 'significance_compare_multi_topo_50x200.json'),
    ]
    comparisons = []
    for p in paths:
        if not os.path.exists(p):
            continue
        data = json.load(open(p, 'r', encoding='utf-8'))
        # unify structure into a dict of metrics with BASE/ROBUST vectors
        if 'total_energy_consumed' in data:
            # single scenario file
            comps = {m: (data[m]['BASE']['values'], data[m]['ROBUST']['values']) for m in data.keys() if m in data}
            comparisons.append(('corridor31_50x200', comps))
        else:
            # multi-topo file
            for scenario, table in data.items():
                comps = {m: (table[m]['BASE']['values'], table[m]['ROBUST']['values']) for m in table.keys()}
                comparisons.append((scenario, comps))
    # Perform Holm-Bonferroni across all metric-scenario pairs
    alpha = 0.05
    records = []
    for scenario, comps in comparisons:
        for metric, (a, b) in comps.items():
            p, t, df = welch_t_pvalue(a, b)
            records.append({'scenario': scenario, 'metric': metric, 'p': p, 't': t, 'df': df})
    # sort by p ascending
    records.sort(key=lambda r: r['p'])
    m = len(records)
    decisions = []
    for i, r in enumerate(records, start=1):
        threshold = alpha / (m - i + 1)
        decisions.append({**r, 'holm_threshold': threshold, 'reject_null': r['p'] <= threshold})
    out = os.path.join(repo, 'results', 'multitest_holm_bonferroni.json')
    json.dump(decisions, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out)

