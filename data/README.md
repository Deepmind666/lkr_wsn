# 📊 数据集说明

## Intel Berkeley Research Lab数据集

本项目使用MIT CSAIL Intel Berkeley Research Lab提供的真实WSN数据集进行算法验证和性能测试。

### 📋 数据集基本信息

- **官方网站**: https://db.csail.mit.edu/labdata/labdata.html
- **数据来源**: MIT计算机科学与人工智能实验室
- **收集时间**: 2004年2月28日 - 2004年4月5日 (36天)
- **网络规模**: 54个传感器节点
- **数据规模**: 2,219,799条传感器记录

### 📁 数据文件结构

```
data/
├── README.md                    # 本说明文件
├── sample_data/                 # 示例数据文件
│   ├── sample_sensor_data.csv   # 传感器数据样本
│   ├── sample_locations.csv     # 节点位置样本
│   └── sample_connectivity.csv  # 连接性数据样本
└── intel_lab_info.md           # 详细数据集信息
```

### 🔍 数据字段说明

#### 传感器数据 (sensor_data)
- **date**: 时间戳 (YYYY-MM-DD HH:MM:SS.mmm)
- **time**: Unix时间戳
- **epoch**: 数据采集轮次
- **moteid**: 传感器节点ID (1-54)
- **temperature**: 温度读数 (摄氏度)
- **humidity**: 湿度读数 (相对湿度%)
- **light**: 光照强度读数 (Lux)
- **voltage**: 电池电压 (V)

#### 节点位置数据 (locations)
- **moteid**: 传感器节点ID
- **x**: X坐标 (米)
- **y**: Y坐标 (米)

#### 连接性数据 (connectivity)
- **moteid**: 源节点ID
- **connected_nodes**: 可连接的邻居节点列表

### 📈 数据质量

- **总记录数**: 2,219,799条
- **有效数据率**: 81.5% (经过异常值过滤)
- **缺失数据**: 18.5% (主要由于传感器故障或通信中断)
- **数据完整性**: 高质量的真实环境数据

### 🔧 数据预处理

项目中的数据预处理包括：

1. **异常值检测**: 移除明显错误的传感器读数
2. **缺失值处理**: 使用插值方法填补缺失数据
3. **数据标准化**: 将不同类型的传感器数据标准化到相同范围
4. **时间序列对齐**: 确保所有节点的时间戳同步

### 📊 使用示例

```python
from src.intel_dataset_loader import IntelLabDataLoader

# 加载数据
loader = IntelLabDataLoader()
sensor_data = loader.load_sensor_data()
locations = loader.load_locations_data()
connectivity = loader.load_connectivity_data()

print(f"加载了 {len(sensor_data)} 条传感器记录")
print(f"网络包含 {len(locations)} 个节点")
```

### 🎯 在 AERIS 协议中的应用

1. **网络拓扑**: 使用真实的节点位置和连接性数据
2. **能量模型**: 基于真实的电压读数建立能量消耗模型
3. **环境感知**: 利用温度、湿度、光照数据进行智能路由决策
4. **性能验证**: 使用真实数据验证协议的实际效果

### 📚 引用信息

如果您在研究中使用了此数据集，请引用：

```bibtex
@misc{intel_lab_data,
  title={Intel Berkeley Research lab},
  author={Intel Berkeley Research Lab},
  year={2004},
  url={https://db.csail.mit.edu/labdata/labdata.html}
}
```

### ⚠️ 使用注意事项

1. **数据大小**: 完整数据集约34.4MB，请确保有足够存储空间
2. **处理时间**: 大规模数据处理可能需要较长时间
3. **内存使用**: 建议至少4GB RAM用于数据处理
4. **网络下载**: 首次使用需要从官方网站下载数据

### 🔗 相关链接

- [MIT CSAIL官方数据页面](https://db.csail.mit.edu/labdata/labdata.html)
- [数据集论文](https://db.csail.mit.edu/labdata/labdata.html)
- [Intel Berkeley Research Lab](https://www.intel.com/content/www/us/en/research/overview.html)
