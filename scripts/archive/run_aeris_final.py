#!/usr/bin/env python3
"""
AERIS Final: Targeted Reliability Enhancement

Key insight from experiments:
- Intra-cluster links are short and have high PDR (>90%)
- CH-to-BS links are the bottleneck (longer distance, lower PDR)

Strategy:
- Keep intra-cluster transmission simple (like LEACH)
- Focus enhancement only on CH-to-BS links:
  1. ARQ (Automatic Repeat Request) for failed transmissions
  2. Select CHs closer to BS when possible
  3. Use cooperative transmission for distant CHs only
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


class ChannelModel:
    """Standard channel model."""

    def __init__(self, environment: EnvironmentType = EnvironmentType.INDOOR_OFFICE):
        self.shadowing_model = LogNormalShadowingModel(environment)
        self.link_quality = IEEE802154LinkQuality()
        self.tx_power_dbm = 0.0

    def calculate_pdr(self, distance: float) -> float:
        received_power = self.shadowing_model.calculate_received_power(self.tx_power_dbm, distance)
        rssi = self.link_quality.calculate_rssi(received_power)
        return self.link_quality.calculate_pdr(rssi)


class Node:
    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True

    def distance_to(self, other) -> float:
        if hasattr(other, 'x'):
            return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
        return math.sqrt((self.x - other[0])**2 + (self.y - other[1])**2)

    def consume_energy(self, amount: float):
        self.current_energy -= amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False


class AERISFinal:
    """AERIS with targeted CH-to-BS reliability enhancement."""

    def __init__(self, nodes, bs_pos, channel_model, max_retries=2):
        self.nodes = nodes
        self.bs_pos = bs_pos
        self.channel = channel_model
        self.p = 0.1
        self.max_retries = max_retries  # ARQ retries for CH->BS

        # Energy
        self.E_tx = 208.8e-9
        self.E_rx = 225.6e-9
        self.packet_size = 4000

        # Distance threshold for considering cooperative tx
        self.far_ch_threshold = 80  # meters

        # Stats
        self.packets_sent = 0
        self.packets_delivered = 0
        self.total_energy = 0.0
        self.retries_used = 0
        self.cooperative_used = 0

    def run_round(self):
        alive = [n for n in self.nodes if n.is_alive]
        if not alive:
            return False

        # CH selection with preference for nodes closer to BS
        chs = []
        for n in alive:
            d_bs = n.distance_to(self.bs_pos)
            # Slightly favor closer nodes (but don't exclude distant ones)
            adjusted_p = self.p * (1.2 if d_bs < 60 else 1.0)
            if np.random.random() < adjusted_p:
                chs.append(n)

        if not chs:
            chs = [max(alive, key=lambda n: n.current_energy)]

        # Cluster formation
        clusters = {ch.node_id: [] for ch in chs}
        for n in alive:
            if n not in chs:
                closest_ch = min(chs, key=lambda ch: n.distance_to(ch))
                clusters[closest_ch.node_id].append(n)

        # Intra-cluster: standard transmission (short distances, high PDR)
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

        # CH to BS: Enhanced with ARQ
        for ch in chs:
            if not ch.is_alive:
                continue

            d_bs = ch.distance_to(self.bs_pos)
            pdr = self.channel.calculate_pdr(d_bs)

            self.packets_sent += 1
            delivered = False

            # Try up to max_retries times
            for attempt in range(1 + self.max_retries):
                tx_e = self.E_tx * self.packet_size
                ch.consume_energy(tx_e)
                self.total_energy += tx_e

                if np.random.random() < pdr:
                    delivered = True
                    break

                if attempt > 0:
                    self.retries_used += 1

            # If still failed and CH is far, try cooperative with nearest other CH
            if not delivered and d_bs > self.far_ch_threshold:
                other_chs = [c for c in chs if c.node_id != ch.node_id and c.is_alive]
                if other_chs:
                    helper = min(other_chs, key=lambda c: c.distance_to(self.bs_pos))
                    d_helper_bs = helper.distance_to(self.bs_pos)

                    # Relay through helper
                    d_to_helper = ch.distance_to(helper)
                    tx_e = self.E_tx * self.packet_size
                    rx_e = self.E_rx * self.packet_size
                    ch.consume_energy(tx_e)
                    helper.consume_energy(rx_e)
                    self.total_energy += tx_e + rx_e

                    pdr_relay = self.channel.calculate_pdr(d_to_helper)
                    if np.random.random() < pdr_relay:
                        # Helper -> BS
                        tx_e = self.E_tx * self.packet_size
                        helper.consume_energy(tx_e)
                        self.total_energy += tx_e

                        pdr_helper = self.channel.calculate_pdr(d_helper_bs)
                        if np.random.random() < pdr_helper:
                            delivered = True
                            self.cooperative_used += 1

            if delivered:
                self.packets_delivered += 1

        return True

    def get_results(self):
        pdr = self.packets_delivered / max(1, self.packets_sent)
        return {
            'protocol': 'AERISFinal',
            'pdr': pdr,
            'total_energy': self.total_energy,
            'alive_nodes': len([n for n in self.nodes if n.is_alive]),
            'retries_used': self.retries_used,
            'cooperative_used': self.cooperative_used
        }


class StandardLEACH:
    """LEACH baseline."""

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

        chs = [n for n in alive if np.random.random() < self.p]
        if not chs:
            chs = [max(alive, key=lambda n: n.current_energy)]

        clusters = {ch.node_id: [] for ch in chs}
        for n in alive:
            if n not in chs:
                closest_ch = min(chs, key=lambda ch: n.distance_to(ch))
                clusters[closest_ch.node_id].append(n)

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
                if np.random.random() < self.channel.calculate_pdr(d):
                    self.packets_delivered += 1

        for ch in chs:
            if not ch.is_alive:
                continue
            d_bs = ch.distance_to(self.bs_pos)
            tx_e = self.E_tx * self.packet_size
            ch.consume_energy(tx_e)
            self.total_energy += tx_e
            self.packets_sent += 1
            if np.random.random() < self.channel.calculate_pdr(d_bs):
                self.packets_delivered += 1

        return True

    def get_results(self):
        pdr = self.packets_delivered / max(1, self.packets_sent)
        return {
            'protocol': 'LEACH',
            'pdr': pdr,
            'total_energy': self.total_energy,
            'alive_nodes': len([n for n in self.nodes if n.is_alive])
        }


def create_network(num_nodes=54, area_size=100, seed=42):
    np.random.seed(seed)
    nodes = [Node(i, np.random.uniform(0, area_size), np.random.uniform(0, area_size)) for i in range(num_nodes)]
    bs_pos = (area_size / 2, area_size + 20)
    return nodes, bs_pos


def run_experiment(protocol_class, nodes, bs_pos, channel, max_rounds=200, **kwargs):
    test_nodes = [Node(n.node_id, n.x, n.y, n.initial_energy) for n in nodes]
    protocol = protocol_class(test_nodes, bs_pos, channel, **kwargs)
    for _ in range(max_rounds):
        if not protocol.run_round():
            break
    return protocol.get_results()


def main():
    print("=" * 60)
    print("AERIS Final: Targeted CH-to-BS Reliability Enhancement")
    print("Strategy: ARQ + Cooperative for distant CHs only")
    print("=" * 60)

    num_runs = 30
    max_rounds = 200
    channel = ChannelModel(EnvironmentType.INDOOR_OFFICE)

    # Test different retry counts
    configs = [
        ('LEACH', StandardLEACH, {}),
        ('AERIS_ARQ1', AERISFinal, {'max_retries': 1}),
        ('AERIS_ARQ2', AERISFinal, {'max_retries': 2}),
        ('AERIS_ARQ3', AERISFinal, {'max_retries': 3}),
    ]

    results = {name: [] for name, _, _ in configs}

    print(f"\nRunning {num_runs} experiments per config...")

    for run in range(num_runs):
        seed = 1000 + run
        nodes, bs_pos = create_network(54, 100, seed)

        for name, cls, kwargs in configs:
            r = run_experiment(cls, nodes, bs_pos, channel, max_rounds, **kwargs)
            results[name].append(r)

        if (run + 1) % 10 == 0:
            print(f"  Completed {run + 1}/{num_runs}")

    # Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    summary = {}
    for name in results:
        runs = results[name]
        pdrs = [r['pdr'] for r in runs]
        energies = [r['total_energy'] for r in runs]

        summary[name] = {
            'pdr_mean': np.mean(pdrs),
            'pdr_ci95': 1.96 * np.std(pdrs) / np.sqrt(len(pdrs)),
            'energy_mean': np.mean(energies),
            'energy_std': np.std(energies)
        }

        print(f"\n{name}:")
        print(f"  PDR: {summary[name]['pdr_mean']*100:.2f}% +/- {summary[name]['pdr_ci95']*100:.2f}%")
        print(f"  Energy: {summary[name]['energy_mean']:.3f}J +/- {summary[name]['energy_std']:.3f}J")

        if 'AERIS' in name:
            retries = np.mean([r['retries_used'] for r in runs])
            coop = np.mean([r['cooperative_used'] for r in runs])
            print(f"  Avg retries: {retries:.1f}, Cooperative tx: {coop:.1f}")

    # Analysis
    print("\n" + "=" * 60)
    print("IMPROVEMENT vs LEACH")
    print("=" * 60)

    leach = summary['LEACH']
    for name in ['AERIS_ARQ1', 'AERIS_ARQ2', 'AERIS_ARQ3']:
        aeris = summary[name]
        pdr_imp = (aeris['pdr_mean'] - leach['pdr_mean']) * 100
        energy_overhead = (aeris['energy_mean'] / leach['energy_mean'] - 1) * 100
        efficiency = pdr_imp / max(0.1, energy_overhead) if energy_overhead > 0 else float('inf')

        print(f"\n{name}:")
        print(f"  PDR improvement: {pdr_imp:+.2f}%")
        print(f"  Energy overhead: {energy_overhead:+.1f}%")
        print(f"  Efficiency ratio: {efficiency:.2f} (PDR gain per % energy)")

    # Save best result
    output_file = Path(__file__).parent.parent / 'results' / 'aeris_final_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {k: {sk: float(sv) for sk, sv in v.items()} for k, v in summary.items()}
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
