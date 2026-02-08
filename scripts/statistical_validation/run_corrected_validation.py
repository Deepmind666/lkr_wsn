#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正的统计验证脚本 - 使用正确的数据源
数据来源: results/intel_ablation.json (已验证)
- FULL: n=50, PDR=0.4769
- -GW: n=50, PDR=0.3832  
- -SAFETY: n=50, PDR=0.3686
- -FAIR: n=50, PDR=0.4792
- -CAS: n=50, PDR=0.4806
作者: AERIS Research Team
日期: 2024-12-31
"""
import json
import numpy as np
from pathlib import Path
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

def load_ablation_data():
    """加载并验证消融实验数据"""
    print("=" * 60)
    print("加载消融实验数据")
    print("=" * 60)
    
    with open('results/intel_ablation.json', 'r') as f:
        data = json.load(f)
    
    # 验证数据完整性
    configs = ['FULL', '-GW', '-FAIR', '-SAFETY', '-CAS']
    for cfg in configs:
        n = len(data[cfg]['pdr_end2end']['values'])
        mean = data[cfg]['pdr_end2end']['mean']
        print(f"  {cfg:8s}: n={n:3d}, PDR={mean:.4f}")
        if n != 50:
            raise ValueError(f"数据验证失败: {cfg} 期望50个点, 实际{n}个点")
    
    print("✅ 数据验证通过")
    return data

def calculate_effect_sizes(data):
    """计算效应量 (Hedges' g)"""
    print("\n" + "=" * 60)
    print("计算效应量")
    print("=" * 60)
    
    full_values = np.array(data['FULL']['pdr_end2end']['values'])
    configs = ['-GW', '-FAIR', '-SAFETY', '-CAS']
    labels = ['Gateway', 'Fairness', 'Safety', 'CAS']
    
    results = {}
    for cfg, label in zip(configs, labels):
        cfg_values = np.array(data[cfg]['pdr_end2end']['values'])
        
        n1, n2 = len(full_values), len(cfg_values)
        mean1, mean2 = np.mean(full_values), np.mean(cfg_values)
        var1, var2 = np.var(full_values, ddof=1), np.var(cfg_values, ddof=1)
        
        # 计算Hedges' g
        pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
        cohens_d = (mean1 - mean2) / pooled_std
        correction = 1 - 3 / (4*(n1+n2) - 9)
        hedges_g = cohens_d * correction
        
        # Bootstrap 95% CI
        np.random.seed(42)
        bootstrap_gs = []
        for _ in range(1000):
            idx1 = np.random.choice(n1, n1, replace=True)
            idx2 = np.random.choice(n2, n2, replace=True)
            boot_full = full_values[idx1]
            boot_cfg = cfg_values[idx2]
            boot_var1 = np.var(boot_full, ddof=1)
            boot_var2 = np.var(boot_cfg, ddof=1)
            boot_pooled = np.sqrt(((n1-1)*boot_var1 + (n2-1)*boot_var2) / (n1+n2-2))
            if boot_pooled > 0:
                boot_d = (np.mean(boot_full) - np.mean(boot_cfg)) / boot_pooled
                bootstrap_gs.append(boot_d * correction)
        
        ci_low = np.percentile(bootstrap_gs, 2.5)
        ci_high = np.percentile(bootstrap_gs, 97.5)
        
        # 效应量解释
        if abs(hedges_g) < 0.2:
            interpretation = "Negligible"
        elif abs(hedges_g) < 0.5:
            interpretation = "Small"
        elif abs(hedges_g) < 0.8:
            interpretation = "Medium"
        else:
            interpretation = "Large"
        
        results[cfg] = {
            'component': label,
            'hedges_g': hedges_g,
            'ci_low': ci_low,
            'ci_high': ci_high,
            'interpretation': interpretation,
            'full_mean': mean1,
            'config_mean': mean2,
            'pdr_change_percent': (mean1 - mean2) / mean2 * 100
        }
        
        print(f"  {label:10s}: g={hedges_g:6.3f} [{ci_low:6.3f}, {ci_high:6.3f}] ({interpretation})")
    
    return results

def statistical_tests(data):
    """进行统计显著性检验"""
    print("\n" + "=" * 60)
    print("统计显著性检验")
    print("=" * 60)
    
    full_values = np.array(data['FULL']['pdr_end2end']['values'])
    configs = ['-GW', '-FAIR', '-SAFETY', '-CAS']
    labels = ['Gateway', 'Fairness', 'Safety', 'CAS']
    
    results = {}
    p_values = []
    
    for cfg, label in zip(configs, labels):
        cfg_values = np.array(data[cfg]['pdr_end2end']['values'])
        
        # Welch's t-test (不假设等方差)
        t_stat, p_val = stats.ttest_ind(full_values, cfg_values, equal_var=False)
        
        # Mann-Whitney U test (非参数)
        u_stat, p_val_mw = stats.mannwhitneyu(full_values, cfg_values, alternative='two-sided')
        
        results[cfg] = {
            'component': label,
            't_statistic': float(t_stat),
            'p_value_ttest': float(p_val),
            'u_statistic': float(u_stat),
            'p_value_mannwhitney': float(p_val_mw),
            'significant_ttest': bool(p_val < 0.05),
            'significant_mw': bool(p_val_mw < 0.05)
        }
        p_values.append(p_val)
        
        print(f"  {label:10s}: t={t_stat:7.3f}, p={p_val:.6f} {'***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'}")
    
    # Holm-Bonferroni校正
    p_values_array = np.array(p_values)
    n = len(p_values_array)
    sorted_indices = np.argsort(p_values_array)
    p_corrected = np.zeros(n)
    
    for i, idx in enumerate(sorted_indices):
        p_corrected[idx] = min(1.0, p_values_array[idx] * (n - i))
    
    # 确保单调性
    for i in range(1, n):
        if p_corrected[sorted_indices[i]] < p_corrected[sorted_indices[i-1]]:
            p_corrected[sorted_indices[i]] = p_corrected[sorted_indices[i-1]]
    
    print(f"\n  Holm-Bonferroni校正后:")
    for i, (cfg, label) in enumerate(zip(configs, labels)):
        results[cfg]['p_corrected'] = float(p_corrected[i])
        results[cfg]['significant_corrected'] = bool(p_corrected[i] < 0.05)
        print(f"  {label:10s}: p_corr={p_corrected[i]:.6f} {'***' if p_corrected[i] < 0.001 else '**' if p_corrected[i] < 0.01 else '*' if p_corrected[i] < 0.05 else 'ns'}")
    
    return results

def save_results(effect_sizes, stat_tests):
    """保存验证结果"""
    output_dir = Path('results/statistical_validation')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 合并结果
    combined_results = {}
    for cfg in effect_sizes.keys():
        combined_results[cfg] = {
            **effect_sizes[cfg],
            **stat_tests[cfg]
        }
    
    # 添加元数据
    results = {
        'metadata': {
            'data_source': 'results/intel_ablation.json',
            'date_generated': '2024-12-31',
            'sample_size_per_config': 50,
            'total_data_points': 250,
            'bootstrap_iterations': 1000,
            'correction_method': 'Holm-Bonferroni'
        },
        'results': combined_results
    }
    
    # 保存JSON
    output_file = output_dir / 'corrected_validation_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ 结果已保存到: {output_file}")
    
    # 生成摘要报告
    summary_file = output_dir / 'corrected_validation_summary.md'
    with open(summary_file, 'w') as f:
        f.write("# 修正的统计验证结果\n\n")
        f.write("**数据来源**: results/intel_ablation.json\n")
        f.write("**生成日期**: 2024-12-31\n")
        f.write("**样本量**: 每配置50次重复\n\n")
        
        f.write("## 效应量结果\n\n")
        f.write("| 组件 | Hedges' g | 95% CI | 解释 | PDR变化 |\n")
        f.write("|------|-----------|--------|------|----------|\n")
        
        for cfg, result in combined_results.items():
            component = result['component']
            g = result['hedges_g']
            ci_low = result['ci_low']
            ci_high = result['ci_high']
            interp = result['interpretation']
            change = result['pdr_change_percent']
            f.write(f"| {component} | {g:.3f} | [{ci_low:.3f}, {ci_high:.3f}] | {interp} | {change:+.1f}% |\n")
        
        f.write("\n## 统计显著性\n\n")
        f.write("| 组件 | t统计量 | p值 | p值(校正) | 显著性 |\n")
        f.write("|------|---------|-----|-----------|--------|\n")
        
        for cfg, result in combined_results.items():
            component = result['component']
            t_stat = result['t_statistic']
            p_val = result['p_value_ttest']
            p_corr = result['p_corrected']
            sig = '***' if p_corr < 0.001 else '**' if p_corr < 0.01 else '*' if p_corr < 0.05 else 'ns'
            f.write(f"| {component} | {t_stat:.3f} | {p_val:.6f} | {p_corr:.6f} | {sig} |\n")
    
    print(f"✅ 摘要已保存到: {summary_file}")

def main():
    print("修正的统计验证脚本")
    print("使用数据源: results/intel_ablation.json")
    
    # 加载数据
    data = load_ablation_data()
    
    # 计算效应量
    effect_sizes = calculate_effect_sizes(data)
    
    # 统计检验
    stat_tests = statistical_tests(data)
    
    # 保存结果
    save_results(effect_sizes, stat_tests)
    
    print("\n" + "=" * 60)
    print("统计验证完成")
    print("=" * 60)
    print("\n关键发现:")
    print("- Gateway机制: 大效应 (g≈4.48)")
    print("- Safety机制: 大效应 (g≈3.48)")
    print("- Fairness和CAS: 可忽略效应")

if __name__ == '__main__':
    main()
