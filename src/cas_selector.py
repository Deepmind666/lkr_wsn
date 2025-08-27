#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context-Adaptive Switching (CAS) selector for AETHER

This module provides a lightweight, explainable selector that chooses
one of {Direct, Chain, TwoHop} based on per-round/per-cluster context
features. It is designed to be computationally inexpensive and robust.

Key design choices:
- Linear, interpretable scoring with domain-specific feature shaping
- Confidence term based on feature stability (rolling variance proxy)
- Exponential smoothing for temporal stability (EMA)
- Enables online adaptation without any heavy training

Author: Enhanced EEHFR Research Team
Date: 2025-08-23
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, Optional
import math


class CASMode(str, Enum):
    DIRECT = "direct"      # Members -> CH (single hop to CH)
    CHAIN = "chain"        # Intra-cluster chain aggregation -> CH
    TWO_HOP = "two_hop"    # Members -> relay (closer to CH) -> CH


@dataclass
class CASConfig:
    # Feature normalization guards
    eps: float = 1e-9

    # Exponential smoothing for scores
    ema_alpha: float = 0.2

    # Confidence scaling (penalize switching when uncertainty high)
    min_confidence: float = 0.2

    # Uncertainty penalty (applied to riskier modes under high uncertainty)
    lambda_uncertainty: float = 0.0
    uncertainty_conf_threshold: float = 0.4

    # Weights for each mode (interpretable linear weights)
    # Features assumed in [0,1] after normalization/ shaping
    # f = {
    #   energy,     # higher is better for any mode
    #   link,       # mean link quality (proxy PDR)
    #   dist_bs,    # mean normalized distance to BS (higher = farther)
    #   radius,     # mean normalized cluster radius (higher = larger cluster)
    #   density,    # normalized node density in cluster
    #   fairness    # penalty term in [0,1], higher = less fair currently
    # }
    w_direct_energy: float = 0.6
    w_direct_link: float = 0.6
    w_direct_dist_bs: float = -0.5
    w_direct_radius: float = -0.4
    w_direct_density: float = 0.1
    w_direct_fair: float = -0.2

    w_chain_energy: float = 0.4
    w_chain_link: float = 0.4
    w_chain_dist_bs: float = 0.2
    w_chain_radius: float = 0.6
    w_chain_density: float = 0.4
    w_chain_fair: float = -0.2

    w_twohop_energy: float = 0.5
    w_twohop_link: float = 0.5
    w_twohop_dist_bs: float = 0.5    # helpful for rescuing far tails
    w_twohop_radius: float = 0.2
    w_twohop_density: float = 0.2
    w_twohop_fair: float = -0.2

    # Distance threshold heuristic for two-hop activation (normalized)
    twohop_tail_threshold: float = 0.6


class CASSelector:
    def __init__(self, config: Optional[CASConfig] = None):
        self.cfg = config or CASConfig()
        self._ema_scores: Dict[CASMode, float] = {
            CASMode.DIRECT: 0.0,
            CASMode.CHAIN: 0.0,
            CASMode.TWO_HOP: 0.0,
        }
        self._last_mode: Optional[CASMode] = None

    @staticmethod
    def _clip01(x: float) -> float:
        return 0.0 if math.isnan(x) else max(0.0, min(1.0, x))

    def _score_direct(self, f: Dict[str, float]) -> float:
        c = self.cfg
        return (
            c.w_direct_energy * f["energy"] +
            c.w_direct_link   * f["link"] +
            c.w_direct_dist_bs* f["dist_bs"] +
            c.w_direct_radius * f["radius"] +
            c.w_direct_density* f["density"] +
            c.w_direct_fair   * f["fairness"]
        )

    def _score_chain(self, f: Dict[str, float]) -> float:
        c = self.cfg
        return (
            c.w_chain_energy * f["energy"] +
            c.w_chain_link   * f["link"] +
            c.w_chain_dist_bs* f["dist_bs"] +
            c.w_chain_radius * f["radius"] +
            c.w_chain_density* f["density"] +
            c.w_chain_fair   * f["fairness"]
        )

    def _score_twohop(self, f: Dict[str, float]) -> float:
        c = self.cfg
        base = (
            c.w_twohop_energy * f["energy"] +
            c.w_twohop_link   * f["link"] +
            c.w_twohop_dist_bs* f["dist_bs"] +
            c.w_twohop_radius * f["radius"] +
            c.w_twohop_density* f["density"] +
            c.w_twohop_fair   * f["fairness"]
        )
        # Tail bonus: if max member distance (normalized) is large
        base += 0.2 * max(0.0, f.get("tail_max", 0.0) - self.cfg.twohop_tail_threshold)
        return base

    def _ema_update(self, mode: CASMode, score: float) -> float:
        a = self.cfg.ema_alpha
        prev = self._ema_scores[mode]
        newv = a * score + (1 - a) * prev
        self._ema_scores[mode] = newv
        return newv

    def select_mode(self, features: Dict[str, float]) -> Tuple[CASMode, float, Dict[CASMode, float]]:
        """
        Select a mode based on normalized features in [0,1].
        features keys: energy, link, dist_bs, radius, density, fairness, tail_max(optional)
        Returns: (mode, confidence, scores)
        """
        # Guard & clip
        f = {k: self._clip01(float(features.get(k, 0.0))) for k in [
            "energy", "link", "dist_bs", "radius", "density", "fairness"
        ]}
        f["tail_max"] = self._clip01(float(features.get("tail_max", 0.0)))

        s_direct = self._ema_update(CASMode.DIRECT, self._score_direct(f))
        s_chain  = self._ema_update(CASMode.CHAIN,  self._score_chain(f))
        s_twohop = self._ema_update(CASMode.TWO_HOP, self._score_twohop(f))

        scores = {
            CASMode.DIRECT: s_direct,
            CASMode.CHAIN: s_chain,
            CASMode.TWO_HOP: s_twohop,
        }

        # Uncertainty penalty: penalize riskier modes under high variance
        mean_f = (f["energy"] + f["link"] + f["dist_bs"] + f["radius"] + f["density"]) / 5.0
        var_proxy = (
            (f["energy"] - mean_f) ** 2 +
            (f["link"] - mean_f) ** 2 +
            (f["dist_bs"] - mean_f) ** 2 +
            (f["radius"] - mean_f) ** 2 +
            (f["density"] - mean_f) ** 2
        ) / 5.0
        confidence = 1.0 - min(1.0, math.sqrt(var_proxy))
        if self.cfg.lambda_uncertainty > 0.0 and confidence < self.cfg.uncertainty_conf_threshold:
            penalty = self.cfg.lambda_uncertainty * (1.0 - confidence)
            # Penalize riskier modes more (two-hop > chain), keep direct neutral/slightly boosted
            scores[CASMode.CHAIN] -= 0.5 * penalty
            scores[CASMode.TWO_HOP] -= 1.0 * penalty
            scores[CASMode.DIRECT] += 0.1 * penalty

        # Choose max score; if confidence too low, retain last mode
        chosen = max(scores, key=scores.get)
        if self._last_mode is not None and confidence < self.cfg.min_confidence:
            chosen = self._last_mode
        self._last_mode = chosen

        # Normalize scores to [0,1] for logging
        min_s, max_s = min(scores.values()), max(scores.values())
        if max_s - min_s < self.cfg.eps:
            norm_scores = {m: 0.5 for m in scores}
        else:
            norm_scores = {m: (v - min_s) / (max_s - min_s) for m, v in scores.items()}

        return chosen, confidence, norm_scores

