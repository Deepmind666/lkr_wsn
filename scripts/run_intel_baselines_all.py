#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from intel_dataset_loader import IntelLabDataLoader
from baseline_protocols.leach_protocol import LEACHProtocol, LEACHNode
from baseline_protocols.heed_protocol import HEEDProtocol, HEEDNode
from baseline_protocols.pegasis_protocol import PEGASISProtocol, PEGASISNode

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    locs = loader.locations_data.sort_values('node_id')
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
        'geometry': {'num_nodes': len(xs)}
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'intel_baselines_all.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

