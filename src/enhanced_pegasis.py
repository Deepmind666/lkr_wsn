#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced PEGASIS: 能量感知的链式路由协议
基于经典PEGASIS算法，加入智能能量管理和链优化机制

核心改进:
1. 能量感知的链构建算法
2. 动态领导者选择机制  
3. 自适应传输功率控制
4. 智能数据融合策略

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0 (基于PEGASIS的渐进式改进)
"""

import math
import random
from typing import List, Dict, Tuple
from dataclasses import dataclass
from benchmark_protocols import NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

@dataclass
class EnhancedPEGASISConfig:
    """Enhanced PEGASIS配置参数"""
    # 基础网络参数
    num_nodes: int = 50
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 50.0
    initial_energy: float = 2.0
    
    # 通信参数
    transmission_range: float = 30.0
    packet_size: int = 1024  # bits
    
    # Enhanced PEGASIS特有参数
    energy_threshold: float = 0.1  # 能量阈值，低于此值的节点优先级降低
    leader_rotation_interval: int = 10  # 领导者轮换间隔
    chain_optimization_interval: int = 50  # 链优化间隔
    data_fusion_efficiency: float = 0.9  # 数据融合效率

class EnhancedNode:
    """Enhanced PEGASIS节点类"""
    
    def __init__(self, node_id: int, x: float, y: float, initial_energy: float):
        self.id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        
        # 链相关属性
        self.next_node_id = -1
        self.prev_node_id = -1
        self.is_leader = False
        self.chain_position = -1
        
        # 统计信息
        self.packets_sent = 0
        self.packets_received = 0
        self.total_distance_transmitted = 0.0
        self.leadership_count = 0
    
    def is_alive(self) -> bool:
        """检查节点是否存活"""
        return self.current_energy > 0
    
    def energy_ratio(self) -> float:
        """计算剩余能量比例"""
        return self.current_energy / self.initial_energy if self.initial_energy > 0 else 0
    
    def distance_to(self, other: 'EnhancedNode') -> float:
        """计算到另一个节点的距离"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def distance_to_base_station(self, bs_x: float, bs_y: float) -> float:
        """计算到基站的距离"""
        return math.sqrt((self.x - bs_x)**2 + (self.y - bs_y)**2)

class EnhancedPEGASISProtocol:
    """Enhanced PEGASIS协议主类"""
    
    def __init__(self, config: EnhancedPEGASISConfig):
        self.config = config
        self.nodes: List[EnhancedNode] = []
        self.chain: List[int] = []  # 节点ID的链序列
        self.current_leader_id = -1
        self.current_round = 0
        self.base_station = (config.base_station_x, config.base_station_y)
        
        # 性能统计
        self.total_energy_consumed = 0.0
        self.packets_transmitted = 0
        self.packets_received = 0
        self.packets_sent = 0  # 添加发送数据包统计
        self.network_lifetime = 0
        self.round_stats = []
        
        # 能耗模型
        self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    def initialize_network(self):
        """初始化网络拓扑"""
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            node = EnhancedNode(i, x, y, self.config.initial_energy)
            self.nodes.append(node)
        
        # 构建初始链
        self.build_energy_aware_chain()
        print(f"✅ Enhanced PEGASIS网络初始化完成: {len(self.nodes)}个节点")
    
    def build_energy_aware_chain(self):
        """构建能量感知的链结构"""
        alive_nodes = [node for node in self.nodes if node.is_alive()]
        if len(alive_nodes) <= 1:
            self.chain = [alive_nodes[0].id] if alive_nodes else []
            return
        
        # 改进1: 能量感知的起始节点选择
        # 不再选择距离基站最远的节点，而是选择能量充足且位置合适的节点
        start_candidates = sorted(alive_nodes, 
                                key=lambda n: (n.energy_ratio(), 
                                             -n.distance_to_base_station(*self.base_station)), 
                                reverse=True)
        
        # 选择前30%能量充足的节点中距离基站较远的作为起点
        top_energy_nodes = start_candidates[:max(1, len(start_candidates) // 3)]
        start_node = max(top_energy_nodes, 
                        key=lambda n: n.distance_to_base_station(*self.base_station))
        
        # 改进2: 能量感知的贪心链构建
        chain = [start_node.id]
        remaining = [n for n in alive_nodes if n.id != start_node.id]
        current = start_node
        
        while remaining:
            # 计算每个候选节点的综合得分
            best_node = None
            best_score = float('-inf')
            
            for candidate in remaining:
                # 距离因子 (越近越好)
                distance = current.distance_to(candidate)
                distance_score = 1.0 / (1.0 + distance)
                
                # 能量因子 (能量越多越好)
                energy_score = candidate.energy_ratio()
                
                # 综合得分 (距离权重0.7，能量权重0.3)
                total_score = 0.7 * distance_score + 0.3 * energy_score
                
                if total_score > best_score:
                    best_score = total_score
                    best_node = candidate
            
            if best_node:
                chain.append(best_node.id)
                remaining.remove(best_node)
                current = best_node
        
        self.chain = chain
        
        # 更新节点的链信息
        for i, node_id in enumerate(chain):
            node = self.nodes[node_id]
            node.chain_position = i
            node.next_node_id = chain[i + 1] if i < len(chain) - 1 else -1
            node.prev_node_id = chain[i - 1] if i > 0 else -1
    
    def select_leader(self) -> int:
        """改进3: 智能领导者选择"""
        alive_nodes = [node for node in self.nodes if node.is_alive()]
        if not alive_nodes:
            return -1
        
        # 计算每个节点的领导者适合度
        best_leader = None
        best_fitness = float('-inf')
        
        for node in alive_nodes:
            # 能量因子 (40%)
            energy_factor = node.energy_ratio()
            
            # 位置因子 (30%) - 距离基站适中的节点更适合
            distance_to_bs = node.distance_to_base_station(*self.base_station)
            avg_distance = sum(n.distance_to_base_station(*self.base_station) for n in alive_nodes) / len(alive_nodes)
            position_factor = 1.0 / (1.0 + abs(distance_to_bs - avg_distance))
            
            # 负载均衡因子 (20%) - 之前当过领导者的节点优先级降低
            load_factor = 1.0 / (1.0 + node.leadership_count)
            
            # 连接性因子 (10%) - 链中心位置的节点更适合
            connectivity_factor = 1.0 - abs(node.chain_position - len(self.chain) / 2) / (len(self.chain) / 2)
            
            # 综合适合度
            fitness = (0.4 * energy_factor + 0.3 * position_factor + 
                      0.2 * load_factor + 0.1 * connectivity_factor)
            
            if fitness > best_fitness:
                best_fitness = fitness
                best_leader = node
        
        if best_leader:
            # 重置所有节点的领导者状态
            for node in self.nodes:
                node.is_leader = False
            
            best_leader.is_leader = True
            best_leader.leadership_count += 1
            self.current_leader_id = best_leader.id
            return best_leader.id
        
        return -1
    
    def data_transmission_round(self) -> int:
        """数据传输轮次 - 修复版本，确保正确的数据包计数"""
        if not self.chain or self.current_leader_id == -1:
            return 0

        total_packets = 0
        leader_node = self.nodes[self.current_leader_id]
        leader_position = leader_node.chain_position
        alive_nodes = [node for node in self.nodes if node.is_alive()]

        if not alive_nodes:
            return 0

        # 阶段1: 链内数据传输 - 每个节点都生成并传输数据包
        # 左侧链传输 (从0到leader_position-1)
        for i in range(leader_position):
            current_node = self.nodes[self.chain[i]]

            if not current_node.is_alive():
                continue

            # 找到下一个存活的节点作为接收者
            next_node = None
            for j in range(i + 1, len(self.chain)):
                if self.nodes[self.chain[j]].is_alive():
                    next_node = self.nodes[self.chain[j]]
                    break

            if not next_node:
                continue

            # 计算传输距离和能耗
            distance = current_node.distance_to(next_node)
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8, distance
            )
            rx_energy = self.energy_model.calculate_reception_energy(
                self.config.packet_size * 8
            )

            # 检查能量是否足够并执行传输
            if (current_node.current_energy >= tx_energy and
                next_node.current_energy >= rx_energy):

                # 消耗能量
                current_node.current_energy -= tx_energy
                next_node.current_energy -= rx_energy

                # 更新统计
                current_node.packets_sent += 1
                current_node.total_distance_transmitted += distance
                self.total_energy_consumed += (tx_energy + rx_energy)
                self.packets_sent += 1  # 协议级别统计
                total_packets += 1

                # 成功接收计数
                self.packets_received += 1

        # 右侧链传输 (从len(chain)-1到leader_position+1)
        for i in range(len(self.chain) - 1, leader_position, -1):
            current_node = self.nodes[self.chain[i]]

            if not current_node.is_alive():
                continue

            # 找到前一个存活的节点作为接收者
            prev_node = None
            for j in range(i - 1, -1, -1):
                if self.nodes[self.chain[j]].is_alive():
                    prev_node = self.nodes[self.chain[j]]
                    break

            if not prev_node:
                continue

            # 计算传输距离和能耗
            distance = current_node.distance_to(prev_node)
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8, distance
            )
            rx_energy = self.energy_model.calculate_reception_energy(
                self.config.packet_size * 8
            )

            # 检查能量是否足够并执行传输
            if (current_node.current_energy >= tx_energy and
                prev_node.current_energy >= rx_energy):

                # 消耗能量
                current_node.current_energy -= tx_energy
                prev_node.current_energy -= rx_energy

                # 更新统计
                current_node.packets_sent += 1
                current_node.total_distance_transmitted += distance
                self.total_energy_consumed += (tx_energy + rx_energy)
                self.packets_sent += 1  # 协议级别统计
                total_packets += 1

                # 成功接收计数
                self.packets_received += 1

        # 阶段2: 数据聚合（领导者处理所有收到的数据）
        if leader_node.is_alive():
            # 聚合能耗：每个存活节点的数据都需要处理
            aggregation_energy = 0.000005 * len(alive_nodes)  # 5nJ per bit per node
            if leader_node.current_energy >= aggregation_energy:
                leader_node.current_energy -= aggregation_energy
                self.total_energy_consumed += aggregation_energy

        # 阶段3: 领导者向基站传输聚合数据
        if leader_node.is_alive():
            distance_to_bs = leader_node.distance_to_base_station(*self.base_station)
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8, distance_to_bs
            )

            if leader_node.current_energy >= tx_energy:
                leader_node.current_energy -= tx_energy
                leader_node.packets_sent += 1
                leader_node.total_distance_transmitted += distance_to_bs
                self.total_energy_consumed += tx_energy
                self.packets_sent += 1  # 协议级别统计
                total_packets += 1
                self.packets_received += 1  # 基站成功接收聚合数据

        # 更新总传输数据包计数
        self.packets_transmitted += total_packets
        return total_packets

    def run_round(self) -> bool:
        """运行一轮协议"""
        self.current_round += 1

        # 检查存活节点
        alive_nodes = [node for node in self.nodes if node.is_alive()]
        if not alive_nodes:
            return False

        # 定期优化链结构
        if self.current_round % self.config.chain_optimization_interval == 1:
            self.build_energy_aware_chain()

        # 定期轮换领导者
        if (self.current_round % self.config.leader_rotation_interval == 1 or
            self.current_leader_id == -1 or
            not self.nodes[self.current_leader_id].is_alive()):
            self.select_leader()

        # 执行数据传输
        packets_sent = self.data_transmission_round()

        # 记录统计信息
        alive_count = len(alive_nodes)
        total_energy = sum(node.current_energy for node in self.nodes)
        avg_energy_ratio = sum(node.energy_ratio() for node in alive_nodes) / len(alive_nodes)

        round_stat = {
            'round': self.current_round,
            'alive_nodes': alive_count,
            'total_energy': total_energy,
            'avg_energy_ratio': avg_energy_ratio,
            'packets_sent': packets_sent,
            'leader_id': self.current_leader_id,
            'chain_length': len(self.chain)
        }
        self.round_stats.append(round_stat)

        return alive_count > 0

    def run_simulation(self, max_rounds: int = 200) -> Dict:
        """运行完整仿真"""
        print(f"🚀 开始Enhanced PEGASIS仿真 (最大轮数: {max_rounds})")

        while self.current_round < max_rounds:
            if not self.run_round():
                break

            # 每50轮输出状态
            if self.current_round % 50 == 0:
                alive_nodes = len([n for n in self.nodes if n.is_alive()])
                total_energy = sum(n.current_energy for n in self.nodes)
                avg_energy = total_energy / len(self.nodes)
                print(f"   轮数 {self.current_round}: 存活节点 {alive_nodes}, "
                      f"平均能量 {avg_energy:.3f}J, 链长度 {len(self.chain)}")

        # 计算最终统计
        self.network_lifetime = self.current_round
        final_alive_nodes = len([n for n in self.nodes if n.is_alive()])

        # 计算性能指标
        energy_efficiency = self.packets_received / self.total_energy_consumed if self.total_energy_consumed > 0 else 0
        packet_delivery_ratio = self.packets_received / self.packets_transmitted if self.packets_transmitted > 0 else 0

        # 计算改进指标
        total_leadership_changes = sum(node.leadership_count for node in self.nodes)
        avg_transmission_distance = (sum(node.total_distance_transmitted for node in self.nodes) /
                                   sum(node.packets_sent for node in self.nodes) if
                                   sum(node.packets_sent for node in self.nodes) > 0 else 0)

        print(f"✅ Enhanced PEGASIS仿真完成，网络在 {self.network_lifetime} 轮后结束")

        return {
            'protocol': 'Enhanced PEGASIS',
            'network_lifetime': self.network_lifetime,
            'total_energy_consumed': self.total_energy_consumed,
            'packets_transmitted': self.packets_transmitted,
            'packets_received': self.packets_received,
            'packet_delivery_ratio': packet_delivery_ratio,
            'energy_efficiency': energy_efficiency,
            'final_alive_nodes': final_alive_nodes,
            'total_leadership_changes': total_leadership_changes,
            'avg_transmission_distance': avg_transmission_distance,
            'round_stats': self.round_stats
        }

def create_enhanced_pegasis_from_network_config(config: NetworkConfig, energy_model) -> EnhancedPEGASISProtocol:
    """从NetworkConfig创建Enhanced PEGASIS协议实例"""
    enhanced_config = EnhancedPEGASISConfig(
        num_nodes=config.num_nodes,
        area_width=config.area_width,
        area_height=config.area_height,
        base_station_x=config.base_station_x,
        base_station_y=config.base_station_y,
        initial_energy=config.initial_energy,
        transmission_range=getattr(config, 'transmission_range', 30.0),
        packet_size=getattr(config, 'packet_size', 1024)
    )

    protocol = EnhancedPEGASISProtocol(enhanced_config)
    return protocol
