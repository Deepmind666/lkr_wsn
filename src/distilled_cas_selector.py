#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import time
import math
from typing import Dict, Tuple, Optional

import numpy as np

from cas_selector import CASMode, CASConfig


class DistilledCASSelector:
    def __init__(self, config: Optional[CASConfig] = None):
        self.cfg = config or CASConfig()
        self._last_mode: Optional[CASMode] = None
        self.last_infer_us: float = 0.0

        self._q = 10  # Q10 fixed-point scaling
        self._scale = 1 << self._q

        self.W1 = np.zeros((8, 6), dtype=np.int32)
        self.b1 = np.zeros((8,), dtype=np.int32)
        self.W2 = np.zeros((3, 8), dtype=np.int32)
        self.b2 = np.zeros((3,), dtype=np.int32)

        self._init_default_weights()
        self._maybe_load_weights_from_file()
        self._update_dimensions()

    def _init_default_weights(self) -> None:
        s = self._scale
        W1 = np.zeros((8, 6), dtype=np.int32)
        # Emphasize domain-aligned features per hidden unit
        W1[0, 0] = int(0.8 * s)  # energy
        W1[1, 1] = int(0.8 * s)  # link
        W1[2, 2] = int(0.7 * s)  # dist_bs
        W1[3, 3] = int(0.7 * s)  # radius
        W1[4, 4] = int(0.6 * s)  # density
        W1[5, 5] = int(-0.6 * s) # fairness (penalty)
        # Cross terms
        W1[6, 0] = int(0.4 * s); W1[6, 1] = int(0.4 * s)
        W1[7, 2] = int(0.4 * s); W1[7, 3] = int(0.4 * s)
        self.W1 = W1
        self.b1 = np.zeros((8,), dtype=np.int32)

        W2 = np.zeros((3, 8), dtype=np.int32)
        # direct: energy + link, penalize dist, radius
        W2[0, 0] = int(0.7 * s)
        W2[0, 1] = int(0.7 * s)
        W2[0, 2] = int(-0.5 * s)
        W2[0, 3] = int(-0.4 * s)
        W2[0, 5] = int(-0.2 * s)
        # chain: radius + density, moderate energy/link
        W2[1, 3] = int(0.6 * s)
        W2[1, 4] = int(0.5 * s)
        W2[1, 0] = int(0.3 * s)
        W2[1, 1] = int(0.3 * s)
        W2[1, 5] = int(-0.2 * s)
        # two-hop: dist + link, mild radius, density
        W2[2, 2] = int(0.6 * s)
        W2[2, 1] = int(0.5 * s)
        W2[2, 3] = int(0.2 * s)
        W2[2, 4] = int(0.2 * s)
        W2[2, 5] = int(-0.2 * s)
        self.W2 = W2
        self.b2 = np.zeros((3,), dtype=np.int32)

    def _maybe_load_weights_from_file(self) -> None:
        try:
            data = np.load("data/distilled_cas_weights.npz")
            self.W1 = data["W1"].astype(np.int32)
            self.b1 = data["b1"].astype(np.int32)
            self.W2 = data["W2"].astype(np.int32)
            self.b2 = data["b2"].astype(np.int32)
        except Exception:
            pass
        else:
            self._update_dimensions()

    def _update_dimensions(self) -> None:
        self.hidden_dim = int(self.W1.shape[0])
        self.input_dim = int(self.W1.shape[1])
        if self.input_dim == 6:
            self._feature_order = ["energy", "link", "dist_bs", "radius", "density", "fairness"]
        elif self.input_dim == 7:
            self._feature_order = ["energy", "link", "dist_bs", "radius", "density", "fairness", "tail_max"]
        else:
            # Fallback: use first six known features and pad/truncate as needed
            base = ["energy", "link", "dist_bs", "radius", "density", "fairness", "tail_max"]
            if self.input_dim < len(base):
                self._feature_order = base[: self.input_dim]
            else:
                extra = [f"extra_{i}" for i in range(self.input_dim - len(base))]
                self._feature_order = base + extra

    @staticmethod
    def _clip01(x: float) -> float:
        return 0.0 if math.isnan(x) else max(0.0, min(1.0, x))

    def _confidence(self, f: Dict[str, float]) -> float:
        mean_f = (f["energy"] + f["link"] + f["dist_bs"] + f["radius"] + f["density"]) / 5.0
        var_proxy = (
            (f["energy"] - mean_f) ** 2 +
            (f["link"] - mean_f) ** 2 +
            (f["dist_bs"] - mean_f) ** 2 +
            (f["radius"] - mean_f) ** 2 +
            (f["density"] - mean_f) ** 2
        ) / 5.0
        return 1.0 - min(1.0, math.sqrt(var_proxy))

    def select_mode(self, features: Dict[str, float]) -> Tuple[CASMode, float, Dict[CASMode, float]]:
        t0 = time.perf_counter()

        base = {
            "energy": self._clip01(float(features.get("energy", 0.0))),
            "link": self._clip01(float(features.get("link", 0.0))),
            "dist_bs": self._clip01(float(features.get("dist_bs", 0.0))),
            "radius": self._clip01(float(features.get("radius", 0.0))),
            "density": self._clip01(float(features.get("density", 0.0))),
            "fairness": self._clip01(float(features.get("fairness", 0.0))),
            "tail_max": self._clip01(float(features.get("tail_max", 0.0))),
        }

        x_vals = [self._clip01(float(base.get(name, 0.0))) for name in self._feature_order]
        x = np.array(x_vals, dtype=np.float32)
        xin = (x * self._scale).astype(np.int32)

        h1 = (self.W1 @ xin + self.b1) >> self._q
        h1 = np.maximum(h1, 0)
        out = (self.W2 @ h1 + self.b2) >> self._q

        outf = out.astype(np.float32)
        min_s, max_s = float(outf.min()), float(outf.max())
        if max_s - min_s <= 1e-9:
            norm_scores = np.full_like(outf, 0.5)
        else:
            norm_scores = (outf - min_s) / (max_s - min_s)

        idx = int(np.argmax(outf))
        mode = [CASMode.DIRECT, CASMode.CHAIN, CASMode.TWO_HOP][idx]

        conf = self._confidence(base)
        if self._last_mode is not None and conf < self.cfg.min_confidence:
            mode = self._last_mode
        self._last_mode = mode

        scores = {
            CASMode.DIRECT: float(norm_scores[0]),
            CASMode.CHAIN: float(norm_scores[1]),
            CASMode.TWO_HOP: float(norm_scores[2]),
        }

        self.last_infer_us = (time.perf_counter() - t0) * 1e6
        return mode, conf, scores
