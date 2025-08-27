#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, math, numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from intel_dataset_loader import IntelLabDataLoader
from experiment_logger import ExperimentLogger

if __name__ == '__main__':
    # 1) Load Intel Lab dataset (public)
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    assert loader.sensor_data is not None and not loader.sensor_data.empty, 'Intel dataset not found. Please place data.txt.gz under data/. '
    assert loader.locations_data is not None and not loader.locations_data.empty, 'Location file missing; see intel loader README.'

    # 2) Build a static topology from mote locations
    locs = loader.locations_data.sort_values('node_id')
    n = len(locs)
    # Normalize coordinates to meters scale (assume original in meters or relative units)
    xs = locs['x'].to_list(); ys = locs['y'].to_list()
    minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys)
    width = maxx - minx if maxx > minx else 50.0
    height = maxy - miny if maxy > miny else 50.0
    # 3) Network config using real geometry
    cfg = NetworkConfig(num_nodes=n, area_width=width, area_height=height, initial_energy=2.0, packet_size=1024)

    # 4) Initialize protocol profiles
    def run_profile(profile: str):
        proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile=profile, verbose=False)
        # place nodes
        for i,(x,y) in enumerate(zip(xs, ys)):
            proto.nodes[i].x = float(x) - minx
            proto.nodes[i].y = float(y) - miny
        # build a per-round environment provider using humidity percentiles
        # Map humidity [0,100] -> (shadowing_std, noise_floor)
        s = loader.sensor_data.dropna(subset=['humidity','temperature'])
        env_map = []
        if not s.empty:
            h_vals = s['humidity'].values
            t_vals = s['temperature'].values
            h_p33 = float(np.percentile(h_vals, 33))
            h_p66 = float(np.percentile(h_vals, 66))
            t_med = float(np.percentile(t_vals, 50))
            # Define three humidity regimes: low/normal/high with shadowing std mapping
            regimes = [
                {'name':'low', 'h': h_p33, 'shadow': 3.5},
                {'name':'mid', 'h': (h_p33+h_p66)/2, 'shadow': 7.0},
                {'name':'high','h': h_p66, 'shadow': 12.0},
            ]
            def env_provider(round_idx: int):
                r = regimes[round_idx % 3]
                humidity_ratio = max(0.0, min(1.0, r['h']/100.0))
                temperature_c = t_med
                # Conservative mapping: only shadowing_std (4.5/7.0/9.5 dB) and slight noise_floor shift
                nf = -96.0 + (0.5 if r['name']=='mid' else (1.0 if r['name']=='high' else 0.0))
                proto.channel_model.set_env_mapping(
                    shadowing_std=r['shadow'],
                    noise_floor_dbm=nf,
                )
                return (temperature_c, humidity_ratio)
        else:
            env_provider = None
        return proto.run_simulation(200, env_provider=env_provider)

    logger = ExperimentLogger()
    res_energy = run_profile('energy')
    logger.log('intel_replay', {'profile':'energy'}, res_energy)
    res_robust = run_profile('robust')
    logger.log('intel_replay', {'profile':'robust'}, res_robust)

    out = {
        'AETHER_energy': {k: res_energy.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes')},
        'AETHER_robust': {k: res_robust.get(k) for k in ('total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','final_alive_nodes')},
        'geometry': {'width': width, 'height': height, 'num_nodes': n},
        'env_mapping': 'humidity_percentiles->humidity_ratio (33/50/66)',
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_replay_compare.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

