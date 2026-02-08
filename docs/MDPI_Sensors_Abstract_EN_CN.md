# ISJ Abstract (EN) and 中文摘要（CN）

## Abstract (EN)
Background: Wireless sensor networks (WSNs) must deliver reliable data under dynamic interference and environmental variability while preserving energy and lifetime; classical clustering/chain protocols degrade when link quality and traffic fluctuate.

Objective: Present AERIS (historical naming "Enhanced AERIS/EASR" unified here as AERIS), an environment‑adaptive routing framework that couples predictive environment mapping with safety‑constrained, entropy‑ and fuzzy‑logic–guided cluster‑head (CH) selection and hybrid coordination.

Methods: We replay real Intel Lab traces across multiple topologies (uniform, corridor, grid) under a calibrated energy model and log‑normal shadowing channels; AERIS integrates fuzzy‑logic CH selection and PSO‑based path optimization with a lightweight coordination layer. Performance is evaluated against LEACH/PEGASIS/HEED using total energy, network lifetime, energy‑efficiency ratio and end‑to‑end PDR. Statistical inference uses two‑sided Welch’s t‑tests with Holm–Bonferroni adjustment, bootstrap 95% confidence intervals, and effect sizes; ablations and sensitivity analyses probe component contributions and stability.

Results: AERIS reduces total energy by 7.9% versus PEGASIS over 500 rounds while maintaining 100% node survival; energy‑efficiency improves by 8.6% packets/J. Improvements are statistically significant with large effect sizes; overhead remains <4% even at 100‑node scale, and convergence is stable (≈25–30 PSO iterations). Robustness holds across deployment topologies and parameter sweeps.

Conclusions: Prediction‑informed routing with principled statistics and lightweight cross‑layer coordination yields dependable gains in realistic settings, offering a practical path to energy‑efficient and reliable WSN operation. Artifacts (code, logs, scripts) and vector figures enable transparent, reproducible regeneration of results.

Keywords: Wireless Sensor Networks; Environment Mapping; Robust Routing; Energy Efficiency; Reliability; Statistical Significance; Uncertainty; Reproducibility

---

## 中文摘要（CN）
我们提出 AERIS（环境自适应骨架路由；历史命名为“Enhanced AERIS/EASR”，本文统一为 AERIS）：一种面向环境感知且具鲁棒性的 WSN 路由框架，将预测型环境映射与具安全约束的熵/模糊逻辑簇首选择有机融合。基于 Intel 实验室真实轨迹与多类拓扑，框架结合经典与学习式预测以前瞻性刻画业务与信道变化，并以不确定性认知驱动自适应决策与严格统计评估。相较基线与在消融验证中，AERIS 在提升投递可靠性、降低总能耗与推迟节点失效方面呈现一致优势，统计显著性采用双侧 Welch 检验并以 Holm–Bonferroni 进行多重比较校正；置信区间通过 bootstrap 估计（报告 95% CI），必要时给出效应量。灵敏度、跨拓扑显著性与不确定性网格分析表明其在非平稳与不利条件下仍保持稳定。我们同时以 SVG-only 的出版级矢量出图与最小可复现实验流程规范开源产物。结果显示：面向预测的鲁棒路由与严格统计验证能够在真实场景下实现能效与可靠性的双提升，为构建高效可靠的 WSN 提供了可行路径。

关键词：无线传感器网络；环境映射；鲁棒路由；能效；可靠性；统计显著性；不确定性和复现性