# GPT-5 提示词：Day 1 - CAS训练数据提取

**任务**: 从AERIS仿真中提取CAS（Context-Aware Selector）的训练数据  
**目标**: 生成可直接运行的Python脚本

---

## 📋 复制以下内容给GPT-5

```
你好！我正在开发一个无线传感器网络路由协议AERIS，需要你帮我生成数据提取脚本。

### 项目背景

我的AERIS协议有一个CAS（Context-Aware Selector）模块，负责为每个节点选择最佳传输模式：
- Mode 0: direct（直接传输到基站）
- Mode 1: chain（链式传输）
- Mode 2: two_hop（两跳传输）

CAS当前使用6个特征进行决策：
1. energy: 节点剩余能量比例 (0-1)
2. link_quality: 链路质量 (0-1)
3. dist_bs: 到基站的归一化距离 (0-1)
4. cluster_radius: 簇半径归一化值 (0-1)
5. node_density: 节点密度 (0-1)
6. fairness: 公平性指标 (0-1)

### 当前项目结构

```
C:\Enhanced-EEHFR-WSN-Protocol\
├── src\
│   ├── aeris_protocol.py          # 主协议实现
│   ├── cas_selector.py            # CAS选择器（当前基于规则）
│   └── improved_energy_model.py   # 能量模型
├── scripts\                       # 脚本目录（将在此创建新脚本）
├── data\                          # 数据目录（将保存训练数据）
└── results\                       # 仿真结果目录
```

### 任务要求

请生成一个完整的Python脚本 `scripts/extract_cas_training_data.py`，实现以下功能：

#### 方案A：如果有现成的仿真日志
1. 检查 `results/` 目录下是否有仿真日志文件（可能是.json, .csv, .pkl等格式）
2. 解析日志，提取每次CAS决策的：
   - 输入特征：6维特征向量
   - 输出标签：选择的模式(0/1/2)
3. 数据预处理：
   - 确保所有特征已归一化到[0,1]
   - 检查是否有缺失值或异常值
   - 过滤无效样本
4. 保存为NumPy格式：
   - `data/cas_features.npy`: shape=(N, 6), dtype=float32
   - `data/cas_labels.npy`: shape=(N,), dtype=int64

#### 方案B：如果没有现成日志（更可能的情况）
1. 修改 `src/aeris_protocol.py`，在CAS决策点添加数据记录
2. 生成一个数据收集脚本 `scripts/collect_cas_data.py`，运行多次仿真收集数据
3. 具体实现：
   - 在CAS选择函数被调用时，记录(features, mode)
   - 运行仿真：不同拓扑、不同参数、至少收集10000个样本
   - 保存到临时文件 `data/cas_raw_data.pkl`
4. 从临时文件转换为NumPy格式

### 具体技术要求

1. **数据量**：
   - 最少10000个样本
   - 建议15000-20000个样本
   - 确保3个类别均衡（每类至少30%）

2. **特征归一化**：
   - 使用MinMaxScaler确保所有特征在[0,1]范围
   - 保存归一化参数到 `data/cas_scaler.pkl`（用于后续推理）

3. **数据验证**：
   - 检查特征范围是否在[0,1]
   - 检查标签是否只有0/1/2
   - 打印类别分布
   - 打印每个特征的统计信息（min, max, mean, std）

4. **输出格式**：
   ```python
   # cas_features.npy
   shape: (N, 6)
   dtype: np.float32
   范围: [0, 1]
   
   # cas_labels.npy
   shape: (N,)
   dtype: np.int64
   取值: {0, 1, 2}
   ```

### 代码参考

我的CAS选择器当前实现在 `src/cas_selector.py` 中，核心函数可能类似：

```python
class CASSelector:
    def select_mode(self, node, network_state):
        # 提取特征
        features = self._extract_features(node, network_state)
        # 当前基于规则选择模式
        mode = self._rule_based_selection(features)
        return mode
    
    def _extract_features(self, node, network_state):
        # 返回6维特征向量
        return np.array([
            node.energy / node.initial_energy,  # energy
            node.link_quality,                   # link_quality
            node.distance_to_bs / max_dist,      # dist_bs
            cluster.radius / max_radius,         # cluster_radius
            network_state.density,               # node_density
            network_state.fairness               # fairness
        ])
```

你需要在这个函数中添加数据记录功能。

### 输出要求

请生成以下文件（完整代码，可直接运行）：

1. **主脚本**：`scripts/extract_cas_training_data.py`
   - 自动检测使用方案A还是方案B
   - 包含详细的进度提示和错误处理
   - 最后打印数据统计报告

2. **数据收集脚本**（如果需要方案B）：`scripts/collect_cas_data.py`
   - 运行多轮仿真收集数据
   - 参数化配置（拓扑数量、节点数、运行轮次）

3. **README**：`scripts/README_data_collection.md`
   - 说明如何运行脚本
   - 常见问题解决方案
   - 数据质量检查方法

### 示例输出

脚本运行后应该显示类似：

```
=== CAS Training Data Extraction ===

Step 1: Checking for existing logs...
✓ Found simulation logs in results/

Step 2: Extracting features and labels...
  Processed 15234 decision points
  Filtered 142 invalid samples
  Valid samples: 15092

Step 3: Data statistics
  Total samples: 15092
  Class distribution:
    Mode 0 (direct):   5821 (38.6%)
    Mode 1 (chain):    4892 (32.4%)
    Mode 2 (two_hop):  4379 (29.0%)
  
  Feature ranges:
    energy:         [0.02, 1.00], mean=0.64, std=0.23
    link_quality:   [0.15, 0.98], mean=0.72, std=0.18
    dist_bs:        [0.08, 0.95], mean=0.48, std=0.21
    cluster_radius: [0.12, 0.89], mean=0.53, std=0.19
    node_density:   [0.25, 0.88], mean=0.61, std=0.15
    fairness:       [0.42, 0.96], mean=0.78, std=0.12

Step 4: Saving data...
✓ Saved to data/cas_features.npy (15092, 6)
✓ Saved to data/cas_labels.npy (15092,)
✓ Saved scaler to data/cas_scaler.pkl

=== Extraction Complete! ===
Next step: Train teacher LSTM model
```

### 注意事项

1. 代码必须健壮，包含所有异常处理
2. 如果数据不足，给出明确的下一步指示
3. 代码中包含详细注释（中文或英文均可）
4. 确保Windows路径兼容性（使用 `pathlib.Path`）
5. 依赖库：numpy, scipy, scikit-learn, pickle

### 如果你需要更多信息

如果你需要查看 `src/cas_selector.py` 或 `src/aeris_protocol.py` 的实际代码才能生成脚本，请告诉我，我会提供。否则，请基于上述描述生成通用的、健壮的数据提取脚本。

现在请开始生成完整代码！
```

---

## 📝 使用说明

1. **复制上面的提示词**（从"你好！我正在开发..."到"现在请开始生成完整代码！"）

2. **粘贴到GPT-5对话框**

3. **GPT-5会生成3个文件的完整代码**：
   - `scripts/extract_cas_training_data.py`
   - `scripts/collect_cas_data.py`（如果需要）
   - `scripts/README_data_collection.md`

4. **复制GPT-5生成的代码到对应文件**

5. **运行脚本**：
   ```bash
   cd C:\Enhanced-EEHFR-WSN-Protocol
   python scripts/extract_cas_training_data.py
   ```

---

## 🔧 如果GPT-5问你问题

GPT-5可能会问：

**Q1**: "我需要看一下你的 `cas_selector.py` 实际代码才能更精确地生成脚本，可以提供吗？"

**A1**: 提供以下路径让我读取：
```
C:\Enhanced-EEHFR-WSN-Protocol\src\cas_selector.py
```

**Q2**: "你的仿真日志是什么格式？"

**A2**: "我不确定，请生成能自动检测.json/.csv/.pkl的通用脚本"

**Q3**: "需要多少训练数据？"

**A3**: "至少10000个样本，建议15000-20000"

---

## ✅ 验收标准

GPT-5生成的脚本应该能：

- [x] 自动检测数据源（日志文件或需要收集）
- [x] 处理Windows路径
- [x] 包含进度提示
- [x] 异常处理完善
- [x] 输出详细统计报告
- [x] 生成正确格式的.npy文件

---

**准备好了吗？复制上面的提示词，粘贴给GPT-5，开始Day 1的任务！** 🚀

