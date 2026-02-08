# Section 8: Conclusion

---

## 8. Conclusion

This paper presents AERIS, a lightweight hierarchical routing protocol evaluated across four channel environments (indoor_office, indoor_factory, outdoor_urban, outdoor_suburban) with 30 independent seeds per configuration.

### 8.1 Summary of Contributions

**C1. Multi-Environment Reliability Leadership**: At 100 nodes (n=30), AERIS achieves the highest PDR (pdr_expected) among all five tested protocols across all four evaluated channel environments (Welch's t-test p < 0.001 in all cases). Scalability experiments (100–1000 nodes, n=60) confirm this advantage in 3/4 environments; in indoor_office, PEGASIS maintains higher PDR at scale.

**C2. Evidence-Based Module Analysis**: Ablation analysis shows that module contributions are environment-dependent. Gateway provides statistically significant PDR gains in 3/4 environments (indoor_factory p=6.57e-4, outdoor_urban p=0.017, outdoor_suburban p=0.020), while CAS does not provide a consistent positive effect.

**C3. Reproducible Evaluation Framework**: All source code, experimental configurations, and raw result JSON files with full provenance metadata (git commit, script SHA256, config hash) are released as open source to enable independent verification.

**C4. Application-Specific Recommendations**: Based on comprehensive experiments (30 independent seeds per configuration across four environments), we provide clear protocol selection guidelines that acknowledge each protocol's optimal domain.

### 8.2 Honest Positioning

AERIS is **not** a universal replacement for existing protocols:

- In **indoor_office** environments, PEGASIS achieves higher PDR than AERIS at all tested scales ≥200 nodes (n=60, Hedges' g = −3.88 to −6.36). At 100 nodes (n=30), AERIS leads (0.974 vs 0.908) but the margin narrows at scale.

- In environments where **energy efficiency** is the sole concern, energy trade-offs have not yet been characterized in publication-tier evidence.

- Under the evaluated setup (100 nodes, 300 rounds, 10 dBm), AERIS's advantage is most pronounced in **harsh channel environments** (indoor_factory, outdoor_urban, outdoor_suburban) where baseline PDR drops substantially.

### 8.3 Key Findings

1. **Gateway** provides statistically significant PDR improvement in 3/4 environments (indoor_factory p=6.57e-4, outdoor_urban p=0.017, outdoor_suburban p=0.020) but is neutral in indoor_office (p=0.878). Data source: `ablation_diag_multi_20260207_205448.json`.

2. **CAS** does not provide a consistent positive effect: it is significantly negative in outdoor_urban (no_cas > full, p=2.20e-3) and non-significant in the other three environments.

3. **Skeleton and Safety** modules show no measurable marginal effect under the current evaluation setup (full == no_skeleton == no_safety within reported precision).

### 8.4 Reproducibility

All source code, experimental configurations, and raw result data are released as open source to enable independent verification and facilitate future research.

### 8.5 Future Directions

1. **Gateway optimization**: Given that Gateway provides significant PDR gains in 3/4 tested environments, future research should focus on understanding why it is neutral in indoor_office and on adaptive gateway mechanisms.

2. **Hardware validation**: Deploy AERIS on real TelosB/CC2650 hardware to validate simulation results and measure actual computational overhead.

3. **Lightweight ML integration**: Explore TinyML approaches (<5KB memory) for link quality prediction while maintaining AERIS's lightweight characteristics.

### 8.6 Closing Remarks

Under the current four-environment, n=30 evaluation at 100 nodes, AERIS achieves the highest PDR among tested baselines in all four environments. Scalability experiments (n=60, up to 1000 nodes) confirm this in 3/4 environments, with PEGASIS surpassing AERIS in indoor_office at scale. Module contributions are environment-dependent rather than universally positive. Rather than claiming universal superiority, we advocate for **honest, evidence-scoped protocol evaluation** that acknowledges each approach's strengths and limitations within tested conditions. We hope this work contributes not only the AERIS protocol but also a framework for transparent WSN protocol evaluation that enables practitioners to make informed deployment decisions.


