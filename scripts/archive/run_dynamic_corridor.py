#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulate a dynamic corridor scenario by generating multiple snapshots
of a narrow deployment (nodes slowly sliding along the corridor) and
running AERIS (energy/robust) together with LEACH for reference.

Outputs results/dynamic_corridor.json for downstream plotting.
"""

import os
import sys
import json
import random
from typing import List, Tuple, Dict

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig, LEACHProtocol
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol

AREA_WIDTH = 30.0
AREA_HEIGHT = 250.0
BASE_STATION = (15.0, 300.0)
NUM_NODES = 80
PHASES = [
    {"name": "phase1_static", "shift": 0.0},
    {"name": "phase2_shift", "shift": 20.0},
    {"name": "phase3_shift", "shift": 40.0},
    {"name": "phase4_shift", "shift": 60.0},
]


def generate_corridor_positions(shift: float, seed: int) -> List[Tuple[float, float]]:
    rng = random.Random(seed)
    positions: List[Tuple[float, float]] = []
    for _ in range(NUM_NODES):
        x = rng.uniform(3.0, AREA_WIDTH - 3.0)
        y = (rng.uniform(0.5, AREA_HEIGHT - 0.5) + shift) % AREA_HEIGHT
        positions.append((x, y))
    return positions


def run_phase(phase: Dict, seed: int) -> Dict[str, Dict]:
    cfg = NetworkConfig(
        num_nodes=NUM_NODES,
        area_width=AREA_WIDTH,
        area_height=AREA_HEIGHT,
        base_station_x=BASE_STATION[0],
        base_station_y=BASE_STATION[1],
        initial_energy=2.0,
        packet_size=1024,
    )
    cfg.positions = generate_corridor_positions(phase["shift"], seed)

    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    phase_results: Dict[str, Dict] = {}

    print(f"[{phase['name']}] Running LEACH baseline")
    phase_results["LEACH"] = LEACHProtocol(cfg, em).run_simulation(200)

    print(f"[{phase['name']}] Running AERIS (energy)")
    phase_results["AERIS_energy"] = AerisProtocol(
        cfg,
        enable_cas=True,
        enable_fairness=True,
        enable_gateway=True,
        enable_skeleton=True,
        profile="energy",
        verbose=False,
    ).run_simulation(200)

    print(f"[{phase['name']}] Running AERIS (robust)")
    phase_results["AERIS_robust"] = AerisProtocol(
        cfg,
        enable_cas=True,
        enable_fairness=True,
        enable_gateway=True,
        enable_skeleton=True,
        profile="robust",
        verbose=False,
    ).run_simulation(200)

    return phase_results


if __name__ == "__main__":
    dynamic_results: Dict[str, Dict] = {}
    base_seed = 50000
    for idx, phase in enumerate(PHASES):
        phase_seed = base_seed + idx * 17
        dynamic_results[phase["name"]] = run_phase(phase, phase_seed)

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'dynamic_corridor.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(dynamic_results, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved dynamic corridor results to {out_path}")
