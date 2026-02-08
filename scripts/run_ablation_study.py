#!/usr/bin/env python3
"""
AERIS消融实验脚本
测试各模块对性能的贡献：
1. 完整AERIS
2. 无Gateway模块
3. 无CAS模块
4. 无Skeleton模块
5. 无Safety Fallback
6. 基线（全部关闭）

n=30 seeds，符合统计显著性要求
"""

import sys
import os
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import numpy as np
from datetime import datetime
from typing import Dict

# 实验配置
SEEDS = list(range(42001, 42031))  # 30 seeds
NODE_COUNTS = [100, 200, 500]
ROUND_COUNTS = [300, 500]

# 统一功率设置
UNIFIED_TX_POWER_DBM = 10.0

# 消融配置
ABLATION_CONFIGS = {
    'AERIS_full': {
        'enable_gateway': True,
        'enable_cas': True,
        'enable_skeleton': True,
        'safety_fallback_enabled': True,
    },
    'AERIS_no_gateway': {
        'enable_gateway': False,
        'enable_cas': True,
        'enable_skeleton': True,
        'safety_fallback_enabled': True,
    },
    'AERIS_no_cas': {
        'enable_gateway': True,
        'enable_cas': False,
        'enable_skeleton': True,
        'safety_fallback_enabled': True,
    },
    'AERIS_no_skeleton': {
        'enable_gateway': True,
        'enable_cas': True,
        'enable_skeleton': False,
        'safety_fallback_enabled': True,
    },
    'AERIS_no_safety': {
        'enable_gateway': True,
        'enable_cas': True,
        'enable_skeleton': True,
        'safety_fallback_enabled': False,
    },
    'AERIS_baseline': {
        'enable_gateway': False,
        'enable_cas': False,
        'enable_skeleton': False,
        'safety_fallback_enabled': False,
    },
}


def run_ablation_experiment(config_name: str, ablation_config: dict,
                            num_nodes: int, num_rounds: int,
                            seed: int, positions: list, channel) -> Dict:
    """运行单次消融实验"""
    import random
    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol

    random.seed(seed)
    np.random.seed(seed)
    channel.reset_rng(seed)

    result = {
        'config_name': config_name,
        'num_nodes': num_nodes,
        'num_rounds': num_rounds,
        'seed': seed,
        'ablation_config': ablation_config,
        'pdr_expected': 0.0,
        'pdr_attempted': 0.0,
        'source_packets_expected': 0,
        'bs_delivered': 0,
        'energy_mj': 0.0,
        'alive_nodes': 0,
        'error': None
    }

    try:
        config = NetworkConfig()
        config.num_nodes = num_nodes
        config.area_width = 200.0
        config.area_height = 200.0
        config.base_station_x = 100.0
        config.base_station_y = 200.0
        config.tx_power_dbm = UNIFIED_TX_POWER_DBM
        config.positions = positions
        config.force_environment = 'indoor_office'
        config.external_channel_model = channel

        # 提取消融参数（传递给AerisProtocol构造函数）
        enable_gateway = ablation_config.get('enable_gateway', True)
        enable_cas = ablation_config.get('enable_cas', True)
        enable_skeleton = ablation_config.get('enable_skeleton', True)

        # safety_fallback需要在协议实例化后设置
        safety_fallback = ablation_config.get('safety_fallback_enabled', True)

        proto = AerisProtocol(config, seed=seed,
                              enable_gateway=enable_gateway,
                              enable_cas=enable_cas,
                              enable_skeleton=enable_skeleton)
        proto.safety_fallback_enabled = safety_fallback
        res = proto.run_simulation(max_rounds=num_rounds)

        result['source_packets_expected'] = proto.source_packets_expected
        result['bs_delivered'] = proto.bs_delivered_total
        result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
        result['alive_nodes'] = res.get('final_alive_nodes', 0)

        if result['source_packets_expected'] > 0:
            result['pdr_expected'] = result['bs_delivered'] / result['source_packets_expected']
            result['pdr_attempted'] = result['pdr_expected']

    except Exception as e:
        import traceback
        result['error'] = f"{str(e)}\n{traceback.format_exc()}"

    return result


def main():
    parser = argparse.ArgumentParser(description='AERIS消融实验')
    parser.add_argument('--full', action='store_true', help='完整模式(30 seeds)')
    parser.add_argument('--seeds', type=int, default=5, help='seed数量')
    parser.add_argument('--nodes', type=int, nargs='+', default=[100], help='节点数')
    parser.add_argument('--rounds', type=int, nargs='+', default=[300], help='轮数')
    args = parser.parse_args()

    if args.full:
        exp_seeds = SEEDS
        exp_nodes = NODE_COUNTS
        exp_rounds = ROUND_COUNTS
    else:
        exp_seeds = SEEDS[:args.seeds]
        exp_nodes = args.nodes
        exp_rounds = args.rounds

    print("=" * 60)
    print("AERIS消融实验")
    print(f"模式: {'完整(n=30)' if args.full else '验证'}")
    print(f"Seeds: {len(exp_seeds)}, Nodes: {exp_nodes}, Rounds: {exp_rounds}")
    print(f"消融配置数: {len(ABLATION_CONFIGS)}")
    print("=" * 60)

    all_results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    from realistic_channel_model import RealisticChannelModel, EnvironmentType

    total_exp = len(exp_seeds) * len(exp_nodes) * len(exp_rounds) * len(ABLATION_CONFIGS)
    completed = 0

    for nodes in exp_nodes:
        for rounds in exp_rounds:
            for seed in exp_seeds:
                np.random.seed(seed)
                positions = [(np.random.uniform(0, 200), np.random.uniform(0, 200))
                             for _ in range(nodes)]
                channel = RealisticChannelModel(EnvironmentType.INDOOR_OFFICE)

                for config_name, ablation_config in ABLATION_CONFIGS.items():
                    completed += 1
                    print(f"[{completed}/{total_exp}] {config_name} N={nodes} "
                          f"R={rounds} seed={seed}")

                    res = run_ablation_experiment(
                        config_name, ablation_config, nodes, rounds,
                        seed, positions, channel)
                    all_results.append(res)

                    if res['error']:
                        print(f"    ERROR: {res['error'][:100]}")
                    else:
                        print(f"    PDR_exp={res['pdr_expected']:.4f}")

    # 保存结果
    output_file = f"results/ablation_study_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'experiment_type': 'ablation_study',
            'primary_metric': 'pdr_expected',
            'config': {
                'seeds': exp_seeds,
                'node_counts': exp_nodes,
                'round_counts': exp_rounds,
                'ablation_configs': ABLATION_CONFIGS
            },
            'raw_results': all_results
        }, f, indent=2)

    # 打印汇总
    print("\n" + "=" * 60)
    print("消融实验汇总 (主指标: pdr_expected):")
    for config_name in ABLATION_CONFIGS.keys():
        config_results = [r for r in all_results
                         if r['config_name'] == config_name and not r['error']]
        if config_results:
            pdrs = [r['pdr_expected'] for r in config_results]
            energies = [r['energy_mj'] for r in config_results]
            print(f"  {config_name}:")
            print(f"    PDR={np.mean(pdrs):.4f}±{np.std(pdrs):.4f}")
            print(f"    Energy={np.mean(energies):.1f}±{np.std(energies):.1f} mJ")

    print(f"\n结果已保存: {output_file}")


if __name__ == "__main__":
    main()
