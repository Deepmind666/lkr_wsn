# AERIS: A Hierarchical Routing Protocol for Reliable Large-Scale Wireless Sensor Networks

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

Wireless sensor networks (WSNs) face a fundamental trade-off between energy efficiency, communication reliability, and transmission latency. Classical protocols such as PEGASIS achieve optimal energy efficiency through chain-based aggregation but suffer from O(n) transmission latency, rendering them unsuitable for real-time applications. Conversely, LEACH provides minimal latency but exhibits packet delivery ratio (PDR) degradation at scale.

This paper presents **AERIS** (Adaptive Environment-aware Routing for IoT Sensors), a lightweight hierarchical routing protocol designed to fill the gap between energy-optimal and latency-optimal approaches. Through comprehensive experiments across four channel environments with 30 independent seeds per configuration (seeds 42001–42030) and statistical validation (Welch's t-test), we demonstrate that AERIS achieves:

1. **Highest PDR (pdr_expected) among all tested baselines at 100 nodes** across indoor_office (0.974), indoor_factory (0.603), outdoor_urban (0.375), and outdoor_suburban (0.745) with n=30 seeds;
2. **Statistically significant improvement** over LEACH, PEGASIS, HEED, and TEEN in all four environments at 100 nodes (p < 0.001), and in 3/4 environments (indoor_factory, outdoor_urban, outdoor_suburban) across all tested scales up to 1000 nodes (n=60, Holm-Bonferroni corrected p < 0.05);
3. **Deployability** on commodity WSN hardware (23KB memory, lightweight rule-based decision logic without neural inference).

**Honest Assessment**: Under the evaluated four-environment setup (100 nodes, 300 rounds, 10 dBm, n=30), AERIS achieves the highest PDR but module contributions are environment-dependent: Gateway provides significant gains in 3/4 environments, while CAS does not provide a consistent positive effect. At larger scales (200–1000 nodes, n=60), AERIS maintains first rank in indoor_factory, outdoor_urban, and outdoor_suburban, but PEGASIS surpasses AERIS in indoor_office (e.g., 0.999 vs 0.990 at 1000 nodes, Hedges' g = −6.36). AERIS is positioned for **multi-environment WSN deployments** where reliability across diverse channel conditions is critical. All source code and experimental configurations are released as open source to ensure reproducibility.

**Keywords**: Wireless Sensor Networks; Reliable Routing; Hierarchical Protocol; Real-Time IoT; Energy-Reliability Trade-off

---

## 1. Introduction

### 1.1 Background and Motivation

Wireless sensor networks (WSNs) have emerged as a cornerstone technology for the Internet of Things (IoT), enabling ubiquitous sensing and data collection in applications ranging from environmental monitoring to industrial automation [1, 2]. Given the battery-powered nature of sensor nodes and often inaccessible deployment environments, energy efficiency has traditionally been the paramount design objective for WSN routing protocols [3, 4].

Over the past two decades, classical protocols such as LEACH (Low-Energy Adaptive Clustering Hierarchy) [3], PEGASIS (Power-Efficient GAthering in Sensor Information Systems) [4], and HEED (Hybrid Energy-Efficient Distributed clustering) [5] have established the foundation for energy-efficient routing through cluster-based aggregation and multi-hop transmission strategies.

However, as WSNs expand into **real-time applications**—industrial process monitoring, medical vital sign tracking, and emergency alert systems—a critical limitation has emerged: **transmission latency**.

### 1.2 The Latency Problem

PEGASIS and similar chain-based protocols achieve energy efficiency by passing data sequentially through a chain of nodes. While this minimizes individual transmission distances, it introduces **O(n)** end-to-end latency, where n is the number of nodes. As network scale grows, this sequential delay becomes a bottleneck for applications requiring timely data delivery.

**Table 1: PDR Comparison Across Environments (100 nodes, 300 rounds, 10 dBm, n=30)**

Data source: `env_sensitivity_20260207_205317.json`

| Protocol | indoor_office | indoor_factory | outdoor_urban | outdoor_suburban |
|----------|--------------|----------------|---------------|-----------------|
| **AERIS** | **0.974±0.005** | **0.603±0.026** | **0.375±0.035** | **0.745±0.019** |
| LEACH | 0.554±0.040 | 0.161±0.021 | 0.055±0.013 | 0.270±0.027 |
| PEGASIS | 0.908±0.017 | 0.193±0.026 | 0.054±0.012 | 0.338±0.033 |
| HEED | 0.937±0.008 | 0.233±0.026 | 0.064±0.012 | 0.422±0.031 |
| TEEN | 0.822±0.004 | 0.311±0.025 | 0.120±0.018 | 0.475±0.024 |

### 1.3 Research Gap

Existing protocols occupy distinct regions in the latency-energy-reliability design space:

- **Energy-optimal region (PEGASIS)**: Achieves 50% energy reduction but with O(n) latency unsuitable for real-time applications.
- **Latency-optimal region (LEACH)**: Achieves O(1) latency but with lower PDR under harsh channel conditions.
- **Balanced region (HEED)**: Moderate performance across all metrics without excelling in any dimension.

**The Gap**: No existing lightweight protocol simultaneously provides:
1. Highest PDR among tested baselines in all four evaluated environments at 100 nodes (n=30), and in 3/4 environments across scales up to 1000 nodes (n=60)
2. Environment-adaptive routing with module-level configurability
3. Deployability on commodity hardware (10KB RAM)

### 1.4 Proposed Solution: AERIS

This paper presents AERIS (Adaptive Environment-aware Routing for IoT Sensors), a lightweight hierarchical routing protocol designed to fill this gap. AERIS employs a three-layer architecture:

1. **Context-Adaptive Switching (CAS)**: Selects optimal transmission mode based on real-time network conditions.
2. **Skeleton Backbone**: Establishes stable hierarchical paths using PCA-based principal axis analysis.
3. **Gateway Coordination**: Deploys strategic relay nodes to reinforce critical paths.

### 1.5 Contributions

This paper makes the following contributions:

**C1. Multi-Environment Reliability Leadership**: We present AERIS, which achieves the highest PDR among five tested protocols (LEACH, PEGASIS, HEED, TEEN) across all four evaluated channel environments at 100 nodes (n=30, Welch's t-test p < 0.001 in all cases). Scalability experiments (100–1000 nodes, n=60) confirm this advantage in 3/4 environments; in indoor_office, PEGASIS maintains higher PDR at scale (Section 6).

**C2. Evidence-Based Module Analysis**: We provide transparent ablation analysis showing that module contributions are environment-dependent: Gateway provides statistically significant PDR gains in 3/4 environments (p < 0.02), while CAS contribution is mixed across environments.

**C3. Reproducible Evaluation Framework**: All source code, data processing scripts, experimental configurations, and raw result JSON files with full provenance metadata (git commit, script SHA256, config hash) are released as open source to enable independent verification.

**C4. Application-Specific Recommendations**: Based on comprehensive experiments (30 independent seeds per configuration across four environments), we provide clear guidelines for protocol selection across different application requirements.

### 1.6 Honest Limitations

We explicitly acknowledge the following limitations:

1. **Module contributions are environment-dependent**: Gateway improves PDR significantly in 3/4 environments but is neutral in indoor_office. CAS does not provide a consistent positive effect and is significantly negative in outdoor_urban (p=0.002).

2. **Skeleton and Safety modules show no measurable marginal effect** under the current evaluation setup (100 nodes, 300 rounds, 10 dBm).

3. **Results are from a Python simulator**: NS-3 alignment is trend-level only; hardware validation is not yet available.

4. **Scope**: The 100-node results (n=30) apply to 200×200m area, 300 rounds, 10 dBm, dropout 0.0, uniform random deployment.

5. **Indoor_office at scale**: Scalability experiments (100–1000 nodes, n=60) show PEGASIS surpasses AERIS in indoor_office at all tested node counts ≥200 (e.g., 0.999 vs 0.990 at 1000 nodes, Hedges' g = −6.36). AERIS's multi-environment advantage holds in the other three environments across all scales.

### 1.7 Target Applications

AERIS is designed for applications requiring high reliability across diverse channel environments. At 100 nodes (n=30), AERIS achieves the highest PDR among all tested baselines in all four environments. At larger scales (n=60), AERIS maintains this advantage in indoor_factory, outdoor_urban, and outdoor_suburban, making it suitable for deployments where channel conditions vary or are uncertain.

**AERIS is NOT recommended for**:
- Scenarios where only indoor_office conditions apply (PEGASIS achieves higher PDR at all tested scales ≥200 nodes)
- Deployments where energy efficiency is the sole concern (energy trade-offs are not yet characterized in publication-tier evidence)

### 1.8 Paper Organization

The remainder of this paper is organized as follows:

- **Section 2** reviews related work in WSN routing protocols with emphasis on latency-energy trade-offs.
- **Section 3** presents the system model and preliminary analysis linking experimental findings to design decisions.
- **Section 4** details the AERIS protocol design with complexity analysis.
- **Section 5** describes the experimental setup and statistical methodology.
- **Section 6** presents comprehensive results with honest comparison to baselines.
- **Section 7** discusses limitations, practical implications, and protocol selection guidelines.
- **Section 8** concludes with a summary of contributions and future directions.

---

## References (Section 1)

[1] I. F. Akyildiz, W. Su, Y. Sankarasubramaniam, and E. Cayirci, "Wireless sensor networks: A survey," *Computer Networks*, vol. 38, no. 4, pp. 393–422, 2002.

[2] J. Yick, B. Mukherjee, and D. Ghosal, "Wireless sensor network survey," *Computer Networks*, vol. 52, no. 12, pp. 2292–2330, 2008.

[3] W. R. Heinzelman, A. Chandrakasan, and H. Balakrishnan, "Energy-efficient communication protocol for wireless microsensor networks," in *Proc. 33rd Annual Hawaii International Conference on System Sciences (HICSS)*, 2000.

[4] S. Lindsey and C. S. Raghavendra, "PEGASIS: Power-efficient gathering in sensor information systems," in *Proc. IEEE Aerospace Conference*, 2002.

[5] O. Younis and S. Fahmy, "HEED: A hybrid, energy-efficient, distributed clustering approach for ad hoc sensor networks," *IEEE Trans. Mobile Comput.*, vol. 3, no. 4, pp. 366–379, 2004.

