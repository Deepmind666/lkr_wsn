# AERIS: A Reliable Hierarchical Routing Protocol for Large-Scale Wireless Sensor Networks

**Target Journal**: Applied Intelligence (APIN) - Springer
**Version**: 2026-01-18 (数据真实性修正版)

---

## Authors

1. **Xiaobo Zhang**<sup>1</sup>
2. **Kangrui Li**<sup>1,*</sup>
3. **Junyi Lin**<sup>1</sup>
4. **Yuting Wen**<sup>1</sup>

<sup>1</sup> Faculty of Automation, Guangdong University of Technology, Guangzhou 510006, China
<sup>*</sup> Corresponding author. E-mail: 1403073295@mails.gdut.edu.cn

---

## Abstract

Wireless sensor networks (WSNs) face challenges in maintaining high packet delivery ratio (PDR) as network scale increases. Classical protocols such as LEACH exhibit PDR degradation at large scales due to increased transmission distances, while PEGASIS achieves optimal energy efficiency but with higher computational complexity.

This paper presents **AERIS** (Adaptive Environment-aware Routing for IoT Sensors), a hierarchical routing protocol designed to maintain reliable data delivery at scale. Through comprehensive experiments with **200 independent runs** per configuration and rigorous statistical validation (Welch's t-test, Holm-Bonferroni correction), we demonstrate:

1. **100% PDR at scale**: AERIS maintains 100% PDR at 500 nodes, while LEACH degrades to 98.68% (statistically significant, p < 0.001)
2. **18.5% energy reduction vs LEACH**: AERIS consumes 82.1mJ vs LEACH's 100.7mJ at 100 nodes
3. **Robustness**: AERIS maintains 100% PDR under 30% node churn and 40% regional failure

**Honest Assessment**: We acknowledge that PEGASIS achieves approximately **50% lower energy consumption** than AERIS (41.9mJ vs 82.1mJ). For energy-critical applications, PEGASIS remains optimal. AERIS is positioned for **large-scale deployments (>200 nodes) requiring guaranteed data delivery**.

**Keywords**: Wireless Sensor Networks; Reliable Routing; Hierarchical Protocol; Large-Scale IoT; PDR Optimization

---

## 1. Introduction

### 1.1 Background and Motivation

Wireless sensor networks (WSNs) have become essential for IoT applications including environmental monitoring, industrial automation, and smart cities. As deployments scale to hundreds of nodes, maintaining reliable data delivery becomes critical.

### 1.2 The Scalability Problem

Our preliminary experiments reveal a critical issue: **LEACH's PDR degrades at scale**.

**Table 1: PDR Degradation at Scale (Measured)**

| Protocol | 100 Nodes | 300 Nodes | 500 Nodes | Δ |
|----------|-----------|-----------|-----------|---|
| **AERIS** | 100.0% | 100.0% | **100.0%** | 0% |
| LEACH | 100.0% | 99.30% | **98.68%** | -1.32% |
| PEGASIS | 100.0% | 100.0% | 100.0% | 0% |
| HEED | 99.98% | 99.88% | 99.72% | -0.26% |

At 500 nodes, LEACH loses 1.32% of packets—unacceptable for critical applications.

### 1.3 Research Gap

Existing protocols present trade-offs:
- **LEACH**: Simple but PDR degrades at scale
- **PEGASIS**: Optimal energy but complex chain reconstruction
- **HEED**: Balanced but probabilistic clustering causes occasional packet loss

**Gap**: No protocol simultaneously achieves {100% PDR at 500 nodes, lower energy than LEACH, robustness to node failures}.

### 1.4 Contributions

This paper makes the following contributions (all supported by experimental data):

**C1. Scale Reliability**: AERIS maintains 100% PDR at 500 nodes while LEACH degrades to 98.68% (p < 0.001, Cohen's d = 1.89).

**C2. Energy Efficiency vs LEACH**: AERIS reduces energy consumption by 18.5% compared to LEACH (82.1mJ vs 100.7mJ).

**C3. Robustness**: AERIS maintains 100% PDR under 30% node churn and 40% regional failure scenarios.

**C4. Gateway Mechanism**: Ablation study shows Gateway coordination is the primary contributor (Hedges' g = 10.09).

### 1.5 Honest Limitations

We explicitly acknowledge:

1. **Energy vs PEGASIS**: PEGASIS consumes ~50% less energy than AERIS (41.9mJ vs 82.1mJ). For energy-critical applications, PEGASIS is optimal.

2. **Computational overhead**: AERIS requires 15.17s execution time at 500 nodes vs PEGASIS's 0.11s.

3. **Small-scale**: At <200 nodes, all protocols achieve ~100% PDR. AERIS advantage emerges only at scale.

### 1.6 Target Applications

AERIS is designed for:
- Large-scale deployments (>200 nodes) requiring guaranteed delivery
- Applications where 1-2% packet loss is unacceptable
- Dynamic environments with potential node failures

**AERIS is NOT recommended for**:
- Energy-harvesting deployments → Use **PEGASIS**
- Small-scale networks (<200 nodes) → Use **LEACH** (simpler)

---

## 修正检查清单

- [x] 删除所有"延迟"、"latency"相关声称
- [x] 删除"96%延迟降低"
- [x] 删除O(log n) vs O(n)延迟对比
- [x] 重新定位为"大规模PDR稳定性"
- [x] Table 1改为PDR对比（实测数据）
- [x] 诚实承认PEGASIS能效优势
- [x] 所有数据均来自实际仿真测量

---

**数据来源**: results/Comprehensive_Experiment_Analysis_Report.md
**统计验证**: 200次独立运行，Welch's t-test, Holm-Bonferroni校正
