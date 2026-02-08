# aeris_paper_final.tex 数据完整性修正报告
## 日期: 2026-01-18

---

## 数据来源

所有修正基于验证的实验数据文件：
- **large_scale_scalability_verified.json**: 480次运行 (30重复 × 4规模 × 4协议)
- **sota_comparison_rigorous.json**: AERIS多模式测试 (10次运行/配置)

---

## 修正前的错误数据

| 位置 | 错误声明 | 问题 |
|------|---------|------|
| Theory section (L176) | "AERIS 81% PDR...centralized 100%" | 完全相反 |
| Discussion section | "centralized protocols 100% PDR, AERIS 81%" | 完全相反 |
| Discussion (TDA) | "AERIS 81%, PEGASIS dynamic 67.2%, AERIS dynamic 89.1%" | 无验证数据支持 |
| Conclusion | "81% PDR, 19% gap" | 完全相反 |
| Figure captions | "19% static PDR gap" | 错误 |

---

## 修正后的验证数据

### 核心性能数据 (来自 large_scale_scalability_verified.json)

| 协议 | 100节点 PDR | 300节点 PDR | 500节点 PDR |
|------|------------|------------|------------|
| **AERIS** | **100%** | **100%** | **100%** |
| LEACH | 64.76% | 42.88% | 38.09% |
| PEGASIS | 87.97% | 66.72% | 56.13% |
| HEED | 66.09% | 41.91% | 33.99% |

### 能耗数据 (500节点)

| 协议 | 能耗 (mJ) |
|------|----------|
| AERIS | 806.9 |
| LEACH | 898.3 |
| PEGASIS | 368.2 |
| HEED | 895.9 |

---

## 修正内容详情

### 1. Theory Section (原L176)
**修改前**: "AERIS 81% PDR...centralized 100%...19% gap"
**修改后**: 添加注释说明实验验证结果与理论分析的关系；明确AERIS=100%, baselines=38-88%

### 2. Discussion - Protocol Gap Section
**修改前**: "centralized protocols achieve 100% PDR, AERIS 81%"
**修改后**: "AERIS achieves 100% PDR, classical protocols show 34-88%"

### 3. Discussion - Critical Analysis
**修改前**: 讨论"centralized protocols的PDR优势"
**修改后**: 分析为什么classical protocols在realistic channels下失败

### 4. Discussion - TDA Section
**修改前**: "static: centralized 100% vs AERIS 81%, dynamic: AERIS 89.1% vs PEGASIS 67.2%"
**修改后**: Scalability分析，展示AERIS在各规模下保持100% PDR

### 5. Discussion - Ecological Niche
**修改前**: "19% PDR gap is explicit design choice"
**修改后**: "AERIS provides 100% reliability vs 34-88% for classical protocols"

### 6. Conclusion
**修改前**: "81% PDR, 19% gap, trade-off reverses under dynamic conditions"
**修改后**: "100% PDR across all scales, 35-62 pp improvement over LEACH"

### 7. Limitations
**修改前**: "100 nodes"
**修改后**: "500 nodes (verified); 1000+ nodes for future work"

### 8. Figure Captions
- fig_advanced_analysis: 移除"19% gap"声明
- 添加注释提示图表需要重新生成

---

## 关键发现

### AERIS的真实优势（有数据支持）
1. 所有规模下100% PDR
2. 500节点时比LEACH高61.9 pp
3. 随规模增大优势扩大

### AERIS的真实劣势（诚实承认）
1. 能耗比PEGASIS高约2倍 (806.9 vs 368.2 mJ)
2. 决策延迟167ms超过MCU预算

---

## 修正状态

| 检查项 | 状态 |
|--------|------|
| "81%" 声明已移除 | ✅ |
| "19% gap" 声明已移除 | ✅ |
| "centralized 100%" 声明已移除 | ✅ |
| "67.2%", "89.1%" 未验证数据已移除 | ✅ |
| 所有PDR数据可追溯到JSON文件 | ✅ |
| 能耗数据可追溯到JSON文件 | ✅ |

---

## 待办事项

1. [ ] 重新生成图表以匹配验证数据
2. [ ] 编译PDF并最终审查
3. [ ] 更新Data Availability Statement中的仓库链接

---

**修正完成时间**: 2026-01-18
**审查者**: Claude Code (严格数据完整性模式)
**状态**: 论文数据已与实验JSON文件对齐
