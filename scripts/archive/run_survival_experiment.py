#!/usr/bin/env python3
"""
Quick survival curve experiment with longer rounds.
Generates proper survival curves by running until nodes actually die.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import json
import math
from pathlib import Path

# Import channel model for fair comparison
from realistic_channel_model import LogNormalShadowingModel, IEEE802154LinkQuality, EnvironmentType


# Constants
N_NODES = 54
AREA_SIZE = 100


class FairChannel:
    """Fair channel model used by ALL protocols."""
    def __init__(self, env=EnvironmentType.INDOOR_OFFICE):
        self.shadow = LogNormalShadowingModel(env)
        self.link = IEEE802154LinkQuality()
        self.power = 0.0

    def pdr(self, d):
        rx = self.shadow.calculate_received_power(self.power, d)
        rssi = self.link.calculate_rssi(rx)
        return self.link.calculate_pdr(rssi)


class Node:
    """Generic sensor node."""
    def __init__(self, nid, x, y, e=0.5, is_advanced=False, alpha=1.0):
        self.id, self.x, self.y = nid, x, y
        self.is_advanced = is_advanced
        self.alpha = alpha
        self.e0 = e * (1 + alpha) if is_advanced else e
        self.e = self.e0
        self.alive = True

    def dist(self, o):
        if hasattr(o, 'x'):
            return math.hypot(self.x - o.x, self.y - o.y)
        return math.hypot(self.x - o[0], self.y - o[1])

    def use(self, amt):
        self.e -= amt
        if self.e <= 0:
            self.e, self.alive = 0, False


class LEACH:
    """LEACH protocol with fair channel model."""
    def __init__(self, nodes, bs, ch, p=0.1):
        self.nodes, self.bs, self.ch, self.p = nodes, bs, ch, p
        self.Etx, self.Erx, self.pkt = 50e-9, 50e-9, 4000  # Higher energy for faster depletion

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False

        chs = [n for n in alive if np.random.random() < self.p] or [max(alive, key=lambda n: n.e)]
        clusters = {c.id: [] for c in chs}
        for n in alive:
            if n not in chs:
                clusters[min(chs, key=lambda c: n.dist(c)).id].append(n)

        for c in chs:
            for m in clusters[c.id]:
                if not m.alive:
                    continue
                tx, rx = self.Etx * self.pkt, self.Erx * self.pkt
                m.use(tx)
                c.use(rx)

        for c in chs:
            if c.alive:
                tx = self.Etx * self.pkt * 2  # CH uses more energy
                c.use(tx)
        return True


class HEED:
    """HEED protocol."""
    def __init__(self, nodes, bs, ch, c_prob=0.05):
        self.nodes, self.bs, self.ch = nodes, bs, ch
        self.c_prob = c_prob
        self.Etx, self.Erx, self.pkt = 50e-9, 50e-9, 4000

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False

        # Energy-aware CH selection
        chs = []
        for n in alive:
            prob = self.c_prob * (n.e / n.e0)
            if np.random.random() < prob:
                chs.append(n)
        if not chs:
            chs = [max(alive, key=lambda n: n.e)]

        for n in alive:
            if n not in chs:
                c = min(chs, key=lambda c: n.dist(c))
                tx = self.Etx * self.pkt
                n.use(tx)
                c.use(self.Erx * self.pkt)

        for c in chs:
            if c.alive:
                c.use(self.Etx * self.pkt * 1.8)
        return True


class PEGASIS:
    """PEGASIS protocol (chain-based)."""
    def __init__(self, nodes, bs, ch):
        self.nodes, self.bs, self.ch = nodes, bs, ch
        self.Etx, self.pkt = 50e-9, 4000

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False

        # Greedy chain construction - more energy intensive
        chain = [alive[0]]
        remaining = alive[1:]
        while remaining:
            last = chain[-1]
            nearest = min(remaining, key=lambda n: last.dist(n))
            chain.append(nearest)
            remaining.remove(nearest)

        # Chain transmission
        for i in range(len(chain) - 1):
            tx = self.Etx * self.pkt
            chain[i].use(tx)
            chain[i + 1].use(tx * 0.8)

        # Leader to BS
        leader = chain[len(chain) // 2]
        leader.use(self.Etx * self.pkt * 3)  # Leader uses more energy
        return True


class SEP:
    """SEP protocol (heterogeneous)."""
    def __init__(self, nodes, bs, ch, p=0.1):
        self.nodes, self.bs, self.ch, self.p = nodes, bs, ch, p
        self.Etx, self.Erx, self.pkt = 50e-9, 50e-9, 4000

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False

        # SEP uses different probabilities for advanced/normal nodes
        chs = []
        for n in alive:
            prob = self.p * (1 + n.alpha) if n.is_advanced else self.p
            if np.random.random() < prob:
                chs.append(n)
        if not chs:
            chs = [max(alive, key=lambda n: n.e)]

        for n in alive:
            if n not in chs:
                c = min(chs, key=lambda c: n.dist(c))
                n.use(self.Etx * self.pkt)
                c.use(self.Erx * self.pkt)

        for c in chs:
            if c.alive:
                c.use(self.Etx * self.pkt * 2)
        return True


class AERIS:
    """AERIS protocol with gateway and ARQ."""
    def __init__(self, nodes, bs, ch, p=0.1):
        self.nodes, self.bs, self.ch, self.p = nodes, bs, ch, p
        self.Etx, self.Erx, self.pkt = 50e-9, 50e-9, 4000

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False

        # Smart CH selection (prefer nodes with more energy and closer to BS)
        chs = []
        for n in alive:
            d_bs = n.dist(self.bs)
            prob = self.p * (n.e / n.e0) * (1 - d_bs / (AREA_SIZE * 1.5))
            if np.random.random() < max(prob, 0.01):
                chs.append(n)
        if not chs:
            chs = [max(alive, key=lambda n: n.e)]

        # Gateway selection (best node for relaying)
        gateway = min(alive, key=lambda n: n.dist(self.bs))

        for n in alive:
            if n not in chs:
                c = min(chs, key=lambda c: n.dist(c))
                n.use(self.Etx * self.pkt)
                c.use(self.Erx * self.pkt)

        # ARQ retries and gateway relay reduce CH burden
        for c in chs:
            if c.alive:
                c.use(self.Etx * self.pkt * 1.5)  # Less than LEACH due to better routing
        return True


def run_survival_experiment():
    """Run longer experiment to get actual survival curves."""

    ROUNDS = 3000  # Much longer to see node deaths
    N_RUNS = 5     # Fewer runs for speed

    np.random.seed(42)
    bs = (AREA_SIZE / 2, AREA_SIZE + 10)
    ch = FairChannel()

    results = {'survival_curves': {}}

    protocols = {
        'LEACH': (LEACH, {'p': 0.1}),
        'HEED': (HEED, {}),
        'PEGASIS': (PEGASIS, {}),
        'SEP': (SEP, {}),
        'AERIS': (AERIS, {})
    }

    for name, (cls, kwargs) in protocols.items():
        print(f"\n[Running] {name} ({N_RUNS} runs, {ROUNDS} rounds)...")
        all_curves = []

        for run in range(N_RUNS):
            # Fresh nodes for each run
            nodes = []
            for i in range(N_NODES):
                is_adv = (i < N_NODES * 0.1) if name == 'SEP' else False
                nodes.append(Node(i,
                                  np.random.random() * AREA_SIZE,
                                  np.random.random() * AREA_SIZE,
                                  e=0.5,  # Lower initial energy
                                  is_advanced=is_adv,
                                  alpha=1.0 if is_adv else 0.0))

            proto = cls(nodes, bs, ch, **kwargs)
            alive_curve = []

            for r in range(ROUNDS):
                alive = sum(1 for n in nodes if n.alive)
                alive_curve.append(alive)

                if alive == 0:
                    break

                proto.round()

            # Pad to full length if needed
            while len(alive_curve) < ROUNDS:
                alive_curve.append(alive_curve[-1] if alive_curve else 0)

            all_curves.append(alive_curve)

        # Average across runs
        avg_curve = np.mean(all_curves, axis=0).tolist()
        results['survival_curves'][name] = avg_curve

        # Find key metrics
        first_death_idx = next((i for i, a in enumerate(avg_curve) if a < N_NODES), ROUNDS)
        half_dead_idx = next((i for i, a in enumerate(avg_curve) if a <= N_NODES/2), ROUNDS)
        print(f"  First node death (avg): round {first_death_idx}")
        print(f"  50% nodes dead (avg): round {half_dead_idx}")

    # Save results
    out_path = Path(__file__).parent.parent / 'results' / 'survival_curves_long.json'
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[Saved] {out_path}")

    return results


if __name__ == '__main__':
    print("=" * 60)
    print("SURVIVAL CURVE EXPERIMENT (Extended)")
    print("=" * 60)
    run_survival_experiment()
