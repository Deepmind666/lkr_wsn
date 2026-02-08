# Figure QA Checklist (MDPI Sensors)

目标：确保所有图表满足四项要求：格式规范、数据准确、价值体现、专业审查。此清单适用于三套图集：`results/publication_figures/`、`results/Sensors_figures/`、`results/plots_curated/`。

## 1. 格式规范
- 文件格式：主稿使用 `SVG`（优先），必要时 `PDF`/`PNG`。
- 尺寸：
  - SVG：`viewBox` 宽度建议 ≥ 1200（像素等效），比例适中（1:1–16:9）。
  - PNG：宽度 ≥ 1200px，避免过低分辨率；无锯齿。
- 字体与标注：
  - 统一字体族（无衬线或 MDPI 推荐字体），字号 ≥ 9pt，子图标签 (a)(b)(c) 清晰。
  - 轴标签、单位、图例完整；颜色对比度 ≥ 4.5:1。
- 线宽与布局：
  - 折线/箱线/小提琴图线宽统一，元素不遮挡；图例不压盖数据。
- 命名与可复现：
  - 文件名仅使用 `[A-Za-z0-9._-]`；避免空格与中文；与稿件引用一致。

## 2. 数据准确
- 数据来源：仅使用仓库中现有 JSON/CSV（如 `results/multitest_bh_fdr.json`、`results/intel_*`）。
- 一致性：确保图中数值与数据源一致；严禁修改数据或“美化”数值。
- 统计标注：
  - 显著性使用 BH-FDR（主）与 Holm-Bonferroni（核对）；星标或 q/p 值显示一致。
- 版本锁定：图的生成脚本/数据版本记录在 README/manifest。

## 3. 价值体现
- 每张图有明确结论或洞见：性能对比、能耗权衡、鲁棒性、方法流程等。
- 独立可读：即使脱离正文，图题能说明关键结论、数据集、参数设置。
- 结构化呈现：主稿 2–3 张核心图，补充材料承载更细节的面板或流程图。

## 4. 专业审查流程
- 自动化验证（本仓库提供 `scripts/validate_figures.py`）：
  - 校验尺寸、命名规范、SVG 关键属性，输出报告 `results/figure_validation_report.md/json`。
- 人工两轮审查：
  - 第1轮：排版/遮挡/标注完整性；第2轮：数据匹配与结论表达。
- 通过准则：
  - 无格式错乱或遮挡；尺寸合规；标注完整；数据与源一致；图题清晰；通过两轮审查。

## 5. 执行说明
- 图集路径：
  - Publication：`results/publication_figures/`
  - Sensors：`results/Sensors_figures/`
  - Curated：`results/plots_curated/`
- 清单与脚本：
  - 运行：`py -3 scripts/validate_figures.py --dirs results/publication_figures results/Sensors_figures results/plots_curated --out results/figure_validation_report.md`
- 审查记录：
  - 在 `results/figure_validation_report.md` 中逐条标注问题与修复状态。

## 6. 常见问题与修复建议
- 分辨率不足：提升导出尺寸或改用 SVG；重设画布。
- 字体不统一或过小：统一样式并提高字号；检查图例与轴标签。
- 颜色过多或对比不足：限制调色板，使用高对比色。
- 命名杂乱：重命名为 `paper_<topic>_<dataset>.svg/png`，与稿件一致。

---
维护人：论文作者组
版本：v1.0