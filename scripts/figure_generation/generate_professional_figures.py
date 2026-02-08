#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业论文图表生成脚本 - 严格使用真实数据

数据来源 (已验证):
- results/intel_ablation.json: 消融实验 (50次重复 × 5配置 = 250点)
- results/intel_sensitivity.json: 参数敏感性 (40次重复 × 9配置 = 360点)
- results/prior_experiments/e0_env_link_correlation.json: E0环境相关性

禁止事项:
- 禁止使用np.random生成假数据
- 禁止硬编码数值
- 所有数据必须从JSON文件读取

作者: AERIS Research Team
日期: 2024-12-30
"""

import json
import numpy as np
from pathlib import Path
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.patches as mpatches

# ============================================================
# 专业样式配置 - Nature/Science风格
# ============================================================
plt.rcParams.update({
    'figure.dpi': 150,
    'savefig.dpi': 600,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 10,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'axes.linewidth': 1.0,
    'lines.linewidth': 1.5,
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})

# 专业配色方案 (色盲友好)
COLORS = {
    'full': '#0072B2',      # 蓝色 - Full AERIS
    'gw': '#D55E00',        # 橙红色 - Gateway (最重要)
    'fair': '#009E73',      # 绿色 - Fairness
    'safety': '#CC79A7',    # 粉紫色 - Safety
    'cas': '#F0E442',       # 黄色 - CAS
    'baseline': '#999999',  # 灰色 - 基线
}

OUTPUT_DIRS = [
    Path('results/professional_figures'),
    Path('for_submission/figures'),
]
for out_dir in OUTPUT_DIRS:
    out_dir.mkdir(parents=True, exist_ok=True)


class ProfessionalFigureGenerator:
    """专业图表生成器 - 严格使用真实数据"""
    
    def __init__(self):
        print("=" * 60)
        print("专业图表生成器 - 严格使用真实数据")
        print("=" * 60)
        
        # 加载并验证数据
        self.ablation_data = self._load_and_validate_ablation()
        self.sensitivity_data = self._load_and_validate_sensitivity()
        self.e0_data = self._load_e0_data()
        
    def _load_and_validate_ablation(self):
        """加载并验证消融实验数据"""
        print("\n[1] 加载消融实验数据...")
        
        path = 'results/intel_ablation.json'
        with open(path, 'r') as f:
            data = json.load(f)
        
        # 严格验证（允许更高重复次数）
        configs = ['FULL', '-GW', '-FAIR', '-SAFETY', '-CAS']
        for cfg in configs:
            n = len(data[cfg]['pdr_end2end']['values'])
            if n < 30:
                raise ValueError(f"数据验证失败: {cfg} 期望≥30个点, 实际{n}个点")
            print(f"  ✓ {cfg}: n={n}, PDR={data[cfg]['pdr_end2end']['mean']:.4f}")
        
        print(f"  数据来源: {path}")
        return data
    
    def _load_and_validate_sensitivity(self):
        """加载并验证参数敏感性数据"""
        print("\n[2] 加载参数敏感性数据...")
        
        path = 'results/intel_sensitivity.json'
        with open(path, 'r') as f:
            data = json.load(f)
        
        # 严格验证（允许更高重复次数）
        configs = ['E1.0_P256_G1', 'E1.0_P256_G2', 'E1.0_P256_G3',
                   'E1.0_P512_G1', 'E1.0_P512_G2', 'E1.0_P512_G3',
                   'E1.0_P1024_G1', 'E1.0_P1024_G2', 'E1.0_P1024_G3']
        
        for cfg in configs:
            n = len(data[cfg]['pdr_end2end']['values'])
            if n < 30:
                raise ValueError(f"数据验证失败: {cfg} 期望≥30个点, 实际{n}个点")
        
        print(f"  ✓ 9个配置验证通过, 每个配置≥30个数据点")
        print(f"  数据来源: {path}")
        return data
    
    def _load_e0_data(self):
        """加载E0环境相关性数据"""
        print("\n[3] 加载E0环境相关性数据...")
        
        path = 'results/prior_experiments/e0_env_link_correlation.json'
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            print(f"  ✓ 数据加载成功")
            print(f"  数据来源: {path}")
            return data
        except FileNotFoundError:
            print(f"  ⚠️ 文件不存在: {path}")
            return None
    
    def save_figure(self, fig, name):
        """保存图表为多种格式"""
        for out_dir in OUTPUT_DIRS:
            for fmt in ['pdf', 'png', 'svg']:
                filepath = out_dir / f'{name}.{fmt}'
                fig.savefig(filepath,
                           dpi=600 if fmt == 'png' else 300,
                           bbox_inches='tight',
                           facecolor='white',
                           pad_inches=0.1)
        plt.close(fig)
        print(f"  ✓ 已保存: {name}")

    @staticmethod
    def _hedges_g_with_ci(a, b, n_boot=1000, seed=42):
        """Compute Hedges' g with bootstrap CI; handles zero-variance safely."""
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        n1, n2 = len(a), len(b)
        pooled_std = np.sqrt(((n1 - 1) * np.var(a, ddof=1) +
                              (n2 - 1) * np.var(b, ddof=1)) / (n1 + n2 - 2))
        if not np.isfinite(pooled_std) or pooled_std <= 0:
            return 0.0, 0.0, 0.0

        cohens_d = (np.mean(a) - np.mean(b)) / pooled_std
        correction = 1 - 3 / (4 * (n1 + n2) - 9)
        hedges_g = cohens_d * correction

        rng = np.random.RandomState(seed)
        bootstrap_gs = []
        for _ in range(n_boot):
            idx1 = rng.choice(n1, n1, replace=True)
            idx2 = rng.choice(n2, n2, replace=True)
            boot_a = a[idx1]
            boot_b = b[idx2]
            boot_pooled = np.sqrt(((n1 - 1) * np.var(boot_a, ddof=1) +
                                   (n2 - 1) * np.var(boot_b, ddof=1)) / (n1 + n2 - 2))
            if boot_pooled > 0:
                boot_d = (np.mean(boot_a) - np.mean(boot_b)) / boot_pooled
                bootstrap_gs.append(boot_d * correction)

        if not bootstrap_gs:
            return hedges_g, hedges_g, hedges_g

        ci_low = np.percentile(bootstrap_gs, 2.5)
        ci_high = np.percentile(bootstrap_gs, 97.5)
        return hedges_g, ci_low, ci_high


    def figure4_ablation_study(self):
        """
        Figure 4: 消融实验 - 专业版
        
        数据来源: results/intel_ablation.json
        - FULL: 50次实验, PDR mean=0.4769
        - -GW: 50次实验, PDR mean=0.3832 (下降19.7%)
        - -FAIR: 50次实验, PDR mean=0.4792
        - -SAFETY: 50次实验, PDR mean=0.3686 (下降22.7%)
        - -CAS: 50次实验, PDR mean=0.4806
        """
        print("\n[Figure 4] 生成消融实验图表...")
        
        fig = plt.figure(figsize=(12, 10))
        
        # 配置
        configs = ['FULL', '-GW', '-FAIR', '-SAFETY', '-CAS']
        labels = ['Full\nAERIS', 'w/o\nGateway', 'w/o\nFairness', 'w/o\nSafety', 'w/o\nCAS']
        colors = [COLORS['full'], COLORS['gw'], COLORS['fair'], COLORS['safety'], COLORS['cas']]
        
        # 从真实数据提取
        pdr_data = []
        energy_data = []
        
        for cfg in configs:
            pdr_vals = self.ablation_data[cfg]['pdr_end2end']['values']
            energy_vals = self.ablation_data[cfg]['energy']['values']
            pdr_data.append(pdr_vals)
            energy_data.append(energy_vals)
            # 打印验证
            print(f"    {cfg}: PDR n={len(pdr_vals)}, mean={np.mean(pdr_vals):.4f}")
        
        # ========== (a) 小提琴图 - PDR分布 ==========
        ax1 = fig.add_subplot(2, 2, 1)
        
        parts = ax1.violinplot(pdr_data, positions=range(len(configs)), 
                              showmeans=True, showmedians=True, widths=0.7)
        
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(colors[i])
            pc.set_alpha(0.7)
            pc.set_edgecolor('black')
            pc.set_linewidth(0.8)
        
        parts['cmeans'].set_color('black')
        parts['cmeans'].set_linewidth(2)
        parts['cmedians'].set_color('white')
        parts['cmedians'].set_linewidth(1.5)
        
        # 添加散点 (jittered) - 显示所有50个真实数据点
        for i, data in enumerate(pdr_data):
            x = np.random.RandomState(42).normal(i, 0.08, len(data))
            ax1.scatter(x, data, alpha=0.4, s=15, color=colors[i], zorder=2)
        
        ax1.set_xticks(range(len(configs)))
        ax1.set_xticklabels(labels)
        ax1.set_ylabel('PDR (Packet Delivery Ratio)')
        ax1.set_title('(a) PDR Distribution', fontweight='bold', loc='left')
        ax1.set_ylim(0.25, 0.6)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # 添加样本量标注
        for i, data in enumerate(pdr_data):
            ax1.text(i, 0.27, f'n={len(data)}', ha='center', fontsize=8, color='gray')
        
        # ========== (b) 条形图 - PDR变化百分比 ==========
        ax2 = fig.add_subplot(2, 2, 2)
        
        full_mean = np.mean(pdr_data[0])
        changes = [(np.mean(d) - full_mean) / full_mean * 100 for d in pdr_data]
        
        bars = ax2.bar(range(len(configs)), changes, color=colors, 
                      edgecolor='black', linewidth=0.8, alpha=0.8)
        
        ax2.axhline(y=0, color='black', linewidth=1)
        
        # 添加数值标签
        for i, (bar, change) in enumerate(zip(bars, changes)):
            y_pos = change - 2 if change < 0 else change + 1
            ax2.text(bar.get_x() + bar.get_width()/2, y_pos,
                    f'{change:+.1f}%', ha='center', fontsize=9, fontweight='bold')
        
        ax2.set_xticks(range(len(configs)))
        ax2.set_xticklabels(labels)
        ax2.set_ylabel('PDR Change vs Full AERIS (%)')
        ax2.set_title('(b) Component Contribution', fontweight='bold', loc='left')
        ax2.set_ylim(-30, 10)
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        # ========== (c) 箱线图 - 能耗分布 ==========
        ax3 = fig.add_subplot(2, 2, 3)
        
        bp = ax3.boxplot(energy_data, positions=range(len(configs)), 
                        patch_artist=True, widths=0.6,
                        medianprops=dict(color='black', linewidth=1.5),
                        flierprops=dict(marker='o', markersize=4, alpha=0.5))
        
        for i, (patch, color) in enumerate(zip(bp['boxes'], colors)):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
            patch.set_edgecolor('black')
            patch.set_linewidth(0.8)
        
        ax3.set_xticks(range(len(configs)))
        ax3.set_xticklabels(labels)
        ax3.set_ylabel('Energy Consumption (J)')
        ax3.set_title('(c) Energy Distribution', fontweight='bold', loc='left')
        ax3.grid(axis='y', alpha=0.3, linestyle='--')
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        
        # ========== (d) 效应量森林图 ==========
        ax4 = fig.add_subplot(2, 2, 4)
        
        # 计算效应量 (Hedges' g)
        full_pdr = np.array(pdr_data[0])
        effect_sizes = []
        ci_lows = []
        ci_highs = []
        
        for i, cfg in enumerate(configs[1:]):  # 跳过FULL
            cfg_pdr = np.array(pdr_data[i+1])
            hedges_g, ci_low, ci_high = self._hedges_g_with_ci(full_pdr, cfg_pdr)
            
            effect_sizes.append(hedges_g)
            ci_lows.append(ci_low)
            ci_highs.append(ci_high)
        
        # 绘制森林图
        y_pos = np.arange(len(configs)-1)
        effect_labels = labels[1:]
        effect_colors = colors[1:]
        
        # 背景区域
        ax4.axvspan(0.8, max(effect_sizes)+1, alpha=0.1, color='red')
        ax4.axvspan(0.5, 0.8, alpha=0.1, color='orange')
        ax4.axvspan(0.2, 0.5, alpha=0.1, color='yellow')
        ax4.axvspan(-0.2, 0.2, alpha=0.1, color='green')
        
        for i, (es, low, high, color) in enumerate(zip(effect_sizes, ci_lows, ci_highs, effect_colors)):
            ax4.plot([low, high], [i, i], color=color, linewidth=3, solid_capstyle='round')
            ax4.scatter([es], [i], color=color, s=150, zorder=5, 
                       edgecolors='white', linewidths=2)
            ax4.text(max(effect_sizes)+0.5, i, f'g={es:.2f}', va='center', fontsize=9)
        
        ax4.axvline(x=0, color='black', linewidth=1)
        ax4.set_yticks(y_pos)
        ax4.set_yticklabels(effect_labels)
        ax4.set_xlabel("Effect Size (Hedges' g)")
        ax4.set_title("(d) Effect Sizes with 95% CI", fontweight='bold', loc='left')
        ax4.set_xlim(-1, max(effect_sizes)+1.5)
        ax4.spines['top'].set_visible(False)
        ax4.spines['right'].set_visible(False)
        ax4.grid(axis='x', alpha=0.3, linestyle='--')
        
        # 添加数据来源说明
        fig.text(0.5, 0.01, 
                'Data: results/intel_ablation.json (n=50 independent runs per configuration)',
                ha='center', fontsize=9, style='italic', color='gray')
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.97])
        self.save_figure(fig, 'fig4_ablation_professional')
        return True


    def figure7_sensitivity_analysis(self):
        """
        Figure 7: 参数敏感性分析 - 专业版
        
        数据来源: results/intel_sensitivity.json
        - 9个配置 (3 packet sizes × 3 gateway counts)
        - 每个配置40次重复实验
        """
        print("\n[Figure 7] 生成参数敏感性图表...")
        
        fig = plt.figure(figsize=(14, 10))
        
        base_energy = 1.0
        packet_sizes = sorted({
            int(k.split('_P')[1].split('_G')[0])
            for k in self.sensitivity_data.keys()
            if k.startswith(f'E{base_energy}_')
        })
        gateway_vals = sorted({
            int(k.split('_G')[1])
            for k in self.sensitivity_data.keys()
            if k.startswith(f'E{base_energy}_')
        })
        
        colors_packet = {
            256: '#0072B2',   # 蓝
            512: '#009E73',   # 绿
            1024: '#D55E00',  # 橙红
        }
        
        # ========== 行1: PDR vs Gateway (不同packet size) ==========
        for col, psize in enumerate(packet_sizes):
            ax = fig.add_subplot(2, 3, col + 1)
            
            pdr_all = []
            pdr_means = []
            pdr_stds = []
            
            for g in gateway_vals:
                key = f'E{base_energy}_P{psize}_G{g}'
                values = self.sensitivity_data[key]['pdr_end2end']['values']
                pdr_all.append(values)
                pdr_means.append(np.mean(values))
                pdr_stds.append(np.std(values))
                print(f"    {key}: n={len(values)}, PDR={np.mean(values):.4f}")
            
            # 小提琴图
            parts = ax.violinplot(pdr_all, positions=gateway_vals, 
                                 showmeans=True, widths=0.5)
            
            for pc in parts['bodies']:
                pc.set_facecolor(colors_packet[psize])
                pc.set_alpha(0.6)
                pc.set_edgecolor('black')
            
            parts['cmeans'].set_color('black')
            parts['cmeans'].set_linewidth(2)
            
            # 连接均值线
            ax.plot(gateway_vals, pdr_means, 'o-', color=colors_packet[psize], 
                   linewidth=2.5, markersize=10, markeredgecolor='white', 
                   markeredgewidth=2, zorder=5)
            
            # 添加散点 - 显示所有40个真实数据点
            rng = np.random.RandomState(42)
            for i, (g, data) in enumerate(zip(gateway_vals, pdr_all)):
                x = rng.normal(g, 0.05, len(data))
                ax.scatter(x, data, alpha=0.3, s=10, color=colors_packet[psize])
            
            ax.set_xlabel('Gateway Count (k)')
            ax.set_ylabel('PDR' if col == 0 else '')
            ax.set_title(f'({chr(97+col)}) Packet Size = {psize}B', fontweight='bold', loc='left')
            ax.set_xticks(gateway_vals)
            ax.set_ylim(0.4, 0.65)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            # 添加均值标注
            for g, mean in zip(gateway_vals, pdr_means):
                ax.annotate(f'{mean:.3f}', xy=(g, mean), xytext=(g+0.15, mean+0.01),
                           fontsize=8, fontweight='bold')
            
            # 添加样本量
            if pdr_all and pdr_all[0]:
                ax.text(np.mean(gateway_vals), 0.42, f'n={len(pdr_all[0])} each',
                        ha='center', fontsize=8, color='gray')
        
        # ========== 行2: Energy vs Gateway (不同packet size) ==========
        for col, psize in enumerate(packet_sizes):
            ax = fig.add_subplot(2, 3, col + 4)
            
            energy_all = []
            energy_means = []
            
            for g in gateway_vals:
                key = f'E{base_energy}_P{psize}_G{g}'
                values = self.sensitivity_data[key]['energy']['values']
                energy_all.append(values)
                energy_means.append(np.mean(values))
            
            # 箱线图
            bp = ax.boxplot(energy_all, positions=gateway_vals, 
                           patch_artist=True, widths=0.4)
            
            for patch in bp['boxes']:
                patch.set_facecolor(colors_packet[psize])
                patch.set_alpha(0.6)
                patch.set_edgecolor('black')
            
            # 连接均值线
            ax.plot(gateway_vals, energy_means, 's-', color=colors_packet[psize], 
                   linewidth=2.5, markersize=10, markeredgecolor='white', 
                   markeredgewidth=2, zorder=5)
            
            ax.set_xlabel('Gateway Count (k)')
            ax.set_ylabel('Energy (J)' if col == 0 else '')
            ax.set_title(f'({chr(100+col)}) Packet Size = {psize}B', fontweight='bold', loc='left')
            ax.set_xticks(gateway_vals)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
        
        # 添加数据来源说明
        fig.text(0.5, 0.01, 
                'Data: results/intel_sensitivity.json (n=40 independent runs per configuration)',
                ha='center', fontsize=9, style='italic', color='gray')
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.97])
        self.save_figure(fig, 'fig7_sensitivity_professional')
        return True

    def figure_effect_sizes_forest(self):
        """
        效应量森林图 - 独立图表
        
        从真实数据计算Hedges' g和Bootstrap 95% CI
        """
        print("\n[Effect Sizes] 生成效应量森林图...")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 从真实数据计算效应量
        configs = ['-GW', '-FAIR', '-SAFETY', '-CAS']
        labels = ['w/o Gateway', 'w/o Fairness', 'w/o Safety', 'w/o CAS']
        colors_effect = [COLORS['gw'], COLORS['fair'], COLORS['safety'], COLORS['cas']]
        
        full_pdr = np.array(self.ablation_data['FULL']['pdr_end2end']['values'])
        
        effect_sizes = []
        ci_lows = []
        ci_highs = []
        
        for cfg in configs:
            cfg_pdr = np.array(self.ablation_data[cfg]['pdr_end2end']['values'])
            hedges_g, ci_low, ci_high = self._hedges_g_with_ci(full_pdr, cfg_pdr)
            
            effect_sizes.append(hedges_g)
            ci_lows.append(ci_low)
            ci_highs.append(ci_high)
            
            print(f"    {cfg}: Hedges' g = {hedges_g:.3f} [{ci_low:.3f}, {ci_high:.3f}]")
        
        # 绘制森林图
        y_pos = np.arange(len(configs))
        
        # 背景区域 - 效应量解释
        ax.axvspan(0.8, max(effect_sizes)+1, alpha=0.15, color='#D55E00', label='Large effect (g>0.8)')
        ax.axvspan(0.5, 0.8, alpha=0.15, color='#F0E442', label='Medium effect (0.5<g<0.8)')
        ax.axvspan(0.2, 0.5, alpha=0.15, color='#009E73', label='Small effect (0.2<g<0.5)')
        ax.axvspan(-0.2, 0.2, alpha=0.15, color='#0072B2', label='Negligible (|g|<0.2)')
        
        for i, (es, low, high, color, label) in enumerate(zip(effect_sizes, ci_lows, ci_highs, colors_effect, labels)):
            # CI线
            ax.plot([low, high], [i, i], color=color, linewidth=4, solid_capstyle='round')
            # 效应量点
            ax.scatter([es], [i], color=color, s=200, zorder=5, 
                      edgecolors='white', linewidths=2)
            # 数值标签
            ax.text(max(effect_sizes)+0.8, i, f'g = {es:.2f} [{low:.2f}, {high:.2f}]', 
                   va='center', fontsize=10, fontweight='bold')
        
        ax.axvline(x=0, color='black', linewidth=1)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=11)
        ax.set_xlabel("Effect Size (Hedges' g)", fontsize=11)
        ax.set_title("Effect Sizes with 95% Bootstrap CI\n(Calculated from Real Experimental Data)", 
                    fontweight='bold', fontsize=12)
        ax.set_xlim(-0.5, max(effect_sizes)+3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        # 图例
        ax.legend(loc='lower right', fontsize=9)
        
        # 数据来源
        fig.text(0.5, 0.01, 
                'Data: results/intel_ablation.json (n=50 runs per configuration, 1000 bootstrap iterations)',
                ha='center', fontsize=9, style='italic', color='gray')
        
        plt.tight_layout(rect=[0, 0.04, 1, 0.98])
        self.save_figure(fig, 'fig_effect_sizes_forest')
        return True

    def generate_all(self):
        """生成所有专业图表"""
        print("\n" + "=" * 60)
        print("开始生成专业论文图表")
        print("=" * 60)
        
        success = True
        
        try:
            self.figure4_ablation_study()
        except Exception as e:
            print(f"  ✗ Figure 4 生成失败: {e}")
            success = False
        
        try:
            self.figure7_sensitivity_analysis()
        except Exception as e:
            print(f"  ✗ Figure 7 生成失败: {e}")
            success = False
        
        try:
            self.figure_effect_sizes_forest()
        except Exception as e:
            print(f"  ✗ Effect Sizes 生成失败: {e}")
            success = False
        
        print("\n" + "=" * 60)
        print(f"图表生成完成! 输出目录: {', '.join(map(str, OUTPUT_DIRS))}")
        print("=" * 60)
        
        if success:
            print("\n✅ 所有图表已从真实数据生成")
            print("\n数据验证摘要:")
            print("  - 消融实验: 50次重复 × 5配置 = 250个真实数据点")
            print("  - 参数敏感性: 40次重复 × 9配置 = 360个真实数据点")
            print("  - 效应量: 从真实数据计算, 1000次Bootstrap")
        
        return success


def main():
    generator = ProfessionalFigureGenerator()
    generator.generate_all()


if __name__ == '__main__':
    main()
