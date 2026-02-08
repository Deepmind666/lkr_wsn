#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sweep gateway parameters (number of gateways and distance weights) with multiple replicates,
capturing mean/std of end-to-end PDR and energy for a 200-node uniform topology.
"""

import argparse
import os
import sys
import json
import random
import statistics
from typing import List, Tuple, Dict

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol
from gateway_selector import GatewayConfig


def parse_list(value: str, cast):
    return [cast(x.strip()) for x in value.split(",") if x.strip()]


def parse_args():
    parser = argparse.ArgumentParser(description="Gateway parameter sweep with diagnostic outputs.")
    parser.add_argument("--num-nodes", type=int, default=200)
    parser.add_argument("--area", type=float, default=220.0)
    parser.add_argument("--base-x", type=float, default=110.0)
    parser.add_argument("--base-y", type=float, default=260.0)
    parser.add_argument("--initial-energy", type=float, default=4.0)
    parser.add_argument("--rounds", type=int, default=200)
    parser.add_argument("--counts", type=str, default="1,2,3,4", help="Comma list of gateway counts.")
    parser.add_argument("--w-dist", type=str, default="-0.9,-0.7,-0.5,-0.3", help="Comma list of distance weights.")
    parser.add_argument("--replicates", type=int, default=5)
    parser.add_argument("--seed", type=int, default=70000, help="Base seed.")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument(
        "--extra-bases",
        type=str,
        default="",
        help="Semicolon-separated list of extra BS coordinates formatted as 'x:y'.",
    )
    parser.add_argument("--skeleton-k", type=int, default=None, help="Override skeleton backbone count.")
    parser.add_argument(
        "--skeleton-d-threshold",
        type=float,
        default=None,
        help="Override skeleton d_threshold_ratio.",
    )
    parser.add_argument(
        "--skeleton-q-far",
        type=float,
        default=None,
        help="Override skeleton q_far quantile (0-1).",
    )
    parser.add_argument(
        "--gateway-limit",
        type=int,
        default=None,
        help="Maximum number of non-gateway clusters each gateway may serve.",
    )
    parser.add_argument(
        "--gateway-concurrency",
        type=int,
        default=None,
        help="Maximum number of gateways allowed to uplink per round.",
    )
    parser.add_argument(
        "--gateway-limit-dynamic",
        action="store_true",
        help="Enable adaptive gateway load limit adjustments (requires --gateway-limit).",
    )
    parser.add_argument(
        "--gateway-limit-min",
        type=int,
        default=1,
        help="Minimum per-gateway load when dynamic limit is enabled.",
    )
    parser.add_argument(
        "--gateway-limit-window",
        type=int,
        default=20,
        help="Number of link attempts to accumulate before adapting the load limit.",
    )
    parser.add_argument(
        "--gateway-limit-reduce",
        type=float,
        default=0.35,
        help="Failure ratio threshold to tighten the load limit.",
    )
    parser.add_argument(
        "--gateway-limit-expand",
        type=float,
        default=0.15,
        help="Failure ratio threshold to relax the load limit.",
    )
    parser.add_argument(
        "--gateway-limit-cooldown",
        type=int,
        default=3,
        help="Rounds to wait after a dynamic adjustment.",
    )
    return parser.parse_args()


def generate_positions(seed: int, num_nodes: int, area: float) -> List[Tuple[float, float]]:
    rng = random.Random(seed)
    return [(rng.uniform(5, area - 5), rng.uniform(5, area - 5)) for _ in range(num_nodes)]


def run_case(seed: int, cfg_kwargs: Dict, rounds: int, gateway_k: int, w_dist: float) -> Dict:
    cfg = NetworkConfig(**cfg_kwargs)
    cfg.positions = generate_positions(seed, cfg_kwargs["num_nodes"], cfg_kwargs["area_width"])

    aeris = AerisProtocol(
        cfg,
        enable_cas=True,
        enable_fairness=True,
        enable_gateway=True,
        enable_skeleton=True,
        profile="robust",
        verbose=False,
    )
    try:
        aeris.gateway_selector = aeris.gateway_selector.__class__(
            GatewayConfig(k=gateway_k, w_dist_bs=w_dist, w_centrality=0.3)
        )
    except Exception:
        pass
    return aeris.run_simulation(rounds)


def aggregate_stats(runs: List[Dict], key: str):
    values = [run.get(key) for run in runs if run.get(key) is not None]
    if not values:
        return {"mean": None, "std": None}
    return {
        "mean": statistics.mean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
    }


if __name__ == "__main__":
    args = parse_args()
    gateway_counts = parse_list(args.counts, int)
    dist_weights = parse_list(args.w_dist, float)

    cfg_kwargs = {
        "num_nodes": args.num_nodes,
        "area_width": args.area,
        "area_height": args.area,
        "base_station_x": args.base_x,
        "base_station_y": args.base_y,
        "initial_energy": args.initial_energy,
        "packet_size": 1024,
    }
    extra_bases = []
    if args.extra_bases:
        for token in args.extra_bases.split(";"):
            token = token.strip()
            if not token:
                continue
            try:
                bx_str, by_str = token.split(":")
                extra_bases.append((float(bx_str), float(by_str)))
            except ValueError:
                continue
    if extra_bases:
        cfg_kwargs["extra_base_stations"] = extra_bases
    skeleton_cfg = {}
    if args.skeleton_k is not None:
        skeleton_cfg["k"] = max(1, int(args.skeleton_k))
    if args.skeleton_d_threshold is not None:
        skeleton_cfg["d_threshold_ratio"] = float(args.skeleton_d_threshold)
    if args.skeleton_q_far is not None:
        skeleton_cfg["q_far"] = float(args.skeleton_q_far)
    if skeleton_cfg:
        cfg_kwargs["skeleton_config"] = skeleton_cfg
    if args.gateway_limit is not None:
        cfg_kwargs["gateway_load_limit"] = max(1, int(args.gateway_limit))
    if args.gateway_concurrency is not None:
        cfg_kwargs["gateway_concurrency"] = max(0, int(args.gateway_concurrency))
    if args.gateway_limit_dynamic and args.gateway_limit is not None:
        cfg_kwargs["gateway_limit_dynamic"] = True
        cfg_kwargs["gateway_limit_min"] = max(1, int(args.gateway_limit_min))
        cfg_kwargs["gateway_limit_window"] = max(1, int(args.gateway_limit_window))
        cfg_kwargs["gateway_limit_reduce_threshold"] = float(args.gateway_limit_reduce)
        cfg_kwargs["gateway_limit_expand_threshold"] = float(args.gateway_limit_expand)
        cfg_kwargs["gateway_limit_cooldown_steps"] = max(1, int(args.gateway_limit_cooldown))

    sweep_results = {}
    for i, k in enumerate(gateway_counts):
        for j, wd in enumerate(dist_weights):
            key = f"k{k}_wd{wd}"
            runs = []
            for r in range(args.replicates):
                seed = args.seed + i * 1000 + j * 200 + r * 23
                print(f"[GATEWAY SWEEP] {key} replicate {r+1}/{args.replicates}")
                res = run_case(seed, cfg_kwargs, args.rounds, k, wd)
                am = res.get("additional_metrics", {})
                runs.append(
                    {
                        "seed": seed,
                        "pdr_end2end": res.get("packet_delivery_ratio_end2end", 0.0),
                        "pdr_hop": res.get("packet_delivery_ratio", 0.0),
                        "energy": res.get("total_energy_consumed", 0.0),
                        "ch_to_bs_pdr": am.get("ch_to_bs_pdr_total"),
                        "gateway_uplink_pdr": am.get("gateway_uplink_pdr_total"),
                        "cluster_radius_mean": am.get("cluster_radius_mean_total"),
                        "ch_to_bs_distance_mean": am.get("ch_to_bs_distance_mean_total"),
                        "gateway_uplink_suppressed": am.get("gateway_uplink_suppressed_total"),
                        "gateway_limit_final": am.get("gateway_limit_current"),
                        "gateway_limit_trace": am.get("gateway_limit_history"),
                        "gateway_concurrency_avg": am.get("gateway_concurrency_usage_avg"),
                        "gateway_limit_dynamic": am.get("gateway_limit_dynamic_enabled"),
                    }
                )
            sweep_results[key] = {
                "runs": runs,
                "stats": {
                    "pdr_end2end": aggregate_stats(runs, "pdr_end2end"),
                    "energy": aggregate_stats(runs, "energy"),
                    "ch_to_bs_pdr": aggregate_stats(runs, "ch_to_bs_pdr"),
                    "gateway_uplink_pdr": aggregate_stats(runs, "gateway_uplink_pdr"),
                    "cluster_radius_mean": aggregate_stats(runs, "cluster_radius_mean"),
                    "ch_to_bs_distance_mean": aggregate_stats(runs, "ch_to_bs_distance_mean"),
                },
            }

    out_path = args.output or os.path.join(os.path.dirname(__file__), '..', 'results', 'gateway_sweep.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(sweep_results, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved gateway sweep to {out_path}")
