# ISJ Repro Quickstart (1‑Page)

Audience: reviewers/readers who need a minimal, reliable path to reproduce key results and figures.

---

## Prerequisites
- OS: Windows 10/11 or Linux
- Python: 3.8+ (3.10 recommended)
- Tools: Conda/Miniconda recommended

Setup (recommended):
```bash
conda create -n aeris-wsn python=3.10 -y
conda activate aeris-wsn
pip install -r requirements.txt
```

## One-click Pipeline (Order)
```bash
# 1) Recreate Intel replay metrics
python scripts/run_intel_replay.py

# 2) Baselines on same geometry/definitions
python scripts/run_intel_baselines_all.py

# 3) Significance testing (n=50)
python scripts/run_parallel_significance_intel.py 50

# 4) Paper figures (IEEE/ACM style)
python scripts/plot_paper_figures.py

# 5) Curate final figures (for Word/LaTeX)
python scripts/curate_figures.py
```

## Outputs (Key Folders)
- results/plots/ … raw SVGs
- results/plots_curated/ … curated SVGs + manifest.json
- results/publication_figures/ … copies for journal submission
- results/isj_minimal_svg/ … minimal SVG package

Expected curated files include:
- paper_intel_energy.svg, paper_intel_pdr.svg
- paper_intel_baselines_energy.svg, paper_intel_baselines_pdr.svg
- paper_intel_predenv_energy.svg, paper_intel_predenv_pdr.svg
- paper_intel_sig_energy.svg, paper_intel_sig_pdr.svg

## Paper Mode (Titles Inside Figures)
- Default: ON (PAPER_MODE=True)
- Toggle via env var:
  - Windows PowerShell: `setx PAPER_MODE 1` (on) / `setx PAPER_MODE 0` (off), then restart shell
  - Unix bash: `export PAPER_MODE=1` or `export PAPER_MODE=0`

## Metric Semantics
- End-to-End PDR = packet_delivery_ratio_end2end (source→BS)
- Hop-level PDR = packet_delivery_ratio (reported separately)
- Baselines are aligned to the same E2E definition.

## Quick Verify
- results/plots_curated/manifest.json exists
- End-to-End PDR figures use “End-to-End PDR” wording
- Visual style: Okabe–Ito palette, journal-grade rcParams

## Troubleshooting (Fast)
- Path issues: run commands from repo root
- Permissions: ensure results/ is writable
- Fonts/Word issues: use plots_curated SVGs (embedded text)
- Internet access: required for first-time dataset fetch

For full details, see:
- docs/ISJ_Reproducibility_and_Usability_Guide.md (Chinese)
- docs/ISJ_Reproducibility_and_Usability_Guide_EN.md (English)