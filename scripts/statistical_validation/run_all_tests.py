#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计验证管道

实现完整的统计检验流程：
1. Welch t检验
2. 效应量计算（Cliff's δ, Hedges g）
3. Bootstrap置信区间
4. Holm-Bonferroni多重比较校正

输出：
- results/statistical_validation/
"""

import sys
import os
import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from scipy import stats
from itertools import combinations

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


@dataclass
class WelchResult:
    """Welch t检验结果"""
    group1: str
    group2: str
    metric: str
    t_statistic: float
    p_value: float
    df: float
    mean1: float
    mean2: float
    std1: float
    std2: float
    n1: int
    n2: int
    significant: bool


@dataclass
class EffectSizeResult:
    """效应量结果"""
    group1: str
    group2: str
    metric: str
    cliffs_delta: float
    hedges_g: float
    interpretation: str


@dataclass
class BootstrapCIResult:
    """Bootstrap置信区间结果"""
    group: str
    metric: str
    mean: float
    ci_low: float
    ci_high: float
    method: str


@dataclass
class CorrectedPValue:
    """校正后的p值"""
    comparison: str
    original_p: float
    corrected_p: float
    significant: bool


class StatisticalValidator:
    """统计验证器"""
    
    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha
        self.results = {
            'welch_tests': [],
            'effect_sizes': [],
            'bootstrap_cis': [],
            'corrected_pvalues': []
        }
    
    def welch_t_test(self, group1: np.ndarray, group2: np.ndarray,
                    group1_name: str, group2_name: str,
                    metric_name: str) -> WelchResult:
        """Welch t检验（不假设方差相等）"""
        t_stat, p_value = stats.ttest_ind(group1, group2, equal_var=False)
        
        # 计算自由度（Welch-Satterthwaite方程）
        n1, n2 = len(group1), len(group2)
        v1, v2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        
        if v1 == 0 and v2 == 0:
            df = n1 + n2 - 2
        else:
            df = ((v1/n1 + v2/n2)**2) / \
                 ((v1/n1)**2/(n1-1) + (v2/n2)**2/(n2-1)) if (v1/n1 + v2/n2) > 0 else n1 + n2 - 2
        
        result = WelchResult(
            group1=group1_name,
            group2=group2_name,
            metric=metric_name,
            t_statistic=float(t_stat),
            p_value=float(p_value),
            df=float(df),
            mean1=float(np.mean(group1)),
            mean2=float(np.mean(group2)),
            std1=float(np.std(group1, ddof=1)),
            std2=float(np.std(group2, ddof=1)),
            n1=n1,
            n2=n2,
            significant=p_value < self.alpha
        )
        
        self.results['welch_tests'].append(result)
        return result
    
    def compute_cliffs_delta(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """计算Cliff's δ（非参数效应量）"""
        n1, n2 = len(group1), len(group2)
        
        # 计算所有配对比较
        more = 0
        less = 0
        
        for x in group1:
            for y in group2:
                if x > y:
                    more += 1
                elif x < y:
                    less += 1
        
        delta = (more - less) / (n1 * n2)
        return float(delta)
    
    def compute_hedges_g(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """计算Hedges' g（偏差校正的Cohen's d）"""
        n1, n2 = len(group1), len(group2)
        mean1, mean2 = np.mean(group1), np.mean(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        
        # 池化标准差
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0.0
        
        # Cohen's d
        d = (mean1 - mean2) / pooled_std
        
        # Hedges' g校正因子
        correction = 1 - 3 / (4 * (n1 + n2) - 9)
        g = d * correction
        
        return float(g)
    
    def interpret_effect_size(self, g: float) -> str:
        """解释效应量"""
        abs_g = abs(g)
        if abs_g < 0.2:
            return "negligible"
        elif abs_g < 0.5:
            return "small"
        elif abs_g < 0.8:
            return "medium"
        else:
            return "large"
    
    def compute_effect_size(self, group1: np.ndarray, group2: np.ndarray,
                           group1_name: str, group2_name: str,
                           metric_name: str) -> EffectSizeResult:
        """计算效应量"""
        delta = self.compute_cliffs_delta(group1, group2)
        g = self.compute_hedges_g(group1, group2)
        interpretation = self.interpret_effect_size(g)
        
        result = EffectSizeResult(
            group1=group1_name,
            group2=group2_name,
            metric=metric_name,
            cliffs_delta=delta,
            hedges_g=g,
            interpretation=interpretation
        )
        
        self.results['effect_sizes'].append(result)
        return result
    
    def bootstrap_ci(self, data: np.ndarray, group_name: str, metric_name: str,
                    n_bootstrap: int = 10000, confidence: float = 0.95,
                    method: str = 'bca') -> BootstrapCIResult:
        """Bootstrap置信区间"""
        rng = np.random.default_rng(42)
        n = len(data)
        
        # Bootstrap重采样
        bootstrap_means = []
        for _ in range(n_bootstrap):
            sample = rng.choice(data, size=n, replace=True)
            bootstrap_means.append(np.mean(sample))
        
        bootstrap_means = np.array(bootstrap_means)
        original_mean = np.mean(data)
        
        if method == 'percentile':
            # 百分位法
            alpha = 1 - confidence
            ci_low = np.percentile(bootstrap_means, 100 * alpha / 2)
            ci_high = np.percentile(bootstrap_means, 100 * (1 - alpha / 2))
        
        elif method == 'bca':
            # BCa方法（偏差校正加速）
            alpha = 1 - confidence
            
            # 偏差校正
            prop_below = np.mean(bootstrap_means < original_mean)
            if prop_below == 0:
                prop_below = 1e-10
            elif prop_below == 1:
                prop_below = 1 - 1e-10
            z0 = stats.norm.ppf(prop_below)
            
            # 加速因子（使用jackknife）
            jackknife_means = []
            for i in range(n):
                jack_sample = np.delete(data, i)
                jackknife_means.append(np.mean(jack_sample))
            jackknife_means = np.array(jackknife_means)
            jack_mean = np.mean(jackknife_means)
            
            num = np.sum((jack_mean - jackknife_means) ** 3)
            denom = 6 * (np.sum((jack_mean - jackknife_means) ** 2) ** 1.5)
            a = num / denom if denom != 0 else 0
            
            # 调整百分位
            z_alpha_low = stats.norm.ppf(alpha / 2)
            z_alpha_high = stats.norm.ppf(1 - alpha / 2)
            
            # 防止除零
            denom_low = 1 - a * (z0 + z_alpha_low)
            denom_high = 1 - a * (z0 + z_alpha_high)
            
            if abs(denom_low) < 1e-10 or abs(denom_high) < 1e-10:
                # 回退到百分位法
                ci_low = np.percentile(bootstrap_means, 100 * alpha / 2)
                ci_high = np.percentile(bootstrap_means, 100 * (1 - alpha / 2))
            else:
                p_low = stats.norm.cdf(z0 + (z0 + z_alpha_low) / denom_low)
                p_high = stats.norm.cdf(z0 + (z0 + z_alpha_high) / denom_high)
                
                # 确保在有效范围内
                p_low = np.clip(p_low, 0.001, 0.999)
                p_high = np.clip(p_high, 0.001, 0.999)
                
                ci_low = np.percentile(bootstrap_means, 100 * p_low)
                ci_high = np.percentile(bootstrap_means, 100 * p_high)
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        result = BootstrapCIResult(
            group=group_name,
            metric=metric_name,
            mean=float(original_mean),
            ci_low=float(ci_low),
            ci_high=float(ci_high),
            method=method
        )
        
        self.results['bootstrap_cis'].append(result)
        return result
    
    def holm_bonferroni_correction(self, p_values: List[Tuple[str, float]]) -> List[CorrectedPValue]:
        """Holm-Bonferroni多重比较校正"""
        n = len(p_values)
        
        # 按p值排序
        sorted_pvals = sorted(p_values, key=lambda x: x[1])
        
        corrected = []
        for i, (comparison, p) in enumerate(sorted_pvals):
            # Holm-Bonferroni校正
            corrected_p = min(1.0, p * (n - i))
            
            # 确保单调性
            if i > 0 and corrected_p < corrected[-1].corrected_p:
                corrected_p = corrected[-1].corrected_p
            
            result = CorrectedPValue(
                comparison=comparison,
                original_p=float(p),
                corrected_p=float(corrected_p),
                significant=corrected_p < self.alpha
            )
            corrected.append(result)
        
        self.results['corrected_pvalues'] = corrected
        return corrected
    
    def run_full_validation(self, data: Dict[str, Dict[str, np.ndarray]],
                           metrics: List[str] = None) -> Dict:
        """运行完整验证流程"""
        if metrics is None:
            metrics = ['pdr', 'energy']
        
        groups = list(data.keys())
        
        # 1. 对所有组对进行Welch t检验和效应量计算
        print("\n[1/4] Running Welch t-tests and effect size calculations...")
        p_values_for_correction = []
        
        for metric in metrics:
            for g1, g2 in combinations(groups, 2):
                if metric in data[g1] and metric in data[g2]:
                    d1 = np.array(data[g1][metric])
                    d2 = np.array(data[g2][metric])
                    
                    # Welch t检验
                    welch = self.welch_t_test(d1, d2, g1, g2, metric)
                    p_values_for_correction.append((f"{g1}_vs_{g2}_{metric}", welch.p_value))
                    
                    # 效应量
                    self.compute_effect_size(d1, d2, g1, g2, metric)
                    
                    print(f"  {g1} vs {g2} ({metric}): t={welch.t_statistic:.3f}, "
                          f"p={welch.p_value:.4f}, g={self.results['effect_sizes'][-1].hedges_g:.3f}")
        
        # 2. Bootstrap置信区间
        print("\n[2/4] Computing bootstrap confidence intervals...")
        for group in groups:
            for metric in metrics:
                if metric in data[group]:
                    d = np.array(data[group][metric])
                    ci = self.bootstrap_ci(d, group, metric)
                    print(f"  {group} ({metric}): {ci.mean:.3f} [{ci.ci_low:.3f}, {ci.ci_high:.3f}]")
        
        # 3. Holm-Bonferroni校正
        print("\n[3/4] Applying Holm-Bonferroni correction...")
        corrected = self.holm_bonferroni_correction(p_values_for_correction)
        
        n_significant_before = sum(1 for _, p in p_values_for_correction if p < self.alpha)
        n_significant_after = sum(1 for c in corrected if c.significant)
        print(f"  Significant before correction: {n_significant_before}/{len(p_values_for_correction)}")
        print(f"  Significant after correction: {n_significant_after}/{len(corrected)}")
        
        # 4. 生成摘要
        print("\n[4/4] Generating summary...")
        summary = self._generate_summary()
        
        return summary
    
    def _generate_summary(self) -> Dict:
        """生成摘要"""
        return {
            'timestamp': datetime.now().isoformat(),
            'alpha': self.alpha,
            'welch_tests': [asdict(r) for r in self.results['welch_tests']],
            'effect_sizes': [asdict(r) for r in self.results['effect_sizes']],
            'bootstrap_cis': [asdict(r) for r in self.results['bootstrap_cis']],
            'corrected_pvalues': [asdict(r) for r in self.results['corrected_pvalues']],
            'summary': {
                'n_comparisons': len(self.results['welch_tests']),
                'n_significant_uncorrected': sum(1 for r in self.results['welch_tests'] if r.significant),
                'n_significant_corrected': sum(1 for r in self.results['corrected_pvalues'] if r.significant),
                'large_effects': [
                    f"{r.group1}_vs_{r.group2}_{r.metric}"
                    for r in self.results['effect_sizes']
                    if r.interpretation == 'large'
                ]
            }
        }


def load_experiment_data(results_path: str) -> Dict[str, Dict[str, np.ndarray]]:
    """从实验结果加载数据"""
    with open(results_path, 'r') as f:
        raw_results = json.load(f)
    
    # 按协议聚合数据
    data = {}
    
    for result in raw_results:
        if result.get('error') is not None:
            continue
        
        protocol = result['protocol']
        if protocol not in data:
            data[protocol] = {'pdr': [], 'energy': []}
        
        data[protocol]['pdr'].append(result['pdr'])
        data[protocol]['energy'].append(result['energy_total'])
    
    # 转换为numpy数组
    for protocol in data:
        data[protocol]['pdr'] = np.array(data[protocol]['pdr'])
        data[protocol]['energy'] = np.array(data[protocol]['energy'])
    
    return data


def main():
    print("=" * 60)
    print("统计验证管道")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = Path('results/statistical_validation')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 加载实验数据
    print("\n加载实验数据...")
    results_path = 'results/experiment_matrix/raw_results.json'
    
    if not Path(results_path).exists():
        print(f"  错误: {results_path} 不存在")
        print("  请先运行实验矩阵")
        return None
    
    data = load_experiment_data(results_path)
    
    print(f"  加载 {len(data)} 个协议的数据:")
    for protocol, metrics in data.items():
        print(f"    {protocol}: {len(metrics['pdr'])} samples")
    
    # 运行统计验证
    validator = StatisticalValidator(alpha=0.05)
    summary = validator.run_full_validation(data)
    
    # 保存结果
    output_file = output_dir / 'statistical_validation_results.json'
    
    # 转换numpy类型为Python原生类型
    def convert_numpy(obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(i) for i in obj]
        return obj
    
    summary = convert_numpy(summary)
    
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n结果已保存至: {output_file}")
    
    # 打印结论
    print("\n" + "=" * 60)
    print("统计验证结论:")
    print("=" * 60)
    print(f"✓ 总比较数: {summary['summary']['n_comparisons']}")
    print(f"✓ 显著（未校正）: {summary['summary']['n_significant_uncorrected']}")
    print(f"✓ 显著（校正后）: {summary['summary']['n_significant_corrected']}")
    print(f"✓ Large效应: {summary['summary']['large_effects']}")
    
    return summary


if __name__ == '__main__':
    main()
