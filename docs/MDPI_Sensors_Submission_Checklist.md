# MDPI Sensors Submission Checklist (AERIS)

生成时间：2025-10-24 11:08:27

## 1. 主要图表与打包
- 已生成压缩包：
  - `results/for_submission/publication_figures_20251024-110827.zip`
  - `results/for_submission/Sensors_figures_20251024-110827.zip`
  - `results/for_submission/plots_curated_20251024-110827.zip`
- 对应清单已更新：`results/for_submission/manifest.json`
- 建议稿件引用文件名时使用上述 zip 中的 SVG/PDF 原件。

## 2. 统计一致性要求（要点）
- 统一显著性检验：`BH-FDR` 与 `Holm–Bonferroni` 两套校正并行报告。
- 统一采样种子：图表来自同一批结果集（corridor31/41、uniform 50x200）。
- 统一误差度量：均值±95%CI，并在必要处给出效应量（Cliff's delta 或 Hedges' g）。
- 显著性可视化：在 `paper_intel_sig_combined.svg` 与多拓扑面板中保持一致模板标注。

## 3. 论文结构补充（MDPI 必需项）
- Data Availability：指向 `results/_archive_*` 与 `results/for_submission/*` 的可公开工件。
- Code Availability：公开仓库（当前仓库路径）；附复现脚本说明。
- Author Contributions（CRediT）：`Conceptualization, Methodology, Software, Validation, Writing, Supervision` 按作者分配。
- Conflicts of Interest：如无，请明确声明“作者声明不存在竞争性利益”。
- Acknowledgments：硬件/经费与同事致谢；如涉及 GPU/DML 资源可注明。
- Nomenclature/Abbreviations：术语与符号表（已在草稿中准备）。
- Ethics Statements（如适用）：多数仿真类研究通常“不适用”，可按期刊指引处理。

## 4. 贡献列表（建议在导言或结论中以编号呈现）
1) 提出预测驱动的环境映射以约束AERIS路由的公平性与安全性。
2) 构建轻量可部署的蒸馏模型链条，并在资源受限设备上验证其有效性。
3) 系统化的统计检验与显著性可视化，确保结论稳健且可复现。
4) 完成端到端产出链条：仿真、统计、图表、打包与投稿物料。

## 5. 引用与数字统一
- 统一稿件与图注中的数值（准确对应 `distillation_report.json` 与显著性结果）。
- 参考文献清理：`Paper_Quality_Improvement_Summary.md` 中列出的缺项需补齐。
- 伪代码与符号表：在方法章节插入算法伪代码，术语表统一定义。

## 6. 提交前自检（快速核对）
- [ ] 主图与面板命名统一，稿件引用文件名一致。
- [ ] 显著性文件已更新并在图中一致呈现。
- [ ] 必需章节（数据/代码/贡献/冲突/致谢/术语）均已出现。
- [ ] `manifest.json` 与 zip 均可打开，图形渲染正常。
- [ ] 稿件 PDF 可生成（LaTeX/Word 流程均可），页码与图表编号正确。

备注：若需将 Checklist 直接迁入 LaTeX/Word 稿件，可按章节互引方式添加附录或补充材料链接。