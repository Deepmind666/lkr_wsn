#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0诊断埋点消融实验 - 完整验证
输出到 results/v2.0_20260201/
包含所有P0字段的完整输出
"""
import os, sys, json
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol

VARIANTS = {
    'FULL': {'enable_cas': True, 'enable_fairness': True, 'enable_gateway': True},
    '-CAS': {'enable_cas': False, 'enable_fairness': True, 'enable_gateway': True},
    '-GW':  {'enable_cas': True, 'enable_fairness': True, 'enable_gateway': False},
}

def run_variant(name, opts, seed=12345):
    cfg = NetworkConfig(num_nodes=50, area_width=100, area_height=100,
                        initial_energy=2.0, packet_size=512)
    proto = AerisProtocol(cfg, verbose=False, seed=seed, **opts)
    res = proto.run_simulation(max_rounds=50)

    am = res.get('additional_metrics', {})
    return {
        'variant': name,
        'seed': seed,
        'pdr_end2end': res.get('packet_delivery_ratio_end2end', 0),
        'energy': res.get('total_energy_consumed', 0),
        # P0.1 CAS诊断埋点 - 完整字段
        'cas_mode_usage': am.get('cas_mode_usage_stats', {}),
        'cas_switch_count': am.get('cas_switch_count', 0),
        'cas_total_decisions': am.get('cas_total_decisions', 0),
        'cas_decisions_note': am.get('cas_decisions_note', 'per-CH-per-round'),
        'cas_switch_rate': am.get('cas_switch_rate', 0),
        'cas_confidence_mean': am.get('cas_confidence_mean', 0),
        'cas_confidence_min': am.get('cas_confidence_min', 0),
        # P0.2 特征分布统计
        'cas_feature_stats': am.get('cas_feature_stats', {}),
        # P0.3 权重追踪
        'effective_weights': am.get('effective_weights', {}),
        'effective_weights_initial': am.get('effective_weights_initial', {}),
        'weights_changed': am.get('weights_changed', False),
        'stage_feature_scaling': am.get('stage_feature_scaling', {}),
        # P0.4 PDR口径
        'pdr_metadata': am.get('pdr_metadata', {}),
    }

def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results = []
    for name, opts in VARIANTS.items():
        print(f"Running {name}...")
        r = run_variant(name, opts)
        results.append(r)
        print(f"  PDR={r['pdr_end2end']:.3f}, CAS={r['cas_mode_usage']}")

    out_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'v2.0_20260201')
    out_path = os.path.join(out_dir, f'ablation_p0_test_{timestamp}.json')
    with open(out_path, 'w') as f:
        json.dump({'timestamp': timestamp, 'variants': results}, f, indent=2)
    print(f"\nSaved to {out_path}")

if __name__ == '__main__':
    main()
