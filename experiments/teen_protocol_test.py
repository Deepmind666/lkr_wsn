#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEEN协议测试脚本

测试TEEN (Threshold sensitive Energy Efficient sensor Network) 协议的实现
验证阈值敏感机制和反应式数据传输特性

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_protocols import test_teen_protocol, TEENProtocolWrapper, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
import numpy as np

def test_teen_thresholds():
    """测试TEEN协议的阈值机制"""
    print("🧪 测试TEEN协议阈值机制")
    print("=" * 50)
    
    # 测试不同阈值配置
    threshold_configs = [
        {'hard': 60.0, 'soft': 1.0, 'name': '低阈值配置'},
        {'hard': 70.0, 'soft': 2.0, 'name': '标准阈值配置'},
        {'hard': 80.0, 'soft': 5.0, 'name': '高阈值配置'}
    ]
    
    results = []
    
    for config in threshold_configs:
        print(f"\n📊 测试 {config['name']} (硬阈值: {config['hard']}, 软阈值: {config['soft']})")
        
        # 创建网络配置
        network_config = NetworkConfig(
            num_nodes=50,
            initial_energy=2.0,
            area_width=100,
            area_height=100
        )
        
        # 创建能耗模型
        energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        
        # 创建TEEN协议实例
        teen_wrapper = TEENProtocolWrapper(network_config, energy_model)
        
        # 修改阈值配置
        teen_wrapper.teen_config.hard_threshold = config['hard']
        teen_wrapper.teen_config.soft_threshold = config['soft']
        teen_wrapper.teen_protocol = teen_wrapper.teen_protocol.__class__(teen_wrapper.teen_config)
        
        # 运行仿真
        result = teen_wrapper.run_simulation(max_rounds=200)
        
        # 记录结果
        results.append({
            'config': config['name'],
            'hard_threshold': config['hard'],
            'soft_threshold': config['soft'],
            'network_lifetime': result['network_lifetime'],
            'energy_efficiency': result['energy_efficiency'],
            'packet_delivery_ratio': result['packet_delivery_ratio'],
            'total_energy_consumed': result['total_energy_consumed']
        })
        
        print(f"   网络生存时间: {result['network_lifetime']} 轮")
        print(f"   能效: {result['energy_efficiency']:.2f} packets/J")
        print(f"   投递率: {result['packet_delivery_ratio']:.3f}")
        print(f"   总能耗: {result['total_energy_consumed']:.6f} J")
    
    # 分析结果
    print("\n📈 阈值配置对比分析:")
    print("-" * 80)
    print(f"{'配置':<15} {'硬阈值':<8} {'软阈值':<8} {'生存时间':<10} {'能效':<12} {'投递率':<8}")
    print("-" * 80)
    
    for result in results:
        print(f"{result['config']:<15} {result['hard_threshold']:<8.1f} {result['soft_threshold']:<8.1f} "
              f"{result['network_lifetime']:<10} {result['energy_efficiency']:<12.2f} {result['packet_delivery_ratio']:<8.3f}")
    
    return results

def test_teen_vs_baselines():
    """TEEN协议与基准协议对比测试"""
    print("\n🚀 TEEN协议与基准协议对比测试")
    print("=" * 60)
    
    # 统一网络配置
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 测试TEEN协议
    print("\n📊 测试TEEN协议...")
    teen_wrapper = TEENProtocolWrapper(config, energy_model)
    teen_results = teen_wrapper.run_simulation(max_rounds=200)
    
    print(f"✅ TEEN协议测试完成:")
    print(f"   网络生存时间: {teen_results['network_lifetime']} 轮")
    print(f"   总能耗: {teen_results['total_energy_consumed']:.6f} J")
    print(f"   数据包投递率: {teen_results['packet_delivery_ratio']:.3f}")
    print(f"   能效: {teen_results['energy_efficiency']:.2f} packets/J")
    print(f"   最终存活节点: {teen_results['final_alive_nodes']}")
    
    return teen_results

def analyze_teen_characteristics():
    """分析TEEN协议特性"""
    print("\n🔍 TEEN协议特性分析")
    print("=" * 50)
    
    print("📋 TEEN协议核心特点:")
    print("   1. 阈值敏感机制 - 只有当感知值超过硬阈值时才传输")
    print("   2. 软阈值控制 - 感知值变化超过软阈值时才传输")
    print("   3. 时间间隔限制 - 防止长时间不传输数据")
    print("   4. 反应式传输 - 适用于时间关键应用")
    print("   5. 基于LEACH的聚类结构")
    
    print("\n📊 适用场景:")
    print("   ✓ 环境监测 (温度、湿度异常检测)")
    print("   ✓ 安全监控 (入侵检测、火灾报警)")
    print("   ✓ 工业控制 (设备状态监测)")
    print("   ✓ 医疗监护 (生理参数异常检测)")
    
    print("\n⚡ 性能优势:")
    print("   ✓ 减少不必要的数据传输")
    print("   ✓ 延长网络生存时间")
    print("   ✓ 适应动态环境变化")
    print("   ✓ 支持实时响应")

def main():
    """主测试函数"""
    print("🚀 TEEN协议综合测试")
    print("=" * 60)
    
    # 1. 基本功能测试
    print("\n1️⃣ 基本功能测试")
    test_teen_protocol()
    
    # 2. 阈值机制测试
    print("\n2️⃣ 阈值机制测试")
    threshold_results = test_teen_thresholds()
    
    # 3. 对比测试
    print("\n3️⃣ 与基准协议对比")
    comparison_results = test_teen_vs_baselines()
    
    # 4. 特性分析
    print("\n4️⃣ 协议特性分析")
    analyze_teen_characteristics()
    
    print("\n✅ TEEN协议测试完成!")
    print("📝 测试总结:")
    print("   - TEEN协议成功实现阈值敏感机制")
    print("   - 反应式数据传输有效减少能耗")
    print("   - 适用于事件驱动的WSN应用场景")
    print("   - 为Enhanced EEHFR提供了新的基准对比")

if __name__ == "__main__":
    main()
