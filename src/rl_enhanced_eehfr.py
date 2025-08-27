#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强化学习增强的Enhanced EEHFR协议 (RL-Enhanced EEHFR)

基于Q-Learning的自适应路由决策：
1. 智能下一跳选择
2. 自适应环境学习
3. 多目标奖励函数优化
4. 分布式学习机制

基于2024年顶级期刊ML+WSN研究成果
作者: Enhanced EEHFR Research Team
日期: 2025-01-31
版本: 1.0 (Machine Learning Integration)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import math
import random
import copy
import time
import pickle
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from collections import defaultdict, deque

# 导入基础组件
from benchmark_protocols import Node, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

@dataclass
class RLNode(Node):
    """强化学习节点类"""
    
    # RL相关属性
    q_table: Dict = None
    state_history: List = None
    action_history: List = None
    reward_history: List = None
    
    # 学习参数
    learning_rate: float = 0.1
    discount_factor: float = 0.9
    epsilon: float = 0.1
    epsilon_decay: float = 0.995
    min_epsilon: float = 0.01
    
    # 性能统计
    successful_transmissions: int = 0
    failed_transmissions: int = 0
    total_energy_consumed: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        if self.q_table is None:
            self.q_table = defaultdict(lambda: defaultdict(float))
        if self.state_history is None:
            self.state_history = deque(maxlen=100)
        if self.action_history is None:
            self.action_history = deque(maxlen=100)
        if self.reward_history is None:
            self.reward_history = deque(maxlen=100)

class QLearningAgent:
    """Q-Learning智能体"""
    
    def __init__(self, node_id: int, learning_rate: float = 0.1, 
                 discount_factor: float = 0.9, epsilon: float = 0.1):
        self.node_id = node_id
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = 0.995
        self.min_epsilon = 0.01
        
        # Q表：状态 -> 动作 -> Q值
        self.q_table = defaultdict(lambda: defaultdict(float))
        
        # 经验回放
        self.experience_buffer = deque(maxlen=1000)
        
        # 学习统计
        self.learning_episodes = 0
        self.total_reward = 0.0
        
    def discretize_state(self, state_features: Tuple[float, ...]) -> Tuple[int, ...]:
        """将连续状态离散化"""
        discretized = []
        
        for feature in state_features:
            # 将[0,1]范围的特征离散化为10个区间
            discrete_value = min(9, int(feature * 10))
            discretized.append(discrete_value)
        
        return tuple(discretized)
    
    def get_q_value(self, state: Tuple, action: int) -> float:
        """获取Q值"""
        discrete_state = self.discretize_state(state)
        return self.q_table[discrete_state][action]
    
    def select_action(self, state: Tuple, available_actions: List[int]) -> int:
        """选择动作（ε-贪婪策略）"""
        if not available_actions:
            return -1
        
        if random.random() < self.epsilon:
            # 探索：随机选择
            return random.choice(available_actions)
        else:
            # 利用：选择Q值最高的动作
            q_values = [self.get_q_value(state, action) for action in available_actions]
            max_q = max(q_values)
            
            # 如果有多个最优动作，随机选择一个
            best_actions = [action for action, q in zip(available_actions, q_values) if q == max_q]
            return random.choice(best_actions)
    
    def update_q_value(self, state: Tuple, action: int, reward: float, 
                      next_state: Tuple, next_available_actions: List[int]):
        """更新Q值"""
        discrete_state = self.discretize_state(state)
        discrete_next_state = self.discretize_state(next_state)
        
        # 当前Q值
        current_q = self.q_table[discrete_state][action]
        
        # 下一状态的最大Q值
        if next_available_actions:
            max_next_q = max([self.q_table[discrete_next_state][a] for a in next_available_actions])
        else:
            max_next_q = 0.0
        
        # Q-Learning更新公式
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[discrete_state][action] = new_q
        
        # 更新统计信息
        self.total_reward += reward
        self.learning_episodes += 1
        
        # ε衰减
        if self.epsilon > self.min_epsilon:
            self.epsilon *= self.epsilon_decay
    
    def add_experience(self, state: Tuple, action: int, reward: float, 
                      next_state: Tuple, done: bool):
        """添加经验到回放缓冲区"""
        experience = (state, action, reward, next_state, done)
        self.experience_buffer.append(experience)
    
    def get_learning_stats(self) -> Dict[str, float]:
        """获取学习统计信息"""
        return {
            'total_episodes': self.learning_episodes,
            'average_reward': self.total_reward / max(1, self.learning_episodes),
            'current_epsilon': self.epsilon,
            'q_table_size': len(self.q_table)
        }

class StateExtractor:
    """状态特征提取器"""
    
    def __init__(self):
        self.feature_names = [
            'normalized_energy',    # 归一化剩余能量
            'distance_to_bs',      # 到基站的归一化距离
            'neighbor_density',    # 邻居密度
            'environment_factor',  # 环境因子
            'load_factor'         # 负载因子
        ]
    
    def extract_state(self, node: RLNode, network_info: Dict) -> Tuple[float, ...]:
        """提取节点状态特征"""
        
        # 1. 归一化剩余能量
        normalized_energy = node.current_energy / node.initial_energy
        
        # 2. 到基站的归一化距离
        bs_distance = math.sqrt(
            (node.x - network_info['bs_x'])**2 + 
            (node.y - network_info['bs_y'])**2
        )
        max_distance = network_info['max_distance']
        distance_to_bs = bs_distance / max_distance
        
        # 3. 邻居密度
        neighbor_count = len([n for n in network_info['all_nodes'] 
                            if n.id != node.id and n.is_alive and 
                            math.sqrt((n.x - node.x)**2 + (n.y - node.y)**2) <= 30])
        max_neighbors = network_info['max_neighbors']
        neighbor_density = neighbor_count / max_neighbors if max_neighbors > 0 else 0
        
        # 4. 环境因子（基于环境类型）
        environment_types = ['indoor', 'outdoor_open', 'outdoor_obstructed', 
                           'industrial', 'urban', 'forest']
        env_type = getattr(node, 'environment_type', 'outdoor_open')
        environment_factor = environment_types.index(env_type) / len(environment_types)
        
        # 5. 负载因子
        load_factor = min(1.0, getattr(node, 'data_load', 0) / 10.0)
        
        state = (
            normalized_energy,
            distance_to_bs,
            neighbor_density,
            environment_factor,
            load_factor
        )
        
        return state

class RewardCalculator:
    """奖励函数计算器"""
    
    def __init__(self, energy_weight: float = 0.4, success_weight: float = 0.4, 
                 delay_weight: float = 0.2):
        self.energy_weight = energy_weight
        self.success_weight = success_weight
        self.delay_weight = delay_weight
    
    def calculate_reward(self, transmission_result: Dict) -> float:
        """计算多目标奖励函数"""
        
        # 1. 能耗奖励（负奖励，鼓励低能耗）
        energy_consumed = transmission_result.get('energy_consumed', 0)
        energy_reward = -energy_consumed * 1000  # 转换为mJ
        
        # 2. 成功奖励
        success = transmission_result.get('success', False)
        success_reward = 10.0 if success else -10.0
        
        # 3. 延迟奖励（负奖励，鼓励低延迟）
        delay = transmission_result.get('delay', 0)
        delay_reward = -delay * 0.1
        
        # 4. 网络生存时间奖励
        network_lifetime_bonus = transmission_result.get('lifetime_bonus', 0)
        
        # 加权组合
        total_reward = (
            self.energy_weight * energy_reward +
            self.success_weight * success_reward +
            self.delay_weight * delay_reward +
            network_lifetime_bonus
        )
        
        return total_reward

class RLEnhancedEEHFRProtocol:
    """强化学习增强的Enhanced EEHFR协议"""
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        
        # 初始化组件
        self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        self.state_extractor = StateExtractor()
        self.reward_calculator = RewardCalculator()
        
        # 网络状态
        self.nodes: List[RLNode] = []
        self.rl_agents: Dict[int, QLearningAgent] = {}
        self.current_round = 0
        
        # 统计信息
        self.round_statistics = []
        self.total_energy_consumed = 0.0
        self.total_packets_sent = 0
        self.total_packets_received = 0
        
        # 学习参数
        self.learning_enabled = True
        self.exploration_rounds = 100  # 前100轮主要用于探索
        
        # 初始化网络
        self._initialize_network()
    
    def _initialize_network(self):
        """初始化网络节点和RL智能体"""
        
        self.nodes = []
        self.rl_agents = {}
        
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            
            node = RLNode(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy,
                is_alive=True,
                is_cluster_head=False,
                cluster_id=-1
            )
            self.nodes.append(node)
            
            # 为每个节点创建RL智能体
            self.rl_agents[i] = QLearningAgent(
                node_id=i,
                learning_rate=0.1,
                discount_factor=0.9,
                epsilon=0.3 if self.current_round < self.exploration_rounds else 0.1
            )
        
        # 初始簇头选择
        self._select_cluster_heads()
        self._form_clusters()
    
    def _get_network_info(self) -> Dict:
        """获取网络信息"""
        max_distance = math.sqrt(self.config.area_width**2 + self.config.area_height**2)
        max_neighbors = len(self.nodes) - 1
        
        return {
            'bs_x': self.config.base_station_x,
            'bs_y': self.config.base_station_y,
            'max_distance': max_distance,
            'max_neighbors': max_neighbors,
            'all_nodes': self.nodes
        }
    
    def _select_cluster_heads(self):
        """使用RL选择簇头"""
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if len(alive_nodes) < 2:
            return
        
        target_ch_count = max(1, int(len(alive_nodes) * 0.1))
        network_info = self._get_network_info()
        
        # 重置簇头状态
        for node in alive_nodes:
            node.is_cluster_head = False
            node.cluster_id = -1
        
        # 为每个节点计算成为簇头的Q值
        ch_candidates = []
        
        for node in alive_nodes:
            state = self.state_extractor.extract_state(node, network_info)
            agent = self.rl_agents[node.id]
            
            # 动作：成为簇头(1) 或 不成为簇头(0)
            q_ch = agent.get_q_value(state, 1)  # 成为簇头的Q值
            q_member = agent.get_q_value(state, 0)  # 成为成员的Q值
            
            # 簇头倾向性得分
            ch_preference = q_ch - q_member + node.current_energy / node.initial_energy
            ch_candidates.append((node, ch_preference))
        
        # 选择得分最高的节点作为簇头
        ch_candidates.sort(key=lambda x: x[1], reverse=True)
        selected_chs = [candidate[0] for candidate in ch_candidates[:target_ch_count]]
        
        # 设置簇头状态
        for i, ch in enumerate(selected_chs):
            ch.is_cluster_head = True
            ch.cluster_id = i
    
    def _form_clusters(self):
        """形成簇结构"""
        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]
        member_nodes = [node for node in self.nodes if not node.is_cluster_head and node.is_alive]
        
        # 为每个成员节点分配最近的簇头
        for member in member_nodes:
            if not cluster_heads:
                continue
            
            min_distance = float('inf')
            best_cluster_head = None
            
            for ch in cluster_heads:
                distance = math.sqrt((member.x - ch.x)**2 + (member.y - ch.y)**2)
                if distance < min_distance:
                    min_distance = distance
                    best_cluster_head = ch
            
            if best_cluster_head:
                member.cluster_id = best_cluster_head.cluster_id
    
    def _rl_next_hop_selection(self, sender: RLNode, candidates: List[RLNode]) -> Optional[RLNode]:
        """使用RL选择下一跳节点"""
        if not candidates:
            return None
        
        network_info = self._get_network_info()
        state = self.state_extractor.extract_state(sender, network_info)
        agent = self.rl_agents[sender.id]
        
        # 可用动作：候选节点的ID
        available_actions = [node.id for node in candidates]
        
        # 使用RL智能体选择动作
        selected_action = agent.select_action(state, available_actions)
        
        # 找到对应的节点
        selected_node = next((node for node in candidates if node.id == selected_action), None)
        
        # 记录状态和动作
        sender.state_history.append(state)
        sender.action_history.append(selected_action)
        
        return selected_node
    
    def _execute_transmission(self, sender: RLNode, receiver: RLNode) -> Dict:
        """执行传输并返回结果"""
        if not sender.is_alive or not receiver.is_alive:
            return {'success': False, 'energy_consumed': 0, 'delay': 0}
        
        # 计算传输距离
        distance = math.sqrt((sender.x - receiver.x)**2 + (sender.y - receiver.y)**2)
        
        # 自适应功率控制
        if distance < 20:
            tx_power = -5.0  # -5 dBm
        elif distance < 50:
            tx_power = 0.0   # 0 dBm
        else:
            tx_power = 5.0   # 5 dBm
        
        # 计算能耗
        tx_energy = self.energy_model.calculate_transmission_energy(
            self.config.packet_size * 8, distance, tx_power
        )
        rx_energy = self.energy_model.calculate_reception_energy(self.config.packet_size * 8)
        
        # 更新能量
        sender.current_energy -= tx_energy
        receiver.current_energy -= rx_energy
        
        # 更新统计
        sender.total_energy_consumed += tx_energy
        receiver.total_energy_consumed += rx_energy
        
        # 检查节点状态
        if sender.current_energy <= 0:
            sender.is_alive = False
            sender.current_energy = 0
        if receiver.current_energy <= 0:
            receiver.is_alive = False
            receiver.current_energy = 0
        
        # 计算成功率（简化模型）
        success_rate = 0.95 - (distance / 100) * 0.1  # 距离越远成功率越低
        success = random.random() < success_rate
        
        # 计算延迟（简化模型）
        delay = distance * 0.001 + random.uniform(0, 0.01)
        
        return {
            'success': success,
            'energy_consumed': tx_energy + rx_energy,
            'delay': delay,
            'distance': distance
        }
    
    def _update_rl_agents(self, transmission_results: List[Dict]):
        """更新RL智能体"""
        if not self.learning_enabled:
            return
        
        network_info = self._get_network_info()
        
        for result in transmission_results:
            sender_id = result['sender_id']
            sender = next((node for node in self.nodes if node.id == sender_id), None)
            
            if not sender or len(sender.state_history) < 2:
                continue
            
            # 获取状态和动作
            prev_state = sender.state_history[-2]
            action = sender.action_history[-1]
            current_state = self.state_extractor.extract_state(sender, network_info)
            
            # 计算奖励
            reward = self.reward_calculator.calculate_reward(result)
            sender.reward_history.append(reward)
            
            # 获取当前可用动作
            alive_neighbors = [node for node in self.nodes 
                             if node.is_alive and node.id != sender.id]
            available_actions = [node.id for node in alive_neighbors]
            
            # 更新Q值
            agent = self.rl_agents[sender_id]
            agent.update_q_value(prev_state, action, reward, current_state, available_actions)
            
            # 更新成功/失败统计
            if result['success']:
                sender.successful_transmissions += 1
            else:
                sender.failed_transmissions += 1
    
    def _data_collection_phase(self) -> List[Dict]:
        """数据收集阶段"""
        transmission_results = []
        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]
        
        for ch in cluster_heads:
            cluster_members = [node for node in self.nodes 
                             if node.cluster_id == ch.cluster_id and not node.is_cluster_head and node.is_alive]
            
            for member in cluster_members:
                if member.current_energy > 0:
                    # 使用RL选择传输策略
                    candidates = [ch]  # 簇内传输只能选择簇头
                    selected_receiver = self._rl_next_hop_selection(member, candidates)
                    
                    if selected_receiver:
                        result = self._execute_transmission(member, selected_receiver)
                        result['sender_id'] = member.id
                        result['receiver_id'] = selected_receiver.id
                        result['phase'] = 'data_collection'
                        transmission_results.append(result)
        
        return transmission_results
    
    def _data_forwarding_phase(self) -> List[Dict]:
        """数据转发阶段"""
        transmission_results = []
        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]
        
        for ch in cluster_heads:
            if ch.current_energy > 0:
                # 簇头向基站发送数据
                # 这里简化为直接传输，实际可以使用RL选择中继节点
                bs_distance = math.sqrt(
                    (ch.x - self.config.base_station_x)**2 + 
                    (ch.y - self.config.base_station_y)**2
                )
                
                # 计算传输能耗
                tx_energy = self.energy_model.calculate_transmission_energy(
                    self.config.packet_size * 8, bs_distance, 0.0
                )
                
                ch.current_energy -= tx_energy
                ch.total_energy_consumed += tx_energy
                
                if ch.current_energy <= 0:
                    ch.is_alive = False
                    ch.current_energy = 0
                
                # 基站传输成功率较高
                success = random.random() < 0.98
                delay = bs_distance * 0.001
                
                result = {
                    'sender_id': ch.id,
                    'receiver_id': -1,  # 基站
                    'success': success,
                    'energy_consumed': tx_energy,
                    'delay': delay,
                    'distance': bs_distance,
                    'phase': 'data_forwarding'
                }
                transmission_results.append(result)
        
        return transmission_results
    
    def _collect_round_statistics(self, round_num: int, transmission_results: List[Dict]):
        """收集轮次统计信息"""
        alive_nodes = sum(1 for node in self.nodes if node.is_alive)
        cluster_heads = sum(1 for node in self.nodes if node.is_cluster_head and node.is_alive)
        remaining_energy = sum(node.current_energy for node in self.nodes if node.is_alive)
        
        # 统计传输结果
        packets_sent = len(transmission_results)
        packets_received = sum(1 for result in transmission_results if result['success'])
        round_energy_consumed = sum(result['energy_consumed'] for result in transmission_results)
        
        # RL学习统计
        total_reward = sum(sum(node.reward_history) for node in self.nodes if node.reward_history)
        avg_epsilon = sum(agent.epsilon for agent in self.rl_agents.values()) / len(self.rl_agents)
        
        round_stats = {
            'round': round_num,
            'alive_nodes': alive_nodes,
            'cluster_heads': cluster_heads,
            'remaining_energy': remaining_energy,
            'packets_sent': packets_sent,
            'packets_received': packets_received,
            'energy_consumed': round_energy_consumed,
            'pdr': packets_received / packets_sent if packets_sent > 0 else 0,
            # RL特定指标
            'total_reward': total_reward,
            'average_epsilon': avg_epsilon,
            'learning_enabled': self.learning_enabled
        }
        
        self.round_statistics.append(round_stats)
    
    def run_simulation(self, max_rounds: int) -> Dict[str, Any]:
        """运行RL增强的EEHFR仿真"""
        
        print(f"🤖 开始强化学习增强的Enhanced EEHFR协议仿真")
        print(f"   节点数量: {len(self.nodes)}")
        print(f"   最大轮数: {max_rounds}")
        print(f"   探索轮数: {self.exploration_rounds}")
        
        start_time = time.time()
        
        for round_num in range(max_rounds):
            self.current_round = round_num
            
            # 检查是否还有存活节点
            alive_nodes = [node for node in self.nodes if node.is_alive]
            if len(alive_nodes) < 2:
                print(f"💀 网络在第 {round_num} 轮结束生命周期")
                break
            
            # 定期重新选择簇头
            if round_num % 20 == 0:
                self._select_cluster_heads()
                self._form_clusters()
            
            # 调整学习参数
            if round_num == self.exploration_rounds:
                print(f"🎯 第 {round_num} 轮：切换到利用模式")
                for agent in self.rl_agents.values():
                    agent.epsilon = 0.1
            
            # 执行数据收集阶段
            collection_results = self._data_collection_phase()
            
            # 执行数据转发阶段
            forwarding_results = self._data_forwarding_phase()
            
            # 合并传输结果
            all_results = collection_results + forwarding_results
            
            # 更新RL智能体
            self._update_rl_agents(all_results)
            
            # 收集统计信息
            self._collect_round_statistics(round_num, all_results)
            
            # 更新总统计
            self.total_packets_sent += len(all_results)
            self.total_packets_received += sum(1 for r in all_results if r['success'])
            self.total_energy_consumed += sum(r['energy_consumed'] for r in all_results)
            
            # 定期输出进度
            if round_num % 50 == 0:
                avg_reward = sum(sum(node.reward_history) for node in self.nodes if node.reward_history) / len(alive_nodes)
                print(f"   轮数 {round_num}: 存活节点 {len(alive_nodes)}, 平均奖励 {avg_reward:.2f}")
        
        execution_time = time.time() - start_time
        
        # 生成最终结果
        return self._generate_final_results(execution_time)
    
    def _generate_final_results(self, execution_time: float) -> Dict[str, Any]:
        """生成最终结果"""
        
        final_alive_nodes = sum(1 for node in self.nodes if node.is_alive)
        network_lifetime = len(self.round_statistics)
        
        if self.total_energy_consumed > 0:
            energy_efficiency = self.total_packets_received / self.total_energy_consumed
        else:
            energy_efficiency = 0
        
        if self.total_packets_sent > 0:
            packet_delivery_ratio = self.total_packets_received / self.total_packets_sent
        else:
            packet_delivery_ratio = 0
        
        # RL学习统计
        total_successful = sum(node.successful_transmissions for node in self.nodes)
        total_failed = sum(node.failed_transmissions for node in self.nodes)
        success_rate = total_successful / (total_successful + total_failed) if (total_successful + total_failed) > 0 else 0
        
        # 智能体学习统计
        agent_stats = {}
        for node_id, agent in self.rl_agents.items():
            agent_stats[node_id] = agent.get_learning_stats()
        
        print(f"✅ RL增强仿真完成，网络在 {network_lifetime} 轮后结束")
        print(f"   学习成功率: {success_rate:.3f}")
        print(f"   平均Q表大小: {np.mean([stats['q_table_size'] for stats in agent_stats.values()]):.1f}")
        
        return {
            'protocol': 'RL_Enhanced_EEHFR',
            'network_lifetime': network_lifetime,
            'total_energy_consumed': self.total_energy_consumed,
            'final_alive_nodes': final_alive_nodes,
            'energy_efficiency': energy_efficiency,
            'packet_delivery_ratio': packet_delivery_ratio,
            'execution_time': execution_time,
            'round_statistics': self.round_statistics,
            'config': {
                'num_nodes': len(self.nodes),
                'initial_energy': self.config.initial_energy,
                'area_size': f"{self.config.area_width}x{self.config.area_height}",
                'packet_size': self.config.packet_size,
                'exploration_rounds': self.exploration_rounds
            },
            'rl_metrics': {
                'learning_success_rate': success_rate,
                'agent_statistics': agent_stats,
                'total_successful_transmissions': total_successful,
                'total_failed_transmissions': total_failed,
                'average_q_table_size': np.mean([stats['q_table_size'] for stats in agent_stats.values()]),
                'final_epsilon': np.mean([agent.epsilon for agent in self.rl_agents.values()])
            },
            'additional_metrics': {
                'total_packets_sent': self.total_packets_sent,
                'total_packets_received': self.total_packets_received,
                'average_cluster_heads': sum(stats['cluster_heads'] for stats in self.round_statistics) / len(self.round_statistics) if self.round_statistics else 0
            }
        }


# 测试函数
def test_rl_enhanced_eehfr():
    """测试强化学习增强的EEHFR协议"""
    
    print("🤖 测试强化学习增强的Enhanced EEHFR协议")
    print("=" * 70)
    
    # 网络配置
    config = NetworkConfig(
        num_nodes=50,
        area_width=100,
        area_height=100,
        initial_energy=2.0,
        base_station_x=50,
        base_station_y=50,
        packet_size=512
    )
    
    # 创建协议实例
    protocol = RLEnhancedEEHFRProtocol(config)
    
    # 运行仿真
    result = protocol.run_simulation(200)
    
    # 输出结果
    print(f"\n📊 测试结果:")
    print(f"   网络生存时间: {result['network_lifetime']} 轮")
    print(f"   总能耗: {result['total_energy_consumed']:.3f} J")
    print(f"   能效: {result['energy_efficiency']:.1f} packets/J")
    print(f"   数据包投递率: {result['packet_delivery_ratio']:.3f}")
    print(f"   学习成功率: {result['rl_metrics']['learning_success_rate']:.3f}")
    print(f"   平均Q表大小: {result['rl_metrics']['average_q_table_size']:.1f}")
    print(f"   最终ε值: {result['rl_metrics']['final_epsilon']:.3f}")
    
    return result


if __name__ == "__main__":
    test_rl_enhanced_eehfr()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强化学习增强的Enhanced EEHFR协议 (RL-Enhanced EEHFR)

基于Q-Learning的自适应路由决策：
1. 智能下一跳选择
2. 自适应环境学习
3. 多目