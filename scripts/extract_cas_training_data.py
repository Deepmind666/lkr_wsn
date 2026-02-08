#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract CAS training dataset from AERIS simulation.

Outputs:
- data/cas_features.npy    # shape [N, 7], order: [energy, link, dist_bs, radius, density, fairness, tail_max]
- data/cas_labels.npy      # shape [N], int labels: {direct:0, chain:1, two_hop:2}
- data/cas_dataset_meta.json  # summary statistics and run config

Notes:
- This script hooks into AERIS CAS selection to log per-cluster features
  right before mode selection, using the rule-based CASSelector as the default teacher.
- Use CLI flags to control topology size and rounds to reach desired sample size.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List

import numpy as np

# Make src importable
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol
from cas_selector import CASSelector, CASConfig, CASMode
from distilled_cas_selector import DistilledCASSelector
from intel_dataset_loader import IntelLabDataLoader


LABEL_MAP = {CASMode.DIRECT: 0, CASMode.CHAIN: 1, CASMode.TWO_HOP: 2}
FEATURE_KEYS = ["energy", "link", "dist_bs", "radius", "density", "fairness", "tail_max"]


class LoggingCASSelector:
    """A selector wrapper that logs features and labels while delegating to the underlying selector."""

    def __init__(self, use_distilled: bool = False):
        base = DistilledCASSelector(CASConfig()) if use_distilled else CASSelector(CASConfig())
        self._base = base
        self.features: List[List[float]] = []
        self.labels: List[int] = []
        self.confidences: List[float] = []
        self.scores: List[Dict[str, float]] = []

    # Forward important attributes used by AerisProtocol for one-time tuning
    @property
    def cfg(self):
        return self._base.cfg

    @cfg.setter
    def cfg(self, value):
        self._base.cfg = value

    @property
    def last_infer_us(self):
        return getattr(self._base, 'last_infer_us', None)

    def select_mode(self, features: Dict[str, float]):
        mode, conf, scores = self._base.select_mode(features)
        # Stable feature vector order
        vec = [float(features.get(k, 0.0)) for k in FEATURE_KEYS]
        self.features.append(vec)
        self.labels.append(LABEL_MAP[mode])
        self.confidences.append(float(conf))
        # scores keys are CASMode; convert to str
        self.scores.append({m.value if hasattr(m, 'value') else str(m): float(v) for m, v in scores.items()})
        return mode, conf, scores

    def __getattr__(self, name: str):
        # Fallback to underlying selector for any other attributes/methods
        return getattr(self._base, name)


def build_argparser():
    ap = argparse.ArgumentParser(description="Extract CAS training data from AERIS simulation")
    ap.add_argument('--nodes', type=int, default=100, help='Number of nodes in the topology')
    ap.add_argument('--width', type=float, default=100.0, help='Area width')
    ap.add_argument('--height', type=float, default=100.0, help='Area height')
    ap.add_argument('--rounds', type=int, default=400, help='Number of rounds to simulate')
    ap.add_argument('--packet-size', type=int, default=1024, help='Packet size (bytes)')
    ap.add_argument('--seed', type=int, default=42, help='Random seed')
    ap.add_argument('--profile', type=str, default='energy', choices=['energy', 'robust', 'default'], help='AERIS profile')
    ap.add_argument('--use-distilled-teacher', action='store_true', help='Use distilled selector as teacher for logging (default: rule-based)')
    ap.add_argument('--output-dir', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'data'), help='Output directory for dataset files')
    ap.add_argument('--min-samples', type=int, default=10000, help='Minimum acceptable sample count (warn if below)')
    ap.add_argument('--use-intel', action='store_true', help='Use real Intel Lab dataset for topology and environment (no simulation-only synthetic data)')
    ap.add_argument('--initial-energy', type=float, default=2.0, help='Initial energy per node (Joules) to extend simulation length')
    return ap


def main():
    args = build_argparser().parse_args()

    # Build protocol and environment based on real Intel dataset if requested
    if args.use_intel:
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
        # Validate required assets
        if loader.sensor_data is None or (hasattr(loader.sensor_data, 'empty') and loader.sensor_data.empty):
            raise RuntimeError('Intel sensor dataset not found. Please ensure data.txt.gz exists under data/.')
        if loader.locations_data is None or (hasattr(loader.locations_data, 'empty') and loader.locations_data.empty):
            raise RuntimeError('Intel mote locations file missing. Ensure mote_locs.txt exists under data/Intel_Lab_Data/.')

        # Geometry from real mote locations
        locs = loader.locations_data.sort_values('node_id') if 'node_id' in loader.locations_data.columns else loader.locations_data.sort_values('moteid')
        xs = locs['x'].to_list(); ys = locs['y'].to_list()
        n = len(xs)
        minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys)
        width = (maxx - minx) if maxx > minx else float(args.width)
        height = (maxy - miny) if maxy > miny else float(args.height)

        cfg = NetworkConfig(
            num_nodes=n,
            area_width=width,
            area_height=height,
            initial_energy=float(args.initial_energy),
            packet_size=args.packet_size,
        )

        proto = AerisProtocol(
            cfg,
            enable_cas=True,
            enable_fairness=True,
            enable_gateway=True,
            enable_skeleton=False,
            profile=args.profile,
            verbose=False,
            seed=args.seed,
        )

        # Normalize and assign real positions
        minx0, miny0 = minx, miny
        for i, (x, y) in enumerate(zip(xs, ys)):
            proto.nodes[i].x = float(x) - minx0
            proto.nodes[i].y = float(y) - miny0

        # Build environment provider from real humidity/temperature time series
        s = loader.sensor_data.dropna(subset=['humidity','temperature'])
        hum = s['humidity'].values.astype(np.float32)
        tmp = s['temperature'].values.astype(np.float32)

        def env_provider(t: int):
            idx = min(t, len(hum) - 1)
            temp_c = float(tmp[idx])
            hum_ratio = float(np.clip(hum[idx], 0.0, 100.0)) / 100.0
            return (temp_c, hum_ratio)
    else:
        # Fallback: use synthetic topology (not allowed for final dataset by policy, but kept for CLI completeness)
        cfg = NetworkConfig(
            num_nodes=args.nodes,
            area_width=args.width,
            area_height=args.height,
            initial_energy=float(args.initial_energy),
            packet_size=args.packet_size,
        )

        proto = AerisProtocol(
            cfg,
            enable_cas=True,
            enable_fairness=True,
            enable_gateway=True,
            enable_skeleton=False,
            profile=args.profile,
            verbose=False,
            seed=args.seed,
        )
        env_provider = None

    # Pre-inject logging selector so protocol will use it instead of creating a new one
    logger_sel = LoggingCASSelector(use_distilled=args.use_distilled_teacher)
    proto.cas_selector = logger_sel

    # Run simulation with real environment if provided
    res = proto.run_simulation(args.rounds, env_provider=env_provider) if args.use_intel else proto.run_simulation(args.rounds)

    # Prepare outputs
    X = np.array(logger_sel.features, dtype=np.float32)
    y = np.array(logger_sel.labels, dtype=np.int64)

    os.makedirs(args.output_dir, exist_ok=True)
    feat_path = os.path.join(args.output_dir, 'cas_features.npy')
    label_path = os.path.join(args.output_dir, 'cas_labels.npy')
    meta_path = os.path.join(args.output_dir, 'cas_dataset_meta.json')

    np.save(feat_path, X)
    np.save(label_path, y)

    # Class distribution
    counts = { 'direct': int((y == 0).sum()), 'chain': int((y == 1).sum()), 'two_hop': int((y == 2).sum()) }
    total = int(y.shape[0])
    dist = {k: (v / total if total > 0 else 0.0) for k, v in counts.items()}

    meta: Dict[str, Any] = {
        'total_samples': total,
        'class_counts': counts,
        'class_distribution': dist,
        'feature_keys': FEATURE_KEYS,
        'config': {
            'nodes': args.nodes,
            'width': args.width,
            'height': args.height,
            'rounds': args.rounds,
            'packet_size': args.packet_size,
            'seed': args.seed,
            'profile': args.profile,
            'teacher': ('distilled' if args.use_distilled_teacher else 'rule-based')
        },
        'data_source': ('intel' if args.use_intel else 'synthetic'),
        'protocol_summary': {
            'network_lifetime': res.get('network_lifetime'),
            'packet_delivery_ratio': res.get('packet_delivery_ratio'),
            'total_energy_consumed': res.get('total_energy_consumed'),
        }
    }

    # Attach Intel-specific meta when applicable
    if args.use_intel:
        meta['intel_meta'] = {
            'locations_file': os.path.join(os.path.dirname(__file__), '..', 'data', 'Intel_Lab_Data', 'mote_locs.txt'),
            'sensor_file': os.path.join(os.path.dirname(__file__), '..', 'data', 'data.txt.gz'),
        }

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Saved features to: {feat_path}")
    print(f"Saved labels to:   {label_path}")
    print(f"Saved meta to:     {meta_path}")

    if total < args.min_samples:
        print(f"[WARN] Sample count {total} < min-samples {args.min_samples}. Consider increasing --nodes or --rounds.")


if __name__ == '__main__':
    main()