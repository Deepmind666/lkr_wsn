#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顶级期刊标准图表生成器

按照Nature/Science/IEEE TPAMI等顶级期刊的图表标准生成高质量图表：
- 清晰的视觉层次
- 专业的配色方案
- 精确的统计可视化
- 完整的误差表示
- 适当的注释和标签

输出：results/publication_figures_premium/
"""

import sys
import os
import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, FancyBboxPatch
from matplotlib.lines import Line2D
import matplotlib.ticker as ticker
from matplotlib.gridspec import GridSpec
import matplotlib.patheffects as path_effects
# from scipy import stats  # Not needed for basic plotting

# 顶级期刊配置
PREMIUM_CONFIG = {
    # 基础设置
    'figure.dpi': 300,
    'savefig.dpi': 600,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    
    # 字体设置 - 使用专业字体
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 9,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'legend.title_fontsize': 9,
    
    # 线条和边框
    'axes.linewidth': 0.8,
    'axes.edgecolor': '#333333',
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'xtick.minor.width': 0.5,
    'ytick.minor.width': 0.5,
    'grid.linewidth': 0.5,
    'grid.alpha': 0.3,
    
    # 输出格式
    'svg.fonttype': 'none',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
}

# 应用配置
for key, value in PREMIUM_CONFIG.items():
    plt.rcParams[key] = value

# 专业配色方案 (Nature风格)
NATURE_COLORS = {
    'blue': '#0077BB',
    'red': '#CC3311', 
    'green': '#009988',
    'orange': '#EE7733',
    'purple': '#AA3377',
    'cyan': '#33BBEE',
    'grey': '#BBBBBB',
    'dark': '#332288',
}

# 协议配色
PROTOCOL_COLORS = {
    'AERIS': '#0077BB',      # 蓝色 - 主角
    'AERIS-R': '#0077BB',
    'AERIS-E': '#33BBEE',    # 浅蓝
    'LEACH': '#CC3311',      # 红色
    'HEED': '#EE7733',       # 橙色
    'PEGASIS': '#009988',    # 绿色
    'TEEN': '#AA3377',       # 紫色
    'FULL': '#0077BB',
    '-CAS': '#33BBEE',
    '-FAIR': '#EE7733',
    '-GW': '#CC3311',
    '-SAFETY': '#009988',
}

# 效应量颜色
EFFECT_COLORS = {
    'large': '#CC3311',
    'medium': '#EE7733',
    'small': '#009988',
    'negligible': '#BBBBBB',
}


class PremiumFigureGenerator:
    """顶级期刊标准图表生成器"""
    
    def __init__(self, output_dir: str = 'results/publication_figures_premium'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generated_figures = []
        
    def _add_significance_markers(self, ax, x1, x2, y, h, text='*'):
        """添加显著性标记"""
        ax.plot([x1, x1, x2, x2], [y, y+h, y+h, y], lw=1, c='black')
        ax.text((x1+x2)/2, y+h, text, ha='center', va='bottom', fontsize=10)
    
    def _format_pvalue(self, p):
        """格式化p值"""
        if p < 0.001:
            return '***'
        elif p < 0.01:
            return '**'
        elif p < 0.05:
            return '*'
        else:
            return 'ns'
    
    def save_figure(self, fig: plt.Figure, name: str, 
                   formats: List[str] = ['pdf', 'svg', 'png']) -> List[str]:
        """保存多格式图表"""
        saved_paths = []
        for fmt in formats:
            path = self.output_dir / f'{name}.{fmt}'
            fig.savefig(path, dpi=600 if fmt == 'png' else 300, 
                       bbox_inches='tight', facecolor='white', 
                       edgecolor='none', transparent=False)
            saved_paths.append(str(path))
        plt.close(fig)
        self.generated_figures.append(name)
        return saved_paths


    def plot_ablation_effect_sizes(self, stats_path: str, 
                                   filename: str = 'fig_ablation_effect_sizes') -> None:
        """
        Figure 1: 消融实验效应量图 (Nature风格)
        
        展示各模块对PDR的贡献度，使用森林图风格
        """
        with open(stats_path, 'r') as f:
            data = json.load(f)
        
        # 提取PDR相关的效应量
        pdr_effects = [e for e in data['effect_sizes'] 
                      if e['metric'] == 'pdr' and e['group1'] == 'FULL']
        
        fig, ax = plt.subplots(figsize=(7, 4))
        
        # 准备数据
        comparisons = []
        hedges_g = []
        ci_lows = []
        ci_highs = []
        colors = []
        
        for e in pdr_effects:
            module = e['group2'].replace('-', '')
            comparisons.append(module)
            hedges_g.append(e['hedges_g'])
            ci_lows.append(e['ci_low'])
            ci_highs.append(e['ci_high'])
            colors.append(EFFECT_COLORS.get(e['interpretation'], '#666666'))
        
        # 按效应量排序
        sorted_idx = np.argsort(hedges_g)[::-1]
        comparisons = [comparisons[i] for i in sorted_idx]
        hedges_g = [hedges_g[i] for i in sorted_idx]
        ci_lows = [ci_lows[i] for i in sorted_idx]
        ci_highs = [ci_highs[i] for i in sorted_idx]
        colors = [colors[i] for i in sorted_idx]
        
        y_pos = np.arange(len(comparisons))
        
        # 绘制森林图
        for i, (y, g, ci_l, ci_h, c) in enumerate(zip(y_pos, hedges_g, ci_lows, ci_highs, colors)):
            # 置信区间线
            ax.plot([ci_l, ci_h], [y, y], color=c, linewidth=2, solid_capstyle='round')
            # 效应量点
            ax.scatter([g], [y], color=c, s=120, zorder=5, edgecolors='white', linewidths=1.5)
        
        # 添加参考线
        ax.axvline(x=0, color='#333333', linestyle='-', linewidth=0.8, alpha=0.5)
        ax.axvline(x=0.2, color='#999999', linestyle='--', linewidth=0.5, alpha=0.5)
        ax.axvline(x=0.5, color='#999999', linestyle='--', linewidth=0.5, alpha=0.5)
        ax.axvline(x=0.8, color='#999999', linestyle='--', linewidth=0.5, alpha=0.5)
        
        # 添加效应量区域标签
        ax.text(0.1, len(comparisons)-0.3, 'Small', fontsize=7, color='#666666', ha='center')
        ax.text(0.35, len(comparisons)-0.3, 'Medium', fontsize=7, color='#666666', ha='center')
        ax.text(0.65, len(comparisons)-0.3, 'Large', fontsize=7, color='#666666', ha='center')
        
        # 设置坐标轴
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f'FULL vs {c}' for c in comparisons])
        ax.set_xlabel("Hedges' g (Effect Size)", fontweight='bold')
        ax.set_title('Module Contribution to PDR (Ablation Study)', fontweight='bold', pad=15)
        
        # 添加数值标注
        for i, (y, g) in enumerate(zip(y_pos, hedges_g)):
            if g > 1:
                ax.text(min(g + 0.5, ax.get_xlim()[1] - 1), y, f'g = {g:.2f}', 
                       va='center', fontsize=8, fontweight='bold')
            else:
                ax.text(g + 0.1, y, f'{g:.2f}', va='center', fontsize=8)
        
        # 图例
        legend_elements = [
            Patch(facecolor=EFFECT_COLORS['large'], label='Large (|g| > 0.8)'),
            Patch(facecolor=EFFECT_COLORS['medium'], label='Medium (0.5 < |g| ≤ 0.8)'),
            Patch(facecolor=EFFECT_COLORS['small'], label='Small (0.2 < |g| ≤ 0.5)'),
            Patch(facecolor=EFFECT_COLORS['negligible'], label='Negligible (|g| ≤ 0.2)'),
        ]
        ax.legend(handles=legend_elements, loc='lower right', frameon=True, 
                 fancybox=False, edgecolor='#cccccc')
        
        ax.set_xlim(-0.5, max(hedges_g) + 2)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        self.save_figure(fig, filename)
        print(f"  ✓ {filename}")

    def plot_environment_link_correlation(self, e0_path: str,
                                          filename: str = 'fig_env_link_correlation') -> None:
        """
        Figure 2: 环境-链路相关性分析图 (双面板)
        
        左: 相关性热力图
        右: 滞后相关性曲线
        """
        with open(e0_path, 'r') as f:
            data = json.load(f)
        
        fig = plt.figure(figsize=(10, 4))
        gs = GridSpec(1, 2, width_ratios=[1, 1.2], wspace=0.3)
        
        # 左图: 相关性条形图
        ax1 = fig.add_subplot(gs[0])
        
        features = ['humidity', 'temperature', 'temp_diff', 'humidity_diff']
        feature_labels = ['Humidity', 'Temperature', 'Temp. Δ', 'Humidity Δ']
        correlations = []
        
        for feat in features:
            for c in data['correlations']:
                if c['feature'] == feat and c['metric'] == 'link_quality_proxy':
                    correlations.append(c['pearson_r'])
                    break
        
        colors = [NATURE_COLORS['blue'] if c < 0 else NATURE_COLORS['red'] for c in correlations]
        
        y_pos = np.arange(len(features))
        bars = ax1.barh(y_pos, correlations, color=colors, alpha=0.8, height=0.6)
        
        # 添加数值标注
        for bar, corr in zip(bars, correlations):
            width = bar.get_width()
            ax1.text(width + 0.02 if width > 0 else width - 0.02, 
                    bar.get_y() + bar.get_height()/2,
                    f'r = {corr:.3f}', va='center', 
                    ha='left' if width > 0 else 'right', fontsize=8)
        
        ax1.axvline(x=0, color='#333333', linewidth=0.8)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(feature_labels)
        ax1.set_xlabel('Pearson Correlation (r)', fontweight='bold')
        ax1.set_title('(a) Environment-Link Correlation', fontweight='bold', pad=10)
        ax1.set_xlim(-0.7, 0.1)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # 添加显著性标记
        ax1.text(-0.65, -0.8, '*** p < 0.001 for all correlations', fontsize=7, 
                style='italic', color='#666666')
        
        # 右图: 滞后相关性
        ax2 = fig.add_subplot(gs[1])
        
        lag_data = data['lagged_correlations']
        
        for feat, color, label in [('humidity', NATURE_COLORS['blue'], 'Humidity'),
                                   ('temperature', NATURE_COLORS['red'], 'Temperature')]:
            lags = lag_data[feat]['lags']
            corrs = [-c for c in lag_data[feat]['correlation']]  # 取绝对值
            ax2.plot(lags, corrs, color=color, linewidth=2, label=label, marker='o', 
                    markersize=4, markerfacecolor='white', markeredgewidth=1.5)
            
            # 标记最大相关点
            max_idx = np.argmax(corrs)
            ax2.scatter([lags[max_idx]], [corrs[max_idx]], color=color, s=100, 
                       zorder=5, edgecolors='white', linewidths=2)
            ax2.annotate(f'max @ lag={lags[max_idx]}h\nr={corrs[max_idx]:.3f}',
                        xy=(lags[max_idx], corrs[max_idx]),
                        xytext=(lags[max_idx]+2, corrs[max_idx]+0.02),
                        fontsize=7, color=color,
                        arrowprops=dict(arrowstyle='->', color=color, lw=0.8))
        
        ax2.set_xlabel('Lag (hours)', fontweight='bold')
        ax2.set_ylabel('|Correlation|', fontweight='bold')
        ax2.set_title('(b) Lagged Cross-Correlation', fontweight='bold', pad=10)
        ax2.legend(loc='lower right', frameon=True, fancybox=False, edgecolor='#cccccc')
        ax2.grid(True, alpha=0.3)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        plt.tight_layout()
        self.save_figure(fig, filename)
        print(f"  ✓ {filename}")


    def plot_feature_importance(self, e1_path: str,
                                filename: str = 'fig_feature_importance') -> None:
        """
        Figure 3: CAS特征重要性分析图
        
        使用水平条形图展示特征重要性，带置信区间
        """
        with open(e1_path, 'r') as f:
            data = json.load(f)
        
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        
        # 左图: Permutation Importance
        ax1 = axes[0]
        
        importances = data['actual_model']['feature_importances']
        features = [fi['feature'] for fi in importances]
        perm_imp = [fi['permutation_importance'] for fi in importances]
        
        # 按重要性排序
        sorted_idx = np.argsort(perm_imp)[::-1]
        features = [features[i] for i in sorted_idx]
        perm_imp = [perm_imp[i] for i in sorted_idx]
        
        # 颜色渐变
        colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(features)))[::-1]
        
        y_pos = np.arange(len(features))
        bars = ax1.barh(y_pos, perm_imp, color=colors, height=0.6, edgecolor='white', linewidth=0.5)
        
        # 添加数值标注
        for bar, imp in zip(bars, perm_imp):
            width = bar.get_width()
            ax1.text(width + 0.005, bar.get_y() + bar.get_height()/2,
                    f'{imp:.3f}', va='center', fontsize=8)
        
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels([f.replace('_', ' ').title() for f in features])
        ax1.set_xlabel('Permutation Importance', fontweight='bold')
        ax1.set_title('(a) Feature Importance Ranking', fontweight='bold', pad=10)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.invert_yaxis()
        
        # 右图: 系数显著性
        ax2 = axes[1]
        
        coefficients = [fi['coefficient'] for fi in importances]
        p_values = [fi['p_value'] for fi in importances]
        
        # 按原始顺序
        coefficients = [coefficients[i] for i in sorted_idx]
        p_values = [p_values[i] for i in sorted_idx]
        
        # 颜色根据显著性
        sig_colors = [NATURE_COLORS['blue'] if p < 0.001 else 
                     NATURE_COLORS['orange'] if p < 0.05 else 
                     NATURE_COLORS['grey'] for p in p_values]
        
        bars2 = ax2.barh(y_pos, coefficients, color=sig_colors, height=0.6, 
                        edgecolor='white', linewidth=0.5)
        
        # 添加显著性标记
        for bar, p in zip(bars2, p_values):
            width = bar.get_width()
            marker = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
            ax2.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                    marker, va='center', fontsize=10, fontweight='bold')
        
        ax2.axvline(x=0, color='#333333', linewidth=0.8)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels([f.replace('_', ' ').title() for f in features])
        ax2.set_xlabel('Logistic Regression Coefficient', fontweight='bold')
        ax2.set_title('(b) Coefficient Significance', fontweight='bold', pad=10)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.invert_yaxis()
        
        # 图例
        legend_elements = [
            Patch(facecolor=NATURE_COLORS['blue'], label='p < 0.001 (***)'),
            Patch(facecolor=NATURE_COLORS['orange'], label='p < 0.05 (*)'),
            Patch(facecolor=NATURE_COLORS['grey'], label='Not significant'),
        ]
        ax2.legend(handles=legend_elements, loc='lower right', frameon=True,
                  fancybox=False, edgecolor='#cccccc', fontsize=7)
        
        plt.tight_layout()
        self.save_figure(fig, filename)
        print(f"  ✓ {filename}")

    def plot_statistical_validation_summary(self, stats_path: str,
                                            filename: str = 'fig_statistical_summary') -> None:
        """
        Figure 4: 统计验证汇总图 (三面板)
        
        展示完整的统计验证结果
        """
        with open(stats_path, 'r') as f:
            data = json.load(f)
        
        fig = plt.figure(figsize=(12, 4))
        gs = GridSpec(1, 3, width_ratios=[1, 1, 1], wspace=0.35)
        
        # 面板A: PDR/能耗对比 (带置信区间)
        ax1 = fig.add_subplot(gs[0])
        
        # 提取消融实验的PDR数据（若PDR全为常数则改用能耗）
        metric = 'pdr'
        pdr_cis = [ci for ci in data['bootstrap_cis'] 
                  if ci['metric'] == metric and 'ablation' in ci['group']]
        if not pdr_cis or all(ci['ci_low'] == ci['ci_high'] for ci in pdr_cis):
            metric = 'energy'
            pdr_cis = [ci for ci in data['bootstrap_cis'] 
                      if ci['metric'] == metric and 'ablation' in ci['group']]
        
        groups = [ci['group'].replace('ablation_', '') for ci in pdr_cis]
        means = [ci['mean'] for ci in pdr_cis]
        ci_lows = [ci['ci_low'] for ci in pdr_cis]
        ci_highs = [ci['ci_high'] for ci in pdr_cis]
        
        x = np.arange(len(groups))
        colors = [PROTOCOL_COLORS.get(g, '#666666') for g in groups]
        
        bars = ax1.bar(x, means, color=colors, alpha=0.8, width=0.6, 
                      edgecolor='white', linewidth=1)
        ax1.errorbar(x, means, 
                    yerr=[np.array(means) - np.array(ci_lows),
                          np.array(ci_highs) - np.array(means)],
                    fmt='none', color='black', capsize=4, capthick=1.5, elinewidth=1.5)
        
        ax1.set_xticks(x)
        ax1.set_xticklabels(groups, rotation=45, ha='right')
        ylabel = 'PDR' if metric == 'pdr' else 'Energy (J)'
        ax1.set_ylabel(ylabel, fontweight='bold')
        ax1.set_title(f'(a) {ylabel} with 95% CI', fontweight='bold', pad=10)
        if metric == 'pdr':
            ax1.set_ylim(0.7, 0.95)
        else:
            y_min = min(ci_lows)
            y_max = max(ci_highs)
            pad = (y_max - y_min) * 0.15 if y_max > y_min else 1.0
            ax1.set_ylim(y_min - pad, y_max + pad)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.grid(axis='y', alpha=0.3)
        
        # 面板B: 效应量分布
        ax2 = fig.add_subplot(gs[1])
        
        effect_sizes = data['effect_sizes']
        pdr_effects = [e for e in effect_sizes if e['metric'] == metric]
        
        interpretations = [e['interpretation'] for e in pdr_effects]
        counts = {}
        for interp in ['large', 'medium', 'small', 'negligible']:
            counts[interp] = interpretations.count(interp)
        
        labels = list(counts.keys())
        values = list(counts.values())
        colors = [EFFECT_COLORS[l] for l in labels]
        
        wedges, texts, autotexts = ax2.pie(values, labels=None, colors=colors,
                                           autopct='%1.0f%%', startangle=90,
                                           wedgeprops=dict(width=0.6, edgecolor='white'),
                                           pctdistance=0.75)
        
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_fontweight('bold')
        
        ax2.legend(wedges, [f'{l.capitalize()} (n={v})' for l, v in zip(labels, values)],
                  loc='center left', bbox_to_anchor=(0.9, 0.5), frameon=False)
        ax2.set_title(f'(b) Effect Size Distribution ({ylabel})', fontweight='bold', pad=10)
        
        # 面板C: p值校正结果
        ax3 = fig.add_subplot(gs[2])
        
        corrected = [c for c in data['corrected_pvalues'] 
                     if c['comparison'].endswith(f'_{metric}')]
        
        # 统计显著/不显著数量
        sig_count = sum(1 for c in corrected if c['significant'])
        nonsig_count = len(corrected) - sig_count
        
        # 绘制堆叠条形图
        categories = ['Before\nCorrection', 'After\nHolm-Bonferroni']
        sig_before = sum(1 for c in corrected if c['original_p'] < 0.05)
        nonsig_before = len(corrected) - sig_before
        
        x = np.arange(len(categories))
        width = 0.5
        
        ax3.bar(x, [sig_before, sig_count], width, label='Significant', 
               color=NATURE_COLORS['green'], alpha=0.8)
        ax3.bar(x, [nonsig_before, nonsig_count], width, bottom=[sig_before, sig_count],
               label='Not Significant', color=NATURE_COLORS['grey'], alpha=0.8)
        
        ax3.set_xticks(x)
        ax3.set_xticklabels(categories)
        ax3.set_ylabel('Number of Comparisons', fontweight='bold')
        ax3.set_title('(c) Multiple Testing Correction', fontweight='bold', pad=10)
        ax3.legend(loc='upper right', frameon=True, fancybox=False, edgecolor='#cccccc')
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        
        # 添加数值标注
        for i, (s, ns) in enumerate([(sig_before, nonsig_before), (sig_count, nonsig_count)]):
            ax3.text(i, s/2, str(s), ha='center', va='center', fontweight='bold', color='white')
            ax3.text(i, s + ns/2, str(ns), ha='center', va='center', fontweight='bold')
        
        plt.tight_layout()
        self.save_figure(fig, filename)
        print(f"  ✓ {filename}")


    def plot_prior_experiments_panel(self, e0_path: str, e1_path: str, 
                                     e2_path: str, e3_path: str, e4_path: str,
                                     filename: str = 'fig_prior_experiments_panel') -> None:
        """
        Figure 5: 先验实验汇总面板 (2x3布局)
        
        展示所有先验实验的关键结果
        """
        fig = plt.figure(figsize=(14, 8))
        gs = GridSpec(2, 3, hspace=0.35, wspace=0.3)
        
        # E0: 环境-链路相关性
        ax1 = fig.add_subplot(gs[0, 0])
        try:
            with open(e0_path, 'r') as f:
                e0_data = json.load(f)
            
            features = ['humidity', 'temperature']
            correlations = []
            for feat in features:
                for c in e0_data['correlations']:
                    if c['feature'] == feat and c['metric'] == 'link_quality_proxy':
                        correlations.append(abs(c['pearson_r']))
                        break
            
            colors = [NATURE_COLORS['blue'], NATURE_COLORS['red']]
            bars = ax1.bar(features, correlations, color=colors, alpha=0.8, width=0.5,
                          edgecolor='white', linewidth=1)
            
            for bar, corr in zip(bars, correlations):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                        f'r = {corr:.3f}', ha='center', fontsize=8, fontweight='bold')
            
            ax1.set_ylabel('|Pearson r|', fontweight='bold')
            ax1.set_title('E0: Environment-Link\nCorrelation', fontweight='bold', pad=10)
            ax1.set_ylim(0, 0.7)
            ax1.axhline(y=0.3, color='#999999', linestyle='--', linewidth=0.8, alpha=0.5)
            ax1.text(1.5, 0.32, 'moderate', fontsize=7, color='#666666')
            
        except Exception as e:
            ax1.text(0.5, 0.5, f'E0 data\nnot available', ha='center', va='center', fontsize=10)
        
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # E1: CAS特征重要性 (Top 5)
        ax2 = fig.add_subplot(gs[0, 1])
        try:
            with open(e1_path, 'r') as f:
                e1_data = json.load(f)
            
            importances = e1_data['actual_model']['feature_importances'][:5]
            features = [fi['feature'].replace('_', '\n') for fi in importances]
            values = [fi['permutation_importance'] for fi in importances]
            
            colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(features)))
            bars = ax2.bar(features, values, color=colors, alpha=0.8, width=0.6,
                          edgecolor='white', linewidth=1)
            
            for bar, val in zip(bars, values):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                        f'{val:.3f}', ha='center', fontsize=7)
            
            ax2.set_ylabel('Importance', fontweight='bold')
            ax2.set_title('E1: CAS Feature\nImportance (Top 5)', fontweight='bold', pad=10)
            ax2.tick_params(axis='x', labelsize=7)
            
        except Exception as e:
            ax2.text(0.5, 0.5, f'E1 data\nnot available', ha='center', va='center', fontsize=10)
        
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        # E2: Safety阈值标定
        ax3 = fig.add_subplot(gs[0, 2])
        try:
            with open(e2_path, 'r') as f:
                e2_data = json.load(f)
            
            opt = e2_data['optimization_result']
            metrics = ['FPR', 'TPR', 'F1']
            values = [opt['false_positive_rate'], opt['true_positive_rate'], opt['f1_score']]
            colors = [NATURE_COLORS['red'], NATURE_COLORS['green'], NATURE_COLORS['blue']]
            
            bars = ax3.bar(metrics, values, color=colors, alpha=0.8, width=0.5,
                          edgecolor='white', linewidth=1)
            
            for bar, val in zip(bars, values):
                ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                        f'{val:.2f}', ha='center', fontsize=9, fontweight='bold')
            
            ax3.set_ylabel('Score', fontweight='bold')
            ax3.set_title(f"E2: Safety Threshold\n(θ={opt['optimal_theta']:.2f}, T={opt['optimal_T']})", 
                         fontweight='bold', pad=10)
            ax3.set_ylim(0, 1.15)
            
        except Exception as e:
            ax3.text(0.5, 0.5, f'E2 data\nnot available', ha='center', va='center', fontsize=10)
        
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        
        # E3: 负载均衡效应
        ax4 = fig.add_subplot(gs[1, 0])
        try:
            with open(e3_path, 'r') as f:
                e3_data = json.load(f)
            
            corr_results = e3_data['correlation_results']
            metrics = ['Gini-PDR', 'Gini-Energy', 'Jain-PDR', 'Jain-Energy']
            correlations = [
                corr_results['gini_pdr']['pearson_r'],
                corr_results['gini_energy']['pearson_r'],
                corr_results['jain_pdr']['pearson_r'],
                corr_results['jain_energy']['pearson_r']
            ]
            
            colors = [NATURE_COLORS['red'] if c < 0 else NATURE_COLORS['green'] for c in correlations]
            
            y_pos = np.arange(len(metrics))
            bars = ax4.barh(y_pos, correlations, color=colors, alpha=0.8, height=0.5)
            
            for bar, corr in zip(bars, correlations):
                width = bar.get_width()
                ax4.text(width + 0.02 if width > 0 else width - 0.02, 
                        bar.get_y() + bar.get_height()/2,
                        f'{corr:.2f}', va='center', fontsize=8,
                        ha='left' if width > 0 else 'right')
            
            ax4.axvline(x=0, color='#333333', linewidth=0.8)
            ax4.set_yticks(y_pos)
            ax4.set_yticklabels(metrics)
            ax4.set_xlabel('Pearson r', fontweight='bold')
            ax4.set_title('E3: Load Balance\nCorrelation', fontweight='bold', pad=10)
            ax4.set_xlim(-1, 1)
            
        except Exception as e:
            ax4.text(0.5, 0.5, f'E3 data\nnot available', ha='center', va='center', fontsize=10)
        
        ax4.spines['top'].set_visible(False)
        ax4.spines['right'].set_visible(False)
        
        # E4: 决策时延
        ax5 = fig.add_subplot(gs[1, 1])
        try:
            with open(e4_path, 'r') as f:
                e4_data = json.load(f)
            
            components = ['CAS', 'Skeleton', 'Gateway', 'Total']
            latencies = [
                e4_data['component_latencies']['cas']['mean_ms'],
                e4_data['component_latencies']['skeleton']['mean_ms'],
                e4_data['component_latencies']['gateway']['mean_ms'],
                e4_data['total_latency']['mean_ms']
            ]
            
            colors = [NATURE_COLORS['green'] if l < 25 else NATURE_COLORS['orange'] 
                     if l < 100 else NATURE_COLORS['red'] for l in latencies]
            
            bars = ax5.bar(components, latencies, color=colors, alpha=0.8, width=0.5,
                          edgecolor='white', linewidth=1)
            
            for bar, lat in zip(bars, latencies):
                ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
                        f'{lat:.1f}ms', ha='center', fontsize=8, fontweight='bold')
            
            ax5.axhline(y=25, color=NATURE_COLORS['green'], linestyle='--', 
                       linewidth=1.5, label='MCU Budget (25ms)')
            ax5.set_ylabel('Latency (ms)', fontweight='bold')
            ax5.set_title('E4: Decision Latency', fontweight='bold', pad=10)
            ax5.legend(loc='upper left', fontsize=7, frameon=False)
            
        except Exception as e:
            ax5.text(0.5, 0.5, f'E4 data\nnot available', ha='center', va='center', fontsize=10)
        
        ax5.spines['top'].set_visible(False)
        ax5.spines['right'].set_visible(False)
        
        # 汇总面板: 预测器性能
        ax6 = fig.add_subplot(gs[1, 2])
        try:
            with open(e0_path, 'r') as f:
                e0_data = json.load(f)
            with open(e1_path, 'r') as f:
                e1_data = json.load(f)
            
            metrics = ['E0: Link\nPredictor', 'E1: Mode\nClassifier']
            aucs = [e0_data['predictor']['auc'], e1_data['actual_model']['auc_ovr']]
            
            colors = [NATURE_COLORS['blue'], NATURE_COLORS['purple']]
            bars = ax6.bar(metrics, aucs, color=colors, alpha=0.8, width=0.5,
                          edgecolor='white', linewidth=1)
            
            for bar, auc in zip(bars, aucs):
                ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                        f'AUC = {auc:.3f}', ha='center', fontsize=9, fontweight='bold')
            
            ax6.axhline(y=0.9, color='#999999', linestyle='--', linewidth=0.8, alpha=0.5)
            ax6.text(1.5, 0.91, 'excellent', fontsize=7, color='#666666')
            ax6.set_ylabel('AUC', fontweight='bold')
            ax6.set_title('Predictor Performance', fontweight='bold', pad=10)
            ax6.set_ylim(0.85, 1.02)
            
        except Exception as e:
            ax6.text(0.5, 0.5, f'Data\nnot available', ha='center', va='center', fontsize=10)
        
        ax6.spines['top'].set_visible(False)
        ax6.spines['right'].set_visible(False)
        
        plt.tight_layout()
        self.save_figure(fig, filename)
        print(f"  ✓ {filename}")


    def plot_protocol_comparison_premium(self, data_path: str,
                                         filename: str = 'fig_protocol_comparison') -> None:
        """
        Figure 6: 协议性能对比图 (高级版)
        
        使用分组条形图展示PDR和能耗对比
        """
        try:
            with open(data_path, 'r') as f:
                data = json.load(f)
        except:
            print(f"  ✗ Cannot load {data_path}")
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
        
        # 提取数据
        protocols = list(data['results'].keys())
        pdrs = [data['results'][p]['pdr_end2end'] for p in protocols]
        energies = [data['results'][p]['total_energy'] for p in protocols]
        
        x = np.arange(len(protocols))
        colors = [PROTOCOL_COLORS.get(p, '#666666') for p in protocols]
        
        # 左图: PDR
        ax1 = axes[0]
        bars1 = ax1.bar(x, pdrs, color=colors, alpha=0.85, width=0.6,
                       edgecolor='white', linewidth=1.5)
        
        for bar, pdr in zip(bars1, pdrs):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2, height + 0.02,
                    f'{pdr:.2%}', ha='center', fontsize=9, fontweight='bold')
        
        ax1.set_xticks(x)
        ax1.set_xticklabels(protocols, fontweight='bold')
        ax1.set_ylabel('Packet Delivery Ratio', fontweight='bold')
        ax1.set_title('(a) End-to-End PDR', fontweight='bold', pad=15)
        ax1.set_ylim(0, 1.15)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.grid(axis='y', alpha=0.3)
        
        # 右图: 能耗
        ax2 = axes[1]
        bars2 = ax2.bar(x, energies, color=colors, alpha=0.85, width=0.6,
                       edgecolor='white', linewidth=1.5)
        
        for bar, energy in zip(bars2, energies):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2, height + 1,
                    f'{energy:.1f}J', ha='center', fontsize=9, fontweight='bold')
        
        ax2.set_xticks(x)
        ax2.set_xticklabels(protocols, fontweight='bold')
        ax2.set_ylabel('Total Energy (J)', fontweight='bold')
        ax2.set_title('(b) Energy Consumption', fontweight='bold', pad=15)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        self.save_figure(fig, filename)
        print(f"  ✓ {filename}")

    def generate_all_premium_figures(self) -> Dict:
        """生成所有顶级期刊标准图表"""
        print("=" * 60)
        print("🎨 顶级期刊标准图表生成")
        print("=" * 60)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'output_dir': str(self.output_dir),
            'figures': [],
            'errors': []
        }
        
        # Figure 1: 消融实验效应量
        print("\n[1/6] 生成消融实验效应量图...")
        try:
            self.plot_ablation_effect_sizes(
                'results/statistical_validation/comprehensive_validation_results.json'
            )
            results['figures'].append('fig_ablation_effect_sizes')
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            results['errors'].append(str(e))
        
        # Figure 2: 环境-链路相关性
        print("\n[2/6] 生成环境-链路相关性图...")
        try:
            self.plot_environment_link_correlation(
                'results/prior_experiments/e0_env_link_correlation.json'
            )
            results['figures'].append('fig_env_link_correlation')
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            results['errors'].append(str(e))
        
        # Figure 3: CAS特征重要性
        print("\n[3/6] 生成CAS特征重要性图...")
        try:
            self.plot_feature_importance(
                'results/prior_experiments/e1_cas_features.json'
            )
            results['figures'].append('fig_feature_importance')
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            results['errors'].append(str(e))
        
        # Figure 4: 统计验证汇总
        print("\n[4/6] 生成统计验证汇总图...")
        try:
            self.plot_statistical_validation_summary(
                'results/statistical_validation/comprehensive_validation_results.json',
                filename='fig4_statistical_validation_enhanced'
            )
            results['figures'].append('fig4_statistical_validation_enhanced')
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            results['errors'].append(str(e))
        
        # Figure 5: 先验实验面板
        print("\n[5/6] 生成先验实验汇总面板...")
        try:
            self.plot_prior_experiments_panel(
                'results/prior_experiments/e0_env_link_correlation.json',
                'results/prior_experiments/e1_cas_features.json',
                'results/prior_experiments/e2_safety_threshold.json',
                'results/prior_experiments/e3_load_balance.json',
                'results/prior_experiments/e4_latency.json'
            )
            results['figures'].append('fig_prior_experiments_panel')
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            results['errors'].append(str(e))
        
        # Figure 6: 协议对比
        print("\n[6/6] 生成协议性能对比图...")
        try:
            self.plot_protocol_comparison_premium(
                'results/intel_baselines_unified.json'
            )
            results['figures'].append('fig_protocol_comparison')
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            results['errors'].append(str(e))
        
        # 保存生成记录
        results['total_figures'] = len(results['figures'])
        results['total_errors'] = len(results['errors'])
        
        record_path = self.output_dir / 'generation_record.json'
        with open(record_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n" + "=" * 60)
        print(f"✅ 生成完成: {results['total_figures']} 张图表")
        if results['errors']:
            print(f"⚠️  错误数: {results['total_errors']}")
        print(f"📁 输出目录: {self.output_dir}")
        print("=" * 60)
        
        return results


def main():
    generator = PremiumFigureGenerator()
    results = generator.generate_all_premium_figures()
    return results


if __name__ == '__main__':
    main()
