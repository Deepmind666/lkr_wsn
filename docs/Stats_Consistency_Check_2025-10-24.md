# Statistical Consistency Check — AERIS (2025-10-24)

Scope: Verify presence and alignment of significance outputs (BH-FDR and Holm–Bonferroni) for Intel replay and multi-topology (50x200) experiments.

## 1) Files Located
- Top-level results:
  - `results/multitest_bh_fdr.json` — present
  - `results/multitest_holm_bonferroni.json` — present
- Archived runs (2025-10-12):
  - `results/_archive_20251012-082311/multitest_bh_fdr.json` — present
  - `results/_archive_20251012-082311/multitest_holm_bonferroni.json` — present
  - CSV summary: `results/_archive_20251012-191849/significance_bh_fdr.csv` — present
- Scenario-specific:
  - `results/_archive_20251012-082311/significance_compare_multi_topo_50x200.json` — present

## 2) Key Scenarios & Metrics (as reported)
- `significance_compare_intel` and `significance_compare_intel_parallel`
  - Metrics: `total_energy_consumed`, `pdr_end2end_mean`, `pdr_end2end_p05`, `lifetime`
- `significance_compare_50x200` and `significance_compare_multi_topo_50x200:*`
  - Metric focus: `pdr_end2end_mean` primarily; parallel entries for `pdr_end2end_p05`, `lifetime` included

## 3) Consistency Notes
- Both BH-FDR and Holm–Bonferroni outputs exist and show aligned rejection decisions for high-signal metrics (e.g., energy, mean PDR) on Intel parallel scenario.
- Non-significant metrics (`pdr_end2end_p05`, `lifetime`) consistently reported as `reject_null: false` across files.
- Multi-topology corridor vs. uniform show expected gradient of significance (corridor stronger than uniform), consistent in both multitest outputs.

## 4) Recommended Use in Manuscript
- Report both corrections: “BH-FDR (Benjamini–Hochberg)” and “Holm–Bonferroni” with alpha `0.05`.
- Include effect sizes: `Gardner–Altman` or `Cliff's delta` where applicable; provide CI95.
- Cite file sources in Supplementary: `results/multitest_*.json` and archive CSV.
- Align figure overlays (e.g., `paper_intel_sig_combined.svg`) to these decisions.

## 5) Optional Refresh
- If environment ready, run: `python scripts/run_stats_multitest.py` to regenerate JSONs.
- If `scipy` not available, follow `docs/Python_Environment_Fix_Guide.md` to install dependencies or run on a prepared workstation.

Conclusion: Consistency verified; outputs present and aligned. Ready to reference and integrate in final figures and text.