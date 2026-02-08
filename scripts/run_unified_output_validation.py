#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一输出格式验证实验
====================
满足 Codex 审查要求: ≥4场景 × ≥6协议 × ≥10reps

此脚本生成符合论文发表标准的统一输出格式实验结果。

Author: AERIS Research Team
Date: 2026-01-27
"""

import sys
import os
import json
import time
import random
import argparse
import subprocess
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

sys.path.insert(0, str(SRC_DIR))

from experiment_output_format import (
    UnifiedExperimentResult, UnifiedMetrics,
    create_unified_result, save_unified_results, to_unified_dict
)

# ============================================================
# 实验配置 - 满足 Codex 审查要求
# ============================================================

# 4种场景 (拓扑)
SCENARIOS = ["uniform", "corridor", "clustered", "hotspot"]

# 6种协议 - 使用论文一致命名
PROTOCOLS = ["AERIS-R", "LEACH", "PEGASIS", "HEED", "TEEN", "AERIS-E"]

# 重复次数
N_REPLICATES = 15  # ≥10 reps

# 基础配置
BASE_SEED = 70000
N_NODES = 100
N_ROUNDS = 200


def get_git_commit() -> str:
    """获取当前 git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        return result.stdout.strip()[:12]
    except Exception:
        return "unknown"


def generate_positions(seed: int, n: int, width: float, height: float,
                       topology: str) -> List[Tuple[float, float]]:
    """生成节点位置"""
    rng = random.Random(seed)

    if topology == "corridor":
        # 走廊拓扑: 沿中心线分布
        positions = []
        for _ in range(n):
            x = rng.uniform(width * 0.1, width * 0.9)
            y = height * 0.5 + rng.gauss(0, height * 0.1)
            y = max(5, min(height - 5, y))
            positions.append((x, y))
    elif topology == "clustered":
        # 聚类拓扑: 3-4个聚类中心
        centers = [
            (width * 0.25, height * 0.25),
            (width * 0.75, height * 0.25),
            (width * 0.25, height * 0.75),
            (width * 0.75, height * 0.75),
        ]
        positions = []
        for _ in range(n):
            cx, cy = rng.choice(centers)
            x = cx + rng.gauss(0, width * 0.1)
            y = cy + rng.gauss(0, height * 0.1)
            x = max(5, min(width - 5, x))
            y = max(5, min(height - 5, y))
            positions.append((x, y))
    elif topology == "hotspot":
        # 热点拓扑: 中心密集，边缘稀疏
        positions = []
        for _ in range(n):
            if rng.random() < 0.6:
                # 60% 在中心区域
                x = width * 0.5 + rng.gauss(0, width * 0.15)
                y = height * 0.5 + rng.gauss(0, height * 0.15)
            else:
                # 40% 在边缘
                x = rng.uniform(5, width - 5)
                y = rng.uniform(5, height - 5)
            x = max(5, min(width - 5, x))
            y = max(5, min(height - 5, y))
            positions.append((x, y))
    else:
        # uniform: 均匀分布
        positions = [(rng.uniform(5, width-5), rng.uniform(5, height-5))
                     for _ in range(n)]

    return positions


def run_single_experiment(args: Tuple) -> Dict:
    """运行单个实验"""
    protocol, scenario, seed, nodes, rounds, replicate_id = args

    # 延迟导入避免多进程问题
    from benchmark_protocols import (
        NetworkConfig, LEACHProtocol, PEGASISProtocol,
        HEEDProtocolWrapper, TEENProtocolWrapper
    )
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
    from aeris_protocol import AerisProtocol

    width = 150.0
    height = 150.0

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
    cfg.gateway_k = 3
    cfg.positions = generate_positions(seed, nodes, width, height, scenario)

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
        elif protocol == "AERIS-R":
            # AERIS-R: Robust profile (论文命名)
            proto = AerisProtocol(
                cfg, profile="robust", verbose=False, seed=seed,
                enable_cas=True, enable_gateway=True, enable_skeleton=True
            )
        elif protocol == "AERIS-E":
            # AERIS-E: Energy profile (论文命名)
            proto = AerisProtocol(
                cfg, profile="energy", verbose=False, seed=seed,
                enable_cas=True, enable_gateway=True, enable_skeleton=True
            )
        else:
            return {
                "protocol": protocol, "scenario": scenario, "seed": seed,
                "status": "skipped", "reason": "unsupported"
            }

        result = proto.run_simulation(rounds)

        # 获取存活节点数
        alive = result.get("alive_nodes", nodes)
        if alive == 0:
            alive = result.get("surviving_nodes", nodes)

        return {
            "protocol": protocol,
            "scenario": scenario,
            "seed": seed,
            "replicate_id": replicate_id,
            "n_nodes": nodes,
            "n_rounds": rounds,
            "pdr": result.get("packet_delivery_ratio", 0),
            "pdr_end2end": (
                result.get("packet_delivery_ratio_end2end", -1.0)
                if STRICT_PDR_END2END
                else result.get("packet_delivery_ratio_end2end", result.get("packet_delivery_ratio", 0))
            ),
            "energy": result.get("total_energy_consumed", 0),
            "alive_nodes": alive,
            "lifetime": result.get("network_lifetime", rounds),
            "status": "ok"
        }
    except Exception as e:
        return {
            "protocol": protocol, "scenario": scenario, "seed": seed,
            "replicate_id": replicate_id,
            "status": "error", "error": str(e)
        }


def main(workers: int = 8, replicates: int = N_REPLICATES):
    """主函数"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    git_commit = get_git_commit()

    print("=" * 70)
    print("统一输出格式验证实验")
    print("=" * 70)
    print(f"场景数: {len(SCENARIOS)} ({', '.join(SCENARIOS)})")
    print(f"协议数: {len(PROTOCOLS)} ({', '.join(PROTOCOLS)})")
    print(f"重复次数: {replicates}")
    print(f"总实验数: {len(SCENARIOS) * len(PROTOCOLS) * replicates}")
    print(f"Git commit: {git_commit}")
    print("=" * 70)

    # 构建任务列表 - 添加 replicate_id 用于追溯
    all_tasks = []
    seeds_used = []
    for scenario in SCENARIOS:
        for protocol in PROTOCOLS:
            for rep in range(replicates):
                seed = BASE_SEED + rep * 1000 + stable_hash(scenario) % 100
                seeds_used.append(seed)
                # 添加 rep (replicate_id) 到任务参数
                all_tasks.append((protocol, scenario, seed, N_NODES, N_ROUNDS, rep))

    print(f"\n开始运行 {len(all_tasks)} 个实验...")
    start_time = time.time()

    results = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_single_experiment, t): t for t in all_tasks}
        done = 0
        for future in as_completed(futures):
            done += 1
            r = future.result()
            results.append(r)
            if done % 20 == 0 or done == len(all_tasks):
                elapsed = time.time() - start_time
                print(f"  进度: [{done}/{len(all_tasks)}] {elapsed:.1f}s")

    elapsed_total = time.time() - start_time
    print(f"\n实验完成! 总耗时: {elapsed_total:.1f}s")

    # 统计成功/失败
    ok_count = sum(1 for r in results if r.get("status") == "ok")
    error_count = sum(1 for r in results if r.get("status") == "error")
    skip_count = sum(1 for r in results if r.get("status") == "skipped")

    print(f"成功: {ok_count}, 错误: {error_count}, 跳过: {skip_count}")

    # 转换为统一格式 - 包含 metrics 字典结构
    unified_results = []
    for r in results:
        if r.get("status") == "ok":
            # 计算 j_per_delivered
            total_pkts = r["n_nodes"] * r["n_rounds"]
            delivered = int(total_pkts * r["pdr"])
            j_per_del = r["energy"] / max(delivered, 1)

            ur_dict = {
                "protocol": r["protocol"],
                "scenario": r["scenario"],
                "n_nodes": r["n_nodes"],
                "n_rounds": r["n_rounds"],
                "seed": r["seed"],
                "replicate_id": r["replicate_id"],
                "replicate_count_total": replicates,
                "metrics": {
                    "pdr_end2end": r.get("pdr_end2end", -1.0),
                    "pdr_hop": r["pdr"],
                    "energy_total_j": r["energy"],
                    "j_per_delivered": j_per_del,
                    "alive_nodes": r["alive_nodes"],
                    "lifetime_rounds": r.get("lifetime", r["n_rounds"]),
                }
            }
            unified_results.append(ur_dict)

    # 构建完整输出 - 顶层包含 n_results 和 format_version
    output = {
        "n_results": len(unified_results),
        "format_version": "1.0",
        "schema_type": "unified_metrics",
        "metadata": {
            "experiment": "unified_output_validation",
            "timestamp": timestamp,
            "git_commit": git_commit,
            "output_version": OUTPUT_VERSION,
            "n_scenarios": len(SCENARIOS),
            "scenarios": SCENARIOS,
            "n_protocols": len(PROTOCOLS),
            "protocols": PROTOCOLS,
            "n_replicates": replicates,
            "replicate_count_total": replicates,
            "base_seed": BASE_SEED,
            "seed_stride": 1000,
            "seeds_used": list(set(seeds_used)),
            "n_nodes": N_NODES,
            "n_rounds": N_ROUNDS,
            "total_experiments": len(all_tasks),
            "successful_experiments": ok_count,
            "elapsed_seconds": elapsed_total,
        },
        "summary": {},
        "results": unified_results
    }

    # 计算每个场景×协议的统计摘要（含 95% CI）
    from scipy import stats as sp_stats
    for scenario in SCENARIOS:
        output["summary"][scenario] = {}
        for protocol in PROTOCOLS:
            matching = [r for r in results
                       if r.get("status") == "ok"
                       and r["scenario"] == scenario
                       and r["protocol"] == protocol]
            if matching:
                pdrs = [r["pdr"] for r in matching]
                energies = [r["energy"] for r in matching]
                n = len(matching)
                pdr_mean = float(np.mean(pdrs))
                pdr_std = float(np.std(pdrs, ddof=1)) if n > 1 else 0.0
                # 95% CI using t-distribution
                if n > 1:
                    ci = sp_stats.t.interval(0.95, n-1, loc=pdr_mean, scale=pdr_std/np.sqrt(n))
                    pdr_ci95_low, pdr_ci95_high = float(ci[0]), float(ci[1])
                else:
                    pdr_ci95_low, pdr_ci95_high = pdr_mean, pdr_mean
                output["summary"][scenario][protocol] = {
                    "n": n,
                    "pdr_mean": pdr_mean,
                    "pdr_std": pdr_std,
                    "pdr_ci95_low": pdr_ci95_low,
                    "pdr_ci95_high": pdr_ci95_high,
                    "pdr_min": float(np.min(pdrs)),
                    "pdr_max": float(np.max(pdrs)),
                    "energy_mean": float(np.mean(energies)),
                    "energy_std": float(np.std(energies, ddof=1)) if n > 1 else 0.0,
                }

    # 保存结果
    out_file = RESULTS_DIR / f"unified_output_validation_{timestamp}_{OUTPUT_VERSION}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {out_file}")

    # 打印摘要表格
    print("\n" + "=" * 70)
    print("PDR 摘要 (mean ± std)")
    print("=" * 70)
    print(f"{'场景':<12}", end="")
    for proto in PROTOCOLS:
        print(f"{proto:<14}", end="")
    print()
    print("-" * 70)

    for scenario in SCENARIOS:
        print(f"{scenario:<12}", end="")
        for proto in PROTOCOLS:
            stats = output["summary"].get(scenario, {}).get(proto, {})
            if stats:
                pdr_m = stats["pdr_mean"] * 100
                pdr_s = stats["pdr_std"] * 100
                print(f"{pdr_m:.1f}±{pdr_s:.1f}%    ", end="")
            else:
                print(f"{'N/A':<14}", end="")
        print()

    print("=" * 70)

    # 验证是否满足 Codex 要求
    print("\n" + "=" * 70)
    print("Codex 审查要求验证")
    print("=" * 70)
    print(f"✓ 场景数 ≥ 4: {len(SCENARIOS)} >= 4 -> {'PASS' if len(SCENARIOS) >= 4 else 'FAIL'}")
    print(f"✓ 协议数 ≥ 6: {len(PROTOCOLS)} >= 6 -> {'PASS' if len(PROTOCOLS) >= 6 else 'FAIL'}")
    print(f"✓ 重复数 ≥ 10: {replicates} >= 10 -> {'PASS' if replicates >= 10 else 'FAIL'}")
    print(f"✓ 成功实验数: {ok_count}/{len(all_tasks)}")
    print(f"✓ Git commit 追溯: {git_commit}")
    print(f"✓ 统一输出格式: format_version=1.0")
    print("=" * 70)

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="统一输出格式验证实验")
    parser.add_argument("--workers", type=int, default=8, help="并行工作进程数")
    parser.add_argument("--replicates", type=int, default=N_REPLICATES, help="重复次数")
    args = parser.parse_args()

    main(workers=args.workers, replicates=args.replicates)
