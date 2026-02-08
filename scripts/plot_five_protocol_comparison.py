#!/usr/bin/env python3
"""生成5协议对比图表"""
import matplotlib.pyplot as plt
import numpy as np
import json
import os

# 设置中文字体
plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

def load_results():
    """加载结果数据"""
    with open('results/five_protocol_comparison.json', 'r') as f:
        return json.load(f)

def plot_pdr_comparison(data):
    """绘制PDR对比图"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    protocols = ['AERIS', 'PEGASIS', 'HEED', 'LEACH', 'TEEN']
    colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c', '#f39c12']

    # 标准场景
    ax1 = axes[0]
    std_results = data['standard_scenario']['results']
    pdr_std = [std_results[p]['pdr'] * 100 for p in protocols]

    bars1 = ax1.bar(protocols, pdr_std, color=colors, edgecolor='black', linewidth=1.2)
    ax1.set_ylabel('PDR (%)', fontsize=12)
    ax1.set_title('Standard Scenario (100 nodes)', fontsize=13)
    ax1.set_ylim(0, 105)
    ax1.axhline(y=90, color='gray', linestyle='--', alpha=0.5)

    for bar, val in zip(bars1, pdr_std):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10)

    # 高掉线场景
    ax2 = axes[1]
    dropout_results = data['high_dropout_scenario']['results']
    pdr_dropout = [dropout_results[p]['pdr_mean'] * 100 for p in protocols]
    pdr_err = [dropout_results[p]['pdr_std'] * 100 for p in protocols]

    bars2 = ax2.bar(protocols, pdr_dropout, yerr=pdr_err, color=colors,
                   edgecolor='black', linewidth=1.2, capsize=4)
    ax2.set_ylabel('PDR (%)', fontsize=12)
    ax2.set_title('High Dropout Scenario (Dynamic)', fontsize=13)
    ax2.set_ylim(0, 105)
    ax2.axhline(y=90, color='gray', linestyle='--', alpha=0.5)

    for bar, val in zip(bars2, pdr_dropout):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    return fig

def plot_energy_comparison(data):
    """绘制能耗对比图"""
    fig, ax = plt.subplots(figsize=(8, 5))

    protocols = ['AERIS', 'PEGASIS', 'HEED', 'LEACH', 'TEEN']
    colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c', '#f39c12']

    std_results = data['standard_scenario']['results']
    energy = [std_results[p]['energy'] for p in protocols]

    bars = ax.bar(protocols, energy, color=colors, edgecolor='black', linewidth=1.2)
    ax.set_ylabel('Energy Consumption (J)', fontsize=12)
    ax.set_title('Energy Consumption Comparison', fontsize=13)

    for bar, val in zip(bars, energy):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{val:.1f}J', ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.join(script_dir, '..'))

    print("Loading results...")
    data = load_results()

    print("Generating PDR comparison chart...")
    fig1 = plot_pdr_comparison(data)
    fig1.savefig('results/plots/five_protocol_pdr_comparison.pdf', dpi=300)
    fig1.savefig('results/plots/five_protocol_pdr_comparison.png', dpi=300)
    print("Saved: five_protocol_pdr_comparison.pdf/png")

    print("Generating energy comparison chart...")
    fig2 = plot_energy_comparison(data)
    fig2.savefig('results/plots/five_protocol_energy_comparison.pdf', dpi=300)
    fig2.savefig('results/plots/five_protocol_energy_comparison.png', dpi=300)
    print("Saved: five_protocol_energy_comparison.pdf/png")

    print("\nAll charts generated successfully!")
