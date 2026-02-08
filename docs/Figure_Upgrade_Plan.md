## Figure & Table Upgrade Plan (MDPI Sensors)

> 目标：用 1–2 轮迭代重绘核心图表、修复表格版式与拓扑示意，使审稿人直观看到 AERIS 的价值、瓶颈与改进路线。统一配色/字体/统计注释，避免“信息不足、粗糙、不如基线”观感。

### 优先级与交付
- **P0 必做（本轮完成）**
  1) **核心对比图**：端到端 PDR + 总能耗双面板，AERIS energy/robust vs LEACH/HEED/PEGASIS/TEEN，场景：Intel、50×100、Uniform-200/300/500（各含 95% CI + 显著性/效应量标注）。  
  2) **并发/限额热图**：横轴并发 C、纵轴 $L_{gw}$，颜色为 $\mathrm{PDR}_{e2e}$；叠加文本显示均值 $L_{gw}$、$L_{gw}=1$ 占比、实际并发；包含 baseline 与 relaxed 配置。  
  3) **诊断链条**：cluster→CH、CH→BS、端到端均值+CI，并在标题/注释点出瓶颈（如“CH→BS 0.48 但 e2e 0.066：簇内+限额塌陷”）。  
  4) **表格修复**：三线表（动态/大规模等）列宽与对齐，避免文字出界；必要时拆表或转横版。
- **P1 建议（若时间允许）**
  5) **拓扑/流程示意**：重绘矢量图，展示双 BS、骨干、gateway 流，统一风格。  
  6) **故事化汇总图**：2×2 面板串联“诊断→策略→结果”（如动态/失联/大规模）。  
  7) **附录热图/敏感性**：gateway 参数扫描热图标注目标线（PDR=0.40/0.20）和最优点。

### 数据源与脚本
- 核心 JSON：`results/intel_baselines_all.json`，`results/monte_carlo_uniform50.json`，`results/compare_multi_topo.json`，`results/large_scale_long.json`，`results/gateway_sweep_uniform{300,500}_dualbs_concurrency{2,4}.json`，`results/gateway_sweep_uniform{300,500}_dualbs_conc4_relaxed.json`。
- 现有绘图脚本（需改造统一风格/加基线）：`scripts/plot_paper_figures.py`，`plot_gateway_limit_heatmap.py`，`plot_gateway_concurrency_effect.py`（新增 base+relaxed），`plot_dynamic_diagnostics.py`，`plot_pdr_breakdown_diagnostics.py`。
- 统计注释：使用已有 `results/significance_*` 与 `results/for_submission/*stats.md`；显著性标星/CI/样本量需写入图注。

### 统一样式规范
- 字体/字号：Palatino/Times, 主文 9–10pt；线宽/marker 统一；ColorBrewer/Tableau 色板。
- 图例放空白区不遮挡曲线；刻度/网格线浅灰；坐标轴标题对齐。
- 图注必须包含：n（复现/窗口/种子）、CI 类型（bootstrap 95%）、校正方法（Holm-Bonferroni/BH-FDR）、效应量（d 或 δ）/显著性标记。
- 语言全英文；避免中英文混排。

### 具体行动列表（P0）
1) **重绘核心对比图**：改造 `plot_paper_figures.py` 或新脚本，生成 AERIS vs baselines 的 PDR/能耗双面板（Intel, 50×100, Uniform-200/300/500），输出到 `results/plots/paper_core_compare.pdf/svg`，替换正文引用。  
2) **并发/限额热图升级**：基于 `plot_gateway_concurrency_effect.py` 增加热力版本（C × Lgw），叠加最优点与目标线，输出 PDF/SVG，正文引用更新。  
3) **诊断链条图**：从 `results/dynamic_*_compare_reps.json` / `large_scale_long.json` 提取 cluster→CH / CH→BS / e2e，绘制均值+CI 条形/折线，标题点明瓶颈；输出 `paper_pdr_breakdown_combined.pdf`。  
4) **三线表修复**：调整列宽/换行，必要时转 landscape（动态显著性表、大规模表），保证不出界；检查所有表头/脚注的统计说明。  
5) **正文/附录同步**：更新 LaTeX 图注与引用路径；Supplement 表 S2/Sx 中加入新图/新表，保证 Reproduction 表列出新命令。

### 验收检查
- XeLaTeX 编译通过；所有图表/表格不溢出，字体/配色一致。  
- 每幅核心图含基线对比、CI/显著性、清晰图注与 n/校正方法。  
- Data Availability/Reproduction 表含新图的命令与 JSON 路径。  
- PDF 视觉检查：无遮挡、无错位、表格对齐、图例清晰。
