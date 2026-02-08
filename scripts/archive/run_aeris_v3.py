#!/usr/bin/env python3
"""
AERIS v3: Focus on Energy Efficiency and Network Lifetime

Key insight: In indoor environments with reasonable link quality,
routing optimizations provide minimal PDR improvement.

Instead, focus on:
1. Energy-efficient cluster head rotation
2. Load balancing to extend network lifetime
3. Transmission power optimization to save energy
4. Minimize unnecessary transmissions

The goal is: Similar PDR with LESS energy, leading to longer network lifetime.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import json
import math
from datetime import datetime
from pathlib import Path

from realistic_channel_model import LogNormalShadowingModel, IEEE802154LinkQuality, EnvironmentType


class EfficientChannelModel:
    """Channel model with power-aware PDR calculation."""

    def __init__(self, environment: EnvironmentType = EnvironmentType.INDOOR_OFFICE):
        self.shadowing_model = LogNormalShadowingModel(environment)
        self.link_quality = IEEE802154LinkQuality()
        self.base_tx_power_dbm = 0.0

    def calculate_pdr(self, distance: float, tx_power_dbm: float = None) -> float:
        if tx_power_dbm is None:
            tx_power_dbm = self.base_tx_power_dbm
        received_power = self.shadowing_model.calculate_received_power(tx_power_dbm, distance)
        rssi = self.link_quality.calculate_rssi(received_power)
        pdr = self.link_quality.calculate_pdr(rssi)
        return pdr

    def get_min_power_for_pdr(self, distance: float, target_pdr: float = 0.85) -> float:
        """Find minimum TX power to achieve target PDR (save energy)."""
        for power in [-10, -5, -3, 0, 3, 5]:
            if self.calculate_pdr(distance, power) >= target_pdr:
                return power
        return 5.0  # Max power


class EfficientNode:
    """Node optimized for energy efficiency."""

    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True
        self.ch_rounds = 0  # Times served as CH
        self.total_tx = 0   # Total transmissions

    def distance_to(self, other) -> float:
        if hasattr(other, 'x'):
            return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
        return math.sqrt((self.x - other[0])**2 + (self.y - other[1])**2)

    def consume_energy(self, amount: float):
        self.current_energy -= amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False

    def get_energy_ratio(self) -> float:
        return self.current_energy / self.initial_energy


class AERISv3:
    """AERIS v3: Energy-Efficient Protocol with Same Reliability."""

    def __init__(self, nodes, bs_pos, channel_model):
        self.nodes = nodes
        self.bs_pos = bs_pos
        self.channel = channel_model
        self.round_num = 0

        # Energy parameters (CC2420)
        self.E_tx_base = 208.8e-9  # J/bit at 0dBm
        self.E_rx = 225.6e-9      # J/bit
        self.packet_size = 4000   # bits

        # Power-to-energy multiplier (approximate)
        self.power_energy_factor = {
            -10: 0.5,   # Half power = half energy
            -5: 0.7,
            -3: 0.8,
            0: 1.0,
            3: 1.3,
            5: 1.6
        }

        # Target PDR (maintain reliability)
        self.target_pdr = 0.85

        # Statistics
        self.packets_sent = 0
        self.packets_delivered = 0
        self.total_energy = 0.0

    def _get_adaptive_ch_probability(self, node) -> float:
        """CH probability heavily weighted by remaining energy."""
        alive = [n for n in self.nodes if n.is_alive]
        if not alive:
            return 0

        # Energy-based probability
        max_energy = max(n.current_energy for n in alive)
        if max_energy <= 0:
            return 0.1

        e_ratio = node.current_energy / max_energy

        # Favor high-energy nodes strongly
        base_p = 0.05  # 5% base
        return base_p * (e_ratio ** 2)  # Squared to strongly favor high energy

    def _get_tx_energy(self, distance: float) -> tuple:
        """Get optimized TX energy and expected PDR."""
        # Find minimum power for target PDR
        min_power = self.channel.get_min_power_for_pdr(distance, self.target_pdr)
        pdr = self.channel.calculate_pdr(distance, min_power)

        # Calculate energy with power factor
        factor = self.power_energy_factor.get(int(min_power), 1.0)
        energy = self.E_tx_base * self.packet_size * factor

        return energy, pdr

    def run_round(self):
        self.round_num += 1
        alive = [n for n in self.nodes if n.is_alive]
        if not alive:
            return False

        # Adaptive CH selection (energy-aware)
        chs = []
        for n in alive:
            p = self._get_adaptive_ch_probability(n)
            if np.random.random() < p:
                chs.append(n)
                n.ch_rounds += 1

        # Ensure at least one CH
        if not chs:
            # Select highest energy node
            best = max(alive, key=lambda n: n.current_energy)
            chs = [best]
            best.ch_rounds += 1

        # Cluster formation - minimize total distance
        clusters = {ch.node_id: [] for ch in chs}
        for n in alive:
            if n not in chs:
                closest_ch = min(chs, key=lambda ch: n.distance_to(ch))
                clusters[closest_ch.node_id].append(n)

        # Intra-cluster: member -> CH (power-optimized)
        for ch in chs:
            members = clusters[ch.node_id]
            for m in members:
                if not m.is_alive:
                    continue

                d = m.distance_to(ch)
                tx_energy, pdr = self._get_tx_energy(d)
                rx_energy = self.E_rx * self.packet_size

                m.consume_energy(tx_energy)
                ch.consume_energy(rx_energy)
                self.total_energy += tx_energy + rx_energy
                m.total_tx += 1

                self.packets_sent += 1
                if np.random.random() < pdr:
                    self.packets_delivered += 1

        # CH -> BS (power-optimized)
        for ch in chs:
            if not ch.is_alive:
                continue

            d_bs = ch.distance_to(self.bs_pos)
            tx_energy, pdr = self._get_tx_energy(d_bs)

            ch.consume_energy(tx_energy)
            self.total_energy += tx_energy
            ch.total_tx += 1

            self.packets_sent += 1
            if np.random.random() < pdr:
                self.packets_delivered += 1

        return True

    def get_results(self):
        pdr = self.packets_delivered / max(1, self.packets_sent)
        alive = [n for n in self.nodes if n.is_alive]

        # Fairness metric (Jain's index)
        if alive:
            energies = [n.current_energy for n in alive]
            mean_e = np.mean(energies)
            sum_sq = sum(e**2 for e in energies)
            jain = (sum(energies)**2) / (len(energies) * sum_sq) if sum_sq > 0 else 1.0
        else:
            jain = 0

        return {
            'protocol': 'AERISv3',
            'packets_sent': self.packets_sent,
            'packets_delivered': self.packets_delivered,
            'pdr': pdr,
            'total_energy': self.total_energy,
            'alive_nodes': len(alive),
            'fairness_index': jain,
            'energy_efficiency': self.packets_delivered / max(0.001, self.total_energy)
        }


class StandardLEACH:
    """Standard LEACH for comparison."""

    def __init__(self, nodes, bs_pos, channel_model):
        self.nodes = nodes
        self.bs_pos = bs_pos
        self.channel = channel_model
        self.p = 0.1
        self.E_tx = 208.8e-9
        self.E_rx = 225.6e-9
        self.packet_size = 4000
        self.packets_sent = 0
        self.packets_delivered = 0
        self.total_energy = 0.0

    def run_round(self):
        alive = [n for n in self.nodes if n.is_alive]
        if not alive:
            return False

        # Standard LEACH CH selection
        chs = [n for n in alive if np.random.random() < self.p]
        if not chs:
            chs = [max(alive, key=lambda n: n.current_energy)]

        clusters = {ch.node_id: [] for ch in chs}
        for n in alive:
            if n not in chs:
                closest_ch = min(chs, key=lambda ch: n.distance_to(ch))
                clusters[closest_ch.node_id].append(n)

        # Fixed power transmission
        for ch in chs:
            for m in clusters[ch.node_id]:
                if not m.is_alive:
                    continue
                d = m.distance_to(ch)
                tx_e = self.E_tx * self.packet_size
                rx_e = self.E_rx * self.packet_size
                m.consume_energy(tx_e)
                ch.consume_energy(rx_e)
                self.total_energy += tx_e + rx_e
                self.packets_sent += 1
                pdr = self.channel.calculate_pdr(d)
                if np.random.random() < pdr:
                    self.packets_delivered += 1

        for ch in chs:
            if not ch.is_alive:
                continue
            d_bs = ch.distance_to(self.bs_pos)
            tx_e = self.E_tx * self.packet_size
            ch.consume_energy(tx_e)
            self.total_energy += tx_e
            self.packets_sent += 1
            pdr = self.channel.calculate_pdr(d_bs)
            if np.random.random() < pdr:
                self.packets_delivered += 1

        return True

    def get_results(self):
        pdr = self.packets_delivered / max(1, self.packets_sent)
        alive = [n for n in self.nodes if n.is_alive]

        if alive:
            energies = [n.current_energy for n in alive]
            sum_sq = sum(e**2 for e in energies)
            jain = (sum(energies)**2) / (len(energies) * sum_sq) if sum_sq > 0 else 1.0
        else:
            jain = 0

        return {
            'protocol': 'LEACH',
            'packets_sent': self.packets_sent,
            'packets_delivered': self.packets_delivered,
            'pdr': pdr,
            'total_energy': self.total_energy,
            'alive_nodes': len(alive),
            'fairness_index': jain,
            'energy_efficiency': self.packets_delivered / max(0.001, self.total_energy)
        }


def create_network(num_nodes=54, area_size=100, seed=42):
    np.random.seed(seed)
    nodes = []
    for i in range(num_nodes):
        x = np.random.uniform(0, area_size)
        y = np.random.uniform(0, area_size)
        nodes.append(EfficientNode(i, x, y, initial_energy=2.0))
    bs_pos = (area_size / 2, area_size + 20)
    return nodes, bs_pos


def run_experiment(protocol_class, nodes, bs_pos, channel, max_rounds=200):
    test_nodes = [EfficientNode(n.node_id, n.x, n.y, n.initial_energy) for n in nodes]
    protocol = protocol_class(test_nodes, bs_pos, channel)
    for r in range(max_rounds):
        if not protocol.run_round():
            break
    return protocol.get_results()


def main():
    print("=" * 60)
    print("AERIS v3: Energy-Efficient Protocol")
    print("Goal: Similar PDR with LESS energy = Longer lifetime")
    print("=" * 60)

    num_runs = 30
    max_rounds = 200
    results = {'LEACH': [], 'AERISv3': []}

    channel = EfficientChannelModel(EnvironmentType.INDOOR_OFFICE)

    print(f"\nRunning {num_runs} experiments...")

    for run in range(num_runs):
        seed = 1000 + run
        nodes, bs_pos = create_network(num_nodes=54, area_size=100, seed=seed)

        results['LEACH'].append(run_experiment(StandardLEACH, nodes, bs_pos, channel, max_rounds))
        results['AERISv3'].append(run_experiment(AERISv3, nodes, bs_pos, channel, max_rounds))

        if (run + 1) % 10 == 0:
            print(f"  Completed {run + 1}/{num_runs} runs")

    # Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    for name, runs in results.items():
        pdrs = [r['pdr'] for r in runs]
        energies = [r['total_energy'] for r in runs]
        efficiencies = [r['energy_efficiency'] for r in runs]
        fairness = [r['fairness_index'] for r in runs]

        print(f"\n{name}:")
        print(f"  PDR: {np.mean(pdrs)*100:.2f}% +/- {1.96*np.std(pdrs)/np.sqrt(len(pdrs))*100:.2f}%")
        print(f"  Total Energy: {np.mean(energies):.3f}J +/- {np.std(energies):.3f}J")
        print(f"  Energy Efficiency: {np.mean(efficiencies):.1f} packets/J")
        print(f"  Fairness (Jain's Index): {np.mean(fairness):.4f}")

    # Comparison
    print("\n" + "=" * 60)
    print("IMPROVEMENT ANALYSIS")
    print("=" * 60)

    leach_pdr = np.mean([r['pdr'] for r in results['LEACH']])
    aeris_pdr = np.mean([r['pdr'] for r in results['AERISv3']])
    leach_energy = np.mean([r['total_energy'] for r in results['LEACH']])
    aeris_energy = np.mean([r['total_energy'] for r in results['AERISv3']])
    leach_eff = np.mean([r['energy_efficiency'] for r in results['LEACH']])
    aeris_eff = np.mean([r['energy_efficiency'] for r in results['AERISv3']])

    print(f"\nAERISv3 vs LEACH:")
    print(f"  PDR difference: {(aeris_pdr - leach_pdr)*100:+.2f}%")
    print(f"  Energy savings: {(1 - aeris_energy/leach_energy)*100:.1f}%")
    print(f"  Efficiency gain: {(aeris_eff/leach_eff - 1)*100:.1f}%")

    # Save
    output_dir = Path(__file__).parent.parent / 'results'
    output_file = output_dir / 'aeris_v3_results.json'

    summary = {
        'LEACH': {
            'pdr': float(leach_pdr),
            'energy': float(leach_energy),
            'efficiency': float(leach_eff)
        },
        'AERISv3': {
            'pdr': float(aeris_pdr),
            'energy': float(aeris_energy),
            'efficiency': float(aeris_eff)
        }
    }

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'improvement': {
                'pdr_diff': float((aeris_pdr - leach_pdr) * 100),
                'energy_savings': float((1 - aeris_energy/leach_energy) * 100),
                'efficiency_gain': float((aeris_eff/leach_eff - 1) * 100)
            }
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
