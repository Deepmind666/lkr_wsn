# 2026-01-27 实验计划（AERIS）

> 版本：v1.0  
> 目标：在统一能量模型与信道模型下，重跑关键实验并产出可复现实验结果与图表  
> 说明：所有实验统一使用 CC2420 能耗模型与同一信道环境配置，确保公平对比。

---

## 0. 总体原则
- **统一模型**：同一能耗模型（CC2420）、同一信道模型（Log-normal / indoor_office）。
- **统一配置**：相同节点数、区域密度、包长、路由参数基线。
- **可复现**：每类实验固定 seed + 记录 seeds；输出 JSON 进入 `results/`。
- **统计严谨**：默认 n=30 replicates（Intel 部分可更高），报告均值、CI95、效应量。
- **公平对比**：对事件驱动协议（TEEN/SEP）需单独说明比较语义，必要时给出“等包量”设置或作为附录比较。
- **一致性校验**：所有实验输出字段统一为 PDR / energy / lifetime / alive_nodes，避免绘图或统计混用字段。

---

## 1. 实验矩阵（优先级从高到低）

### P0. SOTA 基线对比（100 节点）
目的：重新校准 AERIS‑E / AERIS‑R 与 LEACH/HEED/PEGASIS/TEEN/SEP 的真实差异。  
**必须新增对照**：Contiki‑NG 的 RPL（baseline），若无法公平对比则在附录说明。
- 规模：100 nodes, 200 rounds, n=30
- 输出：PDR / 能耗 / 寿命 + 统计显著性
- 关键注意：
  - TEEN/SEP 需要“等包量”或“事件驱动”对照说明
  - 明确是否使用 AERIS‑E / AERIS‑R 双 profile
- 脚本：
  - `scripts/run_sota_comparison_v2.py`（基线）
  - AERIS 结果从统一实验结果读取
  - RPL 对照：优先 `contiki-ng` / `ns3_validation`（视可用性）

### P0. 大规模可扩展性（100/200/300/500）
目的：验证规模上升时 AERIS 与基线差距与能耗增长趋势。
- 规模：100/200/300/500 nodes, rounds=200, n=30
- 脚本：`scripts/run_large_scale_scalability.py`
- 输出：`results/large_scale_scalability_YYYYMMDD_HHMMSS.json`

### P0. Intel Lab 真实轨迹消融
目的：明确 CAS / GW / Fairness / Safety 等模块贡献。
- 数据：Intel Lab
- n=50~100（并行）
- 脚本：`scripts/run_intel_ablation_parallel.py`
- 输出：`results/intel_ablation.json`

### P0. Intel Lab 敏感性实验
目的：评估 packet_size / gateway_k / initial_energy 对性能的稳定性。
- n=50~60（并行）
- 脚本：`scripts/run_intel_sensitivity_parallel.py`
- 输出：`results/intel_sensitivity.json`

### P0. NS‑3 交叉验证（关键场景）
目的：验证 Python 仿真结论的可信度与一致性。  
- 场景：100 节点 / Intel 复现 / 动态走廊（选 1–2 个）  
- 输出：NS‑3 结果 JSON + Python 对照表  
- 位置：`ns3_validation/`（需与 Python 版本参数对齐）  

---

### P1. 动态压力测试（走廊/移动BS/节点失效）
目的：明确失败模式与适用边界；反证“过强 claims”。
- 走廊动态：`scripts/run_dynamic_corridor_compare.py`（n=30）
- 移动 BS：`scripts/run_dynamic_moving_bs_compare.py`（n=30）
- 随机失效：`scripts/run_dynamic_dropout_compare.py`（n=30）
- 输出：`results/dynamic_*_compare_YYYYMMDD_HHMMSS.json`

### P1. 复现实验图表更新
- 使用 `scripts/plot_dynamic_*` 与 `scripts/generate_sota_figures.py`
- 保证图例不遮挡、排版统一、统计表字体可读
- 图表统一补充：能耗/寿命/能量‑每成功包（energy per delivered packet）

---

### P2. 工程指标
- 运行时开销测算（执行时间均值/方差）
- 记录每种协议的执行时间分布（仅统计，避免过度夸大）

### P2. 多数据集对照（如可用）
- 目标：除 Intel 外增加 1–2 套公开数据集  
- 数据集候选：Sensorscope / GreenOrbs / 其他 WSN 公开集（TODO: 确认可用性）  
- 若无法获取，必须在论文中明确局限与未来计划。

---

## 2. 统一执行（推荐）
使用调度器统一跑：
```
python scripts/run_overnight_8h.py --workers 22 --intel-repeats 50 --dynamic-reps 30 --scale-reps 30
```
- 优点：避免 API 变更导致崩溃；所有输出集中到 `results/`。

---

## 3. 预期输出与验收标准
- 所有实验输出 JSON + run_logs 完整生成
- PDR/能耗趋势合理、统计项齐全
- 图表排版无遮挡、无异常点孤立
- 可追溯的 seed / n 值记录
- Python 与 NS‑3 的关键场景趋势一致（方向一致即可）

---

## 4. 时间预估（可高强度）
- P0 全部完成：约 6–10 小时（取决于 workers）
- P1 动态压力：约 2–4 小时
- P2 + 图表重绘：约 2–3 小时

---

## 5. 风险与注意事项
- 任何“100% PDR”声明需要明确条件与置信区间
- 需保持 AERIS-E / AERIS-R 与 baseline 的公平对比
- 动态场景若失败应明确写入“适用边界”
- 若 TEEN/SEP 与持续上报协议比较不公平，需分场景讨论或放附录

---

> 负责人：Codex  
> 备注：执行前应确认数据目录完整（Intel Lab 数据存在），否则需改为 synthetic fallback。
