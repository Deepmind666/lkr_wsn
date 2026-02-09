#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PEGASIS (Power-Efficient Gathering in Sensor Information Systems) protocol implementation.
This module provides a basic PEGASIS simulation for WSN baseline comparison.

**MODIFIED 2025-11-04**: Now uses ImprovedEnergyModel for unified comparison with AERIS.

References:
Lindsey, S., & Raghavendra, C. S. (2002).
PEGASIS: Power-efficient gathering in sensor information systems.
In Proceedings, IEEE aerospace conference (Vol. 3, pp. 3-1125).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import math
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt

# Import unified energy model
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

class PEGASISNode:
    """PEGASIS node representing a sensor node."""
    
    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True
        self.is_leader = False
        
        # PEGASIS specific parameters
        self.next_node = None
        self.prev_node = None
        self.chain_position = -1
        self.data_packets = []
        
    def distance_to(self, other_node) -> float:
        """Compute Euclidean distance to another node."""
        return math.sqrt((self.x - other_node.x)**2 + (self.y - other_node.y)**2)
    
    def consume_energy(self, energy_amount: float):
        """Consume energy and update alive status."""
        self.current_energy -= energy_amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False
    
    def reset_chain_info(self):
        """Reset chain-related info."""
        self.next_node = None
        self.prev_node = None
        self.chain_position = -1
        self.is_leader = False

class PEGASISProtocol:
    """PEGASIS protocol simulator."""

    def __init__(self, nodes: List[PEGASISNode], base_station: Tuple[float, float],
                 use_unified_energy_model: bool = True, tx_power_dbm: float = 10.0,
                 channel_model=None):
        """Initialize PEGASIS protocol.

        Args:
            nodes: List of PEGASIS nodes
            base_station: Base station coordinates (x, y)
            use_unified_energy_model: If True, use ImprovedEnergyModel (CC2420 parameters).
                                     If False, use legacy simplified parameters.
            tx_power_dbm: Transmission power in dBm (default 10.0 for fair comparison)
            channel_model: Optional RealisticChannelModel for PDR calculation
        """
        self.nodes = nodes
        self.base_station = base_station
        self.current_round = 0
        self.chain = []
        self.leader_index = 0
        self.use_unified_energy_model = use_unified_energy_model
        self.tx_power_dbm = tx_power_dbm
        self.channel_model = channel_model

        # Packet size
        self.packet_size = 8192  # packet size (bits) - 统一为1024 bytes

        if use_unified_energy_model:
            # Use unified real hardware model (CC2420 TelosB)
            self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
            print(f"[PEGASIS] Using unified energy model (CC2420 TelosB, 208.8 nJ/bit)")
        else:
            # Legacy simplified parameters (for backward compatibility)
            self.E_elec = 50e-9  # electronics energy (J/bit)
            self.E_fs = 10e-12   # free-space model (J/bit/m^2)
            self.E_mp = 0.0013e-12  # multi-path model (J/bit/m^4)
            self.E_DA = 5e-9     # data aggregation energy (J/bit)
            self.d_crossover = 87  # distance threshold (m)
            self.energy_model = None
            print(f"[PEGASIS] Using legacy energy model (50 nJ/bit)")
        
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

        # Construct initial chain
        self.construct_chain()

        print(f"[OK] PEGASIS initialization complete")
        print(f"   Nodes: {len(self.nodes)}")
        print(f"   Base station: {self.base_station}")
        print(f"   Chain length: {len(self.chain)}")
    
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
    
    def construct_chain(self):
        """Construct greedy chain structure."""
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return
        
        # Reset chain info
        for node in alive_nodes:
            node.reset_chain_info()
        
        self.chain = []
        remaining_nodes = alive_nodes.copy()
        
        # Select start node (farthest from base station)
        max_distance = 0
        start_node = None
        for node in remaining_nodes:
            distance = math.sqrt((node.x - self.base_station[0])**2 + 
                               (node.y - self.base_station[1])**2)
            if distance > max_distance:
                max_distance = distance
                start_node = node
        
        if start_node is None:
            start_node = remaining_nodes[0]
        
        self.chain.append(start_node)
        remaining_nodes.remove(start_node)
        
        # Greedy chain construction
        while remaining_nodes:
            last_node = self.chain[-1]
            min_distance = float('inf')
            closest_node = None
            
            for node in remaining_nodes:
                distance = last_node.distance_to(node)
                if distance < min_distance:
                    min_distance = distance
                    closest_node = node
            
            if closest_node:
                self.chain.append(closest_node)
                remaining_nodes.remove(closest_node)
            else:
                break
        
        # Set neighbor relations
        for i, node in enumerate(self.chain):
            node.chain_position = i
            if i > 0:
                node.prev_node = self.chain[i-1]
            if i < len(self.chain) - 1:
                node.next_node = self.chain[i+1]
    
    def select_leader(self) -> Optional[PEGASISNode]:
        """Select chain leader in a round-robin manner."""
        alive_chain = [n for n in self.chain if n.is_alive]
        if not alive_chain:
            return None
        
        self.leader_index = self.current_round % len(alive_chain)
        leader = alive_chain[self.leader_index]
        leader.is_leader = True
        
        return leader
    
    def data_transmission_phase(self, leader: PEGASISNode):
        """Simulate one data transmission phase."""
        round_energy_consumption = 0.0
        if not hasattr(self, '_all_hop_counts'):
            self._all_hop_counts = []

        # PEGASIS链式转发：追踪每个节点的数据是否成功到达leader
        # 使用累积成功率来模拟多跳转发
        alive_nodes = [n for n in self.chain if n.is_alive]
        alive_count = len(alive_nodes)

        # 1. Chain data forwarding to leader from both sides
        leader_pos = leader.chain_position

        # 追踪左侧和右侧成功到达leader的包数
        left_success_count = 0
        right_success_count = 0

        # Left side: 从最左边向leader转发
        for i in range(leader_pos - 1, -1, -1):
            current_node = self.chain[i]
            if not current_node.is_alive:
                continue

            next_node = self.chain[i + 1]
            if not next_node.is_alive:
                for j in range(i + 2, len(self.chain)):
                    if self.chain[j].is_alive:
                        next_node = self.chain[j]
                        break
                else:
                    continue

            distance = current_node.distance_to(next_node)
            tx_energy = self.calculate_transmission_energy(
                distance, self.packet_size, temperature_c=25.0, humidity_ratio=0.5)
            rx_energy = self.calculate_reception_energy(
                self.packet_size, temperature_c=25.0, humidity_ratio=0.5)

            current_node.consume_energy(tx_energy)
            next_node.consume_energy(rx_energy)
            round_energy_consumption += tx_energy + rx_energy
            self.packets_sent += 1

            # 信道判断
            forward_success = True
            if self.channel_model is not None:
                import random
                link_metrics = self.channel_model.calculate_link_metrics(
                    self.tx_power_dbm, distance, 25.0, 0.5)
                forward_success = random.random() < link_metrics['pdr']

            if forward_success and next_node.is_alive:
                self.packets_received += 1
                left_success_count += 1

        # Right side: 从最右边向leader转发
        for i in range(leader_pos + 1, len(self.chain)):
            current_node = self.chain[i]
            if not current_node.is_alive:
                continue

            prev_node = self.chain[i - 1]
            if not prev_node.is_alive:
                for j in range(i - 2, -1, -1):
                    if self.chain[j].is_alive:
                        prev_node = self.chain[j]
                        break
                else:
                    continue

            distance = current_node.distance_to(prev_node)
            tx_energy = self.calculate_transmission_energy(
                distance, self.packet_size, temperature_c=25.0, humidity_ratio=0.5)
            rx_energy = self.calculate_reception_energy(
                self.packet_size, temperature_c=25.0, humidity_ratio=0.5)

            current_node.consume_energy(tx_energy)
            prev_node.consume_energy(rx_energy)
            round_energy_consumption += tx_energy + rx_energy
            self.packets_sent += 1

            forward_success = True
            if self.channel_model is not None:
                import random
                link_metrics = self.channel_model.calculate_link_metrics(
                    self.tx_power_dbm, distance, 25.0, 0.5)
                forward_success = random.random() < link_metrics['pdr']

            if forward_success and prev_node.is_alive:
                self.packets_received += 1
                right_success_count += 1

        # 2. 计算到达leader的包数
        # 简化模型：左侧成功转发数 + 右侧成功转发数 + leader自己
        packets_reached_leader = left_success_count + right_success_count
        if leader.is_alive:
            packets_reached_leader += 1

        if leader.is_alive and packets_reached_leader > 0:
            if self.use_unified_energy_model:
                aggregation_energy = self.energy_model.calculate_processing_energy(
                    self.packet_size * packets_reached_leader)
            else:
                aggregation_energy = self.E_DA * self.packet_size * packets_reached_leader
            leader.consume_energy(aggregation_energy)
            round_energy_consumption += aggregation_energy

        # 3. Leader transmits aggregated data to base station
        alive_count = len([n for n in self.chain if n.is_alive])
        if leader.is_alive and packets_reached_leader > 0:
            bs_distance = math.sqrt((leader.x - self.base_station[0])**2 +
                                  (leader.y - self.base_station[1])**2)
            tx_energy = self.calculate_transmission_energy(
                bs_distance, self.packet_size, temperature_c=25.0, humidity_ratio=0.5)
            leader.consume_energy(tx_energy)
            round_energy_consumption += tx_energy

            self.packets_sent += 1
            self.total_source_packets += alive_count  # attempted按存活节点计（PEGASIS特性）
            # Leader→BS信道判断
            leader_to_bs_success = True
            if self.channel_model is not None:
                import random
                link_metrics = self.channel_model.calculate_link_metrics(
                    self.tx_power_dbm, bs_distance, 25.0, 0.5)
                leader_to_bs_success = random.random() < link_metrics['pdr']
            if leader_to_bs_success:
                self.total_bs_delivered += packets_reached_leader
                # Average source->leader hop distance in a chain:
                # mean_i |i - leader_pos|, then +1 for leader->BS hop.
                chain_len = len(self.chain)
                leader_pos = min(max(leader.chain_position, 0), max(0, chain_len - 1))
                left_sum = leader_pos * (leader_pos + 1) / 2.0
                right_count = chain_len - leader_pos - 1
                right_sum = right_count * (right_count + 1) / 2.0
                avg_chain_hops = (left_sum + right_sum) / max(1.0, float(chain_len))
                for _ in range(packets_reached_leader):
                    self._all_hop_counts.append(avg_chain_hops + 1.0)

        self.total_energy_consumed += round_energy_consumption
        self.energy_consumption_per_round.append(round_energy_consumption)
    
    def run_round(self) -> bool:
        """Run a single PEGASIS round."""
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return False
        # 累计期望包数 = 每轮存活节点数（无条件计入）
        self.source_packets_expected += len(alive_nodes)
        self.current_round += 1
        
        # 1. Reconstruct chain if membership changed
        current_alive = len(alive_nodes)
        if current_alive != len([n for n in self.chain if n.is_alive]):
            self.construct_chain()
        
        # 2. Select leader
        leader = self.select_leader()
        if not leader:
            return False
        
        # 3. Data transmission phase
        self.data_transmission_phase(leader)
        
        # 4. Update metrics
        current_dead = len(self.nodes) - current_alive
        
        if current_dead > self.dead_nodes:
            self.dead_nodes = current_dead
            if self.network_lifetime == 0 and current_dead > 0:
                self.network_lifetime = self.current_round
        
        self.alive_nodes_per_round.append(current_alive)
        
        return True
    
    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """Run a complete PEGASIS simulation and return summary metrics."""
        print(f">>> Start PEGASIS protocol simulation (max rounds: {max_rounds})")
        
        for round_num in range(max_rounds):
            success = self.run_round()
            
            if not success:
                print(f"[WARN] Network lifetime ended at round {round_num}")
                break
            
            if round_num % 100 == 0:
                alive_count = len([n for n in self.nodes if n.is_alive])
                print(f"   Round {round_num}: alive nodes={alive_count}, total energy {self.total_energy_consumed:.3f}J")
        
        results = {
            'protocol_name': 'PEGASIS',
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
            'hop_count_distribution': dict((h, self._all_hop_counts.count(h)) for h in set(self._all_hop_counts)) if hasattr(self, '_all_hop_counts') and self._all_hop_counts else {},
        }
        
        print(f"[OK] PEGASIS simulation complete")
        print(f"   Network lifetime: {results['network_lifetime']} rounds")
        print(f"   Total energy: {results['total_energy_consumed']:.3f} J")
        print(f"   PDR: {results['packet_delivery_ratio']*100:.1f}%")
        
        return results

