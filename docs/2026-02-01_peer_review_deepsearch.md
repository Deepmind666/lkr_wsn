# GPT DeepSearch 研究发现深度评审与改进计划（对照版）

**日期**: 2026-02-01  
**目的**: 对同事的 GPT DeepSearch 研究发现做严格评审，指出与我方审查的差异与不足，并给出可执行改进计划（含 NS-3 交叉验证）。

---

## 1. 评审结论概览
同事的核心判断方向（CAS 可能失效、Gateway 有效）与现有消融数据趋势一致，但**证据链不完整**、**跨平台对齐不足**、**统计与指标定义存在风险**。在当前状态下，结论可作为“研究假设”，**不应直接写入论文结论**。

---

## 2. 同事结论中**成立**或**基本成立**的部分
1) **CAS 权重偏向 Direct（有效权重）**  
   - AERIS 在运行时对 CAS 权重做了覆盖调整，而非仅使用 `cas_selector.py` 默认值。  
   - 有效权重在 `src/aeris_protocol.py:1232-1242` 明确设置（`w_direct_link=0.8`, `w_direct_energy=0.7` 等），与“Direct 过强偏好”结论一致。  
   - **注意**：默认 Direct 权重和为 **0.60**（含负权重），覆盖后约 **1.35**（非 1.50）。  

2) **EMA 过度平滑 + 置信度锁定可能导致切换迟滞**  
   - CASSelector 采用 EMA 平滑且存在置信度锁定逻辑，确实可能抑制切换。  
   - 但需配合实际统计验证（目前消融结果文件不包含 CAS 模式统计）。

3) **EMA 跨集群污染风险存在**  
   - CASSelector 实例在 AERIS 中是全局对象而非每簇实例，`_ema_scores` 会跨簇共享。  
   - 证据：`src/aeris_protocol.py:1232-1306`（同一 `self.cas_selector` 多簇使用）。

---

## 3. 同事结论中**不充分/需修正**的部分
### 3.1 权重证据来源混淆
- 同事引用“Direct 权重和=1.5”来自 **运行时覆盖**，但文档中未明确区分“默认值 vs 生效值”。  
  - 默认权重位于 `src/cas_selector.py`；  
  - 生效权重位于 `src/aeris_protocol.py:1232-1242`。  
> **修正**：论文与计划中必须明确“生效权重”，否则可被审稿人质疑为证据不一致。  

### 3.2 “三层权重叠加”表述需校正
- 当前机制是 **默认权重 + 运行期覆盖 + 阶段自适应（权重/特征）** 的组合，但“权重和=1.50”与代码不完全吻合。  
- `cas_selector.py` 内还有**阶段特征加权**（`_apply_stage_weight_adjustment`），不应与权重覆盖混为一谈。  
> **修正**：必须记录 **effective_weights** 与 **stage_feature_scaling** 才能准确解释“叠加效应”。  

### 3.3 NS-3 PDR 定义不一致
- NS-3 的 `GetPdr()` 为 **hop-level PDR**（`packetsReceived/packetsSent`），**并非端到端**。  
  - 证据：`ns3_validation/src/aeris/model/aeris-protocol.cc:740-746`。  
> **影响**：NS-3 “CAS 无效 / Gateway 有效”结论尚不能与 Python 端到端 PDR 对齐比较。  

### 3.4 NS-3 实现是简化版
- NS-3 中 CAS/Gateway/Skeleton 逻辑**简化或缺失**，无法直接证明 Python 版本模块贡献。  
  - 证据：`ns3_validation/src/aeris/model/aeris-protocol.cc`（未见 Skeleton/PCA 逻辑；Gateway 简化）。  
> **修正**：必须完成逻辑对齐或做“功能降级对照”。  

### 3.5 NS-3 参数不对齐
- 信道模型与能耗参数显著不同，NS-3 使用 `INDOOR_LOS` (n=2.5, σ=3.0) 等；  
- Python 使用 `INDOOR_OFFICE` (n=2.0, σ=4.5)。  
  - 证据：`ns3_validation/aeris-validation-standalone.cc`；`src/realistic_channel_model.py`。  
> **影响**：PDR 差异可能来自模型，而非算法。  

### 3.6 NS-3 样本量不足
- `ns3_ablation_results.json` 中消融每变体仅 3 个种子，无法给出显著性结论。  
> **修正**：需提升至 n≥30。  

### 3.7 消融统计结论需更谨慎
- Python 消融数据显示 `no_cas > full` 但 **不显著**（p≈0.057）。  
> **修正**：应使用“趋势”而非“结论性”措辞。  

### 3.8 safety_fallback 会扭曲 CAS 统计
- `safety_fallback` 达到阈值时强制 DIRECT，若未单独计数，CAS 模式分布将被系统性偏置。  
  - 证据：`src/aeris_protocol.py:1274-1299`（`safety_override` 统计已存在）。  
> **修正**：必须输出 `safety_override_count` 并在消融分析中剔除/分层。  

### 3.9 可靠模式可能“抹平”真实 PDR
- `force_ctp_reliable` 会把本轮源包强制计为成功投递，导致端到端 PDR 被高估。  
> **修正**：结果必须标注 `reliability_mode/force_ctp_reliable` 状态，避免论文误用。  

---

## 4. 与我方审查相比的不足点（互相考虑不周）
### 同事考虑不足
1) **指标一致性**：NS-3 PDR 定义与 Python 不一致。  
2) **NS-3 实现简化**：无法直接验证 Python 模块贡献。  
3) **参数对齐缺失**：信道/能耗参数不同导致不可比。  
4) **样本量不足**：n=3 的 NS-3 消融无法支撑统计结论。  

### 我方此前考虑不足
1) **权重覆盖来源未强调**：应明确指出权重来自 `aeris_protocol.py` 覆盖。  
2) **消融与 CAS 诊断链接不足**：消融结果缺 CAS 统计时，应立即提出埋点要求。  
3) **跨平台“功能对齐策略”未明确**：需要明确“降级对齐”方案。

---

## 5. 详细改进计划（含 NS-3 验证）

### P0（必须先完成）
1) **CAS 诊断埋点**
   - 输出每轮/每簇 CAS 模式选择计数、切换率、置信度，**并显式记录 safety_override_count**。  
   - 产出：`results/cas_mode_stats_YYYYMMDD.json`。  

2) **统一端到端 PDR 口径**
   - Python 输出严格模式（缺失即 -1），并标注 `reliability_mode/force_ctp_reliable`。  
   - NS-3 增加端到端统计（源包数 vs BS 收包数）。  

3) **NS-3 参数对齐**
   - 信道：新增 `INDOOR_OFFICE` 参数与 Python 一致；  
   - 能耗：NS-3 改用 CC2420 参数（E_ELEC=208.8 nJ/bit）。  

4) **NS-3 逻辑对齐**
   - CAS/Gateway/Skeleton 功能对齐，或做“功能降级对照”。  

5) **权重来源统一与可追踪**
   - 输出每轮 effective_weights 与 stage_feature_scaling；  
   - 文档说明 “默认值/覆盖值/阶段自适应” 三者关系。  

### P1（强烈建议）
1) **CAS 权重/EMA 校准实验**
   - 比较 `ema_alpha=0.2/0.5/1.0`；  
   - 测试 “不覆盖权重” vs “覆盖权重”。  

2) **特征归一化修正**
   - density 基于簇面积；  
   - radius 使用簇内最大/分位数归一化。  

3) **NS-3 消融扩展**
   - n≥30，至少两拓扑（uniform/corridor）。  

### P2（论文策略）
1) **承认 CAS 局限性**
   - 以“negative result”形式报告。  
2) **突出 Gateway 贡献**
   - 给出显著性与效应量证据。  

---

## 6. 输出交付物（供审稿与复现）
- `docs/ns3_param_map.md`（参数对齐表）  
- `docs/ns3_alignment_checklist.md`（逻辑对齐清单）  
- `results/cas_mode_stats_YYYYMMDD.json`  
- `results/ns3_validation_YYYYMMDD.json`  
- `docs/validation_report.md`（Python vs NS-3 对齐报告）  

---

## 7. 结论（审查建议）
当前 DeepSearch 结论可作为**诊断假设**，但必须在 **NS-3 参数/逻辑对齐 + CAS 统计埋点 + 端到端口径一致** 后才能形成可写入论文的“验证结论”。  
优先顺序应与 `docs/2月1日gpt.md` 一致（任务2→任务3→任务6→任务1→任务4→任务5），并在此基础上完成 P0/P1/P2 改进链路。
