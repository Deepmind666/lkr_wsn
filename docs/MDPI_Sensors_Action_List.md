# MDPI Sensors 提交行动清单（AERIS）

目标：完成端到端性能修复与稿件更新，使稿件满足“纯算法、可复现”的审稿要求。

一、数据与脚本统一
- 统一实验入口：`scripts/run_experiments.py` 调用 `tests/test_integrated_eehfr.py`（现已改为 AERIS 集成测试）。
- 清理旧名：全面替换 `EEHFR`/`Enhanced-EEHFR` 文本与文件引用（README、脚本、实验对比）。
- Intel 回放默认真实几何：`scripts/run_intel_baselines_all.py` 默认 `use_synthetic=False`，缺失时打印显式警告并降级。

二、端到端计数修复与验证
- 代码层：`src/aeris_protocol.py` 已实现严格端到端计数（见 `docs/PDR_EndToEnd_Audit.md`）。
- 快速冒烟：`python scripts/run_experiments.py --test quick` 正常通过，基础流程未破坏。
- 批量重跑：刷新 `results/aether_*.json、compare_*.json`，记录 `bs_delivered_total/source_packets_total` 与 CAS 模式频度。

三、拓扑扩展与敏感性
- 节点数：扩展 50→100/200。
- 轮数：500–1000。
- 统计：记录 CAS 模式比例、能耗分解、FND 时刻；图表更新 `paper_multi_topo_sig_pdr.svg` 等。

四、图表与仓库
- 重新导出：`paper_intel_ablation_pdr.svg、paper_multi_topo_sig_pdr.svg`，并复制至 `for_submission/`。
- 链接修正：Supplementary Materials 链接更新为 `https://github.com/Deepmind666/AERIS-WSN-Protocol`（已完成）。

五、LaTeX 稿件修订
- 完成中文摘要、数据可用性、图表引用与标签；删除错误的 `\end{figure}`（已修正）。
- 在 `Results` 中保留占位符，待批量重跑后替换数值与图注。

六、风险提示与质量门槛
- 当前评估显示 AERIS 的 PDR/能耗劣于基准协议；需通过修复与调参验证是否为实现偏差而非算法缺陷。
- 若批量重跑后仍不达标，建议下调主张并定位为“算法框架 + 可复现实验计划”，以争取审稿认可。

里程碑与验收
- M1：端到端计数修复与冒烟（完成）。
- M2：Intel/多拓扑批量重跑与 JSON 更新（待做）。
- M3：图表再导出与 LaTeX 更新（待做）。
- M4：最终自检清单（脚本、链接、数据、图表一致）与投稿。