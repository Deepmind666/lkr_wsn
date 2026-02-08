#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS SOTA Integration Test
===========================
Test all new modules inspired by SOTA algorithm analysis:
1. Adaptive Reliability Manager
2. Multi-Objective Gateway Selector
3. AoI-Aware Scheduler
4. Simplified CAS Selector

Author: AERIS Research Team
Date: 2026-01-04
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import random
import numpy as np
from dataclasses import dataclass
from typing import List, Dict

# Import new modules
from adaptive_reliability import (
    AdaptiveReliabilityManager, ReliabilityLevel,
    create_default_manager, compare_profiles
)
from multi_objective_gateway import (
    MultiObjectiveGatewaySelector, MultiObjectiveGatewayConfig,
    create_multi_objective_gateway_selector
)
from aoi_scheduler import (
    AoIAwareScheduler, Packet, PacketCriticality,
    create_aoi_scheduler, create_freshness_first_scheduler
)
from simplified_cas import (
    SimplifiedCASSelector, NodeState, SimpleCASConfig,
    create_simple_cas_selector, create_aeris_enhanced_selector
)


def test_adaptive_reliability():
    """Test Adaptive Reliability Manager"""
    print("\n" + "=" * 60)
    print("TEST 1: Adaptive Reliability Manager")
    print("=" * 60)

    manager = create_default_manager()

    # Print profile comparison
    print("\nAvailable Profiles:")
    print(compare_profiles())

    # Test scenario-based selection
    test_cases = [
        {"energy": 0.9, "channel": 0.9, "pdr": 0.85, "desc": "Normal operation"},
        {"energy": 0.25, "channel": 0.8, "pdr": 0.85, "desc": "Low energy"},
        {"energy": 0.10, "channel": 0.8, "pdr": 0.80, "desc": "Critical energy"},
        {"energy": 0.7, "channel": 0.4, "pdr": 0.90, "desc": "Poor channel"},
        {"energy": 0.8, "channel": 0.9, "pdr": 0.95, "desc": "High reliability need"},
    ]

    print("\nScenario-based Profile Selection:")
    for tc in test_cases:
        profile = manager.select_profile_for_conditions(
            network_energy_ratio=tc["energy"],
            required_pdr=tc["pdr"],
            channel_quality=tc["channel"]
        )
        print(f"  {tc['desc']:25} -> {profile.name:17} (Energy factor: {profile.energy_factor:.1f}x)")

    # Verify statistics
    stats = manager.get_statistics()
    print(f"\nTotal adaptations: {stats['total_adaptations']}")

    return True


def test_multi_objective_gateway():
    """Test Multi-Objective Gateway Selector"""
    print("\n" + "=" * 60)
    print("TEST 2: Multi-Objective Gateway Selector")
    print("=" * 60)

    # Create mock CHs
    @dataclass
    class MockCH:
        id: int
        x: float
        y: float
        energy: float
        initial_energy: float
        lqi: float
        cluster_size: int

    chs = [
        MockCH(0, 20, 30, 0.9, 1.0, 0.85, 15),  # Good energy
        MockCH(1, 50, 50, 0.5, 1.0, 0.90, 20),  # Best LQI
        MockCH(2, 80, 70, 0.3, 1.0, 0.75, 25),  # Low energy
        MockCH(3, 30, 80, 0.8, 1.0, 0.80, 10),  # Good balance
        MockCH(4, 70, 20, 0.6, 1.0, 0.95, 30),  # Best LQI but large cluster
    ]

    bs_pos = (50, 100)

    print(f"\nTest CHs:")
    for ch in chs:
        print(f"  CH {ch.id}: pos=({ch.x:.0f},{ch.y:.0f}), E={ch.energy:.1f}, LQI={ch.lqi:.2f}, size={ch.cluster_size}")

    # Test with different k values
    print(f"\nGateway Selection (BS at {bs_pos}):")
    for k in [1, 2, 3]:
        selector = create_multi_objective_gateway_selector(k=k)
        selected = selector.select_gateways(chs, bs_pos, total_nodes=100)
        print(f"  k={k}: Selected gateways = {selected}")

        # Show scores for selected
        if selector.score_history:
            details = selector.score_history[-1]['details']
            for gw_id in selected:
                if gw_id in details:
                    d = details[gw_id]
                    print(f"       CH {gw_id}: dist={d['dist']:.2f}, energy={d['energy']:.2f}, "
                          f"balance={d['balance']:.2f}, coverage={d['coverage']:.2f}")

    return True


def test_aoi_scheduler():
    """Test AoI-Aware Scheduler"""
    print("\n" + "=" * 60)
    print("TEST 3: AoI-Aware Scheduler")
    print("=" * 60)

    scheduler = create_aoi_scheduler()
    current_time = 100.0

    # Create test packets with different ages and priorities
    packets = [
        Packet(1, 101, current_time - 10.0, criticality=PacketCriticality.LOW,
               source_energy_ratio=0.9),
        Packet(2, 102, current_time - 5.0, criticality=PacketCriticality.HIGH,
               source_energy_ratio=0.3),
        Packet(3, 103, current_time - 1.0, criticality=PacketCriticality.NORMAL,
               source_energy_ratio=0.7),
        Packet(4, 104, current_time - 20.0, criticality=PacketCriticality.CRITICAL,
               source_energy_ratio=0.5),
        Packet(5, 105, current_time - 2.0, criticality=PacketCriticality.NORMAL,
               source_energy_ratio=0.95),
    ]

    print("\nInput packets (before scheduling):")
    for pkt in packets:
        freshness = pkt.get_freshness_score(current_time)
        print(f"  Packet {pkt.packet_id}: age={pkt.get_age(current_time):.1f}s, "
              f"criticality={pkt.criticality.name}, freshness={freshness:.3f}")

    # Enqueue all packets
    for pkt in packets:
        scheduler.enqueue(pkt, current_time)

    # Dequeue and show order
    print("\nDequeue order (priority-based):")
    order = []
    while True:
        pkt = scheduler.dequeue(current_time)
        if pkt is None:
            break
        order.append(pkt.packet_id)
        freshness = pkt.get_freshness_score(current_time)
        print(f"  Packet {pkt.packet_id}: freshness={freshness:.3f}, "
              f"criticality={pkt.criticality.name}")

    print(f"\nFinal order: {order}")
    print("Statistics:", scheduler.get_queue_status()['statistics'])

    return True


def test_simplified_cas():
    """Test Simplified CAS Selector"""
    print("\n" + "=" * 60)
    print("TEST 4: Simplified CAS Selector")
    print("=" * 60)

    # Create test nodes
    random.seed(42)
    nodes = [
        NodeState(
            node_id=i,
            x=random.uniform(0, 100),
            y=random.uniform(0, 100),
            energy=random.uniform(0.3, 1.0),
            initial_energy=1.0,
            rounds_since_ch=random.randint(0, 30),
            avg_link_quality=random.uniform(0.6, 0.95)
        )
        for i in range(50)
    ]

    # Create density map
    density_map = {n.node_id: random.uniform(0.5, 2.0) for n in nodes}

    print(f"\nTest with {len(nodes)} nodes")

    # Test simplified selector
    selector = create_simple_cas_selector()

    print("\nRound-by-round CH selection:")
    ch_counts = []
    for round_num in range(1, 11):
        chs = selector.select_cluster_heads(nodes, round_num, density_map)
        ch_counts.append(len(chs))
        print(f"  Round {round_num}: {len(chs)} CHs selected")

    stats = selector.get_ch_statistics()
    print(f"\nStatistics:")
    print(f"  Average CHs per round: {stats['avg_ch_per_round']:.2f}")
    print(f"  Fairness index: {stats['fairness']:.3f}")

    # Compare with I-LEACH compatible selector
    from simplified_cas import create_ileach_compatible_selector
    ileach_selector = create_ileach_compatible_selector()

    # Reset node states
    for n in nodes:
        n.rounds_since_ch = 999

    print("\nI-LEACH Compatible mode:")
    for round_num in range(1, 6):
        chs = ileach_selector.select_cluster_heads(nodes, round_num)
        print(f"  Round {round_num}: {len(chs)} CHs selected")

    return True


def test_integration():
    """Test all modules working together"""
    print("\n" + "=" * 60)
    print("TEST 5: Full Integration Test")
    print("=" * 60)

    random.seed(42)
    np.random.seed(42)

    # Simulate a complete round of AERIS with all new modules

    # 1. Create nodes
    num_nodes = 50
    nodes = [
        NodeState(
            node_id=i,
            x=random.uniform(0, 100),
            y=random.uniform(0, 100),
            energy=random.uniform(0.3, 1.0),
            initial_energy=1.0,
            rounds_since_ch=random.randint(0, 30),
            avg_link_quality=random.uniform(0.6, 0.95)
        )
        for i in range(num_nodes)
    ]

    # 2. Select CHs using simplified CAS
    cas_selector = create_simple_cas_selector()
    ch_ids = cas_selector.select_cluster_heads(nodes, round_number=1)
    print(f"\n1. CH Selection: {len(ch_ids)} CHs selected from {num_nodes} nodes")

    # 3. Get network energy state
    avg_energy = sum(n.energy for n in nodes) / len(nodes)
    print(f"2. Network state: avg energy = {avg_energy:.2f}")

    # 4. Select reliability profile based on energy
    reliability_manager = create_default_manager()
    profile = reliability_manager.select_profile_for_conditions(
        network_energy_ratio=avg_energy,
        required_pdr=0.85,
        channel_quality=0.8
    )
    print(f"3. Reliability profile: {profile.name} "
          f"(ARQ={profile.max_arq_attempts}, PDR={profile.expected_pdr:.0%})")

    # 5. Create mock CHs for gateway selection
    @dataclass
    class MockCH:
        id: int
        x: float
        y: float
        energy: float
        initial_energy: float
        lqi: float
        cluster_size: int

    chs = [
        MockCH(ch_id, nodes[ch_id].x, nodes[ch_id].y,
               nodes[ch_id].energy, 1.0, nodes[ch_id].avg_link_quality, 10)
        for ch_id in ch_ids
    ]

    # 6. Select gateways using multi-objective selector
    if len(chs) >= 2:
        gateway_selector = create_multi_objective_gateway_selector(k=2)
        gateways = gateway_selector.select_gateways(chs, (50, 100), total_nodes=num_nodes)
        print(f"4. Gateway selection: {gateways} (from {len(chs)} CHs)")
    else:
        gateways = ch_ids[:1]
        print(f"4. Gateway selection: {gateways} (only 1 CH)")

    # 7. Schedule packets using AoI-aware scheduler
    scheduler = create_aoi_scheduler()
    current_time = 0.0

    # Generate packets from nodes
    for node in nodes[:10]:  # First 10 nodes generate packets
        pkt = Packet(
            packet_id=node.node_id,
            source_node_id=node.node_id,
            generation_time=current_time - random.uniform(0, 10),
            criticality=random.choice(list(PacketCriticality)),
            source_energy_ratio=node.energy
        )
        scheduler.enqueue(pkt, current_time)

    # Get scheduled order
    scheduled = []
    while True:
        pkt = scheduler.dequeue(current_time)
        if pkt is None:
            break
        scheduled.append(pkt.packet_id)

    print(f"5. Packet scheduling: {len(scheduled)} packets scheduled")
    print(f"   Order: {scheduled[:5]}{'...' if len(scheduled) > 5 else ''}")

    print("\n" + "-" * 40)
    print("Integration test PASSED!")

    return True


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("AERIS SOTA Integration Test Suite")
    print("=" * 60)

    tests = [
        ("Adaptive Reliability Manager", test_adaptive_reliability),
        ("Multi-Objective Gateway Selector", test_multi_objective_gateway),
        ("AoI-Aware Scheduler", test_aoi_scheduler),
        ("Simplified CAS Selector", test_simplified_cas),
        ("Full Integration", test_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, result, error in results:
        status = "PASS" if result else "FAIL"
        if result:
            passed += 1
        else:
            failed += 1
        print(f"  {name:40} [{status}]")
        if error:
            print(f"    Error: {error}")

    print("-" * 60)
    print(f"Total: {passed} passed, {failed} failed")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
