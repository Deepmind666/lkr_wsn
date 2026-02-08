"""
HEED (Hybrid Energy-Efficient Distributed clustering) Protocol Implementation
Based on: Younis, O. & Fahmy, S. "HEED: A Hybrid, Energy-Efficient, Distributed 
Clustering Approach for Ad Hoc Sensor Networks" IEEE TMC 2004

Key Features:
- Hybrid cluster head selection based on residual energy and intra-cluster communication cost
- Distributed clustering without global knowledge
- Probabilistic cluster head selection with iterative refinement
- Secondary clustering parameter (communication cost) for tie-breaking
"""

import numpy as np
import random
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
try:
    from realistic_channel_model import RealisticChannelModel, EnvironmentType
except Exception:
    RealisticChannelModel = None
    EnvironmentType = None


def _resolve_channel_env(env):
    if EnvironmentType is None:
        return None
    if isinstance(env, EnvironmentType):
        return env
    if isinstance(env, str):
        key = env.strip().lower()
        for item in EnvironmentType:
            if item.value == key:
                return item
        for item in EnvironmentType:
            if item.name.lower() == key:
                return item
    return EnvironmentType.INDOOR_OFFICE

class NodeState(Enum):
    UNCOVERED = "uncovered"
    TENTATIVE_CH = "tentative_ch"
    FINAL_CH = "final_ch"
    COVERED = "covered"

@dataclass
class HEEDNode:
    """HEED Protocol Node"""
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    transmission_range: float
    state: NodeState = NodeState.UNCOVERED
    cluster_head_id: Optional[int] = None
    ch_probability: float = 0.0
    communication_cost: float = float('inf')
    neighbors: List[int] = None
    tentative_cluster_heads: List[int] = None
    
    def __post_init__(self):
        if self.neighbors is None:
            self.neighbors = []
        if self.tentative_cluster_heads is None:
            self.tentative_cluster_heads = []

@dataclass
class HEEDConfig:
    """HEED Protocol Configuration"""
    # Protocol parameters
    c_prob: float = 0.05  # Percentage of cluster heads (5%)
    p_min: float = 0.001  # Minimum probability threshold
    max_iterations: int = 10  # Maximum clustering iterations
    
    # Communication parameters
    transmission_range: float = 30.0
    packet_size: int = 1024  # bytes
    
    # Energy parameters
    initial_energy: float = 2.0  # Joules
    
    # Network parameters
    network_width: float = 100.0
    network_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 50.0
    enable_channel: bool = False
    channel_env: Optional[str] = None
    tx_power_dbm: float = 0.0
    temperature_c: float = 25.0
    humidity_ratio: float = 0.5
    link_retx: int = 0
    link_retx_power_step: float = 0.0

class HEEDProtocol:
    """HEED Protocol Implementation"""
    
    def __init__(self, config: HEEDConfig):
        self.config = config
        self.nodes: List[HEEDNode] = []
        self.clusters: Dict[int, List[int]] = {}
        self.round_number = 0
        self.total_energy_consumed = 0.0
        self.packets_transmitted = 0
        self.packets_received = 0
        self.alive_nodes = 0
        
        # Statistics
        self.stats = {
            'energy_consumed': 0.0,
            'packets_transmitted': 0,
            'packets_received': 0,
            'alive_nodes': 0,
            'cluster_heads': [],
            'network_lifetime': 0
        }

        self.source_packets_total = 0
        self.bs_delivered_total = 0
        self._all_hop_counts = []
        self.enable_channel = bool(getattr(config, "enable_channel", False))
        self.tx_power_dbm = float(getattr(config, "tx_power_dbm", 0.0) or 0.0)
        self.link_retx = max(0, int(getattr(config, "link_retx", 0) or 0))
        self.link_retx_power_step = float(getattr(config, "link_retx_power_step", 0.0) or 0.0)
        self.temperature_c = float(getattr(config, "temperature_c", 25.0) or 25.0)
        self.humidity_ratio = float(getattr(config, "humidity_ratio", 0.5) or 0.5)
        if self.enable_channel and RealisticChannelModel is not None:
            env = _resolve_channel_env(getattr(config, "channel_env", None))
            self.channel_model = RealisticChannelModel(env)
        else:
            self.channel_model = None
    
    def initialize_network(self, node_positions: List[Tuple[float, float]]):
        """Initialize network with given node positions"""
        self.nodes = []
        for i, (x, y) in enumerate(node_positions):
            node = HEEDNode(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy,
                transmission_range=self.config.transmission_range
            )
            self.nodes.append(node)
        
        # Build neighbor lists
        self._build_neighbor_lists()
        self.alive_nodes = len(self.nodes)
        self.total_energy_consumed = 0.0
        self.packets_transmitted = 0
        self.packets_received = 0
        self.round_number = 0
        self.source_packets_total = 0
        self.bs_delivered_total = 0
        self._all_hop_counts = []

    def _build_neighbor_lists(self):
        """Build neighbor lists for all nodes"""
        for i, node in enumerate(self.nodes):
            node.neighbors = []
            for j, other_node in enumerate(self.nodes):
                if i != j:
                    distance = self._calculate_distance(node, other_node)
                    if distance <= self.config.transmission_range:
                        node.neighbors.append(j)
    
    def _calculate_distance(self, node1: HEEDNode, node2: HEEDNode) -> float:
        """Calculate Euclidean distance between two nodes"""
        return math.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)
    
    def _calculate_communication_cost(self, node: HEEDNode) -> float:
        """Calculate intra-cluster communication cost for a node"""
        if not node.neighbors:
            return float('inf')
        
        # Average distance to neighbors (simplified cost metric)
        total_distance = 0.0
        for neighbor_id in node.neighbors:
            neighbor = self.nodes[neighbor_id]
            if neighbor.current_energy > 0:  # Only consider alive neighbors
                total_distance += self._calculate_distance(node, neighbor)
        
        if len(node.neighbors) == 0:
            return float('inf')
        
        return total_distance / len(node.neighbors)
    
    def _calculate_ch_probability(self, node: HEEDNode) -> float:
        """Calculate cluster head probability for a node"""
        if node.current_energy <= 0:
            return 0.0
        
        # Energy ratio
        energy_ratio = node.current_energy / node.initial_energy
        
        # Base probability scaled by energy ratio
        prob = self.config.c_prob * energy_ratio
        
        # Ensure minimum probability
        return max(prob, self.config.p_min)
    
    def run_clustering_phase(self):
        """Execute HEED clustering algorithm"""
        # Reset node states
        for node in self.nodes:
            if node.current_energy > 0:
                node.state = NodeState.UNCOVERED
                node.cluster_head_id = None
                node.tentative_cluster_heads = []
                node.communication_cost = self._calculate_communication_cost(node)
                node.ch_probability = self._calculate_ch_probability(node)
        
        # Iterative clustering process
        for iteration in range(self.config.max_iterations):
            self._clustering_iteration()
            
            # Check if all nodes are covered
            uncovered_nodes = [n for n in self.nodes if n.current_energy > 0 and n.state == NodeState.UNCOVERED]
            if not uncovered_nodes:
                break
        
        # Finalize clustering
        self._finalize_clustering()
        
        # Build cluster structure
        self._build_clusters()
    
    def _clustering_iteration(self):
        """Single iteration of HEED clustering"""
        # Phase 1: Tentative cluster head selection
        for node in self.nodes:
            if node.current_energy <= 0:
                continue
                
            if node.state == NodeState.UNCOVERED:
                # Probabilistic cluster head selection
                if random.random() < node.ch_probability:
                    node.state = NodeState.TENTATIVE_CH
                    # Announce tentative cluster head status
                    self._announce_tentative_ch(node)
        
        # Phase 2: Cluster head finalization
        for node in self.nodes:
            if node.current_energy <= 0:
                continue
                
            if node.state == NodeState.UNCOVERED:
                # Select best cluster head from tentative CHs
                best_ch = self._select_best_cluster_head(node)
                if best_ch is not None:
                    node.cluster_head_id = best_ch.id
                    node.state = NodeState.COVERED
        
        # Phase 3: Update probabilities for next iteration
        for node in self.nodes:
            if node.current_energy <= 0:
                continue
                
            if node.state == NodeState.TENTATIVE_CH:
                # Double the probability for next iteration
                node.ch_probability = min(node.ch_probability * 2, 1.0)
    
    def _announce_tentative_ch(self, ch_node: HEEDNode):
        """Announce tentative cluster head to neighbors"""
        for neighbor_id in ch_node.neighbors:
            neighbor = self.nodes[neighbor_id]
            if neighbor.current_energy > 0:
                neighbor.tentative_cluster_heads.append(ch_node.id)
    
    def _select_best_cluster_head(self, node: HEEDNode) -> Optional[HEEDNode]:
        """Select best cluster head based on communication cost"""
        if not node.tentative_cluster_heads:
            return None
        
        best_ch = None
        best_cost = float('inf')
        
        for ch_id in node.tentative_cluster_heads:
            ch_node = self.nodes[ch_id]
            if ch_node.current_energy > 0:
                # Cost is based on distance and cluster head's communication cost
                distance = self._calculate_distance(node, ch_node)
                total_cost = distance + ch_node.communication_cost
                
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_ch = ch_node
        
        return best_ch
    
    def _finalize_clustering(self):
        """Finalize cluster head selection"""
        # Convert tentative CHs to final CHs
        for node in self.nodes:
            if node.current_energy > 0 and node.state == NodeState.TENTATIVE_CH:
                node.state = NodeState.FINAL_CH
        
        # Uncovered nodes become cluster heads themselves
        for node in self.nodes:
            if node.current_energy > 0 and node.state == NodeState.UNCOVERED:
                node.state = NodeState.FINAL_CH
                node.cluster_head_id = node.id
    
    def _build_clusters(self):
        """Build cluster structure"""
        self.clusters = {}
        
        # Initialize clusters with cluster heads
        for node in self.nodes:
            if node.current_energy > 0 and node.state == NodeState.FINAL_CH:
                self.clusters[node.id] = [node.id]
        
        # Add member nodes to clusters
        for node in self.nodes:
            if node.current_energy > 0 and node.state == NodeState.COVERED:
                if node.cluster_head_id in self.clusters:
                    self.clusters[node.cluster_head_id].append(node.id)
    
    def run_communication_phase(self):
        """Execute communication phase"""
        if not self.clusters:
            return

        # Intra-cluster communication
        for ch_id, members in self.clusters.items():
            ch_node = self.nodes[ch_id]
            if ch_node.current_energy <= 0:
                continue

            payload_packets = 1
            self.source_packets_total += 1

            # Members send data to cluster head
            for member_id in members:
                if member_id == ch_id:
                    continue
                member_node = self.nodes[member_id]
                if member_node.current_energy > 0:
                    self.source_packets_total += 1
                    if self._transmit_data(member_node, ch_node):
                        payload_packets += 1

            # Cluster head aggregates and sends to base station
            if payload_packets > 0 and self._transmit_to_base_station(ch_node):
                self.bs_delivered_total += payload_packets
                for _ in range(payload_packets):
                    self._all_hop_counts.append(2)

    def _transmit_data(self, sender: HEEDNode, receiver: HEEDNode) -> bool:
        """Simulate data transmission between nodes"""
        if sender.current_energy <= 0 or receiver.current_energy <= 0:
            return False

        def link_success(distance: float, tx_power: float) -> bool:
            if self.channel_model is None:
                return True
            metrics = self.channel_model.calculate_link_metrics(tx_power, distance, self.temperature_c, self.humidity_ratio)
            return random.random() < metrics.get("pdr", 0.0)
        
        distance = self._calculate_distance(sender, receiver)
        
        # Simple energy model (similar to LEACH)
        # E_tx = E_elec * k + E_amp * k * d^2
        E_elec = 50e-9  # 50 nJ/bit
        E_amp = 100e-12  # 100 pJ/bit/m^2
        
        packet_bits = self.config.packet_size * 8
        tx_energy = E_elec * packet_bits + E_amp * packet_bits * (distance ** 2)
        rx_energy = E_elec * packet_bits
        
        for attempt in range(self.link_retx + 1):
            tx_power = self.tx_power_dbm + attempt * self.link_retx_power_step
            if sender.current_energy < tx_energy or receiver.current_energy < rx_energy:
                if sender.current_energy < tx_energy:
                    sender.current_energy = 0
                if receiver.current_energy < rx_energy:
                    receiver.current_energy = 0
                return False

            # Consume energy
            sender.current_energy -= tx_energy
            receiver.current_energy -= rx_energy
            self.total_energy_consumed += (tx_energy + rx_energy)
            self.packets_transmitted += 1

            if link_success(distance, tx_power):
                self.packets_received += 1
                return True

        return False

    def _transmit_to_base_station(self, ch_node: HEEDNode) -> bool:
        """Transmit aggregated data to base station"""
        if ch_node.current_energy <= 0:
            return False
        
        # Distance to base station
        distance = math.sqrt(
            (ch_node.x - self.config.base_station_x)**2 + 
            (ch_node.y - self.config.base_station_y)**2
        )
        
        # Energy consumption for long-range transmission
        E_elec = 50e-9
        E_amp = 100e-12
        
        packet_bits = self.config.packet_size * 8
        tx_energy = E_elec * packet_bits + E_amp * packet_bits * (distance ** 2)
        
        def link_success(distance: float, tx_power: float) -> bool:
            if self.channel_model is None:
                return True
            metrics = self.channel_model.calculate_link_metrics(tx_power, distance, self.temperature_c, self.humidity_ratio)
            return random.random() < metrics.get("pdr", 0.0)

        for attempt in range(self.link_retx + 1):
            tx_power = self.tx_power_dbm + attempt * self.link_retx_power_step
            if ch_node.current_energy < tx_energy:
                ch_node.current_energy = 0
                return False
            ch_node.current_energy -= tx_energy
            self.total_energy_consumed += tx_energy
            self.packets_transmitted += 1
            if link_success(distance, tx_power):
                self.packets_received += 1
                return True
        return False
    
    def run_round(self) -> Dict:
        """Execute one complete round of HEED protocol"""
        self.round_number += 1

        # Update alive nodes count
        self.alive_nodes = sum(1 for node in self.nodes if node.current_energy > 0)

        if self.alive_nodes == 0:
            return self.get_statistics()

        # Clustering phase
        try:
            self.run_clustering_phase()

            # Check if clustering was successful
            if not self.clusters or len(self.clusters) == 0:
                print(f"[HEED Debug] Round {self.round_number}: No clusters formed")
                # Fallback: allow some nodes to become self-clustered
                for node in self.nodes:
                    if node.current_energy > 0 and node.state == NodeState.UNCOVERED:
                        node.state = NodeState.FINAL_CH
                        node.cluster_head_id = node.id
                        self.clusters[node.id] = [node.id]

        except Exception as e:
            print(f"[HEED Error] Clustering failed in round {self.round_number}: {e}")
            return self.get_statistics()

        # Communication phase - limit energy consumption in first round
        try:
            self.run_communication_phase()
        except Exception as e:
            print(f"[HEED Error] Communication failed in round {self.round_number}: {e}")
            return self.get_statistics()

        # Update statistics
        self.stats['energy_consumed'] = self.total_energy_consumed
        self.stats['packets_transmitted'] = self.packets_transmitted
        self.stats['packets_received'] = self.packets_received
        self.stats['alive_nodes'] = self.alive_nodes
        self.stats['cluster_heads'] = [ch_id for ch_id in self.clusters.keys()
                                     if self.nodes[ch_id].current_energy > 0]
        self.stats['network_lifetime'] = self.round_number

        return self.get_statistics()
    
    def get_statistics(self) -> Dict:
        """Get current protocol statistics"""
        return {
            'round': self.round_number,
            'alive_nodes': self.alive_nodes,
            'total_energy_consumed': self.total_energy_consumed,
            'packets_transmitted': self.packets_transmitted,
            'packets_received': self.packets_received,
            'packet_delivery_ratio': self.packets_received / max(self.packets_transmitted, 1),
            'packet_delivery_ratio_end2end': self.bs_delivered_total / max(self.source_packets_total, 1),
            'energy_efficiency': self.packets_received / max(self.total_energy_consumed, 1e-9),
            'num_clusters': len(self.clusters),
            'cluster_heads': list(self.clusters.keys()) if self.clusters else [],
            'source_packets_total': self.source_packets_total,
            'bs_delivered_total': self.bs_delivered_total
        }
    
    def get_final_statistics(self) -> Dict:
        """Get final protocol statistics"""
        pdr = self.packets_received / max(self.packets_transmitted, 1)
        energy_efficiency = self.packets_received / max(self.total_energy_consumed, 1e-9)
        
        return {
            'protocol': 'HEED',
            'network_lifetime': self.round_number,
            'total_energy_consumed': self.total_energy_consumed,
            'packets_transmitted': self.packets_transmitted,
            'packets_received': self.packets_received,
            'packet_delivery_ratio': pdr,
            'packet_delivery_ratio_end2end': self.bs_delivered_total / max(self.source_packets_total, 1),
            'energy_efficiency': energy_efficiency,
            'final_alive_nodes': self.alive_nodes,
            'additional_metrics': {
                'total_packets_sent': self.packets_transmitted,
                'total_packets_received': self.packets_received,
                'source_packets_total': self.source_packets_total,
                'bs_delivered_total': self.bs_delivered_total
            },
            'avg_hops_to_bs': (sum(self._all_hop_counts) / len(self._all_hop_counts)) if self._all_hop_counts else 0,
        }
