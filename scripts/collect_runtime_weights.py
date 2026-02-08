#!/usr/bin/env python3
"""
P1诊断脚本: 收集AERIS运行时权重分布
用于验证B.5理论分析与实际运行数据的一致性
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import numpy as np
from datetime import datetime

def run_single_experiment(seed: int, num_nodes: int = 100, num_rounds: int = 300):
    """运行单次实验并收集权重采样"""
    import random
    random.seed(seed)
    np.random.seed(seed)

    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol
    from realistic_channel_model import RealisticChannelModel, EnvironmentType

    area_size = 200.0
    positions = [(np.random.uniform(0, area_size),
                  np.random.uniform(0, area_size)) for _ in range(num_nodes)]

    channel = RealisticChannelModel(EnvironmentType.INDOOR_OFFICE)
    channel.reset_rng(seed)

    config = NetworkConfig()
    config.num_nodes = num_nodes
    config.area_width = config.area_height = area_size
    config.base_station_x = area_size / 2
    config.base_station_y = area_size
    config.tx_power_dbm = 10.0
    config.positions = positions
    config.force_environment = 'indoor_office'
    config.external_channel_model = channel

    # 使用energy profile以启用adaptive weights
    proto = AerisProtocol(config, seed=seed, verbose=False, profile='energy')
    proto.run_simulation(max_rounds=num_rounds)

    # 提取诊断数据
    samples = getattr(proto, '_diag_weight_samples', [])
    return samples


def main():
    seeds = [42001, 42002, 42003]  # 3个seed快速诊断
    all_samples = []

    print("P1诊断: 收集运行时权重分布")
    print("=" * 50)

    for seed in seeds:
        print(f"运行 seed={seed}...")
        samples = run_single_experiment(seed)
        all_samples.extend(samples)
        print(f"  采集 {len(samples)} 个样本")

    if not all_samples:
        print("警告: 未采集到任何样本")
        return

    # 统计分析
    stage_boosts = [s['stage_boost'] for s in all_samples]
    energy_boosts = [s['energy_boost'] for s in all_samples]
    w_direct_links = [s['w_direct_link'] for s in all_samples]
    w_direct_energies = [s['w_direct_energy'] for s in all_samples]
    # B.6 新增字段
    avg_energy_ratios = [s.get('avg_energy_ratio', 0) for s in all_samples]
    rel_boosts = [s.get('rel_boost', 0) for s in all_samples]
    levels = [s.get('level', 0) for s in all_samples]
    pdr_trends = [s.get('pdr_trend', 0) for s in all_samples]

    print("\n运行时权重统计 (实测):")
    print("-" * 50)

    def print_stats(name, values):
        arr = np.array(values)
        print(f"{name}:")
        print(f"  min={arr.min():.4f}, mean={arr.mean():.4f}, "
              f"max={arr.max():.4f}, p95={np.percentile(arr, 95):.4f}")

    print_stats("stage_boost", stage_boosts)
    print_stats("energy_boost", energy_boosts)
    print_stats("w_direct_link", w_direct_links)
    print_stats("w_direct_energy", w_direct_energies)
    # B.6 新增字段
    print_stats("avg_energy_ratio", avg_energy_ratios)
    print_stats("rel_boost", rel_boosts)
    print_stats("level", levels)
    print_stats("pdr_trend", pdr_trends)

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        'timestamp': timestamp,
        'experiment_type': 'runtime_weight_diagnosis',
        'run_tier': 'diagnostic',
        'seeds': seeds,
        'sample_count': len(all_samples),
        'statistics': {
            'stage_boost': {
                'min': float(np.min(stage_boosts)),
                'mean': float(np.mean(stage_boosts)),
                'max': float(np.max(stage_boosts)),
                'p95': float(np.percentile(stage_boosts, 95))
            },
            'energy_boost': {
                'min': float(np.min(energy_boosts)),
                'mean': float(np.mean(energy_boosts)),
                'max': float(np.max(energy_boosts)),
                'p95': float(np.percentile(energy_boosts, 95))
            },
            'w_direct_link': {
                'min': float(np.min(w_direct_links)),
                'mean': float(np.mean(w_direct_links)),
                'max': float(np.max(w_direct_links)),
                'p95': float(np.percentile(w_direct_links, 95))
            },
            'w_direct_energy': {
                'min': float(np.min(w_direct_energies)),
                'mean': float(np.mean(w_direct_energies)),
                'max': float(np.max(w_direct_energies)),
                'p95': float(np.percentile(w_direct_energies, 95))
            },
            # B.6 新增字段
            'avg_energy_ratio': {
                'min': float(np.min(avg_energy_ratios)),
                'mean': float(np.mean(avg_energy_ratios)),
                'max': float(np.max(avg_energy_ratios)),
                'p95': float(np.percentile(avg_energy_ratios, 95))
            },
            'rel_boost': {
                'min': float(np.min(rel_boosts)),
                'mean': float(np.mean(rel_boosts)),
                'max': float(np.max(rel_boosts)),
                'p95': float(np.percentile(rel_boosts, 95))
            },
            'level': {
                'min': float(np.min(levels)),
                'mean': float(np.mean(levels)),
                'max': float(np.max(levels)),
                'p95': float(np.percentile(levels, 95))
            },
            'pdr_trend': {
                'min': float(np.min(pdr_trends)),
                'mean': float(np.mean(pdr_trends)),
                'max': float(np.max(pdr_trends)),
                'p95': float(np.percentile(pdr_trends, 95))
            }
        },
        'raw_samples': all_samples
    }

    outfile = f"results/runtime_weights_{timestamp}.json"
    with open(outfile, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n结果已保存: {outfile}")


if __name__ == "__main__":
    main()
