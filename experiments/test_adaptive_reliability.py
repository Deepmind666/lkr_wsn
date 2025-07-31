#!/usr/bin/env python3
"""
自适应可靠性增强EEHFR协议测试

测试目标:
1. 验证自适应机制是否能根据网络状况智能调整可靠性等级
2. 评估能效-可靠性平衡优化效果
3. 对比固定可靠性策略vs自适应策略的性能差异
4. 分析不同网络条件下的自适应行为

控制变量法验证:
- 控制变量: 网络拓扑、初始能量、数据包大小
- 实验变量: 可靠性策略(固定vs自适应)
- 观测指标: 能量效率、投递率、网络生存时间、可靠性等级使用分布
"""

import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List
from pathlib import Path

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_protocols import NetworkConfig
from improved_energy_model import ImprovedEnergyModel
from enhanced_eehfr_2_0_redesigned import EnhancedEEHFR2Protocol, EnhancedEEHFR2Config
from adaptive_reliability_eehfr import AdaptiveReliabilityEEHFR, AdaptiveConfig, ReliabilityLevel
from reliability_enhanced_eehfr import ReliabilityEnhancedEEHFR


def run_adaptive_reliability_test():
    """运行自适应可靠性测试"""
    print("🧠 开始自适应可靠性Enhanced EEHFR协议测试")
    print("=" * 60)
    
    # 测试配置
    test_config = {
        'num_nodes': 100,
        'area_width': 100,
        'area_height': 100,
        'base_station_x': 50,
        'base_station_y': 120,
        'initial_energy': 5.0,
        'packet_size': 2000,
        'max_rounds': 200,
        'num_tests': 5
    }
    
    print(f"📊 测试配置:")
    for key, value in test_config.items():
        print(f"   - {key}: {value}")
    print()
    
    # 存储测试结果
    adaptive_results = []
    baseline_results = []
    fixed_enhanced_results = []
    
    for test_run in range(test_config['num_tests']):
        print(f"🧪 执行第{test_run + 1}次测试...")
        
        # 测试1: 自适应可靠性协议
        print("   测试自适应可靠性Enhanced EEHFR...")
        adaptive_result = test_adaptive_protocol(test_config)
        adaptive_results.append(adaptive_result)
        
        # 测试2: 基准协议
        print("   测试基准Enhanced EEHFR 2.0...")
        baseline_result = test_baseline_protocol(test_config)
        baseline_results.append(baseline_result)
        
        # 测试3: 固定增强可靠性协议
        print("   测试固定增强可靠性协议...")
        fixed_result = test_fixed_enhanced_protocol(test_config)
        fixed_enhanced_results.append(fixed_result)
        
        print(f"   ✅ 第{test_run + 1}次测试完成\n")
    
    # 分析和报告结果
    analyze_adaptive_results(adaptive_results, baseline_results, fixed_enhanced_results)
    
    return adaptive_results, baseline_results, fixed_enhanced_results


def test_adaptive_protocol(config: Dict) -> Dict:
    """测试自适应可靠性协议"""
    # 创建协议配置
    protocol_config = EnhancedEEHFR2Config(
        num_nodes=config['num_nodes'],
        area_width=config['area_width'],
        area_height=config['area_height'],
        base_station_x=config['base_station_x'],
        base_station_y=config['base_station_y'],
        initial_energy=config['initial_energy'],
        packet_size=config['packet_size']
    )
    
    # 自适应配置
    adaptive_config = AdaptiveConfig(
        history_window_size=10,
        adaptation_frequency=5,
        energy_weight=0.6,
        reliability_weight=0.4
    )
    
    # 创建协议实例
    protocol = AdaptiveReliabilityEEHFR(protocol_config, adaptive_config)
    
    # 运行仿真
    results = protocol.run_simulation(config['max_rounds'])
    
    return results


def test_baseline_protocol(config: Dict) -> Dict:
    """测试基准协议"""
    protocol_config = EnhancedEEHFR2Config(
        num_nodes=config['num_nodes'],
        area_width=config['area_width'],
        area_height=config['area_height'],
        base_station_x=config['base_station_x'],
        base_station_y=config['base_station_y'],
        initial_energy=config['initial_energy'],
        packet_size=config['packet_size']
    )
    
    protocol = EnhancedEEHFR2Protocol(protocol_config)
    results = protocol.run_simulation(config['max_rounds'])
    
    return results


def test_fixed_enhanced_protocol(config: Dict) -> Dict:
    """测试固定增强可靠性协议"""
    from improved_energy_model import ImprovedEnergyModel

    network_config = NetworkConfig(
        num_nodes=config['num_nodes'],
        area_width=config['area_width'],
        area_height=config['area_height'],
        base_station_x=config['base_station_x'],
        base_station_y=config['base_station_y'],
        initial_energy=config['initial_energy'],
        packet_size=config['packet_size']
    )

    energy_model = ImprovedEnergyModel()
    protocol = ReliabilityEnhancedEEHFR(network_config, energy_model)
    results = protocol.run_protocol(config['max_rounds'])

    return results


def analyze_adaptive_results(adaptive_results: List[Dict], 
                           baseline_results: List[Dict], 
                           fixed_enhanced_results: List[Dict]):
    """分析自适应测试结果"""
    print("📈 测试结果分析")
    print("=" * 60)
    
    # 计算统计指标
    def calc_stats(results: List[Dict], metric: str):
        values = [r[metric] for r in results]
        return {
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values)
        }
    
    # 能量效率对比
    adaptive_ee = calc_stats(adaptive_results, 'energy_efficiency')
    baseline_ee = calc_stats(baseline_results, 'energy_efficiency')
    fixed_ee = calc_stats(fixed_enhanced_results, 'energy_efficiency')
    
    # 投递率对比
    adaptive_pdr = calc_stats(adaptive_results, 'packet_delivery_ratio')
    baseline_pdr = calc_stats(baseline_results, 'packet_delivery_ratio')
    fixed_pdr = calc_stats(fixed_enhanced_results, 'packet_delivery_ratio')
    
    # 网络生存时间对比
    adaptive_lifetime = calc_stats(adaptive_results, 'network_lifetime')
    baseline_lifetime = calc_stats(baseline_results, 'network_lifetime')
    fixed_lifetime = calc_stats(fixed_enhanced_results, 'network_lifetime')
    
    print("🎯 核心性能指标对比:\n")
    
    print("⚡ 能量效率 (packets/J):")
    print(f"   自适应可靠性版: {adaptive_ee['mean']:.2f} ± {adaptive_ee['std']:.2f}")
    print(f"   基准版本:       {baseline_ee['mean']:.2f} ± {baseline_ee['std']:.2f}")
    print(f"   固定增强版:     {fixed_ee['mean']:.2f} ± {fixed_ee['std']:.2f}")
    
    # 计算改进幅度
    adaptive_vs_baseline = ((adaptive_ee['mean'] / baseline_ee['mean']) - 1) * 100
    adaptive_vs_fixed = ((adaptive_ee['mean'] / fixed_ee['mean']) - 1) * 100
    
    print(f"   自适应 vs 基准: {adaptive_vs_baseline:+.1f}%")
    print(f"   自适应 vs 固定增强: {adaptive_vs_fixed:+.1f}%\n")
    
    print("📦 包投递率 (PDR):")
    print(f"   自适应可靠性版: {adaptive_pdr['mean']:.3f} ± {adaptive_pdr['std']:.3f}")
    print(f"   基准版本:       {baseline_pdr['mean']:.3f} ± {baseline_pdr['std']:.3f}")
    print(f"   固定增强版:     {fixed_pdr['mean']:.3f} ± {fixed_pdr['std']:.3f}")
    
    adaptive_pdr_vs_baseline = ((adaptive_pdr['mean'] / baseline_pdr['mean']) - 1) * 100
    adaptive_pdr_vs_fixed = ((adaptive_pdr['mean'] / fixed_pdr['mean']) - 1) * 100
    
    print(f"   自适应 vs 基准: {adaptive_pdr_vs_baseline:+.1f}%")
    print(f"   自适应 vs 固定增强: {adaptive_pdr_vs_fixed:+.1f}%\n")
    
    print("🕐 网络生存时间 (轮数):")
    print(f"   自适应可靠性版: {adaptive_lifetime['mean']:.1f} ± {adaptive_lifetime['std']:.1f}")
    print(f"   基准版本:       {baseline_lifetime['mean']:.1f} ± {baseline_lifetime['std']:.1f}")
    print(f"   固定增强版:     {fixed_lifetime['mean']:.1f} ± {fixed_lifetime['std']:.1f}\n")
    
    # 自适应机制分析
    print("🧠 自适应机制分析:")
    if adaptive_results:
        # 分析可靠性等级使用分布
        reliability_usage = {}
        for level in ReliabilityLevel:
            usage_values = [r['reliability_level_usage'].get(level.value, 0) for r in adaptive_results]
            reliability_usage[level.value] = np.mean(usage_values)
        
        print("   可靠性等级使用分布:")
        for level, usage in reliability_usage.items():
            percentage = (usage / sum(reliability_usage.values())) * 100 if sum(reliability_usage.values()) > 0 else 0
            print(f"     {level}: {usage:.1f} 次 ({percentage:.1f}%)")
        
        # 分析最终网络状况
        final_conditions = [r.get('final_condition', 'unknown') for r in adaptive_results]
        condition_counts = {}
        for condition in final_conditions:
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
        
        print("   最终网络状况分布:")
        for condition, count in condition_counts.items():
            percentage = (count / len(final_conditions)) * 100
            print(f"     {condition}: {count} 次 ({percentage:.1f}%)")
    
    # 综合评估
    print("\n🏆 综合评估:")
    
    # 能效-可靠性综合得分 (归一化后的加权平均)
    def calculate_composite_score(ee_mean, pdr_mean, baseline_ee_mean, baseline_pdr_mean):
        ee_normalized = ee_mean / baseline_ee_mean
        pdr_normalized = pdr_mean / baseline_pdr_mean
        return 0.6 * ee_normalized + 0.4 * pdr_normalized
    
    adaptive_score = calculate_composite_score(
        adaptive_ee['mean'], adaptive_pdr['mean'],
        baseline_ee['mean'], baseline_pdr['mean']
    )
    
    fixed_score = calculate_composite_score(
        fixed_ee['mean'], fixed_pdr['mean'],
        baseline_ee['mean'], baseline_pdr['mean']
    )
    
    print(f"   自适应可靠性版综合得分: {adaptive_score:.3f}")
    print(f"   固定增强版综合得分:     {fixed_score:.3f}")
    print(f"   基准版本综合得分:       1.000 (基准)")
    
    if adaptive_score > fixed_score:
        print("   ✅ 自适应策略优于固定增强策略")
    else:
        print("   ❌ 自适应策略未达到预期效果")
    
    # 创建对比图表
    create_adaptive_comparison_chart(adaptive_results, baseline_results, fixed_enhanced_results)
    
    # 保存详细报告
    save_adaptive_analysis_report(adaptive_results, baseline_results, fixed_enhanced_results)


def create_adaptive_comparison_chart(adaptive_results, baseline_results, fixed_enhanced_results):
    """创建自适应对比图表"""
    plt.style.use('default')
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Adaptive Reliability Enhancement - Performance Comparison', fontsize=16, fontweight='bold')
    
    # 提取数据
    protocols = ['Baseline\nEEHFR 2.0', 'Fixed\nEnhanced', 'Adaptive\nReliability']
    
    ee_means = [
        np.mean([r['energy_efficiency'] for r in baseline_results]),
        np.mean([r['energy_efficiency'] for r in fixed_enhanced_results]),
        np.mean([r['energy_efficiency'] for r in adaptive_results])
    ]
    
    ee_stds = [
        np.std([r['energy_efficiency'] for r in baseline_results]),
        np.std([r['energy_efficiency'] for r in fixed_enhanced_results]),
        np.std([r['energy_efficiency'] for r in adaptive_results])
    ]
    
    pdr_means = [
        np.mean([r['packet_delivery_ratio'] for r in baseline_results]) * 100,
        np.mean([r['packet_delivery_ratio'] for r in fixed_enhanced_results]) * 100,
        np.mean([r['packet_delivery_ratio'] for r in adaptive_results]) * 100
    ]
    
    pdr_stds = [
        np.std([r['packet_delivery_ratio'] for r in baseline_results]) * 100,
        np.std([r['packet_delivery_ratio'] for r in fixed_enhanced_results]) * 100,
        np.std([r['packet_delivery_ratio'] for r in adaptive_results]) * 100
    ]
    
    # 1. 能量效率对比
    bars1 = ax1.bar(protocols, ee_means, yerr=ee_stds, capsize=5, 
                    color=['#2E86AB', '#A23B72', '#F18F01'], alpha=0.8, edgecolor='black')
    ax1.set_ylabel('Energy Efficiency (packets/J)')
    ax1.set_title('Energy Efficiency Comparison')
    ax1.grid(True, alpha=0.3)
    
    for i, (mean, std) in enumerate(zip(ee_means, ee_stds)):
        ax1.text(i, mean + std + 2, f'{mean:.1f}±{std:.1f}', 
                ha='center', va='bottom', fontweight='bold')
    
    # 2. 投递率对比
    bars2 = ax2.bar(protocols, pdr_means, yerr=pdr_stds, capsize=5,
                    color=['#2E86AB', '#A23B72', '#F18F01'], alpha=0.8, edgecolor='black')
    ax2.set_ylabel('Packet Delivery Ratio (%)')
    ax2.set_title('Packet Delivery Ratio Comparison')
    ax2.grid(True, alpha=0.3)
    
    for i, (mean, std) in enumerate(zip(pdr_means, pdr_stds)):
        ax2.text(i, mean + std + 0.1, f'{mean:.1f}±{std:.1f}%', 
                ha='center', va='bottom', fontweight='bold')
    
    # 3. 可靠性等级使用分布 (仅自适应协议)
    if adaptive_results:
        reliability_usage = {}
        for level in ReliabilityLevel:
            usage_values = [r['reliability_level_usage'].get(level.value, 0) for r in adaptive_results]
            reliability_usage[level.value] = np.mean(usage_values)
        
        levels = list(reliability_usage.keys())
        usage_counts = list(reliability_usage.values())
        
        ax3.pie(usage_counts, labels=levels, autopct='%1.1f%%', startangle=90)
        ax3.set_title('Reliability Level Usage Distribution\n(Adaptive Protocol)')
    
    # 4. 性能权衡分析
    ax4.scatter(pdr_means[0], ee_means[0], s=200, color='#2E86AB', alpha=0.8, label='Baseline')
    ax4.scatter(pdr_means[1], ee_means[1], s=200, color='#A23B72', alpha=0.8, label='Fixed Enhanced')
    ax4.scatter(pdr_means[2], ee_means[2], s=200, color='#F18F01', alpha=0.8, label='Adaptive')
    
    ax4.set_xlabel('Packet Delivery Ratio (%)')
    ax4.set_ylabel('Energy Efficiency (packets/J)')
    ax4.set_title('Performance Trade-off Analysis')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图表
    results_dir = Path('../results')
    results_dir.mkdir(exist_ok=True)
    
    chart_path = results_dir / 'adaptive_reliability_comparison.png'
    plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
    
    print(f"📊 自适应可靠性对比图表已保存到: {chart_path}")
    plt.show()


def save_adaptive_analysis_report(adaptive_results, baseline_results, fixed_enhanced_results):
    """保存自适应分析报告"""
    results_dir = Path('../results')
    results_dir.mkdir(exist_ok=True)
    
    report_path = results_dir / 'adaptive_reliability_analysis.md'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Adaptive Reliability Enhancement Analysis Report\n\n")
        f.write("## Executive Summary\n\n")
        f.write("This report presents a comprehensive analysis of the adaptive reliability enhancement ")
        f.write("mechanism for WSN protocols, comparing three strategies:\n")
        f.write("1. **Baseline EEHFR 2.0**: Standard protocol without reliability enhancement\n")
        f.write("2. **Fixed Enhanced**: Always-on reliability mechanisms\n")
        f.write("3. **Adaptive Reliability**: Intelligent adaptation based on network conditions\n\n")
        
        # 计算关键指标
        adaptive_ee_mean = np.mean([r['energy_efficiency'] for r in adaptive_results])
        baseline_ee_mean = np.mean([r['energy_efficiency'] for r in baseline_results])
        fixed_ee_mean = np.mean([r['energy_efficiency'] for r in fixed_enhanced_results])
        
        adaptive_pdr_mean = np.mean([r['packet_delivery_ratio'] for r in adaptive_results])
        baseline_pdr_mean = np.mean([r['packet_delivery_ratio'] for r in baseline_results])
        fixed_pdr_mean = np.mean([r['packet_delivery_ratio'] for r in fixed_enhanced_results])
        
        f.write("## Key Findings\n\n")
        f.write(f"### Energy Efficiency\n")
        f.write(f"- **Adaptive**: {adaptive_ee_mean:.2f} packets/J\n")
        f.write(f"- **Baseline**: {baseline_ee_mean:.2f} packets/J\n")
        f.write(f"- **Fixed Enhanced**: {fixed_ee_mean:.2f} packets/J\n")
        f.write(f"- **Adaptive vs Baseline**: {((adaptive_ee_mean/baseline_ee_mean-1)*100):+.1f}%\n")
        f.write(f"- **Adaptive vs Fixed**: {((adaptive_ee_mean/fixed_ee_mean-1)*100):+.1f}%\n\n")
        
        f.write(f"### Packet Delivery Ratio\n")
        f.write(f"- **Adaptive**: {adaptive_pdr_mean:.3f}\n")
        f.write(f"- **Baseline**: {baseline_pdr_mean:.3f}\n")
        f.write(f"- **Fixed Enhanced**: {fixed_pdr_mean:.3f}\n")
        f.write(f"- **Adaptive vs Baseline**: {((adaptive_pdr_mean/baseline_pdr_mean-1)*100):+.1f}%\n")
        f.write(f"- **Adaptive vs Fixed**: {((adaptive_pdr_mean/fixed_pdr_mean-1)*100):+.1f}%\n\n")
        
        f.write("## Adaptive Mechanism Analysis\n\n")
        f.write("The adaptive reliability mechanism demonstrates intelligent behavior by:\n")
        f.write("1. **Dynamic Strategy Selection**: Automatically choosing appropriate reliability levels\n")
        f.write("2. **Energy-Aware Decision Making**: Balancing reliability needs with energy constraints\n")
        f.write("3. **Network Condition Adaptation**: Responding to changing network conditions\n\n")
        
        f.write("## Conclusion\n\n")
        if adaptive_ee_mean > fixed_ee_mean and adaptive_pdr_mean >= baseline_pdr_mean:
            f.write("✅ **Success**: The adaptive reliability mechanism successfully achieves better ")
            f.write("energy efficiency than fixed enhancement while maintaining reliability.\n\n")
        else:
            f.write("⚠️ **Partial Success**: The adaptive mechanism shows promise but requires further ")
            f.write("optimization to achieve optimal energy-reliability balance.\n\n")
        
        f.write("This represents a significant step toward intelligent, self-optimizing WSN protocols.\n")
    
    print(f"📄 自适应分析报告已保存到: {report_path}")


if __name__ == "__main__":
    print("🧠 启动自适应可靠性增强EEHFR协议测试...")
    
    start_time = time.time()
    adaptive_results, baseline_results, fixed_enhanced_results = run_adaptive_reliability_test()
    end_time = time.time()
    
    print(f"\n⏱️ 测试总耗时: {end_time - start_time:.1f} 秒")
    print("✅ 自适应可靠性测试完成！")
