# AERIS论文修订指南

基于先验实验和统计验证结果，本指南提供论文修订建议。

生成时间: 2025-12-27

---

## 🔬 关键实验发现

### 1. CAS模块效应量为零 ⚠️
- **FULL vs -CAS**: Hedges g = 0.000 (negligible)
- **含义**: CAS模块对PDR和能耗没有统计显著影响
- **建议**: 降低CAS在论文中的重要性

### 2. Gateway是核心贡献 ✓
- **FULL vs -GW**: Hedges g = 10.088 (large)
- **含义**: Gateway中继机制是AERIS性能的主要来源
- **建议**: 将Gateway作为核心创新点

### 3. MCU时延超预算 ⚠️
- **总时延**: 167ms (超出25ms MCU预算)
- **CAS组件**: 4.5ms (在预算内)
- **瓶颈**: Skeleton选择
- **建议**: 调整"MCU可部署"声称

### 4. 环境感知有科学基础 ✓
- **AUC**: 0.990 (优秀预测能力)
- **相关性**: r=-0.499 (湿度-链路)
- **建议**: 保留环境感知描述

---

## 📝 Section-by-Section修订建议

### Abstract
**原文可能声称**:
> "AERIS通过CAS实现环境感知路由..."

**建议修改为**:
> "AERIS通过Gateway中继机制和负载均衡策略提升WSN可靠性，
> 辅以环境感知的上下文切换框架..."

### Section 1: Introduction

**需要调整的声称**:
1. ❌ "CAS是核心创新" → ✓ "Gateway/Fairness是核心创新"
2. ❌ "MCU可部署" → ✓ "边缘网关级别可部署"或"小规模网络(<10 CHs)"
3. ❌ "面向动态环境" → ✓ "面向静态部署环境"

**建议添加**:
- 先验实验的科学支撑（E0-E4）
- 诚实的适用范围声明

### Section 3: Methodology

**CAS部分**:
- 保留CAS描述，但降低其重要性
- 说明CAS提供模式选择框架
- 强调实际效果依赖Gateway

**Gateway部分**:
- 突出Gateway中继机制
- 详细描述两跳中继策略
- 强调对远距离簇头的支持

**Fairness部分**:
- 强调负载均衡的必要性
- 引用E3实验结果（Gini-PDR r=-0.75）

### Section 4: Experiments

**需要添加的内容**:

1. **先验实验结果** (新增Section 4.1)
   - E0: 环境-链路相关性分析
   - E1: CAS特征贡献度验证
   - E2: Safety阈值概率论标定
   - E3: 负载均衡效应验证
   - E4: MCU决策时延分析

2. **消融实验** (新增或扩展)
   - 各模块效应量表格
   - Gateway贡献度分析
   - CAS效应量为零的讨论

3. **统计验证**
   - Welch t检验结果
   - Hedges g效应量
   - Bootstrap 95% CI
   - Holm-Bonferroni校正

### Section 5: Results

**需要诚实报告**:
1. CAS模块效应量为零
2. Gateway是主要贡献
3. MCU时延超预算
4. 适用规模限制

**建议表格**:

| 模块 | Hedges g | 解释 | 论文定位 |
|------|----------|------|----------|
| Gateway | 10.088 | Large | 核心创新 |
| Fairness | 0.593 | Medium | 重要贡献 |
| Safety | 0.424 | Small | 辅助机制 |
| CAS | 0.000 | Negligible | 框架/辅助 |

### Section 6: Discussion

**需要讨论**:
1. CAS效应量为零的可能原因
   - 当前实现可能存在问题
   - 效果被Gateway掩盖
   - 特征选择可能需要优化

2. 适用范围限制
   - 网络规模: ≤100节点
   - 部署环境: 静态
   - 硬件级别: 边缘网关

3. 未来工作
   - CAS机制优化
   - 大规模网络支持
   - 动态场景适应

---

## 📊 需要更新的图表

### 新增图表
1. 先验实验汇总图 (`prior_experiments_summary.pdf`)
2. 消融实验效应量图 (`ablation_effect_sizes.pdf`)
3. 统计验证汇总图 (`statistical_summary.pdf`)

### 需要更新的图表
1. 架构图 - 调整CAS的位置/重要性
2. 性能对比图 - 添加置信区间
3. 消融实验图 - 添加效应量标注

---

## 📁 补充材料建议

### Supplementary Material A: 先验实验详情
- E0-E4完整结果
- 所有相关性分析
- 特征重要性详表

### Supplementary Material B: 统计验证
- 完整Welch t检验矩阵
- 所有效应量计算
- Bootstrap CI详情
- Holm-Bonferroni校正表

### Supplementary Material C: 敏感性分析
- 参数扫描结果
- k_gw/k_sk敏感性曲面

---

## ✅ 修订检查清单

### 必须修改
- [ ] 调整CAS定位（核心→辅助）
- [ ] 突出Gateway贡献
- [ ] 调整MCU可部署性声称
- [ ] 添加先验实验结果
- [ ] 添加统计验证

### 建议修改
- [ ] 添加效应量表格
- [ ] 添加置信区间
- [ ] 更新架构图
- [ ] 完善补充材料

### 可选修改
- [ ] 讨论CAS效应量为零的原因
- [ ] 添加未来工作方向
- [ ] 优化图表风格

---

## 📚 参考文献建议添加

1. 效应量解释标准 (Cohen, 1988)
2. Bootstrap方法 (Efron & Tibshirani, 1993)
3. 多重比较校正 (Holm, 1979)
4. WSN能耗模型 (Heinzelman et al., 2000)
