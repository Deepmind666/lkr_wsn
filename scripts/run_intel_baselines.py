#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, math
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
from intel_dataset_loader import IntelLabDataLoader
from baseline_protocols.leach_protocol import LEACHProtocol, LEACHNode
from baseline_protocols.heed_protocol import HEEDProtocol, HEEDNode

if __name__ == '__main__':
    # 1) Load Intel dataset (public)
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    assert loader.locations_data is not None and not loader.locations_data.empty, 'Location file missing; run scripts/download_intel_assets.py'

    # 2) Build node list from real geometry
    locs = loader.locations_data.sort_values('node_id')
    minx, miny = float(locs['x'].min()), float(locs['y'].min())
    xs = (locs['x'] - minx).astype(float).to_list()
    ys = (locs['y'] - miny).astype(float).to_list()
    base_station = (max(xs)*1.05, max(ys)*0.5)

    nodes = [LEACHNode(i, xs[i], ys[i], initial_energy=2.0) for i in range(len(xs))]
    leach = LEACHProtocol(nodes, base_station=base_station, desired_ch_percentage=0.1)

    # 3) Run baseline simulation (LEACH)
    res = leach.run_simulation(max_rounds=200)

    out = {
        'LEACH': {k: res.get(k) for k in (
            'total_energy_consumed','packet_delivery_ratio','network_lifetime','alive_nodes','dead_nodes'
        )},
        'geometry': {'num_nodes': len(nodes)}
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_baseline_leach.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

