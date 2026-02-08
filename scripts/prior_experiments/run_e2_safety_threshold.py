#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
先验实验E2：Safety阈值/窗口概率论标定

目标：证明safety阈值θ和窗口T不是拍脑袋定的
方法：
1. 将每轮delivery建模为Bernoulli试验，窗口内成功数服从Binomial分布
2. 使用Beta-Binomial得到后验P(p < θ | data)
3. 优化阈值以控制误触发率（FPR < 10%）

输出：
- results/prior_experiments/e2_safety_threshold.json
- results/prior_experiments/e2_safety_figures/
"""

import os
import sys
import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from scipy import stats
from scipy.special import beta as beta_func, betainc

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# MDPI规范设置
plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 150


@dataclass
class BetaBinomialResult:
    """Beta-Binomial模型结果"""
    alpha_prior: float
    beta_prior: float
    alpha_posterior: float
    beta_posterior: float
    posterior_mean: float
    posterior_std: float
    credible_interval_95: Tuple[float, float]


@dataclass
class ThresholdOptimizationResult:
    """阈值优化结果"""
    optimal_theta: float
    optimal_T: int
    false_positive_rate: float
    true_positive_rate: float
    f1_score: float


class SafetyThresholdCalibrator:
    """Safety阈值标定器"""
    
    def __init__(self, round_pdrs: np.ndarray = None):
        """
        round_pdrs: 每轮的PDR值数组
        """
        if round_pdrs is None:
            # 生成模拟数据
            self.round_pdrs = self._generate_simulated_pdrs()
        else:
            self.round_pdrs = round_pdrs
        
        self.n_rounds = len(self.round_pdrs)
    
    def _generate_simulated_pdrs(self, n_rounds: int = 1000, 
                                  base_pdr: float = 0.9,
                                  crisis_prob: float = 0.1,
                                  crisis_pdr: float = 0.5) -> np.ndarray:
        """
        生成模拟的PDR序列
        
        包含正常轮次和危机轮次
        """
        rng = np.random.default_rng(42)
        pdrs = []
        
        for _ in range(n_rounds):
            if rng.random() < crisis_prob:
                # 危机轮次：PDR下降
                pdr = rng.beta(crisis_pdr * 10, (1 - crisis_pdr) * 10)
            else:
                # 正常轮次
                pdr = rng.beta(base_pdr * 20, (1 - base_pdr) * 20)
            pdrs.append(pdr)
        
        return np.array(pdrs)
    
    def fit_beta_binomial(self, window_size: int = 10,
                         alpha_prior: float = 1.0,
                         beta_prior: float = 1.0) -> BetaBinomialResult:
        """
        拟合Beta-Binomial模型
        
        将每轮的PDR视为成功概率，窗口内的成功次数服从Binomial分布
        使用Beta先验得到后验分布
        """
        # 将PDR转换为成功/失败（以0.7为阈值）
        successes = (self.round_pdrs > 0.7).astype(int)
        
        # 计算窗口内的成功次数
        n_windows = len(successes) // window_size
        window_successes = []
        
        for i in range(n_windows):
            start = i * window_size
            end = start + window_size
            window_successes.append(np.sum(successes[start:end]))
        
        window_successes = np.array(window_successes)
        
        # 计算后验参数
        total_successes = np.sum(window_successes)
        total_trials = n_windows * window_size
        
        alpha_posterior = alpha_prior + total_successes
        beta_posterior = beta_prior + (total_trials - total_successes)
        
        # 后验统计量
        posterior_mean = alpha_posterior / (alpha_posterior + beta_posterior)
        posterior_var = (alpha_posterior * beta_posterior) / \
                       ((alpha_posterior + beta_posterior) ** 2 * (alpha_posterior + beta_posterior + 1))
        posterior_std = np.sqrt(posterior_var)
        
        # 95%可信区间
        ci_low = stats.beta.ppf(0.025, alpha_posterior, beta_posterior)
        ci_high = stats.beta.ppf(0.975, alpha_posterior, beta_posterior)
        
        return BetaBinomialResult(
            alpha_prior=alpha_prior,
            beta_prior=beta_prior,
            alpha_posterior=float(alpha_posterior),
            beta_posterior=float(beta_posterior),
            posterior_mean=float(posterior_mean),
            posterior_std=float(posterior_std),
            credible_interval_95=(float(ci_low), float(ci_high))
        )
    
    def compute_trigger_probability(self, theta: float, T: int,
                                   alpha: float, beta: float) -> float:
        """
        计算给定阈值θ和窗口T的触发概率
        
        P(触发) = P(窗口内成功率 < θ)
        """
        # 使用Beta分布的CDF
        return stats.beta.cdf(theta, alpha, beta)
    
    def compute_false_positive_rate(self, theta: float, T: int,
                                   true_pdr: float = 0.9) -> float:
        """
        计算误触发率（False Positive Rate）
        
        在真实PDR为true_pdr时，错误触发safety的概率
        """
        # 模拟正常情况下的窗口PDR分布
        rng = np.random.default_rng(42)
        n_simulations = 10000
        
        false_positives = 0
        for _ in range(n_simulations):
            # 生成T轮的PDR
            window_pdrs = rng.beta(true_pdr * 20, (1 - true_pdr) * 20, size=T)
            window_mean = np.mean(window_pdrs)
            
            if window_mean < theta:
                false_positives += 1
        
        return false_positives / n_simulations
    
    def compute_true_positive_rate(self, theta: float, T: int,
                                  crisis_pdr: float = 0.5) -> float:
        """
        计算真正率（True Positive Rate）
        
        在真实PDR为crisis_pdr时，正确触发safety的概率
        """
        rng = np.random.default_rng(43)
        n_simulations = 10000
        
        true_positives = 0
        for _ in range(n_simulations):
            window_pdrs = rng.beta(crisis_pdr * 10, (1 - crisis_pdr) * 10, size=T)
            window_mean = np.mean(window_pdrs)
            
            if window_mean < theta:
                true_positives += 1
        
        return true_positives / n_simulations
    
    def optimize_threshold(self, target_fpr: float = 0.1,
                          theta_range: Tuple[float, float] = (0.5, 0.9),
                          T_range: Tuple[int, int] = (3, 15)) -> ThresholdOptimizationResult:
        """
        优化阈值以控制误触发率
        
        在FPR < target_fpr的约束下，最大化TPR
        """
        best_result = None
        best_f1 = 0
        
        theta_values = np.linspace(theta_range[0], theta_range[1], 20)
        T_values = range(T_range[0], T_range[1] + 1)
        
        results_grid = []
        
        for theta in theta_values:
            for T in T_values:
                fpr = self.compute_false_positive_rate(theta, T)
                tpr = self.compute_true_positive_rate(theta, T)
                
                # 计算F1 score
                precision = tpr / (tpr + fpr) if (tpr + fpr) > 0 else 0
                recall = tpr
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                
                results_grid.append({
                    'theta': theta,
                    'T': T,
                    'fpr': fpr,
                    'tpr': tpr,
                    'f1': f1
                })
                
                # 在FPR约束下选择最佳
                if fpr <= target_fpr and f1 > best_f1:
                    best_f1 = f1
                    best_result = ThresholdOptimizationResult(
                        optimal_theta=float(theta),
                        optimal_T=int(T),
                        false_positive_rate=float(fpr),
                        true_positive_rate=float(tpr),
                        f1_score=float(f1)
                    )
        
        self.results_grid = results_grid
        
        if best_result is None:
            # 如果没有满足约束的，选择FPR最小的
            min_fpr_result = min(results_grid, key=lambda x: x['fpr'])
            best_result = ThresholdOptimizationResult(
                optimal_theta=float(min_fpr_result['theta']),
                optimal_T=int(min_fpr_result['T']),
                false_positive_rate=float(min_fpr_result['fpr']),
                true_positive_rate=float(min_fpr_result['tpr']),
                f1_score=float(min_fpr_result['f1'])
            )
        
        return best_result
    
    def validate_on_data(self, theta: float, T: int) -> Dict:
        """
        在实际数据上验证阈值
        """
        # 计算滑动窗口PDR
        window_pdrs = []
        triggers = []
        
        for i in range(len(self.round_pdrs) - T + 1):
            window_pdr = np.mean(self.round_pdrs[i:i+T])
            window_pdrs.append(window_pdr)
            triggers.append(window_pdr < theta)
        
        window_pdrs = np.array(window_pdrs)
        triggers = np.array(triggers)
        
        # 统计触发情况
        n_triggers = np.sum(triggers)
        trigger_rate = n_triggers / len(triggers)
        
        # 分析触发时的实际PDR
        trigger_pdrs = window_pdrs[triggers] if n_triggers > 0 else np.array([])
        
        return {
            'n_windows': len(window_pdrs),
            'n_triggers': int(n_triggers),
            'trigger_rate': float(trigger_rate),
            'mean_window_pdr': float(np.mean(window_pdrs)),
            'std_window_pdr': float(np.std(window_pdrs)),
            'mean_trigger_pdr': float(np.mean(trigger_pdrs)) if len(trigger_pdrs) > 0 else None,
            'window_pdrs': window_pdrs.tolist()[:100],  # 只保存前100个用于绘图
            'triggers': triggers.tolist()[:100]
        }


class E2FigureGenerator:
    """E2实验图表生成器"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def plot_fpr_surface(self, results_grid: List[Dict],
                        optimal_theta: float, optimal_T: int,
                        filename: str = 'e2_fpr_surface'):
        """绘制FPR vs θ/T曲面图"""
        import pandas as pd
        
        df = pd.DataFrame(results_grid)
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # 左图：FPR热力图
        ax1 = axes[0]
        pivot_fpr = df.pivot(index='T', columns='theta', values='fpr')
        im1 = ax1.imshow(pivot_fpr.values, aspect='auto', cmap='RdYlGn_r',
                        extent=[pivot_fpr.columns.min(), pivot_fpr.columns.max(),
                               pivot_fpr.index.max(), pivot_fpr.index.min()])
        ax1.set_xlabel('Threshold θ')
        ax1.set_ylabel('Window Size T')
        ax1.set_title('False Positive Rate')
        plt.colorbar(im1, ax=ax1, label='FPR')
        
        # 标注最优点
        ax1.plot(optimal_theta, optimal_T, 'k*', markersize=15, label='Optimal')
        ax1.legend()
        
        # 右图：TPR热力图
        ax2 = axes[1]
        pivot_tpr = df.pivot(index='T', columns='theta', values='tpr')
        im2 = ax2.imshow(pivot_tpr.values, aspect='auto', cmap='RdYlGn',
                        extent=[pivot_tpr.columns.min(), pivot_tpr.columns.max(),
                               pivot_tpr.index.max(), pivot_tpr.index.min()])
        ax2.set_xlabel('Threshold θ')
        ax2.set_ylabel('Window Size T')
        ax2.set_title('True Positive Rate')
        plt.colorbar(im2, ax=ax2, label='TPR')
        
        ax2.plot(optimal_theta, optimal_T, 'k*', markersize=15, label='Optimal')
        ax2.legend()
        
        plt.tight_layout()
        for fmt in ['pdf', 'svg', 'png']:
            fig.savefig(self.output_dir / f'{filename}.{fmt}', dpi=300, bbox_inches='tight')
        plt.close(fig)
    
    def plot_posterior_distribution(self, bb_result: BetaBinomialResult,
                                   theta: float,
                                   filename: str = 'e2_posterior'):
        """绘制后验分布图"""
        fig, ax = plt.subplots(figsize=(8, 5))
        
        x = np.linspace(0, 1, 1000)
        y = stats.beta.pdf(x, bb_result.alpha_posterior, bb_result.beta_posterior)
        
        ax.plot(x, y, 'b-', linewidth=2, label='Posterior Distribution')
        ax.fill_between(x, y, alpha=0.3)
        
        # 标注阈值
        ax.axvline(x=theta, color='r', linestyle='--', linewidth=2, 
                  label=f'Threshold θ={theta:.2f}')
        
        # 标注后验均值
        ax.axvline(x=bb_result.posterior_mean, color='g', linestyle='-', linewidth=2,
                  label=f'Posterior Mean={bb_result.posterior_mean:.3f}')
        
        # 标注95%可信区间
        ci_low, ci_high = bb_result.credible_interval_95
        ax.axvspan(ci_low, ci_high, alpha=0.2, color='green', 
                  label=f'95% CI: [{ci_low:.3f}, {ci_high:.3f}]')
        
        # 计算P(p < θ)
        p_below_theta = stats.beta.cdf(theta, bb_result.alpha_posterior, bb_result.beta_posterior)
        ax.fill_between(x[x < theta], y[x < theta], alpha=0.5, color='red',
                       label=f'P(p < θ) = {p_below_theta:.3f}')
        
        ax.set_xlabel('Success Probability p')
        ax.set_ylabel('Density')
        ax.set_title('Beta-Binomial Posterior Distribution')
        ax.legend(loc='upper left')
        ax.set_xlim(0, 1)
        
        plt.tight_layout()
        for fmt in ['pdf', 'svg', 'png']:
            fig.savefig(self.output_dir / f'{filename}.{fmt}', dpi=300, bbox_inches='tight')
        plt.close(fig)
    
    def plot_validation_timeline(self, validation: Dict, theta: float,
                                filename: str = 'e2_validation_timeline'):
        """绘制验证时间线图"""
        fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
        
        window_pdrs = np.array(validation['window_pdrs'])
        triggers = np.array(validation['triggers'])
        x = np.arange(len(window_pdrs))
        
        # 上图：窗口PDR
        ax1 = axes[0]
        ax1.plot(x, window_pdrs, 'b-', linewidth=1, alpha=0.7)
        ax1.axhline(y=theta, color='r', linestyle='--', linewidth=2, label=f'θ={theta:.2f}')
        ax1.scatter(x[triggers], window_pdrs[triggers], c='red', s=50, zorder=5, label='Trigger')
        ax1.set_ylabel('Window PDR')
        ax1.set_title('Safety Mechanism Validation')
        ax1.legend()
        ax1.set_ylim(0, 1)
        
        # 下图：触发状态
        ax2 = axes[1]
        ax2.fill_between(x, triggers.astype(int), step='mid', alpha=0.5, color='red')
        ax2.set_ylabel('Trigger Status')
        ax2.set_xlabel('Window Index')
        ax2.set_ylim(-0.1, 1.1)
        ax2.set_yticks([0, 1])
        ax2.set_yticklabels(['Normal', 'Triggered'])
        
        plt.tight_layout()
        for fmt in ['pdf', 'svg', 'png']:
            fig.savefig(self.output_dir / f'{filename}.{fmt}', dpi=300, bbox_inches='tight')
        plt.close(fig)


def main():
    """运行E2先验实验"""
    print("=" * 60)
    print("E2: Safety阈值/窗口概率论标定")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = Path('results/prior_experiments')
    output_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = output_dir / 'e2_safety_figures'
    fig_dir.mkdir(exist_ok=True)
    
    # 初始化标定器
    print("\n[1/5] 生成模拟PDR数据...")
    calibrator = SafetyThresholdCalibrator()
    print(f"  生成 {calibrator.n_rounds} 轮PDR数据")
    print(f"  PDR范围: [{calibrator.round_pdrs.min():.3f}, {calibrator.round_pdrs.max():.3f}]")
    print(f"  PDR均值: {calibrator.round_pdrs.mean():.3f}")
    
    # 拟合Beta-Binomial模型
    print("\n[2/5] 拟合Beta-Binomial模型...")
    window_sizes = [5, 10, 15]
    bb_results = {}
    
    for T in window_sizes:
        result = calibrator.fit_beta_binomial(window_size=T)
        bb_results[T] = result
        print(f"  T={T}: 后验均值={result.posterior_mean:.3f}, "
              f"95% CI=[{result.credible_interval_95[0]:.3f}, {result.credible_interval_95[1]:.3f}]")
    
    # 优化阈值
    print("\n[3/5] 优化阈值参数...")
    opt_result = calibrator.optimize_threshold(target_fpr=0.1)
    print(f"  最优θ: {opt_result.optimal_theta:.3f}")
    print(f"  最优T: {opt_result.optimal_T}")
    print(f"  FPR: {opt_result.false_positive_rate:.3f}")
    print(f"  TPR: {opt_result.true_positive_rate:.3f}")
    print(f"  F1 Score: {opt_result.f1_score:.3f}")
    
    # 验证
    print("\n[4/5] 在数据上验证...")
    validation = calibrator.validate_on_data(opt_result.optimal_theta, opt_result.optimal_T)
    print(f"  窗口数: {validation['n_windows']}")
    print(f"  触发次数: {validation['n_triggers']}")
    print(f"  触发率: {validation['trigger_rate']:.3f}")
    print(f"  平均窗口PDR: {validation['mean_window_pdr']:.3f}")
    
    # 生成图表
    print("\n[5/5] 生成图表...")
    fig_gen = E2FigureGenerator(str(fig_dir))
    
    fig_gen.plot_fpr_surface(calibrator.results_grid, 
                            opt_result.optimal_theta, 
                            opt_result.optimal_T)
    print("  ✓ FPR/TPR曲面图")
    
    fig_gen.plot_posterior_distribution(bb_results[10], opt_result.optimal_theta)
    print("  ✓ 后验分布图")
    
    fig_gen.plot_validation_timeline(validation, opt_result.optimal_theta)
    print("  ✓ 验证时间线图")
    
    # 保存结果
    results = {
        'experiment': 'E2_safety_threshold_calibration',
        'timestamp': datetime.now().isoformat(),
        'data_summary': {
            'n_rounds': calibrator.n_rounds,
            'pdr_mean': float(calibrator.round_pdrs.mean()),
            'pdr_std': float(calibrator.round_pdrs.std()),
            'pdr_min': float(calibrator.round_pdrs.min()),
            'pdr_max': float(calibrator.round_pdrs.max())
        },
        'beta_binomial_results': {
            str(T): asdict(result) for T, result in bb_results.items()
        },
        'optimization_result': asdict(opt_result),
        'validation': {
            k: v for k, v in validation.items() 
            if k not in ['window_pdrs', 'triggers']  # 不保存大数组
        },
        'conclusions': {
            'optimal_theta': opt_result.optimal_theta,
            'optimal_T': opt_result.optimal_T,
            'fpr_controlled': opt_result.false_positive_rate <= 0.1,
            'interpretation': (
                f"通过Beta-Binomial概率模型标定safety阈值。"
                f"最优参数θ={opt_result.optimal_theta:.2f}, T={opt_result.optimal_T}，"
                f"在FPR={opt_result.false_positive_rate:.1%}的约束下，"
                f"TPR达到{opt_result.true_positive_rate:.1%}。"
                f"这为AERIS的safety机制提供了概率论支撑。"
            )
        }
    }
    
    output_file = output_dir / 'e2_safety_threshold.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存至: {output_file}")
    print(f"图表已保存至: {fig_dir}")
    
    # 打印结论
    print("\n" + "=" * 60)
    print("E2实验结论:")
    print("=" * 60)
    print(f"✓ 最优阈值θ: {opt_result.optimal_theta:.3f}")
    print(f"✓ 最优窗口T: {opt_result.optimal_T}")
    print(f"✓ 误触发率FPR: {opt_result.false_positive_rate:.1%} (目标<10%)")
    print(f"✓ 真正率TPR: {opt_result.true_positive_rate:.1%}")
    print(f"✓ F1 Score: {opt_result.f1_score:.3f}")
    
    return results


if __name__ == '__main__':
    main()
