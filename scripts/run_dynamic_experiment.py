#!/usr/bin/env python3
"""动态环境实验：测试AERIS在复杂场景下的优势"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import random
import numpy as np
from datetime import datetime
from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol
from aeris_protocol import AerisProtocol
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

def run_dynamic_experiment():
    """动态环境实验：节点掉线场景"""
    print("="*60)
    print("动态环境实验：节点掉线场景")
    print("="*60)

    seeds = [42, 123, 456]
    results = {'AERIS': [], 'LEACH': [], 'PEGASIS': []}

    for seed in seeds:
        print(f"\n--- Seed {seed} ---")

        # 配置：启用高掉线模式
        cfg = NetworkConfig(
            num_nodes=100,
            area_width=200,
            area_height=200,
            initial_energy=2.0,
            packet_size=512,
            enable_channel=True,
            channel_env='indoor_office',
            tx_power_dbm=0.0,
        )
        cfg.high_dropout_mode = True

        # AERIS
        random.seed(seed)
        np.random.seed(seed)
        proto = AerisProtocol(cfg, verbose=False, seed=seed,
                              enable_cas=True, enable_gateway=True)
        r = proto.run_simulation(max_rounds=200)
        results['AERIS'].append(r.get('packet_delivery_ratio_end2end', 0))
        print(f"AERIS: PDR={r.get('packet_delivery_ratio_end2end',0)*100:.1f}%")

        # LEACH
        random.seed(seed)
        np.random.seed(seed)
        em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        leach = LEACHProtocol(cfg, em)
        r = leach.run_simulation(max_rounds=200)
        results['LEACH'].append(r.get('packet_delivery_ratio', 0))
        print(f"LEACH: PDR={r.get('packet_delivery_ratio',0)*100:.1f}%")

        # PEGASIS
        random.seed(seed)
        np.random.seed(seed)
        em2 = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        pegasis = PEGASISProtocol(cfg, em2)
        r = pegasis.run_simulation(max_rounds=200)
        results['PEGASIS'].append(r.get('packet_delivery_ratio', 0))
        print(f"PEGASIS: PDR={r.get('packet_delivery_ratio',0)*100:.1f}%")

    print("\n" + "="*60)
    print("动态环境结果汇总")
    print("="*60)
    for proto, pdrs in results.items():
        avg = np.mean(pdrs) * 100
        print(f"{proto}: {avg:.2f}%")

    return results

def run_large_scale_experiment():
    """大规模网络实验"""
    print("\n" + "="*60)
    print("大规模网络实验：300节点")
    print("="*60)

    seed = 42
    results = {}

    cfg = NetworkConfig(
        num_nodes=300,
        area_width=400,
        area_height=400,
        initial_energy=2.0,
        packet_size=512,
        enable_channel=True,
        channel_env='indoor_office',
        tx_power_dbm=0.0,
    )

    # AERIS
    random.seed(seed)
    np.random.seed(seed)
    proto = AerisProtocol(cfg, verbose=False, seed=seed,
                          enable_cas=True, enable_gateway=True)
    r = proto.run_simulation(max_rounds=100)
    results['AERIS'] = r.get('packet_delivery_ratio_end2end', 0)
    print(f"AERIS: PDR={results['AERIS']*100:.1f}%")

    # LEACH
    random.seed(seed)
    np.random.seed(seed)
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    leach = LEACHProtocol(cfg, em)
    r = leach.run_simulation(max_rounds=100)
    results['LEACH'] = r.get('packet_delivery_ratio', 0)
    print(f"LEACH: PDR={results['LEACH']*100:.1f}%")

    # PEGASIS
    random.seed(seed)
    np.random.seed(seed)
    em2 = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    pegasis = PEGASISProtocol(cfg, em2)
    r = pegasis.run_simulation(max_rounds=100)
    results['PEGASIS'] = r.get('packet_delivery_ratio', 0)
    print(f"PEGASIS: PDR={results['PEGASIS']*100:.1f}%")

    return results

if __name__ == "__main__":
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 运行实验
    dynamic_results = run_dynamic_experiment()
    large_scale_results = run_large_scale_experiment()

    # 保存结果
    output = {
        'timestamp': datetime.now().isoformat(),
        'dynamic_dropout': dynamic_results,
        'large_scale_300': large_scale_results
    }

    with open('results/dynamic_experiment.json', 'w') as f:
        json.dump(output, f, indent=2, default=float)

    print("\n结果已保存到 results/dynamic_experiment.json")
