## MDPI Sensors Remediation Plan

> 目标：统一指标与统计口径、补齐诊断与复现材料，在下次投递前把接受概率提升至 60% 左右。每个任务完成后务必在 PR/日志中记录命令与输出路径，避免遗忘。

### 1. 指标与结论收敛
- [x] 审核正文所有跨协议比较，只保留 `端到端 PDR`、`总能耗 (J)`、`J/packet` 三个主指标；`跳级 PDR` 仅在诊断段落出现。
- [ ] 将“最佳”“显著支配”等措辞替换为“demonstrates reproducible trade-off”等中性表达。
- [x] 在 Results 中新增“Common Baseline Setup”段，统一描述包长、能耗模型、初始能量、随机种子等共用配置。

### 2. 统计嵌入与图表
- [x] 扩写 `scripts/compute_dynamic_significance.py` / `compute_monte_carlo_stats.py`，输出 Holm–Bonferroni / BH-FDR 纠正后的 p 值。
- [x] 生成 Gardner–Altman 或 Cliff’s delta 图（新增脚本），写入 `paper_dynamic_effect_sizes.pdf` 并在正文引用。
- [x] 在 LaTeX 中插入统计表：样本量、t 值、p 值、效应量、校正方式；图注说明“5 replicates, seed stride 500”。

### 3. 性能诊断与瓶颈解释
- [x] 修改 AERIS 协议核心，输出 `cluster_to_ch_*` 与 `ch_to_bs_*` 诊断字段（见 `additional_metrics` 与 `round_statistics` 中新增条目）。
- [x] 扩展日志以包含 `cluster_radius_mean`、`ch_to_bs_distance_mean`、`gateway_link/uplink_attempts/successes` 等信息。
- [x] 新增诊断绘图脚本（如 `plot_dynamic_phase_breakdown.py`、`plot_dynamic_diagnostics.py`），并在正文引用 Figure~7–8 解释动态与大规模场景的瓶颈。
- [x] 根据诊断给出明确改进计划（例如提高 skeleton 密度或多网关冗余），写入 Discussion/Conclusion。

### 4. Skeleton / Gateway 参数扫描
- [x] 扩展 `run_gateway_sweep.py`：覆盖骨干密度、gateway 权重、冗余概率等二维网格；输出热图 (`paper_gateway_heatmap.pdf`)。
- [x] 在 Supplement 添加最优配置表和敏感性曲线，正文引用“参数扫描表明……”
- [x] **多基站/多 gateway 计划**：在 Uniform-300/500 上设置目标——CH$\rightarrow$BS 成功率（Round-level）提升至 $\ge 0.40$（300）与 $\ge 0.20$（500）；探索方案包括 (i) 增加 gateway 数量 $k \in \{2,3,4\}$，(ii) 引入 2 个 BS（位于对角），(iii) skeleton 半径减半。实验顺序：先单 BS 多 gateway，后固定 gateway 密度测试双 BS。**结果**：双基站配置（`results/gateway_sweep_uniform300_dualbs_k468.json`、`results/gateway_sweep_uniform500_dualbs_k468.json`）已将 CH$\rightarrow$BS 成功率分别抬升至 0.50/0.48，端到端 PDR 仍在 0.10/0.066，需配合 skeleton 调参；进一步的 gateway 限额实验（`results/gateway_sweep_uniform{300|500}_dualbs_limit{1..4}.json`）显示 $L_{gw}=1$ 时 Uniform-300 的 $\mathrm{PDR}_{e2e}$ 可达 0.105，Uniform-500 约 0.071，证实 gateway 拥塞是当前瓶颈。
- [x] **新增**：实现 gateway 并发上行/自适应限额。`NetworkConfig` 支持 `gateway_concurrency`、`gateway_limit_dynamic` 及窗口/阈值参数，AERIS 记录 `gateway_load_limit_active`、`gateway_concurrency_used`、`gateway_uplink_suppressed`。`scripts/run_gateway_sweep.py` 增加 `--gateway-concurrency`、`--gateway-limit-dynamic` 等 CLI，并在 JSON 中输出轨迹。
- [x] 使用并发 + 自适应限额在 Uniform-300/500 双 BS 场景跑 sweep，对比固定限额（Fig. S1）并在 Supplement / Discussion 中加入新图表与统计。

### 5. 命名与工程一致性
- [x] 清理仓库中残留的 `EEHFR` 命名/文件，统一改成 `AERIS_*`；README 增加“旧名迁移说明”。
- [ ] 更新 `Data Availability / Code Availability` 段，指向新的脚本路径和版本。

### 6. 复现元数据
- [x] 利用 `docs/reproduction_manifest.json` 自动生成“脚本/输入/种子表”（`python scripts/generate_reproduction_table.py` 输出 `docs/Reproduction_Table.md`），并在 Supplement 第 7 节引用。
- [x] 在 README / Reproducibility 段落中给出访问方式，说明如何刷新该表；后续在 Data Availability 中保持引用同步。

### 7. 执行顺序与验收
1. 统一指标 + 語句收敛（章节 1）  
2. 统计脚本与 LaTeX 嵌入（章节 2）  
3. 诊断日志与图表（章节 3）  
4. Skeleton/Gateway 扫描及热图（章节 4）  
5. 命名清理与复现元数据（章节 5、6）  
6. 最终全文审校 + 发表概率复评  

完成每一步后：  
- 在 `docs/Progress_Summary_2025.md` 记录命令/产物；  
- 更新本清单的复选框，并在 PR 中引用。  

### 附：统计/复现信息待插入位置
- **Intel replay段落（for_submission/final_paper.tex:334–312）**：需要写明样本量（五个 200 轮窗口）与 Holm--Bonferroni校正因子；计划在 Figure 2 图注加入“n=5 seeds, seed stride 500”。
- **50×100 场景段落（312 行）**：补充“端到端 PDR 值来自 Figure 3 中的 100-seed Monte Carlo 均值 ±95% CI”，并给出 Welch $t$ 结果。
- **动态场景表述（334–360 行）**：在文字和 Table~\ref{tab:dynamic_significance} 之间加入“$n=5$ replicates × 4 phases，总样本 20”，并注明 boxplot 图引用。
- **Large-scale 场景（397 行）**：加入“1000 rounds × 5 seeds”说明，并在图注提及能耗统计方式（J per packet）。
- **Supplementary**：在 `docs/Supplementary_Results.md` 新增一个表格列出每个脚本、输入 JSON、随机种子及输出图（来源 `docs/reference_metadata.json`）。  

上述插入点将在章节 2 任务实施时补全，以免遗漏。

### 进度快照（2025-11-11 19:25）

| 模块 | 完成度 | 说明 |
|---|---|---|
| 1. 指标与结论收敛 | 2/3 | 已完成指标统一与 Common Baseline 段落，仍需全局扫除“最佳/显著支配”类措辞。 |
| 2. 统计嵌入与图表 | 3/3 | 已完成脚本输出、正文统计表与 Gardner–Altman + Cliff’s δ 图；等待后续审阅。 |
| 3. 性能诊断与瓶颈解释 | 4/4 | 结论段已写入“提高 gateway 密度、多基站”路线，诊断闭环完成。 |
| 4. Skeleton/Gateway 扫描 | 3/3 | 多基站 sweep（Uniform-300/500）完成并写入 Supplement，接下来可聚焦 skeleton 半径扫描。 |
| 5. 命名与工程一致性 | 1/2 | README/Data Availability 已更新；仍需对 archive/老报告补充迁移指引。 |
| 6. 复现元数据 | 2/2 | Reproduction 表格与 README 引用已完成，无需额外动作。 |

> 下一执行批次聚焦任务 1–3，并在完成 Common Baseline Setup 后同步插入统计表格；随后展开多基站实验以兑现任务 4 的最后一项。
