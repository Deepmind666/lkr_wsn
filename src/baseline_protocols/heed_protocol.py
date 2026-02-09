#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HEED (Hybrid Energy-Efficient Distributed clustering) protocol implementation.
This module provides a basic HEED simulation for WSN baseline comparison.

**MODIFIED 2025-11-04**: Now uses ImprovedEnergyModel for unified comparison with AERIS.

References:
Younis, O., & Fahmy, S. (2004).
HEED: a hybrid, energy-efficient, distributed clustering approach for ad hoc sensor networks.
IEEE Transactions on Mobile Computing, 3(4), 366-379.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import math
import random
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt

# Import unified energy model
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

class HEEDNode:
    """HEED protocol sensor node."""
    
    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True
        self.is_cluster_head = False
        self.cluster_head_id = None
        self.cluster_members = []
        
        # HEED specific parameters
        self.ch_probability = 0.0
        self.communication_cost = 0.0
        self.neighbors = []
        self.cluster_radius = 50.0  # cluster radius (m)
        
    def distance_to(self, other_node) -> float:
        """Compute Euclidean distance to another node."""
        return math.sqrt((self.x - other_node.x)**2 + (self.y - other_node.y)**2)
    
    def consume_energy(self, energy_amount: float):
        """Consume energy and update alive status."""
        self.current_energy -= energy_amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False
    
    def reset_cluster_info(self):
        """Reset cluster-related information."""
        self.is_cluster_head = False
        self.cluster_head_id = None
        self.cluster_members = []
        self.ch_probability = 0.0
        self.communication_cost = 0.0

class HEEDProtocol:
    """HEED protocol simulator."""

    def __init__(self, nodes: List[HEEDNode], base_station: Tuple[float, float],
                 c_prob: float = 0.05, cluster_radius: float = 50.0,
                 use_unified_energy_model: bool = True, tx_power_dbm: float = 10.0,
                 channel_model=None):
        """Initialize HEED protocol.

        Args:
            nodes: List of HEED nodes
            base_station: Base station coordinates (x, y)
            c_prob: Initial cluster head probability
            cluster_radius: Cluster radius (meters)
            use_unified_energy_model: If True, use ImprovedEnergyModel (CC2420 parameters).
                                     If False, use legacy simplified parameters.
            tx_power_dbm: Transmission power in dBm (default 10.0)
            channel_model: Optional RealisticChannelModel for PDR calculation
        """
        self.nodes = nodes
        self.base_station = base_station
        self.c_prob = c_prob
        self.cluster_radius = cluster_radius
        self.current_round = 0
        self.use_unified_energy_model = use_unified_energy_model
        self.tx_power_dbm = tx_power_dbm
        self.channel_model = channel_model

        # Packet size
        self.packet_size = 8192  # packet size (bits) - 统一为1024 bytes

        if use_unified_energy_model:
            # Use unified real hardware model (CC2420 TelosB)
            self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
            print(f"[HEED] Using unified energy model (CC2420 TelosB, 208.8 nJ/bit)")
        else:
            # Legacy simplified parameters (for backward compatibility)
            self.E_elec = 50e-9  # electronics energy (J/bit)
            self.E_fs = 10e-12   # free-space model (J/bit/m^2)
            self.E_mp = 0.0013e-12  # multi-path model (J/bit/m^4)
            self.E_DA = 5e-9     # data aggregation energy (J/bit)
            self.d_crossover = 87  # distance threshold (m)
            self.energy_model = None
            print(f"[HEED] Using legacy energy model (50 nJ/bit)")
        
        # Metrics
        self.total_energy_consumed = 0.0
        self.packets_sent = 0
        self.packets_received = 0
        self.total_source_packets = 0  # 实际尝试发送的包数 (attempted)
        self.source_packets_expected = 0  # 期望包数 = 每轮存活节点数累计
        self.total_bs_delivered = 0
        self.dead_nodes = 0
        self.network_lifetime = 0
        self.energy_consumption_per_round = []
        self.alive_nodes_per_round = []
        self._all_hop_counts = []

        # Initialize neighbor relationships
        self.initialize_neighbors()
        
        print(f"[OK] HEED initialization complete")
        print(f"   Nodes: {len(self.nodes)}")
        print(f"   Base station: {self.base_station}")
        print(f"   Cluster radius: {self.cluster_radius} m")
        print(f"   Initial CH probability: {self.c_prob}")
    
    def initialize_neighbors(self):
        """Initialize neighbor list for each node within cluster radius."""
        for node in self.nodes:
            node.neighbors = []
            for other_node in self.nodes:
                if node.node_id != other_node.node_id:
                    distance = node.distance_to(other_node)
                    if distance <= self.cluster_radius:
                        node.neighbors.append(other_node)
    
    def calculate_transmission_energy(self, distance: float, packet_size: int,
                                     temperature_c: float = 25.0, humidity_ratio: float = 0.5) -> float:
        """Compute transmission energy per packet based on distance.

        Uses unified energy model if enabled, otherwise legacy simplified model.
        """
        if self.use_unified_energy_model:
            # Use ImprovedEnergyModel (real CC2420 parameters)
            return self.energy_model.calculate_transmission_energy(
                data_size_bits=packet_size,
                distance=distance,
                tx_power_dbm=self.tx_power_dbm,
                temperature_c=temperature_c,
                humidity_ratio=humidity_ratio
            )
        else:
            # Legacy simplified model
            if distance < self.d_crossover:
                return self.E_elec * packet_size + self.E_fs * packet_size * (distance ** 2)
            else:
                return self.E_elec * packet_size + self.E_mp * packet_size * (distance ** 4)

    def calculate_reception_energy(self, packet_size: int,
                                   temperature_c: float = 25.0, humidity_ratio: float = 0.5) -> float:
        """Compute reception energy per packet.

        Uses unified energy model if enabled, otherwise legacy simplified model.
        """
        if self.use_unified_energy_model:
            # Use ImprovedEnergyModel (real CC2420 parameters)
            return self.energy_model.calculate_reception_energy(
                data_size_bits=packet_size,
                temperature_c=temperature_c,
                humidity_ratio=humidity_ratio
            )
        else:
            # Legacy simplified model
            return self.E_elec * packet_size
    
    def calculate_communication_cost(self, node: HEEDNode) -> float:
        """Compute communication cost as average distance to alive neighbors."""
        if not node.neighbors:
            return float('inf')
        
        total_distance = 0.0
        alive_neighbors = [n for n in node.neighbors if n.is_alive]
        
        if not alive_neighbors:
            return float('inf')
        
        for neighbor in alive_neighbors:
            total_distance += node.distance_to(neighbor)
        
        return total_distance / len(alive_neighbors)
    
    def calculate_ch_probability(self, node: HEEDNode) -> float:
        """Compute probability that a node becomes a cluster head."""
        if node.current_energy <= 0:
            return 0.0
        
        energy_ratio = node.current_energy / node.initial_energy
        return self.c_prob * energy_ratio
    
    def cluster_head_selection(self) -> List[HEEDNode]:
        """Select cluster heads using HEED heuristic."""
        cluster_heads = []
        
        # Reset state for all nodes
        for node in self.nodes:
            node.reset_cluster_info()
        
        # Compute CH probability and communication cost
        for node in self.nodes:
            if not node.is_alive:
                continue
            
            node.ch_probability = self.calculate_ch_probability(node)
            node.communication_cost = self.calculate_communication_cost(node)
        
        # Iterative selection
        max_iterations = 5
        for iteration in range(max_iterations):
            new_cluster_heads = []

            for node in self.nodes:
                # 跳过：死亡节点、已是CH、已分配到某CH
                if not node.is_alive or node.is_cluster_head or node.cluster_head_id is not None:
                    continue
                
                should_be_ch = False
                
                if iteration == 0:
                    # First round: probabilistic selection
                    if random.random() < node.ch_probability:
                        should_be_ch = True
                else:
                    # Subsequent rounds: pick if no better candidate among neighbors
                    better_candidates = []
                    for neighbor in node.neighbors:
                        if (neighbor.is_alive and 
                            neighbor.ch_probability > node.ch_probability and
                            neighbor.communication_cost < node.communication_cost):
                            better_candidates.append(neighbor)
                    
                    if not better_candidates:
                        should_be_ch = True
                
                if should_be_ch:
                    node.is_cluster_head = True
                    new_cluster_heads.append(node)
            
            cluster_heads.extend(new_cluster_heads)
            
            # Assign members to new cluster heads
            for ch in new_cluster_heads:
                for neighbor in ch.neighbors:
                    if (neighbor.is_alive and 
                        not neighbor.is_cluster_head and 
                        neighbor.cluster_head_id is None):
                        neighbor.cluster_head_id = ch.node_id
                        ch.cluster_members.append(neighbor)
        
        # Ensure all alive nodes are associated with a cluster head
        for node in self.nodes:
            if (node.is_alive and 
                not node.is_cluster_head and 
                node.cluster_head_id is None):
                # Find closest CH
                min_distance = float('inf')
                closest_ch = None
                
                for ch in cluster_heads:
                    distance = node.distance_to(ch)
                    if distance < min_distance:
                        min_distance = distance
                        closest_ch = ch
                
                if closest_ch:
                    node.cluster_head_id = closest_ch.node_id
                    closest_ch.cluster_members.append(node)
                else:
                    # If no CH exists, make this node a CH
                    node.is_cluster_head = True
                    cluster_heads.append(node)
        
        return cluster_heads
    
    def data_transmission_phase(self, cluster_heads: List[HEEDNode]):
        """Simulate intra-cluster transmissions and CH-to-BS transmissions."""
        round_energy_consumption = 0.0
        if not hasattr(self, '_all_hop_counts'):
            self._all_hop_counts = []
        
        # 1. Intra-cluster data transmission
        for ch in cluster_heads:
            if not ch.is_alive:
                continue
            
            for member in ch.cluster_members:
                if not member.is_alive:
                    continue
                
                distance = member.distance_to(ch)
                tx_energy = self.calculate_transmission_energy(distance, self.packet_size, temperature_c=25.0, humidity_ratio=0.5)
                rx_energy = self.calculate_reception_energy(self.packet_size, temperature_c=25.0, humidity_ratio=0.5)
                
                member.consume_energy(tx_energy)
                round_energy_consumption += tx_energy
                
                ch.consume_energy(rx_energy)
                round_energy_consumption += rx_energy
                
                self.packets_sent += 1
                self.total_source_packets += 1  # 源节点发送即计入
                # 成员→CH使用信道模型判断
                member_to_ch_success = True
                if self.channel_model is not None:
                    import random
                    link_metrics = self.channel_model.calculate_link_metrics(
                        self.tx_power_dbm, distance, 25.0, 0.5)
                    member_to_ch_success = random.random() < link_metrics['pdr']
                if member_to_ch_success and ch.is_alive:
                    self.packets_received += 1
                    if not hasattr(ch, '_packets_received_this_round'):
                        ch._packets_received_this_round = 0
                    ch._packets_received_this_round += 1
        
        # 2. Cluster head transmits aggregated data to base station
        for ch in cluster_heads:
            if not ch.is_alive:
                continue

            # 获取本轮到达CH的包数 + CH自己的数据
            packets_at_ch = getattr(ch, '_packets_received_this_round', 0) + 1

            # Data aggregation at cluster head
            if self.use_unified_energy_model:
                aggregation_energy = self.energy_model.calculate_processing_energy(
                    self.packet_size * packets_at_ch)
            else:
                aggregation_energy = self.E_DA * self.packet_size * packets_at_ch
            ch.consume_energy(aggregation_energy)
            round_energy_consumption += aggregation_energy

            bs_distance = math.sqrt((ch.x - self.base_station[0])**2 +
                                  (ch.y - self.base_station[1])**2)
            tx_energy = self.calculate_transmission_energy(
                bs_distance, self.packet_size, temperature_c=25.0, humidity_ratio=0.5)
            ch.consume_energy(tx_energy)
            round_energy_consumption += tx_energy

            self.packets_sent += 1
            self.total_source_packets += 1  # CH自己的数据
            # CH→BS信道判断
            ch_to_bs_success = True
            if self.channel_model is not None:
                import random
                link_metrics = self.channel_model.calculate_link_metrics(
                    self.tx_power_dbm, bs_distance, 25.0, 0.5)
                ch_to_bs_success = random.random() < link_metrics['pdr']
            if ch_to_bs_success:
                self.total_bs_delivered += packets_at_ch
                for _ in range(packets_at_ch):
                    self._all_hop_counts.append(2)
            # 清理临时变量
            ch._packets_received_this_round = 0

        self.total_energy_consumed += round_energy_consumption
        self.energy_consumption_per_round.append(round_energy_consumption)
    
    def run_round(self) -> bool:
        """Run one HEED protocol round."""
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return False
        # 累计期望包数 = 每轮存活节点数
        self.source_packets_expected += len(alive_nodes)
        self.current_round += 1
        
        # 1. Cluster head selection phase
        cluster_heads = self.cluster_head_selection()
        
        # 2. Data transmission phase
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
        """Run complete HEED simulation and return summary metrics."""
        print(f">>> Start HEED protocol simulation (max rounds: {max_rounds})")
        
        for round_num in range(max_rounds):
            success = self.run_round()
            
            if not success:
                print(f"[WARN] Network lifetime ended at round {round_num}")
                break
            
            if round_num % 100 == 0:
                alive_count = len([n for n in self.nodes if n.is_alive])
                print(f"   Round {round_num}: alive nodes={alive_count}, total energy {self.total_energy_consumed:.3f}J")
        
        results = {
            'protocol_name': 'HEED',
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
            'alive_nodes_per_round': self.alive_nodes_per_round,
            'average_energy_per_round': self.total_energy_consumed / max(self.current_round, 1),
            'avg_hops_to_bs': (sum(self._all_hop_counts) / len(self._all_hop_counts)) if hasattr(self, '_all_hop_counts') and self._all_hop_counts else 0,
        }
        
        print(f"[OK] HEED simulation complete")
        print(f"   Network lifetime: {results['network_lifetime']} rounds")
        print(f"   Total energy: {results['total_energy_consumed']:.3f} J")
        print(f"   PDR: {results['packet_delivery_ratio']*100:.1f}%")
        
        return results

