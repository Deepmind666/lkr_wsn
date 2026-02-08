#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Large-scale, long-duration simulations (300/500 nodes, 1000 rounds) to stress CAS/Gateway/Skeleton.
Outputs results/large_scale_long.json
"""

import os
import sys
import json
import random
import math
import argparse
from typing import List, Tuple, Dict

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import (
    NetworkConfig,
    LEACHProtocol,
    PEGASISProtocol,
    HEEDProtocolWrapper,
    TEENProtocolWrapper,
)
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol

SETUPS = [
    {"name": "uniform_300", "num_nodes": 300, "area": 250.0, "base": (125.0, 320.0), "seed": 81001},
    {"name": "uniform_500", "num_nodes": 500, "area": 320.0, "base": (160.0, 420.0), "seed": 82001},
]


def generate_positions(num_nodes: int, area: float, seed: int) -> List[Tuple[float, float]]:
    rng = random.Random(seed)
    return [(rng.uniform(5, area - 5), rng.uniform(5, area - 5)) for _ in range(num_nodes)]


def run_setup(cfg_name: str, num_nodes: int, area: float, base: Tuple[float, float], seed: int) -> Dict[str, Dict]:
    cfg = NetworkConfig(
        num_nodes=num_nodes,
        area_width=area,
        area_height=area,
        base_station_x=base[0],
        base_station_y=base[1],
        initial_energy=4.0,
        packet_size=1024,
    )
    cfg.enable_channel = True
    cfg.channel_env = "indoor_office"
    cfg.tx_power_dbm = 0.0
    cfg.link_retx = 1
    cfg.link_retx_power_step = 1.0
    # Larger maps benefit from multiple gateways + retry
    cfg.gateway_k = max(4, int(math.ceil(num_nodes / 60.0)))
    cfg.gateway_retry_limit = 2
    cfg.gateway_rescue_direct = True
    cfg.intra_link_retx = 2
    cfg.intra_link_power_step = 1.5
    cfg.positions = generate_positions(num_nodes, area, seed)

    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    results: Dict[str, Dict] = {}

    print(f"[LargeScale] {cfg_name} Running LEACH")
    results["LEACH"] = LEACHProtocol(cfg, em).run_simulation(1000)

    print(f"[LargeScale] {cfg_name} Running PEGASIS")
    results["PEGASIS"] = PEGASISProtocol(cfg, em).run_simulation(1000)

    print(f"[LargeScale] {cfg_name} Running HEED")
    results["HEED"] = HEEDProtocolWrapper(cfg, em).run_simulation(1000)

    print(f"[LargeScale] {cfg_name} Running TEEN")
    results["TEEN"] = TEENProtocolWrapper(cfg, em).run_simulation(1000)

    for profile in ("energy", "robust"):
        print(f"[LargeScale] {cfg_name} Running AERIS profile={profile}")
        proto = AerisProtocol(
            cfg,
            enable_cas=True,
            enable_fairness=True,
            enable_gateway=True,
            enable_skeleton=True,
            profile=profile,
            verbose=False,
            seed=seed + (0 if profile == "energy" else 1),
        )
        results[f"AERIS_{profile}"] = proto.run_simulation(1000)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Large-scale 300/500-node long runs")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--replicates", type=int, default=1, help="Number of replicate runs")
    parser.add_argument("--seed-offset", type=int, default=0, help="Seed offset for replicate 0")
    parser.add_argument("--seed-stride", type=int, default=1000, help="Seed stride between replicates")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    out_path = args.output or os.path.join(os.path.dirname(__file__), '..', 'results', 'large_scale_long.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if args.replicates <= 1:
        all_results: Dict[str, Dict] = {}
        for setup in SETUPS:
            seed = setup["seed"] + args.seed_offset
            all_results[setup["name"]] = run_setup(
                setup["name"],
                setup["num_nodes"],
                setup["area"],
                setup["base"],
                seed,
            )
    else:
        all_results = {}
        for rep in range(args.replicates):
            rep_seed_offset = args.seed_offset + rep * args.seed_stride
            rep_key = f"rep_{rep}"
            all_results[rep_key] = {}
            print(f"[LargeScale] replicate {rep} seed_offset={rep_seed_offset}")
            for setup in SETUPS:
                seed = setup["seed"] + rep_seed_offset
                all_results[rep_key][setup["name"]] = run_setup(
                    setup["name"],
                    setup["num_nodes"],
                    setup["area"],
                    setup["base"],
                    seed,
                )

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved long-run results to {out_path}")
