#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monte Carlo runs for the 50x100 topology (100 seeds) to capture statistical stability of energy vs robust profiles.
Outputs results/monte_carlo_uniform50.json
"""

import os
import sys
import json
import random
import statistics

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol

NUM_SEEDS = 100


def generate_positions(seed: int):
    rng = random.Random(seed)
    return [(rng.uniform(5, 95), rng.uniform(5, 95)) for _ in range(50)]


def run_once(seed: int, profile: str):
    cfg = NetworkConfig(
        num_nodes=50,
        area_width=100.0,
        area_height=100.0,
        base_station_x=50.0,
        base_station_y=175.0,
        initial_energy=2.0,
        packet_size=1024,
    )
    cfg.positions = generate_positions(seed)
    proto = AerisProtocol(
        cfg,
        enable_cas=True,
        enable_fairness=True,
        enable_gateway=True,
        enable_skeleton=True,
        profile=profile,
        verbose=False,
    )
    res = proto.run_simulation(200)
    return {
        "seed": seed,
        "pdr_end2end": res.get("packet_delivery_ratio_end2end", 0.0),
        "pdr_hop": res.get("packet_delivery_ratio", 0.0),
        "energy": res.get("total_energy_consumed", 0.0),
        "cas_usage": res["additional_metrics"].get("cas_mode_usage_stats", {}),
    }


if __name__ == "__main__":
    results = {"energy": [], "robust": []}
    for seed in range(NUM_SEEDS):
        print(f"[MonteCarlo] seed={seed}")
        results["energy"].append(run_once(seed, "energy"))
        results["robust"].append(run_once(seed, "robust"))

    stats = {}
    for profile, runs in results.items():
        stats[profile] = {
            "mean_pdr": statistics.mean(r["pdr_end2end"] for r in runs),
            "std_pdr": statistics.pstdev(r["pdr_end2end"] for r in runs),
            "mean_energy": statistics.mean(r["energy"] for r in runs),
            "std_energy": statistics.pstdev(r["energy"] for r in runs),
        }

    out = {"runs": results, "stats": stats}
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'monte_carlo_uniform50.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved Monte Carlo results to {out_path}")
