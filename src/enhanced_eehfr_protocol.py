#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced EEHFR: 基于基准协议对比实验结果优化的能量高效混合模糊路由协议

优化策略:
1. 融合PEGASIS链式结构优势，减少簇内通信开销
2. 改进模糊逻辑评分系统，提高簇头选择质量
3. 优化元启发式路由算法，降低计算复杂度
4. 增强预测模型，提高路由决策准确性
5. 精细化能量消耗模型，提升能效

项目路径: EEHFR：融合模糊逻辑与混合元启发式优化的WSN智能节能路由协议/EEHFR_Optimized_v1/
数据源: Intel Berkeley Research Lab数据集 (https://db.csail.mit.edu/labdata/labdata.html)
"""

import numpy as np
import matplotlib.pyplot as plt
import random
import math
import time
from typing import List, Tuple, Dict, Optional
from collections import defaultdict
from sklearn.cluster import KMeans
import networkx as nx

class EnhancedNode:
    """增强型传感器节点类"""
    
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
        self.data_queue = []
        
        # 增强属性
        self.residual_energy_ratio = 1.0
        self.trust_value = 1.0
        self.link_quality = {}
        self.communication_cost = 0.0
        self.node_degree = 0
        self.centrality_score = 0.0
        
        # 模糊逻辑评分
        self.fuzzy_score = 0.0
        self.energy_score = 0.0
        self.location_score = 0.0
        self.connectivity_score = 0.0
        
        # 预测相关
        self.predicted_lifetime = float('inf')
        self.congestion_probability = 0.0
        self.failure_risk = 0.0
        
        # 链式结构相关（借鉴PEGASIS）
        self.chain_position = -1
        self.chain_neighbors = []
        self.is_chain_leader = False
        
        # 能量消耗模型参数
        self.E_elec = 50e-9  # 电子能耗 (J/bit)
        self.E_fs = 10e-12   # 自由空间模型 (J/bit/m²)
        self.E_mp = 0.0013e-12  # 多径衰落模型 (J/bit/m⁴)
        self.E_DA = 5e-9     # 数据聚合能耗 (J/bit/signal)
        self.d_crossover = 87  # 距离阈值 (m)
        self.packet_size = 4000  # 数据包大小 (bits)
    
    def distance_to(self, other_node) -> float:
        """计算到另一个节点的欧几里得距离"""
        return math.sqrt((self.x - other_node.x)**2 + (self.y - other_node.y)**2)
    
    def calculate_transmission_energy(self, distance: float, packet_size: int) -> float:
        """计算传输能耗（优化版本）"""
        if distance < self.d_crossover:
            return self.E_elec * packet_size + self.E_fs * packet_size * (distance ** 2)
        else:
            return self.E_elec * packet_size + self.E_mp * packet_size * (distance ** 4)
    
    def calculate_reception_energy(self, packet_size: int) -> float:
        """计算接收能耗"""
        return self.E_elec * packet_size
    
    def consume_energy(self, energy_amount: float):
        """消耗能量并更新状态"""
        self.current_energy -= energy_amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False
        self.residual_energy_ratio = self.current_energy / self.initial_energy
    
    def update_fuzzy_scores(self, base_station_pos: Tuple[float, float]):
        """更新模糊逻辑评分（增强版本）"""
        # 能量评分 (0-1)
        self.energy_score = self.residual_energy_ratio
        
        # 位置评分 (考虑到基站的距离和网络中心性)
        bs_distance = math.sqrt((self.x - base_station_pos[0])**2 + (self.y - base_station_pos[1])**2)
        self.base_station_distance = bs_distance
        max_distance = 200 * math.sqrt(2)  # 网络对角线长度
        self.location_score = max(0, 1 - bs_distance / max_distance)
        
        # 连接性评分 (基于邻居数量和链路质量)
        self.node_degree = len(self.neighbors)
        if self.node_degree > 0:
            avg_link_quality = sum(self.link_quality.values()) / len(self.link_quality)
            degree_factor = min(self.node_degree / 8, 1)  # 归一化到0-1
            self.connectivity_score = (degree_factor + avg_link_quality) / 2
        else:
            self.connectivity_score = 0
        
        # 综合模糊评分（权重优化）
        w_energy = 0.5      # 能量权重最高
        w_location = 0.3    # 位置权重中等
        w_connectivity = 0.2 # 连接性权重较低
        
        self.fuzzy_score = (w_energy * self.energy_score + 
                           w_location * self.location_score + 
                           w_connectivity * self.connectivity_score)
    
    def update_communication_cost(self):
        """更新通信代价（考虑能耗和拥塞）"""
        if not self.neighbors:
            self.communication_cost = float('inf')
            return
        
        total_cost = 0.0
        for neighbor in self.neighbors:
            if neighbor.is_alive:
                distance = self.distance_to(neighbor)
                energy_cost = self.calculate_transmission_energy(distance, self.packet_size)
                congestion_cost = neighbor.congestion_probability * 0.1
                total_cost += energy_cost + congestion_cost
        
        self.communication_cost = total_cost / len([n for n in self.neighbors if n.is_alive])

class EnhancedEEHFR:
    """增强型EEHFR协议实现"""
    
    def __init__(self, nodes: List[EnhancedNode], base_station: Tuple[float, float], 
                 cluster_ratio: float = 0.05, chain_enabled: bool = True):
        """
        初始化增强型EEHFR协议
        
        参数:
            nodes: 传感器节点列表
            base_station: 基站坐标 (x, y)
            cluster_ratio: 期望簇头比例
            chain_enabled: 是否启用链式结构优化
        """
        self.nodes = nodes
        self.base_station = base_station
        self.cluster_ratio = cluster_ratio
        self.chain_enabled = chain_enabled
        self.current_round = 0
        
        # 网络状态
        self.cluster_heads = []
        self.chains = []  # 链式结构
        self.network_graph = None
        
        # 性能统计
        self.total_energy_consumed = 0.0
        self.packets_sent = 0
        self.packets_received = 0
        self.dead_nodes = 0
        self.network_lifetime = 0
        self.energy_consumption_per_round = []
        self.alive_nodes_per_round = []
        
        # 优化参数
        self.reclustering_threshold = 0.1  # 重新分簇阈值
        self.prediction_window = 10        # 预测窗口
        self.energy_threshold = 0.2        # 能量阈值
        
        # 初始化网络
        self.initialize_network()
        
        print(f"🚀 Enhanced EEHFR协议初始化完成")
        print(f"   节点数: {len(self.nodes)}")
        print(f"   基站位置: {self.base_station}")
        print(f"   簇头比例: {self.cluster_ratio}")
        print(f"   链式结构: {'启用' if self.chain_enabled else '禁用'}")
    
    def initialize_network(self):
        """初始化网络拓扑和邻居关系"""
        # 建立邻居关系
        for i, node_i in enumerate(self.nodes):
            node_i.neighbors = []
            node_i.link_quality = {}
            
            for j, node_j in enumerate(self.nodes):
                if i != j:
                    distance = node_i.distance_to(node_j)
                    if distance <= 50:  # 通信半径50m
                        node_i.neighbors.append(node_j)
                        # 链路质量基于距离和能量
                        link_quality = max(0, 1 - distance / 50) * 0.7 + node_j.residual_energy_ratio * 0.3
                        node_i.link_quality[node_j.node_id] = link_quality
        
        # 创建网络图用于分析
        self.build_network_graph()
        
        # 如果启用链式结构，构建初始链
        if self.chain_enabled:
            self.build_energy_efficient_chains()
    
    def build_network_graph(self):
        """构建网络图用于拓扑分析"""
        self.network_graph = nx.Graph()
        
        # 添加节点
        for node in self.nodes:
            if node.is_alive:
                self.network_graph.add_node(node.node_id, pos=(node.x, node.y))
        
        # 添加边
        for node in self.nodes:
            if node.is_alive:
                for neighbor in node.neighbors:
                    if neighbor.is_alive:
                        weight = 1.0 / (node.distance_to(neighbor) + 1e-6)
                        self.network_graph.add_edge(node.node_id, neighbor.node_id, weight=weight)
        
        # 计算中心性
        if len(self.network_graph.nodes()) > 0:
            centrality = nx.betweenness_centrality(self.network_graph)
            for node in self.nodes:
                if node.is_alive and node.node_id in centrality:
                    node.centrality_score = centrality[node.node_id]
    
    def build_energy_efficient_chains(self):
        """构建能量高效的链式结构（借鉴PEGASIS优势）"""
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if len(alive_nodes) < 2:
            return
        
        # 使用贪心算法构建最小生成树式的链
        unvisited = alive_nodes.copy()
        chains = []
        
        while unvisited:
            if len(unvisited) == 1:
                # 最后一个节点单独成链
                chains.append([unvisited[0]])
                break
            
            # 选择能量最高的节点作为链的起点
            start_node = max(unvisited, key=lambda n: n.current_energy)
            current_chain = [start_node]
            unvisited.remove(start_node)
            
            current_node = start_node
            
            # 贪心构建链：每次选择距离最近且能量充足的节点
            while unvisited:
                min_cost = float('inf')
                next_node = None
                
                for candidate in unvisited:
                    # 综合考虑距离和能量的代价函数
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
                    
                    # 限制链长度，避免过长链路
                    if len(current_chain) >= 8:
                        break
                else:
                    break
            
            chains.append(current_chain)
        
        # 更新节点的链信息
        self.chains = chains
        for chain_id, chain in enumerate(chains):
            for pos, node in enumerate(chain):
                node.chain_position = pos
                node.cluster_id = chain_id
                
                # 设置链内邻居
                node.chain_neighbors = []
                if pos > 0:
                    node.chain_neighbors.append(chain[pos-1])
                if pos < len(chain) - 1:
                    node.chain_neighbors.append(chain[pos+1])
                
                # 选择链头（能量最高的节点）
                node.is_chain_leader = (node == max(chain, key=lambda n: n.current_energy))
    
    def enhanced_fuzzy_clustering(self):
        """增强型模糊逻辑分簇算法"""
        # 更新所有节点的模糊评分
        for node in self.nodes:
            if node.is_alive:
                node.update_fuzzy_scores(self.base_station)
                node.update_communication_cost()
        
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if not alive_nodes:
            return
        
        # 如果启用链式结构，使用链式分簇
        if self.chain_enabled:
            self.build_energy_efficient_chains()
            self.cluster_heads = []
            for chain in self.chains:
                if chain:
                    # 选择链中模糊评分最高的节点作为簇头
                    chain_head = max(chain, key=lambda n: n.fuzzy_score)
                    chain_head.is_cluster_head = True
                    self.cluster_heads.append(chain_head)
        else:
            # 传统分簇方法
            self.traditional_fuzzy_clustering(alive_nodes)
    
    def traditional_fuzzy_clustering(self, alive_nodes: List[EnhancedNode]):
        """传统模糊分簇方法"""
        # 重置簇头状态
        for node in self.nodes:
            node.is_cluster_head = False
        
        # 计算期望簇头数量
        expected_ch_count = max(1, int(len(alive_nodes) * self.cluster_ratio))
        
        # 使用K-means进行初始分簇
        if len(alive_nodes) > expected_ch_count:
            # 特征向量：位置 + 模糊评分
            features = np.array([[node.x, node.y, node.fuzzy_score * 50] for node in alive_nodes])
            kmeans = KMeans(n_clusters=expected_ch_count, random_state=42, n_init=10).fit(features)
            
            # 分配簇ID
            for i, node in enumerate(alive_nodes):
                node.cluster_id = kmeans.labels_[i]
            
            # 在每个簇中选择模糊评分最高的节点作为簇头
            self.cluster_heads = []
            for cluster_id in range(expected_ch_count):
                cluster_nodes = [node for node in alive_nodes if node.cluster_id == cluster_id]
                if cluster_nodes:
                    ch = max(cluster_nodes, key=lambda n: n.fuzzy_score)
                    ch.is_cluster_head = True
                    self.cluster_heads.append(ch)
        else:
            # 节点数少于期望簇头数，每个节点作为簇头
            self.cluster_heads = alive_nodes
            for i, node in enumerate(alive_nodes):
                node.cluster_id = i
                node.is_cluster_head = True

    def hybrid_metaheuristic_routing(self):
        """混合元启发式路由优化（PSO+ACO融合）"""
        if not self.cluster_heads:
            return

        # 为每个簇头计算最优路由路径
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue

            # 使用改进的蚁群算法寻找到基站的最优路径
            optimal_path = self.enhanced_aco_routing(ch)

            # 使用粒子群优化调整路由参数
            optimized_params = self.pso_parameter_optimization(ch, optimal_path)

            # 更新路由信息
            if optimal_path and len(optimal_path) > 1:
                ch.next_hop = optimal_path[1]  # 下一跳节点
            else:
                ch.next_hop = None  # 直接发送到基站

    def enhanced_aco_routing(self, source_node: EnhancedNode) -> List[EnhancedNode]:
        """增强型蚁群算法路由"""
        if not source_node.is_alive:
            return []

        # 构建候选节点集合（活跃的簇头节点）
        candidates = [ch for ch in self.cluster_heads if ch.is_alive and ch != source_node]

        if not candidates:
            return [source_node]  # 直接到基站

        # 初始化信息素矩阵
        pheromone = defaultdict(lambda: 0.1)

        # ACO参数
        alpha = 1.0    # 信息素重要性
        beta = 2.0     # 启发式信息重要性
        rho = 0.1      # 信息素挥发率
        n_ants = 5     # 蚂蚁数量

        best_path = []
        best_cost = float('inf')

        # 多轮蚂蚁搜索
        for iteration in range(3):  # 减少迭代次数以降低计算复杂度
            for ant in range(n_ants):
                current_node = source_node
                path = [current_node]
                total_cost = 0.0
                visited = {current_node.node_id}

                # 构建路径
                while len(path) < 5:  # 限制路径长度
                    # 计算到基站的距离
                    bs_distance = math.sqrt((current_node.x - self.base_station[0])**2 +
                                          (current_node.y - self.base_station[1])**2)

                    # 如果距离基站很近，直接发送
                    if bs_distance < 50:
                        break

                    # 选择下一个节点
                    next_candidates = [node for node in candidates
                                     if node.node_id not in visited and node.is_alive]

                    if not next_candidates:
                        break

                    # 计算选择概率
                    probabilities = []
                    for candidate in next_candidates:
                        # 启发式信息：综合考虑距离、能量和信任值
                        distance = current_node.distance_to(candidate)
                        energy_factor = candidate.residual_energy_ratio
                        trust_factor = candidate.trust_value

                        heuristic = (energy_factor * trust_factor) / (distance + 1e-6)

                        # 信息素
                        pheromone_value = pheromone[(current_node.node_id, candidate.node_id)]

                        # 综合概率
                        prob = (pheromone_value ** alpha) * (heuristic ** beta)
                        probabilities.append(prob)

                    # 轮盘赌选择
                    prob_sum = sum(probabilities)
                    if prob_sum > 0 and not np.isnan(prob_sum) and not np.isinf(prob_sum):
                        probabilities = np.array(probabilities) / prob_sum
                        # 检查概率数组是否有效
                        if any(np.isnan(p) or np.isinf(p) for p in probabilities):
                            # 如果有无效值，使用均匀分布
                            probabilities = np.ones(len(next_candidates)) / len(next_candidates)

                        try:
                            next_idx = np.random.choice(len(next_candidates), p=probabilities)
                            next_node = next_candidates[next_idx]
                        except ValueError:
                            # 如果概率选择失败，随机选择
                            next_idx = np.random.randint(0, len(next_candidates))
                            next_node = next_candidates[next_idx]

                        path.append(next_node)
                        total_cost += current_node.calculate_transmission_energy(
                            current_node.distance_to(next_node), current_node.packet_size)
                        visited.add(next_node.node_id)
                        current_node = next_node
                    else:
                        break

                # 添加到基站的最终传输成本
                bs_distance = math.sqrt((current_node.x - self.base_station[0])**2 +
                                      (current_node.y - self.base_station[1])**2)
                total_cost += current_node.calculate_transmission_energy(bs_distance, current_node.packet_size)

                # 更新最优路径
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_path = path.copy()

            # 更新信息素
            for i in range(len(best_path) - 1):
                pheromone[(best_path[i].node_id, best_path[i+1].node_id)] *= (1 - rho)
                pheromone[(best_path[i].node_id, best_path[i+1].node_id)] += 1.0 / best_cost

        return best_path

    def pso_parameter_optimization(self, node: EnhancedNode, path: List[EnhancedNode]) -> Dict:
        """粒子群优化路由参数"""
        if not path:
            return {}

        # 简化的PSO参数优化
        # 优化传输功率、数据聚合率等参数

        # PSO参数
        n_particles = 5
        n_dimensions = 3  # 传输功率因子、聚合率、重传概率

        # 初始化粒子群
        particles = []
        for _ in range(n_particles):
            position = np.random.uniform(0.1, 1.0, n_dimensions)
            velocity = np.random.uniform(-0.1, 0.1, n_dimensions)
            particles.append({'pos': position, 'vel': velocity, 'best_pos': position.copy(), 'best_cost': float('inf')})

        global_best_pos = np.random.uniform(0.1, 1.0, n_dimensions)
        global_best_cost = float('inf')

        # PSO迭代
        for iteration in range(3):  # 减少迭代次数
            for particle in particles:
                # 评估当前位置的适应度
                cost = self.evaluate_routing_parameters(node, path, particle['pos'])

                # 更新个体最优
                if cost < particle['best_cost']:
                    particle['best_cost'] = cost
                    particle['best_pos'] = particle['pos'].copy()

                # 更新全局最优
                if cost < global_best_cost:
                    global_best_cost = cost
                    global_best_pos = particle['pos'].copy()

            # 更新粒子速度和位置
            w = 0.5  # 惯性权重
            c1 = 1.5  # 个体学习因子
            c2 = 1.5  # 社会学习因子

            for particle in particles:
                r1, r2 = np.random.random(n_dimensions), np.random.random(n_dimensions)

                particle['vel'] = (w * particle['vel'] +
                                 c1 * r1 * (particle['best_pos'] - particle['pos']) +
                                 c2 * r2 * (global_best_pos - particle['pos']))

                particle['pos'] += particle['vel']
                particle['pos'] = np.clip(particle['pos'], 0.1, 1.0)

        return {
            'power_factor': global_best_pos[0],
            'aggregation_rate': global_best_pos[1],
            'retransmission_prob': global_best_pos[2]
        }

    def evaluate_routing_parameters(self, node: EnhancedNode, path: List[EnhancedNode], params: np.ndarray) -> float:
        """评估路由参数的适应度"""
        if not path:
            return float('inf')

        power_factor, aggregation_rate, retrans_prob = params

        # 计算总能耗
        total_energy = 0.0
        for i in range(len(path) - 1):
            distance = path[i].distance_to(path[i + 1])
            energy = path[i].calculate_transmission_energy(distance, node.packet_size)
            total_energy += energy * power_factor

        # 计算延迟惩罚
        delay_penalty = len(path) * 0.1

        # 计算可靠性奖励
        reliability_bonus = sum(n.trust_value for n in path) / len(path)

        # 综合适应度（越小越好）
        fitness = total_energy + delay_penalty - reliability_bonus * 0.5

        return fitness

    def enhanced_data_transmission(self):
        """增强型数据传输阶段"""
        if not self.cluster_heads:
            return

        round_energy_consumption = 0.0
        successful_transmissions = 0

        # 簇内数据收集（链式结构优化）
        for cluster_id, chain in enumerate(self.chains) if self.chain_enabled else enumerate([]):
            if not chain:
                continue

            # 链式数据传输：从链尾到链头
            for i in range(len(chain) - 1, 0, -1):
                current_node = chain[i]
                next_node = chain[i - 1]

                if current_node.is_alive and next_node.is_alive:
                    # 计算传输能耗
                    distance = current_node.distance_to(next_node)
                    tx_energy = current_node.calculate_transmission_energy(distance, current_node.packet_size)
                    rx_energy = next_node.calculate_reception_energy(current_node.packet_size)

                    # 消耗能量
                    current_node.consume_energy(tx_energy)
                    next_node.consume_energy(rx_energy)

                    round_energy_consumption += tx_energy + rx_energy
                    successful_transmissions += 1

                    # 数据聚合（减少数据量）
                    if hasattr(next_node, 'aggregation_rate'):
                        current_node.packet_size = int(current_node.packet_size * 0.8)  # 聚合压缩

        # 传统簇内数据收集（非链式结构）
        if not self.chain_enabled:
            for node in self.nodes:
                if node.is_alive and not node.is_cluster_head and node.cluster_id >= 0:
                    # 找到对应的簇头
                    cluster_head = None
                    for ch in self.cluster_heads:
                        if ch.cluster_id == node.cluster_id:
                            cluster_head = ch
                            break

                    if cluster_head and cluster_head.is_alive:
                        # 发送数据到簇头
                        distance = node.distance_to(cluster_head)
                        tx_energy = node.calculate_transmission_energy(distance, node.packet_size)
                        rx_energy = cluster_head.calculate_reception_energy(node.packet_size)

                        node.consume_energy(tx_energy)
                        cluster_head.consume_energy(rx_energy)

                        round_energy_consumption += tx_energy + rx_energy
                        successful_transmissions += 1

        # 簇头到基站的数据传输
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue

            if ch.next_hop and ch.next_hop.is_alive:
                # 多跳传输
                distance = ch.distance_to(ch.next_hop)
                tx_energy = ch.calculate_transmission_energy(distance, ch.packet_size)
                rx_energy = ch.next_hop.calculate_reception_energy(ch.packet_size)

                ch.consume_energy(tx_energy)
                ch.next_hop.consume_energy(rx_energy)

                round_energy_consumption += tx_energy + rx_energy
                successful_transmissions += 1
            else:
                # 直接传输到基站
                bs_distance = math.sqrt((ch.x - self.base_station[0])**2 + (ch.y - self.base_station[1])**2)
                tx_energy = ch.calculate_transmission_energy(bs_distance, ch.packet_size)

                ch.consume_energy(tx_energy)
                round_energy_consumption += tx_energy
                successful_transmissions += 1

        # 更新统计信息
        self.total_energy_consumed += round_energy_consumption
        self.packets_sent += successful_transmissions
        self.packets_received += successful_transmissions  # 假设无丢包

        # 更新死亡节点数
        current_dead = sum(1 for node in self.nodes if not node.is_alive)
        if current_dead > self.dead_nodes:
            self.dead_nodes = current_dead
            if self.network_lifetime == 0:  # 记录第一个节点死亡时间
                self.network_lifetime = self.current_round

    def adaptive_energy_management(self):
        """自适应能量管理"""
        # 预测节点剩余生命周期
        for node in self.nodes:
            if node.is_alive and node.current_energy > 0:
                # 基于当前能耗速率预测剩余轮数
                if self.current_round > 0:
                    energy_consumption_rate = (node.initial_energy - node.current_energy) / self.current_round
                    if energy_consumption_rate > 0:
                        node.predicted_lifetime = node.current_energy / energy_consumption_rate
                    else:
                        node.predicted_lifetime = float('inf')

                # 更新拥塞概率（基于邻居节点状态）
                alive_neighbors = sum(1 for n in node.neighbors if n.is_alive)
                total_neighbors = len(node.neighbors)
                if total_neighbors > 0:
                    node.congestion_probability = 1.0 - (alive_neighbors / total_neighbors)
                else:
                    node.congestion_probability = 0.0

                # 更新故障风险
                if node.residual_energy_ratio < 0.2:
                    node.failure_risk = 1.0 - node.residual_energy_ratio
                else:
                    node.failure_risk = 0.0

        # 动态调整簇头选择策略
        avg_energy = np.mean([node.current_energy for node in self.nodes if node.is_alive])
        if avg_energy < 0.5:  # 网络能量较低时
            self.cluster_ratio = min(0.1, self.cluster_ratio + 0.01)  # 增加簇头比例
        elif avg_energy > 1.5:  # 网络能量充足时
            self.cluster_ratio = max(0.03, self.cluster_ratio - 0.01)  # 减少簇头比例

    def run_single_round(self):
        """执行单轮协议操作"""
        self.current_round += 1

        # 检查网络连通性
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if len(alive_nodes) < 2:
            return False  # 网络已断开

        # 1. 更新网络拓扑
        self.build_network_graph()

        # 2. 自适应能量管理
        self.adaptive_energy_management()

        # 3. 增强型模糊分簇
        self.enhanced_fuzzy_clustering()

        # 4. 混合元启发式路由
        self.hybrid_metaheuristic_routing()

        # 5. 数据传输
        self.enhanced_data_transmission()

        # 6. 记录性能数据
        current_energy = sum(node.current_energy for node in self.nodes if node.is_alive)
        self.energy_consumption_per_round.append(self.total_energy_consumed)
        self.alive_nodes_per_round.append(len(alive_nodes))

        return len(alive_nodes) > 0

    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """运行完整仿真"""
        print(f"🚀 开始Enhanced EEHFR协议仿真...")
        print(f"   最大轮数: {max_rounds}")

        start_time = time.time()

        for round_num in range(max_rounds):
            if not self.run_single_round():
                print(f"⚠️  网络在第 {round_num} 轮断开连接")
                break

            # 每100轮输出一次进度
            if round_num % 100 == 0:
                alive_count = len([n for n in self.nodes if n.is_alive])
                avg_energy = np.mean([n.current_energy for n in self.nodes if n.is_alive]) if alive_count > 0 else 0
                print(f"   轮次 {round_num}: 存活节点 {alive_count}/{len(self.nodes)}, 平均能量 {avg_energy:.3f}J")

        simulation_time = time.time() - start_time

        # 计算最终统计结果
        final_results = self.calculate_performance_metrics()
        final_results['simulation_time'] = simulation_time
        final_results['total_rounds'] = self.current_round

        print(f"✅ 仿真完成!")
        print(f"   总轮数: {self.current_round}")
        print(f"   网络生存时间: {self.network_lifetime} 轮")
        print(f"   总能耗: {self.total_energy_consumed:.4f} J")
        print(f"   仿真时间: {simulation_time:.2f} 秒")

        return final_results

    def calculate_performance_metrics(self) -> Dict:
        """计算性能指标"""
        alive_nodes = [node for node in self.nodes if node.is_alive]

        metrics = {
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
            'rounds_completed': self.current_round
        }

        return metrics
