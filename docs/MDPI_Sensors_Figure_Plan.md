# MDPI Sensors Figure Storyboard & Experiment Matrix (B-tier)
 
目标：面向 **Sensors（MDPI）** 的可发表质量，建立“主张 → 指标 → 场景/参数 → 统计检验 → 最终图（主文 6–8 张 + Supplementary） → 脚本/数据源”的一一映射，并补齐“指标/特征选择的先验证据链”（先验实验 + 理论/统计支撑）。
 
## 0. 约束与验收口径（对齐 Sensors）
 
- **主文图数量**：目标 6–8 张（包含方法流程图）；其余放 Supplementary。
- **输出格式**：优先 `SVG`（文字保持 text，`svg.fonttype=none`），同时导出同名 `PDF`。
- **统计口径（默认）**：
  - **CI**：bootstrap 95% CI（在图中标注 `n`）。
  - **显著性**：Welch t-test（或必要时非参），多重比较主用 **BH-FDR**，主文可点名 Holm–Bonferroni 作为稳健核对。
  - **效应量**：Cohen’s d / Cliff’s δ（至少一类）+ 方向解释。
- **可靠性指标优先级**：主文优先 **端到端 PDR**；如动态场景暂需用 hop-level PDR，必须在图注写清并给出“端到端缺失原因与修复计划/已修复版本”。
 
## 1. 可证伪主张（Claims → Figures）
 
- **C1（Trace-calibrated 价值）**：Intel trace replay 下，AERIS 相对经典协议在端到端可靠性与能效上形成可复现的优势/权衡（CI + 纠正检验 + 效应量）。
- **C2（机制与可解释诊断）**：性能变化可由可观测诊断量解释（例如 cluster→CH、CH→BS、gateway 争用/限额、CAS 模式占比、安全触发频率），并能定位瓶颈。
- **C3（跨拓扑/参数鲁棒性）**：在多拓扑与参数扫描中，优势/局限的方向一致（敏感性与稳健性互证）。
- **C4（MCU-grade 可部署性）**：决策延迟/内存/复杂度满足 MCU 级约束，并与更重的 ML 方案形成可量化差异。
 
## 2. 主文 Figure Storyboard（建议版：7 张）
 
> 注：Fig 编号为“建议编号”，最终以 LaTeX 编号为准；每张图都要求在图注中写清 `n / CI / 校正方法 / 数据源 JSON`。
 
### Fig 1. Method / Coordination Stack（保留你的流程图）
- **信息点**：round pipeline、CAS/skeleton/gateway/safety/fairness 的数据流与钩子位置。
- **输入/输出**：`for_submission/AERIS_flowchart.pdf`（保持原设计，不在此任务中重画）。
 
### Fig 2. Intel Replay：端到端 PDR × Energy（主结论图）
- **场景/数据**：Intel replay（多窗口/多 replicate）。
- **图形**：多面板柱状/点估计 + 95% CI + 显著性标记；必要时补 Gardner–Altman（差值+CI）。
- **数据源**：`results/intel_baselines_all.json`（及统计表 `results/significance_compare_intel*.json`）。
- **脚本**：`scripts/run_intel_baselines_all.py` → `scripts/plot_paper_figures.py`
- **对应主张**：C1。
 
### Fig 3. 合成基准（50×100 Monte Carlo）：分布/效应量视角
- **场景/数据**：Uniform 50 nodes，100 seeds（0–99）。
- **图形**：PDR 与能耗的分布（box/violin/ECDF）+ 95% CI；强调“可复现分布而非单点均值”。
- **数据源**：`results/monte_carlo_uniform50.json` + `results/for_submission/monte_carlo_stats.md`
- **脚本**：`scripts/run_monte_carlo_uniform.py` → `scripts/compute_monte_carlo_stats.py` → `scripts/plot_*`（统一出口）
- **对应主张**：C1（跨分布的第二证据）+ C3（基础鲁棒性）。
 
### Fig 4. Multi-topology：AERIS-E vs AERIS-R（跨拓扑稳健性）
- **场景/数据**：uniform/corridor 多拓扑（固定 rounds），多 seeds（目标 ≥20；现有若不足则补跑）。
- **图形**：按拓扑分组的 PDR–Energy（CI）+ 右侧能耗（CI）或 Pareto 前沿（可选）。
- **数据源**：`results/compare_multi_topo.json` + `results/significance_compare_multi_topo_50x200.json`
- **脚本**：`scripts/run_compare_multi_topo.py` → `scripts/run_significance_multi_topo.py` → `scripts/plot_paper_figures.py`
- **对应主张**：C3。
 
### Fig 5. Dynamic Stress Tests（合并为 1 张多行面板）
- **场景/数据**：corridor phase shift / moving BS / random dropout（每个 level/phase 多 replicates）。
- **图形**：3×2 或 3×1 面板（PDR 与 energy 的 time-series/phase summary）+ 同一色板；避免 3 张图拆散叙事。
- **数据源**：`results/dynamic_*_compare_reps.json`
- **脚本**：`scripts/run_dynamic_*_compare.py` → `scripts/plot_dynamic_comparisons.py`（或统一入口）
- **对应主张**：C3（边界条件）+ Scope（不夸大）。
 
### Fig 6. Bottleneck Diagnostics（把“为什么会这样”讲清楚）
- **场景/数据**：从 dynamic 与 large-scale/dual-BS sweeps 中抽取诊断量。
- **图形**：PDR breakdown（cluster→CH、CH→BS、end-to-end）+ gateway limit/concurrency 的可视化（条形/热图二选一，另一张放 Supplementary）。
- **数据源**：`results/large_scale_long*.json`、`results/gateway_sweep_uniform*_dualbs_*.json`
- **脚本**：`scripts/plot_pdr_breakdown_diagnostics.py`、`scripts/plot_gateway_limit_heatmap.py`、`scripts/plot_gateway_concurrency_heatmap.py`
- **对应主张**：C2。
 
### Fig 7. MCU-grade Evidence（决策延迟分布 + 复杂度/资源）
- **图形**：决策时间 ECDF/box（p50/p95/p99）+ scaling（node/CH 数变化）或配套 Table（内存/训练需求）。
- **数据源**：`results/benchmark_decision_time.json`、`results/inference_bench.json`
- **脚本**：`scripts/benchmark_decision_time.py`（生成 JSON）+ `scripts/plot_scalability_aeris.py`（或新 plot）
- **对应主张**：C4。
 
## 3. Supplementary（建议清单）
 
- **S1**：全 pairwise 显著性矩阵（BH-FDR / Holm）+ 效应量热图（Intel、multi-topo）。
- **S2**：Ablation（去掉 CAS/skeleton/gateway/safety/fairness）对 PDR/Energy 的影响（n≥20）。
- **S3**：安全参数 trade-off（`θ, T, p_r, ΔP`）对均值与尾部风险（p05）的影响（risk-control 视角）。
- **S4**：Gateway sweep（k、w_dist、limit、concurrency）全热图 + 最优点与目标线（PDR target lines）。
- **S5**：更多拓扑族（cluster/obstacle-like）与更多 traffic tiers（低/中/高），用于外部效度。
 
## 4. 实验矩阵（B-tier：可并行 32）
 
| 维度 | 取值（建议） | 复现数（建议） | 产出 |
|---|---|---:|---|
| Intel replay windows | 200-round non-overlap windows | n=20 windows（现有若为 5 则补） | Fig 2 + S1 |
| Uniform Monte Carlo | N=50/100/200 | n=100 seeds/scale | Fig 3 + S5 |
| Multi-topology | uniform / corridor / cluster / obstacle-like | n=20 seeds/topology | Fig 4 + S1 |
| Dynamic stress | shift / moving BS / dropout | n=20（phase×rep 组合） | Fig 5 + S1 |
| Large-scale | N=300/500/1000 | n=20 seeds/scale（优先 300/500） | Fig 6 + S5 |
| Sensitivity | k, limit, concurrency, θ/T/p_r/ΔP | 网格 × n=10–20 | S3/S4 |
| MCU-grade | decision time, memory proxy | n=1000 iterations（per component） | Fig 7 |
 
## 5. “指标/特征”的先验证据链（必须补齐）
 
- **E0（环境→链路）**：证明湿度/温度驱动的信道退化与链路质量统计相关（相关/回归/置换检验）。
- **E1（CAS 特征有效性）**：用可解释模型/消融展示特征对模式选择的增益（对照随机/删特征）。
- **E2（安全阈值的风险控制）**：用 Beta–Binomial/分位数指标证明阈值设置能控制“坏轮次”风险，并量化代价（能耗）。
- **E3（网关争用/负载不均衡）**：用 limit/concurrency sweep + 诊断量证明瓶颈来自争用而非单链路衰落。
- **E4（MCU 约束）**：延迟分布（p95/p99）+ 复杂度随规模的增长曲线；对比 ML 推理延迟/内存。
 
## 6. 当前缺口（从仓库现状反推）
 
- **图表数量与叙事不一致**：当前 paper 已包含多张结果图；需按上面的 7 张主文图合并/重排。
- **复现数不足**：Intel windows / dynamic replicates / multi-topology seeds 需提升到 B-tier 指标（默认 n≥20）。
- **图质量告警**：`figure_validation_report.md` 显示大量 SVG 宽度 < 1200；后续需要统一画布与导出尺寸。