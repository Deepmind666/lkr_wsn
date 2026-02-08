#!/usr/bin/env python3
"""
AERIS v2: Environment-Adaptive Intelligent Routing System

Enhanced features:
1. Link quality prediction using moving average
2. Environment-adaptive transmission strategies
3. Cooperative redundancy for critical links
4. Load-aware cluster head rotation
5. Proactive gateway switching before link degradation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import json
import math
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from realistic_channel_model import LogNormalShadowingModel, IEEE802154LinkQuality, EnvironmentType


class AdaptiveChannelModel:
    """Channel model with environment adaptation and link prediction."""

    def __init__(self, environment: EnvironmentType = EnvironmentType.INDOOR_OFFICE):
        self.shadowing_model = LogNormalShadowingModel(environment)
        self.link_quality = IEEE802154LinkQuality()
        self.base_tx_power_dbm = 0.0
        self.environment = environment

        # Environment-specific parameters
        self.env_params = {
            EnvironmentType.INDOOR_OFFICE: {
                'path_loss_exp': 3.0,
                'shadowing_std': 4.0,
                'reliability_margin': 3.0  # dB margin for reliability
            },
            EnvironmentType.OUTDOOR_OPEN: {
                'path_loss_exp': 2.0,
                'shadowing_std': 2.0,
                'reliability_margin': 2.0
            },
            EnvironmentType.OUTDOOR_SUBURBAN: {
                'path_loss_exp': 2.5,
                'shadowing_std': 3.0,
                'reliability_margin': 2.5
            }
        }

    def calculate_pdr(self, distance: float, tx_power_dbm: float = None,
                      with_margin: bool = False) -> float:
        """Calculate PDR with optional reliability margin."""
        if tx_power_dbm is None:
            tx_power_dbm = self.base_tx_power_dbm

        if with_margin:
            # Add margin for reliability
            margin = self.env_params.get(self.environment, {}).get('reliability_margin', 2.0)
            tx_power_dbm += margin

        received_power = self.shadowing_model.calculate_received_power(tx_power_dbm, distance)
        rssi = self.link_quality.calculate_rssi(received_power)
        pdr = self.link_quality.calculate_pdr(rssi)
        return pdr

    def get_link_category(self, distance: float) -> str:
        """Categorize link quality based on distance."""
        pdr = self.calculate_pdr(distance)
        if pdr > 0.9:
            return 'excellent'
        elif pdr > 0.7:
            return 'good'
        elif pdr > 0.5:
            return 'marginal'
        else:
            return 'poor'


class EnhancedNode:
    """Node with link prediction and energy awareness."""

    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True

        # Link quality tracking
        self.link_history = defaultdict(list)  # neighbor_id -> [pdr_samples]
        self.link_ema = {}  # neighbor_id -> ema_pdr
        self.alpha = 0.3  # EMA smoothing factor

        # CH rotation tracking
        self.ch_count = 0
        self.last_ch_round = -100

    def distance_to(self, other) -> float:
        if hasattr(other, 'x'):
            return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
        return math.sqrt((self.x - other[0])**2 + (self.y - other[1])**2)

    def consume_energy(self, amount: float):
        self.current_energy -= amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False

    def update_link_quality(self, neighbor_id: int, pdr: float):
        """Update link quality estimate with EMA."""
        if neighbor_id in self.link_ema:
            self.link_ema[neighbor_id] = (self.alpha * pdr +
                                          (1 - self.alpha) * self.link_ema[neighbor_id])
        else:
            self.link_ema[neighbor_id] = pdr

        self.link_history[neighbor_id].append(pdr)
        if len(self.link_history[neighbor_id]) > 20:
            self.link_history[neighbor_id] = self.link_history[neighbor_id][-20:]

    def predict_link_quality(self, neighbor_id: int, current_pdr: float) -> float:
        """Predict future link quality using trend analysis."""
        if neighbor_id not in self.link_ema:
            return current_pdr

        ema = self.link_ema[neighbor_id]
        history = self.link_history[neighbor_id]

        if len(history) >= 5:
            # Check for degradation trend
            recent = history[-5:]
            trend = (recent[-1] - recent[0]) / 5
            predicted = ema + trend * 2  # Predict 2 steps ahead
            return max(0.1, min(1.0, predicted))

        return ema

    def get_energy_ratio(self) -> float:
        """Get remaining energy ratio."""
        return self.current_energy / self.initial_energy


class AERISv2:
    """AERIS v2: Environment-Adaptive Intelligent Routing."""

    def __init__(self, nodes, bs_pos, channel_model):
        self.nodes = nodes
        self.bs_pos = bs_pos
        self.channel = channel_model

        # Energy parameters
        self.E_tx = 208.8e-9
        self.E_rx = 225.6e-9
        self.packet_size = 4000

        # Adaptive CH probability
        self.base_p = 0.1
        self.round_num = 0

        # Thresholds
        self.min_pdr_for_direct = 0.6
        self.gateway_benefit_threshold = 0.1
        self.redundancy_pdr_threshold = 0.4
        self.low_energy_threshold = 0.3

        # Statistics
        self.packets_sent = 0
        self.packets_delivered = 0
        self.total_energy = 0.0

        self.route_stats = {
            'direct': 0,
            'gateway': 0,
            'redundant': 0,
            'cooperative': 0
        }

    def _get_adaptive_ch_probability(self, node) -> float:
        """Adaptive CH probability based on energy and history."""
        base = self.base_p

        # Energy factor: higher energy = higher probability
        e_ratio = node.get_energy_ratio()
        energy_factor = 0.5 + 0.5 * e_ratio

        # History factor: avoid nodes that were recently CH
        rounds_since_ch = self.round_num - node.last_ch_round
        if rounds_since_ch < 5:
            history_factor = rounds_since_ch / 5
        else:
            history_factor = 1.0

        # Location factor: prefer nodes closer to centroid
        alive = [n for n in self.nodes if n.is_alive]
        if alive:
            cx = sum(n.x for n in alive) / len(alive)
            cy = sum(n.y for n in alive) / len(alive)
            d_centroid = math.sqrt((node.x - cx)**2 + (node.y - cy)**2)
            max_d = max(math.sqrt((n.x - cx)**2 + (n.y - cy)**2) for n in alive)
            location_factor = 1.0 - 0.3 * (d_centroid / max(max_d, 1))
        else:
            location_factor = 1.0

        return base * energy_factor * history_factor * location_factor

    def _select_gateways(self, chs, top_k=3):
        """Select gateway CHs based on position and link quality."""
        if not chs:
            return []

        scored = []
        for ch in chs:
            d_bs = ch.distance_to(self.bs_pos)
            pdr_to_bs = self.channel.calculate_pdr(d_bs)
            e_ratio = ch.get_energy_ratio()

            # Score: high PDR to BS + high energy + central position
            score = 0.5 * pdr_to_bs + 0.3 * e_ratio
            scored.append((score, ch.node_id, ch))

        scored.sort(reverse=True, key=lambda x: (x[0], x[1]))
        return [ch for _, _, ch in scored[:top_k]]

    def _find_best_route(self, ch, gateways):
        """Find optimal route: direct, gateway, or cooperative."""
        d_bs = ch.distance_to(self.bs_pos)
        pdr_direct = self.channel.calculate_pdr(d_bs)
        predicted_pdr = ch.predict_link_quality(-1, pdr_direct)  # -1 for BS

        best = {
            'type': 'direct',
            'pdr': pdr_direct,
            'predicted_pdr': predicted_pdr,
            'gateway': None,
            'helper': None
        }

        # Check gateway routes
        for gw in gateways:
            if gw.node_id == ch.node_id:
                continue

            d_to_gw = ch.distance_to(gw)
            d_gw_to_bs = gw.distance_to(self.bs_pos)

            pdr1 = self.channel.calculate_pdr(d_to_gw)
            pdr2 = self.channel.calculate_pdr(d_gw_to_bs)
            pdr_twohop = pdr1 * pdr2

            # Consider gateway only if significant improvement
            if pdr_twohop > pdr_direct + self.gateway_benefit_threshold:
                if pdr_twohop > best['pdr']:
                    best = {
                        'type': 'gateway',
                        'pdr': pdr_twohop,
                        'predicted_pdr': pdr_twohop,
                        'gateway': gw,
                        'helper': None
                    }

        # Cooperative transmission for very poor links
        if best['pdr'] < self.redundancy_pdr_threshold and gateways:
            # Multi-path: at least one should succeed
            combined_fail = (1 - pdr_direct)
            for gw in gateways[:2]:  # Use top 2 gateways
                if gw.node_id != ch.node_id:
                    d_gw = ch.distance_to(gw)
                    d_bs_gw = gw.distance_to(self.bs_pos)
                    pdr_via_gw = self.channel.calculate_pdr(d_gw) * self.channel.calculate_pdr(d_bs_gw)
                    combined_fail *= (1 - pdr_via_gw)

            cooperative_pdr = 1 - combined_fail
            if cooperative_pdr > best['pdr'] + 0.1:
                best = {
                    'type': 'cooperative',
                    'pdr': cooperative_pdr,
                    'predicted_pdr': cooperative_pdr,
                    'gateway': gateways[0] if gateways else None,
                    'helper': gateways[1] if len(gateways) > 1 else None
                }

        return best

    def run_round(self):
        self.round_num += 1
        alive = [n for n in self.nodes if n.is_alive]
        if not alive:
            return False

        # Adaptive CH selection
        chs = []
        for n in alive:
            p = self._get_adaptive_ch_probability(n)
            if np.random.random() < p:
                chs.append(n)
                n.ch_count += 1
                n.last_ch_round = self.round_num

        if not chs:
            # Select node with highest energy
            best = max(alive, key=lambda n: n.current_energy)
            chs = [best]
            best.ch_count += 1
            best.last_ch_round = self.round_num

        # Gateway selection
        gateways = self._select_gateways(chs, top_k=3)

        # Cluster formation
        clusters = {ch.node_id: [] for ch in chs}
        for n in alive:
            if n not in chs:
                closest_ch = min(chs, key=lambda ch: n.distance_to(ch))
                clusters[closest_ch.node_id].append(n)

        # Intra-cluster transmission
        for ch in chs:
            members = clusters[ch.node_id]
            for m in members:
                if not m.is_alive:
                    continue

                d = m.distance_to(ch)
                pdr = self.channel.calculate_pdr(d)

                # Adaptive transmission based on link category
                link_cat = self.channel.get_link_category(d)
                tx_energy = self.E_tx * self.packet_size

                if link_cat in ['marginal', 'poor']:
                    # Use higher power for poor links
                    pdr = self.channel.calculate_pdr(d, with_margin=True)
                    tx_energy *= 1.5

                rx_energy = self.E_rx * self.packet_size
                m.consume_energy(tx_energy)
                ch.consume_energy(rx_energy)
                self.total_energy += tx_energy + rx_energy

                self.packets_sent += 1
                m.update_link_quality(ch.node_id, pdr)
                if np.random.random() < pdr:
                    self.packets_delivered += 1

        # CH to BS with intelligent routing
        for ch in chs:
            if not ch.is_alive:
                continue

            route = self._find_best_route(ch, gateways)

            if route['type'] == 'direct':
                self.route_stats['direct'] += 1
                self._transmit_direct(ch)

            elif route['type'] == 'gateway':
                self.route_stats['gateway'] += 1
                self._transmit_via_gateway(ch, route['gateway'])

            elif route['type'] == 'cooperative':
                self.route_stats['cooperative'] += 1
                self._transmit_cooperative(ch, route['gateway'], route['helper'])

        return True

    def _transmit_direct(self, ch):
        """Direct transmission to BS."""
        d_bs = ch.distance_to(self.bs_pos)
        link_cat = self.channel.get_link_category(d_bs)

        tx_energy = self.E_tx * self.packet_size
        if link_cat in ['marginal', 'poor']:
            tx_energy *= 1.5
            pdr = self.channel.calculate_pdr(d_bs, with_margin=True)
        else:
            pdr = self.channel.calculate_pdr(d_bs)

        ch.consume_energy(tx_energy)
        self.total_energy += tx_energy
        self.packets_sent += 1

        ch.update_link_quality(-1, pdr)
        if np.random.random() < pdr:
            self.packets_delivered += 1

    def _transmit_via_gateway(self, ch, gw):
        """Two-hop transmission via gateway."""
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

    def _transmit_cooperative(self, ch, gw1, gw2):
        """Cooperative multi-path transmission."""
        delivered = False

        # Path 1: Direct
        d_bs = ch.distance_to(self.bs_pos)
        tx_e = self.E_tx * self.packet_size
        ch.consume_energy(tx_e)
        self.total_energy += tx_e
        self.packets_sent += 1

        if np.random.random() < self.channel.calculate_pdr(d_bs):
            delivered = True

        # Path 2: Via gateway 1
        if gw1 and not delivered:
            d_gw = ch.distance_to(gw1)
            tx_e = self.E_tx * self.packet_size
            rx_e = self.E_rx * self.packet_size
            ch.consume_energy(tx_e)
            gw1.consume_energy(rx_e)
            self.total_energy += tx_e + rx_e

            if np.random.random() < self.channel.calculate_pdr(d_gw):
                d_bs_gw = gw1.distance_to(self.bs_pos)
                tx_e = self.E_tx * self.packet_size
                gw1.consume_energy(tx_e)
                self.total_energy += tx_e

                if np.random.random() < self.channel.calculate_pdr(d_bs_gw):
                    delivered = True

        if delivered:
            self.packets_delivered += 1

    def get_results(self):
        pdr = self.packets_delivered / max(1, self.packets_sent)
        total_routes = sum(self.route_stats.values())

        return {
            'protocol': 'AERISv2',
            'packets_sent': self.packets_sent,
            'packets_delivered': self.packets_delivered,
            'pdr': pdr,
            'total_energy': self.total_energy,
            'alive_nodes': len([n for n in self.nodes if n.is_alive]),
            'routing_stats': {
                'direct': self.route_stats['direct'],
                'gateway': self.route_stats['gateway'],
                'cooperative': self.route_stats['cooperative'],
                'gateway_ratio': (self.route_stats['gateway'] + self.route_stats['cooperative']) / max(1, total_routes)
            }
        }


class FairLEACH:
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
        nodes.append(EnhancedNode(i, x, y, initial_energy=2.0))
    bs_pos = (area_size / 2, area_size + 20)
    return nodes, bs_pos


def run_experiment(protocol_class, nodes, bs_pos, channel, max_rounds=200):
    test_nodes = [EnhancedNode(n.node_id, n.x, n.y, n.initial_energy) for n in nodes]
    protocol = protocol_class(test_nodes, bs_pos, channel)
    for r in range(max_rounds):
        if not protocol.run_round():
            break
    return protocol.get_results()


def main():
    print("=" * 60)
    print("AERIS v2: Environment-Adaptive Intelligent Routing")
    print("=" * 60)

    num_runs = 30
    max_rounds = 200
    results = {'LEACH': [], 'AERISv2': []}

    channel = AdaptiveChannelModel(EnvironmentType.INDOOR_OFFICE)

    print(f"\nRunning {num_runs} experiments...")

    for run in range(num_runs):
        seed = 1000 + run
        nodes, bs_pos = create_network(num_nodes=54, area_size=100, seed=seed)

        results['LEACH'].append(run_experiment(FairLEACH, nodes, bs_pos, channel, max_rounds))
        results['AERISv2'].append(run_experiment(AERISv2, nodes, bs_pos, channel, max_rounds))

        if (run + 1) % 10 == 0:
            print(f"  Completed {run + 1}/{num_runs} runs")

    # Results
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
        }

        print(f"\n{name}:")
        print(f"  PDR: {summary[name]['pdr_mean']*100:.2f}% +/- {summary[name]['pdr_ci95']*100:.2f}%")
        print(f"  Energy: {summary[name]['energy_mean']:.3f}J +/- {summary[name]['energy_std']:.3f}J")

        if name == 'AERISv2':
            gw_ratios = [r['routing_stats']['gateway_ratio'] for r in runs]
            print(f"  Gateway/Cooperative usage: {np.mean(gw_ratios)*100:.1f}%")

    # Analysis
    print("\n" + "=" * 60)
    print("IMPROVEMENT ANALYSIS")
    print("=" * 60)

    leach = summary['LEACH']
    aeris = summary['AERISv2']

    pdr_improve = (aeris['pdr_mean'] - leach['pdr_mean']) * 100
    pdr_relative = (aeris['pdr_mean'] / leach['pdr_mean'] - 1) * 100
    energy_overhead = (aeris['energy_mean'] / leach['energy_mean'] - 1) * 100

    print(f"\nAERISv2 vs LEACH:")
    print(f"  Absolute PDR improvement: {pdr_improve:.2f}%")
    print(f"  Relative PDR improvement: {pdr_relative:.1f}%")
    print(f"  Energy overhead: {energy_overhead:.1f}%")

    # Efficiency
    leach_eff = leach['pdr_mean'] / leach['energy_mean'] * 100
    aeris_eff = aeris['pdr_mean'] / aeris['energy_mean'] * 100
    print(f"  PDR per Joule: LEACH={leach_eff:.2f}%, AERIS={aeris_eff:.2f}%")

    # Save
    output_dir = Path(__file__).parent.parent / 'results'
    output_file = output_dir / 'aeris_v2_results.json'

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'improvement': {
                'pdr_absolute': pdr_improve,
                'pdr_relative': pdr_relative,
                'energy_overhead': energy_overhead
            }
        }, f, indent=2, default=str)

    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
