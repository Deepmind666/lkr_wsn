#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from intel_dataset_loader import IntelLabDataLoader
from baseline_protocols.pegasis_protocol import PEGASISProtocol, PEGASISNode

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    locs = loader.locations_data.sort_values('node_id')
    minx, miny = float(locs['x'].min()), float(locs['y'].min())
    xs = (locs['x'] - minx).astype(float).to_list()
    ys = (locs['y'] - miny).astype(float).to_list()
    base_station = (max(xs)*1.05, max(ys)*0.5)

    nodes = [PEGASISNode(i, xs[i], ys[i], initial_energy=2.0) for i in range(len(xs))]
    proto = PEGASISProtocol(nodes, base_station=base_station)
    res = proto.run_simulation(max_rounds=200)

    out = {'PEGASIS': {k: res.get(k) for k in (
        'total_energy_consumed','packet_delivery_ratio','packet_delivery_ratio_end2end','network_lifetime','alive_nodes','dead_nodes'
    )}}

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_baseline_pegasis.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

