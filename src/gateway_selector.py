#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gateway CH selector for AETHER

Select K gateway cluster-heads (CHs) to act as landmarks for inter-cluster
aggregation before sending to the base station (BS). The scoring combines
(distance to BS), (CH centrality among CH graph), and (optional link quality).

Author: AERIS Research Team
Date: 2025-08-24
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Sequence, Union, Optional
import math

@dataclass
class GatewayConfig:
    k: int = 1
    w_dist_bs: float = -0.7   # closer to BS better (negative weight on normalized distance)
    w_centrality: float = 0.3 # higher centrality among CHs better
    w_link: float = 0.0       # placeholder for mean link quality if available
    w_energy: float = 0.0     # optional: prefer higher residual energy

class GatewaySelector:
    def __init__(self, cfg: GatewayConfig):
        self.cfg = cfg
        # GPT DeepSearch: Stage-adaptive weight overrides
        self._stage_weights: Optional[Dict[str, float]] = None
        # GPT DeepSearch: Load tracking for load balancing
        self._gateway_loads: Dict[int, int] = {}

    def set_stage_weights(self, weights: Dict[str, float]) -> None:
        """
        Set stage-adaptive weights from get_stage_adaptive_weights().
        GPT DeepSearch: Enable dynamic weight adjustment based on network stage.

        Args:
            weights: Dict with keys 'energy', 'reliability', 'distance'
        """
        self._stage_weights = weights

    def _get_adaptive_weights(self) -> Tuple[float, float, float, float]:
        """
        GPT DeepSearch: Get stage-adaptive scoring weights.
        Returns (w_dist_bs, w_centrality, w_link, w_energy)
        """
        if self._stage_weights is None:
            return (self.cfg.w_dist_bs, self.cfg.w_centrality,
                    self.cfg.w_link, self.cfg.w_energy)

        energy_w = self._stage_weights.get('energy', 0.4)
        reliability_w = self._stage_weights.get('reliability', 0.4)

        # Adjust weights based on stage priorities
        if reliability_w > 0.5:
            # Late stage: prioritize link quality and centrality
            return (-0.5, 0.4, 0.3, 0.2)
        elif energy_w > 0.5:
            # Early stage: prioritize energy and distance
            return (-0.6, 0.2, 0.1, 0.4)
        else:
            # Balanced stage
            return (self.cfg.w_dist_bs, self.cfg.w_centrality,
                    self.cfg.w_link, self.cfg.w_energy)

    def _normalize(self, x: float, lo: float, hi: float) -> float:
        if hi - lo <= 1e-12:
            return 0.0
        return max(0.0, min(1.0, (x - lo) / (hi - lo)))

    def _resolve_bs_positions(self, bs_pos: Union[Tuple[float, float], Sequence[Tuple[float, float]], Sequence[float]]) -> List[Tuple[float, float]]:
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

    def select_gateways(self, chs: List, bs_pos: Union[Tuple[float, float], Sequence[Tuple[float, float]]]) -> List[int]:
        """
        Select top-k gateway CH ids.
        Each CH in `chs` is expected to have attributes: id, x, y, lqi (optional)
        """
        if not chs:
            return []
        try:
            bs_positions = self._resolve_bs_positions(bs_pos)
        except ValueError:
            bs_positions = [(0.0, 0.0)]
        # distances to BS
        dists = [
            min(math.hypot(ch.x - bx, ch.y - by) for bx, by in bs_positions)
            for ch in chs
        ]
        d_min, d_max = (min(dists), max(dists)) if dists else (0.0, 1.0)
        # residual energy ratio
        energy_ratios = []
        for ch in chs:
            current = getattr(ch, 'current_energy', getattr(ch, 'energy', 0.0))
            initial = getattr(ch, 'initial_energy', getattr(ch, 'E0', 1.0))
            if initial <= 0:
                initial = 1.0
            energy_ratios.append(max(0.0, min(1.0, current / initial)))
        e_min, e_max = (min(energy_ratios), max(energy_ratios)) if energy_ratios else (0.0, 1.0)
        # centrality proxy: inverse of mean distance to other CHs
        centralities: Dict[int, float] = {}
        for i, ch in enumerate(chs):
            acc = 0.0
            cnt = 0
            for j, other in enumerate(chs):
                if i == j: continue
                acc += math.hypot(ch.x - other.x, ch.y - other.y)
                cnt += 1
            mean_d = (acc / cnt) if cnt > 0 else 1.0
            centralities[ch.id] = 1.0 / (mean_d + 1e-9)
        c_vals = list(centralities.values())
        c_min, c_max = (min(c_vals), max(c_vals)) if c_vals else (0.0, 1.0)

        scored = []
        # GPT DeepSearch: Use adaptive weights based on network stage
        w_dist, w_cent, w_link, w_energy = self._get_adaptive_weights()

        for ch, d, e_ratio in zip(chs, dists, energy_ratios):
            d_norm = self._normalize(d, d_min, d_max)
            c_norm = self._normalize(centralities[ch.id], c_min, c_max)
            link = getattr(ch, 'gateway_lqi', None)
            if link is None:
                link = getattr(ch, 'lqi', 0.0)
            e_norm = self._normalize(e_ratio, e_min, e_max)
            s = (w_dist * d_norm +
                 w_cent * c_norm +
                 w_link * link +
                 w_energy * e_norm)
            scored.append((s, ch.id))
        scored.sort(reverse=True)  # higher score better
        k = max(1, min(self.cfg.k, len(scored)))
        return [cid for _, cid in scored[:k]]

    def update_gateway_load(self, gateway_id: int, load: int) -> None:
        """
        GPT DeepSearch: Track gateway load for load balancing.
        """
        self._gateway_loads[gateway_id] = load

    def reset_loads(self) -> None:
        """Reset load tracking at start of each round."""
        self._gateway_loads.clear()

    def get_backup_gateway(self, chs: List, primary_gw_id: int,
                           bs_pos: Union[Tuple[float, float], Sequence[Tuple[float, float]]],
                           load_threshold: int = 10) -> Optional[int]:
        """
        GPT DeepSearch: Select backup gateway when primary is overloaded.

        Args:
            chs: List of cluster heads
            primary_gw_id: ID of overloaded primary gateway
            bs_pos: Base station position(s)
            load_threshold: Max load before triggering backup

        Returns:
            Backup gateway ID or None if not needed
        """
        current_load = self._gateway_loads.get(primary_gw_id, 0)
        if current_load < load_threshold:
            return None

        # Find next best gateway excluding primary
        candidates = [ch for ch in chs if ch.id != primary_gw_id]
        if not candidates:
            return None

        try:
            bs_positions = self._resolve_bs_positions(bs_pos)
        except ValueError:
            bs_positions = [(0.0, 0.0)]

        # Score candidates
        best_score = float('-inf')
        best_id = None
        w_dist, w_cent, w_link, w_energy = self._get_adaptive_weights()

        # Calculate centrality for candidates
        centralities: Dict[int, float] = {}
        for i, ch in enumerate(candidates):
            acc = 0.0
            cnt = 0
            for j, other in enumerate(candidates):
                if i == j:
                    continue
                acc += math.hypot(ch.x - other.x, ch.y - other.y)
                cnt += 1
            mean_d = (acc / cnt) if cnt > 0 else 1.0
            centralities[ch.id] = 1.0 / (mean_d + 1e-9)

        c_vals = list(centralities.values()) if centralities else [0.0]
        c_min, c_max = min(c_vals), max(c_vals)

        for ch in candidates:
            d = min(math.hypot(ch.x - bx, ch.y - by) for bx, by in bs_positions)
            current = getattr(ch, 'current_energy', getattr(ch, 'energy', 0.0))
            initial = getattr(ch, 'initial_energy', getattr(ch, 'E0', 1.0))
            e_ratio = current / max(initial, 1e-9)
            link = getattr(ch, 'lqi', 0.5)
            c_norm = self._normalize(centralities.get(ch.id, 0.0), c_min, c_max)

            # Penalize already loaded gateways
            existing_load = self._gateway_loads.get(ch.id, 0)
            load_penalty = 0.1 * existing_load

            score = (w_dist * (1.0 - d / 200.0) +
                     w_cent * c_norm +
                     w_energy * e_ratio +
                     w_link * link - load_penalty)

            if score > best_score:
                best_score = score
                best_id = ch.id

        return best_id


