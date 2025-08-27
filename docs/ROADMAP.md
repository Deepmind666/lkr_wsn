## Roadmap: AETHER WSN – Experiments and Publication Plan

Milestones (Weeks)
- W1: Statistical rigor and figures
  - Intel parallel significance repeats=50; bootstrap CI; Holm–Bonferroni
  - Figures: Intel energy/PDR; Predicted-env (LSTM/TCN) vs conservative mapping
- W2: Baselines, ablations, sensitivity
  - Implement LEACH/HEED/PEGASIS baselines; ablate CAS/fairness/gateway/safety
  - Sensitivity: initial energy, packet size, gateway count, shadowing_std tiers
- W3: Scalability and second dataset
  - Node counts 50/100/200; add topology variants (grid/clustered)
  - Integrate a second public dataset (geometry+env series)
- W4: Reliability and engineering guidance
  - Strong fallback trade-offs (energy–end2end–p05) and recommended ranges
  - Energy fairness metrics; finalize paper figures/tables; artifacts

Principles
- Public datasets, fully reproducible scripts, clear statistics
- Conservative, explainable environment→channel mappings
- Report effect sizes and uncertainty; emphasize real-geometry realism

