#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多数据集下载和预处理脚本

支持的数据集：
1. Intel Berkeley Lab (已有)
2. SensorScope EPFL - 户外山地环境
3. CRAWDAD Dartmouth - 校园WiFi/传感器
4. 合成数据集 - 多种拓扑和规模
"""

import os
import sys
import json
import gzip
import urllib.request
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# 数据目录
DATA_DIR = Path('data')
DATASETS_DIR = DATA_DIR / 'multi_datasets'
DATASETS_DIR.mkdir(parents=True, exist_ok=True)


class DatasetDownloader:
    """数据集下载器"""
    
    # 公开可用的WSN数据集URL
    DATASETS = {
        'sensorscope_grandst': {
            'name': 'SensorScope Grand-St-Bernard',
            'url': 'https://zenodo.org/record/3610078/files/sensorscope_grandst.csv.gz',
            'description': '户外山地环境，97节点，恶劣天气条件',
            'nodes': 97,
            'environment': 'outdoor_mountain',
            'features': ['temperature', 'humidity', 'wind', 'rain']
        },
        'flocklab': {
            'name': 'FlockLab ETH',
            'url': 'https://www.flocklab.ethz.ch/user/downloads/',
            'description': '室内测试床，30节点，精确控制',
            'nodes': 30,
            'environment': 'indoor_testbed',
            'features': ['rssi', 'lqi', 'temperature']
        }
    }
    
    def __init__(self):
        self.downloaded = {}
    
    def download_file(self, url: str, dest: Path) -> bool:
        """下载文件"""
        try:
            print(f"  下载: {url}")
            urllib.request.urlretrieve(url, dest)
            return True
        except Exception as e:
            print(f"  下载失败: {e}")
            return False
    
    def generate_synthetic_datasets(self):
        """生成合成数据集"""
        print("\n生成合成数据集...")
        
        configs = [
            # 不同拓扑
            {'name': 'grid_10x10', 'topology': 'grid', 'nodes': 100, 'area': (100, 100)},
            {'name': 'grid_15x15', 'topology': 'grid', 'nodes': 225, 'area': (150, 150)},
            {'name': 'random_100', 'topology': 'random', 'nodes': 100, 'area': (100, 100)},
            {'name': 'random_200', 'topology': 'random', 'nodes': 200, 'area': (150, 150)},
            {'name': 'random_500', 'topology': 'random', 'nodes': 500, 'area': (250, 250)},
            {'name': 'corridor_narrow', 'topology': 'corridor', 'nodes': 50, 'area': (200, 30)},
            {'name': 'corridor_wide', 'topology': 'corridor', 'nodes': 100, 'area': (300, 50)},
            {'name': 'cluster_4', 'topology': 'cluster', 'nodes': 100, 'clusters': 4, 'area': (100, 100)},
            {'name': 'cluster_8', 'topology': 'cluster', 'nodes': 200, 'clusters': 8, 'area': (150, 150)},
            # 不同环境条件
            {'name': 'harsh_indoor', 'topology': 'random', 'nodes': 100, 'area': (80, 80), 
             'channel': {'path_loss_exp': 3.5, 'shadowing_std': 8.0}},
            {'name': 'mild_outdoor', 'topology': 'random', 'nodes': 100, 'area': (150, 150),
             'channel': {'path_loss_exp': 2.5, 'shadowing_std': 4.0}},
            {'name': 'industrial', 'topology': 'grid', 'nodes': 64, 'area': (80, 80),
             'channel': {'path_loss_exp': 4.0, 'shadowing_std': 10.0}},
        ]
        
        for cfg in configs:
            self._generate_single_dataset(cfg)
        
        print(f"  ✓ 生成了 {len(configs)} 个合成数据集")
    
    def _generate_single_dataset(self, config: Dict):
        """生成单个合成数据集"""
        name = config['name']
        topology = config['topology']
        nodes = config['nodes']
        area = config['area']
        
        output_dir = DATASETS_DIR / 'synthetic' / name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成节点位置
        if topology == 'grid':
            side = int(np.sqrt(nodes))
            x = np.linspace(5, area[0]-5, side)
            y = np.linspace(5, area[1]-5, side)
            xx, yy = np.meshgrid(x, y)
            positions = np.column_stack([xx.ravel(), yy.ravel()])[:nodes]
        elif topology == 'corridor':
            positions = np.column_stack([
                np.random.uniform(5, area[0]-5, nodes),
                np.random.uniform(5, area[1]-5, nodes)
            ])
        elif topology == 'cluster':
            n_clusters = config.get('clusters', 4)
            cluster_centers = np.random.uniform(20, min(area)-20, (n_clusters, 2))
            positions = []
            per_cluster = nodes // n_clusters
            for center in cluster_centers:
                cluster_pos = center + np.random.randn(per_cluster, 2) * 10
                positions.extend(cluster_pos)
            positions = np.array(positions)[:nodes]
        else:  # random
            positions = np.column_stack([
                np.random.uniform(5, area[0]-5, nodes),
                np.random.uniform(5, area[1]-5, nodes)
            ])
        
        # 生成环境数据 (模拟36天，每小时采样)
        n_samples = 36 * 24  # 36天
        timestamps = np.arange(n_samples)
        
        # 温度：日周期 + 随机波动
        base_temp = 22 + 5 * np.sin(2 * np.pi * timestamps / 24)
        temperature = base_temp + np.random.randn(n_samples) * 2
        
        # 湿度：与温度负相关
        humidity = 60 - 0.5 * (temperature - 22) + np.random.randn(n_samples) * 5
        humidity = np.clip(humidity, 30, 90)
        
        # 保存数据
        np.savez(output_dir / 'topology.npz', 
                 positions=positions, 
                 area=np.array(area),
                 n_nodes=nodes)
        
        np.savez(output_dir / 'environment.npz',
                 timestamps=timestamps,
                 temperature=temperature,
                 humidity=humidity)
        
        # 保存配置
        with open(output_dir / 'config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"    ✓ {name}: {nodes}节点, {area[0]}x{area[1]}m")


class SyntheticTraceGenerator:
    """合成trace数据生成器 - 模拟真实WSN行为"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.n_nodes = config['nodes']
        self.area = config['area']
        
    def generate_trace(self, duration_hours: int = 864) -> Dict:
        """生成完整的trace数据 (默认36天)"""
        n_samples = duration_hours
        
        # 节点位置
        positions = self._generate_positions()
        
        # 环境数据
        env_data = self._generate_environment(n_samples)
        
        # 链路质量数据
        link_data = self._generate_link_quality(positions, env_data)
        
        # 能量数据
        energy_data = self._generate_energy(n_samples)
        
        return {
            'positions': positions,
            'environment': env_data,
            'links': link_data,
            'energy': energy_data,
            'config': self.config
        }
    
    def _generate_positions(self) -> np.ndarray:
        """生成节点位置"""
        topology = self.config.get('topology', 'random')
        
        if topology == 'grid':
            side = int(np.ceil(np.sqrt(self.n_nodes)))
            x = np.linspace(5, self.area[0]-5, side)
            y = np.linspace(5, self.area[1]-5, side)
            xx, yy = np.meshgrid(x, y)
            positions = np.column_stack([xx.ravel(), yy.ravel()])[:self.n_nodes]
        else:
            positions = np.column_stack([
                np.random.uniform(5, self.area[0]-5, self.n_nodes),
                np.random.uniform(5, self.area[1]-5, self.n_nodes)
            ])
        
        return positions
    
    def _generate_environment(self, n_samples: int) -> Dict:
        """生成环境数据"""
        t = np.arange(n_samples)
        
        # 温度：日周期 + 季节趋势 + 噪声
        daily = 5 * np.sin(2 * np.pi * t / 24)
        seasonal = 3 * np.sin(2 * np.pi * t / (24 * 30))
        noise = np.random.randn(n_samples) * 1.5
        temperature = 22 + daily + seasonal + noise
        
        # 湿度：与温度负相关
        humidity = 55 - 0.8 * (temperature - 22) + np.random.randn(n_samples) * 4
        humidity = np.clip(humidity, 25, 95)
        
        return {
            'temperature': temperature,
            'humidity': humidity,
            'timestamps': t
        }
    
    def _generate_link_quality(self, positions: np.ndarray, env_data: Dict) -> Dict:
        """生成链路质量数据"""
        n_samples = len(env_data['temperature'])
        
        # 计算节点间距离 (不使用scipy)
        n = len(positions)
        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                distances[i,j] = np.sqrt(np.sum((positions[i] - positions[j])**2))
        
        # 基础链路质量 (基于距离)
        channel = self.config.get('channel', {})
        path_loss_exp = channel.get('path_loss_exp', 3.0)
        shadowing_std = channel.get('shadowing_std', 6.0)
        
        # 参考距离处的路径损耗
        d0 = 1.0
        pl_d0 = 55  # dBm at 1m
        
        # 计算每对节点的平均RSSI
        rssi_base = np.zeros_like(distances)
        for i in range(self.n_nodes):
            for j in range(self.n_nodes):
                if i != j and distances[i,j] > 0:
                    rssi_base[i,j] = -pl_d0 - 10 * path_loss_exp * np.log10(distances[i,j] / d0)
        
        # 时变链路质量 (受环境影响)
        humidity = env_data['humidity']
        humidity_effect = -0.1 * (humidity - 50)  # 湿度影响
        
        return {
            'distances': distances,
            'rssi_base': rssi_base,
            'humidity_effect': humidity_effect,
            'shadowing_std': shadowing_std
        }
    
    def _generate_energy(self, n_samples: int) -> Dict:
        """生成能量数据"""
        # 初始能量
        initial_energy = np.random.uniform(1.8, 2.2, self.n_nodes)
        
        # 能量消耗率 (每小时)
        consumption_rate = np.random.uniform(0.001, 0.003, self.n_nodes)
        
        return {
            'initial': initial_energy,
            'consumption_rate': consumption_rate
        }


def main():
    """主函数"""
    print("=" * 60)
    print("🌐 多数据集下载和生成")
    print("=" * 60)
    
    downloader = DatasetDownloader()
    
    # 1. 生成合成数据集
    downloader.generate_synthetic_datasets()
    
    # 2. 生成详细trace数据
    print("\n生成详细trace数据...")
    
    trace_configs = [
        {'name': 'trace_indoor_small', 'topology': 'random', 'nodes': 50, 'area': (50, 50),
         'channel': {'path_loss_exp': 3.0, 'shadowing_std': 6.0}},
        {'name': 'trace_indoor_medium', 'topology': 'random', 'nodes': 100, 'area': (80, 80),
         'channel': {'path_loss_exp': 3.2, 'shadowing_std': 7.0}},
        {'name': 'trace_indoor_large', 'topology': 'random', 'nodes': 200, 'area': (120, 120),
         'channel': {'path_loss_exp': 3.5, 'shadowing_std': 8.0}},
        {'name': 'trace_outdoor_sparse', 'topology': 'random', 'nodes': 100, 'area': (200, 200),
         'channel': {'path_loss_exp': 2.5, 'shadowing_std': 4.0}},
        {'name': 'trace_outdoor_dense', 'topology': 'random', 'nodes': 300, 'area': (150, 150),
         'channel': {'path_loss_exp': 2.8, 'shadowing_std': 5.0}},
        {'name': 'trace_industrial', 'topology': 'grid', 'nodes': 100, 'area': (100, 100),
         'channel': {'path_loss_exp': 4.0, 'shadowing_std': 10.0}},
    ]
    
    for cfg in trace_configs:
        output_dir = DATASETS_DIR / 'traces' / cfg['name']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generator = SyntheticTraceGenerator(cfg)
        trace = generator.generate_trace(duration_hours=864)  # 36天
        
        # 保存trace
        np.savez(output_dir / 'trace.npz', **{
            'positions': trace['positions'],
            'temperature': trace['environment']['temperature'],
            'humidity': trace['environment']['humidity'],
            'distances': trace['links']['distances'],
            'rssi_base': trace['links']['rssi_base'],
            'initial_energy': trace['energy']['initial']
        })
        
        with open(output_dir / 'config.json', 'w') as f:
            json.dump(cfg, f, indent=2)
        
        print(f"  ✓ {cfg['name']}: {cfg['nodes']}节点")
    
    print("\n" + "=" * 60)
    print("✅ 数据集准备完成")
    print(f"📁 输出目录: {DATASETS_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()
