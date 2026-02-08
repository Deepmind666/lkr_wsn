#!/usr/bin/env python3
"""
Fair Comparison Experiment: AERIS vs Baselines with Same Channel Model

This script ensures all protocols use the same channel model for fair comparison.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import json
import math
from datetime import datetime
from pathlib import Path

# Import channel model
from realistic_channel_model import LogNormalShadowingModel, IEEE802154LinkQuality, EnvironmentType


class FairChannelModel:
    """Unified channel model for all protocols."""

    def __init__(self, environment: EnvironmentType = EnvironmentType.INDOOR_OFFICE):
        self.shadowing_model = LogNormalShadowingModel(environment)
        self.link_quality = IEEE802154LinkQuality()
        self.tx_power_dbm = 0.0  # CC2420 typical

    def calculate_pdr(self, distance: float) -> float:
        """Calculate packet delivery ratio for given distance."""
        received_power = self.shadowing_model.calculate_received_power(self.tx_power_dbm, distance)
        rssi = self.link_quality.calculate_rssi(received_power)
        pdr = self.link_quality.calculate_pdr(rssi)
        return pdr


class SimpleNode:
    """Simple node for fair comparison."""

    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True

    def distance_to(self, other) -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def consume_energy(self, amount: float):
        self.current_energy -= amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False


class FairLEACH:
    """LEACH with fair channel model."""

    def __init__(self, nodes, bs_pos, channel_model):
        self.nodes = nodes
        self.bs_pos = bs_pos
        self.channel = channel_model
        self.p = 0.1  # CH probability

        # Energy parameters (CC2420)
        self.E_tx = 208.8e-9  # J/bit
        self.E_rx = 225.6e-9  # J/bit
        self.packet_size = 4000  # bits

        # Statistics
        self.packets_sent = 0
        self.packets_delivered = 0
        self.total_energy = 0.0

    def run_round(self):
        alive = [n for n in self.nodes if n.is_alive]
        if not alive:
            return False

        # CH selection
        chs = [n for n in alive if np.random.random() < self.p]
        if not chs:
            chs = [max(alive, key=lambda n: n.current_energy)]

        # Assign members
        clusters = {ch.node_id: [] for ch in chs}
        for n in alive:
            if n not in chs:
                closest_ch = min(chs, key=lambda ch: n.distance_to(ch))
                clusters[closest_ch.node_id].append(n)

        # Intra-cluster transmission
        for ch in chs:
            members = clusters[ch.node_id]
            for m in members:
                d = m.distance_to(ch)

                # Energy
                tx_e = self.E_tx * self.packet_size
                rx_e = self.E_rx * self.packet_size
                m.consume_energy(tx_e)
                ch.consume_energy(rx_e)
                self.total_energy += tx_e + rx_e

                # PDR using channel model
                self.packets_sent += 1
                pdr = self.channel.calculate_pdr(d)
                if np.random.random() < pdr:
                    self.packets_delivered += 1

        # CH to BS
        for ch in chs:
            if not ch.is_alive:
                continue
            d_bs = math.sqrt((ch.x - self.bs_pos[0])**2 + (ch.y - self.bs_pos[1])**2)

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
        return {
            'protocol': 'LEACH',
            'packets_sent': self.packets_sent,
            'packets_delivered': self.packets_delivered,
            'pdr': pdr,
            'total_energy': self.total_energy,
            'alive_nodes': len([n for n in self.nodes if n.is_alive])
        }


class FairAERIS:
    """AERIS with fair channel model (same as baselines)."""

    def __init__(self, nodes, bs_pos, channel_model, gateway_enabled=True, safety_enabled=True):
        self.nodes = nodes
        self.bs_pos = bs_pos
        self.channel = channel_model
        self.p = 0.1
        self.gateway_enabled = gateway_enabled
        self.safety_enabled = safety_enabled
        self.safety_threshold = 0.5  # PDR threshold for safety mode

        # Energy parameters
        self.E_tx = 208.8e-9
        self.E_rx = 225.6e-9
        self.packet_size = 4000

        # Statistics
        self.packets_sent = 0
        self.packets_delivered = 0
        self.total_energy = 0.0

    def _select_gateway(self, chs):
        """Select gateway CH closest to BS with good energy."""
        if not chs:
            return None

        # Score: closer to BS + higher energy
        def score(ch):
            d_bs = math.sqrt((ch.x - self.bs_pos[0])**2 + (ch.y - self.bs_pos[1])**2)
            max_d = 150  # area diagonal
            d_norm = d_bs / max_d
            e_norm = ch.current_energy / ch.initial_energy
            return -0.7 * d_norm + 0.3 * e_norm

        return max(chs, key=score)

    def run_round(self):
        alive = [n for n in self.nodes if n.is_alive]
        if not alive:
            return False

        # CH selection
        chs = [n for n in alive if np.random.random() < self.p]
        if not chs:
            chs = [max(alive, key=lambda n: n.current_energy)]

        # Gateway selection
        gateway = self._select_gateway(chs) if self.gateway_enabled else None

        # Assign members
        clusters = {ch.node_id: [] for ch in chs}
        for n in alive:
            if n not in chs:
                closest_ch = min(chs, key=lambda ch: n.distance_to(ch))
                clusters[closest_ch.node_id].append(n)

        # Intra-cluster transmission
        for ch in chs:
            members = clusters[ch.node_id]
            for m in members:
                d = m.distance_to(ch)

                tx_e = self.E_tx * self.packet_size
                rx_e = self.E_rx * self.packet_size
                m.consume_energy(tx_e)
                ch.consume_energy(rx_e)
                self.total_energy += tx_e + rx_e

                self.packets_sent += 1
                pdr = self.channel.calculate_pdr(d)

                # Safety mode: retry if PDR low
                if self.safety_enabled and pdr < self.safety_threshold:
                    # Retry once with extra energy
                    m.consume_energy(tx_e * 0.5)
                    self.total_energy += tx_e * 0.5
                    pdr = min(0.99, pdr * 1.3)  # Improved PDR from retry

                if np.random.random() < pdr:
                    self.packets_delivered += 1

        # CH to BS (via gateway if enabled)
        for ch in chs:
            if not ch.is_alive:
                continue

            if self.gateway_enabled and gateway and ch != gateway:
                # Two-hop: CH -> Gateway -> BS
                d_gw = ch.distance_to(gateway)
                d_bs = math.sqrt((gateway.x - self.bs_pos[0])**2 + (gateway.y - self.bs_pos[1])**2)

                # CH -> Gateway
                tx_e = self.E_tx * self.packet_size
                rx_e = self.E_rx * self.packet_size
                ch.consume_energy(tx_e)
                gateway.consume_energy(rx_e)
                self.total_energy += tx_e + rx_e

                self.packets_sent += 1
                pdr1 = self.channel.calculate_pdr(d_gw)

                if np.random.random() < pdr1:
                    # Gateway -> BS
                    tx_e = self.E_tx * self.packet_size
                    gateway.consume_energy(tx_e)
                    self.total_energy += tx_e

                    pdr2 = self.channel.calculate_pdr(d_bs)
                    if np.random.random() < pdr2:
                        self.packets_delivered += 1
            else:
                # Direct: CH -> BS
                d_bs = math.sqrt((ch.x - self.bs_pos[0])**2 + (ch.y - self.bs_pos[1])**2)

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
        variant = 'AERIS_FULL'
        if not self.gateway_enabled:
            variant = 'AERIS_noGW'
        elif not self.safety_enabled:
            variant = 'AERIS_noSafety'

        return {
            'protocol': variant,
            'packets_sent': self.packets_sent,
            'packets_delivered': self.packets_delivered,
            'pdr': pdr,
            'total_energy': self.total_energy,
            'alive_nodes': len([n for n in self.nodes if n.is_alive])
        }


def create_network(num_nodes=54, area_size=100, seed=42):
    """Create network with fixed seed for reproducibility."""
    np.random.seed(seed)
    nodes = []
    for i in range(num_nodes):
        x = np.random.uniform(0, area_size)
        y = np.random.uniform(0, area_size)
        nodes.append(SimpleNode(i, x, y, initial_energy=2.0))
    bs_pos = (area_size / 2, area_size + 20)  # BS outside area
    return nodes, bs_pos


def run_experiment(protocol_class, nodes, bs_pos, channel, max_rounds=200, **kwargs):
    """Run single experiment."""
    # Deep copy nodes
    test_nodes = [SimpleNode(n.node_id, n.x, n.y, n.initial_energy) for n in nodes]

    protocol = protocol_class(test_nodes, bs_pos, channel, **kwargs)

    for r in range(max_rounds):
        if not protocol.run_round():
            break

    return protocol.get_results()


def main():
    print("=" * 60)
    print("FAIR COMPARISON: AERIS vs Baselines (Same Channel Model)")
    print("=" * 60)

    # Setup
    num_runs = 30
    max_rounds = 200
    results = {
        'LEACH': [],
        'AERIS_FULL': [],
        'AERIS_noGW': [],
        'AERIS_noSafety': []
    }

    channel = FairChannelModel(EnvironmentType.INDOOR_OFFICE)

    print(f"\nRunning {num_runs} experiments per protocol...")

    for run in range(num_runs):
        seed = 1000 + run
        nodes, bs_pos = create_network(num_nodes=54, area_size=100, seed=seed)

        # LEACH
        r = run_experiment(FairLEACH, nodes, bs_pos, channel, max_rounds)
        results['LEACH'].append(r)

        # AERIS variants
        r = run_experiment(FairAERIS, nodes, bs_pos, channel, max_rounds,
                          gateway_enabled=True, safety_enabled=True)
        results['AERIS_FULL'].append(r)

        r = run_experiment(FairAERIS, nodes, bs_pos, channel, max_rounds,
                          gateway_enabled=False, safety_enabled=True)
        results['AERIS_noGW'].append(r)

        r = run_experiment(FairAERIS, nodes, bs_pos, channel, max_rounds,
                          gateway_enabled=True, safety_enabled=False)
        results['AERIS_noSafety'].append(r)

        if (run + 1) % 10 == 0:
            print(f"  Completed {run + 1}/{num_runs} runs")

    # Compute statistics
    print("\n" + "=" * 60)
    print("RESULTS (Fair Comparison with Same Channel Model)")
    print("=" * 60)

    summary = {}
    for name, runs in results.items():
        pdrs = [r['pdr'] for r in runs]
        energies = [r['total_energy'] for r in runs]

        summary[name] = {
            'pdr_mean': np.mean(pdrs),
            'pdr_std': np.std(pdrs),
            'pdr_ci95': 1.96 * np.std(pdrs) / np.sqrt(len(pdrs)),
            'energy_mean': np.mean(energies),
            'energy_std': np.std(energies),
            'n_runs': len(runs)
        }

        print(f"\n{name}:")
        print(f"  PDR: {summary[name]['pdr_mean']*100:.2f}% ± {summary[name]['pdr_ci95']*100:.2f}%")
        print(f"  Energy: {summary[name]['energy_mean']:.3f}J ± {summary[name]['energy_std']:.3f}J")

    # Save results
    output_dir = Path(__file__).parent.parent / 'results'
    output_file = output_dir / 'fair_comparison_results.json'

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'config': {
                'num_runs': num_runs,
                'max_rounds': max_rounds,
                'num_nodes': 54,
                'channel_model': 'LogNormalShadowing_INDOOR_OFFICE'
            },
            'summary': summary,
            'raw_results': {k: v for k, v in results.items()}
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    # Print improvement analysis
    print("\n" + "=" * 60)
    print("IMPROVEMENT ANALYSIS")
    print("=" * 60)

    leach_pdr = summary['LEACH']['pdr_mean']
    aeris_pdr = summary['AERIS_FULL']['pdr_mean']

    print(f"\nAERIS vs LEACH:")
    print(f"  PDR improvement: {(aeris_pdr - leach_pdr)*100:.2f}%")
    print(f"  Relative improvement: {(aeris_pdr/leach_pdr - 1)*100:.1f}%")

    print(f"\nGateway contribution (AERIS_FULL vs AERIS_noGW):")
    nogw_pdr = summary['AERIS_noGW']['pdr_mean']
    print(f"  PDR difference: {(aeris_pdr - nogw_pdr)*100:.2f}%")

    print(f"\nSafety contribution (AERIS_FULL vs AERIS_noSafety):")
    nosafe_pdr = summary['AERIS_noSafety']['pdr_mean']
    print(f"  PDR difference: {(aeris_pdr - nosafe_pdr)*100:.2f}%")


if __name__ == '__main__':
    main()
