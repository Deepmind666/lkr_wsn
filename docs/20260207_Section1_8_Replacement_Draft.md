# Section 1/8 Replacement Draft (Data-Constrained)

Date: 2026-02-07  
Goal: Replace unsupported statements in Section 1 and Section 8 with claims supported by publication-tier JSON.

## Section 1 (Introduction) Replacement Guidance

## Replace These Statements

- Remove "200 independent runs per configuration".
- Remove "100% PDR at scale (50-500 nodes)".
- Remove fixed latency constants unless publication-tier latency evidence is attached.
- Remove TDA contribution claim unless TDA publication result file is attached.
- Replace target journal text from Applied Intelligence to MDPI Sensors workflow text if this manuscript is for Sensors submission.

## Recommended Abstract Core (Example)

This paper presents AERIS (Adaptive Environment-aware Routing), evaluated under four channel environments with 30 independent seeds per environment. Using end-to-end reliability metric `pdr_expected = bs_delivered / source_packets_expected`, AERIS achieves the highest PDR among LEACH, PEGASIS, HEED, and TEEN across all tested environments. Statistical testing (Welch's t-test) confirms significant AERIS-vs-baseline differences under this evaluation setup.

## Recommended Contribution Bullets (Example)

1. Multi-environment reliability validation: AERIS ranks first in PDR across indoor_office, indoor_factory, outdoor_urban, and outdoor_suburban (n=30 each).
2. Evidence-based module analysis: Gateway effect is significant in 3/4 environments; CAS contribution is mixed (significant negative in outdoor_urban under current setup).
3. Reproducible protocol comparison with publication-tier metadata (run_tier, commit, script hash, config hash).

## Section 8 (Conclusion) Replacement Guidance

## Replace These Statements

- Remove "100% PDR up to 500 nodes".
- Remove "sub-500ms latency and 100% PDR at 500 nodes" unless latency files are included in the same paper package.
- Remove "200 runs".
- Replace "Gateway is primary contributor" with conditional statement backed by p-values.

## Recommended Conclusion Core (Example)

Under the current four-environment, n=30 protocol comparison, AERIS consistently achieves the highest PDR among tested baselines. Ablation analysis shows that module contributions are environment-dependent: Gateway provides significant gains in three environments and is neutral in one, while CAS does not provide a consistent positive gain and is significantly negative in one environment. These findings support a scoped reliability claim and motivate further design refinement before making universal module-level claims.

## Hard Consistency Notes

- Metric wording must stay consistent:
  - "PDR refers to pdr_expected in all reported tables."
- Keep scope explicit:
  - "Results apply to 100 nodes, 300 rounds, 10 dBm, dropout 0.0, four environments, n=30."

## Insertable Evidence Reference Block

- C:\AERIS-WSN-Protocol\results\mega_experiments\env_sensitivity_20260207_205317.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\ablation_diag_multi_20260207_205448.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\fact_table_5protocol_pdr.csv
- C:\AERIS-WSN-Protocol\results\mega_experiments\fact_table_ablation_pdr_pvalues.csv

