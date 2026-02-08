#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Large-scale scalability experiment for paper validation.
Tests: 100, 200, 300, 500 nodes with 30 replicates each.

This script provides REAL data to support paper claims.
"""

import argparse
import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime
from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple

import numpy as np


def stable_hash(s: str) -> int:
    """确定性哈希函数，替代Python内置hash()以保证可重复性"""
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % (10**9)

# Output tagging
OUTPUT_VERSION = "v1_1"
STRICT_PDR_END2END = True

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from benchmark_protocols import (
    NetworkConfig,
    LEACHProtocol,
    PEGASISProtocol,
    HEEDProtocolWrapper,
)
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

# Try to import AERIS
try:
    from aeris_protocol import AerisProtocol
    AERIS_AVAILABLE = True
except ImportError:
    AERIS_AVAILABLE = False
    print("[WARN] AerisProtocol not found, will skip AERIS tests")


# Large scale node counts for paper
NODE_COUNTS = (100, 200, 300, 500)
PROTOCOLS = ["LEACH", "PEGASIS", "HEED"]
if AERIS_AVAILABLE:
    PROTOCOLS.append("AERIS")


def generate_positions(seed: int, num_nodes: int, width: float, height: float) -> List[Tuple[float, float]]:
    """Generate random node positions."""
    rng = random.Random(seed)
    return [
        (rng.uniform(5.0, width - 5.0), rng.uniform(5.0, height - 5.0))
        for _ in range(num_nodes)
    ]


def build_config(num_nodes: int, seed: int) -> NetworkConfig:
    """Build network configuration with proper scaling."""
    # Keep density roughly constant by scaling area with sqrt(n/100)
    scale = (num_nodes / 100.0) ** 0.5
    width = 150.0 * scale
    height = 150.0 * scale
    base_station = (width * 0.5, height * 1.2)

    cfg = NetworkConfig(
        num_nodes=num_nodes,
        area_width=width,
        area_height=height,
        base_station_x=base_station[0],
        base_station_y=base_station[1],
        initial_energy=2.0,
        packet_size=1024,
        temperature_c=25.0,
        humidity_ratio=0.5,
        enable_channel=True,
        channel_env="indoor_office",
        tx_power_dbm=0.0,
        link_retx=1,
        link_retx_power_step=1.0,
    )
    cfg.positions = generate_positions(seed, num_nodes, width, height)
    cfg.gateway_k = max(3, int(num_nodes / 20))
    cfg.gateway_retry_limit = 2
    cfg.gateway_rescue_direct = True
    cfg.intra_link_retx = 2
    cfg.intra_link_power_step = 1.5
    return cfg


def run_protocol(protocol: str, cfg: NetworkConfig, seed: int, rounds: int = 200) -> Dict:
    """Run a single protocol simulation."""
    random.seed(seed)
    np.random.seed(seed)
    cfg_local = deepcopy(cfg)
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    start_time = time.time()

    if protocol == "LEACH":
        res = LEACHProtocol(cfg_local, em).run_simulation(rounds)
    elif protocol == "PEGASIS":
        res = PEGASISProtocol(cfg_local, em).run_simulation(rounds)
    elif protocol == "HEED":
        res = HEEDProtocolWrapper(cfg_local, em).run_simulation(rounds)
    elif protocol == "AERIS" and AERIS_AVAILABLE:
        # [FIX] 显式禁用强制可靠模式，确保PDR数据真实
        cfg_local.force_ctp_reliable = False
        res = AerisProtocol(
            cfg_local,
            enable_cas=True,
            enable_fairness=True,
            enable_gateway=True,
            enable_skeleton=True,
            profile="robust",
            verbose=False,
            seed=seed,
        ).run_simulation(rounds)
    else:
        raise ValueError(f"Unknown protocol {protocol}")

    exec_time = time.time() - start_time

    # 严格模式：同时输出 pdr_hop 和 pdr_end2end，不使用回退
    pdr_hop = float(res.get("packet_delivery_ratio", 0.0))
    pdr_e2e = float(res.get("packet_delivery_ratio_end2end", 0.0))
    # 如果 pdr_end2end 缺失，标记为 -1 表示无效
    if "packet_delivery_ratio_end2end" not in res:
        pdr_e2e = -1.0  # 标记为无效，而非静默回退

    return {
        "pdr_hop": pdr_hop,
        "pdr_end2end": pdr_e2e,
        "energy": float(res.get("total_energy_consumed", 0.0)),
        "lifetime": int(res.get("network_lifetime", 0)),
        "alive_nodes": int(res.get("final_alive_nodes", res.get("alive_nodes", 0))),
        "execution_time": exec_time,
    }


def run_task(args: Tuple[int, int, str, int, int]) -> Dict:
    """Run a single task (one protocol, one replicate, one node count)."""
    num_nodes, replicate, protocol, base_seed, rounds = args
    seed = base_seed + replicate * 997 + stable_hash(protocol) % 997
    cfg = build_config(num_nodes, seed)

    try:
        metrics = run_protocol(protocol, cfg, seed + 17, rounds)
        return {
            "num_nodes": num_nodes,
            "replicate": replicate,
            "protocol": protocol,
            "seed": seed,
            "metrics": metrics,
            "success": True,
        }
    except Exception as e:
        return {
            "num_nodes": num_nodes,
            "replicate": replicate,
            "protocol": protocol,
            "seed": seed,
            "metrics": None,
            "success": False,
            "error": str(e),
        }


def aggregate(runs: List[Dict]) -> Dict:
    """Aggregate results into summary statistics."""
    summary: Dict = {}
    for num_nodes in NODE_COUNTS:
        summary[num_nodes] = {}
        for protocol in PROTOCOLS:
            filtered = [r for r in runs if r["num_nodes"] == num_nodes
                       and r["protocol"] == protocol and r["success"]]
            if not filtered:
                continue
            pdrs = [r["metrics"]["pdr_end2end"] for r in filtered]
            energies = [r["metrics"]["energy"] for r in filtered]
            exec_times = [r["metrics"]["execution_time"] for r in filtered]

            summary[num_nodes][protocol] = {
                "pdr_mean": float(np.mean(pdrs)),
                "pdr_std": float(np.std(pdrs)),
                "pdr_min": float(np.min(pdrs)),
                "pdr_max": float(np.max(pdrs)),
                "energy_mean": float(np.mean(energies)),
                "energy_std": float(np.std(energies)),
                "exec_time_mean": float(np.mean(exec_times)),
                "n_runs": len(pdrs),
            }
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Run large-scale scalability experiment.")
    parser.add_argument("--replicates", type=int, default=30, help="Replicates per node count")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers")
    parser.add_argument("--seed", type=int, default=42, help="Base seed")
    parser.add_argument("--rounds", type=int, default=200, help="Simulation rounds")
    parser.add_argument("--output", default=None, help="Output JSON path")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("LARGE-SCALE SCALABILITY EXPERIMENT")
    print("=" * 60)
    print(f"Node counts: {NODE_COUNTS}")
    print(f"Protocols: {PROTOCOLS}")
    print(f"Replicates: {args.replicates}")
    print(f"Rounds: {args.rounds}")
    print(f"Workers: {args.workers}")
    print("=" * 60)

    # Build task list
    tasks: List[Tuple[int, int, str, int, int]] = []
    for num_nodes in NODE_COUNTS:
        for rep in range(args.replicates):
            for protocol in PROTOCOLS:
                tasks.append((num_nodes, rep, protocol, args.seed, args.rounds))

    total = len(tasks)
    print(f"Total tasks: {total}")
    print("Starting experiment...")

    runs: List[Dict] = []
    completed = 0
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_task, t): t for t in tasks}
        for future in as_completed(futures):
            result = future.result()
            runs.append(result)
            completed += 1

            elapsed = time.time() - start_time
            eta = (elapsed / completed) * (total - completed) if completed > 0 else 0

            if completed % 5 == 0 or completed == total:
                status = "OK" if result["success"] else "FAIL"
                print(f"[{completed}/{total}] {result['protocol']}@{result['num_nodes']} "
                      f"rep={result['replicate']} [{status}] | "
                      f"Elapsed: {elapsed/60:.1f}min, ETA: {eta/60:.1f}min")

    total_time = time.time() - start_time
    print(f"\nExperiment completed in {total_time/60:.1f} minutes")

    # Aggregate results
    summary = aggregate(runs)

    # Print summary table
    print("\n" + "=" * 60)
    print("SUMMARY: PDR at Scale")
    print("=" * 60)
    print(f"{'Protocol':<12}", end="")
    for n in NODE_COUNTS:
        print(f"{n:>10}", end="")
    print()
    print("-" * 60)
    for protocol in PROTOCOLS:
        print(f"{protocol:<12}", end="")
        for n in NODE_COUNTS:
            if n in summary and protocol in summary[n]:
                pdr = summary[n][protocol]["pdr_mean"] * 100
                print(f"{pdr:>9.2f}%", end="")
            else:
                print(f"{'N/A':>10}", end="")
        print()

    # Build output
    out = {
        "output_version": OUTPUT_VERSION,
        "config": {
            "replicates": args.replicates,
            "rounds": args.rounds,
            "node_counts": list(NODE_COUNTS),
            "protocols": PROTOCOLS,
            "channel_env": "indoor_office",
            "base_seed": args.seed,
            "total_time_seconds": total_time,
        },
        "runs": runs,
        "summary": summary,
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = args.output or os.path.join(
        os.path.dirname(__file__),
        "..",
        "results",
        f"large_scale_scalability_verified_{timestamp}_{OUTPUT_VERSION}.json",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[DONE] Wrote results to {out_path}")


if __name__ == "__main__":
    main()
