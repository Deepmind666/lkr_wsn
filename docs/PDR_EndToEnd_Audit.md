# AERIS 端到端 PDR 统计审计（代码级）

审计目标：验证 `src/aeris_protocol.py` 的 `_perform_data_transmission` 是否实现真正的端到端（BS）投递统计，并避免簇级聚合误计。

结论（通过代码走查）：
- 每轮源包计数：`alive_nodes` 数量在函数开头记录为 `self._last_source_packets_round = len(alive_nodes)`，与“每个活跃节点每轮产生一个数据包”的口径一致。
- 簇内聚合：
  - `handle_direct/handle_chain/handle_two_hop` 仅在簇内链路 `transmit_link(...)` 成功时累计到 `delivered_members`；`cluster_payloads[ch.id] = 1（CH自包） + delivered_members`。
  - 链式（CHAIN）实现保证只有首节点成功到 CH 时才将整条链的聚合载荷传递（避免中途失败仍计入）。
  - 两跳（TWO_HOP）对远端成员走中继、近端成员直达 CH，只有中继→CH 成功才把中继载荷汇入。
- 上行至 BS：
  - 统一通过 `transmit_to_bs(sender, payload_count, tx_power_override)` 实现；仅在成功时 `self._last_bs_delivered_round += payload_count`。
  - 支持 Gateway 模式：普通 CH 将载荷发往最近 gateway，gateway 再将累计载荷上行；失败时可根据 Safety 逻辑尝试冗余上行。
  - Skeleton 模式：当“远离 BS 的 CH 比例”达到阈值时选取骨干并分配聚合职责，否则直接上行。
- 轮末统计：
  - `_collect_round_statistics(...)` 中将 `self.source_packets_total += _last_source_packets_round` 和 `self.bs_delivered_total += _last_bs_delivered_round`，随后清零轮次缓存。
  - `run_simulation(...)` 返回 `packet_delivery_ratio_end2end = bs_delivered_total / source_packets_total`，语义正确。

能耗与分布：
- 每次簇内/上行链路调用分别扣减发送/接收能耗并累计到 `energy_consumed`。
- 保留跳数统计与 CAS 模式使用频度，便于结果诊断。

推荐验证用例（可作为单元/集成测试）：
- 直达簇（10 节点，理想信道 `pdr=1`）：当 Gateway/Skeleton 关闭时，轮次级 `e2e PDR = 1.0`，`bs_delivered_round = 10`。
- 链式聚合（5 节点，强制倒数第二跳失败）：`bs_delivered_round` 仅在首节点→CH 成功且链条完整时等于链长度，否则为失败前的成功聚合量。
- Gateway 聚合（3 个 CH，1 个 Gateway）：普通 CH 的载荷先汇入 Gateway，仅在 Gateway→BS 成功时合并计入 BS 投递。

潜在注意点：
- CAS 权重当前含少量硬编码调参（`_cas_cfg_tuned`），建议在实验脚本中记录并统一；不影响 PDR 统计语义。
- `cluster_payloads` 中 CH 自包的 1 计数若 CH 上行失败不会计入 BS 投递（符合端到端定义）。

结论：当前实现已满足端到端 PDR 的严格定义（仅最终到达 BS 的包才计入），杜绝了簇级成功即“过度乐观”的统计偏差。后续应通过批量回放和拓扑扩展验证数值表现。