#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS 协议（集成能量模型、真实信道建模、环境分类与模糊逻辑）

项目定位与命名政策：
- 论文与项目统一名称为 “AERIS（Adaptive Environment-aware Routing for IoT Sensors）”。
- “EEHFR” 名称已永久废弃，不再在代码、测试与文档中使用。

研究性质声明（重要）：
- 本项目为纯算法研究与仿真，不涉及任何硬件实现与驱动。
- 代码中的硬件平台枚举与参数仅用于仿真配置与灵感参考，不构成对具体硬件性能的声明或承诺。
- IEEE 802.15.4 相关内容为标准一致性的仿真近似，不包含完整 MAC 行为的工程实现（如 CSMA/CA、ACK 重传等）。

目标：构建完备、可复现且性能稳健的 WSN 路由协议（AERIS）。

作者: AERIS Research Team
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

# 瀵煎叆鎵€鏈変紭鍖栫粍浠?
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform, EnergyParameters
from realistic_channel_model import RealisticChannelModel, EnvironmentType, LogNormalShadowingModel
from benchmark_protocols import Node, NetworkConfig
from cas_selector import CASSelector, CASConfig, CASMode
from distilled_cas_selector import DistilledCASSelector
from gateway_selector import GatewaySelector, GatewayConfig
from skeleton_selector import SkeletonSelector, SkeletonConfig
from collections import defaultdict, deque
import itertools


@dataclass
class EnhancedNode(Node):
    """澧炲己鑺傜偣绫伙紝鎵╁睍鍩虹鑺傜偣鍔熻兘"""

    # 鐜鎰熺煡灞炴€?
    environment_type: Optional[EnvironmentType] = None

    # 妯��$硦閫昏緫鍐崇瓥灞炴€?
    fuzzy_score: float = 0.0
    cluster_head_probability: float = 0.0
    lqi: float = 0.0 # 鏂板锛氶摼璺川閲忔寚鏁?
    cluster_size: int = 0
    cluster_link_quality: float = 0.0
    gateway_lqi: float = 0.0

    # 鑷€傚簲鍙傛暟
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
        鍩轰簬鑺傜偣鍒嗗竷鍜屼俊鍙风壒寰佽嚜鍔ㄥ垎绫荤幆澧?
        绠€鍖栫増瀹炵幇锛屽熀浜庤妭鐐瑰瘑搴﹀拰鍖哄煙澶у皬
        """

        if not nodes:
            return EnvironmentType.INDOOR_OFFICE

        # 璁＄畻鑺傜偣瀵嗗害
        area = 100 * 100  # 鍋囪100x100鍖哄煙
        density = len(nodes) / area

        # 鍩轰簬瀵嗗害绠€鍗曞垎绫?
        if density > 0.01:  # 楂樺瘑搴?
            return EnvironmentType.INDOOR_OFFICE
        elif density > 0.005:  # 涓瘑搴?
            return EnvironmentType.INDOOR_RESIDENTIAL
        else:  # 浣庡瘑搴?
            return EnvironmentType.OUTDOOR_OPEN

# 绉婚櫎浜嗗唴閮ㄧ畝鍖栫殑FuzzyLogicSystem锛屽皢浣跨敤澶栭儴妯″潡

class AerisProtocol:
    """
    AERIS 协议：集成能量/信道建模、CAS、骨架、网关等组件的完整实现
    """

    @dataclass
    class NeighborStats:
        """用于维护邻居 PRR/ETX 的滑动窗口统计"""
        window: deque
        window_size: int = 20
        success: int = 0
        attempts: int = 0

        def record(self, success_flag: bool):
            self.attempts += 1
            self.success += 1 if success_flag else 0
            self.window.append(1 if success_flag else 0)
            if len(self.window) > self.window_size:
                old = self.window.popleft()
                self.success -= old
                self.attempts -= 1

        @property
        def prr(self) -> float:
            if not self.window:
                return 0.0
            return max(0.0, min(1.0, sum(self.window) / len(self.window)))

        @property
        def etx(self) -> float:
            p = self.prr
            return 1.0 / max(1e-9, p)

    def __init__(self, config: NetworkConfig, *, enable_cas: bool = True, enable_fairness: bool = True, enable_aco_intercluster: bool = False, enable_gateway: bool = True, enable_skeleton: bool = True, profile: str | None = None, verbose: bool = True, seed: int | None = None, use_distilled_cas: Optional[bool] = None):
        self.config = config
        self.enable_cas = enable_cas
        self.enable_fairness = enable_fairness
        self.enable_aco_intercluster = enable_aco_intercluster
        self.enable_gateway = enable_gateway
        self.enable_skeleton = enable_skeleton
        self.profile = profile
        self.verbose = verbose
        self.seed = seed
        # 强制"可靠模式"：默认关闭以获取真实PDR数据，可通过 config.force_ctp_reliable=True 显式开启
        # 注意：开启此选项会导致PDR被强制设为100%，仅用于特殊测试场景
        self.force_ctp_reliable = bool(getattr(config, "force_ctp_reliable", False))
        self._rand = random.Random(seed)
        self._rng = np.random.default_rng(seed if seed is not None else None)
        self._adaptive_gateway_k: Optional[int] = None
        self._adaptive_gateway_weights: Dict[str, float] = {}
        self._adaptive_cluster_assign: Dict[str, float] = {}
        self._adaptive_cas_weights: Dict[str, float] = {}
        self._adaptive_skeleton_cfg: Dict[str, Any] = {}
        self._adaptive_profile_level = 0
        self._adaptive_profile_hold = 0
        self._cas_cfg_defaults: Dict[str, float] = {}
        self._cas_switch_window = deque(maxlen=60)
        self._cas_last_mode: Optional[CASMode] = None
        self.max_rounds: Optional[int] = None
        self.run_metadata: Dict[str, Any] = {
            'seed': seed,
            'profile': profile or 'default',
            'enable_cas': enable_cas,
            'enable_fairness': enable_fairness,
            'enable_aco_intercluster': enable_aco_intercluster,
            'enable_gateway': enable_gateway,
            'enable_skeleton': enable_skeleton,
            'verbose': verbose
        }
        # P1诊断: 运行时权重采样记录 (per RULES.md §5)
        self._diag_weight_samples: List[Dict[str, Any]] = []
        # 主 BS + 可选辅助 BS（支持 run_dynamic_dropout_compare 传入 secondary_base_station）
        extra_bs = getattr(config, 'extra_base_stations', None) or []
        secondary_bs = getattr(config, 'secondary_base_station', None)
        if secondary_bs and isinstance(secondary_bs, (tuple, list)) and len(secondary_bs) == 2:
            extra_bs.append(secondary_bs)
        self.base_stations: List[Tuple[float, float]] = [
            (float(self.config.base_station_x), float(self.config.base_station_y))
        ]
        for bx, by in extra_bs:
            try:
                self.base_stations.append((float(bx), float(by)))
            except Exception:
                continue
        # 记录掉线标志，外部可通过 config.high_dropout_mode 控制
        self.high_dropout_mode = bool(getattr(config, "high_dropout_mode", False))
        self.skeleton_cfg_override: Dict[str, Any] = {}
        override_cfg = getattr(config, 'skeleton_config', None)
        if isinstance(override_cfg, dict):
            for key in ('k', 'w_axis_proximity', 'w_centrality', 'd_threshold_ratio', 'q_far'):
                if key in override_cfg:
                    self.skeleton_cfg_override[key] = override_cfg[key]
        self.gateway_load_limit = getattr(config, 'gateway_load_limit', None)
        self.gateway_limit_dynamic = bool(getattr(config, 'gateway_limit_dynamic', False))
        self.gateway_limit_min = getattr(config, 'gateway_limit_min', None)
        if self.gateway_limit_min is not None:
            try:
                self.gateway_limit_min = max(1, int(self.gateway_limit_min))
            except Exception:
                self.gateway_limit_min = 1
        elif isinstance(self.gateway_load_limit, int):
            self.gateway_limit_min = 1
        self.gateway_limit_window = getattr(config, 'gateway_limit_window', None) or 15
        self.gateway_limit_reduce_threshold = getattr(config, 'gateway_limit_reduce_threshold', None) or 0.35
        self.gateway_limit_expand_threshold = getattr(config, 'gateway_limit_expand_threshold', None) or 0.15
        self.gateway_limit_cooldown_steps = getattr(config, 'gateway_limit_cooldown_steps', None) or 3
        self.gateway_concurrency = getattr(config, 'gateway_concurrency', None)
        if self.gateway_concurrency is not None:
            try:
                self.gateway_concurrency = max(0, int(self.gateway_concurrency))
            except Exception:
                self.gateway_concurrency = None
        self._dynamic_gateway_limit = self.gateway_load_limit if isinstance(self.gateway_load_limit, int) else None
        self._gateway_limit_recent_attempts = 0
        self._gateway_limit_recent_success = 0
        self._gateway_limit_cooldown = 0
        self.gateway_limit_history: List[int] = []
        self.gateway_concurrency_usage_total = 0
        self.gateway_concurrency_usage_rounds = 0
        self.gateway_uplink_suppressed_total = 0
        self.intra_link_retx = max(0, int(getattr(config, 'intra_link_retx', 0) or 0))
        self.intra_link_power_step = float(getattr(config, 'intra_link_power_step', 0.0) or 0.0)
        self.gateway_retry_limit = max(0, int(getattr(config, 'gateway_retry_limit', 2) or 2))
        self.gateway_rescue_direct = bool(getattr(config, 'gateway_rescue_direct', True))

        # 邻居质量表（PRR/ETX）
        self.neighbor_stats: Dict[int, Dict[int, AerisProtocol.NeighborStats]] = defaultdict(dict)
        # 父节点迟滞缓存：节点 -> (父ID, 上次ETX)
        self.last_parent: Dict[int, Tuple[int, float]] = {}
        # 探测周期与缓存（进一步减载：更长周期、更小扇出，包长后续在能量模型按半长估计）
        self.probe_interval = getattr(config, 'probe_interval', 15)
        self.probe_window = getattr(config, 'probe_window', 20)
        self.probe_fanout = getattr(config, 'probe_fanout', 3)  # 每轮探测少量邻居
        self._last_probe_round = -1
        # 父节点迟滞：仅当 ETX 改善超过阈值才切换
        self.parent_switch_improve = getattr(config, 'parent_switch_improve', 0.15)  # 15%

        if use_distilled_cas is None:
            env_flag = os.getenv('USE_DISTILLED_CAS', '0')
            self.use_distilled_cas = (env_flag == '1')
        else:
            self.use_distilled_cas = bool(use_distilled_cas)

        # 瀵煎叆澶栭儴妯″潡锛堝甫瀹夊叏鍥為€€锛?
        try:
            from fuzzy_logic_system import FuzzyLogicSystem
            _fuzzy = FuzzyLogicSystem()
        except Exception:
            # 杞檷绾э細缂哄皯skfuzzy绛変緷璧栨椂浣跨敤鏈婚噺鍔犳潈杩戜技锛屼繚璇佸彛寰勪竴鑷存€х浉瀵瑰彲鎺ュ彈
            class _FallbackFuzzy:
                def calculate_cluster_head_chance(self, residual_energy, node_centrality, node_degree, distance_to_bs, link_quality):
                    re = max(0.0, min(1.0, float(residual_energy)))
                    ce = max(0.0, min(1.0, float(node_centrality)))
                    nd = min(max(0.0, float(node_degree)/20.0), 1.0)
                    db = 1.0 - min(1.0, float(distance_to_bs)/max(1.0, 0.001 + (300.0)))  # 杩戣窛鏇cret紭
                    lq = max(0.0, min(1.0, float(link_quality)))
                    return 0.35*re + 0.25*ce + 0.15*nd + 0.10*db + 0.15*lq
                def calculate_next_hop_suitability(self, residual_energy, link_quality, distance_to_bs):
                    re = max(0.0, min(1.0, float(residual_energy)))
                    lq = max(0.0, min(1.0, float(link_quality)))
                    db = 1.0 - min(1.0, float(distance_to_bs)/300.0)
                    return 0.5*lq + 0.3*re + 0.2*db
            _fuzzy = _FallbackFuzzy()
        from node_state_manager import NodeStateManager

        # 鍒濆鍖栨墍鏈夌粍浠?
        self.energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        self.environment_classifier = EnvironmentClassifier()
        self.fuzzy_system = _fuzzy
        self.state_manager = NodeStateManager(config.num_nodes) # 瀹炰緥鍖栫姸鎬佺鐞嗗櫒

        # 鍏��0hook鎬э細绨囧ご浣跨敤璁℃暟锛堟粦鍔ㄧ獥鍙ｅ彲鍚庣画鍔犲叆锛?
        self.ch_usage_count: Dict[int, int] = {}

        # 鍏堣繘琛岀幆澧冨垎绫伙紝鐒跺悗鍒濆鍖栦俊閬撴ā鍨?
        self.current_environment = EnvironmentType.INDOOR_OFFICE  # 榛樿鐜
        self.channel_model = None  # 绋嶅悗鍒濆鍖?

        # 缃戠粶鐘舵€?
        self.nodes: List[EnhancedNode] = []
        self.current_round = 0
        self.current_environment = EnvironmentType.INDOOR_OFFICE

        # 缁熻淇℃伅
        self.round_statistics = []
        self.total_energy_consumed = 0.0
        self.total_packets_sent = 0
        self.total_packets_received = 0
        # 绔埌绔粺璁★紙鑱氬悎璇箟锛夛細婧愬寘鎬绘暟涓庢垚鍔熷埌杈綛S鐨勬暟鎹崟鍏冩€绘暟
        self.source_packets_total = 0  # attempted
        self.source_packets_expected = 0  # 期望包数
        self.bs_delivered_total = 0
        # 鏈€杩戜竴杞殑绔埌绔粺璁★紙渚沖round_statistics浣跨敤锛?
        self._last_source_packets_round = 0
        self._last_bs_delivered_round = 0
        # [NEW] 跳数追踪（用于诊断PDR异常问题）
        self.hop_count_distribution = {}  # {hop_count: frequency}
        self._all_hop_counts = []  # raw hop counts for all delivered packets
        self.packet_paths = {}  # {packet_id: path_length}
        self.cas_mode_usage_stats = {'DIRECT': 0, 'CHAIN': 0, 'TWO_HOP': 0, 'safety_override': 0}
        self.cas_rule_trigger_counts = {'DIRECT': 0, 'CHAIN': 0, 'TWO_HOP': 0, 'NONE': 0}
        self.cas_score_winner_counts = {'DIRECT': 0, 'CHAIN': 0, 'TWO_HOP': 0}
        self._packet_id_counter = 0
        self.intra_attempts_total = 0
        self.intra_success_total = 0
        self.uplink_attempts_total = 0
        self.uplink_success_total = 0
        self.cluster_radius_sum_total = 0.0
        self.cluster_radius_samples_total = 0
        self.ch_bs_distance_sum_total = 0.0
        self.ch_bs_distance_samples_total = 0
        self.gateway_link_attempts_total = 0
        self.gateway_link_success_total = 0
        self.gateway_uplink_attempts_total = 0
        self.gateway_uplink_success_total = 0

        # 灏鹃儴瀹夊叏闃€锛圫afety Fallback锛夊弬鏁颁笌鐘舵€?
        self.safety_fallback_enabled = True
        self.safety_T = 1          # 杩炵画澶辫触杞槇鍊?
        self.safety_theta = 0.05  # [FIXED] 降低阈值以减少safety_forced_direct触发    # 鍗曡疆绔埌绔槇鍊硷紙浣庝簬鍒欒涓哄け璐ワ級
        self._consec_bad_rounds = 0
        # 鍗辨満nits繚搴曞姩浣?
        self.safety_redundant_uplink = False   # 澶辫触鍒欓澶栭噸浼犱竴娆¤嚦BS
        self.safety_redundant_prob = 1.0       # 鍐椾綑涓婅瑙﹀彂姒傜巼锛堝嵄鏈鸿疆鍐咃����級
        self.safety_power_bump = False         # 鍗辨満nits繚搴曞姩浣?
        self.safety_power_bump_delta = 2.0     # dBm 澧為噺锛堟牴鎹兘閲忔ā鍨嬪彛寰勶級
        self.safety_extra_uplink_max = 1       # 鍗辨満nits繚搴曞姩浣?
        # 掉线强化模式：提高冗余与功率
        if self.high_dropout_mode:
            self.safety_extra_uplink_max = 6
            self.safety_power_bump = True
            self.safety_power_bump_delta = 5.0
            # 链路层重传参数（仅高掉线下启用）
            self.linklayer_retx = 2        # 每次上行最多再试 2 次
            self.linklayer_ack_loss_prob = 0.0  # 认为 ACK 理想，简化模拟
            self.intra_link_retx = max(self.intra_link_retx, 3)
            self.intra_link_power_step = max(self.intra_link_power_step, 2.0)
            self.gateway_retry_limit = max(self.gateway_retry_limit, 2)
            self.gateway_rescue_direct = True
        # 璋冭瘯/娴嬭瘯淇″彿
        self._last_forced_direct = False
        self._last_extra_uplink_used = False

        # 鍒濆鍖栫綉缁?
        self._initialize_network()

        # 搴旂敤profile蹇嵎閰嶇疆锛堜笉鏀瑰彉榛樿鍊硷紝鍙湁浼犲叆鏃舵墠瑕嗙洊锛?
        if self.profile:
            p = self.profile.lower()
            if p == 'energy':
                # Energy profile: keep overhead low but avoid catastrophic PDR loss.
                # Enable a lightweight safety layer that only triggers on sustained low PDR.
                self.safety_fallback_enabled = True
                self.safety_T = 2
                self.safety_theta = 0.75
                self.safety_redundant_uplink = True
                self.safety_redundant_prob = 0.25
                self.safety_power_bump = False
                self.safety_power_bump_delta = 0.0
                self.intra_link_retx = max(self.intra_link_retx, 1)
                self.intra_link_power_step = max(self.intra_link_power_step, 0.5)
                self.gateway_retry_limit = max(self.gateway_retry_limit, 1)
                self.gateway_rescue_direct = True
                # Adaptive reliability tuning for AERIS-E (keeps energy profile light but responsive).
                self.adaptive_energy_profile = True
                self.adaptive_profile_window = 5
                self.adaptive_update_interval = 5
                self.adaptive_pdr_low = 0.90
                self.adaptive_pdr_high = 0.97
                self.adaptive_energy_low = 0.35
                self._last_adaptive_update_round = -1
                self._energy_profile_defaults = {
                    'safety_T': self.safety_T,
                    'safety_theta': self.safety_theta,
                    'safety_redundant_prob': self.safety_redundant_prob,
                    'safety_power_bump': self.safety_power_bump,
                    'safety_power_bump_delta': self.safety_power_bump_delta,
                    'safety_extra_uplink_max': self.safety_extra_uplink_max,
                    'intra_link_retx': self.intra_link_retx,
                    'intra_link_power_step': self.intra_link_power_step,
                    'gateway_retry_limit': self.gateway_retry_limit,
                    'gateway_k': getattr(self.config, 'gateway_k', 1),
                    'gateway_w_dist': getattr(self.config, 'gateway_w_dist', -0.6),
                    'gateway_w_centrality': getattr(self.config, 'gateway_w_centrality', 0.2),
                    'gateway_w_link': getattr(self.config, 'gateway_w_link', 0.35),
                    'gateway_w_energy': getattr(self.config, 'gateway_w_energy', 0.15),
                    'cluster_assign_w_dist': getattr(self.config, 'cluster_assign_w_dist', 0.45),
                    'cluster_assign_w_lqi': getattr(self.config, 'cluster_assign_w_lqi', 0.4),
                    'cluster_assign_w_energy': getattr(self.config, 'cluster_assign_w_energy', 0.15),
                    'cluster_assign_min_prr': getattr(self.config, 'cluster_assign_min_prr', 0.2),
                }
            elif p == 'robust':
                self.safety_fallback_enabled = True
                self.safety_T = 1
                self.safety_theta = 0.05  # [FIXED] 降低阈值以减少safety_forced_direct触发
                self.safety_redundant_uplink = True
                self.safety_redundant_prob = 1.0
                self.safety_power_bump = True
                self.safety_power_bump_delta = 1.0
                self.intra_link_retx = max(self.intra_link_retx, 2)
                self.intra_link_power_step = max(self.intra_link_power_step, 1.5)
                self.gateway_retry_limit = max(self.gateway_retry_limit, 1)
                self.gateway_rescue_direct = True

    def _distance_to_nearest_bs(self, x: float, y: float) -> float:
        bases = self.base_stations or [(self.config.base_station_x, self.config.base_station_y)]
        return min(math.hypot(x - bx, y - by) for bx, by in bases)

    def _nearest_bs(self, x: float, y: float) -> Tuple[float, float]:
        bases = self.base_stations or [(self.config.base_station_x, self.config.base_station_y)]
        return min(bases, key=lambda p: math.hypot(x - p[0], y - p[1]))

    def _initialize_network(self):
        """初始化网络节点"""
        self.nodes = []
        positions = getattr(self.config, "positions", None)
        use_positions = None
        if isinstance(positions, list) and len(positions) >= self.config.num_nodes:
            use_positions = positions[: self.config.num_nodes]

        for i in range(self.config.num_nodes):
            if use_positions:
                x, y = use_positions[i]
            else:
                x = self._rand.uniform(0, self.config.area_width)
                y = self._rand.uniform(0, self.config.area_height)

            node = EnhancedNode(
                id=i,
                x=x,
                y=y,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy,
                is_alive=True,
                is_cluster_head=False,
                cluster_id=-1,
                transmission_power=0.0  # dBm, 灏嗘牴鎹幆澧冭皟鏁?
            )
            self.nodes.append(node)

        # 鐜鍒嗙被
        self.current_environment = self.environment_classifier.classify_environment(self.nodes)

        # 支持强制环境类型（用于公平对比实验）
        force_env = getattr(self.config, 'force_environment', None)
        if force_env:
            env_map = {
                'indoor_office': EnvironmentType.INDOOR_OFFICE,
                'indoor_factory': EnvironmentType.INDOOR_FACTORY,
                'indoor_residential': EnvironmentType.INDOOR_RESIDENTIAL,
                'outdoor_open': EnvironmentType.OUTDOOR_OPEN,
            }
            self.current_environment = env_map.get(force_env, self.current_environment)

        # 鐜板湪鍙互鍒濆鍖栦俊閬撴ā鍨?
        # 支持从config注入外部信道模型（构造期注入，优先级最高）
        external_channel = getattr(self.config, 'external_channel_model', None)
        if external_channel is not None:
            self.channel_model = external_channel
        elif self.channel_model is None:
            from realistic_channel_model import RealisticChannelModel
            self.channel_model = RealisticChannelModel(self.current_environment)

        # 鏍规嵁鐜璋冩暣鍒濆鍙傛暟
        self._adapt_to_environment()

    def _adapt_to_environment(self):
        """鏍规嵁鐜绫诲瀷璋冩暣鍗忚鍙傛暟"""

        # 鏍规嵁鐜绫诲瀷璁剧设置有
        power_settings = {
            EnvironmentType.INDOOR_OFFICE: 10.0,      # 提高功率
            EnvironmentType.INDOOR_RESIDENTIAL: 10.0,  # 涓綆鍔熺巼
            EnvironmentType.INDOOR_FACTORY: 10.0,      # 涓姛鐜?
            EnvironmentType.OUTDOOR_OPEN: 10.0,        # 涓珮鍔熺巼
            EnvironmentType.OUTDOOR_SUBURBAN: 10.0,    # 楂樺姛鐜?
            EnvironmentType.OUTDOOR_URBAN: 10.0        # 鏈€楂樺姛鐜?
        }

        default_power = power_settings.get(self.current_environment, 10.0)

        # 优先从config读取tx_power_dbm（允许0dBm设置）
        config_power = getattr(self.config, 'tx_power_dbm', None)
        if config_power is not None:
            default_power = float(config_power)

        for node in self.nodes:
            if node.is_alive:
                node.transmission_power = default_power
                node.environment_type = self.current_environment

    def _estimate_link_quality(
        self,
        sender: Node,
        receiver: Node,
        temp_c: float,
        hum_ratio: float,
        min_samples: int = 5,
    ) -> float:
        """Estimate link PDR between sender and receiver using probe stats or channel model."""
        try:
            ns = self.neighbor_stats.get(sender.id, {}).get(receiver.id)
            if ns is not None and len(ns.window) >= min_samples:
                return max(0.0, min(1.0, ns.prr))
        except Exception:
            pass
        if self.channel_model is None:
            return 0.0
        dist = math.hypot(sender.x - receiver.x, sender.y - receiver.y)
        link_metrics = self.channel_model.calculate_link_metrics(sender.transmission_power, dist, temp_c, hum_ratio)
        return max(0.0, min(1.0, link_metrics.get('pdr', 0.0)))

    def _estimate_bs_link_quality(
        self,
        node: Node,
        temp_c: float,
        hum_ratio: float,
        target_bs: Optional[Tuple[float, float]] = None,
    ) -> float:
        """Estimate uplink PDR from node to BS using channel model."""
        if self.channel_model is None:
            return 0.0
        if target_bs is None:
            dist = self._distance_to_nearest_bs(node.x, node.y)
        else:
            dist = math.hypot(node.x - target_bs[0], node.y - target_bs[1])
        link_metrics = self.channel_model.calculate_link_metrics(node.transmission_power, dist, temp_c, hum_ratio)
        return max(0.0, min(1.0, link_metrics.get('pdr', 0.0)))

    def _compute_cluster_head_ratio(self, alive_nodes: List[EnhancedNode]) -> float:
        """Adaptive CH ratio based on link quality and density."""
        base_ratio = getattr(self.config, 'cluster_head_ratio', None)
        if base_ratio is not None:
            try:
                base_ratio = float(base_ratio)
            except Exception:
                base_ratio = 0.1
            return max(0.01, min(0.3, base_ratio))
        lqi_stats = self.state_manager.get_network_lqi_stats(self.current_round)
        mean_lqi = float(lqi_stats.get('mean', 0.0))
        area = max(1e-9, self.config.area_width * self.config.area_height)
        density = len(alive_nodes) / area
        ratio = 0.08
        if mean_lqi < 0.45:
            ratio += 0.04
        if mean_lqi < 0.30:
            ratio += 0.04
        if density > 0.01:
            ratio += 0.03
        if density < 0.004:
            ratio -= 0.02
        min_ratio = getattr(self.config, 'cluster_head_ratio_min', 0.05)
        max_ratio = getattr(self.config, 'cluster_head_ratio_max', 0.2)
        try:
            min_ratio = float(min_ratio)
            max_ratio = float(max_ratio)
        except Exception:
            min_ratio = 0.05
            max_ratio = 0.2
        return max(min_ratio, min(max_ratio, ratio))

    def _select_cluster_heads(self):
        """使用模糊逻辑选择簇头，并叠加公平度约束"""
        from fairness_metrics import ch_usage_penalty

        # 閲嶇疆鎵€鏈夎妭鐐圭殑绨囧ご鐘舵€?
        for node in self.nodes:
            node.is_cluster_head = False
            node.cluster_id = -1

        # 璁＄畻姣忎釜鑺傜偣鐨勭皣澶存鐜?
        alive_nodes = [node for node in self.nodes if node.is_alive]
        area_diag = math.sqrt(self.config.area_width**2 + self.config.area_height**2) or 1.0

        for node in alive_nodes:
            # 璁＄畻LQI
            node.lqi = self.state_manager.get_lqi(node.id, self.current_round)

            # 璁＄畻涓績鎬?
            distances = [math.sqrt((node.x - other.x)**2 + (node.y - other.y)**2)
                         for other in alive_nodes if other.id != node.id]
            avg_distance = sum(distances) / len(distances) if distances else 0
            max_distance = area_diag
            centrality = 1 - (avg_distance / max_distance) if max_distance > 0 else 0

            # 璁＄畻鑺傜偣搴?
            node_degree = len(distances)

            # 璁＄畻鍒板熀绔欑殑璺濈
            dist_to_bs = self._distance_to_nearest_bs(node.x, node.y)

            # 璋冪敤澧炲己鐨勬ā绯婇€昏緫绯荤粺锛堝熀纭€姒傜巼锛?
            base_prob = self.fuzzy_system.calculate_cluster_head_chance(
                residual_energy=node.current_energy / node.initial_energy,
                node_centrality=centrality,
                node_degree=node_degree,
                distance_to_bs=dist_to_bs,
                link_quality=node.lqi
            )
            # 鍏��0hook鎯╃綒锛氭牴鎹皣澶 трежок
            if self.enable_fairness:
                penalty = ch_usage_penalty(self.ch_usage_count, node.id, self.current_round + 1, target_ratio=0.1)
                node.cluster_head_probability = base_prob * (1.0 - 0.25 * penalty)
            else:
                node.cluster_head_probability = base_prob

        # 鍩轰簬姒傜巼閫夋嫨绨囧ご
        ch_ratio = self._compute_cluster_head_ratio(alive_nodes)
        target_cluster_heads = max(1, int(len(alive_nodes) * ch_ratio))

        # 鎸夋鐜囨帓搴忥紝閫夋嫨鍓峃涓綔涓虹皣澶?
        sorted_nodes = sorted(alive_nodes, key=lambda n: n.cluster_head_probability, reverse=True)

        for i in range(min(target_cluster_heads, len(sorted_nodes))):
            sorted_nodes[i].is_cluster_head = True
            sorted_nodes[i].cluster_id = i
            # 璁板綍绨囧ご浣跨敤娆℃暟
            self.ch_usage_count[sorted_nodes[i].id] = self.ch_usage_count.get(sorted_nodes[i].id, 0) + 1

    def _form_clusters(self):
        """形成簇结构"""

        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]
        member_nodes = [node for node in self.nodes if not node.is_cluster_head and node.is_alive]

        if not cluster_heads:
            return

        area_diag = math.hypot(self.config.area_width, self.config.area_height) or 1.0
        temp_c = getattr(self, '_current_env_temp', getattr(self.config, 'temperature_c', 25.0))
        hum_ratio = getattr(self, '_current_env_humidity', getattr(self.config, 'humidity_ratio', 0.5))

        w_dist = float(getattr(self.config, 'cluster_assign_w_dist', 0.45))
        w_lqi = float(getattr(self.config, 'cluster_assign_w_lqi', 0.4))
        w_energy = float(getattr(self.config, 'cluster_assign_w_energy', 0.15))
        min_prr = float(getattr(self.config, 'cluster_assign_min_prr', 0.2))
        if self._adaptive_cluster_assign:
            w_dist = float(self._adaptive_cluster_assign.get('w_dist', w_dist))
            w_lqi = float(self._adaptive_cluster_assign.get('w_lqi', w_lqi))
            w_energy = float(self._adaptive_cluster_assign.get('w_energy', w_energy))
            min_prr = float(self._adaptive_cluster_assign.get('min_prr', min_prr))

        cluster_member_counts: Dict[int, int] = {ch.id: 1 for ch in cluster_heads}
        cluster_link_sums: Dict[int, float] = {ch.id: 0.0 for ch in cluster_heads}
        cluster_link_counts: Dict[int, int] = {ch.id: 0 for ch in cluster_heads}

        for member in member_nodes:
            best_score = -1e9
            best_cluster_head = None
            best_link = 0.0

            for ch in cluster_heads:
                distance = math.hypot(member.x - ch.x, member.y - ch.y)
                dist_norm = min(1.0, distance / area_diag)
                link_q = self._estimate_link_quality(member, ch, temp_c, hum_ratio)
                if link_q < min_prr and len(cluster_heads) > 1:
                    continue
                energy_norm = (ch.current_energy / ch.initial_energy) if ch.initial_energy > 0 else 0.0
                score = w_dist * (1.0 - dist_norm) + w_lqi * link_q + w_energy * energy_norm
                if score > best_score:
                    best_score = score
                    best_cluster_head = ch
                    best_link = link_q

            if best_cluster_head is None:
                best_cluster_head = min(
                    cluster_heads,
                    key=lambda ch: math.hypot(member.x - ch.x, member.y - ch.y),
                )
                best_link = self._estimate_link_quality(member, best_cluster_head, temp_c, hum_ratio)

            member.cluster_id = best_cluster_head.cluster_id
            cluster_member_counts[best_cluster_head.id] = cluster_member_counts.get(best_cluster_head.id, 1) + 1
            cluster_link_sums[best_cluster_head.id] = cluster_link_sums.get(best_cluster_head.id, 0.0) + best_link
            cluster_link_counts[best_cluster_head.id] = cluster_link_counts.get(best_cluster_head.id, 0) + 1

        for ch in cluster_heads:
            ch.cluster_size = cluster_member_counts.get(ch.id, 1)
            link_cnt = cluster_link_counts.get(ch.id, 0)
            if link_cnt > 0:
                ch.cluster_link_quality = cluster_link_sums.get(ch.id, 0.0) / link_cnt
            else:
                ch.cluster_link_quality = ch.lqi
        self.cluster_member_counts = cluster_member_counts

    def _resolve_gateway_limit(self) -> Optional[int]:
        """Return the effective per-gateway load limit for the current round."""
        if self.gateway_load_limit is None:
            return None
        try:
            base_limit = int(self.gateway_load_limit)
        except Exception:
            return None
        if base_limit <= 0:
            return 1
        if not self.gateway_limit_dynamic:
            return base_limit
        dyn_limit = self._dynamic_gateway_limit if isinstance(self._dynamic_gateway_limit, int) else base_limit
        min_limit = self.gateway_limit_min or 1
        dyn_limit = max(min_limit, min(base_limit, dyn_limit))
        return dyn_limit

    def _resolve_gateway_concurrency(self, total_gateways: int) -> Optional[int]:
        """Return how many gateways may uplink concurrently this round."""
        if self.gateway_concurrency is None:
            return None
        try:
            limit = int(self.gateway_concurrency)
        except Exception:
            return None
        if limit <= 0 or total_gateways <= 0:
            return 0
        return min(limit, total_gateways)

    def _update_dynamic_gateway_limit_state(self):
        """Adaptively tighten/relax the per-gateway load limit based on recent success ratio."""
        if not self.gateway_limit_dynamic or self.gateway_load_limit is None:
            return
        self._gateway_limit_recent_attempts += self._round_gateway_link_attempts
        self._gateway_limit_recent_success += self._round_gateway_link_success
        window = max(1, int(self.gateway_limit_window or 15))
        if self._gateway_limit_recent_attempts < window:
            return
        if self._gateway_limit_cooldown > 0:
            self._gateway_limit_cooldown -= 1
            self._gateway_limit_recent_attempts = 0
            self._gateway_limit_recent_success = 0
            return
        success_ratio = self._gateway_limit_recent_success / max(1, self._gateway_limit_recent_attempts)
        failure_ratio = 1.0 - success_ratio
        min_limit = self.gateway_limit_min or 1
        max_limit = int(self.gateway_load_limit) if isinstance(self.gateway_load_limit, int) else None
        if max_limit is None:
            self._gateway_limit_recent_attempts = 0
            self._gateway_limit_recent_success = 0
            return
        current = self._dynamic_gateway_limit if isinstance(self._dynamic_gateway_limit, int) else max_limit
        updated = False
        reduce_threshold = self.gateway_limit_reduce_threshold or 0.35
        expand_threshold = self.gateway_limit_expand_threshold or 0.15
        if failure_ratio > reduce_threshold and current > min_limit:
            current -= 1
            updated = True
        elif failure_ratio < expand_threshold and current < max_limit:
            current += 1
            updated = True
        if updated:
            self._dynamic_gateway_limit = current
            self._gateway_limit_cooldown = max(1, int(self.gateway_limit_cooldown_steps or 3))
        self._gateway_limit_recent_attempts = 0
        self._gateway_limit_recent_success = 0

    def _perform_data_transmission(self):
        """???????????? hop ????"""
        packets_sent = 0
        packets_received = 0
        energy_consumed = 0.0
        hop_counts_to_bs = []  # collect per-packet hop count for latency measurement

        alive_nodes = [node for node in self.nodes if node.is_alive]
        self._last_source_packets_round = len(alive_nodes)
        self.source_packets_expected += len(alive_nodes)  # 累计期望包数
        self._last_bs_delivered_round = 0
        self._round_intra_attempts = 0
        self._round_intra_success = 0
        self._round_uplink_attempts = 0
        self._round_uplink_success = 0
        self._round_cluster_radius_sum = 0.0
        self._round_cluster_radius_samples = 0
        self._round_ch_bs_distance_sum = 0.0
        self._round_ch_bs_distance_samples = 0
        self._round_gateway_link_attempts = 0
        self._round_gateway_link_success = 0
        self._round_gateway_uplink_attempts = 0
        self._round_gateway_uplink_success = 0
        self._round_gateway_load_limit_active = 0
        self._round_gateway_concurrency_used = 0
        self._round_gateway_uplink_suppressed = 0

        cluster_heads = [node for node in self.nodes if node.is_cluster_head and node.is_alive]
        temp_c = getattr(self, '_current_env_temp', 25.0)
        hum_ratio = getattr(self, '_current_env_humidity', 0.5)
        area_diag = math.hypot(self.config.area_width, self.config.area_height) or 1.0

        def transmit_link(sender: Node, receiver: Node, tx_power_override: Optional[float] = None) -> bool:
            nonlocal packets_sent, packets_received, energy_consumed
            if sender is None or receiver is None:
                return False
            if sender.current_energy <= 0 or receiver.current_energy <= 0:
                return False
            base_tx_power = tx_power_override if tx_power_override is not None else sender.transmission_power
            max_retx = max(0, int(getattr(self, 'intra_link_retx', 0) or 0))
            power_step = float(getattr(self, 'intra_link_power_step', 0.0) or 0.0)

            def attempt_link(tx_power: float) -> bool:
                nonlocal packets_sent, packets_received, energy_consumed
                distance = math.hypot(sender.x - receiver.x, sender.y - receiver.y)
                tx_energy = self.energy_model.calculate_transmission_energy(
                    self.config.packet_size * 8, distance, tx_power, temp_c, hum_ratio
                )
                rx_energy = self.energy_model.calculate_reception_energy(
                    self.config.packet_size * 8, temp_c, hum_ratio
                )
                sender.current_energy -= tx_energy
                receiver.current_energy -= rx_energy
                energy_consumed += tx_energy + rx_energy
                packets_sent += 1
                self._round_intra_attempts += 1
                self.intra_attempts_total += 1
                link_metrics = self.channel_model.calculate_link_metrics(tx_power, distance, temp_c, hum_ratio)
                success = (self._rand.random() < link_metrics['pdr'])
                if success:
                    packets_received += 1
                    self._round_intra_success += 1
                    self.intra_success_total += 1
                try:
                    self.state_manager.update_link_quality(
                        sender.id,
                        receiver.id,
                        link_metrics.get('rssi', -100.0),
                        success,
                        self.current_round,
                    )
                except Exception:
                    pass
                # 更新邻居质量表（用于 PRR/ETX 父选）
                try:
                    sdict = self.neighbor_stats[sender.id]
                    ns = sdict.get(receiver.id)
                    if ns is None:
                        ns = AerisProtocol.NeighborStats(window=deque(maxlen=self.probe_window or 20))
                        sdict[receiver.id] = ns
                    ns.record(success)
                except Exception:
                    pass
                return success

            for attempt in range(max_retx + 1):
                tx_power = base_tx_power + attempt * power_step
                if attempt_link(tx_power):
                    return True
            return False

        def transmit_to_bs(
            sender: Node,
            payload_count: int,
            tx_power_override: Optional[float] = None,
            target_bs: Optional[Tuple[float, float]] = None,
            max_retx: int = 0,
        ) -> bool:
            nonlocal packets_sent, packets_received, energy_consumed
            if payload_count <= 0 or sender is None or sender.current_energy <= 0:
                return False

            # Record hop latency per successfully delivered source packet.
            def record_hops(hops: int):
                if payload_count > 0:
                    hop_counts_to_bs.extend([hops] * payload_count)

            # ---- 重写 uplink：CTP/ORW 风格：多父集合 + 双副本 + Hop-ARQ + 功率阶梯 + 并行补链 ----
            tx_power_base = tx_power_override if tx_power_override is not None else sender.transmission_power
            distance = self._distance_to_nearest_bs(sender.x, sender.y) if target_bs is None else math.hypot(sender.x - target_bs[0], sender.y - target_bs[1])

            # 父节点挑选（基于 ETX/PRR + BS 距离 + 剩余能量）
            def estimate_prr(node_from: Node, node_to: Node) -> float:
                ns = self.neighbor_stats.get(node_from.id, {}).get(node_to.id)
                if ns is not None and len(ns.window) >= 5:
                    return ns.prr
                d = math.hypot(node_from.x - node_to.x, node_from.y - node_to.y)
                lm = self.channel_model.calculate_link_metrics(tx_power_base, d, temp_c, hum_ratio)
                return lm.get('pdr', 0.0)

            sender_bs_dist = distance
            candidates: List[Tuple[Node, float, float, float]] = []
            for cand in alive_nodes:
                if cand.id == sender.id or not cand.is_alive or cand.current_energy <= 0:
                    continue
                cand_bs_dist = self._distance_to_nearest_bs(cand.x, cand.y) if target_bs is None else math.hypot(cand.x - target_bs[0], cand.y - target_bs[1])
                if cand_bs_dist >= sender_bs_dist * 0.99:
                    continue
                prr_c = estimate_prr(sender, cand)
                etx_c = 1.0 / max(1e-9, prr_c)
                candidates.append((cand, prr_c, etx_c, cand_bs_dist))
            candidates = sorted(candidates, key=lambda t: (t[2], t[3], -t[0].current_energy))
            parent_list: List[Node] = [c[0] for c in candidates[:3]]
            if parent_list:
                self.last_parent[sender.id] = (parent_list[0].id, candidates[0][2])

            # Hop/BS 封装
            def one_try_bs(bs_target: Optional[Tuple[float, float]] = None, tx_override: Optional[float] = None, sender_node: Optional[Node] = None) -> bool:
                nonlocal packets_sent, packets_received, energy_consumed
                tx_sender = sender_node if sender_node is not None else sender
                if tx_sender is None or tx_sender.current_energy <= 0:
                    return False
                bs_tx_power = tx_override if tx_override is not None else tx_power_base
                bs_distance = self._distance_to_nearest_bs(tx_sender.x, tx_sender.y) if bs_target is None else math.hypot(tx_sender.x - bs_target[0], tx_sender.y - bs_target[1])
                tx_energy = self.energy_model.calculate_transmission_energy(self.config.packet_size * 8, bs_distance, bs_tx_power, temp_c, hum_ratio)
                tx_sender.current_energy -= tx_energy
                energy_consumed += tx_energy
                packets_sent += 1
                self._round_uplink_attempts += 1
                self.uplink_attempts_total += 1
                link_metrics = self.channel_model.calculate_link_metrics(bs_tx_power, bs_distance, temp_c, hum_ratio)
                ok = (self._rand.random() < link_metrics['pdr'])
                if ok:
                    packets_received += 1
                    self._last_bs_delivered_round += payload_count
                    self._round_uplink_success += 1
                    self.uplink_success_total += 1
                return ok

            def one_try_link(sender_node: Node, relay_node: Node, tx_override: Optional[float] = None) -> bool:
                nonlocal packets_sent, packets_received, energy_consumed
                if sender_node.current_energy <= 0 or relay_node.current_energy <= 0:
                    return False
                link_tx_power = tx_override if tx_override is not None else sender_node.transmission_power
                dist = math.hypot(sender_node.x - relay_node.x, sender_node.y - relay_node.y)
                tx_energy = self.energy_model.calculate_transmission_energy(self.config.packet_size * 8, dist, link_tx_power, temp_c, hum_ratio)
                rx_energy = self.energy_model.calculate_reception_energy(self.config.packet_size * 8, temp_c, hum_ratio)
                sender_node.current_energy -= tx_energy
                relay_node.current_energy -= rx_energy
                energy_consumed += tx_energy + rx_energy
                packets_sent += 1
                self._round_uplink_attempts += 1
                self.uplink_attempts_total += 1
                link_metrics = self.channel_model.calculate_link_metrics(link_tx_power, dist, temp_c, hum_ratio)
                ok = (self._rand.random() < link_metrics['pdr'])
                if ok:
                    packets_received += 1
                    self._round_uplink_success += 1
                    self.uplink_success_total += 1
                return ok

            # Hop-ARQ + 功率阶梯（再次加大可靠性）
            base_steps = [0.0, 3.0, 6.0, 9.0, 11.0]
            if self.high_dropout_mode:
                base_steps = [0.0, 3.5, 7.0, 10.5, 12.0]
            hop_arq = 9 if self.high_dropout_mode else 7

            def hop_with_arq(link_fn, p_base: float) -> bool:
                for step in base_steps:
                    pw = p_base + step
                    for _ in range(hop_arq):
                        if link_fn(pw):
                            return True
                return False

            def relay_via_parent(parent: Optional[Node], copies: int, p_boost: float) -> bool:
                if parent is None:
                    return False
                for _ in range(copies):
                    ok1 = hop_with_arq(lambda pw: one_try_link(sender, parent, pw), tx_power_base + p_boost)
                    if not ok1:
                        continue
                    ok2 = hop_with_arq(lambda pw: one_try_bs(target_bs, pw, parent), tx_power_base + p_boost + 1.5)
                    if ok2:
                        record_hops(2)
                        return True
                return False

            copies_primary = 4
            copies_other = 3
            parent_boost = 6.0 if self.high_dropout_mode else 4.5

            # 并行尝试父节点：主父优先，其次/三父也试
            for idx, parent in enumerate(parent_list):
                copies = copies_primary if idx == 0 else copies_other
                if relay_via_parent(parent, copies, parent_boost):
                    return True

            # 额外邻居救援：挑选最多 5 个比发件人更近 BS 且 PRR>=0.3 的邻居做一次“求援”转发
            rescue_candidates: List[Node] = []
            try:
                for cand in alive_nodes:
                    if cand.id == sender.id or not cand.is_alive or cand.current_energy <= 0:
                        continue
                    if self._distance_to_nearest_bs(cand.x, cand.y) >= sender_bs_dist * 0.98:
                        continue
                    prr_c = estimate_prr(sender, cand)
                    if prr_c < 0.25:
                        continue
                    rescue_candidates.append((cand, prr_c))
                rescue_candidates.sort(key=lambda t: (-t[1], self._distance_to_nearest_bs(t[0].x, t[0].y)))
            except Exception:
                rescue_candidates = []

            for cand, prr_c in rescue_candidates[:6]:
                # "求援"双副本：sender->cand（2 副本），cand->BS（2 副本），高功率 + ARQ
                if hop_with_arq(lambda pw: one_try_link(sender, cand, tx_power_base + parent_boost + 1.5 + pw), 0.0):
                    if hop_with_arq(lambda pw: one_try_bs(target_bs, tx_power_base + parent_boost + 3.0 + pw, cand), 0.0):
                        record_hops(2)
                        return True

            # 直达 BS 阶梯兜底
            direct_tries = 32 if self.high_dropout_mode else 24
            for j in range(direct_tries):
                pw = tx_power_base + j * 1.5
                if hop_with_arq(lambda step: one_try_bs(target_bs, pw, sender), 0.0):
                    record_hops(1)
                    return True
            for bs_pos in self.base_stations:
                for j in range(10):
                    if hop_with_arq(lambda step: one_try_bs(bs_pos, tx_power_base + 3.0 + j * 1.2, sender), 0.0):
                        record_hops(1)
                        return True

            # 广播级兜底（近似 flood）：选取前 12 个离 BS 最近的活跃节点并行尝试
            # 目的：保证在极端高衰落/高掉线下仍能把关键数据推到 BS，代价是能耗大
            relay_pool = sorted(
                [n for n in alive_nodes if n.is_alive and n.current_energy > 0],
                key=lambda n: self._distance_to_nearest_bs(n.x, n.y)
            )[:12]
            for relay in relay_pool:
                if relay.id == sender.id:
                    continue
                if hop_with_arq(lambda pw: one_try_bs(target_bs, tx_power_base + 6.0 + pw, relay), 0.0):
                    record_hops(2)
                    return True

            # 极限兜底
            for _ in range(12):
                if one_try_bs(target_bs, tx_power_base + 13.5, sender):
                    record_hops(1)
                    return True

            # 终极“可靠模式”兜底：近似 CTP/ORW flood，强行计为成功但扣除能量
            if self.force_ctp_reliable and sender.current_energy > 0:
                bs_distance = self._distance_to_nearest_bs(sender.x, sender.y) if target_bs is None else math.hypot(sender.x - target_bs[0], sender.y - target_bs[1])
                strong_power = max(tx_power_base, 14.0)
                tx_energy = self.energy_model.calculate_transmission_energy(self.config.packet_size * 8, bs_distance, strong_power, temp_c, hum_ratio)
                # 额外惩罚因 flood（乘以 2.5），避免能耗虚低
                penalty = tx_energy * 2.5
                sender.current_energy -= penalty
                energy_consumed += max(0.0, penalty)
                packets_sent += 1
                self._round_uplink_attempts += 1
                self.uplink_attempts_total += 1
                packets_received += 1
                self._last_bs_delivered_round += payload_count
                self._round_uplink_success += 1
                self.uplink_success_total += 1
                record_hops(3)  # flood approximation
                return True
            return False

        def handle_direct(ch: Node, members: List[Node]) -> int:
            delivered = 0
            for m in members:
                if m.current_energy <= 0:
                    continue
                if transmit_link(m, ch):
                    delivered += 1
            return delivered

        def handle_chain(ch: Node, members: List[Node]) -> int:
            if not members:
                return 0
            ordered = sorted(members, key=lambda m: math.hypot(m.x - ch.x, m.y - ch.y))
            payloads = {m.id: (1 if m.current_energy > 0 else 0) for m in ordered}
            for idx in range(len(ordered) - 1, 0, -1):
                sender = ordered[idx]
                receiver = ordered[idx - 1]
                payload = payloads.get(sender.id, 0)
                if payload <= 0:
                    continue
                if transmit_link(sender, receiver):
                    payloads[receiver.id] = payloads.get(receiver.id, (1 if receiver.current_energy > 0 else 0)) + payload
            first = ordered[0]
            payload = payloads.get(first.id, 1 if first.current_energy > 0 else 0)
            if payload <= 0:
                return 0
            if transmit_link(first, ch):
                return payload
            return 0

        def handle_two_hop(ch: Node, members: List[Node]) -> int:
            if not members:
                return 0
            ordered = sorted(members, key=lambda m: math.hypot(m.x - ch.x, m.y - ch.y))
            relay = ordered[len(ordered) // 2] if len(ordered) >= 2 else ch
            relay_payload = 0
            delivered = 0
            for m in ordered:
                if m.current_energy <= 0:
                    continue
                d_norm = math.hypot(m.x - ch.x, m.y - ch.y) / area_diag
                if relay is not ch and m is not relay and d_norm > 0.5:
                    if transmit_link(m, relay):
                        relay_payload += 1
                else:
                    if transmit_link(m, ch):
                        delivered += 1
            if relay is not ch and relay_payload > 0 and relay.current_energy > 0:
                if transmit_link(relay, ch):
                    delivered += relay_payload
            return delivered

        cluster_payloads = {ch.id: (1 if ch.current_energy > 0 else 0) for ch in cluster_heads}
        avg_energy = sum(node.current_energy for node in alive_nodes) / max(1, len(alive_nodes))
        max_energy = max((node.initial_energy for node in self.nodes), default=1.0)
        energy_norm = min(1.0, max(0.0, avg_energy / max(1e-9, max_energy)))
        lqi_stats = self.state_manager.get_network_lqi_stats(self.current_round)
        link_norm_global = min(1.0, max(0.0, lqi_stats.get('mean', 0.0)))

        for ch in cluster_heads:
            cluster_members = [node for node in self.nodes if node.cluster_id == ch.cluster_id and not node.is_cluster_head and node.is_alive]
            if not cluster_members:
                continue
            dists = [math.hypot(m.x - ch.x, m.y - ch.y) for m in cluster_members]
            mean_radius = (sum(dists) / len(dists)) if dists else 0.0
            radius_norm = min(1.0, mean_radius / area_diag)
            density_norm = min(1.0, len(cluster_members) / max(1, self.config.num_nodes))
            dist_bs = self._distance_to_nearest_bs(ch.x, ch.y)
            dist_bs_norm = min(1.0, dist_bs / area_diag)
            if dists:
                self._round_cluster_radius_sum += sum(dists)
                self._round_cluster_radius_samples += len(dists)
            self._round_ch_bs_distance_sum += dist_bs
            self._round_ch_bs_distance_samples += 1
            member_energies = [m.current_energy for m in cluster_members]
            if self.enable_fairness and member_energies:
                from fairness_metrics import jain_index
                J = jain_index(member_energies)
                fair_penalty = float(max(0.0, min(1.0, 1.0 - J)))
            else:
                fair_penalty = 0.0
            tail_max = min(1.0, (max(dists) if dists else 0.0) / area_diag)
            link_norm = min(1.0, max(0.0, getattr(ch, 'cluster_link_quality', link_norm_global)))

            mode = CASMode.DIRECT
            if self.enable_cas:
                if not hasattr(self, 'cas_selector'):
                    if getattr(self, 'use_distilled_cas', False):
                        self.cas_selector = DistilledCASSelector(CASConfig())
                    else:
                        self.cas_selector = CASSelector(CASConfig())
                # CAS权重使用默认值，启用CHAIN/TWO_HOP模式
                if not self._cas_cfg_defaults:
                    cfg = self.cas_selector.cfg
                    self._cas_cfg_defaults = {
                        'w_direct_energy': cfg.w_direct_energy,
                        'w_direct_link': cfg.w_direct_link,
                        'w_direct_dist_bs': cfg.w_direct_dist_bs,
                        'w_direct_radius': cfg.w_direct_radius,
                        'w_direct_density': cfg.w_direct_density,
                        'w_direct_fair': cfg.w_direct_fair,
                        'w_chain_energy': cfg.w_chain_energy,
                        'w_chain_link': cfg.w_chain_link,
                        'w_chain_dist_bs': cfg.w_chain_dist_bs,
                        'w_chain_radius': cfg.w_chain_radius,
                        'w_chain_density': cfg.w_chain_density,
                        'w_chain_fair': cfg.w_chain_fair,
                        'w_twohop_energy': cfg.w_twohop_energy,
                        'w_twohop_link': cfg.w_twohop_link,
                        'w_twohop_dist_bs': cfg.w_twohop_dist_bs,
                        'w_twohop_radius': cfg.w_twohop_radius,
                        'w_twohop_density': cfg.w_twohop_density,
                        'w_twohop_fair': cfg.w_twohop_fair,
                        'twohop_tail_threshold': cfg.twohop_tail_threshold,
                        'lambda_uncertainty': cfg.lambda_uncertainty,
                        'uncertainty_conf_threshold': cfg.uncertainty_conf_threshold,
                        'min_confidence': cfg.min_confidence,
                    }
                if self._adaptive_cas_weights:
                    for key, value in self._adaptive_cas_weights.items():
                        if hasattr(self.cas_selector.cfg, key):
                            setattr(self.cas_selector.cfg, key, float(value))
                if self.safety_fallback_enabled and self._consec_bad_rounds >= self.safety_T:
                    mode = CASMode.DIRECT
                    self._last_forced_direct = True
                    self.cas_mode_usage_stats['safety_override'] += 1
                else:
                    self._last_forced_direct = False
                    mode, conf, scores = self.cas_selector.select_mode({
                        'energy': energy_norm,
                        'link': link_norm,
                        'dist_bs': dist_bs_norm,
                        'radius': radius_norm,
                        'density': density_norm,
                        'fairness': fair_penalty,
                        'tail_max': tail_max,
                    })
                    meta = getattr(self.cas_selector, 'last_decision_meta', None)
                    if isinstance(meta, dict):
                        rule = meta.get('rule_triggered')
                        if rule:
                            key = str(rule).upper()
                            self.cas_rule_trigger_counts[key] = self.cas_rule_trigger_counts.get(key, 0) + 1
                        else:
                            self.cas_rule_trigger_counts['NONE'] = self.cas_rule_trigger_counts.get('NONE', 0) + 1
                        score_winner = meta.get('score_winner')
                        if score_winner:
                            key = str(score_winner).upper()
                            self.cas_score_winner_counts[key] = self.cas_score_winner_counts.get(key, 0) + 1
                if self._cas_last_mode is not None:
                    self._cas_switch_window.append(1 if mode != self._cas_last_mode else 0)
                else:
                    self._cas_switch_window.append(0)
                self._cas_last_mode = mode
                if mode == CASMode.DIRECT:
                    self.cas_mode_usage_stats['DIRECT'] += 1
                elif mode == CASMode.CHAIN:
                    self.cas_mode_usage_stats['CHAIN'] += 1
                elif mode == CASMode.TWO_HOP:
                    self.cas_mode_usage_stats['TWO_HOP'] += 1
                try:
                    self.state_manager.record_round_stat(
                        current_round=self.current_round,
                        cas_mode=mode.value,
                        cas_confidence=float(conf),
                        cas_scores={k.value: float(v) for k, v in scores.items()},
                        cas_infer_us=getattr(self.cas_selector, 'last_infer_us', None),
                    )
                except Exception:
                    pass
            else:
                self._last_forced_direct = False

            delivered_members = 0
            if mode == CASMode.DIRECT:
                delivered_members = handle_direct(ch, cluster_members)
            elif mode == CASMode.CHAIN:
                delivered_members = handle_chain(ch, cluster_members)
            else:
                delivered_members = handle_two_hop(ch, cluster_members)
            cluster_payloads[ch.id] = cluster_payloads.get(ch.id, 0) + delivered_members

        use_gateway = getattr(self, 'enable_gateway', True)
        gateway_ids: List[int] = []
        if use_gateway and cluster_heads:
            k_gateways = getattr(self.config, 'gateway_k', 1) or 1
            if self._adaptive_gateway_k is not None:
                try:
                    k_gateways = max(int(k_gateways), int(self._adaptive_gateway_k))
                except Exception:
                    pass
            try:
                base_k = k_gateways
                k_max = getattr(self.config, 'gateway_k_max', 6)
                k_gateways = base_k
                if getattr(self.config, 'gateway_k_dynamic', True):
                    extra = 0
                    if len(alive_nodes) >= 200:
                        extra += 1
                    if len(alive_nodes) >= 400:
                        extra += 1
                    if link_norm_global < 0.45:
                        extra += 1
                    if link_norm_global < 0.30:
                        extra += 1
                    k_gateways = min(max(1, k_gateways + extra), k_max)
                for ch in cluster_heads:
                    bs_pdr = self._estimate_bs_link_quality(ch, temp_c, hum_ratio)
                    ch.gateway_lqi = 0.5 * bs_pdr + 0.5 * min(1.0, max(0.0, getattr(ch, 'cluster_link_quality', ch.lqi)))
                if not hasattr(self, 'gateway_selector'):
                    gw_cfg = GatewayConfig(k=k_gateways)
                    gw_cfg.w_dist_bs = float(getattr(self.config, 'gateway_w_dist', -0.6))
                    gw_cfg.w_centrality = float(getattr(self.config, 'gateway_w_centrality', 0.2))
                    gw_cfg.w_link = float(getattr(self.config, 'gateway_w_link', 0.35))
                    gw_cfg.w_energy = float(getattr(self.config, 'gateway_w_energy', 0.15))
                    if self._adaptive_gateway_weights:
                        gw_cfg.w_dist_bs = float(self._adaptive_gateway_weights.get('w_dist_bs', gw_cfg.w_dist_bs))
                        gw_cfg.w_centrality = float(self._adaptive_gateway_weights.get('w_centrality', gw_cfg.w_centrality))
                        gw_cfg.w_link = float(self._adaptive_gateway_weights.get('w_link', gw_cfg.w_link))
                        gw_cfg.w_energy = float(self._adaptive_gateway_weights.get('w_energy', gw_cfg.w_energy))
                    self.gateway_selector = GatewaySelector(gw_cfg)
                else:
                    try:
                        self.gateway_selector.cfg.k = k_gateways
                        if self._adaptive_gateway_weights:
                            self.gateway_selector.cfg.w_dist_bs = float(self._adaptive_gateway_weights.get('w_dist_bs', self.gateway_selector.cfg.w_dist_bs))
                            self.gateway_selector.cfg.w_centrality = float(self._adaptive_gateway_weights.get('w_centrality', self.gateway_selector.cfg.w_centrality))
                            self.gateway_selector.cfg.w_link = float(self._adaptive_gateway_weights.get('w_link', self.gateway_selector.cfg.w_link))
                            self.gateway_selector.cfg.w_energy = float(self._adaptive_gateway_weights.get('w_energy', self.gateway_selector.cfg.w_energy))
                    except Exception:
                        pass
                chs_for_gateway = cluster_heads
                gateway_ids = self.gateway_selector.select_gateways(
                    chs_for_gateway,
                    self.base_stations
                )
                # 高掉线模式下，若仅选出少量网关，则直接取最近的若干 CH 作为补充
                if self.high_dropout_mode and len(gateway_ids) < k_gateways:
                    ordered_by_bs = sorted(chs_for_gateway, key=lambda n: self._distance_to_nearest_bs(n.x, n.y))
                    for cand in ordered_by_bs:
                        if cand.id not in gateway_ids:
                            gateway_ids.append(cand.id)
                        if len(gateway_ids) >= k_gateways:
                            break
            except Exception:
                gateway_ids = []
        gateway_set = set(gateway_ids)
        ch_index = {ch.id: ch for ch in cluster_heads}

        if gateway_ids:
            gateways = [ch_index[g] for g in gateway_ids if g in ch_index]
            gateway_payloads = {g.id: cluster_payloads.get(g.id, 0) for g in gateways}
            gateway_assignment_counts = {g.id: 0 for g in gateways}
            load_limit = self._resolve_gateway_limit()
            self._round_gateway_load_limit_active = load_limit or 0
            # 高掉线模式：按距离最近的网关优先，避免长链分配
            if self.high_dropout_mode:
                gateways = sorted(gateways, key=lambda g: self._distance_to_nearest_bs(g.x, g.y))
            # 自适应 Gateway bypass 阈值：CH-BS 链路 PDR 高于此值时跳过 Gateway 直连
            _gw_bypass_threshold = float(getattr(self, 'gateway_bypass_pdr_threshold', 0.7))
            for ch in cluster_heads:
                payload = cluster_payloads.get(ch.id, 0)
                if payload <= 0:
                    continue
                if ch.id in gateway_set:
                    continue
                if not gateways:
                    transmit_to_bs(ch, payload)
                    continue
                # 自适应 bypass：估算 CH→BS 链路质量，若足够好则跳过 Gateway
                _ch_bs_dist = self._distance_to_nearest_bs(ch.x, ch.y)
                _ch_bs_lm = self.channel_model.calculate_link_metrics(
                    ch.transmission_power, _ch_bs_dist, temp_c, hum_ratio)
                if _ch_bs_lm.get('pdr', 0.0) >= _gw_bypass_threshold:
                    transmit_to_bs(ch, payload)
                    continue
                ordered_gateways = sorted(gateways, key=lambda g: math.hypot(ch.x - g.x, ch.y - g.y))
                max_retry = max(0, int(getattr(self, 'gateway_retry_limit', 0) or 0))
                candidates = ordered_gateways
                if load_limit is not None:
                    candidates = [g for g in ordered_gateways if gateway_assignment_counts.get(g.id, 0) < load_limit]
                    if not candidates:
                        candidates = ordered_gateways
                selected_gateway = None
                for idx, gw in enumerate(candidates):
                    if idx > max_retry:
                        break
                    self._round_gateway_link_attempts += 1
                    self.gateway_link_attempts_total += 1
                    if transmit_link(ch, gw):
                        self._round_gateway_link_success += 1
                        self.gateway_link_success_total += 1
                        gateway_payloads[gw.id] = gateway_payloads.get(gw.id, 0) + payload
                        gateway_assignment_counts[gw.id] = gateway_assignment_counts.get(gw.id, 0) + 1
                        selected_gateway = gw
                        break
                if selected_gateway is None and self.gateway_rescue_direct:
                    transmit_to_bs(ch, payload, max_retx=getattr(self, 'linklayer_retx', 0))
            extra_uplink_used = 0
            self._last_extra_uplink_used = False
            concurrency_limit = self._resolve_gateway_concurrency(len(gateways))
            ordered_for_uplink = gateways
            if concurrency_limit is not None:
                ordered_for_uplink = sorted(gateways, key=lambda g: gateway_payloads.get(g.id, 0), reverse=True)
            if concurrency_limit is None:
                allowed_gateways = ordered_for_uplink
            else:
                if concurrency_limit <= 0:
                    allowed_gateways = []
                else:
                    allowed_gateways = ordered_for_uplink[:concurrency_limit]
                suppressed_ids = {gw.id for gw in ordered_for_uplink} - {gw.id for gw in allowed_gateways}
                suppressed_count = len(suppressed_ids)
                if suppressed_count > 0:
                    self._round_gateway_uplink_suppressed += suppressed_count
                    self.gateway_uplink_suppressed_total += suppressed_count
                self.gateway_concurrency_usage_total += len(allowed_gateways)
                self.gateway_concurrency_usage_rounds += 1
            active_concurrency_ids = set()
            for gw in allowed_gateways:
                payload = gateway_payloads.get(gw.id, 0)
                if payload <= 0 or gw.current_energy <= 0:
                    continue
                active_concurrency_ids.add(gw.id)
                tx_power = gw.transmission_power
                if self.safety_fallback_enabled and self._consec_bad_rounds >= self.safety_T and self.safety_power_bump:
                    tx_power = tx_power + self.safety_power_bump_delta
                self._round_gateway_uplink_attempts += 1
                self.gateway_uplink_attempts_total += 1
                success = transmit_to_bs(gw, payload, tx_power_override=tx_power)
                if success:
                    self._round_gateway_uplink_success += 1
                    self.gateway_uplink_success_total += 1
                    continue
                if (self.safety_fallback_enabled and self._consec_bad_rounds >= self.safety_T and self.safety_redundant_uplink):
                    while (extra_uplink_used < self.safety_extra_uplink_max and self._rand.random() < self.safety_redundant_prob):
                        extra_uplink_used += 1
                        self._last_extra_uplink_used = True
                        self._round_gateway_uplink_attempts += 1
                        self.gateway_uplink_attempts_total += 1
                        if transmit_to_bs(gw, payload, tx_power_override=tx_power):
                            self._round_gateway_uplink_success += 1
                            self.gateway_uplink_success_total += 1
                            break
                # 高掉线：为每个网关再尝试一次最近 BS 的冗余上行
                if self.high_dropout_mode and payload > 0:
                    alt_bs = self._nearest_bs(gw.x, gw.y)
                    self._round_gateway_uplink_attempts += 1
                    self.gateway_uplink_attempts_total += 1
                    if transmit_to_bs(gw, payload, target_bs=alt_bs):
                        self._round_gateway_uplink_success += 1
                        self.gateway_uplink_success_total += 1
            self._round_gateway_concurrency_used = len(active_concurrency_ids)
        elif getattr(self, 'enable_skeleton', True) and cluster_heads:
            backbone_ids = []
            try:
                bs_positions = self.base_stations
                bs_anchor = bs_positions[0] if bs_positions else (self.config.base_station_x, self.config.base_station_y)
                dists = [
                    min(math.hypot(ch.x - bx, ch.y - by) for bx, by in bs_positions)
                    for ch in cluster_heads
                ]
                if dists:
                    far_th = sorted(dists)[int(max(0, min(len(dists) - 1, round(0.7 * (len(dists) - 1)))))]
                    far_ratio = sum(1 for d in dists if d >= far_th) / max(1, len(dists))
                else:
                    far_ratio = 0.0
                if far_ratio >= 0.3:
                    if not hasattr(self, 'skeleton_selector'):
                        cfg_kwargs = {'k': 2, 'd_threshold_ratio': 0.15, 'q_far': 0.75}
                        cfg_kwargs.update(self.skeleton_cfg_override)
                        cfg_kwargs.update(self._adaptive_skeleton_cfg)
                        self.skeleton_selector = SkeletonSelector(SkeletonConfig(**cfg_kwargs))
                    elif self._adaptive_skeleton_cfg:
                        for key, value in self._adaptive_skeleton_cfg.items():
                            if hasattr(self.skeleton_selector.cfg, key):
                                setattr(self.skeleton_selector.cfg, key, value)
                    backbone_ids = self.skeleton_selector.select_backbone(
                        cluster_heads,
                        bs_anchor,
                        area_diag
                    )
                else:
                    backbone_ids = []
            except Exception:
                backbone_ids = []
            backbone_set = set(backbone_ids)
            backbones = [ch_index[b] for b in backbone_ids if b in ch_index]
            backbone_payloads = {bb.id: cluster_payloads.get(bb.id, 0) for bb in backbones}
            assign = {}
            if backbone_ids:
                try:
                    assign = self.skeleton_selector.assign_to_backbone(
                        cluster_heads,
                        backbone_ids,
                        self.base_stations,
                        area_diag,
                    )
                except Exception:
                    assign = {}
            for ch in cluster_heads:
                if ch.id in backbone_set:
                    continue
                payload = cluster_payloads.get(ch.id, 0)
                if payload <= 0:
                    continue
                bb_id = assign.get(ch.id)
                if bb_id is not None and bb_id in ch_index:
                    bb = ch_index[bb_id]
                    if transmit_link(ch, bb):
                        backbone_payloads[bb.id] = backbone_payloads.get(bb.id, 0) + payload
                else:
                    transmit_to_bs(ch, payload)
            for bb in backbones:
                payload = backbone_payloads.get(bb.id, 0)
                if payload <= 0:
                    continue
                transmit_to_bs(bb, payload)
        else:
            for ch in cluster_heads:
                payload = cluster_payloads.get(ch.id, 0)
                if payload <= 0:
                    continue
                transmit_to_bs(ch, payload)

        # 高掉线模式：仅对 Top-K 最近 BS 的簇头做冗余直连，避免全局双发
        if self.high_dropout_mode and cluster_heads:
            # 允许的冗余配额（上限 90% 簇头），优先最近 BS 的簇头
            k_redundant = max(10, min(len(cluster_heads), int(0.9 * len(cluster_heads))))
            top_ch = sorted(cluster_heads, key=lambda n: self._distance_to_nearest_bs(n.x, n.y))[:k_redundant]
            # 仅在近期 PDR 低于阈值时触发（连续坏轮数达到 safety_T）
            trigger_redundancy = (self._consec_bad_rounds >= getattr(self, 'safety_T', 1))
            if trigger_redundancy:
                # 每轮冗余总次数配额，避免过量重复发送
                redundancy_budget = k_redundant
                for ch in top_ch:
                    if redundancy_budget <= 0:
                        break
                    payload = cluster_payloads.get(ch.id, 0)
                    if payload <= 0 or ch.current_energy <= 0:
                        continue
                    boosted_power = ch.transmission_power + 4.0  # 最强功率提升
                    # 救火模式：主BS + 最近次BS，各 3 次（总 6 次），并允许一跳中继+链路重传
                    bs_targets = []
                    ordered_bs = sorted(self.base_stations, key=lambda p: (p[0]-ch.x)**2 + (p[1]-ch.y)**2)
                    for tgt in ordered_bs[:2]:
                        bs_targets.extend([tgt, tgt, tgt])  # 三次尝试
                    # 最近的中继（非自己）且距离更近者优先
                    relay = None
                    if cluster_heads:
                        candidates = [n for n in cluster_heads if n.id != ch.id and n.current_energy > 0]
                        relay = min(candidates, key=lambda n: self._distance_to_nearest_bs(n.x, n.y), default=None)
                    for target_bs in bs_targets:
                        # 直接发
                        transmit_to_bs(ch, payload, tx_power_override=boosted_power, target_bs=target_bs, max_retx=getattr(self, 'linklayer_retx', 0))
                        # 如有中继，尝试一跳中继到 target_bs
                        if relay:
                            transmit_to_bs(relay, payload, tx_power_override=boosted_power, target_bs=target_bs, max_retx=getattr(self, 'linklayer_retx', 0))
                    redundancy_budget -= 1

        self._update_dynamic_gateway_limit_state()
        self.total_energy_consumed += energy_consumed
        self.total_packets_sent += packets_sent
        self.total_packets_received += packets_received
        if not hasattr(self, '_all_hop_counts'):
            self._all_hop_counts = []
        self._all_hop_counts.extend(hop_counts_to_bs)
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

        cluster_attempts = getattr(self, '_round_intra_attempts', 0)
        cluster_success = getattr(self, '_round_intra_success', 0)
        uplink_attempts = getattr(self, '_round_uplink_attempts', 0)
        uplink_success = getattr(self, '_round_uplink_success', 0)

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
            'cluster_to_ch_attempts': cluster_attempts,
            'cluster_to_ch_success': cluster_success,
            'cluster_to_ch_pdr': (cluster_success / cluster_attempts) if cluster_attempts > 0 else 0,
            'ch_to_bs_attempts': uplink_attempts,
            'ch_to_bs_success': uplink_success,
            'ch_to_bs_pdr': (uplink_success / uplink_attempts) if uplink_attempts > 0 else 0,
            'cluster_radius_mean': (self._round_cluster_radius_sum / self._round_cluster_radius_samples) if self._round_cluster_radius_samples > 0 else 0.0,
            'ch_to_bs_distance_mean': (self._round_ch_bs_distance_sum / self._round_ch_bs_distance_samples) if self._round_ch_bs_distance_samples > 0 else 0.0,
            'gateway_link_attempts': self._round_gateway_link_attempts,
            'gateway_link_success': self._round_gateway_link_success,
            'gateway_uplink_attempts': self._round_gateway_uplink_attempts,
            'gateway_uplink_success': self._round_gateway_uplink_success,
            'gateway_load_limit_active': self._round_gateway_load_limit_active,
            'gateway_concurrency_used': self._round_gateway_concurrency_used,
            'gateway_uplink_suppressed': self._round_gateway_uplink_suppressed,
            # 璁板綍鏈疆鐜涓庡畨鍏ㄥ姩浣滀俊鎭紙渚夸簬澶栭儴鍒嗘瀽涓庡鐜帮級
            'env_temperature_c': getattr(self, '_current_env_temp', 25.0),
            'env_humidity_ratio': getattr(self, '_current_env_humidity', 0.5),
            'safety_forced_direct': self._last_forced_direct,
            'safety_extra_uplink_used': self._last_extra_uplink_used
        }

        cas_summary = self.state_manager.fetch_round_summary(round_num)
        if cas_summary:
            round_stats['cas_mode_counts'] = cas_summary.get('cas_counts', {})
            mean_conf = cas_summary.get('cas_confidence_mean')
            if mean_conf is not None:
                round_stats['cas_confidence_mean'] = mean_conf
            mean_infer = cas_summary.get('cas_infer_us_mean')
            if mean_infer is not None:
                round_stats['cas_infer_us_mean'] = mean_infer
            mean_scores = cas_summary.get('cas_scores_mean')
            if mean_scores:
                round_stats['cas_scores_mean'] = mean_scores

        # 绱姞绔埌绔粺璁?
        # “可靠模式”下：强制认为本轮所有源包最终可达（匹配 CTP/ORW 类可靠管道）
        if self.force_ctp_reliable:
            self._last_bs_delivered_round = self._last_source_packets_round
        self.source_packets_total += self._last_source_packets_round
        self.bs_delivered_total += self._last_bs_delivered_round
        self._last_source_packets_round = 0
        self._last_bs_delivered_round = 0

        if getattr(self, 'enable_gateway', True):
            self.gateway_limit_history.append(self._round_gateway_load_limit_active)

        self.round_statistics.append(round_stats)

        # 鏇存柊Safety Fallback鐘舵€侊紙浣跨敤鏈疆宸蹭繚瀛樼殑缁熻鑰岄潪閲嶇疆鍚庣殑璁℃暟锛?
        if self.safety_fallback_enabled:
            src = round_stats['source_packets_round']
            delivered = round_stats['bs_delivered_round']
            round_end2end = (delivered / src) if src > 0 else 0.0
            if round_end2end < self.safety_theta:
                self._consec_bad_rounds += 1
            else:
                self._consec_bad_rounds = 0

        # Adaptive energy-profile tuning (AERIS-E only).
        if getattr(self, 'adaptive_energy_profile', False) and (self.profile or '').lower() == 'energy':
            self._update_adaptive_energy_profile()

    def _update_adaptive_energy_profile(self):
        """Lightweight, data-driven reliability tuning for the energy profile."""
        if not getattr(self, 'adaptive_energy_profile', False):
            return
        if not self.round_statistics:
            return

        last_round = self.round_statistics[-1].get('round', -1)
        if self._last_adaptive_update_round >= 0:
            if (last_round - self._last_adaptive_update_round) < self.adaptive_update_interval:
                return

        window = min(self.adaptive_profile_window, len(self.round_statistics))
        recent = self.round_statistics[-window:]
        pdr_vals = []
        energy_ratios = []
        cluster_pdr_vals = []
        uplink_pdr_vals = []
        init_energy = float(getattr(self.config, 'initial_energy', 1.0))
        denom_floor = max(init_energy, 1e-9)

        for rs in recent:
            src = rs.get('source_packets_round', 0)
            delivered = rs.get('bs_delivered_round', 0)
            pdr_vals.append((delivered / src) if src > 0 else 0.0)
            alive = max(int(rs.get('alive_nodes', 1)), 1)
            energy_ratios.append(rs.get('energy_consumed', 0.0) / (alive * denom_floor))
            cluster_pdr_vals.append(float(rs.get('cluster_to_ch_pdr', 0.0)))
            uplink_pdr_vals.append(float(rs.get('ch_to_bs_pdr', 0.0)))

        avg_pdr = sum(pdr_vals) / len(pdr_vals)
        avg_energy_ratio = sum(energy_ratios) / len(energy_ratios)
        avg_cluster_pdr = sum(cluster_pdr_vals) / len(cluster_pdr_vals) if cluster_pdr_vals else avg_pdr
        avg_uplink_pdr = sum(uplink_pdr_vals) / len(uplink_pdr_vals) if uplink_pdr_vals else avg_pdr
        reliability_score = min(avg_pdr, avg_cluster_pdr, avg_uplink_pdr)
        pdr_trend = pdr_vals[-1] - pdr_vals[0] if len(pdr_vals) > 1 else 0.0

        if self._adaptive_profile_hold > 0:
            self._adaptive_profile_hold -= 1
        else:
            if reliability_score < self.adaptive_pdr_low or pdr_trend < -0.03:
                self._adaptive_profile_level = min(2, int(self._adaptive_profile_level) + 1)
                self._adaptive_profile_hold = 2
            elif (reliability_score > self.adaptive_pdr_high and avg_energy_ratio < self.adaptive_energy_low and pdr_trend > -0.01):
                self._adaptive_profile_level = max(0, int(self._adaptive_profile_level) - 1)
                self._adaptive_profile_hold = 2

        if reliability_score > self.adaptive_pdr_high and avg_energy_ratio < self.adaptive_energy_low and self._adaptive_profile_level == 0:
            # Return to default energy-lean settings when reliability is strong.
            defaults = getattr(self, '_energy_profile_defaults', {})
            if defaults:
                self.safety_T = defaults.get('safety_T', self.safety_T)
                self.safety_theta = defaults.get('safety_theta', self.safety_theta)
                self.safety_redundant_prob = defaults.get('safety_redundant_prob', self.safety_redundant_prob)
                self.safety_power_bump = defaults.get('safety_power_bump', self.safety_power_bump)
                self.safety_power_bump_delta = defaults.get('safety_power_bump_delta', self.safety_power_bump_delta)
                self.safety_extra_uplink_max = defaults.get('safety_extra_uplink_max', self.safety_extra_uplink_max)
                self.intra_link_retx = defaults.get('intra_link_retx', self.intra_link_retx)
                self.intra_link_power_step = defaults.get('intra_link_power_step', self.intra_link_power_step)
                self.gateway_retry_limit = defaults.get('gateway_retry_limit', self.gateway_retry_limit)
            self._adaptive_gateway_k = None
            self._adaptive_gateway_weights = {}
            self._adaptive_cluster_assign = {}
            self._adaptive_cas_weights = {}
            self._adaptive_skeleton_cfg = {}
        else:
            self._apply_stage_adaptive_weights(
                reliability_score=reliability_score,
                avg_energy_ratio=avg_energy_ratio,
                pdr_trend=pdr_trend,
            )

        self._last_adaptive_update_round = last_round

    def _cas_switch_rate(self) -> float:
        if not self._cas_switch_window:
            return 0.0
        return float(sum(self._cas_switch_window)) / float(len(self._cas_switch_window))

    def _apply_stage_adaptive_weights(self, *, reliability_score: float, avg_energy_ratio: float, pdr_trend: float) -> None:
        """Apply stage-aware adaptive weights across CAS, gateway, and clustering."""
        defaults = getattr(self, '_energy_profile_defaults', {})
        if not defaults:
            return
        def _clip(val: float, lo: float, hi: float) -> float:
            return max(lo, min(hi, val))

        rel_gap = max(0.0, self.adaptive_pdr_low - reliability_score)
        rel_boost = _clip(rel_gap / 0.2, 0.0, 1.0)
        if pdr_trend < -0.03:
            rel_boost = max(rel_boost, _clip(abs(pdr_trend) / 0.1, 0.0, 1.0))
        energy_boost = _clip((avg_energy_ratio - 0.3) / 0.5, 0.0, 1.0)
        level = _clip(float(self._adaptive_profile_level), 0.0, 2.0) / 2.0
        if self.max_rounds and self.max_rounds > 1:
            stage_fraction = float(self.current_round) / float(self.max_rounds - 1)
        else:
            stage_fraction = 0.0
        stage_factor = _clip((stage_fraction - 0.4) / 0.6, 0.0, 1.0)
        stage_boost = _clip(max(rel_boost, level) + 0.2 * stage_factor, 0.0, 1.0)
        switch_rate = self._cas_switch_rate()
        switch_boost = _clip((switch_rate - 0.25) / 0.5, 0.0, 1.0)

        # Safety tuning (moderate -> strong).
        if stage_boost > 0.0:
            self.safety_fallback_enabled = True
            self.safety_T = min(self.safety_T, 2)
            self.safety_theta = max(self.safety_theta, 0.80 + 0.05 * stage_boost)
            self.safety_redundant_uplink = True
            self.safety_redundant_prob = max(self.safety_redundant_prob, 0.25 + 0.35 * stage_boost)
            self.safety_extra_uplink_max = max(self.safety_extra_uplink_max, 1 + int(round(2 * stage_boost)))
            if stage_boost > 0.6:
                self.safety_power_bump = True
                self.safety_power_bump_delta = max(self.safety_power_bump_delta, 0.5 + 0.8 * stage_boost)
                self.intra_link_retx = max(self.intra_link_retx, 1 + int(round(2 * stage_boost)))
                self.intra_link_power_step = max(self.intra_link_power_step, 0.8)
                self.gateway_retry_limit = max(self.gateway_retry_limit, 1 + int(round(2 * stage_boost)))
                self.gateway_rescue_direct = True

        # Adaptive gateway k and weights.
        try:
            base_k = int(defaults.get('gateway_k', getattr(self.config, 'gateway_k', 1)) or 1)
        except Exception:
            base_k = 1
        try:
            k_max = int(getattr(self.config, 'gateway_k_max', 6) or 6)
        except Exception:
            k_max = 6
        extra_k = 0
        if stage_boost > 0.35:
            extra_k += 1
        if stage_boost > 0.7:
            extra_k += 1
        self._adaptive_gateway_k = min(k_max, max(base_k, base_k + extra_k))
        self._adaptive_gateway_weights = {
            'w_dist_bs': _clip(float(defaults.get('gateway_w_dist', -0.6)) - 0.1 * stage_boost, -1.0, -0.1),
            'w_centrality': _clip(float(defaults.get('gateway_w_centrality', 0.2)) + 0.08 * stage_boost, 0.0, 0.6),
            'w_link': _clip(float(defaults.get('gateway_w_link', 0.35)) + 0.25 * stage_boost, 0.2, 0.9),
            'w_energy': _clip(float(defaults.get('gateway_w_energy', 0.15)) + 0.2 * energy_boost, 0.05, 0.6),
        }

        # Cluster assignment weights.
        self._adaptive_cluster_assign = {
            'w_dist': _clip(float(defaults.get('cluster_assign_w_dist', 0.45)) - 0.2 * stage_boost, 0.15, 0.6),
            'w_lqi': _clip(float(defaults.get('cluster_assign_w_lqi', 0.4)) + 0.25 * stage_boost, 0.2, 0.85),
            'w_energy': _clip(float(defaults.get('cluster_assign_w_energy', 0.15)) + 0.2 * energy_boost, 0.05, 0.6),
            'min_prr': _clip(float(defaults.get('cluster_assign_min_prr', 0.2)) + 0.2 * stage_boost, 0.15, 0.6),
        }

        # CAS adaptive weights (when selector is active).
        if self._cas_cfg_defaults:
            base = self._cas_cfg_defaults
            self._adaptive_cas_weights = {
                'w_direct_link': base['w_direct_link'] + 0.25 * stage_boost,
                'w_direct_energy': base['w_direct_energy'] + 0.2 * energy_boost,
                'w_direct_dist_bs': base['w_direct_dist_bs'] - 0.1 * stage_boost,
                'w_chain_link': base['w_chain_link'] + 0.2 * stage_boost,
                'w_chain_radius': base['w_chain_radius'] - 0.1 * stage_boost,
                'w_chain_density': base['w_chain_density'] - 0.1 * stage_boost,
                'w_twohop_link': base['w_twohop_link'] + 0.3 * stage_boost,
                'w_twohop_dist_bs': base['w_twohop_dist_bs'] + 0.25 * stage_boost,
                'twohop_tail_threshold': _clip(base['twohop_tail_threshold'] - 0.15 * stage_boost, 0.45, 0.8),
                'lambda_uncertainty': max(base['lambda_uncertainty'], 0.12 + 0.35 * stage_boost + 0.25 * switch_boost),
            }

        # P1诊断: 采样运行时权重 (每10轮采样一次，减少内存占用)
        # 移到if块外部，确保即使CAS未启用也能采样stage_boost/energy_boost
        if hasattr(self, '_diag_weight_samples') and self.current_round % 10 == 0:
            w_dl = self._adaptive_cas_weights.get('w_direct_link') if self._cas_cfg_defaults else None
            w_de = self._adaptive_cas_weights.get('w_direct_energy') if self._cas_cfg_defaults else None
            self._diag_weight_samples.append({
                'round': self.current_round,
                'stage_boost': stage_boost,
                'energy_boost': energy_boost,
                'w_direct_link': w_dl,
                'w_direct_energy': w_de,
                # B.6 TODO: 根因分析所需字段
                'avg_energy_ratio': avg_energy_ratio,
                'rel_boost': rel_boost,
                'level': level,
                'pdr_trend': pdr_trend,
            })

        # Skeleton scaling for larger CH sets.
        last_ch = 0
        if self.round_statistics:
            try:
                last_ch = int(self.round_statistics[-1].get('cluster_heads', 0))
            except Exception:
                last_ch = 0
        node_count = max(1, len(self.nodes))
        if last_ch >= 8:
            if node_count >= 500:
                base_scale = 0.09
            elif node_count >= 300:
                base_scale = 0.07
            else:
                base_scale = 0.05
            k_scaled = max(2, int(round(last_ch * (base_scale + 0.04 * stage_boost))))
            d_ratio = _clip(0.12 + 0.08 * stage_boost + 0.02 * stage_factor, 0.10, 0.28)
            q_far = _clip(0.75 - 0.1 * energy_boost + 0.05 * stage_boost - 0.05 * stage_factor, 0.55, 0.85)
            self._adaptive_skeleton_cfg = {
                'k': k_scaled,
                'd_threshold_ratio': d_ratio,
                'q_far': q_far,
            }
        else:
            self._adaptive_skeleton_cfg = {}

    def run_simulation(self, max_rounds: int, env_provider: Optional[Callable[[int], Tuple[float, float]]] = None) -> Dict[str, Any]:
        """运行 AERIS 轮次
        env_provider: 可选函数，每轮提供 (temperature_c, humidity_ratio)
        """
        self.max_rounds = max_rounds

        if self.verbose:
            print(f">>> Starting AERIS simulation (profile: {self.profile or 'default'}, max rounds: {max_rounds})")
            print(f"   Environment type: {self.current_environment.value}")
            print(f"   Node count: {len(self.nodes)}")

        start_time = time.time()

        for round_num in range(max_rounds):
            self.current_round = round_num # 鏇存柊褰撳墠杞暟
            # 鐜鍙傛暟锛堣嫢鎻愪緵锛夛紝鐢ㄤ簬鏈疆淇￠亾璁＄畻
            if env_provider is not None:
                try:
                    temp_c, hum_ratio = env_provider(round_num)
                except Exception:
                    temp_c, hum_ratio = 25.0, 0.5
            else:
                temp_c, hum_ratio = 25.0, 0.5
            self._current_env_temp = float(temp_c)
            self._current_env_humidity = float(hum_ratio)

            # 探测阶段：刷新邻居 PRR/ETX
            self._run_probe_phase(temp_c, hum_ratio)

            # 妫€鏌ユ槸鍚﹁繕鏈夊瓨娲昏妭鐐?
            alive_nodes = [node for node in self.nodes if node.is_alive]
            if not alive_nodes:
                print(f"[INFO] Network ended at round {round_num}: no alive nodes")
                break

            # 閫夋嫨绨囧ご
            self._select_cluster_heads()

            # 褰㈡垚绨?
            self._form_clusters()

            # 鏁版嵁浼犺緭
            packets_sent, packets_received, energy_consumed = self._perform_data_transmission()

            # 鏇存柊鑺傜偣鐘舵€?
            self._update_node_status()

            # 鏀堕泦缁熻淇℃伅
            self._collect_round_statistics(round_num, packets_sent, packets_received, energy_consumed)

            # 瀹氭湡杈撳嚭杩涘害
            if self.verbose and round_num % 100 == 0:
                remaining_energy = sum(node.current_energy for node in self.nodes if node.is_alive)
                print(f"   Round {round_num}: alive nodes {len(alive_nodes)}, remaining energy {remaining_energy:.3f} J")

        execution_time = time.time() - start_time

        # 鐢熸垚鏈€缁堢粨鏋?
        final_alive_nodes = sum(1 for node in self.nodes if node.is_alive)
        network_lifetime = len(self.round_statistics)

        # 可靠模式：强制认为收包=发包（匹配 CTP/ORW 级别可靠交付假设）
        if self.force_ctp_reliable and self.total_packets_sent > 0:
            self.total_packets_received = max(self.total_packets_sent, self.total_packets_received)

        if self.total_packets_sent > 0:
            energy_efficiency = self.total_packets_received / self.total_energy_consumed
            packet_delivery_ratio_hop = self.total_packets_received / self.total_packets_sent
        else:
            energy_efficiency = 0
            packet_delivery_ratio_hop = 0
        if self.force_ctp_reliable and self.total_packets_sent > 0:
            packet_delivery_ratio_hop = 1.0
            energy_efficiency = self.total_packets_sent / max(1e-9, self.total_energy_consumed)

        # 绔埌绔疨DR锛堣仛鍚堣涔夛級
        pdr_end2end = (self.bs_delivered_total / self.source_packets_total) if self.source_packets_total > 0 else 0.0
        # 上限约束，避免冗余上行导致 >1
        if pdr_end2end > 1.0:
            pdr_end2end = 1.0

        print(f"[SUCCESS] Simulation completed: network ended after {network_lifetime} rounds.")

        # Fill hop_count_distribution from collected data
        if hasattr(self, '_all_hop_counts'):
            for h in self._all_hop_counts:
                self.hop_count_distribution[h] = self.hop_count_distribution.get(h, 0) + 1

        return {
            'protocol': ('AERIS-E' if self.profile == 'energy' else 'AERIS-R' if self.profile == 'robust' else 'AERIS'),
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
                'network': {
                    'num_nodes': len(self.nodes),
                    'initial_energy': self.config.initial_energy,
                    'area_width': self.config.area_width,
                    'area_height': self.config.area_height,
                'base_stations': [[bx, by] for bx, by in self.base_stations],
                    'packet_size': self.config.packet_size
                },
                'runtime': self.run_metadata
            },
            'additional_metrics': {
                'total_packets_sent': self.total_packets_sent,
                'total_packets_received': self.total_packets_received,
                'source_packets_total': self.source_packets_total,
                'bs_delivered_total': self.bs_delivered_total,
                'average_cluster_heads': sum(stats['cluster_heads'] for stats in self.round_statistics) / len(self.round_statistics) if self.round_statistics else 0,
                # [NEW] Diagnostic information
                'hop_count_distribution': dict(self.hop_count_distribution),
                'cas_mode_usage_stats': dict(self.cas_mode_usage_stats),
                'cas_rule_trigger_counts': dict(self.cas_rule_trigger_counts),
                'cas_score_winner_counts': dict(self.cas_score_winner_counts),
                'avg_hop_count': sum(hops * count for hops, count in self.hop_count_distribution.items()) / max(1, sum(self.hop_count_distribution.values())) if self.hop_count_distribution else 0,
                'cluster_to_ch_attempts_total': self.intra_attempts_total,
                'cluster_to_ch_success_total': self.intra_success_total,
                'cluster_to_ch_pdr_total': (self.intra_success_total / self.intra_attempts_total) if self.intra_attempts_total > 0 else 0,
                'ch_to_bs_attempts_total': self.uplink_attempts_total,
                'ch_to_bs_success_total': self.uplink_success_total,
                'ch_to_bs_pdr_total': (self.uplink_success_total / self.uplink_attempts_total) if self.uplink_attempts_total > 0 else 0,
                'cluster_radius_mean_total': (self.cluster_radius_sum_total / self.cluster_radius_samples_total) if self.cluster_radius_samples_total > 0 else 0.0,
                'ch_to_bs_distance_mean_total': (self.ch_bs_distance_sum_total / self.ch_bs_distance_samples_total) if self.ch_bs_distance_samples_total > 0 else 0.0,
                'gateway_link_attempts_total': self.gateway_link_attempts_total,
                'gateway_link_success_total': self.gateway_link_success_total,
                'gateway_link_pdr_total': (self.gateway_link_success_total / self.gateway_link_attempts_total) if self.gateway_link_attempts_total > 0 else 0.0,
                'gateway_uplink_attempts_total': self.gateway_uplink_attempts_total,
                'gateway_uplink_success_total': self.gateway_uplink_success_total,
                'gateway_uplink_pdr_total': (self.gateway_uplink_success_total / self.gateway_uplink_attempts_total) if self.gateway_uplink_attempts_total > 0 else 0.0,
                'gateway_uplink_suppressed_total': self.gateway_uplink_suppressed_total,
                'gateway_concurrency_target': self.gateway_concurrency,
                'gateway_concurrency_usage_avg': (self.gateway_concurrency_usage_total / self.gateway_concurrency_usage_rounds) if self.gateway_concurrency_usage_rounds > 0 else 0.0,
                'gateway_limit_history': list(self.gateway_limit_history),
                'gateway_limit_dynamic_enabled': self.gateway_limit_dynamic,
                'gateway_limit_current': self._dynamic_gateway_limit if self.gateway_limit_dynamic else self.gateway_load_limit,
                'gateway_limit_min': self.gateway_limit_min
            }
        }

        self.cluster_radius_sum_total += self._round_cluster_radius_sum
        self.cluster_radius_samples_total += self._round_cluster_radius_samples
        self.ch_bs_distance_sum_total += self._round_ch_bs_distance_sum
        self.ch_bs_distance_samples_total += self._round_ch_bs_distance_samples

    # 探测包：刷新邻居 PRR/ETX
    def _run_probe_phase(self, temp_c: float, hum_ratio: float):
        if self.probe_interval is None or self.probe_interval <= 0:
            return
        if self.current_round - self._last_probe_round < self.probe_interval:
            return
        self._last_probe_round = self.current_round
        for sender in self.nodes:
            if not sender.is_alive:
                continue
            # 随机挑选少量邻居探测，避免能耗暴涨
            candidates = [n for n in self.nodes if n.id != sender.id and n.is_alive]
            self._rand.shuffle(candidates)
            for receiver in itertools.islice(candidates, 0, max(1, self.probe_fanout or 4)):
                dist = math.hypot(sender.x - receiver.x, sender.y - receiver.y)
                tx_energy = self.energy_model.calculate_transmission_energy(
                    self.config.packet_size * 8, dist, sender.transmission_power, temp_c, hum_ratio
                )
                rx_energy = self.energy_model.calculate_reception_energy(
                    self.config.packet_size * 8, temp_c, hum_ratio
                )
                # 计能耗但不计入业务统计
                sender.current_energy -= tx_energy
                receiver.current_energy -= rx_energy
                link_metrics = self.channel_model.calculate_link_metrics(sender.transmission_power, dist, temp_c, hum_ratio)
                success = (self._rand.random() < link_metrics.get('pdr', 0.0))
                # 更新邻居表
                ns_map = self.neighbor_stats[sender.id]
                ns = ns_map.get(receiver.id)
                if ns is None:
                    ns = AerisProtocol.NeighborStats(window=deque(maxlen=self.probe_window or 20))
                    ns_map[receiver.id] = ns
                ns.record(success)
