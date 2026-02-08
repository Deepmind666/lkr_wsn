# MDPI Sensors 技术评估报告（AERIS-WSN-Protocol）

更新时间：2025-11-08  来源仓库：`c:/AERIS-WSN-Protocol`

## 一、项目概览与代码结构

- 核心协议与算法模块：
  - `src/aeris_protocol.py`（集成改进能耗、真实信道、环境分类、模糊逻辑、网关/骨架选择等）
  - `src/entropy_driven_aeris.py`（信息熵驱动的簇头选择与能量均衡）
  - `src/realistic_channel_model.py`（RSSI/LQI/PDR/SINR、环境参数化，含 IEEE 802.15.4 灵敏度与 LQI 映射）
  - `src/improved_energy_model.py`（CC2420/TelosB 硬件参数与能耗估计）
  - `src/baseline_protocols/`（LEACH、PEGASIS、HEED 基线对照）
  - 选路辅助：`gateway_selector.py`、`skeleton_selector.py`、`node_state_manager.py`（维护 PDR/RSSI/LQI、邻居记录与统计）

- 实验与测试支撑：
  - 测试：`tests/test_realistic_leach.py`、`tests/test_fixed_protocols.py`、`tests/test_enhanced_eehfr.py` 等
  - 运行脚本：`scripts/run_reproduce_all.py`、`scripts/run_intel_ablation.py`、`scripts/validate_figures.py`、`scripts/smoke_test.py`
  - 数据：`data/Intel_Lab_Data/`，以及合成数据与中间产物（`results/*.json`、`results/publication_figures/`）

- 可能的旧代码/备份与开发性文件（建议迁移至 `archive/` 或按需剔除）：
  - `src/aeris_protocol.py.backup_*`（多份备份版本）
  - `src/debug_*`、`src/quick_*`、`src/test_*`（开发性或自测脚本混入源码目录）
  - `src/comprehensive_benchmark.py`、`src/generate_theoretical_analysis_report.py`（生成型脚本，建议收敛归档）

结论：核心协议与模型集中在 `src/`，结构清晰，但存在备份和开发脚本混入生产代码目录的问题，需治理以满足可维护性与投稿可复现要求。

## 二、代码质量审查

- 静态分析（ruff）：
  - 命令：`ruff check src tests --statistics`
  - 汇总：共发现约 800 项问题，其中可自动修复约 156 项。
  - 代表性问题：
    - `F541` f-string 无占位符、`F401` 未使用导入、`F821` 未定义名称、`E402` 非顶层导入、`E702/E701` 单行多语句、`E703` 无用分号。
    - 部分文件出现非 ASCII 字符导致解析失败（见 `final_corrected_leach.py`），需要统一编码头与文本清理。

- 语法与编码一致性：
  - 建议在所有 `.py` 文件首行统一加入：`# -*- coding: utf-8 -*-`。
  - 统一字符串使用 ASCII 或明确的 UTF-8 文档字符串，避免特殊块字符（如 `U+2589`）。

- 文档与注释：
  - 核心模块普遍配有模块级文档字符串与说明，但存在中英文混排与噪声字符；建议统一术语与语言，并在关键 API（如能耗模型、信道模型、簇头选择、路由阶段）补充参数与返回值说明。
  - 可考虑生成 API 文档的最小流程（如 `pdoc` 或 `mkdocstrings`），但不宜在本轮增加工具链复杂度。

## 三、实验环境验证

- 环境定义与复现：
  - 现有：`scripts/conda_env.yml` 与 `scripts/setup_conda_env.ps1`，可在 Windows/PowerShell 下复现。
  - 推荐复现流程：
    - `conda env create -f scripts/conda_env.yml -n aeris-wsn`
    - `conda activate aeris-wsn`
    - `python scripts/smoke_test.py`（快速验证环境与依赖）
    - `python scripts/run_reproduce_all.py` 或针对性运行 `tests/`

- 测试执行现状（本次快速尝试）：
  - 运行 `pytest -q` 触发收集阶段错误：
    - `final_corrected_leach.py` 存在非 ASCII 字符导致 `SyntaxError`（缺少/不一致编码头）。
    - `tests/test_enhanced_eehfr.py` 引用缺失模块 `enhanced_eehfr_protocol.py`（仓库中不存在，推测为旧命名）。
    - `tests/test_environment_aware_eehfr.py` 引用 `environment_aware_eehfr`（仓库中不存在）。
  - 结论：测试集与当前源码存在命名漂移和编码不一致，需统一入口与模块命名后再进行全面回归。

- 数据采集模块与校准记录：
  - 模块：`src/intel_dataset_loader.py`；测试脚本中对缺依赖已有健壮回退（`_HAS_PANDAS` 逻辑）。
  - 建议：
    - 在 `data/Intel_Lab_Data/` 中补充 `README.md`（采集来源、预处理流程、校准策略），并在加载器中记录所用校准常数（温湿度补偿、丢包填补）以便复核。

- IEEE 802.15.4 合规性（实现覆盖范围）：
  - 已覆盖：PHY 层关键指标建模（`realistic_channel_model.py` 内含 `IEEE802154LinkQuality`，实现 RSSI→LQI 映射、灵敏度阈值 `-85 dBm`、PDR 分段模型；`realistic_leach_protocol.py` 中有 SINR、RSSI、PDR 推导和环境影响项）。
  - 未覆盖/不足：MAC 层行为（CSMA/CA 退避、ACK/重传、载波侦听、帧控制字段、时隙/信标模式）未显式建模；现有实现更偏向物理链路质量驱动的仿真。
  - 建议：在不显著增加复杂度前提下，新增“简化 MAC 行为层”（可嵌入 `node_state_manager` 或 `realistic_channel_model`）以模拟：退避计时、ACK 成功率与重传计数、信道忙检测，提供与 IEEE 802.15.4 行为一致的上界与下界。

## 四、学术价值评估

- 创新点与差异化：
- 信息熵驱动的簇头选择与能量均衡（`entropy_driven_aeris.py`）。
  - 引入真实信道与链路质量模型（RSSI/LQI/SINR/PDR），并与 CC2420 能耗模型耦合（`realistic_channel_model.py` + `improved_energy_model.py`）。
  - 模糊逻辑与安全回退策略（AERIS 协议内置），以及网关选择与骨架结构辅助路由。
  - 提供对比丰富的基线协议与多脚本实验框架，利于公平对比与可重复性。

- 统计显著性与可重复性：
  - 现有 `results/` 目录含多组 JSON 与 ONNX 导出，可作为初始结果集；但未见系统化的多次独立重复与显著性检验在测试脚本中固化。
  - 建议：
    - 固化 30 次独立重复（不同 `seed`）的批量实验脚本，输出关键指标均值/方差与置信区间。
    - 使用 Benjamini–Hochberg FDR 或非参数检验（见 `results/multitest_bh_fdr.json`）的既有产物，完善统计显著性报告。

- 结果可视化规范：
  - 现有 `scripts/plot_paper_figures.py`、`scripts/curate_figures.py`，以及 `results/publication_figures/`。
  - 建议：统一字体（英文 `DejaVu Sans`/中文 `Microsoft YaHei`）、字号、线宽；确保矢量图（SVG/PDF）与主图/补充图一致，颜色与标注符合期刊规范；图注应明确实验设置与统计口径。

## 五、论文准备评估

- 方法细节完整性：
  - 硬件参数（CC2420/TelosB）、能耗模型公式与校准、信道模型来源与参数化、数据集来源与预处理、簇头选择准则与权重、路由阶段流程与安全回退策略，需要在方法章节详述并对齐代码实现。

- 结果分析支撑假设：
  - 以 PDR、网络寿命、能量效率（包/焦）、每包能耗（mJ/packet）为主指标，辅以 RSSI/SINR 分布与链路质量演化，明确在哪些环境类型（Indoor/Outdoor/Urban/Industrial）下优势显著、是否存在边界条件。

- 图表与代码输出一致性：
  - 建议建立 “数据→图表” 可复现实验流水线（单一入口脚本），并在提交前进行交叉核对（随机抽查图表数据与 JSON 输出一致性，保留核对日志）。

## 六、性能分析与量化指标

- 网络层指标：延迟（平均/95%分位）、PDR、吞吐量（包/轮）、跳数分布（已在 AERIS 中增设 `hop_count_distribution` 与 `packet_paths` 追踪）。
- 能耗指标：总能耗、每包能耗、能量效率（包/焦），按节点/簇/全网分解。
- 计算开销：对核心阶段（簇头选择、成簇、数据传输）进行 `cProfile` 采样，识别热点与不必要的重复计算。
- 建议：在 `experiment_logger.py` 或协议类中添加统一的指标采集与 JSON 输出接口，减少脚本差异。

## 七、改进路线图（面向 MDPI Sensors 投稿）

- 短期（1–3 天）：
  - 统一编码与清理非 ASCII 文本；为所有 `.py` 文件增加 `# -*- coding: utf-8 -*-`。
  - 修复测试命名漂移：将 `tests/` 中旧引用对齐到现有模块（如将 `enhanced_eehfr_protocol` 映射到 `aeris_protocol` 或新增适配层）。
  - 运行 `ruff --fix src tests`（启用安全修复），手工修复不可自动修复项（未定义名称、逻辑错误）。
  - 在 `node_state_manager` 补充最简 MAC 行为参数（退避/ACK/重传计数），并开放阈值配置以便敏感性分析。

- 中期（1–2 周）：
  - 固化多次重复实验与统计显著性输出，生成对比表与主图（含误差线/置信区间）。
  - 扩展 `realistic_channel_model` 的环境参数并与 Intel Lab 数据的温湿度时间序列联动，开展灵敏度分析。
  - 整理 `archive/obsolete_*/` 与 `src/*backup*`，清理冗余文件，确保代码与测试的一致性。
  - 完成“数据→图表→论文”流水线脚本，确保单入口复现。

- 投稿前（1 周）：
  - 方法章节与附录细化，补充参数表与伪代码；在补充材料中给出关键脚本与数据子集。
  - 进行复核抽样（图表与 JSON 输出一致性），并保存复核日志。
  - 进行对照与消融实验，覆盖环境类型与主要参数敏感性。

## 八、合规性与可复现清单（核对项）

- IEEE 802.15.4：提供 PHY 指标映射、MAC 简化行为模型与参数说明；在方法中明确不涵盖的标准模块与合理性说明。
- 统计学：最少 30 次重复、显著性检验（如 BH-FDR/非参数检验）、效应量与置信区间。
- 可复现性：提供 `conda_env.yml`、单入口脚本、固定随机种子、版本锁定与数据下载说明。
- 图表规范：统一字体/字号/矢量格式，图注标明实验设置与统计口径。

## 九、当前阻碍与建议

- 测试集与源码存在命名漂移与编码不一致，需先修复以恢复回归测试能力。
- 存在较多静态分析问题，建议分阶段修复并设定基准线（CI 中以 `ruff`/`pytest` 作为关卡）。
- IEEE 802.15.4 合规性目前偏向 PHY 层，建议按计划补充最简 MAC 行为以满足期刊期望的协议完整性描述。

——
本报告由自动化工具与人工审阅共同生成，后续将根据修复进度更新评估结论与投稿准备状态。