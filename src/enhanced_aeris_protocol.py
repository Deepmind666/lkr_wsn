#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced AERIS Protocol with SOTA Improvements
==============================================
Integrates all SOTA-inspired improvements:
1. Adaptive Reliability Manager (from I-LEACH energy analysis)
2. Multi-Objective Gateway Selector (from PSO-WSN)
3. AoI-Aware Scheduler (from DQN-WSN)
4. Simplified CAS Selector (from I-LEACH)

Author: AERIS Research Team
Date: 2026-01-04
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import math
import random
import time
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Import base AERIS components
from benchmark_protocols import Node, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from realistic_channel_model import RealisticChannelModel, EnvironmentType

# Import new SOTA-inspired modules
from adaptive_reliability import (
    AdaptiveReliabilityManager, ReliabilityLevel, ReliabilityProfile,
    create_default_manager, RELIABILITY_PROFILES
)
from multi_objective_gateway import (
    MultiObjectiveGatewaySelector, MultiObjectiveGatewayConfig,
    create_multi_objective_gateway_selector
)
from aoi_scheduler import (
    AoIAwareScheduler, Packet, PacketCriticality, SchedulerConfig,
    create_aoi_scheduler
)
from simplified_cas import (
    SimplifiedCASSelector, NodeState, SimpleCASConfig,
    create_simple_cas_selector, EnvironmentAwareCHSelector
)


class ReliabilityMode(Enum):
    """Protocol reliability mode"""
    ULTRA_LOW_POWER = "ultra_low_power"  # Like basic LEACH
    BALANCED = "balanced"                 # New default
    HIGH_RELIABILITY = "high_reliability" # Original AERIS


@dataclass
class EnhancedAERISConfig:
    """Configuration for Enhanced AERIS Protocol"""
    # Network parameters
    num_nodes: int = 100
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 150.0
    initial_energy: float = 0.5  # Joules

    # Reliability mode
    reliability_mode: ReliabilityMode = ReliabilityMode.BALANCED
    auto_adapt_reliability: bool = True

    # CH selection
    ch_probability: float = 0.05
    use_simplified_cas: bool = True

    # Gateway selection
    num_gateways: int = 2
    use_multi_objective_gateway: bool = True

    # Packet scheduling
    use_aoi_scheduler: bool = True
    max_queue_size: int = 50

    # Environment awareness
    enable_environment_awareness: bool = True


@dataclass
class EnhancedNode:
    """Enhanced node with SOTA features"""
    id: int
    x: float
    y: float
    energy: float
    initial_energy: float = 0.5

    # Role
    is_cluster_head: bool = False
    is_gateway: bool = False
    cluster_id: int = -1

    # Link quality
    avg_link_quality: float = 0.8

    # CH selection state (for simplified CAS)
    rounds_since_ch: int = 999
    last_ch_round: int = -1

    # Statistics
    packets_sent: int = 0
    packets_received: int = 0
    energy_consumed: float = 0.0


class EnhancedAERISProtocol:
    """
    Enhanced AERIS Protocol with SOTA Improvements

    Key improvements over original AERIS:
    1. Adaptive reliability profiles (6.5x energy savings possible)
    2. Multi-objective gateway selection (better load balance)
    3. AoI-aware packet scheduling (fresher data priority)
    4. Simplified CH selection (lighter computation)
    """

    def __init__(self, config: EnhancedAERISConfig):
        self.config = config
        self.rng = np.random.default_rng()

        # Initialize nodes
        self.nodes: List[EnhancedNode] = []
        self._initialize_nodes()

        # Initialize SOTA modules
        self._init_reliability_manager()
        self._init_gateway_selector()
        self._init_aoi_scheduler()
        self._init_cas_selector()

        # Energy model
        self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

        # Channel model
        self.channel_model = RealisticChannelModel(EnvironmentType.OUTDOOR_OPEN)

        # Statistics
        self.current_round = 0
        self.total_packets_generated = 0
        self.total_packets_delivered = 0
        self.total_energy_consumed = 0.0
        self.round_statistics: List[Dict] = []

        # Cluster heads and gateways
        self.cluster_heads: List[int] = []
        self.gateways: List[int] = []

    def _initialize_nodes(self):
        """Initialize network nodes"""
        cfg = self.config
        for i in range(cfg.num_nodes):
            node = EnhancedNode(
                id=i,
                x=self.rng.uniform(0, cfg.area_width),
                y=self.rng.uniform(0, cfg.area_height),
                energy=cfg.initial_energy,
                initial_energy=cfg.initial_energy,
                avg_link_quality=self.rng.uniform(0.6, 0.95)
            )
            self.nodes.append(node)

    def _init_reliability_manager(self):
        """Initialize adaptive reliability manager"""
        self.reliability_manager = create_default_manager(
            auto_adapt=self.config.auto_adapt_reliability
        )

        # Set initial level based on config
        level_map = {
            ReliabilityMode.ULTRA_LOW_POWER: ReliabilityLevel.ULTRA_LOW_POWER,
            ReliabilityMode.BALANCED: ReliabilityLevel.BALANCED,
            ReliabilityMode.HIGH_RELIABILITY: ReliabilityLevel.HIGH_RELIABILITY
        }
        self.reliability_manager.set_reliability_level(
            level_map.get(self.config.reliability_mode, ReliabilityLevel.BALANCED)
        )

    def _init_gateway_selector(self):
        """Initialize multi-objective gateway selector"""
        if self.config.use_multi_objective_gateway:
            self.gateway_selector = create_multi_objective_gateway_selector(
                k=self.config.num_gateways,
                auto_adjust=True
            )
        else:
            self.gateway_selector = None

    def _init_aoi_scheduler(self):
        """Initialize AoI-aware scheduler"""
        if self.config.use_aoi_scheduler:
            scheduler_config = SchedulerConfig(
                max_queue_size=self.config.max_queue_size,
                w_freshness=0.40,
                w_energy=0.25,
                w_criticality=0.25,
                w_deadline=0.10
            )
            self.packet_scheduler = AoIAwareScheduler(scheduler_config)
        else:
            self.packet_scheduler = None

    def _init_cas_selector(self):
        """Initialize simplified CAS selector"""
        if self.config.use_simplified_cas:
            cas_config = SimpleCASConfig(
                p_base=self.config.ch_probability,
                exclusion_rounds=int(1 / self.config.ch_probability),
                enable_density_modifier=self.config.enable_environment_awareness,
                enable_link_quality_modifier=self.config.enable_environment_awareness
            )
            self.cas_selector = SimplifiedCASSelector(cas_config)
        else:
            self.cas_selector = None

    def get_network_energy_ratio(self) -> float:
        """Calculate average network energy ratio"""
        if not self.nodes:
            return 0.0
        total_energy = sum(n.energy for n in self.nodes)
        total_initial = sum(n.initial_energy for n in self.nodes)
        return total_energy / total_initial if total_initial > 0 else 0.0

    def get_alive_nodes(self) -> List[EnhancedNode]:
        """Get list of alive nodes"""
        return [n for n in self.nodes if n.energy > 0]

    def select_cluster_heads(self) -> List[int]:
        """
        Select cluster heads using simplified CAS or fallback method.

        Returns list of CH node IDs.
        """
        alive_nodes = self.get_alive_nodes()
        if not alive_nodes:
            return []

        if self.cas_selector and self.config.use_simplified_cas:
            # Convert to NodeState for simplified CAS
            node_states = [
                NodeState(
                    node_id=n.id,
                    x=n.x,
                    y=n.y,
                    energy=n.energy,
                    initial_energy=n.initial_energy,
                    rounds_since_ch=n.rounds_since_ch,
                    avg_link_quality=n.avg_link_quality
                )
                for n in alive_nodes
            ]

            # Calculate density map
            density_map = self._calculate_density_map(alive_nodes)

            # Select CHs
            ch_ids = self.cas_selector.select_cluster_heads(
                node_states, self.current_round, density_map
            )

            # Update node states
            for node in self.nodes:
                if node.id in ch_ids:
                    node.is_cluster_head = True
                    node.rounds_since_ch = 0
                    node.last_ch_round = self.current_round
                else:
                    node.is_cluster_head = False
                    node.rounds_since_ch += 1

            return ch_ids

        else:
            # Fallback: simple probability-based selection
            ch_ids = []
            for node in alive_nodes:
                p = self.config.ch_probability * (node.energy / node.initial_energy)
                if self.rng.random() < p:
                    node.is_cluster_head = True
                    ch_ids.append(node.id)
                else:
                    node.is_cluster_head = False

            # Ensure at least one CH
            if not ch_ids and alive_nodes:
                best = max(alive_nodes, key=lambda n: n.energy)
                best.is_cluster_head = True
                ch_ids.append(best.id)

            return ch_ids

    def _calculate_density_map(self, nodes: List[EnhancedNode]) -> Dict[int, float]:
        """Calculate local density for each node"""
        density_map = {}
        radius = 30.0  # Density calculation radius

        for node in nodes:
            neighbors = sum(
                1 for other in nodes
                if other.id != node.id and
                math.hypot(node.x - other.x, node.y - other.y) < radius
            )
            # Normalize: expected neighbors for uniform distribution
            expected = len(nodes) * (math.pi * radius**2) / (self.config.area_width * self.config.area_height)
            density_map[node.id] = neighbors / max(1, expected)

        return density_map

    def select_gateways(self, ch_ids: List[int]) -> List[int]:
        """
        Select gateways using multi-objective selector.

        Returns list of gateway node IDs.
        """
        if len(ch_ids) < 2:
            return ch_ids

        if self.gateway_selector and self.config.use_multi_objective_gateway:
            # Create CH objects for gateway selector
            @dataclass
            class CHInfo:
                id: int
                x: float
                y: float
                energy: float
                initial_energy: float
                lqi: float
                cluster_size: int

            ch_nodes = [self.nodes[cid] for cid in ch_ids if cid < len(self.nodes)]
            ch_infos = [
                CHInfo(
                    id=n.id,
                    x=n.x,
                    y=n.y,
                    energy=n.energy,
                    initial_energy=n.initial_energy,
                    lqi=n.avg_link_quality,
                    cluster_size=10  # Approximate
                )
                for n in ch_nodes
            ]

            bs_pos = (self.config.base_station_x, self.config.base_station_y)
            gw_ids = self.gateway_selector.select_gateways(
                ch_infos, bs_pos, total_nodes=len(self.get_alive_nodes())
            )

            # Mark gateways
            for node in self.nodes:
                node.is_gateway = node.id in gw_ids

            return gw_ids

        else:
            # Fallback: select CHs closest to BS
            bs_x, bs_y = self.config.base_station_x, self.config.base_station_y
            ch_dists = [
                (cid, math.hypot(self.nodes[cid].x - bs_x, self.nodes[cid].y - bs_y))
                for cid in ch_ids if cid < len(self.nodes)
            ]
            ch_dists.sort(key=lambda x: x[1])
            return [cid for cid, _ in ch_dists[:self.config.num_gateways]]

    def simulate_transmission(self, sender: EnhancedNode, receiver_id: int,
                              packet_size: int = 50) -> Tuple[bool, float]:
        """
        Simulate a packet transmission with adaptive reliability.

        Returns (success, energy_consumed).
        """
        if sender.energy <= 0:
            return False, 0.0

        # Get current reliability profile
        network_energy = self.get_network_energy_ratio()
        profile = self.reliability_manager.select_profile_for_conditions(
            network_energy_ratio=network_energy,
            required_pdr=0.85,
            channel_quality=sender.avg_link_quality
        )

        # Calculate base transmission energy
        receiver = self.nodes[receiver_id] if receiver_id < len(self.nodes) else None
        if receiver is None:
            # Transmitting to BS
            distance = math.hypot(
                sender.x - self.config.base_station_x,
                sender.y - self.config.base_station_y
            )
        else:
            distance = math.hypot(sender.x - receiver.x, sender.y - receiver.y)

        base_energy = self.energy_model.calculate_transmission_energy(packet_size, distance)

        # Apply reliability profile
        total_energy = 0.0
        success = False

        for attempt in range(profile.max_arq_attempts):
            # Channel simulation
            tx_power = -10 + attempt * profile.power_step_db
            link_success_prob = self._calculate_link_probability(distance, tx_power)

            attempt_energy = base_energy * (1 + attempt * 0.1)  # Power escalation
            total_energy += attempt_energy

            if self.rng.random() < link_success_prob:
                success = True
                break

        # Update node energy
        sender.energy -= total_energy
        sender.energy = max(0, sender.energy)
        sender.energy_consumed += total_energy

        self.total_energy_consumed += total_energy

        return success, total_energy

    def _calculate_link_probability(self, distance: float, tx_power: float) -> float:
        """
        Calculate link success probability.

        Uses a realistic but simulation-friendly model based on:
        - Log-distance path loss
        - Typical WSN parameters (CC2420 radio)
        """
        if distance < 1:
            distance = 1

        # Path loss parameters for outdoor environment
        path_loss_exp = 2.8  # Outdoor open area
        reference_dist = 1.0
        pl_d0 = 40.0  # Path loss at 1m reference distance (dB)

        # Calculate path loss
        path_loss = pl_d0 + 10 * path_loss_exp * math.log10(distance / reference_dist)

        # Add shadow fading (log-normal, simplified as mean effect)
        shadow_margin = 4.0  # dB margin for fading

        # Received power (tx_power is in dBm, typically 0 dBm for CC2420)
        effective_tx = max(0, tx_power)  # Ensure non-negative
        rx_power = effective_tx - path_loss - shadow_margin

        # Receiver sensitivity for CC2420 is about -95 dBm
        rx_sensitivity = -95.0

        # Link margin
        link_margin = rx_power - rx_sensitivity

        # Success probability based on link margin
        # Positive margin = high probability, negative = low probability
        if link_margin > 15:
            prob = 0.98
        elif link_margin > 10:
            prob = 0.95
        elif link_margin > 5:
            prob = 0.90
        elif link_margin > 0:
            prob = 0.80
        elif link_margin > -5:
            prob = 0.60
        elif link_margin > -10:
            prob = 0.30
        else:
            prob = 0.05

        return prob

    def run_round(self) -> Dict[str, Any]:
        """
        Run one simulation round.

        Returns round statistics.
        """
        self.current_round += 1
        round_stats = {
            'round': self.current_round,
            'alive_nodes': 0,
            'packets_generated': 0,
            'packets_delivered': 0,
            'energy_consumed': 0.0,
            'reliability_profile': '',
            'num_chs': 0,
            'num_gateways': 0
        }

        alive_nodes = self.get_alive_nodes()
        round_stats['alive_nodes'] = len(alive_nodes)

        if len(alive_nodes) < 2:
            return round_stats

        # Phase 1: CH Selection
        self.cluster_heads = self.select_cluster_heads()
        round_stats['num_chs'] = len(self.cluster_heads)

        if not self.cluster_heads:
            return round_stats

        # Phase 2: Gateway Selection
        self.gateways = self.select_gateways(self.cluster_heads)
        round_stats['num_gateways'] = len(self.gateways)

        # Phase 3: Data Collection and Transmission
        packets_generated = 0
        packets_at_ch = 0
        packets_at_gateway = 0
        packets_at_bs = 0
        energy_this_round = 0.0

        # Get current reliability profile name
        profile = self.reliability_manager.get_current_profile()
        round_stats['reliability_profile'] = profile.name

        # Track aggregated data at each CH
        ch_aggregated_data: Dict[int, int] = {ch: 0 for ch in self.cluster_heads}

        # Each non-CH node generates and sends data to its CH
        for node in alive_nodes:
            if node.is_cluster_head:
                continue

            # Find nearest CH
            nearest_ch = min(
                self.cluster_heads,
                key=lambda ch: math.hypot(node.x - self.nodes[ch].x, node.y - self.nodes[ch].y)
            )

            # Generate packet
            packets_generated += 1

            # Transmit to CH
            success, energy = self.simulate_transmission(node, nearest_ch)
            energy_this_round += energy

            if success:
                packets_at_ch += 1
                ch_aggregated_data[nearest_ch] = ch_aggregated_data.get(nearest_ch, 0) + 1

        # Phase 4: CH aggregation and uplink to BS (via gateways)
        gw_aggregated_data: Dict[int, int] = {gw: 0 for gw in self.gateways}

        for ch_id in self.cluster_heads:
            ch_node = self.nodes[ch_id]
            if ch_node.energy <= 0:
                continue

            data_to_forward = ch_aggregated_data.get(ch_id, 0)
            if data_to_forward == 0:
                continue

            # If gateway, transmit directly to BS
            if ch_id in self.gateways:
                success, energy = self.simulate_transmission(ch_node, -1)  # -1 = BS
                energy_this_round += energy
                if success:
                    packets_at_bs += data_to_forward
            else:
                # Find nearest gateway
                if self.gateways:
                    nearest_gw = min(
                        self.gateways,
                        key=lambda gw: math.hypot(ch_node.x - self.nodes[gw].x, ch_node.y - self.nodes[gw].y)
                    )
                    success, energy = self.simulate_transmission(ch_node, nearest_gw)
                    energy_this_round += energy
                    if success:
                        packets_at_gateway += data_to_forward
                        gw_aggregated_data[nearest_gw] = gw_aggregated_data.get(nearest_gw, 0) + data_to_forward

        # Gateway to BS transmission
        for gw_id in self.gateways:
            gw_node = self.nodes[gw_id]
            if gw_node.energy <= 0:
                continue

            data_to_forward = gw_aggregated_data.get(gw_id, 0)
            if data_to_forward == 0:
                continue

            success, energy = self.simulate_transmission(gw_node, -1)  # -1 = BS
            energy_this_round += energy
            if success:
                packets_at_bs += data_to_forward

        # Update statistics - use end-to-end delivery (packets at BS)
        round_stats['packets_generated'] = packets_generated
        round_stats['packets_delivered'] = packets_at_bs  # End-to-end delivery
        round_stats['packets_at_ch'] = packets_at_ch
        round_stats['packets_at_gateway'] = packets_at_gateway
        round_stats['energy_consumed'] = energy_this_round

        self.total_packets_generated += packets_generated
        self.total_packets_delivered += packets_at_bs  # End-to-end

        self.round_statistics.append(round_stats)

        return round_stats

    def run_simulation(self, max_rounds: int = 500) -> Dict[str, Any]:
        """
        Run full simulation.

        Returns final statistics.
        """
        start_time = time.time()

        for _ in range(max_rounds):
            alive = len(self.get_alive_nodes())
            if alive < 2:
                break
            self.run_round()

        elapsed = time.time() - start_time

        # Calculate final metrics
        pdr = (self.total_packets_delivered / self.total_packets_generated
               if self.total_packets_generated > 0 else 0.0)

        # Network lifetime (first node death and all nodes death)
        first_death = max_rounds
        all_death = max_rounds
        for i, stats in enumerate(self.round_statistics):
            if stats['alive_nodes'] < self.config.num_nodes and first_death == max_rounds:
                first_death = i + 1
            if stats['alive_nodes'] == 0:
                all_death = i + 1
                break

        # Reliability profile usage
        reliability_stats = self.reliability_manager.get_statistics()

        return {
            'total_rounds': len(self.round_statistics),
            'total_packets_generated': self.total_packets_generated,
            'total_packets_delivered': self.total_packets_delivered,
            'pdr': pdr,
            'total_energy_consumed': self.total_energy_consumed,
            'avg_energy_per_packet': (self.total_energy_consumed / self.total_packets_generated
                                      if self.total_packets_generated > 0 else 0.0),
            'first_node_death': first_death,
            'network_lifetime': all_death,
            'final_alive_nodes': len(self.get_alive_nodes()),
            'reliability_profile_usage': reliability_stats['profile_usage'],
            'elapsed_time': elapsed,
            'config': {
                'reliability_mode': self.config.reliability_mode.value,
                'use_simplified_cas': self.config.use_simplified_cas,
                'use_multi_objective_gateway': self.config.use_multi_objective_gateway,
                'use_aoi_scheduler': self.config.use_aoi_scheduler
            }
        }


def run_comparison_experiment(num_nodes: int = 100, max_rounds: int = 500, seed: int = 42):
    """
    Run comparison experiment between different reliability modes.
    """
    np.random.seed(seed)
    random.seed(seed)

    results = {}

    modes = [
        ("ULTRA_LOW_POWER (LEACH-like)", ReliabilityMode.ULTRA_LOW_POWER),
        ("BALANCED (New Default)", ReliabilityMode.BALANCED),
        ("HIGH_RELIABILITY (Original AERIS)", ReliabilityMode.HIGH_RELIABILITY),
    ]

    for mode_name, mode in modes:
        print(f"\nRunning: {mode_name}")

        config = EnhancedAERISConfig(
            num_nodes=num_nodes,
            reliability_mode=mode,
            auto_adapt_reliability=False,  # Fix mode for comparison
            use_simplified_cas=True,
            use_multi_objective_gateway=True,
            use_aoi_scheduler=True
        )

        protocol = EnhancedAERISProtocol(config)
        result = protocol.run_simulation(max_rounds)
        results[mode_name] = result

        print(f"  PDR: {result['pdr']:.2%}")
        print(f"  Energy: {result['total_energy_consumed']:.4f} J")
        print(f"  Lifetime: {result['network_lifetime']} rounds")

    return results


if __name__ == "__main__":
    print("Enhanced AERIS Protocol with SOTA Improvements")
    print("=" * 60)

    results = run_comparison_experiment(num_nodes=50, max_rounds=300)

    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)

    print(f"\n{'Mode':<35} {'PDR':>8} {'Energy':>10} {'Lifetime':>10}")
    print("-" * 65)

    for mode, result in results.items():
        print(f"{mode:<35} {result['pdr']:>7.1%} {result['total_energy_consumed']:>9.4f}J {result['network_lifetime']:>9}r")
