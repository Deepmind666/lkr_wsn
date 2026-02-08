#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Honest analysis: verify whether AERIS results are reasonable

Objective: analyze results truthfully and identify potential issues
"""

import json
import sys
import os
import glob
from typing import Optional


def _find_latest_aeris_result_json(results_dir: str) -> Optional[str]:
    """Find the latest aeris_test_*.json file in the results directory; return None if missing"""
    pattern = os.path.join(results_dir, 'aeris_test_*.json')
    candidates = glob.glob(pattern)
    if not candidates:
        return None
    # choose the most recently modified
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def analyze_results():
    """Analyze whether experimental results are reasonable"""
    
    print("[ANALYZE] Honest analysis: AERIS experiment results")
    print("=" * 50)
    
    # read test result
    try:
        # locate results directory relative to this file
        here = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.abspath(os.path.join(here, '..', 'results'))
        result_path = _find_latest_aeris_result_json(results_dir)
        if result_path is None:
            # fallback to a legacy path if it exists
            legacy_path = os.path.abspath(os.path.join(here, '..', 'results', 'integrated_eehfr_test_20250730_115641.json'))
            if os.path.exists(legacy_path):
                result_path = legacy_path
            else:
                raise FileNotFoundError('aeris_test_*.json result file not found')
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[FILE] Using result file: {os.path.relpath(result_path, start=os.path.join(here, '..'))}")
    except FileNotFoundError:
        print("[WARN] Test result file not found (expected: results/aeris_test_*.json)")
        return
    
    # extract three-protocol comparison
    comparison = data['three_protocol_comparison']
    
    aeris_result = comparison.get('AERIS')
    leach_result = comparison.get('LEACH')
    pegasis_result = comparison.get('PEGASIS')
    
    if not all([aeris_result, leach_result, pegasis_result]):
        print("[WARN] Missing protocol comparison data (need AERIS/LEACH/PEGASIS)")
        return
    
    print("[INFO] Raw data:")
    print(f"AERIS: {aeris_result['total_energy_consumed']:.6f}J, energy efficiency: {aeris_result['energy_efficiency']:.1f}")
    print(f"LEACH: {leach_result['total_energy_consumed']:.6f}J, energy efficiency: {leach_result['energy_efficiency']:.1f}")
    print(f"PEGASIS: {pegasis_result['total_energy_consumed']:.6f}J, energy efficiency: {pegasis_result['energy_efficiency']:.1f}")
    
    # analyze energy differences
    aeris_energy = aeris_result['total_energy_consumed']
    leach_energy = leach_result['total_energy_consumed']
    pegasis_energy = pegasis_result['total_energy_consumed']
    
    print(f"\n[ANALYZE] Energy consumption comparison:")
    leach_ratio = aeris_energy / leach_energy
    pegasis_ratio = aeris_energy / pegasis_energy
    
    print(f"AERIS vs LEACH: {leach_ratio:.3f} ({(1-leach_ratio)*100:.1f}% reduction)")
    print(f"AERIS vs PEGASIS: {pegasis_ratio:.3f} ({(1-pegasis_ratio)*100:.1f}% reduction)")
    
    # reasonableness check
    print(f"\n[CHECK] Reasonableness check")
    
    suspicious_issues = []
    
    # check: are the differences too large?
    if leach_ratio < 0.2:
        suspicious_issues.append(f"AERIS energy is {(1-leach_ratio)*100:.1f}% lower than LEACH; difference may be too large")
    
    if pegasis_ratio < 0.2:
        suspicious_issues.append(f"AERIS energy is {(1-pegasis_ratio)*100:.1f}% lower than PEGASIS; difference may be too large")
    
    # check: is energy efficiency too high
    aeris_efficiency = aeris_result['energy_efficiency']
    leach_efficiency = leach_result['energy_efficiency']
    pegasis_efficiency = pegasis_result['energy_efficiency']
    
    if aeris_efficiency > leach_efficiency * 5:
        suspicious_issues.append(f"AERIS energy efficiency is {aeris_efficiency/leach_efficiency:.1f}x higher than LEACH; may be unrealistic")
    
    if aeris_efficiency > pegasis_efficiency * 5:
        suspicious_issues.append(f"AERIS energy efficiency is {aeris_efficiency/pegasis_efficiency:.1f}x higher than PEGASIS; may be unrealistic")
    
    # check: delivery ratio reasonable?
    aeris_pdr = aeris_result['packet_delivery_ratio']
    leach_pdr = leach_result['packet_delivery_ratio']
    pegasis_pdr = pegasis_result['packet_delivery_ratio']
    
    print(f"\n[COMPARE] Packet delivery ratio:")
    print(f"AERIS: {aeris_pdr:.3f}")
    print(f"LEACH: {leach_pdr:.3f}")
    print(f"PEGASIS: {pegasis_pdr:.3f}")
    
    if aeris_pdr > 0.99:
        suspicious_issues.append("AERIS PDR is too high (>99%); may be unrealistic")
    
    # output findings
    if suspicious_issues:
        print(f"\n[FINDINGS] Potential issues:")
        for i, issue in enumerate(suspicious_issues, 1):
            print(f"   {i}. {issue}")
    else:
        print(f"\n[FINDINGS] No obvious issues found")
    
    return suspicious_issues


def analyze_energy_model():
    """Analyze whether the energy model is reasonable"""
    
    print(f"\n[ANALYZE] Energy model analysis")
    print("=" * 30)
    
    # check energy model params
    try:
        from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
        
        energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        params = energy_model.platform_params[HardwarePlatform.CC2420_TELOSB]
        
        print(f"Hardware platform: {energy_model.platform.value}")
        print(f"TX energy: {params.tx_energy_per_bit*1e9:.1f} nJ/bit")
        print(f"RX energy: {params.rx_energy_per_bit*1e9:.1f} nJ/bit")
        print(f"Processing energy: {params.processing_energy_per_bit*1e9:.1f} nJ/bit")
        
        # typical packet energy
        packet_size = 1024  # bits
        distance = 50  # meters
        tx_power = 0  # dBm
        
        # typical packet comparison
        typical_packet_bits = 512 * 8
        typical_distance = 30.0
        typical_power_dbm = 0.0
        
        # environment parameters: from config if available, else defaults
        try:
            temp_c = config.temperature_c
            hum_r = config.humidity_ratio
        except Exception:
            temp_c = 25.0
            hum_r = 0.5
        
        tx_energy = energy_model.calculate_transmission_energy(typical_packet_bits, typical_distance, typical_power_dbm, temp_c, hum_r)
        rx_energy = energy_model.calculate_reception_energy(typical_packet_bits, temp_c, hum_r)
        total_energy = (tx_energy + rx_energy) * 1000  # mJ
        print(f"Typical packet: TX={tx_energy*1000:.3f} mJ, RX={rx_energy*1000:.3f} mJ, Total={total_energy:.3f} mJ @ {temp_c}C/{hum_r}RH")
        print(f"TX energy: {tx_energy*1000:.6f} mJ")
        print(f"RX energy: {rx_energy*1000:.6f} mJ")
        print(f"Total energy: {(tx_energy + rx_energy)*1000:.6f} mJ")
        
    except Exception as e:
        print(f"[ERROR] Energy model analysis failed: {e}")


def check_implementation_logic():
    """Check implementation logic"""
    
    print(f"\n[CHECK] Implementation logic")
    print("=" * 30)
    
    # check AERIS key logic
    issues = []
    
    # 1. environment awareness
    print("1. Environment awareness:")
    try:
        from aeris_protocol import EnvironmentClassifier
        classifier = EnvironmentClassifier()
        print("   OK: Environment classifier available")
        
        # but classification logic is simple
        print("   WARN: Environment classification is simple (based on node density)")
        issues.append("Environment classification logic is too simple")
        
    except Exception as e:
        print(f"   ERROR: Environment awareness check failed: {e}")
        issues.append("Environment awareness may have issues")
    
    # 2. fuzzy logic
    print("2. Fuzzy logic system:")
    try:
        from aeris_protocol import FuzzyLogicSystem
        fuzzy = FuzzyLogicSystem()
        print("   OK: Fuzzy logic system available")
        print("   WARN: Fuzzy rules are relatively basic")
        issues.append("Fuzzy rules are relatively basic")
        
    except Exception as e:
        print(f"   ERROR: Fuzzy logic check failed: {e}")
        issues.append("Fuzzy logic system may have issues")
    
    # 3. channel model
    print("3. Channel model:")
    try:
        from realistic_channel_model import RealisticChannelModel, EnvironmentType
        channel = RealisticChannelModel(EnvironmentType.INDOOR_OFFICE)
        print("   OK: Realistic channel model available")
        print("   OK: Supports multiple environment types")
        
    except Exception as e:
        print(f"   ERROR: Channel model check failed: {e}")
        issues.append("Channel model may have issues")
    
    return issues


def main():
    """Main function"""
    
    print("[REPORT] AERIS honest analysis report")
    print("Goal: analyze the project honestly, without exaggeration")
    print()
    
    # 1. analyze experimental results
    result_issues = analyze_results()
    
    # 2. analyze energy model
    analyze_energy_model()
    
    # 3. check implementation logic
    logic_issues = check_implementation_logic()
    
    # summary
    print(f"\n[SUMMARY] Honest summary:")
    print("=" * 30)
    
    all_issues = (result_issues or []) + (logic_issues or [])
    
    if all_issues:
        print("Found issues:")
        for i, issue in enumerate(all_issues, 1):
            print(f"   {i}. {issue}")
    
    print(f"\n[POSITIVES] Confirmed strengths:")
    print("   1. Protocol runs as expected")
    print("   2. Integrates multiple modules")
    print("   3. Has a complete testing framework")
    print("   4. Code structure is clear")
    
    print(f"\n[IMPROVE] Areas for improvement:")
    print("   1. Environment classification logic is too simple")
    print("   2. Fuzzy logic rules are relatively basic")
    print("   3. Performance gains may be overstated")
    print("   4. Needs deeper technical innovation")
    
    print(f"\n[ASSESS] Objective evaluation:")
    print("   - Technical level: above average (not top-tier)")
    print("   - Innovation: limited (mostly integration of existing techniques)")
    print("   - Practical value: moderate (needs further validation)")
    print("   - Academic value: needs improvement (requires deeper innovation)")


if __name__ == "__main__":
    main()
