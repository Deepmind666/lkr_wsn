#!/usr/bin/env python3
"""
全面的WSN协议基准测试
验证LEACH、PEGASIS、HEED、TEEN、Enhanced PEGASIS的正确性
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from enhanced_pegasis import EnhancedPEGASISProtocol, EnhancedPEGASISConfig
from benchmark_protocols import (
    LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, TEENProtocolWrapper,
    NetworkConfig
)
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
import json
from datetime import datetime
import time

def create_test_network(num_nodes=50):
    """创建标准测试网络"""
    config = NetworkConfig(
        num_nodes=num_nodes,
        area_width=100,
        area_height=100,
        base_station_x=50,
        base_station_y=175,
        initial_energy=2.0,
        packet_size=4000
    )
    return config

def run_protocol_test(protocol_class, config, protocol_name, max_rounds=200):
    """运行单个协议的完整测试"""
    print(f"\n🔬 测试 {protocol_name}...")
    
    try:
        # 创建协议实例
        if protocol_class == EnhancedPEGASISProtocol:
            enhanced_config = EnhancedPEGASISConfig(
                num_nodes=config.num_nodes,
                area_width=config.area_width,
                area_height=config.area_height,
                base_station_x=config.base_station_x,
                base_station_y=config.base_station_y,
                initial_energy=config.initial_energy,
                packet_size=config.packet_size,
                chain_optimization_interval=10,
                leader_rotation_interval=5
            )
            protocol = protocol_class(enhanced_config)
            protocol.initialize_network()
        elif protocol_class in [HEEDProtocolWrapper, TEENProtocolWrapper]:
            # 为包装类协议创建能量模型
            energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
            protocol = protocol_class(config, energy_model)
        else:
            # 为基准协议创建能量模型
            energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
            protocol = protocol_class(config, energy_model)
        
        # 运行仿真
        start_time = time.time()
        round_count = 0

        if protocol_class in [HEEDProtocolWrapper, TEENProtocolWrapper]:
            # 包装类使用run_simulation方法
            simulation_result = protocol.run_simulation(max_rounds)
            round_count = simulation_result.get('network_lifetime', max_rounds)
        else:
            # 其他协议使用run_round方法
            for round_num in range(max_rounds):
                if protocol_class == EnhancedPEGASISProtocol:
                    if not protocol.run_round():
                        break
                else:
                    result = protocol.run_round()
                    if not result or (hasattr(result, 'get') and result.get('alive_nodes', 0) == 0):
                        break

                round_count += 1
            
            # 每50轮输出一次状态
            if round_num % 50 == 0:
                alive_nodes = len([n for n in protocol.nodes if n.is_alive])
                if hasattr(protocol, 'stats'):
                    total_packets = protocol.stats.get('packets_transmitted', 0)
                    total_energy = protocol.stats.get('total_energy_consumed', 0)
                else:
                    total_packets = getattr(protocol, 'packets_sent', 0)
                    total_energy = getattr(protocol, 'total_energy_consumed', 0)
                print(f"  轮次 {round_num}: 存活={alive_nodes}, 数据包={total_packets}, 能耗={total_energy:.3f}J")
        
        execution_time = time.time() - start_time
        
        # 收集最终统计
        if protocol_class in [HEEDProtocolWrapper, TEENProtocolWrapper]:
            # 包装类已经有simulation_result
            total_packets_sent = simulation_result.get('packets_transmitted', 0)
            total_packets_received = simulation_result.get('packets_received', 0)
            total_energy = simulation_result.get('total_energy_consumed', 0)
            alive_nodes = simulation_result.get('final_alive_nodes', 0)
        elif hasattr(protocol, 'stats'):
            total_packets_sent = protocol.stats.get('packets_transmitted', 0)
            total_packets_received = protocol.stats.get('packets_received', 0)
            total_energy = protocol.stats.get('total_energy_consumed', 0)
            alive_nodes = len([n for n in protocol.nodes if n.is_alive])
        else:
            total_packets_sent = getattr(protocol, 'packets_sent', 0)
            total_packets_received = getattr(protocol, 'packets_received', 0)
            total_energy = getattr(protocol, 'total_energy_consumed', 0)
            alive_nodes = len([n for n in protocol.nodes if n.is_alive])
        
        # 计算性能指标
        energy_efficiency = total_packets_received / total_energy if total_energy > 0 else 0
        packet_delivery_ratio = total_packets_received / total_packets_sent if total_packets_sent > 0 else 0
        avg_packets_per_round = total_packets_sent / round_count if round_count > 0 else 0
        
        results = {
            'protocol_name': protocol_name,
            'success': True,
            'rounds_survived': round_count,
            'total_packets_sent': total_packets_sent,
            'total_packets_received': total_packets_received,
            'total_energy_consumed': total_energy,
            'alive_nodes': alive_nodes,
            'energy_efficiency': energy_efficiency,
            'packet_delivery_ratio': packet_delivery_ratio,
            'avg_packets_per_round': avg_packets_per_round,
            'execution_time': execution_time
        }
        
        print(f"✅ {protocol_name} 测试成功:")
        print(f"   存活轮次: {round_count}")
        print(f"   发送数据包: {total_packets_sent}")
        print(f"   接收数据包: {total_packets_received}")
        print(f"   总能耗: {total_energy:.6f} J")
        print(f"   能效: {energy_efficiency:.2f} packets/J")
        print(f"   投递率: {packet_delivery_ratio:.3f}")
        print(f"   平均每轮数据包: {avg_packets_per_round:.1f}")
        print(f"   执行时间: {execution_time:.2f}s")
        
        return results
        
    except Exception as e:
        print(f"❌ {protocol_name} 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'protocol_name': protocol_name,
            'success': False,
            'error': str(e),
            'rounds_survived': 0,
            'total_packets_sent': 0,
            'total_packets_received': 0,
            'total_energy_consumed': 0,
            'alive_nodes': 0,
            'energy_efficiency': 0,
            'packet_delivery_ratio': 0,
            'avg_packets_per_round': 0,
            'execution_time': 0
        }

def main():
    """主测试函数"""
    print("🚀 WSN协议全面基准测试")
    print("=" * 60)
    
    # 创建测试网络
    config = create_test_network(50)
    
    # 定义要测试的协议
    protocols = [
        (LEACHProtocol, "LEACH"),
        (PEGASISProtocol, "PEGASIS"),
        (HEEDProtocolWrapper, "HEED"),
        (TEENProtocolWrapper, "TEEN"),
        (EnhancedPEGASISProtocol, "Enhanced PEGASIS")
    ]
    
    all_results = []
    successful_results = []
    
    # 运行所有协议测试
    for protocol_class, protocol_name in protocols:
        result = run_protocol_test(protocol_class, config, protocol_name)
        all_results.append(result)
        if result['success']:
            successful_results.append(result)
    
    # 性能对比分析
    if len(successful_results) >= 2:
        print("\n📊 协议性能对比分析")
        print("=" * 60)
        
        # 按能效排序
        sorted_by_efficiency = sorted(successful_results, key=lambda x: x['energy_efficiency'], reverse=True)
        
        print("🏆 能效排名 (packets/J):")
        for i, result in enumerate(sorted_by_efficiency, 1):
            print(f"  {i}. {result['protocol_name']}: {result['energy_efficiency']:.2f}")
        
        print("\n📦 投递率排名:")
        sorted_by_pdr = sorted(successful_results, key=lambda x: x['packet_delivery_ratio'], reverse=True)
        for i, result in enumerate(sorted_by_pdr, 1):
            print(f"  {i}. {result['protocol_name']}: {result['packet_delivery_ratio']:.3f}")
        
        print("\n⚡ 能耗排名 (越低越好):")
        sorted_by_energy = sorted(successful_results, key=lambda x: x['total_energy_consumed'])
        for i, result in enumerate(sorted_by_energy, 1):
            print(f"  {i}. {result['protocol_name']}: {result['total_energy_consumed']:.3f}J")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"../results/comprehensive_protocol_test_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_timestamp': timestamp,
            'test_config': {
                'num_nodes': config.num_nodes,
                'area_size': f"{config.area_width}x{config.area_height}",
                'base_station': f"({config.base_station_x}, {config.base_station_y})",
                'initial_energy': config.initial_energy,
                'packet_size': config.packet_size
            },
            'results': all_results,
            'summary': {
                'total_protocols_tested': len(protocols),
                'successful_protocols': len(successful_results),
                'failed_protocols': len(all_results) - len(successful_results)
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 完整结果已保存到: {results_file}")
    print(f"\n📈 测试总结:")
    print(f"   测试协议数: {len(protocols)}")
    print(f"   成功协议数: {len(successful_results)}")
    print(f"   失败协议数: {len(all_results) - len(successful_results)}")

if __name__ == "__main__":
    main()
