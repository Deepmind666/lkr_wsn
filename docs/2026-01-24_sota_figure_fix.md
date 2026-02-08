# 2026-01-24 SOTA 6-Panel Figure Review & Fix

## Scope
- Target figure: `for_submission/figures/sota_comparison_6panel.*`
- Focus: panel (c) readability, panel (d) clutter, table font size (panel f), layout collisions.

## Issues Observed (before fix)
- Panel (c) looked under-informative to reviewers (points sparse/unclear, label used “baseline”).
- Panel (d) looked visually flat and could be read as “too smooth,” raising doubts about variability.
- Panel (f) table text too small relative to panel size, making values hard to read.
- Overall spacing made right-column panels feel compressed.

## Fixes Applied (script-level)
- Enlarged right column for panels (c)/(f) by increasing `GridSpec` width ratio.
- Panel (c):
  - Kept AERIS‑E/AERIS‑R with larger offsets for clarity.
  - Removed “baseline” wording in axis label (use “protocol”).
  - Added “Positive favors AERIS” annotation to disambiguate direction.
  - Expanded x‑range padding so CI bars are fully visible.
- Panel (d):
  - Added per‑run scatter (low alpha) plus mean ± 95% CI overlay.
  - Keeps variability visible while preserving readability.
- Panel (f):
  - Increased table font size and scaling for readability.
- Re-generated outputs in both `results/publication_figures/` and `for_submission/figures/`.

## Output Files
- `for_submission/figures/sota_comparison_6panel.pdf`
- `for_submission/figures/sota_comparison_6panel.png`
- `for_submission/figures/sota_comparison_6panel.svg`

## Paper Draft Update (Same-Day)
- Updated SOTA comparison paragraph + caption in `for_submission/aeris_paper_final.tex`
  to match the new 7-protocol SOTA figure (LEACH/HEED/PEGASIS/SEP/TEEN + AERIS‑E/R).
- Replaced outdated numbers (n=60, 94.6% PDR, etc.) with values from
  `results/sota_comparison.json` (n=30 runs).

## Notes / Next Checks
- Confirm panel (c) shows all protocols (LEACH/HEED/PEGASIS/SEP/TEEN) vs both AERIS‑E/AERIS‑R.
- Confirm panel (f) text legibility at 100% zoom in the compiled PDF.
- If reviewer still finds panel (d) unconvincing, consider showing survival curves in a separate figure instead of embedding here.

## Next Steps (Pending Approval)
- If figure is accepted, update manuscript to ensure caption matches “ΔPDR vs protocols (AERIS‑E/R)”.
- If algorithm fairness is questioned, rerun with a fully unified channel model for AERIS (same as baselines) and regenerate.
