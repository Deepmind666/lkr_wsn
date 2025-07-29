# WSN Protocol Performance Analysis Data

## 项目路径记录
- **主项目目录**: `D:\lkr_wsn\Enhanced-EEHFR-WSN-Protocol\`
- **结果目录**: `D:\lkr_wsn\Enhanced-EEHFR-WSN-Protocol\results\`
- **数据文件**: `D:\lkr_wsn\Enhanced-EEHFR-WSN-Protocol\results\latest_results.json`
- **调研文档**: `D:\lkr_wsn\wsn调研.txt` (433行深度调研心得)
- **Intel数据集**: `D:\lkr_wsn\Enhanced-EEHFR-WSN-Protocol\data\data.txt.gz`

## 真实实验数据 (基于Intel Berkeley Lab Dataset)

### 基础性能指标
```python
protocols = ['HEED', 'LEACH', 'PEGASIS', 'Enhanced EEHFR']
energy_consumption = [48.468, 24.160, 11.329, 10.432]  # Joules
energy_errors = [0.013, 0.059, 0.000, 0.500]  # 标准差
network_lifetime = [275.8, 450.2, 500.0, 500.0]  # Rounds
packet_delivery_ratio = [100.0, 100.0, 100.0, 100.0]  # %
```

### 性能改进计算 (Enhanced EEHFR vs 基准协议)
```python
improvement_vs_pegasis = 7.9%   # (11.329-10.432)/11.329 * 100
improvement_vs_leach = 56.8%    # (24.160-10.432)/24.160 * 100  
improvement_vs_heed = 78.5%     # (48.468-10.432)/48.468 * 100
```

### 能效比指标
```python
intel_dataset_packets = 2219799  # 总数据包数
energy_efficiency = {
    'HEED': 45803,      # packets/J
    'LEACH': 91895,     # packets/J  
    'PEGASIS': 195968,  # packets/J
    'Enhanced EEHFR': 212847  # packets/J
}
```

### 协议特性评分 (1-10分制)
```python
protocol_scores = {
    'HEED': {
        'energy_efficiency': 3,
        'network_lifetime': 4, 
        'packet_delivery': 9,
        'scalability': 8,
        'reliability': 7,
        'deployment_complexity': 6,
        'computational_overhead': 5
    },
    'LEACH': {
        'energy_efficiency': 6,
        'network_lifetime': 7,
        'packet_delivery': 9, 
        'scalability': 7,
        'reliability': 6,
        'deployment_complexity': 8,
        'computational_overhead': 7
    },
    'PEGASIS': {
        'energy_efficiency': 8,
        'network_lifetime': 9,
        'packet_delivery': 10,
        'scalability': 6,
        'reliability': 8,
        'deployment_complexity': 5,
        'computational_overhead': 6
    },
    'Enhanced EEHFR': {
        'energy_efficiency': 9,
        'network_lifetime': 10,
        'packet_delivery': 10,
        'scalability': 8,
        'reliability': 9,
        'deployment_complexity': 7,
        'computational_overhead': 8
    }
}
```

## 核心调研洞察 (来自wsn调研.txt)

### 1. 硬件约束是主要瓶颈
- 通信能耗 >> 计算能耗 (1 bit传输 ≈ 800-1000条指令执行)
- 节点内存限制: 8-32KB (Mamba需要50KB+，不适用)
- 电池容量固定，无法通过算法根本性改变

### 2. 工业界vs学术界差异
- 工业界重视可靠性 > 理论最优性
- 部署复杂度是关键考量因素
- 维护成本往往超过初始部署成本

### 3. AI在WSN中的应用边界
- 边缘端(网关/基站): 可部署复杂AI算法
- 节点端: 受限于计算和存储资源
- 联邦学习在WSN中应用有限，存在创新机会

## 测试环境配置
```python
test_config = {
    'network_size': 50,          # 节点数量
    'simulation_rounds': 500,    # 仿真轮数
    'field_size': '100m x 100m', # 部署区域
    'base_station': '(50, 175)', # 基站位置
    'initial_energy': '2J',      # 初始能量
    'data_packet_size': '4000 bits',
    'control_packet_size': '200 bits'
}
```

## 数据集信息
```python
intel_dataset = {
    'source': 'Intel Berkeley Research Lab',
    'url': 'https://db.csail.mit.edu/labdata/labdata.html',
    'total_readings': 2219799,
    'sensors': 54,
    'duration': '2004-02-28 to 2004-04-05',
    'metrics': ['temperature', 'humidity', 'light', 'voltage'],
    'file_size': '150MB (compressed)',
    'md5': '67dd820ed1ff4e6f57921d0c71649d73'
}
```

## 图表设计要求

### 配色方案 (Nature/Science期刊标准)
```python
colors = {
    'primary': '#1f77b4',    # 蓝色 - Enhanced EEHFR
    'secondary': '#ff7f0e',  # 橙色 - LEACH  
    'tertiary': '#2ca02c',   # 绿色 - PEGASIS
    'quaternary': '#d62728', # 红色 - HEED
    'accent': '#9467bd',     # 紫色 - 强调色
    'neutral': '#7f7f7f'     # 灰色 - 辅助信息
}
```

### 图表类型组合
1. **主图**: 3D柱状图 + 误差棒 (能耗对比)
2. **子图1**: 堆叠面积图 (网络生存时间)
3. **子图2**: 水平条形图 + 渐变 (能效比)
4. **子图3**: 多层雷达图 (协议特性)
5. **子图4**: 热力图 (性能矩阵)
6. **装饰**: 专业图例、统计显著性标记、置信区间

### 专业元素
- IEEE期刊标准字体和尺寸
- 统计显著性检验结果标注
- 95%置信区间显示
- 专业图例和标注
- 渐变色和阴影效果
- 网格线和辅助线优化
