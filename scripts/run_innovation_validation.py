#!/usr/bin/env python3
"""全面对比实验：AERIS vs 基线协议，找出创新点和优化方向"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import random
import numpy as np
from datetime import datetime
from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol
from aeris_protocol import AerisProtocol
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def run_aeris(cfg, seed, **kwargs):
    """运行AERIS协议"""
    random.seed(seed)
    np.random.seed(seed)
    proto = AerisProtocol(cfg, verbose=False, seed=seed, **kwargs)
    return proto.run_simulation(max_rounds=200)

def run_experiment(name, num_nodes, area_size, seeds, max_rounds=200):
    """运行单组实验"""
    print(f"\n{'='*60}")
    print(f"实验: {name}")
    print(f"节点数: {num_nodes}, 区域: {area_size}x{area_size}m")
    print(f"{'='*60}")

    cfg = NetworkConfig(
        num_nodes=num_nodes,
        area_width=area_size,
        area_height=area_size,
        initial_energy=2.0,
        packet_size=512,
        enable_channel=True,
        channel_env='indoor_office',
        tx_power_dbm=0.0,
    )

    results = {
        'AERIS': [], 'AERIS-noCAS': [], 'AERIS-noGW': [],
        'LEACH': [], 'PEGASIS': []
    }

    for seed in seeds:
        print(f"\n--- Seed {seed} ---")

        # AERIS完整版
        r = run_aeris(cfg, seed, enable_cas=True, enable_gateway=True)
        results['AERIS'].append({
            'pdr': r.get('packet_delivery_ratio_end2end', 0),
            'energy': r.get('total_energy_consumed', 0),
            'lifetime': r.get('network_lifetime', 0)
        })
        print(f"AERIS: PDR={r.get('packet_delivery_ratio_end2end',0)*100:.1f}%")

        # AERIS无CAS
        r = run_aeris(cfg, seed, enable_cas=False, enable_gateway=True)
        results['AERIS-noCAS'].append({
            'pdr': r.get('packet_delivery_ratio_end2end', 0),
            'energy': r.get('total_energy_consumed', 0),
            'lifetime': r.get('network_lifetime', 0)
        })
        print(f"AERIS-noCAS: PDR={r.get('packet_delivery_ratio_end2end',0)*100:.1f}%")

        # AERIS无Gateway
        r = run_aeris(cfg, seed, enable_cas=True, enable_gateway=False)
        results['AERIS-noGW'].append({
            'pdr': r.get('packet_delivery_ratio_end2end', 0),
            'energy': r.get('total_energy_consumed', 0),
            'lifetime': r.get('network_lifetime', 0)
        })
        print(f"AERIS-noGW: PDR={r.get('packet_delivery_ratio_end2end',0)*100:.1f}%")

        # LEACH
        random.seed(seed)
        np.random.seed(seed)
        energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        leach = LEACHProtocol(cfg, energy_model)
        r = leach.run_simulation(max_rounds=max_rounds)
        results['LEACH'].append({
            'pdr': r.get('packet_delivery_ratio', 0),
            'energy': r.get('total_energy_consumed', 0),
            'lifetime': r.get('network_lifetime', 0)
        })
        print(f"LEACH: PDR={r.get('packet_delivery_ratio',0)*100:.1f}%")

        # PEGASIS
        random.seed(seed)
        np.random.seed(seed)
        energy_model2 = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        pegasis = PEGASISProtocol(cfg, energy_model2)
        r = pegasis.run_simulation(max_rounds=max_rounds)
        results['PEGASIS'].append({
            'pdr': r.get('packet_delivery_ratio', 0),
            'energy': r.get('total_energy_consumed', 0),
            'lifetime': r.get('network_lifetime', 0)
        })
        print(f"PEGASIS: PDR={r.get('packet_delivery_ratio',0)*100:.1f}%")

    return results

def analyze_results(results):
    """分析结果"""
    print("\n" + "="*60)
    print("结果汇总")
    print("="*60)

    summary = {}
    for proto, data in results.items():
        if data:
            pdr_list = [d['pdr'] for d in data]
            energy_list = [d['energy'] for d in data]
            summary[proto] = {
                'pdr_mean': np.mean(pdr_list) * 100,
                'pdr_std': np.std(pdr_list) * 100,
                'energy_mean': np.mean(energy_list),
            }

    print(f"\n{'协议':<15} {'PDR均值':<12} {'PDR标准差':<12} {'能耗(J)':<12}")
    print("-" * 51)
    for proto, s in summary.items():
        print(f"{proto:<15} {s['pdr_mean']:.2f}%{'':<6} {s['pdr_std']:.2f}%{'':<6} {s['energy_mean']:.2f}")

    return summary

# 主实验
if __name__ == "__main__":
    seeds = [42, 123, 456, 789, 1024]

    print("="*60)
    print("AERIS创新点验证实验")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 实验1: 标准场景 (100节点, 200x200)
    results_std = run_experiment("标准场景", 100, 200, seeds)
    summary_std = analyze_results(results_std)

    # 保存结果
    output = {
        'timestamp': datetime.now().isoformat(),
        'standard_scenario': {
            'config': {'nodes': 100, 'area': 200},
            'results': results_std,
            'summary': summary_std
        }
    }

    with open('results/innovation_validation.json', 'w') as f:
        json.dump(output, f, indent=2, default=float)

    print("\n" + "="*60)
    print("创新点分析")
    print("="*60)

    # 计算各模块贡献
    aeris_pdr = summary_std['AERIS']['pdr_mean']
    nocas_pdr = summary_std['AERIS-noCAS']['pdr_mean']
    nogw_pdr = summary_std['AERIS-noGW']['pdr_mean']
    leach_pdr = summary_std['LEACH']['pdr_mean']
    pegasis_pdr = summary_std['PEGASIS']['pdr_mean']

    print(f"\n1. CAS模块贡献: {aeris_pdr - nocas_pdr:.2f}% PDR提升")
    print(f"2. Gateway模块贡献: {aeris_pdr - nogw_pdr:.2f}% PDR提升")
    print(f"3. AERIS vs LEACH: +{aeris_pdr - leach_pdr:.2f}% PDR")
    print(f"4. AERIS vs PEGASIS: {aeris_pdr - pegasis_pdr:+.2f}% PDR")

    print("\n结果已保存到 results/innovation_validation.json")
