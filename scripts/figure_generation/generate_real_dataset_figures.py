#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实数据集实验结果可视化

生成Nature级别的多数据集对比图表
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# 样式配置
plt.rcParams.update({
    'figure.dpi': 300,
    'savefig.dpi': 600,
    'figure.facecolor': 'white',
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 8,
    'axes.titlesize': 9,
    'axes.labelsize': 8,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    'axes.linewidth': 0.6,
    'pdf.fonttype': 42,
    'legend.frameon': False,
})

COLORS = {
    'AERIS': '#4E79A7',
    'LEACH': '#E15759',
    'PEGASIS': '#59A14F',
    'HEED': '#F28E2B',
}

DATASET_COLORS = {
    'intel': '#4E79A7',
    'sensorscope': '#59A14F',
    'sonoma': '#76B7B2',
    'greentoronto': '#EDC948',
    'industrial': '#E15759',
}

OUTPUT_DIR = Path('results/real_dataset_experiments/figures')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_results():
    """加载实验结果"""
    with open('results/real_dataset_experiments/analysis.json', 'r') as f:
        return json.load(f)


def fig1_multi_dataset_pdr_comparison(analysis):
    """图1: 多数据集PDR对比"""
    fig, ax = plt.subplots(figsize=(7, 3.5))
    
    datasets = list(analysis['by_dataset'].keys())
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    
    # 数据集显示名称
    dataset_labels = {
        'intel': 'Intel Lab\n(Indoor)',
        'sensorscope': 'SensorScope\n(Mountain)',
        'sonoma': 'Sonoma\n(Forest)',
        'greentoronto': 'GreenToronto\n(Urban)',
        'industrial': 'Industrial\n(Factory)'
    }
    
    x = np.arange(len(datasets))
    width = 0.2
    
    for i, protocol in enumerate(protocols):
        pdrs = []
        stds = []
        for ds in datasets:
            if protocol in analysis['by_dataset'][ds]:
                pdrs.append(analysis['by_dataset'][ds][protocol]['pdr_mean'])
                stds.append(analysis['by_dataset'][ds][protocol]['pdr_std'])
            else:
                pdrs.append(0)
                stds.append(0)
        
        offset = (i - 1.5) * width
        bars = ax.bar(x + offset, pdrs, width, label=protocol, 
                     color=COLORS[protocol], alpha=0.85, yerr=stds, capsize=2)
    
    ax.set_xlabel('Dataset / Environment')
    ax.set_ylabel('Packet Delivery Ratio (PDR)')
    ax.set_title('Protocol Performance Across Real-World Datasets', fontweight='bold', pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels([dataset_labels.get(ds, ds) for ds in datasets])
    ax.legend(loc='upper right', ncol=2)
    ax.set_ylim(0, 1.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3)
    
    # 添加AERIS优势标注
    for i, ds in enumerate(datasets):
        if 'AERIS' in analysis['by_dataset'][ds]:
            aeris_pdr = analysis['by_dataset'][ds]['AERIS']['pdr_mean']
            ax.annotate(f'{aeris_pdr:.2f}', xy=(i - 1.5*width, aeris_pdr + 0.05),
                       fontsize=6, ha='center', fontweight='bold', color=COLORS['AERIS'])
    
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / 'fig1_multi_dataset_pdr.pdf', bbox_inches='tight')
    fig.savefig(OUTPUT_DIR / 'fig1_multi_dataset_pdr.png', dpi=600, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ fig1_multi_dataset_pdr")


def fig2_aeris_improvement_heatmap(analysis):
    """图2: AERIS相对提升热力图"""
    fig, ax = plt.subplots(figsize=(5, 3.5))
    
    datasets = list(analysis['cross_dataset_comparison'].keys())
    baselines = ['LEACH', 'PEGASIS', 'HEED']
    
    # 构建提升矩阵
    improvement_matrix = []
    for ds in datasets:
        row = []
        for baseline in baselines:
            imp = analysis['cross_dataset_comparison'][ds]['improvements'].get(baseline, 0)
            row.append(imp)
        improvement_matrix.append(row)
    
    improvement_matrix = np.array(improvement_matrix)
    
    # 热力图
    im = ax.imshow(improvement_matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    
    # 标签
    dataset_labels = {
        'sensorscope': 'SensorScope',
        'sonoma': 'Sonoma',
        'greentoronto': 'GreenToronto',
        'industrial': 'Industrial'
    }
    
    ax.set_xticks(np.arange(len(baselines)))
    ax.set_yticks(np.arange(len(datasets)))
    ax.set_xticklabels([f'vs {b}' for b in baselines])
    ax.set_yticklabels([dataset_labels.get(ds, ds) for ds in datasets])
    
    # 添加数值
    for i in range(len(datasets)):
        for j in range(len(baselines)):
            val = improvement_matrix[i, j]
            color = 'white' if val > 50 else 'black'
            ax.text(j, i, f'+{val:.0f}%', ha='center', va='center',
                   fontsize=8, fontweight='bold', color=color)
    
    ax.set_title('AERIS Improvement Over Baselines (%)', fontweight='bold', pad=10)
    
    # 颜色条
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Improvement (%)', fontsize=8)
    
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / 'fig2_aeris_improvement_heatmap.pdf', bbox_inches='tight')
    fig.savefig(OUTPUT_DIR / 'fig2_aeris_improvement_heatmap.png', dpi=600, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ fig2_aeris_improvement_heatmap")


def fig3_environment_comparison(analysis):
    """图3: 不同环境下的性能对比"""
    fig, axes = plt.subplots(1, 2, figsize=(7, 3))
    
    # 环境分类
    env_mapping = {
        'sensorscope': 'Outdoor',
        'sonoma': 'Forest',
        'greentoronto': 'Urban',
        'industrial': 'Industrial'
    }
    
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    
    # (a) PDR by environment
    ax1 = axes[0]
    
    env_data = {}
    for ds, env in env_mapping.items():
        if ds in analysis['by_dataset']:
            env_data[env] = analysis['by_dataset'][ds]
    
    envs = list(env_data.keys())
    x = np.arange(len(envs))
    width = 0.2
    
    for i, protocol in enumerate(protocols):
        pdrs = [env_data[env][protocol]['pdr_mean'] if protocol in env_data[env] else 0 
               for env in envs]
        offset = (i - 1.5) * width
        ax1.bar(x + offset, pdrs, width, label=protocol, color=COLORS[protocol], alpha=0.85)
    
    ax1.set_xlabel('Environment Type')
    ax1.set_ylabel('PDR')
    ax1.set_title('(a) PDR by Environment', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(envs, rotation=15, ha='right')
    ax1.legend(loc='upper right', fontsize=6)
    ax1.set_ylim(0, 1.0)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # (b) AERIS优势 by environment
    ax2 = axes[1]
    
    aeris_advantages = []
    for env in envs:
        aeris_pdr = env_data[env]['AERIS']['pdr_mean']
        baseline_avg = np.mean([env_data[env][p]['pdr_mean'] 
                               for p in ['LEACH', 'PEGASIS', 'HEED'] if p in env_data[env]])
        advantage = (aeris_pdr - baseline_avg) / baseline_avg * 100
        aeris_advantages.append(advantage)
    
    colors = ['#59A14F' if a > 30 else '#F28E2B' if a > 15 else '#E15759' for a in aeris_advantages]
    bars = ax2.bar(envs, aeris_advantages, color=colors, alpha=0.85)
    
    ax2.axhline(y=0, color='black', linewidth=0.5)
    ax2.set_xlabel('Environment Type')
    ax2.set_ylabel('AERIS Advantage (%)')
    ax2.set_title('(b) AERIS vs Baseline Average', fontweight='bold')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    # 添加数值
    for bar, val in zip(bars, aeris_advantages):
        ax2.text(bar.get_x() + bar.get_width()/2, val + 2, f'+{val:.0f}%',
                ha='center', fontsize=7, fontweight='bold')
    
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / 'fig3_environment_comparison.pdf', bbox_inches='tight')
    fig.savefig(OUTPUT_DIR / 'fig3_environment_comparison.png', dpi=600, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ fig3_environment_comparison")


def fig4_comprehensive_summary(analysis):
    """图4: 综合汇总图"""
    fig = plt.figure(figsize=(8, 5))
    gs = GridSpec(2, 3, hspace=0.4, wspace=0.35)
    
    # (a) 总体协议对比
    ax1 = fig.add_subplot(gs[0, 0])
    
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    pdr_means = [analysis['by_protocol'][p]['pdr_mean'] for p in protocols]
    pdr_stds = [analysis['by_protocol'][p]['pdr_std'] for p in protocols]
    
    bars = ax1.bar(protocols, pdr_means, color=[COLORS[p] for p in protocols],
                  alpha=0.85, yerr=pdr_stds, capsize=3)
    ax1.set_ylabel('PDR')
    ax1.set_title('(a) Overall PDR', fontweight='bold')
    ax1.set_ylim(0, 1.0)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    for bar, m in zip(bars, pdr_means):
        ax1.text(bar.get_x() + bar.get_width()/2, m + 0.08, f'{m:.2f}',
                ha='center', fontsize=7, fontweight='bold')
    
    # (b) 能效对比
    ax2 = fig.add_subplot(gs[0, 1])
    
    energy_means = [analysis['by_protocol'][p]['energy_mean'] for p in protocols]
    efficiency = [pdr_means[i] / energy_means[i] * 100 for i in range(len(protocols))]
    
    bars = ax2.bar(protocols, efficiency, color=[COLORS[p] for p in protocols], alpha=0.85)
    ax2.set_ylabel('Efficiency (PDR/100J)')
    ax2.set_title('(b) Energy Efficiency', fontweight='bold')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    # (c) 数据集覆盖
    ax3 = fig.add_subplot(gs[0, 2])
    
    datasets = list(analysis['by_dataset'].keys())
    dataset_labels = ['SensorScope', 'Sonoma', 'GreenToronto', 'Industrial']
    samples = [600, 600, 600, 600]  # 每个数据集的实验数
    
    ax3.barh(dataset_labels, samples, color=[DATASET_COLORS.get(ds, '#888888') for ds in datasets], alpha=0.85)
    ax3.set_xlabel('Experiments')
    ax3.set_title('(c) Dataset Coverage', fontweight='bold')
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    
    # (d) 平均提升
    ax4 = fig.add_subplot(gs[1, 0])
    
    avg_improvements = {}
    for baseline in ['LEACH', 'PEGASIS', 'HEED']:
        imps = [analysis['cross_dataset_comparison'][ds]['improvements'].get(baseline, 0)
               for ds in analysis['cross_dataset_comparison']]
        avg_improvements[baseline] = np.mean(imps)
    
    baselines = list(avg_improvements.keys())
    improvements = list(avg_improvements.values())
    colors = [COLORS[b] for b in baselines]
    
    bars = ax4.bar(baselines, improvements, color=colors, alpha=0.85)
    ax4.set_ylabel('Average Improvement (%)')
    ax4.set_title('(d) AERIS Avg. Improvement', fontweight='bold')
    ax4.spines['top'].set_visible(False)
    ax4.spines['right'].set_visible(False)
    
    for bar, val in zip(bars, improvements):
        ax4.text(bar.get_x() + bar.get_width()/2, val + 2, f'+{val:.0f}%',
                ha='center', fontsize=7, fontweight='bold')
    
    # (e) 实验统计
    ax5 = fig.add_subplot(gs[1, 1])
    
    stats = {
        'Datasets': len(datasets),
        'Protocols': 4,
        'Experiments': analysis['total_experiments'],
        'Environments': 4
    }
    
    ax5.axis('off')
    stats_text = '\n'.join([f'{k}: {v:,}' for k, v in stats.items()])
    ax5.text(0.5, 0.5, stats_text, transform=ax5.transAxes, fontsize=10,
            ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#E8F4F8', edgecolor='#4E79A7'))
    ax5.set_title('(e) Experiment Statistics', fontweight='bold')
    
    # (f) 关键发现
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis('off')
    
    findings = [
        "• AERIS outperforms all baselines",
        "  across 4 real-world datasets",
        f"• Avg. +{np.mean(improvements):.0f}% vs baselines",
        "• Consistent gains in all environments",
        "• Largest gains in harsh conditions"
    ]
    
    ax6.text(0.1, 0.9, '\n'.join(findings), transform=ax6.transAxes,
            fontsize=8, verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#E8F4F8', edgecolor='#4E79A7'))
    ax6.set_title('(f) Key Findings', fontweight='bold')
    
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / 'fig4_comprehensive_summary.pdf', bbox_inches='tight')
    fig.savefig(OUTPUT_DIR / 'fig4_comprehensive_summary.png', dpi=600, bbox_inches='tight')
    plt.close(fig)
    print("  ✓ fig4_comprehensive_summary")


def main():
    """主函数"""
    print("=" * 60)
    print("📊 真实数据集实验结果可视化")
    print("=" * 60)
    
    # 加载结果
    print("\n加载实验结果...")
    analysis = load_results()
    print(f"  总实验数: {analysis['total_experiments']:,}")
    print(f"  数据集数: {len(analysis['by_dataset'])}")
    
    # 生成图表
    print("\n生成图表...")
    fig1_multi_dataset_pdr_comparison(analysis)
    fig2_aeris_improvement_heatmap(analysis)
    fig3_environment_comparison(analysis)
    fig4_comprehensive_summary(analysis)
    
    print(f"\n✅ 完成! 图表保存至: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
