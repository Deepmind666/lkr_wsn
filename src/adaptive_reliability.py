#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adaptive Reliability Manager for AERIS Protocol
================================================
Provides configurable reliability-energy trade-offs based on SOTA algorithm analysis.

Key Innovation: Instead of fixed high-reliability mode (7 ARQ, 5 power levels),
AERIS now offers adaptive profiles that can be selected based on:
1. Network energy state
2. Required QoS level
3. Channel conditions

Inspired by:
- I-LEACH: Simple, energy-efficient approach
- PSO-WSN: Multi-objective optimization
- DQN-WSN: Dynamic adaptation

Author: AERIS Research Team
Date: 2026-01-04
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
from enum import Enum


class ReliabilityLevel(Enum):
    """Reliability level enumeration"""
    ULTRA_LOW_POWER = "ultra_low_power"
    LOW_POWER = "low_power"
    BALANCED = "balanced"
    HIGH_RELIABILITY = "high_reliability"
    ULTRA_RELIABLE = "ultra_reliable"


@dataclass
class ReliabilityProfile:
    """Configuration profile for reliability-energy trade-off"""
    name: str
    max_arq_attempts: int
    power_levels: int
    relay_copies: int
    rescue_enabled: bool
    power_step_db: float
    expected_pdr: float
    energy_factor: float
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'max_arq_attempts': self.max_arq_attempts,
            'power_levels': self.power_levels,
            'relay_copies': self.relay_copies,
            'rescue_enabled': self.rescue_enabled,
            'power_step_db': self.power_step_db,
            'expected_pdr': self.expected_pdr,
            'energy_factor': self.energy_factor
        }


# Pre-defined reliability profiles based on SOTA analysis
RELIABILITY_PROFILES: Dict[ReliabilityLevel, ReliabilityProfile] = {
    ReliabilityLevel.ULTRA_LOW_POWER: ReliabilityProfile(
        name="ultra_low_power",
        max_arq_attempts=1,
        power_levels=1,
        relay_copies=1,
        rescue_enabled=False,
        power_step_db=0,
        expected_pdr=0.72,
        energy_factor=1.0,
        description="Minimal reliability, maximum energy savings (like basic LEACH)"
    ),
    ReliabilityLevel.LOW_POWER: ReliabilityProfile(
        name="low_power",
        max_arq_attempts=2,
        power_levels=2,
        relay_copies=1,
        rescue_enabled=False,
        power_step_db=2.0,
        expected_pdr=0.80,
        energy_factor=1.8,
        description="Low power with basic retry (like I-LEACH)"
    ),
    ReliabilityLevel.BALANCED: ReliabilityProfile(
        name="balanced",
        max_arq_attempts=3,
        power_levels=3,
        relay_copies=2,
        rescue_enabled=False,
        power_step_db=2.0,
        expected_pdr=0.88,
        energy_factor=2.8,
        description="Balanced reliability and energy (recommended default)"
    ),
    ReliabilityLevel.HIGH_RELIABILITY: ReliabilityProfile(
        name="high_reliability",
        max_arq_attempts=5,
        power_levels=4,
        relay_copies=3,
        rescue_enabled=True,
        power_step_db=2.0,
        expected_pdr=0.93,
        energy_factor=4.5,
        description="High reliability for critical applications"
    ),
    ReliabilityLevel.ULTRA_RELIABLE: ReliabilityProfile(
        name="ultra_reliable",
        max_arq_attempts=7,
        power_levels=5,
        relay_copies=4,
        rescue_enabled=True,
        power_step_db=2.0,
        expected_pdr=0.96,
        energy_factor=6.5,
        description="Maximum reliability (original AERIS)"
    ),
}


class AdaptiveReliabilityManager:
    """
    Adaptive Reliability Manager

    Dynamically adjusts reliability mechanisms based on:
    1. Current network energy state
    2. Required QoS level
    3. Channel conditions
    4. Application requirements

    This allows AERIS to compete with SOTA algorithms on energy efficiency
    while maintaining its reliability advantage when needed.
    """

    def __init__(self,
                 default_level: ReliabilityLevel = ReliabilityLevel.BALANCED,
                 auto_adapt: bool = True,
                 energy_threshold_low: float = 0.3,
                 energy_threshold_critical: float = 0.15):
        """
        Initialize the Adaptive Reliability Manager.

        Args:
            default_level: Default reliability level
            auto_adapt: Whether to automatically adapt based on network state
            energy_threshold_low: Energy ratio below which to reduce reliability
            energy_threshold_critical: Energy ratio for minimal reliability
        """
        self.default_level = default_level
        self.auto_adapt = auto_adapt
        self.energy_threshold_low = energy_threshold_low
        self.energy_threshold_critical = energy_threshold_critical

        self.current_level = default_level
        self.current_profile = RELIABILITY_PROFILES[default_level]

        # Statistics tracking
        self.profile_usage_count: Dict[ReliabilityLevel, int] = {
            level: 0 for level in ReliabilityLevel
        }
        self.adaptation_history: List[Tuple[float, ReliabilityLevel]] = []

    def get_current_profile(self) -> ReliabilityProfile:
        """Get the current reliability profile"""
        return self.current_profile

    def set_reliability_level(self, level: ReliabilityLevel):
        """Manually set the reliability level"""
        self.current_level = level
        self.current_profile = RELIABILITY_PROFILES[level]
        self.profile_usage_count[level] += 1

    def select_profile_for_conditions(self,
                                       network_energy_ratio: float,
                                       required_pdr: float = 0.85,
                                       channel_quality: float = 0.8,
                                       packet_criticality: float = 0.5) -> ReliabilityProfile:
        """
        Select optimal reliability profile based on current conditions.

        Args:
            network_energy_ratio: Average remaining energy (0-1)
            required_pdr: Minimum required PDR (0-1)
            channel_quality: Current channel quality estimate (0-1)
            packet_criticality: Importance of the packet (0-1)

        Returns:
            Selected ReliabilityProfile
        """
        if not self.auto_adapt:
            return self.current_profile

        # Priority 1: Critical energy state
        if network_energy_ratio < self.energy_threshold_critical:
            selected = ReliabilityLevel.ULTRA_LOW_POWER

        # Priority 2: Low energy state
        elif network_energy_ratio < self.energy_threshold_low:
            if required_pdr > 0.90:
                selected = ReliabilityLevel.BALANCED
            else:
                selected = ReliabilityLevel.LOW_POWER

        # Priority 3: Based on requirements and channel
        else:
            # Combine factors
            reliability_need = max(required_pdr, packet_criticality)
            effective_need = reliability_need / max(channel_quality, 0.1)

            if effective_need < 0.75:
                selected = ReliabilityLevel.LOW_POWER
            elif effective_need < 0.85:
                selected = ReliabilityLevel.BALANCED
            elif effective_need < 0.92:
                selected = ReliabilityLevel.HIGH_RELIABILITY
            else:
                selected = ReliabilityLevel.ULTRA_RELIABLE

        # Update state
        self.current_level = selected
        self.current_profile = RELIABILITY_PROFILES[selected]
        self.profile_usage_count[selected] += 1

        return self.current_profile

    def get_transmission_parameters(self,
                                     network_energy_ratio: float = 1.0,
                                     required_pdr: float = 0.85,
                                     channel_quality: float = 0.8) -> Dict:
        """
        Get transmission parameters based on current conditions.

        Returns a dictionary of parameters for the transmission module.
        """
        profile = self.select_profile_for_conditions(
            network_energy_ratio, required_pdr, channel_quality
        )

        return {
            'max_retries': profile.max_arq_attempts,
            'power_levels': profile.power_levels,
            'power_step_db': profile.power_step_db,
            'use_relay': profile.relay_copies > 1,
            'relay_copies': profile.relay_copies,
            'use_rescue': profile.rescue_enabled,
            'expected_pdr': profile.expected_pdr
        }

    def estimate_energy_consumption(self,
                                    base_tx_energy: float,
                                    profile: Optional[ReliabilityProfile] = None) -> float:
        """
        Estimate energy consumption for a transmission under given profile.

        Args:
            base_tx_energy: Base transmission energy (single transmission)
            profile: Profile to use (or current if None)

        Returns:
            Estimated total energy consumption
        """
        if profile is None:
            profile = self.current_profile

        # Estimate based on expected retries and power escalation
        avg_attempts = 1 + (1 - profile.expected_pdr) * profile.max_arq_attempts
        power_factor = 1 + (profile.power_levels - 1) * 0.15  # Power escalation
        relay_factor = profile.relay_copies
        rescue_factor = 1.2 if profile.rescue_enabled else 1.0

        return base_tx_energy * avg_attempts * power_factor * relay_factor * rescue_factor

    def get_statistics(self) -> Dict:
        """Get usage statistics"""
        total_usage = sum(self.profile_usage_count.values())
        if total_usage == 0:
            total_usage = 1

        return {
            'current_level': self.current_level.value,
            'profile_usage': {
                level.value: count / total_usage
                for level, count in self.profile_usage_count.items()
            },
            'total_adaptations': total_usage
        }

    def reset_statistics(self):
        """Reset usage statistics"""
        self.profile_usage_count = {level: 0 for level in ReliabilityLevel}
        self.adaptation_history = []


class PerNodeReliabilityManager:
    """
    Per-node reliability management for fine-grained control.

    Each node can have its own reliability settings based on:
    - Node's remaining energy
    - Node's link quality to neighbors
    - Node's role (CH, Gateway, regular)
    """

    def __init__(self, base_manager: AdaptiveReliabilityManager):
        self.base_manager = base_manager
        self.node_profiles: Dict[int, ReliabilityLevel] = {}

    def get_node_profile(self, node_id: int,
                         node_energy_ratio: float,
                         node_role: str = 'regular',
                         link_quality: float = 0.8) -> ReliabilityProfile:
        """
        Get reliability profile for a specific node.

        Args:
            node_id: Node identifier
            node_energy_ratio: Node's remaining energy ratio
            node_role: 'regular', 'ch', or 'gateway'
            link_quality: Average link quality to neighbors
        """
        # Role-based adjustments
        if node_role == 'gateway':
            required_pdr = 0.92  # Gateways need higher reliability
        elif node_role == 'ch':
            required_pdr = 0.88
        else:
            required_pdr = 0.82

        profile = self.base_manager.select_profile_for_conditions(
            network_energy_ratio=node_energy_ratio,
            required_pdr=required_pdr,
            channel_quality=link_quality
        )

        self.node_profiles[node_id] = self.base_manager.current_level
        return profile

    def get_cluster_profile(self,
                            cluster_avg_energy: float,
                            cluster_size: int,
                            ch_link_quality: float) -> ReliabilityProfile:
        """
        Get reliability profile for an entire cluster.

        Balances the needs of all cluster members.
        """
        # Larger clusters need more reliability
        size_factor = min(1.0, cluster_size / 20)
        required_pdr = 0.80 + 0.12 * size_factor

        return self.base_manager.select_profile_for_conditions(
            network_energy_ratio=cluster_avg_energy,
            required_pdr=required_pdr,
            channel_quality=ch_link_quality
        )


# Utility functions for integration with existing AERIS modules

def create_default_manager(auto_adapt: bool = True) -> AdaptiveReliabilityManager:
    """Create a default reliability manager with balanced settings"""
    return AdaptiveReliabilityManager(
        default_level=ReliabilityLevel.BALANCED,
        auto_adapt=auto_adapt
    )


def get_profile_by_name(name: str) -> Optional[ReliabilityProfile]:
    """Get a reliability profile by name string"""
    for level, profile in RELIABILITY_PROFILES.items():
        if profile.name == name or level.value == name:
            return profile
    return None


def compare_profiles() -> str:
    """Generate a comparison table of all profiles"""
    lines = [
        "| Profile | ARQ | Power Levels | Relay | Rescue | Expected PDR | Energy Factor |",
        "|---------|-----|--------------|-------|--------|--------------|---------------|"
    ]

    for level, profile in RELIABILITY_PROFILES.items():
        lines.append(
            f"| {profile.name:17} | {profile.max_arq_attempts:3} | "
            f"{profile.power_levels:12} | {profile.relay_copies:5} | "
            f"{'Yes' if profile.rescue_enabled else 'No':6} | "
            f"{profile.expected_pdr:.2f}         | {profile.energy_factor:.1f}x          |"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    # Demo usage
    print("AERIS Adaptive Reliability Manager")
    print("=" * 50)
    print()
    print(compare_profiles())
    print()

    # Create manager
    manager = create_default_manager()

    # Test different scenarios
    scenarios = [
        {"name": "Full energy, good channel", "energy": 0.9, "channel": 0.9, "pdr": 0.85},
        {"name": "Low energy, good channel", "energy": 0.25, "channel": 0.9, "pdr": 0.85},
        {"name": "Critical energy", "energy": 0.10, "channel": 0.8, "pdr": 0.80},
        {"name": "High reliability need", "energy": 0.7, "channel": 0.7, "pdr": 0.95},
        {"name": "Poor channel", "energy": 0.8, "channel": 0.4, "pdr": 0.85},
    ]

    print("\nScenario-based Profile Selection:")
    print("-" * 50)
    for scenario in scenarios:
        profile = manager.select_profile_for_conditions(
            network_energy_ratio=scenario["energy"],
            required_pdr=scenario["pdr"],
            channel_quality=scenario["channel"]
        )
        print(f"{scenario['name']:30} -> {profile.name} (PDR: {profile.expected_pdr:.0%})")

    print("\n" + "=" * 50)
    print("Statistics:", manager.get_statistics())
