#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced EEHFR 2.0 重新设计版本测试脚本
对比测试新的智能混合协议与基准协议的性能

作者: Enhanced EEHFR Research Team
日期: 2025-07-31
版本: 1.0
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from enhanced_eehfr_2_0_redesigned import EnhancedEEHFR2Protocol, EnhancedEEHFR2Config
from benchmark_protocols import LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
import time
import json
from datetime import datetime

def test_enhanced_eehfr_2_0_redesigned():
    """测试Enhanced EEHFR 2.0重新设计版本"""
    print("🚀 Enhanced EEHFR 2.0 重新设计版本性能测试")
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
        cluster_head_percentage=0.1
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
    print(f"\n📊 Enhanced EEHFR 2.0 重新设计版本测试结果:")
    print(f"   网络生存时间: {results['network_lifetime']} 轮")
    print(f"   总能耗: {results['total_energy_consumed']:.6f} J")
    print(f"   能效: {results['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {results['packet_delivery_ratio']:.3f}")
    print(f"   最终存活节点: {results['final_alive_nodes']}")
    print(f"   执行时间: {execution_time:.2f}s")
    
    return results

def run_comprehensive_comparison():
    """运行全面的协议对比测试"""
    print("\n🏆 Enhanced EEHFR 2.0 重新设计版本 vs 基准协议对比测试")
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
    
    # 1. 测试Enhanced EEHFR 2.0重新设计版本
    print("\n1️⃣ 测试Enhanced EEHFR 2.0重新设计版本")
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
    
    results['Enhanced EEHFR 2.0'] = {
        **eehfr2_results,
        'execution_time': eehfr2_time
    }
    
    # 2. 测试PEGASIS协议
    print("\n2️⃣ 测试PEGASIS协议")
    print("-" * 50)
    
    start_time = time.time()
    pegasis = PEGASISProtocol(base_config, energy_model)
    pegasis_results = pegasis.run_simulation(max_rounds=200)
    pegasis_time = time.time() - start_time
    
    results['PEGASIS'] = {
        **pegasis_results,
        'execution_time': pegasis_time
    }
    
    # 3. 测试LEACH协议
    print("\n3️⃣ 测试LEACH协议")
    print("-" * 50)
    
    start_time = time.time()
    leach = LEACHProtocol(base_config, energy_model)
    leach_results = leach.run_simulation(max_rounds=200)
    leach_time = time.time() - start_time
    
    results['LEACH'] = {
        **leach_results,
        'execution_time': leach_time
    }
    
    # 4. 测试HEED协议
    print("\n4️⃣ 测试HEED协议")
    print("-" * 50)
    
    start_time = time.time()
    heed = HEEDProtocolWrapper(base_config, energy_model)
    heed_results = heed.run_simulation(max_rounds=200)
    heed_time = time.time() - start_time
    
    results['HEED'] = {
        **heed_results,
        'execution_time': heed_time
    }
    
    # 输出对比结果
    print("\n📊 协议性能对比结果:")
    print("=" * 80)
    print(f"{'协议':<20} {'能效(packets/J)':<15} {'投递率':<10} {'生存时间':<10} {'执行时间(s)':<12}")
    print("-" * 80)
    
    for protocol_name, result in results.items():
        energy_efficiency = result.get('energy_efficiency', 0)
        pdr = result.get('packet_delivery_ratio', 0)
        lifetime = result.get('network_lifetime', 0)
        exec_time = result.get('execution_time', 0)
        
        print(f"{protocol_name:<20} {energy_efficiency:<15.2f} {pdr:<10.3f} {lifetime:<10} {exec_time:<12.2f}")
    
    # 计算性能提升
    if 'Enhanced EEHFR 2.0' in results and 'PEGASIS' in results:
        eehfr_efficiency = results['Enhanced EEHFR 2.0']['energy_efficiency']
        pegasis_efficiency = results['PEGASIS']['energy_efficiency']
        
        if pegasis_efficiency > 0:
            improvement = ((eehfr_efficiency - pegasis_efficiency) / pegasis_efficiency) * 100
            print(f"\n🎯 Enhanced EEHFR 2.0 vs PEGASIS 性能提升: {improvement:.2f}%")
        
        eehfr_pdr = results['Enhanced EEHFR 2.0']['packet_delivery_ratio']
        pegasis_pdr = results['PEGASIS']['packet_delivery_ratio']
        
        if pegasis_pdr > 0:
            pdr_improvement = ((eehfr_pdr - pegasis_pdr) / pegasis_pdr) * 100
            print(f"🎯 Enhanced EEHFR 2.0 vs PEGASIS 投递率提升: {pdr_improvement:.2f}%")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"enhanced_eehfr_2_0_redesigned_comparison_{timestamp}.json"
    filepath = os.path.join(os.path.dirname(__file__), '..', 'results', filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存到: {filename}")
    
    return results

if __name__ == "__main__":
    # 单独测试Enhanced EEHFR 2.0
    test_enhanced_eehfr_2_0_redesigned()
    
    # 运行对比测试
    run_comprehensive_comparison()
