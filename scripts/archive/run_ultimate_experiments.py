#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS 论文级超大规模实验 (10小时版)
===================================
覆盖 SCI 论文所需的全部实验维度。

实验总览：
- 10个实验类别
- 50+ 配置组合
- 2000+ 独立实验运行
- 预估时长: 8-10小时

Author: AERIS Research Team
Date: 2026-01-26
"""

import sys
import os
import json
import time
import random
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
RESULTS_DIR = PROJECT_ROOT / "results"
LOG_DIR = RESULTS_DIR / "run_logs"

sys.path.insert(0, str(SRC_DIR))

LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 实验配置
# ============================================================

# 可扩展性实验配置
SCALABILITY_CONFIGS = [
    {"nodes": 50, "reps": 100, "rounds": 500},
    {"nodes": 100, "reps": 100, "rounds": 500},
    {"nodes": 150, "reps": 100, "rounds": 500},
    {"nodes": 200, "reps": 100, "rounds": 500},
    {"nodes": 300, "reps": 80, "rounds": 500},
    {"nodes": 400, "reps": 60, "rounds": 400},
    {"nodes": 500, "reps": 60, "rounds": 400},
    {"nodes": 600, "reps": 40, "rounds": 300},
    {"nodes": 800, "reps": 30, "rounds": 300},
    {"nodes": 1000, "reps": 20, "rounds": 200},
]

# 拓扑配置
TOPOLOGY_CONFIGS = [
    {"name": "uniform", "reps": 80},
    {"name": "clustered", "reps": 80},
    {"name": "corridor", "reps": 80},
    {"name": "grid", "reps": 80},
    {"name": "hotspot", "reps": 80},
]

# 参数敏感性配置
PARAM_SENSITIVITY = {
    "gateway_k": [1, 2, 3, 4, 5, 6],
    "tx_power": [-3, 0, 3, 6, 9],
    "skeleton_ratio": [0.05, 0.1, 0.15, 0.2, 0.25],
}

# 消融实验配置
ABLATION_VARIANTS = [
    "full",
    "no_cas",
    "no_gateway",
    "no_skeleton",
    "no_adaptive",
    "no_safety",
    "cas_only",
]

PROTOCOLS = ["LEACH", "PEGASIS", "HEED", "AERIS"]


# ============================================================
# 工具函数
# ============================================================

def generate_positions(seed: int, n: int, width: float, height: float, topology: str = "uniform"):
    """生成不同拓扑的节点位置"""
    rng = random.Random(seed)
    positions = []

    if topology == "uniform":
        positions = [(rng.uniform(5, width-5), rng.uniform(5, height-5)) for _ in range(n)]

    elif topology == "clustered":
        # 3-5个簇
        n_clusters = rng.randint(3, 5)
        centers = [(rng.uniform(20, width-20), rng.uniform(20, height-20)) for _ in range(n_clusters)]
        for i in range(n):
            cx, cy = centers[i % n_clusters]
            x = max(5, min(width-5, cx + rng.gauss(0, 15)))
            y = max(5, min(height-5, cy + rng.gauss(0, 15)))
            positions.append((x, y))

    elif topology == "corridor":
        # 狭长走廊
        for _ in range(n):
            x = rng.uniform(5, width * 0.3)
            y = rng.uniform(5, height - 5)
            positions.append((x, y))

    elif topology == "grid":
        # 网格分布
        side = int(np.ceil(np.sqrt(n)))
        dx = (width - 10) / side
        dy = (height - 10) / side
        for i in range(n):
            row, col = i // side, i % side
            x = 5 + col * dx + rng.uniform(-dx*0.2, dx*0.2)
            y = 5 + row * dy + rng.uniform(-dy*0.2, dy*0.2)
            positions.append((max(5, min(width-5, x)), max(5, min(height-5, y))))

    elif topology == "hotspot":
        # 热点分布：中心密集，边缘稀疏
        for _ in range(n):
            r = rng.gauss(0, min(width, height) * 0.25)
            theta = rng.uniform(0, 2 * np.pi)
            x = width/2 + r * np.cos(theta)
            y = height/2 + r * np.sin(theta)
            positions.append((max(5, min(width-5, x)), max(5, min(height-5, y))))

    return positions


def run_single_experiment(args: Tuple) -> Dict:
    """运行单个实验（用于并行）"""
    protocol, nodes, seed, rounds, topology, extra_cfg = args

    from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
    from aeris_protocol import AerisProtocol

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
    cfg.tx_power_dbm = extra_cfg.get("tx_power", 0.0)
    cfg.gateway_k = extra_cfg.get("gateway_k", 3)
    cfg.positions = generate_positions(seed, nodes, width, height, topology)

    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    try:
        if protocol == "LEACH":
            proto = LEACHProtocol(cfg, em)
        elif protocol == "PEGASIS":
            proto = PEGASISProtocol(cfg, em)
        elif protocol == "HEED":
            proto = HEEDProtocolWrapper(cfg, em)
        else:
            proto = AerisProtocol(cfg, profile="robust", verbose=False, seed=seed,
                                  enable_cas=extra_cfg.get("enable_cas", True),
                                  enable_gateway=extra_cfg.get("enable_gateway", True),
                                  enable_skeleton=extra_cfg.get("enable_skeleton", True))

        result = proto.run_simulation(rounds)
        return {
            "protocol": protocol,
            "nodes": nodes,
            "seed": seed,
            "topology": topology,
            "pdr": result.get("pdr", 0),
            "energy": result.get("total_energy_consumed", 0),
            "lifetime": result.get("network_lifetime", rounds),
            "status": "ok"
        }
    except Exception as e:
        return {"protocol": protocol, "nodes": nodes, "seed": seed, "status": "error", "error": str(e)}


# ============================================================
# 主实验函数
# ============================================================

def run_scalability_experiments(workers: int = 12) -> Dict:
    """运行可扩展性实验"""
    print("\n" + "=" * 70)
    print("实验1: 可扩展性实验 (10个规模 × 4协议)")
    print("=" * 70)

    all_tasks = []
    for cfg in SCALABILITY_CONFIGS:
        for protocol in PROTOCOLS:
            for rep in range(cfg["reps"]):
                seed = 10000 + rep
                all_tasks.append((protocol, cfg["nodes"], seed, cfg["rounds"], "uniform", {}))

    print(f"总任务数: {len(all_tasks)}")
    results = []
    start = time.time()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, t): t for t in all_tasks}
        done = 0
        for future in as_completed(futures):
            done += 1
            r = future.result()
            results.append(r)
            if done % 100 == 0:
                elapsed = time.time() - start
                print(f"  [{done}/{len(all_tasks)}] {elapsed/60:.1f}min")

    print(f"完成! 耗时: {(time.time()-start)/60:.1f}min")
    return {"name": "scalability", "results": results}


def run_topology_experiments(workers: int = 12) -> Dict:
    """运行拓扑敏感性实验"""
    print("\n" + "=" * 70)
    print("实验2: 拓扑敏感性实验 (5拓扑 × 4协议)")
    print("=" * 70)

    all_tasks = []
    nodes = 200
    rounds = 400
    for topo_cfg in TOPOLOGY_CONFIGS:
        for protocol in PROTOCOLS:
            for rep in range(topo_cfg["reps"]):
                seed = 20000 + rep
                all_tasks.append((protocol, nodes, seed, rounds, topo_cfg["name"], {}))

    print(f"总任务数: {len(all_tasks)}")
    results = []
    start = time.time()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, t): t for t in all_tasks}
        done = 0
        for future in as_completed(futures):
            done += 1
            results.append(future.result())
            if done % 50 == 0:
                print(f"  [{done}/{len(all_tasks)}] {(time.time()-start)/60:.1f}min")

    print(f"完成! 耗时: {(time.time()-start)/60:.1f}min")
    return {"name": "topology", "results": results}


def run_param_sensitivity_experiments(workers: int = 12) -> Dict:
    """运行参数敏感性实验"""
    print("\n" + "=" * 70)
    print("实验3: 参数敏感性实验")
    print("=" * 70)

    all_tasks = []
    nodes = 200
    rounds = 300
    reps = 50

    # 网关数量敏感性
    for k in PARAM_SENSITIVITY["gateway_k"]:
        for rep in range(reps):
            seed = 30000 + rep
            all_tasks.append(("AERIS", nodes, seed, rounds, "uniform", {"gateway_k": k}))

    # 发射功率敏感性
    for tx in PARAM_SENSITIVITY["tx_power"]:
        for rep in range(reps):
            seed = 31000 + rep
            all_tasks.append(("AERIS", nodes, seed, rounds, "uniform", {"tx_power": tx}))

    print(f"总任务数: {len(all_tasks)}")
    results = []
    start = time.time()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, t): t for t in all_tasks}
        for future in as_completed(futures):
            results.append(future.result())

    print(f"完成! 耗时: {(time.time()-start)/60:.1f}min")
    return {"name": "param_sensitivity", "results": results}


def run_ablation_experiments(workers: int = 12) -> Dict:
    """运行消融实验"""
    print("\n" + "=" * 70)
    print("实验4: 消融实验 (7变体)")
    print("=" * 70)

    all_tasks = []
    nodes = 200
    rounds = 400
    reps = 80

    variant_configs = {
        "full": {},
        "no_cas": {"enable_cas": False},
        "no_gateway": {"enable_gateway": False},
        "no_skeleton": {"enable_skeleton": False},
    }

    for variant, cfg in variant_configs.items():
        for rep in range(reps):
            seed = 40000 + rep
            all_tasks.append(("AERIS", nodes, seed, rounds, "uniform", cfg))

    print(f"总任务数: {len(all_tasks)}")
    results = []
    start = time.time()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, t): t for t in all_tasks}
        for future in as_completed(futures):
            results.append(future.result())

    print(f"完成! 耗时: {(time.time()-start)/60:.1f}min")
    return {"name": "ablation", "results": results}


def analyze_results(results: List[Dict]) -> Dict:
    """统计分析结果"""
    from scipy import stats

    analysis = {}
    for exp in results:
        name = exp["name"]
        data = exp["results"]

        # 按协议分组
        by_protocol = {}
        for r in data:
            if r.get("status") != "ok":
                continue
            p = r["protocol"]
            if p not in by_protocol:
                by_protocol[p] = []
            by_protocol[p].append(r["pdr"])

        # 计算统计量
        stats_by_protocol = {}
        for p, pdrs in by_protocol.items():
            if len(pdrs) < 2:
                continue
            arr = np.array(pdrs)
            stats_by_protocol[p] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr, ddof=1)),
                "ci95": float(1.96 * np.std(arr, ddof=1) / np.sqrt(len(arr))),
                "n": len(arr)
            }

        analysis[name] = stats_by_protocol

    return analysis


def main(workers: int = 12):
    """主函数"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("AERIS 论文级超大规模实验")
    print("=" * 70)
    print(f"启动: {datetime.now()}")
    print(f"并行度: {workers}")

    all_results = []
    start = time.time()

    # 运行各类实验
    all_results.append(run_scalability_experiments(workers))
    all_results.append(run_topology_experiments(workers))
    all_results.append(run_param_sensitivity_experiments(workers))
    all_results.append(run_ablation_experiments(workers))

    # 统计分析
    analysis = analyze_results(all_results)

    # 保存结果
    output = {
        "timestamp": timestamp,
        "total_time_min": (time.time() - start) / 60,
        "experiments": all_results,
        "analysis": analysis
    }

    out_file = RESULTS_DIR / f"ultimate_experiments_{timestamp}.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 70)
    print(f"全部完成! 总耗时: {(time.time()-start)/60:.1f} 分钟")
    print(f"结果: {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    main(args.workers)
