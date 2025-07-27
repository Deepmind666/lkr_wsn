# 基于LSTM的深度学习预测模块 - 用于EEHFR协议
# 参考文献：
# [8] Alsheikh, M. A., Lin, S., Niyato, D., & Tan, H. P. (2014). Machine learning in wireless sensor networks: Algorithms, strategies, and applications.
# [9] Raza, U., Kulkarni, P., & Sooriyabandara, M. (2017). Low power wide area networks: An overview.
# [10] Fadel, E., Gungor, V. C., Nassef, L., Akkari, N., Malik, M. A., Almasri, S., & Akyildiz, I. F. (2015). A survey on wireless sensor networks for smart grid.
# [11] Luo, C., Wu, F., Sun, J., & Chen, C. W. (2015). Compressive data gathering for large-scale wireless sensor networks.
# [12] Wang, J., Chen, Y., Hao, S., Peng, X., & Hu, L. (2019). Deep learning for sensor-based activity recognition: A survey.
# [13] Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. Neural computation, 9(8), 1735-1780.
# [14] Mao, B., Kawamoto, Y., & Kato, N. (2020). AI-Based Joint Optimization of QoS and Security for 6G Energy Harvesting Internet of Things.
# [15] Qiu, T., Chen, N., Li, K., Atiquzzaman, M., & Zhao, W. (2018). How can heterogeneous Internet of Things build our future: A survey.

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

class LSTMPrediction:
    """基于LSTM的深度学习预测模块，用于WSN中的网络流量、节点故障和链路质量预测
    
    参考文献：
    [12] Wang, J., Chen, Y., Hao, S., Peng, X., & Hu, L. (2019). Deep learning in sensor-based activity recognition: A survey.
    [13] Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. Neural computation, 9(8), 1735-1780.
    [14] Mao, B., Kawamoto, Y., & Kato, N. (2020). AI-Based Joint Optimization of QoS and Security for 6G Energy Harvesting Internet of Things.
    """
    
    def __init__(self, sequence_length=10, prediction_horizon=5, multi_feature=False):
        """初始化LSTM预测模型
        
        参数:
            sequence_length: 用于预测的历史数据长度
            prediction_horizon: 预测的未来时间步长度
            multi_feature: 是否使用多特征输入（默认为False，仅使用单特征）
        """
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        self.multi_feature = multi_feature
        
        # 预测模型
        self.traffic_model = None
        self.energy_model = None
        self.link_quality_model = None
        
        # 数据标准化器
        self.traffic_scaler = MinMaxScaler(feature_range=(0, 1))
        self.energy_scaler = MinMaxScaler(feature_range=(0, 1))
        self.link_quality_scaler = MinMaxScaler(feature_range=(0, 1))
        
        # 模型训练状态
        self.is_trained_traffic = False
        self.is_trained_energy = False
        self.is_trained_link_quality = False
        
        # 模型版本和更新时间
        self.model_version = 1.0
        self.last_update = None
        
    def build_model(self, input_shape, output_dim=1):
        """构建LSTM模型
        
        参数:
            input_shape: 输入数据形状 (sequence_length, features)
            output_dim: 输出维度
            
        返回:
            构建好的LSTM模型
        """
        model = Sequential()
        
        # 第一层LSTM，返回序列
        model.add(LSTM(64, return_sequences=True, input_shape=input_shape))
        model.add(Dropout(0.2))
        
        # 第二层LSTM，不返回序列
        model.add(LSTM(32, return_sequences=False))
        model.add(Dropout(0.2))
        
        # 输出层
        model.add(Dense(output_dim))
        
        # 编译模型
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        return model
    
    def prepare_data(self, data, is_traffic=True, is_link_quality=False):
        """准备LSTM模型的单变量训练数据
        
        参数:
            data: 原始时间序列数据
            is_traffic: 是否为流量数据
            is_link_quality: 是否为链路质量数据
            
        返回:
            X: 输入序列
            y: 目标值
        """
        # 选择合适的标准化器
        if is_traffic:
            scaler = self.traffic_scaler
        elif is_link_quality:
            scaler = self.link_quality_scaler
        else:
            scaler = self.energy_scaler
            
        scaled_data = scaler.fit_transform(data.reshape(-1, 1))
        
        X, y = [], []
        
        # 创建输入序列和目标值
        for i in range(len(scaled_data) - self.sequence_length - self.prediction_horizon + 1):
            X.append(scaled_data[i:(i + self.sequence_length), 0])
            y.append(scaled_data[i + self.sequence_length:(i + self.sequence_length + self.prediction_horizon), 0])
        
        # 转换为numpy数组
        X = np.array(X)
        y = np.array(y)
        
        # 重塑为LSTM输入格式 [samples, time steps, features]
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        
        return X, y
        
    def prepare_multivariate_data(self, data_dict, target_type='traffic'):
        """准备LSTM模型的多变量训练数据
        
        参数:
            data_dict: 包含多个特征的字典，格式为 {feature_name: feature_data}
            target_type: 目标变量类型，可选值为 'traffic', 'energy', 'link_quality'
            
        返回:
            X: 输入序列
            y: 目标值
        """
        # 确定目标变量和对应的标准化器
        if target_type == 'traffic':
            target_key = next((k for k in data_dict.keys() if 'traffic' in k.lower()), list(data_dict.keys())[0])
            target_scaler = self.traffic_scaler
        elif target_type == 'link_quality':
            target_key = next((k for k in data_dict.keys() if 'link' in k.lower() or 'quality' in k.lower()), list(data_dict.keys())[0])
            target_scaler = self.link_quality_scaler
        else:  # energy
            target_key = next((k for k in data_dict.keys() if 'energy' in k.lower()), list(data_dict.keys())[0])
            target_scaler = self.energy_scaler
        
        # 提取目标变量
        target_data = data_dict[target_key]
        
        # 标准化目标变量
        scaled_target = target_scaler.fit_transform(target_data.reshape(-1, 1))
        
        # 标准化所有特征
        scaled_features = {}
        feature_scalers = {}
        
        for feature_name, feature_data in data_dict.items():
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_features[feature_name] = scaler.fit_transform(feature_data.reshape(-1, 1))
            feature_scalers[feature_name] = scaler
        
        # 创建多变量输入序列和目标值
        X, y = [], []
        
        for i in range(len(scaled_target) - self.sequence_length - self.prediction_horizon + 1):
            # 收集所有特征的序列
            features_sequence = []
            for feature_name in data_dict.keys():
                features_sequence.append(scaled_features[feature_name][i:(i + self.sequence_length), 0])
            
            # 将所有特征堆叠为一个多变量序列
            X.append(np.column_stack(features_sequence))
            
            # 目标值仍然是单变量
            y.append(scaled_target[i + self.sequence_length:(i + self.sequence_length + self.prediction_horizon), 0])
        
        # 转换为numpy数组
        X = np.array(X)
        y = np.array(y)
        
        return X, y, target_scaler, feature_scalers
    
    def train_traffic_model(self, traffic_data, epochs=50, batch_size=32, validation_split=0.2, multi_features=None):
        """训练网络流量预测模型
        
        参数:
            traffic_data: 网络流量历史数据
            epochs: 训练轮数
            batch_size: 批次大小
            validation_split: 验证集比例
            multi_features: 多特征输入字典，格式为 {feature_name: feature_data}
            
        返回:
            训练历史
        """
        print("\n开始训练流量预测模型...")
        print(f"配置参数: epochs={epochs}, batch_size={batch_size}, validation_split={validation_split}")
        
        if multi_features is not None and self.multi_feature:
            # 使用多特征输入
            data_dict = multi_features.copy()
            data_dict['traffic'] = traffic_data
            X, y, target_scaler, _ = self.prepare_multivariate_data(data_dict, target_type='traffic')
            input_shape = (self.sequence_length, len(data_dict))
            print(f"使用多特征输入: {list(data_dict.keys())}")
        else:
            # 使用单特征输入
            X, y = self.prepare_data(traffic_data, is_traffic=True)
            input_shape = (self.sequence_length, 1)
            print("使用单特征输入: 流量数据")
        
        print(f"训练数据形状: X={X.shape}, y={y.shape}")
        
        # 构建模型
        self.traffic_model = self.build_model(input_shape, self.prediction_horizon)
        
        # 早停回调
        early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        
        # 进度打印回调
        class ProgressCallback(tf.keras.callbacks.Callback):
            def on_epoch_end(self, epoch, logs=None):
                if epoch % 5 == 0 or epoch == epochs - 1:  # 每5个epoch打印一次，以及最后一个epoch
                    progress = (epoch + 1) / epochs * 100
                    print(f"训练进度: {progress:.1f}% (Epoch {epoch+1}/{epochs}), "
                          f"损失: {logs['loss']:.4f}, 验证损失: {logs['val_loss']:.4f}")
        
        # 训练模型
        history = self.traffic_model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[early_stopping, ProgressCallback()],
            verbose=0  # 关闭默认进度条，使用自定义进度显示
        )
        
        self.is_trained_traffic = True
        print("流量预测模型训练完成!")
        return history
    
    def train_energy_model(self, energy_data, epochs=50, batch_size=32, validation_split=0.2, multi_features=None):
        """训练节点能量消耗预测模型
        
        参数:
            energy_data: 节点能量历史数据
            epochs: 训练轮数
            batch_size: 批次大小
            validation_split: 验证集比例
            multi_features: 多特征输入字典，格式为 {feature_name: feature_data}
            
        返回:
            训练历史
        """
        if multi_features is not None and self.multi_feature:
            # 使用多特征输入
            data_dict = multi_features.copy()
            data_dict['energy'] = energy_data
            X, y, target_scaler, _ = self.prepare_multivariate_data(data_dict, target_type='energy')
            input_shape = (self.sequence_length, len(data_dict))
        else:
            # 使用单特征输入
            X, y = self.prepare_data(energy_data, is_traffic=False)
            input_shape = (self.sequence_length, 1)
        
        # 构建模型
        self.energy_model = self.build_model(input_shape, self.prediction_horizon)
        
        # 早停回调
        early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        
        # 训练模型
        history = self.energy_model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[early_stopping],
            verbose=1
        )
        
        self.is_trained_energy = True
        return history
        
    def train_link_quality_model(self, link_quality_data, epochs=50, batch_size=32, validation_split=0.2, multi_features=None):
        """训练链路质量预测模型
        
        参数:
            link_quality_data: 链路质量历史数据
            epochs: 训练轮数
            batch_size: 批次大小
            validation_split: 验证集比例
            multi_features: 多特征输入字典，格式为 {feature_name: feature_data}
            
        返回:
            训练历史
        """
        if multi_features is not None and self.multi_feature:
            # 使用多特征输入
            data_dict = multi_features.copy()
            data_dict['link_quality'] = link_quality_data
            X, y, target_scaler, _ = self.prepare_multivariate_data(data_dict, target_type='link_quality')
            input_shape = (self.sequence_length, len(data_dict))
        else:
            # 使用单特征输入
            X, y = self.prepare_data(link_quality_data, is_traffic=False, is_link_quality=True)
            input_shape = (self.sequence_length, 1)
        
        # 构建模型
        self.link_quality_model = self.build_model(input_shape, self.prediction_horizon)
        
        # 早停回调
        early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        
        # 训练模型
        history = self.link_quality_model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[early_stopping],
            verbose=1
        )
        
        self.is_trained_link_quality = True
        return history
    
    def predict_traffic(self, recent_traffic, multi_features=None):
        """预测未来网络流量
        
        参数:
            recent_traffic: 最近的流量数据，长度应为sequence_length
            multi_features: 多特征输入字典，格式为 {feature_name: feature_data}
            
        返回:
            预测的未来流量数据
        """
        if not self.is_trained_traffic:
            raise ValueError("流量预测模型尚未训练")
        
        # 确保输入长度正确
        if len(recent_traffic) != self.sequence_length:
            raise ValueError(f"输入数据长度应为{self.sequence_length}")
        
        if multi_features is not None and self.multi_feature:
            # 使用多特征输入
            data_dict = multi_features.copy()
            data_dict['traffic'] = recent_traffic
            
            # 标准化所有特征
            scaled_features = {}
            for feature_name, feature_data in data_dict.items():
                scaler = MinMaxScaler(feature_range=(0, 1))
                scaled_features[feature_name] = scaler.fit_transform(feature_data.reshape(-1, 1))
            
            # 收集所有特征的序列
            features_sequence = []
            for feature_name in data_dict.keys():
                features_sequence.append(scaled_features[feature_name][:self.sequence_length, 0])
            
            # 将所有特征堆叠为一个多变量序列
            X = np.column_stack(features_sequence)
            X = np.reshape(X, (1, X.shape[0], X.shape[1]))
        else:
            # 使用单特征输入
            # 数据标准化
            scaled_data = self.traffic_scaler.transform(recent_traffic.reshape(-1, 1))
            
            # 重塑为LSTM输入格式
            X = np.reshape(scaled_data, (1, self.sequence_length, 1))
        
        # 预测
        scaled_prediction = self.traffic_model.predict(X)
        
        # 反标准化
        prediction = self.traffic_scaler.inverse_transform(scaled_prediction.reshape(-1, 1))
        
        return prediction.flatten()
    
    def predict_energy(self, recent_energy, multi_features=None):
        """预测未来节点能量消耗
        
        参数:
            recent_energy: 最近的能量数据，长度应为sequence_length
            multi_features: 多特征输入字典，格式为 {feature_name: feature_data}
            
        返回:
            预测的未来能量数据
        """
        if not self.is_trained_energy:
            raise ValueError("能量预测模型尚未训练")
        
        # 确保输入长度正确
        if len(recent_energy) != self.sequence_length:
            raise ValueError(f"输入数据长度应为{self.sequence_length}")
        
        if multi_features is not None and self.multi_feature:
            # 使用多特征输入
            data_dict = multi_features.copy()
            data_dict['energy'] = recent_energy
            
            # 标准化所有特征
            scaled_features = {}
            for feature_name, feature_data in data_dict.items():
                scaler = MinMaxScaler(feature_range=(0, 1))
                scaled_features[feature_name] = scaler.fit_transform(feature_data.reshape(-1, 1))
            
            # 收集所有特征的序列
            features_sequence = []
            for feature_name in data_dict.keys():
                features_sequence.append(scaled_features[feature_name][:self.sequence_length, 0])
            
            # 将所有特征堆叠为一个多变量序列
            X = np.column_stack(features_sequence)
            X = np.reshape(X, (1, X.shape[0], X.shape[1]))
        else:
            # 使用单特征输入
            # 数据标准化
            scaled_data = self.energy_scaler.transform(recent_energy.reshape(-1, 1))
            
            # 重塑为LSTM输入格式
            X = np.reshape(scaled_data, (1, self.sequence_length, 1))
        
        # 预测
        scaled_prediction = self.energy_model.predict(X)
        
        # 反标准化
        prediction = self.energy_scaler.inverse_transform(scaled_prediction.reshape(-1, 1))
        
        return prediction.flatten()
    
    def predict_link_quality(self, recent_link_quality, multi_features=None):
        """预测未来链路质量
        
        参数:
            recent_link_quality: 最近的链路质量数据，长度应为sequence_length
            multi_features: 多特征输入字典，格式为 {feature_name: feature_data}
            
        返回:
            预测的未来链路质量数据
        """
        if not self.is_trained_link_quality:
            raise ValueError("链路质量预测模型尚未训练")
        
        # 确保输入长度正确
        if len(recent_link_quality) != self.sequence_length:
            raise ValueError(f"输入数据长度应为{self.sequence_length}")
        
        if multi_features is not None and self.multi_feature:
            # 使用多特征输入
            data_dict = multi_features.copy()
            data_dict['link_quality'] = recent_link_quality
            
            # 标准化所有特征
            scaled_features = {}
            for feature_name, feature_data in data_dict.items():
                scaler = MinMaxScaler(feature_range=(0, 1))
                scaled_features[feature_name] = scaler.fit_transform(feature_data.reshape(-1, 1))
            
            # 收集所有特征的序列
            features_sequence = []
            for feature_name in data_dict.keys():
                features_sequence.append(scaled_features[feature_name][:self.sequence_length, 0])
            
            # 将所有特征堆叠为一个多变量序列
            X = np.column_stack(features_sequence)
            X = np.reshape(X, (1, X.shape[0], X.shape[1]))
        else:
            # 使用单特征输入
            # 数据标准化
            scaled_data = self.link_quality_scaler.transform(recent_link_quality.reshape(-1, 1))
            
            # 重塑为LSTM输入格式
            X = np.reshape(scaled_data, (1, self.sequence_length, 1))
        
        # 预测
        scaled_prediction = self.link_quality_model.predict(X)
        
        # 反标准化
        prediction = self.link_quality_scaler.inverse_transform(scaled_prediction.reshape(-1, 1))
        
        return prediction.flatten()
    
    def predict_node_failure(self, recent_energy, energy_threshold=0.1, time_steps=None, multi_features=None, additional_factors=None):
        """预测节点故障
        
        参数:
            recent_energy: 最近的能量数据
            energy_threshold: 能量阈值，低于此值视为故障
            time_steps: 预测的时间步数，默认为prediction_horizon
            multi_features: 多特征输入字典，用于能量预测
            additional_factors: 影响节点故障的额外因素字典，格式为 {factor_name: weight}
            
        返回:
            (failure_predicted, time_to_failure, failure_probability): 是否预测到故障，预计故障时间，以及故障概率
        """
        if time_steps is None:
            time_steps = self.prediction_horizon
        
        # 预测未来能量
        if multi_features is not None and self.multi_feature:
            # 使用多特征预测能量
            future_energy = self.predict_energy(recent_energy, multi_features)
        else:
            future_energy = self.predict_energy(recent_energy)
        
        # 基础故障检测：检查是否有预测值低于阈值
        failure_indices = np.where(future_energy < energy_threshold)[0]
        
        # 计算基础故障概率
        if len(failure_indices) > 0:
            # 找到第一次故障的时间步
            time_to_failure = failure_indices[0] + 1  # +1因为索引从0开始
            base_failure_probability = 1.0 - (future_energy[failure_indices[0]] / energy_threshold)
        else:
            time_to_failure = None
            min_energy = np.min(future_energy)
            base_failure_probability = 0.5 * (1.0 - (min_energy / energy_threshold))
            if base_failure_probability < 0:
                base_failure_probability = 0
        
        # 考虑额外因素
        final_failure_probability = base_failure_probability
        if additional_factors is not None:
            # 额外因素权重总和
            total_weight = sum(additional_factors.values())
            
            # 计算额外因素的影响
            for factor, weight in additional_factors.items():
                if factor == 'traffic_congestion' and 'congestion_probability' in additional_factors:
                    # 网络拥塞会增加故障概率
                    final_failure_probability += (additional_factors['congestion_probability'] * weight / total_weight)
                elif factor == 'link_quality' and 'link_quality_value' in additional_factors:
                    # 链路质量差会增加故障概率
                    link_quality = additional_factors['link_quality_value']
                    link_quality_factor = 1.0 - link_quality  # 链路质量越低，影响越大
                    final_failure_probability += (link_quality_factor * weight / total_weight)
                elif factor == 'temperature' and 'temperature_value' in additional_factors:
                    # 温度过高会增加故障概率
                    temp = additional_factors['temperature_value']
                    temp_threshold = additional_factors.get('temperature_threshold', 70)  # 默认温度阈值
                    if temp > temp_threshold:
                        temp_factor = (temp - temp_threshold) / 30  # 假设温度超过阈值30度会导致100%故障
                        final_failure_probability += (min(temp_factor, 1.0) * weight / total_weight)
            
            # 确保概率在[0,1]范围内
            final_failure_probability = max(0.0, min(1.0, final_failure_probability))
        
        # 根据最终概率确定是否预测到拥塞
        failure_predicted = final_failure_probability > 0.5 or (time_to_failure is not None)
        
        return failure_predicted, time_to_failure, final_failure_probability
    
    def predict_congestion(self, recent_traffic, capacity_threshold, time_steps=None, multi_features=None, additional_factors=None):
        """预测网络拥塞
        
        参数:
            recent_traffic: 最近的流量数据
            capacity_threshold: 容量阈值，高于此值视为拥塞
            time_steps: 预测的时间步数，默认为prediction_horizon
            multi_features: 多特征输入字典，用于流量预测
            additional_factors: 影响拥塞的额外因素字典，格式为 {factor_name: weight}
            
        返回:
            (congestion_predicted, time_to_congestion, congestion_probability): 是否预测到拥塞，预计拥塞时间，以及拥塞概率
        """
        if time_steps is None:
            time_steps = self.prediction_horizon
        
        # 预测未来流量
        if multi_features is not None and self.multi_feature:
            # 使用多特征预测流量
            future_traffic = self.predict_traffic(recent_traffic, multi_features)
        else:
            future_traffic = self.predict_traffic(recent_traffic)
        
        # 基础拥塞检测：检查是否有预测值高于阈值
        congestion_indices = np.where(future_traffic > capacity_threshold)[0]
        
        # 计算基础拥塞概率
        if len(congestion_indices) > 0:
            # 找到第一次拥塞的时间步
            time_to_congestion = congestion_indices[0] + 1  # +1因为索引从0开始
            base_congestion_probability = (future_traffic[congestion_indices[0]] / capacity_threshold) - 1.0
            base_congestion_probability = min(base_congestion_probability, 1.0)  # 确保概率不超过1
        else:
            time_to_congestion = None
            max_traffic = np.max(future_traffic)
            base_congestion_probability = 0.5 * (max_traffic / capacity_threshold)
            if base_congestion_probability > 1.0:
                base_congestion_probability = 1.0
        
        # 考虑额外因素
        final_congestion_probability = base_congestion_probability
        if additional_factors is not None:
            # 额外因素权重总和
            total_weight = sum(additional_factors.values())
            
            # 计算额外因素的影响
            for factor, weight in additional_factors.items():
                if factor == 'node_failures' and 'failure_count' in additional_factors:
                    # 节点故障会增加拥塞概率
                    failure_count = additional_factors['failure_count']
                    failure_factor = min(failure_count / 10.0, 1.0)  # 假设10个节点故障会导致100%拥塞
                    final_congestion_probability += (failure_factor * weight / total_weight)
                elif factor == 'link_quality' and 'link_quality_value' in additional_factors:
                    # 链路质量差会增加拥塞概率
                    link_quality = additional_factors['link_quality_value']
                    link_quality_factor = 1.0 - link_quality  # 链路质量越低，影响越大
                    final_congestion_probability += (link_quality_factor * weight / total_weight)
                elif factor == 'packet_loss' and 'packet_loss_rate' in additional_factors:
                    # 丢包率高会增加拥塞概率
                    packet_loss = additional_factors['packet_loss_rate']
                    final_congestion_probability += (packet_loss * weight / total_weight)
            
            # 确保概率在[0,1]范围内
            final_congestion_probability = max(0.0, min(1.0, final_congestion_probability))
        
        # 根据最终概率确定是否预测到拥塞
        congestion_predicted = final_congestion_probability > 0.5 or (time_to_congestion is not None)
        
        return congestion_predicted, time_to_congestion, final_congestion_probability
    
    def visualize_prediction(self, actual_data, recent_data, prediction, title="预测结果"):
        """可视化预测结果
        
        参数:
            actual_data: 实际数据（如果有）
            recent_data: 最近的历史数据
            prediction: 预测数据
            title: 图表标题
        """
        plt.figure(figsize=(12, 6))
        
        # 绘制历史数据
        time_points = list(range(len(recent_data)))
        plt.plot(time_points, recent_data, 'b-', label='历史数据')
        
        # 绘制预测数据
        future_time_points = list(range(len(recent_data), len(recent_data) + len(prediction)))
        plt.plot(future_time_points, prediction, 'r--', label='预测数据')
        
        # 如果有实际未来数据，也绘制出来
        if actual_data is not None and len(actual_data) >= len(prediction):
            plt.plot(future_time_points, actual_data[:len(prediction)], 'g-', label='实际数据')
        
        plt.title(title)
        plt.xlabel('时间步')
        plt.ylabel('值')
        plt.legend()
        plt.grid(True)
        plt.show()
    
    def save_models(self, traffic_model_path='traffic_model.h5', energy_model_path='energy_model.h5', link_quality_model_path='link_quality_model.h5'):
        """保存训练好的模型
        
        参数:
            traffic_model_path: 流量模型保存路径
            energy_model_path: 能量模型保存路径
            link_quality_model_path: 链路质量模型保存路径
        """
        if self.is_trained_traffic:
            self.traffic_model.save(traffic_model_path)
            print(f"流量预测模型已保存到 {traffic_model_path}")
        
        if self.is_trained_energy:
            self.energy_model.save(energy_model_path)
            print(f"能量预测模型已保存到 {energy_model_path}")
            
        if self.is_trained_link_quality:
            self.link_quality_model.save(link_quality_model_path)
            print(f"链路质量预测模型已保存到 {link_quality_model_path}")
        
        # 保存模型版本和更新时间
        from datetime import datetime
        self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"模型版本: {self.model_version}, 更新时间: {self.last_update}")
    
    def load_models(self, traffic_model_path='traffic_model.h5', energy_model_path='energy_model.h5', link_quality_model_path='link_quality_model.h5'):
        """加载预训练模型
        
        参数:
            traffic_model_path: 流量模型路径
            energy_model_path: 能量模型路径
            link_quality_model_path: 链路质量模型路径
        """
        try:
            self.traffic_model = tf.keras.models.load_model(traffic_model_path)
            self.is_trained_traffic = True
            print(f"已加载流量预测模型 {traffic_model_path}")
        except Exception as e:
            print(f"加载流量模型失败: {e}")
        
        try:
            self.energy_model = tf.keras.models.load_model(energy_model_path)
            self.is_trained_energy = True
            print(f"已加载能量预测模型 {energy_model_path}")
        except Exception as e:
            print(f"加载能量模型失败: {e}")
            
        try:
            self.link_quality_model = tf.keras.models.load_model(link_quality_model_path)
            self.is_trained_link_quality = True
            print(f"已加载链路质量预测模型 {link_quality_model_path}")
        except Exception as e:
            print(f"加载链路质量模型失败: {e}")
            
        # 更新加载时间
        from datetime import datetime
        self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"模型加载完成，当前时间: {self.last_update}")

    def integrated_prediction_for_routing(self, node_id, neighbor_nodes, recent_data):
        """为EEHFR协议的路由决策提供集成预测结果
        
        参数:
            node_id: 当前节点ID
            neighbor_nodes: 邻居节点列表，每个元素为包含节点信息的字典
            recent_data: 包含各种最近数据的字典，格式为 {data_type: data_array}
            
        返回:
            routing_metrics: 路由决策指标字典，包含各种预测结果和建议
        """
        # 初始化路由指标字典
        routing_metrics = {
            'node_id': node_id,
            'timestamp': None,
            'predictions': {},
            'recommendations': {}
        }
        
        # 记录当前时间
        from datetime import datetime
        routing_metrics['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 提取各种数据
        recent_traffic = recent_data.get('traffic', None)
        recent_energy = recent_data.get('energy', None)
        recent_link_quality = recent_data.get('link_quality', None)
        
        # 创建多特征输入字典
        multi_features = {k: v for k, v in recent_data.items() if k not in ['traffic', 'energy', 'link_quality']}
        
        # 预测结果字典
        predictions = {}
        
        # 1. 流量预测
        if recent_traffic is not None and self.is_trained_traffic:
            try:
                future_traffic = self.predict_traffic(recent_traffic, multi_features if self.multi_feature else None)
                predictions['traffic'] = future_traffic.tolist()
                
                # 检测拥塞
                capacity_threshold = recent_data.get('capacity_threshold', np.max(recent_traffic) * 1.5)
                congestion_predicted, time_to_congestion, congestion_probability = self.predict_congestion(
                    recent_traffic, capacity_threshold, multi_features=multi_features if self.multi_feature else None
                )
                predictions['congestion'] = {
                    'predicted': congestion_predicted,
                    'time_to_congestion': time_to_congestion,
                    'probability': float(congestion_probability)
                }
            except Exception as e:
                predictions['traffic_error'] = str(e)
        
        # 2. 能量预测
        if recent_energy is not None and self.is_trained_energy:
            try:
                future_energy = self.predict_energy(recent_energy, multi_features if self.multi_feature else None)
                predictions['energy'] = future_energy.tolist()
                
                # 检测节点故障
                energy_threshold = recent_data.get('energy_threshold', np.min(recent_energy) * 0.5)
                additional_factors = {
                    'traffic_congestion': 0.3,
                    'link_quality': 0.3,
                    'temperature': 0.2
                }
                if 'congestion_probability' in predictions.get('congestion', {}):
                    additional_factors['congestion_probability'] = predictions['congestion']['probability']
                if recent_link_quality is not None:
                    additional_factors['link_quality_value'] = np.mean(recent_link_quality)
                if 'temperature' in recent_data:
                    additional_factors['temperature_value'] = np.mean(recent_data['temperature'])
                    additional_factors['temperature_threshold'] = recent_data.get('temperature_threshold', 70)
                
                failure_predicted, time_to_failure, failure_probability = self.predict_node_failure(
                    recent_energy, energy_threshold, 
                    multi_features=multi_features if self.multi_feature else None,
                    additional_factors=additional_factors
                )
                predictions['node_failure'] = {
                    'predicted': failure_predicted,
                    'time_to_failure': time_to_failure,
                    'probability': float(failure_probability)
                }
            except Exception as e:
                predictions['energy_error'] = str(e)
        
        # 3. 链路质量预测
        if recent_link_quality is not None and self.is_trained_link_quality:
            try:
                future_link_quality = self.predict_link_quality(recent_link_quality, multi_features if self.multi_feature else None)
                predictions['link_quality'] = future_link_quality.tolist()
            except Exception as e:
                predictions['link_quality_error'] = str(e)
        
        # 将预测结果添加到路由指标中
        routing_metrics['predictions'] = predictions
        
        # 生成路由建议
        recommendations = {}
        
        # 1. 节点排名 - 基于预测结果为邻居节点评分
        if neighbor_nodes:
            node_scores = {}
            for node in neighbor_nodes:
                # 初始分数
                score = 50.0
                
                # 根据能量水平调整分数
                if 'energy_level' in node:
                    score += node['energy_level'] * 20  # 能量水平范围假设为[0,1]
                
                # 根据链路质量调整分数
                if 'link_quality' in node:
                    score += node['link_quality'] * 15  # 链路质量范围假设为[0,1]
                
                # 根据拥塞情况调整分数
                if 'congestion_level' in node:
                    score -= node['congestion_level'] * 25  # 拥塞水平范围假设为[0,1]
                
                # 根据故障概率调整分数
                if 'failure_probability' in node:
                    score -= node['failure_probability'] * 30  # 故障概率范围为[0,1]
                
                # 存储节点分数
                node_scores[node['id']] = max(0, min(100, score))  # 确保分数在[0,100]范围内
            
            # 对节点进行排名
            ranked_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
            recommendations['node_ranking'] = ranked_nodes
        
        # 2. 路由策略建议
        routing_strategy = {}
        
        # 基于拥塞预测的策略
        if 'congestion' in predictions and predictions['congestion']['predicted']:
            routing_strategy['congestion_avoidance'] = True
            routing_strategy['load_balancing'] = True
        else:
            routing_strategy['congestion_avoidance'] = False
            routing_strategy['load_balancing'] = False
        
        # 基于节点故障预测的策略
        if 'node_failure' in predictions and predictions['node_failure']['predicted']:
            routing_strategy['fault_tolerance'] = True
            routing_strategy['redundant_paths'] = True
        else:
            routing_strategy['fault_tolerance'] = False
            routing_strategy['redundant_paths'] = False
        
        # 基于链路质量预测的策略
        if 'link_quality' in predictions:
            avg_future_link_quality = np.mean(predictions['link_quality'])
            if avg_future_link_quality < 0.5:  # 假设链路质量范围为[0,1]
                routing_strategy['link_quality_aware'] = True
                routing_strategy['retransmission'] = True
            else:
                routing_strategy['link_quality_aware'] = False
                routing_strategy['retransmission'] = False
        
        # 添加路由策略到建议中
        recommendations['routing_strategy'] = routing_strategy
        
        # 3. 能量管理建议
        energy_management = {}
        
        # 基于能量预测的策略
        if 'energy' in predictions:
            min_future_energy = np.min(predictions['energy'])
            if min_future_energy < 20:  # 假设能量阈值为20
                energy_management['energy_conservation'] = True
                energy_management['duty_cycling'] = True
                energy_management['transmission_power_control'] = True
            else:
                energy_management['energy_conservation'] = False
                energy_management['duty_cycling'] = False
                energy_management['transmission_power_control'] = False
        
        # 添加能量管理策略到建议中
        recommendations['energy_management'] = energy_management
        
        # 将建议添加到路由指标中
        routing_metrics['recommendations'] = recommendations
        
        return routing_metrics

# 测试代码
if __name__ == "__main__":
    # 生成模拟数据
    np.random.seed(42)
    
    # 模拟网络流量数据（带有周期性和趋势）
    time_steps = 200
    t = np.arange(time_steps)
    trend = 0.01 * t
    seasonality = 10 * np.sin(t * (2 * np.pi / 24))  # 24小时周期
    noise = 2 * np.random.normal(0, 1, time_steps)
    traffic_data = trend + seasonality + noise
    
    # 模拟节点能量数据（递减趋势）
    initial_energy = 100
    energy_decay = np.exp(-0.01 * t)
    energy_noise = 2 * np.random.normal(0, 1, time_steps)
    energy_data = initial_energy * energy_decay + energy_noise
    energy_data = np.clip(energy_data, 0, initial_energy)  # 确保能量非负且不超过初始值
    
    # 模拟链路质量数据（波动趋势）
    link_quality_base = 0.8 - 0.3 * (t / time_steps)  # 基础链路质量随时间下降
    link_quality_noise = 0.1 * np.random.normal(0, 1, time_steps)
    link_quality_data = link_quality_base + link_quality_noise
    link_quality_data = np.clip(link_quality_data, 0, 1)  # 确保链路质量在[0,1]范围内
    
    # 创建LSTM预测模型
    sequence_length = 24  # 使用24个时间步的历史数据
    prediction_horizon = 12  # 预测未来12个时间步
    
    lstm_predictor = LSTMPrediction(sequence_length, prediction_horizon, multi_feature=True)
    
    # 训练流量模型（使用前160个数据点）
    traffic_train = traffic_data[:160]
    history_traffic = lstm_predictor.train_traffic_model(traffic_train, epochs=50)
    
    # 训练能量模型
    energy_train = energy_data[:160]
    history_energy = lstm_predictor.train_energy_model(energy_train, epochs=50)
    
    # 训练链路质量模型
    link_quality_train = link_quality_data[:160]
    history_link_quality = lstm_predictor.train_link_quality_model(link_quality_train, epochs=50)
    
    # 测试流量预测
    test_start = 160
    recent_traffic = traffic_data[test_start:test_start+sequence_length]
    predicted_traffic = lstm_predictor.predict_traffic(recent_traffic)
    actual_future_traffic = traffic_data[test_start+sequence_length:test_start+sequence_length+prediction_horizon]
    
    print("流量预测结果:")
    print("预测值:", predicted_traffic)
    print("实际值:", actual_future_traffic)
    
    # 测试能量预测
    recent_energy = energy_data[test_start:test_start+sequence_length]
    predicted_energy = lstm_predictor.predict_energy(recent_energy)
    actual_future_energy = energy_data[test_start+sequence_length:test_start+sequence_length+prediction_horizon]
    
    print("\n能量预测结果:")
    print("预测值:", predicted_energy)
    print("实际值:", actual_future_energy)
    
    # 测试链路质量预测
    recent_link_quality = link_quality_data[test_start:test_start+sequence_length]
    predicted_link_quality = lstm_predictor.predict_link_quality(recent_link_quality)
    actual_future_link_quality = link_quality_data[test_start+sequence_length:test_start+sequence_length+prediction_horizon]
    
    print("\n链路质量预测结果:")
    print("预测值:", predicted_link_quality)
    print("实际值:", actual_future_link_quality)
    
    # 测试节点故障预测
    failure_predicted, time_to_failure, failure_probability = lstm_predictor.predict_node_failure(recent_energy, energy_threshold=20)
    print(f"\n节点故障预测: {failure_predicted}")
    if failure_predicted:
        print(f"预计在{time_to_failure}个时间步后发生故障")
    print(f"故障概率: {failure_probability:.2f}")
    
    # 测试网络拥塞预测
    congestion_predicted, time_to_congestion, congestion_probability = lstm_predictor.predict_congestion(recent_traffic, capacity_threshold=25)
    print(f"\n网络拥塞预测: {congestion_predicted}")
    if congestion_predicted:
        print(f"预计在{time_to_congestion}个时间步后发生拥塞")
    print(f"拥塞概率: {congestion_probability:.2f}")
    
    # 测试多特征预测
    multi_features = {
        'temperature': np.random.normal(25, 5, sequence_length),
        'humidity': np.random.normal(60, 10, sequence_length),
        'packet_loss': np.random.uniform(0, 0.2, sequence_length)
    }
    
    # 测试集成预测
    node_id = 'node_1'
    neighbor_nodes = [
        {'id': 'node_2', 'energy_level': 0.8, 'link_quality': 0.9, 'congestion_level': 0.1, 'failure_probability': 0.05},
        {'id': 'node_3', 'energy_level': 0.6, 'link_quality': 0.7, 'congestion_level': 0.3, 'failure_probability': 0.15},
        {'id': 'node_4', 'energy_level': 0.4, 'link_quality': 0.5, 'congestion_level': 0.6, 'failure_probability': 0.35}
    ]
    
    recent_data = {
        'traffic': recent_traffic,
        'energy': recent_energy,
        'link_quality': recent_link_quality,
        'temperature': multi_features['temperature'],
        'humidity': multi_features['humidity'],
        'packet_loss': multi_features['packet_loss'],
        'capacity_threshold': 25,
        'energy_threshold': 20,
        'temperature_threshold': 35
    }
    
    routing_metrics = lstm_predictor.integrated_prediction_for_routing(node_id, neighbor_nodes, recent_data)
    print("\n集成预测结果:")
    print(f"节点排名: {routing_metrics['recommendations']['node_ranking']}")
    print(f"路由策略: {routing_metrics['recommendations']['routing_strategy']}")
    print(f"能量管理: {routing_metrics['recommendations']['energy_management']}")
    
    # 可视化预测结果
    lstm_predictor.visualize_prediction(
        actual_future_traffic, recent_traffic, predicted_traffic, 
        title="网络流量预测"
    )
    
    lstm_predictor.visualize_prediction(
        actual_future_energy, recent_energy, predicted_energy, 
        title="节点能量预测"
    )
    
    lstm_predictor.visualize_prediction(
        actual_future_link_quality, recent_link_quality, predicted_link_quality, 
        title="链路质量预测"
    )
