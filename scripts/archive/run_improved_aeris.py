#!/usr/bin/env python3
"""
Improved AERIS Algorithm with Smart Routing

Key improvements:
1. Gateway only used when PDR_twohop > PDR_direct (smart routing decision)
2. Multi-path redundancy for critical links
3. Adaptive power control based on link quality
4. Link quality prediction for proactive switching
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


class ImprovedChannelModel:
    """Enhanced channel model with power control."""

    def __init__(self, environment: EnvironmentType = EnvironmentType.INDOOR_OFFICE):
        self.shadowing_model = LogNormalShadowingModel(environment)
        self.link_quality = IEEE802154LinkQuality()
        self.base_tx_power_dbm = 0.0  # CC2420 typical

    def calculate_pdr(self, distance: float, tx_power_dbm: float = None) -> float:
        """Calculate PDR with optional power control."""
        if tx_power_dbm is None:
            tx_power_dbm = self.base_tx_power_dbm
        received_power = self.shadowing_model.calculate_received_power(tx_power_dbm, distance)
        rssi = self.link_quality.calculate_rssi(received_power)
        pdr = self.link_quality.calculate_pdr(rssi)
        return pdr

    def get_adaptive_power(self, distance: float, target_pdr: float = 0.9) -> float:
        """Calculate required TX power to achieve target PDR."""
        # Binary search for required power
        low, high = -10.0, 10.0
        while high - low > 0.5:
            mid = (low + high) / 2
            pdr = self.calculate_pdr(distance, mid)
            if pdr < target_pdr:
                low = mid
            else:
                high = mid
        return high


class SmartNode:
    """Node with energy tracking and link quality history."""

    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True
        self.link_history = {}  # neighbor_id -> [pdr_history]

    def distance_to(self, other) -> float:
        if hasattr(other, 'x'):
            return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
        return math.sqrt((self.x - other[0])**2 + (self.y - other[1])**2)

    def consume_energy(self, amount: float):
        self.current_energy -= amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False

    def update_link_history(self, neighbor_id: int, pdr: float):
        """Track link quality over time for prediction."""
        if neighbor_id not in self.link_history:
            self.link_history[neighbor_id] = []
        self.link_history[neighbor_id].append(pdr)
        # Keep only recent history
        if len(self.link_history[neighbor_id]) > 10:
            self.link_history[neighbor_id] = self.link_history[neighbor_id][-10:]

    def predict_link_quality(self, neighbor_id: int) -> float:
        """Predict future link quality using EMA."""
        if neighbor_id not in self.link_history or not self.link_history[neighbor_id]:
            return 0.5  # Unknown
        history = self.link_history[neighbor_id]
        # Exponential moving average
        alpha = 0.3
        ema = history[0]
        for pdr in history[1:]:
            ema = alpha * pdr + (1 - alpha) * ema
        return ema


class ImprovedAERIS:
    """AERIS with smart routing decisions."""

    def __init__(self, nodes, bs_pos, channel_model):
        self.nodes = nodes
        self.bs_pos = bs_pos
        self.channel = channel_model
        self.p = 0.1  # CH probability

        # Energy parameters (CC2420)
        self.E_tx = 208.8e-9  # J/bit
        self.E_rx = 225.6e-9  # J/bit
        self.packet_size = 4000  # bits

        # Smart routing thresholds
        self.min_pdr_threshold = 0.3  # Use gateway if direct PDR below this
        self.gateway_benefit_margin = 0.05  # Gateway must improve PDR by at least 5%

        # Statistics
        self.packets_sent = 0
        self.packets_delivered = 0
        self.total_energy = 0.0
        self.gateway_used_count = 0
        self.direct_used_count = 0
        self.redundancy_used_count = 0

    def _select_gateway_candidates(self, chs):
        """Select multiple gateway candidates based on position and energy."""
        if not chs:
            return []

        def score(ch):
            d_bs = ch.distance_to(self.bs_pos)
            max_d = 150
            d_norm = d_bs / max_d
            e_norm = ch.current_energy / ch.initial_energy
            # Score: closer to BS and higher energy
            return -0.6 * d_norm + 0.4 * e_norm

        # Return top 3 candidates
        sorted_chs = sorted(chs, key=score, reverse=True)
        return sorted_chs[:min(3, len(sorted_chs))]

    def _calculate_best_route(self, ch, gateway_candidates):
        """Determine best route: direct or via gateway."""
        d_bs_direct = ch.distance_to(self.bs_pos)
        pdr_direct = self.channel.calculate_pdr(d_bs_direct)

        best_route = {
            'type': 'direct',
            'pdr': pdr_direct,
            'gateway': None,
            'energy_cost': self.E_tx * self.packet_size
        }

        # Check if any gateway provides better PDR
        for gw in gateway_candidates:
            if gw.node_id == ch.node_id:
                continue

            d_to_gw = ch.distance_to(gw)
            d_gw_to_bs = gw.distance_to(self.bs_pos)

            pdr_hop1 = self.channel.calculate_pdr(d_to_gw)
            pdr_hop2 = self.channel.calculate_pdr(d_gw_to_bs)
            pdr_twohop = pdr_hop1 * pdr_hop2

            # Only use gateway if it provides significant benefit
            if pdr_twohop > pdr_direct + self.gateway_benefit_margin:
                if pdr_twohop > best_route['pdr']:
                    energy_cost = (self.E_tx + self.E_rx) * self.packet_size * 2
                    best_route = {
                        'type': 'gateway',
                        'pdr': pdr_twohop,
                        'gateway': gw,
                        'energy_cost': energy_cost
                    }

        # Multi-path redundancy for very low PDR links
        if best_route['pdr'] < self.min_pdr_threshold and len(gateway_candidates) >= 2:
            # Use two paths for redundancy
            best_route['type'] = 'redundant'
            # At least one path should succeed
            best_route['pdr'] = 1 - (1 - pdr_direct) * (1 - best_route['pdr'])
            best_route['energy_cost'] *= 1.5  # Extra energy for redundancy

        return best_route

    def run_round(self):
        alive = [n for n in self.nodes if n.is_alive]
        if not alive:
            return False

        # CH selection
        chs = [n for n in alive if np.random.random() < self.p]
        if not chs:
            chs = [max(alive, key=lambda n: n.current_energy)]

        # Gateway candidate selection
        gateway_candidates = self._select_gateway_candidates(chs)

        # Assign members
        clusters = {ch.node_id: [] for ch in chs}
        for n in alive:
            if n not in chs:
                closest_ch = min(chs, key=lambda ch: n.distance_to(ch))
                clusters[closest_ch.node_id].append(n)

        # Intra-cluster transmission (member -> CH)
        for ch in chs:
            members = clusters[ch.node_id]
            for m in members:
                if not m.is_alive:
                    continue

                d = m.distance_to(ch)
                pdr = self.channel.calculate_pdr(d)

                # Adaptive power for poor links
                tx_energy = self.E_tx * self.packet_size
                if pdr < 0.5:
                    # Use higher power for poor links
                    adaptive_power = self.channel.get_adaptive_power(d, target_pdr=0.7)
                    power_factor = 10 ** ((adaptive_power - 0.0) / 10)
                    tx_energy *= min(2.0, max(1.0, power_factor))
                    pdr = self.channel.calculate_pdr(d, adaptive_power)

                rx_energy = self.E_rx * self.packet_size
                m.consume_energy(tx_energy)
                ch.consume_energy(rx_energy)
                self.total_energy += tx_energy + rx_energy

                self.packets_sent += 1
                if np.random.random() < pdr:
                    self.packets_delivered += 1

        # CH to BS with smart routing
        for ch in chs:
            if not ch.is_alive:
                continue

            route = self._calculate_best_route(ch, gateway_candidates)

            if route['type'] == 'direct':
                self.direct_used_count += 1
                d_bs = ch.distance_to(self.bs_pos)
                tx_e = self.E_tx * self.packet_size
                ch.consume_energy(tx_e)
                self.total_energy += tx_e

                self.packets_sent += 1
                pdr = self.channel.calculate_pdr(d_bs)
                if np.random.random() < pdr:
                    self.packets_delivered += 1

            elif route['type'] == 'gateway':
                self.gateway_used_count += 1
                gw = route['gateway']

                # CH -> Gateway
                d_gw = ch.distance_to(gw)
                tx_e = self.E_tx * self.packet_size
                rx_e = self.E_rx * self.packet_size
                ch.consume_energy(tx_e)
                gw.consume_energy(rx_e)
                self.total_energy += tx_e + rx_e

                self.packets_sent += 1
                pdr1 = self.channel.calculate_pdr(d_gw)

                if np.random.random() < pdr1:
                    # Gateway -> BS
                    d_bs = gw.distance_to(self.bs_pos)
                    tx_e = self.E_tx * self.packet_size
                    gw.consume_energy(tx_e)
                    self.total_energy += tx_e

                    pdr2 = self.channel.calculate_pdr(d_bs)
                    if np.random.random() < pdr2:
                        self.packets_delivered += 1

            elif route['type'] == 'redundant':
                self.redundancy_used_count += 1
                # Send via both direct and gateway paths
                delivered = False

                # Direct path
                d_bs = ch.distance_to(self.bs_pos)
                tx_e = self.E_tx * self.packet_size
                ch.consume_energy(tx_e)
                self.total_energy += tx_e
                self.packets_sent += 1

                pdr_direct = self.channel.calculate_pdr(d_bs)
                if np.random.random() < pdr_direct:
                    delivered = True

                # Gateway path (if gateway available)
                if route['gateway'] and not delivered:
                    gw = route['gateway']
                    d_gw = ch.distance_to(gw)
                    tx_e = self.E_tx * self.packet_size
                    rx_e = self.E_rx * self.packet_size
                    ch.consume_energy(tx_e)
                    gw.consume_energy(rx_e)
                    self.total_energy += tx_e + rx_e

                    pdr1 = self.channel.calculate_pdr(d_gw)
                    if np.random.random() < pdr1:
                        d_bs_gw = gw.distance_to(self.bs_pos)
                        tx_e = self.E_tx * self.packet_size
                        gw.consume_energy(tx_e)
                        self.total_energy += tx_e

                        pdr2 = self.channel.calculate_pdr(d_bs_gw)
                        if np.random.random() < pdr2:
                            delivered = True

                if delivered:
                    self.packets_delivered += 1

        return True

    def get_results(self):
        pdr = self.packets_delivered / max(1, self.packets_sent)
        total_routes = self.gateway_used_count + self.direct_used_count + self.redundancy_used_count
        return {
            'protocol': 'ImprovedAERIS',
            'packets_sent': self.packets_sent,
            'packets_delivered': self.packets_delivered,
            'pdr': pdr,
            'total_energy': self.total_energy,
            'alive_nodes': len([n for n in self.nodes if n.is_alive]),
            'routing_stats': {
                'direct': self.direct_used_count,
                'gateway': self.gateway_used_count,
                'redundant': self.redundancy_used_count,
                'gateway_ratio': self.gateway_used_count / max(1, total_routes)
            }
        }


class FairLEACH:
    """LEACH baseline with same channel model."""

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
            members = clusters[ch.node_id]
            for m in members:
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
        return {
            'protocol': 'LEACH',
            'packets_sent': self.packets_sent,
            'packets_delivered': self.packets_delivered,
            'pdr': pdr,
            'total_energy': self.total_energy,
            'alive_nodes': len([n for n in self.nodes if n.is_alive])
        }


def create_network(num_nodes=54, area_size=100, seed=42):
    np.random.seed(seed)
    nodes = []
    for i in range(num_nodes):
        x = np.random.uniform(0, area_size)
        y = np.random.uniform(0, area_size)
        nodes.append(SmartNode(i, x, y, initial_energy=2.0))
    bs_pos = (area_size / 2, area_size + 20)
    return nodes, bs_pos


def run_experiment(protocol_class, nodes, bs_pos, channel, max_rounds=200, **kwargs):
    test_nodes = [SmartNode(n.node_id, n.x, n.y, n.initial_energy) for n in nodes]
    protocol = protocol_class(test_nodes, bs_pos, channel, **kwargs)
    for r in range(max_rounds):
        if not protocol.run_round():
            break
    return protocol.get_results()


def main():
    print("=" * 60)
    print("IMPROVED AERIS: Smart Routing Algorithm")
    print("=" * 60)

    num_runs = 30
    max_rounds = 200
    results = {
        'LEACH': [],
        'ImprovedAERIS': []
    }

    channel = ImprovedChannelModel(EnvironmentType.INDOOR_OFFICE)

    print(f"\nRunning {num_runs} experiments per protocol...")

    for run in range(num_runs):
        seed = 1000 + run
        nodes, bs_pos = create_network(num_nodes=54, area_size=100, seed=seed)

        # LEACH
        r = run_experiment(FairLEACH, nodes, bs_pos, channel, max_rounds)
        results['LEACH'].append(r)

        # Improved AERIS
        r = run_experiment(ImprovedAERIS, nodes, bs_pos, channel, max_rounds)
        results['ImprovedAERIS'].append(r)

        if (run + 1) % 10 == 0:
            print(f"  Completed {run + 1}/{num_runs} runs")

    # Compute statistics
    print("\n" + "=" * 60)
    print("RESULTS")
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
        print(f"  PDR: {summary[name]['pdr_mean']*100:.2f}% +/- {summary[name]['pdr_ci95']*100:.2f}%")
        print(f"  Energy: {summary[name]['energy_mean']:.3f}J +/- {summary[name]['energy_std']:.3f}J")

        # Routing stats for ImprovedAERIS
        if name == 'ImprovedAERIS':
            gw_ratios = [r['routing_stats']['gateway_ratio'] for r in runs]
            print(f"  Gateway usage: {np.mean(gw_ratios)*100:.1f}%")

    # Improvement analysis
    print("\n" + "=" * 60)
    print("IMPROVEMENT ANALYSIS")
    print("=" * 60)

    leach_pdr = summary['LEACH']['pdr_mean']
    aeris_pdr = summary['ImprovedAERIS']['pdr_mean']
    leach_energy = summary['LEACH']['energy_mean']
    aeris_energy = summary['ImprovedAERIS']['energy_mean']

    print(f"\nImprovedAERIS vs LEACH:")
    print(f"  PDR improvement: {(aeris_pdr - leach_pdr)*100:.2f}%")
    print(f"  Relative PDR improvement: {(aeris_pdr/leach_pdr - 1)*100:.1f}%")
    print(f"  Energy overhead: {(aeris_energy/leach_energy - 1)*100:.1f}%")

    # Energy efficiency (PDR per Joule)
    leach_eff = leach_pdr / leach_energy
    aeris_eff = aeris_pdr / aeris_energy
    print(f"  Energy efficiency: LEACH={leach_eff:.4f}, AERIS={aeris_eff:.4f}")

    # Save results
    output_dir = Path(__file__).parent.parent / 'results'
    output_file = output_dir / 'improved_aeris_results.json'

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'config': {
                'num_runs': num_runs,
                'max_rounds': max_rounds,
                'num_nodes': 54,
                'channel_model': 'ImprovedLogNormalShadowing_INDOOR_OFFICE'
            },
            'summary': summary,
            'raw_results': results
        }, f, indent=2, default=str)

    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
