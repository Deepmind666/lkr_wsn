#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fairness and hotspot suppression metrics for AETHER

This module provides lightweight, explainable metrics to discourage
hotspots and improve fairness in cluster-head (CH) utilization and
intra-cluster energy distribution.

Author: Enhanced EEHFR Research Team
Date: 2025-08-23
"""
from __future__ import annotations
from typing import Iterable, Dict


def jain_index(values: Iterable[float]) -> float:
    """Compute Jain's fairness index for a set of non-negative values.
    J = (sum x_i)^2 / (n * sum x_i^2), defined in [0,1].
    Edge cases: if all values are zero -> define J = 1.0 (perfectly equal).
    """
    vals = [max(0.0, float(v)) for v in values]
    n = len(vals)
    if n == 0:
        return 1.0
    s1 = sum(vals)
    s2 = sum(v * v for v in vals)
    if s1 <= 0.0 or s2 <= 0.0:
        return 1.0
    return (s1 * s1) / (n * s2)


def ch_usage_penalty(usage_count: Dict[int, int], ch_id: int, total_rounds: int, target_ratio: float = 0.1) -> float:
    """Compute a penalty for CH over-utilization.
    - usage_count: map of node_id -> times selected as CH
    - ch_id: the current CH node id
    - total_rounds: how many rounds so far (>=1)
    - target_ratio: desired CH duty ~ percentage of rounds a node acts as CH

    Returns a value in [0,1], higher means less fair (more penalty).
    """
    if total_rounds <= 0:
        return 0.0
    used = float(usage_count.get(ch_id, 0)) / float(total_rounds)
    # penalty grows when used > target; linear clamp to [0,1]
    over = max(0.0, used - target_ratio)
    span = max(1e-9, 1.0 - target_ratio)
    return min(1.0, over / span)

