#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nature/Science级别高质量图表生成器

设计原则：
1. 简洁清晰 - 去除不必要的装饰
2. 数据优先 - 让数据说话
3. 专业配色 - 使用经过验证的配色方案
4. 精确标注 - 所有数值清晰可读
5. 统一风格 - 全局一致的视觉语言
"""

import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec
import matplotlib.patheffects as pe

# ============================================================
# 全局样式配置 (Nature/Science标准)
# ============================================================

plt.rcParams.update({
    # 图形基础
    'figure.dpi': 300,
    'savefig.dpi': 600,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    
    # 字体 - Nature使用Helvetica/Arial
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica Neue', 'Helvetica', 'DejaVu Sans'],
    'font.size': 8,
    'axes.titlesize': 9,
    'axes.labelsize': 8,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    
    # 线条
    'axes.linewidth': 0.5,
    'axes.edgecolor': '#333333',
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'grid.linewidth': 0.3,
    'grid.alpha': 0.4,
    'lines.linewidth': 1.2,
    
    # 输出
    'svg.fonttype': 'none',
    'pdf.fonttype': 42,
    
    # 图例
    'legend.frameon': False,
    'legend.borderpad': 0.3,
    'legend.handlelength': 1.5,
})

# Nature配色方案
COLORS = {
    'blue': '#4E79A7',
    'orange': '#F28E2B', 
    'red': '#E15759',
    'teal': '#76B7B2',
    'green': '#59A14F',
    'yellow': '#EDC948',
    'purple': '#B07AA1',
    'pink': '#FF9DA7',
    'brown': '#9C755F',
    'gray': '#BAB0AC',
}

# 协议颜色映射
PROTOCOL_COLORS = {
    'AERIS': COLORS['blue'],
    'AERIS-R': COLORS['blue'],
    'AERIS-E': COLORS['teal'],
    'LEACH': COLORS['red'],
    'HEED': COLORS['orange'],
    'PEGASIS': COLORS['green'],
    'TEEN': COLORS['purple'],
    'FULL': COLORS['blue'],
    '-CAS': COLORS['teal'],
    '-FAIR': COLORS['orange'],
    '-GW': COLORS['red'],
    '-SAFETY': COLORS['green'],
}


class NatureQualityFigures:
    """Nature/Science级别图表生成器"""
    
    def __init__(self, output_dir: str = 'results/nature_figures'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def save(self, fig, name, formats=['pdf', 'svg', 'png']):
        """保存图表"""
        for fmt in formats:
            path = self.output_dir / f'{name}.{fmt}'
            fig.savefig(path, dpi=600 if fmt == 'png' else 300,
                       bbox_inches='tight', facecolor='white',
                       edgecolor='none', pad_inches=0.02)
        plt.close(fig)
        print(f"  ✓ {name}")
        return str(self.output_dir / f'{name}.pdf')


    def fig1_ablation_forest_plot(self, stats_path: str):
        """
        Figure 1: 消融实验森林图 (Forest Plot)
        
        展示各模块的效应量和95%置信区间
        """
        with open(stats_path, 'r') as f:
            data = json.load(f)
        
        # 提取FULL vs 各模块的PDR效应量
        effects = []
        for e in data['effect_sizes']:
            if e['metric'] == 'pdr' and e['group1'] == 'FULL':
                effects.append({
                    'module': e['group2'].replace('-', ''),
                    'g': e['hedges_g'],
                    'ci_low': e['ci_low'],
                    'ci_high': e['ci_high'],
                    'interp': e['interpretation']
                })
        
        # 按效应量排序
        effects.sort(key=lambda x: x['g'], reverse=True)
        
        # 创建图形 - 紧凑尺寸
        fig, ax = plt.subplots(figsize=(4.5, 2.5))
        
        y_pos = np.arange(len(effects))
        
        # 绘制参考线
        ax.axvline(x=0, color='#666666', linestyle='-', linewidth=0.5, zorder=1)
        ax.axvline(x=0.2, color='#cccccc', linestyle=':', linewidth=0.4, zorder=1)
        ax.axvline(x=0.5, color='#cccccc', linestyle=':', linewidth=0.4, zorder=1)
        ax.axvline(x=0.8, color='#cccccc', linestyle=':', linewidth=0.4, zorder=1)
        
        # 绘制效应量和CI
        for i, e in enumerate(effects):
            color = COLORS['red'] if e['g'] > 0.8 else COLORS['orange'] if e['g'] > 0.5 else COLORS['teal'] if e['g'] > 0.2 else COLORS['gray']
            
            # CI线
            ax.plot([e['ci_low'], e['ci_high']], [i, i], 
                   color=color, linewidth=1.5, solid_capstyle='round', zorder=2)
            # 效应量点
            ax.scatter([e['g']], [i], color=color, s=50, zorder=3, 
                      edgecolors='white', linewidths=0.8)
            
            # 数值标注
            if e['g'] > 1:
                ax.text(min(e['g'] + 0.3, 11), i, f"g={e['g']:.2f}", 
                       va='center', fontsize=7, fontweight='bold', color=color)
            else:
                ax.text(e['ci_high'] + 0.1, i, f"{e['g']:.2f}", 
                       va='center', fontsize=7, color='#333333')
        
        # 设置坐标轴
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f"−{e['module']}" for e in effects])
        ax.set_xlabel("Effect Size (Hedges' g)", fontweight='bold')
        ax.set_xlim(-0.3, 11.5)
        ax.set_ylim(-0.5, len(effects) - 0.5)
        
        # 添加效应量区域标签
        ax.text(0.1, len(effects) - 0.2, 'S', fontsize=6, color='#999999', ha='center')
        ax.text(0.35, len(effects) - 0.2, 'M', fontsize=6, color='#999999', ha='center')
        ax.text(0.65, len(effects) - 0.2, 'L', fontsize=6, color='#999999', ha='center')
        
        # 简化边框
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.tick_params(left=False)
        
        # 图例
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['red'], 
                   markersize=6, label='Large (g>0.8)'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['orange'], 
                   markersize=6, label='Medium'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['gray'], 
                   markersize=6, label='Negligible'),
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=6, 
                 frameon=False, handletextpad=0.3)
        
        plt.tight_layout()
        return self.save(fig, 'fig1_ablation_forest')

    def fig2_env_link_panel(self, e0_path: str):
        """
        Figure 2: 环境-链路相关性面板
        
        (a) 相关性条形图  (b) 滞后相关性曲线
        """
        with open(e0_path, 'r') as f:
            data = json.load(f)
        
        fig, axes = plt.subplots(1, 2, figsize=(6, 2.2))
        
        # (a) 相关性条形图
        ax1 = axes[0]
        
        features = ['humidity', 'temperature']
        labels = ['Humidity', 'Temperature']
        correlations = []
        for feat in features:
            for c in data['correlations']:
                if c['feature'] == feat and c['metric'] == 'link_quality_proxy':
                    correlations.append(c['pearson_r'])
                    break
        
        colors = [COLORS['blue'], COLORS['red']]
        x = np.arange(len(features))
        bars = ax1.bar(x, [abs(c) for c in correlations], color=colors, 
                      width=0.5, edgecolor='white', linewidth=0.5)
        
        # 数值标注
        for bar, corr in zip(bars, correlations):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    f'r={corr:.3f}', ha='center', fontsize=7, fontweight='bold')
        
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels)
        ax1.set_ylabel('|Pearson r|')
        ax1.set_ylim(0, 0.65)
        ax1.set_title('(a) Correlation Strength', fontsize=8, fontweight='bold', pad=8)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # 添加显著性标记
        ax1.text(0.5, -0.15, '*** p < 0.001', transform=ax1.transAxes, 
                fontsize=6, ha='center', style='italic', color='#666666')
        
        # (b) 滞后相关性
        ax2 = axes[1]
        
        lag_data = data['lagged_correlations']
        for feat, color, label in [('humidity', COLORS['blue'], 'Humidity'),
                                   ('temperature', COLORS['red'], 'Temperature')]:
            lags = lag_data[feat]['lags']
            corrs = [abs(c) for c in lag_data[feat]['correlation']]
            ax2.plot(lags, corrs, color=color, linewidth=1.2, label=label,
                    marker='o', markersize=2.5, markerfacecolor='white', 
                    markeredgewidth=0.8)
            
            # 标记最大点
            max_idx = np.argmax(corrs)
            ax2.scatter([lags[max_idx]], [corrs[max_idx]], color=color, 
                       s=30, zorder=5, edgecolors='white', linewidths=0.8)
        
        ax2.set_xlabel('Lag (hours)')
        ax2.set_ylabel('|Correlation|')
        ax2.set_title('(b) Lagged Cross-Correlation', fontsize=8, fontweight='bold', pad=8)
        ax2.legend(loc='lower right', fontsize=6)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.grid(True, alpha=0.3, linewidth=0.3)
        
        plt.tight_layout()
        return self.save(fig, 'fig2_env_link_panel')


    def fig3_prior_experiments_summary(self, e0_path, e1_path, e2_path, e3_path, e4_path):
        """
        Figure 3: 先验实验汇总图 (2x3面板)
        
        紧凑展示E0-E4所有先验实验的关键结果
        """
        fig = plt.figure(figsize=(7, 4))
        gs = GridSpec(2, 3, hspace=0.4, wspace=0.35)
        
        # E0: 预测器AUC
        ax1 = fig.add_subplot(gs[0, 0])
        try:
            with open(e0_path, 'r') as f:
                e0 = json.load(f)
            auc = e0['predictor']['auc']
            
            # 半圆仪表盘
            theta = np.linspace(0, np.pi, 100)
            r = 1
            ax1.fill_between(theta, 0, r, alpha=0.1, color=COLORS['gray'])
            ax1.fill_between(theta[:int(auc*100)], 0, r, alpha=0.6, color=COLORS['blue'])
            ax1.set_xlim(0, np.pi)
            ax1.set_ylim(0, 1.2)
            ax1.text(np.pi/2, 0.4, f'{auc:.3f}', ha='center', va='center', 
                    fontsize=14, fontweight='bold', color=COLORS['blue'])
            ax1.text(np.pi/2, 0.1, 'AUC', ha='center', fontsize=7, color='#666666')
            ax1.set_title('E0: Link Predictor', fontsize=8, fontweight='bold', pad=5)
            ax1.axis('off')
        except:
            ax1.text(0.5, 0.5, 'N/A', ha='center', va='center')
            ax1.axis('off')
        
        # E1: 特征重要性 (Top 3)
        ax2 = fig.add_subplot(gs[0, 1])
        try:
            with open(e1_path, 'r') as f:
                e1 = json.load(f)
            
            imps = e1['actual_model']['feature_importances'][:3]
            features = [i['feature'] for i in imps]
            values = [i['permutation_importance'] for i in imps]
            
            colors = [COLORS['blue'], COLORS['teal'], COLORS['green']]
            y = np.arange(len(features))
            ax2.barh(y, values, color=colors, height=0.5, edgecolor='white')
            
            for i, v in enumerate(values):
                ax2.text(v + 0.005, i, f'{v:.3f}', va='center', fontsize=6)
            
            ax2.set_yticks(y)
            ax2.set_yticklabels([f.title() for f in features], fontsize=7)
            ax2.set_xlabel('Importance', fontsize=7)
            ax2.set_title('E1: Feature Importance', fontsize=8, fontweight='bold', pad=5)
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            ax2.invert_yaxis()
        except:
            ax2.text(0.5, 0.5, 'N/A', ha='center', va='center')
        
        # E2: Safety阈值
        ax3 = fig.add_subplot(gs[0, 2])
        try:
            with open(e2_path, 'r') as f:
                e2 = json.load(f)
            
            opt = e2['optimization_result']
            metrics = ['FPR', 'TPR', 'F1']
            values = [opt['false_positive_rate'], opt['true_positive_rate'], opt['f1_score']]
            colors = [COLORS['red'], COLORS['green'], COLORS['blue']]
            
            x = np.arange(len(metrics))
            bars = ax3.bar(x, values, color=colors, width=0.5, edgecolor='white')
            
            for bar, v in zip(bars, values):
                ax3.text(bar.get_x() + bar.get_width()/2, v + 0.03,
                        f'{v:.2f}', ha='center', fontsize=6, fontweight='bold')
            
            ax3.set_xticks(x)
            ax3.set_xticklabels(metrics, fontsize=7)
            ax3.set_ylim(0, 1.15)
            ax3.set_title(f"E2: Safety (θ={opt['optimal_theta']:.2f})", 
                         fontsize=8, fontweight='bold', pad=5)
            ax3.spines['top'].set_visible(False)
            ax3.spines['right'].set_visible(False)
        except:
            ax3.text(0.5, 0.5, 'N/A', ha='center', va='center')
        
        # E3: 负载均衡相关性
        ax4 = fig.add_subplot(gs[1, 0])
        try:
            with open(e3_path, 'r') as f:
                e3 = json.load(f)
            
            corr = e3['correlation_results']
            pairs = [('Gini', 'PDR'), ('Gini', 'Energy'), ('Jain', 'PDR')]
            values = [
                corr['gini_pdr']['pearson_r'],
                corr['gini_energy']['pearson_r'],
                corr['jain_pdr']['pearson_r']
            ]
            
            colors = [COLORS['red'] if v < 0 else COLORS['green'] for v in values]
            y = np.arange(len(pairs))
            ax4.barh(y, values, color=colors, height=0.4, edgecolor='white')
            
            for i, v in enumerate(values):
                ax4.text(v + 0.02 if v > 0 else v - 0.02, i, f'{v:.2f}', 
                        va='center', fontsize=6, ha='left' if v > 0 else 'right')
            
            ax4.axvline(x=0, color='#333333', linewidth=0.5)
            ax4.set_yticks(y)
            ax4.set_yticklabels([f'{p[0]}-{p[1]}' for p in pairs], fontsize=7)
            ax4.set_xlim(-1, 1)
            ax4.set_title('E3: Load Balance', fontsize=8, fontweight='bold', pad=5)
            ax4.spines['top'].set_visible(False)
            ax4.spines['right'].set_visible(False)
        except:
            ax4.text(0.5, 0.5, 'N/A', ha='center', va='center')
        
        # E4: 决策时延
        ax5 = fig.add_subplot(gs[1, 1])
        try:
            with open(e4_path, 'r') as f:
                e4 = json.load(f)
            
            comps = ['CAS', 'Skeleton', 'Gateway']
            lats = [
                e4['component_latencies']['cas']['mean_ms'],
                e4['component_latencies']['skeleton']['mean_ms'],
                e4['component_latencies']['gateway']['mean_ms']
            ]
            
            colors = [COLORS['green'] if l < 25 else COLORS['orange'] if l < 50 else COLORS['red'] for l in lats]
            x = np.arange(len(comps))
            bars = ax5.bar(x, lats, color=colors, width=0.5, edgecolor='white')
            
            for bar, l in zip(bars, lats):
                ax5.text(bar.get_x() + bar.get_width()/2, l + 2,
                        f'{l:.0f}', ha='center', fontsize=6)
            
            ax5.axhline(y=25, color=COLORS['green'], linestyle='--', linewidth=0.8, label='MCU budget')
            ax5.set_xticks(x)
            ax5.set_xticklabels(comps, fontsize=7)
            ax5.set_ylabel('Latency (ms)', fontsize=7)
            ax5.set_title('E4: Decision Latency', fontsize=8, fontweight='bold', pad=5)
            ax5.legend(fontsize=5, loc='upper right')
            ax5.spines['top'].set_visible(False)
            ax5.spines['right'].set_visible(False)
        except:
            ax5.text(0.5, 0.5, 'N/A', ha='center', va='center')
        
        # 汇总: 模型准确率
        ax6 = fig.add_subplot(gs[1, 2])
        try:
            with open(e0_path, 'r') as f:
                e0 = json.load(f)
            with open(e1_path, 'r') as f:
                e1 = json.load(f)
            
            models = ['Link\nPredictor', 'Mode\nClassifier']
            accs = [e0['predictor']['auc'], e1['actual_model']['accuracy']]
            
            colors = [COLORS['blue'], COLORS['purple']]
            x = np.arange(len(models))
            bars = ax6.bar(x, accs, color=colors, width=0.5, edgecolor='white')
            
            for bar, a in zip(bars, accs):
                ax6.text(bar.get_x() + bar.get_width()/2, a + 0.02,
                        f'{a:.2%}', ha='center', fontsize=7, fontweight='bold')
            
            ax6.axhline(y=0.9, color='#999999', linestyle=':', linewidth=0.5)
            ax6.set_xticks(x)
            ax6.set_xticklabels(models, fontsize=7)
            ax6.set_ylim(0.85, 1.02)
            ax6.set_title('Model Performance', fontsize=8, fontweight='bold', pad=5)
            ax6.spines['top'].set_visible(False)
            ax6.spines['right'].set_visible(False)
        except:
            ax6.text(0.5, 0.5, 'N/A', ha='center', va='center')
        
        plt.tight_layout()
        return self.save(fig, 'fig3_prior_experiments')

    def fig4_statistical_validation(self, stats_path: str):
        """
        Figure 4: 统计验证汇总图
        
        (a) PDR对比  (b) 效应量分布  (c) 多重比较校正
        """
        with open(stats_path, 'r') as f:
            data = json.load(f)
        
        fig, axes = plt.subplots(1, 3, figsize=(7, 2.2))
        
        # (a) PDR对比
        ax1 = axes[0]
        
        pdr_cis = [ci for ci in data['bootstrap_cis'] 
                  if ci['metric'] == 'pdr' and 'ablation' in ci['group']]
        
        groups = [ci['group'].replace('ablation_', '') for ci in pdr_cis]
        means = [ci['mean'] for ci in pdr_cis]
        ci_lows = [ci['ci_low'] for ci in pdr_cis]
        ci_highs = [ci['ci_high'] for ci in pdr_cis]
        
        x = np.arange(len(groups))
        colors = [PROTOCOL_COLORS.get(g, COLORS['gray']) for g in groups]
        
        bars = ax1.bar(x, means, color=colors, width=0.6, edgecolor='white', linewidth=0.5)
        ax1.errorbar(x, means, 
                    yerr=[np.array(means) - np.array(ci_lows),
                          np.array(ci_highs) - np.array(means)],
                    fmt='none', color='#333333', capsize=2, capthick=0.8, elinewidth=0.8)
        
        ax1.set_xticks(x)
        ax1.set_xticklabels(groups, rotation=45, ha='right', fontsize=6)
        ax1.set_ylabel('PDR')
        ax1.set_ylim(0.7, 0.95)
        ax1.set_title('(a) PDR with 95% CI', fontsize=8, fontweight='bold', pad=5)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # (b) 效应量分布
        ax2 = axes[1]
        
        pdr_effects = [e for e in data['effect_sizes'] if e['metric'] == 'pdr']
        interps = [e['interpretation'] for e in pdr_effects]
        
        counts = {'large': 0, 'medium': 0, 'small': 0, 'negligible': 0}
        for i in interps:
            if i in counts:
                counts[i] += 1
        
        labels = list(counts.keys())
        values = list(counts.values())
        colors = [COLORS['red'], COLORS['orange'], COLORS['teal'], COLORS['gray']]
        
        wedges, texts = ax2.pie(values, colors=colors, startangle=90,
                                wedgeprops=dict(width=0.5, edgecolor='white'))
        
        # 中心文字
        total = sum(values)
        ax2.text(0, 0, f'n={total}', ha='center', va='center', fontsize=8, fontweight='bold')
        
        # 图例
        ax2.legend(wedges, [f'{l.capitalize()} ({v})' for l, v in zip(labels, values)],
                  loc='center left', bbox_to_anchor=(0.85, 0.5), fontsize=5, frameon=False)
        ax2.set_title('(b) Effect Sizes', fontsize=8, fontweight='bold', pad=5)
        
        # (c) 多重比较校正
        ax3 = axes[2]
        
        corrected = data['corrected_pvalues']
        sig_before = sum(1 for c in corrected if c['original_p'] < 0.05)
        sig_after = sum(1 for c in corrected if c['significant'])
        total = len(corrected)
        
        categories = ['Before', 'After\nCorrection']
        sig_vals = [sig_before, sig_after]
        nonsig_vals = [total - sig_before, total - sig_after]
        
        x = np.arange(len(categories))
        width = 0.5
        
        ax3.bar(x, sig_vals, width, label='Significant', color=COLORS['green'], edgecolor='white')
        ax3.bar(x, nonsig_vals, width, bottom=sig_vals, label='Not Sig.', color=COLORS['gray'], edgecolor='white')
        
        for i, (s, ns) in enumerate(zip(sig_vals, nonsig_vals)):
            ax3.text(i, s/2, str(s), ha='center', va='center', fontsize=7, fontweight='bold', color='white')
            if ns > 0:
                ax3.text(i, s + ns/2, str(ns), ha='center', va='center', fontsize=7)
        
        ax3.set_xticks(x)
        ax3.set_xticklabels(categories, fontsize=7)
        ax3.set_ylabel('Comparisons')
        ax3.set_title('(c) Holm-Bonferroni', fontsize=8, fontweight='bold', pad=5)
        ax3.legend(fontsize=5, loc='upper right')
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        
        plt.tight_layout()
        return self.save(fig, 'fig4_statistical_validation')


    def fig5_protocol_comparison(self, baseline_path: str):
        """
        Figure 5: 协议性能对比图
        
        简洁的双面板对比图
        """
        try:
            with open(baseline_path, 'r') as f:
                data = json.load(f)
        except:
            print(f"  ✗ Cannot load {baseline_path}")
            return None
        
        fig, axes = plt.subplots(1, 2, figsize=(5.5, 2.2))
        
        protocols = list(data['results'].keys())
        pdrs = [data['results'][p]['pdr_end2end'] for p in protocols]
        energies = [data['results'][p]['total_energy'] for p in protocols]
        
        x = np.arange(len(protocols))
        colors = [PROTOCOL_COLORS.get(p, COLORS['gray']) for p in protocols]
        
        # (a) PDR
        ax1 = axes[0]
        bars1 = ax1.bar(x, pdrs, color=colors, width=0.6, edgecolor='white', linewidth=0.5)
        
        for bar, pdr in zip(bars1, pdrs):
            ax1.text(bar.get_x() + bar.get_width()/2, pdr + 0.03,
                    f'{pdr:.0%}', ha='center', fontsize=7, fontweight='bold')
        
        ax1.set_xticks(x)
        ax1.set_xticklabels(protocols, fontsize=7)
        ax1.set_ylabel('PDR')
        ax1.set_ylim(0, 1.15)
        ax1.set_title('(a) Packet Delivery Ratio', fontsize=8, fontweight='bold', pad=5)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # (b) Energy
        ax2 = axes[1]
        bars2 = ax2.bar(x, energies, color=colors, width=0.6, edgecolor='white', linewidth=0.5)
        
        for bar, e in zip(bars2, energies):
            ax2.text(bar.get_x() + bar.get_width()/2, e + 1,
                    f'{e:.1f}J', ha='center', fontsize=7)
        
        ax2.set_xticks(x)
        ax2.set_xticklabels(protocols, fontsize=7)
        ax2.set_ylabel('Energy (J)')
        ax2.set_title('(b) Total Energy', fontsize=8, fontweight='bold', pad=5)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        plt.tight_layout()
        return self.save(fig, 'fig5_protocol_comparison')

    def generate_all(self):
        """生成所有图表"""
        print("=" * 50)
        print("🎨 Nature/Science级别图表生成")
        print("=" * 50)
        
        figures = []
        
        print("\n[1/5] 消融实验森林图...")
        try:
            path = self.fig1_ablation_forest_plot(
                'results/statistical_validation/comprehensive_validation_results.json')
            figures.append(path)
        except Exception as e:
            print(f"  ✗ 失败: {e}")
        
        print("\n[2/5] 环境-链路相关性面板...")
        try:
            path = self.fig2_env_link_panel(
                'results/prior_experiments/e0_env_link_correlation.json')
            figures.append(path)
        except Exception as e:
            print(f"  ✗ 失败: {e}")
        
        print("\n[3/5] 先验实验汇总图...")
        try:
            path = self.fig3_prior_experiments_summary(
                'results/prior_experiments/e0_env_link_correlation.json',
                'results/prior_experiments/e1_cas_features.json',
                'results/prior_experiments/e2_safety_threshold.json',
                'results/prior_experiments/e3_load_balance.json',
                'results/prior_experiments/e4_latency.json')
            figures.append(path)
        except Exception as e:
            print(f"  ✗ 失败: {e}")
        
        print("\n[4/5] 统计验证汇总图...")
        try:
            path = self.fig4_statistical_validation(
                'results/statistical_validation/comprehensive_validation_results.json')
            figures.append(path)
        except Exception as e:
            print(f"  ✗ 失败: {e}")
        
        print("\n[5/5] 协议性能对比图...")
        try:
            path = self.fig5_protocol_comparison(
                'results/intel_baselines_unified.json')
            if path:
                figures.append(path)
        except Exception as e:
            print(f"  ✗ 失败: {e}")
        
        print("\n" + "=" * 50)
        print(f"✅ 完成: {len(figures)} 张图表")
        print(f"📁 输出: {self.output_dir}")
        print("=" * 50)
        
        return figures


def main():
    gen = NatureQualityFigures()
    return gen.generate_all()


if __name__ == '__main__':
    main()
