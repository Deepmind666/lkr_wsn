#!/usr/bin/env python3
"""
CAS Weight Sweep Experiment - Test if CHAIN/TWO_HOP can be triggered

Goal: Find weight configurations that enable CAS multi-mode selection.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import subprocess
import numpy as np
import random
from datetime import datetime
from itertools import product


SEEDS = [42001, 42002, 42003, 42004, 42005]  # smoke test


def get_git_commit():
    """获取当前 git commit hash."""
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=os.path.dirname(__file__)
        ).decode().strip()[:8]
    except:
        return 'unknown'

# Weight configurations to test - FULL CASConfig override
# 每个配置包含完整的 CASConfig 字段，确保实验可复现
WEIGHT_CONFIGS = [
    {
        'name': 'baseline_default',
        'description': 'CASConfig 默认值，作为对照组',
        # 规则触发控制
        'rule_override': True,
        'chain_density_threshold': 0.6,
        'chain_radius_threshold': 0.45,
        'chain_dist_min': 0.3,
        'chain_dist_max': 0.6,
        'twohop_dist_threshold': 0.6,
        'twohop_link_max': 0.55,
        'twohop_tail_threshold': 0.6,
        # 不确定性惩罚
        'lambda_uncertainty': 0.0,
        'uncertainty_conf_threshold': 0.4,
        # DIRECT 权重
        'w_direct_energy': 0.35,
        'w_direct_link': 0.65,
        'w_direct_dist_bs': -0.25,
        'w_direct_radius': -0.05,
        'w_direct_density': 0.10,
        'w_direct_fair': -0.05,
        # CHAIN 权重
        'w_chain_energy': 0.30,
        'w_chain_link': 0.40,
        'w_chain_dist_bs': 0.20,
        'w_chain_radius': 0.20,
        'w_chain_density': 0.20,
        'w_chain_fair': -0.05,
        # TWO_HOP 权重
        'w_twohop_energy': 0.20,
        'w_twohop_link': 0.25,
        'w_twohop_dist_bs': 0.50,
        'w_twohop_radius': 0.15,
        'w_twohop_density': 0.05,
        'w_twohop_fair': -0.05,
    },
    {
        'name': 'aggressive_multimode',
        'description': '激进多模式：同时降低 CHAIN 和 TWO_HOP 阈值',
        'rule_override': True,
        'chain_density_threshold': 0.30,
        'chain_radius_threshold': 0.25,
        'chain_dist_min': 0.15,
        'chain_dist_max': 0.75,
        'twohop_dist_threshold': 0.35,
        'twohop_link_max': 0.75,
        'twohop_tail_threshold': 0.35,
        'lambda_uncertainty': 0.0,
        'uncertainty_conf_threshold': 0.4,
        'w_direct_energy': 0.35,
        'w_direct_link': 0.65,
        'w_direct_dist_bs': -0.25,
        'w_direct_radius': -0.05,
        'w_direct_density': 0.10,
        'w_direct_fair': -0.05,
        'w_chain_energy': 0.30,
        'w_chain_link': 0.40,
        'w_chain_dist_bs': 0.20,
        'w_chain_radius': 0.20,
        'w_chain_density': 0.20,
        'w_chain_fair': -0.05,
        'w_twohop_energy': 0.20,
        'w_twohop_link': 0.25,
        'w_twohop_dist_bs': 0.50,
        'w_twohop_radius': 0.15,
        'w_twohop_density': 0.05,
        'w_twohop_fair': -0.05,
    },
    {
        'name': 'score_favor_chain',
        'description': '通过权重调整偏好 CHAIN（规则关闭）',
        'rule_override': False,
        'chain_density_threshold': 0.6,
        'chain_radius_threshold': 0.45,
        'chain_dist_min': 0.3,
        'chain_dist_max': 0.6,
        'twohop_dist_threshold': 0.6,
        'twohop_link_max': 0.55,
        'twohop_tail_threshold': 0.6,
        'lambda_uncertainty': 0.0,
        'uncertainty_conf_threshold': 0.4,
        'w_direct_energy': 0.20,
        'w_direct_link': 0.30,
        'w_direct_dist_bs': -0.40,
        'w_direct_radius': -0.10,
        'w_direct_density': 0.05,
        'w_direct_fair': -0.05,
        'w_chain_energy': 0.40,
        'w_chain_link': 0.50,
        'w_chain_dist_bs': 0.30,
        'w_chain_radius': 0.35,
        'w_chain_density': 0.35,
        'w_chain_fair': -0.05,
        'w_twohop_energy': 0.20,
        'w_twohop_link': 0.25,
        'w_twohop_dist_bs': 0.50,
        'w_twohop_radius': 0.15,
        'w_twohop_density': 0.05,
        'w_twohop_fair': -0.05,
    },
]


def run_single_config(seed, weight_cfg, scenario):
    """Run single experiment with specific CAS weights.

    修复漏洞：
    1. 强制初始化 CASSelector（不依赖 hasattr 检查）
    2. 全量覆盖 CASConfig 字段
    3. 记录规则触发诊断字段
    """
    np.random.seed(seed)
    random.seed(seed)

    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol
    from cas_selector import CASSelector, CASConfig

    config = NetworkConfig()
    config.num_nodes = scenario['num_nodes']
    config.area_width = scenario['area_width']
    config.area_height = scenario['area_height']
    config.base_station_x = scenario['area_width'] / 2
    config.base_station_y = scenario['area_height']
    config.tx_power_dbm = scenario['tx_power']

    result = {
        'weight_config': weight_cfg['name'],
        'weight_description': weight_cfg.get('description', ''),
        'scenario': scenario['name'],
        'seed': seed,
        'pdr_expected': 0.0,
        'cas_direct': 0,
        'cas_chain': 0,
        'cas_twohop': 0,
        'cas_rule_triggers': {'DIRECT': 0, 'CHAIN': 0, 'TWO_HOP': 0, 'NONE': 0},
        'cas_score_winners': {'DIRECT': 0, 'CHAIN': 0, 'TWO_HOP': 0},
        'cas_selector_initialized': False,
        'error': None,
    }

    try:
        proto = AerisProtocol(config, seed=seed, verbose=False,
                              enable_gateway=True,
                              enable_cas=True,
                              enable_skeleton=True)

        # 强制初始化 CASSelector 并全量覆盖配置
        cas_cfg = CASConfig()

        # 规则触发控制
        cas_cfg.rule_override = weight_cfg.get('rule_override', True)
        cas_cfg.chain_density_threshold = weight_cfg.get('chain_density_threshold', 0.6)
        cas_cfg.chain_radius_threshold = weight_cfg.get('chain_radius_threshold', 0.45)
        cas_cfg.chain_dist_min = weight_cfg.get('chain_dist_min', 0.3)
        cas_cfg.chain_dist_max = weight_cfg.get('chain_dist_max', 0.6)
        cas_cfg.twohop_dist_threshold = weight_cfg.get('twohop_dist_threshold', 0.6)
        cas_cfg.twohop_link_max = weight_cfg.get('twohop_link_max', 0.55)
        cas_cfg.twohop_tail_threshold = weight_cfg.get('twohop_tail_threshold', 0.6)

        # 不确定性惩罚
        cas_cfg.lambda_uncertainty = weight_cfg.get('lambda_uncertainty', 0.0)
        cas_cfg.uncertainty_conf_threshold = weight_cfg.get('uncertainty_conf_threshold', 0.4)

        # DIRECT 权重
        cas_cfg.w_direct_energy = weight_cfg.get('w_direct_energy', 0.35)
        cas_cfg.w_direct_link = weight_cfg.get('w_direct_link', 0.65)
        cas_cfg.w_direct_dist_bs = weight_cfg.get('w_direct_dist_bs', -0.25)
        cas_cfg.w_direct_radius = weight_cfg.get('w_direct_radius', -0.05)
        cas_cfg.w_direct_density = weight_cfg.get('w_direct_density', 0.10)
        cas_cfg.w_direct_fair = weight_cfg.get('w_direct_fair', -0.05)

        # CHAIN 权重
        cas_cfg.w_chain_energy = weight_cfg.get('w_chain_energy', 0.30)
        cas_cfg.w_chain_link = weight_cfg.get('w_chain_link', 0.40)
        cas_cfg.w_chain_dist_bs = weight_cfg.get('w_chain_dist_bs', 0.20)
        cas_cfg.w_chain_radius = weight_cfg.get('w_chain_radius', 0.20)
        cas_cfg.w_chain_density = weight_cfg.get('w_chain_density', 0.20)
        cas_cfg.w_chain_fair = weight_cfg.get('w_chain_fair', -0.05)

        # TWO_HOP 权重
        cas_cfg.w_twohop_energy = weight_cfg.get('w_twohop_energy', 0.20)
        cas_cfg.w_twohop_link = weight_cfg.get('w_twohop_link', 0.25)
        cas_cfg.w_twohop_dist_bs = weight_cfg.get('w_twohop_dist_bs', 0.50)
        cas_cfg.w_twohop_radius = weight_cfg.get('w_twohop_radius', 0.15)
        cas_cfg.w_twohop_density = weight_cfg.get('w_twohop_density', 0.05)
        cas_cfg.w_twohop_fair = weight_cfg.get('w_twohop_fair', -0.05)

        # 强制替换 CASSelector
        proto.cas_selector = CASSelector(cas_cfg)
        result['cas_selector_initialized'] = True

        proto.run_simulation(max_rounds=scenario['num_rounds'])

        if proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.bs_delivered_total / proto.source_packets_expected

        # CAS 模式使用统计
        if hasattr(proto, 'cas_mode_usage_stats'):
            stats = proto.cas_mode_usage_stats
            result['cas_direct'] = stats.get('DIRECT', 0)
            result['cas_chain'] = stats.get('CHAIN', 0)
            result['cas_twohop'] = stats.get('TWO_HOP', 0)

        # 规则触发诊断字段
        if hasattr(proto, 'cas_rule_trigger_counts'):
            result['cas_rule_triggers'] = dict(proto.cas_rule_trigger_counts)

        if hasattr(proto, 'cas_score_winner_counts'):
            result['cas_score_winners'] = dict(proto.cas_score_winner_counts)

    except Exception as e:
        result['error'] = str(e)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Full test (n=30)')
    args = parser.parse_args()

    seeds = list(range(42001, 42031)) if args.full else SEEDS
    run_tier = 'publication' if args.full else 'diagnostic'
    git_commit = get_git_commit()

    scenarios = [
        {
            'name': 'indoor_office',
            'num_nodes': 100,
            'area_width': 200.0,
            'area_height': 200.0,
            'tx_power': 10.0,
            'num_rounds': 300,
        },
        {
            'name': 'sparse_outdoor',
            'num_nodes': 50,
            'area_width': 300.0,
            'area_height': 300.0,
            'tx_power': 5.0,
            'num_rounds': 300,
        },
    ]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"CAS Weight Sweep Experiment")
    print(f"Seeds: {len(seeds)}, Configs: {len(WEIGHT_CONFIGS)}, Scenarios: {len(scenarios)}")
    print("=" * 60)

    all_results = []

    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")

        for weight_cfg in WEIGHT_CONFIGS:
            print(f"  Config: {weight_cfg['name']}", end=" ")

            cfg_results = []
            for seed in seeds:
                r = run_single_config(seed, weight_cfg, scenario)
                cfg_results.append(r)
                all_results.append(r)

            # Summary
            valid = [r for r in cfg_results if not r.get('error')]
            if valid:
                pdrs = [r['pdr_expected'] for r in valid]
                chain_total = sum(r['cas_chain'] for r in valid)
                twohop_total = sum(r['cas_twohop'] for r in valid)
                direct_total = sum(r['cas_direct'] for r in valid)

                print(f"PDR={np.mean(pdrs):.4f} | "
                      f"DIRECT={direct_total} CHAIN={chain_total} TWO_HOP={twohop_total}")
            else:
                print("ALL ERRORS")

    # Save results
    output_dir = 'results/mega_experiments'
    os.makedirs(output_dir, exist_ok=True)

    suffix = '_full' if args.full else '_smoke'
    outfile = os.path.join(output_dir, f"cas_weight_sweep{suffix}_{timestamp}.json")

    # §5 诊断字段聚合
    valid_results = [r for r in all_results if not r.get('error')]
    total_direct = sum(r.get('cas_direct', 0) for r in valid_results)
    total_chain = sum(r.get('cas_chain', 0) for r in valid_results)
    total_twohop = sum(r.get('cas_twohop', 0) for r in valid_results)
    cas_total = total_direct + total_chain + total_twohop

    # 规则触发统计聚合
    rule_triggers_agg = {'DIRECT': 0, 'CHAIN': 0, 'TWO_HOP': 0, 'NONE': 0}
    score_winners_agg = {'DIRECT': 0, 'CHAIN': 0, 'TWO_HOP': 0}
    for r in valid_results:
        rt = r.get('cas_rule_triggers', {})
        for k in rule_triggers_agg:
            rule_triggers_agg[k] += rt.get(k, 0)
        sw = r.get('cas_score_winners', {})
        for k in score_winners_agg:
            score_winners_agg[k] += sw.get(k, 0)

    output = {
        'timestamp': timestamp,
        'git_commit': git_commit,
        'experiment_type': 'cas_weight_sweep',
        'run_tier': run_tier,
        'primary_metric': 'pdr_expected',
        'environment': 'multiple',
        'tx_power_dbm': 'multiple',
        'config': {
            'seeds': seeds,
            'node_counts': [s['num_nodes'] for s in scenarios],
            'round_counts': [s['num_rounds'] for s in scenarios],
            'environments': [s['name'] for s in scenarios],
            'tx_powers_dbm': [s['tx_power'] for s in scenarios],
        },
        # §5 诊断字段
        'diag_cas_modes': {
            'DIRECT': total_direct,
            'CHAIN': total_chain,
            'TWO_HOP': total_twohop,
        },
        'cas_total_decisions': cas_total,
        'diag_rule_triggers': rule_triggers_agg,
        'diag_score_winners': score_winners_agg,
        'weight_configs': WEIGHT_CONFIGS,
        'scenarios': [s['name'] for s in scenarios],
        'raw_results': all_results,
    }

    with open(outfile, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved: {outfile}")

    # Final summary
    print("\n" + "=" * 60)
    print("SUMMARY: CHAIN/TWO_HOP Trigger Counts")
    print("-" * 60)

    for cfg in WEIGHT_CONFIGS:
        cfg_results = [r for r in all_results if r['weight_config'] == cfg['name']]
        chain = sum(r['cas_chain'] for r in cfg_results if not r.get('error'))
        twohop = sum(r['cas_twohop'] for r in cfg_results if not r.get('error'))
        direct = sum(r['cas_direct'] for r in cfg_results if not r.get('error'))
        total = chain + twohop + direct

        if total > 0:
            print(f"{cfg['name']:20s}: CHAIN={chain:5d} ({100*chain/total:5.1f}%) "
                  f"TWO_HOP={twohop:5d} ({100*twohop/total:5.1f}%)")
        else:
            print(f"{cfg['name']:20s}: NO CAS DECISIONS")


if __name__ == "__main__":
    main()
