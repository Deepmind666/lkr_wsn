#!/usr/bin/env python3
"""
AERIS SOTA Protocol Comparison with Rigorous Statistical Testing

This script implements the expert consensus on evaluation methodology:
1. Fair comparison: All protocols use identical channel/energy models
2. SOTA baselines: LEACH, HEED, PEGASIS, SEP (not just LEACH)
3. Proper statistical workflow: Shapiro-Wilk → Levene → choose test
4. Effect size reporting: Cohen's d with 95% CI
5. Multiple runs: 30 independent simulations per configuration

References:
- Gemini review feedback on statistical rigor
- Sensors (MDPI) evaluation standards
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import argparse
import numpy as np
import json
import math
import random
from datetime import datetime
from pathlib import Path
from scipy import stats
from typing import Dict, List, Tuple

# Import channel model for fair comparison
from realistic_channel_model import LogNormalShadowingModel, IEEE802154LinkQuality, EnvironmentType
from aeris_protocol import AerisProtocol
from benchmark_protocols import NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from teen_protocol import TEENProtocol, TEENConfig

# Unified packet size (bits) and energy model parameters
PACKET_SIZE_BITS = 4000
PACKET_SIZE_BYTES = PACKET_SIZE_BITS // 8
TX_POWER_DBM = 0.0
TEMP_C = 25.0
HUM_RATIO = 0.5


def make_energy_model():
    return ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)


def tx_energy(model: ImprovedEnergyModel, distance: float) -> float:
    return model.calculate_transmission_energy(
        PACKET_SIZE_BITS, distance, TX_POWER_DBM, TEMP_C, HUM_RATIO
    )


def rx_energy(model: ImprovedEnergyModel) -> float:
    return model.calculate_reception_energy(PACKET_SIZE_BITS, TEMP_C, HUM_RATIO)


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


class FairChannelAdapter:
    """Adapter to use FairChannel within protocols expecting calculate_link_metrics()."""
    def __init__(self, channel: FairChannel):
        self.channel = channel

    def calculate_link_metrics(self, tx_power, distance, temperature_c=25.0, humidity_ratio=0.5):
        return {"pdr": self.channel.pdr(distance)}


class Node:
    """Generic sensor node."""
    def __init__(self, nid, x, y, e=2.0, is_advanced=False, alpha=1.0):
        self.id, self.x, self.y = nid, x, y
        self.is_advanced = is_advanced
        self.alpha = alpha
        # SEP: advanced nodes have more energy
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


# ============================================================
# Protocol Implementations (All use same channel model)
# ============================================================

class LEACH:
    """LEACH protocol with fair channel model."""
    def __init__(self, nodes, bs, ch, p=0.1):
        self.nodes, self.bs, self.ch, self.p = nodes, bs, ch, p
        self.energy_model = make_energy_model()
        self.sent, self.recv, self.energy = 0, 0, 0.0
        self.alive_per_round = []

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False
        self.alive_per_round.append(len(alive))

        chs = [n for n in alive if np.random.random() < self.p] or [max(alive, key=lambda n: n.e)]
        clusters = {c.id: [] for c in chs}
        for n in alive:
            if n not in chs:
                clusters[min(chs, key=lambda c: n.dist(c)).id].append(n)

        for c in chs:
            for m in clusters[c.id]:
                if not m.alive:
                    continue
                d = m.dist(c)
                tx = tx_energy(self.energy_model, d)
                rx = rx_energy(self.energy_model)
                m.use(tx); c.use(rx); self.energy += tx + rx; self.sent += 1
                if np.random.random() < self.ch.pdr(d):
                    self.recv += 1

        for c in chs:
            if not c.alive:
                continue
            tx = tx_energy(self.energy_model, c.dist(self.bs))
            c.use(tx); self.energy += tx; self.sent += 1
            if np.random.random() < self.ch.pdr(c.dist(self.bs)):
                self.recv += 1
        return True

    def result(self):
        return {'pdr': self.recv / max(1, self.sent), 'energy': self.energy,
                'alive_per_round': self.alive_per_round}


class HEED:
    """HEED protocol with fair channel model."""
    def __init__(self, nodes, bs, ch, c_prob=0.05, cluster_radius=50.0):
        self.nodes, self.bs, self.ch = nodes, bs, ch
        self.c_prob, self.cluster_radius = c_prob, cluster_radius
        self.energy_model = make_energy_model()
        self.sent, self.recv, self.energy = 0, 0, 0.0
        self.alive_per_round = []

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False
        self.alive_per_round.append(len(alive))

        # HEED CH selection based on energy and communication cost
        for n in alive:
            n.ch_prob = self.c_prob * (n.e / n.e0)
            neighbors = [o for o in alive if o.id != n.id and n.dist(o) <= self.cluster_radius]
            n.comm_cost = np.mean([n.dist(o) for o in neighbors]) if neighbors else float('inf')

        # Iterative selection
        chs = []
        for _ in range(3):  # max iterations
            for n in alive:
                if n in chs:
                    continue
                if np.random.random() < n.ch_prob:
                    chs.append(n)

        if not chs:
            chs = [max(alive, key=lambda n: n.e)]

        # Assign members
        clusters = {c.id: [] for c in chs}
        for n in alive:
            if n not in chs:
                closest = min(chs, key=lambda c: n.dist(c))
                clusters[closest.id].append(n)

        # Data transmission
        for c in chs:
            for m in clusters[c.id]:
                if not m.alive:
                    continue
                d = m.dist(c)
                tx = tx_energy(self.energy_model, d)
                rx = rx_energy(self.energy_model)
                m.use(tx); c.use(rx); self.energy += tx + rx; self.sent += 1
                if np.random.random() < self.ch.pdr(d):
                    self.recv += 1

            if c.alive:
                tx = tx_energy(self.energy_model, c.dist(self.bs))
                c.use(tx); self.energy += tx; self.sent += 1
                if np.random.random() < self.ch.pdr(c.dist(self.bs)):
                    self.recv += 1
        return True

    def result(self):
        return {'pdr': self.recv / max(1, self.sent), 'energy': self.energy,
                'alive_per_round': self.alive_per_round}


class PEGASIS:
    """PEGASIS protocol with fair channel model."""
    def __init__(self, nodes, bs, ch):
        self.nodes, self.bs, self.ch = nodes, bs, ch
        self.energy_model = make_energy_model()
        self.sent, self.recv, self.energy = 0, 0, 0.0
        self.chain = []
        self.round_count = 0
        self.alive_per_round = []
        self._construct_chain()

    def _construct_chain(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return

        # Greedy chain construction
        remaining = alive.copy()
        # Start from farthest node from BS
        start = max(remaining, key=lambda n: n.dist(self.bs))
        self.chain = [start]
        remaining.remove(start)

        while remaining:
            last = self.chain[-1]
            nearest = min(remaining, key=lambda n: last.dist(n))
            self.chain.append(nearest)
            remaining.remove(nearest)

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False
        self.alive_per_round.append(len(alive))

        # Reconstruct if needed
        if len([n for n in self.chain if n.alive]) != len(alive):
            self._construct_chain()

        alive_chain = [n for n in self.chain if n.alive]
        if not alive_chain:
            return False

        # Round-robin leader
        leader_idx = self.round_count % len(alive_chain)
        leader = alive_chain[leader_idx]
        self.round_count += 1

        # Chain transmission toward leader
        for i, n in enumerate(alive_chain):
            if n == leader:
                continue
            # Find next alive node toward leader
            if i < leader_idx:
                next_n = alive_chain[i + 1] if i + 1 < len(alive_chain) else leader
            else:
                next_n = alive_chain[i - 1] if i > 0 else leader

            d = n.dist(next_n)
            tx = tx_energy(self.energy_model, d)
            rx = rx_energy(self.energy_model)
            n.use(tx); next_n.use(rx); self.energy += tx + rx; self.sent += 1
            if np.random.random() < self.ch.pdr(d):
                self.recv += 1

        # Leader to BS
        if leader.alive:
            tx = tx_energy(self.energy_model, leader.dist(self.bs))
            leader.use(tx); self.energy += tx; self.sent += 1
            if np.random.random() < self.ch.pdr(leader.dist(self.bs)):
                self.recv += 1
        return True

    def result(self):
        return {'pdr': self.recv / max(1, self.sent), 'energy': self.energy,
                'alive_per_round': self.alive_per_round}


class SEP:
    """SEP protocol with fair channel model."""
    def __init__(self, nodes, bs, ch, p_opt=0.1, m=0.1, alpha=1.0):
        self.nodes, self.bs, self.ch = nodes, bs, ch
        self.p_opt, self.m, self.alpha = p_opt, m, alpha
        self.energy_model = make_energy_model()
        self.sent, self.recv, self.energy = 0, 0, 0.0
        self.round_count = 0
        self.alive_per_round = []

        # SEP weighted probabilities
        self.p_nrm = p_opt / (1 + m * alpha)
        self.p_adv = p_opt * (1 + alpha) / (1 + m * alpha)

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False
        self.alive_per_round.append(len(alive))
        self.round_count += 1

        # CH selection with weighted probability
        chs = []
        for n in alive:
            p = self.p_adv if n.is_advanced else self.p_nrm
            # Energy-weighted threshold
            threshold = p * (n.e / n.e0)
            if np.random.random() < threshold:
                chs.append(n)

        if not chs:
            chs = [max(alive, key=lambda n: n.e)]

        # Assign members
        clusters = {c.id: [] for c in chs}
        for n in alive:
            if n not in chs:
                clusters[min(chs, key=lambda c: n.dist(c)).id].append(n)

        # Data transmission
        for c in chs:
            for m in clusters[c.id]:
                if not m.alive:
                    continue
                d = m.dist(c)
                tx = tx_energy(self.energy_model, d)
                rx = rx_energy(self.energy_model)
                m.use(tx); c.use(rx); self.energy += tx + rx; self.sent += 1
                if np.random.random() < self.ch.pdr(d):
                    self.recv += 1

            if c.alive:
                tx = tx_energy(self.energy_model, c.dist(self.bs))
                c.use(tx); self.energy += tx; self.sent += 1
                if np.random.random() < self.ch.pdr(c.dist(self.bs)):
                    self.recv += 1
        return True

    def result(self):
        return {'pdr': self.recv / max(1, self.sent), 'energy': self.energy,
                'alive_per_round': self.alive_per_round}


class AERIS:
    """AERIS protocol with fair channel model."""
    def __init__(self, nodes, bs, ch, p=0.1, retry=2, arq=True, coop=True, smart=True):
        self.nodes, self.bs, self.ch, self.p = nodes, bs, ch, p
        self.retry, self.arq, self.coop, self.smart = retry, arq, coop, smart
        self.energy_model = make_energy_model()
        self.sent, self.recv, self.energy = 0, 0, 0.0
        self.retries, self.coops = 0, 0
        self.alive_per_round = []

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False
        self.alive_per_round.append(len(alive))

        chs = []
        for n in alive:
            prob = self.p * (1.2 if self.smart and n.dist(self.bs) < 60 else 1.0)
            if np.random.random() < prob:
                chs.append(n)
        if not chs:
            chs = [max(alive, key=lambda n: n.e)]

        clusters = {c.id: [] for c in chs}
        for n in alive:
            if n not in chs:
                clusters[min(chs, key=lambda c: n.dist(c)).id].append(n)

        for c in chs:
            for m in clusters[c.id]:
                if not m.alive:
                    continue
                d = m.dist(c)
                tx = tx_energy(self.energy_model, d)
                rx = rx_energy(self.energy_model)
                m.use(tx); c.use(rx); self.energy += tx + rx; self.sent += 1
                if np.random.random() < self.ch.pdr(d):
                    self.recv += 1

        for c in chs:
            if not c.alive:
                continue
            d, pdr, done = c.dist(self.bs), self.ch.pdr(c.dist(self.bs)), False
            self.sent += 1

            for att in range(1 + (self.retry if self.arq else 0)):
                tx = tx_energy(self.energy_model, d)
                c.use(tx); self.energy += tx
                if np.random.random() < pdr:
                    done = True; break
                if att > 0:
                    self.retries += 1

            if not done and self.coop and d > 80:
                others = [o for o in chs if o.id != c.id and o.alive]
                if others:
                    h = min(others, key=lambda o: o.dist(self.bs))
                    tx = tx_energy(self.energy_model, c.dist(h))
                    rx = rx_energy(self.energy_model)
                    c.use(tx); h.use(rx); self.energy += tx + rx
                    if np.random.random() < self.ch.pdr(c.dist(h)):
                        tx = tx_energy(self.energy_model, h.dist(self.bs))
                        h.use(tx); self.energy += tx
                        if np.random.random() < self.ch.pdr(h.dist(self.bs)):
                            done, self.coops = True, self.coops + 1
            if done:
                self.recv += 1
        return True

    def result(self):
        return {'pdr': self.recv / max(1, self.sent), 'energy': self.energy,
                'retries': self.retries, 'coops': self.coops,
                'alive_per_round': self.alive_per_round}


def run_aeris_protocol(nodes, bs, rounds: int, seed: int, profile: str) -> Dict:
    """Run the full AerisProtocol using fixed geometry for fair comparison."""
    positions = [(n.x, n.y) for n in nodes]
    area_size = max(1.0, float(bs[1] - 20.0))
    config = NetworkConfig(
        num_nodes=len(nodes),
        area_width=area_size,
        area_height=area_size,
        base_station_x=float(bs[0]),
        base_station_y=float(bs[1]),
        initial_energy=2.0,
        packet_size=PACKET_SIZE_BYTES,
        temperature_c=TEMP_C,
        humidity_ratio=HUM_RATIO,
        enable_channel=True,
        channel_env="indoor_office",
        tx_power_dbm=TX_POWER_DBM,
        link_retx=0,
        link_retx_power_step=0.0,
        positions=positions,
    )
    # Avoid forcing perfect delivery; keep results honest.
    config.force_ctp_reliable = False
    config.high_dropout_mode = False

    protocol = AerisProtocol(config, profile=profile, verbose=False, seed=seed)
    results = protocol.run_simulation(rounds)

    return {
        'pdr': results.get('packet_delivery_ratio_end2end', 0.0),
        'energy': results.get('total_energy_consumed', 0.0),
        'alive_per_round': [r.get('alive_nodes', 0) for r in results.get('round_statistics', [])]
    }


def run_teen_protocol(nodes, bs, rounds: int, seed: int, channel: FairChannel) -> Dict:
    """Run TEEN with unified packet size and fair channel."""
    random.seed(seed)
    positions = [(n.x, n.y) for n in nodes]
    area_size = max(1.0, float(bs[1] - 20.0))
    config = TEENConfig(
        num_nodes=len(nodes),
        area_width=area_size,
        area_height=area_size,
        base_station_x=float(bs[0]),
        base_station_y=float(bs[1]),
        initial_energy=2.0,
        packet_size=PACKET_SIZE_BYTES,
        transmission_range=30.0,
        enable_channel=True,
        channel_env="indoor_office",
        tx_power_dbm=TX_POWER_DBM,
        temperature_c=TEMP_C,
        humidity_ratio=HUM_RATIO,
        link_retx=0,
        link_retx_power_step=0.0,
    )
    protocol = TEENProtocol(config, use_unified_energy_model=True)
    protocol.initialize_network(positions)
    protocol.channel_model = FairChannelAdapter(channel)
    results = protocol.run_simulation(rounds)
    alive_per_round = [s.get("alive", 0) for s in getattr(protocol, "round_stats", [])]
    return {
        'pdr': results.get('packet_delivery_ratio_end2end', results.get('packet_delivery_ratio', 0.0)),
        'energy': results.get('total_energy_consumed', 0.0),
        'alive_per_round': alive_per_round
    }


# ============================================================
# Statistical Testing Functions
# ============================================================

def proper_statistical_test(group1: List[float], group2: List[float], alpha: float = 0.05) -> Dict:
    """
    Perform proper statistical testing following expert consensus:
    1. Shapiro-Wilk normality test
    2. Levene variance homogeneity test
    3. Choose appropriate test based on results

    Returns dict with test results and interpretation.
    """
    result = {
        'n1': len(group1), 'n2': len(group2),
        'mean1': np.mean(group1), 'mean2': np.mean(group2),
        'std1': np.std(group1), 'std2': np.std(group2)
    }

    # Step 1: Shapiro-Wilk normality test
    _, p_norm1 = stats.shapiro(group1)
    _, p_norm2 = stats.shapiro(group2)
    result['shapiro_p1'] = p_norm1
    result['shapiro_p2'] = p_norm2
    result['normal1'] = p_norm1 > alpha
    result['normal2'] = p_norm2 > alpha
    result['both_normal'] = result['normal1'] and result['normal2']

    if result['both_normal']:
        # Step 2: Levene test for variance homogeneity
        _, p_levene = stats.levene(group1, group2)
        result['levene_p'] = p_levene
        result['equal_variance'] = p_levene > alpha

        # Step 3: Choose t-test variant
        if result['equal_variance']:
            # Standard t-test
            t_stat, p_val = stats.ttest_ind(group1, group2, equal_var=True)
            result['test_used'] = 'Independent t-test'
        else:
            # Welch's t-test
            t_stat, p_val = stats.ttest_ind(group1, group2, equal_var=False)
            result['test_used'] = "Welch's t-test"
        result['t_statistic'] = t_stat
    else:
        # Non-parametric: Mann-Whitney U test
        u_stat, p_val = stats.mannwhitneyu(group1, group2, alternative='two-sided')
        result['test_used'] = 'Mann-Whitney U test'
        result['u_statistic'] = u_stat

    result['p_value'] = p_val
    result['significant'] = p_val < alpha

    # Cohen's d effect size
    pooled_std = np.sqrt((np.std(group1)**2 + np.std(group2)**2) / 2)
    result['cohens_d'] = (np.mean(group2) - np.mean(group1)) / pooled_std if pooled_std > 0 else 0

    # Effect size interpretation
    d = abs(result['cohens_d'])
    if d < 0.2:
        result['effect_interpretation'] = 'negligible'
    elif d < 0.5:
        result['effect_interpretation'] = 'small'
    elif d < 0.8:
        result['effect_interpretation'] = 'medium'
    else:
        result['effect_interpretation'] = 'large'

    # 95% CI for Cohen's d
    se_d = np.sqrt((len(group1) + len(group2)) / (len(group1) * len(group2)) +
                   result['cohens_d']**2 / (2 * (len(group1) + len(group2))))
    result['cohens_d_ci_low'] = result['cohens_d'] - 1.96 * se_d
    result['cohens_d_ci_high'] = result['cohens_d'] + 1.96 * se_d

    return result


def create_network(n: int, sz: float, seed: int, m_advanced: float = 0.0, alpha: float = 1.0) -> Tuple[List[Node], Tuple[float, float]]:
    """Create network with optional heterogeneous nodes for SEP."""
    np.random.seed(seed)
    nodes = []
    n_advanced = int(n * m_advanced)

    for i in range(n):
        x = np.random.uniform(0, sz)
        y = np.random.uniform(0, sz)
        is_adv = i < n_advanced
        nodes.append(Node(i, x, y, is_advanced=is_adv, alpha=alpha))

    bs = (sz / 2, sz + 20)
    return nodes, bs


def run_protocol(cls, nodes, bs, ch, rounds=200, **kwargs):
    """Run a protocol simulation."""
    # Create fresh node copies
    test_nodes = [Node(n.id, n.x, n.y, n.e0, n.is_advanced, n.alpha) for n in nodes]
    protocol = cls(test_nodes, bs, ch, **kwargs)

    for _ in range(rounds):
        if not protocol.round():
            break

    return protocol.result()


def parse_args():
    parser = argparse.ArgumentParser(description="Run SOTA protocol comparison.")
    parser.add_argument("--runs", type=int, default=int(os.environ.get("SOTA_RUNS", "30")))
    # [FIX] 统一口径: rounds=500, nodes=100 与主实验一致
    parser.add_argument("--rounds", type=int, default=int(os.environ.get("SOTA_ROUNDS", "500")))
    parser.add_argument("--nodes", type=int, default=int(os.environ.get("SOTA_NODES", "100")))
    parser.add_argument("--area", type=float, default=float(os.environ.get("SOTA_AREA", "100")))
    parser.add_argument("--output", default=os.environ.get("SOTA_OUTPUT"))
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 70)
    print("AERIS SOTA COMPARISON WITH RIGOROUS STATISTICAL TESTING")
    print("=" * 70)
    print("\nFollowing expert consensus on evaluation methodology:")
    print("- Fair comparison: All protocols use identical channel models")
    print("- SOTA baselines: LEACH, HEED, PEGASIS, SEP, TEEN")
    print("- Statistical workflow: Shapiro-Wilk -> Levene -> Choose test")
    print("- Effect size: Cohen's d with 95% CI")
    print(f"- Multiple runs: {args.runs} independent simulations")
    print("=" * 70)

    ch = FairChannel()
    N_RUNS = args.runs
    ROUNDS = args.rounds
    N_NODES = args.nodes
    AREA = args.area

    results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'n_runs': N_RUNS,
            'rounds': ROUNDS,
            'n_nodes': N_NODES,
            'area_size': AREA,
            # [FIX] 更新说明，明确信道模型配置
            'methodology': 'All protocols use unified channel model (FairChannel with Log-Normal Shadowing parameters)',
            'channel_env': 'indoor_office',
            'unified_config': True
        },
        'protocols': {},
        'statistics': {},
        'survival_curves': {}
    }

    # ============================================================
    # Run all protocols
    # ============================================================
    protocol_order = ['LEACH', 'HEED', 'PEGASIS', 'SEP', 'TEEN', 'AERIS-E', 'AERIS-R']
    results['metadata']['protocols'] = protocol_order
    baseline_protocols = {
        'LEACH': (LEACH, {}),
        'HEED': (HEED, {'c_prob': 0.05, 'cluster_radius': 50.0}),
        'PEGASIS': (PEGASIS, {}),
        'SEP': (SEP, {'p_opt': 0.1, 'm': 0.1, 'alpha': 1.0}),
    }
    aeris_profiles = {'AERIS-E': 'energy', 'AERIS-R': 'robust'}

    for name in protocol_order:
        print(f"\n[Running] {name} ({N_RUNS} runs)...")
        pdrs = []
        energies = []
        alive_curves = []

        for r in range(N_RUNS):
            # SEP needs heterogeneous nodes
            if name == 'SEP':
                nodes, bs = create_network(N_NODES, AREA, 1000 + r, m_advanced=0.1, alpha=1.0)
            else:
                nodes, bs = create_network(N_NODES, AREA, 1000 + r)

            if name == 'TEEN':
                res = run_teen_protocol(nodes, bs, ROUNDS, seed=1000 + r, channel=ch)
            elif name in aeris_profiles:
                res = run_aeris_protocol(nodes, bs, ROUNDS, seed=1000 + r, profile=aeris_profiles[name])
            else:
                cls, kwargs = baseline_protocols[name]
                res = run_protocol(cls, nodes, bs, ch, ROUNDS, **kwargs)
            pdrs.append(res['pdr'])
            energies.append(res['energy'])
            if 'alive_per_round' in res:
                alive_curves.append(res['alive_per_round'])

        results['protocols'][name] = {
            'pdr_values': pdrs,
            'energy_values': energies,
            'pdr_mean': float(np.mean(pdrs)),
            'pdr_std': float(np.std(pdrs)),
            'pdr_ci95': float(1.96 * np.std(pdrs) / np.sqrt(N_RUNS)),
            'energy_mean': float(np.mean(energies)),
            'energy_std': float(np.std(energies))
        }

        # Average survival curve
        if alive_curves:
            max_len = max(len(c) for c in alive_curves)
            padded = []
            for c in alive_curves:
                if len(c) < max_len:
                    c = c + [c[-1]] * (max_len - len(c))
                padded.append(c)
            avg_curve = np.mean(padded, axis=0).tolist()
            results['survival_curves'][name] = avg_curve

        print(f"   PDR: {np.mean(pdrs)*100:.2f}% +/- {np.std(pdrs)*100:.2f}%")
        print(f"   Energy: {np.mean(energies):.4f} J")

    # ============================================================
    # Statistical comparisons (AERIS vs each baseline)
    # ============================================================
    print("\n" + "=" * 70)
    print("STATISTICAL ANALYSIS")
    print("=" * 70)

    baselines = ['LEACH', 'HEED', 'PEGASIS', 'SEP', 'TEEN']
    for profile in ['AERIS-E', 'AERIS-R']:
        aeris_pdrs = results['protocols'][profile]['pdr_values']
        for baseline in baselines:
            baseline_pdrs = results['protocols'][baseline]['pdr_values']

            print(f"\n[Comparison] {profile} vs {baseline}")
            stat_result = proper_statistical_test(baseline_pdrs, aeris_pdrs)

            results['statistics'][f'{profile}_vs_{baseline}'] = {
                k: float(v) if isinstance(v, (np.floating, float)) else v
                for k, v in stat_result.items()
            }

            print(f"   Test used: {stat_result['test_used']}")
            print(f"   Normality: Group1={stat_result['normal1']}, Group2={stat_result['normal2']}")
            if 'equal_variance' in stat_result:
                print(f"   Equal variance: {stat_result['equal_variance']}")
            print(f"   p-value: {stat_result['p_value']:.2e}")
            print(f"   Significant: {stat_result['significant']}")
            print(f"   Cohen's d: {stat_result['cohens_d']:.3f} ({stat_result['effect_interpretation']})")
            print(f"   95% CI: [{stat_result['cohens_d_ci_low']:.3f}, {stat_result['cohens_d_ci_high']:.3f}]")

            # Calculate improvement
            improvement = (np.mean(aeris_pdrs) - np.mean(baseline_pdrs)) * 100
            print(f"   PDR Improvement: {improvement:+.2f}%")

    # Backward-compatible aliases for tooling that expects "AERIS"
    results['protocols']['AERIS'] = results['protocols']['AERIS-R']
    for baseline in baselines:
        key = f'AERIS-R_vs_{baseline}'
        if key in results['statistics']:
            results['statistics'][f'AERIS_vs_{baseline}'] = results['statistics'][key]

    # ============================================================
    # Summary table
    # ============================================================
    print("\n" + "=" * 70)
    print("SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Protocol':<12} {'PDR (%)':<15} {'Energy (J)':<12} {'vs AERIS-R':<15}")
    print("-" * 54)

    ref_pdr = results['protocols']['AERIS-R']['pdr_mean'] * 100
    for name in protocol_order:
        pdr = results['protocols'][name]['pdr_mean'] * 100
        pdr_ci = results['protocols'][name]['pdr_ci95'] * 100
        energy = results['protocols'][name]['energy_mean']

        if name == 'AERIS-R':
            diff = '-'
        else:
            diff = f"{pdr - ref_pdr:+.2f}%"

        print(f"{name:<12} {pdr:.2f} +/- {pdr_ci:.2f}   {energy:.4f}       {diff}")

    # ============================================================
    # Save results
    # ============================================================
    out_path = Path(args.output) if args.output else (
        Path(__file__).parent.parent / 'results' / 'sota_comparison.json'
    )

    # Convert numpy types for JSON serialization
    def convert_numpy(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.floating, np.integer)):
            return float(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(v) for v in obj]
        return obj

    with open(out_path, 'w') as f:
        json.dump(convert_numpy(results), f, indent=2)

    print(f"\n[Saved] {out_path}")
    print("\n" + "=" * 70)
    print("EXPERIMENT COMPLETE")
    print("=" * 70)

    return results


if __name__ == '__main__':
    main()
