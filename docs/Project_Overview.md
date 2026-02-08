# AERIS-WSN-Protocol 项目说明（精简但可查证）

## 1) 仓库结构（可信度优先）
- `data/intel_lab/`（若缺省可从 Intel Berkeley Research Lab 链接获取）：IEEE 802.15.4 实测湿度/温度/信号强度，回放到模拟中；在脚本中以 JSON/CSV 调用。
- `results/`：所有实验 JSON、统计输出；`results/plots/` 含投稿用 SVG/PDF 主图与流程图。
- `scripts/`：从数据→仿真→统计→绘图全链路脚本；`run_experiments.py`（汇总跑实验）、`plot_paper_figures.py`（主图）、`plot_method_flowchart.py`（流程图）。
- `for_submission/`：LaTeX 与 PDF（`final_paper.tex`、`final_paper_new.pdf`）；引用路径已指向 `results/plots/`。
- `references/main.bib`：30 篇高质量参考文献，正文全量交叉引用。
- `docs/`：摘要整理、真伪核验、审阅记录、本说明。

## 2) 算法逻辑结构（可落地、可复现）
1. **输入与环境更新**：感知湿度/温度 → 依据 Intel Lab 实测拟合的对数阴影参数；能耗按 CC2420 实测参数计算。  
2. **CAS + Skeleton**：基于能量/距离/可靠性/冗余评分，CAS 在直连/链式/两跳聚合间切换；Skeleton 选主干节点缩短路径。  
3. **Gateway 协作**：能量/鲁棒双配置（energy vs robust），采用种子同步聚合以稳态对比。  
4. **Safety/Fairness**：检测持续失败/掉点触发冗余或功率补偿；公平轮换簇头避免过载。  
5. **统计与诊断**：统一 PDR/能耗指标，Welch t 检验 + 效应量；输出 JSON + 表格 + 图。  
6. **可重复性**：所有脚本与 seeds、JSON、LaTeX、图表在 git 管理下，可一键重现。

> 逻辑线索与图示：`results/plots/paper_method_flowchart.{svg,pdf}`（徽标化、WCAG 配色）直观映射输入→CAS/ Skeleton→Gateway→Safety/Fairness→输出/统计。

## 3) 数据真实性与调用位置
- Intel Lab 实测：在 `scripts/run_experiments.py`、`scripts/plot_paper_figures.py` 中读取对应 JSON/CSV（路径经 `data/intel_lab/` 或下载链接）。  
- 所有图表来源：`results/*.json`，由 `plot_*` 脚本生成；路径在 `docs/Reproduction_Table.md` 对应清晰。  
- 无模拟假数据：若缺源文件，可依据文档链接重新下载，脚本会报错提示缺失文件。

## 4) 主要创新点
- **真实信道+能耗校准**：Intel 湿度/温度驱动的阴影模型 + CC2420 能耗参数，取代自由空间假设。  
- **纯算法、MCU 友好**：CAS/Skeleton/Gateway/Safety/Fairness 全闭式/线性，无训练、无专用硬件，适配 16 MHz 节点。  
- **统计透明**：统一 PDR/能耗，Welch t 检验、效应量、Holm/BH 校正；正文直接给出核心数值。  
- **可扩展钩子**：骨干密度、多网关/多 Sink、并发调度、安全/公平旋转可独立开关，便于后续调优与审稿追问。  
- **可复现性**：脚本、种子、JSON、图表、LaTeX 全链路公开；`docs/Reproduction_Table.md` 列出“图/表 → 命令/输入”映射。

## 5) 关键结果（可查证）
- Intel 回放：PDR 0.389 → 0.524（+34.6%），能耗仅 +0.8 J。  
- 50×100 Monte Carlo：PDR 0.817，能耗 36.8 J。  
- 动态/掉点/大规模 300/500：保持能效与存活率，暴露 CH→BS 瓶颈，为多网关/密度调优指路。  
- 所有数值均可在 `results/*.json` + `scripts/plot_paper_figures.py` 重绘验证。

## 6) 复现命令（最短路径）
```bash
cd AERIS-WSN-Protocol
# 全套实验（示例）
python scripts/run_experiments.py --test all
# 生成主文图表（WCAG 配色/Arial，SVG+PDF）
python scripts/plot_paper_figures.py --scenario all --palette wcag --font Arial --svg --pdf --dpi 600
python scripts/plot_method_flowchart.py
# 编译论文
cd for_submission && latexmk -xelatex -interaction=nonstopmode final_paper.tex
```

本说明旨在回答：项目结构在哪里、算法链路是什么、数据是否真实、如何复现与验证、核心创新与结果是什么。所有要素均指向仓库内可验证的脚本/数据/图表。 
