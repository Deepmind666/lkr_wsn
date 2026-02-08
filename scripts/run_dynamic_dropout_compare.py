#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run baseline protocols and AERIS variants under random dropout stress.
Each phase increases the failed-node ratio while keeping surviving nodes fixed,
allowing direct comparison between LEACH/PEGASIS/HEED/TEEN and AERIS.

Outputs:
    results/dynamic_dropout_compare.json
"""

import argparse
import json
import os
import random
import sys
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

# 更激进设置：再缩短距离、提高初始能量、更多 gateway，双基站靠近节点区域
BASE_NUM = 120
AREA_WIDTH = 80.0
AREA_HEIGHT = 120.0
BASE_STATION = (40.0, 120.0)
SECONDARY_BS = (40.0, 60.0)  # 较近的辅助 BS，强化上行
PHASES = [
    {"name": "drop0", "fail_ratio": 0.0},
    {"name": "drop10", "fail_ratio": 0.10},
    {"name": "drop20", "fail_ratio": 0.20},
    {"name": "drop30", "fail_ratio": 0.30},
]
BASE_SEED = 90001
ROUNDS = 150


def generate_positions(seed: int) -> List[Tuple[float, float]]:
    rng = random.Random(seed)
    return [
        (rng.uniform(5.0, AREA_WIDTH - 5.0), rng.uniform(5.0, AREA_HEIGHT - 5.0))
        for _ in range(BASE_NUM)
    ]


def select_survivors(base_positions: List[Tuple[float, float]], fail_ratio: float, seed: int) -> List[Tuple[float, float]]:
    rng = random.Random(seed)
    survivors = base_positions.copy()
    rng.shuffle(survivors)
    fail_count = int(len(base_positions) * fail_ratio)
    if fail_count >= len(base_positions):
        return []
    return survivors[fail_count:]


def run_phase(positions: List[Tuple[float, float]], phase_seed: int) -> Dict[str, Dict]:
    cfg = NetworkConfig(
        num_nodes=len(positions),
        area_width=AREA_WIDTH,
        area_height=AREA_HEIGHT,
        base_station_x=BASE_STATION[0],
        base_station_y=BASE_STATION[1],
        initial_energy=6.0,
        packet_size=1024,
    )
    cfg.enable_channel = True
    cfg.channel_env = "indoor_office"
    cfg.tx_power_dbm = 0.0
    cfg.link_retx = 1
    cfg.link_retx_power_step = 1.0
    # 更密集网关、更高能量，且允许备用 BS；由 AerisProtocol 内部使用辅助 BS 评分
    cfg.gateway_k = 32
    cfg.gateway_concurrency = None  # 不限并发
    cfg.gateway_load_limit = None   # 不限负载
    cfg.gateway_retry_limit = 2
    cfg.gateway_rescue_direct = True
    cfg.intra_link_retx = 2
    cfg.intra_link_power_step = 1.5
    # 更激进骨架/网关参数：鼓励近距离、限制长链
    cfg.skeleton_config = {
        "d_threshold_ratio": 0.25,
        "q_far": 0.2,
        "w_axis_proximity": 2.0,
        "w_centrality": 1.0,
    }
    # 掉线强化模式：在 AerisProtocol 内触发“近 BS+冗余”逻辑
    cfg.high_dropout_mode = True
    # 允许骨架最长跳数 H=1（禁用长链）
    cfg.h_max = 1
    cfg.secondary_base_station = SECONDARY_BS
    cfg.positions = positions

    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    results: Dict[str, Dict] = {}

    results["LEACH"] = LEACHProtocol(cfg, em).run_simulation(ROUNDS)
    results["PEGASIS"] = PEGASISProtocol(cfg, em).run_simulation(ROUNDS)
    results["HEED"] = HEEDProtocolWrapper(cfg, em).run_simulation(ROUNDS)
    results["TEEN"] = TEENProtocolWrapper(cfg, em).run_simulation(ROUNDS)

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
            seed=phase_seed,
        )
        results[profile_map[profile]] = proto.run_simulation(ROUNDS)
    return results


def run_replicate(base_seed: int) -> Dict[str, Dict]:
    base_positions = generate_positions(base_seed)
    replicate_results: Dict[str, Dict] = {}

    for idx, phase in enumerate(PHASES):
        phase_seed = base_seed + idx * 173
        positions = select_survivors(base_positions, phase["fail_ratio"], phase_seed)
        if not positions:
            print(f"[WARN] {phase['name']} removed all nodes; skipping.")
            continue
        print(f"[DropoutCompare] {phase['name']} fail_ratio={phase['fail_ratio']:.2f} survivors={len(positions)} seed={phase_seed}")
        replicate_results[phase["name"]] = run_phase(positions, phase_seed)
    return replicate_results


def parse_args():
    parser = argparse.ArgumentParser(description="Dynamic dropout comparison with optional replicates.")
    parser.add_argument("--output", default=None, help="Output JSON path")
    # 默认跑 5 轮以补足样本量
    parser.add_argument("--replicates", type=int, default=5, help="Number of replicates to run")
    parser.add_argument("--seed-offset", type=int, default=0, help="Offset added to base seed for first replicate")
    parser.add_argument("--seed-stride", type=int, default=1000, help="Stride added between replicate seeds")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    out_path = args.output or os.path.join(os.path.dirname(__file__), '..', 'results', 'dynamic_dropout_compare.json')
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
        "experiment": "dynamic_dropout_compare",
        "timestamp": datetime.now().isoformat(),
        "git_commit": git_commit,
        "n_replicates": args.replicates,
        "base_seed": BASE_SEED,
        "seed_offset": args.seed_offset,
        "seed_stride": args.seed_stride,
        "n_nodes": BASE_NUM,  # 统一命名
        "n_rounds": ROUNDS,
        "scenario_config": {
            "area_width": AREA_WIDTH,
            "area_height": AREA_HEIGHT,
            "base_station": BASE_STATION,
            "secondary_bs": SECONDARY_BS,
            "phases": PHASES,
        },
        "phases": [p["name"] for p in PHASES],
        "format_version": "1.0"
    }

    if args.replicates <= 1:
        base_seed = BASE_SEED + args.seed_offset
        all_results = run_replicate(base_seed)
        metadata["seeds_used"] = [base_seed]
    else:
        all_results = {}
        seeds_used = []
        for rep in range(args.replicates):
            base_seed = BASE_SEED + args.seed_offset + rep * args.seed_stride
            seeds_used.append(base_seed)
            print(f"[DropoutCompare] replicate {rep} base_seed={base_seed}")
            all_results[f"rep_{rep}"] = run_replicate(base_seed)
        metadata["seeds_used"] = seeds_used

    # 计算结果数量
    if args.replicates <= 1:
        n_results = len(PHASES) * 6  # phases × 6 protocols
    else:
        n_results = args.replicates * len(PHASES) * 6

    output = {
        "n_results": n_results,
        "format_version": "1.0",
        "schema_type": "dynamic_dropout",
        "metadata": metadata,
        "results": all_results
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved dropout comparison to {out_path}")
