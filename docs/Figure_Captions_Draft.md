# 图注草稿（Sensors / ISJ）

- 文件 `results/publication_figures/paper_intel_sig_combined.svg`
  - Intel – AERIS-E 与 AERIS-R 显著性组合图（PDR 与能耗，mean ± 95% CI）。页脚包含非参数统计摘要：Mann–Whitney U、AUC、Cliff’s δ、Cohen’s d。PDR坐标系限定于 [0, 1.05]，能耗以焦耳计；误差线为基于重复实验的95%置信区间。

- 文件 `results/publication_figures/paper_intel_ablation_energy.svg`
  - Intel – 消融实验：能耗柱形图（mean ± 95% CI）。各方法按能耗排序，误差线为95%CI。图内数值标签显示均值，页脚注明统计解释与CI含义。

- 文件 `results/publication_figures/paper_intel_ablation_pdr.svg`
  - Intel – 消融实验：PDR柱形图（mean ± 95% CI）。坐标系限定于 [0, 1.05]，误差线为95%CI。图内数值标签显示均值，页脚注明统计解释与CI含义。

- 文件 `results/publication_figures/paper_intel_energy_minimal.svg`
  - Intel – 极简能耗散点图（AERIS-E vs AERIS-R）。只展示方法标签与数值点，无误差线，适用于正文内的轻量级对照展示。

- 文件 `results/publication_figures/paper_intel_pdr_minimal.svg`
  - Intel – 极简PDR散点图（AERIS-E vs AERIS-R）。坐标限定于 [0, 1.05]，只展示方法标签与数值点，无误差线，适用于正文内的轻量级对照展示。

- 文件 `results/Sensors_figures/gpu_dml_smi.png`
  - GPU负载（nvidia-smi）：显示GPU总利用率与显存使用百分比的时间序列曲线。用于补充实验期间的计算资源占用情况，支持方法段中对计算开销的描述。

- 文件 `results/Sensors_figures/gpu_dml_engine.png`
  - GPU引擎利用率（Engine sum）：显示SM/拷贝等引擎占用的总和百分比随时间的曲线。用于辅助判断推理与数据搬运阶段的资源分配与瓶颈。

注：若需英文版图注或更改术语（如“AERIS-E/R”到“Energy/Robust”），可在排版阶段统一替换；所有图均采用出版模式风格（Times 字体、统一色板、SVG/PDF双格式）。