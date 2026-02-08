## Supplementary Experimental Results

本文附录列出新增实验的关键数值，便于审稿人快速核查。所有原始 JSON 均位于 `results/` 目录，可由脚本自动生成。

> 历史文档中若仍引用 `C:\Enhanced-EEHFR-WSN-Protocol\...`，请参考 `docs/Legacy_Path_Mapping.md` 将路径映射到当前仓库结构。

### 1. Gateway 参数扫描（`scripts/run_gateway_sweep.py`）

| $k$ | $w_{dist}$ | $\mathrm{PDR}_{e2e}$ (mean ± std) | 能耗 (J, 平均) |
|---|---|---|---|
| 1 | -0.9 | 0.097 ± 0.010 | 148.2 |
| 1 | -0.7 | 0.096 ± 0.008 | 147.0 |
| 1 | -0.5 | 0.094 ± 0.007 | 146.6 |
| 1 | -0.3 | 0.083 ± 0.006 | 145.9 |
| 2 | -0.9 | 0.098 ± 0.009 | 147.8 |
| 2 | -0.7 | **0.085 ± 0.008** | 147.5 |
| 2 | -0.5 | 0.082 ± 0.006 | 146.3 |
| 2 | -0.3 | 0.074 ± 0.005 | 146.0 |
| 3 | -0.9 | 0.081 ± 0.006 | 146.2 |
| 3 | -0.7 | 0.079 ± 0.006 | 146.8 |
| 3 | -0.5 | 0.076 ± 0.005 | 146.0 |
| 3 | -0.3 | 0.071 ± 0.004 | 145.7 |
| 4 | -0.9 | 0.073 ± 0.004 | 147.9 |
| 4 | -0.7 | 0.070 ± 0.004 | 147.3 |
| 4 | -0.5 | 0.068 ± 0.004 | 147.1 |
| 4 | -0.3 | 0.065 ± 0.003 | 146.8 |

> 说明：每行由 5 次独立仿真统计所得；详细数值请参见 `results/gateway_sweep.json`。

> **最新脚本开关**：`scripts/run_gateway_sweep.py` 新增 `--gateway-concurrency`（限制同轮次可上行的 gateway 数）、`--gateway-limit` + `--gateway-limit-dynamic`（按失败率自适应收紧或放宽负载上限），所用参数会写入 JSON 的 `gateway_limit_trace` 与 `gateway_concurrency_avg` 字段，并在 AERIS `additional_metrics` 中留存 `gateway_load_limit_active` 与 `gateway_uplink_suppressed_total`，便于 Supplement 图表引用。

#### 1.1 大规模扩展（Uniform-300 / Uniform-500）

我们新增了两个扩展 sweep：

- `results/gateway_sweep_uniform300_ext_c1234.json` + `results/gateway_sweep_uniform300_ext_c68.json`（300 节点，面积 250×250 m，BS 在 (125,320)）。
- `results/gateway_sweep_uniform500_ext_c1234.json`（500 节点，面积 320×320 m，BS 在 (160,420)）。

每个配置运行 3 次独立复现（200 轮），下表列出 CH$\rightarrow$BS 成功率最高的若干组合：

| 场景 | $k$ | $w_{dist}$ | $\mathrm{PDR}_{\mathrm{CH}\rightarrow\mathrm{BS}}$ | $\mathrm{PDR}_{e2e}$ | 能耗 (J) |
|---|---|---|---|---|---|
| Uniform-300 | 8 | -0.7 | 0.242 | 0.057 | 224.76 |
| Uniform-300 | 3 | -0.7 | 0.239 | 0.059 | 224.21 |
| Uniform-300 | 1 | -0.3 | 0.239 | 0.056 | 225.06 |
| Uniform-300 | 1 | -0.9 | 0.236 | 0.059 | 226.63 |
| Uniform-300 | 2 | -0.9 | 0.235 | 0.057 | 227.46 |
| Uniform-500 | 2 | -0.5 | 0.141 | 0.027 | 409.75 |
| Uniform-500 | 4 | -0.7 | 0.140 | 0.024 | 402.10 |
| Uniform-500 | 4 | -0.3 | 0.137 | 0.024 | 406.15 |

> 结论：单基站 + 多 gateway 的 CH$\rightarrow$BS 成功率在 300 节点场景最高约 0.24，在 500 节点场景最高约 0.14，距离 Section~\ref{sec:conclusion} 中“Uniform-300 $\ge 0.40$ / Uniform-500 $\ge 0.20$” 的目标仍有显著差距。后续实验计划转向 skeleton 半径调整与多基站配置。

##### 多基站扩展（南北双 BS）

为进一步验证多基站策略，我们在 Uniform-300 与 Uniform-500 场景中为 AERIS 配置了第二个基站，分别位于 (125,-20) 与 (160,-20)，构成“北/南”双 BS。对应 JSON：

- `results/gateway_sweep_uniform300_dualbs_k468.json`
- `results/gateway_sweep_uniform500_dualbs_k468.json`

| 场景 | $k$ | $w_{dist}$ | $\mathrm{PDR}_{\mathrm{CH}\rightarrow\mathrm{BS}}$ | $\mathrm{PDR}_{e2e}$ | 能耗 (J) |
|---|---|---|---|---|---|
| Uniform-300 + dual BS | 8 | -0.7 | **0.498** | 0.102 | 224.8 |
| Uniform-300 + dual BS | 6 | -0.3 | 0.459 | 0.096 | 224.6 |
| Uniform-300 + dual BS | 8 | -0.9 | 0.455 | 0.093 | 225.1 |
| Uniform-500 + dual BS | 4 | -0.5 | **0.480** | 0.066 | 409.7 |
| Uniform-500 + dual BS | 6 | -0.3 | 0.474 | 0.065 | 411.1 |
| Uniform-500 + dual BS | 8 | -0.9 | 0.474 | 0.063 | 407.8 |

> 双基站大幅提升了 CH$\rightarrow$BS 成功率：300 节点场景可达 0.50，500 节点场景约 0.48。但端到端 PDR 仍仅在 0.09--0.10（300 节点）与 0.06--0.07（500 节点）之间，说明多基站虽然缓解了长距离上行，但簇内拥塞与 gateway 堆积仍限制整体吞吐；下一步将结合 skeleton 半径调整与多链路调度进一步压缩损失。

进一步，将 skeleton 连通阈值从 $d_{\text{th}}/\mathrm{diag}=0.15$ 降至 $0.08$、$q_{\text{far}}$ 从 0.75 调整为 0.60（JSON：`results/gateway_sweep_uniform300_dualbs_skeleton.json`, `results/gateway_sweep_uniform500_dualbs_skeleton.json`），得到：

| 场景 | $k$ | $w_{dist}$ | $\mathrm{PDR}_{\mathrm{CH}\rightarrow\mathrm{BS}}$ | $\mathrm{PDR}_{e2e}$ | 能耗 (J) |
|---|---|---|---|---|---|
| Uniform-300 + dual BS + 小半径 | 8 | -0.7 | 0.478 | 0.097 | 224.7 |
| Uniform-300 + dual BS + 小半径 | 6 | -0.7 | 0.465 | 0.094 | 224.3 |
| Uniform-500 + dual BS + 小半径 | 6 | -0.7 | 0.468 | 0.067 | 411.7 |
| Uniform-500 + dual BS + 小半径 | 8 | -0.3 | 0.464 | 0.062 | 405.3 |

> Skeleton 半径收紧后，CH$\rightarrow$BS 成功率保持在 0.46--0.48，但端到端 PDR 并未明显改善（反而略有下降），说明当前瓶颈主要是 gateway 争用与簇内拥塞，未来需要结合多链路调度或骨干再平衡策略。

##### Gateway 负载限额（Uniform-300，双 BS）

利用新增的 `--gateway-limit` 选项，我们对 $k=8$ 情况做了复现实验（JSON：`results/gateway_sweep_uniform300_dualbs_limit{1,2,3,4}.json`），限制每个 gateway 同轮次内可服务的簇数。结果如下：

| $L_{\text{gw}}$ | $\max \mathrm{PDR}_{\mathrm{CH}\rightarrow\mathrm{BS}}$ | 对应配置 | $\max \mathrm{PDR}_{e2e}$ |
|---|---|---|---|
| 1 | **0.502** | $k=8, w_{dist}=-0.5$ | **0.105** |
| 2 | 0.468 | $k=8, w_{dist}=-0.5$ | 0.101 |
| 3 | 0.463 | $k=8, w_{dist}=-0.3$ | 0.096 |
| 4 | 0.486 | $k=8, w_{dist}=-0.5$ | 0.101 |

> 限额 $L_{\text{gw}}=1$（即严格单簇接入）时，端到端 PDR 可提升至 0.105，随后随限额增大逐渐回落，说明 gateway 争用确实是当前瓶颈之一。下一步将探索自适应限额或多 gateway 并发上行策略。

同样的 sweep 也在 Uniform-500 双 BS 场景中执行（JSON：`results/gateway_sweep_uniform500_dualbs_limit{1,2,3,4}.json`）：

| $L_{\text{gw}}$ | $\max \mathrm{PDR}_{\mathrm{CH}\rightarrow\mathrm{BS}}$ | 对应配置 | $\max \mathrm{PDR}_{e2e}$ |
|---|---|---|---|
| 1 | 0.470 | $k=8, w_{dist}=-0.9$ | 0.068 |
| 2 | **0.485** | $k=8, w_{dist}=-0.3$ | **0.071** |
| 3 | 0.491 | $k=8, w_{dist}=-0.7$ | 0.064 |
| 4 | 0.477 | $k=8, w_{dist}=-0.5$ | 0.066 |

> Uniform-500 的端到端提升幅度较小（最高 0.071），但依旧比无限制情形的 0.066 稍有改进，证明适度限额能缓解 gateway 串扰。后续将结合 skeleton 调参与分布式多 gateway 上行进一步探索。

将限额与骨干压缩（$d_{\text{th}}/\mathrm{diag}=0.08$, $q_{\text{far}}=0.60$）结合后，Uniform-300 的最佳配置为 $k=8,w_{dist}=-0.7$（$\mathrm{PDR}_{\text{CH}\rightarrow\text{BS}}=0.490$, $\mathrm{PDR}_{e2e}=0.102$, `results/gateway_sweep_uniform300_dualbs_limit1_skeleton.json`），Uniform-500 对应 $k=8,w_{dist}=-0.3$（$\mathrm{PDR}_{\text{CH}\rightarrow\text{BS}}=0.453$, $\mathrm{PDR}_{e2e}=0.064$, `results/gateway_sweep_uniform500_dualbs_limit1_skeleton.json`）。相比无骨干压缩时的 0.105/0.068 幅度有限，表明限额带来的收益主要来自中继争用的缓解，而非骨干半径。

![Gateway limit heatmaps for dual-BS experiments（横轴为 $L_{\mathrm{gw}}$，纵轴列出默认/骨干压缩两组场景，颜色表示最佳端到端 PDR；文件：`results/plots/paper_gateway_limit_heatmap_combined.pdf`）](../results/plots/paper_gateway_limit_heatmap_combined.pdf)

> 图 S1 直观展示了不同限额下的最佳端到端 PDR：300 节点场景在 $L_{\mathrm{gw}}=1$ 达到峰值，而 500 节点在 $L_{\mathrm{gw}}=2$ 略优；骨干压缩整体呈现平移而非抬升，进一步佐证 gateway 拥塞才是当前主要瓶颈。

##### Gateway 并发 + 自适应限额诊断（双基站）

针对并发 uplink，我们在 Uniform-300/500 场景中分别运行了 `--gateway-concurrency 2/4` 的 sweep（含较“温和”限额窗口 150、reduce=0.6 的变体；JSON：`results/gateway_sweep_uniform300_dualbs_concurrency{2,4}.json`、`results/gateway_sweep_uniform300_dualbs_conc4_relaxed.json`、`results/gateway_sweep_uniform500_dualbs_concurrency{2,4}.json`、`results/gateway_sweep_uniform500_dualbs_conc4_relaxed.json`），并用脚本 `python scripts/plot_gateway_concurrency_effect.py` 生成 Figure~\ref{fig:gateway_concurrency_effect}，`python scripts/plot_gateway_concurrency_heatmap.py` 生成热图 Figure~\ref{fig:gateway_concurrency_heatmap}。表 S2 给出最佳端到端 PDR 及诊断数据：

| 场景 | 并发上限 $C$ | 最优配置 (key) | $\mathrm{PDR}_{e2e}$ | $\mathrm{PDR}_{\text{CH}\rightarrow\text{BS}}$ | $\overline{L_{gw}}$（运行平均） | $L_{gw}=1$ 占比 | 实际并发利用（平均） |
|---|---|---|---|---|---|---|---|
| Uniform-300 dual BS | 2 | `k6_wd-0.3` | 0.1016 | 0.482 | 1.32 | 0.81 | 1.0 |
| Uniform-300 dual BS | 4 | `k6_wd-0.9` | 0.1017 | 0.502 | 1.32 | 0.81 | 1.0 |
| Uniform-300 dual BS | 4（窗口150, reduce=0.6） | `k4_wd-0.5` | 0.1026 | 0.507 | 1.67 | 0.60 | 1.0 |
| Uniform-500 dual BS | 2 | `k6_wd-0.3` | 0.0654 | 0.464 | 1.21 | 0.87 | 1.0 |
| Uniform-500 dual BS | 4 | `k8_wd-0.9` | 0.0663 | 0.476 | 1.21 | 0.87 | 1.0 |
| Uniform-500 dual BS | 4（窗口150, reduce=0.6） | `k8_wd-0.5` | 0.0640 | 0.457 | 1.42 | 0.74 | 1.0 |

> 尽管允许两/四个 gateway 并发上行，动态限额在几十次失败后迅速降到 1，使得 `gateway_concurrency_avg` 始终为 1.0。换言之，现有限额策略会过早地禁止第二条 uplink，导致并发参数无法发挥作用。Figure~\ref{fig:gateway_concurrency_effect} 中的折线显示运行期间的平均 $L_{gw}$ 仅 1.2–1.3，柱状图则表明端到端 PDR 仍停留在 0.10/0.07 左右。后续实验将尝试提高 `--gateway-limit-reduce` 阈值、延长窗口或加入簇内调度，以避免自适应限额与并发策略“互相抵消”。
> 尽管允许两/四个 gateway 并发上行，动态限额在几十次失败后迅速降到 1，使得 `gateway_concurrency_avg` 始终为 1.0。换言之，现有限额策略会过早地禁止第二条 uplink，导致并发参数无法发挥作用。Figure~\ref{fig:gateway_concurrency_effect} 与 Figure~\ref{fig:gateway_concurrency_heatmap} 显示，放宽窗口/阈值后平均 $L_{gw}$ 可抬升到 1.4–1.7、$L_{gw}=1$ 占比降到 0.60–0.74，但端到端 PDR 依旧停留在 0.10/0.07 左右，证明单纯放宽限额不足以解锁并发收益，需结合簇内调度或多链路策略。

![Gateway concurrency heatmap（横轴为并发配置标签，纵轴为场景；颜色为最佳 $\mathrm{PDR}_{e2e}$，注释包含 CH→BS、平均 $L_{gw}$、$L_{gw}=1$ 占比；文件：`results/plots/paper_gateway_concurrency_heatmap.pdf`）](../results/plots/paper_gateway_concurrency_heatmap.pdf)

### 2. 动态走廊（节点平移 + Intel 信道）

| Phase | 位移 (m) | $\mathrm{PDR}_{e2e}$ (Energy) | $\mathrm{PDR}_{e2e}$ (Robust) | Hop-level PDR | 能耗 (J) |
|---|---|---|---|---|---|
| phase1_static | 0 | 0.486 | 0.498 | 0.88 | 59.5 |
| phase2_shift | +20 | 0.484 | **0.545** | 0.89 | 59.0 |
| phase3_shift | +40 | **0.520** | 0.469 | 0.86 | 59.9 |
| phase4_shift | +60 | 0.437 | 0.497 | 0.87 | 59.5 |

> 数据来源：`results/dynamic_corridor_compare_reps.json`（生成命令：`python scripts/run_dynamic_corridor_compare.py --replicates 5 --seed-stride 500`）。

### 3. 动态基站（BS 平移）

| Phase | BS 位置 (m) | $\mathrm{PDR}_{e2e}$ | Hop-level PDR | 能耗 (J) |
|---|---|---|---|---|
| bs_phase1 | 260 | 0.531 | 0.873 | 58.9 |
| bs_phase2 | 300 | 0.512 | 0.861 | 59.1 |
| bs_phase3 | 340 | 0.497 | 0.853 | 59.3 |
| bs_phase4 | 380 | 0.476 | 0.846 | 59.5 |

> 所有数据可通过 `python scripts/run_dynamic_moving_bs_compare.py` 重新生成，详见 `results/dynamic_moving_bs_compare_reps.json`（若仅需单次运行，可检查 `_compare.json`）。

### 4. 随机失联场景

| Phase | 失效比例 | $\mathrm{PDR}_{e2e}$ | Hop PDR | 能耗 (J) |
|---|---|---|---|---|
| drop0 | 0% | 0.524 | 0.882 | 63.1 |
| drop10 | 10% | 0.503 | 0.861 | 59.5 |
| drop20 | 20% | 0.471 | 0.842 | 55.8 |
| drop30 | 30% | 0.432 | 0.812 | 51.2 |

数据来自 `results/dynamic_dropout_compare_reps.json`。

### 4.1 平均统计

针对走廊/移动基站/随机失联三个动态场景，我们在 `results/dynamic_*_compare_reps.json` 中提供了 5 组、种子相差 500 的复现实验。主文中的 Figure~3--5（`paper_dynamic_*.pdf`）直接读取这些 JSON，并显示均值曲线及 $\pm1\sigma$ 的阴影区域；Figure~6（`paper_dynamic_pdr_boxplots.pdf`）则对同一批复现结果的均值做箱线+散点展示。平均 PDR、能耗、存活节点的表格位于 `results/for_submission/dynamic_stats_summary.md`，由 `python scripts/summarize_dynamic_stats.py` 自动生成。利用这些复现实验的阶段级样本，`python scripts/compute_dynamic_significance.py` 会写出 `results/for_submission/dynamic_significance.md`，内含 AERIS（energy/robust）与各经典协议之间的 Welch $t$ 检验、Cohen's $d$，并附上 Holm--Bonferroni（FWER）与 Benjamini--Hochberg（FDR）两种校正后的 $p$ 值。另一方面，`python scripts/compute_aeris_round_significance.py` 基于轮次级数据输出 `results/for_submission/aeris_round_significance.md`，用于评估 AERIS energy 与 robust 两种配置之间的统计差异。

### 4.2 AERIS energy vs robust（轮次级 Welch $t$）

| 场景 | $\mu_E \pm \sigma_E$ | $\mu_R \pm \sigma_R$ | $t$ | $p$ | Cohen's $d$ |
|---|---|---|---|---|---|
| Corridor phase shifts | $0.459 \pm 0.347$ | $0.487 \pm 0.331$ | $3.639$ | $2.75\times10^{-4}$ | $0.081$ |
| Moving BS corridor | $0.402 \pm 0.354$ | $0.447 \pm 0.343$ | $5.801$ | $6.83\times10^{-9}$ | $0.130$ |
| Random dropout | $0.307 \pm 0.362$ | $0.367 \pm 0.358$ | $9.186$ | $4.75\times10^{-20}$ | $0.168$ |

> 数据来自 `results/for_submission/aeris_round_significance.md`，由 `python scripts/compute_aeris_round_significance.py` 生成。

### 4.3 动态场景跨协议检验（Supplementary Table S2）

表 S2 直接嵌入 `results/for_submission/dynamic_significance.md` 的结果，审稿人无需额外脚本即可查看完整的 Holm–Bonferroni / BH-FDR 纠正值与效应量。所有对比均基于 $n=20$ 样本（5 次复现 $\times$ 4 阶段），与主文 Figure~2--4 的阴影/箱线图保持一致。主文仅列出代表性的 LEACH 行，完整表格如下。

**Corridor phase shifts（Table S2a）**

| Baseline | Target | $t$ | dof | $p$ | $p_{\mathrm{Holm}}$ | $p_{\mathrm{BH}}$ | Cohen's $d$ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LEACH | AERIS\_energy | -73.652 | 19.149 | $5.78\times10^{-25}$ | $1.30\times10^{-24}$ | $7.29\times10^{-25}$ | -23.291 |
| LEACH | AERIS\_robust | -80.909 | 19.201 | $8.48\times10^{-26}$ | $6.38\times10^{-25}$ | $2.39\times10^{-25}$ | -25.586 |
| HEED | AERIS\_energy | -74.548 | 19.004 | $6.48\times10^{-25}$ | $1.30\times10^{-24}$ | $7.29\times10^{-25}$ | -23.574 |
| HEED | AERIS\_robust | -81.992 | 19.005 | $1.06\times10^{-25}$ | $6.38\times10^{-25}$ | $2.39\times10^{-25}$ | -25.928 |
| PEGASIS | AERIS\_energy | -74.648 | 19.000 | $6.37\times10^{-25}$ | $1.30\times10^{-24}$ | $7.29\times10^{-25}$ | -23.606 |
| PEGASIS | AERIS\_robust | -82.109 | 19.000 | $1.05\times10^{-25}$ | $6.38\times10^{-25}$ | $2.39\times10^{-25}$ | -25.965 |
| TEEN | AERIS\_energy | -74.648 | 19.000 | $6.37\times10^{-25}$ | $1.30\times10^{-24}$ | $7.29\times10^{-25}$ | -23.606 |
| TEEN | AERIS\_robust | -82.109 | 19.000 | $1.05\times10^{-25}$ | $6.38\times10^{-25}$ | $2.39\times10^{-25}$ | -25.965 |
| AERIS\_energy | AERIS\_robust | 2.885 | 37.200 | $5.96\times10^{-3}$ | $5.96\times10^{-3}$ | $5.96\times10^{-3}$ | 0.912 |

**Moving BS corridor（Table S2b）**

| Baseline | Target | $t$ | dof | $p$ | $p_{\mathrm{Holm}}$ | $p_{\mathrm{BH}}$ | Cohen's $d$ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LEACH | AERIS\_energy | -20.394 | 19.077 | $2.05\times10^{-14}$ | $4.10\times10^{-14}$ | $2.31\times10^{-14}$ | -6.449 |
| LEACH | AERIS\_robust | -24.079 | 19.126 | $9.08\times10^{-16}$ | $5.45\times10^{-15}$ | $2.04\times10^{-15}$ | -7.614 |
| HEED | AERIS\_energy | -20.686 | 19.004 | $1.72\times10^{-14}$ | $4.10\times10^{-14}$ | $2.21\times10^{-14}$ | -6.541 |
| HEED | AERIS\_robust | -24.465 | 19.006 | $7.88\times10^{-16}$ | $5.45\times10^{-15}$ | $2.04\times10^{-15}$ | -7.737 |
| PEGASIS | AERIS\_energy | -20.162 | 19.843 | $1.10\times10^{-14}$ | $4.10\times10^{-14}$ | $1.98\times10^{-14}$ | -6.376 |
| PEGASIS | AERIS\_robust | -23.654 | 20.379 | $2.70\times10^{-16}$ | $2.43\times10^{-15}$ | $2.04\times10^{-15}$ | -7.480 |
| TEEN | AERIS\_energy | -20.744 | 19.000 | $1.64\times10^{-14}$ | $4.10\times10^{-14}$ | $2.21\times10^{-14}$ | -6.560 |
| TEEN | AERIS\_robust | -24.541 | 19.000 | $7.50\times10^{-16}$ | $5.45\times10^{-15}$ | $2.04\times10^{-15}$ | -7.760 |
| AERIS\_energy | AERIS\_robust | 1.237 | 35.900 | $2.24\times10^{-1}$ | $2.24\times10^{-1}$ | $2.24\times10^{-1}$ | 0.391 |

**Random dropout（Table S2c）**

| Baseline | Target | $t$ | dof | $p$ | $p_{\mathrm{Holm}}$ | $p_{\mathrm{BH}}$ | Cohen's $d$ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LEACH | AERIS\_energy | -14.747 | 19.000 | $7.42\times10^{-12}$ | $3.79\times10^{-11}$ | $1.68\times10^{-11}$ | -4.663 |
| LEACH | AERIS\_robust | -13.979 | 19.000 | $1.89\times10^{-11}$ | $3.79\times10^{-11}$ | $2.13\times10^{-11}$ | -4.421 |
| HEED | AERIS\_energy | -14.743 | 19.000 | $7.45\times10^{-12}$ | $3.79\times10^{-11}$ | $1.68\times10^{-11}$ | -4.662 |
| HEED | AERIS\_robust | -13.976 | 19.000 | $1.90\times10^{-11}$ | $3.79\times10^{-11}$ | $2.13\times10^{-11}$ | -4.420 |
| PEGASIS | AERIS\_energy | -14.747 | 19.000 | $7.42\times10^{-12}$ | $3.79\times10^{-11}$ | $1.68\times10^{-11}$ | -4.663 |
| PEGASIS | AERIS\_robust | -13.979 | 19.000 | $1.89\times10^{-11}$ | $3.79\times10^{-11}$ | $2.13\times10^{-11}$ | -4.421 |
| TEEN | AERIS\_energy | -14.747 | 19.000 | $7.42\times10^{-12}$ | $3.79\times10^{-11}$ | $1.68\times10^{-11}$ | -4.663 |
| TEEN | AERIS\_robust | -13.979 | 19.000 | $1.89\times10^{-11}$ | $3.79\times10^{-11}$ | $2.13\times10^{-11}$ | -4.421 |
| AERIS\_energy | AERIS\_robust | 0.925 | 37.946 | $3.61\times10^{-1}$ | $3.61\times10^{-1}$ | $3.61\times10^{-1}$ | 0.293 |

> Supplementary Table S2（a–c）对应主文 Table~\ref{tab:dynamic_significance} 的扩展版本；若需验证可执行 `python scripts/compute_dynamic_significance.py --output results/for_submission/dynamic_significance.md`。

### 5. 大规模长时仿真

| 拓扑 | 配置 | $\mathrm{PDR}_{e2e}$ | Hop PDR | 能耗 (J) |
|---|---|---|---|---|
| Uniform-300 | AERIS energy | 0.0205 | 0.665 | 1129.7 |
|  | AERIS robust | 0.0466 | 0.657 | 1131.6 |
| Uniform-500 | AERIS energy | 0.0079 | 0.631 | 1967.9 |
|  | AERIS robust | 0.0170 | 0.618 | 1966.4 |

基于 `results/gateway_sweep.json` 与 `results/gateway_sweep_uniform500.json`，我们进一步绘制了 gateway 参数热图（`python scripts/plot_gateway_heatmap.py`，输出 `results/plots/gateway_sweep*_*.pdf`），对比不同 $k$ 与 $w_{dist}$ 对 end-to-end PDR、CH$\rightarrow$BS PDR、Gateway$\rightarrow$BS PDR 的影响。如图所示，200 节点场景在 $(k=1,w_{dist}=-0.5)$ 附近可实现 $0.415$ 的 CH$\rightarrow$BS 成功率，但 500 节点场景在 $(k=4,w_{dist}=-0.9)$ 也仅约 $0.149$，说明要达到 Section~\ref{sec:conclusion} 中提出的“Uniform-300 $\ge 0.40$ / Uniform-500 $\ge 0.20$” 目标还需引入多基站或骨干增强策略。

### 6. Monte Carlo（50×100）

| 配置 | $\mu \pm \sigma$ (PDR) |
|---|---|
| AERIS energy | $0.772 \pm 0.024$ |
| AERIS robust | $0.787 \pm 0.021$ |

| 统计量 | 数值 |
|---|---|
| Welch $t$ | $4.946$ |
| dof | $195.5$ |
| two-sided $p$ | $1.63\times10^{-6}$ |
| Cohen's $d$ | $0.700$ |

> 详见 `results/for_submission/monte_carlo_stats.md`，由 `python scripts/compute_monte_carlo_stats.py` 生成；原始样本存放在 `results/monte_carlo_uniform50.json`。

### 7. 可复现元数据

| 场景 / 图表 | 关键脚本（命令示例） | 种子 / 复现设置 | 主要输出 | 关联图表 / 表格 |
|---|---|---|---|---|
| Intel replay baselines | `python scripts/run_intel_baselines_all.py` | 真实轨迹（无额外随机） | `results/intel_baselines_all.json`, `paper_intel_baselines_*.pdf` | Figures 1–2 |
| 50×100 合成基线 + Monte Carlo | `python scripts/run_monte_carlo_uniform.py` | $100$ seeds (0–99) | `results/monte_carlo_uniform50.json`, `results/for_submission/monte_carlo_stats.md` | Figure~\ref{fig:monte_carlo_uniform}, Monte Carlo stats |
| 动态走廊（phase shift） | `python scripts/run_dynamic_corridor_compare.py --replicates 5 --seed-stride 500 --output results/dynamic_corridor_compare_reps.json` | 基础种子 $55000 + 500 \times$rep | `results/dynamic_corridor_compare_reps.json` | Figures~\ref{fig:dynamic_corridor}, \ref{fig:dynamic_pdr_boxplots}, \ref{fig:dynamic_phase_breakdown} |
| 移动基站走廊 | `python scripts/run_dynamic_moving_bs_compare.py --replicates 5 --seed-stride 500 --output results/dynamic_moving_bs_compare_reps.json` | 基础种子 $56000 + 500 \times$rep | `results/dynamic_moving_bs_compare_reps.json` | Figure~\ref{fig:dynamic_moving_bs}, \ref{fig:dynamic_phase_breakdown} |
| 随机失联压力测试 | `python scripts/run_dynamic_dropout_compare.py --replicates 5 --seed-stride 500 --output results/dynamic_dropout_compare_reps.json` | 基础种子 $90001 + 500 \times$rep，失联率 0/10/20/30% | `results/dynamic_dropout_compare_reps.json` | Figure~\ref{fig:dynamic_dropout}, \ref{fig:dynamic_phase_breakdown} |
| 大规模 1000 轮仿真 | `python scripts/run_large_scale_long.py` | Uniform-300 使用 seed 81001，Uniform-500 使用 seed 82001 | `results/large_scale_long.json` | Figures~\ref{fig:large_scale_long}, \ref{fig:pdr_breakdown_large_scale}, \ref{fig:round_diagnostics_large_scale} |
| 诊断图（PDR breakdown + round density） | `python scripts/plot_pdr_breakdown_diagnostics.py`；`python scripts/plot_round_diagnostics.py` | 读取上一行的 JSON（无额外随机） | `paper_pdr_breakdown_large_scale.pdf`, `paper_round_diagnostics_large_scale.pdf` | Figures~\ref{fig:pdr_breakdown_large_scale}, \ref{fig:round_diagnostics_large_scale} |
| 动态结构诊断 | `python scripts/plot_dynamic_diagnostics.py` | 读取 `results/dynamic_*_compare_reps.json` | `paper_dynamic_diagnostics.pdf` | Figure~\ref{fig:dynamic_diagnostics} |
| Gateway 并发诊断 | `python scripts/plot_gateway_concurrency_effect.py` | 读取 `results/gateway_sweep_uniform{300,500}_dualbs_concurrency{2,4}.json` | `paper_gateway_concurrency_effect.pdf/.svg` | Figure~\ref{fig:gateway_concurrency_effect} |

> 上述表格由 `docs/reproduction_manifest.json` 经 `python scripts/generate_reproduction_table.py` 自动生成（产物见 `docs/Reproduction_Table.md`），投稿前可一键刷新以保持脚本与表格同步。

> 额外图表（如 sensitivity、gateway heatmaps 等）沿用相同格式：运行 `scripts/run_*` 生成 JSON，然后调用 `scripts/plot_*` 导出 SVG/PDF。命令行输出会记录 seed/配置，便于审稿人复核。
