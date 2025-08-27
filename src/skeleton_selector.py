#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skeleton (Backbone) CH selector using PCA principal axis.
Chooses k backbone CHs closest to the principal axis and relatively central.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict
import numpy as np
import math

@dataclass
class SkeletonConfig:
    k: int = 1
    w_axis_proximity: float = 0.7   # closer to axis is better
    w_centrality: float = 0.3       # more central among CHs is better
    d_threshold_ratio: float = 0.15 # allowed connect distance to backbone as ratio of area diagonal
    q_far: float = 0.75             # only CHs beyond this distance quantile to BS may connect to backbone

class SkeletonSelector:
    def __init__(self, cfg: SkeletonConfig):
        self.cfg = cfg

    def _pca_axis(self, pts: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        # pts: N x 2, return mean (mu) and first principal direction (unit vector v)
        mu = pts.mean(axis=0)
        X = pts - mu
        C = X.T @ X / max(1, len(pts)-1)
        vals, vecs = np.linalg.eigh(C)
        v = vecs[:, np.argmax(vals)]
        v = v / (np.linalg.norm(v) + 1e-12)
        return mu, v

    def select_backbone(self, chs: List, bs_pos: Tuple[float, float] | None = None, area_diag: float | None = None) -> List[int]:
        if not chs:
            return []
        pts = np.array([[ch.x, ch.y] for ch in chs], dtype=float)
        mu, v = self._pca_axis(pts)
        # distance to axis
        def dist_to_axis(p):
            u = np.array(p) - mu
            proj = v * (u @ v)
            perp = u - proj
            return float(np.linalg.norm(perp))
        # centrality proxy (inverse mean distance)
        cent: Dict[int,float] = {}
        for i, chi in enumerate(chs):
            s=0.0;c=0
            for j, chj in enumerate(chs):
                if i==j: continue
                s += math.hypot(chi.x - chj.x, chi.y - chj.y)
                c += 1
            mean_d = s/max(1,c)
            cent[chi.id] = 1.0/(mean_d+1e-9)
        c_vals = list(cent.values()); cmin=min(c_vals); cmax=max(c_vals)
        def norm(x,a,b):
            if b-a<=1e-12: return 0.0
            return (x-a)/(b-a)
        scores = []
        dists = [dist_to_axis([ch.x, ch.y]) for ch in chs]
        dmin, dmax = min(dists), max(dists)
        for ch, d in zip(chs, dists):
            axis_score = 1.0 - norm(d, dmin, dmax)  # closer to axis -> higher
            c_norm = norm(cent[ch.id], cmin, cmax)
            s = self.cfg.w_axis_proximity*axis_score + self.cfg.w_centrality*c_norm
            scores.append((s, ch.id))
        scores.sort(reverse=True)
        k = max(1, min(self.cfg.k, len(scores)))
        return [cid for _, cid in scores[:k]]

    def assign_to_backbone(self, chs: List, backbone_ids: List[int], bs_pos: Tuple[float,float], area_diag: float) -> Dict[int, int]:
        """Return mapping ch_id -> backbone_id for CHs allowed to connect under thresholds.
        Only CHs beyond q_far distance quantile to BS and within d_threshold to backbone are assigned.
        """
        if not chs or not backbone_ids:
            return {}
        # Precompute
        bb_map = {ch.id: ch for ch in chs if ch.id in backbone_ids}
        d_th = self.cfg.d_threshold_ratio * area_diag
        # distances to BS
        d_bs = {ch.id: math.hypot(ch.x - bs_pos[0], ch.y - bs_pos[1]) for ch in chs}
        # far threshold by quantile
        distances = sorted(d_bs.values())
        q_idx = int(max(0, min(len(distances)-1, round(self.cfg.q_far*(len(distances)-1)))))
        far_th = distances[q_idx]
        assign: Dict[int,int] = {}
        for ch in chs:
            if d_bs[ch.id] < far_th:
                continue
            # find nearest backbone
            bb = min(bb_map.values(), key=lambda b: math.hypot(ch.x - b.x, ch.y - b.y))
            d = math.hypot(ch.x - bb.x, ch.y - bb.y)
            if d <= d_th:
                assign[ch.id] = bb.id
        return assign

