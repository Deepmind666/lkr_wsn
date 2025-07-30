#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于2024-2025年最新文献的WSN能耗模型

参考文献:
[1] "GSHFA-HCP: a novel intelligent high-performance clustering" (Nature 2024)
[2] "An Adaptive Energy-Efficient Uneven Clustering Routing Protocol" (IEEE 2024)
[3] "Energy-efficient synchronization for body sensor network" (2025)
[4] "Adaptive Jamming Mitigation for Clustered Energy-Efficient LoRa" (2025)

技术特点:
- 基于最新实验测量的能耗参数
- 考虑传输、接收、处理、待机等全部能耗组件
- 支持不同硬件平台的能耗特性
- 包含环境因素对能耗的影响

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 2.0 (基于最新文献优化)
"""

import numpy as np
import math
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class HardwarePlatform(Enum):
    """硬件平台类型"""
    CC2420_TELOSB = "cc2420_telosb"      # 经典WSN平台
    CC2650_SENSORTAG = "cc2650_sensortag" # 现代低功耗平台
    ESP32_LORA = "esp32_lora"            # LoRa平台
    GENERIC_WSN = "generic_wsn"          # 通用WSN节点

@dataclass
class EnergyParameters:
    """能耗参数配置"""
    # 传输能耗 (基于2024-2025年最新文献)
    tx_energy_per_bit: float      # J/bit
    rx_energy_per_bit: float      # J/bit
    
    # 处理能耗
    processing_energy_per_bit: float  # J/bit
    
    # 功耗参数
    idle_power: float             # W (空闲功耗)
    sleep_power: float            # W (睡眠功耗)
    
    # 放大器参数
    amplifier_efficiency: float   # 放大器效率
    path_loss_threshold: float    # 路径损耗阈值 (m)

class ImprovedEnergyModel:
    """
    改进的WSN能耗模型
    基于2024-2025年最新文献的完整能耗建模
    """
    
    def __init__(self, platform: HardwarePlatform = HardwarePlatform.GENERIC_WSN):
        self.platform = platform
        self.params = self._get_platform_parameters(platform)
        
        # 环境因素影响系数
        self.temperature_coefficient = 0.02  # 每度温度变化的能耗影响
        self.humidity_coefficient = 0.01     # 湿度对能耗的影响
        
    def _get_platform_parameters(self, platform: HardwarePlatform) -> EnergyParameters:
        """根据硬件平台获取能耗参数"""
        
        # 基于2024-2025年最新文献的实测参数
        params_dict = {
            HardwarePlatform.CC2420_TELOSB: EnergyParameters(
                tx_energy_per_bit=208.8e-9,   # 208.8 nJ/bit (基于17.4mA@3V@250kbps)
                rx_energy_per_bit=225.6e-9,   # 225.6 nJ/bit (基于18.8mA@3V@250kbps)
                processing_energy_per_bit=5e-9,  # 5 nJ/bit (处理能耗)
                idle_power=1.4e-3,            # 1.4 mW (空闲功耗)
                sleep_power=15e-6,            # 15 μW (睡眠功耗)
                amplifier_efficiency=0.5,     # 50% (功放效率，修复后)
                path_loss_threshold=87.0      # 87m (自由空间vs多径阈值)
            ),
            
            HardwarePlatform.CC2650_SENSORTAG: EnergyParameters(
                tx_energy_per_bit=16.7e-9,    # 16.7 nJ/bit (2025年BSN研究)
                rx_energy_per_bit=36.1e-9,    # 36.1 nJ/bit (最新测量)
                processing_energy_per_bit=3e-9,  # 3 nJ/bit (低功耗处理器)
                idle_power=0.8e-3,            # 0.8 mW (改进的空闲功耗)
                sleep_power=5e-6,             # 5 μW (深度睡眠)
                amplifier_efficiency=0.45,    # 45% (现代功放)
                path_loss_threshold=100.0     # 100m
            ),
            
            HardwarePlatform.ESP32_LORA: EnergyParameters(
                tx_energy_per_bit=200e-9,     # 200 nJ/bit (LoRa高功耗)
                rx_energy_per_bit=100e-9,     # 100 nJ/bit (LoRa接收)
                processing_energy_per_bit=10e-9, # 10 nJ/bit (ESP32处理)
                idle_power=2.5e-3,            # 2.5 mW (ESP32空闲)
                sleep_power=100e-6,           # 100 μW (ESP32睡眠)
                amplifier_efficiency=0.25,    # 25% (LoRa功放效率较低)
                path_loss_threshold=1000.0    # 1km (LoRa长距离)
            ),
            
            HardwarePlatform.GENERIC_WSN: EnergyParameters(
                tx_energy_per_bit=50e-9,      # 通用参数 (基于文献平均值)
                rx_energy_per_bit=50e-9,
                processing_energy_per_bit=5e-9,
                idle_power=1.0e-3,            # 1.0 mW
                sleep_power=10e-6,            # 10 μW
                amplifier_efficiency=0.35,
                path_loss_threshold=87.0
            )
        }
        
        return params_dict[platform]
    
    def calculate_transmission_energy(self, 
                                    data_size_bits: int,
                                    distance: float,
                                    tx_power_dbm: float = 0.0,
                                    temperature_c: float = 25.0,
                                    humidity_ratio: float = 0.5) -> float:
        """
        计算传输能耗
        
        Args:
            data_size_bits: 数据大小 (bits)
            distance: 传输距离 (m)
            tx_power_dbm: 发射功率 (dBm)
            temperature_c: 环境温度 (°C)
            humidity_ratio: 相对湿度 (0-1)
            
        Returns:
            传输能耗 (J)
        """
        
        # 基础传输能耗
        base_tx_energy = data_size_bits * self.params.tx_energy_per_bit
        
        # 功率放大器能耗 (基于距离和发射功率)
        tx_power_linear = 10**(tx_power_dbm / 10) / 1000  # 转换为瓦特
        
        # 根据距离选择传播模型
        if distance <= self.params.path_loss_threshold:
            # 自由空间传播: Pamp = ε_fs * d^2
            amplifier_energy = (tx_power_linear / self.params.amplifier_efficiency) * \
                             (distance ** 2) * 1e-12  # ε_fs = 10 pJ/bit/m^2
        else:
            # 多径传播: Pamp = ε_mp * d^4
            amplifier_energy = (tx_power_linear / self.params.amplifier_efficiency) * \
                             (distance ** 4) * 1e-15  # ε_mp = 0.0013 pJ/bit/m^4
        
        # 环境因素影响
        temp_factor = 1 + self.temperature_coefficient * abs(temperature_c - 25.0)
        humidity_factor = 1 + self.humidity_coefficient * humidity_ratio
        
        total_energy = (base_tx_energy + amplifier_energy) * temp_factor * humidity_factor
        
        return total_energy
    
    def calculate_reception_energy(self, 
                                 data_size_bits: int,
                                 temperature_c: float = 25.0,
                                 humidity_ratio: float = 0.5) -> float:
        """
        计算接收能耗
        
        Args:
            data_size_bits: 数据大小 (bits)
            temperature_c: 环境温度 (°C)
            humidity_ratio: 相对湿度 (0-1)
            
        Returns:
            接收能耗 (J)
        """
        
        # 基础接收能耗
        base_rx_energy = data_size_bits * self.params.rx_energy_per_bit
        
        # 环境因素影响
        temp_factor = 1 + self.temperature_coefficient * abs(temperature_c - 25.0)
        humidity_factor = 1 + self.humidity_coefficient * humidity_ratio
        
        total_energy = base_rx_energy * temp_factor * humidity_factor
        
        return total_energy
    
    def calculate_processing_energy(self, 
                                  data_size_bits: int,
                                  processing_complexity: float = 1.0) -> float:
        """
        计算数据处理能耗
        
        Args:
            data_size_bits: 数据大小 (bits)
            processing_complexity: 处理复杂度系数 (1.0为基础处理)
            
        Returns:
            处理能耗 (J)
        """
        
        base_processing_energy = data_size_bits * self.params.processing_energy_per_bit
        return base_processing_energy * processing_complexity
    
    def calculate_idle_energy(self, idle_time_seconds: float) -> float:
        """
        计算空闲状态能耗
        
        Args:
            idle_time_seconds: 空闲时间 (秒)
            
        Returns:
            空闲能耗 (J)
        """
        return self.params.idle_power * idle_time_seconds
    
    def calculate_sleep_energy(self, sleep_time_seconds: float) -> float:
        """
        计算睡眠状态能耗
        
        Args:
            sleep_time_seconds: 睡眠时间 (秒)
            
        Returns:
            睡眠能耗 (J)
        """
        return self.params.sleep_power * sleep_time_seconds
    
    def calculate_total_communication_energy(self,
                                           data_size_bits: int,
                                           distance: float,
                                           tx_power_dbm: float = 0.0,
                                           include_processing: bool = True,
                                           temperature_c: float = 25.0,
                                           humidity_ratio: float = 0.5) -> Dict[str, float]:
        """
        计算完整的通信能耗 (发送+接收+处理)
        
        Returns:
            包含各组件能耗的字典
        """
        
        tx_energy = self.calculate_transmission_energy(
            data_size_bits, distance, tx_power_dbm, temperature_c, humidity_ratio
        )
        
        rx_energy = self.calculate_reception_energy(
            data_size_bits, temperature_c, humidity_ratio
        )
        
        processing_energy = 0.0
        if include_processing:
            processing_energy = self.calculate_processing_energy(data_size_bits)
        
        total_energy = tx_energy + rx_energy + processing_energy
        
        return {
            'transmission_energy': tx_energy,
            'reception_energy': rx_energy,
            'processing_energy': processing_energy,
            'total_energy': total_energy,
            'energy_breakdown': {
                'tx_percentage': (tx_energy / total_energy) * 100,
                'rx_percentage': (rx_energy / total_energy) * 100,
                'processing_percentage': (processing_energy / total_energy) * 100
            }
        }
    
    def get_energy_efficiency_metrics(self, 
                                    data_size_bits: int,
                                    distance: float) -> Dict[str, float]:
        """
        计算能效指标
        
        Returns:
            能效相关指标
        """
        
        energy_result = self.calculate_total_communication_energy(data_size_bits, distance)
        
        # 能效指标
        energy_per_bit = energy_result['total_energy'] / data_size_bits
        energy_per_meter = energy_result['total_energy'] / distance if distance > 0 else 0
        
        return {
            'energy_per_bit': energy_per_bit,           # J/bit
            'energy_per_meter': energy_per_meter,       # J/m
            'energy_per_byte': energy_per_bit * 8,      # J/byte
            'platform': self.platform.value,
            'total_energy': energy_result['total_energy']
        }

# 测试和验证函数
def test_energy_model():
    """测试改进的能耗模型"""
    
    print("🧪 测试改进的WSN能耗模型")
    print("=" * 50)
    
    # 测试不同硬件平台
    platforms = [
        HardwarePlatform.CC2420_TELOSB,
        HardwarePlatform.CC2650_SENSORTAG,
        HardwarePlatform.ESP32_LORA
    ]
    
    test_data_size = 1024  # 1KB数据包
    test_distance = 50.0   # 50m距离
    
    for platform in platforms:
        print(f"\n📱 平台: {platform.value}")
        
        energy_model = ImprovedEnergyModel(platform)
        
        # 计算完整通信能耗
        energy_result = energy_model.calculate_total_communication_energy(
            test_data_size * 8,  # 转换为bits
            test_distance
        )
        
        print(f"   传输能耗: {energy_result['transmission_energy']*1e6:.2f} μJ")
        print(f"   接收能耗: {energy_result['reception_energy']*1e6:.2f} μJ")
        print(f"   处理能耗: {energy_result['processing_energy']*1e6:.2f} μJ")
        print(f"   总能耗: {energy_result['total_energy']*1e6:.2f} μJ")
        
        # 能效指标
        efficiency = energy_model.get_energy_efficiency_metrics(
            test_data_size * 8, test_distance
        )
        print(f"   能效: {efficiency['energy_per_bit']*1e9:.2f} nJ/bit")

if __name__ == "__main__":
    test_energy_model()
