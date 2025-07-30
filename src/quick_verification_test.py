#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速验证测试脚本

目的：验证修复后的实验框架是否真正具有随机性
检查PEGASIS协议在多次重复实验中是否产生不同结果

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0 (问题修复验证)
"""

import time
import random
import hashlib
from comprehensive_benchmark import ComprehensiveBenchmark, ExperimentConfig, create_quick_test_config
from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def test_randomness_fix():
    """测试随机性修复是否有效"""
    
    print("🔧 测试随机性修复效果")
    print("=" * 50)
    
    # 创建测试配置
    config = NetworkConfig(
        num_nodes=20,
        area_width=50,
        area_height=50,
        initial_energy=1.0
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 测试PEGASIS协议的随机性
    print("\n🧪 测试PEGASIS协议随机性:")
    pegasis_results = []
    
    for i in range(3):
        # 设置不同的随机种子
        experiment_id = f"pegasis_test_{i}"
        seed_string = f"{experiment_id}_{int(time.time() * 1000000)}"
        seed = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        print(f"   实验 {i+1}: 随机种子 {seed}")
        
        # 创建协议实例并运行
        pegasis = PEGASISProtocol(config, energy_model)
        result = pegasis.run_simulation(max_rounds=100)
        
        pegasis_results.append(result['total_energy_consumed'])
        print(f"   结果: 总能耗 {result['total_energy_consumed']:.6f} J")
    
    # 检查结果是否不同
    print(f"\n📊 PEGASIS结果分析:")
    print(f"   结果1: {pegasis_results[0]:.6f} J")
    print(f"   结果2: {pegasis_results[1]:.6f} J") 
    print(f"   结果3: {pegasis_results[2]:.6f} J")
    
    # 计算标准差
    import statistics
    if len(pegasis_results) > 1:
        std_dev = statistics.stdev(pegasis_results)
        print(f"   标准差: {std_dev:.6f}")
        
        if std_dev > 0:
            print("   ✅ 随机性修复成功！结果有变化")
        else:
            print("   ❌ 随机性修复失败！结果仍然相同")
    
    # 测试LEACH协议作为对比
    print("\n🧪 测试LEACH协议随机性:")
    leach_results = []
    
    for i in range(3):
        # 设置不同的随机种子
        experiment_id = f"leach_test_{i}"
        seed_string = f"{experiment_id}_{int(time.time() * 1000000)}"
        seed = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        print(f"   实验 {i+1}: 随机种子 {seed}")
        
        # 创建协议实例并运行
        leach = LEACHProtocol(config, energy_model)
        result = leach.run_simulation(max_rounds=100)
        
        leach_results.append(result['total_energy_consumed'])
        print(f"   结果: 总能耗 {result['total_energy_consumed']:.6f} J")
    
    # 检查LEACH结果
    print(f"\n📊 LEACH结果分析:")
    print(f"   结果1: {leach_results[0]:.6f} J")
    print(f"   结果2: {leach_results[1]:.6f} J")
    print(f"   结果3: {leach_results[2]:.6f} J")
    
    if len(leach_results) > 1:
        std_dev = statistics.stdev(leach_results)
        print(f"   标准差: {std_dev:.6f}")

def test_comprehensive_framework():
    """测试修复后的综合框架"""
    
    print("\n🚀 测试修复后的综合基准测试框架")
    print("=" * 60)
    
    # 创建快速测试配置
    experiment_config = create_quick_test_config()
    
    print(f"测试配置:")
    print(f"   节点数: {experiment_config.node_counts}")
    print(f"   区域大小: {experiment_config.area_sizes}")
    print(f"   初始能量: {experiment_config.initial_energies}")
    print(f"   最大轮数: {experiment_config.max_rounds}")
    print(f"   重复次数: {experiment_config.repeat_times}")
    
    # 创建基准测试实例
    benchmark = ComprehensiveBenchmark(experiment_config)
    
    # 运行测试
    results = benchmark.run_comprehensive_benchmark()
    
    # 分析结果
    print("\n📊 修复后的结果分析:")
    for config_name, config_results in results.items():
        print(f"\n实验配置: {config_name}")
        
        for protocol_name, protocol_data in config_results.items():
            stats = protocol_data['statistics']
            print(f"   {protocol_name}:")
            print(f"      能耗: {stats['total_energy_consumed']['mean']:.3f}±{stats['total_energy_consumed']['std']:.3f} J")
            print(f"      能效: {stats['energy_efficiency']['mean']:.1f}±{stats['energy_efficiency']['std']:.1f} packets/J")
            print(f"      投递率: {stats['packet_delivery_ratio']['mean']:.3f}±{stats['packet_delivery_ratio']['std']:.3f}")
            
            # 检查标准差是否为0
            if stats['total_energy_consumed']['std'] == 0:
                print(f"      ⚠️  警告: {protocol_name}的能耗标准差为0，可能仍有问题")
            else:
                print(f"      ✅ {protocol_name}的结果有合理变化")

def main():
    """主函数"""
    
    print("🔍 Enhanced EEHFR 项目诚实验证测试")
    print("=" * 60)
    print("目的: 验证修复后的实验框架是否真正解决了随机性问题")
    print("时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # 1. 测试随机性修复
    test_randomness_fix()
    
    # 2. 测试综合框架
    test_comprehensive_framework()
    
    print("\n" + "=" * 60)
    print("🎯 验证测试完成")
    print("请检查上述结果，确认随机性问题是否已解决")
    print("如果PEGASIS和LEACH的标准差都大于0，说明修复成功")

if __name__ == "__main__":
    main()
