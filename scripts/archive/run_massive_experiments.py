#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS 大规模实验脚本 (10小时版)
================================
高强度实验配置，支持长时间运行。

实验规模：
- 重复次数：100次 (统计显著性)
- 节点规模：100/200/300/500/800 节点
- 轮次：500-2000轮
- 动态场景：8个phase

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

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RESULTS_DIR = PROJECT_ROOT / "results"
LOG_DIR = RESULTS_DIR / "run_logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)

# 大规模实验配置 (10小时版)
MASSIVE_EXPERIMENTS = {
    # P1: 核心对比实验 (高重复)
    "sota_rigorous": {
        "script": "run_rigorous_sota_comparison.py",
        "args": ["--replicates", "50", "--nodes", "100,200,300,500", "--rounds", "500"],
        "priority": 1,
        "timeout_hours": 3,
        "description": "SOTA严谨对比 (50重复, 4规模)"
    },
    "large_scale_extended": {
        "script": "run_large_scale_scalability.py",
        "args": ["--replicates", "60", "--workers", "16", "--rounds", "1000"],
        "priority": 1,
        "timeout_hours": 4,
        "description": "大规模可扩展性 (60重复, 1000轮)"
    },

    # P2: 动态场景实验 (高重复)
    "dynamic_corridor_massive": {
        "script": "run_dynamic_corridor_compare.py",
        "args": ["--replicates", "100", "--rounds", "300"],
        "priority": 2,
        "timeout_hours": 2,
        "description": "动态走廊 (100重复)"
    },
    "dynamic_moving_bs_massive": {
        "script": "run_dynamic_moving_bs_compare.py",
        "args": ["--replicates", "100", "--rounds", "300"],
        "priority": 2,
        "timeout_hours": 2,
        "description": "移动基站 (100重复)"
    },
    "dynamic_dropout_massive": {
        "script": "run_dynamic_dropout_compare.py",
        "args": ["--replicates", "100", "--rounds", "300"],
        "priority": 2,
        "timeout_hours": 2,
        "description": "节点掉线 (100重复)"
    },

    # P3: Intel真实数据集
    "intel_replay_extended": {
        "script": "run_intel_replay.py",
        "args": ["--replicates", "30", "--rounds", "500"],
        "priority": 3,
        "timeout_hours": 1.5,
        "description": "Intel数据集验证 (30重复)"
    },
    "intel_baselines_full": {
        "script": "run_intel_baselines_all.py",
        "args": ["--replicates", "30"],
        "priority": 3,
        "timeout_hours": 1.5,
        "description": "Intel基线对比 (30重复)"
    },

    # P4: 统计显著性检验
    "significance_multi_topo": {
        "script": "run_significance_multi_topo.py",
        "args": ["--replicates", "50"],
        "priority": 4,
        "timeout_hours": 2,
        "description": "多拓扑显著性检验 (50重复)"
    },
    "stats_bootstrap": {
        "script": "run_stats_bootstrap.py",
        "args": ["--bootstrap", "5000"],
        "priority": 4,
        "timeout_hours": 1,
        "description": "Bootstrap统计分析 (5000次)"
    },

    # P5: 消融实验
    "intel_ablation": {
        "script": "run_intel_ablation.py",
        "args": ["--replicates", "30"],
        "priority": 5,
        "timeout_hours": 1.5,
        "description": "消融实验 (30重复)"
    },
}


def run_experiment(name: str, config: dict) -> dict:
    """运行单个实验"""
    script_path = SCRIPTS_DIR / config["script"]
    if not script_path.exists():
        return {"name": name, "status": "skipped", "reason": f"Script not found: {script_path}"}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"massive_{name}_{timestamp}.log"

    start_time = time.time()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting: {name}")
    print(f"   {config['description']}")
    print(f"   Timeout: {config['timeout_hours']}h | Log: {log_file.name}")

    cmd = [sys.executable, str(script_path)] + config.get("args", [])
    timeout_sec = config["timeout_hours"] * 3600

    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"Started: {datetime.now().isoformat()}\n")
            f.write("=" * 70 + "\n\n")
            f.flush()

            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=f,
                stderr=subprocess.STDOUT,
                timeout=timeout_sec
            )

        elapsed = time.time() - start_time
        status = "success" if result.returncode == 0 else "failed"

        return {
            "name": name,
            "status": status,
            "returncode": result.returncode,
            "elapsed_seconds": elapsed,
            "elapsed_hours": elapsed / 3600,
            "log_file": str(log_file)
        }

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        return {
            "name": name,
            "status": "timeout",
            "elapsed_hours": elapsed / 3600,
            "log_file": str(log_file)
        }
    except Exception as e:
        return {"name": name, "status": "error", "error": str(e)}


def run_massive_experiments(max_workers: int = 8):
    """运行大规模实验"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("AERIS 大规模实验 (10小时版)")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"并行度: {max_workers}")
    print(f"实验数量: {len(MASSIVE_EXPERIMENTS)}")

    total_hours = sum(c["timeout_hours"] for c in MASSIVE_EXPERIMENTS.values())
    print(f"最大总时长: {total_hours:.1f} 小时 (串行)")
    print(f"预估时长: {total_hours/max_workers:.1f} 小时 (并行)")
    print()

    # 按优先级分组
    priority_groups = {}
    for name, config in MASSIVE_EXPERIMENTS.items():
        p = config["priority"]
        if p not in priority_groups:
            priority_groups[p] = []
        priority_groups[p].append((name, config))

    all_results = []
    start_time = time.time()

    for priority in sorted(priority_groups.keys()):
        group = priority_groups[priority]
        print(f"\n{'='*70}")
        print(f"Priority {priority} ({len(group)} experiments)")
        print("=" * 70)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_experiment, name, config): name
                for name, config in group
            }

            for future in as_completed(futures):
                result = future.result()
                all_results.append(result)

                icon = "✓" if result["status"] == "success" else "✗"
                hours = result.get("elapsed_hours", 0)
                print(f"[{icon}] {result['name']}: {result['status']} ({hours:.2f}h)")

    total_elapsed = time.time() - start_time

    # 保存汇总
    summary = {
        "timestamp": timestamp,
        "total_elapsed_hours": total_elapsed / 3600,
        "experiments": all_results,
        "success_count": sum(1 for r in all_results if r["status"] == "success"),
        "failed_count": sum(1 for r in all_results if r["status"] != "success"),
    }

    summary_file = LOG_DIR / f"massive_summary_{timestamp}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("实验完成")
    print("=" * 70)
    print(f"总耗时: {total_elapsed/3600:.2f} 小时")
    print(f"成功: {summary['success_count']}/{len(all_results)}")
    print(f"汇总: {summary_file}")

    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AERIS大规模实验")
    parser.add_argument("--workers", type=int, default=8, help="并行进程数")
    parser.add_argument("--list", action="store_true", help="列出实验")
    args = parser.parse_args()

    if args.list:
        print("大规模实验清单:")
        for name, cfg in sorted(MASSIVE_EXPERIMENTS.items(), key=lambda x: x[1]["priority"]):
            print(f"  [P{cfg['priority']}] {name}")
            print(f"       {cfg['description']}")
            print(f"       超时: {cfg['timeout_hours']}h")
        sys.exit(0)

    run_massive_experiments(max_workers=args.workers)
