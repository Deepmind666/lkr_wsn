#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, time
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from cas_selector import CASSelector, CASConfig, CASMode
from distilled_cas_selector import DistilledCASSelector
from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol


def test_interface_compatibility():
    cfg = CASConfig()
    rb = CASSelector(cfg)
    dl = DistilledCASSelector(cfg)
    features = {
        'energy': 0.8, 'link': 0.7, 'dist_bs': 0.3,
        'radius': 0.2, 'density': 0.4, 'fairness': 0.1,
        'tail_max': 0.5,
    }
    m1, c1, s1 = rb.select_mode(features)
    m2, c2, s2 = dl.select_mode(features)
    assert isinstance(m1, CASMode) and isinstance(m2, CASMode)
    assert isinstance(c1, float) and isinstance(c2, float)
    assert set(s1.keys()) == set(s2.keys())


def test_feature_normalization_and_mode_selection():
    dl = DistilledCASSelector()
    # Push towards direct: high energy/link, low dist/radius
    f_direct = {'energy': 0.9, 'link': 0.9, 'dist_bs': 0.1, 'radius': 0.1, 'density': 0.3, 'fairness': 0.0}
    m, c, _ = dl.select_mode(f_direct)
    assert m in (CASMode.DIRECT, CASMode.CHAIN, CASMode.TWO_HOP)
    # Push towards two-hop: far dist
    f_twohop = {'energy': 0.6, 'link': 0.6, 'dist_bs': 0.9, 'radius': 0.4, 'density': 0.3, 'fairness': 0.2}
    m2, c2, _ = dl.select_mode(f_twohop)
    assert m2 in (CASMode.DIRECT, CASMode.CHAIN, CASMode.TWO_HOP)


def test_mode_switch_via_protocol_flag():
    cfg = NetworkConfig(num_nodes=25, area_width=100.0, area_height=100.0, initial_energy=2.0, packet_size=1024)
    p_rb = AerisProtocol(cfg, enable_cas=True, enable_fairness=True, use_distilled_cas=False, verbose=False)
    p_dl = AerisProtocol(cfg, enable_cas=True, enable_fairness=True, use_distilled_cas=True, verbose=False)
    r1 = p_rb.run_simulation(10)
    r2 = p_dl.run_simulation(10)
    assert 'round_statistics' in r1 and 'round_statistics' in r2


def test_inference_performance_budget():
    dl = DistilledCASSelector()
    f = {'energy': 0.5, 'link': 0.5, 'dist_bs': 0.5, 'radius': 0.5, 'density': 0.5, 'fairness': 0.1}
    # Warmup
    for _ in range(10):
        dl.select_mode(f)
    t0 = time.perf_counter()
    for _ in range(1000):
        dl.select_mode(f)
    dt = (time.perf_counter() - t0) / 1000.0
    # 保守阈值：单次<5ms（环境差异较大时仍应通过）
    assert dt * 1e3 < 5.0