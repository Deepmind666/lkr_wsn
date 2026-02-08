#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0诊断埋点严格验证脚本 v3 - 深度完善版
新增:
1. PDR数值正确性验证（包统计一致性）
2. 能耗合理性验证（边界检查）
3. CAS决策口径验证（CH数量与决策数关系）
4. 多seed规模验证支持
"""
import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol


# CASConfig核心参数（排除eps数值稳定常量）
FULL_CASCONFIG_WEIGHTS = [
    'w_direct_energy', 'w_direct_link', 'w_direct_dist_bs',
    'w_direct_radius', 'w_direct_density', 'w_direct_fair',
    'w_chain_energy', 'w_chain_link', 'w_chain_dist_bs',
    'w_chain_radius', 'w_chain_density', 'w_chain_fair',
    'w_twohop_energy', 'w_twohop_link', 'w_twohop_dist_bs',
    'w_twohop_radius', 'w_twohop_density', 'w_twohop_fair',
    'ema_alpha', 'lambda_uncertainty', 'twohop_tail_threshold',
    'min_confidence', 'uncertainty_conf_threshold',
]


def run_single_experiment(num_nodes: int, max_rounds: int, seed: int,
                          enable_cas: bool, enable_gateway: bool) -> dict:
    """运行单次实验，返回完整结果"""
    cfg = NetworkConfig(
        num_nodes=num_nodes,
        area_width=100, area_height=100,
        initial_energy=2.0, packet_size=512
    )
    proto = AerisProtocol(
        cfg, verbose=False, seed=seed,
        enable_cas=enable_cas,
        enable_fairness=True,
        enable_gateway=enable_gateway
    )
    return proto.run_simulation(max_rounds=max_rounds)


def validate_pdr_correctness(am: dict, name: str) -> List[str]:
    """验证PDR数值正确性（包统计一致性）"""
    errors = []

    # 获取包统计
    source_total = am.get('source_packets_total', 0)
    bs_delivered = am.get('bs_delivered_total', 0)

    # PDR应等于 bs_delivered / source_total
    if source_total > 0:
        expected_pdr = bs_delivered / source_total
        pdr_raw = am.get('pdr_metadata', {}).get('pdr_end2end_raw', -1)
        if abs(expected_pdr - pdr_raw) > 1e-9:
            errors.append(
                f"[{name}] PDR计算错误: "
                f"bs/src={bs_delivered}/{source_total}={expected_pdr:.6f}, "
                f"pdr_raw={pdr_raw:.6f}"
            )

    # 包统计合理性
    if bs_delivered > source_total:
        errors.append(f"[{name}] 包统计异常: delivered({bs_delivered}) > source({source_total})")

    # 分段PDR一致性
    intra_attempts = am.get('cluster_to_ch_attempts_total', 0)
    intra_success = am.get('cluster_to_ch_success_total', 0)
    if intra_attempts > 0:
        intra_pdr = intra_success / intra_attempts
        reported_intra = am.get('cluster_to_ch_pdr_total', -1)
        if abs(intra_pdr - reported_intra) > 1e-9:
            errors.append(f"[{name}] intra_pdr计算错误: {intra_pdr:.6f} != {reported_intra:.6f}")

    return errors


def validate_ch_count_reasonableness(am: dict, name: str,
                                      num_nodes: int, actual_rounds: int) -> List[str]:
    """验证CH数量合理性（边界检查）- 原"能耗合理性"已重命名"""
    errors = []

    avg_ch = am.get('average_cluster_heads', 0)

    # CH数量合理性：应在 [1, num_nodes/2] 范围内
    if avg_ch > 0:
        if avg_ch > num_nodes / 2:
            errors.append(f"[{name}] CH数量异常: avg_ch={avg_ch:.2f} > nodes/2={num_nodes/2}")
        if avg_ch < 1:
            errors.append(f"[{name}] CH数量异常: avg_ch={avg_ch:.2f} < 1")

    return errors


def validate_cas_decision_caliber(am: dict, name: str,
                                  num_nodes: int, actual_rounds: int) -> List[str]:
    """验证CAS决策口径（使用实际轮数而非max_rounds）"""
    errors = []

    total_decisions = am.get('cas_total_decisions', 0)
    avg_ch = am.get('average_cluster_heads', 0)

    # 决策口径：per-CH-per-round，使用实际执行轮数
    # 预期决策数 ≈ avg_ch * actual_rounds（允许±50%误差，因CH可能无成员）
    if avg_ch > 0 and total_decisions > 0 and actual_rounds > 0:
        expected_decisions = avg_ch * actual_rounds
        ratio = total_decisions / expected_decisions
        if ratio < 0.3 or ratio > 3.0:
            errors.append(
                f"[{name}] CAS决策数异常: "
                f"total={total_decisions}, expected≈{expected_decisions:.0f}, "
                f"ratio={ratio:.2f}, actual_rounds={actual_rounds}"
            )

    return errors


def validate_variant_v3(am: dict, enable_cas: bool, name: str,
                        pdr_top: float, num_nodes: int, max_rounds: int,
                        actual_rounds: int) -> List[str]:
    """v3验证：包含数值正确性，使用实际轮数"""
    errors = []

    # === 原有字段一致性验证 ===
    # P0.1 CAS诊断埋点
    required_p01 = ['cas_mode_usage_stats', 'cas_switch_count',
                    'cas_total_decisions', 'cas_decisions_note',
                    'cas_switch_rate', 'cas_confidence_mean']
    for field in required_p01:
        if field not in am:
            errors.append(f"[{name}] P0.1缺失: {field}")

    # cas_decisions_note内容验证
    note = am.get('cas_decisions_note')
    if note is None:
        errors.append(f"[{name}] cas_decisions_note为None")
    elif note != 'per-CH-per-round, not per-round':
        errors.append(f"[{name}] cas_decisions_note内容异常")

    # P0.2 特征统计（7项）
    if 'cas_feature_stats' not in am:
        errors.append(f"[{name}] P0.2缺失: cas_feature_stats")
    elif enable_cas:
        fs = am['cas_feature_stats']
        for feat in ['energy', 'link', 'dist_bs', 'radius', 'density']:
            if feat not in fs or fs[feat].get('count', 0) == 0:
                errors.append(f"[{name}] P0.2核心特征{feat}无样本")
        for feat in ['fairness', 'tail_max']:
            if feat not in fs:
                errors.append(f"[{name}] P0.2扩展特征{feat}缺失")

    # P0.3 权重追踪
    if enable_cas:
        ew = am.get('effective_weights', {})
        ewi = am.get('effective_weights_initial', {})
        missing_final = [w for w in FULL_CASCONFIG_WEIGHTS if w not in ew]
        missing_init = [w for w in FULL_CASCONFIG_WEIGHTS if w not in ewi]
        if missing_final:
            errors.append(f"[{name}] P0.3最终权重不完整")
        if missing_init:
            errors.append(f"[{name}] P0.3初始权重不完整")

    # P0.4 PDR口径
    pm = am.get('pdr_metadata', {})
    pdr_raw = pm.get('pdr_end2end_raw', -1)
    if abs(pdr_top - pdr_raw) > 1e-6:
        errors.append(f"[{name}] PDR不一致: top={pdr_top:.6f}, raw={pdr_raw:.6f}")

    # safety_override分层
    if enable_cas:
        usage = am.get('cas_mode_usage_stats', {})
        total = am.get('cas_total_decisions', 0)
        safety = usage.get('safety_override', 0)
        direct = usage.get('DIRECT', 0)
        mode_sum = sum(usage.get(m, 0) for m in ['DIRECT', 'CHAIN', 'TWO_HOP'])

        if safety > direct:
            errors.append(f"[{name}] safety_override > DIRECT")
        if total > 0 and mode_sum != total:
            errors.append(f"[{name}] mode_sum != total")

        # switch_rate一致性
        switch_count = am.get('cas_switch_count', 0)
        switch_rate = am.get('cas_switch_rate', 0)
        expected_rate = (switch_count / max(1, total - 1)) if total > 1 else 0.0
        if abs(switch_rate - expected_rate) > 1e-6:
            errors.append(f"[{name}] switch_rate计算错误")

    # weights_changed_rounds
    changed_rounds = am.get('weights_changed_rounds', [])
    change_count = am.get('weights_change_count', -1)
    if change_count != len(changed_rounds):
        errors.append(f"[{name}] weights_change_count不一致")

    # === 新增数值正确性验证 ===
    errors.extend(validate_pdr_correctness(am, name))
    errors.extend(validate_ch_count_reasonableness(am, name, num_nodes, actual_rounds))
    errors.extend(validate_cas_decision_caliber(am, name, num_nodes, actual_rounds))

    return errors


def run_multi_seed_validation(num_nodes: int, max_rounds: int,
                              seeds: List[int], out_dir: str) -> Tuple[List[str], str]:
    """多seed规模验证"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    all_results = []
    all_errors = []

    variants = {
        'FULL': {'enable_cas': True, 'enable_gateway': True},
        '-CAS': {'enable_cas': False, 'enable_gateway': True},
        '-GW':  {'enable_cas': True, 'enable_gateway': False},
    }

    for seed in seeds:
        for vname, vopts in variants.items():
            res = run_single_experiment(
                num_nodes, max_rounds, seed,
                vopts['enable_cas'], vopts['enable_gateway']
            )
            am = res.get('additional_metrics', {})
            pdr = res.get('packet_delivery_ratio_end2end', 0)
            actual_rounds = res.get('rounds_completed', max_rounds)

            all_results.append({
                'seed': seed,
                'variant': vname,
                'pdr_end2end': pdr,
                'actual_rounds': actual_rounds,
                'additional_metrics': am,
            })

            errors = validate_variant_v3(
                am, vopts['enable_cas'], f"{vname}/seed{seed}",
                pdr, num_nodes, max_rounds, actual_rounds
            )
            all_errors.extend(errors)

    # 保存结果
    json_path = os.path.join(out_dir, f'p0_validation_v3_{timestamp}.json')
    with open(json_path, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'config': {
                'num_nodes': num_nodes,
                'max_rounds': max_rounds,
                'seeds': seeds,
            },
            'results': all_results,
        }, f, indent=2)

    return all_errors, json_path


def validate_from_json(json_path: str, num_nodes: int, max_rounds: int) -> List[str]:
    """从JSON文件回读并验证（恢复v2严谨性）"""
    with open(json_path, 'r') as f:
        data = json.load(f)

    errors = []
    for item in data.get('results', []):
        vname = item.get('variant', 'unknown')
        seed = item.get('seed', 0)
        name = f"{vname}/seed{seed}"
        enable_cas = 'CAS' not in vname or vname == 'FULL'
        am = item.get('additional_metrics', {})
        pdr = item.get('pdr_end2end', 0)
        actual_rounds = item.get('actual_rounds', max_rounds)

        var_errors = validate_variant_v3(
            am, enable_cas, name, pdr, num_nodes, max_rounds, actual_rounds
        )
        errors.extend(var_errors)

    return errors


def main():
    parser = argparse.ArgumentParser(description='P0严格验证 v3')
    parser.add_argument('--nodes', type=int, default=50, help='节点数')
    parser.add_argument('--rounds', type=int, default=50, help='轮数')
    parser.add_argument('--seeds', type=int, default=1, help='seed数量')
    parser.add_argument('--scale', action='store_true', help='规模验证模式')
    args = parser.parse_args()

    out_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'v2.0_20260201')
    os.makedirs(out_dir, exist_ok=True)

    if args.scale:
        # 规模验证：200节点/300轮/30seeds
        num_nodes, max_rounds = 200, 300
        seeds = list(range(30))
        print(f"=== P0规模验证 v3 ({num_nodes}节点/{max_rounds}轮/{len(seeds)}seeds) ===")
    else:
        num_nodes, max_rounds = args.nodes, args.rounds
        seeds = list(range(args.seeds))
        print(f"=== P0严格验证 v3 ({num_nodes}节点/{max_rounds}轮/{len(seeds)}seeds) ===")

    print("步骤1: 运行实验...")
    errors, json_path = run_multi_seed_validation(num_nodes, max_rounds, seeds, out_dir)
    print(f"  已保存: {json_path}")

    print("\n步骤2: 从JSON回读验证...")
    json_errors = validate_from_json(json_path, num_nodes, max_rounds)
    errors.extend(json_errors)

    if errors:
        print(f"\n验证失败 ({len(errors)}个错误):")
        for e in errors[:20]:  # 最多显示20个
            print(f"  - {e}")
        if len(errors) > 20:
            print(f"  ... 还有{len(errors)-20}个错误")
        return 1

    print(f"\n验证通过 ({len(seeds)*3}个实验)")
    print("\n=== 严谨性声明 ===")
    print("[PASS] 已验证: 字段完整性、数值一致性、PDR正确性、CH数量合理性")
    print("   - CASConfig核心参数: 23项（排除eps）")
    print("   - 特征统计: 7项（5核心+2扩展）")
    print("   - JSON回读验证: 已启用")
    if args.scale:
        print("[PASS] 规模验证: 200节点/300轮/30seeds")
    else:
        print(f"[WARN] 限制: {num_nodes}节点/{max_rounds}轮/{len(seeds)}seeds")
    return 0


if __name__ == '__main__':
    sys.exit(main())
