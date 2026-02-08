#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比评估蒸馏CAS与规则CAS：
- 构建同一网络配置，分别运行两种选择器
- 输出 PDR(end2end/hop)、总能耗、寿命、模式分布与推理耗时

Usage:
  python scripts/run_distilled_cas_eval.py --nodes 50 --rounds 200 --seeds 5 --width 100 --height 100 --output results/distilled_eval.json
  # 也可设置 USE_DISTILLED_CAS=1 环境变量后仅运行蒸馏版本
"""
import os, sys, json, time, argparse, random
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol, CASMode


def run_once(cfg: NetworkConfig, *, use_distilled: bool, rounds: int, seed: int):
    proto = AerisProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile='energy', verbose=False, seed=seed, use_distilled_cas=use_distilled)
    res = proto.run_simulation(rounds)
    # 模式分布（按round统计）
    stats = res.get('round_statistics', [])
    mode_counts = {m.value: 0 for m in CASMode}
    infer_us = []
    for r in stats:
        counts = r.get('cas_mode_counts')
        if isinstance(counts, dict):
            for mode_key, count in counts.items():
                if mode_key in mode_counts:
                    mode_counts[mode_key] += int(count)
        else:
            m = r.get('cas_mode')
            if m in mode_counts:
                mode_counts[m] += 1
        iu_mean = r.get('cas_infer_us_mean')
        if isinstance(iu_mean, (int, float)):
            infer_us.append(float(iu_mean))
        else:
            iu = r.get('cas_infer_us')
            if isinstance(iu, (int, float)):
                infer_us.append(float(iu))
    return {
        'total_energy_consumed': res.get('total_energy_consumed', 0.0),
        'pdr_end2end': res.get('packet_delivery_ratio_end2end', 0.0),
        'pdr_hop': res.get('packet_delivery_ratio', 0.0),
        'lifetime': res.get('network_lifetime', 0),
        'final_alive_nodes': res.get('final_alive_nodes', 0),
        'mode_counts': mode_counts,
        'infer_us_mean': (sum(infer_us)/len(infer_us)) if infer_us else None,
        'infer_us_p95': (sorted(infer_us)[int(0.95*(len(infer_us)-1))] if infer_us else None),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nodes', type=int, default=50)
    ap.add_argument('--width', type=float, default=100.0)
    ap.add_argument('--height', type=float, default=100.0)
    ap.add_argument('--rounds', type=int, default=200)
    ap.add_argument('--seeds', type=int, default=5)
    ap.add_argument('--bs-x', type=float, default=None)
    ap.add_argument('--bs-y', type=float, default=None)
    ap.add_argument('--output', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'results', 'distilled_eval.json'))
    args = ap.parse_args()

    cfg = NetworkConfig(
        num_nodes=args.nodes,
        area_width=args.width,
        area_height=args.height,
        initial_energy=2.0,
        packet_size=1024,
    )
    if args.bs_x is not None:
        cfg.base_station_x = float(args.bs_x)
    if args.bs_y is not None:
        cfg.base_station_y = float(args.bs_y)

    results = {'baseline': [], 'distilled': []}
    base_seed = int(os.environ.get('AERIS_SEED', '1337'))
    for i in range(args.seeds):
        seed = base_seed + i
        random.seed(seed); np.random.seed(seed)
        results['baseline'].append(run_once(cfg, use_distilled=False, rounds=args.rounds, seed=seed))
        results['distilled'].append(run_once(cfg, use_distilled=True, rounds=args.rounds, seed=seed))

    # 汇总
    def summarize(arr, key):
        vals = [a.get(key) for a in arr]
        vals = [v for v in vals if v is not None]
        if not vals:
            return {'mean': None, 'std': None}
        m = float(np.mean(vals)); s = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
        return {'mean': m, 'std': s}

    summary = {
        'baseline': {
            'pdr_end2end': summarize(results['baseline'], 'pdr_end2end'),
            'pdr_hop': summarize(results['baseline'], 'pdr_hop'),
            'energy': summarize(results['baseline'], 'total_energy_consumed'),
            'lifetime': summarize(results['baseline'], 'lifetime'),
            'infer_us_mean': summarize(results['baseline'], 'infer_us_mean'),
        },
        'distilled': {
            'pdr_end2end': summarize(results['distilled'], 'pdr_end2end'),
            'pdr_hop': summarize(results['distilled'], 'pdr_hop'),
            'energy': summarize(results['distilled'], 'total_energy_consumed'),
            'lifetime': summarize(results['distilled'], 'lifetime'),
            'infer_us_mean': summarize(results['distilled'], 'infer_us_mean'),
        }
    }

    out_path = args.output
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'results': results, 'summary': summary}, f, ensure_ascii=False, indent=2)
    print(f"Saved eval to {out_path}")


if __name__ == '__main__':
    main()
