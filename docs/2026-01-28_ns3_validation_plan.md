# AERIS 深度改进与 NS-3 交叉验证计划（修订版）

**日期**: 2026-02-01  
**修订原因**: 结合 `docs/2月1日gpt.md` 的 CAS 失效分析与消融实验配置，补充 CAS 诊断与埋点任务、明确优先级顺序，并将 NS-3 验证与消融配置对齐。

---

## 0. 当前状态核对（以仓库现状为准）
> 结论：Phase A **基本完成但需复核**；CAS 诊断与 NS-3 对齐仍是阻塞项。

| 事项 | 状态 | 证据 | 备注 |
|---|---|---|---|
| pdr_end2end 输出 | **基本完成** | 已改为严格模式（缺失标记 -1.0） | 需抽查所有实验脚本是否仍有 fallback |
| enable_channel=True | **基本完成** | 关键脚本已启用 | 仍需对“超长/夜间/综合脚本”逐一核对 |
| stable_hash() 替换 hash() | **基本完成** | 关键脚本已改用 `stable_hash` | 仍需仓库范围抽查是否有遗留 |
| NS-3 参数对齐 | **未完成** | NS-3 与 Python 参数显著不一致 | 见第 1 节 |
| NS-3 逻辑对齐 | **未完成** | NS-3 为简化实现 | 见第 2 节 |

**补充证据来自 `docs/2月1日gpt.md`**：
- 消融实验配置：200 节点、600 轮、拓扑 uniform + corridor31、重复 100/变体/拓扑、信道 indoor_office、模式 lightweight。  
- 关键缺口：CAS 模式统计未入库（无法支撑 “DIRECT vs CHAIN 次数” 结论）。

**判定**：Phase A 仍需补齐；不得直接跑 NS-3 验证。

---

## 1. P0：参数对齐（必须先完成）
> 否则 NS-3 与 Python 差异将主导结果，PDR 差异 >5% 并非算法问题。

### 1.1 信道模型参数统一
**Python (realistic_channel_model.py)**  vs **NS-3 (realistic-channel-model.h / aeris-validation-standalone.cc)**

| 环境 | Python (n, σ, noise) | NS-3 当前 | 差异 | 处理 |
|---|---|---|---|---|
| Indoor Office | n=2.0, σ=4.5 dB, noise=-95 | INDOOR_LOS: n=2.5, σ=3.0 | n +25%、σ -33% | **NS-3 新增/覆盖 IndoorOffice 配置** |
| Indoor NLOS | n=2.7, σ=8.5 | INDOOR_NLOS: n=3.5, σ=6.0 | n +30%、σ -29% | 对齐或显式选择同一环境 |
| Industrial | n=3.0, σ=6.0 (Python alias) | INDUSTRIAL: n=3.8, σ=8.0 | n +27%、σ +33% | 对齐 |

**动作**：在 NS-3 侧新增 `INDOOR_OFFICE` 环境并设置 n=2.0、σ=4.5、noise=-95；所有 NS-3 结果必须记录环境参数。

### 1.2 能量模型统一
| 参数 | Python (CC2420) | NS-3 当前 | 差异 | 处理 |
|---|---|---|---|---|
| E_ELEC | 208.8 nJ/bit | 50 nJ/bit | 4.18× | **NS-3 改为 CC2420** |
| E_DA | 5 nJ/bit | 5 nJ/bit | 一致 | 保留 |
| D_CROSSOVER | 87.0 m | 87.7 m | 近似 | 可保持 |

**动作**：NS-3 `aeris-protocol.cc` 与基线协议中统一使用 CC2420 参数；Python 侧也必须显式记录平台（避免误用 GENERIC）。

---

## 2. P0：算法逻辑对齐清单（必须完成）
> NS-3 当前实现为**简化版**，不符合“交叉验证”要求。

### 2.1 CAS 对齐
- Python 使用特征：energy/link/dist_bs/radius/density/fairness/tail_max
- 权重、EMA、动态惩罚、stage_weights 必须对齐
- NS-3 当前仅用 energy/link/dist/fairness 的简单加权（缺失 radius/density/tail_max）

**动作**：
- NS-3 侧补齐 CAS 特征与权重表
- 复刻 EMA + uncertainty penalty 机制
- 输出 CAS 选择统计（切换频率）

### 2.2 Gateway 对齐
- Python 使用中心性（Closeness proxy）、阶段权重、负载限制
- NS-3 当前仅用 distance + energy 简化

**动作**：
- NS-3 侧实现中心性评分与负载限制
- Gateway 选择日志记录 (负载占比)

### 2.3 Skeleton 对齐
- Python 使用 PCA 主轴 + scale-adaptive 参数
- NS-3 当前**无 Skeleton 实现**

**动作**：
- 方案 A：NS-3 实现 Skeleton
- 方案 B：NS-3 验证时在 Python **关闭 Skeleton** 形成“同功能版本”
- 二者必须二选一并记录说明

**产出**：`docs/ns3_alignment_checklist.md`

---

## 3. 输出规范与差异检测
### 3.1 JSON Schema 统一
所有 NS-3 输出必须包含：
```
{ config, seed, protocol, metrics: {pdr_end2end, pdr_hop, energy_total_j, lifetime_rounds, alive_nodes}, env, git_commit, schema_version }
```

### 3.2 自动化差异检测
- 现有 `ns3_validation/scripts/compare_results.py` 仅比较 pdr/energy
- 必须升级为统一 schema + pdr_end2end

**动作**：新增 `scripts/compare_python_ns3.py` 或升级现有脚本，输出差异报告 JSON + MD。

---

## 4. 环境配置（必须写入计划）
- 依 `ns3_validation/README.md` 安装 NS-3 (建议 WSL2/Ubuntu)
- 建议记录：编译日志、ns-3 commit、编译时间
- 产出：`logs/ns3_build_YYYYMMDD.txt`

---

## 5. 研究优先级（来自 2月1日 DeepSearch 需求）
推荐顺序（必须写入执行计划）：
1) 任务2：CAS 失效根因分析  
2) 任务3：模块干扰分析  
3) 任务6：竞品对比定位  
4) 任务1：文献调研  
5) 任务4：改进方案  
6) 任务5：论文策略  

---

## 6. 修订后的分阶段执行
### Phase A — Python 基线清洗（必须完成）
- [ ] **全脚本**输出 `pdr_end2end`
- [ ] **全脚本**启用信道模型（基线不再 1.0 PDR）
- [ ] **全脚本**改用 `stable_hash`
- [ ] 统一 JSON schema
- [ ] 记录 `reliability_mode`（轻量/标准/可靠）到结果元数据

### Phase B — NS-3 参数对齐
- [ ] 信道参数对齐（Indoor Office + Industrial）
- [ ] 能量参数对齐（E_ELEC 等）
- [ ] 输出环境参数到 JSON

### Phase C — NS-3 逻辑对齐
- [ ] CAS 权重与策略一致
- [ ] Gateway 评分与负载一致
- [ ] Skeleton 处理方案确定并记录
- [ ] 复核 CAS 权重与文档一致性（当前文档与代码存在潜在冲突，需确认）

### Phase D — CAS 诊断与埋点（必须）
- [ ] 增加 CAS 模式统计：DIRECT/CHAIN/TWO_HOP 计数、切换频率  
- [ ] 记录 EMA 参数、置信度门限、stage_weights 使用情况  
- [ ] 分拓扑输出 CAS 统计，避免混合掩盖差异

### Phase E — NS-3 最小验证集
- 先对齐消融配置：200 节点、600 轮、uniform + corridor31  
- 小样本验证：n=5/变体/拓扑  
- 再扩展：100/200/300/500 节点（n=30）  

---

## 7. 里程碑（修订为 4–6 周）
- **第 1 周**：补齐 Phase A + CAS 埋点  
- **第 2 周**：参数对齐（信道+能量）+ NS-3 小样本验证  
- **第 3–4 周**：CAS/Gateway/Skeleton 逻辑对齐 + 扩展验证  
- **第 5–6 周**：论文修订 + 交叉验证结果写入  

---

## 8. 回归测试策略
- 建立最小回归集：
  - 1 个 seed，100 节点，AERIS+LEACH
  - 每次修改后验证 PDR/能耗差异 ≤ 2%
- 输出 `results/regression_baseline.json`

---

## 9. 结论（修订后的行动顺序）
**必须先完成 P0（参数 + 逻辑对齐）再跑 NS-3**，否则“差异过大”将是模型问题而非算法问题。NS-3 的作用是验证关键结论，而非替代 Python 全量实验。

---

## 10. 交付物清单（更新）
- `docs/2026-01-28_ns3_validation_plan.md`（本修订版）
- `docs/ns3_alignment_checklist.md`
- `docs/ns3_param_map.md`
- `scripts/compare_python_ns3.py`
- `results/ns3_validation_YYYYMMDD.json`
- `docs/validation_report.md`
- `results/cas_mode_stats_YYYYMMDD.json`
- `docs/ablation_cas_diagnosis_report.md`
