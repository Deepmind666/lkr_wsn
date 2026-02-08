#!/usr/bin/env python3
"""
Realistic wireless channel model for WSN based on literature and measurements.

Project policy and scope:
- Paper and project name: AERIS. The term “EEHFR” is permanently deprecated.
- Pure algorithmic research: no hardware implementation or drivers are included.
- Hardware-like parameters serve simulation only; they are not hardware claims.
- IEEE 802.15.4 alignment is limited to PHY/link quality modeling; full MAC behavior
  (e.g., CSMA/CA, ACK/retransmissions) is outside this module’s scope.

References:
[1] Rappaport, T. S. (2002). Wireless communications: principles and practice
[2] Srinivasan, K., & Levis, P. (2006). RSSI is under appreciated
[3] Zuniga, M., & Krishnamachari, B. (2004). Analyzing the transitional region
[4] Boano, C. A., et al. (2010). The triangle metric: Fast link quality estimation

Author: AERIS Research Team
Date: 2025-01-30
"""

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
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class EnvironmentType(Enum):
    """Environment type categories for channel modeling."""
    INDOOR_OFFICE = "indoor_office"
    INDOOR_FACTORY = "indoor_factory"
    INDOOR_RESIDENTIAL = "indoor_residential"
    OUTDOOR_OPEN = "outdoor_open"
    OUTDOOR_SUBURBAN = "outdoor_suburban"
    OUTDOOR_URBAN = "outdoor_urban"
    # Compatibility aliases used by some protocol modules
    INDUSTRIAL = "industrial"
    URBAN = "urban"

@dataclass
class ChannelParameters:
    """Channel parameters configuration"""
    path_loss_exponent: float
    reference_path_loss: float  # dB at 1m
    shadowing_std: float        # dB
    noise_floor: float          # dBm
    frequency: float            # GHz

class LogNormalShadowingModel:
    """
    Log-Normal shadowing path-loss model.
    Based on Rappaport's empirical formulation.
    """
    
    def __init__(self, environment: EnvironmentType):
        self.environment = environment
        self.params = self._get_environment_parameters(environment)
        
    def _get_environment_parameters(self, env: EnvironmentType) -> ChannelParameters:
        """Get channel parameters by environment type."""
        # Updated parameters based on 2024-2025 literature and measurements
        params_dict = {
            EnvironmentType.INDOOR_OFFICE: ChannelParameters(
                path_loss_exponent=2.0,
                reference_path_loss=40.0,
                shadowing_std=4.5,
                noise_floor=-95.0,
                frequency=2.4
            ),
            EnvironmentType.INDOOR_FACTORY: ChannelParameters(
                path_loss_exponent=2.7,
                reference_path_loss=45.0,
                shadowing_std=8.5,
                noise_floor=-92.0,
                frequency=2.4
            ),
            EnvironmentType.INDOOR_RESIDENTIAL: ChannelParameters(
                path_loss_exponent=1.8,
                reference_path_loss=38.0,
                shadowing_std=3.5,
                noise_floor=-96.0,
                frequency=2.4,
            ),
            EnvironmentType.OUTDOOR_OPEN: ChannelParameters(
                path_loss_exponent=2.1,
                reference_path_loss=32.0,
                shadowing_std=4.0,
                noise_floor=-98.0,
                frequency=2.4
            ),
            EnvironmentType.OUTDOOR_SUBURBAN: ChannelParameters(
                path_loss_exponent=2.8,
                reference_path_loss=38.0,
                shadowing_std=7.5,
                noise_floor=-96.0,
                frequency=2.4
            ),
            EnvironmentType.OUTDOOR_URBAN: ChannelParameters(
                path_loss_exponent=3.4,
                reference_path_loss=44.0,
                shadowing_std=12.0,
                noise_floor=-93.0,
                frequency=2.4
            ),
            # Compatibility aliases mapping
            EnvironmentType.INDUSTRIAL: ChannelParameters(
                path_loss_exponent=3.0,
                reference_path_loss=50.0,
                shadowing_std=6.0,
                noise_floor=-93.0,
                frequency=2.4
            ),
            EnvironmentType.URBAN: ChannelParameters(
                path_loss_exponent=3.4,
                reference_path_loss=44.0,
                shadowing_std=12.0,
                noise_floor=-93.0,
                frequency=2.4
            ),
        }
        return params_dict[env]
    
    def calculate_path_loss(self, distance: float, reference_distance: float = 1.0) -> float:
        """
        Calculate path loss (dB) using the log-distance model with log-normal shadowing.
        
        Args:
            distance: transmitter-receiver distance in meters
            reference_distance: reference distance in meters (default 1.0)
            
        Returns:
            Path loss in dB.
        """
        if distance < reference_distance:
            distance = reference_distance
            
        # Log-distance component (log-distance model)
        path_loss = (self.params.reference_path_loss + 
                    10 * self.params.path_loss_exponent * 
                    math.log10(distance / reference_distance))
        
        # Shadowing term (log-normal) - 支持外部RNG
        shadowing = np.random.normal(0, self.params.shadowing_std)

        return path_loss + shadowing

    def calculate_path_loss_with_rng(self, distance: float, rng, reference_distance: float = 1.0) -> float:
        """使用独立RNG计算路径损耗"""
        if distance <= 0:
            distance = 0.1
        path_loss = (self.params.reference_path_loss +
                    10 * self.params.path_loss_exponent *
                    math.log10(distance / reference_distance))
        shadowing = rng.normal(0, self.params.shadowing_std)
        return path_loss + shadowing
    
    def calculate_received_power(self, tx_power_dbm: float, distance: float) -> float:
        """
        Calculate received power (dBm) at a given distance.
        
        Args:
            tx_power_dbm: transmit power in dBm
            distance: distance in meters
            
        Returns:
            Received power in dBm.
        """
        path_loss = self.calculate_path_loss(distance)
        return tx_power_dbm - path_loss

    def calculate_received_power_with_rng(self, tx_power_dbm: float, distance: float, rng) -> float:
        """使用独立RNG计算接收功率"""
        path_loss = self.calculate_path_loss_with_rng(distance, rng)
        return tx_power_dbm - path_loss

class IEEE802154LinkQuality:
    """
    IEEE 802.15.4 link quality model based on RSSI.
    Based on Srinivasan & Levis.
    """
    
    def __init__(self):
        # IEEE 802.15.4 standard parameters
        self.sensitivity_threshold = -85.0  # dBm
        self.max_lqi = 255
        self.rssi_measurement_std = 2.0     # RSSI measurement std (dB)
    def calculate_rssi(self, received_power_dbm: float) -> float:
        """
        Calculate RSSI value (includes measurement noise).
        
        Args:
            received_power_dbm: received power in dBm
            
        Returns:
            RSSI in dBm.
        """
        measurement_noise = np.random.normal(0, self.rssi_measurement_std)
        return received_power_dbm + measurement_noise

    def calculate_rssi_with_rng(self, received_power_dbm: float, rng) -> float:
        """使用独立RNG计算RSSI"""
        measurement_noise = rng.normal(0, self.rssi_measurement_std)
        return received_power_dbm + measurement_noise
    
    def calculate_lqi(self, rssi_dbm: float) -> int:
        """
        Calculate LQI value based on RSSI.
        
        Args:
            rssi_dbm: RSSI in dBm
            
        Returns:
            LQI in [0, 255].
        """
        if rssi_dbm < self.sensitivity_threshold:
            return 0
        
        # 绾挎€ф槧灏? RSSI -> LQI
        rssi_range = abs(self.sensitivity_threshold - (-20))  # -85 to -20 dBm
        normalized_rssi = (rssi_dbm - self.sensitivity_threshold) / rssi_range
        lqi = int(normalized_rssi * self.max_lqi)
        
        return max(0, min(self.max_lqi, lqi))
    
    def calculate_pdr(self, rssi_dbm: float) -> float:
        """
        Estimate Packet Delivery Ratio (PDR) from RSSI using a piecewise model.
        Calibrated to match NS-3 INDOOR_LOS results.

        Args:
            rssi_dbm: RSSI in dBm

        Returns:
            PDR in [0.0, 1.0].
        """
        if rssi_dbm < self.sensitivity_threshold:
            return 0.0

        # Calibrated based on NS-3 cross-validation
        if rssi_dbm > -60:
            # Strong signal region
            return 0.999
        elif rssi_dbm > -70:
            # Good signal region
            return 0.98 + 0.019 * (rssi_dbm + 70) / 10
        elif rssi_dbm > -80:
            # Transitional region
            return 0.80 + 0.18 * (rssi_dbm + 80) / 10
        else:
            # Weak signal region
            return max(0.0, (rssi_dbm + 85) / 5 * 0.80)

class InterferenceModel:
    """
    Interference modeling based on SINR.
    """
    
    def __init__(self, noise_floor_dbm: float = -95.0):
        self.noise_floor = noise_floor_dbm
        self.interference_sources: List[Dict] = []
        
    def add_interference_source(self, power_dbm: float, distance: float, 
                              source_type: str = "wifi"):
        """
        Add an interference source.
        
        Args:
            power_dbm: interferer transmit power in dBm
            distance: distance to interferer in meters
            source_type: type label for the interferer
        """
        self.interference_sources.append({
            'power': power_dbm,
            'distance': distance,
            'type': source_type
        })
    
    def calculate_sinr(self, signal_power_dbm: float) -> float:
        """
        Compute Signal-to-Interference-plus-Noise Ratio (SINR) in dB.

        Args:
            signal_power_dbm: received signal power in dBm

        Returns:
            SINR (dB)
        """
        signal_power_mw = 10 ** (signal_power_dbm / 10)
        noise_power_mw = 10 ** (self.noise_floor / 10)

        # Compute total interference power (mW)
        total_interference_mw = 0.0
        for source in self.interference_sources:
            # Interference received power at source (mW)
            interference_power_mw = 10 ** (source['power'] / 10)
            # Use distance-based path-loss attenuation (exponent ~2.5)
            path_loss_linear = (source['distance'] / 1.0) ** 2.5
            interference_power_mw /= max(path_loss_linear, 1.0)
            total_interference_mw += interference_power_mw

        # 濡傛灉娌℃湁骞叉壈婧愶紝鍙€冭檻鍣０
        if not self.interference_sources:
            total_interference_mw = 0

        sinr_linear = signal_power_mw / (noise_power_mw + total_interference_mw)
        return 10 * math.log10(max(sinr_linear, 1e-10))  # avoid log(0)
    
    def calculate_interference_pdr(self, sinr_db: float) -> float:
        """
        Estimate PDR under interference using SINR.
        Calibrated to match NS-3 INDOOR_LOS results (avg_snr ~24dB -> PDR ~99.98%)

        Args:
            sinr_db: SINR in dB

        Returns:
            PDR in [0.0, 1.0].
        """
        # Calibrated thresholds based on NS-3 cross-validation
        if sinr_db > 20:
            return 0.999  # NS-3 shows ~99.98% at 24dB
        elif sinr_db > 15:
            return 0.98 + 0.019 * (sinr_db - 15) / 5
        elif sinr_db > 10:
            return 0.90 + 0.08 * (sinr_db - 10) / 5
        elif sinr_db > 5:
            return 0.70 + 0.20 * (sinr_db - 5) / 5
        elif sinr_db > 0:
            return 0.30 + 0.40 * sinr_db / 5
        else:
            return 0.05  # minimum PDR

class EnvironmentalFactors:
    """
    Environmental factors affecting the signal.
    """
    
    @staticmethod
    def temperature_effect_on_battery(temperature_c: float) -> float:
        """
        Calculate temperature effect on battery.
        
        Args:
            temperature_c: temperature (deg C)
            
        Returns:
            Battery capacity factor (0.0-1.0)
        """
        if temperature_c < 0:
            # Low temperature reduces battery capacity
            capacity_factor = 1.0 - abs(temperature_c) * 0.02
        elif temperature_c > 40:
            # High temperature reduces battery efficiency
            capacity_factor = 1.0 - (temperature_c - 40) * 0.01
        else:
            capacity_factor = 1.0
        
        return max(0.3, capacity_factor)  # minimum 30% capacity retained
    
    @staticmethod
    def humidity_effect_on_signal(humidity_ratio: float, 
                                 frequency_ghz: float = 2.4) -> float:
        """
        Calculate humidity effect on signal.
        
        Args:
            humidity_ratio: humidity ratio (0.0-1.0)
            frequency_ghz: frequency (GHz)
            
        Returns:
            Absorption coefficient (dB/km)
        """
        # Water vapor absorption (simplified model)
        if frequency_ghz == 2.4:
            absorption_coeff = 0.1 * humidity_ratio
        else:
            absorption_coeff = 0.05 * humidity_ratio
        
        return absorption_coeff

class RealisticChannelModel:
    # 可选的环境参数映射（用于调整模型参数）；若为 None 则使用当前模型默认参数
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
    综合的真实信道模型：整合路径损耗、链路质量、干扰与环境因素
    """
    
    def __init__(self, environment: EnvironmentType):
        self.path_loss_model = LogNormalShadowingModel(environment)
        self.link_quality = IEEE802154LinkQuality()
        self.interference = InterferenceModel(
            self.path_loss_model.params.noise_floor
        )
        self.environment_type = environment
        self.dropout_rate = 0.0
        # 独立的随机数生成器，避免污染全局随机状态
        self._rng = np.random.default_rng()

    def set_dropout_rate(self, rate: float) -> None:
        """设置统一的信道dropout率，对所有协议公平应用"""
        self.dropout_rate = max(0.0, min(1.0, rate))

    def add_interference_source(self, power_dbm: float, distance: float, source_type: str = "wifi") -> None:
        """Convenience wrapper to add an interference source.

        Kept for compatibility with protocol modules that call
        RealisticChannelModel.add_interference_source directly.
        """
        self.interference.add_interference_source(power_dbm, distance, source_type)
        
    def calculate_link_metrics(self, tx_power_dbm: float, distance: float,
                             temperature_c: float = 25.0,
                             humidity_ratio: float = 0.5) -> Dict:
        """
        璁＄畻瀹屾暣鐨勯摼璺寚鏍?        
        Args:
            tx_power_dbm: 鍙戝皠鍔熺巼 (dBm)
            distance: 浼犺緭璺濈 (m)
            temperature_c: 娓╁害 (掳C)
            humidity_ratio: 鐩稿婀垮害 (0.0-1.0)
            
        Returns:
            閾捐矾鎸囨爣瀛楀吀
        """
        # 1. 使用独立RNG计算接收功率
        received_power = self.path_loss_model.calculate_received_power_with_rng(
            tx_power_dbm, distance, self._rng
        )
        
        # 2. 鐜鍥犵礌淇
        humidity_loss = EnvironmentalFactors.humidity_effect_on_signal(
            humidity_ratio
        ) * distance / 1000  # 杞崲涓哄疄闄呮崯鑰?        received_power -= humidity_loss
        
        # 3. 使用独立RNG计算RSSI和LQI
        rssi = self.link_quality.calculate_rssi_with_rng(received_power, self._rng)
        lqi = self.link_quality.calculate_lqi(rssi)
        
        # 4. 璁＄畻PDR (鑰冭檻骞叉壈)
        sinr = self.interference.calculate_sinr(received_power)
        pdr_interference = self.interference.calculate_interference_pdr(sinr)
        pdr_rssi = self.link_quality.calculate_pdr(rssi)
        pdr = min(pdr_interference, pdr_rssi)

        # 应用统一dropout率（对所有协议公平）
        if self.dropout_rate > 0:
            pdr = pdr * (1.0 - self.dropout_rate)        
        # 5. 鐢垫睜瀹归噺褰卞搷
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

    def reset_rng(self, seed: int) -> None:
        """重置独立随机数生成器状态，确保协议间随机性一致"""
        self._rng = np.random.default_rng(seed)

# 浣跨敤绀轰緥
if __name__ == "__main__":
    # 鍒涘缓宸ュ巶鐜鐨勪俊閬撴ā鍨?    channel = RealisticChannelModel(EnvironmentType.INDOOR_FACTORY)
    
    # 娣诲姞WiFi骞叉壈婧?    channel.interference.add_interference_source(-30, 10, "wifi")
    
    # 璁＄畻閾捐矾鎸囨爣
    metrics = channel.calculate_link_metrics(
        tx_power_dbm=0,      # 0dBm鍙戝皠鍔熺巼
        distance=50,         # 50m璺濈
        temperature_c=35,    # 35掳C娓╁害
        humidity_ratio=0.8   # 80%婀垮害
    )
    
    print("Link metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")

