#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, random
sys.path.append(os.path.join(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from benchmark_protocols import NetworkConfig
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
from topology_generators import corridor, uniform

random.seed(123)

def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)

def test_skeleton_gateway_coordination():
    # Corridor 4:1 to strongly trigger skeleton backbones
    cfg = NetworkConfig(num_nodes=50, area_width=400.0, area_height=100.0, initial_energy=2.0, packet_size=1024)
    pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=4.0)
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=True, verbose=False)
    for i,(x,y) in enumerate(pts):
        proto.nodes[i].x = x; proto.nodes[i].y = y
    # Run a few rounds to allow stable CH/backbone selection
    proto.run_simulation(5)
    bb = getattr(proto, '_last_backbone_ids', [])
    gw = getattr(proto, '_last_gateway_ids', [])
    assert_true(len(bb) > 0, 'Expected non-empty backbone_ids under corridor 4:1')
    assert_true(len(gw) > 0, 'Expected at least one gateway under gateway-enabled run')
    assert_true(all(g in bb for g in gw), f'Gateway ids {gw} must be subset of backbone ids {bb}')

def test_gateway_fallback_without_skeleton():
    # Uniform small area so far_ratio likely below threshold; skeleton disabled explicitly
    cfg = NetworkConfig(num_nodes=50, area_width=100.0, area_height=100.0, initial_energy=2.0, packet_size=1024)
    pts = uniform(cfg.num_nodes, cfg.area_width, cfg.area_height)
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, verbose=False)
    for i,(x,y) in enumerate(pts):
        proto.nodes[i].x = x; proto.nodes[i].y = y
    proto.run_simulation(3)
    bb = getattr(proto, '_last_backbone_ids', [])
    gw = getattr(proto, '_last_gateway_ids', [])
    # When skeleton is disabled, backbone should be empty and gateway selected among all CHs; we at least ensure gateway exists
    assert_true(len(bb) == 0, 'Backbone must be empty when skeleton disabled')
    assert_true(len(gw) > 0, 'Gateway should exist when gateway enabled')

def test_safety_fallback_forces_direct():
    # Choose a stringent theta so that the first round is very likely below threshold and forces fallback in subsequent rounds
    cfg = NetworkConfig(num_nodes=50, area_width=300.0, area_height=100.0, initial_energy=2.0, packet_size=1024)
    pts = corridor(cfg.num_nodes, cfg.area_width, cfg.area_height, ratio=3.0)
    proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, verbose=False)
    for i,(x,y) in enumerate(pts):
        proto.nodes[i].x = x; proto.nodes[i].y = y
    proto.safety_fallback_enabled = True
    proto.safety_T = 1
    proto.safety_theta = 0.9
    proto.run_simulation(2)
    forced = getattr(proto, '_last_forced_direct', False)
    assert_true(forced is True, 'Safety fallback should force DIRECT mode in crisis round')

if __name__ == '__main__':
    test_skeleton_gateway_coordination()
    test_gateway_fallback_without_skeleton()
    test_safety_fallback_forces_direct()
    print('All coordination and safety tests passed.')

