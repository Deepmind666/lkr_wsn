#!/usr/bin/env python3
"""
测试修复后的Enhanced PEGASIS算法
验证数据包传输逻辑是否正确
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import matplotlib.pyplot as plt
from enhanced_pegasis import EnhancedPEGASISProtocol, EnhancedPEGASISConfig
from benchmark_protocols import PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
import json
from datetime import datetime

def create_test_network(num_nodes=50):
    """创建测试网络"""
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

def run_single_test(protocol_class, config, protocol_name, max_rounds=200):
    """运行单个协议测试"""
    print(f"\n🔬 测试 {protocol_name}...")

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
        # 重要：初始化网络
        protocol.initialize_network()
    else:
        # 为原始PEGASIS创建能量模型
        energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        protocol = protocol_class(config, energy_model)
    
    round_count = 0
    packets_per_round = []
    
    for round_num in range(max_rounds):
        if not protocol.run_round():
            break
        round_count += 1
        
        # 记录每轮的数据包传输数量
        if hasattr(protocol, 'round_stats') and protocol.round_stats:
            packets_this_round = protocol.round_stats[-1].get('packets_sent', 0)
        elif hasattr(protocol, 'stats'):
            # 对于benchmark_protocols中的协议
            current_packets = protocol.stats.get('packets_transmitted', 0)
            packets_this_round = current_packets - sum(packets_per_round)
        else:
            packets_this_round = getattr(protocol, 'packets_sent', 0) - sum(packets_per_round)

        packets_per_round.append(packets_this_round)

        # 每10轮输出一次状态
        if round_num % 10 == 0:
            alive_nodes = len([n for n in protocol.nodes if n.is_alive])
            if hasattr(protocol, 'stats'):
                total_packets = protocol.stats.get('packets_transmitted', 0)
                total_energy = protocol.stats.get('total_energy_consumed', 0)
            else:
                total_packets = getattr(protocol, 'packets_sent', 0)
                total_energy = getattr(protocol, 'total_energy_consumed', 0)
            print(f"  轮次 {round_num}: 存活节点={alive_nodes}, 总数据包={total_packets}, 总能耗={total_energy:.6f}J")
    
    # 计算最终统计
    if hasattr(protocol, 'stats'):
        # 对于benchmark_protocols中的协议
        total_packets_sent = protocol.stats.get('packets_transmitted', 0)
        total_packets_received = protocol.stats.get('packets_received', 0)
        total_energy = protocol.stats.get('total_energy_consumed', 0)
    else:
        # 对于Enhanced PEGASIS
        total_packets_sent = getattr(protocol, 'packets_sent', 0)
        total_packets_received = getattr(protocol, 'packets_received', 0)
        total_energy = getattr(protocol, 'total_energy_consumed', 0)

    alive_nodes = len([n for n in protocol.nodes if n.is_alive])
    
    # 计算性能指标
    energy_efficiency = total_packets_received / total_energy if total_energy > 0 else 0
    packet_delivery_ratio = total_packets_received / total_packets_sent if total_packets_sent > 0 else 0
    avg_packets_per_round = np.mean(packets_per_round) if packets_per_round else 0
    
    results = {
        'protocol_name': protocol_name,
        'rounds_survived': round_count,
        'total_packets_sent': total_packets_sent,
        'total_packets_received': total_packets_received,
        'total_energy_consumed': total_energy,
        'alive_nodes': alive_nodes,
        'energy_efficiency': energy_efficiency,
        'packet_delivery_ratio': packet_delivery_ratio,
        'avg_packets_per_round': avg_packets_per_round,
        'packets_per_round': packets_per_round[:10]  # 只保存前10轮的详细数据
    }
    
    print(f"\n📊 {protocol_name} 测试结果:")
    print(f"   存活轮次: {round_count}")
    print(f"   发送数据包: {total_packets_sent}")
    print(f"   接收数据包: {total_packets_received}")
    print(f"   总能耗: {total_energy:.6f} J")
    print(f"   能效: {energy_efficiency:.2f} packets/J")
    print(f"   投递率: {packet_delivery_ratio:.3f}")
    print(f"   平均每轮数据包: {avg_packets_per_round:.1f}")
    
    return results

def main():
    """主测试函数"""
    print("🚀 Enhanced PEGASIS 修复测试")
    print("=" * 50)
    
    # 创建测试网络
    config = create_test_network(50)
    
    # 测试协议
    protocols = [
        (PEGASISProtocol, "Original PEGASIS"),
        (EnhancedPEGASISProtocol, "Enhanced PEGASIS (Fixed)")
    ]
    
    all_results = []
    
    for protocol_class, protocol_name in protocols:
        try:
            result = run_single_test(protocol_class, config, protocol_name)
            all_results.append(result)
        except Exception as e:
            print(f"❌ {protocol_name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 性能对比
    if len(all_results) >= 2:
        print("\n🔍 性能对比分析:")
        print("=" * 50)
        
        original = all_results[0]
        enhanced = all_results[1]
        
        # 计算改进百分比
        def calculate_improvement(enhanced_val, original_val):
            if original_val == 0:
                return 0
            return ((enhanced_val - original_val) / original_val) * 100
        
        energy_improvement = calculate_improvement(
            enhanced['energy_efficiency'], original['energy_efficiency']
        )
        pdr_improvement = calculate_improvement(
            enhanced['packet_delivery_ratio'], original['packet_delivery_ratio']
        )
        packets_improvement = calculate_improvement(
            enhanced['avg_packets_per_round'], original['avg_packets_per_round']
        )
        
        print(f"能效改进: {energy_improvement:+.1f}%")
        print(f"投递率改进: {pdr_improvement:+.1f}%")
        print(f"每轮数据包改进: {packets_improvement:+.1f}%")
        
        # 判断修复是否成功
        if enhanced['avg_packets_per_round'] > 10:  # 期望每轮至少10个数据包
            print("\n✅ Enhanced PEGASIS 修复成功！")
            print(f"   每轮传输 {enhanced['avg_packets_per_round']:.1f} 个数据包")
        else:
            print("\n❌ Enhanced PEGASIS 仍有问题")
            print(f"   每轮只传输 {enhanced['avg_packets_per_round']:.1f} 个数据包")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"../results/enhanced_pegasis_fix_test_{timestamp}.json"
    
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
            'results': all_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存到: {results_file}")

if __name__ == "__main__":
    main()
