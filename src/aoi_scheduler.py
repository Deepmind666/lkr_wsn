#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Age of Information (AoI) Aware Scheduler for AERIS Protocol
============================================================
Packet scheduling based on data freshness, inspired by DQN-WSN.

Key Concept:
In DQN-WSN, the reward function uses Age of Information (AoI):
    reward = 1 / AoI

Fresher data (lower AoI) gets higher priority for transmission.
This ensures time-sensitive information reaches the sink quickly.

AERIS Integration:
- Prioritize packets based on AoI
- Combine with energy and criticality factors
- Support both TDMA and contention-based scheduling

Author: AERIS Research Team
Date: 2026-01-04
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
from enum import Enum
import time
import heapq
import math


class PacketCriticality(Enum):
    """Packet criticality levels"""
    LOW = 0.2
    NORMAL = 0.5
    HIGH = 0.8
    CRITICAL = 1.0


@dataclass
class Packet:
    """Represents a data packet with AoI tracking"""
    packet_id: int
    source_node_id: int
    generation_time: float
    data: bytes = b''
    criticality: PacketCriticality = PacketCriticality.NORMAL
    destination_id: int = -1  # -1 means base station
    hop_count: int = 0
    deadline: Optional[float] = None

    # Node state at generation (for energy-aware scheduling)
    source_energy_ratio: float = 1.0

    # Tracking
    last_transmission_time: Optional[float] = None
    retransmission_count: int = 0

    def get_age(self, current_time: float) -> float:
        """Calculate current Age of Information"""
        return current_time - self.generation_time

    def get_freshness_score(self, current_time: float, max_age: float = 100.0) -> float:
        """
        Calculate freshness score (0-1, higher is fresher).

        Uses inverse age like DQN-WSN: freshness = 1 / (1 + age)
        """
        age = self.get_age(current_time)
        return 1.0 / (1.0 + age / max_age)

    def is_expired(self, current_time: float) -> bool:
        """Check if packet has exceeded its deadline"""
        if self.deadline is None:
            return False
        return current_time > self.deadline

    def __lt__(self, other):
        """For heap comparison - lower priority value = higher actual priority"""
        return self.packet_id < other.packet_id


@dataclass
class SchedulerConfig:
    """Configuration for AoI-aware scheduler"""
    # Weight factors for priority calculation
    w_freshness: float = 0.40     # Weight for freshness (AoI-based)
    w_energy: float = 0.25        # Weight for source node energy
    w_criticality: float = 0.25  # Weight for packet criticality
    w_deadline: float = 0.10     # Weight for deadline proximity

    # AoI parameters
    max_acceptable_age: float = 50.0  # Maximum age before packet considered stale
    freshness_decay_rate: float = 0.1  # How fast freshness decreases

    # Queue parameters
    max_queue_size: int = 100
    drop_oldest_when_full: bool = True

    # Scheduling mode
    enable_preemption: bool = False  # Allow high-priority to preempt


class AoIAwareScheduler:
    """
    Age of Information Aware Packet Scheduler

    Prioritizes packets based on:
    1. Freshness (1/AoI from DQN-WSN)
    2. Source node energy (avoid draining low-energy nodes)
    3. Packet criticality (application-defined importance)
    4. Deadline proximity (time-sensitive packets)
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()

        # Priority queue: (priority_value, packet)
        # Lower priority_value = higher actual priority (min-heap)
        self._queue: List[Tuple[float, int, Packet]] = []
        self._packet_counter = 0

        # Statistics
        self.stats = {
            'total_enqueued': 0,
            'total_dequeued': 0,
            'total_dropped': 0,
            'total_expired': 0,
            'avg_wait_time': 0.0,
            'avg_age_at_dequeue': 0.0
        }

        # History for analysis
        self._wait_times: List[float] = []
        self._ages_at_dequeue: List[float] = []

    def calculate_priority(self, packet: Packet, current_time: float) -> float:
        """
        Calculate packet priority (lower value = higher priority).

        Inspired by DQN-WSN's reward function but with multiple factors.
        """
        # Freshness score (from AoI)
        freshness = packet.get_freshness_score(current_time, self.config.max_acceptable_age)

        # Energy score (prefer packets from nodes with more energy)
        energy_score = packet.source_energy_ratio

        # Criticality score
        criticality_score = packet.criticality.value

        # Deadline proximity score
        if packet.deadline is not None:
            time_to_deadline = max(0, packet.deadline - current_time)
            deadline_score = 1.0 - min(1.0, time_to_deadline / self.config.max_acceptable_age)
        else:
            deadline_score = 0.5  # Neutral if no deadline

        # Weighted combination (higher = more priority, so we negate for min-heap)
        priority = -(
            self.config.w_freshness * freshness +
            self.config.w_energy * energy_score +
            self.config.w_criticality * criticality_score +
            self.config.w_deadline * deadline_score
        )

        return priority

    def enqueue(self, packet: Packet, current_time: Optional[float] = None) -> bool:
        """
        Add a packet to the scheduling queue.

        Returns True if successfully enqueued, False if dropped.
        """
        if current_time is None:
            current_time = time.time()

        # Check queue capacity
        if len(self._queue) >= self.config.max_queue_size:
            if self.config.drop_oldest_when_full:
                # Drop oldest (lowest priority) packet
                if self._queue:
                    dropped = heapq.heappop(self._queue)
                    self.stats['total_dropped'] += 1
            else:
                self.stats['total_dropped'] += 1
                return False

        # Calculate priority
        priority = self.calculate_priority(packet, current_time)

        # Add to queue
        self._packet_counter += 1
        heapq.heappush(self._queue, (priority, self._packet_counter, packet))
        self.stats['total_enqueued'] += 1

        return True

    def dequeue(self, current_time: Optional[float] = None) -> Optional[Packet]:
        """
        Get the highest priority packet from the queue.

        Also removes expired packets.
        """
        if current_time is None:
            current_time = time.time()

        # Remove expired packets
        self._remove_expired(current_time)

        if not self._queue:
            return None

        # Get highest priority packet
        priority, counter, packet = heapq.heappop(self._queue)

        # Update statistics
        self.stats['total_dequeued'] += 1
        wait_time = current_time - packet.generation_time
        self._wait_times.append(wait_time)
        age_at_dequeue = packet.get_age(current_time)
        self._ages_at_dequeue.append(age_at_dequeue)

        # Update running averages
        n = len(self._wait_times)
        self.stats['avg_wait_time'] = sum(self._wait_times[-100:]) / min(n, 100)
        self.stats['avg_age_at_dequeue'] = sum(self._ages_at_dequeue[-100:]) / min(n, 100)

        packet.last_transmission_time = current_time
        return packet

    def peek(self) -> Optional[Packet]:
        """Look at the highest priority packet without removing it"""
        if not self._queue:
            return None
        return self._queue[0][2]

    def _remove_expired(self, current_time: float):
        """Remove all expired packets from the queue"""
        new_queue = []
        for priority, counter, packet in self._queue:
            if not packet.is_expired(current_time):
                new_queue.append((priority, counter, packet))
            else:
                self.stats['total_expired'] += 1

        if len(new_queue) != len(self._queue):
            self._queue = new_queue
            heapq.heapify(self._queue)

    def requeue_failed(self, packet: Packet, current_time: Optional[float] = None) -> bool:
        """
        Requeue a packet that failed to transmit.

        Increases retransmission count and recalculates priority.
        """
        if current_time is None:
            current_time = time.time()

        packet.retransmission_count += 1

        # Check if packet is still valid
        if packet.is_expired(current_time):
            self.stats['total_expired'] += 1
            return False

        # Recalculate priority (age has increased, so priority changes)
        priority = self.calculate_priority(packet, current_time)

        # Add penalty for retransmission (slight priority reduction)
        priority += 0.1 * packet.retransmission_count

        self._packet_counter += 1
        heapq.heappush(self._queue, (priority, self._packet_counter, packet))

        return True

    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        return {
            'queue_length': len(self._queue),
            'max_queue_size': self.config.max_queue_size,
            'utilization': len(self._queue) / self.config.max_queue_size,
            'statistics': self.stats.copy()
        }

    def get_scheduled_order(self, current_time: Optional[float] = None,
                           max_packets: int = 10) -> List[Packet]:
        """
        Get packets in scheduled order without removing them.

        Useful for TDMA slot allocation.
        """
        if current_time is None:
            current_time = time.time()

        # Create a copy and sort
        packets = [(p, self.calculate_priority(pkt, current_time))
                   for p, _, pkt in self._queue]
        packets.sort(key=lambda x: x[1])

        return [pkt for pkt, _ in packets[:max_packets]]

    def clear(self):
        """Clear the queue"""
        self._queue = []
        self._packet_counter = 0


class ClusterScheduler:
    """
    Cluster-level scheduler that manages packet scheduling for a cluster.

    Integrates AoI-aware scheduling with cluster head aggregation.
    """

    def __init__(self, cluster_id: int, config: Optional[SchedulerConfig] = None):
        self.cluster_id = cluster_id
        self.scheduler = AoIAwareScheduler(config)

        # Per-node scheduling info
        self.node_last_transmission: Dict[int, float] = {}
        self.node_transmission_count: Dict[int, int] = {}

    def schedule_node_packet(self, packet: Packet,
                             current_time: Optional[float] = None) -> bool:
        """Schedule a packet from a member node"""
        if current_time is None:
            current_time = time.time()

        # Update node tracking
        self.node_transmission_count[packet.source_node_id] = \
            self.node_transmission_count.get(packet.source_node_id, 0) + 1

        return self.scheduler.enqueue(packet, current_time)

    def get_next_transmission(self, current_time: Optional[float] = None) -> Optional[Packet]:
        """Get the next packet to transmit (for CH to aggregate/forward)"""
        packet = self.scheduler.dequeue(current_time)
        if packet:
            self.node_last_transmission[packet.source_node_id] = current_time or time.time()
        return packet

    def get_aggregated_batch(self, max_packets: int = 10,
                            current_time: Optional[float] = None) -> List[Packet]:
        """
        Get a batch of packets for aggregation.

        Returns packets in priority order for CH to aggregate before forwarding.
        """
        if current_time is None:
            current_time = time.time()

        batch = []
        for _ in range(max_packets):
            packet = self.scheduler.dequeue(current_time)
            if packet is None:
                break
            batch.append(packet)

        return batch


# Factory functions

def create_aoi_scheduler(
    freshness_weight: float = 0.40,
    energy_weight: float = 0.25,
    criticality_weight: float = 0.25
) -> AoIAwareScheduler:
    """Create an AoI-aware scheduler with custom weights"""
    config = SchedulerConfig(
        w_freshness=freshness_weight,
        w_energy=energy_weight,
        w_criticality=criticality_weight,
        w_deadline=1.0 - freshness_weight - energy_weight - criticality_weight
    )
    return AoIAwareScheduler(config)


def create_freshness_first_scheduler() -> AoIAwareScheduler:
    """Create a scheduler that prioritizes freshness (like DQN-WSN)"""
    config = SchedulerConfig(
        w_freshness=0.60,
        w_energy=0.15,
        w_criticality=0.15,
        w_deadline=0.10
    )
    return AoIAwareScheduler(config)


def create_energy_aware_scheduler() -> AoIAwareScheduler:
    """Create a scheduler that prioritizes energy conservation"""
    config = SchedulerConfig(
        w_freshness=0.25,
        w_energy=0.45,
        w_criticality=0.20,
        w_deadline=0.10
    )
    return AoIAwareScheduler(config)


if __name__ == "__main__":
    # Demo usage
    print("AERIS AoI-Aware Scheduler Demo")
    print("=" * 50)

    # Create scheduler
    scheduler = create_aoi_scheduler()

    # Create test packets with different characteristics
    base_time = 0.0
    packets = [
        Packet(1, 101, base_time - 10.0, criticality=PacketCriticality.LOW, source_energy_ratio=0.9),
        Packet(2, 102, base_time - 5.0, criticality=PacketCriticality.HIGH, source_energy_ratio=0.3),
        Packet(3, 103, base_time - 1.0, criticality=PacketCriticality.NORMAL, source_energy_ratio=0.7),
        Packet(4, 104, base_time - 20.0, criticality=PacketCriticality.CRITICAL, source_energy_ratio=0.5),
        Packet(5, 105, base_time - 2.0, criticality=PacketCriticality.NORMAL, source_energy_ratio=0.95),
    ]

    print("\nEnqueuing packets:")
    for pkt in packets:
        scheduler.enqueue(pkt, base_time)
        print(f"  Packet {pkt.packet_id}: age={pkt.get_age(base_time):.1f}s, "
              f"criticality={pkt.criticality.name}, energy={pkt.source_energy_ratio:.2f}")

    print("\nDequeuing in priority order:")
    while True:
        pkt = scheduler.dequeue(base_time)
        if pkt is None:
            break
        freshness = pkt.get_freshness_score(base_time)
        print(f"  Packet {pkt.packet_id}: freshness={freshness:.3f}, "
              f"criticality={pkt.criticality.name}")

    print("\nQueue Statistics:")
    status = scheduler.get_queue_status()
    for key, value in status['statistics'].items():
        print(f"  {key}: {value}")
