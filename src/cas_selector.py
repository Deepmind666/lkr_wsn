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

Author: AERIS Research Team
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

    # Rule-based trigger controls (explicit mode activation)
    rule_override: bool = True
    chain_density_threshold: float = 0.6
    chain_radius_threshold: float = 0.45
    chain_dist_min: float = 0.3
    chain_dist_max: float = 0.6
    twohop_dist_threshold: float = 0.6
    twohop_link_max: float = 0.55

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
    # 设计说明: 三种模式基于dist_bs区分
    # dist_bs < 0.3: DIRECT优势（近距离直传）
    # 0.3 <= dist_bs < 0.5: 过渡区（DIRECT/CHAIN/TWOHOP竞争）
    # dist_bs >= 0.5: TWO_HOP优势（远距离中继）
    # DIRECT: 适合近距离、高链路质量场景 - 能耗优化版
    w_direct_energy: float = 0.35       # 提高能量权重，鼓励节能
    w_direct_link: float = 0.65         # 高链路质量时优先DIRECT
    w_direct_dist_bs: float = -0.25     # 减少距离惩罚，扩大DIRECT适用范围
    w_direct_radius: float = -0.05      # 减少半径惩罚
    w_direct_density: float = 0.10
    w_direct_fair: float = -0.05

    # CHAIN: 适合中距离、中等密度场景
    w_chain_energy: float = 0.30
    w_chain_link: float = 0.40          # 提高链路权重
    w_chain_dist_bs: float = 0.20       # 提高距离偏好
    w_chain_radius: float = 0.20
    w_chain_density: float = 0.20       # 提高密度权重
    w_chain_fair: float = -0.05

    # TWO_HOP: 仅在远距离、低链路质量时使用
    w_twohop_energy: float = 0.20       # 降低能量权重
    w_twohop_link: float = 0.25         # 降低链路权重
    w_twohop_dist_bs: float = 0.50      # 远距离时强激活
    w_twohop_radius: float = 0.15
    w_twohop_density: float = 0.05
    w_twohop_fair: float = -0.05

    # Distance threshold heuristic for two-hop activation (normalized)
    twohop_tail_threshold: float = 0.6


class CASSelector:
    def __init__(self, config: Optional[CASConfig] = None):
        self.cfg = config or CASConfig()
        # 修复: EMA初始值设为None，首次调用时用实际分数初始化
        # 避免初始值为0导致首次获胜模式持续主导
        self._ema_scores: Dict[CASMode, float] = {
            CASMode.DIRECT: None,
            CASMode.CHAIN: None,
            CASMode.TWO_HOP: None,
        }
        self._ema_initialized: bool = False
        self._last_mode: Optional[CASMode] = None
        # Stage-adaptive weight overrides (GPT DeepSearch recommendation)
        self._stage_weights: Optional[Dict[str, float]] = None
        # Mode switching history for dynamic uncertainty penalty
        self._mode_history: list = []
        self._max_history_len: int = 10
        # Diagnostics for last decision
        self.last_decision_meta: Dict[str, Optional[str]] = {}

    @staticmethod
    def _clip01(x: float) -> float:
        return 0.0 if math.isnan(x) else max(0.0, min(1.0, x))

    def set_stage_weights(self, weights: Dict[str, float]) -> None:
        """
        Set stage-adaptive weights from get_stage_adaptive_weights().
        GPT DeepSearch recommendation: Allow CAS weights to be overridden
        by stage-aware adaptive weights for better environment adaptation.

        Args:
            weights: Dict with keys 'energy', 'reliability', 'distance'
        """
        self._stage_weights = weights

    def _get_dynamic_lambda_uncertainty(self) -> float:
        """
        Calculate dynamic uncertainty penalty based on mode switching frequency.
        GPT DeepSearch recommendation: Adjust penalty based on switching history.

        Returns:
            Dynamic lambda_uncertainty value
        """
        if len(self._mode_history) < 2:
            return self.cfg.lambda_uncertainty

        # Count mode switches in recent history
        switches = sum(1 for i in range(1, len(self._mode_history))
                      if self._mode_history[i] != self._mode_history[i-1])
        switch_rate = switches / (len(self._mode_history) - 1)

        # High switch rate -> increase penalty to stabilize
        # Low switch rate -> decrease penalty to allow adaptation
        base_lambda = self.cfg.lambda_uncertainty
        if switch_rate > 0.5:
            # Frequent oscillation: increase penalty
            return min(1.0, base_lambda * (1.0 + switch_rate))
        elif switch_rate < 0.2:
            # Stable: allow more responsiveness
            return max(0.0, base_lambda * 0.5)
        return base_lambda

    def _apply_stage_weight_adjustment(self, f: Dict[str, float]) -> Dict[str, float]:
        """
        Apply stage-adaptive weight adjustments to features.
        GPT DeepSearch: Adjust CAS decision based on network stage.
        """
        if self._stage_weights is None:
            return f

        adjusted = f.copy()
        # Stage weights influence feature importance
        energy_w = self._stage_weights.get('energy', 0.4)
        reliability_w = self._stage_weights.get('reliability', 0.4)

        # Early stage (energy priority): boost energy feature
        # Late stage (reliability priority): boost link quality
        if energy_w > 0.5:
            adjusted['energy'] = min(1.0, f['energy'] * 1.2)
        if reliability_w > 0.5:
            adjusted['link'] = min(1.0, f['link'] * 1.2)

        return adjusted

    def _select_rule_mode(self, f: Dict[str, float]) -> Tuple[Optional[CASMode], Optional[str]]:
        """
        Rule-based trigger to ensure CHAIN/TWO_HOP can activate in extreme conditions.
        Uses raw normalized features (before stage scaling).
        """
        # TWO_HOP for far distance or long tail with weak link quality
        if f["dist_bs"] >= self.cfg.twohop_dist_threshold and f["link"] <= self.cfg.twohop_link_max:
            return CASMode.TWO_HOP, "twohop_far_low_link"
        if f["tail_max"] >= self.cfg.twohop_tail_threshold and f["link"] <= self.cfg.twohop_link_max:
            return CASMode.TWO_HOP, "twohop_tail_low_link"

        # CHAIN for mid distance, high density, larger radius
        if (f["density"] >= self.cfg.chain_density_threshold and
                f["radius"] >= self.cfg.chain_radius_threshold and
                self.cfg.chain_dist_min <= f["dist_bs"] <= self.cfg.chain_dist_max):
            return CASMode.CHAIN, "chain_dense_mid"

        return None, None

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
        # 修复: 首次调用时用实际分数初始化，避免0值主导
        if prev is None:
            newv = score
        else:
            newv = a * score + (1 - a) * prev
        self._ema_scores[mode] = newv
        return newv

    def select_mode(self, features: Dict[str, float]) -> Tuple[CASMode, float, Dict[CASMode, float]]:
        """
        Select a mode based on normalized features in [0,1].
        features keys: energy, link, dist_bs, radius, density, fairness, tail_max(optional)
        Returns: (mode, confidence, scores)

        GPT DeepSearch enhancements:
        - Stage-adaptive weight adjustment
        - Dynamic uncertainty penalty based on switching history
        """
        # Guard & clip
        f_raw = {k: self._clip01(float(features.get(k, 0.0))) for k in [
            "energy", "link", "dist_bs", "radius", "density", "fairness"
        ]}
        f_raw["tail_max"] = self._clip01(float(features.get("tail_max", 0.0)))

        # Apply stage-adaptive weight adjustment (GPT DeepSearch)
        f = self._apply_stage_weight_adjustment(f_raw)

        # Rule-based trigger (uses raw features)
        rule_mode, rule_reason = self._select_rule_mode(f_raw)

        s_direct = self._ema_update(CASMode.DIRECT, self._score_direct(f))
        s_chain  = self._ema_update(CASMode.CHAIN,  self._score_chain(f))
        s_twohop = self._ema_update(CASMode.TWO_HOP, self._score_twohop(f))

        scores = {
            CASMode.DIRECT: s_direct,
            CASMode.CHAIN: s_chain,
            CASMode.TWO_HOP: s_twohop,
        }

        # Uncertainty penalty with dynamic lambda (GPT DeepSearch)
        mean_f = (f["energy"] + f["link"] + f["dist_bs"] + f["radius"] + f["density"]) / 5.0
        var_proxy = (
            (f["energy"] - mean_f) ** 2 +
            (f["link"] - mean_f) ** 2 +
            (f["dist_bs"] - mean_f) ** 2 +
            (f["radius"] - mean_f) ** 2 +
            (f["density"] - mean_f) ** 2
        ) / 5.0
        confidence = 1.0 - min(1.0, math.sqrt(var_proxy))

        # Use dynamic lambda based on switching history (symmetrical penalty)
        dynamic_lambda = self._get_dynamic_lambda_uncertainty()
        if dynamic_lambda > 0.0 and confidence < self.cfg.uncertainty_conf_threshold:
            penalty = min(1.0, dynamic_lambda * (1.0 - confidence))
            mean_score = (scores[CASMode.DIRECT] + scores[CASMode.CHAIN] + scores[CASMode.TWO_HOP]) / 3.0
            for m in list(scores.keys()):
                scores[m] = scores[m] * (1.0 - penalty) + mean_score * penalty

        # Choose max score; rule-based override can force CHAIN/TWO_HOP
        score_winner = max(scores, key=scores.get)
        chosen = score_winner
        if rule_mode is not None and self.cfg.rule_override:
            chosen = rule_mode
        elif self._last_mode is not None and confidence < self.cfg.min_confidence:
            chosen = self._last_mode

        # Update mode history for dynamic penalty calculation
        self._mode_history.append(chosen)
        if len(self._mode_history) > self._max_history_len:
            self._mode_history.pop(0)

        self._last_mode = chosen

        # Store diagnostics for caller
        self.last_decision_meta = {
            'rule_triggered': rule_mode.value if rule_mode else None,
            'rule_reason': rule_reason,
            'score_winner': score_winner.value,
            'rule_override': bool(rule_mode and self.cfg.rule_override),
        }

        # Normalize scores to [0,1] for logging
        min_s, max_s = min(scores.values()), max(scores.values())
        if max_s - min_s < self.cfg.eps:
            norm_scores = {m: 0.5 for m in scores}
        else:
            norm_scores = {m: (v - min_s) / (max_s - min_s) for m, v in scores.items()}

        return chosen, confidence, norm_scores

    def get_stage_scaling_info(self) -> Dict[str, float]:
        """
        [P0.3] 返回当前阶段特征缩放状态
        用于诊断输出，验证阶段自适应是否生效
        """
        if self._stage_weights is None:
            return {'energy_scaling': 1.0, 'link_scaling': 1.0, 'stage_weights_active': False}
        energy_w = self._stage_weights.get('energy', 0.4)
        reliability_w = self._stage_weights.get('reliability', 0.4)
        return {
            'energy_scaling': 1.2 if energy_w > 0.5 else 1.0,
            'link_scaling': 1.2 if reliability_w > 0.5 else 1.0,
            'stage_weights_active': True,
            'energy_w': energy_w,
            'reliability_w': reliability_w,
        }
