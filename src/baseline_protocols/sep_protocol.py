#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEP (Stable Election Protocol) implementation.
This module provides a SEP simulation for WSN baseline comparison.

SEP extends LEACH by introducing heterogeneous nodes with different initial
energy levels, improving network lifetime and stability.

References:
Smaragdakis, G., Matta, I., & Bestavros, A. (2004).
SEP: A stable election protocol for clustered heterogeneous wireless sensor networks.
Boston University Computer Science Department.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import math
from typing import List, Tuple, Dict, Optional

# Import unified energy model
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform


class SEPNode:
    """SEP protocol sensor node with heterogeneous energy levels."""

    def __init__(self, node_id: int, x: float, y: float,
                 initial_energy: float = 2.0, is_advanced: bool = False,
                 alpha: float = 1.0):
        """
        Initialize SEP node.

        Args:
            node_id: Unique node identifier
            x, y: Node coordinates
            initial_energy: Initial energy for normal nodes
            is_advanced: Whether this is an advanced node
            alpha: Energy factor for advanced nodes (E_adv = (1+alpha)*E_normal)
        """
        self.node_id = node_id
        self.x = x
        self.y = y
        self.is_advanced = is_advanced
        self.alpha = alpha

        # Advanced nodes have (1+alpha) times more energy
        if is_advanced:
            self.initial_energy = initial_energy * (1 + alpha)
        else:
            self.initial_energy = initial_energy

        self.current_energy = self.initial_energy
        self.is_alive = True
        self.is_cluster_head = False
        self.cluster_head_id = None
        self.cluster_members = []

        # SEP specific: round counter for CH eligibility
        self.rounds_since_ch = 0

    def distance_to(self, other) -> float:
        """Compute Euclidean distance to another node or point."""
        if hasattr(other, 'x'):
            return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
        else:
            return math.sqrt((self.x - other[0])**2 + (self.y - other[1])**2)

    def consume_energy(self, energy_amount: float):
        """Consume energy and update alive status."""
        self.current_energy -= energy_amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False

    def reset_round_info(self):
        """Reset round-specific information."""
        self.is_cluster_head = False
        self.cluster_head_id = None
        self.cluster_members = []


class SEPProtocol:
    """SEP (Stable Election Protocol) simulator."""

    def __init__(self, nodes: List[SEPNode], base_station: Tuple[float, float],
                 p_opt: float = 0.1, m: float = 0.1, alpha: float = 1.0,
                 use_unified_energy_model: bool = True):
        """
        Initialize SEP protocol.

        Args:
            nodes: List of SEP nodes
            base_station: Base station coordinates (x, y)
            p_opt: Optimal cluster head probability
            m: Fraction of advanced nodes (0 to 1)
            alpha: Energy factor for advanced nodes
            use_unified_energy_model: If True, use ImprovedEnergyModel
        """
        self.nodes = nodes
        self.base_station = base_station
        self.p_opt = p_opt
        self.m = m  # fraction of advanced nodes
        self.alpha = alpha
        self.current_round = 0
        self.use_unified_energy_model = use_unified_energy_model

        # Packet size
        self.packet_size = 4000  # bits

        if use_unified_energy_model:
            self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        else:
            self.E_elec = 50e-9
            self.E_fs = 10e-12
            self.E_mp = 0.0013e-12
            self.E_DA = 5e-9
            self.d_crossover = 87
            self.energy_model = None

        # Calculate weighted probabilities
        # p_nrm = p_opt / (1 + m*alpha)
        # p_adv = p_opt * (1 + alpha) / (1 + m*alpha)
        self.p_nrm = p_opt / (1 + m * alpha)
        self.p_adv = p_opt * (1 + alpha) / (1 + m * alpha)

        # Metrics
        self.total_energy_consumed = 0.0
        self.packets_sent = 0
        self.packets_received = 0
        self.total_source_packets = 0
        self.total_bs_delivered = 0
        self.dead_nodes = 0
        self.network_lifetime = 0
        self.energy_consumption_per_round = []
        self.alive_nodes_per_round = []

    def calculate_transmission_energy(self, distance: float, packet_size: int,
                                      temperature_c: float = 25.0,
                                      humidity_ratio: float = 0.5) -> float:
        """Calculate transmission energy."""
        if self.use_unified_energy_model:
            return self.energy_model.calculate_transmission_energy(
                data_size_bits=packet_size,
                distance=distance,
                tx_power_dbm=0.0,
                temperature_c=temperature_c,
                humidity_ratio=humidity_ratio
            )
        else:
            if distance < self.d_crossover:
                return self.E_elec * packet_size + self.E_fs * packet_size * (distance ** 2)
            else:
                return self.E_elec * packet_size + self.E_mp * packet_size * (distance ** 4)

    def calculate_reception_energy(self, packet_size: int,
                                   temperature_c: float = 25.0,
                                   humidity_ratio: float = 0.5) -> float:
        """Calculate reception energy."""
        if self.use_unified_energy_model:
            return self.energy_model.calculate_reception_energy(
                data_size_bits=packet_size,
                temperature_c=temperature_c,
                humidity_ratio=humidity_ratio
            )
        else:
            return self.E_elec * packet_size

    def cluster_head_selection(self) -> List[SEPNode]:
        """Select cluster heads using SEP weighted election."""
        cluster_heads = []

        # Reset round info
        for node in self.nodes:
            if node.is_alive:
                node.reset_round_info()

        alive_normal = [n for n in self.nodes if n.is_alive and not n.is_advanced]
        alive_advanced = [n for n in self.nodes if n.is_alive and n.is_advanced]

        # Calculate T(s) threshold for normal and advanced nodes
        # T_nrm(s) = p_nrm / (1 - p_nrm * (r mod 1/p_nrm))
        # T_adv(s) = p_adv / (1 - p_adv * (r mod 1/p_adv))

        # Threshold for normal nodes
        if self.p_nrm > 0:
            r_nrm = self.current_round % int(1 / self.p_nrm) if self.p_nrm < 1 else 0
            t_nrm = self.p_nrm / (1 - self.p_nrm * r_nrm) if (1 - self.p_nrm * r_nrm) > 0 else 1
        else:
            t_nrm = 0

        # Threshold for advanced nodes
        if self.p_adv > 0:
            r_adv = self.current_round % int(1 / self.p_adv) if self.p_adv < 1 else 0
            t_adv = self.p_adv / (1 - self.p_adv * r_adv) if (1 - self.p_adv * r_adv) > 0 else 1
        else:
            t_adv = 0

        # Select cluster heads from normal nodes
        for node in alive_normal:
            # Energy-weighted threshold
            energy_ratio = node.current_energy / node.initial_energy
            threshold = t_nrm * energy_ratio

            if np.random.random() < threshold:
                node.is_cluster_head = True
                cluster_heads.append(node)

        # Select cluster heads from advanced nodes
        for node in alive_advanced:
            # Energy-weighted threshold
            energy_ratio = node.current_energy / node.initial_energy
            threshold = t_adv * energy_ratio

            if np.random.random() < threshold:
                node.is_cluster_head = True
                cluster_heads.append(node)

        # If no CH selected, choose highest energy node
        if not cluster_heads:
            alive = [n for n in self.nodes if n.is_alive]
            if alive:
                best_node = max(alive, key=lambda n: n.current_energy)
                best_node.is_cluster_head = True
                cluster_heads.append(best_node)

        # Assign non-CH nodes to clusters
        for node in self.nodes:
            if not node.is_alive or node.is_cluster_head:
                continue

            # Find closest CH
            min_dist = float('inf')
            closest_ch = None

            for ch in cluster_heads:
                dist = node.distance_to(ch)
                if dist < min_dist:
                    min_dist = dist
                    closest_ch = ch

            if closest_ch:
                node.cluster_head_id = closest_ch.node_id
                closest_ch.cluster_members.append(node)

        return cluster_heads

    def data_transmission_phase(self, cluster_heads: List[SEPNode]):
        """Simulate data transmission phase."""
        round_energy = 0.0

        # 1. Intra-cluster communication
        for ch in cluster_heads:
            if not ch.is_alive:
                continue

            for member in ch.cluster_members:
                if not member.is_alive:
                    continue

                distance = member.distance_to(ch)
                tx_energy = self.calculate_transmission_energy(distance, self.packet_size)
                rx_energy = self.calculate_reception_energy(self.packet_size)

                member.consume_energy(tx_energy)
                round_energy += tx_energy

                ch.consume_energy(rx_energy)
                round_energy += rx_energy

                self.packets_sent += 1
                if ch.is_alive:
                    self.packets_received += 1

        # 2. CH to BS transmission
        for ch in cluster_heads:
            if not ch.is_alive:
                continue

            # Data aggregation
            if self.use_unified_energy_model:
                agg_energy = self.energy_model.calculate_processing_energy(
                    self.packet_size * len(ch.cluster_members))
            else:
                agg_energy = self.E_DA * self.packet_size * len(ch.cluster_members)
            ch.consume_energy(agg_energy)
            round_energy += agg_energy

            # Transmit to BS
            bs_distance = ch.distance_to(self.base_station)
            tx_energy = self.calculate_transmission_energy(bs_distance, self.packet_size)
            ch.consume_energy(tx_energy)
            round_energy += tx_energy

            self.packets_sent += 1
            delivered = 1 + len([m for m in ch.cluster_members if m.is_alive])
            self.total_bs_delivered += delivered
            self.total_source_packets += delivered

        self.total_energy_consumed += round_energy
        self.energy_consumption_per_round.append(round_energy)

    def run_round(self) -> bool:
        """Run one SEP protocol round."""
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return False

        self.current_round += 1

        # 1. CH selection
        cluster_heads = self.cluster_head_selection()

        # 2. Data transmission
        self.data_transmission_phase(cluster_heads)

        # 3. Update metrics
        current_alive = len(alive_nodes)
        current_dead = len(self.nodes) - current_alive

        if current_dead > self.dead_nodes:
            self.dead_nodes = current_dead
            if self.network_lifetime == 0 and current_dead > 0:
                self.network_lifetime = self.current_round

        self.alive_nodes_per_round.append(current_alive)

        return True

    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """Run complete SEP simulation."""
        for round_num in range(max_rounds):
            if not self.run_round():
                break

        return {
            'protocol_name': 'SEP',
            'total_rounds': self.current_round,
            'network_lifetime': self.network_lifetime if self.network_lifetime > 0 else self.current_round,
            'total_energy_consumed': self.total_energy_consumed,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'packet_delivery_ratio': self.packets_received / max(self.packets_sent, 1),
            'packet_delivery_ratio_end2end': self.total_bs_delivered / max(self.total_source_packets, 1),
            'bs_delivered': self.total_bs_delivered,
            'source_packets': self.total_source_packets,
            'dead_nodes': self.dead_nodes,
            'alive_nodes': len(self.nodes) - self.dead_nodes,
            'energy_consumption_per_round': self.energy_consumption_per_round,
            'alive_nodes_per_round': self.alive_nodes_per_round
        }
