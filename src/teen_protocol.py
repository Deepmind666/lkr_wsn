#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEEN (Threshold sensitive Energy Efficient sensor Network) Protocol Implementation
Manjeshwar & Agrawal, "TEEN: A Routing Protocol for Enhanced Efficiency in WSNs", IPDPS 2001.

**MODIFIED 2025-11-04**: Now uses ImprovedEnergyModel for unified comparison with AERIS.

This implementation provides a pragmatic TEEN baseline compatible with the
benchmark wrapper expectations:
 - initialize_network(node_positions)
 - run_simulation(max_rounds) -> returns dict with required metrics
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple
try:
    from realistic_channel_model import RealisticChannelModel, EnvironmentType
except Exception:
    RealisticChannelModel = None
    EnvironmentType = None


def _resolve_channel_env(env):
    if EnvironmentType is None:
        return None
    if isinstance(env, EnvironmentType):
        return env
    if isinstance(env, str):
        key = env.strip().lower()
        for item in EnvironmentType:
            if item.value == key:
                return item
        for item in EnvironmentType:
            if item.name.lower() == key:
                return item
    return EnvironmentType.INDOOR_OFFICE

# Import unified energy model
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

# ------------------------- Config & Data Structures -------------------------

@dataclass
class TEENConfig:
    # Network
    num_nodes: int = 50
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 175.0

    # Energy
    initial_energy: float = 2.0

    # PHY/MAC
    transmission_range: float = 30.0
    packet_size: int = 1024  # bytes
    enable_channel: bool = False
    channel_env: str | None = None
    tx_power_dbm: float = 10.0
    temperature_c: float = 25.0
    humidity_ratio: float = 0.5
    link_retx: int = 0
    link_retx_power_step: float = 0.0

    # TEEN thresholds
    hard_threshold: float = 45.0
    soft_threshold: float = 0.5
    max_time_interval: int = 3

    # Clustering
    cluster_head_percentage: float = 0.08

class TEENNodeState(Enum):
    NORMAL = "normal"
    CLUSTER_HEAD = "cluster_head"
    DEAD = "dead"

@dataclass
class TEENNode:
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    state: TEENNodeState = TEENNodeState.NORMAL

    # Clustering
    cluster_id: int = -1
    is_cluster_head: bool = False
    cluster_head_id: int = -1

    # TEEN sensing state
    last_sensed_value: float = 0.0
    last_transmitted_value: float = 0.0
    last_transmission_time: int = -1  # -1 means never transmitted

    # Accounting
    packets_sent: int = 0
    packets_received: int = 0

    def is_alive(self) -> bool:
        return self.current_energy > 0 and self.state != TEENNodeState.DEAD

    def distance_to(self, other: "TEENNode") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

# ------------------------------ TEEN Protocol ------------------------------

class TEENProtocol:
    def __init__(self, config: TEENConfig, use_unified_energy_model: bool = True):
        """Initialize TEEN protocol.

        Args:
            config: TEEN configuration parameters
            use_unified_energy_model: If True, use ImprovedEnergyModel (CC2420 parameters).
                                     If False, use legacy simplified parameters.
        """
        self.config = config
        self.nodes: List[TEENNode] = []
        self.clusters: Dict[int, Dict] = {}
        self.current_round = 0
        self.base_station = (config.base_station_x, config.base_station_y)
        self.use_unified_energy_model = use_unified_energy_model

        # Statistics
        self.total_energy_consumed = 0.0
        self.packets_transmitted = 0
        self.packets_received = 0
        self.network_lifetime = 0
        self.round_stats: List[Dict] = []
        self.source_packets_total = 0  # 实际尝试发送的包数 (attempted)
        self.source_packets_expected = 0  # 期望包数 = 每轮存活节点数累计
        self.bs_delivered_total = 0

        # Packet size in bits
        self.bits_per_packet = self.config.packet_size * 8
        self.enable_channel = bool(getattr(config, "enable_channel", False))
        self.tx_power_dbm = float(getattr(config, "tx_power_dbm", 0.0) or 0.0)
        self.link_retx = max(0, int(getattr(config, "link_retx", 0) or 0))
        self.link_retx_power_step = float(getattr(config, "link_retx_power_step", 0.0) or 0.0)
        self.temperature_c = float(getattr(config, "temperature_c", 25.0) or 25.0)
        self.humidity_ratio = float(getattr(config, "humidity_ratio", 0.5) or 0.5)
        self.channel_model = None
        # 支持外部注入信道模型
        external_channel = getattr(config, 'external_channel_model', None)
        if external_channel is not None:
            self.channel_model = external_channel
        elif self.enable_channel and RealisticChannelModel is not None:
            env = _resolve_channel_env(getattr(config, "channel_env", None))
            self.channel_model = RealisticChannelModel(env)

        if use_unified_energy_model:
            # Use unified real hardware model (CC2420 TelosB)
            self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
            print(f"[TEEN] Using unified energy model (CC2420 TelosB, 208.8 nJ/bit)")
        else:
            # Legacy simplified parameters (for backward compatibility)
            self.E_elec = 50e-9
            self.E_fs = 10e-12
            self.E_mp = 0.0013e-12
            self.d0 = math.sqrt(self.E_fs / self.E_mp)
            self.energy_model = None
            print(f"[TEEN] Using legacy energy model (50 nJ/bit)")

    # ---------------------------- Energy Model -----------------------------

    def _tx_energy(self, distance_m: float, bits: int,
                   temperature_c: float = 25.0, humidity_ratio: float = 0.5) -> float:
        """Compute transmission energy.

        Uses unified energy model if enabled, otherwise legacy simplified model.
        """
        if self.use_unified_energy_model:
            # Use ImprovedEnergyModel (real CC2420 parameters)
            return self.energy_model.calculate_transmission_energy(
                data_size_bits=bits,
                distance=distance_m,
                tx_power_dbm=self.tx_power_dbm,
                temperature_c=temperature_c,
                humidity_ratio=humidity_ratio
            )
        else:
            # Legacy simplified model
            if distance_m < self.d0:
                return self.E_elec * bits + self.E_fs * bits * (distance_m ** 2)
            else:
                return self.E_elec * bits + self.E_mp * bits * (distance_m ** 4)

    def _rx_energy(self, bits: int,
                   temperature_c: float = 25.0, humidity_ratio: float = 0.5) -> float:
        """Compute reception energy.

        Uses unified energy model if enabled, otherwise legacy simplified model.
        """
        if self.use_unified_energy_model:
            # Use ImprovedEnergyModel (real CC2420 parameters)
            return self.energy_model.calculate_reception_energy(
                data_size_bits=bits,
                temperature_c=temperature_c,
                humidity_ratio=humidity_ratio
            )
        else:
            # Legacy simplified model
            return self.E_elec * bits

    # -------------------------- Network Lifecycle --------------------------

    def initialize_network(self, node_positions: List[Tuple[float, float]]):
        self.nodes = []
        for i, (x, y) in enumerate(node_positions):
            node = TEENNode(
                id=i,
                x=float(x),
                y=float(y),
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy
            )
            self.nodes.append(node)

    def _select_cluster_heads(self) -> List[TEENNode]:
        alive = [n for n in self.nodes if n.is_alive()]
        if not alive:
            return []

        # reset
        for n in alive:
            n.is_cluster_head = False
            n.cluster_id = -1
            n.cluster_head_id = -1
            n.state = TEENNodeState.NORMAL

        expected = max(1, int(len(alive) * self.config.cluster_head_percentage))
        # probability-based selection with energy bias
        candidates = []
        for n in alive:
            # simple energy bias: higher energy, higher chance
            p = self.config.cluster_head_percentage * (n.current_energy / max(1e-9, n.initial_energy))
            if random.random() < p:
                candidates.append(n)
        if not candidates:
            candidates = random.sample(alive, min(expected, len(alive)))
        # keep top expected by residual energy
        candidates = sorted(candidates, key=lambda n: n.current_energy, reverse=True)[:expected]
        for cid, ch in enumerate(candidates):
            ch.is_cluster_head = True
            ch.cluster_id = cid
            ch.cluster_head_id = ch.id
            ch.state = TEENNodeState.CLUSTER_HEAD
        return candidates

    def _form_clusters(self, chs: List[TEENNode]):
        self.clusters = {ch.cluster_id: {"head": ch, "members": []} for ch in chs}
        alive = [n for n in self.nodes if n.is_alive()]
        for n in alive:
            if n.is_cluster_head:
                continue
            # attach to nearest CH within range; otherwise remain standalone (direct-to-BS)
            best = None
            best_d = float("inf")
            for cid, cinfo in self.clusters.items():
                d = n.distance_to(cinfo["head"])
                if d < best_d:
                    best_d = d
                    best = cid
            if best is not None and best_d <= self.config.transmission_range:
                n.cluster_id = best
                n.cluster_head_id = self.clusters[best]["head"].id
                self.clusters[best]["members"].append(n)
            else:
                n.cluster_id = -1  # direct-to-BS candidate

    def _sense_value(self, node: TEENNode) -> float:
        # Simple synthetic sensing centered ~50 with location and noise
        base = 50.0
        loc = ((node.x + node.y) / (self.config.area_width + self.config.area_height)) * 20.0
        noise = random.gauss(0.0, 3.0)
        v = base + loc + noise
        v = max(0.0, min(100.0, v))
        node.last_sensed_value = v
        return v

    def _member_transmit_condition(self, node: TEENNode) -> bool:
        v = self._sense_value(node)
        if v < self.config.hard_threshold:
            return False
        if node.last_transmission_time < 0:
            node.last_transmitted_value = v
            return True
        if abs(v - node.last_transmitted_value) >= self.config.soft_threshold:
            node.last_transmitted_value = v
            return True
        # time-based force
        if (self.current_round - node.last_transmission_time) >= self.config.max_time_interval:
            node.last_transmitted_value = v
            return True
        return False

    def _link_success(self, distance: float, tx_power: float) -> bool:
        if self.channel_model is None:
            return True
        metrics = self.channel_model.calculate_link_metrics(
            tx_power,
            distance,
            temperature_c=self.temperature_c,
            humidity_ratio=self.humidity_ratio,
        )
        return random.random() < metrics.get("pdr", 0.0)

    def _round_communication(self):
        cluster_payloads = {cid: 0 for cid in self.clusters.keys()}

        # Member -> CH (threshold controlled)
        for cid, cinfo in self.clusters.items():
            ch = cinfo["head"]
            for m in list(cinfo["members"]):
                if not m.is_alive() or not ch.is_alive():
                    continue
                if self._member_transmit_condition(m):
                    d = m.distance_to(ch)
                    tx_e = self._tx_energy(d, self.bits_per_packet, self.temperature_c, self.humidity_ratio)
                    rx_e = self._rx_energy(self.bits_per_packet, self.temperature_c, self.humidity_ratio)
                    self.source_packets_total += 1
                    success = False
                    for attempt in range(self.link_retx + 1):
                        tx_power = self.tx_power_dbm + attempt * self.link_retx_power_step
                        if m.current_energy < tx_e or ch.current_energy < rx_e:
                            if m.current_energy < tx_e:
                                m.current_energy = 0.0
                                m.state = TEENNodeState.DEAD
                            if ch.current_energy < rx_e:
                                ch.current_energy = 0.0
                                ch.state = TEENNodeState.DEAD
                            break
                        m.current_energy -= tx_e
                        ch.current_energy -= rx_e
                        m.packets_sent += 1
                        ch.packets_received += 1
                        self.packets_transmitted += 1
                        self.total_energy_consumed += (tx_e + rx_e)
                        if self._link_success(d, tx_power):
                            self.packets_received += 1
                            m.last_transmission_time = self.current_round
                            cluster_payloads[cid] = cluster_payloads.get(cid, 0) + 1
                            success = True
                            break
                    if not success:
                        continue

        # Standalone nodes (no CH) direct to BS if threshold triggers
        for n in self.nodes:
            if not n.is_alive() or n.is_cluster_head or n.cluster_id != -1:
                continue
            if self._member_transmit_condition(n):
                d_bs = math.hypot(n.x - self.base_station[0], n.y - self.base_station[1])
                tx_e = self._tx_energy(d_bs, self.bits_per_packet, self.temperature_c, self.humidity_ratio)
                self.source_packets_total += 1
                success = False
                for attempt in range(self.link_retx + 1):
                    tx_power = self.tx_power_dbm + attempt * self.link_retx_power_step
                    if n.current_energy < tx_e:
                        n.current_energy = 0.0
                        n.state = TEENNodeState.DEAD
                        break
                    n.current_energy -= tx_e
                    n.packets_sent += 1
                    self.packets_transmitted += 1
                    self.total_energy_consumed += tx_e
                    if self._link_success(d_bs, tx_power):
                        self.packets_received += 1
                        n.last_transmission_time = self.current_round
                        self.bs_delivered_total += 1
                        self._all_hop_counts.append(1)
                        success = True
                        break
                if not success:
                    continue

        # CH -> BS (aggregate once per round)
        for cid, cinfo in self.clusters.items():
            ch = cinfo["head"]
            if not ch.is_alive():
                continue
            d_bs = math.hypot(ch.x - self.base_station[0], ch.y - self.base_station[1])
            tx_e = self._tx_energy(d_bs, self.bits_per_packet, self.temperature_c, self.humidity_ratio)
            if ch.current_energy >= tx_e:
                payload = cluster_payloads.get(cid, 0)
                if payload <= 0:
                    continue
                success = False
                for attempt in range(self.link_retx + 1):
                    tx_power = self.tx_power_dbm + attempt * self.link_retx_power_step
                    if ch.current_energy < tx_e:
                        ch.current_energy = 0.0
                        ch.state = TEENNodeState.DEAD
                        break
                    ch.current_energy -= tx_e
                    ch.packets_sent += 1
                    self.packets_transmitted += 1
                    self.total_energy_consumed += tx_e
                    if self._link_success(d_bs, tx_power):
                        self.packets_received += 1
                        self.bs_delivered_total += payload
                        for _ in range(payload):
                            self._all_hop_counts.append(2)
                        success = True
                        break
                if not success:
                    continue
            else:
                ch.current_energy = 0.0
                ch.state = TEENNodeState.DEAD

    def _collect_round_stats(self):
        alive = sum(1 for n in self.nodes if n.is_alive())
        ch_count = sum(1 for n in self.nodes if n.is_alive() and n.is_cluster_head)
        self.round_stats.append({
            "round": self.current_round,
            "alive_nodes": alive,
            "cluster_heads": ch_count
        })
        if alive == 0 and self.network_lifetime == 0:
            self.network_lifetime = self.current_round

    def run_simulation(self, max_rounds: int) -> Dict:
        self.current_round = 0
        self.round_stats = []
        self.total_energy_consumed = 0.0
        self.packets_transmitted = 0
        self.packets_received = 0
        self.network_lifetime = 0
        self.source_packets_total = 0
        self.source_packets_expected = 0
        self.bs_delivered_total = 0
        self._all_hop_counts = []

        for r in range(max_rounds):
            self.current_round = r
            alive_nodes = [n for n in self.nodes if n.is_alive()]
            if not alive_nodes:
                break
            # 累计期望包数 = 每轮存活节点数
            self.source_packets_expected += len(alive_nodes)

            chs = self._select_cluster_heads()
            self._form_clusters(chs)
            self._round_communication()
            self._collect_round_stats()

        final_alive = sum(1 for n in self.nodes if n.is_alive())
        lifetime = self.network_lifetime if self.network_lifetime > 0 else len(self.round_stats)
        pdr = (self.packets_received / self.packets_transmitted) if self.packets_transmitted > 0 else 0.0
        efficiency = (self.packets_received / self.total_energy_consumed) if self.total_energy_consumed > 0 else 0.0
        avg_ch = (sum(s["cluster_heads"] for s in self.round_stats) / len(self.round_stats)) if self.round_stats else 0.0

        return {
            "protocol": "TEEN",
            "network_lifetime": lifetime,
            "total_energy_consumed": self.total_energy_consumed,
            "packets_transmitted": self.packets_transmitted,
            "packets_received": self.packets_received,
            "packet_delivery_ratio": pdr,
            "packet_delivery_ratio_end2end": (self.bs_delivered_total / self.source_packets_total) if self.source_packets_total > 0 else 0.0,
            "energy_efficiency": efficiency,
            "final_alive_nodes": final_alive,
            "average_cluster_heads_per_round": avg_ch,
            "additional_metrics": {
                "hard_threshold": self.config.hard_threshold,
                "soft_threshold": self.config.soft_threshold,
                "source_packets_total": self.source_packets_total,
                "bs_delivered_total": self.bs_delivered_total
            },
            "avg_hops_to_bs": (sum(self._all_hop_counts) / len(self._all_hop_counts)) if self._all_hop_counts else 0,
        }
