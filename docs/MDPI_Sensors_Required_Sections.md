# MDPI Sensors Required Sections — AERIS

Date: 2025-10-24

## Data Availability Statement
All datasets and derived artifacts used in this study are available:
- Intel Lab replay dataset and derived metrics: `data/Intel_Lab_Data/`, processed outputs in `results/intel_*`.
- Experiment results and statistical outputs: `results/` (top-level JSON), archives in `results/_archive_*`.
- Submission-ready figures and curated packages: `results/for_submission/` (with `manifest.json`).
Access policy: Public upon publication; pre-publication shared under request. Scripts for data processing are included in `scripts/`.

## Code Availability Statement
The complete source code for simulation, analysis, and figure generation is hosted in this repository (`C:\Enhanced-EEHFR-WSN-Protocol`). Key entry points:
- Reproduction: `scripts/run_reproduce_all.py`
- Intel replay pipeline: `scripts/run_intel_replay.py`, baselines: `scripts/run_intel_baselines.py`
- Significance testing: `scripts/run_stats_multitest.py`
- Figure generation & curation: `scripts/plot_paper_figures.py`, `scripts/curate_figures.py`

## Author Contributions (CRediT)
- Conceptualization: Lead Author A; Co-Author B
- Methodology: Lead Author A; Co-Author B
- Software: Lead Author A
- Validation: Lead Author A; Co-Author B
- Formal Analysis: Lead Author A
- Investigation: Lead Author A
- Writing—Original Draft: Lead Author A
- Writing—Review & Editing: Lead Author A; Co-Author B
- Supervision: Co-Author B

Note: Replace placeholder roles with actual author names and affiliations before submission.

## Conflicts of Interest
The authors declare no competing interests.

## Funding
This research received no external funding. If internal or grant support applies, specify grant numbers and sponsors here.

## Acknowledgments
We thank colleagues and infrastructure support (GPU/DirectML/WSL environments). We acknowledge the Intel Lab data providers and open-source contributors.

## Nomenclature / Abbreviations
- AERIS: Adaptive Environment-Robust Intelligent Sensing (proposed framework)
- PDR: Packet Delivery Ratio (end-to-end, unless otherwise specified)
- CI95: 95% Confidence Interval
- BH-FDR: Benjamini–Hochberg False Discovery Rate
- HB: Holm–Bonferroni correction
- DML: DirectML (ONNX Runtime)
- ORT: ONNX Runtime
- CUDA: NVIDIA Compute Unified Device Architecture

## Ethics Statements
Not applicable. This work is based on simulations and previously published datasets without human or animal subjects.

## How to Cite Supplemental Materials
Provide direct references in the manuscript to `results/for_submission/manifest.json` and include selected figures as supplemental files. Statistical source files: `results/multitest_bh_fdr.json`, `results/multitest_holm_bonferroni.json`, and archive CSV.