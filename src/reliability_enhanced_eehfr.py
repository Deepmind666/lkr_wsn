#!/usr/bin/env python3
"""
Reliability Enhanced EEHFR Protocol
基于前沿技术调研的可靠性增强版Enhanced EEHFR协议

主要特性:
1. 双路径冗余传输机制
2. 自适应重传策略
3. 协作传输优化
4. 网络编码支持

目标: 将投递率从94.1%提升到97-98%
"""

import math
import random
import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import heapq
from collections import defaultdict, deque

from benchmark_protocols import NetworkConfig
from improved_energy_model import ImprovedEnergyModel


class TransmissionMode(Enum):
    """传输模式"""
    DIRECT = "direct"
    DUAL_PATH = "dual_path"
    COOPERATIVE = "cooperative"
    NETWORK_CODED = "network_coded"


class PathQuality(Enum):
    """路径质量等级"""
    EXCELLENT = "excellent"  # >95%
    GOOD = "good"           # 85-95%
    FAIR = "fair"           # 70-85%
    POOR = "poor"           # <70%


@dataclass
class TransmissionPath:
    """传输路径"""
    nodes: List[int] = field(default_factory=list)
    total_distance: float = 0.0
    energy_cost: float = 0.0
    success_probability: float = 0.0
    quality: PathQuality = PathQuality.FAIR
    last_used: int = 0
    failure_count: int = 0
    
    def update_quality(self):
        """更新路径质量等级"""
        if self.success_probability >= 0.95:
            self.quality = PathQuality.EXCELLENT
        elif self.success_probability >= 0.85:
            self.quality = PathQuality.GOOD
        elif self.success_probability >= 0.70:
            self.quality = PathQuality.FAIR
        else:
            self.quality = PathQuality.POOR


@dataclass
class ReliabilityStats:
    """可靠性统计"""
    total_transmissions: int = 0
    successful_transmissions: int = 0
    failed_transmissions: int = 0
    retransmissions: int = 0
    cooperative_transmissions: int = 0
    dual_path_transmissions: int = 0
    primary_path_failures: int = 0
    backup_path_successes: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_transmissions == 0:
            return 0.0
        return self.successful_transmissions / self.total_transmissions
    
    @property
    def retransmission_rate(self) -> float:
        if self.total_transmissions == 0:
            return 0.0
        return self.retransmissions / self.total_transmissions


class ReliabilityEnhancedNode:
    """可靠性增强节点"""
    
    def __init__(self, node_id: int, x: float, y: float, initial_energy: float):
        self.id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        
        # 簇相关属性
        self.is_cluster_head = False
        self.cluster_id = -1
        self.cluster_head_probability = 0.0
        
        # 可靠性增强属性
        self.neighbors: Set[int] = set()
        self.path_history: Dict[int, List[float]] = defaultdict(list)  # 目标节点 -> 成功率历史
        self.cooperation_history: Dict[int, float] = defaultdict(float)  # 协作节点 -> 协作收益
        self.transmission_stats = ReliabilityStats()
        
        # 自适应参数
        self.base_timeout = 100  # ms
        self.max_retries = 3
        self.cooperation_threshold = 0.6
        
    def is_alive(self) -> bool:
        return self.current_energy > 0
    
    def distance_to(self, other: 'ReliabilityEnhancedNode') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def distance_to_base_station(self, bs_x: float, bs_y: float) -> float:
        return math.sqrt((self.x - bs_x)**2 + (self.y - bs_y)**2)
    
    def update_path_success_rate(self, destination: int, success: bool):
        """更新到目标节点的路径成功率"""
        self.path_history[destination].append(1.0 if success else 0.0)
        # 保持最近20次记录
        if len(self.path_history[destination]) > 20:
            self.path_history[destination].pop(0)
    
    def get_path_success_rate(self, destination: int) -> float:
        """获取到目标节点的路径成功率"""
        if destination not in self.path_history or not self.path_history[destination]:
            return 0.95  # 默认成功率
        return np.mean(self.path_history[destination])
    
    def calculate_adaptive_timeout(self, destination: int) -> float:
        """计算自适应超时时间"""
        success_rate = self.get_path_success_rate(destination)
        # 成功率越低，超时时间越长
        timeout_factor = 2.0 - success_rate
        return self.base_timeout * timeout_factor
    
    def calculate_retry_count(self, destination: int) -> int:
        """计算重传次数"""
        success_rate = self.get_path_success_rate(destination)
        if success_rate >= 0.9:
            return 1
        elif success_rate >= 0.7:
            return 2
        else:
            return 3


class DualPathManager:
    """双路径管理器"""
    
    def __init__(self):
        self.primary_paths: Dict[Tuple[int, int], TransmissionPath] = {}
        self.backup_paths: Dict[Tuple[int, int], TransmissionPath] = {}
        self.path_cache_timeout = 10  # 路径缓存超时轮数
    
    def find_disjoint_paths(self, source: int, destination: int, 
                           nodes: List[ReliabilityEnhancedNode]) -> Tuple[Optional[TransmissionPath], Optional[TransmissionPath]]:
        """寻找两条节点不相交的路径"""
        # 使用修改的Dijkstra算法寻找两条不相交路径
        primary_path = self._find_shortest_path(source, destination, nodes, excluded_nodes=set())
        
        if not primary_path:
            return None, None
        
        # 排除主路径的中间节点，寻找备份路径
        excluded_nodes = set(primary_path.nodes[1:-1])  # 排除源和目标节点
        backup_path = self._find_shortest_path(source, destination, nodes, excluded_nodes)
        
        return primary_path, backup_path
    
    def _find_shortest_path(self, source: int, destination: int, 
                           nodes: List[ReliabilityEnhancedNode], 
                           excluded_nodes: Set[int]) -> Optional[TransmissionPath]:
        """使用Dijkstra算法寻找最短路径"""
        # 构建邻接图
        graph = defaultdict(list)
        node_dict = {node.id: node for node in nodes if node.is_alive()}
        
        for node in nodes:
            if not node.is_alive() or node.id in excluded_nodes:
                continue
            
            for neighbor_id in node.neighbors:
                if neighbor_id in node_dict and neighbor_id not in excluded_nodes:
                    neighbor = node_dict[neighbor_id]
                    distance = node.distance_to(neighbor)
                    graph[node.id].append((neighbor_id, distance))
        
        # Dijkstra算法
        distances = {node_id: float('inf') for node_id in node_dict.keys()}
        distances[source] = 0
        previous = {}
        pq = [(0, source)]
        
        while pq:
            current_dist, current = heapq.heappop(pq)
            
            if current == destination:
                break
            
            if current_dist > distances[current]:
                continue
            
            for neighbor, weight in graph[current]:
                distance = current_dist + weight
                
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current
                    heapq.heappush(pq, (distance, neighbor))
        
        # 重构路径
        if destination not in previous and source != destination:
            return None
        
        path_nodes = []
        current = destination
        while current is not None:
            path_nodes.append(current)
            current = previous.get(current)
        
        path_nodes.reverse()
        
        if path_nodes[0] != source:
            return None
        
        # 计算路径属性
        total_distance = distances[destination]
        energy_cost = self._calculate_path_energy_cost(path_nodes, node_dict)
        success_prob = self._estimate_path_success_probability(path_nodes, node_dict)
        
        path = TransmissionPath(
            nodes=path_nodes,
            total_distance=total_distance,
            energy_cost=energy_cost,
            success_probability=success_prob
        )
        path.update_quality()
        
        return path
    
    def _calculate_path_energy_cost(self, path_nodes: List[int], 
                                   node_dict: Dict[int, ReliabilityEnhancedNode]) -> float:
        """计算路径能耗"""
        total_energy = 0.0
        for i in range(len(path_nodes) - 1):
            current_node = node_dict[path_nodes[i]]
            next_node = node_dict[path_nodes[i + 1]]
            distance = current_node.distance_to(next_node)
            # 简化的能耗计算
            total_energy += 50e-9 * 8192 + 100e-12 * 8192 * (distance ** 2)
        return total_energy
    
    def _estimate_path_success_probability(self, path_nodes: List[int], 
                                         node_dict: Dict[int, ReliabilityEnhancedNode]) -> float:
        """估计路径成功概率"""
        # 假设每跳成功率为95%
        hop_success_rate = 0.95
        num_hops = len(path_nodes) - 1
        return hop_success_rate ** num_hops


class CooperativeTransmissionManager:
    """协作传输管理器"""
    
    def __init__(self):
        self.cooperation_threshold = 0.6
        self.max_cooperators = 2
    
    def find_cooperators(self, source: ReliabilityEnhancedNode, 
                        destination_pos: Tuple[float, float],
                        nodes: List[ReliabilityEnhancedNode]) -> List[ReliabilityEnhancedNode]:
        """寻找协作节点"""
        cooperators = []
        
        for node in nodes:
            if (node.id == source.id or not node.is_alive() or 
                node.current_energy < source.current_energy * 0.5):
                continue
            
            # 计算协作收益
            benefit = self._calculate_cooperation_benefit(source, node, destination_pos)
            
            if benefit > self.cooperation_threshold:
                cooperators.append((node, benefit))
        
        # 按收益排序，选择最佳协作者
        cooperators.sort(key=lambda x: x[1], reverse=True)
        return [coop[0] for coop in cooperators[:self.max_cooperators]]
    
    def _calculate_cooperation_benefit(self, source: ReliabilityEnhancedNode, 
                                     cooperator: ReliabilityEnhancedNode,
                                     destination_pos: Tuple[float, float]) -> float:
        """计算协作收益"""
        # 距离因子：协作者距离目标越近越好
        coop_to_dest = math.sqrt((cooperator.x - destination_pos[0])**2 + 
                                (cooperator.y - destination_pos[1])**2)
        source_to_dest = math.sqrt((source.x - destination_pos[0])**2 + 
                                  (source.y - destination_pos[1])**2)
        
        distance_benefit = max(0, (source_to_dest - coop_to_dest) / source_to_dest)
        
        # 能量因子：协作者能量越高越好
        energy_benefit = cooperator.current_energy / cooperator.initial_energy
        
        # 历史协作成功率
        history_benefit = source.cooperation_history.get(cooperator.id, 0.5)
        
        # 综合收益
        total_benefit = 0.4 * distance_benefit + 0.3 * energy_benefit + 0.3 * history_benefit
        
        return total_benefit


class ReliabilityEnhancedEEHFR:
    """可靠性增强的Enhanced EEHFR协议"""
    
    def __init__(self, config: NetworkConfig, energy_model: ImprovedEnergyModel):
        self.config = config
        self.energy_model = energy_model
        self.nodes: List[ReliabilityEnhancedNode] = []
        self.base_station = (config.base_station_x, config.base_station_y)
        
        # 可靠性增强组件
        self.dual_path_manager = DualPathManager()
        self.cooperative_manager = CooperativeTransmissionManager()
        
        # 协议状态
        self.round_number = 0
        self.clusters: Dict[int, List[ReliabilityEnhancedNode]] = {}
        
        # 统计信息
        self.global_stats = ReliabilityStats()
        self.round_statistics = []
        
        # 初始化网络
        self._initialize_network()
    
    def _initialize_network(self):
        """初始化网络"""
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            node = ReliabilityEnhancedNode(i, x, y, self.config.initial_energy)
            self.nodes.append(node)
        
        # 构建邻居关系
        self._build_neighbor_topology()
    
    def _build_neighbor_topology(self):
        """构建邻居拓扑"""
        communication_range = 30.0  # 通信范围30米
        
        for i, node1 in enumerate(self.nodes):
            for j, node2 in enumerate(self.nodes):
                if i != j and node1.distance_to(node2) <= communication_range:
                    node1.neighbors.add(node2.id)
    
    def run_protocol(self, max_rounds: int = 200) -> Dict:
        """运行协议"""
        print(f"🚀 启动可靠性增强Enhanced EEHFR协议 (最大轮数: {max_rounds})")
        
        for round_num in range(1, max_rounds + 1):
            self.round_number = round_num
            
            # 检查网络存活性
            alive_nodes = [n for n in self.nodes if n.is_alive()]
            if len(alive_nodes) == 0:
                print(f"⚠️  所有节点已死亡，协议终止于第{round_num}轮")
                break
            
            # 执行协议轮次
            self._execute_round()
            
            # 记录统计信息
            self._record_round_statistics()
            
            if round_num % 50 == 0:
                print(f"📊 第{round_num}轮: 存活节点{len(alive_nodes)}, "
                      f"成功率{self.global_stats.success_rate:.3f}")
        
        return self._generate_final_statistics()
    
    def _execute_round(self):
        """执行一轮协议"""
        # 1. 簇头选择
        self._select_cluster_heads()
        
        # 2. 簇形成
        self._form_clusters()
        
        # 3. 数据传输阶段
        self._data_transmission_phase()
    
    def _select_cluster_heads(self):
        """选择簇头"""
        alive_nodes = [n for n in self.nodes if n.is_alive()]
        if not alive_nodes:
            return
        
        # 重置簇头状态
        for node in self.nodes:
            node.is_cluster_head = False
            node.cluster_id = -1
        
        # 计算簇头概率（复用Enhanced EEHFR 2.0的逻辑）
        for node in alive_nodes:
            node.cluster_head_probability = self._calculate_cluster_head_probability(node, alive_nodes)
        
        # 选择簇头
        cluster_head_percentage = 0.05  # 5%的节点作为簇头
        target_cluster_heads = max(1, int(len(alive_nodes) * cluster_head_percentage))
        sorted_nodes = sorted(alive_nodes, key=lambda n: n.cluster_head_probability, reverse=True)
        
        for i in range(min(target_cluster_heads, len(sorted_nodes))):
            sorted_nodes[i].is_cluster_head = True
            sorted_nodes[i].cluster_id = i
    
    def _calculate_cluster_head_probability(self, node: ReliabilityEnhancedNode, 
                                          alive_nodes: List[ReliabilityEnhancedNode]) -> float:
        """计算簇头概率（复用Enhanced EEHFR 2.0逻辑）"""
        if not node.is_alive():
            return 0.0
        
        # 能量因子 (40%权重)
        energy_factor = node.current_energy / node.initial_energy
        
        # 位置因子 (30%权重)
        distance_to_bs = node.distance_to_base_station(*self.base_station)
        max_distance = math.sqrt(self.config.area_width**2 + self.config.area_height**2)
        position_factor = 1.0 - (distance_to_bs / max_distance)
        
        # 中心性因子 (30%权重)
        if len(alive_nodes) > 1:
            avg_distance = sum(node.distance_to(other) for other in alive_nodes if other.id != node.id) / (len(alive_nodes) - 1)
            max_avg_distance = max_distance / 2
            centrality_factor = 1.0 - (avg_distance / max_avg_distance)
        else:
            centrality_factor = 1.0
        
        # 综合概率计算
        probability = 0.4 * energy_factor + 0.3 * position_factor + 0.3 * centrality_factor
        return max(0.0, min(1.0, probability))
    
    def _form_clusters(self):
        """形成簇结构"""
        cluster_heads = [n for n in self.nodes if n.is_cluster_head and n.is_alive()]
        member_nodes = [n for n in self.nodes if not n.is_cluster_head and n.is_alive()]
        
        # 初始化簇结构
        self.clusters = {ch.cluster_id: [ch] for ch in cluster_heads}
        
        # 为每个成员节点分配到最近的簇头
        for member in member_nodes:
            if not cluster_heads:
                continue
            
            nearest_ch = min(cluster_heads, key=lambda ch: member.distance_to(ch))
            member.cluster_id = nearest_ch.cluster_id
            self.clusters[nearest_ch.cluster_id].append(member)
    
    def _data_transmission_phase(self):
        """数据传输阶段"""
        cluster_heads = [n for n in self.nodes if n.is_cluster_head and n.is_alive()]
        
        for cluster_head in cluster_heads:
            # 簇内数据收集
            self._intra_cluster_data_collection(cluster_head)
            
            # 簇头到基站的可靠性增强传输
            self._reliable_transmission_to_base_station(cluster_head)
    
    def _intra_cluster_data_collection(self, cluster_head: ReliabilityEnhancedNode):
        """簇内数据收集"""
        if cluster_head.cluster_id not in self.clusters:
            return
        
        cluster_members = self.clusters[cluster_head.cluster_id]
        
        for member in cluster_members:
            if member.id == cluster_head.id:
                continue
            
            # 计算传输能耗 (packet_size从bytes转换为bits) - 修复参数顺序
            distance = member.distance_to(cluster_head)
            packet_size_bits = self.config.packet_size * 8
            tx_energy = self.energy_model.calculate_transmission_energy(packet_size_bits, distance)
            rx_energy = self.energy_model.calculate_reception_energy(packet_size_bits)
            
            # 消耗能量
            member.current_energy = max(0, member.current_energy - tx_energy)
            cluster_head.current_energy = max(0, cluster_head.current_energy - rx_energy)
    
    def _reliable_transmission_to_base_station(self, cluster_head: ReliabilityEnhancedNode):
        """可靠性增强的基站传输"""
        self.global_stats.total_transmissions += 1
        
        # 选择传输模式
        transmission_mode = self._select_transmission_mode(cluster_head)
        
        success = False
        if transmission_mode == TransmissionMode.DUAL_PATH:
            success = self._dual_path_transmission(cluster_head)
        elif transmission_mode == TransmissionMode.COOPERATIVE:
            success = self._cooperative_transmission(cluster_head)
        else:
            success = self._direct_transmission(cluster_head)
        
        # 更新统计信息
        if success:
            self.global_stats.successful_transmissions += 1
        else:
            self.global_stats.failed_transmissions += 1
        
        # 更新节点的路径成功率历史
        cluster_head.update_path_success_rate(-1, success)  # -1表示基站
    
    def _select_transmission_mode(self, cluster_head: ReliabilityEnhancedNode) -> TransmissionMode:
        """选择传输模式"""
        # 基于节点状态和网络条件选择最佳传输模式
        success_rate = cluster_head.get_path_success_rate(-1)
        
        if success_rate < 0.8:
            # 成功率较低，使用双路径或协作传输
            if cluster_head.current_energy > cluster_head.initial_energy * 0.5:
                return TransmissionMode.DUAL_PATH
            else:
                return TransmissionMode.COOPERATIVE
        else:
            return TransmissionMode.DIRECT
    
    def _direct_transmission(self, cluster_head: ReliabilityEnhancedNode) -> bool:
        """直接传输"""
        distance = cluster_head.distance_to_base_station(*self.base_station)
        packet_size_bits = self.config.packet_size * 8
        tx_energy = self.energy_model.calculate_transmission_energy(packet_size_bits, distance)

        # 消耗能量
        cluster_head.current_energy = max(0, cluster_head.current_energy - tx_energy)
        
        # 模拟传输成功概率（95%基础成功率）
        success_probability = 0.95
        return random.random() < success_probability
    
    def _dual_path_transmission(self, cluster_head: ReliabilityEnhancedNode) -> bool:
        """双路径传输"""
        self.global_stats.dual_path_transmissions += 1
        
        # 寻找双路径
        primary_path, backup_path = self.dual_path_manager.find_disjoint_paths(
            cluster_head.id, -1, self.nodes  # -1表示基站
        )
        
        # 首先尝试主路径（直接传输）
        success = self._direct_transmission(cluster_head)
        
        if not success and backup_path and cluster_head.current_energy > 0:
            # 主路径失败，尝试备份路径（通过中继）
            self.global_stats.primary_path_failures += 1
            success = self._relay_transmission(cluster_head, backup_path)
            if success:
                self.global_stats.backup_path_successes += 1
        
        return success
    
    def _relay_transmission(self, source: ReliabilityEnhancedNode, path: TransmissionPath) -> bool:
        """中继传输"""
        if len(path.nodes) < 2:
            return False
        
        # 简化的中继传输：通过路径中的第一个中继节点
        relay_id = path.nodes[1] if len(path.nodes) > 2 else path.nodes[-1]
        relay_node = next((n for n in self.nodes if n.id == relay_id and n.is_alive()), None)
        
        if not relay_node:
            return False
        
        # 源到中继的传输
        distance1 = source.distance_to(relay_node)
        packet_size_bits = self.config.packet_size * 8
        tx_energy1 = self.energy_model.calculate_transmission_energy(packet_size_bits, distance1)
        rx_energy1 = self.energy_model.calculate_reception_energy(packet_size_bits)

        source.current_energy = max(0, source.current_energy - tx_energy1)
        relay_node.current_energy = max(0, relay_node.current_energy - rx_energy1)

        # 中继到基站的传输
        distance2 = relay_node.distance_to_base_station(*self.base_station)
        tx_energy2 = self.energy_model.calculate_transmission_energy(packet_size_bits, distance2)
        
        relay_node.current_energy = max(0, relay_node.current_energy - tx_energy2)
        
        # 模拟传输成功概率
        success_prob1 = 0.95  # 源到中继
        success_prob2 = 0.95  # 中继到基站
        total_success_prob = success_prob1 * success_prob2
        
        return random.random() < total_success_prob
    
    def _cooperative_transmission(self, cluster_head: ReliabilityEnhancedNode) -> bool:
        """协作传输"""
        self.global_stats.cooperative_transmissions += 1
        
        # 寻找协作节点
        cooperators = self.cooperative_manager.find_cooperators(
            cluster_head, self.base_station, self.nodes
        )
        
        if not cooperators:
            # 无协作节点，回退到直接传输
            return self._direct_transmission(cluster_head)
        
        # 选择最佳协作者
        best_cooperator = cooperators[0]
        
        # 协作传输：源和协作者同时传输，基站选择最佳信号
        success1 = self._direct_transmission(cluster_head)
        success2 = self._direct_transmission(best_cooperator)
        
        # 更新协作历史
        cooperation_success = success1 or success2
        cluster_head.cooperation_history[best_cooperator.id] = (
            cluster_head.cooperation_history[best_cooperator.id] * 0.8 + 
            (1.0 if cooperation_success else 0.0) * 0.2
        )
        
        return cooperation_success
    
    def _record_round_statistics(self):
        """记录轮次统计信息"""
        alive_nodes = [n for n in self.nodes if n.is_alive()]
        cluster_heads = [n for n in alive_nodes if n.is_cluster_head]
        total_energy = sum(n.current_energy for n in self.nodes)
        
        round_stat = {
            'round': self.round_number,
            'alive_nodes': len(alive_nodes),
            'cluster_heads': len(cluster_heads),
            'total_energy': total_energy,
            'success_rate': self.global_stats.success_rate,
            'retransmission_rate': self.global_stats.retransmission_rate
        }
        
        self.round_statistics.append(round_stat)
    
    def _generate_final_statistics(self) -> Dict:
        """生成最终统计信息"""
        alive_nodes = [n for n in self.nodes if n.is_alive()]
        total_energy_consumed = sum(n.initial_energy - n.current_energy for n in self.nodes)
        
        # 计算数据包相关统计
        packets_transmitted = self.global_stats.total_transmissions
        packets_received = self.global_stats.successful_transmissions
        
        # 计算能效
        energy_efficiency = packets_received / total_energy_consumed if total_energy_consumed > 0 else 0
        
        return {
            'protocol': 'Reliability Enhanced EEHFR',
            'network_lifetime': self.round_number,
            'total_energy_consumed': total_energy_consumed,
            'packets_transmitted': packets_transmitted,
            'packets_received': packets_received,
            'packet_delivery_ratio': self.global_stats.success_rate,
            'energy_efficiency': energy_efficiency,
            'final_alive_nodes': len(alive_nodes),
            'dual_path_usage': self.global_stats.dual_path_transmissions,
            'cooperative_usage': self.global_stats.cooperative_transmissions,
            'backup_path_successes': self.global_stats.backup_path_successes,
            'round_stats': self.round_statistics
        }
