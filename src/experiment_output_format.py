#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Experiment Output Format for AERIS
==========================================
GPT DeepSearch recommendation: Ensure all experiment JSON outputs
contain consistent fields for easier analysis and comparison.

Author: AERIS Research Team
Date: 2026-01-27
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class UnifiedMetrics:
    """
    Unified metrics structure for all AERIS experiments.
    GPT DeepSearch: All experiments must output these fields.
    """
    # Core performance metrics
    pdr_end2end: float = 0.0          # End-to-end packet delivery ratio [0,1]
    energy_total_j: float = 0.0       # Total energy consumed (Joules)
    j_per_delivered: float = 0.0      # Energy per successfully delivered packet
    lifetime_rounds: int = 0          # Network lifetime in rounds
    alive_nodes: int = 0              # Number of alive nodes at end

    # Reliability overhead metrics (GPT DeepSearch P0-1)
    retransmission_rate: float = 0.0  # Retransmissions / total transmissions
    power_stepping_rate: float = 0.0  # Power stepping triggers / total transmissions
    neighbor_rescue_rate: float = 0.0 # Neighbor rescue triggers / total transmissions
    alternate_parent_rate: float = 0.0  # Alternate parent usage rate

    # Optional extended metrics
    first_node_death_round: int = 0   # Round when first node died
    half_nodes_death_round: int = 0   # Round when 50% nodes died
    avg_cluster_size: float = 0.0     # Average cluster size
    avg_hop_count: float = 0.0        # Average hop count to BS


@dataclass
class UnifiedExperimentResult:
    """
    Unified experiment result structure.
    GPT DeepSearch: Standardized output format for all experiments.
    """
    # Experiment metadata
    protocol: str = ""                # Protocol name (e.g., "AERIS-R", "LEACH")
    scenario: str = ""                # Scenario name (e.g., "uniform_100", "corridor_200")
    n_nodes: int = 0                  # Number of nodes
    n_rounds: int = 0                 # Number of simulation rounds
    n_replicates: int = 1             # Number of experiment replicates
    seed: int = 42                    # Random seed

    # Metrics
    metrics: Optional[UnifiedMetrics] = None

    # Statistical info (for multi-replicate experiments)
    pdr_mean: float = 0.0
    pdr_std: float = 0.0
    pdr_ci95_low: float = 0.0
    pdr_ci95_high: float = 0.0
    energy_mean: float = 0.0
    energy_std: float = 0.0

    # Timestamp
    timestamp: str = ""

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = UnifiedMetrics()
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


def create_unified_result(
    protocol: str,
    scenario: str,
    n_nodes: int,
    n_rounds: int,
    pdr: float,
    energy: float,
    alive_nodes: int,
    seed: int = 42,
    n_replicates: int = 1,
    reliability_stats: Optional[Dict] = None,
    **kwargs
) -> UnifiedExperimentResult:
    """
    Create a unified experiment result from raw data.

    Args:
        protocol: Protocol name
        scenario: Scenario description
        n_nodes: Number of nodes
        n_rounds: Number of rounds
        pdr: Packet delivery ratio
        energy: Total energy consumed
        alive_nodes: Alive nodes at end
        seed: Random seed
        n_replicates: Number of replicates
        reliability_stats: Optional reliability overhead stats
        **kwargs: Additional metrics

    Returns:
        UnifiedExperimentResult instance
    """
    # Calculate J/packet delivered
    total_packets = n_nodes * n_rounds
    delivered_packets = int(total_packets * pdr)
    j_per_delivered = energy / max(delivered_packets, 1)

    metrics = UnifiedMetrics(
        pdr_end2end=pdr,
        energy_total_j=energy,
        j_per_delivered=j_per_delivered,
        lifetime_rounds=n_rounds,
        alive_nodes=alive_nodes,
    )

    # Add reliability stats if provided
    if reliability_stats:
        metrics.retransmission_rate = reliability_stats.get('retransmission_rate', 0.0)
        metrics.power_stepping_rate = reliability_stats.get('power_stepping_rate', 0.0)
        metrics.neighbor_rescue_rate = reliability_stats.get('neighbor_rescue_rate', 0.0)
        metrics.alternate_parent_rate = reliability_stats.get('alternate_parent_rate', 0.0)

    # Add any extra metrics from kwargs
    for key, value in kwargs.items():
        if hasattr(metrics, key):
            setattr(metrics, key, value)

    return UnifiedExperimentResult(
        protocol=protocol,
        scenario=scenario,
        n_nodes=n_nodes,
        n_rounds=n_rounds,
        n_replicates=n_replicates,
        seed=seed,
        metrics=metrics,
        pdr_mean=pdr,
        energy_mean=energy,
    )


def to_unified_dict(result: UnifiedExperimentResult) -> Dict[str, Any]:
    """Convert UnifiedExperimentResult to dictionary for JSON serialization."""
    d = asdict(result)
    return d


def save_unified_results(
    results: List[UnifiedExperimentResult],
    filepath: str,
    experiment_name: str = "",
    extra_metadata: Optional[Dict] = None
) -> None:
    """
    Save unified results to JSON file.

    Args:
        results: List of experiment results
        filepath: Output file path
        experiment_name: Name of the experiment batch
        extra_metadata: Additional metadata to include
    """
    output = {
        "experiment_name": experiment_name,
        "generated_at": datetime.now().isoformat(),
        "format_version": "1.0",
        "n_results": len(results),
        "results": [to_unified_dict(r) for r in results],
    }

    if extra_metadata:
        output["metadata"] = extra_metadata

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


def validate_result_fields(result_dict: Dict) -> List[str]:
    """
    Validate that a result dictionary contains all required fields.
    Returns list of missing fields.
    """
    required_fields = [
        'protocol', 'scenario', 'n_nodes', 'n_rounds',
        'metrics.pdr_end2end', 'metrics.energy_total_j',
        'metrics.j_per_delivered', 'metrics.alive_nodes'
    ]

    missing = []
    for field in required_fields:
        parts = field.split('.')
        obj = result_dict
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                missing.append(field)
                break

    return missing


# Convenience function for backward compatibility
def format_legacy_result(legacy_dict: Dict) -> UnifiedExperimentResult:
    """
    Convert legacy result format to unified format.
    GPT DeepSearch: Ensure backward compatibility with existing results.
    """
    # Extract common fields with fallbacks
    protocol = legacy_dict.get('protocol', legacy_dict.get('name', 'unknown'))
    scenario = legacy_dict.get('scenario', legacy_dict.get('topology', 'unknown'))
    n_nodes = legacy_dict.get('n_nodes', legacy_dict.get('nodes', 100))
    n_rounds = legacy_dict.get('n_rounds', legacy_dict.get('rounds', 200))

    # Extract metrics with various possible key names
    pdr = legacy_dict.get('pdr_end2end',
          legacy_dict.get('pdr',
          legacy_dict.get('PDR', 0.0)))

    energy = legacy_dict.get('energy_total_j',
             legacy_dict.get('energy',
             legacy_dict.get('total_energy', 0.0)))

    alive = legacy_dict.get('alive_nodes',
            legacy_dict.get('alive',
            legacy_dict.get('surviving_nodes', 0)))

    seed = legacy_dict.get('seed', 42)

    return create_unified_result(
        protocol=protocol,
        scenario=scenario,
        n_nodes=n_nodes,
        n_rounds=n_rounds,
        pdr=pdr,
        energy=energy,
        alive_nodes=alive,
        seed=seed
    )
