#!/usr/bin/env python3
"""
环境敏感性实验脚本
测试AERIS在不同环境下的性能：
1. indoor_office (室内办公)
2. indoor_factory (室内工厂)
3. outdoor_urban (室外城市)
4. outdoor_rural (室外农村)

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
NODE_COUNTS = [100, 200]
ROUND_COUNTS = [300]
UNIFIED_TX_POWER_DBM = 10.0

# 环境类型
ENVIRONMENTS = [
    'indoor_office',
    'indoor_factory',
    'outdoor_urban',
    'outdoor_suburban'
]

# 协议列表
PROTOCOLS = ['AERIS', 'LEACH', 'PEGASIS', 'HEED', 'TEEN']


def run_env_experiment(protocol: str, environment: str,
                       num_nodes: int, num_rounds: int,
                       seed: int, positions: list) -> Dict:
    """运行单次环境敏感性实验"""
    import random
    from realistic_channel_model import RealisticChannelModel, EnvironmentType

    random.seed(seed)
    np.random.seed(seed)

    # 环境映射
    env_map = {
        'indoor_office': EnvironmentType.INDOOR_OFFICE,
        'indoor_factory': EnvironmentType.INDOOR_FACTORY,
        'outdoor_urban': EnvironmentType.OUTDOOR_URBAN,
        'outdoor_suburban': EnvironmentType.OUTDOOR_SUBURBAN,
    }

    result = {
        'protocol': protocol,
        'environment': environment,
        'num_nodes': num_nodes,
        'num_rounds': num_rounds,
        'seed': seed,
        'pdr_expected': 0.0,
        'source_packets_expected': 0,
        'bs_delivered': 0,
        'energy_mj': 0.0,
        'alive_nodes': 0,
        'error': None
    }

    try:
        channel = RealisticChannelModel(env_map[environment])
        channel.reset_rng(seed)

        if protocol == 'AERIS':
            result = run_aeris(num_nodes, num_rounds, seed,
                              channel, positions, environment, result)
        elif protocol == 'LEACH':
            result = run_leach(num_nodes, num_rounds, seed,
                              channel, positions, result)
        elif protocol == 'PEGASIS':
            result = run_pegasis(num_nodes, num_rounds, seed,
                                channel, positions, result)
        elif protocol == 'HEED':
            result = run_heed(num_nodes, num_rounds, seed,
                              channel, positions, result)
        elif protocol == 'TEEN':
            result = run_teen(num_nodes, num_rounds, seed,
                              channel, positions, result)

        if result['source_packets_expected'] > 0:
            result['pdr_expected'] = (result['bs_delivered'] /
                                      result['source_packets_expected'])

    except Exception as e:
        import traceback
        result['error'] = f"{str(e)}\n{traceback.format_exc()}"

    return result


def run_aeris(num_nodes, num_rounds, seed, channel, positions, env, result):
    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol

    config = NetworkConfig()
    config.num_nodes = num_nodes
    config.area_width = 200.0
    config.area_height = 200.0
    config.base_station_x = 100.0
    config.base_station_y = 200.0
    config.tx_power_dbm = UNIFIED_TX_POWER_DBM
    config.positions = positions
    config.force_environment = env
    config.external_channel_model = channel

    proto = AerisProtocol(config, seed=seed)
    res = proto.run_simulation(max_rounds=num_rounds)

    result['source_packets_expected'] = proto.source_packets_expected
    result['bs_delivered'] = proto.bs_delivered_total
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('final_alive_nodes', 0)
    return result


def run_leach(num_nodes, num_rounds, seed, channel, positions, result):
    from baseline_protocols.leach_protocol import LEACHProtocol, LEACHNode

    nodes = [LEACHNode(i, positions[i][0], positions[i][1])
             for i in range(num_nodes)]
    proto = LEACHProtocol(nodes, (100, 200),
                          tx_power_dbm=UNIFIED_TX_POWER_DBM,
                          channel_model=channel)
    res = proto.run_simulation(num_rounds)

    result['source_packets_expected'] = proto.source_packets_expected
    result['bs_delivered'] = proto.total_bs_delivered
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('alive_nodes', 0)
    return result


def run_pegasis(num_nodes, num_rounds, seed, channel, positions, result):
    from baseline_protocols.pegasis_protocol import PEGASISProtocol, PEGASISNode

    nodes = [PEGASISNode(i, positions[i][0], positions[i][1])
             for i in range(num_nodes)]
    proto = PEGASISProtocol(nodes, (100, 200),
                            tx_power_dbm=UNIFIED_TX_POWER_DBM,
                            channel_model=channel)
    res = proto.run_simulation(num_rounds)

    result['source_packets_expected'] = proto.source_packets_expected
    result['bs_delivered'] = proto.total_bs_delivered
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('alive_nodes', 0)
    return result


def main():
    parser = argparse.ArgumentParser(description='环境敏感性实验')
    parser.add_argument('--full', action='store_true', help='完整模式')
    parser.add_argument('--seeds', type=int, default=5, help='seed数量')
    args = parser.parse_args()

    if args.full:
        exp_seeds = SEEDS
        exp_nodes = NODE_COUNTS
        exp_rounds = ROUND_COUNTS
    else:
        exp_seeds = SEEDS[:args.seeds]
        exp_nodes = [100]
        exp_rounds = [300]

    print("=" * 60)
    print("环境敏感性实验")
    print(f"模式: {'完整(n=30)' if args.full else '验证'}")
    print(f"Seeds: {len(exp_seeds)}, Envs: {len(ENVIRONMENTS)}")
    print("=" * 60)

    all_results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    total = (len(exp_seeds) * len(exp_nodes) * len(exp_rounds) *
             len(ENVIRONMENTS) * len(PROTOCOLS))
    completed = 0

    for nodes in exp_nodes:
        for rounds in exp_rounds:
            for seed in exp_seeds:
                np.random.seed(seed)
                positions = [(np.random.uniform(0, 200),
                             np.random.uniform(0, 200))
                             for _ in range(nodes)]

                for env in ENVIRONMENTS:
                    for proto in PROTOCOLS:
                        completed += 1
                        print(f"[{completed}/{total}] {proto} {env} "
                              f"N={nodes} seed={seed}")

                        res = run_env_experiment(
                            proto, env, nodes, rounds, seed, positions)
                        all_results.append(res)

                        if res['error']:
                            print(f"    ERROR")
                        else:
                            print(f"    PDR={res['pdr_expected']:.4f}")

    # 保存结果
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

    output_file = f"results/env_sensitivity_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'git_commit': git_commit,
            'experiment_type': 'env_sensitivity',
            'run_tier': run_tier,
            'primary_metric': 'pdr_expected',
            'environment': 'multiple',
            'tx_power_dbm': UNIFIED_TX_POWER_DBM,
            'config': {
                'seeds': exp_seeds,
                'node_counts': exp_nodes,
                'round_counts': ROUND_COUNTS,
                'dropout_rates': [0.0],
                'environments': ENVIRONMENTS,
                'protocols': PROTOCOLS
            },
            'raw_results': all_results
        }, f, indent=2)

    # 打印汇总
    print("\n" + "=" * 60)
    print("环境敏感性汇总:")
    for env in ENVIRONMENTS:
        print(f"\n{env}:")
        for proto in PROTOCOLS:
            results = [r for r in all_results
                      if r['environment'] == env
                      and r['protocol'] == proto
                      and not r['error']]
            if results:
                pdrs = [r['pdr_expected'] for r in results]
                print(f"  {proto}: PDR={np.mean(pdrs):.4f}±{np.std(pdrs):.4f}")

    print(f"\n结果已保存: {output_file}")


if __name__ == "__main__":
    main()
