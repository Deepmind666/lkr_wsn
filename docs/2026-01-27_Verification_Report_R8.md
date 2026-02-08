# AERIS 顶刊级别核验报告 (R8)

**生成时间**: 2026-01-27 23:10
**版本**: R8 (第八轮修复)
**目标**: MDPI Sensors (Q2) 投稿

---

## 1. Schema 一致性检查

| 文件 | n_results | format_version | schema_type | 状态 |
|------|-----------|----------------|-------------|------|
| unified_output_validation_20260127_220350.json | 360 | 1.0 | unified_metrics | ✅ PASS |
| dynamic_corridor_compare_r8.json | 720 | 1.0 | dynamic_corridor | ✅ PASS |
| dynamic_moving_bs_compare_r8.json | 720 | 1.0 | dynamic_moving_bs | ✅ PASS |
| dynamic_dropout_compare_r8.json | 720 | 1.0 | dynamic_dropout | ✅ PASS |

**结论**: 4/4 文件通过

---

## 2. 元数据统一性检查

| 文件 | n_nodes | n_rounds | git_commit | 状态 |
|------|---------|----------|------------|------|
| unified | 100 | 200 | 44b51f6fa1d4 | ✅ PASS |
| corridor | 80 | 200 | 44b51f6fa1d4 | ✅ PASS |
| moving_bs | 80 | 200 | 44b51f6fa1d4 | ✅ PASS |
| dropout | 120 | 150 | 44b51f6fa1d4 | ✅ PASS |

**必需字段**: n_nodes, n_rounds, base_seed, seed_stride, seeds_used, git_commit
**结论**: 4/4 文件通过

---

## 3. 实验一致性检查: n_rounds 差异

| 实验 | n_rounds | 说明 |
|------|----------|------|
| unified | 200 | 标准配置 |
| corridor | 200 | 标准配置 |
| moving_bs | 200 | 标准配置 |
| dropout | 150 | 节点 dropout 场景，较短周期 |

**⚠️ ACTION**: dropout 使用 150 rounds，需在论文 Section 5.3 中说明：
> "The dropout scenario uses 150 rounds to capture the transient behavior during node failures, while other scenarios use 200 rounds for steady-state analysis."

---

## 4. 重复次数检查

| 实验 | n_replicates | 要求 | 状态 |
|------|--------------|------|------|
| corridor | 30 | ≥30 | ✅ PASS |
| moving_bs | 30 | ≥30 | ✅ PASS |
| dropout | 30 | ≥30 | ✅ PASS |

**结论**: 3/3 动态实验满足统计显著性要求

---

## 5. 命名一致性检查

### R8 文件协议命名
| 文件 | 协议列表 | 状态 |
|------|----------|------|
| corridor | LEACH, PEGASIS, HEED, TEEN, AERIS-E, AERIS-R | ✅ PASS |
| moving_bs | LEACH, PEGASIS, HEED, TEEN, AERIS-E, AERIS-R | ✅ PASS |
| dropout | LEACH, PEGASIS, HEED, TEEN, AERIS-E, AERIS-R | ✅ PASS |

### 旧文件问题
- **发现**: 26 个旧文件使用 `AERIS_energy/AERIS_robust` 命名
- **ACTION**: 这些文件应标记为废弃，论文仅引用 r8 文件

---

## 6. 统一输出字段验证

### metrics 字典结构
```json
{
  "pdr_end2end": 0.9088,
  "energy_total_j": 80.97,
  "j_per_delivered": 0.00445,
  "alive_nodes": 100,
  "lifetime_rounds": 200
}
```

**结论**: ✅ PASS - 所有必需字段完整

---

## 7. 统计汇总

### 统一输出实验
- 场景数: 4 (uniform, corridor, clustered, hotspot)
- 协议数: 6 (AERIS-R, LEACH, PEGASIS, HEED, TEEN, AERIS-E)
- 重复数: 15
- 成功率: 360/360 (100%)

### 动态实验
- corridor: 30 reps × 4 phases × 6 protocols = 720 results
- moving_bs: 30 reps × 4 phases × 6 protocols = 720 results
- dropout: 30 reps × 4 phases × 6 protocols = 720 results

---

## 8. 最终结论

| 检查项 | 状态 | 备注 |
|--------|------|------|
| Schema 一致性 | ✅ PASS | 4/4 文件 |
| 元数据统一性 | ✅ PASS | 4/4 文件 |
| n_rounds 差异 | ⚠️ WARN | dropout=150, 需论文说明 |
| 重复次数 | ✅ PASS | 3/3 ≥30 reps |
| 命名一致性 | ✅ PASS | r8 文件全部 AERIS-E/R |
| 旧文件 | ⚠️ WARN | 26 个待废弃 |

---

## 9. 待处理事项

1. **论文修改**: 在 Section 5.3 说明 dropout 场景使用 150 rounds 的原因
2. **文件清理**: 将旧命名文件移至 `results/_archived/` 目录
3. **引用更新**: 确保所有绘图脚本引用 r8 文件

---

## 10. 证据文件清单

| 文件 | 用途 | 状态 |
|------|------|------|
| `results/unified_output_validation_20260127_220350.json` | 4场景×6协议×15reps | ✅ |
| `results/dynamic_corridor_compare_r8.json` | 动态走廊 30reps | ✅ |
| `results/dynamic_moving_bs_compare_r8.json` | 动态移动BS 30reps | ✅ |
| `results/dynamic_dropout_compare_r8.json` | 动态dropout 30reps | ✅ |

---

**报告结束**
