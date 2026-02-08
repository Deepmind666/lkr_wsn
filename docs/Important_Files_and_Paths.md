# Enhanced-EEHFR-WSN Manuscript – Important Files & Paths

## Manuscript Source & Output
- Main LaTeX source: `docs/templates/mdpi_latex/_extract/Template-LaTeX-MDPI-master/template.tex`
- Compiled PDF: `docs/templates/mdpi_latex/_extract/Template-LaTeX-MDPI-master/template.pdf`
- Duplicate template (kept in sync): `docs/templates/mdpi_latex/_extract/template-latex-mdpi-master/template.tex`
- Preview URL (local): `http://localhost:8001/template.pdf`

## Authors & Affiliations (MDPI Format)
- `\Author{Kangrui Li ^{1}, Xiaobo Zhang ^{2} and Junyi Lin ^{3,}*}`
- `\AuthorNames{Kangrui Li, Xiaobo Zhang and Junyi Lin}`
- `\address{^{1} Faculty of Automation, Guangdong University of Technology, Guangzhou, China; ^{2} Faculty of Automation, Guangdong University of Technology, Guangzhou, China; ^{3} Faculty of Automation, Guangdong University of Technology, Guangzhou, China}`
- `\corres{Correspondence: deepmind666@163.com}`

## Figure Resolution & Quality
- Graphics search order in LaTeX: `results/for_submission/` → `results/Sensors_figures/` → `results/publication_figures/` → `results/plots/`
- Preferred extensions: `.pdf` (vector), fallback `.png`.
- Figures referenced in manuscript (names without extension):
  - `paper_intel_sig_combined`
  - `paper_intel_baselines_panels_minimal`
  - `paper_safety_tradeoff`
  - `paper_intel_ablation_pdr`
  - `paper_intel_ablation_energy`
  - `paper_intel_pdr_gardner_altman`
  - `paper_intel_baselines_pdr`
  - `paper_intel_baselines_energy`
  - `paper_multi_topo_sig_pdr`
  - `paper_multi_topo_sig_energy`
- High-quality sources (vector PDFs available): `results/publication_figures/`
  - Examples: `paper_intel_sig_combined.pdf`, `paper_intel_baselines_panels_minimal.pdf`, `paper_intel_pdr_gardner_altman.pdf`, etc.
- Curated October packages:
  - `results/for_submission/` – `manifest.json`, `submission_figures.pdf`, `manuscript_draft.pdf`
  - `results/Sensors_figures/` – `manifest.json`, `submission_figures.pdf`, `manuscript_draft.pdf`

## October 2025 Experiments & Data (Key Files)
- Significance & multiple testing:
  - `results/significance_compare_intel_parallel.json`
  - `results/multitest_bh_fdr.json`
  - `results/multitest_holm_bonferroni.json`
  - `results/significance_bh_fdr.csv` (with `results/significance_bh_fdr.md`)
- Effect sizes & summaries:
  - `results/effect_sizes_summary.json`
- Intel ablation & sensitivity:
  - `results/intel_ablation_parallel.json` (fallback: `results/intel_ablation.json`)
  - `results/intel_sensitivity_parallel.json` (fallback: `results/intel_sensitivity.json`)
- Baselines & comparisons:
  - `results/intel_baselines_all.json`
  - `results/intel_replay_compare.json`
- Inference benchmarking:
  - `results/inference_bench.json`
  - `results/inference_bench_gpu_dml.json`
  - `results/inference_ov_npu_probe.json`
- Scalability:
  - `results/scalability_aeris_800_3seeds.csv`
  - `results/scalability_minimal_results.csv`
- Archive manifests (October snapshots):
  - `results/_archive_20251012-082311/ARCHIVE_MANIFEST.json`
  - `results/_archive_20251012-191849/ARCHIVE_MANIFEST.json`

## Figure Generation & Validation
- Plot script (main): `scripts/plot_paper_figures.py`
- Batch export helper: `scripts/run_export.py`
- Publication copy script: `results/publication_figures/render_all_figures.ps1`
- Validation report:
  - `results/figure_validation_report.md`
  - `results/figure_validation_report.json`

## Notes
- The LaTeX template resolves figures from October curated folders first; if a figure exists in multiple locations, `for_submission` takes precedence.
- All included figures are exported as vector `.pdf` for MDPI quality standards.
- The compiled PDF currently shows minor `Underfull \hbox` warnings and a `xeCJK` monofont notice; these are non-blocking and can be tuned later.