# AERIS论文数据真实性审查报告

**审查日期**: 2026-01-18
**审查原因**: 发现延迟数据为理论计算而非实验测量

---

## 一、数据分类

### ✅ 真实仿真测量数据（可在论文中使用）

| 指标 | 数据来源 | AERIS | PEGASIS | LEACH | HEED |
|------|----------|-------|---------|-------|------|
| PDR@100节点 | comprehensive_experiments | 100% | 100% | 100% | 99.98% |
| PDR@500节点 | comprehensive_experiments | **100%** | 100% | **98.68%** | 99.72% |
| 能耗@100节点 | comprehensive_experiments | 82.1mJ | **41.9mJ** | 100.7mJ | 87.3mJ |
| 节点流失30%后PDR | comprehensive_experiments | 100% | 100% | 100% | 99.95% |
| 区域失效40%后PDR | comprehensive_experiments | 100% | 100% | ~100% | 99.94% |
| 执行时间@500节点 | comprehensive_experiments | 15.17s | **0.11s** | 1.03s | 0.64s |

### ❌ 编造/理论数据（必须从论文中删除）

| 声称 | 数据来源 | 问题 |
|------|----------|------|
| AERIS延迟110ms | aeris_vs_pegasis_deep_comparison.json | **理论计算**: log(n) × 10ms |
| PEGASIS延迟2500ms | aeris_vs_pegasis_deep_comparison.json | **理论计算**: n/2 × 10ms |
| LEACH延迟20ms | aeris_vs_pegasis_deep_comparison.json | **假设值**: 固定2跳 |
| "96%延迟降低" | 计算得出 | **基于理论数据的比较** |
| hop_count_distribution | compare_50x200.json | **空值**: {} |
| avg_hop_count | compare_50x200.json | **零值**: 0 |

---

## 二、AERIS真实优势（基于实验数据）

### 1. 大规模PDR稳定性 ✅
- **AERIS**: 500节点下保持100% PDR
- **LEACH**: 500节点下降至98.68% (↓1.32%)
- **统计显著**: 这是AERIS相比LEACH的真实优势

### 2. 能耗比LEACH低 ✅
- AERIS: 82.1mJ vs LEACH: 100.7mJ
- 降低: 18.5%

### 3. 鲁棒性 ✅
- 30%节点流失后仍保持100% PDR
- 40%区域失效后仍保持100% PDR

---

## 三、AERIS真实劣势（必须诚实承认）

### 1. 能耗比PEGASIS高 ❌
- AERIS: 82.1mJ vs PEGASIS: 41.9mJ
- **PEGASIS能效高出约2倍**

### 2. 执行时间长 ❌
- AERIS: 15.17s vs PEGASIS: 0.11s (500节点)
- AERIS计算开销显著更高

### 3. 小规模无优势 ❌
- 在100节点以下，所有协议PDR都是100%
- AERIS没有明显优势

---

## 四、论文重新定位

### 原定位（错误）
> "AERIS实现O(log n)延迟，比PEGASIS的O(n)延迟降低96%"

### 修正定位（基于真实数据）
> "AERIS在大规模WSN（>200节点）中保持100% PDR，
> 而LEACH在500节点时PDR降至98.68%。
> AERIS能耗比LEACH低18.5%，但比PEGASIS高约2倍。
> AERIS适用于对数据可靠性要求极高的大规模部署场景。"

---

## 五、需要修改的文件

### 必须修改的论文章节

| 章节 | 需删除的内容 | 需修正的内容 |
|------|-------------|-------------|
| Section 1 | "96%延迟降低"、延迟对比表 | 重新定位为"大规模PDR稳定性" |
| Section 4 | O(log n)延迟证明 | 改为"理论复杂度分析"或删除 |
| Section 6 | 延迟对比表、延迟实验结果 | 只保留PDR和能耗实验 |
| Section 7 | 延迟相关的应用推荐 | 基于PDR稳定性推荐 |
| Section 8 | "延迟降低96%" | 基于真实数据总结 |

### 必须修改的文档

| 文件 | 修改内容 |
|------|----------|
| 1月18日vs.md | 删除所有延迟声称，更新为真实数据 |
| GPT_Review_Analysis.md | 删除延迟相关分析 |

---

## 六、真实贡献重新评估

### 可声称的贡献（有实验支撑）
1. **C1**: AERIS在500节点规模保持100% PDR，LEACH降至98.68%
2. **C2**: AERIS能耗比LEACH低18.5%
3. **C3**: AERIS在30%节点流失下保持100% PDR
4. **C4**: Gateway机制贡献最大（消融实验Hedges' g = 10.09）

### 不可声称的贡献（无实验支撑）
- ❌ 延迟优势（无实测数据）
- ❌ O(log n)延迟（仅理论分析）
- ❌ 实时应用适用性（无延迟验证）

---

## 七、结论

AERIS的真正价值是**大规模场景下的PDR稳定性和鲁棒性**，而非延迟优势。

如果要声称延迟优势，必须：
1. 实现跳数追踪功能
2. 运行实验收集真实跳数数据
3. 基于真实数据计算延迟

否则，论文应聚焦于已验证的优势：PDR稳定性、能耗（vs LEACH）、鲁棒性。

---

**审查人**: Claude
**审查标准**: 只有实际仿真测量的数据才能作为实验结果报告
