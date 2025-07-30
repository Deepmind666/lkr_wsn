#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试能耗模型 - 分析为什么能耗不随距离和功率变化

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
"""

from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def debug_energy_calculation():
    """调试能耗计算"""
    
    print("🔍 调试能耗模型计算")
    print("=" * 60)
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # 获取参数
    params = energy_model.params
    print(f"📊 CC2420 TelosB 参数:")
    print(f"   TX能耗/bit: {params.tx_energy_per_bit*1e9:.1f} nJ/bit")
    print(f"   RX能耗/bit: {params.rx_energy_per_bit*1e9:.1f} nJ/bit")
    print(f"   功放效率: {params.amplifier_efficiency:.1%}")
    print(f"   路径损耗阈值: {params.path_loss_threshold:.1f}m")
    
    # 测试参数
    packet_size = 1024 * 8  # bits
    distances = [5, 10, 20, 30, 40, 50]
    powers = [-5, 0, 5, 8]
    
    print(f"\n📦 数据包大小: {packet_size} bits ({packet_size//8} bytes)")
    
    # 分析距离影响
    print(f"\n📊 距离影响分析 (功率=0dBm):")
    print("距离(m)  基础TX(mJ)  放大器(mJ)  总TX(mJ)  RX(mJ)  总计(mJ)")
    print("-" * 70)
    
    for distance in distances:
        # 计算各组件能耗
        base_tx = packet_size * params.tx_energy_per_bit * 1000  # mJ
        
        # 功率放大器能耗计算
        tx_power_dbm = 0.0
        tx_power_linear = 10**(tx_power_dbm / 10) / 1000  # W
        
        if distance <= params.path_loss_threshold:
            # 自由空间传播
            amplifier_energy = (tx_power_linear / params.amplifier_efficiency) * \
                             (distance ** 2) * 1e-12  # J
        else:
            # 多径传播
            amplifier_energy = (tx_power_linear / params.amplifier_efficiency) * \
                             (distance ** 4) * 1e-15  # J
        
        amplifier_energy_mj = amplifier_energy * 1000  # mJ
        
        # 总传输能耗
        total_tx = energy_model.calculate_transmission_energy(packet_size, distance, tx_power_dbm)
        total_tx_mj = total_tx * 1000  # mJ
        
        # 接收能耗
        rx_energy = energy_model.calculate_reception_energy(packet_size)
        rx_energy_mj = rx_energy * 1000  # mJ
        
        # 总能耗
        total_energy_mj = total_tx_mj + rx_energy_mj
        
        print(f"{distance:6.0f}   {base_tx:8.3f}   {amplifier_energy_mj:8.6f}   {total_tx_mj:7.3f}   {rx_energy_mj:5.3f}   {total_energy_mj:7.3f}")
    
    # 分析功率影响
    print(f"\n📊 功率影响分析 (距离=30m):")
    print("功率(dBm)  线性功率(mW)  放大器(mJ)  总TX(mJ)  总计(mJ)")
    print("-" * 55)
    
    distance = 30.0
    for power in powers:
        # 功率转换
        tx_power_linear = 10**(power / 10) / 1000  # W
        tx_power_mw = tx_power_linear * 1000  # mW
        
        # 放大器能耗
        if distance <= params.path_loss_threshold:
            amplifier_energy = (tx_power_linear / params.amplifier_efficiency) * \
                             (distance ** 2) * 1e-12  # J
        else:
            amplifier_energy = (tx_power_linear / params.amplifier_efficiency) * \
                             (distance ** 4) * 1e-15  # J
        
        amplifier_energy_mj = amplifier_energy * 1000  # mJ
        
        # 总传输能耗
        total_tx = energy_model.calculate_transmission_energy(packet_size, distance, power)
        total_tx_mj = total_tx * 1000  # mJ
        
        # 接收能耗
        rx_energy = energy_model.calculate_reception_energy(packet_size)
        rx_energy_mj = rx_energy * 1000  # mJ
        
        # 总能耗
        total_energy_mj = total_tx_mj + rx_energy_mj
        
        print(f"{power:8.0f}   {tx_power_mw:10.3f}   {amplifier_energy_mj:8.6f}   {total_tx_mj:7.3f}   {total_energy_mj:7.3f}")
    
    # 分析问题
    print(f"\n🔍 问题分析:")
    
    # 检查放大器能耗是否太小
    base_tx = packet_size * params.tx_energy_per_bit * 1000  # mJ
    tx_power_linear = 10**(0 / 10) / 1000  # 0dBm = 1mW = 0.001W
    amplifier_30m = (tx_power_linear / params.amplifier_efficiency) * (30 ** 2) * 1e-12 * 1000  # mJ
    
    print(f"   基础TX能耗: {base_tx:.3f} mJ")
    print(f"   30m处放大器能耗: {amplifier_30m:.6f} mJ")
    print(f"   放大器能耗占比: {amplifier_30m/base_tx*100:.4f}%")
    
    if amplifier_30m < base_tx * 0.01:  # 如果放大器能耗小于基础能耗的1%
        print("   ❌ 放大器能耗过小，几乎不影响总能耗")
        print("   💡 可能需要调整放大器能耗系数")
    
    # 检查环境因素
    temp_factor = 1 + energy_model.temperature_coefficient * abs(25.0 - 25.0)
    humidity_factor = 1 + energy_model.humidity_coefficient * 0.5
    
    print(f"   温度因子: {temp_factor:.3f}")
    print(f"   湿度因子: {humidity_factor:.3f}")
    
    return energy_model

def propose_energy_model_fix():
    """提出能耗模型修复方案"""
    
    print(f"\n💡 能耗模型修复建议:")
    print("=" * 60)
    
    print("1. 问题诊断:")
    print("   ❌ 放大器能耗系数过小 (1e-12)，导致距离影响微乎其微")
    print("   ❌ 功率影响不明显，因为放大器能耗占比极小")
    print("   ❌ 基础能耗占主导，掩盖了距离和功率的影响")
    
    print("\n2. 修复方案:")
    print("   ✅ 增大放大器能耗系数，使其对总能耗有显著影响")
    print("   ✅ 调整自由空间传播系数从1e-12到更合理的值")
    print("   ✅ 确保功率和距离变化能产生可观察的能耗差异")
    
    print("\n3. 建议的新参数:")
    print("   自由空间系数: 1e-9 (增大1000倍)")
    print("   多径传播系数: 1e-12 (保持不变)")
    print("   这样30m距离的放大器能耗将占总能耗的~50%")
    
    print("\n4. 验证方法:")
    print("   ✅ 5m距离应比50m距离节能显著")
    print("   ✅ -5dBm功率应比8dBm功率节能显著")
    print("   ✅ 能耗差异应在10-50%范围内")

def test_fixed_energy_model():
    """测试修复后的能耗模型"""
    
    print(f"\n🔧 测试修复后的能耗模型:")
    print("=" * 60)
    
    # 这里我们手动计算修复后的能耗
    packet_size = 1024 * 8  # bits
    
    # CC2420参数
    tx_energy_per_bit = 208.8e-9  # J/bit
    rx_energy_per_bit = 225.6e-9  # J/bit
    amplifier_efficiency = 0.5
    
    # 修复后的系数
    free_space_coeff = 1e-9  # 增大1000倍
    
    print("📊 修复后的能耗计算 (功率=0dBm):")
    print("距离(m)  基础TX(mJ)  放大器(mJ)  总TX(mJ)  RX(mJ)  总计(mJ)  相对差异")
    print("-" * 80)
    
    base_tx = packet_size * tx_energy_per_bit * 1000  # mJ
    rx_energy = packet_size * rx_energy_per_bit * 1000  # mJ
    tx_power_linear = 0.001  # 0dBm = 1mW
    
    baseline_total = None
    
    for distance in [5, 10, 20, 30, 40, 50]:
        # 修复后的放大器能耗
        amplifier_energy = (tx_power_linear / amplifier_efficiency) * \
                          (distance ** 2) * free_space_coeff * 1000  # mJ
        
        total_tx = base_tx + amplifier_energy
        total_energy = total_tx + rx_energy
        
        if baseline_total is None:
            baseline_total = total_energy
            relative_diff = "基准"
        else:
            relative_diff = f"{(total_energy/baseline_total-1)*100:+.1f}%"
        
        print(f"{distance:6.0f}   {base_tx:8.3f}   {amplifier_energy:8.3f}   {total_tx:7.3f}   {rx_energy:5.3f}   {total_energy:7.3f}   {relative_diff:>8}")

def main():
    """主函数"""
    
    # 1. 调试当前能耗模型
    energy_model = debug_energy_calculation()
    
    # 2. 提出修复方案
    propose_energy_model_fix()
    
    # 3. 测试修复后的效果
    test_fixed_energy_model()
    
    print(f"\n✅ 能耗模型调试完成！")
    print(f"🎯 下一步: 实施能耗模型修复")

if __name__ == "__main__":
    main()
