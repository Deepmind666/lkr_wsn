# Schema 一致性严格审查报告

**审查身份**: 顶刊审稿人 + 代码审计工程师
**日期**: 2026-01-27
**结论**: ⚠️ Schema 不一致已通过统一读取层解决

**修复状态**: ✅ 已实现 `src/result_loader.py` 统一读取层

---

## 一、核心漏洞清单

### 漏洞1: results 结构类型不一致

| 文件 | results 类型 | 实际结构 |
|------|-------------|----------|
| unified_output_validation_*.json | **Array** | `[{protocol, scenario, metrics:{...}}, ...]` |
| dynamic_corridor_compare_r8.json | **Dict** | `{rep_0: {phase1: {LEACH: {...}}}}` |

**证据**:
```
# unified (Array)
"results": [
  {"protocol": "AERIS-R", "scenario": "uniform", "metrics": {...}}
]

# dynamic (Dict)
"results": {
  "rep_0": {
    "phase1": {
      "LEACH": {"packet_delivery_ratio_end2end": 0.49}
    }
  }
}
```

**统计后果**: 任何试图用 `len(results)` 或 `for item in results` 遍历的代码，在两种文件上行为完全不同。

---

### 漏洞2: n_results 与 len(results) 语义冲突

| 文件 | n_results | len(results) | 实际含义 |
|------|-----------|--------------|----------|
| unified | 360 | 360 | ✓ 一致 |
| dynamic_r8 | 720 | **30** | ❌ 严重冲突 |

**证据** (dynamic_corridor_compare_r8.json):
```json
"n_results": 720,
"results": {
  "rep_0": {...},  // 1
  "rep_1": {...},  // 2
  ...
  "rep_29": {...}  // 30
}
// len(results) = 30, 但 n_results = 720
```

**计算逻辑**: 720 = 30 reps × 4 phases × 6 protocols
但 `results` 是嵌套 dict，`len()` 只返回顶层 key 数量 (30)。

**审稿后果**: 审稿人执行 `assert n_results == len(results)` 会失败，质疑数据造假。

---

### 漏洞3: metrics 字典存在性不一致

| 文件类型 | metrics 字典 | 字段位置 |
|----------|-------------|----------|
| unified | ✓ 存在 | `results[i].metrics.pdr_end2end` |
| dynamic | ❌ 不存在 | `results.rep_0.phase1.LEACH.packet_delivery_ratio_end2end` |

**证据对比**:
```json
// unified
{"metrics": {"pdr_end2end": 0.90, "energy_total_j": 81.1}}

// dynamic
{"packet_delivery_ratio_end2end": 0.49, "total_energy_consumed": 133.7}
```

**代码后果**: 统一读取层必须写两套逻辑，否则 `KeyError`。

---

### 漏洞4: 字段命名不一致

| 指标 | unified 命名 | dynamic 命名 |
|------|-------------|--------------|
| PDR | `pdr_end2end` | `packet_delivery_ratio_end2end` |
| 能耗 | `energy_total_j` | `total_energy_consumed` |
| 存活 | `alive_nodes` | `final_alive_nodes` |

**复现后果**: 论文表格引用字段名时，必须区分来源文件。

---

## 二、修复建议

### 方案A: 统一读取层 (推荐，最小改动)

创建 `src/result_loader.py`，封装两种 schema 的读取逻辑：

```python
def load_experiment_results(path: str) -> List[Dict]:
    """统一返回 flat list 格式"""
    data = json.load(open(path))
    schema = data.get("schema_type", "")

    if schema == "unified_metrics":
        return data["results"]  # 已是 list
    elif schema.startswith("dynamic_"):
        # 展平嵌套 dict
        flat = []
        for rep_key, phases in data["results"].items():
            for phase, protocols in phases.items():
                for proto, metrics in protocols.items():
                    flat.append({
                        "replicate": rep_key,
                        "phase": phase,
                        "protocol": proto,
                        "pdr_end2end": metrics.get("packet_delivery_ratio_end2end"),
                        "energy_total_j": metrics.get("total_energy_consumed"),
                        "alive_nodes": metrics.get("final_alive_nodes"),
                    })
        return flat
```

### 方案B: 修改 n_results 语义

在 dynamic 文件中，将 `n_results` 改为 `n_replicates`，或添加 `n_flat_records` 字段：

```json
{
  "n_replicates": 30,
  "n_phases": 4,
  "n_protocols": 6,
  "n_flat_records": 720,  // 30 × 4 × 6
  "results": {...}
}
```

---

## 三、报告改写建议

### 2026-01-27_Script_Update_Report.md 需修改内容

**原文 (错误)**:
> r8文件schema符合要求：
> - ✅ 顶层 `n_results`: 720

**改为**:
> r8文件schema说明：
> - ⚠️ 顶层 `n_results`: 720 (表示展平后记录数，非 `len(results)`)
> - ⚠️ `results` 为嵌套 dict，`len(results)` = 30

---

## 四、脚本兼容策略

已修复的6个脚本采用了**fallback机制**：
- 优先查找新命名 (AERIS-E/R)
- 回退到旧命名 (AERIS_energy/robust)

但**未解决**的问题：
1. 字段名映射 (pdr_end2end vs packet_delivery_ratio_end2end)
2. results 结构差异 (list vs nested dict)

**建议**: 在每个读取脚本中添加 schema 检测逻辑。

---

## 五、结论

| 检查项 | 原状态 | 修复后 | 说明 |
|--------|--------|--------|------|
| results 类型一致 | ❌ FAIL | ✅ FIXED | `load_experiment_results()` 统一返回 list |
| n_results 语义一致 | ❌ FAIL | ✅ FIXED | `get_metadata()` 返回 declared/actual 两值 |
| metrics 字典存在 | ❌ FAIL | ✅ FIXED | `extract_metrics()` 统一提取 |
| 字段命名一致 | ❌ FAIL | ✅ FIXED | `FIELD_MAPPING` 字典映射 |
| 协议命名一致 | ✓ PASS | ✓ PASS | `PROTOCOL_MAPPING` 字典映射 |
| r8文件引用 | ✓ PASS | ✓ PASS | 6个脚本已更新 |

**修复方案**: `src/result_loader.py` 统一读取层

**重要说明**:
- JSON 文件本身的 schema 差异**保持不变**（向后兼容）
- 通过统一读取层在**代码层面**解决不一致问题
- 所有分析脚本应使用 `load_experiment_results()` 而非直接 `json.load()`

**报告结束**
