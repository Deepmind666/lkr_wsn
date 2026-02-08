#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0诊断埋点快速验证脚本
验证新增字段是否正确输出
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol

def main():
    cfg = NetworkConfig(num_nodes=50, area_width=100, area_height=100,
                        initial_energy=2.0, packet_size=512)

    proto = AerisProtocol(cfg, enable_cas=True, enable_fairness=True,
                          enable_gateway=True, verbose=False, seed=12345)

    res = proto.run_simulation(max_rounds=30)

    # 验证P0字段
    am = res.get('additional_metrics', {})

    print("=== P0.1 CAS诊断埋点 ===")
    print(f"  cas_switch_count: {am.get('cas_switch_count')}")
    print(f"  cas_total_decisions: {am.get('cas_total_decisions')}")
    print(f"  cas_switch_rate: {am.get('cas_switch_rate'):.4f}")
    print(f"  cas_confidence_mean: {am.get('cas_confidence_mean'):.4f}")
    print(f"  cas_mode_usage_stats: {am.get('cas_mode_usage_stats')}")

    print("\n=== P0.2 特征分布统计 ===")
    fs = am.get('cas_feature_stats', {})
    for feat in ['energy', 'link', 'dist_bs', 'radius', 'density']:
        s = fs.get(feat, {})
        print(f"  {feat}: min={s.get('min',0):.3f} mean={s.get('mean',0):.3f} p95={s.get('p95',0):.3f} count={s.get('count',0)}")

    print("\n=== P0.3 权重追踪 ===")
    ew = am.get('effective_weights', {})
    print(f"  w_direct_energy: {ew.get('w_direct_energy')}")
    print(f"  w_direct_link: {ew.get('w_direct_link')}")
    print(f"  ema_alpha: {ew.get('ema_alpha')}")
    print(f"  lambda_uncertainty: {ew.get('lambda_uncertainty')}")
    ss = am.get('stage_feature_scaling', {})
    print(f"  stage_weights_active: {ss.get('stage_weights_active')}")

    print("\n=== P0.4 PDR口径 ===")
    pm = am.get('pdr_metadata', {})
    print(f"  reliability_mode: {pm.get('reliability_mode')}")
    print(f"  force_ctp_reliable: {pm.get('force_ctp_reliable')}")
    print(f"  pdr_end2end_raw: {pm.get('pdr_end2end_raw'):.4f}")

    rm = res.get('config', {}).get('runtime', {})
    print(f"\n=== run_metadata ===")
    print(f"  reliability_mode: {rm.get('reliability_mode')}")
    print(f"  force_ctp_reliable: {rm.get('force_ctp_reliable')}")

    # 验证关键假设
    print("\n=== 验证结果 ===")
    errors = []
    if am.get('cas_total_decisions', 0) == 0:
        errors.append("cas_total_decisions为0")
    if not fs:
        errors.append("cas_feature_stats为空")
    if not ew:
        errors.append("effective_weights为空")
    if pm.get('reliability_mode') is None:
        errors.append("pdr_metadata缺失reliability_mode")

    if errors:
        print(f"  FAIL: {errors}")
        return 1
    else:
        print("  PASS: 所有P0字段正确输出")
        return 0

if __name__ == '__main__':
    sys.exit(main())
