#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, math, statistics
import glob
from scipy import stats

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
    # Parameters
    alpha = float(os.environ.get('MULTITEST_ALPHA', '0.05'))

    # Auto-discover significance comparison result files
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    results_dir = os.path.join(repo, 'results')
    patterns = [
        os.path.join(results_dir, 'significance_compare*.json'),
    ]
    files = []
    for pat in patterns:
        files.extend(glob.glob(pat))
    files = sorted(set(files))

    if not files:
        print('No significance_compare*.json files found in results/. Nothing to do.')
        sys.exit(0)

    def safe_get_values(tbl):
        # Expect dict with BASE/ROBUST each having 'values' list
        try:
            a = tbl['BASE'].get('values')
            b = tbl['ROBUST'].get('values')
            if isinstance(a, list) and isinstance(b, list) and len(a) > 0 and len(b) > 0:
                return a, b
        except Exception:
            pass
        return None

    comparisons = []  # list of (scenario_name, {metric: (A_values, B_values)})

    for p in files:
        name = os.path.splitext(os.path.basename(p))[0]
        try:
            data = json.load(open(p, 'r', encoding='utf-8'))
        except Exception as e:
            print(f'Skip {p}: failed to load JSON, err={e}')
            continue

        # Two possible structures:
        # 1) Single-scenario table: { metric: {BASE:{values:[]}, ROBUST:{values:[]}, ...}, ... }
        # 2) Multi-scenario table: { scenario: { metric: {BASE:{values:[]}, ROBUST:{values:[]}}, ... }, ... }
        if isinstance(data, dict):
            # Heuristic: if any top-level value has BASE/ROBUST -> single-scenario
            top_values = list(data.values())
            if any(isinstance(v, dict) and ('BASE' in v and 'ROBUST' in v) for v in top_values):
                comps = {}
                for metric, tbl in data.items():
                    if not isinstance(tbl, dict):
                        continue
                    sv = safe_get_values(tbl)
                    if sv is None:
                        continue
                    comps[metric] = sv
                if comps:
                    comparisons.append((name, comps))
            else:
                # assume multi-scenario
                for scenario, table in data.items():
                    if not isinstance(table, dict):
                        continue
                    comps = {}
                    for metric, tbl in table.items():
                        if not isinstance(tbl, dict):
                            continue
                        sv = safe_get_values(tbl)
                        if sv is None:
                            continue
                        comps[metric] = sv
                    if comps:
                        comparisons.append((f'{name}:{scenario}', comps))

    if not comparisons:
        print('No comparable BASE/ROBUST value vectors found. Nothing to do.')
        sys.exit(0)

    # Perform Holm-Bonferroni across all metric-scenario pairs
    records = []
    for scenario, comps in comparisons:
        for metric, (a, b) in comps.items():
            try:
                p, t, df = welch_t_pvalue(a, b)
                # Shapiro normality per group
                try:
                    sh_a = stats.shapiro(a).pvalue if len(a) >= 3 else None
                except Exception:
                    sh_a = None
                try:
                    sh_b = stats.shapiro(b).pvalue if len(b) >= 3 else None
                except Exception:
                    sh_b = None
                # Mann-Whitney U (two-sided)
                try:
                    try:
                        mwu_res = stats.mannwhitneyu(a, b, alternative='two-sided', method='auto')
                    except TypeError:
                        mwu_res = stats.mannwhitneyu(a, b, alternative='two-sided')
                    p_mwu = getattr(mwu_res, 'pvalue', None)
                    if p_mwu is None and isinstance(mwu_res, tuple) and len(mwu_res) > 1:
                        p_mwu = mwu_res[1]
                except Exception:
                    p_mwu = None
                records.append({'scenario': scenario, 'metric': metric, 'p': p, 't': t, 'df': df,
                                'shapiro_p_a': sh_a, 'shapiro_p_b': sh_b, 'mannwhitney_p': p_mwu})
            except Exception as e:
                print(f'Skip {scenario}/{metric}: Welch t failed, err={e}')

    if not records:
        print('No valid records for multiple testing. Nothing to do.')
        sys.exit(0)

    # sort by p ascending and apply Holm-Bonferroni
    records.sort(key=lambda r: r['p'])
    m = len(records)
    decisions = []
    for i, r in enumerate(records, start=1):
        threshold = alpha / (m - i + 1)
        decisions.append({**r, 'holm_threshold': threshold, 'reject_null': r['p'] <= threshold})

    out = os.path.join(results_dir, 'multitest_holm_bonferroni.json')
    try:
        json.dump(decisions, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('Saved', out)
        print(f'Total files: {len(files)}, total comparisons: {len(records)}, alpha={alpha}')

        # Also export CSV and Markdown for paper tables
        csv_path = os.path.join(results_dir, 'significance_holm_bonferroni.csv')
        with open(csv_path, 'w', encoding='utf-8') as fcsv:
            fcsv.write('scenario,metric,t,df,p,holm_threshold,reject_null,shapiro_a,shapiro_b,mannwhitney_p\n')
            for r in decisions:
                df_str = ('inf' if (isinstance(r['df'], float) and math.isinf(r['df'])) or r['df'] == float('inf') else f"{r['df']:.4g}")
                p_val = r['p']
                p_str = ('<1e-6' if isinstance(p_val, float) and p_val < 1e-6 else f"{p_val:.6g}")
                sha = r.get('shapiro_p_a', None)
                shb = r.get('shapiro_p_b', None)
                mwu = r.get('mannwhitney_p', None)
                sha_str = '' if sha is None else ("<1e-6" if sha < 1e-6 else f"{sha:.6g}")
                shb_str = '' if shb is None else ("<1e-6" if shb < 1e-6 else f"{shb:.6g}")
                mwu_str = '' if mwu is None else ("<1e-6" if mwu < 1e-6 else f"{mwu:.6g}")
                fcsv.write(f"{r['scenario']},{r['metric']},{r['t']:.6g},{df_str},{p_str},{r['holm_threshold']:.6g},{'YES' if r['reject_null'] else 'NO'},{sha_str},{shb_str},{mwu_str}\n")
        print('Saved', csv_path)

        md_path = os.path.join(results_dir, 'significance_holm_bonferroni.md')
        with open(md_path, 'w', encoding='utf-8') as fmd:
            fmd.write('# 显著性检验与Holm-Bonferroni多重校正汇总\n\n')
            fmd.write(f"总比较数：{len(decisions)}，整体显著性水平 alpha={alpha}.\n\n")
            # Markdown table
            fmd.write('| 场景 | 指标 | t | 自由度 df | 近似 p 值 | Holm 阈值 | 是否拒绝原假设 |\n')
            fmd.write('|---|---:|---:|---:|---:|---:|:---:|\n')
            for r in decisions:
                df_str = ('inf' if (isinstance(r['df'], float) and math.isinf(r['df'])) or r['df'] == float('inf') else f"{r['df']:.4g}")
                p_val = r['p']
                p_str = ('<1e-6' if isinstance(p_val, float) and p_val < 1e-6 else f"{p_val:.6g}")
                fmd.write(f"| {r['scenario']} | {r['metric']} | {r['t']:.6g} | {df_str} | {p_str} | {r['holm_threshold']:.6g} | {'✅' if r['reject_null'] else '❌'} |\n")
            # Paper-ready narrative snippets (Chinese)
            fmd.write('\n## 文稿可用表述（示例）\n')
            for r in decisions:
                metric_cn = {
                    'total_energy_consumed': '总能耗',
                    'pdr_end2end_mean': '端到端PDR（均值）',
                    'pdr_end2end_p05': '端到端PDR（第5百分位）',
                    'lifetime': '网络寿命'
                }.get(r['metric'], r['metric'])
                direction = '显著差异' if r['reject_null'] else '无显著差异'
                df_str = ('无限大' if (isinstance(r['df'], float) and math.isinf(r['df'])) or r['df'] == float('inf') else f"df={r['df']:.2f}")
                p_val = r['p']
                p_str = ('p<1e-6' if isinstance(p_val, float) and p_val < 1e-6 else f"p≈{p_val:.3g}")
                fmd.write(f"- 在场景“{r['scenario']}”中，指标“{metric_cn}”的Welch t检验得到t={r['t']:.2f}（{df_str}），近似{p_str}；经Holm-Bonferroni校正后阈值为{r['holm_threshold']:.3g}，因此判定{direction}。\n")
            # Appendix: normality and MWU
            fmd.write('\n## 附：正态性与Mann–Whitney U 检验\n')
            fmd.write('以下报告每个比较的Shapiro正态性检验（A/BASE与B/ROBUST）以及Mann–Whitney U 双侧检验p值。\\n\n')
            for r in decisions:
                sha = r.get('shapiro_p_a'); shb = r.get('shapiro_p_b'); mwu = r.get('mannwhitney_p')
                def fmt(v):
                    if v is None: return 'NA'
                    return 'p<1e-6' if v < 1e-6 else f"p≈{v:.3g}"
                norm_a = (sha is None) or (sha > alpha)
                norm_b = (shb is None) or (shb > alpha)
                fmd.write(f"- {r['scenario']} / {r['metric']}: Shapiro(A) {fmt(sha)} [{'通过' if norm_a else '不通过'}], Shapiro(B) {fmt(shb)} [{'通过' if norm_b else '不通过'}], MWU {fmt(mwu)}.\n")
        print('Saved', md_path)
        
        # --- Benjamini-Hochberg FDR (BH) summary ---
        # 使用已按p升序的records，计算q值与BH阈值，并输出JSON/CSV/Markdown
        m = len(records)
        ps = [r['p'] for r in records]
        # 计算q值（从大到小累积最小化，确保单调）
        qvals = [0.0] * m
        prev = 1.0
        for i in range(m - 1, -1, -1):
            rank = i + 1
            q = ps[i] * m / max(1, rank)
            if q > prev:
                q = prev
            prev = q
            qvals[i] = min(1.0, q)
        # 找到最大k使得 p_(k) <= (k/m)*alpha
        k = 0
        for i, pval in enumerate(ps, start=1):
            if pval <= (i / m) * alpha:
                k = i
        # 组装BH记录
        bh_records = []
        for i, r in enumerate(records):
            rank = i + 1
            bh_thr = (rank / m) * alpha
            reject = (k > 0 and r['p'] <= bh_thr)
            bh_records.append({**r, 'rank': rank, 'q_value': qvals[i], 'bh_threshold': bh_thr, 'reject_null': reject})
        
        # 写入BH JSON
        out_bh = os.path.join(results_dir, 'multitest_bh_fdr.json')
        json.dump(bh_records, open(out_bh, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('Saved', out_bh)
        
        # 写入BH CSV
        csv2_path = os.path.join(results_dir, 'significance_bh_fdr.csv')
        with open(csv2_path, 'w', encoding='utf-8') as fcsv:
            fcsv.write('scenario,metric,t,df,p,rank,q_value,bh_threshold,reject_null,shapiro_a,shapiro_b,mannwhitney_p\n')
            for r in bh_records:
                df_str = ('inf' if (isinstance(r['df'], float) and math.isinf(r['df'])) or r['df'] == float('inf') else f"{r['df']:.4g}")
                p_val = r['p']
                p_str = ('<1e-6' if isinstance(p_val, float) and p_val < 1e-6 else f"{p_val:.6g}")
                sha = r.get('shapiro_p_a', None)
                shb = r.get('shapiro_p_b', None)
                mwu = r.get('mannwhitney_p', None)
                sha_str = '' if sha is None else ("<1e-6" if sha < 1e-6 else f"{sha:.6g}")
                shb_str = '' if shb is None else ("<1e-6" if shb < 1e-6 else f"{shb:.6g}")
                mwu_str = '' if mwu is None else ("<1e-6" if mwu < 1e-6 else f"{mwu:.6g}")
                fcsv.write(f"{r['scenario']},{r['metric']},{r['t']:.6g},{df_str},{p_str},{r['rank']},{r['q_value']:.6g},{r['bh_threshold']:.6g},{'YES' if r['reject_null'] else 'NO'},{sha_str},{shb_str},{mwu_str}\n")
        print('Saved', csv2_path)
        
        # 写入BH Markdown
        md2_path = os.path.join(results_dir, 'significance_bh_fdr.md')
        with open(md2_path, 'w', encoding='utf-8') as fmd:
            fmd.write('# BH-FDR 多重比较校正汇总\n\n')
            fmd.write(f"总比较数：{m}，整体显著性水平 alpha={alpha}.\n\n")
            fmd.write('| 场景 | 指标 | t | 自由度 df | 近似 p 值 | 排名 | q 值 | BH 阈值 | 是否拒绝原假设 |\n')
            fmd.write('|---|---:|---:|---:|---:|---:|---:|---:|:---:|\n')
            for r in bh_records:
                df_str = ('inf' if (isinstance(r['df'], float) and math.isinf(r['df'])) or r['df'] == float('inf') else f"{r['df']:.4g}")
                p_val = r['p']
                p_str = ('p<1e-6' if isinstance(p_val, float) and p_val < 1e-6 else f"p≈{p_val:.3g}")
                fmd.write(f"| {r['scenario']} | {r['metric']} | {r['t']:.6g} | {df_str} | {p_str} | {r['rank']} | {r['q_value']:.6g} | {r['bh_threshold']:.6g} | {'✅' if r['reject_null'] else '❌'} |\n")
        print('Saved', md2_path)
    except Exception as e:
        print('Failed to write output:', e)
        sys.exit(1)

