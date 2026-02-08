# EASR（面试版）一页纸（历史命名：Enhanced AERIS/AERIS）

一句话：在复杂室内电磁环境中，通过“环境预测 × 软决策 × 动态网关”的三重协同，使WSN在能耗与端到端可靠性之间实现按需自适应的Pareto优化。

- 项目定位：研究生入学面试优质课程项目（工程可复现 + 学术可信）
- 技术栈：Python 3.12，NumPy/Matplotlib；路由：EASR/LEACH/PEGASIS/HEED；时序预测：PatchTST、DLinear、TCN、LSTM；统计：Welch t 检验、95% CI

核心创新（3×3主打法）
- 环境映射预测：用PatchTST/DLinear对RSSI/干扰强度进行短期预测，提前规避“脆弱时隙”与弱链路
- 软决策策略：熵权/模糊融合多指标（剩余能量、链路稳定、拥塞风险、预测置信），实现“强鲁棒/强能效”两种模式的在线切换
- 动态网关编排：多网关候选集合自适应选择与冗余控制（λ_uncertainty × conf_threshold），在安全冗余和能耗之间平衡

系统设计要点
- 双目标：min Energy, max End-to-End PDR（形式化目标与约束已在源码中落实）
- 决策流程：拓扑感知 → 环境预测 → 软决策打分 → GW/路径选择 → 安全冗余 → 运行监控
- 复杂度：对比LEACH/PEGASIS的附加开销可控；关键路径已在实验中给出敏感性分析

实验与结果证据（图见 results/plots_curated）
- Intel 室内实验（200轮）：EASR-E（能效）与EASR-R（鲁棒）在能耗与端到端PDR上均优于经典基线（LEACH/PEGASIS/HEED）
- 显著性与置信区间：基于50~100并行复现，提供Welch t与95% CI条形图与组合图
- 消融：移除CAS/FAIR/GW/SAFETY模块的能耗与PDR变化，定位贡献来源
- 敏感性：初始能量E0、包大小P、网关数G的影响曲线（含CI带）
- 不确定性网格：λ_uncertainty × conf_threshold对PDR与能耗的双热图

关键图表清单（部分）
- Intel：AERIS Energy/PDR（paper_intel_energy.svg / paper_intel_pdr.svg）
- EASR vs Baselines（paper_intel_baselines_energy.svg / paper_intel_baselines_pdr.svg）
- 预测环境 vs 保守映射（paper_intel_predenv_energy.svg / paper_intel_predenv_pdr.svg）
- 组合显著性（paper_intel_sig_combined.svg）；多拓扑显著性（paper_multi_topo_sig_*）
- 敏感性（paper_intel_sens_*）；消融（paper_intel_ablation_*）；不确定性网格（paper_uncertainty_grid.svg）

复现与演示
- 生成图：Windows: 先安装Python matplotlib；或在WSL中运行：
  - python3 -m pip install --user matplotlib numpy
  - python3 scripts/plot_paper_figures.py
  - python3 scripts/curate_figures.py（输出到 results/plots_curated 与 publication_figures）
- 面试演示顺序：Sig Combined → Baselines 对比 → PredEnv 对比 → Ablation/Sensitivity → Uncertainty Grid

面试高频问答要点（速答模板）
- Q：为何预测环境能提升PDR？A：提前绕开高干扰时隙与弱链路，降低重传；配合软决策与动态GW，稳定性显著提升
- Q：如何控制能耗上升？A：软决策中引入能耗惩罚与冗余阈值，显著性图显示在相同可靠性目标下能耗更低
- Q：鲁棒性如何保证？A：不确定性调参（λ、阈值）+ 安全冗余上限；多拓扑显著性检验显示提升具统计意义
- Q：复杂度与可落地性？A：预测窗口与候选GW数量受控；在Mesh/LoRa场景可复用，代码已提供图形与结果产出

落地场景与扩展
- 工业物联网、智慧建筑、仓储物流；可与联邦/边缘学习组合，结合位置感知和能量采集进一步提升

备注
- 更名策略：图中显示“EASR-*”友好标签，数据键仍保留AETHER_*，已通过QA扫描避免论文冲突