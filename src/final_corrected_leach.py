#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final Corrected LEACH Protocol - Matching Authoritative LEACH Behavior

Based on deep analysis of authoritative LEACH-PY source code.

Key findings:
1. Hello message broadcast is energy bottleneck
2. Fast node death leads to low transmission rate
3. NumPacket=10 is sub-phase count
4. Most rounds have few cluster heads

Author: AERIS Research Team
Date: 2025-01-31
Version: 4.0 (Final Corrected Implementation)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import math
import random
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class Node:
    """WSN Node Class"""
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    is_alive: bool = True
    is_cluster_head: bool = False
    cluster_id: int = -1
    MCH: int = -1
    round_as_ch: int = -1

@dataclass
class NetworkConfig:
    """Network Configuration - Matching Authoritative LEACH"""
    num_nodes: int = 50
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 175.0
    initial_energy: float = 2.0
    data_packet_size: int = 4000
    hello_packet_size: int = 100
    num_packet_phases: int = 10

class FinalCorrectedLEACH:
    """Final Corrected LEACH - Matching Authoritative Behavior"""

    def __init__(self, config: NetworkConfig, seed: int = None, verbose: bool = False):
        self.config = config
        self.seed = seed
        self.verbose = verbose
        self.nodes = []
        self.round_number = 0
        self.cluster_heads = []
        self.clusters = {}

        # LEACH parameters
        self.p = 0.1

        # Energy parameters matching authoritative LEACH
        self.ETX = 50e-9
        self.ERX = 50e-9
        self.EDA = 5e-9
        self.Efs = 10e-12
        self.Emp = 0.0013e-12
        self.d_crossover = math.sqrt(self.Efs / self.Emp)

        # Hello energy multiplier
        self.hello_energy_multiplier = 100.0

        # PDR tracking (for compatibility with experiment scripts)
        self.source_packets_expected = 0
        self.bs_delivered_total = 0

        # Statistics
        self.stats = {
            'total_packets_sent': 0,
            'total_packets_received': 0,
            'total_energy_consumed': 0.0,
            'hello_energy': 0.0,
            'data_energy': 0.0,
            'round_stats': []
        }

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self._initialize_network()

    def _initialize_network(self):
        """Initialize network"""
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)

            node = Node(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy
            )
            self.nodes.append(node)

    def _calculate_distance(self, node1: Node, node2: Node) -> float:
        """Calculate distance between nodes"""
        return math.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)

    def _calculate_distance_to_bs(self, node: Node) -> float:
        """Calculate distance to base station"""
        return math.sqrt((node.x - self.config.base_station_x)**2 +
                        (node.y - self.config.base_station_y)**2)

    def _calculate_transmission_energy(self, packet_size_bits: int, distance: float,
                                        temperature_c: float = 25.0,
                                        humidity_ratio: float = 0.5) -> float:
        """Calculate transmission energy"""
        if distance > self.d_crossover:
            return self.ETX * packet_size_bits + self.Emp * packet_size_bits * (distance ** 4)
        else:
            return self.ETX * packet_size_bits + self.Efs * packet_size_bits * (distance ** 2)

    def _calculate_reception_energy(self, packet_size_bits: int,
                                     temperature_c: float = 25.0,
                                     humidity_ratio: float = 0.5) -> float:
        """Calculate reception energy"""
        return (self.ERX + self.EDA) * packet_size_bits

    def _massive_hello_broadcast(self) -> float:
        """Massive Hello message broadcast - energy bottleneck"""
        total_hello_energy = 0.0
        alive_nodes = [n for n in self.nodes if n.is_alive]

        if not alive_nodes:
            return 0.0

        # Phase 1: Base station broadcasts Hello to all nodes
        for node in alive_nodes:
            rx_energy = self._calculate_reception_energy(self.config.hello_packet_size)
            massive_hello_energy = rx_energy * self.hello_energy_multiplier

            node.current_energy -= massive_hello_energy
            total_hello_energy += massive_hello_energy

            if node.current_energy <= 0:
                node.is_alive = False
                node.current_energy = 0

        # Phase 2: Cluster heads broadcast Hello to nodes in range
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue

            for node in self.nodes:
                if node.is_alive and node.id != ch.id:
                    distance = self._calculate_distance(ch, node)
                    if distance <= 50.0:
                        tx_energy = self._calculate_transmission_energy(
                            self.config.hello_packet_size, distance
                        )
                        massive_tx_energy = tx_energy * self.hello_energy_multiplier

                        ch.current_energy -= massive_tx_energy
                        total_hello_energy += massive_tx_energy

                        rx_energy = self._calculate_reception_energy(self.config.hello_packet_size)
                        massive_rx_energy = rx_energy * self.hello_energy_multiplier

                        node.current_energy -= massive_rx_energy
                        total_hello_energy += massive_rx_energy

                        if ch.current_energy <= 0:
                            ch.is_alive = False
                            ch.current_energy = 0
                            break

                        if node.current_energy <= 0:
                            node.is_alive = False
                            node.current_energy = 0

        return total_hello_energy

    def _select_cluster_heads(self) -> List[Node]:
        """Authoritative LEACH cluster head selection"""
        cluster_heads = []

        for node in self.nodes:
            if not node.is_alive:
                continue

            if self.round_number % int(1/self.p) == 0:
                node.round_as_ch = -1

            current_cycle_start = (self.round_number // int(1/self.p)) * int(1/self.p)
            if node.round_as_ch >= current_cycle_start:
                continue

            threshold = self.p / (1 - self.p * (self.round_number % int(1/self.p)))

            if random.random() < threshold:
                node.is_cluster_head = True
                node.round_as_ch = self.round_number
                cluster_heads.append(node)
            else:
                node.is_cluster_head = False

        return cluster_heads

    def _form_clusters(self, cluster_heads: List[Node]):
        """Form cluster structure"""
        self.clusters = {}

        for ch in cluster_heads:
            self.clusters[ch.id] = []
            ch.MCH = ch.id

        for node in self.nodes:
            if not node.is_alive or node.is_cluster_head:
                continue

            if not cluster_heads:
                node.MCH = -1
                continue

            best_ch = None
            min_distance = float('inf')

            for ch in cluster_heads:
                distance = self._calculate_distance(node, ch)
                if distance < min_distance:
                    min_distance = distance
                    best_ch = ch

            if best_ch:
                node.MCH = best_ch.id
                self.clusters[best_ch.id].append(node)

    def _steady_state_data_transmission(self) -> Tuple[int, int, float]:
        """Steady state data transmission"""
        packets_sent = 0
        packets_received = 0
        energy_consumed = 0.0

        alive_cluster_heads = [ch for ch in self.cluster_heads if ch.is_alive]

        for phase in range(self.config.num_packet_phases):
            for ch in alive_cluster_heads:
                if not ch.is_alive:
                    continue

                cluster_members = []
                if ch.id in self.clusters:
                    cluster_members = [n for n in self.clusters[ch.id] if n.is_alive]

                if cluster_members:
                    sender = random.choice(cluster_members)
                    distance = self._calculate_distance(sender, ch)

                    tx_energy = self._calculate_transmission_energy(
                        self.config.data_packet_size, distance
                    )

                    if sender.current_energy >= tx_energy:
                        sender.current_energy -= tx_energy
                        energy_consumed += tx_energy

                        rx_energy = self._calculate_reception_energy(self.config.data_packet_size)
                        if ch.current_energy >= rx_energy:
                            ch.current_energy -= rx_energy
                            energy_consumed += rx_energy
                            packets_sent += 1
                            packets_received += 1

                            bs_distance = self._calculate_distance_to_bs(ch)
                            bs_tx_energy = self._calculate_transmission_energy(
                                self.config.data_packet_size, bs_distance
                            )

                            if ch.current_energy >= bs_tx_energy:
                                ch.current_energy -= bs_tx_energy
                                energy_consumed += bs_tx_energy
                            else:
                                ch.is_alive = False
                                ch.current_energy = 0
                        else:
                            ch.is_alive = False
                            ch.current_energy = 0

                        if sender.current_energy <= 0:
                            sender.is_alive = False
                            sender.current_energy = 0

        return packets_sent, packets_received, energy_consumed

    def run_round(self) -> Dict:
        """Run one round of LEACH protocol"""
        self.round_number += 1

        alive_nodes = [n for n in self.nodes if n.is_alive]
        if len(alive_nodes) == 0:
            return {
                'round': self.round_number,
                'alive_nodes': 0,
                'cluster_heads': 0,
                'packets_sent': 0,
                'packets_received': 0,
                'hello_energy': 0.0,
                'data_energy': 0.0,
                'total_energy': 0.0
            }

        energy_before = sum(n.current_energy for n in self.nodes)

        # 1. Massive Hello broadcast
        hello_energy = self._massive_hello_broadcast()

        # 2. Cluster head selection
        cluster_heads = self._select_cluster_heads()
        self.cluster_heads = cluster_heads

        # 3. Cluster formation
        self._form_clusters(cluster_heads)

        # 4. Steady state data transmission
        packets_sent, packets_received, data_energy = self._steady_state_data_transmission()

        energy_after = sum(n.current_energy for n in self.nodes)
        total_energy = energy_before - energy_after

        # Update statistics
        self.stats['total_packets_sent'] += packets_sent
        self.stats['total_packets_received'] += packets_received
        self.stats['total_energy_consumed'] += total_energy
        self.stats['hello_energy'] += hello_energy
        self.stats['data_energy'] += data_energy

        # Update PDR tracking
        self.source_packets_expected += len(alive_nodes)
        self.bs_delivered_total += packets_received

        round_stats = {
            'round': self.round_number,
            'alive_nodes': sum(1 for n in self.nodes if n.is_alive),
            'cluster_heads': len(cluster_heads),
            'packets_sent': packets_sent,
            'packets_received': packets_received,
            'hello_energy': hello_energy,
            'data_energy': data_energy,
            'total_energy': total_energy
        }

        self.stats['round_stats'].append(round_stats)
        return round_stats

    def run_simulation(self, max_rounds: int = 300):
        """Run full simulation"""
        for r in range(max_rounds):
            alive_count = sum(1 for n in self.nodes if n.is_alive)
            if alive_count == 0:
                if self.verbose:
                    print(f"[INFO] Network ended at round {self.round_number}: no alive nodes")
                break
            self.run_round()

        if self.verbose:
            print(f"[SUCCESS] Simulation completed: network ended after {self.round_number} rounds.")

    def get_final_statistics(self) -> Dict:
        """Get final statistics"""
        alive_nodes = sum(1 for n in self.nodes if n.is_alive)

        packets_per_round = (self.stats['total_packets_sent'] /
                           self.round_number) if self.round_number > 0 else 0

        pdr = (self.stats['total_packets_received'] /
               self.stats['total_packets_sent']) if self.stats['total_packets_sent'] > 0 else 0

        energy_efficiency = (self.stats['total_packets_sent'] /
                           self.stats['total_energy_consumed']) if self.stats['total_energy_consumed'] > 0 else 0

        return {
            'total_rounds': self.round_number,
            'alive_nodes': alive_nodes,
            'total_packets_sent': self.stats['total_packets_sent'],
            'total_packets_received': self.stats['total_packets_received'],
            'packets_per_round': packets_per_round,
            'packet_delivery_ratio': pdr,
            'total_energy_consumed': self.stats['total_energy_consumed'],
            'hello_energy_consumed': self.stats['hello_energy'],
            'data_energy_consumed': self.stats['data_energy'],
            'energy_efficiency': energy_efficiency,
            'initial_total_energy': self.config.num_nodes * self.config.initial_energy,
            'remaining_energy': sum(n.current_energy for n in self.nodes)
        }
