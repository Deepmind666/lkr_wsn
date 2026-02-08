# Enhanced Intel Lab鏁版嵁闆嗗姞杞芥ā鍧?- 鐢ㄤ簬AERIS鍗忚
# 鏀寔澶氱鏁版嵁婧愬拰澧炲己鐨勬暟鎹澶勭悊鍔熻兘

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
    """澧炲己鐗圛ntel Berkeley Research Lab鏁版嵁闆嗗姞杞ject櫒

    璇ユ暟鎹泦鍖呭惈54涓紶鎰熷櫒鍦?004骞?鏈?8鏃ヨ嚦4鏈?鏃ユ湡闂存敹闆嗙殑鏁版嵁锛?    鍖呮嫭娓╁害銆佹箍搴︺€佸厜鐓у拰鐢靛帇绛変俊鎭€?
    鏂板鍔熻兘锛?    - 澶氭簮鏁版嵁闆嗘敮鎸?    - 鏅鸿兘鏁版嵁娓呮礂
    - 鏁版嵁澧炲己绛栫暐
    - 鏃剁┖鐗rague緛宸ョ▼
    """

    def __init__(self, data_dir="../data", use_synthetic=False):
        """鍒濆鍖栨暟鎹姞杞ject櫒

        鍙傛暟:
            data_dir: 鏁版嵁瀛樺偍鐩綍
            use_synthetic: 鏄惁浣跨敤鍚堟垚鏁版嵁锛堝綋鐪熷疄鏁版嵁涓嶅彲鐢ㄦ椂锛?        """
        self.data_dir = data_dir
        self.use_synthetic = use_synthetic

        # 鐪熷疄Intel Lab鏁版嵁鏂囦欢璺緞
        self.data_file = os.path.join(data_dir, "data.txt.gz")
        self.locations_file = os.path.join(data_dir, "Intel_Lab_Data", "mote_locs.txt")
        self.connectivity_file = os.path.join(data_dir, "Intel_Lab_Data", "connectivity.txt")
        # 兼容下载函数的文件别名（拓扑文件与 connectivity 共用）
        self.topology_file = self.connectivity_file

        # 默认下载 URL（若本地缺失时使用）
        # 注：官方数据源为 MIT CSAIL Intel Lab 数据。个别镜像可能不可用，失败时保持回退到合成数据。
        self.data_url = "http://db.csail.mit.edu/labdata/data.txt.gz"
        self.locations_url = "http://db.csail.mit.edu/labdata/mote_locs.txt"
        # 无官方 connectivity 文本；通常由位置重建，保留可选占位
        self.topology_url = None

        # 鏁版嵁瀛樺偍
        self.sensor_data = None
        self.connectivity_data = None
        self.locations_data = None
        self.processed_data = None

        # 鏁版嵁棰勫鐞嗗弬鏁?        self.scaler_features = MinMaxScaler()
        self.scaler_targets = MinMaxScaler()
        self.imputer = KNNImputer(n_neighbors=5)
        
        # 初始化数据
        self._initialize_data()

        # 纭繚鏁版嵁鐩綍瀛樺湪
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # 鍒濆鍖栨暟鎹?        self._initialize_data()
    
    def _initialize_data(self):
        """鍒濆鍖栨暟鎹泦"""
        try:
            # 优先检查根目录的 data.txt.gz，不存在则检查 Intel_Lab_Data 子目录
            alt_data = os.path.join(self.data_dir, "Intel_Lab_Data", "data.txt.gz")
            if (not os.path.exists(self.data_file) or os.path.getsize(self.data_file) <= 1000) and os.path.exists(alt_data) and os.path.getsize(alt_data) > 1000:
                self.data_file = alt_data
            # 灏濊瘯鍔犺浇鐪熷疄鏁版嵁
            if os.path.exists(self.data_file) and os.path.getsize(self.data_file) > 1000:
                self.load_real_data()
                print("[OK] Successfully loaded real Intel Lab dataset")
            else:
                # 尝试下载官方数据
                try:
                    self.download_dataset()
                except Exception as _e:
                    print(f"[WARN] Download attempt failed: {_e}")
                if os.path.exists(self.data_file) and os.path.getsize(self.data_file) > 1000:
                    self.load_real_data()
                    print("[OK] Successfully downloaded and loaded real Intel Lab dataset")
                    return
                if self.use_synthetic:
                    self.generate_synthetic_data()
                    print("[WARN] Real dataset unavailable; generated synthetic dataset")
                else:
                    raise FileNotFoundError("Real dataset file not found and synthetic mode is disabled")
        except Exception as e:
            print(f"[ERROR] Data initialization failed: {e}")
            if self.use_synthetic:
                self.generate_synthetic_data()
                print("[INFO] Switched to synthetic dataset mode")

    def load_real_data(self):
        """Load the real Intel Lab dataset"""
        print("[INFO] Loading real Intel Lab dataset...")

        # Load sensor readings from gzip file
        try:
            with gzip.open(self.data_file, 'rt') as f:
                lines = f.readlines()

            sensor_data = []
            for line_num, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) >= 8:
                    try:
                        date_str = parts[0]
                        time_str = parts[1]
                        epoch = int(parts[2])
                        node_id = int(parts[3])
                        temperature = float(parts[4]) if parts[4] != '-' else np.nan
                        humidity = float(parts[5]) if parts[5] != '-' else np.nan
                        light = float(parts[6]) if parts[6] != '-' else np.nan
                        voltage = float(parts[7]) if parts[7] != '-' else np.nan
    
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
                    except (ValueError, IndexError):
                        if line_num < 10:
                            print(f"  Warning: Parse failed at line {line_num+1}: {line.strip()[:50]}...")
                        continue
    
            self.sensor_data = pd.DataFrame(sensor_data)
            # 统一列命名：部分函数使用 moteid
            if 'node_id' in self.sensor_data.columns:
                # 保持 node_id 主列，同时提供兼容列
                self.sensor_data['moteid'] = self.sensor_data['node_id']
            print(f"[OK] Sensor data loaded: {len(self.sensor_data)} rows")
        except Exception as e:
            print(f"[ERROR] Failed to load sensor data: {e}")
            raise

        # Load locations data
        try:
            locations = []
            if os.path.exists(self.locations_file):
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
                # 统一列命名
                if 'node_id' in self.locations_data.columns:
                    self.locations_data['moteid'] = self.locations_data['node_id']
                print(f"[OK] Locations loaded: {len(self.locations_data)} nodes")
            else:
                print("[WARN] Locations file not found; generating default grid locations")
                self._generate_default_locations()
        except Exception as e:
            print(f"[ERROR] Failed to load locations: {e}")
            self._generate_default_locations()

        # Load connectivity data
        try:
            if os.path.exists(self.connectivity_file):
                self.connectivity_data = self.load_connectivity_data()
                if self.connectivity_data is None or self.connectivity_data.empty:
                    raise ValueError("Connectivity data is empty or failed to read")
                print(f"[OK] Connectivity loaded: {len(self.connectivity_data)} links")
            else:
                print("[WARN] Connectivity file not found; building from locations and saving")
                self.build_and_save_connectivity_from_locations(comm_range=5.0)
        except Exception as e:
            print(f"[ERROR] Failed to load connectivity: {e}")
            try:
                self.build_and_save_connectivity_from_locations(comm_range=5.0)
            except Exception as _e:
                print(f"[WARN] Building connectivity from locations failed; generating in-memory fallback: {_e}")
                self._generate_connectivity_data()

        # Merge locations into sensor data if available
        if self.locations_data is not None and not self.locations_data.empty:
            # 统一列名后合并位置到传感数据
            loc_df = self.locations_data.copy()
            if 'node_id' not in loc_df.columns and 'moteid' in loc_df.columns:
                loc_df = loc_df.rename(columns={'moteid': 'node_id'})
            sens_df = self.sensor_data.copy()
            if 'node_id' not in sens_df.columns and 'moteid' in sens_df.columns:
                sens_df = sens_df.rename(columns={'moteid': 'node_id'})
            self.sensor_data = sens_df.merge(
                loc_df[['node_id', 'x', 'y']],
                on='node_id',
                how='left'
            )

        print("[INFO] Dataset summary")
        print(f"   - Num nodes: {self.sensor_data['node_id'].nunique()}")
        print(f"   - Time range: {self.sensor_data['timestamp'].min()} to {self.sensor_data['timestamp'].max()}")
        print(f"   - Columns: {list(self.sensor_data.columns)}")

    def _generate_default_locations(self):
        """Generate default node locations"""
        unique_nodes = self.sensor_data['node_id'].unique()
        locations = []

        # 绠€鍗栠殑缃戞牸甯冨眬
        cols = int(np.ceil(np.sqrt(len(unique_nodes))))
        for i, node_id in enumerate(sorted(unique_nodes)):
            x = (i % cols) * 5.0
            y = (i // cols) * 5.0
            locations.append({'node_id': node_id, 'x': x, 'y': y})

        self.locations_data = pd.DataFrame(locations)

    def generate_synthetic_data(self):
        """Generate high-quality synthetic WSN dataset"""
        print("[INFO] Generating synthetic Intel Lab dataset...")

        # Network parameters
        n_nodes = 54
        n_days = 36
        samples_per_hour = 12  # 5-minute sampling
        total_samples = n_days * 24 * samples_per_hour

        # Generate timestamps
        start_time = datetime(2004, 2, 28, 0, 0, 0)
        timestamps = [start_time + timedelta(minutes=5 * i) for i in range(total_samples)]

        # Generate node locations (based on Intel Lab layout)
        np.random.seed(42)
        locations = self._generate_node_locations(n_nodes)

        # Initialize synthetic sensor data container
        sensor_data = []
        for i, timestamp in enumerate(timestamps):
            for node_id in range(1, n_nodes + 1):
                temp, humidity, light, voltage = self._generate_sensor_reading(
                    node_id, timestamp, locations[node_id - 1], i
                )

                sensor_data.append({
                    'timestamp': timestamp,
                    'node_id': node_id,
                    'temperature': temp,
                    'humidity': humidity,
                    'light': light,
                    'voltage': voltage,
                    'x': locations[node_id - 1][0],
                    'y': locations[node_id - 1][1]
                })

        # Convert to DataFrame
        self.sensor_data = pd.DataFrame(sensor_data)
        self.locations_data = pd.DataFrame([
            {'node_id': idx + 1, 'x': loc[0], 'y': loc[1]} for idx, loc in enumerate(locations)
        ])

        # Build connectivity
        self._generate_connectivity_data()

        print(f"[OK] Synthetic dataset generated: {len(self.sensor_data)} rows")

    def _generate_node_locations(self, n_nodes):
        """Generate node locations"""
        locations = []
        rows, cols = 6, 9
        for i in range(n_nodes):
            row = i // cols
            col = i % cols

            # Base grid layout with small noise
            x = col * 3.5 + np.random.normal(0, 0.5)
            y = row * 3.8 + np.random.normal(0, 0.5)

            # Clamp within lab bounds (approx. 31m x 23m)
            x = max(0, min(31, x))
            y = max(0, min(23, y))

            locations.append([x, y])

        return locations

    def _generate_sensor_reading(self, node_id, timestamp, location, sample_idx):
        """Generate a realistic synthetic sensor reading for a node"""
        hour = timestamp.hour
        day_of_year = timestamp.timetuple().tm_yday

        # Temperature model: diurnal + seasonal + spatial + noise
        base_temp = 20 + 5 * np.sin(2 * np.pi * hour / 24)
        seasonal_temp = 3 * np.sin(2 * np.pi * day_of_year / 365)
        spatial_temp = (location[0] + location[1]) * 0.1
        noise_temp = np.random.normal(0, 1)
        temperature = base_temp + seasonal_temp + spatial_temp + noise_temp

        # Humidity inversely correlated with temperature + noise
        base_humidity = 50 - 0.5 * (temperature - 20)
        humidity_noise = np.random.normal(0, 5)
        humidity = float(np.clip(base_humidity + humidity_noise, 0, 100))

        # Light model: daytime vs. nighttime + noise
        if 6 <= hour <= 18:
            base_light = 500 + 300 * np.sin(np.pi * (hour - 6) / 12)
        else:
            base_light = 50
        light_noise = np.random.normal(0, 50)
        light = max(0.0, base_light + light_noise)

        # Voltage model: slow decay over time + noise
        base_voltage = 3.0 - 0.0001 * sample_idx
        voltage_noise = np.random.normal(0, 0.05)
        voltage = max(2.0, base_voltage + voltage_noise)

        return float(temperature), float(humidity), float(light), float(voltage)

    def _generate_connectivity_data(self):
        """Generate connectivity data"""
        connectivity = []
        locations = self.locations_data[['x', 'y']].values

        # 鍩轰簬璺濈鐨勮繛鎺ユ€э紙閫氫俊鑼冨洿绾?绫籌級
        comm_range = 5.0

        for i in range(len(locations)):
            for j in range(i + 1, len(locations)):
                distance = np.sqrt(np.sum((locations[i] - locations[j])**2))
                if distance <= comm_range:
                    # 娣诲姞涓€浜涢殢鏈烘€э紙淇″彿琛板噺銆侀殰纰嶇墿绛夛級
                    connection_prob = max(0, 1 - distance / comm_range)
                    if np.random.random() < connection_prob:
                        connectivity.append({
                            'node1': i + 1,
                            'node2': j + 1,
                            'distance': distance,
                            'link_quality': connection_prob
                        })

        self.connectivity_data = pd.DataFrame(connectivity)
        print(f"[OK] Generated {len(connectivity)} connectivity records")

    def build_and_save_connectivity_from_locations(self, comm_range: float = 5.0, bidirectional: bool = True):
        """
        鍩轰簬宸插姞杞界殑鑺傜偣浣嶇疆淇℃伅(mote_locs.txt)鏋勫缓杩炴帴鎷撴墤锛屽苟鎸佷箙鍖栦繚瀛樹负涓夊垪琛?sender receiver probability)銆?        淇濆瓨璺緞: self.connectivity_file (data/Intel_Lab_Data/connectivity.txt)
        """
        # 纭繚鏈変綅缃暟鎹?
        if self.locations_data is None or self.locations_data.empty:
            # 灏濊瘯浠巗ensor_data涓幏鍙栧潗鏍囨垨鐢熸垚榛樿浣嶇疆
            if self.sensor_data is not None and {'x', 'y'}.issubset(self.sensor_data.columns):
                tmp = self.sensor_data.copy()
                if 'node_id' not in tmp.columns and 'moteid' in tmp.columns:
                    tmp = tmp.rename(columns={'moteid': 'node_id'})
                self.locations_data = tmp[['node_id', 'x', 'y']].drop_duplicates('node_id')
            else:
                self._generate_default_locations()
        # 缁熶竴鍒楀悕
        if 'node_id' not in self.locations_data.columns and 'moteid' in self.locations_data.columns:
            self.locations_data = self.locations_data.rename(columns={'moteid': 'node_id'})

        # 浣跨敤鐪熷疄鑺傜偣ID
        nodes = self.locations_data[['node_id', 'x', 'y']].sort_values('node_id').to_numpy()
        rows = []
        for a in range(len(nodes)):
            id_a, xa, ya = int(nodes[a][0]), float(nodes[a][1]), float(nodes[a][2])
            for b in range(a + 1, len(nodes)):
                id_b, xb, yb = int(nodes[b][0]), float(nodes[b][1]), float(nodes[b][2])
                d = float(np.hypot(xa - xb, ya - yb))
                if d <= comm_range:
                    p = max(0.0, 1.0 - d / comm_range)
                    rows.append((id_a, id_b, p))
                    if bidirectional:
                        rows.append((id_b, id_a, p))
        df = pd.DataFrame(rows, columns=['sender', 'receiver', 'probability'])
        # 纭繚鐩綍瀛樺湪骞跺啓鐩?
        os.makedirs(os.path.dirname(self.connectivity_file), exist_ok=True)
        with open(self.connectivity_file, 'w', encoding='utf-8') as f:
            for s, r, p in df.itertuples(index=False):
                f.write(f"{int(s)} {int(r)} {float(p):.6f}\n")
        self.connectivity_data = df
        print(f"[OK] Built and saved connectivity: {len(df)} rows -> {self.connectivity_file}")

    def download_dataset(self):
        """Download Intel Lab dataset"""
        print("[INFO] Downloading Intel Lab dataset...")
        
        # 涓嬭浇浼犳劅鍣ㄦ暟鎹?
        if not os.path.exists(self.data_file):
            print(f"[INFO] Downloading sensor data: {self.data_url}")
            try:
                response = requests.get(self.data_url, stream=True, timeout=30)
                with open(self.data_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print("[OK] Sensor data downloaded")
            except Exception as e:
                print(f"[ERROR] Failed to download sensor data: {e}")
        else:
            print("[INFO] Sensor data already exists; skipping download")
        
        # 涓嬭浇杩炴帴鎷撴墤鏁版嵁
        # 拓扑/连通性：若无 URL 或已存在则跳过；通常由位置重建
        if not os.path.exists(self.topology_file) and self.topology_url:
            print(f"[INFO] Downloading connectivity topology data: {self.topology_url}")
            try:
                response = requests.get(self.topology_url, stream=True, timeout=30)
                with open(self.topology_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print("[OK] Connectivity topology data downloaded")
            except Exception as e:
                print(f"[ERROR] Failed to download connectivity topology data: {e}")
        else:
            if os.path.exists(self.topology_file):
                print("[INFO] Connectivity topology data already exists; skipping download")
        
        # 涓嬭浇鑺傜偣浣嶇疆鏁版嵁
        if not os.path.exists(self.locations_file):
            print(f"[INFO] Downloading node location data: {self.locations_url}")
            try:
                response = requests.get(self.locations_url, timeout=30)
                with open(self.locations_file, 'w') as f:
                    f.write(response.text)
                print("[OK] Node location data downloaded")
            except Exception as e:
                print(f"[ERROR] Failed to download node location data: {e}")
        else:
            print("[INFO] Node location data already exists; skipping download")
    
    def load_sensor_data(self, sample_size=None):
        """Load sensor data"""
        print("[INFO] Loading sensor data...")
        start_time = time.time()
        
        # 瀹氫箟鍒楀悕
        columns = ['date', 'time', 'epoch', 'moteid', 'temperature', 'humidity', 'light', 'voltage']
        
        try:
            # 鐩存帴鎵撳紑鏂囨湰鏂囦欢
            if sample_size is not None:
                lines = []
                with open(self.data_file, 'rt') as f:
                    for i, line in enumerate(f):
                        if i >= sample_size:
                            break
                        lines.append(line.strip())
                
                # 瑙ｆ瀽鏁版嵁
                data = [line.split() for line in lines]
                self.sensor_data = pd.DataFrame(data, columns=columns)
            else:
                # 璇诲彇鍏ㄩ儴鏁版嵁
                self.sensor_data = pd.read_csv(self.data_file, sep=' ', names=columns)
            
            # 杞崲鏁版嵁绫诲瀷
            self.sensor_data['epoch'] = self.sensor_data['epoch'].astype(int)
            self.sensor_data['moteid'] = self.sensor_data['moteid'].astype(int)
            self.sensor_data['temperature'] = self.sensor_data['temperature'].astype(float)
            self.sensor_data['humidity'] = self.sensor_data['humidity'].astype(float)
            self.sensor_data['light'] = self.sensor_data['light'].astype(float)
            self.sensor_data['voltage'] = self.sensor_data['voltage'].astype(float)
            
            # 鍚堝苟鏃ユ湡鍜屾椂闂村垪
            self.sensor_data['timestamp'] = pd.to_datetime(self.sensor_data['date'] + ' ' + self.sensor_data['time'])
            
            # 鍒犻櫎鍘熷鏃ユ湡鍜屾椂闂村垪
            self.sensor_data = self.sensor_data.drop(['date', 'time'], axis=1)
            
            print(f"[OK] Sensor data loaded: {len(self.sensor_data)} rows, elapsed {time.time() - start_time:.2f}s")
            return self.sensor_data
            
        except Exception as e:
            print(f"[ERROR] Failed to load sensor data: {e}")
            return None
    
    def load_connectivity_data(self):
        """Load connectivity data"""
        print("[INFO] Loading connectivity data...")
        
        try:
            # 鐩存帴鎵撳紑鏂囨湰鏂囦欢
            self.connectivity_data = pd.read_csv(self.connectivity_file, sep=' ', names=['sender', 'receiver', 'probability'])
            
            # nits崲鏁版嵁绫诲瀷
            self.connectivity_data['sender'] = self.connectivity_data['sender'].astype(int)
            self.connectivity_data['receiver'] = self.connectivity_data['receiver'].astype(int)
            self.connectivity_data['probability'] = self.connectivity_data['probability'].astype(float)
            
            print(f"[OK] Connectivity data loaded: {len(self.connectivity_data)} rows")
            return self.connectivity_data
            
        except Exception as e:
            print(f"[ERROR] Failed to load connectivity data: {e}")
            return None
    
    def load_locations_data(self):
        """Load locations data"""
        print("[INFO] Loading node location data...")
        
        try:
            # 璇诲彇鏁版嵁
            self.locations_data = pd.read_csv(self.locations_file, sep=' ', names=['moteid', 'x', 'y'])
            
            # nits崲鏁版嵁绫诲瀷
            self.locations_data['moteid'] = self.locations_data['moteid'].astype(int)
            self.locations_data['x'] = self.locations_data['x'].astype(float)
            self.locations_data['y'] = self.locations_data['y'].astype(float)
            
            print(f"[OK] Node location data loaded: {len(self.locations_data)} rows")
            return self.locations_data
            
        except Exception as e:
            print(f"[ERROR] Failed to load node location data: {e}")
            return None
    
    def get_node_data(self, node_id, start_time=None, end_time=None):
        """Get node data"""
        if self.sensor_data is None:
            self.load_sensor_data()
        
        # 绛涢€夋寚瀹氳妭鐐圭殑鏁版嵁
        node_data = self.sensor_data[self.sensor_data['moteid'] == node_id].copy()
        
        # 绛涢€夋椂闂磋寖鍥?
        if start_time is not None:
            start_dt = pd.to_datetime(start_time)
            node_data = node_data[node_data['timestamp'] >= start_dt]
        
        if end_time is not None:
            end_dt = pd.to_datetime(end_time)
            node_data = node_data[node_data['timestamp'] <= end_dt]
        
        return node_data
    
    def get_link_quality(self, sender_id, receiver_id):
        """Get link quality"""
        if self.connectivity_data is None:
            self.load_connectivity_data()
        
        # 绛涢€夋寚瀹氶摼璺殑鏁版嵁
        link_data = self.connectivity_data[
            (self.connectivity_data['sender'] == sender_id) &
            (self.connectivity_data['receiver'] == receiver_id)
        ]
        
        if len(link_data) > 0:
            return link_data['probability'].values[0]
        else:
            return 0.0
    
    def get_node_location(self, node_id):
        """Get node location"""
        if self.locations_data is None:
            self.load_locations_data()
        
        # 绛涢€夋寚瀹氳妭鐐圭殑鏁版嵁
        node_location = self.locations_data[self.locations_data['moteid'] == node_id]
        
        if len(node_location) > 0:
            return (node_location['x'].values[0], node_location['y'].values[0])
        else:
            return (0, 0)
    
    def get_energy_data(self, node_id, start_time=None, end_time=None):
        """Get energy data"""
        node_data = self.get_node_data(node_id, start_time, end_time)
        
        # 浣跨敤鐢靛帇浣滀负鑳介噺鎸囨爣
        energy_data = node_data[['timestamp', 'voltage']].copy()
        energy_data = energy_data.set_index('timestamp')
        
        return energy_data
    
    def get_traffic_data(self, node_ids, time_window='1H'):
        """Get traffic data"""
        if self.sensor_data is None:
            self.load_sensor_data()
        
        # 绛涢€夋寚瀹氳妭鐐圭殑鏁版嵁
        nodes_data = self.sensor_data[self.sensor_data['moteid'].isin(node_ids)].copy()
        
        # 鎸夋椂闂寸獥鍙ｉ噸閲囨牱
        traffic_data = nodes_data.groupby(['moteid', pd.Grouper(key='timestamp', freq=time_window)]).size().reset_index(name='packet_count')
        
        return traffic_data
    
    def visualize_network_topology(self, threshold=0.5):
        """Visualize network topology"""
        if self.connectivity_data is None:
            self.load_connectivity_data()
        
        if self.locations_data is None:
            self.load_locations_data()
        
        # 绛涢€夐珮璐ㄩ噺閾捐矾
        high_quality_links = self.connectivity_data[self.connectivity_data['probability'] >= threshold]
        
        # 鍒涘缓鍥惧舰
        plt.figure(figsize=(12, 10))
        
        # 缁樺埗鑺傜偣
        for _, node in self.locations_data.iterrows():
            plt.scatter(node['x'], node['y'], c='blue', s=100)
            plt.text(node['x'] + 0.5, node['y'] + 0.5, f"Node {node['moteid']}")
        
        # 缁樺埗閾捐矾
        for _, link in high_quality_links.iterrows():
            sender_loc = self.get_node_location(link['sender'])
            receiver_loc = self.get_node_location(link['receiver'])
            
            plt.plot([sender_loc[0], receiver_loc[0]], [sender_loc[1], receiver_loc[1]], 'k-', alpha=link['probability'])
        
        plt.title(f"Intel Lab Network Topology (link quality >= {threshold})")
        plt.xlabel("X coordinate (m)")
        plt.ylabel("Y coordinate (m)")
        plt.grid(True)
        plt.show()
    
    def visualize_sensor_data(self, node_id, feature='temperature', start_time=None, end_time=None):
        """Visualize sensor data"""
        node_data = self.get_node_data(node_id, start_time, end_time)
        
        if len(node_data) == 0:
            print(f"Node {node_id} has no data in the specified time range")
            return
        
        # 鍒涘缓鍥惧舰
        plt.figure(figsize=(12, 6))
        
        # 缁樺埗鏁版嵁
        plt.plot(node_data['timestamp'], node_data[feature], 'b-')
        
        # 璁剧疆鏍囬鍜屾粈绛?
        feature_labels = {
            'temperature': 'Temperature (C)',
            'humidity': 'Humidity (%)',
            'light': 'Light (Lux)',
            'voltage': 'Voltage (V)'
        }
        
        plt.title(f"Node {node_id} {feature_labels.get(feature, feature)}")
        plt.xlabel("Time")
        plt.ylabel(feature_labels.get(feature, feature))
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    def prepare_data_for_aeris(self, num_nodes=54, time_window='1H', features=['temperature', 'humidity', 'light', 'voltage']):
        """Prepare data for AERIS (统一命名，替代旧EEHFR接口)"""
        if self.sensor_data is None:
            self.load_sensor_data()
        
        if self.connectivity_data is None:
            self.load_connectivity_data()
        
        if self.locations_data is None:
            self.load_locations_data()
        
        # 閫夋嫨鍓峮um_nodes涓妭鐐?        node_ids = self.locations_data['moteid'].unique()[:num_nodes]
        
        # 鍑嗗鑺傜偣浣嶇疆鏁版嵁
        node_locations = {}
        for node_id in node_ids:
            node_locations[node_id] = self.get_node_location(node_id)
        
        # 鍑嗗閾捐矾璐ㄩ噺鏁版嵁
        link_quality = {}
        for sender_id in node_ids:
            for receiver_id in node_ids:
                if sender_id != receiver_id:
                    link_id = f"{sender_id}-{receiver_id}"
                    link_quality[link_id] = self.get_link_quality(sender_id, receiver_id)
        
        # 鍑嗗浼犳劅鍣ㄦ暟鎹?        sensor_data = {}
        for feature in features:
            sensor_data[feature] = {}
            for node_id in node_ids:
                node_feature_data = self.get_node_data(node_id)
                if len(node_feature_data) > 0:
                    # 鎸夋椂闂寸獥鍙ｉ噸閲囨牱
                    resampled_data = node_feature_data.set_index('timestamp')[feature].resample(time_window).mean()
                    sensor_data[feature][node_id] = resampled_data
        
        # 鍑嗗娴侀噺鏁版嵁
        traffic_data = self.get_traffic_data(node_ids, time_window)
        
        # 构建 AERIS 数据字典
        aeris_data = {
            'node_locations': node_locations,
            'link_quality': link_quality,
            'sensor_data': sensor_data,
            'traffic_data': traffic_data
        }
        
        return aeris_data

    # 兼容旧名：保留别名以避免外部代码立刻失效（已弃用）
    def prepare_data_for_eehfr(self, num_nodes=54, time_window='1H', features=['temperature', 'humidity', 'light', 'voltage']):
        """Deprecated: 请使用 prepare_data_for_aeris"""
        return self.prepare_data_for_aeris(num_nodes=num_nodes, time_window=time_window, features=features)

# 绀轰緥鐢ㄦ硶
if __name__ == "__main__":
    # 鍒涘缓鏁版嵁鍔犺浇鍣?    loader = IntelLabDataLoader()
    
    # 鍔犺浇灏忔牱鏈暟鎹繘琛屾祴璇?    sensor_data = loader.load_sensor_data(sample_size=10000)
    connectivity_data = loader.load_connectivity_data()
    locations_data = loader.load_locations_data()
    
    # 鎵撳嵃鏁版嵁鍍锋湰
    print("\nSensor data head:")
    print(sensor_data.head())
    
    print("\nConnectivity data head:")
    print(connectivity_data.head())
    
    print("\nNode location data head:")
    print(locations_data.head())
    
    # 鍙鍖栫綉缁滄嫇鎵?    loader.visualize_network_topology(threshold=0.7)
    
    # 鍙鍖栬妭鐐?鐨勬俯搴︽暟鎹?    loader.visualize_sensor_data(node_id=1, feature='temperature')
    
    # 准备 AERIS 数据
    aeris_data = loader.prepare_data_for_aeris(num_nodes=20)
    print("\nAERIS data preparation completed")

    # 娴嬭瘯澧炲己鐗堟暟鎹澶勭悊
    try:
        enhanced_data = loader.preprocess_data_enhanced(sequence_length=24, prediction_horizon=6)
        print(f"\nEnhanced data preprocessing completed:")
        print(f"  - Num sequences: {enhanced_data['sequences'].shape[0]}")
        print(f"  - Sequence length: {enhanced_data['sequence_length']}")
        print(f"  - Prediction horizon: {enhanced_data['prediction_horizon']}")
        print(f"  - Num features: {len(enhanced_data['feature_cols'])}")
    except Exception as e:
        print(f"Enhanced preprocessing test failed: {e}")

# 澧炲己鐗堟暟鎹澶勭悊鏂规硶锛堟坊鍔犲埌IntelLabDataLoader绫queeffigs.txt

# Restore method bindings to class (disabled to avoid NameError if helper functions are absent)
# IntelLabDataLoader.preprocess_data_enhanced = preprocess_data_enhanced
# IntelLabDataLoader._clean_data_enhanced = _clean_data_enhanced
# IntelLabDataLoader._advanced_feature_engineering = _advanced_feature_engineering
# IntelLabDataLoader._calculate_node_density = _calculate_node_density
# IntelLabDataLoader._prepare_spatiotemporal_data = _prepare_spatiotemporal_data
