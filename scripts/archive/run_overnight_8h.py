#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS 过夜实验调度器 (8小时版)
============================
通过调用现有脚本运行关键实验，避免API/类名变更导致的崩溃。

目标:
1) Intel 消融与敏感性
2) 动态场景对比
3) 大规模可扩展性
4) SOTA 基线对比 (如可用)

作者: AERIS Research Team
日期: 2026-01-27
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RESULTS_DIR = PROJECT_ROOT / "results"
RUN_LOG_DIR = RESULTS_DIR / "run_logs"
LOG_FILE = RESULTS_DIR / "overnight_8h_log.txt"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_message(msg: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_cmd(name: str, cmd: List[str], cwd: Path, timeout_s: int = None) -> Dict:
    log_message(f"[START] {name}: {' '.join(cmd)}")
    start = time.time()
    log_path = RUN_LOG_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    result = {
        "name": name,
        "cmd": cmd,
        "log": str(log_path),
        "returncode": None,
        "elapsed_seconds": None,
        "error": None,
    }
    try:
        with open(log_path, "w", encoding="utf-8") as lf:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                stdout=lf,
                stderr=lf,
                timeout=timeout_s,
                check=False,
                text=True,
            )
        result["returncode"] = proc.returncode
    except subprocess.TimeoutExpired:
        result["error"] = "timeout"
    except Exception as exc:
        result["error"] = str(exc)
    result["elapsed_seconds"] = time.time() - start
    log_message(f"[END] {name}: rc={result['returncode']} time={result['elapsed_seconds']:.1f}s")
    return result


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Run overnight experiments via existing scripts")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 8) - 2), help="parallel workers where supported")
    parser.add_argument("--intel-repeats", type=int, default=50, help="repeats for Intel ablation/sensitivity (parallel scripts)")
    parser.add_argument("--dynamic-reps", type=int, default=30, help="replicates for dynamic corridor/moving/dropout")
    parser.add_argument("--scale-reps", type=int, default=30, help="replicates for large-scale scalability")
    parser.add_argument("--scale-rounds", type=int, default=200, help="rounds for large-scale scalability")
    parser.add_argument("--skip-sota", action="store_true", help="skip SOTA baseline comparison")
    parser.add_argument("--summary-json", default=None, help="summary output json")
    return parser.parse_args()


def main():
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    log_message("=" * 70)
    log_message("AERIS 过夜实验调度器 启动")
    log_message(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"workers={args.workers}, intel_repeats={args.intel_repeats}, dynamic_reps={args.dynamic_reps}, scale_reps={args.scale_reps}")
    log_message("=" * 70)

    tasks: List[Dict] = []

    if not args.skip_sota:
        tasks.append({
            "name": "sota_comparison_v2",
            "cmd": [sys.executable, str(SCRIPTS_DIR / "run_sota_comparison_v2.py")],
        })

    tasks.extend([
        {
            "name": "intel_ablation_parallel",
            "cmd": [sys.executable, str(SCRIPTS_DIR / "run_intel_ablation_parallel.py"), str(args.intel_repeats), str(args.workers)],
        },
        {
            "name": "intel_sensitivity_parallel",
            "cmd": [sys.executable, str(SCRIPTS_DIR / "run_intel_sensitivity_parallel.py"), str(args.intel_repeats), str(args.workers)],
        },
        {
            "name": "dynamic_corridor_compare",
            "cmd": [
                sys.executable,
                str(SCRIPTS_DIR / "run_dynamic_corridor_compare.py"),
                "--replicates", str(args.dynamic_reps),
                "--output", str(RESULTS_DIR / f"dynamic_corridor_compare_{timestamp}.json"),
            ],
        },
        {
            "name": "dynamic_moving_bs_compare",
            "cmd": [
                sys.executable,
                str(SCRIPTS_DIR / "run_dynamic_moving_bs_compare.py"),
                "--replicates", str(args.dynamic_reps),
                "--output", str(RESULTS_DIR / f"dynamic_moving_bs_compare_{timestamp}.json"),
            ],
        },
        {
            "name": "dynamic_dropout_compare",
            "cmd": [
                sys.executable,
                str(SCRIPTS_DIR / "run_dynamic_dropout_compare.py"),
                "--replicates", str(args.dynamic_reps),
                "--output", str(RESULTS_DIR / f"dynamic_dropout_compare_{timestamp}.json"),
            ],
        },
        {
            "name": "large_scale_scalability",
            "cmd": [
                sys.executable,
                str(SCRIPTS_DIR / "run_large_scale_scalability.py"),
                "--replicates", str(args.scale_reps),
                "--workers", str(args.workers),
                "--rounds", str(args.scale_rounds),
                "--output", str(RESULTS_DIR / f"large_scale_scalability_{timestamp}.json"),
            ],
        },
    ])

    summary = {
        "start_time": datetime.now().isoformat(),
        "workers": args.workers,
        "intel_repeats": args.intel_repeats,
        "dynamic_reps": args.dynamic_reps,
        "scale_reps": args.scale_reps,
        "tasks": [],
    }

    start = time.time()
    for task in tasks:
        result = run_cmd(task["name"], task["cmd"], PROJECT_ROOT)
        summary["tasks"].append(result)

    summary["total_time_seconds"] = time.time() - start
    summary["end_time"] = datetime.now().isoformat()
    summary["format_version"] = "1.0"  # GPT DeepSearch: Add format version

    summary_path = args.summary_json or (RESULTS_DIR / f"overnight_8h_complete_{timestamp}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log_message("=" * 70)
    log_message(f"所有实验完成，总耗时: {summary['total_time_seconds'] / 3600:.2f} 小时")
    log_message(f"Summary: {summary_path}")
    log_message("=" * 70)


if __name__ == "__main__":
    main()
