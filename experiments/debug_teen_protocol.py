#!/usr/bin/env python3
"""
TEEN协议深度调试脚本
分析0%投递率的根本原因并修复
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from teen_protocol import TEENProtocol, TEENConfig, TEENNode
from benchmark_protocols import TEENProtocolWrapper, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
import random
import matplotlib.pyplot as plt

def analyze_sensor_values():
    """分析传感器感知值分布"""
    print("🔍 分析传感器感知值分布...")
    
    # 创建测试节点
    test_node = TEENNode(
        id=0, x=50, y=50, 
        initial_energy=2.0, current_energy=2.0,
        hard_threshold=70.0, soft_threshold=2.0
    )
    
    # 生成1000个感知值样本
    sensor_values = []
    for _ in range(1000):
        value = test_node.sense_environment()
        sensor_values.append(value)
    
    sensor_values = np.array(sensor_values)
    
    print(f"📊 感知值统计:")
    print(f"   最小值: {sensor_values.min():.2f}")
    print(f"   最大值: {sensor_values.max():.2f}")
    print(f"   平均值: {sensor_values.mean():.2f}")
    print(f"   标准差: {sensor_values.std():.2f}")
    print(f"   超过硬阈值70.0的比例: {(sensor_values > 70.0).mean()*100:.1f}%")
    print(f"   超过硬阈值60.0的比例: {(sensor_values > 60.0).mean()*100:.1f}%")
    print(f"   超过硬阈值50.0的比例: {(sensor_values > 50.0).mean()*100:.1f}%")
    
    return sensor_values

def test_transmission_conditions():
    """测试传输条件触发情况"""
    print("\n🧪 测试传输条件触发情况...")
    
    # 测试不同阈值配置
    configs = [
        {"hard": 70.0, "soft": 2.0, "name": "原始配置"},
        {"hard": 60.0, "soft": 2.0, "name": "降低硬阈值"},
        {"hard": 50.0, "soft": 2.0, "name": "进一步降低硬阈值"},
        {"hard": 60.0, "soft": 1.0, "name": "降低软阈值"},
        {"hard": 50.0, "soft": 1.0, "name": "双重降低"},
    ]
    
    for config in configs:
        print(f"\n📋 测试配置: {config['name']}")
        print(f"   硬阈值: {config['hard']}, 软阈值: {config['soft']}")
        
        # 创建测试节点
        test_node = TEENNode(
            id=0, x=50, y=50,
            initial_energy=2.0, current_energy=2.0,
            hard_threshold=config['hard'], 
            soft_threshold=config['soft']
        )
        
        # 模拟50轮传输决策
        transmissions = 0
        for round_num in range(1, 51):
            if test_node.should_transmit(round_num, 10):
                transmissions += 1
        
        transmission_rate = transmissions / 50 * 100
        print(f"   50轮中传输次数: {transmissions}")
        print(f"   传输率: {transmission_rate:.1f}%")

def debug_teen_wrapper():
    """调试TEEN包装类"""
    print("\n🔧 调试TEEN包装类...")
    
    # 创建网络配置
    config = NetworkConfig(
        num_nodes=20,  # 减少节点数便于调试
        area_width=100,
        area_height=100,
        base_station_x=50,
        base_station_y=175,
        initial_energy=2.0,
        packet_size=4000
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 创建TEEN包装类，使用优化的阈值
    teen_wrapper = TEENProtocolWrapper(config, energy_model)
    teen_wrapper.teen_config.hard_threshold = 50.0  # 降低硬阈值
    teen_wrapper.teen_config.soft_threshold = 1.0   # 降低软阈值
    teen_wrapper.teen_config.max_time_interval = 5  # 缩短强制传输间隔
    
    # 重新创建协议实例
    teen_wrapper.teen_protocol = TEENProtocol(teen_wrapper.teen_config)
    
    print(f"📊 优化后的TEEN配置:")
    print(f"   硬阈值: {teen_wrapper.teen_config.hard_threshold}")
    print(f"   软阈值: {teen_wrapper.teen_config.soft_threshold}")
    print(f"   最大时间间隔: {teen_wrapper.teen_config.max_time_interval}")
    
    # 运行短期仿真
    print(f"\n🚀 运行优化后的TEEN仿真...")
    result = teen_wrapper.run_simulation(max_rounds=50)
    
    print(f"✅ 仿真结果:")
    print(f"   网络生存时间: {result['network_lifetime']} 轮")
    print(f"   发送数据包: {result['packets_transmitted']}")
    print(f"   接收数据包: {result['packets_received']}")
    print(f"   投递率: {result['packet_delivery_ratio']:.3f}")
    print(f"   能效: {result['energy_efficiency']:.2f} packets/J")
    print(f"   总能耗: {result['total_energy_consumed']:.6f} J")
    
    return result

def create_fixed_teen_protocol():
    """创建修复后的TEEN协议"""
    print("\n🛠️ 创建修复后的TEEN协议...")
    
    # 优化的配置参数
    config = TEENConfig(
        num_nodes=50,
        area_width=100,
        area_height=100,
        base_station_x=50,
        base_station_y=175,
        initial_energy=2.0,
        transmission_range=30.0,
        packet_size=1024,
        hard_threshold=45.0,    # 大幅降低硬阈值，确保更多数据被传输
        soft_threshold=0.5,     # 大幅降低软阈值，增加传输敏感性
        max_time_interval=3,    # 缩短强制传输间隔
        cluster_head_percentage=0.08,  # 增加簇头比例
        min_sensor_value=20.0,
        max_sensor_value=100.0
    )
    
    print(f"📋 修复后的TEEN配置:")
    print(f"   硬阈值: {config.hard_threshold} (原70.0)")
    print(f"   软阈值: {config.soft_threshold} (原2.0)")
    print(f"   最大时间间隔: {config.max_time_interval} (原10)")
    print(f"   簇头比例: {config.cluster_head_percentage} (原0.05)")
    
    return config

def run_comprehensive_teen_test():
    """运行全面的TEEN协议测试"""
    print("\n🎯 运行全面的TEEN协议测试...")
    
    # 创建修复后的配置
    fixed_config = create_fixed_teen_protocol()
    
    # 创建网络配置
    network_config = NetworkConfig(
        num_nodes=fixed_config.num_nodes,
        area_width=fixed_config.area_width,
        area_height=fixed_config.area_height,
        base_station_x=fixed_config.base_station_x,
        base_station_y=fixed_config.base_station_y,
        initial_energy=fixed_config.initial_energy,
        packet_size=4000  # 使用标准包大小
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 创建修复后的TEEN包装类
    teen_wrapper = TEENProtocolWrapper(network_config, energy_model)
    teen_wrapper.teen_config = fixed_config
    teen_wrapper.teen_protocol = TEENProtocol(fixed_config)
    
    # 运行完整仿真
    print(f"🚀 运行修复后的TEEN完整仿真...")
    result = teen_wrapper.run_simulation(max_rounds=200)
    
    print(f"\n📊 修复后的TEEN性能:")
    print(f"   网络生存时间: {result['network_lifetime']} 轮")
    print(f"   发送数据包: {result['packets_transmitted']}")
    print(f"   接收数据包: {result['packets_received']}")
    print(f"   投递率: {result['packet_delivery_ratio']:.3f}")
    print(f"   能效: {result['energy_efficiency']:.2f} packets/J")
    print(f"   总能耗: {result['total_energy_consumed']:.6f} J")
    print(f"   最终存活节点: {result['final_alive_nodes']}")
    
    return result

def main():
    """主函数"""
    print("🚀 TEEN协议深度调试开始")
    print("=" * 60)
    
    # 1. 分析感知值分布
    sensor_values = analyze_sensor_values()
    
    # 2. 测试传输条件
    test_transmission_conditions()
    
    # 3. 调试包装类
    debug_result = debug_teen_wrapper()
    
    # 4. 运行修复后的完整测试
    final_result = run_comprehensive_teen_test()
    
    print(f"\n🎉 TEEN协议调试完成!")
    print(f"📈 性能改进对比:")
    print(f"   修复前投递率: 0.000")
    print(f"   修复后投递率: {final_result['packet_delivery_ratio']:.3f}")
    print(f"   修复前能效: 0.00 packets/J")
    print(f"   修复后能效: {final_result['energy_efficiency']:.2f} packets/J")

if __name__ == "__main__":
    main()
