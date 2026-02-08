#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified ablation study - analyze AERIS performance issues

Goal: quickly identify performance bottlenecks and understand why AERIS may underperform PEGASIS
Method: comparative analysis of key parameters and decision logic

Author: AERIS Research Team
Date: 2025-01-30
"""

import numpy as np
import json
import time
from typing import Dict, List

from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol

def analyze_protocol_behavior():
    """Analyze behavior characteristics of each protocol"""
    
    print("Analyze protocol behavior characteristics")
    print("=" * 50)
    
    # Create standard test configuration
    config = NetworkConfig(
        num_nodes=20,
        area_width=50,
        area_height=50,
        initial_energy=1.0
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # Test single-round behavior for each protocol
    protocols = {
        'LEACH': LEACHProtocol(config, energy_model),
        'PEGASIS': PEGASISProtocol(config, energy_model),
        'AERIS': AerisProtocol(config)
    }
    
    results = {}
    
    for name, protocol in protocols.items():
        print(f"\nAnalyzing protocol: {name}")
        
        # Run 5 simulation rounds
        result = protocol.run_simulation(max_rounds=5)
        results[name] = result
        
        print(f"   Alive nodes after 5 rounds: {result['final_alive_nodes']}")
        print(f"   Total energy: {result['total_energy_consumed']*1000:.3f} mJ")
        print(f"   Packets sent: {result.get('additional_metrics', {}).get('total_packets_sent', 'N/A')}")
        print(f"   Packets received: {result.get('additional_metrics', {}).get('total_packets_received', 'N/A')}")
        print(f"   Packet delivery ratio (PDR): {result['packet_delivery_ratio']:.3f}")
        print(f"   Energy efficiency: {result['energy_efficiency']:.1f} packets/J")
    
    return results

def analyze_energy_consumption_pattern():
    """Analyze energy consumption pattern"""
    
    print("\nAnalyze energy consumption pattern")
    print("=" * 50)
    
    config = NetworkConfig(
        num_nodes=10,  # smaller scale for easier analysis
        area_width=30,
        area_height=30,
        initial_energy=0.5
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # Analyze single transmission energy
    distances = [5, 10, 20, 30, 40, 50]  # different distances
    packet_size = 1024 * 8  # bits
    
    print("\nSingle-transmission energy breakdown:")
    print("Distance(m)  TxEnergy(mJ)  RxEnergy(mJ)  Total(mJ)")
    print("-" * 50)
    
    for distance in distances:
        tx_energy = energy_model.calculate_transmission_energy(packet_size, distance, 0.0, config.temperature_c, config.humidity_ratio)
        rx_energy = energy_model.calculate_reception_energy(packet_size, config.temperature_c, config.humidity_ratio)
        total_energy = tx_energy + rx_energy
        
        print(f"{distance:6.0f}   {tx_energy*1000:10.3f}   {rx_energy*1000:10.3f}   {total_energy*1000:8.3f}")
    
    # Analyze energy under different Tx powers
    print("\nEnergy vs Tx power (distance=30m):")
    print("Power(dBm)  TxEnergy(mJ)  Total(mJ)")
    print("-" * 35)
    
    powers = [-5, 0, 5, 8]
    for power in powers:
        tx_energy = energy_model.calculate_transmission_energy(packet_size, 30, power, config.temperature_c, config.humidity_ratio)
        rx_energy = energy_model.calculate_reception_energy(packet_size, config.temperature_c, config.humidity_ratio)
        total_energy = tx_energy + rx_energy
        
        print(f"{power:8.0f}   {tx_energy*1000:10.3f}   {total_energy*1000:8.3f}")

def compare_clustering_strategies():
    """Compare clustering strategies"""
    
    print("\nCompare clustering strategies")
    print("=" * 50)
    
    config = NetworkConfig(
        num_nodes=15,
        area_width=40,
        area_height=40,
        initial_energy=0.8
    )
    
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    # Create protocol instance
    leach = LEACHProtocol(config, energy_model)
    AERIS = AerisProtocol(config)
    
    print("\nClustering characteristics comparison:")
    print("Protocol        CH_count   AvgClusterSize   TotalEnergy(mJ)")
    print("-" * 65)
    
    # Run single round analysis
    for name, protocol in [("LEACH", leach), ("AERIS", AERIS)]:
        result = protocol.run_simulation(max_rounds=1)
        
        if 'additional_metrics' in result:
            cluster_heads = result['additional_metrics'].get('average_cluster_heads', 0)
            avg_cluster_size = config.num_nodes / cluster_heads if cluster_heads > 0 else 0
            total_energy = result['total_energy_consumed'] * 1000  # mJ
            
            print(f"{name:12} {cluster_heads:8.1f} {avg_cluster_size:15.1f} {total_energy:15.3f}")

def identify_performance_bottlenecks():
    """Identify performance bottlenecks"""
    
    print("\nIdentify performance bottlenecks")
    print("=" * 50)
    
    config = NetworkConfig(
        num_nodes=20,
        area_width=50,
        area_height=50,
        initial_energy=1.0
    )
    
    # Run a longer simulation
    protocols = {}
    
    # PEGASIS (best performance)
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    pegasis = PEGASISProtocol(config, energy_model)
    pegasis_result = pegasis.run_simulation(max_rounds=100)
    protocols['PEGASIS'] = pegasis_result
    
    # AERIS (to be analyzed)
    AERIS = AerisProtocol(config)
    eehfr_result = AERIS.run_simulation(max_rounds=100)
    protocols['AERIS'] = eehfr_result
    
    print("\nPerformance comparison analysis:")
    print("Metric                   PEGASIS        AERIS            Delta")
    print("-" * 60)
    
    # Network lifetime
    pegasis_lifetime = pegasis_result['network_lifetime']
    eehfr_lifetime = eehfr_result['network_lifetime']
    lifetime_diff = eehfr_lifetime - pegasis_lifetime
    print(f"Network lifetime (rounds)   {pegasis_lifetime:8d}    {eehfr_lifetime:13d}    {lifetime_diff:+4d}")
    
    # Total energy
    pegasis_energy = pegasis_result['total_energy_consumed']
    eehfr_energy = eehfr_result['total_energy_consumed']
    energy_diff = (eehfr_energy - pegasis_energy) / pegasis_energy * 100
    print(f"Total energy (J)            {pegasis_energy:8.3f}    {eehfr_energy:13.3f}    {energy_diff:+4.1f}%")
    
    # Energy efficiency
    pegasis_efficiency = pegasis_result['energy_efficiency']
    eehfr_efficiency = eehfr_result['energy_efficiency']
    efficiency_diff = (eehfr_efficiency - pegasis_efficiency) / pegasis_efficiency * 100
    print(f"Energy efficiency (p/J)     {pegasis_efficiency:8.1f}    {eehfr_efficiency:13.1f}    {efficiency_diff:+4.1f}%")
    
    # Packet delivery ratio
    pegasis_pdr = pegasis_result['packet_delivery_ratio']
    eehfr_pdr = eehfr_result['packet_delivery_ratio']
    pdr_diff = (eehfr_pdr - pegasis_pdr) * 100
    print(f"Packet delivery ratio       {pegasis_pdr:8.3f}    {eehfr_pdr:13.3f}    {pdr_diff:+4.1f}pp")
    
    # Possible performance bottlenecks
    
    if eehfr_lifetime < pegasis_lifetime:
        print("- AERIS network lifetime is shorter")
        print("  Possible causes: higher energy consumption, load imbalance, suboptimal CH selection")
    
    if eehfr_efficiency < pegasis_efficiency:
        print("- AERIS energy efficiency is lower")
        print("  Possible causes: excessive Tx power, routing overhead, high decision complexity")
    
    if eehfr_energy > pegasis_energy:
        print("- AERIS total energy consumption is higher")
        print("  Possible causes: wrong environment classification, fuzzy logic overhead, multi-stage optimization conflicts")
    
    return protocols

def generate_optimization_recommendations():
    """Generate optimization recommendations"""
    
    print("\nOptimization recommendations")
    print("=" * 50)
    
    recommendations = [
        "1. Simplify environment classification to reduce compute overhead",
        "2. Optimize fuzzy rules to avoid over-complex decisions",
        "3. Tune transmission power control to avoid unnecessary high power",
        "4. Learn PEGASIS load-balancing for better CH selection",
        "5. Reduce protocol overhead and focus on the most effective optimizations",
        "6. Perform parameter tuning across different network scales",
        "7. Consider hybrid strategies with scenario-aware selection"
    ]
    
    for rec in recommendations:
        print(f"   {rec}")
    
    print("\nNext actions:")
    print("   1. Run parameter tuning experiments")
    print("   2. Simplify protocol complexity")
    print("   3. Re-test performance")
    print("   4. Compare with PEGASIS in detail")

def main():
    """Main"""
    
    print("AERIS performance analysis and optimization")
    print("=" * 60)
    
    # 1. 分析协议行为
    protocol_results = analyze_protocol_behavior()
    
    # 2. 分析能耗模�?
    analyze_energy_consumption_pattern()
    
    # 3. 对比分簇策略
    compare_clustering_strategies()
    
    # 4. 识别性能瓶颈
    bottleneck_results = identify_performance_bottlenecks()
    
    # 5. 生成优化建议
    generate_optimization_recommendations()
    
    # 保存分析结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"../results/performance_analysis_{timestamp}.json"
    
    analysis_results = {
        'protocol_comparison': protocol_results,
        'bottleneck_analysis': bottleneck_results,
        'timestamp': timestamp
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=True)
    
    print(f"\nAnalysis results saved to: {results_file}")
    print("\nPerformance analysis completed.")

if __name__ == "__main__":
    main()
