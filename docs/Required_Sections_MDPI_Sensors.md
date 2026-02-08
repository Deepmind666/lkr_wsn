# MDPI Sensors 必需章节模板

**用途**: 直接插入到AERIS论文末尾
**日期**: 2025-10-19
**符合**: MDPI Sensors投稿要求

---

## Data Availability Statement

The Intel Berkeley Research Lab dataset used in this study is publicly available at the following URL:

**Intel Lab Dataset**: http://db.csail.mit.edu/labdata/labdata.html
(Accessed: 2025-01-01)

The dataset comprises 2.22 million temperature, humidity, light, and voltage readings collected from 54 Mica2Dot sensors deployed in the Intel Berkeley Research Lab between February 28 and April 5, 2004. Node deployment coordinates (`mote_locs.txt`) are included with the dataset.

All experimental results generated during this study, including:
- Raw simulation outputs (JSON format)
- Statistical analysis results
- Generated figures and tables

are available in the project repository at: `https://github.com/Deepmind666/AERIS-WSN-Protocol/tree/main/results`

Specific result files referenced in this paper:
- Baseline comparison: `results/final_baseline_compare.json`
- Sensitivity analysis: `results/intel_sensitivity_parallel.json`
- Ablation study: `results/intel_ablation.json`
- Statistical significance: `results/significance_compare_intel_parallel.json`

---

## Code Availability

All source code, experiment scripts, and data processing tools developed for this study are publicly available under the MIT License at:

**GitHub Repository**: https://github.com/Deepmind666/AERIS-WSN-Protocol

The repository includes:
- Protocol implementations (AERIS, LEACH, HEED, PEGASIS, TEEN)
- Environment-aware channel models
- Statistical analysis scripts
- Figure generation scripts
- Complete reproduction instructions in `README.md`

### Reproduction

To reproduce the experiments reported in this paper:

```bash
# 1. Clone the repository
git clone https://github.com/Deepmind666/AERIS-WSN-Protocol
cd AERIS-WSN-Protocol

# 2. Install dependencies
conda create -n aeris python=3.11
conda activate aeris
pip install -r requirements.txt

# 3. Download Intel Lab dataset
python scripts/download_intel_assets.py

# 4. Run core experiments
python scripts/run_intel_baselines_all.py    # Baseline comparison
python scripts/run_intel_ablation.py         # Ablation study
python scripts/run_intel_sensitivity.py      # Sensitivity analysis

# 5. Generate figures
python scripts/plot_paper_figures.py
```

Detailed step-by-step instructions are provided in `README.md`. All experiments use fixed random seeds for reproducibility.

---

## Author Contributions

**Conceptualization**: 康锐 (Kang Rui);
**Methodology**: 康锐;
**Software**: 康锐;
**Validation**: 康锐;
**Formal analysis**: 康锐;
**Investigation**: 康锐;
**Resources**: 康锐;
**Data curation**: 康锐;
**Writing—original draft preparation**: 康锐;
**Writing—review and editing**: 康锐;
**Visualization**: 康锐;
**Supervision**: 康锐;
**Project administration**: 康锐.

All authors have read and agreed to the published version of the manuscript.

**Note for submission**: If there are co-authors, please modify the above using the CRediT (Contributor Roles Taxonomy) format. For example:
- **Conceptualization**: K.R. and A.B.;
- **Methodology**: K.R.;
- **Software**: K.R. and C.D.;
- **Validation**: K.R., A.B., and C.D.;
- etc.

---

## Funding

This research received no external funding.

**Alternative (if funded)**:
This research was funded by [Funding Agency Name], grant number [XXXX-YYYY-ZZZZ]. The APC was funded by [Institution/Grant Name].

---

## Institutional Review Board Statement

Not applicable. This study did not involve humans or animals.

---

## Informed Consent Statement

Not applicable. This study did not involve humans.

---

## Data Protection and Privacy Statement

Not applicable. This study uses publicly available sensor network datasets that do not contain any personally identifiable information.

---

## Conflicts of Interest

The authors declare no conflicts of interest.

**Alternative (if applicable)**:
The authors declare no conflicts of interest. The funders had no role in the design of the study; in the collection, analyses, or interpretation of data; in the writing of the manuscript; or in the decision to publish the results.

---

## Acknowledgments

The authors gratefully acknowledge the Intel Berkeley Research Lab for providing the publicly available sensor network dataset used in this study.

**Optional additions**:
- We thank [Name] for helpful discussions on [topic].
- Computational resources were provided by [Institution/Resource].
- The authors acknowledge the use of [Software/Tool] for [purpose].

---

## Abbreviations

The following abbreviations are used in this manuscript:

| Abbreviation | Full Form |
|--------------|-----------|
| AERIS | Adaptive Environment-aware Routing for IoT Sensors |
| WSN | Wireless Sensor Network |
| IoT | Internet of Things |
| BS | Base Station |
| CH | Cluster Head |
| CAS | Context-Adaptive Switching |
| PDR | Packet Delivery Ratio |
| LEACH | Low-Energy Adaptive Clustering Hierarchy |
| HEED | Hybrid Energy-Efficient Distributed Clustering |
| PEGASIS | Power-Efficient Gathering in Sensor Information Systems |
| TEEN | Threshold-sensitive Energy-Efficient sensor Network |
| IEEE | Institute of Electrical and Electronics Engineers |
| PCA | Principal Component Analysis |
| MAC | Medium Access Control |
| PHY | Physical Layer |
| RSSI | Received Signal Strength Indicator |
| SNR | Signal-to-Noise Ratio |
| LQI | Link Quality Indicator |
| EMA | Exponential Moving Average |
| CI | Confidence Interval |
| FDR | False Discovery Rate |
| ONNX | Open Neural Network Exchange |

---

## Appendix A: Detailed Parameter Settings

**Table A1**: Network configuration parameters used in all experiments.

| Parameter | Value | Description |
|-----------|-------|-------------|
| Area size | 100m × 100m | Deployment area for synthetic topologies |
| Number of nodes | 50-100 | Varied in sensitivity analysis |
| Initial energy | 2.0 J | Per-node battery capacity |
| Packet size | 1024 bytes | Data packet payload size |
| Base station location | (50, 200) | Outside deployment area |
| MAC protocol | IEEE 802.15.4 | CSMA/CA with exponential backoff |
| PHY data rate | 250 kbps | IEEE 802.15.4 standard |
| Transmission power range | -5 dBm to +8 dBm | Environment-adaptive |
| Path loss exponent | 2.0 (indoor) / 4.0 (outdoor) | Environment-dependent |
| Shadow fading std | 3-8 dB | Environment-dependent |

**Table A2**: AERIS-specific algorithm parameters.

| Parameter | Value | Description |
|-----------|-------|-------------|
| CAS EMA alpha | 0.2 | Exponential smoothing factor |
| CAS confidence threshold | 0.2 | Minimum confidence for mode switching |
| Skeleton backbone k | 1-2 | Number of backbone CHs |
| Gateway k | 1-2 | Number of gateway CHs |
| Safety fallback threshold | 0.1 | PDR threshold for triggering safety mode |
| Fairness penalty weight | 0.2 | CH usage fairness constraint |

---

## Appendix B: Statistical Methods

### B.1 Welch's t-Test

We use Welch's t-test (two-sample unequal variance t-test) to compare mean performance metrics between AERIS and baseline protocols:

$$
t = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\frac{s_1^2}{n_1} + \frac{s_2^2}{n_2}}}
$$

where $\bar{X}_i$ is the sample mean, $s_i^2$ is the sample variance, and $n_i$ is the sample size for group $i$.

**Advantages over Student's t-test**: Does not assume equal variances, more robust for real-world data.

### B.2 Holm-Bonferroni Correction

To control the family-wise error rate (FWER) in multiple hypothesis testing, we apply the Holm-Bonferroni sequential correction:

1. Sort p-values in ascending order: $p_{(1)} \leq p_{(2)} \leq \ldots \leq p_{(m)}$
2. For each $i = 1, 2, \ldots, m$, compare $p_{(i)}$ with $\alpha/(m - i + 1)$
3. Reject $H_{(i)}$ if $p_{(i)} \leq \alpha/(m - i + 1)$ and all previous hypotheses were rejected

**Parameters**: $\alpha = 0.05$ (significance level), $m$ = number of comparisons.

### B.3 Bootstrap Confidence Intervals

We compute 95% percentile bootstrap confidence intervals using $B = 1000$ resamples:

1. Resample with replacement $B$ times from observed data
2. Compute statistic $\theta^*_b$ for each resample $b = 1, \ldots, B$
3. CI = $[\theta^*_{(0.025B)}, \theta^*_{(0.975B)}]$

### B.4 Effect Size (Cohen's d)

We report standardized effect sizes using Cohen's d:

$$
d = \frac{\bar{X}_1 - \bar{X}_2}{s_{pooled}}, \quad s_{pooled} = \sqrt{\frac{(n_1 - 1)s_1^2 + (n_2 - 1)s_2^2}{n_1 + n_2 - 2}}
$$

**Interpretation**: $|d| < 0.2$ (small), $0.2 \leq |d| < 0.8$ (medium), $|d| \geq 0.8$ (large).

---

## References

[Note: This section should be automatically generated from the bibliography.bib file]

---

**使用说明**:

1. **复制粘贴**: 将上述内容复制到论文末尾（Conclusion之后）

2. **修改作者信息**: 如果有合作者，修改Author Contributions部分

3. **修改Funding**: 如果有资金支持，修改Funding部分

4. **检查GitHub链接**: 确保仓库链接正确且公开

5. **Abbreviations**: 根据论文实际使用的缩写调整表格

6. **Appendix**: 根据需要保留或删除附录部分

7. **符合MDPI格式**: 已按照MDPI Sensors模板格式编写

**字数统计**:
- 主要章节: ~1,200词
- 附录（可选）: ~800词
- 总计: ~2,000词

**完成后**:
论文总字数 = 17,000 + 2,000 = 19,000词
需要精简至10,000词，可考虑将部分内容移至Supplementary Materials。
