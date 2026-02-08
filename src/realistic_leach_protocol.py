#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鍩轰簬鏉冨▉鏂囩尞鐨勭湡瀹炵幆澧僉EACH鍗忚瀹炵幇

鍩轰簬娣卞害璋冪爺鐨勬潈濞佹柟娉曪細
1. Log-Normal Shadowing淇￠亾妯″瀷 (Rappaport鏁欐潗)
2. IEEE 802.15.4鏍囧噯鐨凴SSI/LQI閾捐矾璐ㄩ噺璇勪及
3. 澶氭簮骞叉壈鐜涓嬬殑SINR寤烘ā鍜孭DR棰勬祴
4. 鐜鍥犵礌瀵筗SN鎬ц兘褰卞搷鐨勯噺鍖栧垎鏋?

鍙傝€冩枃鐚細
- Baazaoui et al. (2023) "Modeling of Packet Error Rate Distribution Based on RSSI in OMNeT++"
- Tangsunantham & Pirak (2023) "Hardware-Based Link Quality Estimation Modelling"
- IEEE 802.15.4-2015 Standard for Low-Rate Wireless Networks

浣滆€? AERIS Research Team
鏃ユ湡: 2025-01-31
鐗堟湰: 2.0 (Realistic Environment)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import numpy as np
except ModuleNotFoundError:
    class _NP:
        class random:
            @staticmethod
            def normal(mu, sigma):
                return __import__('random').gauss(mu, sigma)

        @staticmethod
        def mean(values):
            return sum(values) / len(values) if values else 0.0

    np = _NP()
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import copy
from realistic_channel_model import RealisticChannelModel as SharedRealisticChannelModel, EnvironmentType as SharedEnvironmentType
try:
    from intel_dataset_loader import IntelLabDataLoader  # type: ignore
except Exception:
    IntelLabDataLoader = None  # type: ignore

# Compatibility re-exports for external imports
EnvironmentType = SharedEnvironmentType
RealisticChannelModel = SharedRealisticChannelModel

@dataclass
class Node:
    """WSN node class"""
    id: int
    x: float
    y: float
    initial_energy: float
    current_energy: float
    is_alive: bool = True
    is_cluster_head: bool = False
    cluster_id: int = -1
    
    # 鐜鍙傛暟
    temperature: float = 25.0  # 娓╁害 (掳C)
    humidity: float = 0.5      # 婀垮害 (0-1)

@dataclass
class NetworkConfig:
    """缃戠粶閰嶇疆鍙傛暟"""
    num_nodes: int = 50
    area_width: float = 100.0
    area_height: float = 100.0
    base_station_x: float = 50.0
    base_station_y: float = 175.0
    initial_energy: float = 2.0  # 鍖归厤鏉冨▉LEACH鐨?J
    packet_size: int = 4000      # bits (鏉冨▉LEACH鏍囧噯)
    # 自适应发射功率参数（仅用于终跳→BS）
    tx_power_step_dbm: float = 5.0
    max_tx_power_dbm: float = 10.0
    final_hop_target_pdr: float = 0.6
    hop_target_pdr: float = 0.75
    
class _LegacyEnvironmentType(Enum):
    INDOOR_OFFICE = "indoor_office"
    OUTDOOR_OPEN = "outdoor_open"
    INDUSTRIAL = "industrial"
    URBAN = "urban"

class _LegacyRealisticChannelModel:
    # Legacy placeholder; not used
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.OUTDOOR_OPEN):
        self.environment = environment
        
        # Log-Normal Shadowing妯″瀷鍙傛暟 (鍩轰簬Rappaport鏁欐潗)
        self.path_loss_params = {
            EnvironmentType.INDOOR_OFFICE: {
                'n': 2.0,      # 璺緞鎹熻€楁寚鏁?
                'sigma': 3.0,  # 闃村奖琛拌惤鏍囧噯宸?(dB)
                'P0': -40.0    # 鍙傝€冭窛绂?m澶勭殑鍔熺巼 (dBm)
            },
            EnvironmentType.OUTDOOR_OPEN: {
                'n': 2.5,      # 鑷敱绌洪棿 + 鍦伴潰鍙嶅皠
                'sigma': 4.0,  # 闃村奖琛拌惤
                'P0': -45.0
            },
            EnvironmentType.INDUSTRIAL: {
                'n': 3.0,      # 楂橀殰纰嶇墿鐜
                'sigma': 6.0,  # 楂樺彉寮傛€?
                'P0': -50.0
            },
            EnvironmentType.URBAN: {
                'n': 3.5,      # 瀵嗛泦寤虹瓚鐜
                'sigma': 8.0,  # 鏋侀珮鍙樺紓鎬?
                'P0': -55.0
            }
        }
        
        # IEEE 802.15.4鍙傛暟
        self.tx_power = 0.0  # dBm (CC2420鏍囧噯)
        self.noise_floor = -95.0  # dBm
        self.sensitivity = -85.0  # dBm
        
        # 骞叉壈婧愬弬鏁?
        self.interference_sources = []
        
    def calculate_rssi(self, distance: float, tx_node: Node, rx_node: Node) -> float:
        """
        鍩轰簬Log-Normal Shadowing妯″瀷璁＄畻RSSI
        
        RSSI(dBm) = P_tx - PL(d) - X_蟽
        PL(d) = PL(d0) + 10*n*log10(d/d0)
        """
        params = self.path_loss_params[self.environment]
        
        # 鍩虹璺緞鎹熻€?
        if distance < 1.0:
            distance = 1.0  # 閬垮厤log(0)
            
        path_loss = params['P0'] + 10 * params['n'] * math.log10(distance)
        
        # 闃村奖琛拌惤 (Log-Normal鍒嗗竷)
        shadowing = np.random.normal(0, params['sigma'])
        
        # 鐜鍥犵礌褰卞搷 (鍩轰簬瀹炴祴鏁版嵁)
        temp_factor = self._calculate_temperature_effect(tx_node.temperature)
        humidity_factor = self._calculate_humidity_effect(tx_node.humidity)
        
        # 璁＄畻RSSI
        rssi = self.tx_power - path_loss - shadowing - temp_factor - humidity_factor
        
        return rssi
    
    def _calculate_temperature_effect(self, temperature: float) -> float:
        """娓╁害瀵逛俊鍙蜂紶鎾殑褰卞搷 (鍩轰簬鏂囩尞鏁版嵁)"""
        # 鍩轰簬Boano et al.鐮旂┒锛氭俯搴︽瘡鍗囬珮10掳C锛屼俊鍙疯“鍑忓鍔?.5dB
        reference_temp = 25.0
        return 0.05 * abs(temperature - reference_temp)
    
    def _calculate_humidity_effect(self, humidity: float) -> float:
        """婀垮害瀵逛俊鍙蜂紶鎾殑褰卞搷"""
        # 鍩轰簬Luomala & Hakala鐮旂┒锛氶珮婀垮害澧炲姞淇″彿琛板噺
        return 2.0 * humidity  # 鏈€澶?dB琛板噺
    
    def calculate_sinr(self, rssi: float, interference_power: float = 0.0) -> float:
        """璁＄畻淇″彿骞叉壈鍣０姣?(SINR)"""
        signal_power = 10**(rssi/10)  # 杞崲涓虹嚎鎬у姛鐜?
        noise_power = 10**(self.noise_floor/10)
        interference_linear = 10**(interference_power/10) if interference_power > 0 else 0
        
        sinr_linear = signal_power / (noise_power + interference_linear)
        sinr_db = 10 * math.log10(sinr_linear) if sinr_linear > 0 else -100
        
        return sinr_db
    
    def calculate_pdr(self, rssi: float, sinr: float) -> float:
        """
        鍩轰簬RSSI鍜孲INR璁＄畻鍖呮姇閫掔巼 (PDR)
        浣跨敤閫昏緫鍥炲綊妯″瀷 (鍩轰簬Tangsunantham & Pirak鐮旂┒)
        """
        # RSSI-PDR閫昏緫鍥炲綊妯″瀷鍙傛暟 (鍩轰簬瀹炴祴鏁版嵁鎷熷悎)
        if rssi >= -70:
            pdr = 0.95 + 0.05 * random.random()  # 楂樹俊鍙峰己搴?
        elif rssi >= -80:
            # 閫昏緫鍥炲綊: PDR = 1 / (1 + exp(-(a*RSSI + b)))
            a, b = 0.15, 11.5  # 鍩轰簬鏂囩尞鍙傛暟
            pdr = 1.0 / (1.0 + math.exp(-(a * rssi + b)))
        elif rssi >= -90:
            # 涓瓑淇″彿寮哄害锛屽彈SINR褰卞搷
            base_pdr = 1.0 / (1.0 + math.exp(-(0.12 * rssi + 9.0)))
            sinr_factor = max(0.1, min(1.0, (sinr + 10) / 20))  # SINR淇
            pdr = base_pdr * sinr_factor
        else:
            # 浣庝俊鍙峰己搴︼紝涓昏鍙楀櫔澹板奖鍝?
            pdr = max(0.01, 0.1 * math.exp((rssi + 95) / 5))
        
        return min(0.99, max(0.01, pdr))  # 闄愬埗鍦ㄥ悎鐞嗚寖鍥村唴
    
    def add_interference_source(self, power_dbm: float, distance: float):
        # Add interference source (legacy)
        self.interference_sources.append({
            'power': power_dbm,
            'distance': distance
        })
    
    def calculate_total_interference(self, node_x: float, node_y: float) -> float:
        # Calculate total interference power (legacy)
        total_interference = 0.0
        
        for source in self.interference_sources:
            # 绠€鍖栫殑骞叉壈璁＄畻
            interference_rssi = source['power'] - 20 * math.log10(source['distance'])
            interference_power = 10**(interference_rssi/10)
            total_interference += interference_power
        
        return 10 * math.log10(total_interference) if total_interference > 0 else -100

class RealisticLEACHProtocol:
    """鍩轰簬鐪熷疄鐜寤烘ā鐨凩EACH鍗忚"""
    
    def __init__(self, config: NetworkConfig, environment: SharedEnvironmentType = SharedEnvironmentType.OUTDOOR_OPEN,
                 data_loader: Optional[object] = None,
                 use_real_positions: bool = True):
        self.config = config
        self.channel_model = SharedRealisticChannelModel(environment)
        self.nodes = []
        self.round_number = 0
        self.cluster_heads = []
        self.clusters = {}
        self.data_loader = data_loader
        self.use_real_positions = use_real_positions
        self._dataset_id_map: Dict[int, int] = {}
        self._ts_list: List = []
        self._ts_index: int = 0
        
        # 缁熻淇℃伅
        self.stats = {
            'total_packets_sent': 0,
            'total_packets_received': 0,
            'total_transmission_attempts': 0,
            'total_energy_consumed': 0.0,
            'network_lifetime': 0,
            'pdr_history': [],
            'rssi_history': [],
            'sinr_history': [],
            # 基站维度统计（对齐权威 LEACH 的聚合口径）
            'bs_packets_sent': 0,
            'bs_packets_received': 0,
            'bs_transmission_attempts': 0
        }
        
        # 鍒濆鍖栫綉缁?
        self._initialize_network()
        
        # 娣诲姞鍏稿瀷骞叉壈婧?(WiFi, 宸ヤ笟璁惧绛?
        self.channel_model.add_interference_source(-20, 15)  # WiFi璺敱鍣?
        self.channel_model.add_interference_source(-30, 25)  # 宸ヤ笟璁惧
    
    def _initialize_network(self):
        """Initialize network nodes"""
        # 若提供数据加载器且有真实位置，则使用真实位置初始化
        try:
            if (
                self.data_loader is not None
                and self.use_real_positions
                and getattr(self.data_loader, 'locations_data', None) is not None
                and not self.data_loader.locations_data.empty
            ):
                return self._initialize_network_with_real_positions()
        except Exception as _e:
            print(f"[WARN] Init with real positions failed, fallback to random: {_e}")

        # 回退方案：无需 pandas，直接解析 Intel Lab 的位置文件
        try:
            if self.use_real_positions:
                import os
                loc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Intel_Lab_Data', 'mote_locs.txt')
                if os.path.exists(loc_path):
                    return self._initialize_network_with_mote_locs_file(loc_path)
        except Exception as _e:
            print(f"[WARN] Fallback init with mote_locs.txt failed: {_e}")

        # 回退：随机初始化
        self.nodes = []
        for i in range(self.config.num_nodes):
            x = random.uniform(0, self.config.area_width)
            y = random.uniform(0, self.config.area_height)

            temperature = random.uniform(20, 35)
            humidity = random.uniform(0.3, 0.8)

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

    def _initialize_network_with_real_positions(self):
        """Use Intel Lab locations to place nodes and bootstrap env data."""
        self.nodes = []
        loc_df = self.data_loader.locations_data.copy()
        # 统一列名
        if 'node_id' not in loc_df.columns and 'moteid' in loc_df.columns:
            loc_df = loc_df.rename(columns={'moteid': 'node_id'})
        # 过滤缺失位置
        loc_df = loc_df.dropna(subset=['x', 'y'])
        if loc_df.empty:
            raise ValueError("Locations dataset is empty after cleaning")

        # 缩放到仿真区域
        min_x, max_x = float(loc_df['x'].min()), float(loc_df['x'].max())
        min_y, max_y = float(loc_df['y'].min()), float(loc_df['y'].max())
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)

        ids = sorted(loc_df['node_id'].unique().tolist())
        N = max(1, min(self.config.num_nodes, len(ids)))

        # 预处理时间序列
        sens_df = getattr(self.data_loader, 'sensor_data', None)
        ts_list = []
        if sens_df is not None and not sens_df.empty and 'timestamp' in sens_df.columns:
            ts_list = sorted(sens_df['timestamp'].dropna().unique().tolist())
        self._ts_list = ts_list
        self._ts_index = 0

        for i in range(self.config.num_nodes):
            did = ids[i % N]
            self._dataset_id_map[i] = did
            row = loc_df[loc_df['node_id'] == did].iloc[0]
            raw_x, raw_y = float(row['x']), float(row['y'])
            sx = (raw_x - min_x) / span_x * self.config.area_width
            sy = (raw_y - min_y) / span_y * self.config.area_height

            # 初始化温湿度
            temperature = random.uniform(20, 35)
            humidity = random.uniform(0.3, 0.8)
            if sens_df is not None and not sens_df.empty:
                s_df = sens_df.copy()
                if 'node_id' not in s_df.columns and 'moteid' in s_df.columns:
                    s_df = s_df.rename(columns={'moteid': 'node_id'})
                node_series = s_df[s_df['node_id'] == did]
                if not node_series.empty:
                    if self._ts_list:
                        ts0 = self._ts_list[0]
                        sub = node_series[node_series['timestamp'] <= ts0]
                        if not sub.empty:
                            last = sub.sort_values('timestamp').iloc[-1]
                            temperature = float(last.get('temperature', temperature))
                            hval = float(last.get('humidity', humidity))
                            humidity = (hval / 100.0) if hval > 1.0 else hval
                    else:
                        first = node_series.sort_values('timestamp').iloc[0]
                        temperature = float(first.get('temperature', temperature))
                        hval = float(first.get('humidity', humidity))
                        humidity = (hval / 100.0) if hval > 1.0 else hval

            node = Node(
                id=i,
                x=sx,
                y=sy,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy,
                temperature=temperature,
                humidity=humidity
            )
            self.nodes.append(node)

        print(f"[OK] Initialized {len(self.nodes)} nodes with Intel Lab positions (scaled)")

    def _initialize_network_with_mote_locs_file(self, loc_path: str):
        """无需 pandas 的位置初始化：解析 mote_locs.txt 并缩放到仿真区域。"""
        self.nodes = []
        records = []
        with open(loc_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 兼容逗号/空白分隔，跳过表头
                parts = [p for p in line.replace(',', ' ').split() if p]
                if len(parts) < 3:
                    continue
                try:
                    # 常见顺序：x y moteid 或 moteid x y
                    # 通过是否为整数来判断 moteid 位置
                    ints = []
                    for i, p in enumerate(parts[:3]):
                        try:
                            ints.append((i, int(float(p))))
                        except Exception:
                            pass
                    if ints:
                        mote_idx = ints[-1][0]
                    else:
                        # 无法判断则按第三列为 moteid
                        mote_idx = 2
                    moteid = int(float(parts[mote_idx]))
                    vals = [float(parts[i]) for i in range(3) if i != mote_idx]
                    if len(vals) != 2:
                        continue
                    x_val, y_val = float(vals[0]), float(vals[1])
                    records.append({'node_id': moteid, 'x': x_val, 'y': y_val})
                except Exception:
                    # 非数据行或格式不匹配，跳过
                    continue

        if not records:
            raise ValueError("No valid records parsed from mote_locs.txt")

        # 去重并计算范围
        by_id = {}
        for r in records:
            if r['node_id'] not in by_id:
                by_id[r['node_id']] = r
        uniq = list(by_id.values())
        xs = [r['x'] for r in uniq]
        ys = [r['y'] for r in uniq]
        min_x, max_x = float(min(xs)), float(max(xs))
        min_y, max_y = float(min(ys)), float(max(ys))
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)

        ids = sorted([r['node_id'] for r in uniq])
        N = max(1, min(self.config.num_nodes, len(ids)))

        self._dataset_id_map.clear()
        self._ts_list = []
        self._ts_index = 0

        for i in range(self.config.num_nodes):
            did = ids[i % N]
            self._dataset_id_map[i] = did
            rr = by_id[did]
            raw_x, raw_y = float(rr['x']), float(rr['y'])
            sx = (raw_x - min_x) / span_x * self.config.area_width
            sy = (raw_y - min_y) / span_y * self.config.area_height

            temperature = random.uniform(20, 35)
            humidity = random.uniform(0.3, 0.8)

            node = Node(
                id=i,
                x=sx,
                y=sy,
                initial_energy=self.config.initial_energy,
                current_energy=self.config.initial_energy,
                temperature=temperature,
                humidity=humidity
            )
            self.nodes.append(node)

        print(f"[OK] Initialized {len(self.nodes)} nodes from mote_locs.txt (scaled)")

    def _advance_time_and_update_env(self):
        """Advance to next timestamp and update node temperature/humidity from dataset."""
        sens_df = getattr(self.data_loader, 'sensor_data', None)
        if self.data_loader is None or sens_df is None or sens_df.empty:
            return
        s_df = sens_df.copy()
        if 'node_id' not in s_df.columns and 'moteid' in s_df.columns:
            s_df = s_df.rename(columns={'moteid': 'node_id'})
        if not self._ts_list:
            if 'timestamp' in s_df.columns:
                self._ts_list = sorted(s_df['timestamp'].dropna().unique().tolist())
            else:
                return
        if not self._ts_list:
            return

        ts = self._ts_list[self._ts_index]
        for n in self.nodes:
            did = self._dataset_id_map.get(n.id)
            if did is None:
                continue
            series = s_df[s_df['node_id'] == did]
            if series.empty:
                continue
            sub = series[series['timestamp'] <= ts]
            if sub.empty:
                continue
            last = sub.sort_values('timestamp').iloc[-1]
            tval = last.get('temperature', None)
            hval = last.get('humidity', None)
            if tval is not None:
                try:
                    n.temperature = float(tval)
                except Exception:
                    pass
            if hval is not None:
                try:
                    h = float(hval)
                    n.humidity = (h / 100.0) if h > 1.0 else h
                except Exception:
                    pass

        self._ts_index = (self._ts_index + 1) % len(self._ts_list)
    
    def _calculate_distance(self, node1: Node, node2: Node) -> float:
        # Calculate distance between two nodes
        return math.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)
    
    def _calculate_distance_to_bs(self, node: Node) -> float:
        # Calculate distance from node to base station
        return math.sqrt((node.x - self.config.base_station_x)**2 +
                        (node.y - self.config.base_station_y)**2)

    def _transmit_packet(self, sender: Node, receiver: Optional[Node] = None,
                        packet_size: int = None,
                        tx_power_dbm: Optional[float] = None) -> Tuple[bool, float, float, float]:
        # Data packet transmission in realistic environment
        # Returns (success, rssi, sinr, pdr)
        if packet_size is None:
            packet_size = self.config.packet_size

        # 璁＄畻浼犺緭璺濈
        if receiver is None:
            # 鐩存帴浼犺緭鍒板熀绔?
            distance = self._calculate_distance_to_bs(sender)
        else:
            distance = self._calculate_distance(sender, receiver)

        # 计算综合链路指标（使用共享真实信道模型）
        metrics = self.channel_model.calculate_link_metrics(
            tx_power_dbm=(0.0 if tx_power_dbm is None else tx_power_dbm),
            distance=distance,
            temperature_c=getattr(sender, 'temperature', 25.0),
            humidity_ratio=getattr(sender, 'humidity', 0.5)
        )
        rssi = metrics['rssi']
        sinr = metrics['sinr_db']
        pdr = metrics['pdr']

        # 璁板綍缁熻淇℃伅
        self.stats['rssi_history'].append(rssi)
        self.stats['sinr_history'].append(sinr)
        self.stats['pdr_history'].append(pdr)
        self.stats['total_transmission_attempts'] += 1
        to_bs = (receiver is None)
        if to_bs:
            self.stats['bs_transmission_attempts'] += 1

        # 鍒ゆ柇浼犺緭鏄惁鎴愬姛
        success = random.random() < pdr

        if success:
            self.stats['total_packets_sent'] += 1
            if to_bs:
                self.stats['bs_packets_sent'] += 1
            # 仅成功传输且超过接收灵敏度才计入接收
            if rssi > self.channel_model.link_quality.sensitivity_threshold:
                self.stats['total_packets_received'] += 1
                if to_bs:
                    self.stats['bs_packets_received'] += 1

        # 璁＄畻鑳借€?(鍩轰簬CC2420鍙傛暟)
        tx_energy = self._calculate_transmission_energy(
            packet_size,
            distance,
            getattr(sender, 'temperature', 25.0),
            getattr(sender, 'humidity', 0.5),
            tx_power_dbm=tx_power_dbm
        )
        sender.current_energy -= tx_energy
        self.stats['total_energy_consumed'] += tx_energy

        # 妫€鏌ヨ妭鐐规槸鍚︽浜?
        if sender.current_energy <= 0:
            sender.is_alive = False
            sender.current_energy = 0

        return success, rssi, sinr, pdr

    def _calculate_transmission_energy(self, packet_size_bits: int, distance: float, temperature_c: float = 25.0, humidity_ratio: float = 0.5, tx_power_dbm: Optional[float] = None) -> float:
        # Transmission energy model (CC2420 TelosB; classical LEACH)
        # CC2420鑳借€楀弬鏁?(鍩轰簬鏉冨▉鏂囩尞)
        E_elec = 50e-9      # 50 nJ/bit (鐢佃矾鑳借€?
        E_fs = 10e-12       # 10 pJ/bit/m虏 (鑷敱绌洪棿)
        E_mp = 0.0013e-12   # 0.0013 pJ/bit/m鈦?(澶氬緞琛拌惤)

        # 璺濈闃堝€?
        d_crossover = math.sqrt(E_fs / E_mp)  # ~87.7m

        # 浼犺緭鑳借€楄绠?
        if distance < d_crossover:
            # 鑷敱绌洪棿妯″瀷
            tx_energy = E_elec * packet_size_bits + E_fs * packet_size_bits * (distance ** 2)
        else:
            # 澶氬緞琛拌惤妯″瀷
            tx_energy = E_elec * packet_size_bits + E_mp * packet_size_bits * (distance ** 4)

        # 终跳功率提升的附加能耗（简化线性近似，仅当指定功率时生效）
        if tx_power_dbm is not None and tx_power_dbm > 0:
            # 每比特的功率开销系数（近似）：1e-9 J/bit/dBm
            tx_energy += (tx_power_dbm * 1e-9 * packet_size_bits)

        return tx_energy

    def _choose_tx_power_for_distance(self, distance: float, target_pdr: float,
                                      temperature_c: float, humidity_ratio: float,
                                      energy_budget: Optional[float] = None) -> float:
        """为给定距离选择最小功率以达到目标PDR；若提供能量预算则不超预算。"""
        step = max(1.0, float(self.config.tx_power_step_dbm))
        max_pwr = float(self.config.max_tx_power_dbm)

        candidate_powers = [0.0]
        k = 1
        while True:
            p = step * k
            if p > max_pwr + 1e-9:
                break
            candidate_powers.append(p)
            k += 1

        best_power = 0.0
        for pwr in candidate_powers:
            metrics = self.channel_model.calculate_link_metrics(
                tx_power_dbm=pwr,
                distance=distance,
                temperature_c=temperature_c,
                humidity_ratio=humidity_ratio
            )
            pdr = metrics['pdr']
            energy = self._calculate_transmission_energy(
                self.config.packet_size,
                distance,
                temperature_c,
                humidity_ratio,
                tx_power_dbm=pwr
            )
            if pdr >= target_pdr and (energy_budget is None or energy <= energy_budget):
                best_power = pwr
                break

        if best_power == 0.0 and energy_budget is not None:
            for pwr in reversed(candidate_powers):
                energy = self._calculate_transmission_energy(
                    self.config.packet_size,
                    distance,
                    temperature_c,
                    humidity_ratio,
                    tx_power_dbm=pwr
                )
                if energy <= energy_budget:
                    best_power = pwr
                    break

        return best_power

    def _choose_final_tx_power(self, sender: Node) -> float:
        """为终跳→BS选择自适应发射功率：满足目标PDR且能耗不超出节点当前能量。"""
        distance = self._calculate_distance_to_bs(sender)
        return self._choose_tx_power_for_distance(
            distance,
            float(self.config.final_hop_target_pdr),
            getattr(sender, 'temperature', 25.0),
            getattr(sender, 'humidity', 0.5),
            energy_budget=sender.current_energy
        )

    def _choose_hop_tx_power(self, sender: Node, receiver: Node) -> float:
        """为中间跳选择自适应发射功率：达到每跳目标PDR（不强制能量预算约束）。"""
        distance = self._calculate_distance(sender, receiver)
        return self._choose_tx_power_for_distance(
            distance,
            float(self.config.hop_target_pdr),
            getattr(sender, 'temperature', 25.0),
            getattr(sender, 'humidity', 0.5),
            energy_budget=None
        )

    def _select_cluster_heads(self) -> List[Node]:
        # LEACH cluster-head selection method
        cluster_heads = []
        p = 0.1  # 绨囧ご姒傜巼 (鏉冨▉LEACH鏍囧噯)

        for node in self.nodes:
            if not node.is_alive:
                continue

            # LEACH闃堝€艰绠?
            if self.round_number % (1/p) == 0:
                threshold = p
            else:
                threshold = p / (1 - p * (self.round_number % (1/p)))

            # 闅忔満閫夋嫨
            if random.random() < threshold:
                node.is_cluster_head = True
                cluster_heads.append(node)
            else:
                node.is_cluster_head = False

        return cluster_heads

    def _form_clusters(self, cluster_heads: List[Node]):
        # Form clusters based on selected cluster heads
        self.clusters = {}

        # 鍒濆鍖栫皣
        for ch in cluster_heads:
            self.clusters[ch.id] = []

        # 鑺傜偣鍔犲叆鏈€杩戠殑绨囧ご
        for node in self.nodes:
            if not node.is_alive or node.is_cluster_head:
                continue

            if not cluster_heads:
                # 娌℃湁绨囧ご锛岀洿鎺ヨ繛鎺ュ熀绔?
                node.cluster_id = -1
                continue

            # 鎵惧埌鏈€浣崇皣澶?(鍩轰簬RSSI)
            best_ch = None
            best_rssi = -float('inf')

            for ch in cluster_heads:
                distance = self._calculate_distance(node, ch)
                metrics = self.channel_model.calculate_link_metrics(
                    tx_power_dbm=0.0,
                    distance=distance,
                    temperature_c=getattr(node, 'temperature', 25.0),
                    humidity_ratio=getattr(node, 'humidity', 0.5)
                )
                rssi = metrics['rssi']
                if rssi > best_rssi:
                    best_rssi = rssi
                    best_ch = ch

            if best_ch:
                node.cluster_id = best_ch.id
                self.clusters[best_ch.id].append(node)

    def _select_best_ch_for_bs(self, cluster_heads: List[Node]) -> Optional[Node]:
        """选择对基站聚合上行最优的簇头（优先最高 PDR，其次最小能耗）。"""
        best_ch = None
        best_score = -float('inf')
        for ch in cluster_heads:
            if not ch.is_alive:
                continue
            distance = self._calculate_distance_to_bs(ch)
            metrics = self.channel_model.calculate_link_metrics(
                tx_power_dbm=0.0,
                distance=distance,
                temperature_c=getattr(ch, 'temperature', 25.0),
                humidity_ratio=getattr(ch, 'humidity', 0.5)
            )
            pdr = metrics['pdr']
            # 以 PDR 为主的评分，能耗越小越好（负权重）
            tx_energy = self._calculate_transmission_energy(
                self.config.packet_size,
                distance,
                getattr(ch, 'temperature', 25.0),
                getattr(ch, 'humidity', 0.5)
            )
            score = pdr - 1e-9 * tx_energy
            if score > best_score:
                best_score = score
                best_ch = ch
        return best_ch

    def _plan_route_to_bs(self, source: Node, relay_candidates: List[Node]) -> List[Node]:
        """路径级路由规划：在跳数与束宽限制下，最大化期望成功概率并约束能耗。"""
        if not source or not source.is_alive:
            return []

        MAX_HOPS = 8
        BEAM_WIDTH = 5
        ENERGY_LAMBDA = 1e-9
        DIST_GAIN = 0.001
        CH_BONUS = 0.05
        EPS = 1e-6

        def score_state_basic(path_nodes: List[Node], log_prob_sum: float, energy_sum: float, dist_reduction_sum: float) -> float:
            return log_prob_sum - ENERGY_LAMBDA * energy_sum + DIST_GAIN * dist_reduction_sum

        def _estimate_final_hop_metrics(node: Node) -> Tuple[float, float, float]:
            """前瞻估计：从 node 终跳到BS的(PDR, 能耗, 选定功率)。"""
            tx_pwr = self._choose_final_tx_power(node)
            d_bs = self._calculate_distance_to_bs(node)
            metrics = self.channel_model.calculate_link_metrics(
                tx_power_dbm=tx_pwr,
                distance=d_bs,
                temperature_c=getattr(node, 'temperature', 25.0),
                humidity_ratio=getattr(node, 'humidity', 0.5)
            )
            pdr_f = metrics['pdr']
            e_f = self._calculate_transmission_energy(
                self.config.packet_size,
                d_bs,
                getattr(node, 'temperature', 25.0),
                getattr(node, 'humidity', 0.5),
                tx_power_dbm=tx_pwr
            )
            return pdr_f, e_f, tx_pwr

        def score_state_augmented(state: Dict) -> float:
            """增强评分：在当前路径得分基础上，加入终跳的前瞻PDR与能耗。"""
            pdr_f, e_f, _ = _estimate_final_hop_metrics(state['path'][-1])
            return (
                state['log_prob'] + math.log(max(EPS, pdr_f))
                - ENERGY_LAMBDA * (state['energy'] + e_f)
                + DIST_GAIN * state['dist_red']
            )

        def _estimate_hop_metrics(u: Node, v: Node) -> Tuple[float, float, float]:
            """前瞻估计：从 u→v 的(PDR, 能耗, 选定功率)，使用每跳目标PDR。"""
            d_link = self._calculate_distance(u, v)
            tx_pwr = self._choose_hop_tx_power(u, v)
            metrics = self.channel_model.calculate_link_metrics(
                tx_power_dbm=tx_pwr,
                distance=d_link,
                temperature_c=getattr(u, 'temperature', 25.0),
                humidity_ratio=getattr(u, 'humidity', 0.5)
            )
            pdr_h = metrics['pdr']
            e_h = self._calculate_transmission_energy(
                self.config.packet_size,
                d_link,
                getattr(u, 'temperature', 25.0),
                getattr(u, 'humidity', 0.5),
                tx_power_dbm=tx_pwr
            )
            return pdr_h, e_h, tx_pwr

        initial_state = {
            'path': [source],
            'log_prob': 0.0,
            'energy': 0.0,
            'dist_red': 0.0
        }

        alive_nodes = [n for n in self.nodes if n.is_alive]
        completed_routes = []
        beam = [initial_state]

        for _ in range(MAX_HOPS):
            new_beam = []
            for state in beam:
                last = state['path'][-1]
                d_last_bs = self._calculate_distance_to_bs(last)

                # 选项1：直接到 BS（作为完成候选）
                # 直接到BS：使用自适应功率的前瞻PDR与能耗
                pdr_direct, e_direct, _ = _estimate_final_hop_metrics(last)
                pdr_direct = max(EPS, pdr_direct)
                comp = {
                    'path': list(state['path']),
                    'log_prob': state['log_prob'] + math.log(pdr_direct),
                    'energy': state['energy'] + e_direct,
                    'dist_red': state['dist_red'] + d_last_bs
                }
                completed_routes.append(comp)

                # 选项2：扩展到下一跳（必须逼近 BS）
                candidates = [n for n in relay_candidates if n.is_alive and n.id not in [x.id for x in state['path']] and n.id != last.id]
                if not candidates:
                    candidates = [n for n in alive_nodes if n.id not in [x.id for x in state['path']] and n.id != last.id]

                for nxt in candidates:
                    d_next_bs = self._calculate_distance_to_bs(nxt)
                    if d_next_bs >= d_last_bs:
                        continue

                    pdr_link, e_link, _ = _estimate_hop_metrics(last, nxt)
                    pdr_link = max(EPS, pdr_link)

                    new_state = {
                        'path': state['path'] + [nxt],
                        'log_prob': state['log_prob'] + math.log(pdr_link) + (CH_BONUS if nxt.is_cluster_head else 0.0),
                        'energy': state['energy'] + e_link,
                        'dist_red': state['dist_red'] + (d_last_bs - d_next_bs)
                    }
                    new_beam.append(new_state)

            # 选出下一轮束
            if not new_beam:
                break
            new_beam.sort(key=lambda st: score_state_augmented(st), reverse=True)
            beam = new_beam[:BEAM_WIDTH]

        # 选择最佳完成路径（包含最终直达 BS 的一步）
        if completed_routes:
            completed_routes.sort(key=lambda st: score_state_basic(st['path'], st['log_prob'], st['energy'], st['dist_red']), reverse=True)
            return completed_routes[0]['path']

        # 若没有完成路径，则返回当前束中最优路径（之后直达 BS）
        beam.sort(key=lambda st: score_state_augmented(st), reverse=True)
        return beam[0]['path']

    def _route_aggregate_to_bs(self, source: Node, relay_candidates: List[Node]) -> bool:
        """执行路径：按规划路径逐跳发送，支持每跳一次有限重试，最终一次直达 BS。"""
        route = self._plan_route_to_bs(source, relay_candidates)
        if not route:
            return False

        visited_ids = set()
        for i in range(len(route)):
            current = route[i]
            visited_ids.add(current.id)

            # 最后一段：直达 BS（一次尝试计入 bs_*）
            if i == len(route) - 1:
                # 终跳自适应发射功率
                tx_pwr = self._choose_final_tx_power(current)
                success, rssi, sinr, pdr = self._transmit_packet(current, tx_power_dbm=tx_pwr)
                return success

            # 中间段：到下一跳，失败则有限重试一次
            next_hop = route[i + 1]
            tx_pwr_hop = self._choose_hop_tx_power(current, next_hop)
            success, rssi, sinr, pdr = self._transmit_packet(current, next_hop, tx_power_dbm=tx_pwr_hop)
            if success:
                continue

            # 有限重试：选择一个未访问、逼近 BS 的备选下一跳
            d_curr_bs = self._calculate_distance_to_bs(current)
            alive_nodes = [n for n in self.nodes if n.is_alive]
            fallback = None
            best_score = -float('inf')
            EPS = 1e-6

            candidates = [n for n in relay_candidates if n.is_alive and n.id not in visited_ids and n.id != current.id]
            if not candidates:
                candidates = [n for n in alive_nodes if n.id not in visited_ids and n.id != current.id]

            for cand in candidates:
                d_cand_bs = self._calculate_distance_to_bs(cand)
                if d_cand_bs >= d_curr_bs:
                    continue
                d_link = self._calculate_distance(current, cand)
                tx_pwr_cand = self._choose_hop_tx_power(current, cand)
                m_link = self.channel_model.calculate_link_metrics(
                    tx_power_dbm=tx_pwr_cand,
                    distance=d_link,
                    temperature_c=getattr(current, 'temperature', 25.0),
                    humidity_ratio=getattr(current, 'humidity', 0.5)
                )
                pdr_link = max(EPS, m_link['pdr'])
                e_link = self._calculate_transmission_energy(
                    self.config.packet_size,
                    d_link,
                    getattr(current, 'temperature', 25.0),
                    getattr(current, 'humidity', 0.5),
                    tx_power_dbm=tx_pwr_cand
                )
                score = math.log(pdr_link) - 1e-9 * e_link + 0.001 * (d_curr_bs - d_cand_bs)
                if score > best_score:
                    best_score = score
                    fallback = cand

            if fallback is not None:
                tx_pwr_fb = self._choose_hop_tx_power(current, fallback)
                success, rssi, sinr, pdr = self._transmit_packet(current, fallback, tx_power_dbm=tx_pwr_fb)
                if success:
                    # 将后续路径从该备选点继续（简化：不重规划，直接以备选为下一点）
                    route[i + 1] = fallback
                    visited_ids.add(fallback.id)
                    continue

            # 重试也失败则整条路由失败
            return False

    def run_round(self) -> Dict:
        """Run one LEACH round"""
        self.round_number += 1
        # 在每轮开始前注入真实温湿度数据（若可用）
        try:
            self._advance_time_and_update_env()
        except Exception as _e:
            print(f"[WARN] Env update skipped: {_e}")
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

        # 妫€鏌ョ綉缁滄槸鍚﹁繕娲荤潃
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if len(alive_nodes) == 0:
            return round_stats

        # 1. 绨囧ご閫夋嫨闃舵
        cluster_heads = self._select_cluster_heads()
        self.cluster_heads = cluster_heads
        round_stats['cluster_heads'] = len(cluster_heads)

        # 2. 绨囧舰鎴愰樁娈?
        self._form_clusters(cluster_heads)

        # 3. 鏁版嵁浼犺緭闃舵
        packets_sent_before = self.stats['total_packets_sent']
        packets_received_before = self.stats['total_packets_received']
        attempts_before = self.stats['total_transmission_attempts']
        energy_before = self.stats['total_energy_consumed']

        # 绨囧唴鏁版嵁鏀堕泦
        for ch in cluster_heads:
            if not ch.is_alive:
                continue

            # 绨囨垚鍛樺悜绨囧ご鍙戦€佹暟鎹?
            for member in self.clusters.get(ch.id, []):
                if member.is_alive:
                    success, rssi, sinr, pdr = self._transmit_packet(member, ch)

        # 每轮仅一次基站聚合上行（若有簇头，做多跳路由到 BS）
        if cluster_heads:
            best_ch = self._select_best_ch_for_bs(cluster_heads)
            if best_ch and best_ch.is_alive:
                _ = self._route_aggregate_to_bs(best_ch, cluster_heads)

        # 无簇头时，选择一个“最佳节点”并做多跳到 BS（一次）
        if not cluster_heads:
            candidates = [n for n in self.nodes if n.is_alive]
            if candidates:
                # 先选一个最优源点，再尝试多跳路由到 BS
                best_node = None
                best_score = -float('inf')
                for n in candidates:
                    distance = self._calculate_distance_to_bs(n)
                    metrics = self.channel_model.calculate_link_metrics(
                        tx_power_dbm=0.0,
                        distance=distance,
                        temperature_c=getattr(n, 'temperature', 25.0),
                        humidity_ratio=getattr(n, 'humidity', 0.5)
                    )
                    pdr = metrics['pdr']
                    tx_energy = self._calculate_transmission_energy(
                        self.config.packet_size,
                        distance,
                        getattr(n, 'temperature', 25.0),
                        getattr(n, 'humidity', 0.5)
                    )
                    score = pdr - 1e-9 * tx_energy
                    if score > best_score:
                        best_score = score
                        best_node = n
                if best_node:
                    _ = self._route_aggregate_to_bs(best_node, [])

        # 璁＄畻鏈疆缁熻
        round_stats['packets_sent'] = self.stats['total_packets_sent'] - packets_sent_before
        round_stats['packets_received'] = self.stats['total_packets_received'] - packets_received_before
        round_stats['transmission_attempts'] = self.stats['total_transmission_attempts'] - attempts_before
        round_stats['energy_consumed'] = self.stats['total_energy_consumed'] - energy_before

        # 璁＄畻骞冲潎閾捐矾璐ㄩ噺
        if self.stats['rssi_history']:
            recent_rssi = self.stats['rssi_history'][-round_stats['transmission_attempts']:]
            recent_sinr = self.stats['sinr_history'][-round_stats['transmission_attempts']:]
            recent_pdr = self.stats['pdr_history'][-round_stats['transmission_attempts']:]

            round_stats['avg_rssi'] = np.mean(recent_rssi) if recent_rssi else 0
            round_stats['avg_sinr'] = np.mean(recent_sinr) if recent_sinr else 0
            round_stats['avg_pdr'] = np.mean(recent_pdr) if recent_pdr else 0

        return round_stats

    def get_network_statistics(self) -> Dict:
        """Get network statistics"""
        alive_nodes = sum(1 for n in self.nodes if n.is_alive)

        # 基站维度 PDR 与传输成功率（对齐权威 LEACH 聚合口径）
        actual_pdr = (self.stats['bs_packets_received'] /
                      self.stats['bs_packets_sent']) if self.stats['bs_packets_sent'] > 0 else 0
        transmission_rate = (self.stats['bs_packets_sent'] /
                             self.stats['bs_transmission_attempts']) if self.stats['bs_transmission_attempts'] > 0 else 0

        return {
            'total_rounds': self.round_number,
            'alive_nodes': alive_nodes,
            'network_lifetime': self.round_number if alive_nodes > 0 else self.stats['network_lifetime'],
            'total_packets_sent': self.stats['total_packets_sent'],
            'total_packets_received': self.stats['total_packets_received'],
            'total_transmission_attempts': self.stats['total_transmission_attempts'],
            'bs_packets_sent': self.stats['bs_packets_sent'],
            'bs_packets_received': self.stats['bs_packets_received'],
            'bs_transmission_attempts': self.stats['bs_transmission_attempts'],
            'packet_delivery_ratio': actual_pdr,
            'transmission_rate': transmission_rate,
            'packets_per_round': self.stats['bs_packets_received'] / self.round_number if self.round_number > 0 else 0,
            'total_energy_consumed': self.stats['total_energy_consumed'],
            'avg_rssi': np.mean(self.stats['rssi_history']) if self.stats['rssi_history'] else 0,
            'avg_sinr': np.mean(self.stats['sinr_history']) if self.stats['sinr_history'] else 0,
            'avg_pdr': np.mean(self.stats['pdr_history']) if self.stats['pdr_history'] else 0
        }

