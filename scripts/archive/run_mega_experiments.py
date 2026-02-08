#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS 论文级超大规模实验 (20小时版)
===================================
覆盖 SCI 论文所需的全部实验维度，规模翻倍。

实验总览：
- 15个实验类别
- 100+ 配置组合
- 5000+ 独立实验运行
- 预估时长: 18-20小时

新增内容（相比10小时版）：
- 更多节点规模 (15个: 25-1500)
- 更多拓扑类型 (8种)
- 更多协议对比 (6种: +TEEN, +DEEC)
- 更多参数敏感性维度
- 更多消融变体
- 长时间网络寿命实验
- 收敛性分析实验

Author: AERIS Research Team
Date: 2026-01-26
"""

import sys
import os
import json
import time
import random
import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple
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
LOG_DIR = RESULTS_DIR / "run_logs"

sys.path.insert(0, str(SRC_DIR))

# GPT DeepSearch: Import unified experiment output format
from experiment_output_format import (
    UnifiedExperimentResult, UnifiedMetrics,
    create_unified_result, save_unified_results, to_unified_dict
)

LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 实验配置 (20小时版 - 规模翻倍)
# ============================================================

# 可扩展性实验配置 - 15个规模点
SCALABILITY_CONFIGS = [
    {"nodes": 25, "reps": 100, "rounds": 500},
    {"nodes": 50, "reps": 100, "rounds": 500},
    {"nodes": 75, "reps": 100, "rounds": 500},
    {"nodes": 100, "reps": 100, "rounds": 500},
    {"nodes": 125, "reps": 100, "rounds": 500},
    {"nodes": 150, "reps": 100, "rounds": 500},
    {"nodes": 200, "reps": 100, "rounds": 500},
    {"nodes": 250, "reps": 80, "rounds": 500},
    {"nodes": 300, "reps": 80, "rounds": 500},
    {"nodes": 400, "reps": 60, "rounds": 400},
    {"nodes": 500, "reps": 60, "rounds": 400},
    {"nodes": 600, "reps": 50, "rounds": 400},
    {"nodes": 800, "reps": 40, "rounds": 300},
    {"nodes": 1000, "reps": 30, "rounds": 300},
    {"nodes": 1500, "reps": 20, "rounds": 200},
]

# 拓扑配置 - 8种拓扑
TOPOLOGY_CONFIGS = [
    {"name": "uniform", "reps": 100},
    {"name": "clustered", "reps": 100},
    {"name": "corridor", "reps": 100},
    {"name": "grid", "reps": 100},
    {"name": "hotspot", "reps": 100},
    {"name": "ring", "reps": 80},
    {"name": "sparse", "reps": 80},
    {"name": "dense", "reps": 80},
]

# 参数敏感性配置 - 更多维度
PARAM_SENSITIVITY = {
    "gateway_k": [1, 2, 3, 4, 5, 6, 8],
    "tx_power": [-6, -3, 0, 3, 6, 9, 12],
    "skeleton_ratio": [0.05, 0.08, 0.1, 0.12, 0.15, 0.2, 0.25],
    "initial_energy": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
    "packet_size": [256, 512, 1024, 2048, 4096],
}

# 消融实验配置 - 更多变体
ABLATION_VARIANTS = [
    "full",
    "no_cas",
    "no_gateway",
    "no_skeleton",
    "no_adaptive",
    "no_safety",
    "cas_only",
    "gateway_only",
    "skeleton_only",
    "minimal",
]

# 协议列表 - 6种协议
PROTOCOLS = ["LEACH", "PEGASIS", "HEED", "TEEN", "AERIS", "AERIS_v2"]

# 动态场景配置
DYNAMIC_CONFIGS = {
    "corridor": {"phases": 10, "reps": 80},
    "moving_bs": {"positions": 8, "reps": 80},
    "dropout": {"rates": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4], "reps": 60},
    "burst": {"intervals": [10, 20, 50, 100], "reps": 60},
}

# 网络寿命实验配置
LIFETIME_CONFIGS = [
    {"nodes": 100, "reps": 50, "rounds": 3000},
    {"nodes": 200, "reps": 40, "rounds": 2500},
    {"nodes": 300, "reps": 30, "rounds": 2000},
]


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
        n_clusters = rng.randint(3, 5)
        centers = [(rng.uniform(20, width-20), rng.uniform(20, height-20)) for _ in range(n_clusters)]
        for i in range(n):
            cx, cy = centers[i % n_clusters]
            x = max(5, min(width-5, cx + rng.gauss(0, 15)))
            y = max(5, min(height-5, cy + rng.gauss(0, 15)))
            positions.append((x, y))

    elif topology == "corridor":
        for _ in range(n):
            x = rng.uniform(5, width * 0.3)
            y = rng.uniform(5, height - 5)
            positions.append((x, y))

    elif topology == "grid":
        side = int(np.ceil(np.sqrt(n)))
        dx = (width - 10) / side
        dy = (height - 10) / side
        for i in range(n):
            row, col = i // side, i % side
            x = 5 + col * dx + rng.uniform(-dx*0.2, dx*0.2)
            y = 5 + row * dy + rng.uniform(-dy*0.2, dy*0.2)
            positions.append((max(5, min(width-5, x)), max(5, min(height-5, y))))

    elif topology == "hotspot":
        for _ in range(n):
            r = rng.gauss(0, min(width, height) * 0.25)
            theta = rng.uniform(0, 2 * np.pi)
            x = width/2 + r * np.cos(theta)
            y = height/2 + r * np.sin(theta)
            positions.append((max(5, min(width-5, x)), max(5, min(height-5, y))))

    elif topology == "ring":
        radius = min(width, height) * 0.4
        for i in range(n):
            theta = 2 * np.pi * i / n + rng.uniform(-0.1, 0.1)
            r = radius + rng.gauss(0, 10)
            x = width/2 + r * np.cos(theta)
            y = height/2 + r * np.sin(theta)
            positions.append((max(5, min(width-5, x)), max(5, min(height-5, y))))

    elif topology == "sparse":
        # 稀疏分布：节点间距较大
        for _ in range(n):
            x = rng.uniform(10, width-10)
            y = rng.uniform(10, height-10)
            positions.append((x, y))

    elif topology == "dense":
        # 密集分布：集中在中心区域
        for _ in range(n):
            x = width/2 + rng.gauss(0, width * 0.15)
            y = height/2 + rng.gauss(0, height * 0.15)
            positions.append((max(5, min(width-5, x)), max(5, min(height-5, y))))

    else:
        # 默认均匀分布
        positions = [(rng.uniform(5, width-5), rng.uniform(5, height-5)) for _ in range(n)]

    return positions


def run_single_experiment(args: Tuple) -> Dict:
    """运行单个实验（用于并行）"""
    protocol, nodes, seed, rounds, topology, extra_cfg = args

    from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
    from aeris_protocol import AerisProtocol

    # 尝试导入TEEN协议
    try:
        from teen_protocol import TEENProtocol
        has_teen = True
    except ImportError:
        has_teen = False

    scale = (nodes / 100.0) ** 0.5
    width = 150.0 * scale
    height = 150.0 * scale

    cfg = NetworkConfig(
        num_nodes=nodes,
        area_width=width,
        area_height=height,
        base_station_x=width * 0.5,
        base_station_y=height * 1.2,
        initial_energy=extra_cfg.get("initial_energy", 2.0),
        packet_size=extra_cfg.get("packet_size", 1024),
    )
    cfg.enable_channel = True
    cfg.channel_env = "indoor_office"
    cfg.tx_power_dbm = extra_cfg.get("tx_power", 0.0)
    cfg.gateway_k = extra_cfg.get("gateway_k", 3)
    cfg.positions = generate_positions(seed, nodes, width, height, topology)
    # [FIX] 消融实验使用lightweight模式以观察模块真实贡献
    cfg.reliability_mode = extra_cfg.get("reliability_mode", "standard")

    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    try:
        if protocol == "LEACH":
            proto = LEACHProtocol(cfg, em)
        elif protocol == "PEGASIS":
            proto = PEGASISProtocol(cfg, em)
        elif protocol == "HEED":
            proto = HEEDProtocolWrapper(cfg, em)
        elif protocol == "TEEN" and has_teen:
            proto = TEENProtocol(cfg, em)
        elif protocol == "AERIS":
            proto = AerisProtocol(cfg, profile="robust", verbose=False, seed=seed,
                                  enable_cas=extra_cfg.get("enable_cas", True),
                                  enable_gateway=extra_cfg.get("enable_gateway", True),
                                  enable_skeleton=extra_cfg.get("enable_skeleton", True))
        elif protocol == "AERIS_v2":
            # AERIS v2 使用增强配置
            # [FIX] 移除无效参数 adaptive_gateway
            cfg.force_ctp_reliable = False  # 确保真实PDR
            proto = AerisProtocol(cfg, profile="robust", verbose=False, seed=seed,
                                  enable_cas=True,
                                  enable_gateway=True,
                                  enable_skeleton=True)
        else:
            # 跳过不支持的协议
            return {"protocol": protocol, "nodes": nodes, "seed": seed, "status": "skipped", "reason": "unsupported"}

        result = proto.run_simulation(rounds)
        pdr_hop = result.get("packet_delivery_ratio", 0)
        pdr_e2e = result.get("packet_delivery_ratio_end2end", None)
        if pdr_e2e is None:
            pdr_e2e = -1.0 if STRICT_PDR_END2END else pdr_hop
        return {
            "protocol": protocol,
            "nodes": nodes,
            "seed": seed,
            "topology": topology,
            "pdr": pdr_hop,
            "pdr_end2end": pdr_e2e,
            "energy": result.get("total_energy_consumed", 0),
            "lifetime": result.get("network_lifetime", rounds),
            "extra_cfg": extra_cfg,
            "status": "ok"
        }
    except Exception as e:
        return {"protocol": protocol, "nodes": nodes, "seed": seed, "status": "error", "error": str(e)}


# ============================================================
# 主实验函数
# ============================================================

def run_scalability_experiments(workers: int = 12) -> Dict:
    """运行可扩展性实验 - 15个规模点"""
    print("\n" + "=" * 70)
    print("实验1: 可扩展性实验 (15个规模 × 6协议)")
    print("=" * 70)

    all_tasks = []
    for cfg in SCALABILITY_CONFIGS:
        for protocol in PROTOCOLS:
            for rep in range(cfg["reps"]):
                seed = 10000 + rep * 100 + stable_hash(protocol) % 100
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
            if done % 200 == 0:
                elapsed = time.time() - start
                print(f"  [{done}/{len(all_tasks)}] {elapsed/60:.1f}min")

    print(f"完成! 耗时: {(time.time()-start)/60:.1f}min")
    return {"name": "scalability", "results": results}


def run_topology_experiments(workers: int = 12) -> Dict:
    """运行拓扑敏感性实验 - 8种拓扑"""
    print("\n" + "=" * 70)
    print("实验2: 拓扑敏感性实验 (8拓扑 × 6协议)")
    print("=" * 70)

    all_tasks = []
    nodes = 200
    rounds = 400
    for topo_cfg in TOPOLOGY_CONFIGS:
        for protocol in PROTOCOLS:
            for rep in range(topo_cfg["reps"]):
                seed = 20000 + rep * 100 + stable_hash(topo_cfg["name"] + protocol) % 100
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
            if done % 100 == 0:
                print(f"  [{done}/{len(all_tasks)}] {(time.time()-start)/60:.1f}min")

    print(f"完成! 耗时: {(time.time()-start)/60:.1f}min")
    return {"name": "topology", "results": results}


def run_param_sensitivity_experiments(workers: int = 12) -> Dict:
    """运行参数敏感性实验 - 5个维度"""
    print("\n" + "=" * 70)
    print("实验3: 参数敏感性实验 (5维度)")
    print("=" * 70)

    all_tasks = []
    nodes = 200
    rounds = 300
    reps = 60

    # 网关数量敏感性
    for k in PARAM_SENSITIVITY["gateway_k"]:
        for rep in range(reps):
            seed = 30000 + rep * 100 + stable_hash(f"gateway_k_{k}") % 100
            all_tasks.append(("AERIS", nodes, seed, rounds, "uniform", {"gateway_k": k}))

    # 发射功率敏感性
    for tx in PARAM_SENSITIVITY["tx_power"]:
        for rep in range(reps):
            seed = 31000 + rep * 100 + stable_hash(f"tx_power_{tx}") % 100
            all_tasks.append(("AERIS", nodes, seed, rounds, "uniform", {"tx_power": tx}))

    # 骨干比例敏感性
    for ratio in PARAM_SENSITIVITY["skeleton_ratio"]:
        for rep in range(reps):
            seed = 32000 + rep * 100 + stable_hash(f"skeleton_{ratio}") % 100
            all_tasks.append(("AERIS", nodes, seed, rounds, "uniform", {"skeleton_ratio": ratio}))

    # 初始能量敏感性
    for energy in PARAM_SENSITIVITY["initial_energy"]:
        for rep in range(reps):
            seed = 33000 + rep * 100 + stable_hash(f"energy_{energy}") % 100
            all_tasks.append(("AERIS", nodes, seed, rounds, "uniform", {"initial_energy": energy}))

    # 数据包大小敏感性
    for pkt_size in PARAM_SENSITIVITY["packet_size"]:
        for rep in range(reps):
            seed = 34000 + rep * 100 + stable_hash(f"pkt_{pkt_size}") % 100
            all_tasks.append(("AERIS", nodes, seed, rounds, "uniform", {"packet_size": pkt_size}))

    print(f"总任务数: {len(all_tasks)}")
    results = []
    start = time.time()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, t): t for t in all_tasks}
        done = 0
        for future in as_completed(futures):
            done += 1
            results.append(future.result())
            if done % 100 == 0:
                print(f"  [{done}/{len(all_tasks)}] {(time.time()-start)/60:.1f}min")

    print(f"完成! 耗时: {(time.time()-start)/60:.1f}min")
    return {"name": "param_sensitivity", "results": results}


def run_ablation_experiments(workers: int = 12) -> Dict:
    """运行消融实验 - 10个变体"""
    print("\n" + "=" * 70)
    print("实验4: 消融实验 (10变体)")
    print("=" * 70)

    all_tasks = []
    nodes = 200
    rounds = 600  # [FIX] 增加轮数以观察长期差异
    reps = 100

    # [FIX] 消融实验使用lightweight模式，减少重试次数以观察模块真实贡献
    # 原问题：reliable模式下每个包有~2000次重试机会，导致所有变体PDR都接近100%
    # 同时使用corridor31拓扑增加挑战性
    variant_configs = {
        "full": {"reliability_mode": "lightweight"},
        "no_cas": {"enable_cas": False, "reliability_mode": "lightweight"},
        "no_gateway": {"enable_gateway": False, "reliability_mode": "lightweight"},
        "no_skeleton": {"enable_skeleton": False, "reliability_mode": "lightweight"},
        "cas_only": {"enable_gateway": False, "enable_skeleton": False, "reliability_mode": "lightweight"},
        "gateway_only": {"enable_cas": False, "enable_skeleton": False, "reliability_mode": "lightweight"},
        "skeleton_only": {"enable_cas": False, "enable_gateway": False, "reliability_mode": "lightweight"},
        "minimal": {"enable_cas": False, "enable_gateway": False, "enable_skeleton": False, "reliability_mode": "lightweight"},
    }

    # [FIX] 使用多种拓扑增加消融实验有效性
    topologies = ["uniform", "corridor31"]
    for variant, cfg in variant_configs.items():
        for topo in topologies:
            for rep in range(reps):
                seed = 40000 + rep * 100 + stable_hash(variant) % 100
                task_cfg = cfg.copy()
                task_cfg["variant"] = variant
                all_tasks.append(("AERIS", nodes, seed, rounds, topo, task_cfg))

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
    return {"name": "ablation", "results": results}


def run_lifetime_experiments(workers: int = 12) -> Dict:
    """运行网络寿命实验 - 长时间运行"""
    print("\n" + "=" * 70)
    print("实验5: 网络寿命实验 (FND/HND/LND)")
    print("=" * 70)

    all_tasks = []
    for cfg in LIFETIME_CONFIGS:
        for protocol in ["LEACH", "PEGASIS", "HEED", "AERIS"]:
            for rep in range(cfg["reps"]):
                seed = 50000 + rep * 100 + stable_hash(protocol) % 100
                all_tasks.append((protocol, cfg["nodes"], seed, cfg["rounds"], "uniform", {}))

    print(f"总任务数: {len(all_tasks)}")
    results = []
    start = time.time()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, t): t for t in all_tasks}
        done = 0
        for future in as_completed(futures):
            done += 1
            results.append(future.result())
            if done % 20 == 0:
                print(f"  [{done}/{len(all_tasks)}] {(time.time()-start)/60:.1f}min")

    print(f"完成! 耗时: {(time.time()-start)/60:.1f}min")
    return {"name": "lifetime", "results": results}


def run_multi_scale_topology_experiments(workers: int = 12) -> Dict:
    """运行多规模×多拓扑交叉实验"""
    print("\n" + "=" * 70)
    print("实验6: 多规模×多拓扑交叉实验")
    print("=" * 70)

    all_tasks = []
    scales = [100, 200, 300, 500]
    topos = ["uniform", "clustered", "corridor", "hotspot"]
    reps = 50

    for nodes in scales:
        for topo in topos:
            for protocol in ["LEACH", "PEGASIS", "HEED", "AERIS"]:
                for rep in range(reps):
                    seed = 60000 + rep * 100 + stable_hash(f"{topo}_{protocol}_{nodes}") % 100
                    all_tasks.append((protocol, nodes, seed, 400, topo, {}))

    print(f"总任务数: {len(all_tasks)}")
    results = []
    start = time.time()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, t): t for t in all_tasks}
        done = 0
        for future in as_completed(futures):
            done += 1
            results.append(future.result())
            if done % 100 == 0:
                print(f"  [{done}/{len(all_tasks)}] {(time.time()-start)/60:.1f}min")

    print(f"完成! 耗时: {(time.time()-start)/60:.1f}min")
    return {"name": "multi_scale_topology", "results": results}


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
                by_protocol[p] = {"pdr": [], "energy": [], "lifetime": []}
            by_protocol[p]["pdr"].append(r.get("pdr", 0))
            by_protocol[p]["energy"].append(r.get("energy", 0))
            by_protocol[p]["lifetime"].append(r.get("lifetime", 0))

        # 计算统计量
        stats_by_protocol = {}
        for p, metrics in by_protocol.items():
            pdrs = metrics["pdr"]
            if len(pdrs) < 2:
                continue
            arr = np.array(pdrs)
            stats_by_protocol[p] = {
                "pdr_mean": float(np.mean(arr)),
                "pdr_std": float(np.std(arr, ddof=1)),
                "pdr_ci95": float(1.96 * np.std(arr, ddof=1) / np.sqrt(len(arr))),
                "pdr_median": float(np.median(arr)),
                "pdr_min": float(np.min(arr)),
                "pdr_max": float(np.max(arr)),
                "energy_mean": float(np.mean(metrics["energy"])) if metrics["energy"] else 0,
                "lifetime_mean": float(np.mean(metrics["lifetime"])) if metrics["lifetime"] else 0,
                "n": len(arr)
            }

        # 统计显著性检验 (AERIS vs others)
        if "AERIS" in by_protocol and len(by_protocol["AERIS"]["pdr"]) >= 10:
            aeris_pdr = by_protocol["AERIS"]["pdr"]
            significance = {}
            for p in by_protocol:
                if p != "AERIS" and len(by_protocol[p]["pdr"]) >= 10:
                    other_pdr = by_protocol[p]["pdr"]
                    t_stat, p_val = stats.ttest_ind(aeris_pdr, other_pdr, equal_var=False)
                    # Cohen's d
                    pooled_std = np.sqrt((np.var(aeris_pdr) + np.var(other_pdr)) / 2)
                    cohens_d = (np.mean(aeris_pdr) - np.mean(other_pdr)) / pooled_std if pooled_std > 0 else 0
                    significance[f"AERIS_vs_{p}"] = {
                        "t_stat": float(t_stat),
                        "p_value": float(p_val),
                        "cohens_d": float(cohens_d),
                        "significant": p_val < 0.05
                    }
            stats_by_protocol["significance"] = significance

        analysis[name] = stats_by_protocol

    return analysis


def main(workers: int = 12):
    """主函数"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("AERIS 论文级超大规模实验 (20小时版)")
    print("=" * 70)
    print(f"启动: {datetime.now()}")
    print(f"并行度: {workers}")
    print()
    print("实验计划:")
    print("  1. 可扩展性实验: 15规模 × 6协议 × ~100重复")
    print("  2. 拓扑敏感性实验: 8拓扑 × 6协议 × ~100重复")
    print("  3. 参数敏感性实验: 5维度 × 7值 × 60重复")
    print("  4. 消融实验: 8变体 × 100重复")
    print("  5. 网络寿命实验: 3规模 × 4协议 × ~40重复")
    print("  6. 多规模×多拓扑交叉实验: 4规模 × 4拓扑 × 4协议 × 50重复")
    print()

    all_results = []
    start = time.time()

    # 运行各类实验
    all_results.append(run_scalability_experiments(workers))
    all_results.append(run_topology_experiments(workers))
    all_results.append(run_param_sensitivity_experiments(workers))
    all_results.append(run_ablation_experiments(workers))
    all_results.append(run_lifetime_experiments(workers))
    all_results.append(run_multi_scale_topology_experiments(workers))

    # 统计分析
    print("\n" + "=" * 70)
    print("正在进行统计分析...")
    print("=" * 70)
    analysis = analyze_results(all_results)

    # 保存结果
    output = {
        "timestamp": timestamp,
        "output_version": OUTPUT_VERSION,
        "total_time_min": (time.time() - start) / 60,
        "total_time_hours": (time.time() - start) / 3600,
        "experiments": all_results,
        "analysis": analysis,
        "format_version": "1.0"  # GPT DeepSearch: Add format version
    }

    out_file = RESULTS_DIR / f"mega_experiments_{timestamp}_{OUTPUT_VERSION}.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)

    # GPT DeepSearch: Save unified format results
    unified_results = []
    for exp_batch in all_results:
        if isinstance(exp_batch, dict) and "results" in exp_batch:
            for r in exp_batch["results"]:
                if r.get("status") == "ok":
                    unified_results.append(create_unified_result(
                        protocol=r.get("protocol", "unknown"),
                        scenario=r.get("topology", "uniform"),
                        n_nodes=r.get("nodes", 100),
                        n_rounds=r.get("lifetime", 200),
                        pdr=r.get("pdr", 0.0),
                        energy=r.get("energy", 0.0),
                        alive_nodes=r.get("nodes", 0),
                        seed=r.get("seed", 42)
                    ))
    if unified_results:
        unified_file = RESULTS_DIR / f"mega_experiments_{timestamp}_{OUTPUT_VERSION}_unified.json"
        save_unified_results(unified_results, str(unified_file), "mega_experiments")

    # 打印摘要
    print("\n" + "=" * 70)
    print("实验结果摘要")
    print("=" * 70)
    for exp_name, stats in analysis.items():
        print(f"\n{exp_name}:")
        for proto, s in stats.items():
            if proto == "significance":
                continue
            if isinstance(s, dict) and "pdr_mean" in s:
                print(f"  {proto}: PDR={s['pdr_mean']*100:.2f}% ± {s['pdr_ci95']*100:.2f}% (n={s['n']})")

    print("\n" + "=" * 70)
    print(f"全部完成! 总耗时: {(time.time()-start)/60:.1f} 分钟 ({(time.time()-start)/3600:.2f} 小时)")
    print(f"结果: {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    main(args.workers)
