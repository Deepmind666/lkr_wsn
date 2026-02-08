#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick verification script to test unified energy model modifications.

This script runs a small experiment (50 nodes × 50 rounds) to verify:
1. All baseline protocols can run with unified energy model
2. Energy consumption increases by expected factor (~4.2x)
3. Results are consistent with predictions

Expected results:
- PEGASIS: 4.52J → ~18.88J (4.2x increase)
- LEACH: 4.03J → ~16.85J (4.2x increase)
- HEED: 9.08J → ~38.0J (4.2x increase)
- TEEN: 7.92J → ~33.1J (4.2x increase)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import json
from datetime import datetime

# Import baseline protocols
from baseline_protocols.leach_protocol import LEACHProtocol, LEACHNode
from baseline_protocols.pegasis_protocol import PEGASISProtocol, PEGASISNode
from baseline_protocols.heed_protocol import HEEDProtocol, HEEDNode

def generate_uniform_topology(num_nodes: int, area_size: tuple) -> list:
    """Generate uniform random node positions."""
    np.random.seed(42)  # For reproducibility
    positions = []
    for i in range(num_nodes):
        x = np.random.uniform(0, area_size[0])
        y = np.random.uniform(0, area_size[1])
        positions.append((x, y))
    return positions

def run_leach_test(num_nodes: int = 50, max_rounds: int = 50,
                   use_unified: bool = True) -> dict:
    """Run LEACH protocol test."""
    print(f"\n{'='*60}")
    print(f"Testing LEACH (unified={use_unified})")
    print(f"{'='*60}")

    positions = generate_uniform_topology(num_nodes, (100, 100))
    nodes = [LEACHNode(i, x, y, initial_energy=2.0)
             for i, (x, y) in enumerate(positions)]
    base_station = (50.0, 175.0)

    protocol = LEACHProtocol(nodes, base_station,
                            desired_ch_percentage=0.1,
                            use_unified_energy_model=use_unified)
    results = protocol.run_simulation(max_rounds=max_rounds)

    return {
        'protocol': 'LEACH',
        'unified_model': use_unified,
        'total_energy': results['total_energy_consumed'],
        'pdr': results['packet_delivery_ratio_end2end'],
        'network_lifetime': results['network_lifetime'],
        'alive_nodes': results['alive_nodes']
    }

def run_pegasis_test(num_nodes: int = 50, max_rounds: int = 50,
                     use_unified: bool = True) -> dict:
    """Run PEGASIS protocol test."""
    print(f"\n{'='*60}")
    print(f"Testing PEGASIS (unified={use_unified})")
    print(f"{'='*60}")

    positions = generate_uniform_topology(num_nodes, (100, 100))
    nodes = [PEGASISNode(i, x, y, initial_energy=2.0)
             for i, (x, y) in enumerate(positions)]
    base_station = (50.0, 175.0)

    protocol = PEGASISProtocol(nodes, base_station,
                               use_unified_energy_model=use_unified)
    results = protocol.run_simulation(max_rounds=max_rounds)

    return {
        'protocol': 'PEGASIS',
        'unified_model': use_unified,
        'total_energy': results['total_energy_consumed'],
        'pdr': results['packet_delivery_ratio_end2end'],
        'network_lifetime': results['network_lifetime'],
        'alive_nodes': results['alive_nodes']
    }

def run_heed_test(num_nodes: int = 50, max_rounds: int = 50,
                  use_unified: bool = True) -> dict:
    """Run HEED protocol test."""
    print(f"\n{'='*60}")
    print(f"Testing HEED (unified={use_unified})")
    print(f"{'='*60}")

    positions = generate_uniform_topology(num_nodes, (100, 100))
    nodes = [HEEDNode(i, x, y, initial_energy=2.0)
             for i, (x, y) in enumerate(positions)]
    base_station = (50.0, 175.0)

    protocol = HEEDProtocol(nodes, base_station,
                           c_prob=0.05, cluster_radius=50.0,
                           use_unified_energy_model=use_unified)
    results = protocol.run_simulation(max_rounds=max_rounds)

    return {
        'protocol': 'HEED',
        'unified_model': use_unified,
        'total_energy': results['total_energy_consumed'],
        'pdr': results['packet_delivery_ratio_end2end'],
        'network_lifetime': results['network_lifetime'],
        'alive_nodes': results['alive_nodes']
    }

def analyze_results(results: list):
    """Analyze and compare results."""
    print(f"\n{'='*60}")
    print("VERIFICATION RESULTS")
    print(f"{'='*60}\n")

    # Group results by protocol
    protocol_results = {}
    for result in results:
        protocol_name = result['protocol']
        if protocol_name not in protocol_results:
            protocol_results[protocol_name] = {'legacy': None, 'unified': None}

        if result['unified_model']:
            protocol_results[protocol_name]['unified'] = result
        else:
            protocol_results[protocol_name]['legacy'] = result

    # Compare and print results
    print(f"{'Protocol':<12} {'Legacy Energy':<15} {'Unified Energy':<15} {'Ratio':<10} {'Expected':<10} {'Status':<10}")
    print("-" * 80)

    expected_ratio = 4.176  # 208.8 / 50.0
    tolerance = 0.5  # Allow ±0.5 variation

    all_passed = True

    for protocol_name in ['LEACH', 'PEGASIS', 'HEED']:
        if protocol_name not in protocol_results:
            continue

        legacy = protocol_results[protocol_name].get('legacy')
        unified = protocol_results[protocol_name].get('unified')

        if legacy and unified:
            legacy_energy = legacy['total_energy']
            unified_energy = unified['total_energy']
            ratio = unified_energy / legacy_energy

            # Check if ratio is within expected range
            expected_min = expected_ratio - tolerance
            expected_max = expected_ratio + tolerance
            passed = expected_min <= ratio <= expected_max
            status = "✅ PASS" if passed else "❌ FAIL"

            if not passed:
                all_passed = False

            print(f"{protocol_name:<12} {legacy_energy:<15.3f} {unified_energy:<15.3f} "
                  f"{ratio:<10.2f} {expected_ratio:<10.2f} {status:<10}")
        else:
            print(f"{protocol_name:<12} {'N/A':<15} {'N/A':<15} {'N/A':<10} {'N/A':<10} {'SKIP':<10}")

    print("\n" + "=" * 80)

    if all_passed:
        print("✅ VERIFICATION PASSED: Energy model unified successfully!")
        print(f"   All protocols show energy increase close to expected ratio ({expected_ratio:.2f}x)")
    else:
        print("❌ VERIFICATION FAILED: Some protocols show unexpected energy ratios")
        print("   Please check the energy model integration")

    print("=" * 80)

    # Detailed results
    print("\n" + "=" * 60)
    print("DETAILED RESULTS")
    print("=" * 60 + "\n")

    for result in results:
        model_type = "Unified (CC2420)" if result['unified_model'] else "Legacy (Simplified)"
        print(f"{result['protocol']} ({model_type}):")
        print(f"  Energy:   {result['total_energy']:.3f} J")
        print(f"  PDR:      {result['pdr']*100:.1f}%")
        print(f"  Lifetime: {result['network_lifetime']} rounds")
        print(f"  Alive:    {result['alive_nodes']} nodes")
        print()

    return all_passed

def main():
    """Main verification routine."""
    print("=" * 60)
    print("UNIFIED ENERGY MODEL VERIFICATION")
    print("=" * 60)
    print(f"Test configuration:")
    print(f"  - Nodes: 50")
    print(f"  - Rounds: 50")
    print(f"  - Area: 100m × 100m")
    print(f"  - Base station: (50, 175)")
    print(f"  - Initial energy: 2.0 J")
    print("=" * 60)

    results = []

    # Test each protocol with both legacy and unified energy models
    try:
        # LEACH
        results.append(run_leach_test(use_unified=False))
        results.append(run_leach_test(use_unified=True))

        # PEGASIS
        results.append(run_pegasis_test(use_unified=False))
        results.append(run_pegasis_test(use_unified=True))

        # HEED
        results.append(run_heed_test(use_unified=False))
        results.append(run_heed_test(use_unified=True))

    except Exception as e:
        print(f"\n❌ ERROR during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    # Analyze results
    verification_passed = analyze_results(results)

    # Save results
    output_file = os.path.join(os.path.dirname(__file__), '..', 'results',
                               'unified_energy_model_verification.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    output_data = {
        'timestamp': datetime.now().isoformat(),
        'test_config': {
            'num_nodes': 50,
            'max_rounds': 50,
            'area_size': [100, 100],
            'base_station': [50, 175],
            'initial_energy': 2.0
        },
        'results': results,
        'verification_passed': verification_passed
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return 0 if verification_passed else 1

if __name__ == '__main__':
    sys.exit(main())
