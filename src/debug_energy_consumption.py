#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试能耗异常问题

目的：找出为什么Enhanced EEHFR的能耗比LEACH/PEGASIS低这么多
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def debug_single_round():
    """调试单轮能耗 - 详细分析每个协议的能耗计算"""

    print("🔍 详细调试单轮能耗消耗")
    print("=" * 50)

    # 创建相同的网络配置
    config = NetworkConfig(
        num_nodes=5,  # 减少节点数便于详细调试
        area_width=50,
        area_height=50,
        initial_energy=1.0,
        packet_size=1024,
        base_station_x=25,
        base_station_y=25
    )

    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    # 详细调试Enhanced EEHFR
    print(f"\n🔬 详细调试 Enhanced EEHFR:")
    try:
        eehfr = IntegratedEnhancedEEHFRProtocol(config)

        # 记录初始状态
        initial_energy = sum(node.current_energy for node in eehfr.nodes)
        print(f"   初始总能量: {initial_energy:.6f} J")

        # 打印节点位置
        print(f"   节点位置:")
        for i, node in enumerate(eehfr.nodes):
            print(f"     节点{i}: ({node.x:.1f}, {node.y:.1f}), 能量: {node.current_energy:.3f}J")

        # 执行簇头选择
        eehfr._select_cluster_heads()
        cluster_heads = [node for node in eehfr.nodes if node.is_cluster_head]
        print(f"   选择的簇头: {[node.id for node in cluster_heads]}")

        # 执行簇形成
        eehfr._form_clusters()

        # 详细分析数据传输
        print(f"   详细数据传输分析:")
        packets_sent = 0
        packets_received = 0
        total_energy_consumed = 0.0

        for ch in cluster_heads:
            cluster_members = [node for node in eehfr.nodes
                             if node.cluster_id == ch.cluster_id and not node.is_cluster_head and node.is_alive]
            print(f"     簇头{ch.id}的成员: {[m.id for m in cluster_members]}")

            # 成员向簇头传输
            for member in cluster_members:
                distance = ((member.x - ch.x)**2 + (member.y - ch.y)**2)**0.5
                tx_energy = eehfr.energy_model.calculate_transmission_energy(
                    config.packet_size, distance, member.transmission_power
                )
                rx_energy = eehfr.energy_model.calculate_reception_energy(config.packet_size)

                print(f"       成员{member.id}->簇头{ch.id}: 距离{distance:.1f}m, "
                      f"发射{tx_energy*1000:.3f}mJ, 接收{rx_energy*1000:.3f}mJ, "
                      f"功率{member.transmission_power}dBm")

                total_energy_consumed += tx_energy + rx_energy
                packets_sent += 1
                packets_received += 1  # 假设100%成功率用于调试

            # 簇头向基站传输
            distance_to_bs = ((ch.x - config.base_station_x)**2 + (ch.y - config.base_station_y)**2)**0.5
            tx_energy_bs = eehfr.energy_model.calculate_transmission_energy(
                config.packet_size, distance_to_bs, ch.transmission_power
            )

            print(f"       簇头{ch.id}->基站: 距离{distance_to_bs:.1f}m, "
                  f"发射{tx_energy_bs*1000:.3f}mJ, 功率{ch.transmission_power}dBm")

            total_energy_consumed += tx_energy_bs
            packets_sent += 1

        print(f"   手动计算总能耗: {total_energy_consumed*1000:.3f} mJ")
        print(f"   手动计算发送包数: {packets_sent}")

        # 执行实际的数据传输
        actual_packets_sent, actual_packets_received, actual_energy = eehfr._perform_data_transmission()

        print(f"   实际函数返回:")
        print(f"     发送包数: {actual_packets_sent}")
        print(f"     接收包数: {actual_packets_received}")
        print(f"     能耗: {actual_energy*1000:.3f} mJ")

        # 检查差异
        energy_diff = abs(total_energy_consumed - actual_energy)
        if energy_diff > 1e-6:
            print(f"   ⚠️ 能耗计算差异: {energy_diff*1000:.3f} mJ")

        final_energy = sum(node.current_energy for node in eehfr.nodes)
        actual_consumed = initial_energy - final_energy
        print(f"   实际消耗能量: {actual_consumed*1000:.3f} mJ")

    except Exception as e:
        print(f"   ❌ Enhanced EEHFR 调试失败: {e}")
        import traceback
        traceback.print_exc()

    # 对比调试LEACH
    print(f"\n🔬 对比调试 LEACH:")
    try:
        leach = LEACHProtocol(config, energy_model)

        initial_energy = sum(node.current_energy for node in leach.nodes)
        print(f"   初始总能量: {initial_energy:.6f} J")

        # 执行一轮
        result = leach.run_simulation(max_rounds=1)

        final_energy = sum(node.current_energy for node in leach.nodes)
        actual_consumed = initial_energy - final_energy

        print(f"   LEACH报告能耗: {result['total_energy_consumed']*1000:.3f} mJ")
        print(f"   实际消耗能量: {actual_consumed*1000:.3f} mJ")
        print(f"   发送包数: {leach.stats['packets_transmitted']}")
        print(f"   接收包数: {leach.stats['packets_received']}")

    except Exception as e:
        print(f"   ❌ LEACH 调试失败: {e}")
        import traceback
        traceback.print_exc()

def debug_energy_model():
    """调试能耗模型"""
    
    print(f"\n🔋 调试能耗模型")
    print("=" * 40)
    
    try:
        energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        
        # 测试典型参数
        packet_size = 1024  # bits
        distances = [10, 50, 100]  # meters
        tx_powers = [-5, 0, 5]  # dBm
        
        print("典型能耗计算:")
        for distance in distances:
            for tx_power in tx_powers:
                tx_energy = energy_model.calculate_transmission_energy(packet_size, distance, tx_power)
                rx_energy = energy_model.calculate_reception_energy(packet_size)
                total_energy = tx_energy + rx_energy
                
                print(f"   距离{distance}m, 功率{tx_power}dBm: 发射{tx_energy*1000:.3f}mJ, 接收{rx_energy*1000:.3f}mJ, 总计{total_energy*1000:.3f}mJ")
        
        # 检查能耗模型参数
        print(f"\n能耗模型参数:")
        if hasattr(energy_model, 'platform_params'):
            params = energy_model.platform_params[HardwarePlatform.CC2420_TELOSB]
            print(f"   发射能耗: {params.tx_energy_per_bit*1e9:.1f} nJ/bit")
            print(f"   接收能耗: {params.rx_energy_per_bit*1e9:.1f} nJ/bit")
        else:
            print("   ⚠️ 无法访问platform_params")
            
    except Exception as e:
        print(f"❌ 能耗模型调试失败: {e}")
        import traceback
        traceback.print_exc()

def compare_energy_calculations():
    """对比不同协议的能耗计算方式"""
    
    print(f"\n⚖️ 对比能耗计算方式")
    print("=" * 40)
    
    # 创建测试配置
    config = NetworkConfig(
        num_nodes=5,
        area_width=50,
        area_height=50,
        initial_energy=1.0,
        packet_size=1024
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    try:
        # 创建协议实例
        leach = LEACHProtocol(config, energy_model)
        eehfr = IntegratedEnhancedEEHFRProtocol(config)
        
        print("LEACH能耗计算方式:")
        # 检查LEACH如何计算能耗
        if hasattr(leach, 'energy_model'):
            print("   ✅ 使用ImprovedEnergyModel")
        else:
            print("   ❌ 没有使用ImprovedEnergyModel")
        
        print("Enhanced EEHFR能耗计算方式:")
        if hasattr(eehfr, 'energy_model'):
            print("   ✅ 使用ImprovedEnergyModel")
            print(f"   平台: {eehfr.energy_model.platform.value}")
        else:
            print("   ❌ 没有使用ImprovedEnergyModel")
        
        # 测试相同距离的能耗计算
        distance = 50
        tx_power = 0
        packet_size = 1024
        
        print(f"\n相同条件下的能耗计算 (距离{distance}m, 功率{tx_power}dBm):")
        
        # LEACH的计算
        leach_tx_energy = leach.energy_model.calculate_transmission_energy(packet_size, distance, tx_power)
        leach_rx_energy = leach.energy_model.calculate_reception_energy(packet_size)
        
        # Enhanced EEHFR的计算
        eehfr_tx_energy = eehfr.energy_model.calculate_transmission_energy(packet_size, distance, tx_power)
        eehfr_rx_energy = eehfr.energy_model.calculate_reception_energy(packet_size)
        
        print(f"   LEACH: 发射{leach_tx_energy*1000:.3f}mJ, 接收{leach_rx_energy*1000:.3f}mJ")
        print(f"   Enhanced EEHFR: 发射{eehfr_tx_energy*1000:.3f}mJ, 接收{eehfr_rx_energy*1000:.3f}mJ")
        
        if abs(leach_tx_energy - eehfr_tx_energy) > 1e-6:
            print("   ⚠️ 发射能耗计算不一致")
        if abs(leach_rx_energy - eehfr_rx_energy) > 1e-6:
            print("   ⚠️ 接收能耗计算不一致")
            
    except Exception as e:
        print(f"❌ 能耗计算对比失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    
    print("🔍 Enhanced EEHFR能耗异常调试")
    print("=" * 60)
    print("目的: 找出为什么Enhanced EEHFR能耗异常低")
    print()
    
    # 1. 调试单轮能耗
    debug_single_round()
    
    # 2. 调试能耗模型
    debug_energy_model()
    
    # 3. 对比能耗计算方式
    compare_energy_calculations()
    
    print(f"\n📋 调试总结:")
    print("=" * 30)
    print("需要检查的问题:")
    print("1. Enhanced EEHFR是否正确使用了能耗模型")
    print("2. 能耗计算是否与LEACH/PEGASIS一致")
    print("3. 是否有能耗计算的bug")
    print("4. 协议逻辑是否导致异常低的能耗")

if __name__ == "__main__":
    main()
