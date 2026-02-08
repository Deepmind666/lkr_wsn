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
    # GPT DeepSearch: Scale-adaptive parameters
    auto_scale: bool = True         # Enable automatic parameter scaling based on network size

class SkeletonSelector:
    def __init__(self, cfg: SkeletonConfig):
        self.cfg = cfg
        # 诊断统计属性 (per RULES.md §5)
        self.backbone_size = 0
        self.total_assignments = 0

    def get_scale_adaptive_params(self, n_nodes: int) -> Tuple[int, float]:
        """
        GPT DeepSearch: Calibrate skeleton parameters based on network scale.
        Adjusts k (backbone count) and d_threshold_ratio for different network sizes.

        Args:
            n_nodes: Total number of nodes in the network

        Returns:
            Tuple of (adjusted_k, adjusted_d_threshold_ratio)
        """
        if not self.cfg.auto_scale:
            return self.cfg.k, self.cfg.d_threshold_ratio

        # Scale-adaptive k: more backbone nodes for larger networks
        # Based on empirical calibration for 50-500 node networks
        if n_nodes <= 50:
            k = max(1, self.cfg.k)
            d_ratio = 0.20  # Larger threshold for small networks
        elif n_nodes <= 100:
            k = max(1, int(self.cfg.k * 1.5))
            d_ratio = 0.18
        elif n_nodes <= 200:
            k = max(2, int(self.cfg.k * 2.0))
            d_ratio = 0.15
        elif n_nodes <= 300:
            k = max(2, int(self.cfg.k * 2.5))
            d_ratio = 0.12
        else:  # 500+ nodes
            k = max(3, int(self.cfg.k * 3.0))
            d_ratio = 0.10  # Tighter threshold for dense networks

        return k, d_ratio

    def _pca_axis(self, pts: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        # pts: N x 2, return mean (mu) and first principal direction (unit vector v)
        mu = pts.mean(axis=0)
        X = pts - mu
        C = X.T @ X / max(1, len(pts)-1)
        vals, vecs = np.linalg.eigh(C)
        v = vecs[:, np.argmax(vals)]
        v = v / (np.linalg.norm(v) + 1e-12)
        return mu, v

    def select_backbone(self, chs: List, bs_pos: Tuple[float, float] | None = None, area_diag: float | None = None, n_total_nodes: int | None = None) -> List[int]:
        """
        Select backbone CHs based on PCA axis proximity and centrality.
        GPT DeepSearch: Added n_total_nodes for scale-adaptive parameter calibration.
        """
        if not chs:
            return []

        # Get scale-adaptive k if n_total_nodes provided
        if n_total_nodes is not None:
            k_adaptive, _ = self.get_scale_adaptive_params(n_total_nodes)
        else:
            k_adaptive = self.cfg.k

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
        k = max(1, min(k_adaptive, len(scores)))
        result = [cid for _, cid in scores[:k]]
        # 更新诊断统计
        self.backbone_size = len(result)
        return result

    def assign_to_backbone(self, chs: List, backbone_ids: List[int], bs_positions: List[Tuple[float,float]], area_diag: float, n_total_nodes: int | None = None) -> Dict[int, int]:
        """Return mapping ch_id -> backbone_id for CHs allowed to connect under thresholds.
        Only CHs beyond q_far distance quantile to BS and within d_threshold to backbone are assigned.
        GPT DeepSearch: Added n_total_nodes for scale-adaptive d_threshold_ratio.
        """
        if not chs or not backbone_ids:
            return {}

        # Get scale-adaptive d_threshold_ratio if n_total_nodes provided
        if n_total_nodes is not None:
            _, d_ratio = self.get_scale_adaptive_params(n_total_nodes)
        else:
            d_ratio = self.cfg.d_threshold_ratio

        # Precompute
        bb_map = {ch.id: ch for ch in chs if ch.id in backbone_ids}
        d_th = d_ratio * area_diag
        # distances to BS
        if not bs_positions:
            bs_positions = [(0.0, 0.0)]
        d_bs = {
            ch.id: min(math.hypot(ch.x - bx, ch.y - by) for bx, by in bs_positions)
            for ch in chs
        }
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
        # 更新诊断统计
        self.total_assignments += len(assign)
        return assign
