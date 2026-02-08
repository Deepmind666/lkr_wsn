# AERIS Paper Submission Checklist

## 📁 提交文件清单

### 主文件
- [x] `aeris_paper_final.tex` - LaTeX源文件 (已修订)
- [x] `aeris_paper_final.pdf` - 编译后的PDF
- [x] `bibliography.bib` - 参考文献

### 图表文件
- [x] 消融实验效应量图 (`fig4_ablation_professional.pdf`)
- [x] 环境-链路相关性图 (`fig2_env_link_enhanced.pdf`)
- [x] 先验实验汇总面板 (`fig3_prior_experiments_enhanced.pdf`)
- [x] 统计验证汇总图 (`fig4_statistical_validation_enhanced.pdf`)
- [x] 协议性能对比图 (`fig5_protocol_comparison_enhanced.pdf`)
- [x] 综合性能总结图 (`fig6_comprehensive_summary.pdf`)
- [x] 参数敏感性图 (`fig7_sensitivity_professional.pdf`)

**图表位置**: `results/professional_figures/`, `results/nature_figures_enhanced/`

### 补充材料
- [x] `supplementary_materials.md` - 补充材料源文件
- [x] `supplementary_materials.pdf` - 补充材料PDF
- [x] 完整统计检验表格 (已包含在补充材料中)
- [x] 敏感性分析结果 (已包含在补充材料中)

### 复现材料
- [x] 源代码 (src/)
- [x] 实验脚本 (scripts/)
- [x] 数据文件 (results/)
- [x] README.md

---

## ✅ 论文修订检查

### 必须完成
- [x] 调整CAS定位（核心→辅助）
- [x] 突出Gateway贡献
- [x] 调整MCU可部署性声称
- [x] 添加先验实验结果
- [x] 添加统计验证
- [x] 创建补充材料

### 图表检查
- [x] 所有图表符合MDPI规范（宽度>=1200px）
- [x] SVG保留文字（svg.fonttype='none'）
- [x] 字体统一（Arial）
- [x] 颜色一致

### 统计检查
- [x] 所有对比有效应量
- [x] 所有对比有置信区间
- [x] 多重比较已校正
- [x] 样本量充足（n>=10）

---

## 📊 关键数据汇总

### 先验实验结果
| 实验 | 关键指标 | 结论 |
|------|----------|------|
| E0 | AUC=0.990 | 环境感知有科学基础 |
| E1 | 准确率90% | CAS特征选择合理 |
| E2 | FPR=0% | Safety阈值有概率论支撑 |
| E3 | r=-0.75 | 负载均衡必要 |
| E4 | 167ms | 需调整MCU声称 |

### 消融实验效应量
| 模块 | Hedges g | 定位 |
|------|----------|------|
| Gateway | 4.48 | 核心创新 |
| Safety | 3.48 | 重要贡献 |
| Fairness | -0.10 | 辅助机制 |
| CAS | -0.15 | 框架/辅助 |

### 统计验证
- 总比较数: 20
- 显著（校正后）: 17
- Large效应: 13
- Medium效应: 2

---

## 📝 MDPI Sensors提交要求

### 格式要求
- [x] 使用MDPI LaTeX模板
- [x] 单栏格式
- [x] 行号
- [x] 参考文献格式正确

### 图表要求
- [x] 分辨率>=300 DPI
- [x] 宽度>=1200px
- [x] 可编辑格式（PDF/SVG）

### 补充材料
- [x] 单独PDF文件
- [x] 包含详细方法
- [x] 包含完整数据

---

## 🎯 提交前最终检查

1. [x] 通读全文，检查逻辑一致性
2. [x] 检查所有图表引用
3. [x] 检查所有参考文献
4. [ ] 检查作者信息
5. [ ] 检查ORCID
6. [x] 检查利益冲突声明
7. [x] 检查资金声明
8. [x] 检查数据可用性声明

---

## 📅 时间线

| 阶段 | 状态 | 日期 |
|------|------|------|
| 先验实验 | ✅ 完成 | 2025-12-27 |
| 统计验证 | ✅ 完成 | 2025-12-27 |
| 图表生成 | ✅ 完成 | 2025-12-27 |
| 论文修订 | ✅ 完成 | 2025-12-28 |
| 最终审校 | ✅ 完成 | 2025-12-28 |
| 图表优化 | ✅ 完成 | 2025-12-29 |
| 提交 | ⏳ 待开始 | - |
