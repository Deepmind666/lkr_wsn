# Section 6: Results and Analysis (数据真实性修正版)

**Target Journal**: Applied Intelligence (APIN) - Springer
**Version**: 2026-01-18
**数据来源**: 全部为实际仿真测量数据

---

## 6. Results and Analysis

This section presents experimental results based on **actual simulation measurements**. All data comes from comprehensive experiments with 200 independent runs per configuration.

### 6.1 Baseline Comparison (100 Nodes)

**Table 9: Baseline Protocol Comparison (Measured Data)**

| Protocol | Energy (mJ) | PDR (%) | Execution Time (s) |
|----------|-------------|---------|-------------------|
| LEACH | 100.7 | 100.0 | 0.10 |
| **PEGASIS** | **41.9** | 100.0 | **0.02** |
| HEED | 87.3 | 99.98 | 0.12 |
| **AERIS** | 82.1 | **100.0** | 1.14 |

#### 6.1.1 Energy Consumption Analysis

**Honest Assessment**:
- PEGASIS achieves the lowest energy consumption (41.9mJ)
- **PEGASIS is 49% more energy-efficient than AERIS** (41.9mJ vs 82.1mJ)
- AERIS is 18.5% more energy-efficient than LEACH (82.1mJ vs 100.7mJ)

**Key Finding**: For energy-critical applications, PEGASIS remains the optimal choice.

#### 6.1.2 PDR Analysis

At 100 nodes, AERIS, LEACH, and PEGASIS all achieve ~100% PDR. The differences emerge at larger scales.

### 6.2 Scalability Analysis (核心结果)

This is AERIS's primary advantage: **PDR stability at scale**.

**Table 10: PDR at Scale (Measured Data)**

| Protocol | 50 Nodes | 100 Nodes | 200 Nodes | 300 Nodes | 500 Nodes |
|----------|----------|-----------|-----------|-----------|-----------|
| **AERIS** | 100.0% | 100.0% | 100.0% | **100.0%** | **100.0%** |
| LEACH | 100.0% | 100.0% | 99.71% | 99.30% | **98.68%** |
| PEGASIS | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| HEED | 100.0% | 99.98% | 99.95% | 99.88% | 99.72% |

**Critical Finding**:
- **LEACH PDR degrades 1.32%** at 500 nodes (100% → 98.68%)
- AERIS and PEGASIS both maintain 100% PDR
- This difference is statistically significant (p < 0.001)

**Table 11: Energy at Scale (Measured Data, mJ)**

| Protocol | 50 Nodes | 100 Nodes | 300 Nodes | 500 Nodes |
|----------|----------|-----------|-----------|-----------|
| LEACH | 48.2 | 100.7 | 328.4 | 562.1 |
| **PEGASIS** | **19.8** | **41.9** | **134.5** | **225.8** |
| HEED | 42.1 | 87.3 | 278.2 | 471.3 |
| AERIS | 39.5 | 82.1 | 262.8 | 445.6 |

PEGASIS maintains energy efficiency advantage across all scales.

### 6.3 Dynamic Topology Robustness

#### 6.3.1 Node Churn (Measured Data)

**Table 12: PDR Under Node Churn**

| Protocol | 0% | 10% | 20% | 30% |
|----------|-----|------|------|------|
| AERIS | 100.0% | 100.0% | 100.0% | 100.0% |
| LEACH | 100.0% | 100.0% | 100.0% | 100.0% |
| PEGASIS | 100.0% | 100.0% | 100.0% | 100.0% |
| HEED | 99.98% | 99.97% | 99.96% | 99.95% |

All protocols demonstrate robust performance under node churn.

#### 6.3.2 Regional Failure (Measured Data)

**Table 13: PDR Under Regional Failure (40% nodes failed)**

| Protocol | Baseline | 40% Regional Failure |
|----------|----------|---------------------|
| AERIS | 100.0% | 100.0% |
| LEACH | 100.0% | ~99.997% |
| PEGASIS | 100.0% | 100.0% |
| HEED | 99.98% | 99.94% |

AERIS maintains 100% PDR even with 40% regional node failure.

### 6.4 Statistical Validation

**Table 14: Statistical Significance (AERIS vs Baselines, 500 Nodes)**

| Comparison | Metric | Difference | p-value | Cohen's d |
|------------|--------|------------|---------|-----------|
| AERIS vs LEACH | PDR | +1.32% | <0.001*** | 1.89 (large) |
| AERIS vs LEACH | Energy | -116.5mJ | <0.001*** | 2.76 (large) |
| AERIS vs PEGASIS | Energy | +219.8mJ | <0.001*** | 4.15 (large) |
| AERIS vs HEED | PDR | +0.28% | 0.002** | 0.70 (medium) |

### 6.5 Ablation Study (Measured Data)

**Table 15: AERIS Component Contribution**

| Configuration | PDR (%) | Energy (mJ) | Hedges' g |
|---------------|---------|-------------|-----------|
| AERIS Full | 100.0 | 82.1 | --- |
| −Gateway | 89.2 | 75.4 | **10.09** (large) |
| −Fairness | 99.4 | 84.3 | 0.59 (medium) |
| −Safety | 99.7 | 81.8 | 0.42 (small) |
| −CAS | 100.0 | 82.0 | 0.00 (negligible) |

**Key Finding**: Gateway mechanism is the primary contributor (g = 10.09). CAS module has negligible independent effect.

### 6.6 Honest Trade-off Summary

**Table 16: Honest Comparison at 500 Nodes**

| Metric | AERIS | PEGASIS | LEACH | Winner |
|--------|-------|---------|-------|--------|
| **PDR** | **100%** | 100% | 98.68% | **AERIS/PEGASIS** |
| **Energy** | 445.6mJ | **225.8mJ** | 562.1mJ | **PEGASIS** |
| **Execution Time** | 15.17s | **0.11s** | 1.03s | **PEGASIS** |
| Scale Reliability | ✓ | ✓ | ✗ | AERIS/PEGASIS |

**Conclusion**:
- AERIS优于LEACH: PDR稳定性 + 能耗更低
- PEGASIS优于AERIS: 能耗更低 + 执行更快
- AERIS的价值: 比LEACH更可靠，比PEGASIS更简单

---

## ⚠️ 已删除的内容（无实验支撑）

以下内容因缺乏实际测量数据已从本节删除：
- ~~延迟对比表（110ms vs 2500ms）~~ - 理论计算，非实测
- ~~"96%延迟降低"~~ - 基于理论数据
- ~~O(log n) vs O(n) 延迟分析~~ - 复杂度分析，非实验结果
- ~~跳数统计~~ - hop_count_distribution为空

---

## 数据来源声明

本节所有数据均来自：
- `results/comprehensive_dynamic_experiments.json`
- `results/Comprehensive_Experiment_Analysis_Report.md`

实验配置：
- 200次独立运行
- 相同随机种子确保可重复性
- Welch's t-test + Holm-Bonferroni校正
