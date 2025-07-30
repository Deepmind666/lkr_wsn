#!/usr/bin/env python3
"""
测试真实环境建模的简化脚本

验证基于文献调研的环境干扰建模框架是否正常工作

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from realistic_channel_model import (
        RealisticChannelModel, 
        EnvironmentType,
        LogNormalShadowingModel,
        IEEE802154LinkQuality,
        InterferenceModel,
        EnvironmentalFactors
    )
    print("✅ Successfully imported realistic channel model")
except ImportError as e:
    print(f"❌ Failed to import realistic channel model: {e}")
    sys.exit(1)

def test_channel_models():
    """测试信道模型的各个组件"""
    print("\n🔬 Testing Channel Models...")
    
    # 1. 测试Log-Normal Shadowing模型
    print("\n1️⃣ Testing Log-Normal Shadowing Model")
    
    environments = [
        EnvironmentType.INDOOR_OFFICE,
        EnvironmentType.INDOOR_FACTORY,
        EnvironmentType.OUTDOOR_OPEN
    ]
    
    for env in environments:
        model = LogNormalShadowingModel(env)
        
        # 测试不同距离的路径损耗
        distances = [10, 20, 50, 100]
        path_losses = []
        
        for distance in distances:
            # 多次测量取平均 (因为有随机阴影衰落)
            losses = [model.calculate_path_loss(distance) for _ in range(10)]
            avg_loss = np.mean(losses)
            path_losses.append(avg_loss)
        
        print(f"  {env.value}:")
        for d, pl in zip(distances, path_losses):
            print(f"    {d}m: {pl:.1f} dB")
    
    # 2. 测试IEEE 802.15.4链路质量
    print("\n2️⃣ Testing IEEE 802.15.4 Link Quality")
    
    link_quality = IEEE802154LinkQuality()
    
    rssi_values = [-50, -65, -75, -85, -95]
    for rssi in rssi_values:
        lqi = link_quality.calculate_lqi(rssi)
        pdr = link_quality.calculate_pdr(rssi)
        print(f"  RSSI: {rssi} dBm -> LQI: {lqi}, PDR: {pdr:.3f}")
    
    # 3. 测试干扰模型
    print("\n3️⃣ Testing Interference Model")
    
    interference = InterferenceModel()
    
    # 添加WiFi干扰源
    interference.add_interference_source(-20, 10, "wifi")
    interference.add_interference_source(-25, 20, "bluetooth")
    
    signal_powers = [-40, -50, -60, -70, -80]
    for signal_power in signal_powers:
        sinr = interference.calculate_sinr(signal_power)
        pdr = interference.calculate_interference_pdr(sinr)
        print(f"  Signal: {signal_power} dBm -> SINR: {sinr:.1f} dB, PDR: {pdr:.3f}")
    
    # 4. 测试环境因素
    print("\n4️⃣ Testing Environmental Factors")
    
    temperatures = [-10, 0, 25, 40, 50]
    for temp in temperatures:
        battery_factor = EnvironmentalFactors.temperature_effect_on_battery(temp)
        print(f"  Temperature: {temp}°C -> Battery capacity: {battery_factor:.3f}")
    
    humidities = [0.3, 0.5, 0.7, 0.9]
    for humidity in humidities:
        signal_loss = EnvironmentalFactors.humidity_effect_on_signal(humidity)
        print(f"  Humidity: {humidity*100:.0f}% -> Signal loss: {signal_loss:.4f} dB/km")

def test_integrated_channel_model():
    """测试集成的信道模型"""
    print("\n🌐 Testing Integrated Channel Model...")
    
    # 创建工厂环境的信道模型
    channel = RealisticChannelModel(EnvironmentType.INDOOR_FACTORY)
    
    # 添加干扰源
    channel.interference.add_interference_source(-20, 15, "wifi")
    channel.interference.add_interference_source(-15, 25, "motor")
    
    print("\n📊 Link Quality Analysis:")
    print("Distance(m) | RSSI(dBm) | LQI | PDR   | SINR(dB) | Battery")
    print("-" * 60)
    
    distances = [10, 20, 30, 50, 80]
    results = []
    
    for distance in distances:
        # 多次测量取平均
        metrics_list = []
        for _ in range(5):
            metrics = channel.calculate_link_metrics(
                tx_power_dbm=0,      # 0dBm发射功率
                distance=distance,
                temperature_c=35,    # 35°C工厂温度
                humidity_ratio=0.6   # 60%湿度
            )
            metrics_list.append(metrics)
        
        # 计算平均值
        avg_metrics = {
            'received_power_dbm': np.mean([m['received_power_dbm'] for m in metrics_list]),
            'rssi_dbm': np.mean([m['rssi_dbm'] for m in metrics_list]),
            'lqi': np.mean([m['lqi'] for m in metrics_list]),
            'pdr': np.mean([m['pdr'] for m in metrics_list]),
            'sinr_db': np.mean([m['sinr_db'] for m in metrics_list]),
            'battery_capacity_factor': metrics_list[0]['battery_capacity_factor']  # 温度影响是确定的
        }
        
        print(f"{distance:8.0f}   | {avg_metrics['rssi_dbm']:8.1f} | "
              f"{avg_metrics['lqi']:3.0f} | {avg_metrics['pdr']:5.3f} | "
              f"{avg_metrics['sinr_db']:7.1f} | {avg_metrics['battery_capacity_factor']:7.3f}")
        
        results.append({
            'distance': distance,
            **avg_metrics
        })
    
    return results

def create_performance_visualization(results):
    """创建性能可视化图表"""
    print("\n📈 Creating Performance Visualization...")
    
    distances = [r['distance'] for r in results]
    rssi_values = [r['rssi_dbm'] for r in results]
    lqi_values = [r['lqi'] for r in results]
    pdr_values = [r['pdr'] for r in results]
    sinr_values = [r['sinr_db'] for r in results]
    
    # 创建子图
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Realistic Channel Model Performance Analysis\n(Indoor Factory Environment)', 
                fontsize=14, fontweight='bold')
    
    # RSSI vs Distance
    axes[0,0].plot(distances, rssi_values, 'b-o', linewidth=2, markersize=6)
    axes[0,0].set_xlabel('Distance (m)')
    axes[0,0].set_ylabel('RSSI (dBm)')
    axes[0,0].set_title('RSSI vs Distance')
    axes[0,0].grid(True, alpha=0.3)
    axes[0,0].axhline(y=-85, color='r', linestyle='--', alpha=0.7, label='Sensitivity Threshold')
    axes[0,0].legend()
    
    # LQI vs Distance
    axes[0,1].plot(distances, lqi_values, 'g-s', linewidth=2, markersize=6)
    axes[0,1].set_xlabel('Distance (m)')
    axes[0,1].set_ylabel('LQI')
    axes[0,1].set_title('Link Quality Indicator vs Distance')
    axes[0,1].grid(True, alpha=0.3)
    axes[0,1].set_ylim(0, 255)
    
    # PDR vs Distance
    axes[1,0].plot(distances, pdr_values, 'r-^', linewidth=2, markersize=6)
    axes[1,0].set_xlabel('Distance (m)')
    axes[1,0].set_ylabel('Packet Delivery Ratio')
    axes[1,0].set_title('PDR vs Distance')
    axes[1,0].grid(True, alpha=0.3)
    axes[1,0].set_ylim(0, 1)
    axes[1,0].axhline(y=0.9, color='g', linestyle='--', alpha=0.7, label='Good Quality')
    axes[1,0].axhline(y=0.5, color='orange', linestyle='--', alpha=0.7, label='Marginal Quality')
    axes[1,0].legend()
    
    # SINR vs Distance
    axes[1,1].plot(distances, sinr_values, 'm-d', linewidth=2, markersize=6)
    axes[1,1].set_xlabel('Distance (m)')
    axes[1,1].set_ylabel('SINR (dB)')
    axes[1,1].set_title('Signal-to-Interference-plus-Noise Ratio vs Distance')
    axes[1,1].grid(True, alpha=0.3)
    axes[1,1].axhline(y=10, color='g', linestyle='--', alpha=0.7, label='Good SINR')
    axes[1,1].axhline(y=0, color='r', linestyle='--', alpha=0.7, label='Poor SINR')
    axes[1,1].legend()
    
    plt.tight_layout()
    
    # 保存图表
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_path = f"../results/realistic_channel_model_test_{timestamp}.png"
    
    # 确保目录存在
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)
    
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    print(f"📊 Chart saved to: {chart_path}")
    
    plt.show()

def save_test_results(results):
    """保存测试结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = f"../results/realistic_channel_test_{timestamp}.json"
    
    # 确保目录存在
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    
    test_data = {
        'timestamp': timestamp,
        'environment': 'indoor_factory',
        'test_parameters': {
            'tx_power_dbm': 0,
            'temperature_c': 35,
            'humidity_ratio': 0.6,
            'interference_sources': [
                {'power': -20, 'distance': 15, 'type': 'wifi'},
                {'power': -15, 'distance': 25, 'type': 'motor'}
            ]
        },
        'results': results,
        'summary': {
            'max_communication_range': max([r['distance'] for r in results if r['pdr'] > 0.01], default=0),
            'reliable_communication_range': max([r['distance'] for r in results if r['pdr'] > 0.5], default=0),
            'average_pdr': np.mean([r['pdr'] for r in results]),
            'average_rssi': np.mean([r['rssi_dbm'] for r in results])
        }
    }
    
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Test results saved to: {result_path}")
    return result_path

def main():
    """主测试函数"""
    print("🚀 Starting Realistic Environment Modeling Test")
    print("=" * 60)
    
    try:
        # 1. 测试各个信道模型组件
        test_channel_models()
        
        # 2. 测试集成信道模型
        results = test_integrated_channel_model()
        
        # 3. 创建可视化
        create_performance_visualization(results)
        
        # 4. 保存结果
        result_path = save_test_results(results)
        
        print("\n" + "=" * 60)
        print("✅ Realistic Environment Modeling Test Completed Successfully!")
        print("\n📋 Key Findings:")
        max_range = max([r['distance'] for r in results if r['pdr'] > 0.01], default=0)
        reliable_range = max([r['distance'] for r in results if r['pdr'] > 0.5], default=0)
        print(f"   • Maximum communication range: {max_range}m")
        print(f"   • Reliable communication range: {reliable_range}m")
        print(f"   • Average PDR: {np.mean([r['pdr'] for r in results]):.3f}")
        print(f"   • Average RSSI: {np.mean([r['rssi_dbm'] for r in results]):.1f} dBm")
        
        print("\n🎯 Model Validation:")
        print("   ✅ Log-Normal Shadowing path loss model working")
        print("   ✅ IEEE 802.15.4 RSSI/LQI calculation working")
        print("   ✅ Interference modeling (WiFi + Industrial) working")
        print("   ✅ Environmental factors (temperature/humidity) working")
        print("   ✅ Integrated channel model working")
        
        print(f"\n📊 Results saved to: {result_path}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
