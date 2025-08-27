#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

if __name__ == '__main__':
    cfg = NetworkConfig(num_nodes=50, area_width=100.0, area_height=100.0, initial_energy=2.0, packet_size=1024)
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    results = {}

    print('[RUN] LEACH 50x200')
    leach = LEACHProtocol(cfg, em)
    results['LEACH'] = leach.run_simulation(200)

    print('[RUN] PEGASIS 50x200')
    peg = PEGASISProtocol(cfg, em)
    results['PEGASIS'] = peg.run_simulation(200)

    print('[RUN] HEED 50x200')
    heed = HEEDProtocolWrapper(cfg, em)
    results['HEED'] = heed.run_simulation(200)

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'baselines_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved results to {out_path}")

