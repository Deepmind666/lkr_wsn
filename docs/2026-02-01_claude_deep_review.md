# Claude 4.5 深度评审：GPT DeepSearch 分析与同事评审的交叉验证（v2.0）

**日期**: 2026-02-01
**评审者**: Claude Opus 4.5
**版本**: v2.0（整合用户严苛评审反馈）
**目的**: 对GPT DeepSearch分析和同事评审进行交叉验证，识别遗漏点，完善改进计划

---

## 一、GPT DeepSearch 核心发现的验证状态

### 1.1 权重配置问题 — ✅ 已验证，需校正数值

**GPT结论**: Direct模式权重和=1.5

**代码验证结果（校正后）**:

| 层级 | 来源 | Direct权重 | 说明 |
|------|------|-----------|------|
| Layer 1 | `cas_selector.py` 默认值 | 0.35+0.40-0.20-0.15+0.25-0.05 | **=0.60**（含负权重） |
| Layer 2 | `aeris_protocol.py:1238-1241` | energy=0.70, link=0.80 | **≈1.35**（非1.50） |
| Layer 3 | `_apply_stage_weight_adjustment` | 特征缩放 | **不是权重覆盖** |

**关键修正**:
1. 覆盖后权重和约**1.35**，非1.50
2. 阶段自适应是**特征缩放**（`stage_feature_scaling`），不应与权重覆盖混为一谈
3. 必须同时输出`effective_weights`与`stage_feature_scaling`

### 1.2 EMA平滑机制 — ✅ 已验证，需限定条件

**代码验证** (`cas_selector.py:39`):
```python
ema_alpha: float = 0.2  # 仅20%新信息
lambda_uncertainty: float = 0.0  # 默认关闭动态惩罚
```

**关键修正**:
1. **EMA跨集群污染**: 确认存在
2. **动态惩罚默认关闭**: `lambda_uncertainty=0.0`，仅`min_confidence`的"锁定上次模式"机制在起作用
3. **置信度锁定**: `min_confidence=0.2`，环境剧变时反而锁定旧模式

### 1.3 特征归一化问题 — ⚠️ 待验证

**GPT结论**: radius/density典型值仅0.1-0.2，贡献微弱

**需要验证**: 当前消融实验结果中**缺少特征值统计**，无法直接验证

---

## 二、同事评审的交叉验证

### 2.1 同事正确指出的问题

| 问题 | 同事结论 | 我的验证 |
|------|---------|---------|
| NS-3 PDR定义不一致 | hop-level而非端到端 | ✅ 确认 |
| NS-3实现简化 | CAS/Skeleton逻辑缺失 | ✅ 确认 |
| NS-3参数不对齐 | 信道模型不同 | ✅ 确认 |
| 样本量不足 | n=3无法支撑统计结论 | ✅ 确认，需n≥30 |

### 2.2 同事评审的遗漏点

1. **未提及safety_fallback强制DIRECT**: 会扭曲CAS统计
2. **未提及阶段自适应权重的三层叠加**: 仅提两层
3. **未提出具体的NS-3对齐方案**: 仅指出问题

### 2.3 同事评审的优点（我应采纳）

1. **NS-3能耗参数具体化**: 提出CC2420参数(E_ELEC=208.8 nJ/bit)
2. **功能降级对照策略**: NS-3简化版可做"功能降级对照"

---

## 三、用户严苛评审指出的关键缺口

### 3.1 safety_fallback强制DIRECT未计入CAS统计

**代码证据** (`aeris_protocol.py:333-336`, `1274-1299`):
```python
safety_fallback_enabled = True
safety_T = 1  # 连续1轮失败即触发强制DIRECT
```

**关键发现**: `safety_override`统计**已存在于代码中**，但消融结果未输出此字段。

**影响**: 必须输出`safety_override_count`并在消融分析中剔除/分层。

### 3.2 消融实验缺少诊断字段

当前`ablation_fix_test.json`输出结构没有:
- `cas_mode_usage_stats`
- `additional_metrics`
- 特征分布统计

**影响**: "894次DIRECT vs 12次CHAIN"的证据无法对应本次1600任务结果。

### 3.3 force_ctp_reliable可能抹平真实PDR

**问题**: `force_ctp_reliable`会把本轮源包强制计为成功投递，导致端到端PDR被高估。

**修正**: 结果必须标注`reliability_mode/force_ctp_reliable`状态，避免论文误用。

---

## 四、完善的改进计划（v2.1校正版）

### P0 级别（必须先完成）

#### P0.1 CAS诊断埋点

**必须输出的字段**:
```python
cas_diagnostic = {
    'cas_mode_counts': {'DIRECT': 0, 'CHAIN': 0, 'TWO_HOP': 0},
    'safety_override_count': 0,  # 必须单独统计
    'cas_switch_rate': 0.0,
    'confidence_history': [],    # 置信度历史
}
```

**产出**: `results/cas_mode_stats_YYYYMMDD.json`

#### P0.2 特征分布统计

**必须输出的字段**:
```python
feature_stats = {
    'energy': {'min': 0, 'mean': 0, 'p50': 0, 'p95': 0},
    'link': {...},
    'dist_bs': {...},
    'radius': {...},
    'density': {...}
}
```

**验证目标**: 确认"归一化失衡"假设是否成立

#### P0.3 权重来源统一与可追踪

**必须输出的字段**:
```python
weight_trace = {
    'effective_weights': {...},      # 运行期覆盖后的权重
    'stage_feature_scaling': {...},  # 阶段自适应的特征缩放
}
```

**文档要求**: 说明"默认值/覆盖值/阶段自适应"三者关系

#### P0.4 PDR口径锁定

**必须标注的字段**:
```python
pdr_metadata = {
    'reliability_mode': 'lightweight|standard|reliable',
    'force_ctp_reliable': True|False,
    'pdr_end2end': bs_delivered / source_packets,
}
```

**风险**: `force_ctp_reliable`会把PDR人为抬高，必须标注避免论文误用

### P1 级别（强烈建议）

#### P1.1 NS-3参数对齐

| 参数 | Python | NS-3当前 | 对齐目标 |
|------|--------|---------|---------|
| 路径损耗n | 2.0 | 2.5 | 统一2.0 |
| 阴影衰落σ | 4.5dB | 3.0dB | 统一4.5dB |
| E_ELEC | 50nJ/bit | 50nJ/bit | CC2420: 208.8nJ/bit |

#### P1.2 CAS权重/EMA校准实验

- 比较`ema_alpha=0.2/0.5/1.0`
- 测试"不覆盖权重"vs"覆盖权重"

#### P1.3 NS-3消融实验扩展

- 样本量从n=3扩展到n≥30
- 至少两拓扑（uniform/corridor）

### P2 级别（论文策略）

1. **诚实报告CAS局限性**: 以negative result形式报告
2. **突出Gateway贡献**: p=8.49e-29, Cohen's d=1.21

---

## 五、交付物清单（与同事评审对齐）

### P0交付物

| 序号 | 交付物 | 路径 |
|------|--------|------|
| 1 | CAS诊断埋点 | `results/cas_mode_stats_*.json` |
| 2 | 特征分布统计 | 同上 |
| 3 | 权重追踪 | `effective_weights` + `stage_feature_scaling` |
| 4 | PDR口径标记 | `reliability_mode` + `force_ctp_reliable` |

### P1交付物

| 序号 | 交付物 | 路径 |
|------|--------|------|
| 5 | NS-3参数对齐表 | `docs/ns3_param_map.md` |
| 6 | NS-3逻辑对齐清单 | `docs/ns3_alignment_checklist.md` |
| 7 | NS-3消融(n≥30) | `results/ns3_validation_*.json` |

---

## 六、下一步行动优先级

```
P0.1 CAS诊断埋点 → P0.2 特征统计 → P0.3 权重统一 → P0.4 PDR锁定
    ↓
P1.1 NS-3参数对齐 → P1.3 NS-3消融扩展(n=30)
    ↓
P1.2 CAS权重校准实验
    ↓
P2 论文策略调整
```

---

**文档版本**: v2.1（校正权重数值，与同事评审对齐）
**最后更新**: 2026-02-01
**审核状态**: 待用户确认启动P0
