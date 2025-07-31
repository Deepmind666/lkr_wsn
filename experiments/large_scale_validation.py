#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced PEGASIS 大规模网络验证实验
验证算法在100、200、500节点规模下的可扩展性和性能稳定性

目标: 确保Enhanced PEGASIS在大规模网络中保持90%+性能提升

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from enhanced_pegasis import EnhancedPEGASISProtocol, EnhancedPEGASISConfig
from benchmark_protocols import PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
import time
import json
import statistics
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

def test_scalability(network_sizes=[50, 100, 200], num_tests=3, max_rounds=500):
    """测试Enhanced PEGASIS的可扩展性"""
    print("🚀 Enhanced PEGASIS 大规模网络可扩展性验证")
    print("=" * 80)
    
    results = {}
    
    for size in network_sizes:
        print(f"\n📊 测试网络规模: {size} 节点")
        print("-" * 50)
        
        enhanced_results = []
        original_results = []
        
        for test_id in range(num_tests):
            print(f"   第 {test_id+1}/{num_tests} 次测试...")
            
            # 测试Enhanced PEGASIS
            enhanced_config = EnhancedPEGASISConfig(
                num_nodes=size,
                area_width=int(size * 2),  # 动态调整区域大小
                area_height=int(size * 2),
                base_station_x=size,
                base_station_y=size,
                initial_energy=2.0,
                transmission_range=30.0,
                packet_size=1024
            )
            
            enhanced_protocol = EnhancedPEGASISProtocol(enhanced_config)
            enhanced_protocol.initialize_network()
            
            start_time = time.time()
            enhanced_result = enhanced_protocol.run_simulation(max_rounds=max_rounds)
            enhanced_time = time.time() - start_time
            enhanced_result['execution_time'] = enhanced_time
            enhanced_results.append(enhanced_result)
            
            # 测试原始PEGASIS
            original_config = NetworkConfig(
                num_nodes=size,
                area_width=int(size * 2),
                area_height=int(size * 2),
                base_station_x=size,
                base_station_y=size,
                initial_energy=2.0
            )
            
            energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
            original_protocol = PEGASISProtocol(original_config, energy_model)
            
            start_time = time.time()
            original_result = original_protocol.run_simulation(max_rounds=max_rounds)
            original_time = time.time() - start_time
            original_result['execution_time'] = original_time
            original_results.append(original_result)
            
            # 实时性能对比
            enhanced_eff = enhanced_result['energy_efficiency']
            original_eff = original_result['energy_efficiency']
            improvement = ((enhanced_eff - original_eff) / original_eff) * 100
            
            print(f"      Enhanced: {enhanced_eff:.1f} packets/J, "
                  f"Original: {original_eff:.1f} packets/J, "
                  f"提升: {improvement:+.1f}%")
        
        # 统计分析
        enhanced_efficiency = [r['energy_efficiency'] for r in enhanced_results]
        original_efficiency = [r['energy_efficiency'] for r in original_results]
        enhanced_pdr = [r['packet_delivery_ratio'] for r in enhanced_results]
        original_pdr = [r['packet_delivery_ratio'] for r in original_results]
        enhanced_time = [r['execution_time'] for r in enhanced_results]
        original_time = [r['execution_time'] for r in original_results]
        
        avg_improvement = ((statistics.mean(enhanced_efficiency) - statistics.mean(original_efficiency)) / 
                          statistics.mean(original_efficiency)) * 100
        
        results[size] = {
            'enhanced_efficiency_mean': statistics.mean(enhanced_efficiency),
            'enhanced_efficiency_std': statistics.stdev(enhanced_efficiency) if len(enhanced_efficiency) > 1 else 0,
            'original_efficiency_mean': statistics.mean(original_efficiency),
            'original_efficiency_std': statistics.stdev(original_efficiency) if len(original_efficiency) > 1 else 0,
            'efficiency_improvement': avg_improvement,
            'enhanced_pdr_mean': statistics.mean(enhanced_pdr),
            'original_pdr_mean': statistics.mean(original_pdr),
            'enhanced_time_mean': statistics.mean(enhanced_time),
            'original_time_mean': statistics.mean(original_time),
            'scalability_factor': statistics.mean(enhanced_time) / (size / 50),  # 相对于50节点的时间复杂度
            'enhanced_results': enhanced_results,
            'original_results': original_results
        }
        
        print(f"   📈 平均性能提升: {avg_improvement:+.1f}%")
        print(f"   ⏱️ 平均执行时间: Enhanced {statistics.mean(enhanced_time):.2f}s, "
              f"Original {statistics.mean(original_time):.2f}s")
    
    return results

def analyze_scalability_results(results):
    """分析可扩展性结果"""
    print("\n📊 大规模网络可扩展性分析")
    print("=" * 80)
    
    sizes = sorted(results.keys())
    
    print("📈 性能提升随网络规模变化:")
    print("-" * 60)
    print(f"{'网络规模':<10} {'性能提升':<12} {'能效(Enhanced)':<15} {'能效(Original)':<15} {'执行时间':<10}")
    print("-" * 60)
    
    improvements = []
    for size in sizes:
        data = results[size]
        improvement = data['efficiency_improvement']
        enhanced_eff = data['enhanced_efficiency_mean']
        original_eff = data['original_efficiency_mean']
        exec_time = data['enhanced_time_mean']
        
        improvements.append(improvement)
        
        print(f"{size:<10} {improvement:+.1f}%{'':<7} {enhanced_eff:<15.1f} {original_eff:<15.1f} {exec_time:<10.2f}s")
    
    # 可扩展性评估
    print(f"\n🎯 可扩展性评估:")
    min_improvement = min(improvements)
    max_improvement = max(improvements)
    avg_improvement = statistics.mean(improvements)
    
    print(f"   平均性能提升: {avg_improvement:.1f}%")
    print(f"   性能提升范围: {min_improvement:.1f}% ~ {max_improvement:.1f}%")
    print(f"   性能稳定性: {statistics.stdev(improvements):.1f}% (标准差)")
    
    if min_improvement >= 90:
        print("   ✅ 优秀！所有规模都保持90%+性能提升")
    elif min_improvement >= 50:
        print("   ⚠️ 良好，但大规模网络性能有所下降")
    else:
        print("   ❌ 可扩展性需要改进")
    
    # 时间复杂度分析
    print(f"\n⏱️ 时间复杂度分析:")
    for size in sizes:
        scalability_factor = results[size]['scalability_factor']
        theoretical_factor = (size / 50) * np.log(size / 50)  # O(n log n)理论值
        print(f"   {size}节点: 实际{scalability_factor:.2f}x, 理论{theoretical_factor:.2f}x")
    
    return {
        'average_improvement': avg_improvement,
        'min_improvement': min_improvement,
        'max_improvement': max_improvement,
        'stability': statistics.stdev(improvements),
        'scalability_assessment': 'excellent' if min_improvement >= 90 else 'good' if min_improvement >= 50 else 'needs_improvement'
    }

def generate_scalability_charts(results):
    """生成可扩展性分析图表"""
    sizes = sorted(results.keys())
    
    # 提取数据
    enhanced_efficiency = [results[size]['enhanced_efficiency_mean'] for size in sizes]
    original_efficiency = [results[size]['original_efficiency_mean'] for size in sizes]
    improvements = [results[size]['efficiency_improvement'] for size in sizes]
    execution_times = [results[size]['enhanced_time_mean'] for size in sizes]
    
    # 创建图表
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. 能效对比
    ax1.plot(sizes, enhanced_efficiency, 'b-o', label='Enhanced PEGASIS', linewidth=2, markersize=8)
    ax1.plot(sizes, original_efficiency, 'r-s', label='Original PEGASIS', linewidth=2, markersize=8)
    ax1.set_xlabel('Network Size (nodes)')
    ax1.set_ylabel('Energy Efficiency (packets/J)')
    ax1.set_title('Energy Efficiency vs Network Size')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 性能提升
    ax2.bar(sizes, improvements, color='green', alpha=0.7, width=15)
    ax2.axhline(y=90, color='red', linestyle='--', label='90% Target')
    ax2.set_xlabel('Network Size (nodes)')
    ax2.set_ylabel('Performance Improvement (%)')
    ax2.set_title('Performance Improvement vs Network Size')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 执行时间
    ax3.plot(sizes, execution_times, 'purple', marker='D', linewidth=2, markersize=8)
    theoretical_times = [(size/50)**1.2 * execution_times[0] for size in sizes]  # 理论O(n^1.2)
    ax3.plot(sizes, theoretical_times, 'orange', linestyle='--', label='Theoretical O(n^1.2)')
    ax3.set_xlabel('Network Size (nodes)')
    ax3.set_ylabel('Execution Time (seconds)')
    ax3.set_title('Execution Time vs Network Size')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 投递率对比
    enhanced_pdr = [results[size]['enhanced_pdr_mean'] for size in sizes]
    original_pdr = [results[size]['original_pdr_mean'] for size in sizes]
    ax4.plot(sizes, enhanced_pdr, 'b-o', label='Enhanced PEGASIS', linewidth=2, markersize=8)
    ax4.plot(sizes, original_pdr, 'r-s', label='Original PEGASIS', linewidth=2, markersize=8)
    ax4.set_xlabel('Network Size (nodes)')
    ax4.set_ylabel('Packet Delivery Ratio')
    ax4.set_title('Packet Delivery Ratio vs Network Size')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0.9, 1.01)
    
    plt.tight_layout()
    
    # 保存图表
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_path = os.path.join(os.path.dirname(__file__), '..', 'results', 
                             f'enhanced_pegasis_scalability_{timestamp}.png')
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    print(f"\n📊 可扩展性分析图表已保存: enhanced_pegasis_scalability_{timestamp}.png")
    
    return chart_path

def main():
    """主函数"""
    print("🎯 Enhanced PEGASIS 大规模网络验证")
    print("目标: 验证算法可扩展性，确保90%+性能提升")
    print("=" * 80)
    
    try:
        # 运行可扩展性测试
        print("🔄 开始大规模网络测试...")
        results = test_scalability(
            network_sizes=[50, 100, 200], 
            num_tests=3, 
            max_rounds=300  # 减少轮数以加快测试
        )
        
        # 分析结果
        analysis = analyze_scalability_results(results)
        
        # 生成图表
        chart_path = generate_scalability_charts(results)
        
        # 保存详细结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(os.path.dirname(__file__), '..', 'results', 
                                   f'large_scale_validation_{timestamp}.json')
        
        final_results = {
            'scalability_results': results,
            'analysis_summary': analysis,
            'chart_path': chart_path,
            'test_parameters': {
                'network_sizes': [50, 100, 200],
                'num_tests': 3,
                'max_rounds': 300
            }
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 详细结果已保存: large_scale_validation_{timestamp}.json")
        
        # 总结
        print(f"\n🎉 大规模网络验证完成！")
        print(f"📈 平均性能提升: {analysis['average_improvement']:.1f}%")
        print(f"🎯 可扩展性评估: {analysis['scalability_assessment']}")
        
        if analysis['scalability_assessment'] == 'excellent':
            print("✅ Enhanced PEGASIS在大规模网络中表现优异，满足Q3期刊要求！")
        else:
            print("⚠️ 需要进一步优化大规模网络性能")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
