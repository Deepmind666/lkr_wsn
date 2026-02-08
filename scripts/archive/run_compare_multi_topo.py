#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run baseline comparisons for multiple larger-scale topologies
(100/200 nodes, uniform + corridor) to complement the default 50-node study.

Usage:
    python scripts/run_compare_multi_topo.py
"""

import os
import sys
import json
import random
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


TOPOLOGIES: List[Dict] = [
    {
        "name": "uniform_100",
        "num_nodes": 100,
        "area_width": 150.0,
        "area_height": 150.0,
        "base_station": (75.0, 75.0),
        "kind": "uniform",
        "seed": 101,
    },
    {
        "name": "uniform_200",
        "num_nodes": 200,
        "area_width": 200.0,
        "area_height": 200.0,
        "base_station": (100.0, 100.0),
        "kind": "uniform",
        "seed": 202,
        "initial_energy": 4.0,
    },
    {
        "name": "corridor_100",
        "num_nodes": 100,
        "area_width": 30.0,
        "area_height": 250.0,
        "base_station": (15.0, 300.0),
        "kind": "corridor",
        "seed": 303,
    },
]


def generate_positions(kind: str, num_nodes: int, width: float, height: float, seed: int) -> List[Tuple[float, float]]:
    rng = random.Random(seed)
    positions: List[Tuple[float, float]] = []
    if kind == "corridor":
        for _ in range(num_nodes):
            x = rng.uniform(2.0, max(2.0, width - 2.0))
            y = rng.uniform(0.5, height - 0.5)
            positions.append((x, y))
    else:  # uniform
        for _ in range(num_nodes):
            x = rng.uniform(5.0, width - 5.0)
            y = rng.uniform(5.0, height - 5.0)
            positions.append((x, y))
    return positions


def run_topology(topology: Dict) -> Dict:
    cfg = NetworkConfig(
        num_nodes=topology["num_nodes"],
        area_width=topology["area_width"],
        area_height=topology["area_height"],
        base_station_x=topology["base_station"][0],
        base_station_y=topology["base_station"][1],
        initial_energy=topology.get("initial_energy", 2.0),
        packet_size=1024,
    )
    # Multi-gateway improves PDR/energy on larger maps
    cfg.gateway_k = 3
    cfg.positions = generate_positions(
        topology["kind"],
        topology["num_nodes"],
        topology["area_width"],
        topology["area_height"],
        topology["seed"],
    )

    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    results: Dict[str, Dict] = {}

    print(f">>> [{topology['name']}] Running LEACH")
    results["LEACH"] = LEACHProtocol(cfg, em).run_simulation(200)

    print(f">>> [{topology['name']}] Running PEGASIS")
    results["PEGASIS"] = PEGASISProtocol(cfg, em).run_simulation(200)

    print(f">>> [{topology['name']}] Running HEED")
    results["HEED"] = HEEDProtocolWrapper(cfg, em).run_simulation(200)

    print(f">>> [{topology['name']}] Running TEEN")
    results["TEEN"] = TEENProtocolWrapper(cfg, em).run_simulation(200)

    print(f">>> [{topology['name']}] Running AERIS")
    results["AERIS"] = AerisProtocol(
        cfg,
        enable_cas=True,
        enable_fairness=True,
        enable_gateway=True,
        enable_skeleton=True,
        profile="robust",
        verbose=False,
    ).run_simulation(200)

    return results


if __name__ == "__main__":
    all_results: Dict[str, Dict] = {}
    for topo in TOPOLOGIES:
        all_results[topo["name"]] = run_topology(topo)

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'compare_multi_topo.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved multi-topology comparison to {out_path}")
