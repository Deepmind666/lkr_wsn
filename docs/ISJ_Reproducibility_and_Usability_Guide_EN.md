# ISJ Reproducibility and Usability Guide (English)

This guide explains how to fully reproduce the main experiments and figures, verify results, and curate paper-quality assets for insertion into manuscripts.

Audience: reviewers and readers who want a one-click (or minimal steps) path to reproduce the results.

---

## 1) Environment Setup

- Requirements: Windows 10/11 or Linux, Python 3.8+
- Recommended: Conda or Miniconda for isolation

Create environment:
```bash
conda create -n aeris-wsn python=3.10 -y
conda activate aeris-wsn
pip install -r requirements.txt
```

Optional (fonts for IEEE/ACM style):
- The plotting script configures Matplotlib rcParams for journal-grade output.
- Vector outputs (SVG) embed text to avoid font issues on Word/LaTeX.

## 2) Dataset

- Source: MIT CSAIL Intel Berkeley Research Lab
- Official page: https://db.csail.mit.edu/labdata/labdata.html
- Scale: ~2.22M records, 54 motes, Feb-Apr 2004

The scripts automatically download/process what they need where applicable. If you have a local mirror, place it under data/ and adjust paths as needed.

## 3) One-click Reproduction

Run the core pipeline (recommended order):
```bash
# 1) Recreate Intel replay and computed metrics
python scripts/run_intel_replay.py

# 2) Run baseline methods on the same geometry/definitions
python scripts/run_intel_baselines_all.py

# 3) Significance testing (n=50)
python scripts/run_parallel_significance_intel.py 50

# 4) Generate paper figures (IEEE/ACM style)
python scripts/plot_paper_figures.py

# 5) Curate and package final figures
python scripts/curate_figures.py
```
Outputs location (key folders):
- results/plots/ … raw SVGs
- results/plots_curated/ … curated for Word (with manifest.json)
- results/publication_figures/ … journal-ready copies
- results/isj_minimal_svg/ … minimal SVG package

## 4) Paper Mode (Titles inside figures)

- Default: enabled (PAPER_MODE=True in scripts/plot_paper_figures.py)
- To override via environment:
  - Windows PowerShell: `setx PAPER_MODE 1` (enable) or `setx PAPER_MODE 0` (disable) and restart shell
  - Unix (bash): `export PAPER_MODE=1` or `export PAPER_MODE=0`

When Paper Mode is on, figure-internal titles are suppressed to favor external captions in journals.

## 5) Metric Semantics

- End-to-End PDR: packet_delivery_ratio_end2end (source→base-station delivery semantics)
- Hop-level PDR: packet_delivery_ratio (reported separately)
- All baselines are aligned to the same end-to-end definition on the same geometry for fair comparison.

## 6) Verifying Your Run

Quick checks:
- results/plots_curated/ contains files like:
  - paper_intel_energy.svg, paper_intel_pdr.svg
  - paper_intel_baselines_energy.svg, paper_intel_baselines_pdr.svg
  - paper_intel_predenv_energy.svg, paper_intel_predenv_pdr.svg
  - paper_intel_sig_energy.svg, paper_intel_sig_pdr.svg
- Manifest present: results/plots_curated/manifest.json
- Significant improvements visible in End-to-End PDR with modest energy changes (n=50, 95% CI)

## 7) Troubleshooting

- Missing fonts or garbled text in Word
  - Use the curated figures (plots_curated) which embed fonts properly
  - Prefer SVG over PNG for clarity and scalability
- Different colors between runs
  - We use Okabe–Ito color palette; ensure Matplotlib ≥3.5
- Figure size or DPI issues
  - Outputs are vector (SVG); for raster export, use 300–600 DPI if needed
- Path or file-not-found errors
  - Run scripts from the project root; ensure results/ and data/ are writable

## 8) Re-running Only Figures

If you already have JSON metrics and want to regenerate figures with updated styles:
```bash
python scripts/plot_paper_figures.py
python scripts/curate_figures.py
```

## 9) License and Citation

- Code: MIT License
- Dataset: follow the terms of MIT/CSAIL Intel Lab dataset

If this repository helps your research, please cite the project as described in README.md.