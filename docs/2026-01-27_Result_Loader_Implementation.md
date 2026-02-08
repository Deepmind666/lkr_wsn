# 统一读取层实现报告

**日期**: 2026-01-27
**状态**: ✅ 已完成

---

## 一、实现内容

创建 `src/result_loader.py`，解决 Schema 审查报告中发现的 4 个核心漏洞。

### 核心功能

| 功能 | 说明 |
|------|------|
| `load_experiment_results()` | 统一加载，返回 flat list |
| `load_from_candidates()` | 从候选列表加载第一个存在的文件 |
| `get_metadata()` | 获取文件元数据 |
| `validate_schema_consistency()` | 验证 schema 一致性 |
| `group_by_protocol()` | 按协议分组 |
| `extract_metric()` | 提取特定指标 |

---

## 二、漏洞修复对照

| 漏洞 | 修复方案 |
|------|----------|
| results 类型不一致 (Array vs Dict) | `detect_schema_type()` 自动检测，统一返回 list |
| n_results 语义冲突 | `get_metadata()` 返回 declared 和 actual 两个值 |
| metrics 字典存在性不一致 | `extract_metrics()` 统一提取，无论是否有 metrics 包装 |
| 字段命名不一致 | `FIELD_MAPPING` 字典统一映射 |

---

## 三、验证结果

### 3.1 Unified Schema

```
File: unified_output_validation_20260127_220350.json
Schema: unified
Declared: 360, Actual: 360
Consistent: ✅ True
```

### 3.2 Dynamic Schema

```
File: dynamic_corridor_compare_r8.json
Schema: dynamic
Declared: 720, Actual: 720 (flattened)
Consistent: ✅ True
Protocols: ['LEACH', 'PEGASIS', 'HEED', 'TEEN', 'AERIS-E', 'AERIS-R']
```

---

## 四、使用示例

```python
from src.result_loader import load_experiment_results, group_by_protocol

# 加载任意 schema 的文件
results = load_experiment_results("results/dynamic_corridor_compare_r8.json")

# 按协议分组
grouped = group_by_protocol(results)
for proto, records in grouped.items():
    print(f"{proto}: {len(records)} records")
```

---

## 五、字段映射表

| 原始字段 | 标准化字段 |
|----------|------------|
| `packet_delivery_ratio_end2end` | `pdr_end2end` |
| `total_energy_consumed` | `energy_total_j` |
| `final_alive_nodes` | `alive_nodes` |
| `AERIS_energy` | `AERIS-E` |
| `AERIS_robust` | `AERIS-R` |

---

**报告结束**
