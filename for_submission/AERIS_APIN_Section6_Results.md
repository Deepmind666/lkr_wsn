# Section 6: Results and Analysis

---

## 6. Results and Analysis

This section reports publication-tier results (n=30). All PDR values use
pdr_expected (bs_delivered / source_packets_expected).

### 6.1 Multi-Environment 5-Protocol Comparison (n=30)

Data source:  
C:\AERIS-WSN-Protocol\results\mega_experiments\env_sensitivity_20260207_205317.json

**Table 6.1: PDR by Environment (mean +/- std)**

| Environment | AERIS | LEACH | PEGASIS | HEED | TEEN |
|---|---|---|---|---|---|
| indoor_office | 0.9739+/-0.0047 | 0.5543+/-0.0401 | 0.9078+/-0.0166 | 0.9371+/-0.0076 | 0.8222+/-0.0044 |
| indoor_factory | 0.6031+/-0.0258 | 0.1614+/-0.0209 | 0.1928+/-0.0255 | 0.2326+/-0.0263 | 0.3113+/-0.0245 |
| outdoor_urban | 0.3745+/-0.0354 | 0.0552+/-0.0127 | 0.0542+/-0.0117 | 0.0635+/-0.0121 | 0.1201+/-0.0183 |
| outdoor_suburban | 0.7451+/-0.0193 | 0.2703+/-0.0272 | 0.3382+/-0.0329 | 0.4221+/-0.0313 | 0.4752+/-0.0236 |

**Key finding**: At 100 nodes (n=30), AERIS achieves the highest PDR in all four environments.

**Figure 6.1**  
C:\AERIS-WSN-Protocol\for_submission\figures\fig1_multienv_protocol_comparison_20260206_025510.pdf  
Error bars = std (n=30).

### 6.2 CAS Weight Sweep (n=30)

Data source:  
C:\AERIS-WSN-Protocol\results\mega_experiments\cas_weight_sweep_full_20260206_000736.json

**Table 6.2: CHAIN/TWO_HOP Trigger Rates and PDR**

**Indoor Office**

| Weight Config | CHAIN Rate | TWO_HOP Rate | PDR |
|---|---|---|---|
| baseline_default | 5.03% | 0.09% | 98.43% |
| aggressive_multimode | 7.50% | 0.15% | 98.27% |
| score_favor_chain | 99.98% | 0% | 95.85% |

**Sparse Outdoor**

| Weight Config | CHAIN Rate | TWO_HOP Rate | PDR |
|---|---|---|---|
| baseline_default | 14.30% | 0% | 89.80% |
| aggressive_multimode | 27.55% | 0.15% | 84.30% |
| score_favor_chain | 99.93% | 0% | 76.11% |

**Key finding**: Higher CHAIN trigger rates correlate with lower PDR in sparse
environments.

### 6.3 Multi-Environment Ablation (n=30)

Data source:  
C:\AERIS-WSN-Protocol\results\mega_experiments\ablation_diag_multi_20260207_205448.json

**Table 6.3: Full vs No-Gateway PDR (mean +/- std)**

| Environment | Full | No Gateway | Diff (NoGW - Full) |
|---|---|---|---|
| indoor_office | 0.9739+/-0.0047 | 0.9741+/-0.0036 | +0.0002 |
| indoor_factory | 0.6031+/-0.0258 | 0.5806+/-0.0215 | -0.0225 |
| outdoor_urban | 0.3745+/-0.0354 | 0.3534+/-0.0301 | -0.0212 |
| outdoor_suburban | 0.7451+/-0.0193 | 0.7306+/-0.0264 | -0.0146 |

**Key finding**: Gateway contribution is environment-dependent under the current setup:
it is statistically positive in indoor_factory, outdoor_urban, and outdoor_suburban,
and near-neutral in indoor_office.

**Additional ablation notes (diff vs full)**:
- no_cas: mixed effect (largest positive shift in outdoor_urban; non-significant in the other three environments)
- no_skeleton: ~0.000 (no measurable effect in this setup)
- no_safety: ~0.000 (no measurable effect in this setup)

**Figure 6.2**  
C:\AERIS-WSN-Protocol\for_submission\figures\fig2_ablation_heatmap_20260206_025510.pdf

**Figure 6.3**
C:\AERIS-WSN-Protocol\for_submission\figures\fig3_gateway_effect_20260206_025510.pdf

### 6.4 Scalability Analysis (100-1000 nodes, n=60)

Data source:
C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\

Scalability experiments use 60 independent seeds per configuration across six node counts (100, 200, 300, 500, 800, 1000) and four channel environments. Statistical significance is assessed via Welch's t-test with Holm-Bonferroni correction.

**Table 6.4: Protocol Ranking at 1000 Nodes (PDR, n=60)**

| Environment | AERIS | LEACH | PEGASIS | HEED | TEEN | AERIS Rank |
|---|---|---|---|---|---|---|
| indoor_office | 0.990 | 0.990 | **0.999** | 0.991 | 0.992 | 5th |
| indoor_factory | **0.990** | 0.406 | 0.613 | 0.367 | 0.501 | 1st |
| outdoor_urban | **0.990** | 0.155 | 0.272 | 0.130 | 0.203 | 1st |
| outdoor_suburban | **0.990** | 0.593 | 0.791 | 0.547 | 0.695 | 1st |

**Key finding**: AERIS ranks first in 3/4 environments across all tested scales (100-1000 nodes). In indoor_office, PEGASIS achieves significantly higher PDR than AERIS at all node counts >=500 (Hedges' g = -8.88 to -5.36, Holm-corrected p < 0.001). This is consistent with PEGASIS's chain-based design being well-suited to low-loss indoor channels.

Full statistical details: `scalability_significance_table.csv` and `scalability_significance_summary.md`.

### 6.5 Latency Analysis: Hop Count to Base Station (n=30)

Data source:
- latency_indoor_office_20260209_132945.json
- latency_indoor_factory_20260209_133051.json
- latency_outdoor_urban_20260209_133155.json
- latency_outdoor_suburban_20260209_133257.json
- latency_hop_v2_stats.csv
- latency_hop_v2_significance.csv

Setup: 100 nodes, 200x200m, 300 rounds, 30 independent seeds per environment.
Metric: avg_hops_to_bs (average transmission hops per successfully delivered source packet).

**Table 6.5: Average Hop Count to BS (mean +/- std, n=30)**

| Environment | AERIS | LEACH | PEGASIS | HEED | TEEN |
|---|---|---|---|---|---|
| indoor_office | 1.99+/-0.01 | 1.82+/-0.03 | 33.67+/-0.62 | 2.00+/-0.00 | 1.28+/-0.04 |
| indoor_factory | 1.97+/-0.02 | 1.71+/-0.05 | 32.22+/-1.93 | 2.00+/-0.00 | 1.29+/-0.05 |
| outdoor_urban | 1.97+/-0.02 | 1.55+/-0.08 | 31.47+/-2.66 | 2.00+/-0.00 | 1.23+/-0.05 |
| outdoor_suburban | 1.98+/-0.02 | 1.77+/-0.04 | 32.46+/-1.55 | 2.00+/-0.00 | 1.30+/-0.05 |

**Interpretation**:

- AERIS stays near two hops (member->CH->BS) with occasional 1-hop direct and 3-hop reliable-mode paths, yielding a mean of ~1.97-1.99.
- HEED reports exactly 2.00+/-0.00 because its protocol design routes all packets through a cluster head (member->CH->BS); there is no direct-to-BS path in HEED, so the hop count is deterministically 2.
- LEACH averages ~1.55-1.82 hops because non-CH nodes that fail to join a cluster transmit directly to BS (1-hop), mixing with the 2-hop CH-aggregated path.
- PEGASIS shows the highest latency (~31-34 hops) due to chain-relay aggregation: each source packet traverses on average N/4 chain links (for a chain of length N with a centrally positioned leader) plus one leader->BS hop. This is a known chain-routing trade-off.
- TEEN reports the lowest hop count (~1.23-1.30) because its threshold-triggered reporting means many nodes transmit directly to BS (1-hop) when they exceed the hard threshold, while only a fraction of packets are aggregated through CHs (2-hop).
- All AERIS-vs-baseline differences are statistically significant (Welch's t-test with Holm correction, all p_holm < 0.001). See latency_hop_v2_significance.csv.
- Scope note: this latency metric is hop-based and does not claim wall-clock milliseconds.

### 6.6 Summary of Evidence

1) At 100 nodes (n=30), AERIS leads baselines in all four environments (Table 6.1).
2) CAS multi-mode is triggerable, but higher CHAIN use trades off PDR in sparse
   conditions (Table 6.2).
3) Gateway effect is environment-dependent: positive in 3/4 environments and near-neutral in indoor_office (Table 6.3).
4) At scale (100-1000 nodes, n=60), AERIS maintains first rank in 3/4 environments
   but PEGASIS surpasses AERIS in indoor_office (Table 6.4).
