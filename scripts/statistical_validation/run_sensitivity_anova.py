#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数敏感性ANOVA分析

数据来源: results/intel_sensitivity.json
分析因素: Gateway数量 (1, 2, 3), Packet大小 (256, 512, 1024)
"""

import json
import numpy as np
from scipy import stats
from itertools import combinations

def load_sensitivity_data():
    """加载参数敏感性数据"""
    with open('results/intel_sensitivity.json', 'r') as f:
        data = json.load(f)
    return data

def extract_pdr_by_factors(data):
    """按因素提取PDR数据"""
    results = {}
    
    packet_sizes = [256, 512, 1024]
    gateway_counts = [1, 2, 3]
    
    for psize in packet_sizes:
        for gcount in gateway_counts:
            key = f'E1.0_P{psize}_G{gcount}'
            if key in data:
                pdr_values = data[key]['pdr_end2end']['values']
                results[(psize, gcount)] = pdr_values
    
    return results

def one_way_anova_gateway(data):
    """Gateway数量的单因素ANOVA"""
    print("\n" + "="*60)
    print("单因素ANOVA: Gateway数量对PDR的影响")
    print("="*60)
    
    # 合并所有packet size的数据
    g1_data = []
    g2_data = []
    g3_data = []
    
    for (psize, gcount), values in data.items():
        if gcount == 1:
            g1_data.extend(values)
        elif gcount == 2:
            g2_data.extend(values)
        elif gcount == 3:
            g3_data.extend(values)
    
    # 执行ANOVA
    f_stat, p_value = stats.f_oneway(g1_data, g2_data, g3_data)
    
    print(f"\nGateway=1: n={len(g1_data)}, mean={np.mean(g1_data):.4f}, std={np.std(g1_data):.4f}")
    print(f"Gateway=2: n={len(g2_data)}, mean={np.mean(g2_data):.4f}, std={np.std(g2_data):.4f}")
    print(f"Gateway=3: n={len(g3_data)}, mean={np.mean(g3_data):.4f}, std={np.std(g3_data):.4f}")
    print(f"\nF-statistic: {f_stat:.4f}")
    print(f"p-value: {p_value:.2e}")
    print(f"显著性: {'是 (p < 0.05)' if p_value < 0.05 else '否'}")
    
    # 事后检验 (Tukey HSD 近似)
    print("\n事后检验 (Welch t-test with Bonferroni correction):")
    groups = {'G1': g1_data, 'G2': g2_data, 'G3': g3_data}
    alpha = 0.05 / 3  # Bonferroni correction
    
    for (name1, data1), (name2, data2) in combinations(groups.items(), 2):
        t_stat, p = stats.ttest_ind(data1, data2, equal_var=False)
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < alpha else "ns"
        print(f"  {name1} vs {name2}: t={t_stat:.3f}, p={p:.2e} {sig}")
    
    return {
        'f_statistic': f_stat,
        'p_value': p_value,
        'significant': p_value < 0.05,
        'group_means': {
            'G1': np.mean(g1_data),
            'G2': np.mean(g2_data),
            'G3': np.mean(g3_data)
        }
    }

def one_way_anova_packet_size(data):
    """Packet大小的单因素ANOVA"""
    print("\n" + "="*60)
    print("单因素ANOVA: Packet大小对PDR的影响")
    print("="*60)
    
    # 合并所有gateway count的数据
    p256_data = []
    p512_data = []
    p1024_data = []
    
    for (psize, gcount), values in data.items():
        if psize == 256:
            p256_data.extend(values)
        elif psize == 512:
            p512_data.extend(values)
        elif psize == 1024:
            p1024_data.extend(values)
    
    # 执行ANOVA
    f_stat, p_value = stats.f_oneway(p256_data, p512_data, p1024_data)
    
    print(f"\nPacket=256B: n={len(p256_data)}, mean={np.mean(p256_data):.4f}, std={np.std(p256_data):.4f}")
    print(f"Packet=512B: n={len(p512_data)}, mean={np.mean(p512_data):.4f}, std={np.std(p512_data):.4f}")
    print(f"Packet=1024B: n={len(p1024_data)}, mean={np.mean(p1024_data):.4f}, std={np.std(p1024_data):.4f}")
    print(f"\nF-statistic: {f_stat:.4f}")
    print(f"p-value: {p_value:.2e}")
    print(f"显著性: {'是 (p < 0.05)' if p_value < 0.05 else '否'}")
    
    return {
        'f_statistic': f_stat,
        'p_value': p_value,
        'significant': p_value < 0.05,
        'group_means': {
            'P256': np.mean(p256_data),
            'P512': np.mean(p512_data),
            'P1024': np.mean(p1024_data)
        }
    }

def calculate_effect_sizes(data):
    """计算效应量"""
    print("\n" + "="*60)
    print("效应量分析 (Hedges' g)")
    print("="*60)
    
    # Gateway效应量
    g1_all = []
    g3_all = []
    for (psize, gcount), values in data.items():
        if gcount == 1:
            g1_all.extend(values)
        elif gcount == 3:
            g3_all.extend(values)
    
    n1, n2 = len(g1_all), len(g3_all)
    pooled_std = np.sqrt(((n1-1)*np.var(g1_all, ddof=1) + (n2-1)*np.var(g3_all, ddof=1)) / (n1+n2-2))
    cohens_d = (np.mean(g1_all) - np.mean(g3_all)) / pooled_std
    correction = 1 - 3 / (4*(n1+n2) - 9)
    hedges_g = cohens_d * correction
    
    print(f"\nGateway=1 vs Gateway=3:")
    print(f"  G1 mean: {np.mean(g1_all):.4f}")
    print(f"  G3 mean: {np.mean(g3_all):.4f}")
    print(f"  Hedges' g: {hedges_g:.3f}")
    print(f"  解释: {'大效应' if abs(hedges_g) >= 0.8 else '中效应' if abs(hedges_g) >= 0.5 else '小效应' if abs(hedges_g) >= 0.2 else '可忽略'}")
    
    return {
        'gateway_effect': {
            'hedges_g': hedges_g,
            'interpretation': 'large' if abs(hedges_g) >= 0.8 else 'medium' if abs(hedges_g) >= 0.5 else 'small' if abs(hedges_g) >= 0.2 else 'negligible'
        }
    }

def main():
    print("="*60)
    print("参数敏感性ANOVA分析")
    print("数据来源: results/intel_sensitivity.json")
    print("="*60)
    
    # 加载数据
    raw_data = load_sensitivity_data()
    data = extract_pdr_by_factors(raw_data)
    
    print(f"\n数据验证: {len(data)}个配置")
    for (psize, gcount), values in sorted(data.items()):
        print(f"  P{psize}_G{gcount}: n={len(values)}, mean={np.mean(values):.4f}")
    
    # 执行分析
    gateway_anova = one_way_anova_gateway(data)
    packet_anova = one_way_anova_packet_size(data)
    effect_sizes = calculate_effect_sizes(data)
    
    # 保存结果
    results = {
        'gateway_anova': {
            'f_statistic': float(gateway_anova['f_statistic']),
            'p_value': float(gateway_anova['p_value']),
            'significant': bool(gateway_anova['significant']),
            'group_means': {k: float(v) for k, v in gateway_anova['group_means'].items()}
        },
        'packet_size_anova': {
            'f_statistic': float(packet_anova['f_statistic']),
            'p_value': float(packet_anova['p_value']),
            'significant': bool(packet_anova['significant']),
            'group_means': {k: float(v) for k, v in packet_anova['group_means'].items()}
        },
        'effect_sizes': {
            'gateway_effect': {
                'hedges_g': float(effect_sizes['gateway_effect']['hedges_g']),
                'interpretation': effect_sizes['gateway_effect']['interpretation']
            }
        }
    }
    
    with open('results/sensitivity_anova_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*60)
    print("分析完成! 结果已保存到 results/sensitivity_anova_results.json")
    print("="*60)

if __name__ == '__main__':
    main()
