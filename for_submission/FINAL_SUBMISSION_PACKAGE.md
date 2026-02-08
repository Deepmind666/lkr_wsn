# AERIS Final Submission Package

**Date**: 2026-01-01
**Status**: Ready for Submission

---

## 📦 Package Contents

### 1. Main Paper
- `aeris_paper_final.tex` - LaTeX source
- `aeris_paper_final.pdf` - Compiled PDF
- `bibliography.bib` - References

### 2. Figures (in results/ directories)
| Figure | File | Description |
|--------|------|-------------|
| Fig 1 | `fig2_env_link_enhanced.pdf` | Environment-link correlation |
| Fig 2 | `fig3_prior_experiments_enhanced.pdf` | Prior experiments panel |
| Fig 3 | `fig4_ablation_professional.pdf` | Ablation study results |
| Fig 4 | `fig4_statistical_validation_enhanced.pdf` | Statistical validation |
| Fig 5 | `fig5_protocol_comparison_enhanced.pdf` | Protocol comparison |
| Fig 6 | `fig6_comprehensive_summary.pdf` | Performance summary |
| Fig 7 | `fig7_sensitivity_professional.pdf` | Parameter sensitivity |

### 3. Supplementary Materials
- `supplementary_materials.md` - Source
- `supplementary_materials.pdf` - PDF version

### 4. Data Files
| File | Location | Description |
|------|----------|-------------|
| `intel_ablation.json` | results/ | Ablation experiment (n=50×5) |
| `intel_sensitivity.json` | results/ | Sensitivity analysis (n=40×9) |
| `e0_env_link_correlation.json` | results/prior_experiments/ | E0 results |
| `e1_cas_features.json` | results/prior_experiments/ | E1 results |
| `e2_safety_threshold.json` | results/prior_experiments/ | E2 results |
| `e3_load_balance.json` | results/prior_experiments/ | E3 results |

---

## 📊 Key Results Summary

### Effect Sizes (Hedges' g)
| Component | Effect Size | Interpretation | PDR Change |
|-----------|-------------|----------------|------------|
| Gateway | 4.48 | Large | +24.4% |
| Safety | 3.48 | Large | +29.4% |
| Fairness | -0.10 | Negligible | -0.5% |
| CAS | -0.15 | Negligible | -0.8% |

### Statistical Validation
- Sample size: 50 runs per configuration
- Total comparisons: 4
- Significant (p<0.05): 2 (Gateway, Safety)
- Correction method: Holm-Bonferroni

### Prior Experiments
| Experiment | Key Finding |
|------------|-------------|
| E0 | AUC=0.990, r=-0.499 |
| E1 | Accuracy=90% |
| E2 | θ=0.647, FPR=0% |
| E3 | r=-0.749 |
| E4 | 167ms total latency |

---

## ✅ Verification Checklist

### Data Integrity
- [x] All data from verified source (intel_ablation.json)
- [x] Sample sizes correct (n=50 per config)
- [x] Effect sizes recalculated and verified
- [x] Statistical tests with proper correction

### Paper Content
- [x] Abstract matches results
- [x] All figures reference correct data
- [x] Effect sizes consistent throughout
- [x] Limitations clearly stated

### Figures
- [x] Resolution ≥300 DPI
- [x] Width ≥1200px
- [x] Consistent style
- [x] Error bars/CI included

---

## 🔬 Reproducibility

### Scripts
```
scripts/
├── prior_experiments/
│   ├── run_e0_env_link.py
│   ├── run_e1_cas_features.py
│   ├── run_e2_safety_threshold.py
│   ├── run_e3_load_balance.py
│   └── run_e4_latency.py
├── statistical_validation/
│   └── run_corrected_validation.py
└── figure_generation/
    └── generate_professional_figures.py
```

### Data Sources
- Intel Lab trace: `data/Intel_Lab_Data/`
- Experiment results: `results/`

---

## 📝 Submission Notes

### Target Journal
MDPI Sensors (or similar WSN/IoT journal)

### Key Contributions
1. **Gateway-Enhanced Relay**: Core innovation (g=4.48)
2. **Safety Threshold**: Important mechanism (g=3.48)
3. **Evidence-Based Design**: E0-E4 prior experiments
4. **Statistical Rigor**: Full validation with effect sizes

### Limitations Acknowledged
- Decision latency (167ms) exceeds MCU budget
- Validated for ≤100 nodes
- Static deployment environments

---

*Package prepared: 2026-01-01*
