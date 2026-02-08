#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

BASE_SEED = int(os.environ.get('AERIS_BASELINE_SEED', '2411'))
random.seed(BASE_SEED)

from intel_dataset_loader import IntelLabDataLoader
from baseline_protocols.leach_protocol import LEACHProtocol, LEACHNode
from baseline_protocols.heed_protocol import HEEDProtocol, HEEDNode
from baseline_protocols.pegasis_protocol import PEGASISProtocol, PEGASISNode
from teen_protocol import TEENProtocol, TEENConfig

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    # Prefer real Intel Lab data/geometry by default; fall back to synthetic with explanation
    try:
        loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    except Exception as e:
        print(f"[WARN] Real Intel dataset unavailable or failed to initialize: {e}")
        print("[INFO] Falling back to synthetic dataset for baseline runs; ensure real data.txt.gz/mote_locs.txt exist under data/Intel_Lab_Data/ for replay.")
        loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=True)
    # Ensure dataset is available
    if loader.sensor_data is None or (hasattr(loader.sensor_data, 'empty') and loader.sensor_data.empty):
        try:
            loader.generate_synthetic_data()
            print('[INFO] Generated synthetic dataset for baselines')
        except Exception as e:
            raise RuntimeError(f"Failed to generate synthetic dataset: {e}")
    # Prefer real geometry if available (mote_locs.txt / connectivity.txt)
    try:
        if os.path.exists(loader.locations_file):
            loc_df = loader.load_locations_data()
            if loc_df is not None and not loc_df.empty:
                loader.locations_data = loc_df
                print('[INFO] Using real mote locations from mote_locs.txt')
        else:
            print('[WARN] Real mote_locs.txt not found; using generated/default locations')
        if os.path.exists(loader.connectivity_file):
            conn_df = loader.load_connectivity_data()
            if conn_df is not None and not conn_df.empty:
                loader.connectivity_data = conn_df
                print('[INFO] Using real connectivity from connectivity.txt')
        else:
            print('[WARN] Real connectivity.txt not found; building connectivity from locations')
    except Exception as e:
        print(f"[WARN] Could not prioritize real geometry: {e}")
    # Ensure locations are available
    if loader.locations_data is None or (hasattr(loader.locations_data, 'empty') and loader.locations_data.empty):
        try:
            loader._generate_default_locations()
            print('[INFO] Generated default grid locations')
        except Exception as e:
            raise RuntimeError(f"Locations data unavailable and default generation failed: {e}")
    # Normalize column names for node id
    if 'node_id' not in loader.locations_data.columns and 'moteid' in loader.locations_data.columns:
        loader.locations_data = loader.locations_data.rename(columns={'moteid': 'node_id'})
    locs = loader.locations_data.sort_values('node_id')
    xs = locs['x'].to_numpy().tolist()
    ys = locs['y'].to_numpy().tolist()
    minx, miny = float(locs['x'].min()), float(locs['y'].min())
    xs = (locs['x'] - minx).astype(float).to_list()
    ys = (locs['y'] - miny).astype(float).to_list()
    base_station = (max(xs)*1.05, max(ys)*0.5)

    # LEACH
    nodes_l = [LEACHNode(i, xs[i], ys[i], initial_energy=2.0) for i in range(len(xs))]
    leach = LEACHProtocol(nodes_l, base_station=base_station, desired_ch_percentage=0.1)
    res_leach = leach.run_simulation(max_rounds=200)

    # HEED
    nodes_h = [HEEDNode(i, xs[i], ys[i], initial_energy=2.0) for i in range(len(xs))]
    heed = HEEDProtocol(nodes_h, base_station=base_station, c_prob=0.05, cluster_radius=50.0)
    res_heed = heed.run_simulation(max_rounds=200)

    # PEGASIS
    nodes_p = [PEGASISNode(i, xs[i], ys[i], initial_energy=2.0) for i in range(len(xs))]
    pega = PEGASISProtocol(nodes_p, base_station=base_station)
    res_pega = pega.run_simulation(max_rounds=200)

    # TEEN (using benchmark TEENProtocol with Intel coordinates)
    teen_cfg = TEENConfig(
        num_nodes=len(xs),
        area_width=max(xs) if xs else 100.0,
        area_height=max(ys) if ys else 100.0,
        base_station_x=base_station[0],
        base_station_y=base_station[1],
        initial_energy=2.0,
    )
    teen = TEENProtocol(teen_cfg)
    teen.initialize_network(list(zip(xs, ys)))
    res_teen = teen.run_simulation(max_rounds=200)

    out = {
        'LEACH': {k: res_leach.get(k) for k in (
            'total_energy_consumed','packet_delivery_ratio_end2end','network_lifetime','alive_nodes','dead_nodes'
        )},
        'HEED': {k: res_heed.get(k) for k in (
            'total_energy_consumed','packet_delivery_ratio_end2end','network_lifetime','alive_nodes','dead_nodes'
        )},
        'PEGASIS': {k: res_pega.get(k) for k in (
            'total_energy_consumed','packet_delivery_ratio_end2end','network_lifetime','alive_nodes','dead_nodes'
        )},
        'TEEN': {
            'total_energy_consumed': res_teen.get('total_energy_consumed'),
            'packet_delivery_ratio_end2end': res_teen.get('packet_delivery_ratio_end2end', res_teen.get('packet_delivery_ratio', 0.0)),
            'network_lifetime': res_teen.get('network_lifetime'),
            'alive_nodes': res_teen.get('final_alive_nodes'),
            'dead_nodes': max(0, len(xs) - int(res_teen.get('final_alive_nodes', 0)))
        },
        'geometry': {'num_nodes': len(xs)},
        'runtime': {'seed': BASE_SEED}
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_baselines_all.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

