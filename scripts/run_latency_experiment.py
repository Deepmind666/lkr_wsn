#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Latency (hop-count) experiment with the same fairness pipeline as run_fair_5protocol.py.

Key points:
- same topology per seed across all 5 protocols
- same environment and tx_power per run
- primary metric follows project rule: pdr_expected
- latency metric (avg_hops_to_bs) is reported as secondary
"""

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


DEFAULT_PROTOCOLS = ("AERIS", "LEACH", "PEGASIS", "HEED", "TEEN")
DEFAULT_NUM_NODES = 100
DEFAULT_AREA_SIZE = 200.0
DEFAULT_BASE_STATION = (100.0, 200.0)
DEFAULT_INITIAL_ENERGY = 2.0
DEFAULT_PACKET_SIZE = 1024
DEFAULT_ROUNDS = 300
DEFAULT_TX_POWER = 10.0
DEFAULT_ENV = "indoor_office"
OUTPUT_VERSION = "v2_2"


def get_git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=os.path.dirname(__file__),
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        return out or "unknown"
    except Exception:
        return "unknown"


def get_git_dirty() -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=os.path.dirname(__file__),
            stderr=subprocess.DEVNULL,
        ).decode("utf-8")
        return bool(out.strip())
    except Exception:
        return True


def get_git_diff_stat() -> Dict[str, str]:
    def _run(cmd: List[str]) -> str:
        try:
            return subprocess.check_output(
                cmd, cwd=os.path.dirname(__file__), stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore").strip() or "clean"
        except Exception:
            return "unknown"

    return {
        "unstaged": _run(["git", "diff", "--shortstat"]),
        "staged": _run(["git", "diff", "--cached", "--shortstat"]),
    }


def get_script_sha256() -> str:
    with open(__file__, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def stable_hash(s: str) -> int:
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16) % (10**9)


def generate_positions(seed: int, num_nodes: int, area_size: float) -> List[Tuple[float, float]]:
    np.random.seed(seed)
    return [(np.random.uniform(0, area_size), np.random.uniform(0, area_size)) for _ in range(num_nodes)]


def _make_channel(env_name: str, seed: int):
    from realistic_channel_model import RealisticChannelModel, EnvironmentType

    env_map = {
        "indoor_office": EnvironmentType.INDOOR_OFFICE,
        "indoor_factory": EnvironmentType.INDOOR_FACTORY,
        "outdoor_urban": EnvironmentType.OUTDOOR_URBAN,
        "outdoor_suburban": EnvironmentType.OUTDOOR_SUBURBAN,
    }
    channel = RealisticChannelModel(env_map.get(env_name, EnvironmentType.INDOOR_OFFICE))
    channel.reset_rng(seed)
    return channel


def _extract_avg_hops(proto_obj, result_dict: Dict) -> float:
    if hasattr(proto_obj, "_all_hop_counts") and proto_obj._all_hop_counts:
        return float(sum(proto_obj._all_hop_counts) / len(proto_obj._all_hop_counts))
    if isinstance(result_dict, dict):
        if "avg_hops_to_bs" in result_dict:
            return float(result_dict.get("avg_hops_to_bs", 0.0))
        add_m = result_dict.get("additional_metrics", {})
        if isinstance(add_m, dict):
            return float(add_m.get("avg_hop_count", 0.0))
    return 0.0


def run_aeris(args: Tuple) -> Dict:
    seed, positions, num_rounds, area_size, tx_power, env_name = args
    np.random.seed(seed)
    random.seed(seed)

    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol

    out = {
        "protocol": "AERIS",
        "seed": seed,
        "environment": env_name,
        "pdr_expected": 0.0,
        "avg_hops_to_bs": 0.0,
        "total_energy_consumed": 0.0,
        "total_rounds": 0,
        "first_node_death_round": 0,
        "error": None,
    }

    try:
        channel = _make_channel(env_name, seed)
        config = NetworkConfig()
        config.num_nodes = len(positions)
        config.area_width = config.area_height = area_size
        config.base_station_x = area_size / 2.0
        config.base_station_y = area_size
        config.tx_power_dbm = tx_power
        config.positions = positions
        config.force_environment = env_name
        config.external_channel_model = channel

        proto = AerisProtocol(
            config,
            seed=seed,
            verbose=False,
            enable_gateway=True,
            enable_cas=True,
            enable_skeleton=True,
        )
        proto.safety_fallback_enabled = True
        sim = proto.run_simulation(max_rounds=num_rounds)

        if proto.source_packets_expected > 0:
            out["pdr_expected"] = proto.bs_delivered_total / proto.source_packets_expected
        out["avg_hops_to_bs"] = _extract_avg_hops(proto, sim)
        out["total_energy_consumed"] = float(getattr(proto, "total_energy_consumed", 0.0))
        if getattr(proto, "round_statistics", None):
            out["total_rounds"] = len(proto.round_statistics)
            for idx, rs in enumerate(proto.round_statistics, start=1):
                if rs.get("alive_nodes", len(positions)) < len(positions):
                    out["first_node_death_round"] = idx
                    break
    except Exception as exc:
        out["error"] = str(exc)

    return out


def run_leach(args: Tuple) -> Dict:
    seed, positions, num_rounds, area_size, tx_power, env_name = args
    np.random.seed(seed)
    random.seed(seed)

    from baseline_protocols import LEACHProtocol
    from baseline_protocols.leach_protocol import LEACHNode

    out = {
        "protocol": "LEACH",
        "seed": seed,
        "environment": env_name,
        "pdr_expected": 0.0,
        "avg_hops_to_bs": 0.0,
        "total_energy_consumed": 0.0,
        "total_rounds": 0,
        "first_node_death_round": 0,
        "error": None,
    }

    try:
        channel = _make_channel(env_name, seed)
        nodes = [LEACHNode(i, pos[0], pos[1], initial_energy=DEFAULT_INITIAL_ENERGY) for i, pos in enumerate(positions)]
        proto = LEACHProtocol(
            nodes,
            DEFAULT_BASE_STATION,
            tx_power_dbm=tx_power,
            channel_model=channel,
            use_unified_energy_model=True,
        )
        sim = proto.run_simulation(max_rounds=num_rounds)

        if getattr(proto, "source_packets_expected", 0) > 0:
            out["pdr_expected"] = proto.total_bs_delivered / proto.source_packets_expected
        out["avg_hops_to_bs"] = _extract_avg_hops(proto, sim)
        out["total_energy_consumed"] = float(getattr(proto, "total_energy_consumed", 0.0))
        out["total_rounds"] = int(getattr(proto, "current_round", 0))
        out["first_node_death_round"] = int(getattr(proto, "network_lifetime", 0))
    except Exception as exc:
        out["error"] = str(exc)

    return out


def run_pegasis(args: Tuple) -> Dict:
    seed, positions, num_rounds, area_size, tx_power, env_name = args
    np.random.seed(seed)
    random.seed(seed)

    from baseline_protocols import PEGASISProtocol
    from baseline_protocols.pegasis_protocol import PEGASISNode

    out = {
        "protocol": "PEGASIS",
        "seed": seed,
        "environment": env_name,
        "pdr_expected": 0.0,
        "avg_hops_to_bs": 0.0,
        "total_energy_consumed": 0.0,
        "total_rounds": 0,
        "first_node_death_round": 0,
        "error": None,
    }

    try:
        channel = _make_channel(env_name, seed)
        nodes = [PEGASISNode(i, pos[0], pos[1], initial_energy=DEFAULT_INITIAL_ENERGY) for i, pos in enumerate(positions)]
        proto = PEGASISProtocol(
            nodes,
            DEFAULT_BASE_STATION,
            tx_power_dbm=tx_power,
            channel_model=channel,
            use_unified_energy_model=True,
        )
        sim = proto.run_simulation(max_rounds=num_rounds)

        if getattr(proto, "source_packets_expected", 0) > 0:
            out["pdr_expected"] = proto.total_bs_delivered / proto.source_packets_expected
        out["avg_hops_to_bs"] = _extract_avg_hops(proto, sim)
        out["total_energy_consumed"] = float(getattr(proto, "total_energy_consumed", 0.0))
        out["total_rounds"] = int(getattr(proto, "current_round", 0))
        out["first_node_death_round"] = int(getattr(proto, "network_lifetime", 0))
    except Exception as exc:
        out["error"] = str(exc)

    return out


def run_heed(args: Tuple) -> Dict:
    seed, positions, num_rounds, area_size, tx_power, env_name = args
    np.random.seed(seed)
    random.seed(seed)

    from baseline_protocols import HEEDProtocol
    from baseline_protocols.heed_protocol import HEEDNode

    out = {
        "protocol": "HEED",
        "seed": seed,
        "environment": env_name,
        "pdr_expected": 0.0,
        "avg_hops_to_bs": 0.0,
        "total_energy_consumed": 0.0,
        "total_rounds": 0,
        "first_node_death_round": 0,
        "error": None,
    }

    try:
        channel = _make_channel(env_name, seed)
        nodes = [HEEDNode(i, pos[0], pos[1], initial_energy=DEFAULT_INITIAL_ENERGY) for i, pos in enumerate(positions)]
        proto = HEEDProtocol(
            nodes,
            DEFAULT_BASE_STATION,
            tx_power_dbm=tx_power,
            channel_model=channel,
            use_unified_energy_model=True,
        )
        sim = proto.run_simulation(max_rounds=num_rounds)

        if getattr(proto, "source_packets_expected", 0) > 0:
            out["pdr_expected"] = proto.total_bs_delivered / proto.source_packets_expected
        out["avg_hops_to_bs"] = _extract_avg_hops(proto, sim)
        out["total_energy_consumed"] = float(getattr(proto, "total_energy_consumed", 0.0))
        out["total_rounds"] = int(getattr(proto, "current_round", 0))
        out["first_node_death_round"] = int(getattr(proto, "network_lifetime", 0))
    except Exception as exc:
        out["error"] = str(exc)

    return out


def run_teen(args: Tuple) -> Dict:
    seed, positions, num_rounds, area_size, tx_power, env_name = args
    np.random.seed(seed)
    random.seed(seed)

    from teen_protocol import TEENConfig, TEENProtocol

    out = {
        "protocol": "TEEN",
        "seed": seed,
        "environment": env_name,
        "pdr_expected": 0.0,
        "avg_hops_to_bs": 0.0,
        "total_energy_consumed": 0.0,
        "total_rounds": 0,
        "first_node_death_round": 0,
        "error": None,
    }

    try:
        channel = _make_channel(env_name, seed)
        cfg = TEENConfig(
            num_nodes=len(positions),
            area_width=area_size,
            area_height=area_size,
            base_station_x=area_size / 2.0,
            base_station_y=area_size,
            initial_energy=DEFAULT_INITIAL_ENERGY,
            packet_size=DEFAULT_PACKET_SIZE,
            tx_power_dbm=tx_power,
            enable_channel=True,
            channel_env=env_name,
        )
        proto = TEENProtocol(cfg, external_channel_model=channel)
        proto.initialize_network(positions)
        sim = proto.run_simulation(max_rounds=num_rounds)

        if getattr(proto, "source_packets_expected", 0) > 0:
            out["pdr_expected"] = proto.bs_delivered_total / proto.source_packets_expected
        out["avg_hops_to_bs"] = _extract_avg_hops(proto, sim)
        out["total_energy_consumed"] = float(getattr(proto, "total_energy_consumed", 0.0))
        out["total_rounds"] = int(getattr(proto, "current_round", 0))
        out["first_node_death_round"] = int(getattr(proto, "network_lifetime", 0))
    except Exception as exc:
        out["error"] = str(exc)

    return out


def execute_protocol_batch(protocol: str, runner, tasks: List[Tuple], workers: int) -> List[Dict]:
    results: List[Dict] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for item in pool.map(runner, tasks, chunksize=4):
            results.append(item)
    return results


def aggregate(raw_results: List[Dict], protocols: Tuple[str, ...]) -> Dict:
    summary = {}
    for proto in protocols:
        group = [r for r in raw_results if r["protocol"] == proto and not r.get("error")]
        pdr = [r["pdr_expected"] for r in group if r["pdr_expected"] >= 0]
        hops = [r["avg_hops_to_bs"] for r in group if r["avg_hops_to_bs"] > 0]
        energy = [r["total_energy_consumed"] for r in group]
        if not group:
            continue
        summary[proto] = {
            "pdr_mean": float(np.mean(pdr)) if pdr else 0.0,
            "pdr_std": float(np.std(pdr, ddof=1)) if len(pdr) > 1 else 0.0,
            "hops_mean": float(np.mean(hops)) if hops else 0.0,
            "hops_std": float(np.std(hops, ddof=1)) if len(hops) > 1 else 0.0,
            "energy_mean": float(np.mean(energy)) if energy else 0.0,
            "energy_std": float(np.std(energy, ddof=1)) if len(energy) > 1 else 0.0,
            "n": len(group),
            "errors": sum(1 for r in raw_results if r["protocol"] == proto and r.get("error")),
        }
    return summary


def parse_args():
    ap = argparse.ArgumentParser(description="Run latency experiment (hop count).")
    ap.add_argument("--env", type=str, default=DEFAULT_ENV)
    ap.add_argument("--replicates", type=int, default=30)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=42001)
    ap.add_argument("--nodes", type=int, default=DEFAULT_NUM_NODES)
    ap.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    ap.add_argument("--tx-power", type=float, default=DEFAULT_TX_POWER)
    ap.add_argument("--run-tier", type=str, default="publication")
    ap.add_argument("--output", type=str, default="")
    return ap.parse_args()


def main():
    args = parse_args()
    protocols = DEFAULT_PROTOCOLS

    seed_list = [args.seed + i for i in range(args.replicates)]
    all_positions = {s: generate_positions(s, args.nodes, DEFAULT_AREA_SIZE) for s in seed_list}

    protocol_runners = {
        "AERIS": run_aeris,
        "LEACH": run_leach,
        "PEGASIS": run_pegasis,
        "HEED": run_heed,
        "TEEN": run_teen,
    }

    raw_results: List[Dict] = []
    started = datetime.now()
    for proto in protocols:
        tasks = [
            (s, all_positions[s], args.rounds, DEFAULT_AREA_SIZE, args.tx_power, args.env)
            for s in seed_list
        ]
        print(f"[{datetime.now():%H:%M:%S}] running {proto} ({len(tasks)} runs)")
        raw_results.extend(execute_protocol_batch(proto, protocol_runners[proto], tasks, args.workers))

    summary = aggregate(raw_results, protocols)
    failed_runs = sum(1 for r in raw_results if r.get("error"))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = {
        "timestamp": timestamp,
        "git_commit": get_git_commit(),
        "git_dirty": get_git_dirty(),
        "git_diff_stat": get_git_diff_stat(),
        "script_sha256": get_script_sha256(),
        "experiment_type": "latency_hop_count",
        "run_tier": args.run_tier,
        "primary_metric": "pdr_expected",
        "metric_note": "Latency metric avg_hops_to_bs is secondary; primary_metric follows project rules.",
        "environment": args.env,
        "tx_power_dbm": args.tx_power,
        "error_runs": failed_runs,
        "config": {
            "seeds": seed_list,
            "node_counts": [args.nodes],
            "round_counts": [args.rounds],
            "dropout_rates": [0.0],
            "protocols": list(protocols),
            "area_size": DEFAULT_AREA_SIZE,
            "base_station": list(DEFAULT_BASE_STATION),
            "packet_size": DEFAULT_PACKET_SIZE,
            "initial_energy": DEFAULT_INITIAL_ENERGY,
            "output_version": OUTPUT_VERSION,
        },
        "raw_results": raw_results,
        "summary": summary,
        "elapsed_seconds": (datetime.now() - started).total_seconds(),
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "results", "mega_experiments")
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.output.strip() if args.output else os.path.join(out_dir, f"latency_{args.env}_{timestamp}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"[{datetime.now():%H:%M:%S}] done: {out_path}")
    print(f"[{datetime.now():%H:%M:%S}] failed_runs={failed_runs}")
    for proto in protocols:
        if proto in summary:
            s = summary[proto]
            print(
                f"  {proto:8s}: pdr={s['pdr_mean']:.4f}+/-{s['pdr_std']:.4f}, "
                f"hops={s['hops_mean']:.2f}+/-{s['hops_std']:.2f}, n={s['n']}, errors={s['errors']}"
            )


if __name__ == "__main__":
    main()
