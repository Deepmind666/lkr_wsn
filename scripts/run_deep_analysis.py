#!/usr/bin/env python3
"""深度分析实验：找出AERIS的真正优势和改进方向"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import random
import numpy as np
from datetime import datetime
from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol
from aeris_protocol import AerisProtocol
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def run_single(proto_name, cfg, seed, max_rounds=200):
    """运行单个协议"""
    random.seed(seed)
    np.random.seed(seed)

    if proto_name == 'AERIS':
        p = AerisProtocol(cfg, verbose=False, seed=seed,
                          enable_cas=True, enable_gateway=True)
        r = p.run_simulation(max_rounds=max_rounds)
        return {
            'pdr': r.get('packet_delivery_ratio_end2end', 0),
            'energy': r.get('total_energy_consumed', 0),
            'lifetime': r.get('network_lifetime', 0),
            'alive': r.get('final_alive_nodes', 0)
        }
    elif proto_name == 'LEACH':
        em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        p = LEACHProtocol(cfg, em)
        r = p.run_simulation(max_rounds=max_rounds)
        return {
            'pdr': r.get('packet_delivery_ratio', 0),
            'energy': r.get('total_energy_consumed', 0),
            'lifetime': r.get('network_lifetime', 0),
            'alive': r.get('final_alive_nodes', 0)
        }
    elif proto_name == 'PEGASIS':
        em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        p = PEGASISProtocol(cfg, em)
        r = p.run_simulation(max_rounds=max_rounds)
        return {
            'pdr': r.get('packet_delivery_ratio', 0),
            'energy': r.get('total_energy_consumed', 0),
            'lifetime': r.get('network_lifetime', 0),
            'alive': r.get('final_alive_nodes', 0)
        }

def experiment_scalability():
    """实验1: 可扩展性测试"""
    print("\n" + "="*60)
    print("实验1: 可扩展性测试 (节点数变化)")
    print("="*60)

    results = {}
    node_counts = [50, 100, 150, 200]

    for n in node_counts:
        print(f"\n--- {n}节点 ---")
        cfg = NetworkConfig(
            num_nodes=n, area_width=200, area_height=200,
            initial_energy=2.0, packet_size=512,
            enable_channel=True, channel_env='indoor_office'
        )

        results[n] = {}
        for proto in ['AERIS', 'LEACH', 'PEGASIS']:
            r = run_single(proto, cfg, seed=42, max_rounds=100)
            results[n][proto] = r
            print(f"{proto}: PDR={r['pdr']*100:.1f}%, Energy={r['energy']:.1f}J")

    return results

def experiment_energy_constraint():
    """实验2: 能量受限场景"""
    print("\n" + "="*60)
    print("实验2: 能量受限场景 (初始能量变化)")
    print("="*60)

    results = {}
    energy_levels = [0.5, 1.0, 2.0]

    for e in energy_levels:
        print(f"\n--- 初始能量 {e}J ---")
        cfg = NetworkConfig(
            num_nodes=100, area_width=200, area_height=200,
            initial_energy=e, packet_size=512,
            enable_channel=True, channel_env='indoor_office'
        )

        results[e] = {}
        for proto in ['AERIS', 'LEACH', 'PEGASIS']:
            r = run_single(proto, cfg, seed=42, max_rounds=100)
            results[e][proto] = r
            print(f"{proto}: PDR={r['pdr']*100:.1f}%, Lifetime={r['lifetime']}")

    return results

def experiment_harsh_channel():
    """实验3: 恶劣信道环境"""
    print("\n" + "="*60)
    print("实验3: 恶劣信道环境")
    print("="*60)

    results = {}
    envs = ['indoor_office', 'indoor_factory', 'outdoor_urban']

    for env in envs:
        print(f"\n--- 环境: {env} ---")
        cfg = NetworkConfig(
            num_nodes=100, area_width=200, area_height=200,
            initial_energy=2.0, packet_size=512,
            enable_channel=True, channel_env=env
        )

        results[env] = {}
        for proto in ['AERIS', 'LEACH', 'PEGASIS']:
            r = run_single(proto, cfg, seed=42, max_rounds=100)
            results[env][proto] = r
            print(f"{proto}: PDR={r['pdr']*100:.1f}%")

    return results

def experiment_long_term():
    """实验4: 长期运行稳定性"""
    print("\n" + "="*60)
    print("实验4: 长期运行稳定性 (500轮)")
    print("="*60)

    cfg = NetworkConfig(
        num_nodes=100, area_width=200, area_height=200,
        initial_energy=2.0, packet_size=512,
        enable_channel=True, channel_env='indoor_office'
    )

    results = {}
    for proto in ['AERIS', 'LEACH', 'PEGASIS']:
        r = run_single(proto, cfg, seed=42, max_rounds=500)
        results[proto] = r
        print(f"{proto}: PDR={r['pdr']*100:.1f}%, Lifetime={r['lifetime']}, Alive={r['alive']}")

    return results

if __name__ == "__main__":
    print("="*60)
    print("AERIS深度分析实验")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    all_results = {
        'timestamp': datetime.now().isoformat(),
        'scalability': experiment_scalability(),
        'energy_constraint': experiment_energy_constraint(),
        'harsh_channel': experiment_harsh_channel(),
        'long_term': experiment_long_term()
    }

    # 保存结果
    with open('results/deep_analysis.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=float)

    # 分析总结
    print("\n" + "="*60)
    print("改进方向分析")
    print("="*60)

    print("\n结果已保存到 results/deep_analysis.json")
