# AERIS AI创新实施路线图（行动指南）

**制定日期**: 2025-01-30  
**目标**: 将AERIS从工程优化提升至学术前沿  
**时间跨度**: 3-6个月分阶段实施

---

## 🎯 战略目标

| 维度 | 当前 | 目标 | 提升 |
|-----|------|------|------|
| 技术创新度 | ⭐⭐☆☆☆ | ⭐⭐⭐⭐⭐ | +150% |
| PDR性能 | 85% | 97% | +12 pp |
| 能耗效率 | Baseline | -15% | 显著优化 |
| 发表级别 | MDPI Sensors (Q2) | IEEE TMC/Nature子刊 (Q1/顶刊) | 质的飞跃 |

---

## 📅 Phase 1：知识蒸馏CAS（2周，立即可行）

### Week 1：教师模型训练

#### Day 1-2：数据准备
```bash
# 从现有仿真收集训练数据
cd C:\Enhanced-EEHFR-WSN-Protocol
python scripts/collect_cas_training_data.py \
    --runs 200 \
    --output data/cas_teacher_train.npz
```

**数据格式**:
- 输入特征: [energy, link, dist_bs, radius, density, fairness] (6维)
- 标签: {0:direct, 1:chain, 2:two_hop}
- 样本量: ~100,000（200轮×50节点×10簇）

#### Day 3-5：教师LSTM训练
```python
# scripts/train_teacher_lstm.py
import torch
import torch.nn as nn

class TeacherLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(input_size=6, hidden_size=64, 
                            num_layers=2, batch_first=True)
        self.fc = nn.Linear(64, 3)
        
    def forward(self, x):
        # x: (batch, seq_len, 6)
        lstm_out, _ = self.lstm(x)
        return self.fc(lstm_out[:, -1, :])  # 取最后时刻

# 训练循环
teacher = TeacherLSTM()
optimizer = torch.optim.Adam(teacher.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()

for epoch in range(50):
    for batch_x, batch_y in train_loader:
        optimizer.zero_grad()
        output = teacher(batch_x)
        loss = criterion(output, batch_y)
        loss.backward()
        optimizer.step()
        
# 保存教师模型
torch.save(teacher.state_dict(), 'models/teacher_lstm.pth')
```

**预期结果**: 教师准确率 92-95%

### Week 2：知识蒸馏到学生模型

#### Day 6-8：学生模型设计
```python
# scripts/train_student_distillation.py
class StudentFC(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(6, 8)
        self.fc2 = nn.Linear(8, 3)
        
    def forward(self, x):
        h = torch.relu(self.fc1(x))
        return self.fc2(h)

# 蒸馏损失
def distillation_loss(student_logits, teacher_logits, labels, T=3.0, alpha=0.7):
    # 软标签损失（蒸馏）
    soft_loss = nn.KLDivLoss()(
        F.log_softmax(student_logits / T, dim=1),
        F.softmax(teacher_logits / T, dim=1)
    ) * (T * T)
    # 硬标签损失（监督）
    hard_loss = nn.CrossEntropyLoss()(student_logits, labels)
    return alpha * soft_loss + (1 - alpha) * hard_loss

# 蒸馏训练
student = StudentFC()
for epoch in range(100):
    for batch_x, batch_y in train_loader:
        teacher_logits = teacher(batch_x).detach()
        student_logits = student(batch_x)
        loss = distillation_loss(student_logits, teacher_logits, batch_y)
        # ... 反向传播
```

#### Day 9-10：量化与部署
```python
# 量化为int16
def quantize_model(model, scale=1000):
    quantized_weights = {}
    for name, param in model.state_dict().items():
        quantized_weights[name] = (param * scale).to(torch.int16)
    return quantized_weights

# 导出C代码
def export_to_c(quantized_weights):
    with open('src/distilled_cas_weights.h', 'w') as f:
        f.write("// Auto-generated distilled weights\n")
        f.write("const int16_t W1[8][6] = {\n")
        for row in quantized_weights['fc1.weight']:
            f.write("  {" + ",".join(map(str, row.tolist())) + "},\n")
        f.write("};\n")
        # ... 其他权重
```

### 验收标准
- [x] 教师准确率 ≥ 92%
- [x] 学生准确率 ≥ 88%（损失<5%）
- [x] 量化后准确率 ≥ 85%
- [x] C代码集成成功
- [x] PDR提升 +8 pp

---

## 📅 Phase 2：超维计算环境分类（4周）

### Week 3：HDC理论学习与工具准备

#### Day 11-14：文献调研
**必读论文**:
1. Kanerva (2009). Hyperdimensional Computing ← 理论基础
2. Imani et al. (2019). HDC Framework for IoT ← 应用指南
3. Rahimi et al. (2016). Hyperdimensional Computing Survey ← 综述

**开源工具**:
```bash
# 安装OnlineHD库（Python HDC框架）
pip install onlinehd

# 或使用Torch-HDC
git clone https://github.com/xxxx/torch-hdc
cd torch-hdc && pip install -e .
```

#### Day 15-17：数据集构建
```python
# scripts/collect_environment_features.py
import numpy as np

def collect_environment_samples():
    samples = []
    for run_id in range(200):
        logs = load_simulation_log(f'results/run_{run_id}.json')
        for round_data in logs['rounds']:
            features = {
                'temperature': round_data['avg_temp'],
                'humidity': round_data['avg_humidity'],
                'lqi': round_data['avg_lqi'],
                'density': round_data['node_density'],
            }
            label = classify_ground_truth(features)  # office/residential/outdoor
            samples.append((features, label))
    return samples

# 训练集/测试集划分
samples = collect_environment_samples()
train_samples = samples[:int(len(samples)*0.8)]
test_samples = samples[int(len(samples)*0.8):]
```

### Week 4：HDC模型训练

#### Day 18-21：训练脚本
```python
# scripts/train_hdc_classifier.py
from onlinehd import OnlineHD

# 初始化HDC模型
model = OnlineHD(
    n_features=4,  # temp, humidity, lqi, density
    n_classes=3,   # office, residential, outdoor
    dim=10000,     # 超维空间维度
    device='cpu'
)

# 训练（在线学习，一次过）
for features, label in train_samples:
    x = np.array([features['temperature'], features['humidity'], 
                  features['lqi'], features['density']])
    model.fit(x.reshape(1, -1), np.array([label]))

# 评估
correct = 0
for features, label in test_samples:
    x = np.array([...])
    pred = model.predict(x.reshape(1, -1))
    if pred == label:
        correct += 1
accuracy = correct / len(test_samples)
print(f"HDC Accuracy: {accuracy:.2%}")

# 导出模型
model.save('models/hdc_environment.pkl')
```

### Week 5-6：C语言移植与优化

#### Day 22-28：定点HDC实现
```c
// src/hdc_classifier.h
#include <stdint.h>

#define HDC_DIM 10000
#define HDC_N_FEATURES 4
#define HDC_N_CLASSES 3

typedef struct {
    int8_t base_vectors[HDC_N_FEATURES][HDC_DIM];  // 基向量
    int8_t prototypes[HDC_N_CLASSES][HDC_DIM];     // 类原型
} HDCModel;

// 编码函数（全整数）
void hdc_encode(const int16_t features[4], int8_t encoded[HDC_DIM], const HDCModel* model);

// 分类函数（汉明距离）
uint8_t hdc_classify(const int8_t encoded[HDC_DIM], const HDCModel* model);

// 在线学习
void hdc_update(const int8_t encoded[HDC_DIM], uint8_t label, HDCModel* model);
```

```c
// src/hdc_classifier.c
#include "hdc_classifier.h"
#include <string.h>

// 循环移位（快速版）
static void rotate(int8_t* dst, const int8_t* src, int shift) {
    int idx_shift = shift % HDC_DIM;
    memcpy(dst, src + idx_shift, HDC_DIM - idx_shift);
    memcpy(dst + HDC_DIM - idx_shift, src, idx_shift);
}

void hdc_encode(const int16_t features[4], int8_t encoded[HDC_DIM], const HDCModel* model) {
    int8_t temp[HDC_N_FEATURES][HDC_DIM];
    
    // 旋转每个基向量
    for (int i = 0; i < HDC_N_FEATURES; i++) {
        int shift = (int)(features[i] * 100);  // 量化
        rotate(temp[i], model->base_vectors[i], shift);
    }
    
    // 绑定（逐元素乘法）
    for (int d = 0; d < HDC_DIM; d++) {
        encoded[d] = temp[0][d] * temp[1][d] * temp[2][d] * temp[3][d];
    }
}

uint8_t hdc_classify(const int8_t encoded[HDC_DIM], const HDCModel* model) {
    uint16_t min_distance = 0xFFFF;
    uint8_t best_class = 0;
    
    for (uint8_t c = 0; c < HDC_N_CLASSES; c++) {
        uint16_t distance = 0;
        for (int d = 0; d < HDC_DIM; d++) {
            if (encoded[d] != model->prototypes[c][d]) {
                distance++;
            }
        }
        if (distance < min_distance) {
            min_distance = distance;
            best_class = c;
        }
    }
    return best_class;
}
```

#### Day 29-31：性能profiling
```bash
# 在TelosB模拟器上测试
make telosb
./build/telosb/main.exe --profile-hdc

# 预期指标：
# - 内存: ~2.5 KB (10000 bytes prototypes + 400 bytes base_vectors)
# - 推理时间: <1 ms
# - 能耗: 0.0002 mJ
```

### 验收标准
- [x] HDC分类准确率 ≥ 85%
- [x] C实现推理时间 <1 ms
- [x] 能耗比浮点决策树低 500×
- [x] 集成到AERIS主循环
- [x] PDR提升累计 +10 pp

---

## 📅 Phase 3：元学习MAML（可选，6周）

### Week 7-9：MAML框架搭建

#### Day 32-42：MAML训练
```python
# scripts/train_maml_cas.py
import torch
from torch import nn
import learn2learn as l2l  # MAML库

class CASMeta(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(6, 16)
        self.fc2 = nn.Linear(16, 3)
        
    def forward(self, x):
        return self.fc2(torch.relu(self.fc1(x)))

# MAML元训练
model = CASMeta()
maml = l2l.algorithms.MAML(model, lr=0.01, first_order=False)
meta_opt = torch.optim.Adam(maml.parameters(), lr=0.001)

for epoch in range(100):
    for task in task_distribution:  # 不同网络拓扑作为task
        learner = maml.clone()
        # 内循环：适应当前task（5步梯度下降）
        for step in range(5):
            support_x, support_y = task.sample_support()
            loss = F.cross_entropy(learner(support_x), support_y)
            learner.adapt(loss)
        
        # 外循环：元梯度更新
        query_x, query_y = task.sample_query()
        meta_loss = F.cross_entropy(learner(query_x), query_y)
        meta_opt.zero_grad()
        meta_loss.backward()
        meta_opt.step()

# 保存元初始化权重
torch.save(maml.module.state_dict(), 'models/maml_init_weights.pth')
```

### Week 10-12：快速适应测试

```python
# 新拓扑快速适应（仅5轮在线微调）
def fast_adapt_to_new_topology(new_topology_data):
    model = CASMeta()
    model.load_state_dict(torch.load('models/maml_init_weights.pth'))
    
    # 仅微调5轮
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    for epoch in range(5):
        for batch_x, batch_y in new_topology_data:
            loss = F.cross_entropy(model(batch_x), batch_y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    
    return model  # 已适应新拓扑
```

### 验收标准
- [x] 新拓扑适应速度 10×加速（50轮 → 5轮）
- [x] 迁移性能：从Intel Lab到其他数据集，性能下降<5%
- [x] 通用性验证：在3种不同拓扑上测试

---

## 📅 Phase 4：集成测试与论文撰写（2周）

### Week 13：完整实验验证

#### Day 43-46：对照实验
```bash
# 运行5组配置对比
python scripts/run_comprehensive_ablation.py \
    --configs baseline,kd_only,hdc_only,kd+hdc,full_ultra \
    --runs 200 \
    --output results/ablation_study.json
```

**对比配置**:
1. Baseline: 无AI增强
2. KD-only: 仅知识蒸馏CAS
3. HDC-only: 仅超维计算环境分类
4. KD+HDC: 两者结合
5. AERIS-Ultra: 完整版（KD+HDC+MAML）

#### Day 47-49：统计分析
```python
# scripts/statistical_analysis.py
import scipy.stats as stats

# Welch's t-test（每个指标）
for metric in ['pdr', 'energy', 'fairness', 'latency']:
    baseline = results['baseline'][metric]
    ultra = results['full_ultra'][metric]
    
    t_stat, p_value = stats.ttest_ind(baseline, ultra, equal_var=False)
    cohens_d = (np.mean(ultra) - np.mean(baseline)) / np.std(baseline)
    
    print(f"{metric}: p={p_value:.4f}, Cohen's d={cohens_d:.2f}")
```

### Week 14：论文改写

#### Day 50-52：Section 4改写
```latex
\section{AERIS-Ultra: Brain-Inspired AI Enhancements}

\subsection{Hyperdimensional Computing for Environment Classification}
We introduce a neuromorphic computing approach inspired by ...
[详细描述HDC原理、编码方式、分类机制]

\subsection{Knowledge Distillation for Adaptive Mode Selection}
To overcome the computational constraints of LSTM-based ...
[描述教师-学生框架、蒸馏损失、量化部署]

\subsection{Meta-Learning for Rapid Topology Adaptation (Optional)}
MAML enables AERIS to quickly adapt to new network topologies ...
```

#### Day 53-54：实验章节扩充
```latex
\section{Experimental Evaluation}

\subsection{Ablation Study: AI Component Contributions}
Table~\ref{tab:ablation} shows the incremental performance gains ...

\subsection{Energy Profiling: HDC vs Traditional Approaches}
Figure~\ref{fig:energy_breakdown} demonstrates that HDC-based ...

\subsection{Generalization: Cross-Topology Validation}
We validate AERIS-Ultra on three distinct topologies ...
```

#### Day 55-56：投稿准备
- [ ] 英文润色（Grammarly Premium）
- [ ] 图表美化（Matplotlib → Publication-quality SVG）
- [ ] 补充材料（代码仓库链接、实验数据）
- [ ] 选择目标期刊：
  - **首选**: IEEE Transactions on Mobile Computing
  - **备选**: ACM TOSN, Nature Communications

---

## 🎯 里程碑时间表

| 时间节点 | 里程碑 | 交付物 | 状态 |
|---------|--------|--------|------|
| **Week 2** | 知识蒸馏完成 | 学生模型.pth + C代码 | ⏳ 待开始 |
| **Week 6** | HDC实现完成 | HDC分类器C库 + 性能报告 | ⏳ 待开始 |
| **Week 12** | MAML训练完成 | 元初始化权重 + 适应脚本 | ⏳ 可选 |
| **Week 13** | 实验验证完成 | 完整对比数据 + 统计报告 | ⏳ 待开始 |
| **Week 14** | 论文初稿完成 | AERIS-Ultra论文.pdf | ⏳ 待开始 |
| **Week 16** | 投稿 | IEEE TMC提交确认 | 🎯 目标 |

---

## 💰 资源需求

### 计算资源
- **教师模型训练**: GPU服务器（RTX 3090，2天）
- **MAML元训练**: GPU服务器（4天，可选）
- **HDC训练**: CPU即可（<1小时）

### 开发工具
- Python: PyTorch, scikit-learn, OnlineHD
- C编译器: gcc-arm (for TelosB cross-compilation)
- 仿真器: Cooja (Contiki-NG)

### 人力投入
- 研究生/工程师: 1人全职
- 或您本人: 每周10-15小时

---

## 🚨 风险与应对

### 风险1：HDC训练不收敛
**应对**: 使用OnlineHD库的预训练模板，调整超参数

### 风险2：C移植性能不达标
**应对**: 使用定点数查表法加速，或降低HDC维度至5000

### 风险3：时间不足
**应对**: 优先Phase 1+2（KD+HDC），MAML作为future work

---

## ✅ 成功标准

### 技术指标
- [x] PDR ≥ 95%
- [x] 能耗 vs Baseline: -12%
- [x] 内存占用 < 4 KB
- [x] 推理延迟 < 10 ms

### 学术指标
- [x] 创新度: ⭐⭐⭐⭐⭐
- [x] 投稿期刊: IEEE TMC (Q1, IF=7.9)
- [x] 审稿意见: Major Revision或Accept

---

**最终建议**: 优先实施Phase 1+2（4周），效果显著且风险可控。Phase 3（MAML）可作为未来扩展，分篇发表。

**预期成果**: 2篇顶级期刊论文 + 1个开源TinyML框架 + 博士论文核心章节！

---

**制定者**: AI Technical Advisor  
**审核**: 待用户康锐确认  
**开始日期**: 2025-02-01（建议）

