#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据完整性验证工具
用于验证实验JSON文件的一致性和可信度

Author: Claude Opus 4.5
Date: 2026-01-28
"""

import json
import sys
import os
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np
from scipy import stats


def load_json(filepath: str) -> Dict:
    """加载JSON文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def verify_config(data: Dict) -> Tuple[bool, List[str]]:
    """验证配置完整性"""
    issues = []
    config = data.get('config', {})

    # 检查必需字段
    required = ['replicates', 'rounds', 'node_counts', 'protocols']
    for field in required:
        if field not in config:
            issues.append(f"缺少配置字段: {field}")

    return len(issues) == 0, issues


def verify_runs_count(data: Dict) -> Tuple[bool, List[str]]:
    """验证runs数量"""
    issues = []
    config = data.get('config', {})
    runs = data.get('runs', [])

    expected = (
        config.get('replicates', 0) *
        len(config.get('node_counts', [])) *
        len(config.get('protocols', []))
    )
    actual = len(runs)

    if expected != actual:
        issues.append(f"runs数量不匹配: 期望{expected}, 实际{actual}")

    return len(issues) == 0, issues


def verify_success_rate(data: Dict) -> Tuple[bool, List[str]]:
    """验证所有runs的success状态"""
    issues = []
    runs = data.get('runs', [])

    failed = [r for r in runs if not r.get('success', False)]
    if failed:
        issues.append(f"存在{len(failed)}个失败的run")

    return len(issues) == 0, issues


def recalculate_statistics(data: Dict) -> Dict:
    """重新计算统计值"""
    runs = data.get('runs', [])
    results = defaultdict(lambda: defaultdict(list))

    for run in runs:
        if run.get('success', False):
            key = (run['num_nodes'], run['protocol'])
            metrics = run.get('metrics', run)
            results[key]['pdr'].append(metrics.get('pdr_end2end', 0))
            results[key]['energy'].append(metrics.get('energy', 0))

    stats_out = {}
    for (nodes, proto), vals in results.items():
        key = f"{proto}@{nodes}"
        stats_out[key] = {
            'pdr_mean': np.mean(vals['pdr']),
            'pdr_std': np.std(vals['pdr']),
            'energy_mean': np.mean(vals['energy']),
            'n': len(vals['pdr'])
        }

    return stats_out


def run_significance_test(data: Dict) -> Dict:
    """运行统计显著性检验"""
    runs = data.get('runs', [])
    results = defaultdict(lambda: defaultdict(list))

    for run in runs:
        if run.get('success', False):
            key = (run['num_nodes'], run['protocol'])
            metrics = run.get('metrics', run)
            results[key]['pdr'].append(metrics.get('pdr_end2end', 0))

    sig_results = {}
    node_counts = set(k[0] for k in results.keys())

    for nodes in sorted(node_counts):
        aeris_key = (nodes, 'AERIS')
        if aeris_key not in results:
            continue
        aeris_pdr = results[aeris_key]['pdr']

        for proto in ['LEACH', 'PEGASIS', 'HEED']:
            base_key = (nodes, proto)
            if base_key not in results:
                continue
            base_pdr = results[base_key]['pdr']

            t_stat, p_val = stats.ttest_ind(aeris_pdr, base_pdr, equal_var=False)
            sig_results[f"AERIS_vs_{proto}@{nodes}"] = {
                't_statistic': t_stat,
                'p_value': p_val,
                'significant': p_val < 0.05
            }

    return sig_results


def main(filepath: str):
    """主验证函数"""
    print(f"=" * 60)
    print(f"数据完整性验证报告")
    print(f"文件: {filepath}")
    print(f"=" * 60)

    # 加载数据
    try:
        data = load_json(filepath)
    except Exception as e:
        print(f"[ERROR] 无法加载文件: {e}")
        return False

    all_passed = True

    # 1. 配置验证
    print("\n[1] 配置完整性检查...")
    passed, issues = verify_config(data)
    if passed:
        print("    ✓ 配置完整")
    else:
        all_passed = False
        for issue in issues:
            print(f"    ✗ {issue}")

    # 2. Runs数量验证
    print("\n[2] Runs数量检查...")
    passed, issues = verify_runs_count(data)
    if passed:
        print(f"    ✓ runs={len(data.get('runs', []))} 符合预期")
    else:
        all_passed = False
        for issue in issues:
            print(f"    ✗ {issue}")

    # 3. Success状态验证
    print("\n[3] Success状态检查...")
    passed, issues = verify_success_rate(data)
    if passed:
        print("    ✓ 所有runs成功")
    else:
        all_passed = False
        for issue in issues:
            print(f"    ✗ {issue}")

    # 4. 重算统计值
    print("\n[4] 统计值重算...")
    stats_recalc = recalculate_statistics(data)
    for key, vals in sorted(stats_recalc.items()):
        print(f"    {key}: PDR={vals['pdr_mean']*100:.2f}% (n={vals['n']})")

    # 5. 显著性检验
    print("\n[5] 显著性检验...")
    sig_results = run_significance_test(data)
    for key, vals in sorted(sig_results.items()):
        status = "***" if vals['p_value'] < 0.001 else "ns"
        print(f"    {key}: p={vals['p_value']:.2e} {status}")

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] 数据完整性验证通过")
    else:
        print("[FAIL] 数据完整性验证失败")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 默认验证主数据文件
        default_path = os.path.join(
            os.path.dirname(__file__), "..", "results",
            "large_scale_n30_r500_unified.json"
        )
        main(default_path)
    else:
        main(sys.argv[1])
