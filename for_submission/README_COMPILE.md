# AERIS Paper Compilation Instructions

## Submission Package Contents

```
for_submission/
├── aeris_paper_final.tex    # Main LaTeX source (Updated with 审核意见三 improvements)
├── bibliography.bib          # References
├── figures/                  # All required figures
│   ├── fig2_env_link_enhanced.pdf
│   ├── AERIS_flowchart.pdf
│   ├── aeris_professional_12panel.pdf
│   ├── fig7_sensitivity_professional.pdf
│   ├── fig4_statistical_validation_enhanced.pdf
│   ├── sota_comparison_6panel.pdf
│   ├── ablation_heatmap.pdf         # NEW: Heatmap visualization
│   ├── tradeoff_radar.pdf           # NEW: Trade-off radar chart
│   └── aeris_composite_2x2.pdf      # NEW: 2x2 composite figure (附录A standard)
├── simulated_peer_review.md  # Simulated peer review report
└── README_COMPILE.md         # This file
```

## Key Improvements (审核意见三)

This version incorporates three advanced strategies from Gemini Review 审核意见三:

1. **Strategy 2 - Opening a New Niche**: Introduced Topology Dynamic Adaptability (TDA) as a new evaluation dimension
2. **Strategy 3 - Revealing Hidden Problem**: Documented the "Distributed Optimality Curse" phenomenon
3. **Appendix A Standards**: Created publication-quality figures with global style consistency

## Compilation Methods

### Method 1: Overleaf (Recommended - No Installation Required)

1. Go to https://www.overleaf.com
2. Create a new project → "Upload Project"
3. Upload the entire `for_submission/` folder as a ZIP file
4. Open `aeris_paper_final.tex` and click "Recompile"
5. Download the PDF

### Method 2: Local LaTeX Installation

#### Windows (MiKTeX)
```powershell
# Download MiKTeX from https://miktex.org/download
# After installation:
cd c:\AERIS-WSN-Protocol\for_submission
pdflatex aeris_paper_final.tex
bibtex aeris_paper_final
pdflatex aeris_paper_final.tex
pdflatex aeris_paper_final.tex
```

#### Windows (TeX Live via Chocolatey)
```powershell
choco install texlive
cd c:\AERIS-WSN-Protocol\for_submission
latexmk -pdf aeris_paper_final.tex
```

### Method 3: Docker (Cross-platform)
```bash
docker run --rm -v ${PWD}:/data blang/latex:ubuntu \
  bash -c "cd /data && pdflatex aeris_paper_final && bibtex aeris_paper_final && pdflatex aeris_paper_final && pdflatex aeris_paper_final"
```

## Quick Verification Checklist

Before sharing with colleagues, verify:

- [ ] All 9 figures render correctly (6 original + 3 new)
- [ ] References compile without errors
- [ ] Page count is reasonable (target: 16-22 pages for Sensors)
- [ ] Abstract is within 200-250 words

## Paper Statistics (Updated)

| Metric | Value |
|--------|-------|
| Sections | 6 (Intro, Prior Exp, Method, Results, Discussion, Conclusion) |
| Discussion Subsections | 7 (including TDA and Distributed Optimality Curse) |
| Figures | 9 |
| Contributions in Conclusion | 7 |
| Citations | 30 |
| Keywords | 6 |

## Python Scripts for Figure Generation

```bash
# Generate heatmap and radar figures
python scripts/generate_ablation_heatmap.py

# Generate 2x2 composite figure (附录A standard)
python scripts/generate_composite_figure.py
```

## Contact

For questions about the paper content, contact the corresponding author.
