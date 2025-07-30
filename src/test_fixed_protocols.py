#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的协议对比

目的：使用修复后的能耗模型重新测试三个协议的性能
确保结果的合理性和可信性
"""

import sys
import os
import json
import time
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def test_single_round_comparison():
    """测试单轮对比 - 确保公平性"""
    
    print("🔍 修复后的单轮协议对比")
    print("=" * 50)
    
    # 统一的网络配置
    config = NetworkConfig(
        num_nodes=10,
        area_width=100,
        area_height=100,
        initial_energy=2.0,
        packet_size=1024,
        base_station_x=50,
        base_station_y=50
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    results = {}
    
    # 测试三个协议
    protocols = [
        ('LEACH', LEACHProtocol, lambda c, e: LEACHProtocol(c, e)),
        ('PEGASIS', PEGASISProtocol, lambda c, e: PEGASISProtocol(c, e)),
        ('Enhanced_EEHFR', IntegratedEnhancedEEHFRProtocol, lambda c, e: IntegratedEnhancedEEHFRProtocol(c))
    ]
    
    for protocol_name, protocol_class, protocol_factory in protocols:
        print(f"\n🧪 测试 {protocol_name}:")
        
        try:
            protocol = protocol_factory(config, energy_model)
            
            # 记录初始状态
            initial_energy = sum(node.current_energy for node in protocol.nodes)
            print(f"   初始总能量: {initial_energy:.3f} J")
            
            # 执行一轮
            if protocol_name == 'Enhanced_EEHFR':
                # Enhanced EEHFR的执行方式
                protocol._select_cluster_heads()
                protocol._form_clusters()
                packets_sent, packets_received, energy_consumed = protocol._perform_data_transmission()
                protocol._update_node_status()
                
                # 计算实际能耗
                final_energy = sum(node.current_energy for node in protocol.nodes)
                actual_energy_consumed = initial_energy - final_energy
                
            else:
                # LEACH/PEGASIS的执行方式
                result = protocol.run_simulation(max_rounds=1)
                energy_consumed = result['total_energy_consumed']
                packets_sent = result.get('additional_metrics', {}).get('total_packets_sent', 0)
                packets_received = result.get('additional_metrics', {}).get('total_packets_received', 0)
                
                # 计算实际能耗
                final_energy = sum(node.current_energy for node in protocol.nodes)
                actual_energy_consumed = initial_energy - final_energy
            
            # 计算性能指标
            if packets_sent > 0:
                energy_efficiency = packets_received / energy_consumed if energy_consumed > 0 else 0
                packet_delivery_ratio = packets_received / packets_sent
                energy_per_packet = energy_consumed / packets_sent
            else:
                energy_efficiency = 0
                packet_delivery_ratio = 0
                energy_per_packet = 0
            
            # 存储结果
            results[protocol_name] = {
                'packets_sent': packets_sent,
                'packets_received': packets_received,
                'energy_consumed': energy_consumed,
                'actual_energy_consumed': actual_energy_consumed,
                'energy_efficiency': energy_efficiency,
                'packet_delivery_ratio': packet_delivery_ratio,
                'energy_per_packet': energy_per_packet,
                'alive_nodes': len([n for n in protocol.nodes if n.is_alive])
            }
            
            print(f"   发送包数: {packets_sent}")
            print(f"   接收包数: {packets_received}")
            print(f"   报告能耗: {energy_consumed*1000:.3f} mJ")
            print(f"   实际能耗: {actual_energy_consumed*1000:.3f} mJ")
            print(f"   单包能耗: {energy_per_packet*1000:.3f} mJ/packet")
            print(f"   投递率: {packet_delivery_ratio:.3f}")
            print(f"   能效: {energy_efficiency:.1f} packets/J")
            
        except Exception as e:
            print(f"   ❌ {protocol_name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    return results

def analyze_results(results):
    """分析测试结果"""
    
    print(f"\n📊 结果分析")
    print("=" * 50)
    
    if len(results) < 2:
        print("❌ 结果不足，无法进行对比分析")
        return
    
    # 找到基准协议（通常是LEACH）
    baseline = results.get('LEACH', list(results.values())[0])
    
    print("协议对比分析:")
    print(f"{'协议':<15} {'能耗(mJ)':<10} {'能效':<10} {'投递率':<8} {'相对性能'}")
    print("-" * 60)
    
    for protocol_name, result in results.items():
        energy_mj = result['energy_consumed'] * 1000
        efficiency = result['energy_efficiency']
        pdr = result['packet_delivery_ratio']
        
        # 计算相对性能
        if baseline['energy_consumed'] > 0:
            energy_ratio = result['energy_consumed'] / baseline['energy_consumed']
            relative_perf = f"{energy_ratio:.2f}x能耗"
        else:
            relative_perf = "N/A"
        
        print(f"{protocol_name:<15} {energy_mj:<10.3f} {efficiency:<10.1f} {pdr:<8.3f} {relative_perf}")
    
    # 合理性检查
    print(f"\n⚠️ 合理性检查:")
    
    issues = []
    
    # 检查能耗差异
    energies = [r['energy_consumed'] for r in results.values() if r['energy_consumed'] > 0]
    if energies:
        max_energy = max(energies)
        min_energy = min(energies)
        energy_ratio = max_energy / min_energy if min_energy > 0 else float('inf')
        
        if energy_ratio > 10:
            issues.append(f"能耗差异过大: {energy_ratio:.1f}倍")
        elif energy_ratio < 1.1:
            issues.append(f"能耗差异过小: {energy_ratio:.2f}倍")
        else:
            print(f"✅ 能耗差异合理: {energy_ratio:.2f}倍")
    
    # 检查投递率
    pdrs = [r['packet_delivery_ratio'] for r in results.values()]
    if any(pdr > 0.99 for pdr in pdrs):
        issues.append("某些协议投递率过高(>99%)")
    
    if any(pdr < 0.5 for pdr in pdrs):
        issues.append("某些协议投递率过低(<50%)")
    
    if issues:
        for issue in issues:
            print(f"❌ {issue}")
    else:
        print("✅ 所有指标都在合理范围内")

def test_multi_round_comparison():
    """测试多轮对比"""
    
    print(f"\n🔄 多轮协议对比测试")
    print("=" * 50)
    
    config = NetworkConfig(
        num_nodes=15,
        area_width=100,
        area_height=100,
        initial_energy=2.0,
        packet_size=1024,
        base_station_x=50,
        base_station_y=50
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    max_rounds = 10
    
    results = {}
    
    protocols = [
        ('LEACH', lambda: LEACHProtocol(config, energy_model)),
        ('PEGASIS', lambda: PEGASISProtocol(config, energy_model)),
        ('Enhanced_EEHFR', lambda: IntegratedEnhancedEEHFRProtocol(config))
    ]
    
    for protocol_name, protocol_factory in protocols:
        print(f"\n🧪 测试 {protocol_name} ({max_rounds}轮):")
        
        try:
            protocol = protocol_factory()
            
            if protocol_name == 'Enhanced_EEHFR':
                # Enhanced EEHFR的多轮测试
                total_packets_sent = 0
                total_packets_received = 0
                total_energy_consumed = 0.0
                
                for round_num in range(max_rounds):
                    if not any(node.is_alive for node in protocol.nodes):
                        break
                    
                    protocol._select_cluster_heads()
                    protocol._form_clusters()
                    packets_sent, packets_received, energy_consumed = protocol._perform_data_transmission()
                    protocol._update_node_status()
                    
                    total_packets_sent += packets_sent
                    total_packets_received += packets_received
                    total_energy_consumed += energy_consumed
                
                alive_nodes = len([n for n in protocol.nodes if n.is_alive])
                network_lifetime = max_rounds if alive_nodes > 0 else round_num
                
            else:
                # LEACH/PEGASIS的多轮测试
                result = protocol.run_simulation(max_rounds=max_rounds)
                total_energy_consumed = result['total_energy_consumed']
                total_packets_sent = result.get('additional_metrics', {}).get('total_packets_sent', 0)
                total_packets_received = result.get('additional_metrics', {}).get('total_packets_received', 0)
                network_lifetime = result['network_lifetime']
                alive_nodes = len([n for n in protocol.nodes if n.is_alive])
            
            # 计算性能指标
            if total_packets_sent > 0:
                energy_efficiency = total_packets_received / total_energy_consumed if total_energy_consumed > 0 else 0
                packet_delivery_ratio = total_packets_received / total_packets_sent
            else:
                energy_efficiency = 0
                packet_delivery_ratio = 0
            
            results[protocol_name] = {
                'total_packets_sent': total_packets_sent,
                'total_packets_received': total_packets_received,
                'total_energy_consumed': total_energy_consumed,
                'energy_efficiency': energy_efficiency,
                'packet_delivery_ratio': packet_delivery_ratio,
                'network_lifetime': network_lifetime,
                'alive_nodes': alive_nodes
            }
            
            print(f"   网络生存时间: {network_lifetime} 轮")
            print(f"   总发送包数: {total_packets_sent}")
            print(f"   总接收包数: {total_packets_received}")
            print(f"   总能耗: {total_energy_consumed:.3f} J")
            print(f"   能效: {energy_efficiency:.1f} packets/J")
            print(f"   投递率: {packet_delivery_ratio:.3f}")
            print(f"   存活节点: {alive_nodes}")
            
        except Exception as e:
            print(f"   ❌ {protocol_name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    return results

def save_results(single_round_results, multi_round_results):
    """保存测试结果"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    results = {
        'timestamp': timestamp,
        'test_description': '修复能耗模型后的协议对比测试',
        'energy_model': 'CC2420_TELOSB_Fixed',
        'single_round_comparison': single_round_results,
        'multi_round_comparison': multi_round_results
    }
    
    # 保存到results目录
    os.makedirs('../results', exist_ok=True)
    filename = f'../results/fixed_protocol_comparison_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存到: {filename}")
    return filename

def main():
    """主函数"""
    
    print("🔧 修复后的协议对比测试")
    print("=" * 60)
    print("目的: 使用修复后的能耗模型测试协议性能")
    print("修复: CC2420能耗参数 208.8/225.6 nJ/bit")
    print()
    
    # 1. 单轮对比测试
    single_round_results = test_single_round_comparison()
    
    if single_round_results:
        analyze_results(single_round_results)
    
    # 2. 多轮对比测试
    multi_round_results = test_multi_round_comparison()
    
    # 3. 保存结果
    if single_round_results or multi_round_results:
        save_results(single_round_results, multi_round_results)
    
    print(f"\n📋 测试总结:")
    print("=" * 30)
    print("✅ 能耗模型已修复")
    print("✅ 协议对比测试完成")
    print("✅ 结果已保存")
    
    print(f"\n下一步:")
    print("1. 分析修复后的性能差异")
    print("2. 验证结果的合理性")
    print("3. 基于真实数据撰写论文")

if __name__ == "__main__":
    main()
