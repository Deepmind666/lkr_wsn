#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, TEENProtocolWrapper
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol

if __name__ == '__main__':
    cfg = NetworkConfig(num_nodes=50, area_width=100.0, area_height=100.0, initial_energy=2.0, packet_size=1024)

    # 优先使用真实几何坐标（mote_locs.txt），缺失则回退为随机
    try:
        locs_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Intel_Lab_Data', 'mote_locs.txt')
        if os.path.exists(locs_path):
            print(f"[INFO] Using real mote locations from: {locs_path}")
            positions_dict = {}
            with open(locs_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        try:
                            node_id = int(parts[0])
                            x = float(parts[1]); y = float(parts[2])
                            positions_dict[node_id] = (x, y)
                        except Exception:
                            continue
            sorted_items = sorted(positions_dict.items(), key=lambda kv: kv[0])
            positions = [pos for _, pos in sorted_items][:cfg.num_nodes]
            if positions:
                cfg.positions = positions
                print(f"[INFO] Loaded {len(positions)} positions for simulation")
        else:
            print("[WARN] mote_locs.txt not found; falling back to synthetic positions")
    except Exception as e:
        print(f"[WARN] Failed to load mote_locs.txt: {e}; falling back to synthetic positions")

    results = {}

    # Baselines with unified energy model
    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    leach = LEACHProtocol(cfg, em)
    results['LEACH'] = leach.run_simulation(200)

    peg = PEGASISProtocol(cfg, em)
    results['PEGASIS'] = peg.run_simulation(200)

    heed = HEEDProtocolWrapper(cfg, em)
    results['HEED'] = heed.run_simulation(200)

    teen = TEENProtocolWrapper(cfg, em)
    results['TEEN'] = teen.run_simulation(200)

    aether = AerisProtocol(cfg, enable_cas=True, enable_fairness=True)
    results['AETHER'] = aether.run_simulation(200)

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'compare_50x200.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved results to {out_path}")

