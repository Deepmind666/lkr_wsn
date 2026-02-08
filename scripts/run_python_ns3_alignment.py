#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Python-side alignment experiments to match NS-3 seeds/rounds/nodes.
Outputs raw results and a grouped summary.
"""
import argparse
import contextlib
import io
import json
import math
import os
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import numpy as np

# Local imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, TEENProtocolWrapper
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol


PROTOCOLS = ("AERIS", "LEACH", "PEGASIS", "HEED", "TEEN")


def mean(values):
    return sum(values) / len(values) if values else 0.0


def std(values):
    if len(values) < 2:
        return 0.0
    m = mean(values)
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def generate_positions(seed: int, num_nodes: int, width: float, height: float):
    rng = random.Random(seed)
    return [(rng.uniform(0.0, width), rng.uniform(0.0, height)) for _ in range(num_nodes)]


def build_config(num_nodes: int, seed: int) -> NetworkConfig:
    width = 200.0
    height = 200.0
    cfg = NetworkConfig(
        num_nodes=num_nodes,
        area_width=width,
        area_height=height,
        base_station_x=width * 0.5,
        base_station_y=height,
        initial_energy=2.0,
        packet_size=1024,
        temperature_c=25.0,
        humidity_ratio=0.5,
        enable_channel=True,
        channel_env="indoor_office",
        tx_power_dbm=0.0,
        link_retx=0,
        link_retx_power_step=0.0,
    )
    cfg.positions = generate_positions(seed, num_nodes, width, height)
    # Keep gateway/relay retries aligned with NS-3 (no retrans)
    cfg.gateway_k = max(2, int(num_nodes / 25))
    cfg.gateway_retry_limit = 0
    cfg.gateway_rescue_direct = True
    cfg.intra_link_retx = 0
    cfg.intra_link_power_step = 0.0
    return cfg


def run_protocol(protocol: str, num_nodes: int, rounds: int, seed: int) -> Dict:
    try:
        random.seed(seed)
        np.random.seed(seed)
        cfg = build_config(num_nodes, seed)
        em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

        # Suppress verbose protocol output in multiprocessing workers
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            if protocol == "LEACH":
                res = LEACHProtocol(cfg, em).run_simulation(rounds)
            elif protocol == "AERIS":
                res = AerisProtocol(
                    cfg,
                    enable_cas=True,
                    enable_fairness=True,
                    enable_gateway=True,
                    enable_skeleton=True,
                    profile=None,
                    verbose=False,
                    seed=seed,
                ).run_simulation(rounds)
            elif protocol == "PEGASIS":
                res = PEGASISProtocol(cfg, em).run_simulation(rounds)
            elif protocol == "HEED":
                res = HEEDProtocolWrapper(cfg, em).run_simulation(rounds)
            elif protocol == "TEEN":
                res = TEENProtocolWrapper(cfg, em).run_simulation(rounds)
            else:
                raise ValueError(f"Unknown protocol {protocol}")

        pdr_hop = float(res.get("packet_delivery_ratio", 0.0) or 0.0)
        pdr_e2e = float(res.get("packet_delivery_ratio_end2end", 0.0) or 0.0)
        energy_j = float(res.get("total_energy_consumed", 0.0) or 0.0)
        alive_nodes = int(res.get("final_alive_nodes", res.get("alive_nodes", 0)) or 0)
        return {
            "protocol": protocol,
            "num_nodes": num_nodes,
            "num_rounds": rounds,
            "seed": seed,
            "pdr_hop": pdr_hop,
            "pdr_end2end": pdr_e2e,
            "total_energy_j": energy_j,
            "total_energy_mj": energy_j * 1000.0,
            "alive_nodes": alive_nodes,
            "success": True,
        }
    except Exception as e:
        return {
            "protocol": protocol,
            "num_nodes": num_nodes,
            "num_rounds": rounds,
            "seed": seed,
            "success": False,
            "error": str(e),
        }


def summarize(rows: List[Dict]) -> List[Dict]:
    groups = {}
    for r in rows:
        key = (r["protocol"], r["num_nodes"], r["num_rounds"])
        groups.setdefault(key, []).append(r)
    summary = []
    for (protocol, num_nodes, num_rounds), items in sorted(groups.items()):
        pdrs = [i["pdr_end2end"] for i in items]
        energies = [i["total_energy_mj"] for i in items]
        alive = [i["alive_nodes"] for i in items]
        n = len(items)
        pdr_std = std(pdrs)
        energy_std = std(energies)
        summary.append({
            "protocol": protocol,
            "num_nodes": num_nodes,
            "num_rounds": num_rounds,
            "n": n,
            "pdr_mean": mean(pdrs),
            "pdr_std": pdr_std,
            "pdr_ci95": 1.96 * pdr_std / math.sqrt(n) if n > 1 else 0.0,
            "total_energy_mj_mean": mean(energies),
            "total_energy_mj_std": energy_std,
            "total_energy_mj_ci95": 1.96 * energy_std / math.sqrt(n) if n > 1 else 0.0,
            "alive_nodes_mean": mean(alive),
        })
    return summary


def parse_args():
    ap = argparse.ArgumentParser(description="Run Python NS-3 alignment experiments")
    ap.add_argument("--nodes", default="100,200,500", help="Comma-separated node counts")
    ap.add_argument("--rounds", default="300,500", help="Comma-separated rounds")
    ap.add_argument("--seeds", default="42001-42030", help="Seed range, e.g. 42001-42030")
    ap.add_argument("--workers", type=int, default=4, help="Parallel workers")
    ap.add_argument("--output", required=True, help="Output JSON file (raw results)")
    ap.add_argument("--summary", required=True, help="Output JSON file (summary)")
    return ap.parse_args()


def expand_seeds(seed_spec: str) -> List[int]:
    if "-" in seed_spec:
        a, b = seed_spec.split("-", 1)
        start = int(a.strip())
        end = int(b.strip())
        return list(range(start, end + 1))
    return [int(x.strip()) for x in seed_spec.split(",") if x.strip()]


def main():
    args = parse_args()
    nodes = [int(x.strip()) for x in args.nodes.split(",") if x.strip()]
    rounds_list = [int(x.strip()) for x in args.rounds.split(",") if x.strip()]
    seeds = expand_seeds(args.seeds)

    tasks: List[Tuple[str, int, int, int]] = []
    for protocol in PROTOCOLS:
        for num_nodes in nodes:
            for rounds in rounds_list:
                for seed in seeds:
                    tasks.append((protocol, num_nodes, rounds, seed))

    results: List[Dict] = []
    errors: List[Dict] = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(run_protocol, *t) for t in tasks]
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            if not res.get("success", True):
                errors.append(res)

    raw_out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "protocols": list(PROTOCOLS),
            "nodes": nodes,
            "rounds": rounds_list,
            "seeds": seeds,
            "area": [200.0, 200.0],
            "base_station": [100.0, 200.0],
            "packet_size": 512,
            "channel_env": "indoor_office",
        },
        "results": results,
        "errors": errors,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(raw_out, f, indent=2)

    ok_results = [r for r in results if r.get("success", True)]
    summary = summarize(ok_results)
    summary_out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": args.output,
        "group_by": ["protocol", "num_nodes", "num_rounds"],
        "summary": summary,
        "error_count": len(errors),
    }
    with open(args.summary, "w", encoding="utf-8") as f:
        json.dump(summary_out, f, indent=2)


if __name__ == "__main__":
    main()
