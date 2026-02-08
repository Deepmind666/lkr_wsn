# 方法免责声明（统计与数据说明）

- 数据来源与场景一致性
  - Intel Lab 场景：区域大小约 `40.0 × 30.0`，节点数 `54`，环境映射为 `humidity_percentiles → humidity_ratio (33/50/66)`；运行时含 `energy` 与 `robust` 两种配置（各自种子、公平性参数、CAS/骨架/网关等开关状态已在配置中注明）。
  - 对比主体为 AERIS-E（偏能效）与 AERIS-R（偏鲁棒性），所有显著性图均按同一场景与重复策略构建；如需跨场景对比，建议在方法段明确场景参数并统一误差线策略。

- 重复次数与独立性假设
  - 显著性图的 `mean ± 95% CI` 来自多次重复实验（参见 `significance_compare_intel_parallel.json`），我们假设重复间相互独立且采样分布稳定；若存在时间相关性或批次效应，CI 的覆盖率可能偏离理想值，应在正文讨论其影响。

- 非参数统计与效应量
  - 页脚同时给出非参数统计摘要（来自 `significance_nonparam_intel_parallel.json`）：
    - Mann–Whitney U：两独立样本分布位置的秩检验统计量；不依赖正态性与方差齐性。
    - AUC（相当于概率胜率）：随机抽样下，一组值大于另一组值的概率估计，取值 [0,1]。
    - Cliff’s δ：效应量衡量（无分布假设），取值 [-1,1]，符号指示方向，绝对值表示强度。
    - Cohen’s d（合并标准差）：传统效应量衡量，便于与既有文献对比；当分布重尾或方差不齐时应谨慎解释。
  - 若非参数结果不可用或存在异常，页脚回退到 Welch’s t-test 说明；此时隐含方差不齐但仍需近似正态的假设，应在方法段给出谨慎解释。

- 多重比较与FDR控制
  - 多拓扑显著性（如 `fig_multi_topo_significance`）采用 Benjamini–Hochberg FDR（q=0.05）进行校正；Intel 单场景的双样本对比未进行多重校正，避免过度保守。跨多图的大规模比较需在正文明确校正策略。

- GPU利用率采集与解释
  - 通过 `nvidia-smi dmon -s u` 与引擎级快照（SM、MEM、ENC、DEC、JPG、OFA）计算平均利用率；采样长度约30条记录，适合反映短时推理任务的资源使用概况。
  - 采样窗口有限、混合负载（IO、预处理）与驱动层队列策略可能改变瞬时占用；因此图表用于定性支撑，不作为严格的瓶颈证明。

- 结果可复现性与透明性
  - 所有图表由 `scripts/plot_paper_figures.py` 生成，输出统一复制到 `results/publication_figures/`；必要时可附上 `results/for_submission/manifest.json` 作为提交包索引。
  - 建议在补充材料中共享 `intel_replay_compare.json`、`significance_compare_intel_parallel.json` 与非参数结果文件，以支持同行复核。

- 局限与风险提示
  - 单场景的外推性有限，建议在“Uniform / Corridor”多拓扑下补充验证；当环境映射或传输模型改变时，效应量大小可能重估。
  - 样本量差异（PDR与能耗的n不同）会影响误差线长度与检验功效，图注已尽量明确；但仍建议在方法段给出n值与重复策略的统一表述。