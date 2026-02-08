#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified CAS (Context-Adaptive Switching) Module for AERIS Protocol
======================================================================
Lightweight CH selection inspired by I-LEACH's probabilistic approach,
while retaining AERIS's environment awareness.

Key Design Principles (from I-LEACH analysis):
1. Simple probabilistic selection (not complex scoring)
2. Round-based exclusion (G counter)
3. Energy-weighted probability

AERIS Enhancements:
- Environment map integration for density awareness
- Link quality consideration
- Adaptive probability based on network state

Author: AERIS Research Team
Date: 2026-01-04
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random
import math


class NodeRole(Enum):
    """Node role in the network"""
    REGULAR = "regular"
    CLUSTER_HEAD = "cluster_head"
    GATEWAY = "gateway"
    RELAY = "relay"


@dataclass
class SimpleCASConfig:
    """Configuration for simplified CAS selector"""

    # Base CH probability (like I-LEACH p=0.05)
    p_base: float = 0.05

    # Round exclusion period (like I-LEACH 1/p)
    exclusion_rounds: int = 20  # = 1/0.05

    # Energy threshold for CH eligibility
    min_energy_ratio: float = 0.15

    # Environment modifiers
    enable_density_modifier: bool = True
    enable_link_quality_modifier: bool = True

    # Modifier ranges
    density_modifier_range: Tuple[float, float] = (0.8, 1.2)
    link_modifier_range: Tuple[float, float] = (0.9, 1.1)


@dataclass
class NodeState:
    """Simplified node state for CH selection"""
    node_id: int
    x: float
    y: float
    energy: float
    initial_energy: float = 1.0
    rounds_since_ch: int = 999  # Large number means never been CH
    last_ch_round: int = -1
    avg_link_quality: float = 0.8


class SimplifiedCASSelector:
    """
    Simplified Context-Adaptive CH Selector

    Uses I-LEACH-style probabilistic selection with AERIS enhancements:
    1. Simple probability formula (not weighted scoring)
    2. Round-based exclusion (G counter)
    3. Energy-based eligibility
    4. Environment density modifier (AERIS unique)
    5. Link quality modifier (AERIS unique)

    Complexity: O(n) per round, minimal memory
    """

    def __init__(self, config: Optional[SimpleCASConfig] = None):
        self.config = config or SimpleCASConfig()

        # Statistics
        self.stats = {
            'total_rounds': 0,
            'total_ch_selections': 0,
            'avg_ch_per_round': 0.0,
            'ch_energy_mean': 0.0
        }

        # CH history per round
        self.ch_history: List[List[int]] = []

    def calculate_ch_probability(self,
                                  node: NodeState,
                                  round_number: int,
                                  local_density: float = 1.0,
                                  network_avg_energy: float = 0.5) -> float:
        """
        Calculate CH selection probability for a node.

        Inspired by I-LEACH formula:
        p_threshold = p / (1 - p * (round % (1/p)))

        With AERIS enhancements:
        - Energy modifier
        - Density modifier
        - Link quality modifier
        """
        cfg = self.config

        # Check eligibility
        energy_ratio = node.energy / node.initial_energy

        # 1. Energy check - must have sufficient energy
        if energy_ratio < cfg.min_energy_ratio:
            return 0.0

        # 2. Round exclusion check (like I-LEACH G counter)
        if node.rounds_since_ch < cfg.exclusion_rounds:
            return 0.0

        # 3. Base I-LEACH probability formula
        cycle_position = round_number % cfg.exclusion_rounds
        if cycle_position == 0:
            cycle_position = cfg.exclusion_rounds

        denominator = 1.0 - cfg.p_base * (cycle_position - 1)
        if denominator <= 0:
            denominator = 0.01

        p_base = cfg.p_base / denominator

        # 4. Energy modifier - favor nodes with more energy
        # Higher energy ratio = higher probability
        energy_modifier = 0.5 + 0.5 * energy_ratio

        # Also consider if node has more than average
        if energy_ratio > network_avg_energy:
            energy_modifier *= 1.1

        # 5. Density modifier (AERIS unique)
        # In sparse areas, increase probability to ensure coverage
        # In dense areas, decrease to avoid too many CHs
        if cfg.enable_density_modifier:
            # density < 1 means sparse, > 1 means dense
            density_modifier = 1.0 / max(0.5, min(2.0, local_density))
            # Clamp to range
            lo, hi = cfg.density_modifier_range
            density_modifier = max(lo, min(hi, density_modifier))
        else:
            density_modifier = 1.0

        # 6. Link quality modifier (AERIS unique)
        # Nodes with better link quality make better CHs
        if cfg.enable_link_quality_modifier:
            lq_modifier = 0.8 + 0.4 * node.avg_link_quality
            lo, hi = cfg.link_modifier_range
            lq_modifier = max(lo, min(hi, lq_modifier))
        else:
            lq_modifier = 1.0

        # Final probability
        p_final = p_base * energy_modifier * density_modifier * lq_modifier

        return min(1.0, max(0.0, p_final))

    def select_cluster_heads(self,
                              nodes: List[NodeState],
                              round_number: int,
                              density_map: Optional[Dict[int, float]] = None,
                              network_avg_energy: float = 0.5) -> List[int]:
        """
        Select cluster heads for a round.

        Uses probabilistic selection like I-LEACH but with AERIS enhancements.

        Args:
            nodes: List of node states
            round_number: Current round number
            density_map: Optional map of node_id -> local density
            network_avg_energy: Network average energy ratio

        Returns:
            List of selected CH node IDs
        """
        selected_chs = []

        for node in nodes:
            # Get local density (default 1.0 if not provided)
            local_density = 1.0
            if density_map and node.node_id in density_map:
                local_density = density_map[node.node_id]

            # Calculate probability
            p = self.calculate_ch_probability(
                node, round_number, local_density, network_avg_energy
            )

            # Probabilistic selection (like I-LEACH)
            if random.random() < p:
                selected_chs.append(node.node_id)

        # Ensure at least one CH (fallback to highest energy)
        if len(selected_chs) == 0 and nodes:
            best_node = max(nodes, key=lambda n: n.energy if n.energy > 0 else -1)
            if best_node.energy > 0:
                selected_chs.append(best_node.node_id)

        # Update statistics
        self.stats['total_rounds'] += 1
        self.stats['total_ch_selections'] += len(selected_chs)
        self.stats['avg_ch_per_round'] = (
            self.stats['total_ch_selections'] / self.stats['total_rounds']
        )

        # Update node states (reset rounds_since_ch for selected CHs)
        for node in nodes:
            if node.node_id in selected_chs:
                node.rounds_since_ch = 0
                node.last_ch_round = round_number
            else:
                node.rounds_since_ch += 1

        # Record history
        self.ch_history.append(selected_chs.copy())

        return selected_chs

    def get_ch_statistics(self) -> Dict:
        """Get CH selection statistics"""
        ch_counts: Dict[int, int] = {}
        for ch_list in self.ch_history:
            for ch_id in ch_list:
                ch_counts[ch_id] = ch_counts.get(ch_id, 0) + 1

        return {
            'total_rounds': self.stats['total_rounds'],
            'avg_ch_per_round': self.stats['avg_ch_per_round'],
            'ch_distribution': ch_counts,
            'fairness': self._calculate_fairness(ch_counts)
        }

    def _calculate_fairness(self, ch_counts: Dict[int, int]) -> float:
        """Calculate Jain's fairness index for CH selection"""
        if not ch_counts:
            return 1.0

        counts = list(ch_counts.values())
        n = len(counts)
        sum_x = sum(counts)
        sum_x2 = sum(x * x for x in counts)

        if sum_x2 == 0:
            return 1.0

        return (sum_x * sum_x) / (n * sum_x2)


class EnvironmentAwareCHSelector:
    """
    Environment-Aware CH Selector

    Combines simplified probabilistic selection with AERIS's
    environment map for truly adaptive behavior.
    """

    def __init__(self, config: Optional[SimpleCASConfig] = None):
        self.simple_selector = SimplifiedCASSelector(config)

        # Environment state
        self.channel_quality_history: List[float] = []
        self.density_estimates: Dict[int, float] = {}

    def update_environment(self,
                           node_id: int,
                           channel_quality: float,
                           neighbor_count: int,
                           area_size: float = 100.0):
        """Update environment information for a node"""
        # Update density estimate
        expected_neighbors = (len(self.density_estimates) + 1) / (area_size * area_size)
        if expected_neighbors > 0:
            self.density_estimates[node_id] = neighbor_count / max(1, expected_neighbors * area_size)
        else:
            self.density_estimates[node_id] = 1.0

        # Track channel quality
        self.channel_quality_history.append(channel_quality)
        if len(self.channel_quality_history) > 100:
            self.channel_quality_history.pop(0)

    def get_current_channel_quality(self) -> float:
        """Get average recent channel quality"""
        if not self.channel_quality_history:
            return 0.8
        return sum(self.channel_quality_history[-20:]) / len(self.channel_quality_history[-20:])

    def select_cluster_heads(self,
                              nodes: List[NodeState],
                              round_number: int) -> List[int]:
        """Select CHs with environment awareness"""
        # Calculate network average energy
        total_energy = sum(n.energy for n in nodes)
        total_initial = sum(n.initial_energy for n in nodes)
        avg_energy = total_energy / total_initial if total_initial > 0 else 0.5

        # Adjust link quality based on channel conditions
        channel_quality = self.get_current_channel_quality()
        for node in nodes:
            node.avg_link_quality = (node.avg_link_quality + channel_quality) / 2

        return self.simple_selector.select_cluster_heads(
            nodes, round_number, self.density_estimates, avg_energy
        )


# Factory functions

def create_simple_cas_selector(
    p_base: float = 0.05,
    enable_environment: bool = True
) -> SimplifiedCASSelector:
    """Create a simplified CAS selector"""
    config = SimpleCASConfig(
        p_base=p_base,
        exclusion_rounds=int(1 / p_base),
        enable_density_modifier=enable_environment,
        enable_link_quality_modifier=enable_environment
    )
    return SimplifiedCASSelector(config)


def create_ileach_compatible_selector() -> SimplifiedCASSelector:
    """Create a selector that mimics I-LEACH behavior"""
    config = SimpleCASConfig(
        p_base=0.05,
        exclusion_rounds=20,
        enable_density_modifier=False,  # I-LEACH doesn't use this
        enable_link_quality_modifier=False  # I-LEACH doesn't use this
    )
    return SimplifiedCASSelector(config)


def create_aeris_enhanced_selector() -> EnvironmentAwareCHSelector:
    """Create a fully environment-aware selector"""
    config = SimpleCASConfig(
        p_base=0.05,
        exclusion_rounds=20,
        enable_density_modifier=True,
        enable_link_quality_modifier=True,
        density_modifier_range=(0.7, 1.3),
        link_modifier_range=(0.85, 1.15)
    )
    return EnvironmentAwareCHSelector(config)


if __name__ == "__main__":
    # Demo usage
    print("AERIS Simplified CAS Selector Demo")
    print("=" * 50)

    # Create test nodes
    nodes = [
        NodeState(i, x=random.uniform(0, 100), y=random.uniform(0, 100),
                  energy=random.uniform(0.3, 1.0), initial_energy=1.0,
                  rounds_since_ch=random.randint(0, 30),
                  avg_link_quality=random.uniform(0.6, 0.95))
        for i in range(50)
    ]

    # Create density map (simulate sparse/dense areas)
    density_map = {n.node_id: random.uniform(0.5, 2.0) for n in nodes}

    # Test simplified selector
    print("\n1. Simplified CAS Selector (I-LEACH style + AERIS enhancements):")
    selector = create_simple_cas_selector()

    for round_num in range(1, 11):
        chs = selector.select_cluster_heads(nodes, round_num, density_map)
        print(f"   Round {round_num}: {len(chs)} CHs selected: {chs[:5]}{'...' if len(chs) > 5 else ''}")

    print("\n   Statistics:", selector.get_ch_statistics())

    # Test I-LEACH compatible selector
    print("\n2. I-LEACH Compatible Selector:")
    ileach_selector = create_ileach_compatible_selector()

    # Reset node states
    for n in nodes:
        n.rounds_since_ch = 999

    for round_num in range(1, 6):
        chs = ileach_selector.select_cluster_heads(nodes, round_num)
        print(f"   Round {round_num}: {len(chs)} CHs selected")

    # Test environment-aware selector
    print("\n3. Environment-Aware AERIS Selector:")
    env_selector = create_aeris_enhanced_selector()

    # Reset and add environment info
    for n in nodes:
        n.rounds_since_ch = 999
        env_selector.update_environment(n.node_id, 0.85, random.randint(3, 15))

    for round_num in range(1, 6):
        chs = env_selector.select_cluster_heads(nodes, round_num)
        print(f"   Round {round_num}: {len(chs)} CHs selected, channel quality: {env_selector.get_current_channel_quality():.2f}")
