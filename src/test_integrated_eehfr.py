#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成版Enhanced EEHFR协议测试脚本

目的：验证新集成的Enhanced EEHFR协议是否正常工作
测试内容：
1. 基础功能测试
2. 与LEACH/PEGASIS的初步对比
3. 性能指标验证

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import json
from typing import Dict, List
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def test_basic_functionality():
    """测试基础功能"""
    
    print("🧪 测试集成版Enhanced EEHFR基础功能")
    print("=" * 50)
    
    # 创建测试配置
    config = NetworkConfig(
        num_nodes=20,
        area_width=50,
        area_height=50,
        initial_energy=1.0,
        packet_size=1024,
        base_station_x=25,
        base_station_y=25
    )
    
    try:
        # 创建协议实例
        protocol = IntegratedEnhancedEEHFRProtocol(config)
        
        print(f"✅ 协议实例创建成功")
        print(f"   节点数量: {len(protocol.nodes)}")
        print(f"   环境类型: {protocol.current_environment.value}")
        print(f"   能耗模型: {protocol.energy_model.platform.value}")
        
        # 运行短期仿真
        result = protocol.run_simulation(max_rounds=100)
        
        print(f"\n📊 基础功能测试结果:")
        print(f"   网络生存时间: {result['network_lifetime']} 轮")
        print(f"   总能耗: {result['total_energy_consumed']:.6f} J")
        print(f"   能效: {result['energy_efficiency']:.1f} packets/J")
        print(f"   数据包投递率: {result['packet_delivery_ratio']:.3f}")
        print(f"   最终存活节点: {result['final_alive_nodes']}")
        print(f"   执行时间: {result['execution_time']:.3f} 秒")
        
        return True, result
        
    except Exception as e:
        print(f"❌ 基础功能测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def test_three_protocol_comparison():
    """测试三协议对比"""
    
    print("\n🏆 三协议初步对比测试")
    print("=" * 50)
    
    # 创建测试配置
    config = NetworkConfig(
        num_nodes=30,
        area_width=100,
        area_height=100,
        initial_energy=2.0,
        packet_size=1024
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    protocols = [
        ('LEACH', LEACHProtocol),
        ('PEGASIS', PEGASISProtocol),
        ('Integrated_Enhanced_EEHFR', IntegratedEnhancedEEHFRProtocol)
    ]
    
    results = {}
    
    for protocol_name, protocol_class in protocols:
        print(f"\n🧪 测试 {protocol_name} 协议...")
        
        try:
            if protocol_name == 'Integrated_Enhanced_EEHFR':
                protocol = protocol_class(config)
            else:
                protocol = protocol_class(config, energy_model)
            
            # 运行仿真
            start_time = time.time()
            result = protocol.run_simulation(max_rounds=500)
            execution_time = time.time() - start_time
            
            results[protocol_name] = {
                'network_lifetime': result['network_lifetime'],
                'total_energy_consumed': result['total_energy_consumed'],
                'energy_efficiency': result['energy_efficiency'],
                'packet_delivery_ratio': result['packet_delivery_ratio'],
                'final_alive_nodes': result['final_alive_nodes'],
                'execution_time': execution_time
            }
            
            print(f"   ✅ {protocol_name} 测试完成")
            print(f"      生存时间: {result['network_lifetime']} 轮")
            print(f"      总能耗: {result['total_energy_consumed']:.3f} J")
            print(f"      能效: {result['energy_efficiency']:.1f} packets/J")
            print(f"      投递率: {result['packet_delivery_ratio']:.3f}")
            
        except Exception as e:
            print(f"   ❌ {protocol_name} 测试失败: {str(e)}")
            results[protocol_name] = None
    
    return results

def analyze_comparison_results(results: Dict):
    """分析对比结果"""
    
    print("\n📊 三协议对比分析")
    print("=" * 50)
    
    # 过滤有效结果
    valid_results = {k: v for k, v in results.items() if v is not None}
    
    if len(valid_results) < 2:
        print("❌ 有效结果不足，无法进行对比分析")
        return
    
    # 创建对比表格
    print(f"{'协议':<25} {'生存时间(轮)':<12} {'总能耗(J)':<12} {'能效(p/J)':<12} {'投递率':<8}")
    print("-" * 70)
    
    for protocol_name, result in valid_results.items():
        print(f"{protocol_name:<25} "
              f"{result['network_lifetime']:<12} "
              f"{result['total_energy_consumed']:<12.3f} "
              f"{result['energy_efficiency']:<12.1f} "
              f"{result['packet_delivery_ratio']:<8.3f}")
    
    # 性能分析
    print(f"\n🎯 性能分析:")
    
    # 找出各项指标的最佳协议
    best_lifetime = max(valid_results.items(), key=lambda x: x[1]['network_lifetime'])
    best_energy_eff = max(valid_results.items(), key=lambda x: x[1]['energy_efficiency'])
    best_pdr = max(valid_results.items(), key=lambda x: x[1]['packet_delivery_ratio'])
    
    print(f"   🏆 最长生存时间: {best_lifetime[0]} ({best_lifetime[1]['network_lifetime']} 轮)")
    print(f"   🏆 最高能效: {best_energy_eff[0]} ({best_energy_eff[1]['energy_efficiency']:.1f} packets/J)")
    print(f"   🏆 最高投递率: {best_pdr[0]} ({best_pdr[1]['packet_delivery_ratio']:.3f})")
    
    # Enhanced EEHFR性能评估
    if 'Integrated_Enhanced_EEHFR' in valid_results:
        eehfr_result = valid_results['Integrated_Enhanced_EEHFR']
        
        print(f"\n🎯 Enhanced EEHFR性能评估:")
        
        # 与其他协议对比
        other_protocols = {k: v for k, v in valid_results.items() if k != 'Integrated_Enhanced_EEHFR'}
        
        if other_protocols:
            avg_lifetime = sum(r['network_lifetime'] for r in other_protocols.values()) / len(other_protocols)
            avg_energy_eff = sum(r['energy_efficiency'] for r in other_protocols.values()) / len(other_protocols)
            avg_pdr = sum(r['packet_delivery_ratio'] for r in other_protocols.values()) / len(other_protocols)
            
            lifetime_improvement = (eehfr_result['network_lifetime'] - avg_lifetime) / avg_lifetime * 100
            energy_improvement = (eehfr_result['energy_efficiency'] - avg_energy_eff) / avg_energy_eff * 100
            pdr_improvement = (eehfr_result['packet_delivery_ratio'] - avg_pdr) / avg_pdr * 100
            
            print(f"   相比平均水平:")
            print(f"     生存时间: {lifetime_improvement:+.1f}%")
            print(f"     能效: {energy_improvement:+.1f}%")
            print(f"     投递率: {pdr_improvement:+.1f}%")

def save_test_results(basic_result, comparison_results):
    """保存测试结果"""
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    test_results = {
        'timestamp': timestamp,
        'basic_functionality_test': basic_result,
        'three_protocol_comparison': comparison_results,
        'test_summary': {
            'basic_test_passed': basic_result is not None,
            'protocols_tested': len([r for r in comparison_results.values() if r is not None]),
            'enhanced_eehfr_working': 'Integrated_Enhanced_EEHFR' in comparison_results and 
                                    comparison_results['Integrated_Enhanced_EEHFR'] is not None
        }
    }
    
    # 保存到results目录
    results_dir = "../results"
    os.makedirs(results_dir, exist_ok=True)
    
    filename = f"{results_dir}/integrated_eehfr_test_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 测试结果已保存: {filename}")

def main():
    """主函数"""
    
    print("🔬 集成版Enhanced EEHFR协议测试")
    print("=" * 60)
    print("目的: 验证新集成的Enhanced EEHFR协议功能和性能")
    print("时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # 1. 基础功能测试
    basic_success, basic_result = test_basic_functionality()
    
    if not basic_success:
        print("\n❌ 基础功能测试失败，停止后续测试")
        return
    
    # 2. 三协议对比测试
    comparison_results = test_three_protocol_comparison()
    
    # 3. 结果分析
    analyze_comparison_results(comparison_results)
    
    # 4. 保存结果
    save_test_results(basic_result, comparison_results)
    
    print("\n" + "=" * 60)
    print("🎯 集成版Enhanced EEHFR协议测试完成")
    
    # 总结
    if basic_success and 'Integrated_Enhanced_EEHFR' in comparison_results:
        if comparison_results['Integrated_Enhanced_EEHFR'] is not None:
            print("✅ 集成版Enhanced EEHFR协议工作正常，可以进行下一步优化")
        else:
            print("⚠️  集成版Enhanced EEHFR协议在对比测试中出现问题，需要调试")
    else:
        print("❌ 集成版Enhanced EEHFR协议存在问题，需要修复")

if __name__ == "__main__":
    main()
