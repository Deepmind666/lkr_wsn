#!/usr/bin/env python3
"""
可靠性增强Enhanced EEHFR协议测试脚本

测试目标:
1. 验证投递率从94.1%提升到97-98%
2. 评估能效损失控制在2%以内
3. 对比不同传输模式的性能
4. 分析可靠性增强机制的有效性
"""

import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_protocols import NetworkConfig
from improved_energy_model import ImprovedEnergyModel
from reliability_enhanced_eehfr import ReliabilityEnhancedEEHFR
from enhanced_eehfr_2_0_redesigned import EnhancedEEHFR2Protocol, EnhancedEEHFR2Config


def run_reliability_test():
    """运行可靠性增强测试"""
    print("🔬 开始可靠性增强Enhanced EEHFR协议测试")
    print("=" * 60)
    
    # 优化配置参数 - 解决网络生存时间过短问题
    config = NetworkConfig(
        num_nodes=100,
        area_width=100,
        area_height=100,
        base_station_x=50,
        base_station_y=120,  # 从175减少到120，减少传输距离
        initial_energy=5.0,  # 从2.0增加到5.0，延长网络生存时间
        packet_size=2000     # 从4000减少到2000，降低能耗
    )
    
    energy_model = ImprovedEnergyModel()
    
    # 测试次数
    num_tests = 5
    
    print(f"📊 测试配置:")
    print(f"   - 网络规模: {config.num_nodes}节点")
    print(f"   - 区域大小: {config.area_width}×{config.area_height}m²")
    print(f"   - 基站位置: ({config.base_station_x}, {config.base_station_y})")
    print(f"   - 初始能量: {config.initial_energy}J")
    print(f"   - 测试次数: {num_tests}")
    print()
    
    # 存储结果
    reliability_results = []
    baseline_results = []
    
    for test_num in range(1, num_tests + 1):
        print(f"🧪 执行第{test_num}次测试...")
        
        # 测试可靠性增强版本
        print("   测试可靠性增强Enhanced EEHFR...")
        reliability_protocol = ReliabilityEnhancedEEHFR(config, energy_model)
        reliability_result = reliability_protocol.run_protocol(max_rounds=200)
        reliability_results.append(reliability_result)
        
        # 测试基准版本（Enhanced EEHFR 2.0）
        print("   测试基准Enhanced EEHFR 2.0...")
        baseline_config = EnhancedEEHFR2Config(
            num_nodes=config.num_nodes,
            area_width=config.area_width,
            area_height=config.area_height,
            base_station_x=config.base_station_x,
            base_station_y=config.base_station_y,
            initial_energy=config.initial_energy,
            packet_size=config.packet_size
        )
        baseline_protocol = EnhancedEEHFR2Protocol(baseline_config)
        baseline_result = baseline_protocol.run_simulation(max_rounds=200)
        baseline_results.append(baseline_result)
        
        print(f"   ✅ 第{test_num}次测试完成")
        print()
    
    # 分析结果
    print("📈 测试结果分析")
    print("=" * 60)
    
    analyze_results(reliability_results, baseline_results)
    
    # 生成详细报告
    generate_detailed_report(reliability_results, baseline_results)
    
    # 可视化结果
    visualize_results(reliability_results, baseline_results)


def analyze_results(reliability_results: List[Dict], baseline_results: List[Dict]):
    """分析测试结果"""
    
    # 计算平均值和标准差
    def calculate_stats(results, metric):
        values = [r[metric] for r in results]
        return np.mean(values), np.std(values)
    
    # 可靠性增强版本统计
    rel_pdr_mean, rel_pdr_std = calculate_stats(reliability_results, 'packet_delivery_ratio')
    rel_energy_eff_mean, rel_energy_eff_std = calculate_stats(reliability_results, 'energy_efficiency')
    rel_lifetime_mean, rel_lifetime_std = calculate_stats(reliability_results, 'network_lifetime')
    
    # 基准版本统计
    base_pdr_mean, base_pdr_std = calculate_stats(baseline_results, 'packet_delivery_ratio')
    base_energy_eff_mean, base_energy_eff_std = calculate_stats(baseline_results, 'energy_efficiency')
    base_lifetime_mean, base_lifetime_std = calculate_stats(baseline_results, 'network_lifetime')
    
    print("🎯 核心性能指标对比:")
    print()
    
    # 投递率对比
    pdr_improvement = ((rel_pdr_mean - base_pdr_mean) / base_pdr_mean) * 100
    print(f"📦 包投递率 (PDR):")
    print(f"   可靠性增强版: {rel_pdr_mean:.3f} ± {rel_pdr_std:.3f}")
    print(f"   基准版本:     {base_pdr_mean:.3f} ± {base_pdr_std:.3f}")
    print(f"   改进幅度:     {pdr_improvement:+.2f}%")
    
    # 判断是否达到目标
    if rel_pdr_mean >= 0.97:
        print(f"   ✅ 达到目标投递率 (≥97%)")
    else:
        print(f"   ❌ 未达到目标投递率 (≥97%)")
    print()
    
    # 能效对比
    energy_eff_change = ((rel_energy_eff_mean - base_energy_eff_mean) / base_energy_eff_mean) * 100
    print(f"⚡ 能量效率 (packets/J):")
    print(f"   可靠性增强版: {rel_energy_eff_mean:.2f} ± {rel_energy_eff_std:.2f}")
    print(f"   基准版本:     {base_energy_eff_mean:.2f} ± {base_energy_eff_std:.2f}")
    print(f"   变化幅度:     {energy_eff_change:+.2f}%")
    
    # 判断能效损失是否在可接受范围内
    if energy_eff_change >= -2.0:
        print(f"   ✅ 能效损失控制在目标范围内 (≤2%)")
    else:
        print(f"   ⚠️  能效损失超出目标范围 (>2%)")
    print()
    
    # 网络生存时间对比
    lifetime_change = ((rel_lifetime_mean - base_lifetime_mean) / base_lifetime_mean) * 100
    print(f"🕐 网络生存时间 (轮数):")
    print(f"   可靠性增强版: {rel_lifetime_mean:.1f} ± {rel_lifetime_std:.1f}")
    print(f"   基准版本:     {base_lifetime_mean:.1f} ± {base_lifetime_std:.1f}")
    print(f"   变化幅度:     {lifetime_change:+.2f}%")
    print()
    
    # 可靠性增强机制使用统计
    if reliability_results:
        dual_path_avg = np.mean([r.get('dual_path_usage', 0) for r in reliability_results])
        cooperative_avg = np.mean([r.get('cooperative_usage', 0) for r in reliability_results])
        backup_success_avg = np.mean([r.get('backup_path_successes', 0) for r in reliability_results])
        
        print(f"🔧 可靠性增强机制使用情况:")
        print(f"   双路径传输次数: {dual_path_avg:.1f}")
        print(f"   协作传输次数:   {cooperative_avg:.1f}")
        print(f"   备份路径成功:   {backup_success_avg:.1f}")
        print()
    
    # 综合评估
    print("🏆 综合评估:")
    
    target_achieved = 0
    total_targets = 3
    
    if rel_pdr_mean >= 0.97:
        print("   ✅ 投递率目标达成 (≥97%)")
        target_achieved += 1
    else:
        print("   ❌ 投递率目标未达成")
    
    if energy_eff_change >= -2.0:
        print("   ✅ 能效损失控制目标达成 (≤2%)")
        target_achieved += 1
    else:
        print("   ❌ 能效损失控制目标未达成")
    
    if pdr_improvement > 0:
        print("   ✅ 可靠性提升目标达成")
        target_achieved += 1
    else:
        print("   ❌ 可靠性提升目标未达成")
    
    success_rate = (target_achieved / total_targets) * 100
    print(f"   📊 目标达成率: {target_achieved}/{total_targets} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("   🎉 可靠性增强方案验证成功！")
    else:
        print("   ⚠️  可靠性增强方案需要进一步优化")


def generate_detailed_report(reliability_results: List[Dict], baseline_results: List[Dict]):
    """生成详细测试报告"""
    
    report_path = "../results/reliability_enhancement_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 可靠性增强Enhanced EEHFR协议测试报告\n\n")
        f.write(f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**测试次数**: {len(reliability_results)}\n\n")
        
        f.write("## 测试目标\n\n")
        f.write("1. 将投递率从94.1%提升到97-98%\n")
        f.write("2. 能效损失控制在2%以内\n")
        f.write("3. 验证多路径冗余传输机制的有效性\n")
        f.write("4. 评估协作传输的性能贡献\n\n")
        
        f.write("## 详细测试结果\n\n")
        
        # 逐次测试结果
        f.write("### 各次测试结果\n\n")
        f.write("| 测试次数 | 协议版本 | PDR | 能效 (packets/J) | 网络生存时间 |\n")
        f.write("|----------|----------|-----|------------------|-------------|\n")
        
        for i, (rel_result, base_result) in enumerate(zip(reliability_results, baseline_results), 1):
            f.write(f"| {i} | 可靠性增强版 | {rel_result['packet_delivery_ratio']:.3f} | "
                   f"{rel_result['energy_efficiency']:.2f} | {rel_result['network_lifetime']} |\n")
            f.write(f"| {i} | 基准版本 | {base_result['packet_delivery_ratio']:.3f} | "
                   f"{base_result['energy_efficiency']:.2f} | {base_result['network_lifetime']} |\n")
        
        f.write("\n### 统计分析\n\n")
        
        # 计算统计数据
        rel_pdr_mean = np.mean([r['packet_delivery_ratio'] for r in reliability_results])
        base_pdr_mean = np.mean([r['packet_delivery_ratio'] for r in baseline_results])
        pdr_improvement = ((rel_pdr_mean - base_pdr_mean) / base_pdr_mean) * 100
        
        rel_energy_mean = np.mean([r['energy_efficiency'] for r in reliability_results])
        base_energy_mean = np.mean([r['energy_efficiency'] for r in baseline_results])
        energy_change = ((rel_energy_mean - base_energy_mean) / base_energy_mean) * 100
        
        f.write(f"**投递率改进**: {pdr_improvement:+.2f}% ({base_pdr_mean:.3f} → {rel_pdr_mean:.3f})\n\n")
        f.write(f"**能效变化**: {energy_change:+.2f}% ({base_energy_mean:.2f} → {rel_energy_mean:.2f} packets/J)\n\n")
        
        f.write("## 可靠性增强机制分析\n\n")
        
        if reliability_results:
            dual_path_avg = np.mean([r.get('dual_path_usage', 0) for r in reliability_results])
            cooperative_avg = np.mean([r.get('cooperative_usage', 0) for r in reliability_results])
            
            f.write(f"- **双路径传输使用率**: 平均{dual_path_avg:.1f}次/测试\n")
            f.write(f"- **协作传输使用率**: 平均{cooperative_avg:.1f}次/测试\n")
            f.write(f"- **备份路径成功率**: 在主路径失败时的恢复能力\n\n")
        
        f.write("## 结论\n\n")
        
        if rel_pdr_mean >= 0.97 and energy_change >= -2.0:
            f.write("✅ **测试成功**: 可靠性增强方案达到预期目标\n\n")
            f.write("- 投递率成功提升到97%以上\n")
            f.write("- 能效损失控制在可接受范围内\n")
            f.write("- 多路径冗余和协作传输机制有效\n")
        else:
            f.write("⚠️ **需要优化**: 部分目标未完全达成\n\n")
            if rel_pdr_mean < 0.97:
                f.write("- 投递率仍需进一步提升\n")
            if energy_change < -2.0:
                f.write("- 能效损失需要更好控制\n")
    
    print(f"📄 详细报告已保存到: {report_path}")


def visualize_results(reliability_results: List[Dict], baseline_results: List[Dict]):
    """可视化测试结果"""
    
    # 创建图表
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('可靠性增强Enhanced EEHFR协议性能对比', fontsize=16, fontweight='bold')
    
    # 1. 投递率对比
    rel_pdr = [r['packet_delivery_ratio'] for r in reliability_results]
    base_pdr = [r['packet_delivery_ratio'] for r in baseline_results]
    
    x = range(1, len(rel_pdr) + 1)
    ax1.plot(x, rel_pdr, 'o-', label='可靠性增强版', color='green', linewidth=2, markersize=8)
    ax1.plot(x, base_pdr, 's-', label='基准版本', color='blue', linewidth=2, markersize=8)
    ax1.axhline(y=0.97, color='red', linestyle='--', alpha=0.7, label='目标线 (97%)')
    ax1.set_xlabel('测试次数')
    ax1.set_ylabel('包投递率')
    ax1.set_title('包投递率对比')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0.9, 1.0)
    
    # 2. 能效对比
    rel_energy = [r['energy_efficiency'] for r in reliability_results]
    base_energy = [r['energy_efficiency'] for r in baseline_results]
    
    ax2.plot(x, rel_energy, 'o-', label='可靠性增强版', color='green', linewidth=2, markersize=8)
    ax2.plot(x, base_energy, 's-', label='基准版本', color='blue', linewidth=2, markersize=8)
    ax2.set_xlabel('测试次数')
    ax2.set_ylabel('能量效率 (packets/J)')
    ax2.set_title('能量效率对比')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 网络生存时间对比
    rel_lifetime = [r['network_lifetime'] for r in reliability_results]
    base_lifetime = [r['network_lifetime'] for r in baseline_results]
    
    ax3.plot(x, rel_lifetime, 'o-', label='可靠性增强版', color='green', linewidth=2, markersize=8)
    ax3.plot(x, base_lifetime, 's-', label='基准版本', color='blue', linewidth=2, markersize=8)
    ax3.set_xlabel('测试次数')
    ax3.set_ylabel('网络生存时间 (轮数)')
    ax3.set_title('网络生存时间对比')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 可靠性机制使用情况
    if reliability_results and 'dual_path_usage' in reliability_results[0]:
        dual_path_usage = [r.get('dual_path_usage', 0) for r in reliability_results]
        cooperative_usage = [r.get('cooperative_usage', 0) for r in reliability_results]
        
        width = 0.35
        x_pos = np.arange(len(x))
        
        ax4.bar(x_pos - width/2, dual_path_usage, width, label='双路径传输', color='orange', alpha=0.8)
        ax4.bar(x_pos + width/2, cooperative_usage, width, label='协作传输', color='purple', alpha=0.8)
        ax4.set_xlabel('测试次数')
        ax4.set_ylabel('使用次数')
        ax4.set_title('可靠性增强机制使用情况')
        ax4.set_xticks(x_pos)
        ax4.set_xticklabels(x)
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    else:
        ax4.text(0.5, 0.5, '可靠性机制统计数据不可用', 
                ha='center', va='center', transform=ax4.transAxes, fontsize=12)
        ax4.set_title('可靠性增强机制使用情况')
    
    plt.tight_layout()
    
    # 保存图表
    chart_path = "../results/reliability_enhancement_comparison.png"
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    print(f"📊 性能对比图表已保存到: {chart_path}")
    
    plt.show()


if __name__ == "__main__":
    run_reliability_test()
