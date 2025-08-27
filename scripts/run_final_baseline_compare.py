#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, random
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from baseline_protocols.leach_protocol import LEACHProtocol, LEACHNode
from baseline_protocols.pegasis_protocol import PEGASISProtocol, PEGASISNode
from baseline_protocols.heed_protocol import HEEDProtocol, HEEDNode
from topology_generators import uniform, corridor

random.seed(42)

# Simple baseline runners (uniform API)
def run_eenhfr(cfg, pts, profile):
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile=profile)
    for i,(x,y) in enumerate(pts): proto.nodes[i].x, proto.nodes[i].y = x,y
    return proto.run_simulation(200)

def run_leach(cfg, pts):
    nodes = [LEACHNode(i, x, y, initial_energy=cfg.initial_energy) for i,(x,y) in enumerate(pts)]
    bs = (cfg.base_station_x, cfg.base_station_y)
    proto = LEACHProtocol(nodes, bs, desired_ch_percentage=0.1)
    # emulate 200 rounds; LEACH's API differs; we return coarse metrics
    for _ in range(200):
        chs = proto.cluster_head_selection()
        proto.cluster_formation(chs)
        proto.data_transmission_phase(chs)
        proto.current_round += 1
    return {
        'total_energy_consumed': proto.total_energy_consumed,
        'packet_delivery_ratio_end2end': proto.packets_received / max(1, proto.packets_sent),
        'packet_delivery_ratio': proto.packets_received / max(1, proto.packets_sent),
        'network_lifetime': proto.network_lifetime or 200,
    }

def run_pegasis(cfg, pts):
    nodes = [PEGASISNode(i, x, y, initial_energy=cfg.initial_energy) for i,(x,y) in enumerate(pts)]
    bs = (cfg.base_station_x, cfg.base_station_y)
    proto = PEGASISProtocol(nodes, bs)
    for _ in range(200):
        proto.construct_chain()
        leader = proto.select_leader()
        if leader is None:
            break
        proto.data_transmission_phase(leader)
        proto.current_round += 1
    return {
        'total_energy_consumed': proto.total_energy_consumed,
        'packet_delivery_ratio_end2end': proto.packets_received / max(1, proto.packets_sent),
        'packet_delivery_ratio': proto.packets_received / max(1, proto.packets_sent),
        'network_lifetime': proto.network_lifetime or 200,
    }

def run_heed(cfg, pts):
    nodes = [HEEDNode(i, x, y, initial_energy=cfg.initial_energy) for i,(x,y) in enumerate(pts)]
    bs = (cfg.base_station_x, cfg.base_station_y)
    proto = HEEDProtocol(nodes, bs)
    for _ in range(200):
        proto.initialize_neighbors()
        chs = proto.cluster_head_selection()
        proto.data_transmission_phase(chs)
        proto.current_round += 1
    return {
        'total_energy_consumed': proto.total_energy_consumed,
        'packet_delivery_ratio_end2end': proto.packets_received / max(1, proto.packets_sent),
        'packet_delivery_ratio': proto.packets_received / max(1, proto.packets_sent),
        'network_lifetime': proto.network_lifetime or 200,
    }

if __name__ == '__main__':
    # scenarios
    scenarios = [
        ('uniform_50x200', lambda: (uniform(50, 100.0, 100.0), NetworkConfig(50,100.0,100.0,2.0,1024))),
        ('corridor31_50x200', lambda: (corridor(50, 300.0, 100.0, ratio=3.0), NetworkConfig(50,300.0,100.0,2.0,1024))),
        ('corridor41_50x200', lambda: (corridor(50, 400.0, 100.0, ratio=4.0), NetworkConfig(50,400.0,100.0,2.0,1024))),
    ]
    out = {}
    for name, make in scenarios:
        pts, cfg = make()
        # AETHER: energy vs robust profiles
        a_energy = run_eenhfr(cfg, pts, profile='energy')
        a_robust = run_eenhfr(cfg, pts, profile='robust')
        # Baselines
        leach = run_leach(cfg, pts)
        peg = run_pegasis(cfg, pts)
        heed = run_heed(cfg, pts)
        out[name] = {
            'AETHER_energy': a_energy,
            'AETHER_robust': a_robust,
            'LEACH': leach,
            'PEGASIS': peg,
            'HEED': heed,
        }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'final_baseline_compare.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved', out_path)

