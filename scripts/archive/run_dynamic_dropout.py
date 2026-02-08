#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Random dropout scenario: multiple phases with increasing proportion of failed nodes.
Outputs results/dynamic_dropout.json.
"""

import os
import sys
import json
import random
from typing import List, Tuple

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol

BASE_NUM = 120
AREA = 120.0
BS_POS = (60.0, 180.0)
PHASES = [
    {"name": "drop0", "fail_ratio": 0.0},
    {"name": "drop10", "fail_ratio": 0.10},
    {"name": "drop20", "fail_ratio": 0.20},
    {"name": "drop30", "fail_ratio": 0.30},
]


def generate_positions(seed: int) -> List[Tuple[float, float]]:
    rng = random.Random(seed)
    return [(rng.uniform(5, AREA - 5), rng.uniform(5, AREA - 5)) for _ in range(BASE_NUM)]


def run_phase(base_positions: List[Tuple[float, float]], phase, seed: int):
    rng = random.Random(seed)
    num_fail = int(len(base_positions) * phase["fail_ratio"])
    survivors = base_positions.copy()
    rng.shuffle(survivors)
    survivors = survivors[num_fail:]

    cfg = NetworkConfig(
        num_nodes=len(survivors),
        area_width=AREA,
        area_height=AREA,
        base_station_x=BS_POS[0],
        base_station_y=BS_POS[1],
        initial_energy=2.5,
        packet_size=1024,
        positions=survivors,
    )

    return AerisProtocol(
        cfg,
        enable_cas=True,
        enable_fairness=True,
        enable_gateway=True,
        enable_skeleton=True,
        profile="robust",
        verbose=False,
    ).run_simulation(300)


if __name__ == "__main__":
    base_seed = 90001
    base_positions = generate_positions(base_seed)
    results = {}
    for idx, phase in enumerate(PHASES):
        seed = base_seed + idx * 97
        print(f"[Dropout] {phase['name']} fail_ratio={phase['fail_ratio']}")
        results[phase["name"]] = run_phase(base_positions, phase, seed)

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'dynamic_dropout.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved dropout scenario to {out_path}")
