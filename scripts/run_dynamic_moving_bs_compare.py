#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run baseline protocols and AERIS variants for moving base-station corridor scenario.
Outputs results/dynamic_moving_bs_compare.json
"""

import argparse
import os
import sys
import json
import random

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, TEENProtocolWrapper
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol

NUM_NODES = 80
AREA_WIDTH = 30.0
# Longer corridor and more aggressive BS movement to expose robustness
AREA_HEIGHT = 400.0
BS_PHASES = [
    {"name": "bs_phase1", "y": 240.0},
    {"name": "bs_phase2", "y": 340.0},
    {"name": "bs_phase3", "y": 440.0},
    {"name": "bs_phase4", "y": 540.0},
]
BASE_SEED = 56000


def generate_positions(seed: int):
    rng = random.Random(seed)
    return [(rng.uniform(3.0, AREA_WIDTH - 3.0), rng.uniform(0.5, AREA_HEIGHT - 0.5)) for _ in range(NUM_NODES)]


def run_phase(positions, bs_y: float, seed: int):
    cfg = NetworkConfig(
        num_nodes=len(positions),
        area_width=AREA_WIDTH,
        area_height=AREA_HEIGHT,
        base_station_x=AREA_WIDTH / 2,
        base_station_y=bs_y,
        initial_energy=2.0,
        packet_size=1024,
    )
    cfg.enable_channel = True
    cfg.channel_env = "indoor_office"
    cfg.tx_power_dbm = 0.0
    cfg.link_retx = 1
    cfg.link_retx_power_step = 1.0
    cfg.gateway_k = 4
    cfg.gateway_retry_limit = 1
    cfg.gateway_rescue_direct = True
    cfg.intra_link_retx = 2
    cfg.intra_link_power_step = 1.5
    cfg.positions = positions

    results = {}
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    results["LEACH"] = LEACHProtocol(cfg, em).run_simulation(200)
    results["PEGASIS"] = PEGASISProtocol(cfg, em).run_simulation(200)
    results["HEED"] = HEEDProtocolWrapper(cfg, em).run_simulation(200)
    results["TEEN"] = TEENProtocolWrapper(cfg, em).run_simulation(200)

    # 使用论文一致命名: AERIS-E (energy), AERIS-R (robust)
    profile_map = {"energy": "AERIS-E", "robust": "AERIS-R"}
    for profile in ("energy", "robust"):
        proto = AerisProtocol(
            cfg,
            enable_cas=True,
            enable_fairness=True,
            enable_gateway=True,
            enable_skeleton=True,
            profile=profile,
            verbose=False,
            seed=seed,
        )
        results[profile_map[profile]] = proto.run_simulation(200)
    return results


def run_replicate(base_seed: int):
    positions = generate_positions(base_seed)
    replicate_results = {}
    for idx, phase in enumerate(BS_PHASES):
        phase_seed = base_seed + idx * 53
        print(f"[MovingBS] {phase['name']} BS_y={phase['y']} seed={phase_seed}")
        replicate_results[phase["name"]] = run_phase(positions, phase["y"], phase_seed)
    return replicate_results


def parse_args():
    parser = argparse.ArgumentParser(description="Dynamic moving BS comparison with optional replicates.")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--replicates", type=int, default=1, help="Number of replicates to run")
    parser.add_argument("--seed-offset", type=int, default=0, help="Offset added to BASE_SEED for the first replicate")
    parser.add_argument("--seed-stride", type=int, default=1000, help="Stride added between replicate seeds")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    out_path = args.output or os.path.join(os.path.dirname(__file__), '..', 'results', 'dynamic_moving_bs_compare.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # GPT DeepSearch: Add metadata for traceability
    from datetime import datetime
    import subprocess
    try:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        ).stdout.strip()[:12]
    except Exception:
        git_commit = "unknown"

    metadata = {
        "experiment": "dynamic_moving_bs_compare",
        "timestamp": datetime.now().isoformat(),
        "git_commit": git_commit,
        "n_replicates": args.replicates,
        "base_seed": BASE_SEED,
        "seed_offset": args.seed_offset,
        "seed_stride": args.seed_stride,
        "n_nodes": NUM_NODES,
        "n_rounds": 200,
        "scenario_config": {
            "area_width": AREA_WIDTH,
            "area_height": AREA_HEIGHT,
            "bs_phases": BS_PHASES,
        },
        "bs_phases": [p["name"] for p in BS_PHASES],
        "format_version": "1.0"
    }

    if args.replicates <= 1:
        seed = BASE_SEED + args.seed_offset
        results = run_replicate(seed)
        metadata["seeds_used"] = [seed]
    else:
        results = {}
        seeds_used = []
        for rep in range(args.replicates):
            seed = BASE_SEED + args.seed_offset + rep * args.seed_stride
            seeds_used.append(seed)
            print(f"[MovingBS] replicate {rep} base_seed={seed}")
            results[f"rep_{rep}"] = run_replicate(seed)
        metadata["seeds_used"] = seeds_used

    # 计算结果数量
    if args.replicates <= 1:
        n_results = len(BS_PHASES) * 6  # phases × 6 protocols
    else:
        n_results = args.replicates * len(BS_PHASES) * 6

    output = {
        "n_results": n_results,
        "format_version": "1.0",
        "schema_type": "dynamic_moving_bs",
        "metadata": metadata,
        "results": results
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved moving BS comparison to {out_path}")
