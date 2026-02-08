#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速验证测试 - 10轮×10节点

验证修复后的代码是否正常工作

Author: AERIS Research Team
Date: 2025-11-04
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.aeris_protocol import AerisProtocol
from src.benchmark_protocols import NetworkConfig
import json

def run_quick_test():
    """运行快速验证测试"""

    print("="*70)
    print("[TEST] Quick Verification Test (10 rounds, 10 nodes)")
    print("="*70)
    print()

    # 配置：10节点，10轮，快速测试
    config = NetworkConfig(
        num_nodes=10,
        area_width=50,
        area_height=50,
        initial_energy=2.0,  # 2J足够10轮
        base_station_x=25,
        base_station_y=45,
        packet_size=512
    )

    try:
        # 测试1: 默认配置
        print("[INFO] Test 1: Default AERIS")
        protocol = AerisProtocol(
            config,
            enable_cas=True,
            enable_fairness=True,
            enable_gateway=True,
            enable_skeleton=True,
            verbose=False,
            seed=42
        )

        result = protocol.run_simulation(max_rounds=10)

        print(f"[OK] Simulation completed successfully")
        print(f"     Network lifetime: {result['network_lifetime']} rounds")
        print(f"     PDR (hop-level): {result['packet_delivery_ratio']:.2%}")
        print(f"     PDR (end-to-end): {result['packet_delivery_ratio_end2end']:.2%}")
        print(f"     Energy consumed: {result['total_energy_consumed']:.3f} J")

        # 检查诊断信息
        if 'hop_count_distribution' in result['additional_metrics']:
            hop_dist = result['additional_metrics']['hop_count_distribution']
            print(f"     Hop count distribution: {hop_dist}")
        else:
            print(f"     [WARN] Hop count distribution not found")

        if 'cas_mode_usage_stats' in result['additional_metrics']:
            cas_stats = result['additional_metrics']['cas_mode_usage_stats']
            print(f"     CAS mode usage: {cas_stats}")
        else:
            print(f"     [WARN] CAS mode usage stats not found")

        # 测试2: 只CAS，无Gateway/Skeleton
        print("\n[INFO] Test 2: CAS only (no Gateway/Skeleton)")
        protocol2 = AerisProtocol(
            config,
            enable_cas=True,
            enable_fairness=True,
            enable_gateway=False,
            enable_skeleton=False,
            verbose=False,
            seed=42
        )

        result2 = protocol2.run_simulation(max_rounds=10)
        print(f"[OK] CAS-only test completed")
        print(f"     PDR: {result2['packet_delivery_ratio_end2end']:.2%}")

        # 测试3: 无CAS（测试消融）
        print("\n[INFO] Test 3: No CAS (ablation test)")
        protocol3 = AerisProtocol(
            config,
            enable_cas=False,
            enable_fairness=True,
            enable_gateway=True,
            enable_skeleton=True,
            verbose=False,
            seed=42
        )

        result3 = protocol3.run_simulation(max_rounds=10)
        print(f"[OK] No-CAS test completed")
        print(f"     PDR: {result3['packet_delivery_ratio_end2end']:.2%}")

        # 保存结果
        test_results = {
            'test1_default': result,
            'test2_cas_only': result2,
            'test3_no_cas': result3
        }

        output_file = "results/quick_verification_test.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)

        print(f"\n[SUCCESS] All tests passed!")
        print(f"[INFO] Results saved to: {output_file}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = run_quick_test()

    if success:
        print("\n" + "="*70)
        print("[SUCCESS] Quick Verification Test PASSED")
        print("="*70)
        print("\nCode修复验证成功！可以进行完整实验。")
    else:
        print("\n" + "="*70)
        print("[FAIL] Quick Verification Test FAILED")
        print("="*70)
        print("\n请检查错误信息并修复。")
        sys.exit(1)

if __name__ == "__main__":
    main()
