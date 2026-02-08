#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淇鐗圠EACH鍗忚 - 涓ユ牸鍖归厤鏉冨▉LEACH琛屼负

鍩轰簬鏉冨▉LEACH-PY瀹炵幇鐨勫叧閿彂鐜帮細
1. 鍗忚寮€閿€宸ㄥぇ锛欻ello娑堟伅骞挎挱娑堣€楀ぇ閲忚兘閲?
2. 蹇€熻妭鐐规浜★細2J鍒濆鑳介噺蹇€熻€楀敖
3. 浣庝紶杈撶巼锛殈1鍖?杞紝澶ч儴鍒嗚疆娆℃棤绨囧ご
4. 鐩存帴浼犺緭锛氭棤绨囧ご鏃剁洿鎺ュ悜鍩虹珯浼犺緭

淇瑕佺偣锛?
- 澧炲姞Hello娑堟伅骞挎挱鐨勫崗璁紑閿€
- 瀹炵幇姝ｇ‘鐨勮兘鑰楃疮绉ā寮?
- 鍖归厤鏉冨▉LEACH鐨勮妭鐐规浜℃ā寮?
- 瀹炵幇鐪熷疄鐨勪紶杈撴鐜囨帶鍒?

浣滆€? AERIS Research Team
鏃ユ湡: 2025-01-31
鐗堟湰: 3.0 (Corrected Implementation)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import numpy as np
except ModuleNotFoundError:
    class _NPFallback:
        @staticmethod
        def mean(seq):
            return sum(seq) / len(seq) if seq else 0

        @staticmethod
        def std(seq):
            if not seq:
                return 0
            m = sum(seq) / len(seq)
            var = sum((x - m) ** 2 for x in seq) / len(seq)
            return var ** 0.5

    np = _NPFallback()
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import copy

@dataclass
class Node:
    """WSN node class for corrected LEACH"""
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    is_alive: bool = True
    is_cluster_head: bool = False
    cluster_id: int = -1
    
    # 鏉冨▉LEACH鐗规湁灞炴€?
    my_cluster_head: int = -1  # MCH灞炴€?
    round_as_ch: int = -1      # 涓婃浣滀负绨囧ご鐨勮疆娆?

@dataclass
class NetworkConfig:
    """缃戠粶閰嶇疆鍙傛暟 - 涓ユ牸鍖归厤鏉冨▉LEACH"""
    num_nodes: int = 50
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 175.0
    initial_energy: float = 2.0      # 2J (鏉冨▉LEACH鏍囧噯)
    data_packet_size: int = 4000     # 4000 bits
    hello_packet_size: int = 100     # 100 bits (鍗忚寮€閿€)
    num_packet_attempts: int = 10    # 姣忚疆浼犺緭灏濊瘯娆℃暟

class CorrectedLEACHProtocol:
    """淇鐗圠EACH鍗忚 - 涓ユ牸鍖归厤鏉冨▉琛屼负"""
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        self.nodes = []
        self.round_number = 0
        self.cluster_heads = []
        self.clusters = {}
        
        # 鏉冨▉LEACH鍙傛暟
        self.p = 0.1  # 绨囧ご姒傜巼
        
        # 涓ユ牸鍖归厤鏉冨▉LEACH鐨勮兘鑰楀弬鏁?
        self.ETX = 50e-9         # 50 nJ/bit (鍙戦€佺數璺兘鑰?
        self.ERX = 50e-9         # 50 nJ/bit (鎺ユ敹鐢佃矾鑳借€?
        self.EDA = 5e-9          # 5 nJ/bit (鏁版嵁鑱氬悎鑳借€? - 鍏抽敭缂哄け鍙傛暟!
        self.Efs = 10e-12        # 10 pJ/bit/m虏 (鑷敱绌洪棿鏀惧ぇ鍣?
        self.Emp = 0.0013e-12    # 0.0013 pJ/bit/m鈦?(澶氬緞鏀惧ぇ鍣?
        self.d_crossover = math.sqrt(self.Efs / self.Emp)  # ~87.7m
        
        # 缁熻淇℃伅
        self.stats = {
            'total_packets_sent': 0,
            'total_packets_received': 0,
            'total_transmission_attempts': 0,
            'total_bs_packets_delivered': 0,  # 成功送达基站的聚合包总数
            'total_bs_transmission_attempts': 0,  # 基站上行尝试总数（直接/簇头聚合）
            'total_energy_consumed': 0.0,
            'hello_messages_sent': 0,
            'protocol_overhead_energy': 0.0,
            'data_transmission_energy': 0.0,
            'round_stats': []
        }
        
        # 鍒濆鍖栫綉缁?
        self._initialize_network()
    
    def _initialize_network(self):
        """Initialize network nodes"""
        self.nodes = []
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
        """璁＄畻涓よ妭鐐归棿璺濈"""
        return math.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)
    
    def _calculate_distance_to_bs(self, node: Node) -> float:
        """Calculate distance to base station"""
        return math.sqrt((node.x - self.config.base_station_x)**2 + 
                        (node.y - self.config.base_station_y)**2)
    
    def _calculate_transmission_energy(self, packet_size_bits: int, distance: float, temperature_c: float = 25.0, humidity_ratio: float = 0.5) -> float:
        """
        涓ユ牸鍖归厤鏉冨▉LEACH鐨勮兘鑰楄绠?
        鍩轰簬鏉冨▉LEACH-PY婧愮爜瀹炵幇
        """
        # 鏉冨▉LEACH鑳借€楀叕寮?
        if distance > self.d_crossover:
            # 澶氬緞琛拌惤妯″瀷 (distance > do)
            tx_energy = self.ETX * packet_size_bits + self.Emp * packet_size_bits * (distance ** 4)
        else:
            # 鑷敱绌洪棿妯″瀷 (distance <= do)
            tx_energy = self.ETX * packet_size_bits + self.Efs * packet_size_bits * (distance ** 2)

        return tx_energy

    def _calculate_reception_energy(self, packet_size_bits: int, temperature_c: float = 25.0, humidity_ratio: float = 0.5) -> float:
        """
        涓ユ牸鍖归厤鏉冨▉LEACH鐨勬帴鏀惰兘鑰楄绠?
        鍖呭惈鏁版嵁鑱氬悎鑳借€桬DA
        """
        return (self.ERX + self.EDA) * packet_size_bits

    def _select_best_ch_for_bs(self, candidates: List[Node]) -> Node:
        """选择最优簇头进行聚合并上行到基站
        策略：
        - 优先选择当前能量足以负担对基站发射能耗的候选
        - 在可负担者中选择对基站发射能耗最低者（距离最近）
        - 若均不可负担，则选择距离基站最近者，尽量降低失败影响
        """
        if not candidates:
            raise ValueError("No candidates provided for CH selection")

        scored = []
        for ch in candidates:
            d = self._calculate_distance_to_bs(ch)
            tx_e = self._calculate_transmission_energy(self.config.data_packet_size, d, 25.0, 0.5)
            scored.append((tx_e, d, ch))

        # 首选：可负担者中能耗最低
        affordable = [item for item in scored if item[2].current_energy >= item[0]]
        if affordable:
            affordable.sort(key=lambda x: x[0])
            return affordable[0][2]

        # 回退：距离最近者
        scored.sort(key=lambda x: x[1])
        return scored[0][2]
    
    def _broadcast_hello_messages(self) -> float:
        """
        涓ユ牸鍖归厤鏉冨▉LEACH鐨凥ello娑堟伅骞挎挱妯″紡

        鏉冨▉LEACH鏈変袱涓叧閿箍鎾樁娈碉細
        1. 鍩虹珯鍚戞墍鏈夎妭鐐瑰箍鎾璈ello娑堟伅
        2. 姣忎釜绨囧ご鍚戣寖鍥村唴鑺傜偣骞挎挱Hello娑堟伅

        杩欐槸瀵艰嚧蹇€熻妭鐐规浜＄殑涓昏鍘熷洜锛?
        """
        total_hello_energy = 0.0
        hello_messages_sent = 0

        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes:
            return 0.0

        # 闃舵1: 鍩虹珯鍚戞墍鏈夎妭鐐瑰箍鎾璈ello娑堟伅 (鏉冨▉LEACH绗?27-247琛?
        # 鍩虹珯鍙戦€丠ello缁欐墍鏈夋椿璺冭妭鐐?
        bs_to_nodes_energy = 0.0
        for node in alive_nodes:
            distance_to_bs = self._calculate_distance_to_bs(node)

            # 鍩虹珯鍙戦€佽兘鑰?(鍩虹珯鑳介噺鏃犻檺锛屼笉璁＄畻)
            # 鑺傜偣鎺ユ敹鑳借€?
            rx_energy = self._calculate_reception_energy(self.config.hello_packet_size, 25.0, 0.5)
            node.current_energy -= rx_energy
            bs_to_nodes_energy += rx_energy
            hello_messages_sent += 1

            # 妫€鏌ヨ妭鐐规槸鍚﹀洜鎺ユ敹Hello鑰屾浜?
            if node.current_energy <= 0:
                node.is_alive = False
                node.current_energy = 0

        total_hello_energy += bs_to_nodes_energy

        # 闃舵2: 姣忎釜绨囧ご鍚戣寖鍥村唴鑺傜偣骞挎挱Hello娑堟伅 (鏉冨▉LEACH绗?76-408琛?
        # 娉ㄦ剰锛氳繖鍙戠敓鍦ㄧ皣澶撮€夋嫨涔嬪悗
        ch_broadcast_energy = 0.0
        for ch in self.cluster_heads:
            if not ch.is_alive:
                continue

            # 鎵惧埌鍦ㄧ皣澶撮€氫俊鑼冨洿鍐呯殑鑺傜偣
            receivers_in_range = []
            for node in self.nodes:
                if node.is_alive and node.id != ch.id:
                    distance = self._calculate_distance(ch, node)
                    # 鍋囪閫氫俊鑼冨洿涓?0m (鍙皟鏁?
                    if distance <= 50.0:
                        receivers_in_range.append(node)

            # 绨囧ご鍚戣寖鍥村唴姣忎釜鑺傜偣鍙戦€丠ello娑堟伅
            for receiver in receivers_in_range:
                distance = self._calculate_distance(ch, receiver)

                # 绨囧ご鍙戦€佽兘鑰?
                tx_energy = self._calculate_transmission_energy(
                    self.config.hello_packet_size, distance, 25.0, 0.5
                )
                ch.current_energy -= tx_energy
                ch_broadcast_energy += tx_energy

                # 鎺ユ敹鑺傜偣鎺ユ敹鑳借€?
                rx_energy = self._calculate_reception_energy(self.config.hello_packet_size, 25.0, 0.5)
                receiver.current_energy -= rx_energy
                ch_broadcast_energy += rx_energy

                hello_messages_sent += 1

                # 妫€鏌ヨ妭鐐规槸鍚︽浜?
                if ch.current_energy <= 0:
                    ch.is_alive = False
                    ch.current_energy = 0
                    break  # 绨囧ご姝讳骸锛屽仠姝㈠彂閫?

                if receiver.current_energy <= 0:
                    receiver.is_alive = False
                    receiver.current_energy = 0

        total_hello_energy += ch_broadcast_energy

        # 鏇存柊缁熻
        self.stats['hello_messages_sent'] += hello_messages_sent
        self.stats['protocol_overhead_energy'] += total_hello_energy

        return total_hello_energy
    
    def _select_cluster_heads(self) -> List[Node]:
        """
        鏉冨▉LEACH绨囧ご閫夋嫨绠楁硶
        涓ユ牸鍖归厤鍘熷璁烘枃鐨勯槇鍊艰绠?
        """
        cluster_heads = []
        
        for node in self.nodes:
            if not node.is_alive:
                continue
            
            # 鏉冨▉LEACH闃堝€艰绠?
            # T(n) = P / (1 - P * (r mod (1/P))) if n 鈭?G
            # 鍏朵腑G鏄湪杩囧幓1/P杞腑娌℃湁褰撹繃绨囧ご鐨勮妭鐐归泦鍚?
            
            if self.round_number % int(1/self.p) == 0:
                # 鏂板懆鏈熷紑濮嬶紝閲嶇疆鎵€鏈夎妭鐐圭殑绨囧ご鍘嗗彶
                node.round_as_ch = -1
            
            # 妫€鏌ヨ妭鐐规槸鍚﹀湪褰撳墠鍛ㄦ湡鍐呭綋杩囩皣澶?
            current_cycle_start = (self.round_number // int(1/self.p)) * int(1/self.p)
            if node.round_as_ch >= current_cycle_start:
                continue  # 鏈懆鏈熷凡褰撹繃绨囧ご锛岃烦杩?
            
            # 璁＄畻闃堝€?
            threshold = self.p / (1 - self.p * (self.round_number % int(1/self.p)))
            
            # 闅忔満閫夋嫨
            if random.random() < threshold:
                node.is_cluster_head = True
                node.round_as_ch = self.round_number
                cluster_heads.append(node)
            else:
                node.is_cluster_head = False
        
        return cluster_heads
    
    def _form_clusters(self, cluster_heads: List[Node]):
        """Form cluster structure"""
        self.clusters = {}
        
        # 鍒濆鍖栫皣
        for ch in cluster_heads:
            self.clusters[ch.id] = []
            ch.my_cluster_head = ch.id  # 绨囧ご鐨凪CH鏄嚜宸?
        
        # 闈炵皣澶磋妭鐐瑰姞鍏ユ渶杩戠殑绨囧ご
        for node in self.nodes:
            if not node.is_alive or node.is_cluster_head:
                continue
            
            if not cluster_heads:
                # 娌℃湁绨囧ご锛岀洿鎺ヨ繛鎺ュ熀绔?
                node.cluster_id = -1
                node.my_cluster_head = -1  # -1琛ㄧず鍩虹珯
                continue
            
            # 鎵惧埌鏈€杩戠殑绨囧ご
            best_ch = None
            min_distance = float('inf')
            
            for ch in cluster_heads:
                distance = self._calculate_distance(node, ch)
                if distance < min_distance:
                    min_distance = distance
                    best_ch = ch
            
            if best_ch:
                node.cluster_id = best_ch.id
                node.my_cluster_head = best_ch.id
                self.clusters[best_ch.id].append(node)
    
    def _data_transmission_phase(self) -> Tuple[int, int, int, float]:
        """
        涓ユ牸鍖归厤鏉冨▉LEACH鐨勬暟鎹紶杈撻樁娈?

        鏉冨▉LEACH妯″紡锛?
        1. 姣忎釜绨囧ご鎵惧埌鍙戦€佽€呰妭鐐?
        2. 鍙戦€佽€呭悜绨囧ご鍙戦€佹暟鎹寘
        3. 绨囧ご鑱氬悎鏁版嵁鍚庡悜鍩虹珯鍙戦€?
        4. NumPacket=10鎺у埗姣忚疆浼犺緭灏濊瘯娆℃暟

        Returns:
            (packets_sent, packets_received, transmission_attempts, energy_consumed)
        """
        packets_sent = 0
        packets_received = 0
        transmission_attempts = 0
        energy_consumed = 0.0
        # 记录本轮送达基站的聚合包与上行尝试次数
        bs_packets_delivered = 0
        bs_transmission_attempts = 0
        # 限制每轮仅进行一次“送达基站”的聚合上行，以对齐权威 LEACH 的统计口径
        bs_already_sent = False

        # 鏉冨▉LEACH鐨勫叧閿€昏緫锛氬熀浜庣皣澶磋繘琛屾暟鎹紶杈?
        # 鍙傝€冩潈濞丩EACH绗?16-450琛岀殑steady_state_phase

        for _ in range(self.config.num_packet_attempts):
            transmission_attempts += 1

            # 濡傛灉娌℃湁娲昏穬鐨勭皣澶达紝闅忔満閫夋嫨鑺傜偣鐩存帴鍚戝熀绔欎紶杈?
            alive_cluster_heads = [ch for ch in self.cluster_heads if ch.is_alive]

            if not alive_cluster_heads:
                # 娌℃湁绨囧ご锛岄殢鏈洪€夋嫨鑺傜偣鐩存帴鍚戝熀绔欎紶杈?
                alive_nodes = [n for n in self.nodes if n.is_alive]
                if not alive_nodes:
                    break

                # 选择距离基站最近的存活节点直接上行，降低发射能耗，提高送达率
                sender = min(alive_nodes, key=lambda n: self._calculate_distance_to_bs(n))
                distance = self._calculate_distance_to_bs(sender)

                # 璁＄畻浼犺緭鑳借€?
                tx_energy = self._calculate_transmission_energy(self.config.data_packet_size, distance, 25.0, 0.5)

                # 基站上行尝试（仅限每轮一次）
                if not bs_already_sent:
                    bs_transmission_attempts += 1
                if sender.current_energy >= tx_energy:
                    sender.current_energy -= tx_energy
                    energy_consumed += tx_energy
                    packets_sent += 1
                    packets_received += 1  # 鍋囪鍩虹珯鎴愬姛鎺ユ敹
                    if not bs_already_sent:
                        bs_packets_delivered += 1
                        bs_already_sent = True

                    if sender.current_energy <= 0:
                        sender.is_alive = False
                        sender.current_energy = 0

                continue

            # 鏉冨▉LEACH妯″紡锛氫负姣忎釜绨囧ご鎵惧埌鍙戦€佽€?
            # 选择最优簇头进行聚合上行：优先满足“可上行且所需能耗最低”
            selected_ch = self._select_best_ch_for_bs(alive_cluster_heads)

            # 鎵惧埌璇ョ皣澶寸殑鎴愬憳鑺傜偣浣滀负鍙戦€佽€?
            cluster_members = []
            if selected_ch.id in self.clusters:
                cluster_members = [n for n in self.clusters[selected_ch.id] if n.is_alive]

            if cluster_members:
                # 绨囧唴鏈夋垚鍛橈紝鎴愬憳鍚戠皣澶村彂閫佹暟鎹?
                sender = random.choice(cluster_members)
                distance = self._calculate_distance(sender, selected_ch)

                # 鎴愬憳鑺傜偣鍙戦€佽兘鑰?
                tx_energy = self._calculate_transmission_energy(self.config.data_packet_size, distance, 25.0, 0.5)

                if sender.current_energy >= tx_energy:
                    sender.current_energy -= tx_energy
                    energy_consumed += tx_energy

                    # 绨囧ご鎺ユ敹鑳借€?
                    rx_energy = self._calculate_reception_energy(self.config.data_packet_size, 25.0, 0.5)
                    if selected_ch.current_energy >= rx_energy:
                        selected_ch.current_energy -= rx_energy
                        energy_consumed += rx_energy
                        packets_sent += 1
                        packets_received += 1

                        # 绨囧ご鍚戝熀绔欒浆鍙戣仛鍚堟暟鎹?
                        bs_distance = self._calculate_distance_to_bs(selected_ch)
                        bs_tx_energy = self._calculate_transmission_energy(self.config.data_packet_size, bs_distance, 25.0, 0.5)

                        # 基站上行尝试（仅限每轮一次）
                        if not bs_already_sent:
                            bs_transmission_attempts += 1
                        if selected_ch.current_energy >= bs_tx_energy and not bs_already_sent:
                            selected_ch.current_energy -= bs_tx_energy
                            energy_consumed += bs_tx_energy
                            bs_packets_delivered += 1
                            bs_already_sent = True
                        else:
                            selected_ch.is_alive = False
                            selected_ch.current_energy = 0
                    else:
                        selected_ch.is_alive = False
                        selected_ch.current_energy = 0

                    if sender.current_energy <= 0:
                        sender.is_alive = False
                        sender.current_energy = 0
            else:
                # 绨囧ご娌℃湁鎴愬憳锛岀皣澶寸洿鎺ュ悜鍩虹珯鍙戦€佹暟鎹?
                distance = self._calculate_distance_to_bs(selected_ch)
                tx_energy = self._calculate_transmission_energy(self.config.data_packet_size, distance, 25.0, 0.5)

                # 基站上行尝试（仅限每轮一次）
                if not bs_already_sent:
                    bs_transmission_attempts += 1
                if selected_ch.current_energy >= tx_energy:
                    selected_ch.current_energy -= tx_energy
                    energy_consumed += tx_energy
                    packets_sent += 1
                    packets_received += 1
                    if not bs_already_sent:
                        bs_packets_delivered += 1
                        bs_already_sent = True

                    if selected_ch.current_energy <= 0:
                        selected_ch.is_alive = False
                        selected_ch.current_energy = 0

        # 更新全局统计（基站聚合包）
        self.stats['total_bs_packets_delivered'] += bs_packets_delivered
        self.stats['total_bs_transmission_attempts'] += bs_transmission_attempts

        return packets_sent, packets_received, transmission_attempts, energy_consumed

    def run_round(self) -> Dict:
        """杩愯涓€杞甃EACH鍗忚 - 涓ユ牸鍖归厤鏉冨▉琛屼负"""
        self.round_number += 1

        # 鍒濆鍖栬疆娆＄粺璁?
        round_stats = {
            'round': self.round_number,
            'alive_nodes_start': sum(1 for n in self.nodes if n.is_alive),
            'cluster_heads': 0,
            'packets_sent': 0,
            'packets_received': 0,
            'transmission_attempts': 0,
            'hello_energy': 0.0,
            'data_energy': 0.0,
            'total_energy': 0.0,
            'alive_nodes_end': 0
        }

        # 妫€鏌ョ綉缁滄槸鍚﹁繕娲荤潃
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if len(alive_nodes) == 0:
            return round_stats

        energy_before = sum(n.current_energy for n in self.nodes)

        # 1. 鍗忚寮€閿€闃舵锛欻ello娑堟伅骞挎挱
        hello_energy = self._broadcast_hello_messages()
        round_stats['hello_energy'] = hello_energy

        # 2. 绨囧ご閫夋嫨闃舵
        cluster_heads = self._select_cluster_heads()
        self.cluster_heads = cluster_heads
        round_stats['cluster_heads'] = len(cluster_heads)

        # 3. 绨囧舰鎴愰樁娈?
        self._form_clusters(cluster_heads)

        # 4. 鏁版嵁浼犺緭闃舵
        packets_sent, packets_received, transmission_attempts, data_energy = self._data_transmission_phase()

        round_stats['packets_sent'] = packets_sent
        round_stats['packets_received'] = packets_received
        round_stats['transmission_attempts'] = transmission_attempts
        round_stats['data_energy'] = data_energy

        # 璁＄畻鎬昏兘鑰?
        energy_after = sum(n.current_energy for n in self.nodes)
        total_energy_consumed = energy_before - energy_after
        round_stats['total_energy'] = total_energy_consumed

        # 鏇存柊鍏ㄥ眬缁熻
        self.stats['total_packets_sent'] += packets_sent
        self.stats['total_packets_received'] += packets_received
        self.stats['total_transmission_attempts'] += transmission_attempts
        self.stats['total_energy_consumed'] += total_energy_consumed
        self.stats['data_transmission_energy'] += data_energy

        # 鏈€缁堝瓨娲昏妭鐐规暟
        round_stats['alive_nodes_end'] = sum(1 for n in self.nodes if n.is_alive)

        # 淇濆瓨杞缁熻
        self.stats['round_stats'].append(round_stats)

        return round_stats

    def get_network_statistics(self) -> Dict:
        """鑾峰彇缃戠粶缁熻淇℃伅"""
        alive_nodes = sum(1 for n in self.nodes if n.is_alive)

        # 璁＄畻鐪熷疄鐨凱DR鍜屼紶杈撶巼
        pdr = (self.stats['total_packets_received'] /
               self.stats['total_packets_sent']) if self.stats['total_packets_sent'] > 0 else 0

        transmission_rate = (self.stats['total_packets_sent'] /
                           self.stats['total_transmission_attempts']) if self.stats['total_transmission_attempts'] > 0 else 0

        # 基站聚合包统计
        bs_pdr = (self.stats['total_bs_packets_delivered'] /
                  self.stats['total_bs_transmission_attempts']) if self.stats['total_bs_transmission_attempts'] > 0 else 0
        bs_transmission_rate = bs_pdr
        bs_packets_per_round = (self.stats['total_bs_packets_delivered'] / self.round_number) if self.round_number > 0 else 0
        packets_per_round = bs_packets_per_round  # 将旧键对齐为“送达基站的包/轮”，避免歧义

        # 璁＄畻鑳借€楀垎甯?
        protocol_overhead_ratio = (self.stats['protocol_overhead_energy'] /
                                 self.stats['total_energy_consumed']) if self.stats['total_energy_consumed'] > 0 else 0

        data_transmission_ratio = (self.stats['data_transmission_energy'] /
                                 self.stats['total_energy_consumed']) if self.stats['total_energy_consumed'] > 0 else 0

        return {
            'total_rounds': self.round_number,
            'alive_nodes': alive_nodes,
            'network_lifetime': self.round_number if alive_nodes > 0 else self._find_network_death_round(),
            'total_packets_sent': self.stats['total_packets_sent'],
            'total_packets_received': self.stats['total_packets_received'],
            'total_transmission_attempts': self.stats['total_transmission_attempts'],
            'packet_delivery_ratio': pdr,
            'transmission_rate': transmission_rate,
            'packets_per_round': packets_per_round,
            'total_bs_packets_delivered': self.stats['total_bs_packets_delivered'],
            'total_bs_transmission_attempts': self.stats['total_bs_transmission_attempts'],
            'bs_packet_delivery_ratio': bs_pdr,
            'bs_transmission_rate': bs_transmission_rate,
            'bs_packets_per_round': bs_packets_per_round,
            'total_energy_consumed': self.stats['total_energy_consumed'],
            'protocol_overhead_energy': self.stats['protocol_overhead_energy'],
            'data_transmission_energy': self.stats['data_transmission_energy'],
            'protocol_overhead_ratio': protocol_overhead_ratio,
            'data_transmission_ratio': data_transmission_ratio,
            'hello_messages_sent': self.stats['hello_messages_sent'],
            'initial_total_energy': self.config.num_nodes * self.config.initial_energy,
            'remaining_energy': sum(n.current_energy for n in self.nodes),
            'energy_efficiency': self.stats['total_packets_sent'] / self.stats['total_energy_consumed'] if self.stats['total_energy_consumed'] > 0 else 0
        }

    def _find_network_death_round(self) -> int:
        """Find network death round"""
        for i, round_stat in enumerate(self.stats['round_stats']):
            if round_stat['alive_nodes_end'] == 0:
                return i + 1
        return self.round_number

    def get_node_energy_distribution(self) -> Dict:
        """鑾峰彇鑺傜偣鑳介噺鍒嗗竷"""
        alive_energies = [n.current_energy for n in self.nodes if n.is_alive]
        dead_nodes = sum(1 for n in self.nodes if not n.is_alive)

        return {
            'alive_nodes': len(alive_energies),
            'dead_nodes': dead_nodes,
            'min_energy': min(alive_energies) if alive_energies else 0,
            'max_energy': max(alive_energies) if alive_energies else 0,
            'avg_energy': np.mean(alive_energies) if alive_energies else 0,
            'std_energy': np.std(alive_energies) if alive_energies else 0,
            'total_remaining_energy': sum(alive_energies)
        }

