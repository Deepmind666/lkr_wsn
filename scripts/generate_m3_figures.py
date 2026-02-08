#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Figure 1: Network Scale and Protocol Comparison (4×3=12 panels)
========================================================================
Plan v1 Section M3: 12面板规模对比图

布局设计:
- 行1-3: 50/100/200节点
- 列1-4: PDR / Energy / Lifetime / Dead Nodes
- 每子图5条对比线: AERIS/LEACH/HEED/PEGASIS/TEEN
- 统一配色和标记

作者: Claude (AI Assistant)
日期: 2025-01-02
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

# 专业配色方案 (Nature/Science style, more vibrant)
COLORS = {
    'AERIS': '#E64B35',      # Nature Red (primary - stands out)
    'LEACH': '#4DBBD5',      # Nature Cyan
    'HEED': '#00A087',       # Nature Teal
    'PEGASIS': '#3C5488',    # Nature Blue
    'TEEN': '#F39B7F',       # Nature Salmon
}

MARKERS = {
    'AERIS': 'o',
    'LEACH': 's',
    'HEED': '^',
    'PEGASIS': 'D',
    'TEEN': 'v',
}

LINESTYLES = {
    'AERIS': '-',
    'LEACH': '--',
    'HEED': '-.',
    'PEGASIS': ':',
    'TEEN': (0, (3, 1, 1, 1)),  # densely dash-dotted
}

# 设置专业图表样式
plt.rcParams.update({
    'font.family': 'Arial',
    'font.size': 9,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 7,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'axes.linewidth': 1.0,
    'lines.linewidth': 1.5,
    'lines.markersize': 5,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def compute_ci95(values):
    arr = np.array(values)
    n = len(arr)
    if n < 2:
        return 0.0
    return float(1.96 * np.std(arr, ddof=1) / np.sqrt(n))

def generate_figure1_scale_comparison():
    """生成Figure 1: 12面板规模对比图"""

    # 加载实验数据
    results_dir = Path('c:/AERIS-WSN-Protocol/results/experiments_20250102')
    scale_data = load_json(results_dir / 'scale_experiments.json')

    # 创建图表: 3行(节点数) × 4列(指标)
    fig, axes = plt.subplots(3, 4, figsize=(14, 10))
    fig.subplots_adjust(hspace=0.35, wspace=0.35)

    node_counts = [50, 100, 200]
    protocols = ['AERIS', 'LEACH', 'HEED', 'PEGASIS', 'TEEN']
    metrics = ['pdr', 'energy', 'lifetime']
    metric_labels = ['PDR', 'Energy (J)', 'Lifetime (rounds)']

    # 第四列: PDR改进百分比
    for row_idx, num_nodes in enumerate(node_counts):
        # 列1: PDR
        ax = axes[row_idx, 0]
        for proto in protocols:
            key = f'N{num_nodes}_{proto}'
            if key in scale_data:
                pdr_mean = scale_data[key]['pdr']['mean']
                pdr_ci = scale_data[key]['pdr']['ci95']
                ax.bar(protocols.index(proto), pdr_mean,
                      yerr=pdr_ci, capsize=3,
                      color=COLORS[proto], alpha=0.8,
                      label=proto if row_idx == 0 else None)

        ax.set_ylabel('PDR' if row_idx == 1 else '')
        ax.set_title(f'{num_nodes} Nodes - PDR', fontweight='bold')
        ax.set_xticks(range(len(protocols)))
        ax.set_xticklabels(protocols, rotation=45, ha='right')
        ax.set_ylim(0, 1.05)  # 修正：完整显示0-1范围

        # 列2: Energy
        ax = axes[row_idx, 1]
        for proto in protocols:
            key = f'N{num_nodes}_{proto}'
            if key in scale_data:
                energy_mean = scale_data[key]['energy']['mean']
                energy_ci = scale_data[key]['energy']['ci95']
                ax.bar(protocols.index(proto), energy_mean,
                      yerr=energy_ci, capsize=3,
                      color=COLORS[proto], alpha=0.8)

        ax.set_ylabel('Energy (J)' if row_idx == 1 else '')
        ax.set_title(f'{num_nodes} Nodes - Energy', fontweight='bold')
        ax.set_xticks(range(len(protocols)))
        ax.set_xticklabels(protocols, rotation=45, ha='right')

        # 列3: Lifetime
        ax = axes[row_idx, 2]
        for proto in protocols:
            key = f'N{num_nodes}_{proto}'
            if key in scale_data:
                lifetime_mean = scale_data[key]['lifetime']['mean']
                lifetime_ci = scale_data[key]['lifetime']['ci95']
                ax.bar(protocols.index(proto), lifetime_mean,
                      yerr=lifetime_ci, capsize=3,
                      color=COLORS[proto], alpha=0.8)

        ax.set_ylabel('Lifetime (rounds)' if row_idx == 1 else '')
        ax.set_title(f'{num_nodes} Nodes - Lifetime', fontweight='bold')
        ax.set_xticks(range(len(protocols)))
        ax.set_xticklabels(protocols, rotation=45, ha='right')

        # 列4: PDR绝对差值 (相对于LEACH, 百分点)
        ax = axes[row_idx, 3]
        leach_key = f'N{num_nodes}_LEACH'
        if leach_key in scale_data:
            leach_pdr = scale_data[leach_key]['pdr']['mean']
            improvements = []
            for proto in protocols:
                key = f'N{num_nodes}_{proto}'
                if key in scale_data:
                    pdr = scale_data[key]['pdr']['mean']
                    # 使用绝对差值(百分点)而非相对百分比
                    imp = (pdr - leach_pdr) * 100
                    improvements.append(imp)
                else:
                    improvements.append(0)

            colors = [COLORS[p] for p in protocols]
            bars = ax.bar(range(len(protocols)), improvements,
                         color=colors, alpha=0.8)
            ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

            # 添加数值标签
            for i, (bar, imp) in enumerate(zip(bars, improvements)):
                if abs(imp) > 1:  # 只显示有意义的差值
                    ypos = imp + 2 if imp > 0 else imp - 3
                    ax.text(i, ypos, f'{imp:.0f}', ha='center', fontsize=7, fontweight='bold')

        ax.set_ylabel('ΔPDR (pp)' if row_idx == 1 else '')
        ax.set_title(f'{num_nodes} Nodes - PDR Diff', fontweight='bold')
        ax.set_xticks(range(len(protocols)))
        ax.set_xticklabels(protocols, rotation=45, ha='right')
        ax.set_ylim(-10, 70)  # 固定刻度范围

    # 添加统一图例
    fig.legend(protocols, loc='upper center', ncol=5,
              framealpha=0.9, bbox_to_anchor=(0.5, 1.02))

    # 添加总标题 (不包含Figure编号，由LaTeX管理)
    fig.suptitle('Network Scale Impact on Protocol Performance',
                fontsize=12, fontweight='bold', y=1.05)

    # 保存图表
    output_dir = Path('c:/AERIS-WSN-Protocol/results/experiments_20250102')
    for fmt in ['pdf', 'png', 'svg']:
        filepath = output_dir / f'figure1_scale_comparison.{fmt}'
        fig.savefig(filepath, format=fmt, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        print(f"Saved: {filepath}")

    # 复制到for_submission
    submission_dir = Path('c:/AERIS-WSN-Protocol/for_submission')
    submission_dir.mkdir(exist_ok=True)
    for fmt in ['pdf', 'png']:
        fig.savefig(submission_dir / f'figure1_scale_comparison.{fmt}',
                   format=fmt, dpi=300, bbox_inches='tight', facecolor='white')

    plt.close(fig)
    print("\nFigure 1 generated successfully!")
    print(f"  Dimensions: 14×10 inches (355×254 mm)")
    print(f"  Panels: 3 rows × 4 columns = 12")
    print(f"  Resolution: 300 DPI")

def generate_figure2_topology_comparison():
    """生成Figure 2: 拓扑泛化对比图 (3列×2行=6面板)"""

    results_dir = Path('c:/AERIS-WSN-Protocol/results/experiments_20250102')
    topo_data = load_json(results_dir / 'topology_experiments.json')

    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    fig.subplots_adjust(hspace=0.35, wspace=0.35)

    topologies = ['uniform', 'corridor31', 'corridor41']
    topo_labels = ['Uniform', 'Corridor (31%)', 'Corridor (41%)']
    protocols = ['AERIS', 'LEACH', 'HEED', 'PEGASIS', 'TEEN']

    for col_idx, (topo, topo_label) in enumerate(zip(topologies, topo_labels)):
        # 行1: PDR
        ax = axes[0, col_idx]
        for proto in protocols:
            key = f'{topo}_{proto}'
            if key in topo_data:
                pdr_mean = topo_data[key]['pdr']['mean']
                pdr_ci = topo_data[key]['pdr']['ci95']
                ax.bar(protocols.index(proto), pdr_mean,
                      yerr=pdr_ci, capsize=3,
                      color=COLORS[proto], alpha=0.8,
                      label=proto if col_idx == 0 else None)

        ax.set_ylabel('PDR' if col_idx == 0 else '')
        ax.set_title(f'{topo_label} - PDR', fontweight='bold')
        ax.set_xticks(range(len(protocols)))
        ax.set_xticklabels(protocols, rotation=45, ha='right')
        ax.set_ylim(0, 1.05)  # 修正：完整显示0-1范围

        # 行2: Energy
        ax = axes[1, col_idx]
        for proto in protocols:
            key = f'{topo}_{proto}'
            if key in topo_data:
                energy_mean = topo_data[key]['energy']['mean']
                energy_ci = topo_data[key]['energy']['ci95']
                ax.bar(protocols.index(proto), energy_mean,
                      yerr=energy_ci, capsize=3,
                      color=COLORS[proto], alpha=0.8)

        ax.set_ylabel('Energy (J)' if col_idx == 0 else '')
        ax.set_title(f'{topo_label} - Energy', fontweight='bold')
        ax.set_xticks(range(len(protocols)))
        ax.set_xticklabels(protocols, rotation=45, ha='right')

    # 添加图例
    fig.legend(protocols, loc='upper center', ncol=5,
              framealpha=0.9, bbox_to_anchor=(0.5, 1.02))

    fig.suptitle('Topology Generalization Performance',
                fontsize=12, fontweight='bold', y=1.06)

    # 保存
    output_dir = Path('c:/AERIS-WSN-Protocol/results/experiments_20250102')
    for fmt in ['pdf', 'png', 'svg']:
        fig.savefig(output_dir / f'figure2_topology_comparison.{fmt}',
                   format=fmt, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Saved: figure2_topology_comparison.{fmt}")

    submission_dir = Path('c:/AERIS-WSN-Protocol/for_submission')
    for fmt in ['pdf', 'png']:
        fig.savefig(submission_dir / f'figure2_topology_comparison.{fmt}',
                   format=fmt, dpi=300, bbox_inches='tight', facecolor='white')

    plt.close(fig)
    print("\nFigure 2 generated successfully!")

def generate_figure3_sensitivity():
    """生成Figure 3: 参数敏感度分析 (3×3=9面板)"""

    results_dir = Path('c:/AERIS-WSN-Protocol/results/experiments_20250102')
    energy_data = load_json(results_dir / 'energy_experiments.json')
    rounds_data = load_json(results_dir / 'rounds_experiments.json')

    fig, axes = plt.subplots(3, 3, figsize=(12, 10))
    fig.subplots_adjust(hspace=0.4, wspace=0.35)

    protocols = ['AERIS', 'LEACH', 'HEED', 'PEGASIS', 'TEEN']

    # 行1: 初始能量敏感度 - PDR, Energy, Lifetime
    energy_levels = [0.25, 0.5, 1.0, 2.0]

    for col_idx, metric in enumerate(['pdr', 'energy', 'lifetime']):
        ax = axes[0, col_idx]
        for proto in protocols:
            values = []
            cis = []
            for e in energy_levels:
                key = f'E{e}_{proto}'
                if key in energy_data:
                    values.append(energy_data[key][metric]['mean'])
                    cis.append(energy_data[key][metric]['ci95'])
                else:
                    values.append(np.nan)
                    cis.append(0)

            ax.errorbar(energy_levels, values, yerr=cis,
                       marker=MARKERS[proto], color=COLORS[proto],
                       linestyle=LINESTYLES[proto], linewidth=1.5,
                       markersize=6, capsize=3,
                       label=proto if col_idx == 0 else None,
                       markerfacecolor='white', markeredgewidth=1.5)

        ylabel = ['PDR', 'Energy (J)', 'Lifetime'][col_idx]
        ax.set_xlabel('Initial Energy (J)')
        ax.set_ylabel(ylabel if col_idx == 0 else '')
        ax.set_title(f'Initial Energy vs {ylabel}', fontweight='bold')

    # 行2: 轮次敏感度
    round_counts = [100, 200, 300, 500]

    for col_idx, metric in enumerate(['pdr', 'energy', 'lifetime']):
        ax = axes[1, col_idx]
        for proto in protocols:
            values = []
            cis = []
            for r in round_counts:
                key = f'R{r}_{proto}'
                if key in rounds_data:
                    values.append(rounds_data[key][metric]['mean'])
                    cis.append(rounds_data[key][metric]['ci95'])
                else:
                    values.append(np.nan)
                    cis.append(0)

            ax.errorbar(round_counts, values, yerr=cis,
                       marker=MARKERS[proto], color=COLORS[proto],
                       linestyle=LINESTYLES[proto], linewidth=1.5,
                       markersize=6, capsize=3,
                       markerfacecolor='white', markeredgewidth=1.5)

        ylabel = ['PDR', 'Energy (J)', 'Lifetime'][col_idx]
        ax.set_xlabel('Simulation Rounds')
        ax.set_ylabel(ylabel if col_idx == 0 else '')
        ax.set_title(f'Rounds vs {ylabel}', fontweight='bold')

    # 行3: 统计分析 - 效应量和显著性
    # 效应量热图
    ax = axes[2, 0]
    scale_data = load_json(results_dir / 'scale_experiments.json')

    # 计算AERIS相对于其他协议的效应量
    node_counts = [50, 100, 200]
    effect_matrix = []
    for num_nodes in node_counts:
        row = []
        aeris_key = f'N{num_nodes}_AERIS'
        aeris_pdrs = scale_data[aeris_key]['pdr']['values'] if aeris_key in scale_data else [0]
        for proto in ['LEACH', 'HEED', 'PEGASIS', 'TEEN']:
            key = f'N{num_nodes}_{proto}'
            if key in scale_data:
                proto_pdrs = scale_data[key]['pdr']['values']
                # Hedges' g
                n1, n2 = len(aeris_pdrs), len(proto_pdrs)
                m1, m2 = np.mean(aeris_pdrs), np.mean(proto_pdrs)
                s1, s2 = np.var(aeris_pdrs, ddof=1), np.var(proto_pdrs, ddof=1)
                sp = np.sqrt(((n1-1)*s1 + (n2-1)*s2) / (n1+n2-2)) if n1+n2 > 2 else 1
                g = (m1 - m2) / sp if sp > 0 else 0
                row.append(g)
            else:
                row.append(0)
        effect_matrix.append(row)

    im = ax.imshow(effect_matrix, cmap='RdYlGn', aspect='auto', vmin=-2, vmax=2)
    ax.set_xticks(range(4))
    ax.set_xticklabels(['vs LEACH', 'vs HEED', 'vs PEGASIS', 'vs TEEN'], rotation=45, ha='right')
    ax.set_yticks(range(3))
    ax.set_yticklabels(['50 nodes', '100 nodes', '200 nodes'])
    ax.set_title("Effect Size (Hedges' g)", fontweight='bold')

    # 添加数值标注
    for i in range(3):
        for j in range(4):
            val = effect_matrix[i][j]
            color = 'white' if abs(val) > 1 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', color=color, fontsize=8)

    plt.colorbar(im, ax=ax, shrink=0.8)

    # PDR分布箱线图
    ax = axes[2, 1]
    box_data = []
    box_labels = []
    box_colors = []
    for proto in protocols:
        key = f'N100_{proto}'
        if key in scale_data:
            box_data.append(scale_data[key]['pdr']['values'])
            box_labels.append(proto)
            box_colors.append(COLORS[proto])

    bp = ax.boxplot(box_data, labels=box_labels, patch_artist=True)
    for patch, color in zip(bp['boxes'], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.set_ylabel('PDR')
    ax.set_title('PDR Distribution (100 nodes)', fontweight='bold')
    ax.tick_params(axis='x', rotation=45)

    # 改进百分比汇总
    ax = axes[2, 2]
    improvements = []
    labels = []
    colors = []
    for num_nodes in node_counts:
        leach_key = f'N{num_nodes}_LEACH'
        aeris_key = f'N{num_nodes}_AERIS'
        if leach_key in scale_data and aeris_key in scale_data:
            leach_pdr = scale_data[leach_key]['pdr']['mean']
            aeris_pdr = scale_data[aeris_key]['pdr']['mean']
            imp = (aeris_pdr - leach_pdr) / leach_pdr * 100
            improvements.append(imp)
            labels.append(f'{num_nodes} nodes')
            colors.append(COLORS['AERIS'])

    ax.bar(range(len(improvements)), improvements, color=colors, alpha=0.8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylabel('Improvement over LEACH (%)')
    ax.set_title('AERIS PDR Improvement', fontweight='bold')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

    # 添加图例
    fig.legend(protocols, loc='upper center', ncol=5,
              framealpha=0.9, bbox_to_anchor=(0.5, 1.02))

    fig.suptitle('Parameter Sensitivity and Statistical Analysis',
                fontsize=12, fontweight='bold', y=1.05)

    # 保存
    output_dir = Path('c:/AERIS-WSN-Protocol/results/experiments_20250102')
    for fmt in ['pdf', 'png', 'svg']:
        fig.savefig(output_dir / f'figure3_sensitivity.{fmt}',
                   format=fmt, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Saved: figure3_sensitivity.{fmt}")

    submission_dir = Path('c:/AERIS-WSN-Protocol/for_submission')
    for fmt in ['pdf', 'png']:
        fig.savefig(submission_dir / f'figure3_sensitivity.{fmt}',
                   format=fmt, dpi=300, bbox_inches='tight', facecolor='white')

    plt.close(fig)
    print("\nFigure 3 generated successfully!")

def main():
    print("=" * 60)
    print("M3: 生成专业图表")
    print("=" * 60)

    print("\n生成Figure 1: 规模对比图 (12面板)...")
    generate_figure1_scale_comparison()

    print("\n生成Figure 2: 拓扑泛化图 (6面板)...")
    generate_figure2_topology_comparison()

    print("\n生成Figure 3: 敏感度分析图 (9面板)...")
    generate_figure3_sensitivity()

    print("\n" + "=" * 60)
    print("所有图表生成完成!")
    print("=" * 60)

if __name__ == '__main__':
    main()
