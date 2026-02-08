# Codex 严格审核提示词

**日期**: 2026-01-28 (更新)
**目的**: 请 Codex 对 Claude 的代码修复进行严格审核

---

## 审核背景

Claude 声称已完成 Phase A 的代码修复，修复了以下脚本：

| 脚本 | 修复内容 |
|------|----------|
| run_mega_experiments.py | pdr_end2end + stable_hash |
| run_ultra_scale_10h.py | pdr_end2end + stable_hash |
| overnight_master_v2.py | pdr_end2end + stable_hash |
| run_large_scale_scalability.py | stable_hash |
| run_scalability_experiment.py | stable_hash |
| run_unified_output_validation.py | pdr_end2end + stable_hash |

**警告**: Claude 在第一轮修复中遗漏了 `run_unified_output_validation.py` 的 PDR 定义错误（把链路级 PDR 错误标记为端到端 PDR），请重点验证此问题是否已修复。

---

## 审核任务

请严格审核以下内容，**不要相信 Claude 的自我声明**，必须逐一验证：

### 任务 1: 验证 pdr_end2end 输出完整性

检查以下脚本是否正确输出 `pdr_end2end`：

```
scripts/run_mega_experiments.py
scripts/run_ultra_scale_10h.py
scripts/run_mega_8h.py
scripts/overnight_master_v2.py
scripts/run_large_scale_scalability.py
scripts/run_scalability_experiment.py
scripts/run_unified_output_validation.py
```

**验证方法**:
1. 搜索每个脚本中的 `result = proto.run_simulation` 后的输出字典
2. 确认输出字典包含 `pdr_end2end` 字段
3. 确认 `pdr_end2end` 来源于 `packet_delivery_ratio_end2end`，而非 `packet_delivery_ratio`

---

### 任务 2: 验证 stable_hash 替换完整性

检查以下脚本是否已将所有 `hash()` 替换为 `stable_hash()`：

```
scripts/run_mega_experiments.py
scripts/run_ultra_scale_10h.py
scripts/overnight_master_v2.py
scripts/run_large_scale_scalability.py
scripts/run_scalability_experiment.py
scripts/run_unified_output_validation.py
```

**验证方法**:
1. 搜索 `seed.*hash\(` 模式，应返回 0 结果
2. 搜索 `stable_hash` 定义，确认每个脚本都有
3. 确认 `import hashlib` 存在

---

### 任务 3: 验证 enable_channel 配置

检查实验脚本是否正确启用信道模型：

**验证方法**:
1. 搜索 `enable_channel` 设置
2. 确认值为 `True`
3. 确认基线协议（LEACH/PEGASIS/HEED/TEEN）也受此配置影响

---

### 任务 4: 检查遗漏问题

Claude 可能遗漏了以下问题，请逐一检查：

1. **overnight_master_v2.py 是否输出 pdr_end2end**？
2. **run_large_scale_scalability.py 是否输出 pdr_end2end**？
3. **是否有其他脚本仍使用 `hash()`**？
4. **stable_hash 函数实现是否一致**？（应使用 MD5）

---

### 任务 5: NS-3 验证计划审核

审核 `docs/2026-01-28_ns3_validation_plan.md`（修订版）：

1. Phase A 状态是否正确标注为"部分完成"？
2. P0 参数对齐是否列出所有差异？
3. NS-3 PDR 定义问题是否被识别？（hop-level vs end-to-end）
4. 里程碑是否现实？

---

## 审核输出格式

请按以下格式输出审核结果：

```
## 审核结果

### 任务 1: pdr_end2end 输出
| 脚本 | 状态 | 证据 |
|------|------|------|
| run_mega_experiments.py | ✅/❌ | 行号:xxx |
| ... | ... | ... |

### 任务 2: stable_hash 替换
| 脚本 | 状态 | 证据 |
|------|------|------|
| ... | ... | ... |

### 任务 3: enable_channel 配置
...

### 任务 4: 遗漏问题
...

### 任务 5: NS-3 计划审核
...

## 总体评估
- 修复完成度: X/10
- 遗漏问题数: N
- 建议: ...
```

---

## 重要提醒

1. **不要信任 Claude 的自我声明**，必须逐行验证
2. **检查边界情况**：是否有脚本被遗漏？
3. **检查一致性**：所有 stable_hash 实现是否相同？
4. **检查完整性**：pdr_end2end 是否在所有输出路径都存在？

---

**审核开始**
