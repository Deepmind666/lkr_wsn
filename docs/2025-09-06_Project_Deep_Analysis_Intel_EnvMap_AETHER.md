# Enhanced-AERIS-WSN 项目深度分析（Intel 环境映射与 AERIS 主线）
日期：2025-09-06  作者：Trae AI 助手

—— 目标：在不更改数据资产的前提下，完整梳理代码与结果产物、明确高质量图表路径与论文级实验口径，形成可复现与可扩展的研究闭环。

## 1. 项目结构与关键资产（速览）
- 数据（只读）：
  - data/Intel_Lab_Data/（已存在，mote_locs.txt 等）
  - 不下载、不覆盖；仅读取现有资产
- 源码核心：
  - src/intel_dataset_loader.py（IntelLabDataLoader：真实数据加载、合成、预处理；依赖 pandas/numpy/sklearn）
  - src/integrated_enhanced_eehfr.py（AERIS 主线协议逻辑整合）
  - src/benchmark_protocols.py（NetworkConfig 等实验配置）
  - src/pytorch_lstm_env.py、src/pytorch_tcn_env.py（学习型环境映射实现）
- 脚本入口：
  - scripts/run_intel_classical_envmap.py（SARIMAX/ETS/TBATS 经典基线→JSON）
  - scripts/run_intel_lstm_envmap.py、scripts/run_intel_tcn_envmap.py（学习型→JSON）
  - scripts/run_intel_replay.py、scripts/run_intel_baselines*.py（AERIS 重放/对比→JSON）
  - scripts/plot_paper_figures.py（统一读 JSON → 导出论文图）
- 结果与图表（重点路径）：
  - results/：所有 JSON 结果的默认目录（如 intel_ets_envmap_compare.json 等）
  - results/plots/：批量绘图脚本默认导出目录（PNG/PDF/SVG）
  - results/plots_curated/：高质量策展图表（建议放终稿精选图，配 manifest.json 记录版本）
  - results/publication_figures/：论文交付版图表（建议将最终 SVG 放到此处）
  - results/isj_minimal_svg/：最小图集（快速占位）

## 2. 原本代码的工作流（Intel 环境映射）
1) 数据加载：IntelLabDataLoader（src/intel_dataset_loader.py）
   - 读取湿度/温度/电压等多维度传感器时序，附位置信息；若连接性文件缺失，会生成默认连接
2) 经典时间序列基线：scripts/run_intel_classical_envmap.py
   - 模型：SARIMAX/ETS（可选 TBATS）
   - 训练长度 train_len、预测步长 horizon、季节周期 seasonal_period 可配
   - 产出：results/intel_<model>_envmap_compare.json（含 AETHER_energy、AETHER_robust 两种模式下的总能耗与端到端 PDR）
3) 学习型环境映射：scripts/run_intel_lstm_envmap.py / run_intel_tcn_envmap.py
   - 借助 src/pytorch_lstm_env.py、src/pytorch_tcn_env.py 训练预测，产出 intel_lstm_envmap_compare.json / intel_tcn_envmap_compare.json
4) AERIS 仿真与重放：scripts/run_intel_replay.py、run_intel_baselines*.py、run_final_baseline_compare.py
   - 生成 AERIS 与经典 LEACH/HEED/PEGASIS 的对比 JSON
5) 统一绘图：scripts/plot_paper_figures.py
   - 从 results/ 中取 JSON，导出到 results/plots/（PNG/PDF/SVG）；可再策展到 results/plots_curated/ 与 results/publication_figures/

## 3. 我已核查的文件与要点（当前版）
- scripts/run_intel_classical_envmap.py
  - 严格模式下依赖 statsmodels；缺失时可降级到简化实现（季节性朴素/简单 Holt-Winters）
  - 输出路径：results/intel_<model>_envmap_compare.json（与绘图脚本兼容）
- scripts/plot_paper_figures.py
  - PLOT_DIR=results/plots，DATA_DIR=results，统一读取 compare.json 并导出 SVG/PNG/PDF
  - 函数 fig_intel_classical_envmap() 汇总 SARIMAX/ETS → 生成两张柱状图（Energy/PDR）
- src/intel_dataset_loader.py
  - 提供真实数据加载，包含缺省连接性兜底；依赖 pandas/numpy/sklearn
- src/integrated_enhanced_eehfr.py
  - AERIS 主线协议的整合实现，作为仿真运行时的调度与策略核心
- src/benchmark_protocols.py
  - NetworkConfig 等实验配置对象，串联协议、拓扑与运行参数

说明：后续我会对 integrated_enhanced_eehfr.py、*baseline* 与 *significance* 系列脚本做逐段注释级别的二次核查，并补充到本文件的“附录：逐文件清单”。

## 4. 高质量图表路径与规范
- 生成：scripts/plot_paper_figures.py → results/plots/*.svg（矢量优先，同时有 PNG/PDF）
- 策展：将用于论文展示的精选图表搬运/链接到 results/plots_curated/，并更新 manifest.json 记录数据版本、参数与导出时间
- 交付：终稿 SVG 统一放入 results/publication_figures/，并配文档标注图号/标题/数据来源 JSON 文件
- 命名：paper_* 前缀 + 场景/主题；统一 Times New Roman、轴标签与标题大小，PDR 统一范围 [0,1.05]

## 5. 技术债与潜在缺口（聚焦复现与论文质量）
- 依赖一致性：requirements.txt 需要同时覆盖 TensorFlow/Keras 与 PyTorch（已补充 torch/torchvision/torchaudio 版本建议）
- TBATS 依赖链：安装 tbats → 需先装 numpy 与 pmdarima；Windows 下需预热 numpy 以避免构建失败
- 指标口径统一：端到端 PDR vs hop 级 PDR；能量单位与统计周期；CI 计算方法与样本量标注
- 键名不一致：部分 JSON 的键名存在历史版本差异（fix_result_keys.py 已提供修复脚本）
- 策展流程：高质量图表应进入 plots_curated 与 publication_figures，当前部分图仍停留在 plots 目录，需清单化搬运
- IntelLabDataLoader 历史接口：避免调用下载函数/旧属性，统一使用真实数据加载 + 默认连接兜底（已按此原则运行）

## 6. 论文级实验建议（替代“快速对照图”）
- 多随机种子重复（建议 N≥30，关键图 N≥50），报告均值 ± 95% CI
- 显著性检验：Welch t-test + Holm–Bonferroni 多重比较校正
- 跨拓扑与跨分布：至少两类拓扑（走廊、网格）与两种环境映射（经典 vs 学习型）
- 标准规模：Intel 训练长度 ≥ 200k、预测跨度 horizon ≥ 2 天（例 576 采样，5min 间隔）
- 统一导出：全部图表提供 SVG；图注注明样本量 n、重要参数（季节周期、训练长度、轮数等）
- 复现实验脚本：集中入口（run_reproduce_all.py）+ 清晰的实验矩阵与参数表

## 7. 下一步执行（不改数据，只读现有资产）
1) 完成 SARIMAX（标准规模）结果写出 → 触发 fig_intel_classical_envmap() 生成两图并进入 plots
2) 依规范策展：将通过校验的高质量 SVG 复制/链接至 plots_curated 与 publication_figures，并更新 manifest.json
3) 指标口径核对：端到端 PDR、能量统计窗口、CI 计算方式统一；必要时用 fix_result_keys.py 校正旧 JSON
4) 可选：补齐 TBATS（按 numpy → pmdarima → tbats 顺序安装），形成三基线（SARIMAX/ETS/TBATS）齐全对比
5) 深读 integrated_enhanced_eehfr.py 与 significance/ablation/sensitivity 系列脚本，补充“附录：逐文件清单”

---
如需我立即将已通过人工审阅的高质量图表搬运至 results/plots_curated/ 与 results/publication_figures/ 并生成一份图表清单，请直接告知。我会严格使用 SVG 并维护 manifest。