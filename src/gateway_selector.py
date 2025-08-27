#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gateway CH selector for AETHER

Select K gateway cluster-heads (CHs) to act as landmarks for inter-cluster
aggregation before sending to the base station (BS). The scoring combines
(distance to BS), (CH centrality among CH graph), and (optional link quality).

Author: Enhanced EEHFR Research Team
Date: 2025-08-24
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
import math

@dataclass
class GatewayConfig:
    k: int = 1
    w_dist_bs: float = -0.7   # closer to BS better (negative weight on normalized distance)
    w_centrality: float = 0.3 # higher centrality among CHs better
    w_link: float = 0.0       # placeholder for mean link quality if available

class GatewaySelector:
    def __init__(self, cfg: GatewayConfig):
        self.cfg = cfg

    def _normalize(self, x: float, lo: float, hi: float) -> float:
        if hi - lo <= 1e-12:
            return 0.0
        return max(0.0, min(1.0, (x - lo) / (hi - lo)))

    def select_gateways(self, chs: List, bs_pos: Tuple[float, float]) -> List[int]:
        """
        Select top-k gateway CH ids.
        Each CH in `chs` is expected to have attributes: id, x, y, lqi (optional)
        """
        if not chs:
            return []
        # distances to BS
        dists = [math.hypot(ch.x - bs_pos[0], ch.y - bs_pos[1]) for ch in chs]
        d_min, d_max = (min(dists), max(dists)) if dists else (0.0, 1.0)
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
        for ch, d in zip(chs, dists):
            d_norm = self._normalize(d, d_min, d_max)
            c_norm = self._normalize(centralities[ch.id], c_min, c_max)
            link = getattr(ch, 'lqi', 0.0)
            s = (self.cfg.w_dist_bs * d_norm +
                 self.cfg.w_centrality * c_norm +
                 self.cfg.w_link * link)
            scored.append((s, ch.id))
        scored.sort(reverse=True)  # higher score better
        k = max(1, min(self.cfg.k, len(scored)))
        return [cid for _, cid in scored[:k]]

