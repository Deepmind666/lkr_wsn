# AERIS 论文缺陷深度审计与优化路线

**日期**: 2025-10-28  
**目标期刊**: MDPI Sensors  
**当前版本**: AERIS_Paper_Preview.md（已修订贡献与方法一致性）

---

## 一、总体结论

- 框架完整、图表质量合格，统计方法与期刊规范对齐（Welch t、Holm–Bonferroni、Cohen’s d、bootstrap CI）。
- 主要短板集中在：术语一致性历史残留、部分章节待填充、参考文献补齐与交叉引用警告、以及少量LaTeX包依赖。
- 在不引入新实验的前提下，采用“一致性修订 + 语气降噪 + 引用补齐 + 版式规范”即可达到投稿标准。

---

## 二、关键缺陷清单（按影响度排序）

### D1. 术语与技术一致性（高优先）
- 旧稿残留“30+维特征、K-means 8类、Q-learning”的表述，与当前实现（密度三分类 + 加权评分 + EMA）不符。
- 影响：实质性一致性风险 → 审稿人质疑真实性。
- 状态：AERIS_Paper_Preview.md 已修正；需排查其他文档（中文稿、总结报告）。

### D2. 章节欠填充（高优先）
- Related Work（2）、System Model（3）、Protocol Design（4）、Experimental Setup（5）在预览稿仍有“待转换/待撰写”标记。
- 影响：完整性不足，投稿不可接受。
- 建议：将中文稿现有内容（第2/3节）快速英译并结构化移植；Protocol Design 用伪代码 + 架构图覆盖。

### D3. 参考文献与交叉引用（中高）
- bibliography.bib 缺项约 20–30 条；存在 `\ref{...}` 未定义警告。
- 影响：编译警告、可信度下降。
- 建议：合并 `bibliography_supplement.bib`；两次 pdflatex + bibtex 解决引用。

### D4. LaTeX 包依赖（中）
- algorithm/algorithmic 或 algorithm2e 环境未声明。
- 影响：Algorithm 1 编译失败。
- 建议：在 preamble 增加 `\usepackage{algorithm}`、`\usepackage{algorithmic}`（或选用已测试的最小依赖）。

### D5. 图表与统计脚注（中）
- Figure captions 未统一“单位/统计脚注/n值”风格；部分图内文字接近 8pt 下限。
- 影响：版面规范性、可读性。
- 建议：统一 Caption 模板，补充 n、CI、检验方法；保持深灰 `#333` 字色。

### D6. MDPI 必需声明（中）
- IRB、Informed Consent、Data/Code Availability、Funding、COI、Acknowledgments 等声明需要在终稿出现。
- 状态：已在预览稿末尾补齐；LaTeX 终稿需同步。

---

## 三、优化路线（P0/P1/P2）

### P0（今天完成，关键阻断项）
1. 统一贡献与方法表述（已完成预览稿）。
2. 在预览稿尾部加入 MDPI 声明（已完成）。
3. 生成本审计与路线文档（当前文件）。

### P1（1–2 天，可投稿）
1. 英译并移植中文稿第2/3节到预览稿（结构化小节）。
2. 完成 Protocol Design：伪代码 + 3 张架构/流程图（Mermaid → SVG）。
3. 补齐参考文献：合并 `bibliography_supplement.bib`，修复 `\ref{}`。
4. 统一图表 Caption：添加 n/CI/检验方法脚注，检查字号 ≥ 8pt。
5. LaTeX preamble 增加 algorithm 包，确保 Algorithm 1 编译通过。

### P2（提高录用概率，2–3 天）
1. 语言润色：Grammarly + 术语一致性（CH/cluster head, PDR, fairness）。
2. 扩展 Discussion：对比 DRL/ML 的可部署性与鲁棒性，加入工程建议清单。
3. 增补图表：三层架构总览、CAS流程、Skeleton选择示意（SVG）。
4. 完善复现包：批处理脚本 + README，使新人 30 分钟可复现图表。

---

## 四、时间线与交付物

- T0（今日）: 修订贡献与声明，产出审计报告（本文件）。
- T+1 天: 移植 Related Work/System Model，完成 Protocol Design + 图表3张。
- T+2 天: 引用补齐、算法环境编译、Caption统一，生成提交版 PDF。

交付物：
- `AERIS_Paper_Preview.md`（完整英稿）
- `aeris_paper.pdf`（LaTeX终稿，编译通过）
- `for_submission_artifacts/`（图表与合并 PDF）
- `README_REPRODUCE.md`（30 分钟复现说明）

---

## 五、风险与应对

- R1 数据数字差异：若后续真实仿真与示例数值有偏差，优先更新图表与统计表，正文文字引用统一从脚本自动写入。
- R2 LaTeX 兼容性：若 algorithm2e 不稳定，退回 `algorithm + algorithmic` 组合；伪代码尽量采用简单列表环境以提高兼容性。
- R3 字体与版式：维持 Palatino/YaHei，图内文字 ≥ 9pt；优先 SVG/PDF 矢量输出。

---

## 六、已完成项（本轮）

- 修正贡献 C1–C3 与实现一致（密度三分类、EMA加权、PCA骨架）。
- 在预览稿末尾补齐 MDPI 声明与统计方法说明。
- 统一 t-test、Holm–Bonferroni、Cohen’s d 书写与符号格式。

---

**结论**：按照上述 P0/P1 路线推进，稿件可在 1–2 天内达到 MDPI Sensors 投稿标准；P2 可显著提升审稿通过率（Minor Revision 概率增加）。