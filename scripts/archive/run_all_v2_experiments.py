#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS v2 一键运行脚本
=====================
整合所有关键实验，支持并行执行。

实验清单：
1. SOTA 对比实验 (100/200/300/500 节点)
2. 动态场景实验 (corridor/moving_bs/dropout)
3. 大规模可扩展性实验
4. Intel 数据集验证
5. 消融实验

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

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RESULTS_DIR = PROJECT_ROOT / "results"
LOG_DIR = RESULTS_DIR / "run_logs"

# 确保目录存在
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 实验配置
EXPERIMENTS = {
    "sota_comparison": {
        "script": "run_rigorous_sota_comparison.py",
        "priority": 1,
        "estimated_time_min": 30,
        "description": "SOTA 对比实验 (统计严谨版)"
    },
    "dynamic_corridor": {
        "script": "run_dynamic_corridor_compare.py",
        "priority": 1,
        "estimated_time_min": 45,
        "description": "动态走廊场景实验"
    },
    "dynamic_moving_bs": {
        "script": "run_dynamic_moving_bs_compare.py",
        "priority": 1,
        "estimated_time_min": 45,
        "description": "移动基站场景实验"
    },
    "dynamic_dropout": {
        "script": "run_dynamic_dropout_compare.py",
        "priority": 1,
        "estimated_time_min": 45,
        "description": "节点掉线场景实验"
    },
    "large_scale": {
        "script": "run_large_scale_scalability.py",
        "priority": 2,
        "estimated_time_min": 90,
        "description": "大规模可扩展性实验 (100-500节点)"
    },
    "intel_replay": {
        "script": "run_intel_replay.py",
        "priority": 2,
        "estimated_time_min": 30,
        "description": "Intel 真实数据集验证"
    },
    "intel_baselines": {
        "script": "run_intel_baselines_all.py",
        "priority": 3,
        "estimated_time_min": 40,
        "description": "Intel 数据集基线对比"
    },
    "significance_multi_topo": {
        "script": "run_significance_multi_topo.py",
        "priority": 3,
        "estimated_time_min": 60,
        "description": "多拓扑统计显著性检验"
    },
}


def run_experiment(name: str, config: dict) -> dict:
    """运行单个实验"""
    script_path = SCRIPTS_DIR / config["script"]
    if not script_path.exists():
        return {
            "name": name,
            "status": "skipped",
            "reason": f"Script not found: {script_path}"
        }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"{name}_{timestamp}.log"

    start_time = time.time()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting: {name}")
    print(f"   Description: {config['description']}")
    print(f"   Log: {log_file}")

    try:
        with open(log_file, "w", encoding="utf-8") as f:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(PROJECT_ROOT),
                stdout=f,
                stderr=subprocess.STDOUT,
                timeout=config["estimated_time_min"] * 60 * 3  # 3x 预估时间作为超时
            )

        elapsed = time.time() - start_time
        status = "success" if result.returncode == 0 else "failed"

        return {
            "name": name,
            "status": status,
            "returncode": result.returncode,
            "elapsed_seconds": elapsed,
            "log_file": str(log_file)
        }

    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "status": "timeout",
            "log_file": str(log_file)
        }
    except Exception as e:
        return {
            "name": name,
            "status": "error",
            "error": str(e)
        }


def run_all_experiments(max_workers: int = 4, priority_filter: int = None):
    """运行所有实验"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("AERIS v2 全量实验启动")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"并行度: {max_workers}")
    print(f"日志目录: {LOG_DIR}")
    print()

    # 筛选实验
    experiments_to_run = {}
    for name, config in EXPERIMENTS.items():
        if priority_filter is None or config["priority"] <= priority_filter:
            experiments_to_run[name] = config

    # 计算预估时间
    total_estimated = sum(c["estimated_time_min"] for c in experiments_to_run.values())
    parallel_estimated = total_estimated / max_workers

    print(f"实验数量: {len(experiments_to_run)}")
    print(f"预估总时间 (串行): {total_estimated} 分钟")
    print(f"预估总时间 (并行): {parallel_estimated:.0f} 分钟")
    print()

    # 按优先级分组
    priority_groups = {}
    for name, config in experiments_to_run.items():
        p = config["priority"]
        if p not in priority_groups:
            priority_groups[p] = []
        priority_groups[p].append((name, config))

    all_results = []
    start_time = time.time()

    # 按优先级顺序执行
    for priority in sorted(priority_groups.keys()):
        group = priority_groups[priority]
        print(f"\n--- Priority {priority} 实验组 ({len(group)} 个) ---")

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_experiment, name, config): name
                for name, config in group
            }

            for future in as_completed(futures):
                result = future.result()
                all_results.append(result)

                status_icon = "✓" if result["status"] == "success" else "✗"
                elapsed = result.get("elapsed_seconds", 0)
                print(f"[{status_icon}] {result['name']}: {result['status']} ({elapsed:.1f}s)")

    total_elapsed = time.time() - start_time

    # 保存汇总报告
    summary = {
        "timestamp": timestamp,
        "total_elapsed_seconds": total_elapsed,
        "experiments": all_results,
        "success_count": sum(1 for r in all_results if r["status"] == "success"),
        "failed_count": sum(1 for r in all_results if r["status"] != "success"),
    }

    summary_file = LOG_DIR / f"experiment_summary_{timestamp}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("实验完成汇总")
    print("=" * 70)
    print(f"总耗时: {total_elapsed/60:.1f} 分钟")
    print(f"成功: {summary['success_count']}/{len(all_results)}")
    print(f"汇总文件: {summary_file}")

    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AERIS v2 全量实验")
    parser.add_argument("--workers", type=int, default=4, help="并行进程数")
    parser.add_argument("--priority", type=int, default=None,
                        help="只运行指定优先级及以上的实验 (1=最高)")
    parser.add_argument("--list", action="store_true", help="列出所有实验")

    args = parser.parse_args()

    if args.list:
        print("可用实验:")
        for name, config in sorted(EXPERIMENTS.items(), key=lambda x: x[1]["priority"]):
            print(f"  [{config['priority']}] {name}: {config['description']}")
            print(f"      预估时间: {config['estimated_time_min']} 分钟")
        sys.exit(0)

    run_all_experiments(max_workers=args.workers, priority_filter=args.priority)
