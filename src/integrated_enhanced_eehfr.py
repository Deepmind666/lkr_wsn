#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成版Enhanced EEHFR协议 (Integrated Enhanced EEHFR)

基于诚实验证后的项目现状，集成所有优化组件：
1. 改进的能耗模型 (ImprovedEnergyModel)
2. 现实信道模型 (RealisticChannelModel)
3. 环境感知机制 (EnvironmentClassifier)
4. 模糊逻辑系统 (FuzzyLogicSystem)

目标：创建完整、可靠、高性能的WSN路由协议

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 2.0 (Integrated)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import math
import random
import time
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable

# 导入所有优化组件
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform, EnergyParameters
from realistic_channel_model import RealisticChannelModel, EnvironmentType, LogNormalShadowingModel
from benchmark_protocols import Node, NetworkConfig
from cas_selector import CASSelector, CASConfig, CASMode
from gateway_selector import GatewaySelector, GatewayConfig
from skeleton_selector import SkeletonSelector, SkeletonConfig


@dataclass
class EnhancedNode(Node):
    """增强节点类，扩展基础节点功能"""

    # 环境感知属性
    environment_type: Optional[EnvironmentType] = None

    # 模糊逻辑决策属性
    fuzzy_score: float = 0.0
    cluster_head_probability: float = 0.0
    lqi: float = 0.0 # 新增：链路质量指数

    # 自适应参数
    transmission_power: float = 0.0  # dBm
    retransmission_count: int = 0

    def calculate_distance(self, other: "EnhancedNode") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

class EnvironmentClassifier:
    """环境分类器"""

    def __init__(self):
        self.classification_history = []

    def classify_environment(self, nodes: List[EnhancedNode]) -> EnvironmentType:
        """
        基于节点分布和信号特征自动分类环境
        简化版实现，基于节点密度和区域大小
        """

        if not nodes:
            return EnvironmentType.INDOOR_OFFICE

        # 计算节点密度
        area = 100 * 100  # 假设100x100区域
        density = len(nodes) / area

        # 基于密度简单分类
        if density > 0.01:  # 高密度
            return EnvironmentType.INDOOR_OFFICE
        elif density > 0.005:  # 中密度
            return EnvironmentType.INDOOR_RESIDENTIAL
        else:  # 低密度
            return EnvironmentType.OUTDOOR_OPEN

# 移除了内部简化的FuzzyLogicSystem，将使用外部模块

class IntegratedEnhancedEEHFRProtocol:
    """
    集成版Enhanced EEHFR协议
    整合所有优化组件的完整实现
    """

    def __init__(self, config: NetworkConfig, *, enable_cas: bool = True, enable_fairness: bool = True, enable_aco_intercluster: bool = False, enable_gateway: bool = True, enable_skeleton: bool = True, profile: str | None = None, verbose: bool = True):
        self.config = config
        self.enable_cas = enable_cas
        self.enable_fairness = enable_fairness
        self.enable_aco_intercluster = enable_aco_intercluster
        self.enable_gateway = enable_gateway
        self.enable_skeleton = enable_skeleton
        self.profile = profile
        self.verbose = verbose

        # 导入外部模块（带安全回退）
        try:
            from fuzzy_logic_system import FuzzyLogicSystem
            _fuzzy = FuzzyLogicSystem()
        except Exception:
            # 软降级：缺少skfuzzy等依赖时使用轻量加权近似，保证口径一致性相对可接受
            class _FallbackFuzzy:
                def calculate_cluster_head_chance(self, residual_energy, node_centrality, node_degree, distance_to_bs, link_quality):
                    re = max(0.0, min(1.0, float(residual_energy)))
                    ce = max(0.0, min(1.0, float(node_centrality)))
                    nd = min(max(0.0, float(node_degree)/20.0), 1.0)
                    db = 1.0 - min(1.0, float(distance_to_bs)/max(1.0, 0.001 + (300.0)))  # 近距更优
                    lq = max(0.0, min(1.0, float(link_quality)))
                    return 0.35*re + 0.25*ce + 0.15*nd + 0.10*db + 0.15*lq
                def calculate_next_hop_suitability(self, residual_energy, link_quality, distance_to_bs):
                    re = max(0.0, min(1.0, float(residual_energy)))
                    lq = max(0.0, min(1.0, float(link_quality)))
                    db = 1.0 - min(1.0, float(distance_to_bs)/300.0)
                    return 0.5*lq + 0.3*re + 0.2*db
            _fuzzy = _FallbackFuzzy()
        from node_state_manager import NodeStateManager

        # 初始化所有组件
        self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        self.environment_classifier = EnvironmentClassifier()
        self.fuzzy_system = _fuzzy
        self.state_manager = NodeStateManager(config.num_nodes) # 实例化状态管理器

        # 公平性：簇头使用计数（滑动窗口可后续加入）
        self.ch_usage_count: Dict[int, int] = {}

        # 先进行环境分类，然后初始化信道模型
        self.current_environment = EnvironmentType.INDOOR_OFFICE  # 默认环境
        self.channel_model = None  # 稍后初始化

        # 网络状态
        self.nodes: List[EnhancedNode] = []
        self.current_round = 0
        self.current_environment = EnvironmentType.INDOOR_OFFICE

        # 统计信息
        self.round_statistics = []
        self.total_energy_consumed = 0.0
        self.total_packets_sent = 0
        self.total_packets_received = 0
        # 端到端统计（聚合语义）：源包总数与成功到达BS的数据单元总数
        self.source_packets_total = 0
        self.bs_delivered_total = 0
        # 最近一轮的端到端统计（供_round_statistics使用）
        self._last_source_packets_round = 0
        self._last_bs_delivered_round = 0

        # 尾部安全阀（Safety Fallback）参数与状态
        self.safety_fallback_enabled = True
        self.safety_T = 1          # 连续失败轮阈值
        self.safety_theta = 0.1    # 单轮端到端阈值（低于则记为失败）
        self._consec_bad_rounds = 0
        # 危机轮保底动作
        self.safety_redundant_uplink = False   # 失败则额外重传一次至BS
        self.safety_redundant_prob = 1.0       # 冗余上行触发概率（危机轮内）
        self.safety_power_bump = False         # 危机轮临时提升发射功率
        self.safety_power_bump_delta = 2.0     # dBm 增量（根据能量模型口径）
        self.safety_extra_uplink_max = 1       # 危机轮允许的额外上行次数（默认1次）
        # 调试/测试信号
        self._last_forced_direct = False
        self._last_extra_uplink_used = False

        # 初始化网络
        self._initialize_network()

        # 应用profile快捷配置（不改变默认值，只有传入时才覆盖）
        if self.profile:
            p = self.profile.lower()
            if p == 'energy':
                self.safety_fallback_enabled = False
                # 可选：降低簇头比例或CAS更偏直达（已默认）
            elif p == 'robust':
                self.safety_fallback_enabled = True
                self.safety_T = 1
                self.safety_theta = 0.1
                self.safety_redundant_uplink = True
                self.safety_redundant_prob = 1.0
                self.safety_power_bump = True
                self.safety_power_bump_delta = 1.0

    def _initialize_network(self):
        """初始化网络节点"""
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)

            node = EnhancedNode(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy,
                is_alive=True,
                is_cluster_head=False,
                cluster_id=-1,
                transmission_power=0.0  # dBm, 将根据环境调整
            )
            self.nodes.append(node)

        # 环境分类
        self.current_environment = self.environment_classifier.classify_environment(self.nodes)

        # 现在可以初始化信道模型
        from realistic_channel_model import RealisticChannelModel
        self.channel_model = RealisticChannelModel(self.current_environment)

        # 根据环境调整初始参数
        self._adapt_to_environment()

    def _adapt_to_environment(self):
        """根据环境类型调整协议参数"""

        # 根据环境类型设置传输功率
        power_settings = {
            EnvironmentType.INDOOR_OFFICE: -5.0,      # 低功率
            EnvironmentType.INDOOR_RESIDENTIAL: -3.0,  # 中低功率
            EnvironmentType.INDOOR_FACTORY: 0.0,      # 中功率
            EnvironmentType.OUTDOOR_OPEN: 3.0,        # 中高功率
            EnvironmentType.OUTDOOR_SUBURBAN: 5.0,    # 高功率
            EnvironmentType.OUTDOOR_URBAN: 8.0        # 最高功率
        }

        default_power = power_settings.get(self.current_environment, 0.0)

        for node in self.nodes:
            if node.is_alive:
                node.transmission_power = default_power
                node.environment_type = self.current_environment

    def _select_cluster_heads(self):
        """使用模糊逻辑选择簇头，并叠加公平约束惩罚。"""
        from fairness_metrics import ch_usage_penalty

        # 重置所有节点的簇头状态
        for node in self.nodes:
            node.is_cluster_head = False
            node.cluster_id = -1

        # 计算每个节点的簇头概率
        alive_nodes = [node for node in self.nodes if node.is_alive]
        area_diag = math.sqrt(self.config.area_width**2 + self.config.area_height**2) or 1.0

        for node in alive_nodes:
            # 计算LQI
            node.lqi = self.state_manager.get_lqi(node.id, self.current_round)

            # 计算中心性
            distances = [math.sqrt((node.x - other.x)**2 + (node.y - other.y)**2)
                         for other in alive_nodes if other.id != node.id]
            avg_distance = sum(distances) / len(distances) if distances else 0
            max_distance = area_diag
            centrality = 1 - (avg_distance / max_distance) if max_distance > 0 else 0

            # 计算节点度
            node_degree = len(distances)

            # 计算到基站的距离
            dist_to_bs = math.sqrt((node.x - self.config.base_station_x)**2 +
                                   (node.y - self.config.base_station_y)**2)

            # 调用增强的模糊逻辑系统（基础概率）
            base_prob = self.fuzzy_system.calculate_cluster_head_chance(
                residual_energy=node.current_energy / node.initial_energy,
                node_centrality=centrality,
                node_degree=node_degree,
                distance_to_bs=dist_to_bs,
                link_quality=node.lqi
            )
            # 公平惩罚：根据簇头使用率（历史轮数）降低被频繁担任CH的节点概率
            if self.enable_fairness:
                penalty = ch_usage_penalty(self.ch_usage_count, node.id, self.current_round + 1, target_ratio=0.1)
                node.cluster_head_probability = base_prob * (1.0 - 0.25 * penalty)
            else:
                node.cluster_head_probability = base_prob

        # 基于概率选择簇头
        target_cluster_heads = max(1, int(len(alive_nodes) * 0.1))  # 10%的节点作为簇头

        # 按概率排序，选择前N个作为簇头
        sorted_nodes = sorted(alive_nodes, key=lambda n: n.cluster_head_probability, reverse=True)

        for i in range(min(target_cluster_heads, len(sorted_nodes))):
            sorted_nodes[i].is_cluster_head = True
            sorted_nodes[i].cluster_id = i
            # 记录簇头使用次数
            self.ch_usage_count[sorted_nodes[i].id] = self.ch_usage_count.get(sorted_nodes[i].id, 0) + 1

    def _form_clusters(self):
        """形成簇结构"""

        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]
        member_nodes = [node for node in self.nodes if not node.is_cluster_head and node.is_alive]

        # 为每个成员节点分配最近的簇头
        for member in member_nodes:
            if not cluster_heads:
                continue

            # 找到最近的簇头
            min_distance = float('inf')
            best_cluster_head = None

            for ch in cluster_heads:
                distance = math.sqrt((member.x - ch.x)**2 + (member.y - ch.y)**2)
                if distance < min_distance:
                    min_distance = distance
                    best_cluster_head = ch

            if best_cluster_head:
                member.cluster_id = best_cluster_head.cluster_id

    def _perform_data_transmission(self):
        """执行数据传输（采用CAS模式选择：直达/链式/限跳）"""

        packets_sent = 0
        packets_received = 0
        energy_consumed = 0.0

        # 端到端：每轮源包总数=本轮存活节点数（每个活节点一包）
        self._last_source_packets_round = sum(1 for n in self.nodes if n.is_alive)
        self._last_bs_delivered_round = 0

        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]

        # 计算全局/簇级上下文特征（归一化近似）
        area_diag = math.sqrt(self.config.area_width**2 + self.config.area_height**2) or 1.0
        avg_energy = sum(n.current_energy for n in self.nodes if n.is_alive) / max(1, sum(1 for n in self.nodes if n.is_alive))
        max_energy = max((n.initial_energy for n in self.nodes), default=1.0)
        energy_norm = min(1.0, max(0.0, avg_energy / max_energy))
        lqi_stats = self.state_manager.get_network_lqi_stats(self.current_round)
        link_norm = min(1.0, max(0.0, lqi_stats.get('mean', 0.0)))

        # 每个簇内进行数据收集
        for ch in cluster_heads:
            cluster_members = [node for node in self.nodes
                               if node.cluster_id == ch.cluster_id and not node.is_cluster_head and node.is_alive]
            if not cluster_members:
                continue

            # 估计簇半径与密度
            dists = [math.sqrt((m.x - ch.x)**2 + (m.y - ch.y)**2) for m in cluster_members]
            mean_radius = (sum(dists) / len(dists)) if dists else 0.0
            radius_norm = min(1.0, mean_radius / (area_diag))
            density_norm = min(1.0, len(cluster_members) / max(1, self.config.num_nodes))

            # 到BS距离（归一化）
            dist_bs = math.sqrt((ch.x - self.config.base_station_x)**2 + (ch.y - self.config.base_station_y)**2)
            dist_bs_norm = min(1.0, dist_bs / area_diag)

            # 公平度惩罚（采用 Jain 指数）：J∈[0,1]，越接近1越公平；惩罚=1-J
            member_energies = [m.current_energy for m in cluster_members]
            if self.enable_fairness and member_energies:
                from fairness_metrics import jain_index
                J = jain_index(member_energies)
                fair_penalty = float(max(0.0, min(1.0, 1.0 - J)))
            else:
                fair_penalty = 0.0

            # 簇尾最远成员，用于限跳判定
            tail_max = min(1.0, (max(dists) if dists else 0.0) / area_diag)

            # 选择模式（调用CAS）
            if not hasattr(self, 'cas_selector'):
                self.cas_selector = CASSelector(CASConfig())
            if self.enable_cas:
                # 调高两跳阈值、提升直达权重（通过CAS配置），使链式仅在半径/尾部较大时触发
                if not hasattr(self, '_cas_cfg_tuned'):
                    # 一次性调参
                    self.cas_selector.cfg.w_direct_link = 0.8
                    self.cas_selector.cfg.w_direct_energy = 0.7
                    self.cas_selector.cfg.w_chain_radius = 0.4
                    self.cas_selector.cfg.w_chain_density = 0.3
                    self.cas_selector.cfg.twohop_tail_threshold = 0.7
                    self._cas_cfg_tuned = True
                # Safety fallback：危机轮强制保守直达（不改变簇内成员→CH的逻辑；主要在簇间会用）
                if self.safety_fallback_enabled and self._consec_bad_rounds >= self.safety_T:
                    mode = CASMode.DIRECT
                    self._last_forced_direct = True
                else:
                    self._last_forced_direct = False
                    mode, _, _ = self.cas_selector.select_mode({
                        'energy': energy_norm,
                        'link': link_norm,
                        'dist_bs': dist_bs_norm,
                        'radius': radius_norm,
                        'density': density_norm,
                        'fairness': fair_penalty,
                        'tail_max': tail_max,
                    })
            else:
                mode = CASMode.DIRECT

            # 执行簇内数据收集（三种模式共用基础能耗与成功率估计）
            def send_member_to(target_node, member):
                nonlocal packets_sent, packets_received, energy_consumed
                distance = math.sqrt((member.x - target_node.x)**2 + (member.y - target_node.y)**2)
                tx_energy = self.energy_model.calculate_transmission_energy(
                    self.config.packet_size * 8, distance, member.transmission_power
                )
                rx_energy = self.energy_model.calculate_reception_energy(self.config.packet_size * 8)
                member.current_energy -= tx_energy
                target_node.current_energy -= rx_energy
                energy_consumed += tx_energy + rx_energy
                packets_sent += 1
                link_metrics = self.channel_model.calculate_link_metrics(member.transmission_power, distance, getattr(self, '_current_env_temp', 25.0), getattr(self, '_current_env_humidity', 0.5))
                is_success = (random.random() < link_metrics['pdr'])
                # 保持hop级PDR统计：中继成功计入packets_received；端到端统计另行处理
                if is_success:
                    packets_received += 1
                self.state_manager.update_link_quality(
                    sender_id=member.id,
                    receiver_id=target_node.id,
                    rssi=link_metrics['rssi'],
                    is_success=is_success,
                    current_round=self.current_round
                )

            if mode == CASMode.DIRECT:
                for m in cluster_members:
                    if m.current_energy > 0:
                        send_member_to(ch, m)
            elif mode == CASMode.CHAIN:
                # 链式：按距CH从近到远排序；相邻聚合，最终最邻近节点发往CH
                ordered = sorted(cluster_members, key=lambda m: math.sqrt((m.x - ch.x)**2 + (m.y - ch.y)**2))
                if len(ordered) == 1:
                    if ordered[0].current_energy > 0:
                        send_member_to(ch, ordered[0])
                else:
                    for i in range(len(ordered) - 1):
                        a, b = ordered[i], ordered[i + 1]
                        if a.current_energy > 0:
                            send_member_to(b, a)
                    # 最后一个（离CH最近）发往CH
                    if ordered[-1].current_energy > 0:
                        send_member_to(ch, ordered[-1])
            else:  # CASMode.TWO_HOP
                # 为尾部成员选择中继（半径中位数附近的成员），尾部发往中继，其余直达CH，中继再发CH
                ordered = sorted(cluster_members, key=lambda m: math.sqrt((m.x - ch.x)**2 + (m.y - ch.y)**2))
                relay = ordered[len(ordered)//2] if len(ordered) >= 2 else ch
                relay_used = False
                for m in cluster_members:
                    if m.current_energy <= 0:
                        continue
                    d_norm = math.sqrt((m.x - ch.x)**2 + (m.y - ch.y)**2) / area_diag
                    if relay != ch and m is not relay and d_norm > 0.5:
                        send_member_to(relay, m)
                        relay_used = True
                    else:
                        send_member_to(ch, m)
                if relay_used and relay.current_energy > 0 and relay is not ch:
                    send_member_to(ch, relay)

        # 先进行骨干簇头选择（PCA中轴）；可选启用
        backbone_ids = []
        if getattr(self, 'enable_skeleton', True) and cluster_heads:
            try:
                if not hasattr(self, 'skeleton_selector'):
                    # 初始参数：k=2, 距离阈值与远簇分位后续可从配置暴露
                    self.skeleton_selector = SkeletonSelector(SkeletonConfig(k=2, d_threshold_ratio=0.15, q_far=0.75))
                # 条件启用：仅当“远簇比例”超过阈值（例如>=30%）时启用骨干候选
                bs_pos = (self.config.base_station_x, self.config.base_station_y)
                dists = [math.hypot(ch.x - bs_pos[0], ch.y - bs_pos[1]) for ch in cluster_heads]
                if dists:
                    far_th = sorted(dists)[int(max(0, min(len(dists)-1, round(0.7*(len(dists)-1)))))]
                    far_ratio = sum(1 for d in dists if d >= far_th) / max(1, len(dists))
                else:
                    far_ratio = 0.0
                if far_ratio >= 0.3:
                    backbone_ids = self.skeleton_selector.select_backbone(
                        cluster_heads,
                        bs_pos,
                        math.hypot(self.config.area_width, self.config.area_height)
                    )
                else:
                    backbone_ids = []
            except Exception:
                backbone_ids = []
        backbone_set = set(backbone_ids)
        # 记录调试信息
        self._last_backbone_ids = list(backbone_ids)

        # 网关簇头选择（地标/换乘先验）：若骨干存在，则仅在骨干集合中选择网关
        use_gateway = getattr(self, 'enable_gateway', True)
        gateway_ids = []
        if use_gateway and cluster_heads:
            try:
                if not hasattr(self, 'gateway_selector'):
                    self.gateway_selector = GatewaySelector(GatewayConfig(k=1))
                chs_for_gateway = [ch for ch in cluster_heads if ch.id in backbone_set] if backbone_ids else cluster_heads
                gateway_ids = self.gateway_selector.select_gateways(
                    chs_for_gateway,
                    (self.config.base_station_x, self.config.base_station_y)
                )
            except Exception:
                gateway_ids = []
        gateway_set = set(gateway_ids)
        self._last_gateway_ids = list(gateway_ids)

        # 簇头向基站发送数据（优先骨干/网关接入）
        # 优先级：若有网关→使用网关；否则若有骨干→非骨干接入骨干，由骨干上行；否则直接上行
        if gateway_ids:
            # 建立CH索引
            ch_index = {ch.id: ch for ch in cluster_heads}
            # 计算网关对象
            gateways = [ch_index[g] for g in gateway_ids if g in ch_index]

            # 非网关 -> 最近网关
            for ch in cluster_heads:
                if ch.id in gateway_set:
                    continue
                if ch.current_energy <= 0:
                    continue
                # 找最近网关
                if gateways:
                    gw = min(gateways, key=lambda g: math.hypot(ch.x - g.x, ch.y - g.y))
                    d = math.hypot(ch.x - gw.x, ch.y - gw.y)
                    tx_energy = self.energy_model.calculate_transmission_energy(
                        self.config.packet_size * 8, d, ch.transmission_power
                    )
                    rx_energy = self.energy_model.calculate_reception_energy(self.config.packet_size * 8)
                    ch.current_energy -= tx_energy
                    gw.current_energy -= rx_energy
                    energy_consumed += tx_energy + rx_energy
                    packets_sent += 1
                    link_metrics = self.channel_model.calculate_link_metrics(ch.transmission_power, d, getattr(self, '_current_env_temp', 25.0), getattr(self, '_current_env_humidity', 0.5))
                    if random.random() < link_metrics['pdr']:
                        packets_received += 1
                    # 端到端：非网关成功到网关不算BS delivered，仅在网关->BS统计
                else:
                    # 回退：直接上行
                    distance_to_bs = math.hypot(ch.x - self.config.base_station_x, ch.y - self.config.base_station_y)
                    tx_energy = self.energy_model.calculate_transmission_energy(
                        self.config.packet_size * 8, distance_to_bs, ch.transmission_power
                    )
                    ch.current_energy -= tx_energy
                    energy_consumed += tx_energy
                    packets_sent += 1
                    link_metrics = self.channel_model.calculate_link_metrics(ch.transmission_power, distance_to_bs, getattr(self, '_current_env_temp', 25.0), getattr(self, '_current_env_humidity', 0.5))
                    if random.random() < link_metrics['pdr']:
                        packets_received += 1
                        # 端到端：聚合成功则按簇源数累加delivered
                        delivered = sum(1 for n in self.nodes if n.is_alive and n.cluster_id == ch.cluster_id)
                        self._last_bs_delivered_round += delivered

            # 网关 -> BS（危机轮保底：可冗余上行与功率提升）
            extra_uplink_used = 0
            self._last_extra_uplink_used = False
            for gw in gateways:
                if gw.current_energy <= 0:
                    continue
                distance_to_bs = math.hypot(gw.x - self.config.base_station_x, gw.y - self.config.base_station_y)
                # 危机轮：临时提升发射功率
                tx_power = gw.transmission_power
                if self.safety_fallback_enabled and self._consec_bad_rounds >= self.safety_T and self.safety_power_bump:
                    tx_power = tx_power + self.safety_power_bump_delta
                tx_energy = self.energy_model.calculate_transmission_energy(
                    self.config.packet_size * 8, distance_to_bs, tx_power
                )
                gw.current_energy -= tx_energy
                energy_consumed += tx_energy
                packets_sent += 1
                link_metrics = self.channel_model.calculate_link_metrics(tx_power, distance_to_bs, getattr(self, '_current_env_temp', 25.0), getattr(self, '_current_env_humidity', 0.5))
                success = (random.random() < link_metrics['pdr'])
                if success:
                    packets_received += 1
                    # 端到端：网关成功上行，累加该网关域内所有簇的源数
                    delivered = 0
                    for ch in cluster_heads:
                        # 如果该CH更靠近此网关（视作接入此网关）
                        closest_gw = min(gateways, key=lambda g: math.hypot(ch.x - g.x, ch.y - g.y)) if gateways else None
                        if closest_gw is gw:
                            delivered += sum(1 for n in self.nodes if n.is_alive and n.cluster_id == ch.cluster_id)
                    self._last_bs_delivered_round += delivered
                else:
                    # 危机轮保底：按概率允许一次冗余上行（仅一次）
                    if (self.safety_fallback_enabled and self._consec_bad_rounds >= self.safety_T and
                        self.safety_redundant_uplink and extra_uplink_used < self.safety_extra_uplink_max and random.random() < self.safety_redundant_prob):
                        extra_uplink_used += 1
                        self._last_extra_uplink_used = True
                        tx_energy2 = self.energy_model.calculate_transmission_energy(
                            self.config.packet_size * 8, distance_to_bs, tx_power
                        )
                        gw.current_energy -= tx_energy2
                        energy_consumed += tx_energy2
                        packets_sent += 1
                        link_metrics2 = self.channel_model.calculate_link_metrics(tx_power, distance_to_bs, getattr(self, '_current_env_temp', 25.0), getattr(self, '_current_env_humidity', 0.5))
                        if random.random() < link_metrics2['pdr']:
                            packets_received += 1
                            delivered = 0
                            for ch in cluster_heads:
                                closest_gw = min(gateways, key=lambda g: math.hypot(ch.x - g.x, ch.y - g.y)) if gateways else None
                                if closest_gw is gw:
                                    delivered += sum(1 for n in self.nodes if n.is_alive and n.cluster_id == ch.cluster_id)
                            self._last_bs_delivered_round += delivered
        else:
            if backbone_ids:
                # 使用骨干接入（v2）：仅远簇、且接入距离不超过阈值；骨干集合作为候选上行点（等价“少数网关”）
                ch_index = {ch.id: ch for ch in cluster_heads}
                backbones = [ch_index[b] for b in backbone_ids if b in ch_index]
                area_diag = math.hypot(self.config.area_width, self.config.area_height)
                assign = self.skeleton_selector.assign_to_backbone(cluster_heads, backbone_ids, (self.config.base_station_x, self.config.base_station_y), area_diag)
                # 非骨干CH：若被分配→骨干；否则→直接上行BS（避免遗漏端到端路径）
                for ch in cluster_heads:
                    if ch.id in backbone_ids:
                        continue
                    if ch.current_energy <= 0:
                        continue
                    bb_id = assign.get(ch.id)
                    if bb_id is not None:
                        bb = ch_index[bb_id]
                        d = math.hypot(ch.x - bb.x, ch.y - bb.y)
                        tx_energy = self.energy_model.calculate_transmission_energy(self.config.packet_size*8, d, ch.transmission_power)
                        rx_energy = self.energy_model.calculate_reception_energy(self.config.packet_size*8)
                        ch.current_energy -= tx_energy
                        bb.current_energy -= rx_energy
                        energy_consumed += tx_energy + rx_energy
                        packets_sent += 1
                        link_metrics = self.channel_model.calculate_link_metrics(ch.transmission_power, d, getattr(self, '_current_env_temp', 25.0), getattr(self, '_current_env_humidity', 0.5))
                        if random.random() < link_metrics['pdr']:
                            packets_received += 1
                    else:
                        # 直接上行至BS
                        distance_to_bs = math.hypot(ch.x - self.config.base_station_x, ch.y - self.config.base_station_y)
                        tx_energy = self.energy_model.calculate_transmission_energy(self.config.packet_size*8, distance_to_bs, ch.transmission_power)
                        ch.current_energy -= tx_energy
                        energy_consumed += tx_energy
                        packets_sent += 1
                        link_metrics = self.channel_model.calculate_link_metrics(ch.transmission_power, distance_to_bs, getattr(self, '_current_env_temp', 25.0), getattr(self, '_current_env_humidity', 0.5))
                        if random.random() < link_metrics['pdr']:
                            packets_received += 1
                            delivered = sum(1 for n in self.nodes if n.is_alive and n.cluster_id == ch.cluster_id)
                            self._last_bs_delivered_round += delivered
                # 骨干→BS（将骨干视作候选上行点：少数上行）
                for bb in backbones:
                    if bb.current_energy <= 0:
                        continue
                    distance_to_bs = math.hypot(bb.x - self.config.base_station_x, bb.y - self.config.base_station_y)
                    tx_energy = self.energy_model.calculate_transmission_energy(self.config.packet_size*8, distance_to_bs, bb.transmission_power)
                    bb.current_energy -= tx_energy
                    energy_consumed += tx_energy
                    packets_sent += 1
                    link_metrics = self.channel_model.calculate_link_metrics(bb.transmission_power, distance_to_bs)
                    if random.random() < link_metrics['pdr']:
                        packets_received += 1
                        # 端到端：累加此骨干域下被分配簇的源数
                        delivered = 0
                        for ch in cluster_heads:
                            if assign.get(ch.id) == bb.id:
                                delivered += sum(1 for n in self.nodes if n.is_alive and n.cluster_id == ch.cluster_id)
                        self._last_bs_delivered_round += delivered
            else:
                # 原直接上行逻辑
                for ch in cluster_heads:
                    if ch.current_energy > 0:
                        distance_to_bs = math.sqrt((ch.x - self.config.base_station_x)**2 + (ch.y - self.config.base_station_y)**2)
                        tx_energy = self.energy_model.calculate_transmission_energy(
                            self.config.packet_size * 8, distance_to_bs, ch.transmission_power
                        )
                        ch.current_energy -= tx_energy
                        energy_consumed += tx_energy
                        packets_sent += 1
                        link_metrics = self.channel_model.calculate_link_metrics(ch.transmission_power, distance_to_bs)
                        # 端到端统计：聚合包成功到达BS才计为received；源包为簇成员数+CH自身
                        if random.random() < link_metrics['pdr']:
                            packets_received += 1
                            # 端到端：聚合成功则按簇源数累加delivered
                            delivered = sum(1 for n in self.nodes if n.is_alive and n.cluster_id == ch.cluster_id)
                            self._last_bs_delivered_round += delivered

        # 更新统计信息
        self.total_energy_consumed += energy_consumed
        self.total_packets_sent += packets_sent
        self.total_packets_received += packets_received
        return packets_sent, packets_received, energy_consumed

    def _update_node_status(self):
        """更新节点状态"""
        for node in self.nodes:
            if node.current_energy <= 0:
                node.is_alive = False
                node.is_cluster_head = False

    def _collect_round_statistics(self, round_num: int, packets_sent: int,
                                packets_received: int, energy_consumed: float):
        """收集轮次统计信息"""

        alive_nodes = sum(1 for node in self.nodes if node.is_alive)
        cluster_heads = sum(1 for node in self.nodes if node.is_cluster_head and node.is_alive)
        remaining_energy = sum(node.current_energy for node in self.nodes if node.is_alive)

        round_stats = {
            'round': round_num,
            'alive_nodes': alive_nodes,
            'cluster_heads': cluster_heads,
            'remaining_energy': remaining_energy,
            'packets_sent': packets_sent,
            'packets_received': packets_received,
            'energy_consumed': energy_consumed,
            'pdr_hop_level': packets_received / packets_sent if packets_sent > 0 else 0,
            'source_packets_round': self._last_source_packets_round,
            'bs_delivered_round': self._last_bs_delivered_round,
            # 记录本轮环境与安全动作信息（便于外部分析与复现）
            'env_temperature_c': getattr(self, '_current_env_temp', 25.0),
            'env_humidity_ratio': getattr(self, '_current_env_humidity', 0.5),
            'safety_forced_direct': self._last_forced_direct,
            'safety_extra_uplink_used': self._last_extra_uplink_used
        }

        # 累加端到端统计
        self.source_packets_total += self._last_source_packets_round
        self.bs_delivered_total += self._last_bs_delivered_round
        self._last_source_packets_round = 0
        self._last_bs_delivered_round = 0

        self.round_statistics.append(round_stats)

        # 更新Safety Fallback状态
        if self.safety_fallback_enabled:
            round_end2end = (self._last_bs_delivered_round / self._last_source_packets_round) if self._last_source_packets_round > 0 else 0.0
            if round_end2end < self.safety_theta:
                self._consec_bad_rounds += 1
            else:
                self._consec_bad_rounds = 0

    def run_simulation(self, max_rounds: int, env_provider: Optional[Callable[[int], Tuple[float, float]]] = None) -> Dict[str, Any]:
        """运行Enhanced EEHFR仿真
        env_provider: 可选函数，每轮提供(temperature_c, humidity_ratio)
        """

        if self.verbose:
            print(f">>> 开始Integrated Enhanced EEHFR协议仿真 (最大轮数: {max_rounds})")
            print(f"   环境类型: {self.current_environment.value}")
            print(f"   节点数量: {len(self.nodes)}")

        start_time = time.time()

        for round_num in range(max_rounds):
            self.current_round = round_num # 更新当前轮数
            # 环境参数（若提供），用于本轮信道计算
            if env_provider is not None:
                try:
                    temp_c, hum_ratio = env_provider(round_num)
                except Exception:
                    temp_c, hum_ratio = 25.0, 0.5
            else:
                temp_c, hum_ratio = 25.0, 0.5
            self._current_env_temp = float(temp_c)
            self._current_env_humidity = float(hum_ratio)

            # 检查是否还有存活节点
            alive_nodes = [node for node in self.nodes if node.is_alive]
            if not alive_nodes:
                print(f"[INFO] 网络在第 {round_num} 轮结束生命周期")
                break

            # 选择簇头
            self._select_cluster_heads()

            # 形成簇
            self._form_clusters()

            # 数据传输
            packets_sent, packets_received, energy_consumed = self._perform_data_transmission()

            # 更新节点状态
            self._update_node_status()

            # 收集统计信息
            self._collect_round_statistics(round_num, packets_sent, packets_received, energy_consumed)

            # 定期输出进度
            if self.verbose and round_num % 100 == 0:
                remaining_energy = sum(node.current_energy for node in self.nodes if node.is_alive)
                print(f"   轮数 {round_num}: 存活节点 {len(alive_nodes)}, 剩余能量 {remaining_energy:.3f}J")

        execution_time = time.time() - start_time

        # 生成最终结果
        final_alive_nodes = sum(1 for node in self.nodes if node.is_alive)
        network_lifetime = len(self.round_statistics)

        if self.total_packets_sent > 0:
            energy_efficiency = self.total_packets_received / self.total_energy_consumed
            packet_delivery_ratio_hop = self.total_packets_received / self.total_packets_sent
        else:
            energy_efficiency = 0
            packet_delivery_ratio_hop = 0

        # 端到端PDR（聚合语义）
        pdr_end2end = (self.bs_delivered_total / self.source_packets_total) if self.source_packets_total > 0 else 0.0

        print(f"[SUCCESS] 仿真完成，网络在 {network_lifetime} 轮后结束")

        return {
            'protocol': 'Integrated_Enhanced_EEHFR',
            'network_lifetime': network_lifetime,
            'total_energy_consumed': self.total_energy_consumed,
            'final_alive_nodes': final_alive_nodes,
            'energy_efficiency': energy_efficiency,
            'packet_delivery_ratio': packet_delivery_ratio_hop,
            'packet_delivery_ratio_end2end': pdr_end2end,
            'execution_time': execution_time,
            'environment_type': self.current_environment.value,
            'round_statistics': self.round_statistics,
            'config': {
                'num_nodes': len(self.nodes),
                'initial_energy': self.config.initial_energy,
                'area_size': f"{self.config.area_width}x{self.config.area_height}",
                'packet_size': self.config.packet_size
            },
            'additional_metrics': {
                'total_packets_sent': self.total_packets_sent,
                'total_packets_received': self.total_packets_received,
                'source_packets_total': self.source_packets_total,
                'bs_delivered_total': self.bs_delivered_total,
                'average_cluster_heads': sum(stats['cluster_heads'] for stats in self.round_statistics) / len(self.round_statistics) if self.round_statistics else 0
            }
        }
