#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Objective Gateway Selector for AERIS Protocol
====================================================
Enhanced gateway selection using multi-objective optimization inspired by PSO-WSN.

Extends the original gateway selector with:
1. Energy efficiency term (from PSO-WSN)
2. Load balance term (from PSO-WSN coverage concept)
3. Coverage contribution term
4. Adaptive weight adjustment

Original metrics retained:
- Distance to BS
- Centrality among CHs
- Link quality

Author: AERIS Research Team
Date: 2026-01-04
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Sequence, Union, Optional
import math
import numpy as np


@dataclass
class MultiObjectiveGatewayConfig:
    """Configuration for multi-objective gateway selection"""
    k: int = 1

    # Original weights
    w_dist_bs: float = 0.20       # Closer to BS is better
    w_centrality: float = 0.15    # Higher centrality among CHs is better
    w_link: float = 0.15          # Better link quality is better

    # New weights from PSO analysis
    w_energy: float = 0.20        # Higher remaining energy is better
    w_balance: float = 0.15       # Better load balance is better
    w_coverage: float = 0.15      # Higher coverage contribution is better

    # Adaptive behavior
    auto_adjust_weights: bool = True
    energy_priority_threshold: float = 0.3  # Below this, prioritize energy

    def normalize_weights(self):
        """Ensure weights sum to 1"""
        total = (self.w_dist_bs + self.w_centrality + self.w_link +
                 self.w_energy + self.w_balance + self.w_coverage)
        if total > 0:
            self.w_dist_bs /= total
            self.w_centrality /= total
            self.w_link /= total
            self.w_energy /= total
            self.w_balance /= total
            self.w_coverage /= total


@dataclass
class GatewayCandidate:
    """Represents a gateway candidate with all metrics"""
    node_id: int
    x: float
    y: float
    energy: float = 1.0
    initial_energy: float = 1.0
    lqi: float = 0.8
    cluster_size: int = 1
    coverage_area: float = 0.0

    # Computed scores
    dist_to_bs: float = 0.0
    centrality: float = 0.0
    energy_ratio: float = 1.0
    balance_score: float = 0.0
    coverage_score: float = 0.0
    total_score: float = 0.0


class MultiObjectiveGatewaySelector:
    """
    Multi-Objective Gateway Selector

    Uses a weighted combination of objectives inspired by PSO-WSN:
    - Minimize distance to base station
    - Maximize centrality among cluster heads
    - Maximize link quality
    - Maximize energy efficiency (new)
    - Maximize load balance (new)
    - Maximize coverage contribution (new)
    """

    def __init__(self, cfg: Optional[MultiObjectiveGatewayConfig] = None):
        self.cfg = cfg or MultiObjectiveGatewayConfig()
        self.cfg.normalize_weights()

        # Statistics
        self.selection_history: List[List[int]] = []
        self.score_history: List[Dict] = []

    def _normalize(self, x: float, lo: float, hi: float) -> float:
        """Normalize value to [0, 1] range"""
        if hi - lo <= 1e-12:
            return 0.5  # Return middle if no variance
        return max(0.0, min(1.0, (x - lo) / (hi - lo)))

    def _resolve_bs_positions(self,
                              bs_pos: Union[Tuple[float, float],
                                           Sequence[Tuple[float, float]],
                                           Sequence[float]]) -> List[Tuple[float, float]]:
        """Parse base station position(s)"""
        if isinstance(bs_pos, (list, tuple)):
            if len(bs_pos) >= 1 and isinstance(bs_pos[0], (list, tuple)):
                positions = []
                for item in bs_pos:
                    try:
                        positions.append((float(item[0]), float(item[1])))
                    except Exception:
                        continue
                if positions:
                    return positions
            if len(bs_pos) == 2 and all(isinstance(val, (int, float)) for val in bs_pos):
                return [(float(bs_pos[0]), float(bs_pos[1]))]
        raise ValueError("bs_pos must be a tuple (x, y) or a sequence of such tuples")

    def _compute_distances(self,
                           chs: List,
                           bs_positions: List[Tuple[float, float]]) -> Dict[int, float]:
        """Compute minimum distance from each CH to any BS"""
        distances = {}
        for ch in chs:
            ch_x = getattr(ch, 'x', 0.0)
            ch_y = getattr(ch, 'y', 0.0)
            min_dist = min(
                math.hypot(ch_x - bx, ch_y - by)
                for bx, by in bs_positions
            )
            distances[getattr(ch, 'id', id(ch))] = min_dist
        return distances

    def _compute_centralities(self, chs: List) -> Dict[int, float]:
        """Compute centrality of each CH among other CHs"""
        centralities = {}
        for i, ch in enumerate(chs):
            ch_x = getattr(ch, 'x', 0.0)
            ch_y = getattr(ch, 'y', 0.0)
            ch_id = getattr(ch, 'id', id(ch))

            acc = 0.0
            cnt = 0
            for j, other in enumerate(chs):
                if i == j:
                    continue
                other_x = getattr(other, 'x', 0.0)
                other_y = getattr(other, 'y', 0.0)
                acc += math.hypot(ch_x - other_x, ch_y - other_y)
                cnt += 1

            mean_d = (acc / cnt) if cnt > 0 else 1.0
            centralities[ch_id] = 1.0 / (mean_d + 1e-9)

        return centralities

    def _compute_energy_scores(self, chs: List) -> Dict[int, float]:
        """Compute energy ratio for each CH"""
        scores = {}
        for ch in chs:
            ch_id = getattr(ch, 'id', id(ch))
            energy = getattr(ch, 'energy', 1.0)
            initial = getattr(ch, 'initial_energy', getattr(ch, 'E0', 1.0))
            if initial <= 0:
                initial = 1.0
            scores[ch_id] = energy / initial
        return scores

    def _compute_load_balance_scores(self, chs: List, total_nodes: int) -> Dict[int, float]:
        """
        Compute load balance scores.

        A CH is better if its cluster size is close to the optimal size.
        Inspired by PSO-WSN's cluster balance term.
        """
        if len(chs) == 0:
            return {}

        optimal_size = max(1, total_nodes / len(chs))
        scores = {}

        for ch in chs:
            ch_id = getattr(ch, 'id', id(ch))
            cluster_size = getattr(ch, 'cluster_size', 1)
            # Score is higher when closer to optimal size
            deviation = abs(cluster_size - optimal_size)
            scores[ch_id] = 1.0 / (1.0 + deviation / optimal_size)

        return scores

    def _compute_coverage_scores(self, chs: List, area_size: float = 100.0) -> Dict[int, float]:
        """
        Compute coverage contribution of each CH.

        A CH that covers unique area (not overlapping with others) scores higher.
        Inspired by PSO-WSN's coverage term.
        """
        if len(chs) == 0:
            return {}

        # Estimate coverage radius based on cluster size and area
        avg_coverage_radius = math.sqrt(area_size / (len(chs) * math.pi))

        scores = {}
        for i, ch in enumerate(chs):
            ch_id = getattr(ch, 'id', id(ch))
            ch_x = getattr(ch, 'x', 0.0)
            ch_y = getattr(ch, 'y', 0.0)

            # Count overlapping CHs
            overlap_count = 0
            for j, other in enumerate(chs):
                if i == j:
                    continue
                other_x = getattr(other, 'x', 0.0)
                other_y = getattr(other, 'y', 0.0)
                dist = math.hypot(ch_x - other_x, ch_y - other_y)
                if dist < 2 * avg_coverage_radius:
                    overlap_count += 1

            # Less overlap = higher coverage contribution
            scores[ch_id] = 1.0 / (1.0 + overlap_count)

        return scores

    def _adjust_weights_for_network_state(self, avg_energy_ratio: float):
        """
        Dynamically adjust weights based on network energy state.

        When energy is low, prioritize energy efficiency over other metrics.
        """
        if not self.cfg.auto_adjust_weights:
            return

        if avg_energy_ratio < self.cfg.energy_priority_threshold:
            # Low energy: increase energy weight, decrease others
            boost = (self.cfg.energy_priority_threshold - avg_energy_ratio) / self.cfg.energy_priority_threshold
            self.cfg.w_energy = min(0.5, self.cfg.w_energy + 0.2 * boost)
            # Reduce other weights proportionally
            reduction_factor = 1.0 - 0.2 * boost / (1 - self.cfg.w_energy)
            self.cfg.w_dist_bs *= reduction_factor
            self.cfg.w_centrality *= reduction_factor
            self.cfg.w_link *= reduction_factor
            self.cfg.w_balance *= reduction_factor
            self.cfg.w_coverage *= reduction_factor
            self.cfg.normalize_weights()

    def select_gateways(self,
                        chs: List,
                        bs_pos: Union[Tuple[float, float], Sequence[Tuple[float, float]]],
                        total_nodes: int = 100,
                        area_size: float = 100.0) -> List[int]:
        """
        Select top-k gateway CH ids using multi-objective optimization.

        Args:
            chs: List of cluster head objects with attributes (id, x, y, energy, lqi, cluster_size)
            bs_pos: Base station position(s)
            total_nodes: Total number of nodes in network
            area_size: Network area size for coverage calculation

        Returns:
            List of selected gateway CH ids
        """
        if not chs:
            return []

        try:
            bs_positions = self._resolve_bs_positions(bs_pos)
        except ValueError:
            bs_positions = [(0.0, 0.0)]

        # Compute all metrics
        distances = self._compute_distances(chs, bs_positions)
        centralities = self._compute_centralities(chs)
        energy_scores = self._compute_energy_scores(chs)
        balance_scores = self._compute_load_balance_scores(chs, total_nodes)
        coverage_scores = self._compute_coverage_scores(chs, area_size)

        # Get min/max for normalization
        d_vals = list(distances.values())
        d_min, d_max = min(d_vals), max(d_vals)

        c_vals = list(centralities.values())
        c_min, c_max = min(c_vals), max(c_vals)

        e_vals = list(energy_scores.values())
        e_min, e_max = min(e_vals), max(e_vals)

        b_vals = list(balance_scores.values())
        b_min, b_max = min(b_vals), max(b_vals)

        cov_vals = list(coverage_scores.values())
        cov_min, cov_max = min(cov_vals), max(cov_vals)

        # Adjust weights if needed
        avg_energy = sum(e_vals) / len(e_vals) if e_vals else 1.0
        self._adjust_weights_for_network_state(avg_energy)

        # Score each CH
        scored = []
        for ch in chs:
            ch_id = getattr(ch, 'id', id(ch))

            # Normalize each metric
            d_norm = 1.0 - self._normalize(distances[ch_id], d_min, d_max)  # Invert: smaller is better
            c_norm = self._normalize(centralities[ch_id], c_min, c_max)
            e_norm = self._normalize(energy_scores[ch_id], e_min, e_max)
            b_norm = self._normalize(balance_scores[ch_id], b_min, b_max)
            cov_norm = self._normalize(coverage_scores[ch_id], cov_min, cov_max)
            lqi = getattr(ch, 'lqi', 0.8)

            # Weighted sum (multi-objective fitness like PSO-WSN)
            total_score = (
                self.cfg.w_dist_bs * d_norm +
                self.cfg.w_centrality * c_norm +
                self.cfg.w_link * lqi +
                self.cfg.w_energy * e_norm +
                self.cfg.w_balance * b_norm +
                self.cfg.w_coverage * cov_norm
            )

            scored.append((total_score, ch_id, {
                'dist': d_norm,
                'centrality': c_norm,
                'energy': e_norm,
                'balance': b_norm,
                'coverage': cov_norm,
                'lqi': lqi
            }))

        # Sort by score (higher is better)
        scored.sort(reverse=True, key=lambda x: x[0])

        # Select top-k
        k = max(1, min(self.cfg.k, len(scored)))
        selected = [ch_id for _, ch_id, _ in scored[:k]]

        # Record history
        self.selection_history.append(selected)
        self.score_history.append({
            'selected': selected,
            'scores': {ch_id: score for score, ch_id, _ in scored[:k]},
            'details': {ch_id: details for _, ch_id, details in scored[:k]}
        })

        return selected

    def get_selection_statistics(self) -> Dict:
        """Get statistics about gateway selections"""
        if not self.selection_history:
            return {'total_selections': 0}

        # Count how often each gateway was selected
        gateway_counts: Dict[int, int] = {}
        for selection in self.selection_history:
            for gw_id in selection:
                gateway_counts[gw_id] = gateway_counts.get(gw_id, 0) + 1

        return {
            'total_selections': len(self.selection_history),
            'gateway_frequency': gateway_counts,
            'current_weights': {
                'distance': self.cfg.w_dist_bs,
                'centrality': self.cfg.w_centrality,
                'link_quality': self.cfg.w_link,
                'energy': self.cfg.w_energy,
                'balance': self.cfg.w_balance,
                'coverage': self.cfg.w_coverage
            }
        }


# Factory function for easy creation
def create_multi_objective_gateway_selector(
    k: int = 1,
    auto_adjust: bool = True
) -> MultiObjectiveGatewaySelector:
    """Create a multi-objective gateway selector with default settings"""
    cfg = MultiObjectiveGatewayConfig(k=k, auto_adjust_weights=auto_adjust)
    return MultiObjectiveGatewaySelector(cfg)


# Backward compatible wrapper
class GatewayConfig:
    """Backward compatible config (maps to MultiObjectiveGatewayConfig)"""
    def __init__(self, k: int = 1, w_dist_bs: float = -0.7,
                 w_centrality: float = 0.3, w_link: float = 0.0):
        self.k = k
        self.w_dist_bs = w_dist_bs
        self.w_centrality = w_centrality
        self.w_link = w_link


class GatewaySelector:
    """Backward compatible wrapper using multi-objective selector"""

    def __init__(self, cfg: GatewayConfig):
        self.cfg = cfg
        mo_cfg = MultiObjectiveGatewayConfig(
            k=cfg.k,
            w_dist_bs=abs(cfg.w_dist_bs) / 2,  # Convert from negative weight
            w_centrality=cfg.w_centrality,
            w_link=cfg.w_link,
            w_energy=0.15,
            w_balance=0.1,
            w_coverage=0.1,
            auto_adjust_weights=False
        )
        self._selector = MultiObjectiveGatewaySelector(mo_cfg)

    def select_gateways(self, chs: List,
                        bs_pos: Union[Tuple[float, float], Sequence[Tuple[float, float]]]) -> List[int]:
        return self._selector.select_gateways(chs, bs_pos)


if __name__ == "__main__":
    # Demo usage
    print("AERIS Multi-Objective Gateway Selector")
    print("=" * 50)

    # Create test CHs
    class MockCH:
        def __init__(self, id, x, y, energy, lqi, cluster_size):
            self.id = id
            self.x = x
            self.y = y
            self.energy = energy
            self.initial_energy = 1.0
            self.lqi = lqi
            self.cluster_size = cluster_size

    chs = [
        MockCH(0, 20, 30, 0.9, 0.85, 15),  # Good energy, good LQI
        MockCH(1, 50, 50, 0.5, 0.90, 20),  # Medium energy, best LQI
        MockCH(2, 80, 70, 0.3, 0.75, 25),  # Low energy, low LQI
        MockCH(3, 30, 80, 0.8, 0.80, 10),  # Good energy, medium cluster
        MockCH(4, 70, 20, 0.6, 0.95, 30),  # Medium energy, large cluster
    ]

    bs_pos = (50, 100)

    # Test with different k values
    for k in [1, 2, 3]:
        selector = create_multi_objective_gateway_selector(k=k)
        selected = selector.select_gateways(chs, bs_pos, total_nodes=100)
        print(f"\nk={k}: Selected gateways = {selected}")
        stats = selector.get_selection_statistics()
        print(f"  Weights: {stats['current_weights']}")
