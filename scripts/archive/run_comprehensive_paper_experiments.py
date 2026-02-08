#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS 论文级全面实验脚本
========================
覆盖 SCI 论文所需的所有实验维度。

实验矩阵：
1. 可扩展性实验 (100-1000节点, 100重复)
2. 动态场景实验 (3场景 × 100重复)
3. 拓扑敏感性实验 (5拓扑 × 50重复)
4. 参数敏感性实验 (网格搜索)
5. 消融实验 (组件贡献)
6. 真实数据集验证 (Intel Lab)
7. 统计显著性检验 (完整)
8. 能量效率分析
9. 网络寿命分析
10. 收敛性分析

Author: AERIS Research Team
Date: 2026-01-26
"""

import sys
import os
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RESULTS_DIR = PROJECT_ROOT / "results"
LOG_DIR = RESULTS_DIR / "run_logs"
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 实验配置矩阵
# ============================================================

EXPERIMENT_MATRIX = {
    # ========== 第一类：可扩展性实验 ==========
    "scalability": {
        "name": "可扩展性实验",
        "description": "测试不同网络规模下的性能",
        "configs": [
            {"nodes": 50, "replicates": 100, "rounds": 500},
            {"nodes": 100, "replicates": 100, "rounds": 500},
            {"nodes": 150, "replicates": 100, "rounds": 500},
            {"nodes": 200, "replicates": 100, "rounds": 500},
            {"nodes": 300, "replicates": 100, "rounds": 500},
            {"nodes": 400, "replicates": 80, "rounds": 500},
            {"nodes": 500, "replicates": 80, "rounds": 500},
            {"nodes": 600, "replicates": 60, "rounds": 400},
            {"nodes": 800, "replicates": 50, "rounds": 400},
            {"nodes": 1000, "replicates": 30, "rounds": 300},
        ],
        "priority": 1,
        "timeout_hours": 6,
    },

    # ========== 第二类：动态场景实验 ==========
    "dynamic_corridor": {
        "name": "动态走廊场景",
        "description": "节点沿走廊移动，测试路由适应性",
        "configs": [
            {"phases": 8, "replicates": 100, "rounds": 300},
        ],
        "priority": 1,
        "timeout_hours": 2,
    },
    "dynamic_moving_bs": {
        "name": "移动基站场景",
        "description": "基站位置变化，测试网关重选",
        "configs": [
            {"positions": 6, "replicates": 100, "rounds": 300},
        ],
        "priority": 1,
        "timeout_hours": 2,
    },
    "dynamic_dropout": {
        "name": "节点掉线场景",
        "description": "随机节点失效，测试容错能力",
        "configs": [
            {"dropout_rates": [0.1, 0.2, 0.3, 0.4], "replicates": 100, "rounds": 300},
        ],
        "priority": 1,
        "timeout_hours": 2,
    },

    # ========== 第三类：拓扑敏感性实验 ==========
    "topology_sensitivity": {
        "name": "拓扑敏感性实验",
        "description": "不同网络拓扑下的性能对比",
        "configs": [
            {"topology": "uniform", "replicates": 80, "rounds": 400},
            {"topology": "clustered", "replicates": 80, "rounds": 400},
            {"topology": "corridor", "replicates": 80, "rounds": 400},
            {"topology": "grid", "replicates": 80, "rounds": 400},
            {"topology": "random_hotspot", "replicates": 80, "rounds": 400},
        ],
        "priority": 2,
        "timeout_hours": 3,
    },

    # ========== 第四类：参数敏感性实验 ==========
    "param_sensitivity": {
        "name": "参数敏感性实验",
        "description": "关键参数对性能的影响",
        "configs": [
            # CAS权重敏感性
            {"param": "cas_direct_weight", "values": [0.2, 0.4, 0.6, 0.8], "replicates": 50},
            {"param": "cas_chain_weight", "values": [0.2, 0.4, 0.6, 0.8], "replicates": 50},
            # 网关数量敏感性
            {"param": "gateway_k", "values": [1, 2, 3, 4, 5, 6], "replicates": 50},
            # 骨干节点比例
            {"param": "skeleton_ratio", "values": [0.05, 0.1, 0.15, 0.2], "replicates": 50},
            # 发射功率
            {"param": "tx_power", "values": [-3, 0, 3, 6, 9], "replicates": 50},
        ],
        "priority": 2,
        "timeout_hours": 3,
    },

    # ========== 第五类：消融实验 ==========
    "ablation": {
        "name": "消融实验",
        "description": "各组件对整体性能的贡献",
        "configs": [
            {"variant": "full", "replicates": 100},
            {"variant": "no_cas", "replicates": 100},
            {"variant": "no_gateway", "replicates": 100},
            {"variant": "no_skeleton", "replicates": 100},
            {"variant": "no_adaptive", "replicates": 100},
            {"variant": "no_safety", "replicates": 100},
            {"variant": "cas_only", "replicates": 100},
            {"variant": "gateway_only", "replicates": 100},
        ],
        "priority": 2,
        "timeout_hours": 2,
    },

    # ========== 第六类：真实数据集验证 ==========
    "intel_validation": {
        "name": "Intel Lab数据集验证",
        "description": "使用真实传感器数据验证",
        "configs": [
            {"dataset": "intel_lab", "replicates": 50, "rounds": 500},
        ],
        "priority": 3,
        "timeout_hours": 1.5,
    },

    # ========== 第七类：统计显著性检验 ==========
    "statistical_tests": {
        "name": "统计显著性检验",
        "description": "完整的统计分析",
        "configs": [
            {"test": "welch_t", "comparisons": "all_pairs"},
            {"test": "mann_whitney", "comparisons": "all_pairs"},
            {"test": "wilcoxon", "comparisons": "all_pairs"},
            {"test": "holm_bonferroni", "correction": True},
            {"test": "bootstrap", "n_bootstrap": 10000},
            {"test": "effect_size", "metric": "cohens_d"},
        ],
        "priority": 3,
        "timeout_hours": 1,
    },

    # ========== 第八类：能量效率分析 ==========
    "energy_analysis": {
        "name": "能量效率分析",
        "description": "能耗与PDR的权衡分析",
        "configs": [
            {"metric": "energy_per_packet", "replicates": 80},
            {"metric": "energy_efficiency", "replicates": 80},
            {"metric": "pareto_frontier", "replicates": 80},
        ],
        "priority": 3,
        "timeout_hours": 1.5,
    },

    # ========== 第九类：网络寿命分析 ==========
    "lifetime_analysis": {
        "name": "网络寿命分析",
        "description": "FND/HND/LND分析",
        "configs": [
            {"metric": "fnd", "replicates": 100, "rounds": 2000},  # First Node Dies
            {"metric": "hnd", "replicates": 100, "rounds": 2000},  # Half Nodes Die
            {"metric": "lnd", "replicates": 100, "rounds": 2000},  # Last Node Dies
        ],
        "priority": 3,
        "timeout_hours": 3,
    },

    # ========== 第十类：收敛性分析 ==========
    "convergence_analysis": {
        "name": "收敛性分析",
        "description": "算法收敛速度和稳定性",
        "configs": [
            {"metric": "pdr_convergence", "replicates": 50, "rounds": 1000},
            {"metric": "energy_convergence", "replicates": 50, "rounds": 1000},
            {"metric": "stability", "replicates": 50, "rounds": 1000},
        ],
        "priority": 4,
        "timeout_hours": 2,
    },
}


def estimate_total_time():
    """估算总实验时间"""
    total = sum(exp["timeout_hours"] for exp in EXPERIMENT_MATRIX.values())
    return total


def run_scalability_experiment(config: Dict) -> Dict:
    """运行可扩展性实验"""
    from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
    from aeris_protocol import AerisProtocol
    import numpy as np
    import random

    nodes = config["nodes"]
    replicates = config["replicates"]
    rounds = config["rounds"]

    results = {"nodes": nodes, "protocols": {}}

    for protocol_name in ["LEACH", "PEGASIS", "HEED", "AERIS"]:
        pdrs = []
        energies = []
        lifetimes = []

        for rep in range(replicates):
            seed = 10000 + rep
            scale = (nodes / 100.0) ** 0.5
            width = 150.0 * scale
            height = 150.0 * scale

            cfg = NetworkConfig(
                num_nodes=nodes,
                area_width=width,
                area_height=height,
                base_station_x=width * 0.5,
                base_station_y=height * 1.2,
                initial_energy=2.0,
                packet_size=1024,
            )
            cfg.enable_channel = True
            cfg.channel_env = "indoor_office"
            cfg.tx_power_dbm = 0.0

            rng = random.Random(seed)
            cfg.positions = [(rng.uniform(5, width-5), rng.uniform(5, height-5)) for _ in range(nodes)]

            em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

            try:
                if protocol_name == "LEACH":
                    proto = LEACHProtocol(cfg, em)
                elif protocol_name == "PEGASIS":
                    proto = PEGASISProtocol(cfg, em)
                elif protocol_name == "HEED":
                    proto = HEEDProtocolWrapper(cfg, em)
                else:
                    proto = AerisProtocol(cfg, profile="robust", verbose=False, seed=seed)

                result = proto.run_simulation(rounds)
                pdrs.append(result.get("pdr", 0))
                energies.append(result.get("total_energy_consumed", 0))
                lifetimes.append(result.get("network_lifetime", rounds))
            except Exception as e:
                print(f"[WARN] {protocol_name}@{nodes} rep={rep} failed: {e}")

        results["protocols"][protocol_name] = {
            "pdr_mean": float(np.mean(pdrs)) if pdrs else 0,
            "pdr_std": float(np.std(pdrs)) if pdrs else 0,
            "pdr_ci95": float(1.96 * np.std(pdrs) / np.sqrt(len(pdrs))) if pdrs else 0,
            "energy_mean": float(np.mean(energies)) if energies else 0,
            "lifetime_mean": float(np.mean(lifetimes)) if lifetimes else 0,
            "n_samples": len(pdrs),
        }

    return results


def run_experiment_category(category: str, config: Dict) -> Dict:
    """运行指定类别的实验"""
    if category == "scalability":
        return run_scalability_experiment(config)
    # 其他类别可以调用现有脚本
    return {"status": "not_implemented", "category": category}


def main():
    """主函数"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("AERIS 论文级全面实验")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"实验类别: {len(EXPERIMENT_MATRIX)}")
    print(f"预估总时长: {estimate_total_time():.1f} 小时")
    print()

    # 显示实验矩阵
    print("实验矩阵:")
    for name, exp in sorted(EXPERIMENT_MATRIX.items(), key=lambda x: x[1]["priority"]):
        print(f"  [P{exp['priority']}] {exp['name']}")
        print(f"       {exp['description']}")
        print(f"       配置数: {len(exp['configs'])}, 超时: {exp['timeout_hours']}h")
    print()

    # 运行可扩展性实验（核心）
    print("\n" + "=" * 70)
    print("开始运行可扩展性实验...")
    print("=" * 70)

    scalability_results = []
    for cfg in EXPERIMENT_MATRIX["scalability"]["configs"]:
        print(f"\n>>> 节点数: {cfg['nodes']}, 重复: {cfg['replicates']}, 轮次: {cfg['rounds']}")
        result = run_scalability_experiment(cfg)
        scalability_results.append(result)

        # 打印中间结果
        print(f"    AERIS PDR: {result['protocols']['AERIS']['pdr_mean']*100:.2f}%")
        print(f"    PEGASIS PDR: {result['protocols']['PEGASIS']['pdr_mean']*100:.2f}%")

    # 保存结果
    output_file = RESULTS_DIR / f"comprehensive_scalability_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(scalability_results, f, indent=2)

    print(f"\n[DONE] 结果已保存: {output_file}")


if __name__ == "__main__":
    main()
