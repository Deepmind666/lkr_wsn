#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
节点状态管理器 (Node State Manager)

负责管理和计算节点的动态状态，特别是与通信链路质量相关的指标。
这是实现“可靠性感知”路由的关键模块。

核心功能:
1. 跟踪节点间通信的PDR和RSSI历史记录。
2. 计算综合的链路质量指数 (LQI)。
3. 提供接口供上层路由协议调用。
"""

from dataclasses import dataclass
from collections import deque

@dataclass
class LinkQualityRecord:
    """记录与单个邻居的链路质量历史"""
    neighbor_id: int
    rssi_history: deque
    pdr_history: deque
    last_updated_round: int

class NodeStateManager:
    """管理全网节点的动态状态，特别是链路质量。"""
    def __init__(self, num_nodes: int, history_window: int = 50):
        self.num_nodes = num_nodes
        self.history_window = history_window  # 用于计算滑动平均的窗口大小
        # 存储结构: self.node_states[node_id][neighbor_id] -> LinkQualityRecord
        self.node_states: dict[int, dict[int, LinkQualityRecord]] = {i: {} for i in range(num_nodes)}
        self.lqi_cache: dict[int, tuple[float, int]] = {}  # 缓存: {node_id: (lqi, last_calculated_round)}

    def update_link_quality(self, sender_id: int, receiver_id: int, rssi: float, is_success: bool, current_round: int):
        """
        更新两个节点间的双向链路质量记录。
        """
        self._update_single_link(sender_id, receiver_id, rssi, is_success, current_round)
        self._update_single_link(receiver_id, sender_id, rssi, is_success, current_round)

    def _update_single_link(self, source_id: int, dest_id: int, rssi: float, is_success: bool, current_round: int):
        """内部辅助函数，更新单向链路记录。"""
        if dest_id not in self.node_states[source_id]:
            self.node_states[source_id][dest_id] = LinkQualityRecord(
                neighbor_id=dest_id,
                rssi_history=deque(maxlen=self.history_window),
                pdr_history=deque(maxlen=self.history_window),
                last_updated_round=current_round
            )
        
        record = self.node_states[source_id][dest_id]
        record.rssi_history.append(rssi)
        record.pdr_history.append(1.0 if is_success else 0.0)
        record.last_updated_round = current_round

    def get_lqi(self, node_id: int, current_round: int, w_pdr: float = 0.6, w_rssi: float = 0.4) -> float:
        """
        计算并获取一个节点的综合LQI。
        使用缓存避免在同一轮内重复计算。
        """
        if node_id in self.lqi_cache and self.lqi_cache[node_id][1] == current_round:
            return self.lqi_cache[node_id][0]

        neighbor_links = self.node_states.get(node_id, {})
        if not neighbor_links:
            return 0.0  # 如果没有邻居，LQI为0

        # 计算所有邻居链路的平均PDR和RSSI
        total_pdr = 0.0
        total_rssi = 0.0
        link_count = 0
        for neighbor_id, record in neighbor_links.items():
            if record.pdr_history:
                total_pdr += sum(record.pdr_history) / len(record.pdr_history)
                total_rssi += sum(record.rssi_history) / len(record.rssi_history)
                link_count += 1
        
        if link_count == 0:
            return 0.0

        avg_pdr = total_pdr / link_count
        avg_rssi = total_rssi / link_count
        
        # 归一化RSSI (假设RSSI范围在-100dBm到-30dBm之间)
        normalized_rssi = (avg_rssi - (-100)) / ((-30) - (-100))
        normalized_rssi = max(0.0, min(1.0, normalized_rssi)) # 确保在[0,1]范围内

        # 计算加权LQI
        lqi = w_pdr * avg_pdr + w_rssi * normalized_rssi
        
        self.lqi_cache[node_id] = (lqi, current_round)
        return lqi

    def get_network_lqi_stats(self, current_round: int) -> dict:
        """获取全网的LQI统计信息 (均值、方差等)"""
        all_lqi = [self.get_lqi(i, current_round) for i in range(self.num_nodes)]
        if not all_lqi:
            return {'mean': 0, 'std_dev': 0, 'min': 0, 'max': 0}
            
        mean_lqi = sum(all_lqi) / len(all_lqi)
        std_dev_lqi = (sum([(x - mean_lqi) ** 2 for x in all_lqi]) / len(all_lqi)) ** 0.5
        return {
            'mean': mean_lqi,
            'std_dev': std_dev_lqi,
            'min': min(all_lqi),
            'max': max(all_lqi)
        }