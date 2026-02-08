#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced PEGASIS: 鑳介噺鎰熺煡鐨勯摼寮忚矾鐢卞崗璁?
鍩轰簬缁忓吀PEGASIS绠楁硶锛屽姞鍏ユ櫤鑳借兘閲忕鐞嗗拰閾句紭鍖栨満鍒?

鏍稿績鏀硅繘:
1. 鑳介噺鎰熺煡鐨勯摼鏋勫缓绠楁硶
2. 鍔ㄦ€侀瀵艰€呴€夋嫨鏈哄埗  
3. 鑷€傚簲浼犺緭鍔熺巼鎺у埗
4. 鏅鸿兘鏁版嵁铻嶅悎绛栫暐

浣滆€? AERIS Research Team
鏃ユ湡: 2025-01-30
鐗堟湰: 1.0 (鍩轰簬PEGASIS鐨勬笎杩涘紡鏀硅繘)
"""

import math
import random
from typing import List, Dict, Tuple
from dataclasses import dataclass
from benchmark_protocols import NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform

@dataclass
class EnhancedPEGASISConfig:
    """Enhanced PEGASIS閰嶇疆鍙傛暟"""
    # 鍩虹缃戠粶鍙傛暟
    num_nodes: int = 50
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 50.0
    initial_energy: float = 2.0
    
    # 閫氫俊鍙傛暟
    transmission_range: float = 30.0
    packet_size: int = 1024  # bits
    
    # 鐜鍙傛暟
    temperature_c: float = 25.0
    humidity_ratio: float = 0.5
    
    # Enhanced PEGASIS鐗规湁鍙傛暟
    energy_threshold: float = 0.1  # 鑳介噺闃堝€硷紝浣庝簬姝ゅ€肩殑鑺傜偣浼樺厛绾ч檷浣?
    leader_rotation_interval: int = 10  # 棰嗗鑰呰疆鎹㈤棿闅?
    chain_optimization_interval: int = 50  # 閾句紭鍖栭棿闅?
    data_fusion_efficiency: float = 0.9  # 鏁版嵁铻嶅悎鏁堢巼

class EnhancedNode:
    """Enhanced PEGASIS鑺傜偣绫?""
    
    def __init__(self, node_id: int, x: float, y: float, initial_energy: float):
        self.id = node_id
        self.x = x
        self.y = y
        self.initial_energy = initial_energy
        self.current_energy = initial_energy
        
        # 閾剧浉鍏冲睘鎬?
        self.next_node_id = -1
        self.prev_node_id = -1
        self.is_leader = False
        self.chain_position = -1
        
        # 缁熻淇℃伅
        self.packets_sent = 0
        self.packets_received = 0
        self.total_distance_transmitted = 0.0
        self.leadership_count = 0
    
    def is_alive(self) -> bool:
        """妫€鏌ヨ妭鐐规槸鍚﹀瓨娲?""
        return self.current_energy > 0
    
    def energy_ratio(self) -> float:
        """璁＄畻鍓╀綑鑳介噺姣斾緥"""
        return self.current_energy / self.initial_energy if self.initial_energy > 0 else 0
    
    def distance_to(self, other: 'EnhancedNode') -> float:
        """璁＄畻鍒板彟涓€涓妭鐐圭殑璺濈"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def distance_to_base_station(self, bs_x: float, bs_y: float) -> float:
        """璁＄畻鍒板熀绔欑殑璺濈"""
        return math.sqrt((self.x - bs_x)**2 + (self.y - bs_y)**2)

class EnhancedPEGASISProtocol:
    """Enhanced PEGASIS鍗忚涓荤被"""
    
    def __init__(self, config: EnhancedPEGASISConfig):
        self.config = config
        # 缂撳瓨鐜鍙傛暟锛屼究浜庤皟鐢?
        self.temperature_c = getattr(config, 'temperature_c', 25.0)
        self.humidity_ratio = getattr(config, 'humidity_ratio', 0.5)
        self.nodes: List[EnhancedNode] = []
        self.chain: List[int] = []  # 鑺傜偣ID鐨勯摼搴忓垪
        self.current_leader_id = -1
        self.current_round = 0
        self.base_station = (config.base_station_x, config.base_station_y)
        
        # 鎬ц兘缁熻
        self.total_energy_consumed = 0.0
        self.packets_transmitted = 0
        self.packets_received = 0
        self.packets_sent = 0  # 娣诲姞鍙戦€佹暟鎹寘缁熻
        self.network_lifetime = 0
        self.round_stats = []
        
        # 鑳借€楁ā鍨?
        self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
    
    def initialize_network(self):
        """鍒濆鍖栫綉缁滄嫇鎵?""
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)
            node = EnhancedNode(i, x, y, self.config.initial_energy)
            self.nodes.append(node)
        
        # 鏋勫缓鍒濆閾?
        self.build_energy_aware_chain()
        print(f"[OK] Enhanced PEGASIS network initialized with {len(self.nodes)} nodes")
    
    def build_energy_aware_chain(self):
        """鏋勫缓鑳介噺鎰熺煡鐨勯摼缁撴瀯"""
        alive_nodes = [node for node in self.nodes if node.is_alive()]
        if len(alive_nodes) <= 1:
            self.chain = [alive_nodes[0].id] if alive_nodes else []
            return
        
        # 鏀硅繘1: 鑳介噺鎰熺煡鐨勮捣濮嬭妭鐐归€夋嫨
        # 涓嶅啀閫夋嫨璺濈鍩虹珯鏈€杩滅殑鑺傜偣锛岃€屾槸閫夋嫨鑳介噺鍏呰冻涓斾綅缃悎閫傜殑鑺傜偣
        start_candidates = sorted(alive_nodes, 
                                key=lambda n: (n.energy_ratio(), 
                                             -n.distance_to_base_station(*self.base_station)), 
                                reverse=True)
        
        # 閫夋嫨鍓?0%鑳介噺鍏呰冻鐨勮妭鐐逛腑璺濈鍩虹珯杈冭繙鐨勪綔涓鸿捣鐐?
        top_energy_nodes = start_candidates[:max(1, len(start_candidates) // 3)]
        start_node = max(top_energy_nodes, 
                        key=lambda n: n.distance_to_base_station(*self.base_station))
        
        # 鏀硅繘2: 鑳介噺鎰熺煡鐨勮椽蹇冮摼鏋勫缓
        chain = [start_node.id]
        remaining = [n for n in alive_nodes if n.id != start_node.id]
        current = start_node
        
        while remaining:
            # 璁＄畻姣忎釜鍊欓€夎妭鐐圭殑缁煎悎寰楀垎
            best_node = None
            best_score = float('-inf')
            
            for candidate in remaining:
                # 璺濈鍥犲瓙 (瓒婅繎瓒婂ソ)
                distance = current.distance_to(candidate)
                distance_score = 1.0 / (1.0 + distance)
                
                # 鑳介噺鍥犲瓙 (鑳介噺瓒婂瓒婂ソ)
                energy_score = candidate.energy_ratio()
                
                # 缁煎悎寰楀垎 (璺濈鏉冮噸0.7锛岃兘閲忔潈閲?.3)
                total_score = 0.7 * distance_score + 0.3 * energy_score
                
                if total_score > best_score:
                    best_score = total_score
                    best_node = candidate
            
            if best_node:
                chain.append(best_node.id)
                remaining.remove(best_node)
                current = best_node
        
        self.chain = chain
        
        # 鏇存柊鑺傜偣鐨勯摼淇℃伅
        for i, node_id in enumerate(chain):
            node = self.nodes[node_id]
            node.chain_position = i
            node.next_node_id = chain[i + 1] if i < len(chain) - 1 else -1
            node.prev_node_id = chain[i - 1] if i > 0 else -1
    
    def select_leader(self) -> int:
        """鏀 silk繘3: 鏅鸿兘棰嗗鑰呴€夋嫨"""
        alive_nodes = [node for node in self.nodes if node.is_alive()]
        if not alive_nodes:
            return -1
        
        # 璁＄畻姣忎釜鑺傜偣鐨勯瀵艰€呴€傚悎搴?
        best_leader = None
        best_fitness = float('-inf')
        
        for node in alive_nodes:
            # 鑳介噺鍥犲瓙 (40%)
            energy_factor = node.energy_ratio()
            
            # 浣嶇疆鍥犲瓙 (30%) - 璺濈鍩虹珯閫備腑鐨勮妭鐐规洿閫傚悎
            distance_to_bs = node.distance_to_base_station(*self.base_station)
            avg_distance = sum(n.distance_to_base_station(*self.base_station) for n in alive_nodes) / len(alive_nodes)
            position_factor = 1.0 / (1.0 + abs(distance_to_bs - avg_distance))
            
            # 璐熻浇鍧囪　鍥犲瓙 (20%) - 涔嬪墠褰撹繃棰嗗鑰呯殑鑺傜偣浼樺厛绾ч檷浣?
            load_factor = 1.0 / (1.0 + node.leadership_count)
            
            # 杩炴帴鎬у洜瀛?(10%) - 閾句腑蹇冧綅缃殑鑺傜偣鏇撮€傚悎
            connectivity_factor = 1.0 - abs(node.chain_position - len(self.chain) / 2) / (len(self.chain) / 2)
            
            # 缁煎悎閫傚悎搴?
            fitness = (0.4 * energy_factor + 0.3 * position_factor + 
                      0.2 * load_factor + 0.1 * connectivity_factor)
            
            if fitness > best_fitness:
                best_fitness = fitness
                best_leader = node
        
        if best_leader:
            # 閲嶇疆鎵€鏈夎妭鐐圭殑棰嗗鑰呯姸鎬?
            for node in self.nodes:
                node.is_leader = False
            
            best_leader.is_leader = True
            best_leader.leadership_count += 1
            self.current_leader_id = best_leader.id
            return best_leader.id
        
        return -1
    
    def data_transmission_round(self) -> int:
        """鏁版嵁浼犺緭杞 - 淇鐗堟湰锛岀‘淇濇纭殑鏁版嵁鍖呰鏁?""
        if not self.chain or self.current_leader_id == -1:
            return 0

        total_packets = 0
        leader_node = self.nodes[self.current_leader_id]
        leader_position = leader_node.chain_position
        alive_nodes = [node for node in self.nodes if node.is_alive()]

        if not alive_nodes:
            return 0

        # 闃舵1: 閾惧唴鏁版嵁浼犺緭 - 姣忎釜鑺傜偣閮界敓鎴愬苟浼犺緭鏁版嵁鍖?
        # 宸︿晶閾句紶杈?(浠?鍒發eader_position-1)
        for i in range(leader_position):
            current_node = self.nodes[self.chain[i]]

            if not current_node.is_alive():
                continue

            # 鎵惧埌涓嬩竴涓瓨娲荤殑鑺傜偣浣滀负负鎺ユ敹鑰?
            next_node = None
            for j in range(i + 1, len(self.chain)):
                if self.nodes[self.chain[j]].is_alive():
                    next_node = self.nodes[self.chain[j]]
                    break

            if not next_node:
                continue

            # 璁＄畻浼犺緭璺濈鍜岃兘鑰?
            distance = current_node.distance_to(next_node)
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8, distance,
                temperature_c=self.temperature_c,
                humidity_ratio=self.humidity_ratio
            )
            rx_energy = self.energy_model.calculate_reception_energy(
                self.config.packet_size * 8,
                temperature_c=self.temperature_c,
                humidity_ratio=self.humidity_ratio
            )

            # 妫€鏌ヨ兘閲忔槸鍚﹁冻澶熷苟鎵ц浼犺緭
            if (current_node.current_energy >= tx_energy and
                next_node.current_energy >= rx_energy):

                # 娑堣€楄兘閲?
                current_node.current_energy -= tx_energy
                next_node.current_energy -= rx_energy

                # 鏇存柊缁熻
                current_node.packets_sent += 1
                current_node.total_distance_transmitted += distance
                self.total_energy_consumed += (tx_energy + rx_energy)
                self.packets_sent += 1  # 鍗忚绾у埆缁熻
                total_packets += 1

                # 鎴愬姛鎺ユ敹璁℃暟
                self.packets_received += 1

        # 鍙充晶閾句紶杈?(浠巐en(chain)-1鍒發eader_position+1)
        for i in range(len(self.chain) - 1, leader_position, -1):
            current_node = self.nodes[self.chain[i]]

            if not current_node.is_alive():
                continue

            # 鎵惧埌鍓嶄竴涓瓨娲荤殑鑺傜偣浣滀负负鎺ユ敹鑰?
            prev_node = None
            for j in range(i - 1, -1, -1):
                if self.nodes[self.chain[j]].is_alive():
                    prev_node = self.nodes[self.chain[j]]
                    break

            if not prev_node:
                continue

            # 璁＄畻浼犺緭璺濈鍜岃兘鑰?
            distance = current_node.distance_to(prev_node)
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8, distance,
                temperature_c=self.temperature_c,
                humidity_ratio=self.humidity_ratio
            )
            rx_energy = self.energy_model.calculate_reception_energy(
                self.config.packet_size * 8,
                temperature_c=self.temperature_c,
                humidity_ratio=self.humidity_ratio
            )

            # 妫€鏌ヨ兘閲忔槸鍚﹁冻澶熷苟鎵ц浼犺緭
            if (current_node.current_energy >= tx_energy and
                prev_node.current_energy >= rx_energy):

                # 娑堣€楄兘閲?
                current_node.current_energy -= tx_energy
                prev_node.current_energy -= rx_energy

                # 鏇存柊缁熻
                current_node.packets_sent += 1
                current_node.total_distance_transmitted += distance
                self.total_energy_consumed += (tx_energy + rx_energy)
                self.packets_sent += 1  # 鍗忚绾у埆缁熻
                total_packets += 1

                # 鎴愬姛鎺ユ敹璁℃暟
                self.packets_received += 1

        # 闃舵2: 鏁版嵁鑱氬悎锛堥瀵艰€呭鐞嗘墍鏈夋敹鍒扮殑鏁版嵁锛?
        if leader_node.is_alive():
            # 鑱氬悎鑳借€楋細姣忎釜瀛樻椿鑺傜偣鐨勬暟鎹兘闇€瑕佸鐞?
            aggregation_energy = 0.000005 * len(alive_nodes)  # 5nJ per bit per node
            if leader_node.current_energy >= aggregation_energy:
                leader_node.current_energy -= aggregation_energy
                self.total_energy_consumed += aggregation_energy

        # 闃舵3: 棰嗗鑰呭悜鍩虹珯浼犺緭鑱氬悎鏁版嵁
        if leader_node.is_alive():
            distance_to_bs = leader_node.distance_to_base_station(*self.base_station)
            tx_energy = self.energy_model.calculate_transmission_energy(
                self.config.packet_size * 8, distance_to_bs,
                temperature_c=self.temperature_c,
                humidity_ratio=self.humidity_ratio
            )

            if leader_node.current_energy >= tx_energy:
                leader_node.current_energy -= tx_energy
                leader_node.packets_sent += 1
                leader_node.total_distance_transmitted += distance_to_bs
                self.total_energy_consumed += tx_energy
                self.packets_sent += 1  # 鍗忚绾у埆缁熻
                total_packets += 1
                self.packets_received += 1  # 鍩虹珯鎴愬姛鎺ユ敹鑱氬悎鏁版嵁

        # 鏇存柊鎬讳紶杈撴暟鎹寘璁℃暟
        self.packets_transmitted += total_packets
        return total_packets

    def run_round(self) -> bool:
        """杩愯涓€杞崗璁?""
        self.current_round += 1

        # 妫€鏌ュ瓨娲昏妭鐐?
        alive_nodes = [node for node in self.nodes if node.is_alive()]
        if not alive_nodes:
            return False

        # 瀹氭湡浼樺寲閾剧粨鏋?
        if self.current_round % self.config.chain_optimization_interval == 1:
            self.build_energy_aware_chain()

        # 瀹氭湡杞崲棰嗗鑰?
        if (self.current_round % self.config.leader_rotation_interval == 1 or
            self.current_leader_id == -1 or
            not self.nodes[self.current_leader_id].is_alive()):
            self.select_leader()

        # 鎵ц鏁版嵁浼犺緭
        packets_sent = self.data_transmission_round()

        # 璁板綍缁熻淇℃伅
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
        """杩愯瀹屾暣浠跨湡"""
        print(f">>> Start Enhanced PEGASIS simulation (max rounds: {max_rounds})")

        while self.current_round < max_rounds:
            if not self.run_round():
                break

            # 姣?0杞緭鍑虹姸鎬?
            if self.current_round % 50 == 0:
                alive_nodes = len([n for n in self.nodes if n.is_alive()])
                total_energy = sum(n.current_energy for n in self.nodes)
                avg_energy = total_energy / len(self.nodes)
                print(f"   Round {self.current_round}: alive nodes {alive_nodes}, "
                      f"骞冲潎鑳介噺 {avg_energy:.3f}J, 閾鹃暱搴?{len(self.chain)}")

        # 璁＄畻鏈€缁堢粺璁?
        self.network_lifetime = self.current_round
        final_alive_nodes = len([n for n in self.nodes if n.is_alive()])

        # 璁＄畻鎬ц兘鎸囨爣
        energy_efficiency = self.packets_received / self.total_energy_consumed if self.total_energy_consumed > 0 else 0
        packet_delivery_ratio = self.packets_received / self.packets_transmitted if self.packets_transmitted > 0 else 0

        # 璁＄畻鏀 silk繘鎸囨爣
        total_leadership_changes = sum(node.leadership_count for node in self.nodes)
        avg_transmission_distance = (sum(node.total_distance_transmitted for node in self.nodes) /
                                   sum(node.packets_sent for node in self.nodes) if
                                   sum(node.packets_sent for node in self.nodes) > 0 else 0)

        print(f"[OK] Enhanced PEGASIS simulation complete: network ended after {self.network_lifetime} rounds")

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
    """浠嶯etworkConfig鍒涘缓Enhanced PEGASIS鍗忚瀹炰緥"""
    enhanced_config = EnhancedPEGASISConfig(
        num_nodes=config.num_nodes,
        area_width=config.area_width,
        area_height=config.area_height,
        base_station_x=config.base_station_x,
        base_station_y=config.base_station_y,
        initial_energy=config.initial_energy,
        transmission_range=getattr(config, 'transmission_range', 30.0),
        packet_size=getattr(config, 'packet_size', 1024),
        temperature_c=getattr(config, 'temperature_c', 25.0),
        humidity_ratio=getattr(config, 'humidity_ratio', 0.5)
    )

    protocol = EnhancedPEGASISProtocol(enhanced_config)
    return protocol

