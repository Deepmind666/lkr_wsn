#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSN鍩哄噯璺敱鍗忚鏍囧噯瀹炵幇

鍩轰簬鏉冨▉鏂囩尞鍜屽紑婧愬疄鐜扮殑鏍囧噯鍩哄噯鍗忚:
- LEACH (Low-Energy Adaptive Clustering Hierarchy)
- PEGASIS (Power-Efficient Gathering in Sensor Information Systems)  
- HEED (Hybrid Energy-Efficient Distributed clustering)

鍙傝€冩枃鐚?
[1] Heinzelman et al. "Energy-efficient communication protocol for wireless microsensor networks" (HICSS 2000)
[2] Lindsey & Raghavendra "PEGASIS: Power-efficient gathering in sensor information systems" (ICCC 2002)
[3] Younis & Fahmy "HEED: a hybrid, energy-efficient, distributed clustering approach" (TMC 2004)

鎶€鏈壒鐐?
- 涓ユ牸鎸夌収鍘熷璁烘枃绠楁硶瀹炵幇
- 浣跨敤鏀硅繘鐨勮兘鑰楁ā鍨嬭繘琛屽叕骞冲姣?
- 鏀寔澶氱缃戠粶閰嶇疆鍜岀幆澧冨弬鏁?
- 鎻愪緵璇︾粏鐨勬€ц兘缁熻鍜屽垎鏋?

浣滆€? AERIS Research Team
鏃ユ湡: 2025-01-30
鐗堟湰: 1.0 (鏍囧噯鍩哄噯瀹炵幇)
"""

import numpy as np
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import copy

from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from heed_protocol import HEEDProtocol, HEEDConfig
from teen_protocol import TEENProtocol, TEENConfig
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


def _init_channel_model(config: "NetworkConfig"):
    enable = bool(getattr(config, "enable_channel", False))
    tx_power = float(getattr(config, "tx_power_dbm", 0.0) or 0.0)
    link_retx = max(0, int(getattr(config, "link_retx", 0) or 0))
    link_retx_power_step = float(getattr(config, "link_retx_power_step", 0.0) or 0.0)
    if not enable or RealisticChannelModel is None:
        return enable, None, tx_power, link_retx, link_retx_power_step
    env = _resolve_channel_env(getattr(config, "channel_env", None))
    return enable, RealisticChannelModel(env), tx_power, link_retx, link_retx_power_step


def _link_success(channel_model, tx_power: float, distance: float, temperature_c: float, humidity_ratio: float) -> bool:
    if channel_model is None:
        return True
    metrics = channel_model.calculate_link_metrics(tx_power, distance, temperature_c, humidity_ratio)
    return random.random() < metrics.get("pdr", 0.0)

@dataclass
class Node:
    """WSN node base class"""
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    is_alive: bool = True
    is_cluster_head: bool = False
    cluster_id: int = -1
    chain_position: int = -1
    
    def __post_init__(self):
        if self.current_energy is None:
            self.current_energy = self.initial_energy

@dataclass
class NetworkConfig:
    """缃戠粶閰嶇疆鍙傛暟"""
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 175.0
    extra_base_stations: Optional[List[Tuple[float, float]]] = None
    skeleton_config: Optional[Dict[str, float]] = None
    gateway_load_limit: Optional[int] = None
    gateway_concurrency: Optional[int] = None
    gateway_limit_dynamic: bool = False
    gateway_limit_min: Optional[int] = None
    gateway_limit_window: Optional[int] = None
    gateway_limit_reduce_threshold: Optional[float] = None
    gateway_limit_expand_threshold: Optional[float] = None
    gateway_limit_cooldown_steps: Optional[int] = None
    num_nodes: int = 100
    initial_energy: float = 2.0  # Joules
    packet_size: int = 1024      # bytes
    temperature_c: float = 25.0  # 鐜娓╁害(掳C)
    humidity_ratio: float = 0.5  # 鐩稿婀垮害(0-1)
    enable_channel: bool = False
    channel_env: Optional[str] = None
    tx_power_dbm: float = 0.0
    link_retx: int = 0
    link_retx_power_step: float = 0.0
    # 优先使用真实几何坐标（若提供），格式为 [(x, y), ...]
    positions: Optional[List[Tuple[float, float]]] = None

class LEACHProtocol:
    """
    LEACH鍗忚鏍囧噯瀹炵幇 (宸查噸鏋勫拰淇)
    鍩轰簬Heinzelman et al. (HICSS 2000)鍘熷璁烘枃鐨勭瀛﹂噸鏋勭増鏈?
    """
    
    def __init__(self, config: NetworkConfig, energy_model: ImprovedEnergyModel):
        self.config = config
        self.energy_model = energy_model
        (
            self.enable_channel,
            self.channel_model,
            self.tx_power_dbm,
            self.link_retx,
            self.link_retx_power_step,
        ) = _init_channel_model(config)
        self.nodes = []
        self.round_number = 0
        self.cluster_heads = []
        self.clusters = {}
        
        # LEACH鍙傛暟 (鍩轰簬鍘熷璁烘枃)
        self.desired_cluster_head_percentage = 0.1
        self.cluster_head_rotation_rounds = int(1 / self.desired_cluster_head_percentage)
        
        # 鏂板锛氭暟鎹紶杈撴鐜囷紝鐢ㄤ簬妯℃嫙鏇寸湡瀹炵殑鍦烘櫙
        self.data_transmission_probability = 0.95  # 95%鐨勬鐜囪繘琛屾暟鎹紶杈?

        # 鎬ц兘缁熻
        self.stats = {
            'network_lifetime': 0,
            'total_energy_consumed': 0.0,
            'packets_transmitted': 0,
            'packets_received': 0,
            'cluster_formation_overhead': 0,
            'round_statistics': []
        }

        # 端到端统计
        self.source_packets_total = 0
        self.bs_delivered_total = 0
        self._all_hop_counts = []

        self._initialize_network()

    def _link_success(self, distance: float, tx_power: float) -> bool:
        return _link_success(
            self.channel_model,
            tx_power,
            distance,
            self.config.temperature_c,
            self.config.humidity_ratio,
        )

    def _initialize_network(self):
        """初始化网络节点"""
        self.nodes = []
        # 若配置提供了真实几何坐标，则优先使用
        provided = getattr(self.config, 'positions', None)
        if provided and isinstance(provided, list) and len(provided) > 0:
            limit = min(len(provided), self.config.num_nodes)
            for i in range(limit):
                x, y = provided[i]
                node = Node(
                    id=i,
                    x=float(x),
                    y=float(y),
                    initial_energy=self.config.initial_energy,
                    current_energy=self.config.initial_energy
                )
                self.nodes.append(node)
            # 若提供坐标不足，则补充随机节点以达到预期数量
            for i in range(limit, self.config.num_nodes):
                x = random.uniform(0, self.config.area_width)
                y = random.uniform(0, self.config.area_height)
                node = Node(
                    id=i,
                    x=x,
                    y=y,
                    initial_energy=self.config.initial_energy,
                    current_energy=self.config.initial_energy
                )
                self.nodes.append(node)
            return
        # 默认回退：随机生成
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            node = Node(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy
            )
            self.nodes.append(node)
    
    def _calculate_distance(self, node1: Node, node2: Node) -> float:
        """计算两节点间距离"""
        return math.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)
    
    def _calculate_distance_to_bs(self, node: Node) -> float:
        """计算节点到基站距离"""
        return math.sqrt((node.x - self.config.base_station_x)**2 +
                        (node.y - self.config.base_station_y)**2)

    def _select_cluster_heads(self) -> List[Node]:
        """
        LEACH绨囧ご閫夋嫨绠楁硶 (閲嶆瀯)
        鍩轰簬姒傜巼闃堝€煎拰杞崲鏈哄埗
        """
        cluster_heads = []
        
        P = self.desired_cluster_head_percentage
        r = self.round_number
        
        # 璁＄畻闃堝€?T(n)
        # 绠€鍖栦絾鏈夋晥鐨勯槇鍊艰绠楋紝纭繚绨囧ご姣斾緥绋冲畾
        threshold = P / (1 - P * (r % self.cluster_head_rotation_rounds))
        
        successful_selections = 0
        for node in self.nodes:
            if not node.is_alive:
                continue

            # 鑺傜偣鏍规嵁闃堝€肩嫭绔嬪喅瀹氭槸鍚︽垚涓虹皣澶?
            if random.random() < threshold:
                node.is_cluster_head = True
                cluster_heads.append(node)
                successful_selections += 1
            else:
                node.is_cluster_head = False

        # 璋冭瘯杈撳嚭
        if r < 5:
            print(f"[DEBUG] Round {r}: threshold={threshold:.4f}, alive={sum(1 for n in self.nodes if n.is_alive)}, selected={successful_selections}")

        # 濡傛灉娌℃湁閫夊嚭绨囧ご锛屽垯寮哄埗閫夋嫨涓€涓紙閬垮厤缃戠粶瀹屽叏鍋滄粸锛?
        if not cluster_heads and any(n.is_alive for n in self.nodes):
            alive_nodes = [n for n in self.nodes if n.is_alive]
            chosen_one = random.choice(alive_nodes)
            chosen_one.is_cluster_head = True
            cluster_heads.append(chosen_one)
            if r < 5:
                print(f"[DEBUG] Round {r}: no cluster head selected, forcibly choose node {chosen_one.id}")

        return cluster_heads

    def _form_clusters(self, cluster_heads: List[Node]):
        """
        褰? (閲嶆瀯)
        闈炵皣澶磋妭鐐瑰姞鍏ユ渶杩戠殑绨囧ご
        """
        self.clusters = {ch.id: {'head': ch, 'members': []} for ch in cluster_heads}
        
        for node in self.nodes:
            if not node.is_alive or node.is_cluster_head:
                continue

            if not cluster_heads:
                node.cluster_id = -1
                continue

            # 鎵惧埌鏈€杩戠殑绨囧ご
            min_distance = float('inf')
            nearest_ch = None
            for ch in cluster_heads:
                distance = self._calculate_distance(node, ch)
                if distance < min_distance:
                    min_distance = distance
                    nearest_ch = ch
            
            # 灏嗚妭鐐瑰垎閰嶇粰鏈€杩戠殑绨囧ご
            if nearest_ch:
                node.cluster_id = nearest_ch.id
                self.clusters[nearest_ch.id]['members'].append(node)

    def _steady_state_communication(self):
        """
        绋虫€侀€ (閲嶆瀯)
        瀹炵幇鎴愬憳->绨囧ご->鍩虹珯鐨勬暟鎹紶杈撳拰鑳借€楄绠?
        """
        total_energy_consumed = 0.0
        packets_transmitted = 0
        packets_received = 0
        cluster_payloads = {ch.id: 1 if ch.is_alive else 0 for ch in self.cluster_heads}
        # 记录簇头自己的感知
        for ch_id, payload in cluster_payloads.items():
            if payload > 0:
                self.source_packets_total += 1

        # 1. 鎴愬憳鑺傜偣鍚戠皣澶村彂閫佹暟鎹?
        for cluster_id, cluster_info in self.clusters.items():
            ch = cluster_info['head']
            if not ch.is_alive:
                continue

            for member in cluster_info['members']:
                if not member.is_alive:
                    continue

                distance = self._calculate_distance(member, ch)
                tx_energy = self.energy_model.calculate_transmission_energy(self.config.packet_size * 8, distance, temperature_c=self.config.temperature_c, humidity_ratio=self.config.humidity_ratio)
                rx_energy = self.energy_model.calculate_reception_energy(self.config.packet_size * 8, temperature_c=self.config.temperature_c, humidity_ratio=self.config.humidity_ratio)

                if member.current_energy > tx_energy and ch.current_energy > rx_energy:
                    self.source_packets_total += 1
                    success = False
                    for attempt in range(self.link_retx + 1):
                        tx_power = self.tx_power_dbm + attempt * self.link_retx_power_step
                        if member.current_energy <= tx_energy or ch.current_energy <= rx_energy:
                            if member.current_energy <= tx_energy:
                                member.is_alive = False
                                member.current_energy = 0
                            if ch.current_energy <= rx_energy:
                                ch.is_alive = False
                                ch.current_energy = 0
                            break
                        member.current_energy -= tx_energy
                        ch.current_energy -= rx_energy
                        total_energy_consumed += tx_energy + rx_energy
                        packets_transmitted += 1
                        if self._link_success(distance, tx_power):
                            packets_received += 1
                            cluster_payloads[ch.id] = cluster_payloads.get(ch.id, 0) + 1
                            success = True
                            break
                    if not success:
                        continue
                else:
                    if member.current_energy <= tx_energy:
                        member.is_alive = False
                        member.current_energy = 0
                    if ch.current_energy <= rx_energy:
                        ch.is_alive = False
                        ch.current_energy = 0

        # 2. 绨囧ご鍚戝熀绔欏彂閫佽仛鍚堟暟鎹?
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue

            distance_to_bs = self._calculate_distance_to_bs(ch)
            num_members = len(self.clusters.get(ch.id, {}).get('members', []))
            
            # 鑱氬悎鑳借€?
            aggregation_energy = self.energy_model.calculate_processing_energy(
                self.config.packet_size * 8 * (num_members + 1)
            )  # +1 for CH's own data

            # 浼犺緭鑳借€? (per attempt)
            tx_energy_to_bs = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8,
                distance_to_bs,
                temperature_c=self.config.temperature_c,
                humidity_ratio=self.config.humidity_ratio,
            )

            total_ch_energy_cost = aggregation_energy + tx_energy_to_bs
            delivered = cluster_payloads.get(ch.id, 0)
            if delivered <= 0:
                continue

            if ch.current_energy > total_ch_energy_cost:
                ch.current_energy -= aggregation_energy
                total_energy_consumed += aggregation_energy
                success = False
                for attempt in range(self.link_retx + 1):
                    tx_power = self.tx_power_dbm + attempt * self.link_retx_power_step
                    if ch.current_energy <= tx_energy_to_bs:
                        ch.is_alive = False
                        ch.current_energy = 0
                        break
                    ch.current_energy -= tx_energy_to_bs
                    total_energy_consumed += tx_energy_to_bs
                    packets_transmitted += 1
                    if self._link_success(distance_to_bs, tx_power):
                        packets_received += 1
                        self.bs_delivered_total += delivered
                        for _ in range(delivered):
                            self._all_hop_counts.append(2)
                        success = True
                        break
                if not success and ch.current_energy <= 0:
                    ch.is_alive = False
                    ch.current_energy = 0
            else:
                ch.is_alive = False
                ch.current_energy = 0

        # 鏇存柊缁熻
        self.stats['total_energy_consumed'] += total_energy_consumed
        self.stats['packets_transmitted'] += packets_transmitted
        self.stats['packets_received'] += packets_received
    
    def run_round(self) -> Dict:
        """Run one PEGASIS round"""
        
        if not any(n.is_alive for n in self.nodes):
            return self._get_round_statistics()
        
        # 1. 閲嶇疆 Clockwise 时钟
        for node in self.nodes:
            node.is_cluster_head = False
            node.cluster_id = -1
        
        cluster_heads = self._select_cluster_heads()
        self.cluster_heads = cluster_heads
        
        if self.round_number <= 5:
            print(f"[DEBUG] Cluster heads after selection: {len(cluster_heads)}")

        # 2. 形成簇
        self._form_clusters(cluster_heads)
        
        if self.round_number <= 5:
            active_members = sum(len(c['members']) for c in self.clusters.values())
            print(f"[DEBUG] Formation complete: {len(self.clusters)} clusters, {active_members} members")

        # 2. 褰?
        self._form_clusters(cluster_heads)
        
        if self.round_number <= 5:
            print(f"[DEBUG] Round {self.round_number}: skip data transmission")

        # 3. 绋虫€侀€氫俊 (鏈夋鐜囪烦杩?
        if random.random() < self.data_transmission_probability:
            self._steady_state_communication()
        else:
            if self.round_number <= 5:
                print(f"[DEBUG] Round {self.round_number}: skip data transmission")

        if self.round_number <= 5:
            active_chs_after_comm = sum(1 for ch in self.cluster_heads if ch.is_alive)
            print(f"[DEBUG] Alive cluster heads after communication: {active_chs_after_comm}")
        
        # 4. 鏇存柊杞暟
        self.round_number += 1
        round_stats = self._get_round_statistics()
        self.stats['round_statistics'].append(round_stats)

        return round_stats
    
    def _get_round_statistics(self) -> Dict:
        """Get current round statistics"""
        alive_nodes = [node for node in self.nodes if node.is_alive]
        total_remaining_energy = sum(node.current_energy for node in alive_nodes)

        # 鐩存帴缁熻娲昏穬鐨勭皣澶达紙鑰屼笉鏄緷璧杝elf.cluster_heads鍒楄〃锛?
        active_cluster_heads = [node for node in self.nodes if node.is_alive and node.is_cluster_head]

        return {
            'round': self.round_number,
            'alive_nodes': len(alive_nodes),
            'cluster_heads': len(active_cluster_heads),
            'total_remaining_energy': total_remaining_energy,
            'average_energy': total_remaining_energy / len(alive_nodes) if alive_nodes else 0,
            'energy_consumed_this_round': self.config.num_nodes * self.config.initial_energy - total_remaining_energy - self.stats['total_energy_consumed']
        }
    
    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """运行完整的 LEACH 仿真"""

        print(f">>> Start LEACH protocol simulation (max rounds: {max_rounds})")
        
        for round_num in range(max_rounds):
            round_stats = self.run_round()
            
            # 检查网络生存状态
            if round_stats['alive_nodes'] == 0:
                self.stats['network_lifetime'] = round_num
                print(f"[HEED] Network ended at round {round_num+1}: all nodes are dead")
                break
            
            # 每100轮输出一次进度
            if round_num % 100 == 0:
                print(f"   Round {round_num}: Alive nodes {round_stats['alive_nodes']}, Remaining energy {round_stats['total_remaining_energy']:.3f} J")
        
        else:
            self.stats['network_lifetime'] = max_rounds
            print(f"[SUCCESS] Simulation complete: network still has alive nodes after {max_rounds} rounds")
        
        return self.get_final_statistics()
    
    def get_final_statistics(self) -> Dict:
        """Get final statistics"""
        alive_nodes = [node for node in self.nodes if node.is_alive]
        
        final_stats = {
            'protocol': 'LEACH',
            'network_lifetime': self.stats['network_lifetime'],
            'total_energy_consumed': self.stats['total_energy_consumed'],
            'final_alive_nodes': len(alive_nodes),
            'energy_efficiency': self.stats['packets_transmitted'] / self.stats['total_energy_consumed'] if self.stats['total_energy_consumed'] > 0 else 0,
            'packet_delivery_ratio': self.stats['packets_received'] / self.stats['packets_transmitted'] if self.stats['packets_transmitted'] > 0 else 0,
            'packet_delivery_ratio_end2end': self.bs_delivered_total / self.source_packets_total if self.source_packets_total > 0 else 0,
            'average_cluster_heads_per_round': np.mean([r.get('cluster_heads', 0) for r in self.stats['round_statistics']]) if self.stats['round_statistics'] else 0,
            'additional_metrics': {
                'total_packets_sent': self.stats['packets_transmitted'],
                'total_packets_received': self.stats['packets_received'],
                'source_packets_total': self.source_packets_total,
                'bs_delivered_total': self.bs_delivered_total
            },
            'avg_hops_to_bs': (sum(self._all_hop_counts) / len(self._all_hop_counts)) if self._all_hop_counts else 0,
            'config': {
                'num_nodes': self.config.num_nodes,
                'initial_energy': self.config.initial_energy,
                'area_size': f"{self.config.area_width}x{self.config.area_height}",
                'packet_size': self.config.packet_size
            }
        }

        return final_stats

class PEGASISProtocol:
    """
    PEGASIS 协议标准实现
    基于 Lindsey & Raghavendra (ICCC 2002) 原始论文
    Power-Efficient Gathering in Sensor Information Systems
    """

    def __init__(self, config: NetworkConfig, energy_model: ImprovedEnergyModel):
        self.config = config
        self.energy_model = energy_model
        (
            self.enable_channel,
            self.channel_model,
            self.tx_power_dbm,
            self.link_retx,
            self.link_retx_power_step,
        ) = _init_channel_model(config)
        self.nodes = []
        self.round_number = 0
        self.chain = []  # 节点链
        self.leader_index = 0  # 当前领导者在链中的索引

        # 性能统计
        self.stats = {
            'network_lifetime': 0,
            'total_energy_consumed': 0.0,
            'packets_transmitted': 0,
            'packets_received': 0,
            'chain_construction_overhead': 0,
            'round_statistics': []
        }

        self.source_packets_total = 0
        self.bs_delivered_total = 0
        self._all_hop_counts = []

        self._initialize_network()
        self._construct_chain()

    def _link_success(self, distance: float, tx_power: float) -> bool:
        return _link_success(
            self.channel_model,
            tx_power,
            distance,
            self.config.temperature_c,
            self.config.humidity_ratio,
        )

    def _initialize_network(self):
        """初始化网络节点"""
        self.nodes = []
        provided = getattr(self.config, 'positions', None)
        if provided and isinstance(provided, list) and len(provided) > 0:
            limit = min(len(provided), self.config.num_nodes)
            for i in range(limit):
                x, y = provided[i]
                node = Node(
                    id=i,
                    x=float(x),
                    y=float(y),
                    initial_energy=self.config.initial_energy,
                    current_energy=self.config.initial_energy
                )
                self.nodes.append(node)
            for i in range(limit, self.config.num_nodes):
                x = random.uniform(0, self.config.area_width)
                y = random.uniform(0, self.config.area_height)
                node = Node(
                    id=i,
                    x=x,
                    y=y,
                    initial_energy=self.config.initial_energy,
                    current_energy=self.config.initial_energy
                )
                self.nodes.append(node)
            return
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            node = Node(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy
            )
            self.nodes.append(node)

    def _calculate_distance(self, node1: Node, node2: Node) -> float:
        """计算两节点间距离"""
        return math.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)

    def _calculate_distance_to_bs(self, node: Node) -> float:
        """计算节点到基站距离"""
        return math.sqrt((node.x - self.config.base_station_x)**2 +
                        (node.y - self.config.base_station_y)**2)

    def _construct_chain(self):
        """
        构建 PEGASIS 链
        使用贪心算法构建近似最短路径链
        """
        if not self.nodes:
            return

        # 浠庤窛绂诲熀绔欐渶杩滅殑鑺傜偣寮€濮?
        remaining_nodes = [node for node in self.nodes if node.is_alive]
        if not remaining_nodes:
            return

        # 鎵惧埌璺濈鍩虹珯鏈€杩滅殑鑺傜偣浣滀负璧峰鐐?
        start_node = max(remaining_nodes,
                        key=lambda n: self._calculate_distance_to_bs(n))

        self.chain = [start_node]
        remaining_nodes.remove(start_node)

        # 璐績绠楁硶鏋勫缓閾撅細姣忔閫夋嫨璺濈褰撳墠閾剧鏈€杩戠殑鑺傜偣
        while remaining_nodes:
            current_end = self.chain[-1]

            # 鎵惧埌璺濈閾惧熬鏈€杩戠殑鑺傜偣
            nearest_node = min(remaining_nodes,
                             key=lambda n: self._calculate_distance(current_end, n))

            self.chain.append(nearest_node)
            remaining_nodes.remove(nearest_node)

        # 鍒濆鍖栭瀵艰€呬负閾句腑闂寸殑鑺傜偣
        for idx, node in enumerate(self.chain):
            node.chain_position = idx
        self.leader_index = len(self.chain) // 2

    def _update_chain(self):
        """Update chain structure and remove dead nodes"""
        # 绉婚櫎姝讳骸鑺傜偣
        alive_chain = [node for node in self.chain if node.is_alive]

        if not alive_chain:
            self.chain = []
            return

        # 濡傛灉閾剧粨鏋勫彂鐢熼噸澶у彉鍖栵紝閲嶆柊鏋勫缓
        if len(alive_chain) < len(self.chain) * 0.8:
            self.nodes = [node for node in self.nodes if node.is_alive]
            self._construct_chain()
        else:
            self.chain = alive_chain
            for idx, node in enumerate(self.chain):
                node.chain_position = idx
            # 璋冩暣棰嗗鑰呯储寮?
            if self.leader_index >= len(self.chain):
                self.leader_index = len(self.chain) // 2

    def _data_gathering_phase(self):
        """数据汇聚阶段，返回 (source_packets, delivered_packets)"""
        if not self.chain or len(self.chain) < 1:
            return 0, 0

        total_energy_consumed = 0.0
        packets_transmitted = 0
        packets_received = 0

        active_nodes = [node for node in self.chain if node.is_alive]
        sources_this_round = len(active_nodes)

        leader = self.chain[self.leader_index]

        # 浠庨摼鐨勪袱绔悜棰嗗鑰呬紶杈撴暟鎹?
        # 宸︿晶閾句紶杈?
        for i in range(self.leader_index):
            current_node = self.chain[i]
            next_node = self.chain[i + 1]

            if not current_node.is_alive or not next_node.is_alive:
                continue

            # 璁＄畻浼犺緭璺濈
            distance = self._calculate_distance(current_node, next_node)

            # 璁＄畻浼犺緭鍜屾帴鏀惰兘鑰?
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8,
                distance,
                temperature_c=self.config.temperature_c,
                humidity_ratio=self.config.humidity_ratio
            )
            rx_energy = self.energy_model.calculate_reception_energy(
                self.config.packet_size * 8,
                temperature_c=self.config.temperature_c,
                humidity_ratio=self.config.humidity_ratio
            )

            success = False
            for attempt in range(self.link_retx + 1):
                tx_power = self.tx_power_dbm + attempt * self.link_retx_power_step
                if current_node.current_energy <= tx_energy or next_node.current_energy <= rx_energy:
                    if current_node.current_energy <= tx_energy:
                        current_node.current_energy = 0
                        current_node.is_alive = False
                    if next_node.current_energy <= rx_energy:
                        next_node.current_energy = 0
                        next_node.is_alive = False
                    break
                current_node.current_energy -= tx_energy
                next_node.current_energy -= rx_energy
                total_energy_consumed += (tx_energy + rx_energy)
                packets_transmitted += 1
                if self._link_success(distance, tx_power):
                    packets_received += 1
                    success = True
                    break
            if not success:
                continue

        delivered_packets = 0

        # 棰嗗鑰呭悜鍩虹珯浼犺緭鑱氬悎遰版嵁
        if leader.is_alive:
            distance_to_bs = self._calculate_distance_to_bs(leader)

            # 璁＄畻浼犺緭鑳借€?
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8,
                distance_to_bs,
                tx_power_dbm=5.0,  # 鍚戝熀绔欎紶杈撲娇鐢ㄦ洿楂樺姛鐜?
                temperature_c=self.config.temperature_c,
                humidity_ratio=self.config.humidity_ratio
            )

            # 鑱氬悎澶勭悊鑳借€?
            processing_energy = self.energy_model.calculate_processing_energy(
                self.config.packet_size * 8 * max(1, len(active_nodes)),
                processing_complexity=1.2  # PEGASIS鑱氬悎澶嶆潅搴﹁緝浣?
            )

            cost = tx_energy + processing_energy
            if leader.current_energy > cost:
                leader.current_energy -= processing_energy
                total_energy_consumed += processing_energy
                success = False
                for attempt in range(self.link_retx + 1):
                    tx_power = (self.tx_power_dbm + 5.0) + attempt * self.link_retx_power_step
                    if leader.current_energy <= tx_energy:
                        leader.is_alive = False
                        leader.current_energy = 0
                        break
                    leader.current_energy -= tx_energy
                    total_energy_consumed += tx_energy
                    packets_transmitted += 1
                    if self._link_success(distance_to_bs, tx_power):
                        delivered_packets = sources_this_round
                        packets_received += 1
                        success = True
                        break
                if not success and leader.current_energy <= 0:
                    leader.is_alive = False
                    leader.current_energy = 0
            else:
                leader.is_alive = False
                leader.current_energy = 0

        # 鏇存柊缁熻淇℃伅
        self.stats['total_energy_consumed'] += total_energy_consumed
        self.stats['packets_transmitted'] += packets_transmitted
        self.stats['packets_received'] += packets_received

        return sources_this_round, delivered_packets

    def run_round(self) -> Dict:
        """运行一轮 PEGASIS 协议"""

        # 妫€鏌ョ綉缁滄槸鍚﹁繕鏈夋椿璺冭妭鐐?
        alive_nodes = [node for node in self.nodes if node.is_alive]
        if not alive_nodes:
            return self._get_round_statistics()

        # 1. 鏇存柊閾剧粨鏋?(绉婚櫎姝讳骸鑺傜偣)
        self._update_chain()

        # 2. 遰版嵁鏀堕泦闃舵
        sources, delivered = self._data_gathering_phase()
        self.source_packets_total += sources
        self.bs_delivered_total += delivered
        if delivered > 0:
            chain_len = len(self.chain)
            leader = self.chain[self.leader_index]
            leader_pos = min(max(getattr(leader, "chain_position", self.leader_index), 0), max(0, chain_len - 1))
            left_sum = leader_pos * (leader_pos + 1) / 2.0
            right_count = chain_len - leader_pos - 1
            right_sum = right_count * (right_count + 1) / 2.0
            avg_chain_hops = (left_sum + right_sum) / max(1.0, float(chain_len))
            for _ in range(delivered):
                self._all_hop_counts.append(avg_chain_hops + 1.0)

        # 3. 窄崲棰嗗鑰?
        if self.chain:
            self.leader_index = (self.leader_index + 1) % len(self.chain)

        # 4. 鏇存柊杞暟
        self.round_number += 1

        # 5. 璁板綍鏈疆缁熻
        round_stats = self._get_round_statistics()
        self.stats['round_statistics'].append(round_stats)

        return round_stats

    def _get_round_statistics(self) -> Dict:
        """鑾峰彇褰撳墠杞殑缁熻淇℃伅"""
        alive_nodes = [node for node in self.nodes if node.is_alive]
        total_remaining_energy = sum(node.current_energy for node in alive_nodes)

        return {
            'round': self.round_number,
            'alive_nodes': len(alive_nodes),
            'chain_length': len(self.chain),
            'leader_id': self.chain[self.leader_index].id if self.chain else -1,
            'total_remaining_energy': total_remaining_energy,
            'average_energy': total_remaining_energy / len(alive_nodes) if alive_nodes else 0,
            'energy_consumed_this_round': self.config.num_nodes * self.config.initial_energy - total_remaining_energy - self.stats['total_energy_consumed']
        }

    def run_simulation(self, max_rounds: int = 1000) -> Dict:
        """运行完整的 PEGASIS 仿真"""

        print(f">>> Start PEGASIS protocol simulation (max rounds: {max_rounds})")

        for round_num in range(max_rounds):
            round_stats = self.run_round()

            # 检查网络生存状态
            if round_stats['alive_nodes'] == 0:
                self.stats['network_lifetime'] = round_num
                print(f"[INFO] Network ended at round {round_num}: all nodes dead")
                break

            # 每100轮输出一次进度
            if round_num % 100 == 0:
                print(
                    f"   轮 {round_num}: 存活节点 {round_stats['alive_nodes']}, "
                    f"剩余能量 {round_stats['total_remaining_energy']:.3f}J, "
                    f"链长度 {round_stats['chain_length']}"
                )

        else:
            self.stats['network_lifetime'] = max_rounds
            print(f"[SUCCESS] Simulation complete: network still has alive nodes after {max_rounds} rounds")

        return self.get_final_statistics()

    def get_final_statistics(self) -> Dict:
        """获取最终统计结果"""
        alive_nodes = [node for node in self.nodes if node.is_alive]

        final_stats = {
            'protocol': 'PEGASIS',
            'network_lifetime': self.stats['network_lifetime'],
            'total_energy_consumed': self.stats['total_energy_consumed'],
            'final_alive_nodes': len(alive_nodes),
            'energy_efficiency': self.stats['packets_transmitted'] / self.stats['total_energy_consumed'] if self.stats['total_energy_consumed'] > 0 else 0,
            'packet_delivery_ratio': self.stats['packets_received'] / self.stats['packets_transmitted'] if self.stats['packets_transmitted'] > 0 else 0,
            'packet_delivery_ratio_end2end': self.bs_delivered_total / self.source_packets_total if self.source_packets_total > 0 else 0,
            'average_chain_length': np.mean([r.get('chain_length', 0) for r in self.stats['round_statistics']]) if self.stats['round_statistics'] else 0,
            'additional_metrics': {
                'total_packets_sent': self.stats['packets_transmitted'],
                'total_packets_received': self.stats['packets_received'],
                'source_packets_total': self.source_packets_total,
                'bs_delivered_total': self.bs_delivered_total
            },
            'avg_hops_to_bs': (sum(self._all_hop_counts) / len(self._all_hop_counts)) if self._all_hop_counts else 0,
            'config': {
                'num_nodes': self.config.num_nodes,
                'initial_energy': self.config.initial_energy,
                'area_size': f"{self.config.area_width}x{self.config.area_height}",
                'packet_size': self.config.packet_size
            }
        }

        return final_stats

# 测试封装
class HEEDProtocolWrapper:
    """HEED 协议封装类，使其与基准测试框架对齐"""

    def __init__(self, config: NetworkConfig, energy_model: ImprovedEnergyModel):
        self.config = config
        self.energy_model = energy_model

        # 鍒涘缓HEED閰嶇疆
        self.heed_config = HEEDConfig(
            c_prob=0.05,  # 5% cluster heads
            p_min=0.001,
            max_iterations=10,
            transmission_range=30.0,
            packet_size=1024,
            initial_energy=config.initial_energy,
            network_width=config.area_width,
            network_height=config.area_height,
            base_station_x=config.base_station_x,
            base_station_y=config.base_station_y,
            enable_channel=config.enable_channel,
            channel_env=config.channel_env,
            tx_power_dbm=config.tx_power_dbm,
            temperature_c=config.temperature_c,
            humidity_ratio=config.humidity_ratio,
            link_retx=config.link_retx,
            link_retx_power_step=config.link_retx_power_step
        )

        self.heed_protocol = HEEDProtocol(self.heed_config)
        self.round_stats = []

    def run_simulation(self, max_rounds: int = 200) -> Dict:
        """运行 HEED 协议仿真"""

        # 鐢熸垚鑺傜偣浣嶇疆
        node_positions = getattr(self.config, "positions", None)
        if not node_positions or len(node_positions) < self.config.num_nodes:
            node_positions = []
            for _ in range(self.config.num_nodes):
                x = random.uniform(0, self.config.area_width)
                y = random.uniform(0, self.config.area_height)
                node_positions.append((x, y))

        # 鍒濆鍖栫綉缁?
        self.heed_protocol.initialize_network(node_positions)

        # 杩愯浠跨湡
        for round_num in range(max_rounds):
            try:
                results = self.heed_protocol.run_round()
                if isinstance(results, dict):
                    self.round_stats.append(results)

                # 检查是否还有存活节点
                if self.heed_protocol.alive_nodes == 0:
                    print(f"[HEED] Network ended at round {round_num+1}: all nodes are dead")
                    break

                # 每20轮输出一次进度
                if round_num > 0 and round_num % 20 == 0:
                    alive_count = self.heed_protocol.alive_nodes
                    print(f"   HEED round {round_num}: alive_nodes={alive_count}, cluster_heads={len(self.heed_protocol.clusters)}")

            except Exception as e:
                print(f"[HEED Error] Round {round_num+1} failed: {e}")
                break

        # 璁＄畻鏈€缁堢粺璁?
        final_stats = self.heed_protocol.get_final_statistics()

        # 璁＄畻骞冲潎绨囧ご鏁?
        avg_cluster_heads = 0
        if self.round_stats:
            total_cluster_counts = 0
            valid_rounds = 0
            for stats in self.round_stats:
                if isinstance(stats, dict) and 'num_clusters' in stats:
                    total_cluster_counts += stats.get('num_clusters', 0)
                    valid_rounds += 1
            if valid_rounds > 0:
                avg_cluster_heads = total_cluster_counts / valid_rounds

        # 杩斿洖涓庡叾浠栧崗璁吋瀹圭殑缁撴灉鏍煎紡
        return {
            'protocol': 'HEED',
            'network_lifetime': final_stats['network_lifetime'],
            'total_energy_consumed': final_stats['total_energy_consumed'],
            'packets_transmitted': final_stats['packets_transmitted'],
            'packets_received': final_stats['packets_received'],
            'packet_delivery_ratio': final_stats['packet_delivery_ratio'],
            'packet_delivery_ratio_end2end': final_stats.get('packet_delivery_ratio_end2end', final_stats['packet_delivery_ratio']),
            'energy_efficiency': final_stats['energy_efficiency'],
            'final_alive_nodes': final_stats['final_alive_nodes'],
            'average_cluster_heads_per_round': avg_cluster_heads,
            'additional_metrics': final_stats['additional_metrics'],
            'avg_hops_to_bs': final_stats.get('avg_hops_to_bs', 0),
        }

class TEENProtocolWrapper:
    """TEEN 协议封装类，使其与基准测试框架对齐"""

    def __init__(self, config: NetworkConfig, energy_model: ImprovedEnergyModel):
        self.config = config
        self.energy_model = energy_model

        # 鍒涘缓TEEN閰嶇疆 - 浣跨敤淇鍚庣殑浼樺寲鍙傛暟
        self.teen_config = TEENConfig(
            num_nodes=config.num_nodes,
            area_width=config.area_width,
            area_height=config.area_height,
            base_station_x=config.base_station_x,
            base_station_y=config.base_station_y,
            initial_energy=config.initial_energy,
            transmission_range=30.0,
            packet_size=1024,
            hard_threshold=45.0,    # 淇鍚庯細澶у箙闄嶄綆纭槇鍊?
            soft_threshold=0.5,     # 淇鍚庯細澶у箙闄嶄綆杞槇鍊?
            max_time_interval=3,    # 淇鍚庯細缂╃煭寮哄埗浼犺緭闂撮殧
            cluster_head_percentage=0.08,  # 淇鍚庯細澧炲姞绨囧ご姣斾緥
            enable_channel=config.enable_channel,
            channel_env=config.channel_env,
            tx_power_dbm=config.tx_power_dbm,
            temperature_c=config.temperature_c,
            humidity_ratio=config.humidity_ratio,
            link_retx=config.link_retx,
            link_retx_power_step=config.link_retx_power_step
        )

        self.teen_protocol = TEENProtocol(self.teen_config)
        self.round_stats = []

    def run_simulation(self, max_rounds: int = 200) -> Dict:
        """运行 TEEN 协议仿真"""
        # 鐢熸垚鑺傜偣浣嶇疆
        node_positions = getattr(self.config, "positions", None)
        if not node_positions or len(node_positions) < self.config.num_nodes:
            node_positions = []
            for _ in range(self.config.num_nodes):
                x = random.uniform(0, self.config.area_width)
                y = random.uniform(0, self.config.area_height)
                node_positions.append((x, y))

        # 鍒濆鍖栫綉缁?
        self.teen_protocol.initialize_network(node_positions)

        # 杩愯浠跨湡
        results = self.teen_protocol.run_simulation(max_rounds)

        # 杩斿洖涓庡叾浠栧崗璁吋瀹圭殑缁撴灉鏍煎紡
        return {
            'protocol': 'TEEN',
            'network_lifetime': results['network_lifetime'],
            'total_energy_consumed': results['total_energy_consumed'],
            'packets_transmitted': results['packets_transmitted'],
            'packets_received': results['packets_received'],
            'packet_delivery_ratio': results['packet_delivery_ratio'],
            'packet_delivery_ratio_end2end': results.get('packet_delivery_ratio_end2end', results['packet_delivery_ratio']),
            'energy_efficiency': results['energy_efficiency'],
            'final_alive_nodes': results['final_alive_nodes'],
            'average_cluster_heads_per_round': results['average_cluster_heads_per_round'],
            'additional_metrics': results['additional_metrics'],
            'avg_hops_to_bs': results.get('avg_hops_to_bs', 0),
        }

def test_leach_protocol():
    """娴嬭瘯LEACH鍗忚瀹炵幇"""

    print("[TEST] Verify LEACH reference implementation")
    print("=" * 50)

    # 鍒涘缓缃戠粶閰嶇疆
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )

    # 鍒涘缓鑳借€楁ā鍨?
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    # 鍒涘缓LEACH鍗忚瀹炰緥
    leach = LEACHProtocol(config, energy_model)

    # 杩愯浠跨湡
    results = leach.run_simulation(max_rounds=200)

    # 杈撳嚭缁撴灉
    print("\n[RESULT] LEACH results:")
    print(f"   Network lifetime: {results['network_lifetime']} rounds")
    print(f"   Total energy consumed: {results['total_energy_consumed']:.6f} J")
    print(f"   Final alive nodes: {results['final_alive_nodes']}")
    print(f"   Energy efficiency: {results['energy_efficiency']:.2f} packets/J")
    print(f"   Packet delivery ratio: {results['packet_delivery_ratio']:.3f}")
    print(f"   Avg cluster heads per round: {results['average_cluster_heads_per_round']:.1f}")

def test_pegasis_protocol():
    """娴嬭瘯PEGASIS鍗忚瀹炵幇"""

    print("\n[TEST] Verify PEGASIS reference implementation")
    print("=" * 50)

    # 鍒涘缓缃戠粶閰嶇疆
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )

    # 鍒涘缓鑳借€楁ā鍨?
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    # 鍒涘缓PEGASIS鍗忚瀹炰緥
    pegasis = PEGASISProtocol(config, energy_model)

    # 杩愯浠跨湡
    results = pegasis.run_simulation(max_rounds=200)

    # Output results
    print("\n[RESULT] PEGASIS results:")
    print(f"   Network lifetime: {results['network_lifetime']} rounds")
    print(f"   Total energy consumed: {results['total_energy_consumed']:.6f} J")
    print(f"   Final alive nodes: {results['final_alive_nodes']}")
    print(f"   Energy efficiency: {results['energy_efficiency']:.2f} packets/J")
    print(f"   Packet delivery ratio: {results['packet_delivery_ratio']:.3f}")
    print(f"   Avg chain length: {results['average_chain_length']:.1f}")

def test_heed_protocol():
    """娴嬭瘯HEED鍗忚瀹炵幇"""

    print("\n[TEST] Verify HEED reference implementation")
    print("=" * 50)

    # 鍒涘缓缃戠粶閰嶇疆
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )

    # 鍒涘缓鑳借€楁ā鍨?
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    # 鍒涘缓HEED鍗忚瀹炰緥
    heed = HEEDProtocolWrapper(config, energy_model)

    # 杩愯浠跨湡
    results = heed.run_simulation(max_rounds=200)

    # 杈撳嚭缁撴灉
    print("\n[RESULT] HEED results:")
    print(f"   Network lifetime: {results['network_lifetime']} rounds")
    print(f"   Total energy consumed: {results['total_energy_consumed']:.6f} J")
    print(f"   Final alive nodes: {results['final_alive_nodes']}")
    print(f"   Energy efficiency: {results['energy_efficiency']:.2f} packets/J")
    print(f"   Packet delivery ratio: {results['packet_delivery_ratio']:.3f}")
    print(f"   Avg cluster heads per round: {results['average_cluster_heads_per_round']:.1f}")

def test_teen_protocol():
    """娴嬭瘯TEEN鍗忚瀹炵幇"""

    print("\n[TEST] Verify TEEN reference implementation")
    print("=" * 50)

    # 鍒涘缓缃戠粶閰嶇疆
    config = NetworkConfig(
        num_nodes=50,
        initial_energy=2.0,
        area_width=100,
        area_height=100
    )

    # 鍒涘缓鑳借€楁ā鍨?
    energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    # 鍒涘缓TEEN鍗忚瀹炰緥
    teen = TEENProtocolWrapper(config, energy_model)

    # 杩愯浠跨湡
    results = teen.run_simulation(max_rounds=200)

    # 杈撳嚭缁撴灉
    print("\n[RESULT] TEEN results:")
    print(f"   Network lifetime: {results['network_lifetime']} rounds")
    print(f"   Total energy consumed: {results['total_energy_consumed']:.6f} J")
    print(f"   Final alive nodes: {results['final_alive_nodes']}")
    print(f"   Energy efficiency: {results['energy_efficiency']:.2f} packets/J")
    print(f"   Packet delivery ratio: {results['packet_delivery_ratio']:.3f}")
    print(f"   Avg cluster heads per round: {results['average_cluster_heads_per_round']:.1f}")
    print(f"   Hard threshold: {results['additional_metrics']['hard_threshold']}")
    print(f"   Soft threshold: {results['additional_metrics']['soft_threshold']}")

def test_all_protocols():
    """娴嬭瘯鎵€鏈夊熀鍑嗗崗璁?"""
    print(">>> Baseline WSN protocols comparison test")
    print("=" * 60)

    test_leach_protocol()
    test_pegasis_protocol()
    test_heed_protocol()
    test_teen_protocol()

if __name__ == "__main__":
    test_all_protocols()

