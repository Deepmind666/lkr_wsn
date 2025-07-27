# Enhanced Intel Lab数据集加载模块 - 用于EEHFR协议
# 支持多种数据源和增强的数据预处理功能

import pandas as pd
import numpy as np
import os
import requests
import gzip
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io
import time
import warnings
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.impute import KNNImputer
import seaborn as sns

class IntelLabDataLoader:
    """增强版Intel Berkeley Research Lab数据集加载器

    该数据集包含54个传感器在2004年2月28日至4月5日期间收集的数据，
    包括温度、湿度、光照和电压等信息。

    新增功能：
    - 多源数据集支持
    - 智能数据清洗
    - 数据增强策略
    - 时空特征工程
    """

    def __init__(self, data_dir="../data", use_synthetic=False):
        """初始化数据加载器

        参数:
            data_dir: 数据存储目录
            use_synthetic: 是否使用合成数据（当真实数据不可用时）
        """
        self.data_dir = data_dir
        self.use_synthetic = use_synthetic

        # 真实Intel Lab数据文件路径
        self.data_file = os.path.join(data_dir, "data.txt.gz")
        self.locations_file = os.path.join(data_dir, "Intel_Lab_Data", "mote_locs.txt")
        self.connectivity_file = os.path.join(data_dir, "Intel_Lab_Data", "connectivity.txt")

        # 数据存储
        self.sensor_data = None
        self.connectivity_data = None
        self.locations_data = None
        self.processed_data = None

        # 数据预处理参数
        self.scaler_features = MinMaxScaler()
        self.scaler_targets = MinMaxScaler()
        self.imputer = KNNImputer(n_neighbors=5)

        # 确保数据目录存在
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # 初始化数据
        self._initialize_data()
    
    def _initialize_data(self):
        """初始化数据集"""
        try:
            # 尝试加载真实数据
            if os.path.exists(self.data_file) and os.path.getsize(self.data_file) > 1000:
                self.load_real_data()
                print("✅ 成功加载真实Intel Lab数据集")
            else:
                if self.use_synthetic:
                    self.generate_synthetic_data()
                    print("⚠️ 真实数据不可用，已生成合成数据集")
                else:
                    raise FileNotFoundError("真实数据文件不存在且未启用合成数据")
        except Exception as e:
            print(f"❌ 数据初始化失败: {e}")
            if self.use_synthetic:
                self.generate_synthetic_data()
                print("🔄 已切换到合成数据集")

    def load_real_data(self):
        """加载真实的Intel Lab数据集"""
        print("📂 正在加载真实Intel Lab数据集...")

        # 加载传感器数据
        try:
            # 读取压缩的传感器数据文件
            with gzip.open(self.data_file, 'rt') as f:
                lines = f.readlines()

            # 解析数据
            sensor_data = []
            for line_num, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) >= 8:  # 确保有足够的字段
                    try:
                        # Intel Lab数据格式: date time epoch moteid temperature humidity light voltage
                        date_str = parts[0]
                        time_str = parts[1]
                        epoch = int(parts[2])
                        node_id = int(parts[3])
                        temperature = float(parts[4]) if parts[4] != '-' else np.nan
                        humidity = float(parts[5]) if parts[5] != '-' else np.nan
                        light = float(parts[6]) if parts[6] != '-' else np.nan
                        voltage = float(parts[7]) if parts[7] != '-' else np.nan

                        # 创建时间戳
                        timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f")

                        sensor_data.append({
                            'timestamp': timestamp,
                            'epoch': epoch,
                            'node_id': node_id,
                            'temperature': temperature,
                            'humidity': humidity,
                            'light': light,
                            'voltage': voltage
                        })
                    except (ValueError, IndexError) as e:
                        if line_num < 10:  # 只打印前几行的错误
                            print(f"  警告: 第{line_num+1}行解析失败: {line.strip()[:50]}...")
                        continue  # 跳过格式错误的行

            self.sensor_data = pd.DataFrame(sensor_data)
            print(f"✅ 传感器数据加载完成: {len(self.sensor_data)} 条记录")

        except Exception as e:
            print(f"❌ 传感器数据加载失败: {e}")
            raise

        # 加载位置数据
        try:
            if os.path.exists(self.locations_file):
                locations = []
                with open(self.locations_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            try:
                                node_id = int(parts[0])
                                x = float(parts[1])
                                y = float(parts[2])
                                locations.append({'node_id': node_id, 'x': x, 'y': y})
                            except ValueError:
                                continue

                self.locations_data = pd.DataFrame(locations)
                print(f"✅ 位置数据加载完成: {len(self.locations_data)} 个节点")
            else:
                print("⚠️ 位置数据文件不存在，将生成默认位置")
                self._generate_default_locations()

        except Exception as e:
            print(f"❌ 位置数据加载失败: {e}")
            self._generate_default_locations()

        # 加载连接性数据
        try:
            if os.path.exists(self.connectivity_file):
                connectivity = []
                with open(self.connectivity_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            try:
                                node1 = int(parts[0])
                                node2 = int(parts[1])
                                connectivity.append({'node1': node1, 'node2': node2})
                            except ValueError:
                                continue

                self.connectivity_data = pd.DataFrame(connectivity)
                print(f"✅ 连接性数据加载完成: {len(self.connectivity_data)} 条连接")
            else:
                print("⚠️ 连接性数据文件不存在，将生成默认连接")
                self._generate_connectivity_data()

        except Exception as e:
            print(f"❌ 连接性数据加载失败: {e}")
            self._generate_connectivity_data()

        # 合并位置信息到传感器数据
        if self.locations_data is not None and not self.locations_data.empty:
            self.sensor_data = self.sensor_data.merge(
                self.locations_data[['node_id', 'x', 'y']],
                on='node_id',
                how='left'
            )

        print(f"📊 数据集统计:")
        print(f"   - 节点数量: {self.sensor_data['node_id'].nunique()}")
        print(f"   - 时间范围: {self.sensor_data['timestamp'].min()} 到 {self.sensor_data['timestamp'].max()}")
        print(f"   - 数据列: {list(self.sensor_data.columns)}")

    def _generate_default_locations(self):
        """生成默认的节点位置"""
        unique_nodes = self.sensor_data['node_id'].unique()
        locations = []

        # 简单的网格布局
        cols = int(np.ceil(np.sqrt(len(unique_nodes))))
        for i, node_id in enumerate(sorted(unique_nodes)):
            x = (i % cols) * 5.0
            y = (i // cols) * 5.0
            locations.append({'node_id': node_id, 'x': x, 'y': y})

        self.locations_data = pd.DataFrame(locations)

    def generate_synthetic_data(self):
        """生成高质量的合成WSN数据集"""
        print("🔧 正在生成合成Intel Lab数据集...")

        # 网络参数
        n_nodes = 54  # Intel Lab实际节点数
        n_days = 36   # 数据收集天数
        samples_per_hour = 12  # 每小时采样次数
        total_samples = n_days * 24 * samples_per_hour

        # 生成时间戳
        start_time = datetime(2004, 2, 28, 0, 0, 0)
        timestamps = [start_time + timedelta(minutes=5*i) for i in range(total_samples)]

        # 生成节点位置（基于Intel Lab实际布局）
        np.random.seed(42)  # 确保可重复性
        locations = self._generate_node_locations(n_nodes)

        # 生成传感器数据
        sensor_data = []
        for i, timestamp in enumerate(timestamps):
            for node_id in range(1, n_nodes + 1):
                # 基于时间和位置的真实感数据生成
                temp, humidity, light, voltage = self._generate_sensor_reading(
                    node_id, timestamp, locations[node_id-1], i
                )

                sensor_data.append({
                    'timestamp': timestamp,
                    'node_id': node_id,
                    'temperature': temp,
                    'humidity': humidity,
                    'light': light,
                    'voltage': voltage,
                    'x': locations[node_id-1][0],
                    'y': locations[node_id-1][1]
                })

        # 转换为DataFrame
        self.sensor_data = pd.DataFrame(sensor_data)
        self.locations_data = pd.DataFrame(locations, columns=['x', 'y'])
        self.locations_data['node_id'] = range(1, n_nodes + 1)

        # 生成连接性数据
        self._generate_connectivity_data()

        print(f"✅ 合成数据集生成完成: {len(self.sensor_data)} 条记录")

    def _generate_node_locations(self, n_nodes):
        """生成节点位置（模拟Intel Lab布局）"""
        # Intel Lab是一个大约31m x 23m的实验室
        locations = []

        # 创建网格布局，然后添加随机扰动
        rows, cols = 6, 9
        for i in range(n_nodes):
            row = i // cols
            col = i % cols

            # 基础网格位置
            x = col * 3.5 + np.random.normal(0, 0.5)  # 添加噪声
            y = row * 3.8 + np.random.normal(0, 0.5)

            # 确保在实验室范围内
            x = max(0, min(31, x))
            y = max(0, min(23, y))

            locations.append([x, y])

        return locations

    def _generate_sensor_reading(self, node_id, timestamp, location, sample_idx):
        """生成单个传感器读数"""
        # 基于时间的周期性变化
        hour = timestamp.hour
        day_of_year = timestamp.timetuple().tm_yday

        # 温度模型（考虑日夜变化和季节变化）
        base_temp = 20 + 5 * np.sin(2 * np.pi * hour / 24)  # 日变化
        seasonal_temp = 3 * np.sin(2 * np.pi * day_of_year / 365)  # 季节变化
        spatial_temp = (location[0] + location[1]) * 0.1  # 空间变化
        noise_temp = np.random.normal(0, 1)
        temperature = base_temp + seasonal_temp + spatial_temp + noise_temp

        # 湿度模型（与温度负相关）
        base_humidity = 50 - 0.5 * (temperature - 20)
        humidity_noise = np.random.normal(0, 5)
        humidity = max(0, min(100, base_humidity + humidity_noise))

        # 光照模型（白天高，夜晚低）
        if 6 <= hour <= 18:  # 白天
            base_light = 500 + 300 * np.sin(np.pi * (hour - 6) / 12)
        else:  # 夜晚
            base_light = 50
        light_noise = np.random.normal(0, 50)
        light = max(0, base_light + light_noise)

        # 电压模型（随时间缓慢下降，模拟电池消耗）
        base_voltage = 3.0 - 0.0001 * sample_idx  # 缓慢下降
        voltage_noise = np.random.normal(0, 0.05)
        voltage = max(2.0, base_voltage + voltage_noise)

        return temperature, humidity, light, voltage

    def _generate_connectivity_data(self):
        """生成节点连接性数据"""
        connectivity = []
        locations = self.locations_data[['x', 'y']].values

        # 基于距离的连接性（通信范围约5米）
        comm_range = 5.0

        for i in range(len(locations)):
            for j in range(i + 1, len(locations)):
                distance = np.sqrt(np.sum((locations[i] - locations[j])**2))
                if distance <= comm_range:
                    # 添加一些随机性（信号衰减、障碍物等）
                    connection_prob = max(0, 1 - distance / comm_range)
                    if np.random.random() < connection_prob:
                        connectivity.append({
                            'node1': i + 1,
                            'node2': j + 1,
                            'distance': distance,
                            'link_quality': connection_prob
                        })

        self.connectivity_data = pd.DataFrame(connectivity)
        print(f"✅ 生成了 {len(connectivity)} 条连接记录")

    def download_dataset(self):
        """下载Intel Lab数据集"""
        print("正在下载Intel Lab数据集...")
        
        # 下载传感器数据
        if not os.path.exists(self.data_file):
            print(f"下载传感器数据: {self.data_url}")
            try:
                response = requests.get(self.data_url, stream=True)
                with open(self.data_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print("传感器数据下载完成")
            except Exception as e:
                print(f"下载传感器数据失败: {e}")
        else:
            print("传感器数据已存在，跳过下载")
        
        # 下载连接拓扑数据
        if not os.path.exists(self.topology_file):
            print(f"下载连接拓扑数据: {self.topology_url}")
            try:
                response = requests.get(self.topology_url, stream=True)
                with open(self.topology_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print("连接拓扑数据下载完成")
            except Exception as e:
                print(f"下载连接拓扑数据失败: {e}")
        else:
            print("连接拓扑数据已存在，跳过下载")
        
        # 下载节点位置数据
        if not os.path.exists(self.locations_file):
            print(f"下载节点位置数据: {self.locations_url}")
            try:
                response = requests.get(self.locations_url)
                with open(self.locations_file, 'w') as f:
                    f.write(response.text)
                print("节点位置数据下载完成")
            except Exception as e:
                print(f"下载节点位置数据失败: {e}")
        else:
            print("节点位置数据已存在，跳过下载")
    
    def load_sensor_data(self, sample_size=None):
        """加载传感器数据
        
        参数:
            sample_size: 采样大小，如果为None则加载全部数据
            
        返回:
            传感器数据DataFrame
        """
        print("加载传感器数据...")
        start_time = time.time()
        
        # 定义列名
        columns = ['date', 'time', 'epoch', 'moteid', 'temperature', 'humidity', 'light', 'voltage']
        
        try:
            # 直接打开文本文件
            if sample_size is not None:
                lines = []
                with open(self.data_file, 'rt') as f:
                    for i, line in enumerate(f):
                        if i >= sample_size:
                            break
                        lines.append(line.strip())
                
                # 解析数据
                data = [line.split() for line in lines]
                self.sensor_data = pd.DataFrame(data, columns=columns)
            else:
                # 读取全部数据
                self.sensor_data = pd.read_csv(self.data_file, sep=' ', names=columns)
            
            # 转换数据类型
            self.sensor_data['epoch'] = self.sensor_data['epoch'].astype(int)
            self.sensor_data['moteid'] = self.sensor_data['moteid'].astype(int)
            self.sensor_data['temperature'] = self.sensor_data['temperature'].astype(float)
            self.sensor_data['humidity'] = self.sensor_data['humidity'].astype(float)
            self.sensor_data['light'] = self.sensor_data['light'].astype(float)
            self.sensor_data['voltage'] = self.sensor_data['voltage'].astype(float)
            
            # 合并日期和时间列
            self.sensor_data['timestamp'] = pd.to_datetime(self.sensor_data['date'] + ' ' + self.sensor_data['time'])
            
            # 删除原始日期和时间列
            self.sensor_data = self.sensor_data.drop(['date', 'time'], axis=1)
            
            print(f"传感器数据加载完成，共{len(self.sensor_data)}条记录，耗时{time.time() - start_time:.2f}秒")
            return self.sensor_data
            
        except Exception as e:
            print(f"加载传感器数据失败: {e}")
            return None
    
    def load_connectivity_data(self):
        """加载连接拓扑数据
        
        返回:
            连接拓扑数据DataFrame
        """
        print("加载连接拓扑数据...")
        
        try:
            # 直接打开文本文件
            self.connectivity_data = pd.read_csv(self.topology_file, sep=' ', names=['sender', 'receiver', 'probability'])
            
            # 转换数据类型
            self.connectivity_data['sender'] = self.connectivity_data['sender'].astype(int)
            self.connectivity_data['receiver'] = self.connectivity_data['receiver'].astype(int)
            self.connectivity_data['probability'] = self.connectivity_data['probability'].astype(float)
            
            print(f"连接拓扑数据加载完成，共{len(self.connectivity_data)}条记录")
            return self.connectivity_data
            
        except Exception as e:
            print(f"加载连接拓扑数据失败: {e}")
            return None
    
    def load_locations_data(self):
        """加载节点位置数据
        
        返回:
            节点位置数据DataFrame
        """
        print("加载节点位置数据...")
        
        try:
            # 读取数据
            self.locations_data = pd.read_csv(self.locations_file, sep=' ', names=['moteid', 'x', 'y'])
            
            # 转换数据类型
            self.locations_data['moteid'] = self.locations_data['moteid'].astype(int)
            self.locations_data['x'] = self.locations_data['x'].astype(float)
            self.locations_data['y'] = self.locations_data['y'].astype(float)
            
            print(f"节点位置数据加载完成，共{len(self.locations_data)}条记录")
            return self.locations_data
            
        except Exception as e:
            print(f"加载节点位置数据失败: {e}")
            return None
    
    def get_node_data(self, node_id, start_time=None, end_time=None):
        """获取指定节点的数据
        
        参数:
            node_id: 节点ID
            start_time: 开始时间，格式为'YYYY-MM-DD HH:MM:SS'
            end_time: 结束时间，格式为'YYYY-MM-DD HH:MM:SS'
            
        返回:
            节点数据DataFrame
        """
        if self.sensor_data is None:
            self.load_sensor_data()
        
        # 筛选指定节点的数据
        node_data = self.sensor_data[self.sensor_data['moteid'] == node_id].copy()
        
        # 筛选时间范围
        if start_time is not None:
            start_dt = pd.to_datetime(start_time)
            node_data = node_data[node_data['timestamp'] >= start_dt]
        
        if end_time is not None:
            end_dt = pd.to_datetime(end_time)
            node_data = node_data[node_data['timestamp'] <= end_dt]
        
        return node_data
    
    def get_link_quality(self, sender_id, receiver_id):
        """获取指定链路的质量
        
        参数:
            sender_id: 发送节点ID
            receiver_id: 接收节点ID
            
        返回:
            链路质量（成功概率）
        """
        if self.connectivity_data is None:
            self.load_connectivity_data()
        
        # 筛选指定链路的数据
        link_data = self.connectivity_data[
            (self.connectivity_data['sender'] == sender_id) &
            (self.connectivity_data['receiver'] == receiver_id)
        ]
        
        if len(link_data) > 0:
            return link_data['probability'].values[0]
        else:
            return 0.0
    
    def get_node_location(self, node_id):
        """获取指定节点的位置
        
        参数:
            node_id: 节点ID
            
        返回:
            (x, y) 坐标元组
        """
        if self.locations_data is None:
            self.load_locations_data()
        
        # 筛选指定节点的数据
        node_location = self.locations_data[self.locations_data['moteid'] == node_id]
        
        if len(node_location) > 0:
            return (node_location['x'].values[0], node_location['y'].values[0])
        else:
            return (0, 0)
    
    def get_energy_data(self, node_id, start_time=None, end_time=None):
        """获取指定节点的能量数据（基于电压）
        
        参数:
            node_id: 节点ID
            start_time: 开始时间，格式为'YYYY-MM-DD HH:MM:SS'
            end_time: 结束时间，格式为'YYYY-MM-DD HH:MM:SS'
            
        返回:
            能量数据Series
        """
        node_data = self.get_node_data(node_id, start_time, end_time)
        
        # 使用电压作为能量指标
        energy_data = node_data[['timestamp', 'voltage']].copy()
        energy_data = energy_data.set_index('timestamp')
        
        return energy_data
    
    def get_traffic_data(self, node_ids, time_window='1H'):
        """估计网络流量数据（基于数据包数量）
        
        参数:
            node_ids: 节点ID列表
            time_window: 时间窗口，默认为1小时
            
        返回:
            流量数据DataFrame
        """
        if self.sensor_data is None:
            self.load_sensor_data()
        
        # 筛选指定节点的数据
        nodes_data = self.sensor_data[self.sensor_data['moteid'].isin(node_ids)].copy()
        
        # 按时间窗口统计数据包数量
        traffic_data = nodes_data.groupby(['moteid', pd.Grouper(key='timestamp', freq=time_window)]).size().reset_index(name='packet_count')
        
        return traffic_data
    
    def visualize_network_topology(self, threshold=0.5):
        """可视化网络拓扑
        
        参数:
            threshold: 链路质量阈值，只显示质量高于阈值的链路
        """
        if self.connectivity_data is None:
            self.load_connectivity_data()
        
        if self.locations_data is None:
            self.load_locations_data()
        
        # 筛选高质量链路
        high_quality_links = self.connectivity_data[self.connectivity_data['probability'] >= threshold]
        
        # 创建图形
        plt.figure(figsize=(12, 10))
        
        # 绘制节点
        for _, node in self.locations_data.iterrows():
            plt.scatter(node['x'], node['y'], c='blue', s=100)
            plt.text(node['x'] + 0.5, node['y'] + 0.5, f"Node {node['moteid']}")
        
        # 绘制链路
        for _, link in high_quality_links.iterrows():
            sender_loc = self.get_node_location(link['sender'])
            receiver_loc = self.get_node_location(link['receiver'])
            
            plt.plot([sender_loc[0], receiver_loc[0]], [sender_loc[1], receiver_loc[1]], 'k-', alpha=link['probability'])
        
        plt.title(f"Intel Lab网络拓扑 (链路质量 >= {threshold})")
        plt.xlabel("X坐标 (米)")
        plt.ylabel("Y坐标 (米)")
        plt.grid(True)
        plt.show()
    
    def visualize_sensor_data(self, node_id, feature='temperature', start_time=None, end_time=None):
        """可视化传感器数据
        
        参数:
            node_id: 节点ID
            feature: 特征名称，可选值为'temperature', 'humidity', 'light', 'voltage'
            start_time: 开始时间，格式为'YYYY-MM-DD HH:MM:SS'
            end_time: 结束时间，格式为'YYYY-MM-DD HH:MM:SS'
        """
        node_data = self.get_node_data(node_id, start_time, end_time)
        
        if len(node_data) == 0:
            print(f"节点{node_id}在指定时间范围内没有数据")
            return
        
        # 创建图形
        plt.figure(figsize=(12, 6))
        
        # 绘制数据
        plt.plot(node_data['timestamp'], node_data[feature], 'b-')
        
        # 设置标题和标签
        feature_labels = {
            'temperature': '温度 (°C)',
            'humidity': '湿度 (%)',
            'light': '光照 (Lux)',
            'voltage': '电压 (V)'
        }
        
        plt.title(f"节点{node_id}的{feature_labels.get(feature, feature)}数据")
        plt.xlabel("时间")
        plt.ylabel(feature_labels.get(feature, feature))
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    def prepare_data_for_eehfr(self, num_nodes=54, time_window='1H', features=['temperature', 'humidity', 'light', 'voltage']):
        """准备用于EEHFR协议的数据
        
        参数:
            num_nodes: 节点数量
            time_window: 时间窗口，默认为1小时
            features: 要包含的特征列表
            
        返回:
            用于EEHFR协议的数据字典
        """
        if self.sensor_data is None:
            self.load_sensor_data()
        
        if self.connectivity_data is None:
            self.load_connectivity_data()
        
        if self.locations_data is None:
            self.load_locations_data()
        
        # 选择前num_nodes个节点
        node_ids = self.locations_data['moteid'].unique()[:num_nodes]
        
        # 准备节点位置数据
        node_locations = {}
        for node_id in node_ids:
            node_locations[node_id] = self.get_node_location(node_id)
        
        # 准备链路质量数据
        link_quality = {}
        for sender_id in node_ids:
            for receiver_id in node_ids:
                if sender_id != receiver_id:
                    link_id = f"{sender_id}-{receiver_id}"
                    link_quality[link_id] = self.get_link_quality(sender_id, receiver_id)
        
        # 准备传感器数据
        sensor_data = {}
        for feature in features:
            sensor_data[feature] = {}
            for node_id in node_ids:
                node_feature_data = self.get_node_data(node_id)
                if len(node_feature_data) > 0:
                    # 按时间窗口重采样
                    resampled_data = node_feature_data.set_index('timestamp')[feature].resample(time_window).mean()
                    sensor_data[feature][node_id] = resampled_data
        
        # 准备流量数据
        traffic_data = self.get_traffic_data(node_ids, time_window)
        
        # 构建EEHFR数据字典
        eehfr_data = {
            'node_locations': node_locations,
            'link_quality': link_quality,
            'sensor_data': sensor_data,
            'traffic_data': traffic_data
        }
        
        return eehfr_data

# 示例用法
if __name__ == "__main__":
    # 创建数据加载器
    loader = IntelLabDataLoader()
    
    # 加载小样本数据进行测试
    sensor_data = loader.load_sensor_data(sample_size=10000)
    connectivity_data = loader.load_connectivity_data()
    locations_data = loader.load_locations_data()
    
    # 打印数据样本
    print("\n传感器数据样本:")
    print(sensor_data.head())
    
    print("\n连接拓扑数据样本:")
    print(connectivity_data.head())
    
    print("\n节点位置数据样本:")
    print(locations_data.head())
    
    # 可视化网络拓扑
    loader.visualize_network_topology(threshold=0.7)
    
    # 可视化节点1的温度数据
    loader.visualize_sensor_data(node_id=1, feature='temperature')
    
    # 准备EEHFR数据
    eehfr_data = loader.prepare_data_for_eehfr(num_nodes=20)
    print("\nEEHFR数据准备完成")

    # 测试增强版数据预处理
    try:
        enhanced_data = loader.preprocess_data_enhanced(sequence_length=24, prediction_horizon=6)
        print(f"\n增强版数据预处理完成:")
        print(f"  - 序列数量: {enhanced_data['sequences'].shape[0]}")
        print(f"  - 序列长度: {enhanced_data['sequence_length']}")
        print(f"  - 预测步长: {enhanced_data['prediction_horizon']}")
        print(f"  - 特征维度: {len(enhanced_data['feature_cols'])}")
    except Exception as e:
        print(f"增强版数据预处理测试失败: {e}")

# 增强版数据预处理方法（添加到IntelLabDataLoader类中）
def preprocess_data_enhanced(self, sequence_length=24, prediction_horizon=6):
    """增强版数据预处理和特征工程"""
    if self.sensor_data is None:
        raise ValueError("数据未加载，请先调用相关加载方法")

    print("🔧 开始增强版数据预处理...")

    # 1. 数据清洗和异常值处理
    self.sensor_data = self._clean_data_enhanced(self.sensor_data)

    # 2. 高级特征工程
    self.sensor_data = self._advanced_feature_engineering(self.sensor_data)

    # 3. 时空序列数据准备
    processed_data = self._prepare_spatiotemporal_data(
        self.sensor_data, sequence_length, prediction_horizon
    )

    print("✅ 增强版数据预处理完成")
    return processed_data

def _clean_data_enhanced(self, data):
    """增强版数据清洗"""
    print("  - 执行增强版数据清洗...")

    # 重命名列以保持一致性
    if 'moteid' in data.columns:
        data = data.rename(columns={'moteid': 'node_id'})

    # 移除明显的异常值和传感器故障
    sensor_cols = ['temperature', 'humidity', 'light', 'voltage']

    for col in sensor_cols:
        if col in data.columns:
            # 定义合理的传感器范围
            if col == 'temperature':
                valid_range = (-10, 60)  # 摄氏度
            elif col == 'humidity':
                valid_range = (0, 100)   # 百分比
            elif col == 'light':
                valid_range = (0, 10000) # Lux
            elif col == 'voltage':
                valid_range = (2.0, 3.5) # 电池电压

            # 标记超出合理范围的值
            mask = (data[col] < valid_range[0]) | (data[col] > valid_range[1])
            data.loc[mask, col] = np.nan

            # 使用滑动中位数填充异常值
            data[col] = data.groupby('node_id')[col].transform(
                lambda x: x.fillna(x.rolling(window=5, min_periods=1).median())
            )

    # 处理时间戳异常
    data = data.sort_values(['node_id', 'timestamp']).reset_index(drop=True)

    return data

def _advanced_feature_engineering(self, data):
    """高级特征工程"""
    print("  - 执行高级特征工程...")

    # 基础时间特征
    data['hour'] = data['timestamp'].dt.hour
    data['day_of_week'] = data['timestamp'].dt.dayofweek
    data['day_of_year'] = data['timestamp'].dt.dayofyear
    data['month'] = data['timestamp'].dt.month

    # 周期性编码
    data['hour_sin'] = np.sin(2 * np.pi * data['hour'] / 24)
    data['hour_cos'] = np.cos(2 * np.pi * data['hour'] / 24)
    data['day_sin'] = np.sin(2 * np.pi * data['day_of_week'] / 7)
    data['day_cos'] = np.cos(2 * np.pi * data['day_of_week'] / 7)
    data['month_sin'] = np.sin(2 * np.pi * data['month'] / 12)
    data['month_cos'] = np.cos(2 * np.pi * data['month'] / 12)

    # 传感器数据的统计特征
    sensor_cols = ['temperature', 'humidity', 'light', 'voltage']

    for col in sensor_cols:
        if col in data.columns:
            # 滑动窗口统计特征
            for window in [3, 6, 12]:
                data[f'{col}_ma_{window}'] = data.groupby('node_id')[col].rolling(
                    window, min_periods=1).mean().reset_index(0, drop=True)
                data[f'{col}_std_{window}'] = data.groupby('node_id')[col].rolling(
                    window, min_periods=1).std().reset_index(0, drop=True)

            # 差分特征（变化率）
            data[f'{col}_diff'] = data.groupby('node_id')[col].diff()
            data[f'{col}_diff_2'] = data.groupby('node_id')[f'{col}_diff'].diff()

            # 相对于网络平均值的偏差
            data[f'{col}_network_mean'] = data.groupby('timestamp')[col].transform('mean')
            data[f'{col}_deviation'] = data[col] - data[f'{col}_network_mean']

    # 能量相关特征
    if 'voltage' in data.columns:
        # 估算剩余能量比例
        data['energy_ratio'] = (data['voltage'] - 2.0) / (3.3 - 2.0)
        data['energy_ratio'] = data['energy_ratio'].clip(0, 1)

        # 能量消耗率
        data['energy_consumption_rate'] = -data.groupby('node_id')['voltage'].diff()

    # 空间特征（如果有位置信息）
    if self.locations_data is not None and 'node_id' in data.columns:
        data = data.merge(self.locations_data, on='node_id', how='left')

        if 'x' in data.columns and 'y' in data.columns:
            # 到网络中心的距离
            center_x, center_y = data['x'].mean(), data['y'].mean()
            data['distance_to_center'] = np.sqrt(
                (data['x'] - center_x)**2 + (data['y'] - center_y)**2
            )

            # 节点密度特征
            data['node_density'] = self._calculate_node_density(data)

    # 填充NaN值
    data = data.fillna(method='ffill').fillna(method='bfill')

    return data

def _calculate_node_density(self, data, radius=5.0):
    """计算节点密度特征"""
    densities = []
    unique_nodes = data[['node_id', 'x', 'y']].drop_duplicates()

    for _, node in unique_nodes.iterrows():
        # 计算在指定半径内的邻居节点数量
        distances = np.sqrt(
            (unique_nodes['x'] - node['x'])**2 +
            (unique_nodes['y'] - node['y'])**2
        )
        neighbors = (distances <= radius).sum() - 1  # 排除自己
        densities.append({'node_id': node['node_id'], 'node_density': neighbors})

    density_df = pd.DataFrame(densities)
    return data.merge(density_df, on='node_id', how='left')['node_density']

def _prepare_spatiotemporal_data(self, data, sequence_length, prediction_horizon):
    """准备时空序列数据"""
    print("  - 准备时空序列数据...")

    # 按节点和时间排序
    data = data.sort_values(['node_id', 'timestamp']).reset_index(drop=True)

    # 选择特征列
    feature_cols = [
        'temperature', 'humidity', 'light', 'voltage',
        'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos'
    ]

    # 添加能量特征
    if 'energy_ratio' in data.columns:
        feature_cols.append('energy_ratio')
    if 'energy_consumption_rate' in data.columns:
        feature_cols.append('energy_consumption_rate')

    # 添加滑动窗口特征
    for col in ['temperature', 'humidity', 'light', 'voltage']:
        if col in data.columns:
            for window in [3, 6, 12]:
                if f'{col}_ma_{window}' in data.columns:
                    feature_cols.append(f'{col}_ma_{window}')
                if f'{col}_std_{window}' in data.columns:
                    feature_cols.append(f'{col}_std_{window}')
            if f'{col}_diff' in data.columns:
                feature_cols.append(f'{col}_diff')

    # 添加空间特征
    if 'x' in data.columns:
        feature_cols.extend(['x', 'y'])
    if 'distance_to_center' in data.columns:
        feature_cols.append('distance_to_center')
    if 'node_density' in data.columns:
        feature_cols.append('node_density')

    # 确保所有特征列都存在
    feature_cols = [col for col in feature_cols if col in data.columns]
    target_cols = ['temperature', 'humidity', 'light', 'voltage']
    target_cols = [col for col in target_cols if col in data.columns]

    print(f"    选择的特征列数量: {len(feature_cols)}")
    print(f"    目标列数量: {len(target_cols)}")

    # 数据归一化
    features_scaled = self.scaler_features.fit_transform(data[feature_cols])
    targets_scaled = self.scaler_targets.fit_transform(data[target_cols])

    # 创建时空序列样本
    sequences = []
    targets = []
    node_ids = []
    timestamps = []

    for node_id in data['node_id'].unique():
        node_mask = data['node_id'] == node_id
        node_data = data[node_mask].reset_index(drop=True)
        node_features = features_scaled[node_mask]
        node_targets = targets_scaled[node_mask]

        for i in range(len(node_data) - sequence_length - prediction_horizon + 1):
            sequences.append(node_features[i:i + sequence_length])
            targets.append(node_targets[i + sequence_length:i + sequence_length + prediction_horizon])
            node_ids.append(node_id)
            timestamps.append(node_data.iloc[i + sequence_length]['timestamp'])

    print(f"    生成的序列数量: {len(sequences)}")

    return {
        'sequences': np.array(sequences),
        'targets': np.array(targets),
        'node_ids': np.array(node_ids),
        'timestamps': timestamps,
        'feature_cols': feature_cols,
        'target_cols': target_cols,
        'scaler_features': self.scaler_features,
        'scaler_targets': self.scaler_targets,
        'sequence_length': sequence_length,
        'prediction_horizon': prediction_horizon
    }

# 将这些方法添加到IntelLabDataLoader类中
IntelLabDataLoader.preprocess_data_enhanced = preprocess_data_enhanced
IntelLabDataLoader._clean_data_enhanced = _clean_data_enhanced
IntelLabDataLoader._advanced_feature_engineering = _advanced_feature_engineering
IntelLabDataLoader._calculate_node_density = _calculate_node_density
IntelLabDataLoader._prepare_spatiotemporal_data = _prepare_spatiotemporal_data