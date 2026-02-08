#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS integrated test script

Purpose: verify that AERIS integrated routing system works as expected
Includes:
1. Basic functionality test
2. Initial comparison with LEACH/PEGASIS
3. Metrics validation

Author: AERIS Research Team
Date: 2025-01-30
Version: 1.0
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import json
from typing import Dict, List
from aeris_protocol import AerisProtocol
from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform


def test_basic_functionality():
    """Basic functionality test"""

    print("Start AERIS basic functionality test")
    print("=" * 50)

    # Create the same network configuration
    config = NetworkConfig(
        num_nodes=20,
        area_width=50,
        area_height=50,
        initial_energy=1.0,
        packet_size=1024,
        base_station_x=25,
        base_station_y=25
    )

    try:
        # Create protocol instance
        protocol = AerisProtocol(config)

        print(f"Protocol instance created successfully")
        print(f"   Node count: {len(protocol.nodes)}")
        print(f"   Environment: {protocol.current_environment.value}")
        print(f"   Energy model: {protocol.energy_model.platform.value}")

        # Run simulation
        result = protocol.run_simulation(max_rounds=100)

        print(f"\nBasic functionality results:")
        print(f"   Network lifetime: {result['network_lifetime']} rounds")
        print(f"   Total energy: {result['total_energy_consumed']:.6f} J")
        print(f"   Energy efficiency: {result['energy_efficiency']:.1f} packets/J")
        print(f"   Packet delivery ratio: {result['packet_delivery_ratio']:.3f}")
        print(f"   Final alive nodes: {result['final_alive_nodes']}")
        print(f"   Execution time: {result['execution_time']:.3f} s")

        return True, result

    except Exception as e:
        print(f"Basic functionality test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def test_three_protocol_comparison():
    """Compare three protocols"""

    print("\nThree-protocol initial comparison")
    print("=" * 50)

    # Create config
    config = NetworkConfig(
        num_nodes=30,
        area_width=100,
        area_height=100,
        initial_energy=2.0,
        packet_size=1024
    )

    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    protocols = [
        ('LEACH', LEACHProtocol),
        ('PEGASIS', PEGASISProtocol),
        ('AERIS', AerisProtocol)
    ]

    results = {}

    for protocol_name, protocol_class in protocols:
        print(f"\nRunning {protocol_name} protocol...")

        try:
            if protocol_name == 'AERIS':
                protocol = protocol_class(config)
            else:
                protocol = protocol_class(config, energy_model)

            # Run
            start_time = time.time()
            result = protocol.run_simulation(max_rounds=500)
            execution_time = time.time() - start_time

            results[protocol_name] = {
                'network_lifetime': result['network_lifetime'],
                'total_energy_consumed': result['total_energy_consumed'],
                'energy_efficiency': result['energy_efficiency'],
                'packet_delivery_ratio': result['packet_delivery_ratio'],
                'final_alive_nodes': result['final_alive_nodes'],
                'execution_time': execution_time
            }

            print(f"   {protocol_name} finished")
            print(f"      Lifetime: {result['network_lifetime']} rounds")
            print(f"      Energy: {result['total_energy_consumed']:.3f} J")
            print(f"      Efficiency: {result['energy_efficiency']:.1f} packets/J")
            print(f"      PDR: {result['packet_delivery_ratio']:.3f}")

        except Exception as e:
            print(f"   {protocol_name} failed: {str(e)}")
            results[protocol_name] = None

    return results


def analyze_comparison_results(results: Dict):
    """Analyze comparison results"""

    print("\nProtocol comparison results")
    print("=" * 50)

    # Filter valid
    valid_results = {k: v for k, v in results.items() if v is not None}

    if len(valid_results) < 2:
        print("Not enough valid results to compare")
        return

    # Table header
    print(f"{'Protocol':<25} {'Lifetime(r)':<12} {'Energy(J)':<12} {'Eff(p/J)':<12} {'PDR':<8}")
    print("-" * 70)

    for protocol_name, result in valid_results.items():
        print(f"{protocol_name:<25} "
              f"{result['network_lifetime']:<12} "
              f"{result['total_energy_consumed']:<12.3f} "
              f"{result['energy_efficiency']:<12.1f} "
              f"{result['packet_delivery_ratio']:<8.3f}")

    # Best performers
    print(f"\nBest performers:")

    best_lifetime = max(valid_results.items(), key=lambda x: x[1]['network_lifetime'])
    best_energy_eff = max(valid_results.items(), key=lambda x: x[1]['energy_efficiency'])
    best_pdr = max(valid_results.items(), key=lambda x: x[1]['packet_delivery_ratio'])

    print(f"   Longest lifetime: {best_lifetime[0]} ({best_lifetime[1]['network_lifetime']} rounds)")
    print(f"   Highest efficiency: {best_energy_eff[0]} ({best_energy_eff[1]['energy_efficiency']:.1f} packets/J)")
    print(f"   Highest PDR: {best_pdr[0]} ({best_pdr[1]['packet_delivery_ratio']:.3f})")

    # AERIS summary
    if 'AERIS' in valid_results:
        aeris_result = valid_results['AERIS']

        print(f"\nAERIS summary:")

        other_protocols = {k: v for k, v in valid_results.items() if k != 'AERIS'}

        if other_protocols:
            avg_lifetime = sum(r['network_lifetime'] for r in other_protocols.values()) / len(other_protocols)
            avg_energy_eff = sum(r['energy_efficiency'] for r in other_protocols.values()) / len(other_protocols)
            avg_pdr = sum(r['packet_delivery_ratio'] for r in other_protocols.values()) / len(other_protocols)

            lifetime_improvement = (aeris_result['network_lifetime'] - avg_lifetime) / avg_lifetime * 100
            energy_improvement = (aeris_result['energy_efficiency'] - avg_energy_eff) / avg_energy_eff * 100
            pdr_improvement = (aeris_result['packet_delivery_ratio'] - avg_pdr) / avg_pdr * 100

            print(f"   vs average:")
            print(f"     Lifetime: {lifetime_improvement:+.1f}%")
            print(f"     Efficiency: {energy_improvement:+.1f}%")
            print(f"     PDR: {pdr_improvement:+.1f}%")


def save_test_results(basic_result, comparison_results):
    """Save test results"""

    timestamp = time.strftime("%Y%m%d_%H%M%S")

    test_results = {
        'timestamp': timestamp,
        'basic_functionality_test': basic_result,
        'three_protocol_comparison': comparison_results,
        'test_summary': {
            'basic_test_passed': basic_result is not None,
            'protocols_tested': len([r for r in comparison_results.values() if r is not None]),
            'aeris_working': 'AERIS' in comparison_results and comparison_results['AERIS'] is not None
        }
    }

    # Save into results directory (adjacent to project root)
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
    os.makedirs(results_dir, exist_ok=True)

    filename = f"{results_dir}/aeris_test_{timestamp}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=True)

    print(f"\nTest results saved: {filename}")


def main():
    """Main"""

    print("AERIS integrated protocol test")
    print("=" * 60)
    print("Purpose: verify AERIS protocol functionality and metrics")
    print("Time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()

    # 1. Basic functionality test
    basic_success, basic_result = test_basic_functionality()

    if not basic_success:
        print("\nBasic functionality test failed. Stop further tests.")
        return

    # 2. Three-protocol comparison
    comparison_results = test_three_protocol_comparison()

    # 3. Analyze results
    analyze_comparison_results(comparison_results)

    # 4. Save results
    save_test_results(basic_result, comparison_results)

    print("\n" + "=" * 60)
    print("AERIS protocol tests finished")


if __name__ == "__main__":
    main()
