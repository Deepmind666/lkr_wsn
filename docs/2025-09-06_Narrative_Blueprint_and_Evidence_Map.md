# 研究叙事蓝图与证据地图（Intel 环境映射 × AERIS/EASR 主线）

日期：2025-09-06  作者：Trae助理（全量可追溯记录）

## 0. 背景与问题陈述
在真实部署中，教材化的理想信道与抽象MAC常导致“仿真→落地”性能坍塌。我们研究的起点是：在现实化的802.15.4一致栈（含阴影衰落、同信道干扰、CSMA/CA退避与重传）下，是否可以通过“环境映射预测→协议关键决策”的闭环来稳定地改善端到端可靠性与能量寿命，而不依赖复杂或难以复现的重模型？

## 1. 可证伪主张（Falsifiable Claims）
- C1（闭环有效性）：在现实信道+真实流量回放下，环境映射驱动的协议闭环相较于“无预测/无闭环”的经典基线，能在端到端PDR上获得统计显著提升，同时不恶化能效（packets/J）。
- C2（稳健性与公平）：加入安全回退与寿命公平性协调后，长链路波动降低，节点余能分布更均衡，网络寿命分位数（P50/P90）上升；提升在多拓扑/多种子上统计显著。
- C3（现实一致评测）：在Intel Lab真实数据+现实化信道/能耗模型下得到的改进趋势，与合成拓扑与敏感性实验相互印证，跨分布迁移成立（非偶然）。
- C4（模型非依赖性）：闭环的主效应相对“时序模型复杂度”是一级影响；即使使用基础时序模型（如ETS/SARIMAX/LSTM），相对于无闭环的经典协议，收益依然成立。

注：原“主张三（严谨评测与可复现）”不单列为创新点，而是研究最低规范，置于方法论与复现章节。

## 2. 新颖性定位（相对现有工作）
- S1（系统层闭环整合）：以现实一致的802.15.4风格通道与能耗栈为“可见底”的基座，将环境映射输出闭环注入协议关键决策（簇首/网关/占空比/冗余），强调“预测→控制”的工程可落地路径。
- S2（安全回退×公平协同）：在闭环上叠加“PDR下限保障”的安全回退与寿命公平性约束，形成可解释、可调参、可证伪的稳定化机制组合。
- S3（跨分布验证）：真实回放（Intel）与多拓扑敏感性互证，配合效应量与多重比较控制，输出“趋势可迁移”的证据而非单点分数。

## 3. 证据地图（Evidence Map）
- 数据与现实化栈：
  - 通道模型：<mcfile name="realistic_channel_model.py" path="c:\Enhanced-AERIS-WSN-Protocol\src\realistic_channel_model.py"></mcfile>
  - 能耗模型：<mcfile name="improved_energy_model.py" path="c:\Enhanced-AERIS-WSN-Protocol\src\improved_energy_model.py"></mcfile>
  - Intel数据加载：<mcfile name="intel_dataset_loader.py" path="c:\Enhanced-AERIS-WSN-Protocol\src\intel_dataset_loader.py"></mcfile>
- 闭环与机制：
  - 整合主线：<mcfile name="integrated_enhanced_eehfr.py" path="c:\Enhanced-AERIS-WSN-Protocol\src\integrated_enhanced_eehfr.py"></mcfile>
  - 网关/选择器：<mcfile name="gateway_selector.py" path="c:\Enhanced-AERIS-WSN-Protocol\src\gateway_selector.py"></mcfile>、<mcfile name="cas_selector.py" path="c:\Enhanced-AERIS-WSN-Protocol\src\cas_selector.py"></mcfile>
  - 公平性指标：<mcfile name="fairness_metrics.py" path="c:\Enhanced-AERIS-WSN-Protocol\src\fairness_metrics.py"></mcfile>
- 结果产物（现有）与图：
  - 经典/学习基线JSON：
    - <mcfile name="intel_ets_envmap_compare.json" path="c:\Enhanced-AERIS-WSN-Protocol\results\intel_ets_envmap_compare.json"></mcfile>
    - <mcfile name="intel_lstm_envmap_compare.json" path="c:\Enhanced-AERIS-WSN-Protocol\results\intel_lstm_envmap_compare.json"></mcfile>
    - <mcfile name="intel_tcn_envmap_compare.json" path="c:\Enhanced-AERIS-WSN-Protocol\results\intel_tcn_envmap_compare.json"></mcfile>
    - SARIMAX（运行中，完成后同目录写出）
  - 制图脚本：<mcfile name="plot_paper_figures.py" path="c:\Enhanced-AERIS-WSN-Protocol\scripts\plot_paper_figures.py"></mcfile>
  - 图表目录：<mcfile name="results/plots" path="c:\Enhanced-AERIS-WSN-Protocol\results\plots\"></mcfile>、策展：<mcfile name="results/plots_curated" path="c:\Enhanced-AERIS-WSN-Protocol\results\plots_curated\"></mcfile>
- 统计与显著性：
  - 多重检验与效应量：<mcfile name="compute_effect_sizes.py" path="c:\Enhanced-AERIS-WSN-Protocol\scripts\compute_effect_sizes.py"></mcfile>、<mcfile name="run_stats_multitest.py" path="c:\Enhanced-AERIS-WSN-Protocol\scripts\run_stats_multitest.py"></mcfile>
  - Intel显著性：<mcfile name="run_significance_intel.py" path="c:\Enhanced-AERIS-WSN-Protocol\scripts\run_significance_intel.py"></mcfile>

证据到主张映射：
- C1：比较JSON（经典协议/闭环）→ 端到端PDR与packets/J → Welch t与效应量
- C2：fairness指标分布/尾部风险、寿命分位数、失效轨迹对比 → 显著性与置信区间
- C3：Intel回放 vs 合成拓扑敏感性/鲁棒性 → 方向一致性与显著性
- C4：ETS/SARIMAX/LSTM/TCN均显示闭环主效应 > 模型复杂度效应（消融+统计）

## 4. 实验设计与统计规范（严谨性而非创新点）
- 多随机种子、多拓扑；显著性（Welch t/非参检验备选）、Holm–Bonferroni校正；报告效应量（Hedges g）与95% CI；
- 指标统一：端到端PDR（非hop级）、能效（packets/J）、寿命（首次死亡/50%死亡/全网寿命），并给出采样/聚合周期；
- 图表规范：默认SVG，标注样本量n、均值±CI、统计显著性标识；结果与脚本一一可追溯。

## 5. 提升创新度的可执行增强（如需抬高“方法创新”高度）
- A1 理论化安全回退：将安全回退建模为“CBF式PDR下限约束”，给出在某噪声/负载条件下维持PDR≥τ的充分条件与代价上界；结合<mcfile name="theoretical_analysis_validator.py" path="c:\Enhanced-AERIS-WSN-Protocol\src\theoretical_analysis_validator.py"></mcfile>验证。
- A2 置信度门控闭环：引入环境预测置信度/不确定性加权，触发强回退或保守策略以避免过拟合；在JSON与图中显式呈现“置信度-收益曲线”。
- A3 公平性保证：给出“能量-路径分配”的混合策略在一定拓扑稀疏度下的均衡性下界或失衡上界，配合<mcfile name="fairness_metrics.py" path="c:\Enhanced-AERIS-WSN-Protocol\src\fairness_metrics.py"></mcfile>实证。

## 6. 与命名/叙事对齐
- “AERIS”为历史命名，不视为对标基线；论文叙事可采用更规范的体系化名称（如EASR/AERIS）或保留工程名并在文中统一释义，二选一，以免审稿困惑。

## 7. 风险与有效性威胁（Threats to Validity）
- 外部效度：Intel数据场景偏差；对策：合成拓扑与参数敏感性互证；
- 构念效度：指标口径差异（端到端 vs hop级）；对策：统一定义并提供脚本；
- 结论效度：单次分数与偶然性；对策：多种子+显著性+效应量+多重比较控制；
- 实施威胁：依赖某个模型实现细节；对策：C4主张与多模型旁证。

## 8. 文献阅读与记录（执行计划）
- 参考条目：在<mcfile name="refs_ISJ_2020_2025.md" path="c:\Enhanced-AERIS-WSN-Protocol\docs\refs_ISJ_2020_2025.md"></mcfile>中建立了“25条核心文献”结构化模板与清单（含主题桶与证据标签）。
- 输出要求：每条按模板补充“方法要点/平台/指标/结果/局限/映射/可借鉴点”，并显式标注其支撑/反例C1–C4的证据关系。

## 9. 立即执行的里程碑
- M1（24小时内）：补齐Intel经典时间序列对比（待SARIMAX写出）并导出SVG，运行显著性与效应量脚本，生成统计表—映射到C1/C4。
- M2（48小时内）：完成25篇文献的结构化注释与C1–C4证据对照表；
- M3（72小时内）：输出公平性与寿命分布图，补做鲁棒性与敏感性，完成Threats章节草稿；
- 可选增强（与您确认）：推进A1/A2中至少一项形成“可衡量的方法学增量”。