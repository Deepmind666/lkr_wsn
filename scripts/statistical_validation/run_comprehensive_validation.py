#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合统计验证管道

使用现有实验数据进行完整的统计检验：
1. Welch t检验
2. 效应量计算（Cliff's δ, Hedges g）
3. Bootstrap置信区间（BCa方法）
4. Holm-Bonferroni多重比较校正

数据来源：
- intel_ablation_parallel.json (200 samples)
- significance_compare_intel_parallel.json (10 samples)
"""

import sys
import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field
from scipy import stats
from itertools import combinations

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


@dataclass
class WelchResult:
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
    group1: str
    group2: str
    metric: str
    cliffs_delta: float
    hedges_g: float
    cohens_d: float
    interpretation: str
    ci_low: float = 0.0
    ci_high: float = 0.0


@dataclass
class BootstrapCIResult:
    group: str
    metric: str
    mean: float
    ci_low: float
    ci_high: float
    method: str = "BCa"


class ComprehensiveValidator:
    """综合统计验证器"""
    
    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha
        self.welch_results: List[WelchResult] = []
        self.effect_results: List[EffectSizeResult] = []
        self.bootstrap_results: List[BootstrapCIResult] = []
        self.corrected_pvalues: List[Dict] = []
    
    def welch_t_test(self, g1: np.ndarray, g2: np.ndarray, 
                    name1: str, name2: str, metric: str) -> WelchResult:
        """Welch t检验（不假设方差齐性）"""
        t_stat, p_value = stats.ttest_ind(g1, g2, equal_var=False)
        
        # 计算Welch-Satterthwaite自由度
        n1, n2 = len(g1), len(g2)
        v1, v2 = np.var(g1, ddof=1), np.var(g2, ddof=1)
        
        if v1/n1 + v2/n2 > 0:
            df = ((v1/n1 + v2/n2)**2) / ((v1/n1)**2/(n1-1) + (v2/n2)**2/(n2-1))
        else:
            df = n1 + n2 - 2
        
        result = WelchResult(
            group1=name1, group2=name2, metric=metric,
            t_statistic=float(t_stat), p_value=float(p_value), df=float(df),
            mean1=float(np.mean(g1)), mean2=float(np.mean(g2)),
            std1=float(np.std(g1, ddof=1)), std2=float(np.std(g2, ddof=1)),
            n1=n1, n2=n2, significant=p_value < self.alpha
        )
        self.welch_results.append(result)
        return result
    
    def compute_cliffs_delta(self, g1: np.ndarray, g2: np.ndarray) -> float:
        """Cliff's δ（非参数效应量）"""
        more = sum(1 for x in g1 for y in g2 if x > y)
        less = sum(1 for x in g1 for y in g2 if x < y)
        n = len(g1) * len(g2)
        return (more - less) / n if n > 0 else 0.0
    
    def compute_hedges_g(self, g1: np.ndarray, g2: np.ndarray) -> Tuple[float, float]:
        """Hedges g（校正的Cohen's d）"""
        n1, n2 = len(g1), len(g2)
        
        # Cohen's d
        pooled_var = ((n1-1)*np.var(g1, ddof=1) + (n2-1)*np.var(g2, ddof=1)) / (n1+n2-2)
        pooled_std = np.sqrt(pooled_var) if pooled_var > 0 else 1e-10
        d = (np.mean(g1) - np.mean(g2)) / pooled_std
        
        # Hedges g correction
        correction = 1 - 3 / (4*(n1+n2) - 9)
        g = d * correction
        
        return float(d), float(g)
    
    def interpret_effect(self, g: float) -> str:
        """解释效应量大小"""
        abs_g = abs(g)
        if abs_g < 0.2:
            return "negligible"
        elif abs_g < 0.5:
            return "small"
        elif abs_g < 0.8:
            return "medium"
        else:
            return "large"
    
    def compute_effect_size(self, g1: np.ndarray, g2: np.ndarray,
                           name1: str, name2: str, metric: str) -> EffectSizeResult:
        """计算效应量"""
        delta = self.compute_cliffs_delta(g1, g2)
        d, g = self.compute_hedges_g(g1, g2)
        
        # Bootstrap CI for effect size
        rng = np.random.default_rng(42)
        boot_gs = []
        for _ in range(1000):
            b1 = rng.choice(g1, len(g1), replace=True)
            b2 = rng.choice(g2, len(g2), replace=True)
            _, boot_g = self.compute_hedges_g(b1, b2)
            boot_gs.append(boot_g)
        
        ci_low = float(np.percentile(boot_gs, 2.5))
        ci_high = float(np.percentile(boot_gs, 97.5))
        
        result = EffectSizeResult(
            group1=name1, group2=name2, metric=metric,
            cliffs_delta=delta, hedges_g=g, cohens_d=d,
            interpretation=self.interpret_effect(g),
            ci_low=ci_low, ci_high=ci_high
        )
        self.effect_results.append(result)
        return result
    
    def bootstrap_ci_bca(self, data: np.ndarray, group: str, metric: str,
                        n_boot: int = 10000) -> BootstrapCIResult:
        """BCa Bootstrap置信区间"""
        rng = np.random.default_rng(42)
        n = len(data)
        theta_hat = np.mean(data)
        
        # Bootstrap samples
        boot_means = np.array([np.mean(rng.choice(data, n, replace=True)) for _ in range(n_boot)])
        
        # Simple percentile method as fallback
        try:
            # Bias correction (z0)
            prop_below = np.mean(boot_means < theta_hat)
            if prop_below == 0:
                prop_below = 1 / (2 * n_boot)
            elif prop_below == 1:
                prop_below = 1 - 1 / (2 * n_boot)
            z0 = stats.norm.ppf(prop_below)
            
            # Acceleration (a) using jackknife
            jack_means = np.array([np.mean(np.delete(data, i)) for i in range(n)])
            jack_mean = np.mean(jack_means)
            num = np.sum((jack_mean - jack_means)**3)
            denom = 6 * (np.sum((jack_mean - jack_means)**2))**1.5
            a = num / denom if denom != 0 else 0
            
            # BCa percentiles
            alpha_low = 0.025
            alpha_high = 0.975
            
            z_low = stats.norm.ppf(alpha_low)
            z_high = stats.norm.ppf(alpha_high)
            
            denom_low = 1 - a*(z0 + z_low)
            denom_high = 1 - a*(z0 + z_high)
            
            if abs(denom_low) > 1e-10 and abs(denom_high) > 1e-10:
                p_low = stats.norm.cdf(z0 + (z0 + z_low) / denom_low)
                p_high = stats.norm.cdf(z0 + (z0 + z_high) / denom_high)
                
                # Ensure valid percentiles
                p_low = np.clip(p_low, 0.001, 0.999)
                p_high = np.clip(p_high, 0.001, 0.999)
                
                ci_low = float(np.percentile(boot_means, p_low * 100))
                ci_high = float(np.percentile(boot_means, p_high * 100))
            else:
                # Fallback to simple percentile
                ci_low = float(np.percentile(boot_means, 2.5))
                ci_high = float(np.percentile(boot_means, 97.5))
        except:
            # Fallback to simple percentile
            ci_low = float(np.percentile(boot_means, 2.5))
            ci_high = float(np.percentile(boot_means, 97.5))
        
        result = BootstrapCIResult(
            group=group, metric=metric, mean=float(theta_hat),
            ci_low=ci_low, ci_high=ci_high, method="BCa"
        )
        self.bootstrap_results.append(result)
        return result
    
    def holm_bonferroni(self, p_values: List[Tuple[str, float]]) -> List[Dict]:
        """Holm-Bonferroni多重比较校正"""
        n = len(p_values)
        if n == 0:
            return []
        
        # Sort by p-value
        sorted_p = sorted(p_values, key=lambda x: x[1])
        
        corrected = []
        for i, (comp, p) in enumerate(sorted_p):
            # Holm correction: p * (n - i)
            corr_p = min(1.0, p * (n - i))
            
            # Ensure monotonicity
            if i > 0 and corr_p < corrected[-1]['corrected_p']:
                corr_p = corrected[-1]['corrected_p']
            
            corrected.append({
                'comparison': comp,
                'original_p': float(p),
                'corrected_p': float(corr_p),
                'rank': i + 1,
                'significant': corr_p < self.alpha
            })
        
        self.corrected_pvalues = corrected
        return corrected


def load_ablation_data(path: str) -> Dict[str, Dict[str, np.ndarray]]:
    """加载消融实验数据"""
    with open(path, 'r') as f:
        raw = json.load(f)
    
    data = {}
    for config, results in raw.items():
        if isinstance(results, dict) and 'energy' in results:
            energy_data = results['energy']
            pdr_data = results.get('pdr_end2end', {})
            
            if isinstance(energy_data, dict) and 'values' in energy_data:
                data[config] = {
                    'energy': np.array(energy_data['values']),
                    'pdr': np.array(pdr_data.get('values', []))
                }
    
    return data


def load_significance_data(path: str) -> Dict[str, Dict[str, np.ndarray]]:
    """加载显著性比较数据"""
    with open(path, 'r') as f:
        raw = json.load(f)
    
    data = {}
    for metric, results in raw.items():
        if metric == 'meta':
            continue
        
        for protocol in ['BASE', 'ROBUST', 'AERIS', 'LEACH']:
            if protocol in results:
                if protocol not in data:
                    data[protocol] = {'energy': [], 'pdr': []}
                
                if 'values' in results[protocol]:
                    if 'energy' in metric.lower():
                        data[protocol]['energy'] = np.array(results[protocol]['values'])
                    elif 'pdr' in metric.lower():
                        data[protocol]['pdr'] = np.array(results[protocol]['values'])
    
    return data


def main():
    print("=" * 60)
    print("综合统计验证管道")
    print("=" * 60)
    
    output_dir = Path('results/statistical_validation')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    validator = ComprehensiveValidator(alpha=0.05)
    all_data = {}
    
    # 1. 加载消融实验数据
    print("\n[1/6] 加载消融实验数据...")
    ablation_path = 'results/intel_ablation.json'
    ablation_data = {}
    if Path(ablation_path).exists():
        ablation_data = load_ablation_data(ablation_path)
        print(f"  加载 {len(ablation_data)} 个配置:")
        for config, metrics in ablation_data.items():
            print(f"    {config}: energy n={len(metrics['energy'])}, pdr n={len(metrics['pdr'])}")
            all_data[f"ablation_{config}"] = metrics
    else:
        print(f"  ⚠️ 未找到消融数据: {ablation_path}")
    
    # 2. 加载显著性比较数据
    print("\n[2/6] 加载显著性比较数据...")
    sig_path = 'results/significance_compare_intel_parallel.json'
    if Path(sig_path).exists():
        sig_data = load_significance_data(sig_path)
        print(f"  加载 {len(sig_data)} 个协议:")
        for protocol, metrics in sig_data.items():
            print(f"    {protocol}: energy n={len(metrics['energy'])}, pdr n={len(metrics['pdr'])}")
            all_data[f"sig_{protocol}"] = metrics
    
    # 3. Welch t检验和效应量
    print("\n[3/6] Welch t检验和效应量计算...")
    p_values = []
    
    # 消融实验比较
    if ablation_data:
        configs = list(ablation_data.keys())
        for metric in ['energy', 'pdr']:
            for c1, c2 in combinations(configs, 2):
                d1, d2 = ablation_data[c1][metric], ablation_data[c2][metric]
                if len(d1) > 1 and len(d2) > 1:
                    welch = validator.welch_t_test(d1, d2, c1, c2, metric)
                    effect = validator.compute_effect_size(d1, d2, c1, c2, metric)
                    p_values.append((f"{c1}_vs_{c2}_{metric}", welch.p_value))
                    
                    sig_mark = "***" if welch.p_value < 0.001 else "**" if welch.p_value < 0.01 else "*" if welch.p_value < 0.05 else ""
                    print(f"  {c1} vs {c2} ({metric}): t={welch.t_statistic:.2f}, p={welch.p_value:.4f}{sig_mark}, g={effect.hedges_g:.3f} ({effect.interpretation})")
    
    # 4. Bootstrap置信区间
    print("\n[4/6] Bootstrap置信区间 (BCa)...")
    for name, metrics in all_data.items():
        for metric in ['energy', 'pdr']:
            if metric in metrics and len(metrics[metric]) > 1:
                ci = validator.bootstrap_ci_bca(metrics[metric], name, metric)
                print(f"  {name} ({metric}): {ci.mean:.4f} [{ci.ci_low:.4f}, {ci.ci_high:.4f}]")
    
    # 5. Holm-Bonferroni校正
    print("\n[5/6] Holm-Bonferroni多重比较校正...")
    if p_values:
        corrected = validator.holm_bonferroni(p_values)
        n_sig_before = sum(1 for _, p in p_values if p < 0.05)
        n_sig_after = sum(1 for c in corrected if c['significant'])
        print(f"  总比较数: {len(p_values)}")
        print(f"  校正前显著: {n_sig_before}")
        print(f"  校正后显著: {n_sig_after}")
    
    # 6. 保存结果
    print("\n[6/6] 保存结果...")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'alpha': validator.alpha,
        'data_sources': {
            'ablation': ablation_path if Path(ablation_path).exists() else None,
            'significance': sig_path if Path(sig_path).exists() else None
        },
        'welch_tests': [asdict(r) for r in validator.welch_results],
        'effect_sizes': [asdict(r) for r in validator.effect_results],
        'bootstrap_cis': [asdict(r) for r in validator.bootstrap_results],
        'corrected_pvalues': validator.corrected_pvalues,
        'summary': {
            'n_comparisons': len(validator.welch_results),
            'n_significant_uncorrected': sum(1 for r in validator.welch_results if r.significant),
            'n_significant_corrected': sum(1 for c in validator.corrected_pvalues if c['significant']),
            'large_effects': [
                f"{r.group1}_vs_{r.group2}_{r.metric}" 
                for r in validator.effect_results 
                if r.interpretation == 'large'
            ],
            'medium_effects': [
                f"{r.group1}_vs_{r.group2}_{r.metric}" 
                for r in validator.effect_results 
                if r.interpretation == 'medium'
            ]
        }
    }
    
    output_file = output_dir / 'comprehensive_validation_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n结果已保存至: {output_file}")
    
    # 打印结论
    print("\n" + "=" * 60)
    print("统计验证结论:")
    print("=" * 60)
    print(f"✓ 总比较数: {results['summary']['n_comparisons']}")
    print(f"✓ 显著（未校正）: {results['summary']['n_significant_uncorrected']}")
    print(f"✓ 显著（校正后）: {results['summary']['n_significant_corrected']}")
    print(f"✓ Large效应: {len(results['summary']['large_effects'])}")
    print(f"✓ Medium效应: {len(results['summary']['medium_effects'])}")
    
    # 关键发现
    if validator.effect_results:
        print("\n关键发现:")
        for r in validator.effect_results:
            if r.interpretation in ['large', 'medium']:
                print(f"  • {r.group1} vs {r.group2} ({r.metric}): g={r.hedges_g:.3f} ({r.interpretation})")
    
    return results


if __name__ == '__main__':
    main()
