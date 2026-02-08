#!/usr/bin/env python3
"""
AERIS消融实验 - 并行版本
使用multiprocessing加速，精简实验规模
"""

import sys
import os
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import numpy as np
from datetime import datetime
from multiprocessing import Pool, cpu_count
from functools import partial

SEEDS = list(range(42001, 42031))
UNIFIED_TX_POWER_DBM = 10.0

ABLATION_CONFIGS = {
    'AERIS_full': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_gateway': {'enable_gateway': False, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_cas': {'enable_gateway': True, 'enable_cas': False, 'enable_skeleton': True, 'safety_fallback_enabled': True},
    'AERIS_no_skeleton': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': False, 'safety_fallback_enabled': True},
    'AERIS_no_safety': {'enable_gateway': True, 'enable_cas': True, 'enable_skeleton': True, 'safety_fallback_enabled': False},
    'AERIS_baseline': {'enable_gateway': False, 'enable_cas': False, 'enable_skeleton': False, 'safety_fallback_enabled': False},
}

# 场景配置 - 用于触发不同CAS模式
SCENARIO_CONFIGS = {
    'default': {
        'num_nodes': 100, 'area_size': 200.0, 'tx_power_dbm': 10.0,
        'environment': 'indoor_office', 'description': '默认场景'
    },
    'sparse_lowpower': {
        'num_nodes': 200, 'area_size': 400.0, 'tx_power_dbm': 5.0,
        'environment': 'outdoor_suburban', 'description': '稀疏低功率-触发CHAIN/TWO_HOP'
    },
    'dense_indoor': {
        'num_nodes': 300, 'area_size': 200.0, 'tx_power_dbm': 10.0,
        'environment': 'indoor_factory', 'description': '密集室内-触发Skeleton'
    },
    'ultra_sparse': {
        'num_nodes': 100, 'area_size': 500.0, 'tx_power_dbm': 3.0,
        'environment': 'outdoor_suburban', 'description': '极端稀疏低功率'
    },
    'mega_dense': {
        'num_nodes': 500, 'area_size': 200.0, 'tx_power_dbm': 10.0,
        'environment': 'indoor_factory', 'description': '大规模密集'
    },
}


def run_single(args):
    """单次实验（供并行调用）- 带诊断信息"""
    config_name, ablation_config, num_nodes, num_rounds, seed, scenario_cfg = args

    import random
    random.seed(seed)
    np.random.seed(seed)

    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol
    from realistic_channel_model import RealisticChannelModel, EnvironmentType

    # 从场景配置获取参数
    area_size = scenario_cfg.get('area_size', 200.0)
    tx_power = scenario_cfg.get('tx_power_dbm', 10.0)
    env_name = scenario_cfg.get('environment', 'indoor_office')

    env_map = {
        'indoor_office': EnvironmentType.INDOOR_OFFICE,
        'indoor_factory': EnvironmentType.INDOOR_FACTORY,
        'outdoor_urban': EnvironmentType.OUTDOOR_URBAN,
        'outdoor_suburban': EnvironmentType.OUTDOOR_SUBURBAN,
    }

    positions = [(np.random.uniform(0, area_size), np.random.uniform(0, area_size)) for _ in range(num_nodes)]
    channel = RealisticChannelModel(env_map.get(env_name, EnvironmentType.INDOOR_OFFICE))
    channel.reset_rng(seed)

    result = {
        'config_name': config_name,
        'num_nodes': num_nodes,
        'num_rounds': num_rounds,
        'seed': seed,
        'pdr_expected': 0.0,
        'energy_mj': 0.0,
        'error': None,
        # 诊断字段 (per RULES.md §5)
        'diag_flags': ablation_config.copy(),
        'diag_cas_modes': None,
        'diag_has_gateway': None,
        'diag_has_skeleton': None,
        'diag_safety_overrides': None,
        # 新增诊断字段
        'gateway_uplink_attempts': 0,
        'gateway_uplink_success': 0,
        'skeleton_backbone_size': 0,
        'skeleton_assignments': 0,
        'cas_total_decisions': 0,
    }

    try:
        config = NetworkConfig()
        config.num_nodes = num_nodes
        config.area_width = config.area_height = area_size
        config.base_station_x = area_size / 2
        config.base_station_y = area_size
        config.tx_power_dbm = tx_power
        config.positions = positions
        config.force_environment = env_name
        config.external_channel_model = channel

        # 断言：确保配置正确传入
        enable_gw = ablation_config.get('enable_gateway', True)
        enable_cas = ablation_config.get('enable_cas', True)
        enable_skel = ablation_config.get('enable_skeleton', True)
        safety_fb = ablation_config.get('safety_fallback_enabled', True)

        proto = AerisProtocol(config, seed=seed,
                              enable_gateway=enable_gw,
                              enable_cas=enable_cas,
                              enable_skeleton=enable_skel,
                              verbose=False)
        proto.safety_fallback_enabled = safety_fb

        # 运行时断言
        assert proto.enable_gateway == enable_gw, f"Gateway flag mismatch"
        assert proto.enable_cas == enable_cas, f"CAS flag mismatch"
        assert proto.enable_skeleton == enable_skel, f"Skeleton flag mismatch"
        assert proto.safety_fallback_enabled == safety_fb, f"Safety flag mismatch"

        res = proto.run_simulation(max_rounds=num_rounds)

        if proto.source_packets_expected > 0:
            result['pdr_expected'] = proto.bs_delivered_total / proto.source_packets_expected
        result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000

        # 收集诊断信息 (per RULES.md §5)
        result['diag_cas_modes'] = dict(proto.cas_mode_usage_stats) if hasattr(proto, 'cas_mode_usage_stats') else {}
        result['diag_has_gateway'] = hasattr(proto, 'gateway_selector')
        result['diag_has_skeleton'] = hasattr(proto, 'skeleton_selector')
        result['diag_safety_overrides'] = proto.cas_mode_usage_stats.get('safety_override', 0) if hasattr(proto, 'cas_mode_usage_stats') else 0

        # 新增诊断字段 (per RULES.md §5)
        # Gateway uplink 统计 (使用协议内部正确属性名)
        if hasattr(proto, 'gateway_uplink_attempts_total'):
            result['gateway_uplink_attempts'] = proto.gateway_uplink_attempts_total
        if hasattr(proto, 'gateway_uplink_success_total'):
            result['gateway_uplink_success'] = proto.gateway_uplink_success_total

        # Skeleton 统计
        if hasattr(proto, 'skeleton_selector') and proto.skeleton_selector is not None:
            if hasattr(proto.skeleton_selector, 'backbone_size'):
                result['skeleton_backbone_size'] = proto.skeleton_selector.backbone_size
            if hasattr(proto.skeleton_selector, 'total_assignments'):
                result['skeleton_assignments'] = proto.skeleton_selector.total_assignments

        # CAS 总决策数
        if hasattr(proto, 'cas_mode_usage_stats'):
            cas_stats = proto.cas_mode_usage_stats
            result['cas_total_decisions'] = sum([
                cas_stats.get('DIRECT', 0),
                cas_stats.get('CHAIN', 0),
                cas_stats.get('TWO_HOP', 0)
            ])

    except Exception as e:
        import traceback
        result['error'] = f"{str(e)}\n{traceback.format_exc()}"

    return result


def main():
    parser = argparse.ArgumentParser(description='并行消融实验')
    parser.add_argument('--seeds', type=int, default=30, help='seed数量')
    parser.add_argument('--nodes', type=int, default=0, help='节点数(0=使用场景默认)')
    parser.add_argument('--rounds', type=int, default=300, help='轮数')
    parser.add_argument('--workers', type=int, default=0, help='并行数(0=auto)')
    parser.add_argument('--scenario', type=str, default='default',
                        choices=list(SCENARIO_CONFIGS.keys()),
                        help='场景: default/sparse_lowpower/dense_indoor')
    args = parser.parse_args()

    # 获取场景配置
    scenario_cfg = SCENARIO_CONFIGS[args.scenario]
    num_nodes = args.nodes if args.nodes > 0 else scenario_cfg['num_nodes']

    exp_seeds = SEEDS[:args.seeds]
    workers = args.workers if args.workers > 0 else max(1, cpu_count() - 2)

    print(f"场景: {args.scenario} - {scenario_cfg['description']}")
    print(f"参数: N={num_nodes}, area={scenario_cfg['area_size']}m, "
          f"tx={scenario_cfg['tx_power_dbm']}dBm, env={scenario_cfg['environment']}")

    # 构建任务列表
    tasks = []
    for config_name, ablation_config in ABLATION_CONFIGS.items():
        for seed in exp_seeds:
            tasks.append((config_name, ablation_config, num_nodes, args.rounds, seed, scenario_cfg))

    print(f"消融实验: {len(tasks)}任务, {workers}进程")

    # 并行执行
    with Pool(workers) as pool:
        results = pool.map(run_single, tasks)

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_tier = 'publication' if len(exp_seeds) >= 30 else 'diagnostic'

    # 获取git commit
    git_commit = "unknown"
    try:
        import subprocess
        git_commit = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=os.path.dirname(__file__)
        ).decode().strip()[:8]
    except Exception:
        pass

    output_file = f"results/ablation_{args.scenario}_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'git_commit': git_commit,
            'experiment_type': 'ablation',
            'run_tier': run_tier,
            'primary_metric': 'pdr_expected',
            'environment': scenario_cfg['environment'],
            'tx_power_dbm': scenario_cfg['tx_power_dbm'],
            'scenario': args.scenario,
            'config': {
                'seeds': exp_seeds,
                'node_counts': [num_nodes],
                'round_counts': [args.rounds],
                'dropout_rates': [0.0],
                'area_size': scenario_cfg['area_size'],
                'ablation_configs': list(ABLATION_CONFIGS.keys())
            },
            'raw_results': results
        }, f, indent=2)

    # 汇总 + 诊断
    print("\n" + "=" * 60)
    print("消融实验结果汇总 (含诊断):")
    print("=" * 60)
    for cfg in ABLATION_CONFIGS.keys():
        cfg_res = [r for r in results if r['config_name'] == cfg and not r.get('error')]
        if cfg_res:
            pdrs = [r['pdr_expected'] for r in cfg_res]
            energies = [r['energy_mj'] for r in cfg_res]
            # 诊断统计
            gw_count = sum(1 for r in cfg_res if r.get('diag_has_gateway'))
            skel_count = sum(1 for r in cfg_res if r.get('diag_has_skeleton'))
            safety_total = sum(r.get('diag_safety_overrides', 0) for r in cfg_res)
            # CAS模式统计
            cas_direct = sum(r.get('diag_cas_modes', {}).get('DIRECT', 0) for r in cfg_res)
            cas_chain = sum(r.get('diag_cas_modes', {}).get('CHAIN', 0) for r in cfg_res)
            cas_twohop = sum(r.get('diag_cas_modes', {}).get('TWO_HOP', 0) for r in cfg_res)

            # 新增诊断统计
            gw_attempts = sum(r.get('gateway_uplink_attempts', 0) for r in cfg_res)
            gw_success = sum(r.get('gateway_uplink_success', 0) for r in cfg_res)
            skel_backbone = sum(r.get('skeleton_backbone_size', 0) for r in cfg_res)
            skel_assign = sum(r.get('skeleton_assignments', 0) for r in cfg_res)
            cas_total = sum(r.get('cas_total_decisions', 0) for r in cfg_res)

            print(f"\n{cfg}:")
            print(f"  PDR={np.mean(pdrs):.4f}±{np.std(pdrs):.4f}, Energy={np.mean(energies):.0f}mJ")
            print(f"  [诊断] Gateway创建:{gw_count}/{len(cfg_res)}, Skeleton创建:{skel_count}/{len(cfg_res)}")
            print(f"  [诊断] CAS模式: DIRECT={cas_direct}, CHAIN={cas_chain}, TWO_HOP={cas_twohop}")
            print(f"  [诊断] Safety覆盖次数: {safety_total}")
            print(f"  [诊断] Gateway上行: {gw_attempts}尝试/{gw_success}成功")
            print(f"  [诊断] Skeleton: backbone={skel_backbone}, assignments={skel_assign}")
            print(f"  [诊断] CAS总决策: {cas_total}")

    print(f"\n结果已保存: {output_file}")


if __name__ == "__main__":
    main()
