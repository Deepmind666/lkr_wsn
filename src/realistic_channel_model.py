#!/usr/bin/env python3
"""
基于文献调研的WSN真实信道建模实现

参考文献:
[1] Rappaport, T. S. (2002). Wireless communications: principles and practice
[2] Srinivasan, K., & Levis, P. (2006). RSSI is under appreciated
[3] Zuniga, M., & Krishnamachari, B. (2004). Analyzing the transitional region
[4] Boano, C. A., et al. (2010). The triangle metric: Fast link quality estimation

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
"""

import numpy as np
import math
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class EnvironmentType(Enum):
    """环境类型枚举 - 基于文献调研的标准环境分类"""
    INDOOR_OFFICE = "indoor_office"
    INDOOR_FACTORY = "indoor_factory"
    INDOOR_RESIDENTIAL = "indoor_residential"  # 新增：住宅环境
    OUTDOOR_OPEN = "outdoor_open"
    OUTDOOR_SUBURBAN = "outdoor_suburban"
    OUTDOOR_URBAN = "outdoor_urban"

@dataclass
class ChannelParameters:
    """信道参数配置"""
    path_loss_exponent: float
    reference_path_loss: float  # dB at 1m
    shadowing_std: float        # dB
    noise_floor: float          # dBm
    frequency: float            # GHz

class LogNormalShadowingModel:
    """
    Log-Normal Shadowing路径损耗模型
    基于Rappaport经典教材的标准实现
    """
    
    def __init__(self, environment: EnvironmentType):
        self.environment = environment
        self.params = self._get_environment_parameters(environment)
        
    def _get_environment_parameters(self, env: EnvironmentType) -> ChannelParameters:
        """根据环境类型获取信道参数"""
        # 基于2024-2025年文献调研的更新参数
        # 数据源：Zanella等人RSSI研究、Miranda等人路径损耗分析、IEEE 802.15.4实验测量
        params_dict = {
            EnvironmentType.INDOOR_OFFICE: ChannelParameters(
                path_loss_exponent=2.0,  # Zanella et al. 室内办公环境测量
                reference_path_loss=40.0,
                shadowing_std=4.5,  # 更新的实验数据
                noise_floor=-95.0,
                frequency=2.4
            ),
            EnvironmentType.INDOOR_FACTORY: ChannelParameters(
                path_loss_exponent=2.7,  # Miranda et al. 工厂环境分析
                reference_path_loss=45.0,  # 金属障碍物影响
                shadowing_std=8.5,  # 高变异性环境
                noise_floor=-92.0,  # 工业噪声影响
                frequency=2.4
            ),
            EnvironmentType.INDOOR_RESIDENTIAL: ChannelParameters(
                path_loss_exponent=1.8,  # 住宅环境障碍物较少
                reference_path_loss=38.0,
                shadowing_std=3.5,  # 相对稳定的环境
                noise_floor=-96.0,  # 较低的背景噪声
                frequency=2.4
            ),
            EnvironmentType.OUTDOOR_OPEN: ChannelParameters(
                path_loss_exponent=2.1,  # 接近自由空间传播
                reference_path_loss=32.0,
                shadowing_std=4.0,  # 实验验证数据
                noise_floor=-98.0,
                frequency=2.4
            ),
            EnvironmentType.OUTDOOR_SUBURBAN: ChannelParameters(
                path_loss_exponent=2.8,  # 中等密度障碍物
                reference_path_loss=38.0,
                shadowing_std=7.5,  # 文献综合数据
                noise_floor=-96.0,
                frequency=2.4
            ),
            EnvironmentType.OUTDOOR_URBAN: ChannelParameters(
                path_loss_exponent=3.4,  # 密集城市环境
                reference_path_loss=44.0,  # 高建筑密度影响
                shadowing_std=12.0,  # 高度变异性
                noise_floor=-93.0,  # 城市电磁干扰
                frequency=2.4
            )
        }
        return params_dict[env]
    
    def calculate_path_loss(self, distance: float, reference_distance: float = 1.0) -> float:
        """
        计算路径损耗 (dB)
        
        Args:
            distance: 传输距离 (m)
            reference_distance: 参考距离 (m)
            
        Returns:
            路径损耗 (dB)
        """
        if distance < reference_distance:
            distance = reference_distance
            
        # 基础路径损耗 (Log-distance模型)
        path_loss = (self.params.reference_path_loss + 
                    10 * self.params.path_loss_exponent * 
                    math.log10(distance / reference_distance))
        
        # 阴影衰落 (Log-normal分布)
        shadowing = np.random.normal(0, self.params.shadowing_std)
        
        return path_loss + shadowing
    
    def calculate_received_power(self, tx_power_dbm: float, distance: float) -> float:
        """
        计算接收功率 (dBm)
        
        Args:
            tx_power_dbm: 发射功率 (dBm)
            distance: 传输距离 (m)
            
        Returns:
            接收功率 (dBm)
        """
        path_loss = self.calculate_path_loss(distance)
        return tx_power_dbm - path_loss

class IEEE802154LinkQuality:
    """
    IEEE 802.15.4链路质量建模
    基于Srinivasan & Levis的RSSI研究
    """
    
    def __init__(self):
        # IEEE 802.15.4标准参数
        self.sensitivity_threshold = -85.0  # dBm
        self.max_lqi = 255
        self.rssi_measurement_std = 2.0     # RSSI测量噪声标准差
        
    def calculate_rssi(self, received_power_dbm: float) -> float:
        """
        计算RSSI值 (包含测量噪声)
        
        Args:
            received_power_dbm: 理论接收功率 (dBm)
            
        Returns:
            RSSI测量值 (dBm)
        """
        measurement_noise = np.random.normal(0, self.rssi_measurement_std)
        return received_power_dbm + measurement_noise
    
    def calculate_lqi(self, rssi_dbm: float) -> int:
        """
        基于RSSI计算LQI值
        
        Args:
            rssi_dbm: RSSI值 (dBm)
            
        Returns:
            LQI值 (0-255)
        """
        if rssi_dbm < self.sensitivity_threshold:
            return 0
        
        # 线性映射: RSSI -> LQI
        rssi_range = abs(self.sensitivity_threshold - (-20))  # -85 to -20 dBm
        normalized_rssi = (rssi_dbm - self.sensitivity_threshold) / rssi_range
        lqi = int(normalized_rssi * self.max_lqi)
        
        return max(0, min(self.max_lqi, lqi))
    
    def calculate_pdr(self, rssi_dbm: float) -> float:
        """
        基于RSSI计算包投递率 (PDR)
        基于Zuniga & Krishnamachari的transitional region分析
        
        Args:
            rssi_dbm: RSSI值 (dBm)
            
        Returns:
            包投递率 (0.0-1.0)
        """
        if rssi_dbm < self.sensitivity_threshold:
            return 0.0
        
        # 基于文献的经验公式
        if rssi_dbm > -70:
            return 0.99  # 强信号区域
        elif rssi_dbm > -80:
            # 过渡区域 (transitional region)
            return 0.5 + 0.49 * (rssi_dbm + 80) / 10
        else:
            # 弱信号区域
            return max(0.0, (rssi_dbm + 85) / 5 * 0.5)

class InterferenceModel:
    """
    共信道干扰建模
    基于SINR的干扰分析
    """
    
    def __init__(self, noise_floor_dbm: float = -95.0):
        self.noise_floor = noise_floor_dbm
        self.interference_sources: List[Dict] = []
        
    def add_interference_source(self, power_dbm: float, distance: float, 
                              source_type: str = "wifi"):
        """
        添加干扰源
        
        Args:
            power_dbm: 干扰源功率 (dBm)
            distance: 干扰源距离 (m)
            source_type: 干扰源类型
        """
        self.interference_sources.append({
            'power': power_dbm,
            'distance': distance,
            'type': source_type
        })
    
    def calculate_sinr(self, signal_power_dbm: float) -> float:
        """
        计算信号干扰噪声比 (SINR)

        Args:
            signal_power_dbm: 信号功率 (dBm)

        Returns:
            SINR (dB)
        """
        signal_power_mw = 10 ** (signal_power_dbm / 10)
        noise_power_mw = 10 ** (self.noise_floor / 10)

        # 计算总干扰功率
        total_interference_mw = 0
        for source in self.interference_sources:
            # 改进的干扰功率计算
            interference_power_mw = 10 ** (source['power'] / 10)
            # 使用更合理的距离衰减模型 (路径损耗指数2.5)
            path_loss_linear = (source['distance'] / 1.0) ** 2.5
            interference_power_mw /= max(path_loss_linear, 1.0)
            total_interference_mw += interference_power_mw

        # 如果没有干扰源，只考虑噪声
        if not self.interference_sources:
            total_interference_mw = 0

        sinr_linear = signal_power_mw / (noise_power_mw + total_interference_mw)
        return 10 * math.log10(max(sinr_linear, 1e-10))  # 避免log(0)
    
    def calculate_interference_pdr(self, sinr_db: float) -> float:
        """
        基于SINR计算干扰环境下的PDR
        
        Args:
            sinr_db: SINR值 (dB)
            
        Returns:
            包投递率 (0.0-1.0)
        """
        if sinr_db > 15:
            return 0.95
        elif sinr_db > 10:
            return 0.8 + 0.15 * (sinr_db - 10) / 5
        elif sinr_db > 5:
            return 0.5 + 0.3 * (sinr_db - 5) / 5
        elif sinr_db > 0:
            return 0.1 + 0.4 * sinr_db / 5
        else:
            return 0.05  # 最小PDR

class EnvironmentalFactors:
    """
    环境因素对信号传播的影响
    """
    
    @staticmethod
    def temperature_effect_on_battery(temperature_c: float) -> float:
        """
        温度对电池容量的影响
        
        Args:
            temperature_c: 温度 (°C)
            
        Returns:
            电池容量系数 (0.0-1.0)
        """
        if temperature_c < 0:
            # 低温下电池容量下降
            capacity_factor = 1.0 - abs(temperature_c) * 0.02
        elif temperature_c > 40:
            # 高温下电池性能下降
            capacity_factor = 1.0 - (temperature_c - 40) * 0.01
        else:
            capacity_factor = 1.0
        
        return max(0.3, capacity_factor)  # 最低保持30%容量
    
    @staticmethod
    def humidity_effect_on_signal(humidity_ratio: float, 
                                 frequency_ghz: float = 2.4) -> float:
        """
        湿度对信号传播的影响
        
        Args:
            humidity_ratio: 相对湿度 (0.0-1.0)
            frequency_ghz: 频率 (GHz)
            
        Returns:
            额外路径损耗 (dB/km)
        """
        # 水蒸气吸收损耗 (简化模型)
        if frequency_ghz == 2.4:
            absorption_coeff = 0.1 * humidity_ratio
        else:
            absorption_coeff = 0.05 * humidity_ratio
        
        return absorption_coeff

class RealisticChannelModel:
    # 可选的环境→参数映射（按轮次动态调整）；若为None则使用构造时的默认参数
    def set_env_mapping(self, shadowing_std: float | None = None, noise_floor_dbm: float | None = None,
                        path_loss_exp: float | None = None, rssi_std: float | None = None):
        if shadowing_std is not None:
            self.path_loss_model.params.shadowing_std = float(shadowing_std)
        if noise_floor_dbm is not None:
            self.interference.noise_floor = float(noise_floor_dbm)
        if path_loss_exp is not None:
            self.path_loss_model.params.path_loss_exponent = float(path_loss_exp)
        if rssi_std is not None:
            self.link_quality.rssi_measurement_std = float(rssi_std)
    """
    综合的真实信道模型
    整合路径损耗、链路质量、干扰和环境因素
    """
    
    def __init__(self, environment: EnvironmentType):
        self.path_loss_model = LogNormalShadowingModel(environment)
        self.link_quality = IEEE802154LinkQuality()
        self.interference = InterferenceModel(
            self.path_loss_model.params.noise_floor
        )
        self.environment_type = environment
        
    def calculate_link_metrics(self, tx_power_dbm: float, distance: float,
                             temperature_c: float = 25.0,
                             humidity_ratio: float = 0.5) -> Dict:
        """
        计算完整的链路指标
        
        Args:
            tx_power_dbm: 发射功率 (dBm)
            distance: 传输距离 (m)
            temperature_c: 温度 (°C)
            humidity_ratio: 相对湿度 (0.0-1.0)
            
        Returns:
            链路指标字典
        """
        # 1. 计算接收功率
        received_power = self.path_loss_model.calculate_received_power(
            tx_power_dbm, distance
        )
        
        # 2. 环境因素修正
        humidity_loss = EnvironmentalFactors.humidity_effect_on_signal(
            humidity_ratio
        ) * distance / 1000  # 转换为实际损耗
        received_power -= humidity_loss
        
        # 3. 计算RSSI和LQI
        rssi = self.link_quality.calculate_rssi(received_power)
        lqi = self.link_quality.calculate_lqi(rssi)
        
        # 4. 计算PDR (考虑干扰)
        sinr = self.interference.calculate_sinr(received_power)
        pdr_interference = self.interference.calculate_interference_pdr(sinr)
        pdr_rssi = self.link_quality.calculate_pdr(rssi)
        pdr = min(pdr_interference, pdr_rssi)  # 取较小值
        
        # 5. 电池容量影响
        battery_factor = EnvironmentalFactors.temperature_effect_on_battery(
            temperature_c
        )
        
        return {
            'received_power_dbm': received_power,
            'rssi': rssi,
            'lqi': lqi,
            'sinr_db': sinr,
            'pdr': pdr,
            'battery_capacity_factor': battery_factor,
            'path_loss_db': tx_power_dbm - received_power,
            'environment': self.environment_type.value
        }

# 使用示例
if __name__ == "__main__":
    # 创建工厂环境的信道模型
    channel = RealisticChannelModel(EnvironmentType.INDOOR_FACTORY)
    
    # 添加WiFi干扰源
    channel.interference.add_interference_source(-30, 10, "wifi")
    
    # 计算链路指标
    metrics = channel.calculate_link_metrics(
        tx_power_dbm=0,      # 0dBm发射功率
        distance=50,         # 50m距离
        temperature_c=35,    # 35°C温度
        humidity_ratio=0.8   # 80%湿度
    )
    
    print("链路指标:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
