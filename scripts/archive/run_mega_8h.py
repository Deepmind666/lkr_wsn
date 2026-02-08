#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS 超大规模实验矩阵 (8小时版)
================================
设计目标: 覆盖论文所需全部实验维度，生成详尽图表数据

实验矩阵 (总计约42000实验):
1. 基线对比实验 (1920) - 6协议 × 4拓扑 × 80重复 × 500轮
2. 可扩展性实验 (3240) - 6协议 × 18规模 × 30重复
3. 消融实验 (2560) - 8变体 × 4拓扑 × 80重复
4. 参数敏感性实验 (10080) - 7参数 × 9值 × 4拓扑 × 40重复
5. 动态场景实验 (11520) - 6协议 × 3场景 × 8阶段 × 80重复
6. 跨拓扑实验 (3840) - 6协议 × 8拓扑变体 × 80重复
7. 长期运行实验 (480) - 6协议 × 4拓扑 × 20重复 × 1500轮
8. 蒙特卡洛实验 (7200) - 6协议 × 4拓扑 × 300种子
9. Intel真实数据实验 (900) - 6协议 × 150重复
10. 极端规模实验 (540) - 6协议 × 6规模 × 15重复

预估时长: 8-10小时
Author: AERIS Research Team
Date: 2026-01-28
"""

import sys
import os
import json
import time
import random
import argparse
import psutil
import hashlib
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple, Optional
import numpy as np


def stable_hash(s: str) -> int:
    """确定性哈希函数，替代Python内置hash()以保证可重复性"""
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % (10**9)

# Output tagging
OUTPUT_VERSION = "v1_1"
STRICT_PDR_END2END = True
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
RESULTS_DIR = PROJECT_ROOT / "results"
LOG_DIR = RESULTS_DIR / "mega_8h_logs"

sys.path.insert(0, str(SRC_DIR))

LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# CPU 资源控制配置
# ============================================================

def get_optimal_workers() -> int:
    """根据CPU核心数计算最优worker数，保持80%利用率"""
    cpu_count = psutil.cpu_count(logical=True)
    optimal = max(1, int(cpu_count * 0.8))
    return optimal

MAX_WORKERS = get_optimal_workers()

# ============================================================
# 实验配置
# ============================================================

# 协议列表
PROTOCOLS = ["LEACH", "PEGASIS", "HEED", "TEEN", "AERIS-E", "AERIS-R"]

# 基础拓扑
TOPOLOGIES = ["uniform", "corridor", "clustered", "hotspot"]

# 扩展拓扑变体
EXTENDED_TOPOLOGIES = [
    "uniform", "corridor", "clustered", "hotspot",
    "grid", "ring", "star", "random_clustered"
]

# 可扩展性规模点 (18个)
SCALE_CONFIGS = [
    {"nodes": 30, "rounds": 400},
    {"nodes": 50, "rounds": 400},
    {"nodes": 75, "rounds": 350},
    {"nodes": 100, "rounds": 350},
    {"nodes": 150, "rounds": 300},
    {"nodes": 200, "rounds": 300},
    {"nodes": 250, "rounds": 250},
    {"nodes": 300, "rounds": 250},
    {"nodes": 400, "rounds": 200},
    {"nodes": 500, "rounds": 200},
    {"nodes": 600, "rounds": 180},
    {"nodes": 700, "rounds": 150},
    {"nodes": 800, "rounds": 150},
    {"nodes": 900, "rounds": 120},
    {"nodes": 1000, "rounds": 120},
    {"nodes": 1200, "rounds": 100},
    {"nodes": 1500, "rounds": 80},
    {"nodes": 2000, "rounds": 60},
]

# 极端规模配置
EXTREME_SCALE_CONFIGS = [
    {"nodes": 2000, "rounds": 50},
    {"nodes": 2500, "rounds": 40},
    {"nodes": 3000, "rounds": 35},
    {"nodes": 3500, "rounds": 30},
    {"nodes": 4000, "rounds": 25},
    {"nodes": 5000, "rounds": 20},
]

# 消融变体
ABLATION_VARIANTS = [
    "full",           # 完整AERIS
    "no_cas",         # 无CAS模块
    "no_gateway",     # 无Gateway模块
    "no_skeleton",    # 无Skeleton模块
    "cas_only",       # 仅CAS
    "gateway_only",   # 仅Gateway
    "skeleton_only",  # 仅Skeleton
    "minimal",        # 最小配置
]

# 参数敏感性 (7参数 × 9值)
PARAM_SENSITIVITY = {
    "gateway_k": [1, 2, 3, 4, 5, 6, 7, 8, 10],
    "skeleton_ratio": [0.03, 0.05, 0.08, 0.1, 0.12, 0.15, 0.2, 0.25, 0.3],
    "tx_power": [-9, -6, -3, 0, 3, 6, 9, 12, 15],
    "initial_energy": [0.3, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
    "packet_size": [128, 256, 512, 1024, 2048, 4096, 8192, 12288, 16384],
    "cluster_ratio": [0.03, 0.05, 0.08, 0.1, 0.12, 0.15, 0.18, 0.2, 0.25],
    "aggregation_ratio": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
}

# 动态场景配置 (3场景 × 8阶段)
DYNAMIC_SCENARIOS = {
    "corridor_shift": ["phase1", "phase2", "phase3", "phase4",
                       "phase5", "phase6", "phase7", "phase8"],
    "moving_bs": ["pos1", "pos2", "pos3", "pos4",
                  "pos5", "pos6", "pos7", "pos8"],
    "node_dropout": ["drop0", "drop5", "drop10", "drop15",
                     "drop20", "drop25", "drop30", "drop40"],
}

# ============================================================
# 工具函数
# ============================================================

def get_git_commit() -> str:
    """获取当前git commit hash"""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def generate_positions(seed: int, n: int, width: float, height: float,
                       topology: str = "uniform") -> List[Tuple[float, float]]:
    """生成不同拓扑的节点位置"""
    rng = random.Random(seed)
    positions = []

    if topology == "uniform":
        positions = [(rng.uniform(5, width-5), rng.uniform(5, height-5))
                     for _ in range(n)]
    elif topology == "corridor":
        for _ in range(n):
            x = rng.uniform(5, width * 0.3)
            y = rng.uniform(5, height - 5)
            positions.append((x, y))
    elif topology == "clustered":
        n_clusters = rng.randint(3, 6)
        centers = [(rng.uniform(20, width-20), rng.uniform(20, height-20))
                   for _ in range(n_clusters)]
        for i in range(n):
            cx, cy = centers[i % n_clusters]
            x = max(5, min(width-5, cx + rng.gauss(0, 15)))
            y = max(5, min(height-5, cy + rng.gauss(0, 15)))
            positions.append((x, y))
    elif topology == "hotspot":
        for _ in range(n):
            r = rng.gauss(0, min(width, height) * 0.25)
            theta = rng.uniform(0, 2 * np.pi)
            x = width/2 + r * np.cos(theta)
            y = height/2 + r * np.sin(theta)
            positions.append((max(5, min(width-5, x)), max(5, min(height-5, y))))
    elif topology == "grid":
        side = int(np.ceil(np.sqrt(n)))
        spacing_x = (width - 10) / max(1, side - 1)
        spacing_y = (height - 10) / max(1, side - 1)
        for i in range(n):
            x = 5 + (i % side) * spacing_x + rng.gauss(0, 2)
            y = 5 + (i // side) * spacing_y + rng.gauss(0, 2)
            positions.append((max(5, min(width-5, x)), max(5, min(height-5, y))))
    elif topology == "ring":
        radius = min(width, height) * 0.4
        for i in range(n):
            theta = 2 * np.pi * i / n + rng.gauss(0, 0.1)
            r = radius + rng.gauss(0, 5)
            x = width/2 + r * np.cos(theta)
            y = height/2 + r * np.sin(theta)
            positions.append((max(5, min(width-5, x)), max(5, min(height-5, y))))
    elif topology == "star":
        # 中心节点 + 放射状分布
        positions.append((width/2, height/2))
        n_arms = 5
        for i in range(1, n):
            arm = i % n_arms
            theta = 2 * np.pi * arm / n_arms
            r = 10 + (i // n_arms) * 8 + rng.gauss(0, 3)
            x = width/2 + r * np.cos(theta)
            y = height/2 + r * np.sin(theta)
            positions.append((max(5, min(width-5, x)), max(5, min(height-5, y))))
    elif topology == "random_clustered":
        n_clusters = rng.randint(4, 8)
        cluster_sizes = [n // n_clusters] * n_clusters
        for i in range(n % n_clusters):
            cluster_sizes[i] += 1
        centers = [(rng.uniform(25, width-25), rng.uniform(25, height-25))
                   for _ in range(n_clusters)]
        for ci, size in enumerate(cluster_sizes):
            cx, cy = centers[ci]
            spread = rng.uniform(8, 20)
            for _ in range(size):
                x = max(5, min(width-5, cx + rng.gauss(0, spread)))
                y = max(5, min(height-5, cy + rng.gauss(0, spread)))
                positions.append((x, y))
    else:
        positions = [(rng.uniform(5, width-5), rng.uniform(5, height-5))
                     for _ in range(n)]
    return positions


def run_single_experiment(args: Dict) -> Dict:
    """运行单个实验 - 进程安全"""
    from benchmark_protocols import (
        NetworkConfig, LEACHProtocol, PEGASISProtocol,
        HEEDProtocolWrapper, TEENProtocolWrapper
    )
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
    from aeris_protocol import AerisProtocol

    protocol = args["protocol"]
    seed = args["seed"]
    nodes = args.get("nodes", 100)
    rounds = args.get("rounds", 200)
    topology = args.get("topology", "uniform")
    width = args.get("width", 150.0)
    height = args.get("height", 150.0)
    variant = args.get("variant", "full")
    exp_type = args.get("exp_type", "baseline")

    # 参数敏感性
    param_name = args.get("param_name", None)
    param_value = args.get("param_value", None)

    # 默认值
    initial_energy = 2.0
    packet_size = 1024
    tx_power = 0.0
    gateway_k = 3
    skeleton_ratio = 0.1
    cluster_ratio = 0.1
    aggregation_ratio = 0.5

    # 应用敏感性参数
    if param_name and param_value is not None:
        if param_name == "initial_energy":
            initial_energy = float(param_value)
        elif param_name == "packet_size":
            packet_size = int(param_value)
        elif param_name == "tx_power":
            tx_power = float(param_value)
        elif param_name == "gateway_k":
            gateway_k = int(param_value)
        elif param_name == "skeleton_ratio":
            skeleton_ratio = float(param_value)
        elif param_name == "cluster_ratio":
            cluster_ratio = float(param_value)
        elif param_name == "aggregation_ratio":
            aggregation_ratio = float(param_value)

    positions = generate_positions(seed, nodes, width, height, topology)

    cfg = NetworkConfig(
        num_nodes=nodes,
        area_width=width,
        area_height=height,
        base_station_x=width * 0.5,
        base_station_y=height + 50,
        initial_energy=initial_energy,
        packet_size=packet_size,
        tx_power_dbm=tx_power,
        positions=positions,
    )
    # 启用信道模型，确保基线协议也模拟真实丢包
    setattr(cfg, 'enable_channel', True)
    setattr(cfg, 'channel_env', 'indoor_office')
    setattr(cfg, 'gateway_k', gateway_k)
    setattr(cfg, 'skeleton_config', {'ratio': skeleton_ratio})
    setattr(cfg, 'cluster_ratio', cluster_ratio)
    setattr(cfg, 'aggregation_ratio', aggregation_ratio)

    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    try:
        if protocol == "LEACH":
            proto = LEACHProtocol(cfg, em)
        elif protocol == "PEGASIS":
            proto = PEGASISProtocol(cfg, em)
        elif protocol == "HEED":
            proto = HEEDProtocolWrapper(cfg, em)
        elif protocol == "TEEN":
            proto = TEENProtocolWrapper(cfg, em)
        elif protocol in ["AERIS-E", "AERIS-R"]:
            profile = "energy" if protocol == "AERIS-E" else "robust"
            enable_cas = variant in ["full", "cas_only", "no_gateway", "no_skeleton"]
            enable_gw = variant in ["full", "gateway_only", "no_cas", "no_skeleton"]
            enable_sk = variant in ["full", "skeleton_only", "no_cas", "no_gateway"]
            if variant == "minimal":
                enable_cas = enable_gw = enable_sk = False
            proto = AerisProtocol(
                cfg, profile=profile, verbose=False, seed=seed,
                enable_cas=enable_cas, enable_gateway=enable_gw,
                enable_skeleton=enable_sk
            )
        else:
            return {"status": "skipped", "reason": f"unknown protocol {protocol}"}

        result = proto.run_simulation(rounds)
        # 同时保存链路级PDR和端到端PDR
        pdr_hop = result.get("packet_delivery_ratio", 0)
        pdr_e2e = result.get("packet_delivery_ratio_end2end", None)
        if pdr_e2e is None:
            pdr_e2e = -1.0 if STRICT_PDR_END2END else pdr_hop
        out = {
            "status": "ok",
            "protocol": protocol,
            "exp_type": exp_type,
            "topology": topology,
            "nodes": nodes,
            "rounds": rounds,
            "seed": seed,
            "variant": variant,
            "pdr": pdr_hop,
            "pdr_end2end": pdr_e2e,
            "energy": result.get("total_energy_consumed", 0),
            "alive_nodes": result.get("alive_nodes", nodes),
            "lifetime": result.get("network_lifetime", rounds),
        }
        if param_name is not None:
            out["param_name"] = param_name
            out["param_value"] = param_value
        return out
    except Exception as e:
        return {"status": "error", "error": str(e), **args}


# ============================================================
# 任务生成函数
# ============================================================

def generate_baseline_tasks(base_seed: int, n_reps: int = 80) -> List[Dict]:
    """基线对比实验: 6协议 × 4拓扑 × 80重复 × 500轮"""
    tasks = []
    for topo in TOPOLOGIES:
        for proto in PROTOCOLS:
            for rep in range(n_reps):
                tasks.append({
                    "exp_type": "baseline",
                    "protocol": proto,
                    "topology": topo,
                    "nodes": 100,
                    "rounds": 500,
                    "seed": base_seed + rep * 1000 + stable_hash(topo) % 100,
                    "variant": "full",
                })
    return tasks


def generate_scalability_tasks(base_seed: int, n_reps: int = 30) -> List[Dict]:
    """可扩展性实验: 6协议 × 18规模 × 30重复"""
    tasks = []
    for cfg in SCALE_CONFIGS:
        for proto in PROTOCOLS:
            for rep in range(n_reps):
                tasks.append({
                    "exp_type": "scalability",
                    "protocol": proto,
                    "topology": "uniform",
                    "nodes": cfg["nodes"],
                    "rounds": cfg["rounds"],
                    "seed": base_seed + rep * 1000 + cfg["nodes"],
                    "variant": "full",
                })
    return tasks


def generate_ablation_tasks(base_seed: int, n_reps: int = 80) -> List[Dict]:
    """消融实验: 8变体 × 4拓扑 × 80重复"""
    tasks = []
    for topo in TOPOLOGIES:
        for variant in ABLATION_VARIANTS:
            for rep in range(n_reps):
                tasks.append({
                    "exp_type": "ablation",
                    "protocol": "AERIS-R",
                    "topology": topo,
                    "nodes": 100,
                    "rounds": 300,
                    "seed": base_seed + rep * 1000 + stable_hash(variant) % 100,
                    "variant": variant,
                })
    return tasks


def generate_sensitivity_tasks(base_seed: int, n_reps: int = 40) -> List[Dict]:
    """参数敏感性实验: 7参数 × 9值 × 4拓扑 × 40重复"""
    tasks = []
    for param, values in PARAM_SENSITIVITY.items():
        for val in values:
            for topo in TOPOLOGIES:
                for rep in range(n_reps):
                    tasks.append({
                        "exp_type": f"sensitivity_{param}",
                        "protocol": "AERIS-R",
                        "topology": topo,
                        "nodes": 100,
                        "rounds": 300,
                        "seed": base_seed + rep * 1000 + stable_hash(str(val)) % 100,
                        "variant": "full",
                        "param_name": param,
                        "param_value": val,
                    })
    return tasks


def generate_dynamic_tasks(base_seed: int, n_reps: int = 80) -> List[Dict]:
    """动态场景实验: 6协议 × 3场景 × 8阶段 × 80重复"""
    tasks = []
    for scenario, phases in DYNAMIC_SCENARIOS.items():
        for phase in phases:
            for proto in PROTOCOLS:
                for rep in range(n_reps):
                    tasks.append({
                        "exp_type": f"dynamic_{scenario}",
                        "protocol": proto,
                        "topology": "uniform",
                        "nodes": 100,
                        "rounds": 300,
                        "seed": base_seed + rep * 1000,
                        "variant": "full",
                        "scenario": scenario,
                        "phase": phase,
                    })
    return tasks


def generate_cross_topo_tasks(base_seed: int, n_reps: int = 80) -> List[Dict]:
    """跨拓扑实验: 6协议 × 8拓扑变体 × 80重复"""
    tasks = []
    for topo in EXTENDED_TOPOLOGIES:
        for proto in PROTOCOLS:
            for rep in range(n_reps):
                tasks.append({
                    "exp_type": "cross_topology",
                    "protocol": proto,
                    "topology": topo,
                    "nodes": 100,
                    "rounds": 300,
                    "seed": base_seed + rep * 1000 + stable_hash(topo) % 100,
                    "variant": "full",
                })
    return tasks


def generate_longterm_tasks(base_seed: int, n_reps: int = 20) -> List[Dict]:
    """长期运行实验: 6协议 × 4拓扑 × 20重复 × 1500轮"""
    tasks = []
    for topo in TOPOLOGIES:
        for proto in PROTOCOLS:
            for rep in range(n_reps):
                tasks.append({
                    "exp_type": "longterm",
                    "protocol": proto,
                    "topology": topo,
                    "nodes": 100,
                    "rounds": 1500,
                    "seed": base_seed + rep * 1000 + stable_hash(topo) % 100,
                    "variant": "full",
                })
    return tasks


def generate_montecarlo_tasks(base_seed: int, n_seeds: int = 300) -> List[Dict]:
    """蒙特卡洛实验: 6协议 × 4拓扑 × 300种子"""
    tasks = []
    for topo in TOPOLOGIES:
        for proto in PROTOCOLS:
            for seed_offset in range(n_seeds):
                tasks.append({
                    "exp_type": "montecarlo",
                    "protocol": proto,
                    "topology": topo,
                    "nodes": 100,
                    "rounds": 300,
                    "seed": base_seed + seed_offset * 7919,
                    "variant": "full",
                })
    return tasks


def generate_extreme_scale_tasks(base_seed: int, n_reps: int = 15) -> List[Dict]:
    """极端规模实验: 6协议 × 6规模 × 15重复"""
    tasks = []
    for cfg in EXTREME_SCALE_CONFIGS:
        for proto in PROTOCOLS:
            for rep in range(n_reps):
                area_scale = cfg["nodes"] / 100
                width = 150 * np.sqrt(area_scale)
                height = 150 * np.sqrt(area_scale)
                tasks.append({
                    "exp_type": "extreme_scale",
                    "protocol": proto,
                    "topology": "uniform",
                    "nodes": cfg["nodes"],
                    "rounds": cfg["rounds"],
                    "width": width,
                    "height": height,
                    "seed": base_seed + rep * 1000 + cfg["nodes"],
                    "variant": "full",
                })
    return tasks


# ============================================================
# 主执行函数
# ============================================================

def run_experiment_batch(tasks: List[Dict], desc: str, workers: int) -> List[Dict]:
    """批量执行实验"""
    results = []
    total = len(tasks)
    print(f"\n{'='*60}")
    print(f"开始: {desc} ({total} 个实验, {workers} workers)")
    print(f"{'='*60}")

    start = time.time()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, t): t for t in tasks}
        done = 0
        for future in as_completed(futures):
            done += 1
            result = future.result()
            results.append(result)
            if done % 200 == 0 or done == total:
                elapsed = time.time() - start
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"  进度: {done}/{total} ({done*100/total:.1f}%) "
                      f"速率: {rate:.1f}/s ETA: {eta/60:.1f}min")

    elapsed = time.time() - start
    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"完成: {ok}/{total} 成功, 耗时 {elapsed/60:.1f} 分钟")
    return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AERIS 超大规模实验 (8小时版)")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS,
                        help=f"并行worker数 (默认: {MAX_WORKERS})")
    parser.add_argument("--base-seed", type=int, default=100000,
                        help="基础随机种子")
    parser.add_argument("--skip", nargs="+", default=[],
                        help="跳过的实验类型")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    git_commit = get_git_commit()

    print("=" * 70)
    print("AERIS 超大规模实验矩阵 (8小时版)")
    print("=" * 70)
    print(f"时间戳: {timestamp}")
    print(f"Git commit: {git_commit}")
    print(f"Workers: {args.workers}")
    print(f"CPU核心数: {psutil.cpu_count(logical=True)}")
    print("=" * 70)

    all_results = {}
    total_start = time.time()

    # 1. 基线对比实验
    if "baseline" not in args.skip:
        tasks = generate_baseline_tasks(args.base_seed, n_reps=80)
        results = run_experiment_batch(tasks, "基线对比实验(500轮)", args.workers)
        all_results["baseline"] = results

    # 2. 可扩展性实验
    if "scalability" not in args.skip:
        tasks = generate_scalability_tasks(args.base_seed + 10000, n_reps=30)
        results = run_experiment_batch(tasks, "可扩展性实验(18规模)", args.workers)
        all_results["scalability"] = results

    # 3. 消融实验
    if "ablation" not in args.skip:
        tasks = generate_ablation_tasks(args.base_seed + 20000, n_reps=80)
        results = run_experiment_batch(tasks, "消融实验(8变体)", args.workers)
        all_results["ablation"] = results

    # 4. 参数敏感性实验
    if "sensitivity" not in args.skip:
        tasks = generate_sensitivity_tasks(args.base_seed + 30000, n_reps=40)
        results = run_experiment_batch(tasks, "参数敏感性实验(7x9)", args.workers)
        all_results["sensitivity"] = results

    # 5. 动态场景实验
    if "dynamic" not in args.skip:
        tasks = generate_dynamic_tasks(args.base_seed + 40000, n_reps=80)
        results = run_experiment_batch(tasks, "动态场景实验(3x8)", args.workers)
        all_results["dynamic"] = results

    # 6. 跨拓扑实验
    if "cross_topo" not in args.skip:
        tasks = generate_cross_topo_tasks(args.base_seed + 50000, n_reps=80)
        results = run_experiment_batch(tasks, "跨拓扑实验(8变体)", args.workers)
        all_results["cross_topology"] = results

    # 7. 长期运行实验
    if "longterm" not in args.skip:
        tasks = generate_longterm_tasks(args.base_seed + 60000, n_reps=20)
        results = run_experiment_batch(tasks, "长期运行实验(1500轮)", args.workers)
        all_results["longterm"] = results

    # 8. 蒙特卡洛实验
    if "montecarlo" not in args.skip:
        tasks = generate_montecarlo_tasks(args.base_seed + 70000, n_seeds=300)
        results = run_experiment_batch(tasks, "蒙特卡洛实验(300种子)", args.workers)
        all_results["montecarlo"] = results

    # 9. 极端规模实验
    if "extreme" not in args.skip:
        tasks = generate_extreme_scale_tasks(args.base_seed + 80000, n_reps=15)
        results = run_experiment_batch(tasks, "极端规模实验(2000-5000节点)", args.workers)
        all_results["extreme_scale"] = results

    total_elapsed = time.time() - total_start

    # 统计汇总
    print("\n" + "=" * 70)
    print("实验完成汇总")
    print("=" * 70)

    total_ok = 0
    total_exp = 0
    for exp_type, results in all_results.items():
        ok = sum(1 for r in results if r.get("status") == "ok")
        total_ok += ok
        total_exp += len(results)
        print(f"  {exp_type}: {ok}/{len(results)} 成功")

    print(f"\n总计: {total_ok}/{total_exp} 成功")
    print(f"总耗时: {total_elapsed/3600:.2f} 小时")

    # 保存结果
    output = {
        "n_results": total_ok,
        "format_version": "1.0",
        "output_version": OUTPUT_VERSION,
        "schema_type": "mega_8h",
        "metadata": {
            "timestamp": timestamp,
            "git_commit": git_commit,
            "workers": args.workers,
            "base_seed": args.base_seed,
            "elapsed_hours": total_elapsed / 3600,
            "total_experiments": total_exp,
            "successful_experiments": total_ok,
        },
        "results": all_results,
    }

    out_file = RESULTS_DIR / f"mega_8h_{timestamp}_{OUTPUT_VERSION}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {out_file}")

    # 保存日志
    log_file = LOG_DIR / f"mega_8h_{timestamp}_{OUTPUT_VERSION}.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"AERIS Mega 8h Experiment Log\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Git: {git_commit}\n")
        f.write(f"Total: {total_ok}/{total_exp}\n")
        f.write(f"Elapsed: {total_elapsed/3600:.2f}h\n")

    print(f"日志已保存: {log_file}")


if __name__ == "__main__":
    main()
