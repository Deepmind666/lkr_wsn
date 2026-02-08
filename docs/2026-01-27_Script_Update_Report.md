# 脚本更新报告 - R8文件引用修复

**日期**: 2026-01-27
**目的**: 修复分析/绘图脚本引用旧动态实验文件的问题

---

## 一、问题描述

之前的验证报告存在夸大：声称"所有脚本已更新"，但实际上多个脚本仍引用旧文件名。

**Grep证据（修复前）**:
```
scripts/compute_aeris_round_significance.py: "dynamic_corridor_compare.json"
scripts/compute_dynamic_significance.py: "dynamic_corridor_compare.json"
scripts/plot_dynamic_comparisons.py: "dynamic_corridor_compare.json"
scripts/plot_dynamic_dropout_standalone.py: "dynamic_dropout_compare.json"
scripts/plot_dynamic_pdr_boxplots.py: "dynamic_corridor_compare.json"
scripts/summarize_dynamic_stats.py: "dynamic_corridor_compare.json"
```

---

## 二、修复内容

### 已修复的6个脚本

| 脚本 | 修复内容 |
|------|----------|
| compute_aeris_round_significance.py | 添加r8文件到SCENARIOS列表首位 |
| compute_dynamic_significance.py | 添加r8文件到SCENARIOS列表首位 |
| plot_dynamic_comparisons.py | 添加r8文件到SCENARIOS列表首位 |
| plot_dynamic_dropout_standalone.py | 改用DATA_CANDIDATES列表 |
| plot_dynamic_pdr_boxplots.py | 改用文件列表格式 |
| summarize_dynamic_stats.py | 添加r8文件到SCENARIOS列表首位 |

### 命名兼容性修复

所有脚本已添加AERIS-E/AERIS-R与AERIS_energy/AERIS_robust的双向兼容：
- 优先查找新命名 (AERIS-E/AERIS-R)
- 回退到旧命名 (AERIS_energy/AERIS_robust)

---

## 三、验证证据

### 3.1 Grep验证（修复后）

r8文件引用数量: **16处**

```
compute_aeris_round_significance.py:28: "dynamic_corridor_compare_r8.json"
compute_aeris_round_significance.py:33: "dynamic_moving_bs_compare_r8.json"
compute_aeris_round_significance.py:38: "dynamic_dropout_compare_r8.json"
compute_dynamic_significance.py:22: "dynamic_corridor_compare_r8.json"
compute_dynamic_significance.py:27: "dynamic_moving_bs_compare_r8.json"
compute_dynamic_significance.py:32: "dynamic_dropout_compare_r8.json"
plot_dynamic_comparisons.py:90: "dynamic_corridor_compare_r8.json"
plot_dynamic_comparisons.py:107: "dynamic_moving_bs_compare_r8.json"
plot_dynamic_comparisons.py:124: "dynamic_dropout_compare_r8.json"
plot_dynamic_pdr_boxplots.py:26-28: 3个r8文件
plot_dynamic_dropout_standalone.py:18: "dynamic_dropout_compare_r8.json"
summarize_dynamic_stats.py:23-25: 3个r8文件
```

### 3.2 R8文件存在性验证

```
results/dynamic_corridor_compare_r8.json  ✓ 存在
results/dynamic_moving_bs_compare_r8.json ✓ 存在
results/dynamic_dropout_compare_r8.json   ✓ 存在
```

### 3.3 R8文件Schema验证

**dynamic_corridor_compare_r8.json**:
- n_results: 720 ⚠️ (展平后记录数，非 `len(results)`)
- format_version: "1.0" ✓
- schema_type: "dynamic_corridor" ✓
- metadata.n_replicates: 30 ✓
- metadata.git_commit: "44b51f6fa1d4" ✓

**重要说明**:
- `results` 为嵌套 dict 结构: `{rep_0: {phase1: {LEACH: {...}}}}`
- `len(results)` = 30 (顶层 rep 数量)
- `n_results` = 720 = 30 reps × 4 phases × 6 protocols (展平后)
- 使用 `src/result_loader.py` 可统一处理两种 schema

---

## 四、未修复的已知问题

以下问题**未在本次修复范围内**：

1. **21个脚本仍包含AERIS_energy/AERIS_robust字符串**
   - 这些是旧代码，但已通过fallback机制兼容
   - 不影响功能，但代码不够整洁

2. **run_dynamic_*.py 默认输出仍为旧文件名**
   - 需要手动指定 `--output` 参数生成r8文件
   - 或修改默认输出路径

---

## 五、结论

**本次修复范围**: 6个分析/绘图脚本的文件引用
**修复状态**: 完成
**验证方法**: Grep搜索 + 文件存在性检查 + Schema验证

**报告结束**
