#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced PEGASIS 测试脚本
对比测试改进的PEGASIS协议与原始PEGASIS的性能

目标: 验证5-10%的渐进式性能提升

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from enhanced_pegasis import EnhancedPEGASISProtocol, EnhancedPEGASISConfig
from benchmark_protocols import PEGASISProtocol, HEEDProtocolWrapper, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
import time
import json
from datetime import datetime
import statistics

def test_enhanced_pegasis():
    """测试Enhanced PEGASIS协议"""
    print("🚀 Enhanced PEGASIS 性能测试")
    print("=" * 80)
    
    # 创建配置
    config = EnhancedPEGASISConfig(
        num_nodes=50,
        area_width=100.0,
        area_height=100.0,
        base_station_x=50.0,
        base_station_y=50.0,
        initial_energy=2.0,
        transmission_range=30.0,
        packet_size=1024,
        energy_threshold=0.1,
        leader_rotation_interval=10,
        chain_optimization_interval=50
    )
    
    # 创建协议实例
    protocol = EnhancedPEGASISProtocol(config)
    
    # 初始化网络
    protocol.initialize_network()
    
    # 运行仿真
    print("\n🔄 开始仿真测试...")
    start_time = time.time()
    results = protocol.run_simulation(max_rounds=200)
    execution_time = time.time() - start_time
    
    # 输出结果
    print(f"\n📊 Enhanced PEGASIS 测试结果:")
    print(f"   网络生存时间: {results['network_lifetime']} 轮")
    print(f"   总能耗: {results['total_energy_consumed']:.6f} J")
    print(f"   能效: {results['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {results['packet_delivery_ratio']:.3f}")
    print(f"   领导者变更次数: {results['total_leadership_changes']}")
    print(f"   平均传输距离: {results['avg_transmission_distance']:.2f}")
    print(f"   执行时间: {execution_time:.2f}s")
    
    results['execution_time'] = execution_time
    return results

def run_multiple_tests(num_tests: int = 5):
    """运行多次测试以获得统计显著性"""
    print(f"\n🔬 运行 {num_tests} 次重复测试以验证性能稳定性")
    print("=" * 80)
    
    # 统一网络配置
    base_config = NetworkConfig(
        num_nodes=50,
        area_width=100.0,
        area_height=100.0,
        base_station_x=50.0,
        base_station_y=50.0,
        initial_energy=2.0
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 存储结果
    enhanced_results = []
    original_results = []
    
    for i in range(num_tests):
        print(f"\n🔄 第 {i+1}/{num_tests} 次测试")
        print("-" * 50)
        
        # 测试Enhanced PEGASIS
        enhanced_config = EnhancedPEGASISConfig(
            num_nodes=base_config.num_nodes,
            area_width=base_config.area_width,
            area_height=base_config.area_height,
            base_station_x=base_config.base_station_x,
            base_station_y=base_config.base_station_y,
            initial_energy=base_config.initial_energy
        )
        
        enhanced_protocol = EnhancedPEGASISProtocol(enhanced_config)
        enhanced_protocol.initialize_network()
        enhanced_result = enhanced_protocol.run_simulation(max_rounds=200)
        enhanced_results.append(enhanced_result)
        
        print(f"   Enhanced PEGASIS: {enhanced_result['energy_efficiency']:.2f} packets/J, "
              f"PDR: {enhanced_result['packet_delivery_ratio']:.3f}")
        
        # 测试原始PEGASIS
        original_protocol = PEGASISProtocol(base_config, energy_model)
        original_result = original_protocol.run_simulation(max_rounds=200)
        original_results.append(original_result)
        
        print(f"   Original PEGASIS: {original_result['energy_efficiency']:.2f} packets/J, "
              f"PDR: {original_result['packet_delivery_ratio']:.3f}")
    
    return enhanced_results, original_results

def analyze_statistical_results(enhanced_results, original_results):
    """统计分析结果"""
    print("\n📊 统计分析结果")
    print("=" * 80)
    
    # 提取关键指标
    enhanced_efficiency = [r['energy_efficiency'] for r in enhanced_results]
    original_efficiency = [r['energy_efficiency'] for r in original_results]
    
    enhanced_pdr = [r['packet_delivery_ratio'] for r in enhanced_results]
    original_pdr = [r['packet_delivery_ratio'] for r in original_results]
    
    enhanced_energy = [r['total_energy_consumed'] for r in enhanced_results]
    original_energy = [r['total_energy_consumed'] for r in original_results]
    
    # 计算统计量
    print("📈 能效 (packets/J):")
    print(f"   Enhanced PEGASIS: {statistics.mean(enhanced_efficiency):.2f} ± {statistics.stdev(enhanced_efficiency):.2f}")
    print(f"   Original PEGASIS: {statistics.mean(original_efficiency):.2f} ± {statistics.stdev(original_efficiency):.2f}")
    
    efficiency_improvement = ((statistics.mean(enhanced_efficiency) - statistics.mean(original_efficiency)) / 
                             statistics.mean(original_efficiency)) * 100
    print(f"   性能提升: {efficiency_improvement:+.1f}%")
    
    print("\n📡 投递率:")
    print(f"   Enhanced PEGASIS: {statistics.mean(enhanced_pdr):.3f} ± {statistics.stdev(enhanced_pdr):.3f}")
    print(f"   Original PEGASIS: {statistics.mean(original_pdr):.3f} ± {statistics.stdev(original_pdr):.3f}")
    
    pdr_improvement = ((statistics.mean(enhanced_pdr) - statistics.mean(original_pdr)) / 
                      statistics.mean(original_pdr)) * 100
    print(f"   可靠性提升: {pdr_improvement:+.1f}%")
    
    print("\n⚡ 总能耗 (J):")
    print(f"   Enhanced PEGASIS: {statistics.mean(enhanced_energy):.3f} ± {statistics.stdev(enhanced_energy):.3f}")
    print(f"   Original PEGASIS: {statistics.mean(original_energy):.3f} ± {statistics.stdev(original_energy):.3f}")
    
    energy_improvement = ((statistics.mean(original_energy) - statistics.mean(enhanced_energy)) / 
                         statistics.mean(original_energy)) * 100
    print(f"   能耗降低: {energy_improvement:+.1f}%")
    
    # 评估结果
    print("\n🎯 改进效果评估:")
    if efficiency_improvement >= 5.0:
        print("   ✅ 能效提升达到5%+目标！")
    elif efficiency_improvement >= 2.0:
        print("   ⚠️ 能效有所提升，但未达到5%目标")
    else:
        print("   ❌ 能效提升不明显，需要进一步优化")
    
    if pdr_improvement >= 1.0:
        print("   ✅ 可靠性有显著提升！")
    elif pdr_improvement >= 0:
        print("   ⚠️ 可靠性略有提升")
    else:
        print("   ❌ 可靠性有所下降")
    
    # 保存详细结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_summary = {
        'enhanced_results': enhanced_results,
        'original_results': original_results,
        'statistics': {
            'enhanced_efficiency_mean': statistics.mean(enhanced_efficiency),
            'enhanced_efficiency_std': statistics.stdev(enhanced_efficiency),
            'original_efficiency_mean': statistics.mean(original_efficiency),
            'original_efficiency_std': statistics.stdev(original_efficiency),
            'efficiency_improvement_percent': efficiency_improvement,
            'pdr_improvement_percent': pdr_improvement,
            'energy_improvement_percent': energy_improvement
        }
    }
    
    filename = f"enhanced_pegasis_statistical_analysis_{timestamp}.json"
    filepath = os.path.join(os.path.dirname(__file__), '..', 'results', filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 详细结果已保存到: {filename}")
    
    return results_summary

def main():
    """主函数"""
    print("🎯 Enhanced PEGASIS 渐进式改进验证")
    print("目标: 基于PEGASIS实现5-10%性能提升")
    print("=" * 80)
    
    try:
        # 运行多次测试
        enhanced_results, original_results = run_multiple_tests(num_tests=5)
        
        # 统计分析
        summary = analyze_statistical_results(enhanced_results, original_results)
        
        print("\n🎉 Enhanced PEGASIS测试完成！")
        print("📈 基于能量感知优化的渐进式改进验证完成")
        
        # 简要总结
        improvement = summary['statistics']['efficiency_improvement_percent']
        if improvement >= 5.0:
            print(f"✅ 成功实现 {improvement:.1f}% 性能提升，达到预期目标！")
        else:
            print(f"⚠️ 实现 {improvement:.1f}% 性能提升，需要进一步优化")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
