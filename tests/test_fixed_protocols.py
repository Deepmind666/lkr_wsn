#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的协议对比

目的：使用修复后的能耗模型重新测试三个协议的性能
确保结果的合理性和可信�?
"""

import sys
import os
import json
import time
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aeris_protocol import AerisProtocol
from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform


def test_single_round_comparison():
    """Single-round comparison - ensure fairness"""

    print("[COMPARE] Single-round protocol comparison (fixed energy model)")
    print("=" * 50)

    # Unified network config
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

    # Test three protocols
    protocols = [
        ('LEACH', LEACHProtocol, lambda c, e: LEACHProtocol(c, e)),
        ('PEGASIS', PEGASISProtocol, lambda c, e: PEGASISProtocol(c, e)),
        ('AERIS', AerisProtocol, lambda c, e: AerisProtocol(c))
    ]

    for protocol_name, protocol_class, protocol_factory in protocols:
        print(f"\n[RUN] Testing {protocol_name}:")

        try:
            protocol = protocol_factory(config, energy_model)

            # Record initial state
            initial_energy = sum(node.current_energy for node in protocol.nodes)
            print(f"   Initial total energy: {initial_energy:.3f} J")

            # Execute one round
            if protocol_name == 'AERIS':
                # AERIS execution path
                protocol._select_cluster_heads()
                protocol._form_clusters()
                packets_sent, packets_received, energy_consumed = protocol._perform_data_transmission()
                protocol._update_node_status()

                # Compute actual energy consumption
                final_energy = sum(node.current_energy for node in protocol.nodes)
                actual_energy_consumed = initial_energy - final_energy

            else:
                # LEACH/PEGASIS execution path
                result = protocol.run_simulation(max_rounds=1)
                energy_consumed = result['total_energy_consumed']
                packets_sent = result.get('additional_metrics', {}).get('total_packets_sent', 0)
                packets_received = result.get('additional_metrics', {}).get('total_packets_received', 0)

                # Compute actual energy consumption
                final_energy = sum(node.current_energy for node in protocol.nodes)
                actual_energy_consumed = initial_energy - final_energy

            # Compute metrics
            if packets_sent > 0:
                energy_efficiency = packets_received / energy_consumed if energy_consumed > 0 else 0
                packet_delivery_ratio = packets_received / packets_sent
                energy_per_packet = energy_consumed / packets_sent
            else:
                energy_efficiency = 0
                packet_delivery_ratio = 0
                energy_per_packet = 0

            # Store results
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

            print(f"   Packets sent: {packets_sent}")
            print(f"   Packets received: {packets_received}")
            print(f"   Reported energy: {energy_consumed*1000:.3f} mJ")
            print(f"   Actual energy: {actual_energy_consumed*1000:.3f} mJ")
            print(f"   Energy per packet: {energy_per_packet*1000:.3f} mJ/packet")
            print(f"   Delivery ratio: {packet_delivery_ratio:.3f}")
            print(f"   Energy efficiency: {energy_efficiency:.1f} packets/J")

        except Exception as e:
            print(f"   [ERROR] {protocol_name} test failed: {e}")
            import traceback
            traceback.print_exc()

    return results


def analyze_results(results):
    """Analyze test results"""

    print(f"\n[ANALYZE] Results analysis")
    print("=" * 50)

    if len(results) < 2:
        print("Not enough results to compare.")
        return

    # Baseline protocol (usually LEACH)
    baseline = results.get('LEACH', list(results.values())[0])

    print("Protocol comparison:")
    print(f"{'Protocol':<15} {'Energy(mJ)':<12} {'Efficiency':<12} {'Delivery':<10} {'Relative'}")
    print("-" * 60)

    for protocol_name, result in results.items():
        energy_mj = result['energy_consumed'] * 1000
        efficiency = result['energy_efficiency']
        pdr = result['packet_delivery_ratio']

        # Relative performance vs baseline (energy ratio)
        if baseline['energy_consumed'] > 0:
            energy_ratio = result['energy_consumed'] / baseline['energy_consumed']
            relative_perf = f"{energy_ratio:.2f}x energy vs baseline"
        else:
            relative_perf = "N/A"

        print(f"{protocol_name:<15} {energy_mj:<12.3f} {efficiency:<12.1f} {pdr:<10.3f} {relative_perf}")

    # Sanity checks
    print(f"\n[CHECK] Sanity checks")

    issues = []

    # Check energy variation
    energies = [r['energy_consumed'] for r in results.values() if r['energy_consumed'] > 0]
    if energies:
        max_energy = max(energies)
        min_energy = min(energies)
        energy_ratio = max_energy / min_energy if min_energy > 0 else float('inf')

        if energy_ratio > 10:
            issues.append(f"Energy difference too large: {energy_ratio:.1f}x")
        elif energy_ratio < 1.1:
            issues.append(f"Energy difference too small: {energy_ratio:.2f}x")
        else:
            print(f" - Energy variation acceptable: {energy_ratio:.2f}x")

    # Check delivery ratio
    pdrs = [r['packet_delivery_ratio'] for r in results.values()]
    if any(pdr > 0.99 for pdr in pdrs):
        issues.append("Some protocols have too-high delivery ratio (>99%)")

    if any(pdr < 0.5 for pdr in pdrs):
        issues.append("Some protocols have too-low delivery ratio (<50%)")

    if issues:
        for issue in issues:
            print(f" - {issue}")
    else:
        print(" - All metrics are within reasonable ranges")


def test_multi_round_comparison():
    """Multi-round comparison"""

    print(f"\n[COMPARE] Multi-round protocol comparison")
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
        ('AERIS', lambda: AerisProtocol(config))
    ]

    for protocol_name, protocol_factory in protocols:
        print(f"\n[RUN] Testing {protocol_name} ({max_rounds} rounds):")

        try:
            protocol = protocol_factory()

            if protocol_name == 'AERIS':
                # AERIS multi-round path
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
                # LEACH/PEGASIS multi-round path
                result = protocol.run_simulation(max_rounds=max_rounds)
                total_energy_consumed = result['total_energy_consumed']
                total_packets_sent = result.get('additional_metrics', {}).get('total_packets_sent', 0)
                total_packets_received = result.get('additional_metrics', {}).get('total_packets_received', 0)
                network_lifetime = result['network_lifetime']
                alive_nodes = len([n for n in protocol.nodes if n.is_alive])

            # Compute metrics
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

            print(f"   Network lifetime: {network_lifetime} rounds")
            print(f"   Total packets sent: {total_packets_sent}")
            print(f"   Total packets received: {total_packets_received}")
            print(f"   Total energy: {total_energy_consumed:.3f} J")
            print(f"   Energy efficiency: {energy_efficiency:.1f} packets/J")
            print(f"   Delivery ratio: {packet_delivery_ratio:.3f}")
            print(f"   Alive nodes: {alive_nodes}")

        except Exception as e:
            print(f"   [ERROR] {protocol_name} test failed: {e}")
            import traceback
            traceback.print_exc()

    return results


def save_results(single_round_results, multi_round_results):
    """Save test results"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = {
        'timestamp': timestamp,
        'test_description': 'Protocol comparison after fixed energy model',
        'energy_model': 'CC2420_TELOSB_Fixed',
        'single_round_comparison': single_round_results,
        'multi_round_comparison': multi_round_results
    }

    # Save to results directory
    os.makedirs('../results', exist_ok=True)
    filename = f'../results/fixed_protocol_comparison_{timestamp}.json'

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVED] Results written to: {filename}")
    return filename


def main():
    """Main entry"""

    print("[START] Fixed-protocol comparison test")
    print("=" * 60)
    print("Goal: Evaluate protocol performance with the fixed energy model")
    print("Fix: CC2420 energy params 208.8/225.6 nJ/bit")
    print()

    # 1. Single-round comparison
    single_round_results = test_single_round_comparison()

    if single_round_results:
        analyze_results(single_round_results)

    # 2. Multi-round comparison
    multi_round_results = test_multi_round_comparison()

    # 3. Save results
    if single_round_results or multi_round_results:
        save_results(single_round_results, multi_round_results)

    print(f"\n[SUMMARY]")
    print("=" * 30)
    print(" - Energy model fixed")
    print(" - Protocol comparison complete")
    print(" - Results saved")

    print(f"\nNext steps:")
    print("1. Analyze performance differences after the fix")
    print("2. Validate the sanity of the results")
    print("3. Write a paper based on real data")


if __name__ == "__main__":
    main()
