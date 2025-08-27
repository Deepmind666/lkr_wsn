#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PEGASIS (Power-Efficient Gathering in Sensor Information Systems) 协议实现
基于链式结构的WSN路由协议，用作EEHFR协议的对比基准

参考文献:
Lindsey, S., & Raghavendra, C. S. (2002). 
PEGASIS: Power-efficient gathering in sensor information systems. 
In Proceedings, IEEE aerospace conference (Vol. 3, pp. 3-1125).

项目路径: EEHFR：融合模糊逻辑与混合元启发式优化的WSN智能节能路由协议/EEHFR_Optimized_v1/
数据源: Intel Berkeley Research Lab数据集 (https://db.csail.mit.edu/labdata/labdata.html)
"""

import numpy as np
import math
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt

class PEGASISNode:
    """PEGASIS协议中的传感器节点"""
    
    def __init__(self, node_id: int, x: float, y: float, initial_energy: float = 2.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        self.is_alive = True
        self.is_leader = False
        
        # PEGASIS特定参数
        self.next_node = None
        self.prev_node = None
        self.chain_position = -1
        self.data_packets = []
        
    def distance_to(self, other_node) -> float:
        """计算到另一个节点的欧几里得距离"""
        return math.sqrt((self.x - other_node.x)**2 + (self.y - other_node.y)**2)
    
    def consume_energy(self, energy_amount: float):
        """消耗能量"""
        self.current_energy -= energy_amount
        if self.current_energy <= 0:
            self.current_energy = 0
            self.is_alive = False
    
    def reset_chain_info(self):
        """重置链信息"""
        self.next_node = None
        self.prev_node = None
        self.chain_position = -1
        self.is_leader = False

class PEGASISProtocol:
    """PEGASIS协议实现"""
    
    def __init__(self, nodes: List[PEGASISNode], base_station: Tuple[float, float]):
        """
        初始化PEGASIS协议
        
        参数:
            nodes: 传感器节点列表
            base_station: 基站坐标 (x, y)
        """
        self.nodes = nodes
        self.base_station = base_station
        self.current_round = 0
        self.chain = []
        self.leader_index = 0
        
        # 能量消耗模型参数 (与LEACH保持一致)
        self.E_elec = 50e-9  # 电子能耗 (J/bit)
        self.E_fs = 10e-12   # 自由空间模型 (J/bit/m²)
        self.E_mp = 0.0013e-12  # 多径衰落模型 (J/bit/m⁴)
        self.E_DA = 5e-9     # 数据聚合能耗 (J/bit/signal)
        self.d_crossover = 87  # 距离阈值 (m)
        self.packet_size = 4000  # 数据包大小 (bits)
        
        # 性能统计
        self.total_energy_consumed = 0.0
        self.packets_sent = 0
        self.packets_received = 0
        # 端到端统计（统一为源→BS口径）
        self.total_source_packets = 0
        self.total_bs_delivered = 0
        self.dead_nodes = 0
        self.network_lifetime = 0
        self.energy_consumption_per_round = []
        self.alive_nodes_per_round = []

        # 初始化链结构
        self.construct_chain()

        print(f"🔧 PEGASIS协议初始化完成")
        print(f"   节点数: {len(self.nodes)}")
        print(f"   基站位置: {self.base_station}")
        print(f"   链长度: {len(self.chain)}")
    
    def calculate_transmission_energy(self, distance: float, packet_size: int) -> float:
        """计算传输能耗"""
        if distance < self.d_crossover:
            return self.E_elec * packet_size + self.E_fs * packet_size * (distance ** 2)
        else:
            return self.E_elec * packet_size + self.E_mp * packet_size * (distance ** 4)
    
    def calculate_reception_energy(self, packet_size: int) -> float:
        """计算接收能耗"""
        return self.E_elec * packet_size
    
    def construct_chain(self):
        """构建贪心链结构"""
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return
        
        # 重置所有节点的链信息
        for node in alive_nodes:
            node.reset_chain_info()
        
        self.chain = []
        remaining_nodes = alive_nodes.copy()
        
        # 选择起始节点（距离基站最远的节点）
        max_distance = 0
        start_node = None
        for node in remaining_nodes:
            distance = math.sqrt((node.x - self.base_station[0])**2 + 
                               (node.y - self.base_station[1])**2)
            if distance > max_distance:
                max_distance = distance
                start_node = node
        
        if start_node is None:
            start_node = remaining_nodes[0]
        
        self.chain.append(start_node)
        remaining_nodes.remove(start_node)
        
        # 贪心算法构建链
        while remaining_nodes:
            last_node = self.chain[-1]
            min_distance = float('inf')
            closest_node = None
            
            for node in remaining_nodes:
                distance = last_node.distance_to(node)
                if distance < min_distance:
                    min_distance = distance
                    closest_node = node
            
            if closest_node:
                self.chain.append(closest_node)
                remaining_nodes.remove(closest_node)
            else:
                break
        
        # 设置链中节点的前后关系
        for i, node in enumerate(self.chain):
            node.chain_position = i
            if i > 0:
                node.prev_node = self.chain[i-1]
            if i < len(self.chain) - 1:
                node.next_node = self.chain[i+1]
    
    def select_leader(self) -> Optional[PEGASISNode]:
        """选择链首节点（轮转方式）"""
        alive_chain = [n for n in self.chain if n.is_alive]
        if not alive_chain:
            return None
        
        # 轮转选择领导者
        self.leader_index = self.current_round % len(alive_chain)
        leader = alive_chain[self.leader_index]
        leader.is_leader = True
        
        return leader
    
    def data_transmission_phase(self, leader: PEGASISNode):
        """数据传输阶段"""
        round_energy_consumption = 0.0
        
        # 1. 沿链传输数据到领导者
        # 从链的两端开始向领导者传输
        leader_pos = leader.chain_position
        
        # 处理领导者左侧的节点
        for i in range(leader_pos - 1, -1, -1):
            current_node = self.chain[i]
            if not current_node.is_alive:
                continue
            
            next_node = self.chain[i + 1]
            if not next_node.is_alive:
                # 寻找下一个存活的节点
                for j in range(i + 2, len(self.chain)):
                    if self.chain[j].is_alive:
                        next_node = self.chain[j]
                        break
                else:
                    continue
            
            # 传输数据
            distance = current_node.distance_to(next_node)
            tx_energy = self.calculate_transmission_energy(distance, self.packet_size)
            rx_energy = self.calculate_reception_energy(self.packet_size)
            
            current_node.consume_energy(tx_energy)
            next_node.consume_energy(rx_energy)
            
            round_energy_consumption += tx_energy + rx_energy
            self.packets_sent += 1
            if next_node.is_alive:
                self.packets_received += 1
        
        # 处理领导者右侧的节点
        for i in range(leader_pos + 1, len(self.chain)):
            current_node = self.chain[i]
            if not current_node.is_alive:
                continue
            
            prev_node = self.chain[i - 1]
            if not prev_node.is_alive:
                # 寻找前一个存活的节点
                for j in range(i - 2, -1, -1):
                    if self.chain[j].is_alive:
                        prev_node = self.chain[j]
                        break
                else:
                    continue
            
            # 传输数据
            distance = current_node.distance_to(prev_node)
            tx_energy = self.calculate_transmission_energy(distance, self.packet_size)
            rx_energy = self.calculate_reception_energy(self.packet_size)
            
            current_node.consume_energy(tx_energy)
            prev_node.consume_energy(rx_energy)
            
            round_energy_consumption += tx_energy + rx_energy
            self.packets_sent += 1
            if prev_node.is_alive:
                self.packets_received += 1
        
        # 2. 数据聚合
        if leader.is_alive:
            alive_count = len([n for n in self.chain if n.is_alive])
            aggregation_energy = self.E_DA * self.packet_size * alive_count
            leader.consume_energy(aggregation_energy)
            round_energy_consumption += aggregation_energy

        # 3. 领导者向基站传输聚合数据（计入端到端送达）
        if leader.is_alive:
            bs_distance = math.sqrt((leader.x - self.base_station[0])**2 +
                                  (leader.y - self.base_station[1])**2)
            tx_energy = self.calculate_transmission_energy(bs_distance, self.packet_size)
            leader.consume_energy(tx_energy)
            round_energy_consumption += tx_energy

            self.packets_sent += 1
            # 统一端到端口径：领导者聚合后的上行视为将 alive_count 条源包送达BS
            self.total_bs_delivered += alive_count
            self.total_source_packets += alive_count

        self.total_energy_consumed += round_energy_consumption
        self.energy_consumption_per_round.append(round_energy_consumption)
    
    def run_round(self) -> bool:
        """运行一轮PEGASIS协议"""
        # 检查网络是否还有存活节点
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return False
        
        self.current_round += 1
        
        # 1. 重构链（如果有节点死亡）
        current_alive = len(alive_nodes)
        if current_alive != len([n for n in self.chain if n.is_alive]):
            self.construct_chain()
        
        # 2. 选择领导者
        leader = self.select_leader()
        if not leader:
            return False
        
        # 3. 数据传输阶段
        self.data_transmission_phase(leader)
        
        # 4. 更新统计信息
        current_dead = len(self.nodes) - current_alive
        
        if current_dead > self.dead_nodes:
            self.dead_nodes = current_dead
            if self.network_lifetime == 0 and current_dead > 0:
                self.network_lifetime = self.current_round
        
        self.alive_nodes_per_round.append(current_alive)
        
        return True
    
    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """运行完整的PEGASIS仿真"""
        print(f"🚀 开始PEGASIS协议仿真 (最大轮数: {max_rounds})")
        
        for round_num in range(max_rounds):
            success = self.run_round()
            
            if not success:
                print(f"⚠️ 网络生命周期结束于第 {round_num} 轮")
                break
            
            # 每100轮输出一次状态
            if round_num % 100 == 0:
                alive_count = len([n for n in self.nodes if n.is_alive])
                print(f"   第{round_num}轮: 存活节点={alive_count}, "
                      f"总能耗={self.total_energy_consumed:.3f}J")
        
        # 返回性能结果
        results = {
            'protocol_name': 'PEGASIS',
            'total_rounds': self.current_round,
            'network_lifetime': self.network_lifetime if self.network_lifetime > 0 else self.current_round,
            'total_energy_consumed': self.total_energy_consumed,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'packet_delivery_ratio': self.packets_received / max(self.packets_sent, 1),
                'packet_delivery_ratio_end2end': self.total_bs_delivered / max(self.total_source_packets, 1),
                'bs_delivered': self.total_bs_delivered,
                'source_packets': self.total_source_packets,
            'dead_nodes': self.dead_nodes,
            'alive_nodes': len(self.nodes) - self.dead_nodes,
            'energy_consumption_per_round': self.energy_consumption_per_round,
            'alive_nodes_per_round': self.alive_nodes_per_round,
            'average_energy_per_round': self.total_energy_consumed / max(self.current_round, 1)
        }
        
        print(f"✅ PEGASIS仿真完成")
        print(f"   网络生存时间: {results['network_lifetime']} 轮")
        print(f"   总能耗: {results['total_energy_consumed']:.3f} J")
        print(f"   数据传输成功率: {results['packet_delivery_ratio']*100:.1f}%")
        
        return results
