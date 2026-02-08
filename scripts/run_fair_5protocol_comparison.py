#!/usr/bin/env python3
"""
公平的5协议对比实验脚本
- 所有协议使用统一的tx_power_dbm=10.0
- 所有协议使用统一的RealisticChannelModel
- n=30 seeds，符合项目标准
- 保存原始逐seed数据，可复现

用法:
  python run_fair_5protocol_comparison.py          # 快速验证模式(5 seeds)
  python run_fair_5protocol_comparison.py --full   # 完整实验模式(30 seeds)
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
DROPOUT_RATES = [0.0, 0.1, 0.2]

# 统一功率设置 - 所有协议使用相同功率
UNIFIED_TX_POWER_DBM = 10.0


def run_single_experiment(protocol: str, num_nodes: int, num_rounds: int,
                          seed: int, dropout_rate: float, positions: list,
                          channel, link_success_matrix: np.ndarray) -> Dict:
    """运行单次实验，返回原始结果

    Args:
        positions: 统一的节点位置列表 [(x,y), ...]，所有协议共用
        channel: 共享的信道模型实例（所有协议共用同一实例）
        link_success_matrix: 预生成的链路成功矩阵 [num_nodes+1, num_nodes+1, num_rounds]
                            最后一个索引是BS
    """
    import random
    random.seed(seed)
    np.random.seed(seed)

    # 重置信道模型的随机状态，确保每个协议使用相同的随机序列
    channel.reset_rng(seed)

    result = {
        'protocol': protocol,
        'num_nodes': num_nodes,
        'num_rounds': num_rounds,
        'seed': seed,
        'dropout_rate': dropout_rate,
        'tx_power_dbm': UNIFIED_TX_POWER_DBM,
        'pdr_raw_attempted': 0.0,  # 原始attempted口径（来自协议返回值）
        'pdr_expected': 0.0,       # 主指标：bs_delivered / source_packets_expected
        'pdr_attempted': 0.0,      # 副指标：bs_delivered / source_packets_attempted
        'source_packets_expected': 0,
        'source_packets_attempted': 0,
        'bs_delivered': 0,
        'energy_mj': 0.0,
        'alive_nodes': 0,
        'error': None
    }

    try:
        if protocol == 'AERIS':
            result = run_aeris(num_nodes, num_rounds, seed, channel, positions, result)
        elif protocol == 'LEACH':
            result = run_leach(num_nodes, num_rounds, seed, channel, positions, result)
        elif protocol == 'PEGASIS':
            result = run_pegasis(num_nodes, num_rounds, seed, channel, positions, result)
        elif protocol == 'HEED':
            result = run_heed(num_nodes, num_rounds, seed, channel, positions, result)
        elif protocol == 'TEEN':
            result = run_teen(num_nodes, num_rounds, seed, channel, positions, result)

        # 计算双口径PDR
        if result['source_packets_attempted'] > 0:
            result['pdr_attempted'] = result['bs_delivered'] / result['source_packets_attempted']
        if result['source_packets_expected'] > 0:
            result['pdr_expected'] = result['bs_delivered'] / result['source_packets_expected']

    except Exception as e:
        import traceback
        result['error'] = f"{str(e)}\n{traceback.format_exc()}"

    return result


def run_aeris(num_nodes, num_rounds, seed, channel, positions, result):
    """运行AERIS协议 - 使用统一功率、信道模型和节点位置

    注意：AERIS的source_packets_attempted等于source_packets_expected，
    因为AERIS架构中所有存活节点每轮都会尝试发送数据。
    """
    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol

    config = NetworkConfig()
    config.num_nodes = num_nodes
    config.area_width = 200.0
    config.area_height = 200.0
    config.base_station_x = 100.0
    config.base_station_y = 200.0
    config.high_dropout_mode = False
    config.tx_power_dbm = UNIFIED_TX_POWER_DBM
    config.positions = positions
    config.force_environment = 'indoor_office'
    config.external_channel_model = channel  # 构造期注入

    proto = AerisProtocol(config, seed=seed)
    res = proto.run_simulation(max_rounds=num_rounds)

    # 废弃pdr字段，改用pdr_raw_attempted标注来源
    result['pdr_raw_attempted'] = res.get('packet_delivery_ratio_end2end', 0)
    # AERIS: attempted == expected (架构特性)
    result['source_packets_attempted'] = proto.source_packets_expected
    result['source_packets_expected'] = proto.source_packets_expected
    result['attempted_equals_expected'] = True  # 标注
    result['bs_delivered'] = proto.bs_delivered_total
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('final_alive_nodes', 0)
    return result


def run_leach(num_nodes, num_rounds, seed, channel, positions, result):
    """运行LEACH协议 - 使用统一功率、信道模型和节点位置"""
    from baseline_protocols.leach_protocol import LEACHProtocol, LEACHNode

    nodes = [LEACHNode(i, positions[i][0], positions[i][1]) for i in range(num_nodes)]
    proto = LEACHProtocol(nodes, (100, 200),
                          tx_power_dbm=UNIFIED_TX_POWER_DBM,
                          channel_model=channel)
    res = proto.run_simulation(num_rounds)

    result['pdr_raw_attempted'] = res.get('packet_delivery_ratio_end2end', 0)
    result['source_packets_attempted'] = proto.total_source_packets
    result['source_packets_expected'] = proto.source_packets_expected
    result['bs_delivered'] = proto.total_bs_delivered
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('alive_nodes', 0)
    return result


def run_pegasis(num_nodes, num_rounds, seed, channel, positions, result):
    """运行PEGASIS协议 - 使用统一功率、信道模型和节点位置"""
    from baseline_protocols.pegasis_protocol import PEGASISProtocol, PEGASISNode

    nodes = [PEGASISNode(i, positions[i][0], positions[i][1]) for i in range(num_nodes)]
    proto = PEGASISProtocol(nodes, (100, 200),
                            tx_power_dbm=UNIFIED_TX_POWER_DBM,
                            channel_model=channel)
    res = proto.run_simulation(num_rounds)

    result['pdr_raw_attempted'] = res.get('packet_delivery_ratio_end2end', 0)
    result['source_packets_attempted'] = proto.total_source_packets
    result['source_packets_expected'] = proto.source_packets_expected
    result['bs_delivered'] = proto.total_bs_delivered
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('alive_nodes', 0)
    return result


def run_heed(num_nodes, num_rounds, seed, channel, positions, result):
    """运行HEED协议 - 使用统一功率、信道模型和节点位置"""
    from baseline_protocols.heed_protocol import HEEDProtocol, HEEDNode

    nodes = [HEEDNode(i, positions[i][0], positions[i][1]) for i in range(num_nodes)]
    proto = HEEDProtocol(nodes, (100, 200),
                         tx_power_dbm=UNIFIED_TX_POWER_DBM,
                         channel_model=channel)
    res = proto.run_simulation(num_rounds)

    result['pdr_raw_attempted'] = res.get('packet_delivery_ratio_end2end', 0)
    result['source_packets_attempted'] = proto.total_source_packets
    result['source_packets_expected'] = proto.source_packets_expected
    result['bs_delivered'] = proto.total_bs_delivered
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('alive_nodes', 0)
    return result


def run_teen(num_nodes, num_rounds, seed, channel, positions, result):
    """运行TEEN协议 - 使用统一功率、信道模型和节点位置"""
    from teen_protocol import TEENProtocol, TEENConfig

    config = TEENConfig()
    config.num_nodes = num_nodes
    config.area_width = 200.0
    config.area_height = 200.0
    config.base_station_x = 100.0
    config.base_station_y = 200.0
    config.tx_power_dbm = UNIFIED_TX_POWER_DBM
    config.enable_channel = True
    config.channel_env = 'indoor_office'
    config.external_channel_model = channel

    proto = TEENProtocol(config)
    proto.initialize_network(positions)  # 使用统一位置
    res = proto.run_simulation(num_rounds)

    result['pdr_raw_attempted'] = res.get('packet_delivery_ratio_end2end', 0)
    result['source_packets_attempted'] = proto.source_packets_total
    result['source_packets_expected'] = proto.source_packets_expected
    result['bs_delivered'] = proto.bs_delivered_total
    result['energy_mj'] = res.get('total_energy_consumed', 0) * 1000
    result['alive_nodes'] = res.get('alive_nodes', 0)
    return result


def main():
    """主函数：运行公平的5协议对比实验"""
    parser = argparse.ArgumentParser(description='公平5协议对比实验')
    parser.add_argument('--full', action='store_true', help='完整实验模式(30 seeds)')
    parser.add_argument('--seeds', type=int, default=5, help='seed数量')
    parser.add_argument('--nodes', type=int, nargs='+', default=[100], help='节点数列表')
    parser.add_argument('--rounds', type=int, nargs='+', default=[300], help='轮数列表')
    parser.add_argument('--dropout', type=float, nargs='+', default=[0.0], help='dropout率列表')
    args = parser.parse_args()

    # 根据模式选择参数
    if args.full:
        exp_seeds = SEEDS  # 30 seeds
        exp_nodes = NODE_COUNTS
        exp_rounds = ROUND_COUNTS
        exp_dropout = DROPOUT_RATES
    else:
        exp_seeds = SEEDS[:args.seeds]
        exp_nodes = args.nodes
        exp_rounds = args.rounds
        exp_dropout = args.dropout

    print("=" * 60)
    print("公平5协议对比实验")
    print(f"模式: {'完整(n=30)' if args.full else '验证'}")
    print(f"统一功率: {UNIFIED_TX_POWER_DBM} dBm")
    print(f"Seeds: {len(exp_seeds)}, Nodes: {exp_nodes}, Rounds: {exp_rounds}")
    print("=" * 60)

    all_results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED', 'TEEN']

    # 获取git commit信息
    git_commit = "unknown"
    try:
        import subprocess
        git_commit = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=os.path.dirname(__file__)
        ).decode().strip()[:8]
    except Exception:
        pass

    from realistic_channel_model import RealisticChannelModel, EnvironmentType

    for dropout in exp_dropout:
        for nodes in exp_nodes:
            for rounds in exp_rounds:
                # 为每个(seed, nodes)组合生成统一位置和共享信道
                for seed in exp_seeds:
                    np.random.seed(seed)
                    positions = [(np.random.uniform(0, 200), np.random.uniform(0, 200))
                                 for _ in range(nodes)]

                    # 创建共享信道实例（每个seed一个，所有协议共用）
                    channel = RealisticChannelModel(EnvironmentType.INDOOR_OFFICE)
                    channel.set_dropout_rate(dropout)

                    # 预生成链路成功矩阵（暂时为None，后续可扩展）
                    link_success_matrix = None

                    for proto in protocols:
                        print(f">>> {proto} N={nodes} R={rounds} "
                              f"dropout={dropout} seed={seed}")
                        res = run_single_experiment(
                            proto, nodes, rounds, seed, dropout, positions,
                            channel, link_success_matrix)
                        all_results.append(res)
                        if res['error']:
                            print(f"    ERROR: {res['error']}")
                        else:
                            print(f"    PDR_exp={res['pdr_expected']:.4f}")

    # 保存原始结果
    run_tier = 'publication' if len(exp_seeds) >= 30 else 'diagnostic'
    output_file = f"results/fair_5protocol_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'git_commit': git_commit,
            'experiment_type': 'fair_5protocol',
            'run_tier': run_tier,
            'primary_metric': 'pdr_expected',
            'environment': 'indoor_office',
            'tx_power_dbm': UNIFIED_TX_POWER_DBM,
            'metric_note': 'pdr_expected=bs_delivered/source_packets_expected; pdr_attempted=bs_delivered/source_packets_attempted',
            'config': {
                'seeds': exp_seeds,
                'node_counts': exp_nodes,
                'round_counts': exp_rounds,
                'dropout_rates': exp_dropout
            },
            'raw_results': all_results
        }, f, indent=2)

    # 打印汇总 - 使用pdr_expected作为主指标
    print("\n" + "=" * 60)
    print("汇总结果 (主指标: pdr_expected):")
    for proto in protocols:
        proto_results = [r for r in all_results if r['protocol'] == proto and not r['error']]
        if proto_results:
            pdrs_exp = [r['pdr_expected'] for r in proto_results]
            pdrs_att = [r['pdr_attempted'] for r in proto_results]
            print(f"  {proto}: PDR_exp={np.mean(pdrs_exp):.4f}±{np.std(pdrs_exp):.4f}, "
                  f"PDR_att={np.mean(pdrs_att):.4f}±{np.std(pdrs_att):.4f}")

    print(f"\n结果已保存: {output_file}")


if __name__ == "__main__":
    main()
