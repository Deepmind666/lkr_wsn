# NS-3与Python对齐工作深度评审报告

**评审人**: Claude Opus 4.5
**日期**: 2026-02-02
**评审对象**: 5协议NS-3对齐实验

---

## 一、评审结论摘要

| 评审项 | 结论 | 严重程度 |
|--------|------|----------|
| AERIS对齐 | **基本可接受** | 低 |
| LEACH/HEED/TEEN PDR差异 | **严重问题** | 高 |
| PEGASIS能耗差异 | **严重问题** | 高 |
| 口径一致性 | **存在问题** | 中 |

---

## 二、核心问题分析

### 2.1 LEACH/HEED/TEEN的PDR差异（-43%~-48%）

**现象**: Python端PDR约51%-60%，NS-3端PDR约99%

**根因诊断**:

1. **NS-3端过于乐观**: NS-3的LEACH实现中，PDR计算逻辑如下：
   - 每个cluster member发送数据到CH
   - CH聚合后发送到BS
   - 使用`TransmitPacket()`判断成功，但**每个member的数据被独立计算delivered**

2. **Python端更严格**: Python的LEACH实现中：
   - 只有当节点能量足够时才计数`packets_sent`
   - `total_bs_delivered`只在CH成功发送到BS时+1
   - **没有信道丢包模型**，但有能量约束导致的隐式丢包

**关键代码对比**:

```cpp
// NS-3 LEACH (aeris-validation-standalone.cc:334-341)
for (uint32_t i = 0; i < clusterSize; i++) {
    if (!m_channelModel.TransmitPacket(memberPos, m_position, m_dataPacketSize)) continue;
    if (m_channelModel.TransmitPacket(m_position, m_bsPosition, aggSize)) delivered++;
}
s_globalPacketsDelivered += delivered;  // 每个member独立计数
```

```python
# Python LEACH (leach_protocol.py:270-271)
self.packets_sent += 1
self.total_bs_delivered += 1  # CH发送成功才+1，不是按member计数
```

**结论**: PDR口径不一致。NS-3按member计数，Python按CH聚合包计数。

### 2.2 PEGASIS能耗差异（-50%~-68%）

**现象**: Python能耗比NS-3低50%-68%

**根因诊断**:

1. **链式转发建模差异**: PEGASIS的核心是链式转发，每个节点只与邻居通信
2. **NS-3可能重复计算**: 链上每跳都计算能耗，而Python可能只计算端到端
3. **聚合包大小计算不同**: NS-3使用`aggSize = m_dataPacketSize + clusterSize * 64`

### 2.3 AERIS对齐情况

**现象**: PDR差异0.1%-6%，能耗差异-13%~+27%

**评价**: 相对可接受，但仍需解释：
- 100节点/300轮: PDR差-5.9%，能耗差+2.8%
- 500节点/500轮: PDR差-1.3%，能耗差-27.5%

---

## 三、严苛审查清单回应

### 3.1 口径核验

| 指标 | NS-3定义 | Python定义 | 是否一致 |
|------|----------|------------|----------|
| PDR | delivered/sent (per member) | bs_delivered/source_packets | **不一致** |
| Energy | 累加所有节点消耗 | 累加所有节点消耗 | 一致 |

### 3.2 协议实现一致性

**NS-3的PEGASIS/HEED/TEEN是简化实现**，与Python的完整实现存在差异：
- NS-3只有AERIS和LEACH的完整实现
- PEGASIS/HEED/TEEN在NS-3中可能是stub或简化版

### 3.3 能耗模型一致性

| 参数 | NS-3 | Python |
|------|------|--------|
| E_ELEC | 50e-9 J/bit | 50e-9 J/bit (legacy) / 208.8e-9 (CC2420) |
| E_FS | 10e-12 J/bit/m² | 10e-12 J/bit/m² |
| d_crossover | 87.7m | 87.0m |

**问题**: Python使用CC2420统一模型时E_ELEC=208.8nJ/bit，与NS-3的50nJ/bit差4倍。

---

## 四、建议的修复优先级

### 优先级1: PDR口径统一（最紧急）

修改NS-3或Python的PDR计算，统一为：
- **端到端PDR** = 成功到达BS的源数据包数 / 总源数据包数

### 优先级2: PEGASIS能耗溯源

核对链式转发的能耗计算逻辑，确保每跳能耗一致。

### 优先级3: 能耗模型参数对齐

统一E_ELEC参数，或在论文中明确说明差异。

---

## 五、总体评价

同事的工作**框架正确**，但存在**口径不一致**的根本问题。建议：

1. 先修复PDR口径问题再做大规模对比
2. 论文中只使用AERIS vs LEACH的NS-3验证结果
3. PEGASIS/HEED/TEEN暂时只用Python结果

**评审结论**: 需要返工修复口径问题后才能用于论文。
