#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版 AERIS 协议烟囱测试脚本

测试 AERIS 核心流程，避免复杂依赖；用于快速验证管线是否健康。
"""

import numpy as np
import matplotlib.pyplot as plt
import json
import time
import math
import random
from typing import Dict, List, Tuple

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


class SimpleAerisNode:
    """简化版传感器节点"""

    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True
        self.is_cluster_head = False
        self.cluster_id = -1
        self.next_hop = None

        # 基础属性
        self.base_station_distance = 0.0
        self.neighbors = []
        self.residual_energy_ratio = 1.0
        self.fuzzy_score = 0.0

        # 能量消耗模型参数
        self.E_elec = 50e-9
        self.E_fs = 10e-12
        self.E_mp = 0.0013e-12
        self.d_crossover = 87
        self.packet_size = 4000

    def distance_to(self, other_node) -> float:
        return math.sqrt((self.x - other_node.x) ** 2 + (self.y - other_node.y) ** 2)

    def calculate_transmission_energy(self, distance: float, packet_size: int, temperature_c: float = 25.0, humidity_ratio: float = 0.5) -> float:
        if distance < self.d_crossover:
            return self.E_elec * packet_size + self.E_fs * packet_size * (distance ** 2)
        else:
            return self.E_elec * packet_size + self.E_mp * packet_size * (distance ** 4)

    def calculate_reception_energy(self, packet_size: int, temperature_c: float = 25.0, humidity_ratio: float = 0.5) -> float:
        return self.E_elec * packet_size

    def consume_energy(self, energy_amount: float):
        self.current_energy -= energy_amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False
        self.residual_energy_ratio = self.current_energy / self.initial_energy

    def update_fuzzy_score(self, base_station_pos: Tuple[float, float]):
        energy_score = self.residual_energy_ratio
        bs_distance = math.sqrt((self.x - base_station_pos[0]) ** 2 + (self.y - base_station_pos[1]) ** 2)
        self.base_station_distance = bs_distance
        max_distance = 200 * math.sqrt(2)
        location_score = max(0, 1 - bs_distance / max_distance)
        connectivity_score = min(len(self.neighbors) / 8, 1) if self.neighbors else 0
        self.fuzzy_score = 0.5 * energy_score + 0.3 * location_score + 0.2 * connectivity_score


class SimpleAerisProtocol:
    """简化版 AERIS 协议"""

    def __init__(self, nodes: List[SimpleAerisNode], base_station: Tuple[float, float],
                 cluster_ratio: float = 0.05, chain_enabled: bool = True):
        self.nodes = nodes
        self.base_station = base_station
        self.cluster_ratio = cluster_ratio
        self.chain_enabled = chain_enabled
        self.current_round = 0

        self.cluster_heads = []
        self.chains = []

        self.total_energy_consumed = 0.0
        self.packets_sent = 0
        self.packets_received = 0
        self.dead_nodes = 0
        self.network_lifetime = 0
        self.energy_consumption_per_round = []
        self.alive_nodes_per_round = []

        self.initialize_network()

        print(f"🚀 简化版 AERIS 协议初始化完成")
        print(f"   节点数: {len(self.nodes)}")
        print(f"   基站位置: {self.base_station}")
        print(f"   链式结构: {'启用' if self.chain_enabled else '禁用'}")

    def initialize_network(self):
        for i, node_i in enumerate(self.nodes):
            node_i.neighbors = []
            for j, node_j in enumerate(self.nodes):
                if i != j:
                    distance = node_i.distance_to(node_j)
                    if distance <= 50:
                        node_i.neighbors.append(node_j)
        if self.chain_enabled:
            self.build_energy_efficient_chains()

    def build_energy_efficient_chains(self):
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if len(alive_nodes) < 2:
            return
        unvisited = alive_nodes.copy()
        chains = []
        while unvisited:
            if len(unvisited) == 1:
                chains.append([unvisited[0]])
                break
            start_node = max(unvisited, key=lambda n: n.current_energy)
            current_chain = [start_node]
            unvisited.remove(start_node)
            current_node = start_node
            while unvisited and len(current_chain) < 8:
                min_cost = float('inf')
                next_node = None
                for candidate in unvisited:
                    distance = current_node.distance_to(candidate)
                    energy_factor = 1.0 / (candidate.residual_energy_ratio + 0.1)
                    cost = distance * energy_factor
                    if cost < min_cost:
                        min_cost = cost
                        next_node = candidate
                if next_node:
                    current_chain.append(next_node)
                    unvisited.remove(next_node)
                    current_node = next_node
                else:
                    break
            chains.append(current_chain)
        self.chains = chains
        for chain_id, chain in enumerate(chains):
            for node in chain:
                node.cluster_id = chain_id

    def enhanced_fuzzy_clustering(self):
        for node in self.nodes:
            if node.is_alive:
                node.update_fuzzy_score(self.base_station)
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if not alive_nodes:
            return
        for node in self.nodes:
            node.is_cluster_head = False
        if self.chain_enabled:
            self.build_energy_efficient_chains()
            self.cluster_heads = []
            for chain in self.chains:
                if chain:
                    chain_head = max(chain, key=lambda n: n.fuzzy_score)
                    chain_head.is_cluster_head = True
                    self.cluster_heads.append(chain_head)
        else:
            expected_ch_count = max(1, int(len(alive_nodes) * self.cluster_ratio))
            sorted_nodes = sorted(alive_nodes, key=lambda n: n.fuzzy_score, reverse=True)
            self.cluster_heads = sorted_nodes[:expected_ch_count]
            for i, ch in enumerate(self.cluster_heads):
                ch.is_cluster_head = True
                ch.cluster_id = i
            for node in alive_nodes:
                if not node.is_cluster_head:
                    min_distance = float('inf')
                    best_cluster = 0
                    for i, ch in enumerate(self.cluster_heads):
                        distance = node.distance_to(ch)
                        if distance < min_distance:
                            min_distance = distance
                            best_cluster = i
                    node.cluster_id = best_cluster

    def simple_routing_optimization(self):
        if not self.cluster_heads:
            return
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue
            bs_distance = math.sqrt((ch.x - self.base_station[0]) ** 2 + (ch.y - self.base_station[1]) ** 2)
            if bs_distance < 60:
                ch.next_hop = None
                continue
            best_relay = None
            best_cost = float('inf')
            for candidate in self.cluster_heads:
                if candidate != ch and candidate.is_alive:
                    relay_distance = ch.distance_to(candidate)
                    relay_to_bs = math.sqrt((candidate.x - self.base_station[0]) ** 2 +
                                            (candidate.y - self.base_station[1]) ** 2)
                    energy_factor = 2.0 - candidate.residual_energy_ratio
                    total_cost = relay_distance + relay_to_bs * 0.5 + energy_factor * 10
                    if total_cost < best_cost and relay_to_bs < bs_distance:
                        best_cost = total_cost
                        best_relay = candidate
            ch.next_hop = best_relay

    def enhanced_data_transmission(self):
        if not self.cluster_heads:
            return
        round_energy_consumption = 0.0
        successful_transmissions = 0
        if self.chain_enabled:
            for chain in self.chains:
                if not chain:
                    continue
                for i in range(len(chain) - 1, 0, -1):
                    current_node = chain[i]
                    next_node = chain[i - 1]
                    if current_node.is_alive and next_node.is_alive:
                        distance = current_node.distance_to(next_node)
                        tx_energy = current_node.calculate_transmission_energy(distance, current_node.packet_size)
                        rx_energy = next_node.calculate_reception_energy(current_node.packet_size)
                        current_node.consume_energy(tx_energy)
                        next_node.consume_energy(rx_energy)
                        round_energy_consumption += tx_energy + rx_energy
                        successful_transmissions += 1
        else:
            for node in self.nodes:
                if node.is_alive and not node.is_cluster_head and node.cluster_id >= 0:
                    cluster_head = None
                    for ch in self.cluster_heads:
                        if ch.cluster_id == node.cluster_id:
                            cluster_head = ch
                            break
                    if cluster_head and cluster_head.is_alive:
                        distance = node.distance_to(cluster_head)
                        tx_energy = node.calculate_transmission_energy(distance, node.packet_size)
                        rx_energy = cluster_head.calculate_reception_energy(node.packet_size)
                        node.consume_energy(tx_energy)
                        cluster_head.consume_energy(rx_energy)
                        round_energy_consumption += tx_energy + rx_energy
                        successful_transmissions += 1
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue
            if ch.next_hop and ch.next_hop.is_alive:
                distance = ch.distance_to(ch.next_hop)
                tx_energy = ch.calculate_transmission_energy(distance, ch.packet_size)
                rx_energy = ch.next_hop.calculate_reception_energy(ch.packet_size)
                ch.consume_energy(tx_energy)
                ch.next_hop.consume_energy(rx_energy)
                round_energy_consumption += tx_energy + rx_energy
                successful_transmissions += 1
            else:
                bs_distance = math.sqrt((ch.x - self.base_station[0]) ** 2 + (ch.y - self.base_station[1]) ** 2)
                tx_energy = ch.calculate_transmission_energy(bs_distance, ch.packet_size)
                ch.consume_energy(tx_energy)
                round_energy_consumption += tx_energy
                successful_transmissions += 1
        self.total_energy_consumed += round_energy_consumption
        self.packets_sent += successful_transmissions
        self.packets_received += successful_transmissions
        current_dead = sum(1 for node in self.nodes if not node.is_alive)
        if current_dead > self.dead_nodes:
            self.dead_nodes = current_dead
            if self.network_lifetime == 0:
                self.network_lifetime = self.current_round

    def run_single_round(self):
        self.current_round += 1
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if len(alive_nodes) < 2:
            return False
        self.enhanced_fuzzy_clustering()
        self.simple_routing_optimization()
        self.enhanced_data_transmission()
        self.energy_consumption_per_round.append(self.total_energy_consumed)
        self.alive_nodes_per_round.append(len(alive_nodes))
        return len(alive_nodes) > 0

    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        print(f"🚀 开始简化版 AERIS 协议仿真...")
        print(f"   最大轮数: {max_rounds}")
        start_time = time.time()
        for round_num in range(max_rounds):
            if not self.run_single_round():
                print(f"⚠️  网络在第 {round_num} 轮断开连接")
                break
            if round_num % 100 == 0:
                alive_count = len([n for n in self.nodes if n.is_alive])
                avg_energy = np.mean([n.current_energy for n in self.nodes if n.is_alive]) if alive_count > 0 else 0
                print(f"   轮次 {round_num}: 存活节点 {alive_count}/{len(self.nodes)}, 平均能量 {avg_energy:.3f}J")
        simulation_time = time.time() - start_time
        alive_nodes = [node for node in self.nodes if node.is_alive]
        results = {
            'total_energy_consumed': self.total_energy_consumed,
            'network_lifetime': self.network_lifetime if self.network_lifetime > 0 else self.current_round,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'packet_delivery_ratio': self.packets_received / max(self.packets_sent, 1),
            'alive_nodes': len(alive_nodes),
            'dead_nodes': self.dead_nodes,
            'survival_rate': len(alive_nodes) / len(self.nodes),
            'average_residual_energy': np.mean([node.current_energy for node in alive_nodes]) if alive_nodes else 0,
            'energy_efficiency': self.packets_received / max(self.total_energy_consumed, 1e-6),
            'rounds_completed': self.current_round,
            'simulation_time': simulation_time
        }
        print(f"✅ 仿真完成!")
        print(f"   总轮数: {self.current_round}")
        print(f"   网络生存时间: {results['network_lifetime']} 轮")
        print(f"   总能耗: {self.total_energy_consumed:.4f} J")
        print(f"   仿真时间: {simulation_time:.2f} 秒")
        return results


def create_test_network(n_nodes: int = 50, area_size: int = 200) -> List[SimpleAerisNode]:
    nodes = []
    np.random.seed(42)
    for i in range(n_nodes):
        x = np.random.uniform(10, area_size - 10)
        y = np.random.uniform(10, area_size - 10)
        initial_energy = 2.0 + np.random.normal(0, 0.1)
        initial_energy = max(1.5, min(2.5, initial_energy))
        node = SimpleAerisNode(i, x, y, initial_energy)
        nodes.append(node)
    return nodes


def run_comparison_test():
    print("🧪 开始简化版 AERIS 协议对比测试")
    print("=" * 60)
    nodes = create_test_network(50, 200)
    base_station = (100, 100)
    test_configs = [
        {'name': 'AERIS_Chain', 'chain_enabled': True, 'cluster_ratio': 0.05},
        {'name': 'AERIS_Traditional', 'chain_enabled': False, 'cluster_ratio': 0.05},
    ]
    results = {}
    for config in test_configs:
        print(f"\n🔬 测试 {config['name']}...")
        test_nodes = []
        for original_node in nodes:
            new_node = SimpleAerisNode(
                original_node.node_id,
                original_node.x,
                original_node.y,
                original_node.initial_energy
            )
            test_nodes.append(new_node)
        protocol = SimpleAerisProtocol(
            nodes=test_nodes,
            base_station=base_station,
            cluster_ratio=config['cluster_ratio'],
            chain_enabled=config['chain_enabled']
        )
        result = protocol.run_simulation(max_rounds=500)
        results[config['name']] = result
        print(f"   ✅ 完成 - 能耗: {result['total_energy_consumed']:.4f}J, "
              f"生存时间: {result['network_lifetime']} 轮")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"simple_aeris_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 测试结果已保存至: {results_file}")
    protocols = list(results.keys())
    energy_consumption = [results[p]['total_energy_consumed'] for p in protocols]
    network_lifetime = [results[p]['network_lifetime'] for p in protocols]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    ax1.bar(protocols, energy_consumption, color=['#FF6B6B', '#4ECDC4'])
    ax1.set_title('总能耗对比 (J)')
    ax1.set_ylabel('能耗 (J)')
    ax1.tick_params(axis='x', rotation=45)
    ax2.bar(protocols, network_lifetime, color=['#FFD93D', '#6BCF7F'])
    ax2.set_title('网络生存时间对比 (轮)')
    ax2.set_ylabel('生存时间 (轮)')
    ax2.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    chart_file = f"simple_aeris_chart_{timestamp}.png"
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    print(f"📊 性能对比图表已保存至: {chart_file}")
    print("\n" + "=" * 60)
    print("✅ 简化版 AERIS 协议测试完成!")
    return results


if __name__ == "__main__":
    run_comparison_test()
