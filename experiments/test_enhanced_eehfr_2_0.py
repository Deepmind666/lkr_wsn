#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced EEHFR 2.0 测试脚本
对比测试新的混合优化协议与基准协议的性能

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from enhanced_eehfr_2_0 import EnhancedEEHFR2Protocol, EnhancedEEHFR2Config
from benchmark_protocols import LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
import time
import json
from datetime import datetime

def test_enhanced_eehfr_2_0():
    """测试Enhanced EEHFR 2.0协议"""
    print("🚀 Enhanced EEHFR 2.0 性能测试")
    print("=" * 80)
    
    # 创建配置
    config = EnhancedEEHFR2Config(
        num_nodes=50,
        area_width=100.0,
        area_height=100.0,
        base_station_x=50.0,
        base_station_y=50.0,
        initial_energy=2.0,
        transmission_range=30.0,
        packet_size=1024,
        cluster_head_percentage=0.05
    )
    
    # 创建协议实例
    protocol = EnhancedEEHFR2Protocol(config)
    
    # 初始化网络
    protocol.initialize_network()
    
    # 运行仿真
    print("\n🔄 开始仿真测试...")
    start_time = time.time()
    results = protocol.run_simulation(max_rounds=200)
    execution_time = time.time() - start_time
    
    # 输出结果
    print(f"\n📊 Enhanced EEHFR 2.0 测试结果:")
    print(f"   网络生存时间: {results['network_lifetime']} 轮")
    print(f"   总能耗: {results['total_energy_consumed']:.6f} J")
    print(f"   能效: {results['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {results['packet_delivery_ratio']:.3f}")
    print(f"   最终存活节点: {results['final_alive_nodes']}")
    print(f"   执行时间: {execution_time:.2f}s")
    
    return results

def run_comprehensive_comparison():
    """运行全面的协议对比测试"""
    print("\n🏆 Enhanced EEHFR 2.0 vs 基准协议对比测试")
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
    results = {}
    
    # 1. 测试Enhanced EEHFR 2.0
    print("\n1️⃣ 测试Enhanced EEHFR 2.0")
    print("-" * 50)
    
    eehfr2_config = EnhancedEEHFR2Config(
        num_nodes=base_config.num_nodes,
        area_width=base_config.area_width,
        area_height=base_config.area_height,
        base_station_x=base_config.base_station_x,
        base_station_y=base_config.base_station_y,
        initial_energy=base_config.initial_energy
    )
    
    start_time = time.time()
    eehfr2 = EnhancedEEHFR2Protocol(eehfr2_config)
    eehfr2.initialize_network()
    eehfr2_results = eehfr2.run_simulation(max_rounds=200)
    eehfr2_time = time.time() - start_time
    
    results['Enhanced EEHFR 2.0'] = eehfr2_results
    results['Enhanced EEHFR 2.0']['execution_time'] = eehfr2_time
    
    print(f"✅ Enhanced EEHFR 2.0测试完成 (耗时: {eehfr2_time:.2f}s)")
    print(f"   能效: {eehfr2_results['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {eehfr2_results['packet_delivery_ratio']:.3f}")
    
    # 2. 测试PEGASIS协议
    print("\n2️⃣ 测试PEGASIS协议")
    print("-" * 50)
    start_time = time.time()
    
    pegasis = PEGASISProtocol(base_config, energy_model)
    pegasis_results = pegasis.run_simulation(max_rounds=200)
    pegasis_time = time.time() - start_time
    
    results['PEGASIS'] = pegasis_results
    results['PEGASIS']['execution_time'] = pegasis_time
    
    print(f"✅ PEGASIS测试完成 (耗时: {pegasis_time:.2f}s)")
    print(f"   能效: {pegasis_results['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {pegasis_results['packet_delivery_ratio']:.3f}")
    
    # 3. 测试HEED协议
    print("\n3️⃣ 测试HEED协议")
    print("-" * 50)
    start_time = time.time()
    
    heed = HEEDProtocolWrapper(base_config, energy_model)
    heed_results = heed.run_simulation(max_rounds=200)
    heed_time = time.time() - start_time
    
    results['HEED'] = heed_results
    results['HEED']['execution_time'] = heed_time
    
    print(f"✅ HEED测试完成 (耗时: {heed_time:.2f}s)")
    print(f"   能效: {heed_results['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {heed_results['packet_delivery_ratio']:.3f}")
    
    return results

def analyze_results(results):
    """分析对比结果"""
    print("\n📊 性能对比分析")
    print("=" * 80)
    
    # 性能指标对比表
    print("📈 关键性能指标对比:")
    print("-" * 100)
    print(f"{'协议':<20} {'生存时间':<12} {'总能耗(J)':<12} {'能效':<15} {'投递率':<10} {'执行时间(s)':<12}")
    print("-" * 100)
    
    for protocol, result in results.items():
        print(f"{protocol:<20} {result['network_lifetime']:<12} "
              f"{result['total_energy_consumed']:<12.6f} "
              f"{result['energy_efficiency']:<15.2f} "
              f"{result['packet_delivery_ratio']:<10.3f} "
              f"{result['execution_time']:<12.2f}")
    
    # 性能提升分析
    if 'Enhanced EEHFR 2.0' in results and 'PEGASIS' in results:
        eehfr2_efficiency = results['Enhanced EEHFR 2.0']['energy_efficiency']
        pegasis_efficiency = results['PEGASIS']['energy_efficiency']
        
        if pegasis_efficiency > 0:
            improvement = ((eehfr2_efficiency - pegasis_efficiency) / pegasis_efficiency) * 100
            print(f"\n🎯 Enhanced EEHFR 2.0 vs PEGASIS:")
            print(f"   能效提升: {improvement:+.1f}%")
            
            if improvement >= 10:
                print("   ✅ 达到10%+性能提升目标！")
            elif improvement >= 5:
                print("   ⚠️ 接近目标，需要进一步优化")
            else:
                print("   ❌ 未达到预期目标，需要算法改进")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"enhanced_eehfr_2_0_comparison_{timestamp}.json"
    filepath = os.path.join(os.path.dirname(__file__), '..', 'results', filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存到: {filename}")

def main():
    """主函数"""
    print("🎯 Enhanced EEHFR 2.0 协议测试与验证")
    print("目标: 验证双阶段混合优化协议的性能提升")
    print("=" * 80)
    
    try:
        # 运行全面对比测试
        results = run_comprehensive_comparison()
        
        # 分析结果
        analyze_results(results)
        
        print("\n🎉 测试完成！")
        print("📈 Enhanced EEHFR 2.0 双阶段混合优化协议验证完成")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
