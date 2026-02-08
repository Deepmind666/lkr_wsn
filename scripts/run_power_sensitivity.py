#!/usr/bin/env python3
"""
功率敏感性实验脚本
测试不同发射功率对协议性能的影响：
- 功率范围: 0, 5, 10, 15, 20 dBm
- n=30 seeds
"""

import sys
import os
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import numpy as np
from datetime import datetime
from typing import Dict

SEEDS = list(range(42001, 42031))
NODE_COUNTS = [100, 200]
ROUND_COUNTS = [300]
TX_POWERS = [0, 5, 10, 15, 20]  # dBm
PROTOCOLS = ['AERIS', 'LEACH', 'PEGASIS']


def run_power_experiment(protocol: str, tx_power: float,
                         num_nodes: int, num_rounds: int,
                         seed: int, positions: list) -> Dict:
    """运行单次功率敏感性实验"""
    import random
    from realistic_channel_model import RealisticChannelModel, EnvironmentType

    random.seed(seed)
    np.random.seed(seed)

    result = {
        'protocol': protocol,
        'tx_power_dbm': tx_power,
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
        channel = RealisticChannelModel(EnvironmentType.INDOOR_OFFICE)
        channel.reset_rng(seed)

        if protocol == 'AERIS':
            result = _run_aeris(num_nodes, num_rounds, seed,
                               channel, positions, tx_power, result)
        elif protocol == 'LEACH':
            result = _run_leach(num_nodes, num_rounds, seed,
                               channel, positions, tx_power, result)
        elif protocol == 'PEGASIS':
            result = _run_pegasis(num_nodes, num_rounds, seed,
                                 channel, positions, tx_power, result)

        if result['source_packets_expected'] > 0:
            result['pdr_expected'] = (result['bs_delivered'] /
                                      result['source_packets_expected'])

    except Exception as e:
        import traceback
        result['error'] = f"{str(e)}\n{traceback.format_exc()}"

    return result


def _run_aeris(num_nodes, num_rounds, seed, channel, positions, tx_power, result):
    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol

    config = NetworkConfig()
    config.num_nodes = num_nodes
    config.area_width = 200.0
    config.area_height = 200.0
    config.base_station_x = 100.0
    config.base_station_y = 200.0
    config.tx_power_dbm = tx_power
    config.positions = positions
    config.force_environment = 'indoor_office'
    config.external_channel_model = channel

    proto = AerisProtocol(config, seed=seed)
    res = proto.run_simulation(max_rounds=num_rounds)

    result['source_packets_expected'] = proto.source_packets_expected
    result['bs_delivered'] = proto.bs_delivered_total
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('final_alive_nodes', 0)
    return result


def _run_leach(num_nodes, num_rounds, seed, channel, positions, tx_power, result):
    from baseline_protocols.leach_protocol import LEACHProtocol, LEACHNode

    nodes = [LEACHNode(i, positions[i][0], positions[i][1])
             for i in range(num_nodes)]
    proto = LEACHProtocol(nodes, (100, 200),
                          tx_power_dbm=tx_power,
                          channel_model=channel)
    res = proto.run_simulation(num_rounds)

    result['source_packets_expected'] = proto.source_packets_expected
    result['bs_delivered'] = proto.total_bs_delivered
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('alive_nodes', 0)
    return result


def _run_pegasis(num_nodes, num_rounds, seed, channel, positions, tx_power, result):
    from baseline_protocols.pegasis_protocol import PEGASISProtocol, PEGASISNode

    nodes = [PEGASISNode(i, positions[i][0], positions[i][1])
             for i in range(num_nodes)]
    proto = PEGASISProtocol(nodes, (100, 200),
                            tx_power_dbm=tx_power,
                            channel_model=channel)
    res = proto.run_simulation(num_rounds)

    result['source_packets_expected'] = proto.source_packets_expected
    result['bs_delivered'] = proto.total_bs_delivered
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('alive_nodes', 0)
    return result


def main():
    parser = argparse.ArgumentParser(description='功率敏感性实验')
    parser.add_argument('--full', action='store_true', help='完整模式')
    parser.add_argument('--seeds', type=int, default=5, help='seed数量')
    args = parser.parse_args()

    if args.full:
        exp_seeds = SEEDS
        exp_nodes = NODE_COUNTS
    else:
        exp_seeds = SEEDS[:args.seeds]
        exp_nodes = [100]

    print("=" * 60)
    print("功率敏感性实验")
    print(f"模式: {'完整(n=30)' if args.full else '验证'}")
    print(f"Seeds: {len(exp_seeds)}, Powers: {TX_POWERS}")
    print("=" * 60)

    all_results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    total = len(exp_seeds) * len(exp_nodes) * len(TX_POWERS) * len(PROTOCOLS)
    completed = 0

    for nodes in exp_nodes:
        for seed in exp_seeds:
            np.random.seed(seed)
            positions = [(np.random.uniform(0, 200), np.random.uniform(0, 200))
                         for _ in range(nodes)]
            for tx_power in TX_POWERS:
                for proto in PROTOCOLS:
                    completed += 1
                    print(f"[{completed}/{total}] {proto} P={tx_power}dBm N={nodes}")
                    res = run_power_experiment(proto, tx_power, nodes, 300, seed, positions)
                    all_results.append(res)
                    if not res['error']:
                        print(f"    PDR={res['pdr_expected']:.4f}")

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

    output_file = f"results/power_sensitivity_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'git_commit': git_commit,
            'experiment_type': 'power_sensitivity',
            'run_tier': run_tier,
            'primary_metric': 'pdr_expected',
            'environment': 'indoor_office',
            'tx_power_dbm': 'multiple',
            'config': {
                'seeds': exp_seeds,
                'node_counts': exp_nodes,
                'round_counts': [300],
                'dropout_rates': [0.0],
                'tx_powers_dbm': TX_POWERS,
                'protocols': PROTOCOLS
            },
            'raw_results': all_results
        }, f, indent=2)
    print(f"\n结果已保存: {output_file}")


if __name__ == "__main__":
    main()
