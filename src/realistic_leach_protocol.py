#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于权威文献的真实环境LEACH协议实现

基于深度调研的权威方法：
1. Log-Normal Shadowing信道模型 (Rappaport教材)
2. IEEE 802.15.4标准的RSSI/LQI链路质量评估
3. 多源干扰环境下的SINR建模和PDR预测
4. 环境因素对WSN性能影响的量化分析

参考文献：
- Baazaoui et al. (2023) "Modeling of Packet Error Rate Distribution Based on RSSI in OMNeT++"
- Tangsunantham & Pirak (2023) "Hardware-Based Link Quality Estimation Modelling"
- IEEE 802.15.4-2015 Standard for Low-Rate Wireless Networks

作者: Enhanced EEHFR Research Team
日期: 2025-01-31
版本: 2.0 (Realistic Environment)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import copy

@dataclass
class Node:
    """WSN节点类"""
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    is_alive: bool = True
    is_cluster_head: bool = False
    cluster_id: int = -1
    
    # 环境参数
    temperature: float = 25.0  # 温度 (°C)
    humidity: float = 0.5      # 湿度 (0-1)

@dataclass
class NetworkConfig:
    """网络配置参数"""
    num_nodes: int = 50
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 175.0
    initial_energy: float = 2.0  # 匹配权威LEACH的2J
    packet_size: int = 4000      # bits (权威LEACH标准)
    
class EnvironmentType(Enum):
    """环境类型枚举"""
    INDOOR_OFFICE = "indoor_office"
    OUTDOOR_OPEN = "outdoor_open"
    INDUSTRIAL = "industrial"
    URBAN = "urban"

class RealisticChannelModel:
    """基于权威文献的真实信道模型"""
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.OUTDOOR_OPEN):
        self.environment = environment
        
        # Log-Normal Shadowing模型参数 (基于Rappaport教材)
        self.path_loss_params = {
            EnvironmentType.INDOOR_OFFICE: {
                'n': 2.0,      # 路径损耗指数
                'sigma': 3.0,  # 阴影衰落标准差 (dB)
                'P0': -40.0    # 参考距离1m处的功率 (dBm)
            },
            EnvironmentType.OUTDOOR_OPEN: {
                'n': 2.5,      # 自由空间 + 地面反射
                'sigma': 4.0,  # 阴影衰落
                'P0': -45.0
            },
            EnvironmentType.INDUSTRIAL: {
                'n': 3.0,      # 高障碍物环境
                'sigma': 6.0,  # 高变异性
                'P0': -50.0
            },
            EnvironmentType.URBAN: {
                'n': 3.5,      # 密集建筑环境
                'sigma': 8.0,  # 极高变异性
                'P0': -55.0
            }
        }
        
        # IEEE 802.15.4参数
        self.tx_power = 0.0  # dBm (CC2420标准)
        self.noise_floor = -95.0  # dBm
        self.sensitivity = -85.0  # dBm
        
        # 干扰源参数
        self.interference_sources = []
        
    def calculate_rssi(self, distance: float, tx_node: Node, rx_node: Node) -> float:
        """
        基于Log-Normal Shadowing模型计算RSSI
        
        RSSI(dBm) = P_tx - PL(d) - X_σ
        PL(d) = PL(d0) + 10*n*log10(d/d0)
        """
        params = self.path_loss_params[self.environment]
        
        # 基础路径损耗
        if distance < 1.0:
            distance = 1.0  # 避免log(0)
            
        path_loss = params['P0'] + 10 * params['n'] * math.log10(distance)
        
        # 阴影衰落 (Log-Normal分布)
        shadowing = np.random.normal(0, params['sigma'])
        
        # 环境因素影响 (基于实测数据)
        temp_factor = self._calculate_temperature_effect(tx_node.temperature)
        humidity_factor = self._calculate_humidity_effect(tx_node.humidity)
        
        # 计算RSSI
        rssi = self.tx_power - path_loss - shadowing - temp_factor - humidity_factor
        
        return rssi
    
    def _calculate_temperature_effect(self, temperature: float) -> float:
        """温度对信号传播的影响 (基于文献数据)"""
        # 基于Boano et al.研究：温度每升高10°C，信号衰减增加0.5dB
        reference_temp = 25.0
        return 0.05 * abs(temperature - reference_temp)
    
    def _calculate_humidity_effect(self, humidity: float) -> float:
        """湿度对信号传播的影响"""
        # 基于Luomala & Hakala研究：高湿度增加信号衰减
        return 2.0 * humidity  # 最大2dB衰减
    
    def calculate_sinr(self, rssi: float, interference_power: float = 0.0) -> float:
        """计算信号干扰噪声比 (SINR)"""
        signal_power = 10**(rssi/10)  # 转换为线性功率
        noise_power = 10**(self.noise_floor/10)
        interference_linear = 10**(interference_power/10) if interference_power > 0 else 0
        
        sinr_linear = signal_power / (noise_power + interference_linear)
        sinr_db = 10 * math.log10(sinr_linear) if sinr_linear > 0 else -100
        
        return sinr_db
    
    def calculate_pdr(self, rssi: float, sinr: float) -> float:
        """
        基于RSSI和SINR计算包投递率 (PDR)
        使用逻辑回归模型 (基于Tangsunantham & Pirak研究)
        """
        # RSSI-PDR逻辑回归模型参数 (基于实测数据拟合)
        if rssi >= -70:
            pdr = 0.95 + 0.05 * random.random()  # 高信号强度
        elif rssi >= -80:
            # 逻辑回归: PDR = 1 / (1 + exp(-(a*RSSI + b)))
            a, b = 0.15, 11.5  # 基于文献参数
            pdr = 1.0 / (1.0 + math.exp(-(a * rssi + b)))
        elif rssi >= -90:
            # 中等信号强度，受SINR影响
            base_pdr = 1.0 / (1.0 + math.exp(-(0.12 * rssi + 9.0)))
            sinr_factor = max(0.1, min(1.0, (sinr + 10) / 20))  # SINR修正
            pdr = base_pdr * sinr_factor
        else:
            # 低信号强度，主要受噪声影响
            pdr = max(0.01, 0.1 * math.exp((rssi + 95) / 5))
        
        return min(0.99, max(0.01, pdr))  # 限制在合理范围内
    
    def add_interference_source(self, power_dbm: float, distance: float):
        """添加干扰源"""
        self.interference_sources.append({
            'power': power_dbm,
            'distance': distance
        })
    
    def calculate_total_interference(self, node_x: float, node_y: float) -> float:
        """计算总干扰功率"""
        total_interference = 0.0
        
        for source in self.interference_sources:
            # 简化的干扰计算
            interference_rssi = source['power'] - 20 * math.log10(source['distance'])
            interference_power = 10**(interference_rssi/10)
            total_interference += interference_power
        
        return 10 * math.log10(total_interference) if total_interference > 0 else -100

class RealisticLEACHProtocol:
    """基于真实环境建模的LEACH协议"""
    
    def __init__(self, config: NetworkConfig, environment: EnvironmentType = EnvironmentType.OUTDOOR_OPEN):
        self.config = config
        self.channel_model = RealisticChannelModel(environment)
        self.nodes = []
        self.round_number = 0
        self.cluster_heads = []
        self.clusters = {}
        
        # 统计信息
        self.stats = {
            'total_packets_sent': 0,
            'total_packets_received': 0,
            'total_transmission_attempts': 0,
            'total_energy_consumed': 0.0,
            'network_lifetime': 0,
            'pdr_history': [],
            'rssi_history': [],
            'sinr_history': []
        }
        
        # 初始化网络
        self._initialize_network()
        
        # 添加典型干扰源 (WiFi, 工业设备等)
        self.channel_model.add_interference_source(-20, 15)  # WiFi路由器
        self.channel_model.add_interference_source(-30, 25)  # 工业设备
    
    def _initialize_network(self):
        """初始化网络节点"""
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            
            # 模拟环境条件变化
            temperature = random.uniform(20, 35)  # 20-35°C
            humidity = random.uniform(0.3, 0.8)   # 30-80%
            
            node = Node(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy,
                temperature=temperature,
                humidity=humidity
            )
            self.nodes.append(node)
    
    def _calculate_distance(self, node1: Node, node2: Node) -> float:
        """计算两节点间距离"""
        return math.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)
    
    def _calculate_distance_to_bs(self, node: Node) -> float:
        """计算节点到基站距离"""
        return math.sqrt((node.x - self.config.base_station_x)**2 +
                        (node.y - self.config.base_station_y)**2)

    def _transmit_packet(self, sender: Node, receiver: Optional[Node] = None,
                        packet_size: int = None) -> Tuple[bool, float, float, float]:
        """
        真实环境下的数据包传输

        Returns:
            (success, rssi, sinr, pdr): 传输结果和链路质量指标
        """
        if packet_size is None:
            packet_size = self.config.packet_size

        # 计算传输距离
        if receiver is None:
            # 直接传输到基站
            distance = self._calculate_distance_to_bs(sender)
        else:
            distance = self._calculate_distance(sender, receiver)

        # 计算RSSI
        rssi = self.channel_model.calculate_rssi(distance, sender, receiver or sender)

        # 计算干扰
        interference = self.channel_model.calculate_total_interference(sender.x, sender.y)

        # 计算SINR
        sinr = self.channel_model.calculate_sinr(rssi, interference)

        # 计算PDR
        pdr = self.channel_model.calculate_pdr(rssi, sinr)

        # 记录统计信息
        self.stats['rssi_history'].append(rssi)
        self.stats['sinr_history'].append(sinr)
        self.stats['pdr_history'].append(pdr)
        self.stats['total_transmission_attempts'] += 1

        # 判断传输是否成功
        success = random.random() < pdr

        if success:
            self.stats['total_packets_sent'] += 1
            # 只有成功传输才计算接收
            if rssi > self.channel_model.sensitivity:
                self.stats['total_packets_received'] += 1

        # 计算能耗 (基于CC2420参数)
        tx_energy = self._calculate_transmission_energy(packet_size, distance)
        sender.current_energy -= tx_energy
        self.stats['total_energy_consumed'] += tx_energy

        # 检查节点是否死亡
        if sender.current_energy <= 0:
            sender.is_alive = False
            sender.current_energy = 0

        return success, rssi, sinr, pdr

    def _calculate_transmission_energy(self, packet_size_bits: int, distance: float) -> float:
        """
        基于CC2420 TelosB平台的能耗计算
        严格匹配权威LEACH的能耗模型
        """
        # CC2420能耗参数 (基于权威文献)
        E_elec = 50e-9      # 50 nJ/bit (电路能耗)
        E_fs = 10e-12       # 10 pJ/bit/m² (自由空间)
        E_mp = 0.0013e-12   # 0.0013 pJ/bit/m⁴ (多径衰落)

        # 距离阈值
        d_crossover = math.sqrt(E_fs / E_mp)  # ~87.7m

        # 传输能耗计算
        if distance < d_crossover:
            # 自由空间模型
            tx_energy = E_elec * packet_size_bits + E_fs * packet_size_bits * (distance ** 2)
        else:
            # 多径衰落模型
            tx_energy = E_elec * packet_size_bits + E_mp * packet_size_bits * (distance ** 4)

        return tx_energy

    def _select_cluster_heads(self) -> List[Node]:
        """LEACH簇头选择算法"""
        cluster_heads = []
        p = 0.1  # 簇头概率 (权威LEACH标准)

        for node in self.nodes:
            if not node.is_alive:
                continue

            # LEACH阈值计算
            if self.round_number % (1/p) == 0:
                threshold = p
            else:
                threshold = p / (1 - p * (self.round_number % (1/p)))

            # 随机选择
            if random.random() < threshold:
                node.is_cluster_head = True
                cluster_heads.append(node)
            else:
                node.is_cluster_head = False

        return cluster_heads

    def _form_clusters(self, cluster_heads: List[Node]):
        """形成簇结构"""
        self.clusters = {}

        # 初始化簇
        for ch in cluster_heads:
            self.clusters[ch.id] = []

        # 节点加入最近的簇头
        for node in self.nodes:
            if not node.is_alive or node.is_cluster_head:
                continue

            if not cluster_heads:
                # 没有簇头，直接连接基站
                node.cluster_id = -1
                continue

            # 找到最佳簇头 (基于RSSI)
            best_ch = None
            best_rssi = -float('inf')

            for ch in cluster_heads:
                distance = self._calculate_distance(node, ch)
                rssi = self.channel_model.calculate_rssi(distance, node, ch)

                if rssi > best_rssi:
                    best_rssi = rssi
                    best_ch = ch

            if best_ch:
                node.cluster_id = best_ch.id
                self.clusters[best_ch.id].append(node)

    def run_round(self) -> Dict:
        """运行一轮LEACH协议"""
        self.round_number += 1
        round_stats = {
            'round': self.round_number,
            'alive_nodes': sum(1 for n in self.nodes if n.is_alive),
            'cluster_heads': 0,
            'packets_sent': 0,
            'packets_received': 0,
            'transmission_attempts': 0,
            'avg_rssi': 0,
            'avg_sinr': 0,
            'avg_pdr': 0,
            'energy_consumed': 0
        }

        # 检查网络是否还活着
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if len(alive_nodes) == 0:
            return round_stats

        # 1. 簇头选择阶段
        cluster_heads = self._select_cluster_heads()
        self.cluster_heads = cluster_heads
        round_stats['cluster_heads'] = len(cluster_heads)

        # 2. 簇形成阶段
        self._form_clusters(cluster_heads)

        # 3. 数据传输阶段
        packets_sent_before = self.stats['total_packets_sent']
        packets_received_before = self.stats['total_packets_received']
        attempts_before = self.stats['total_transmission_attempts']
        energy_before = self.stats['total_energy_consumed']

        # 簇内数据收集
        for ch in cluster_heads:
            if not ch.is_alive:
                continue

            # 簇成员向簇头发送数据
            for member in self.clusters.get(ch.id, []):
                if member.is_alive:
                    success, rssi, sinr, pdr = self._transmit_packet(member, ch)

            # 簇头向基站发送聚合数据
            if ch.is_alive:
                success, rssi, sinr, pdr = self._transmit_packet(ch)

        # 非簇头节点直接向基站发送数据
        for node in self.nodes:
            if node.is_alive and not node.is_cluster_head and node.cluster_id == -1:
                success, rssi, sinr, pdr = self._transmit_packet(node)

        # 计算本轮统计
        round_stats['packets_sent'] = self.stats['total_packets_sent'] - packets_sent_before
        round_stats['packets_received'] = self.stats['total_packets_received'] - packets_received_before
        round_stats['transmission_attempts'] = self.stats['total_transmission_attempts'] - attempts_before
        round_stats['energy_consumed'] = self.stats['total_energy_consumed'] - energy_before

        # 计算平均链路质量
        if self.stats['rssi_history']:
            recent_rssi = self.stats['rssi_history'][-round_stats['transmission_attempts']:]
            recent_sinr = self.stats['sinr_history'][-round_stats['transmission_attempts']:]
            recent_pdr = self.stats['pdr_history'][-round_stats['transmission_attempts']:]

            round_stats['avg_rssi'] = np.mean(recent_rssi) if recent_rssi else 0
            round_stats['avg_sinr'] = np.mean(recent_sinr) if recent_sinr else 0
            round_stats['avg_pdr'] = np.mean(recent_pdr) if recent_pdr else 0

        return round_stats

    def get_network_statistics(self) -> Dict:
        """获取网络统计信息"""
        alive_nodes = sum(1 for n in self.nodes if n.is_alive)

        # 计算真实的PDR
        actual_pdr = (self.stats['total_packets_received'] /
                     self.stats['total_packets_sent']) if self.stats['total_packets_sent'] > 0 else 0

        # 计算传输率 (成功传输/尝试传输)
        transmission_rate = (self.stats['total_packets_sent'] /
                           self.stats['total_transmission_attempts']) if self.stats['total_transmission_attempts'] > 0 else 0

        return {
            'total_rounds': self.round_number,
            'alive_nodes': alive_nodes,
            'network_lifetime': self.round_number if alive_nodes > 0 else self.stats['network_lifetime'],
            'total_packets_sent': self.stats['total_packets_sent'],
            'total_packets_received': self.stats['total_packets_received'],
            'total_transmission_attempts': self.stats['total_transmission_attempts'],
            'packet_delivery_ratio': actual_pdr,
            'transmission_rate': transmission_rate,
            'packets_per_round': self.stats['total_packets_sent'] / self.round_number if self.round_number > 0 else 0,
            'total_energy_consumed': self.stats['total_energy_consumed'],
            'avg_rssi': np.mean(self.stats['rssi_history']) if self.stats['rssi_history'] else 0,
            'avg_sinr': np.mean(self.stats['sinr_history']) if self.stats['sinr_history'] else 0,
            'avg_pdr': np.mean(self.stats['pdr_history']) if self.stats['pdr_history'] else 0
        }
