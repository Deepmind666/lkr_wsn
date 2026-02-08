# P0 诊断埋点实现报告

**日期**: 2026-02-01
**版本**: v1.0
**状态**: 已完成

---

## 一、修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `src/aeris_protocol.py` | 新增字段 | P0.1-P0.4 诊断数据结构 |
| `src/aeris_protocol.py` | 修改逻辑 | CAS决策时收集特征与统计 |
| `src/aeris_protocol.py` | 新增方法 | `_compute_feature_stats()` |
| `src/aeris_protocol.py` | 修改输出 | `get_metrics()` 增加诊断字段 |
| `src/cas_selector.py` | 新增方法 | `get_stage_scaling_info()` |

---

## 二、P0.1 CAS诊断埋点

### 新增字段 (aeris_protocol.py:321-324)
```python
self.cas_confidence_history: List[float] = []
self.cas_switch_count = 0
self.cas_total_decisions = 0
```

### 输出字段 (get_metrics)
- `cas_switch_count`: 模式切换总次数
- `cas_total_decisions`: CAS决策总次数
- `cas_switch_rate`: 切换率 = switch_count / (decisions - 1)
- `cas_confidence_mean`: 平均置信度
- `cas_confidence_min`: 最低置信度
- `cas_mode_usage_stats`: 包含 `safety_override` 计数

---

## 三、P0.2 特征分布统计

### 新增字段 (aeris_protocol.py:325-329)
```python
self.cas_feature_samples: Dict[str, List[float]] = {
    'energy': [], 'link': [], 'dist_bs': [],
    'radius': [], 'density': [], 'fairness': [], 'tail_max': []
}
```

### 输出字段 (get_metrics)
```json
"cas_feature_stats": {
    "energy": {"min": 0.5, "mean": 0.7, "p50": 0.72, "p95": 0.9, "max": 1.0, "count": 1200},
    "link": {...},
    "dist_bs": {...},
    "radius": {...},
    "density": {...}
}
```

### 验证目标
- 确认 GPT DeepSearch 假设："radius/density 典型值仅 0.1-0.2"

---

## 四、P0.3 权重追踪

### 新增字段 (aeris_protocol.py:330-332)
```python
self.effective_weights_snapshot: Dict[str, float] = {}
self.stage_feature_scaling_snapshot: Dict[str, float] = {}
```

### 输出字段 (get_metrics)
```json
"effective_weights": {
    "w_direct_energy": 0.7,
    "w_direct_link": 0.8,
    "ema_alpha": 0.2,
    "lambda_uncertainty": 0.0
},
"stage_feature_scaling": {
    "energy_scaling": 1.0,
    "link_scaling": 1.0,
    "stage_weights_active": false
}
```

### 关键说明
- `effective_weights`: 运行期覆盖后的权重（非默认值）
- `stage_feature_scaling`: 阶段自适应的特征缩放（非权重覆盖）

---

## 五、P0.4 PDR口径锁定

### 新增字段 (run_metadata)
```python
'reliability_mode': getattr(config, 'reliability_mode', 'standard'),
'force_ctp_reliable': bool(getattr(config, 'force_ctp_reliable', False)),
```

### 输出字段 (get_metrics)
```json
"pdr_metadata": {
    "reliability_mode": "standard",
    "force_ctp_reliable": false,
    "pdr_end2end_raw": 0.885
}
```

### 风险警告
- `force_ctp_reliable=True` 会强制 PDR=100%，**必须标注避免论文误用**

---

## 六、Bug修复

### 修复1: safety_override时scores未定义
**位置**: aeris_protocol.py:1322
**问题**: 当 `safety_fallback` 触发时，`scores` 变量未赋值
**修复**: 添加占位 `scores = {CASMode.DIRECT: 1.0, ...}`

---

## 七、自查清单

| 检查项 | 状态 |
|--------|------|
| 语法正确性 | ✅ |
| scores变量定义 | ✅ 已修复 |
| 特征收集位置正确 | ✅ |
| 权重快照时机正确 | ✅ |
| PDR标记完整 | ✅ |
| 阶段缩放可追踪 | ✅ |

---

## 八、下一步建议

1. **运行消融实验**验证诊断输出
2. **检查特征统计**确认归一化失衡假设
3. **对比 safety_override 计数**与 CAS 模式分布
4. **NS-3 参数对齐**（P1级别）

---

**文档版本**: v1.0
**最后更新**: 2026-02-01
