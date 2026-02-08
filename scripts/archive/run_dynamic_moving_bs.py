#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moving base station scenario: simulate a corridor deployment where the BS
slides along the corridor while nodes retain Intel-driven channel characteristics.
"""

import os
import sys
import json
import random

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol

AREA_WIDTH = 30.0
AREA_HEIGHT = 250.0
NUM_NODES = 80
BS_PHASES = [
    {"name": "bs_phase1", "bs_y": 260.0},
    {"name": "bs_phase2", "bs_y": 300.0},
    {"name": "bs_phase3", "bs_y": 340.0},
    {"name": "bs_phase4", "bs_y": 380.0},
]


def generate_positions(seed: int):
    rng = random.Random(seed)
    return [(rng.uniform(3.0, AREA_WIDTH - 3.0), rng.uniform(0.5, AREA_HEIGHT - 0.5)) for _ in range(NUM_NODES)]


def run_phase(seed: int, bs_y: float):
    cfg = NetworkConfig(
        num_nodes=NUM_NODES,
        area_width=AREA_WIDTH,
        area_height=AREA_HEIGHT,
        base_station_x=AREA_WIDTH / 2,
        base_station_y=bs_y,
        initial_energy=2.0,
        packet_size=1024,
    )
    cfg.positions = generate_positions(seed)
    return AerisProtocol(
        cfg,
        enable_cas=True,
        enable_fairness=True,
        enable_gateway=True,
        enable_skeleton=True,
        profile="robust",
        verbose=False,
    ).run_simulation(200)


if __name__ == "__main__":
    results = {}
    base_seed = 72000
    for idx, phase in enumerate(BS_PHASES):
        seed = base_seed + idx * 57
        print(f"[Moving BS] {phase['name']} seed={seed}")
        results[phase["name"]] = run_phase(seed, phase["bs_y"])
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'dynamic_moving_bs.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved moving BS results to {out_path}")
