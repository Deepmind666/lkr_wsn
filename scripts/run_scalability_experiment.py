#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scalability experiment across network sizes with multiple protocols.

Publication-tier experiment for AERIS paper.
Outputs results with full metadata for reproducibility.
"""

import argparse
import contextlib
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple

import numpy as np

try:
    import psutil
except ImportError:
    psutil = None


sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from benchmark_protocols import (  # noqa: E402
    NetworkConfig,
    LEACHProtocol,
    PEGASISProtocol,
    HEEDProtocolWrapper,
    TEENProtocolWrapper,
)
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform  # noqa: E402
from aeris_protocol import AerisProtocol  # noqa: E402


OUTPUT_VERSION = "v2_1"
DEFAULT_PROTOCOLS = ("AERIS", "LEACH", "PEGASIS", "HEED", "TEEN")
NODE_COUNTS = (50, 100, 200, 300, 500)

# Paper-aligned defaults
DEFAULT_AREA_SIZE = 200.0
DEFAULT_BASE_STATION = (100.0, 200.0)
DEFAULT_INITIAL_ENERGY = 2.0
DEFAULT_PACKET_SIZE = 1024
DEFAULT_TX_POWER = 10.0
DEFAULT_ROUNDS = 300
DEFAULT_ENV = "indoor_office"
DEFAULT_MAX_CPU_PERCENT = 70.0
DEFAULT_MAX_MEM_PERCENT = 70.0
DEFAULT_RESOURCE_CHECK_SEC = 2.0


def stable_hash(s: str) -> int:
    """Deterministic hash replacement for Python built-in hash()."""
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16) % (10**9)


def get_git_commit() -> str:
    """Get current git commit short hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def get_safe_worker_limit(requested_workers: int, max_cpu_percent: float) -> int:
    """Cap workers so this process does not request > configured CPU share."""
    cpu_total = max(1, os.cpu_count() or 1)
    # Keep one-core buffer below the hard threshold to avoid burst overshoot.
    cpu_budget_workers = max(1, math.floor(cpu_total * (max_cpu_percent / 100.0)) - 1)
    return max(1, min(requested_workers, cpu_budget_workers))


def has_resource_headroom(max_cpu_percent: float, max_mem_percent: float) -> bool:
    """Check if system usage is within configured thresholds."""
    if psutil is None:
        return True
    cpu_now = psutil.cpu_percent(interval=0.25)
    mem_now = psutil.virtual_memory().percent
    return cpu_now <= max_cpu_percent and mem_now <= max_mem_percent


def wait_for_resource_headroom(max_cpu_percent: float, max_mem_percent: float, check_sec: float) -> None:
    """Block until CPU and memory are under thresholds."""
    if psutil is None:
        print("[WARN] psutil not installed; resource headroom checks disabled.")
        return
    attempts = 0
    while True:
        cpu_now = psutil.cpu_percent(interval=0.25)
        mem_now = psutil.virtual_memory().percent
        if cpu_now <= max_cpu_percent and mem_now <= max_mem_percent:
            if attempts > 0:
                print(f"[ResourceGuard] Recovered: cpu={cpu_now:.1f}% mem={mem_now:.1f}%")
            return
        attempts += 1
        if attempts == 1 or attempts % 10 == 0:
            print(
                "[ResourceGuard] Waiting: "
                f"cpu={cpu_now:.1f}%>{max_cpu_percent:.1f}% or mem={mem_now:.1f}%>{max_mem_percent:.1f}%"
            )
        time.sleep(max(check_sec, 0.5))


def generate_positions(seed: int, num_nodes: int, width: float, height: float) -> List[Tuple[float, float]]:
    rng = random.Random(seed)
    return [
        (rng.uniform(5.0, width - 5.0), rng.uniform(5.0, height - 5.0))
        for _ in range(num_nodes)
    ]


def build_config(
    num_nodes: int,
    seed: int,
    area_size: float,
    base_station: Tuple[float, float],
    env: str,
    tx_power: float,
) -> NetworkConfig:
    """Build network config with fixed 200x200 area (paper-aligned)."""
    cfg = NetworkConfig(
        num_nodes=num_nodes,
        area_width=area_size,
        area_height=area_size,
        base_station_x=base_station[0],
        base_station_y=base_station[1],
        initial_energy=DEFAULT_INITIAL_ENERGY,
        packet_size=DEFAULT_PACKET_SIZE,
        temperature_c=25.0,
        humidity_ratio=0.5,
        enable_channel=True,
        channel_env=env,
        tx_power_dbm=tx_power,
        link_retx=1,
        link_retx_power_step=1.0,
    )
    cfg.positions = generate_positions(seed, num_nodes, area_size, area_size)
    cfg.gateway_k = max(2, int(num_nodes / 25))
    cfg.gateway_retry_limit = 1
    cfg.gateway_rescue_direct = True
    cfg.intra_link_retx = 2
    cfg.intra_link_power_step = 1.5
    return cfg


def compute_pdr_expected(res: Dict) -> float:
    """Unified PDR fallback chain."""
    if "pdr_expected" in res and res["pdr_expected"] is not None:
        val = float(res["pdr_expected"])
        if val >= 0:
            return val

    if "packet_delivery_ratio_end2end" in res and res["packet_delivery_ratio_end2end"] is not None:
        val = float(res["packet_delivery_ratio_end2end"])
        if val >= 0:
            return val

    add_m = res.get("additional_metrics", {})
    bs_del = add_m.get("bs_delivered_total", 0)
    src_total = add_m.get("source_packets_total", 0)
    if src_total > 0:
        return float(bs_del) / float(src_total)

    bs_del = res.get("bs_delivered", 0)
    src_exp = res.get("source_packets_expected", 0)
    if src_exp > 0:
        return float(bs_del) / float(src_exp)

    recv = res.get("packets_received", res.get("total_packets_received", 0))
    sent = res.get("packets_sent", res.get("total_packets_sent", 0))
    if sent > 0:
        return float(recv) / float(sent)

    return -1.0


def run_protocol(
    protocol: str,
    cfg: NetworkConfig,
    seed: int,
    rounds: int,
    verbose_protocol_logs: bool = False,
) -> Dict:
    random.seed(seed)
    np.random.seed(seed)
    cfg_local = deepcopy(cfg)
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    def _run_once() -> Dict:
        if protocol == "LEACH":
            return LEACHProtocol(cfg_local, em).run_simulation(rounds)
        if protocol == "PEGASIS":
            return PEGASISProtocol(cfg_local, em).run_simulation(rounds)
        if protocol == "HEED":
            return HEEDProtocolWrapper(cfg_local, em).run_simulation(rounds)
        if protocol == "TEEN":
            return TEENProtocolWrapper(cfg_local, em).run_simulation(rounds)
        if protocol == "AERIS":
            return AerisProtocol(
                cfg_local,
                enable_cas=True,
                enable_fairness=True,
                enable_gateway=True,
                enable_skeleton=True,
                profile="energy",
                verbose=False,
                seed=seed,
            ).run_simulation(rounds)
        raise ValueError(f"Unknown protocol: {protocol}")

    if verbose_protocol_logs:
        res = _run_once()
    else:
        with open(os.devnull, "w", encoding="utf-8", errors="ignore") as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                res = _run_once()

    pdr_expected = compute_pdr_expected(res)
    return {
        "pdr_expected": pdr_expected,
        "energy": float(res.get("total_energy_consumed", 0.0)),
        "lifetime": int(res.get("network_lifetime", 0)),
        "alive_nodes": int(res.get("final_alive_nodes", res.get("alive_nodes", 0))),
        "total_rounds": int(res.get("total_rounds", rounds)),
    }


def run_task(args: Tuple) -> Dict:
    """Execute a single experiment task and never raise to parent."""
    (
        num_nodes,
        replicate,
        protocol,
        base_seed,
        area_size,
        base_station,
        env,
        tx_power,
        rounds,
        verbose_protocol_logs,
    ) = args
    seed = base_seed + replicate * 997 + stable_hash(protocol) % 997

    try:
        cfg = build_config(num_nodes, seed, area_size, base_station, env, tx_power)
        metrics = run_protocol(protocol, cfg, seed + 17, rounds, verbose_protocol_logs=verbose_protocol_logs)
        return {
            "num_nodes": num_nodes,
            "replicate": replicate,
            "protocol": protocol,
            "seed": seed,
            "environment": env,
            "metrics": metrics,
            "success": True,
            "error": None,
        }
    except Exception as e:
        return {
            "num_nodes": num_nodes,
            "replicate": replicate,
            "protocol": protocol,
            "seed": seed,
            "environment": env,
            "metrics": {
                "pdr_expected": -1.0,
                "energy": 0.0,
                "lifetime": 0,
                "alive_nodes": 0,
                "total_rounds": 0,
            },
            "success": False,
            "error": str(e),
        }


def execute_tasks(
    tasks: List[Tuple],
    workers: int,
    max_cpu_percent: float,
    max_mem_percent: float,
    resource_check_sec: float,
    progress_step: int = 10,
) -> List[Dict]:
    """Run with bounded in-flight futures to reduce memory pressure."""
    runs: List[Dict] = []
    total = len(tasks)
    completed = 0
    failed = 0
    next_idx = 0
    max_inflight = max(workers * 4, workers)

    wait_for_resource_headroom(max_cpu_percent, max_mem_percent, resource_check_sec)

    with ProcessPoolExecutor(max_workers=workers) as executor:
        inflight = {}

        while next_idx < total and len(inflight) < max_inflight:
            if not has_resource_headroom(max_cpu_percent, max_mem_percent):
                time.sleep(max(resource_check_sec, 0.5))
                continue
            fut = executor.submit(run_task, tasks[next_idx])
            inflight[fut] = tasks[next_idx]
            next_idx += 1

        while inflight:
            for fut in as_completed(list(inflight.keys())):
                _ = inflight.pop(fut)
                result = fut.result()
                runs.append(result)
                completed += 1
                if not result.get("success", True):
                    failed += 1

                if completed % progress_step == 0 or completed == total:
                    print(f"[Scalability] {completed}/{total} completed, failed={failed}")

                while next_idx < total and len(inflight) < max_inflight:
                    if not has_resource_headroom(max_cpu_percent, max_mem_percent):
                        time.sleep(max(resource_check_sec, 0.5))
                        break
                    nf = executor.submit(run_task, tasks[next_idx])
                    inflight[nf] = tasks[next_idx]
                    next_idx += 1
                break

    return runs


def aggregate(runs: List[Dict], node_counts: Tuple, protocols: Tuple) -> Dict:
    """Aggregate summary by node_count and protocol using valid pdr_expected only."""
    summary: Dict = {}
    for num_nodes in node_counts:
        summary[num_nodes] = {}
        for protocol in protocols:
            filtered = [r for r in runs if r["num_nodes"] == num_nodes and r["protocol"] == protocol]
            valid = [r for r in filtered if r["metrics"]["pdr_expected"] >= 0]
            pdrs = [r["metrics"]["pdr_expected"] for r in valid]
            energies = [r["metrics"]["energy"] for r in valid]
            if not pdrs:
                continue
            summary[num_nodes][protocol] = {
                "pdr_mean": float(np.mean(pdrs)),
                "pdr_std": float(np.std(pdrs, ddof=1)) if len(pdrs) > 1 else 0.0,
                "energy_mean": float(np.mean(energies)),
                "energy_std": float(np.std(energies, ddof=1)) if len(energies) > 1 else 0.0,
                "n": len(pdrs),
            }
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Run scalability experiment.")
    parser.add_argument("--replicates", type=int, default=30, help="Replicates per config")
    parser.add_argument("--workers", type=int, default=6, help="Parallel workers")
    parser.add_argument("--seed", type=int, default=42001, help="Base seed")
    parser.add_argument("--nodes", default=None, help="Comma-separated node counts")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="Simulation rounds")
    parser.add_argument("--env", type=str, default=DEFAULT_ENV, help="Environment type")
    parser.add_argument("--tx-power", type=float, default=DEFAULT_TX_POWER, help="TX power dBm")
    parser.add_argument("--run-tier", type=str, default="publication", help="Run tier")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--allow-partial", action="store_true", help="Exit 0 even if some tasks fail")
    parser.add_argument(
        "--verbose-protocol-logs",
        action="store_true",
        help="Keep protocol internal debug logs (default is silent for stability)",
    )
    parser.add_argument(
        "--max-cpu-percent",
        type=float,
        default=DEFAULT_MAX_CPU_PERCENT,
        help="Maximum allowed system CPU percentage before queueing new tasks",
    )
    parser.add_argument(
        "--max-mem-percent",
        type=float,
        default=DEFAULT_MAX_MEM_PERCENT,
        help="Maximum allowed system memory percentage before queueing new tasks",
    )
    parser.add_argument(
        "--resource-check-sec",
        type=float,
        default=DEFAULT_RESOURCE_CHECK_SEC,
        help="Seconds between resource guard checks",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    protocols = DEFAULT_PROTOCOLS
    workers = get_safe_worker_limit(args.workers, args.max_cpu_percent)
    if workers < args.workers:
        print(
            "[ResourceGuard] Worker cap applied: "
            f"requested={args.workers}, capped={workers}, max_cpu_percent={args.max_cpu_percent:.1f}"
        )

    if args.nodes:
        node_counts = tuple(int(x.strip()) for x in args.nodes.split(",") if x.strip())
    else:
        node_counts = NODE_COUNTS

    area_size = DEFAULT_AREA_SIZE
    base_station = DEFAULT_BASE_STATION

    tasks: List[Tuple] = []
    for num_nodes in node_counts:
        for rep in range(args.replicates):
            for protocol in protocols:
                tasks.append((
                    num_nodes,
                    rep,
                    protocol,
                    args.seed,
                    area_size,
                    base_station,
                    args.env,
                    args.tx_power,
                    args.rounds,
                    args.verbose_protocol_logs,
                ))

    runs = execute_tasks(
        tasks,
        workers,
        args.max_cpu_percent,
        args.max_mem_percent,
        args.resource_check_sec,
        progress_step=10,
    )
    seeds_used = sorted(set(r["seed"] for r in runs))
    failed_runs = sum(1 for r in runs if not r.get("success", True))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = {
        "timestamp": timestamp,
        "git_commit": get_git_commit(),
        "experiment_type": "scalability",
        "run_tier": args.run_tier,
        "primary_metric": "pdr_expected",
        "environment": args.env,
        "tx_power_dbm": args.tx_power,
        "max_cpu_percent": args.max_cpu_percent,
        "max_mem_percent": args.max_mem_percent,
        "workers_requested": args.workers,
        "workers_effective": workers,
        "error_runs": failed_runs,
        "config": {
            "seeds": seeds_used,
            "node_counts": list(node_counts),
            "round_counts": [args.rounds],
            "dropout_rates": [0.0],
            "protocols": list(protocols),
            "area_size": area_size,
            "base_station": list(base_station),
            "packet_size": DEFAULT_PACKET_SIZE,
            "initial_energy": DEFAULT_INITIAL_ENERGY,
            "output_version": OUTPUT_VERSION,
        },
        "raw_results": runs,
        "summary": aggregate(runs, node_counts, protocols),
    }

    out_path = args.output or os.path.join(
        os.path.dirname(__file__),
        "..",
        "results",
        "mega_experiments",
        f"scalability_{timestamp}.json",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"[DONE] Wrote {out_path}")
    if failed_runs > 0:
        print(f"[WARN] failed_runs={failed_runs}")
        if not args.allow_partial:
            sys.exit(2)


if __name__ == "__main__":
    main()
