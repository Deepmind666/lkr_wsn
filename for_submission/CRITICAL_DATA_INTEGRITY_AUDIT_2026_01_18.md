# CRITICAL DATA INTEGRITY AUDIT REPORT
## AERIS Protocol Paper - Pre-Submission Self-Review
## Date: 2026-01-18

---

# EXECUTIVE SUMMARY: MAJOR ISSUES FOUND

This audit identifies **critical data integrity issues** that MUST be corrected before any journal submission.

## SEVERITY LEVELS
- **CRITICAL**: False claims that constitute academic misconduct
- **MAJOR**: Significant discrepancies requiring correction
- **MINOR**: Minor inaccuracies or missing information

---

# ISSUE #1: FABRICATED RUN COUNT CLAIM [CRITICAL]

## Paper Claims:
> "200 independent runs per configuration" (Section 6, Data Authenticity Statement)

## Actual Data Found:
| Experiment File | Actual Runs |
|-----------------|-------------|
| comprehensive_dynamic_experiments.json | **10-15 runs** |
| significance_compare_50x200.json | **5 values** |
| scalability_experiment.json | **30 replicates** |
| fair_comparison_results.json | **30 runs** |
| baseline_comparison.json | **50 replicates** |
| sota_experiments_quick | **3-5 runs** |

## Maximum Observed: 50 runs
## Paper Claimed: 200 runs

**This is a 4× exaggeration of experimental rigor and constitutes academic misconduct.**

### Required Action:
- [ ] Change "200 independent runs" to actual run count per experiment
- [ ] Or run actual experiments with 200 repetitions

---

# ISSUE #2: SCALABILITY DATA FABRICATION [CRITICAL]

## Paper Claims (Table 3 - Scalability PDR):
| Protocol | 50 Nodes | 100 Nodes | 200 Nodes | 300 Nodes | 500 Nodes |
|----------|----------|-----------|-----------|-----------|-----------|
| LEACH | 100.0% | 100.0% | 99.71% | 99.30% | **98.68%** |
| AERIS | 100.0% | 100.0% | 100.0% | 100.0% | **100.0%** |

## Actual Data Found:

### scalability_experiment.json:
- **Only tests 30, 50, 70, 100 nodes** - NOT 200, 300, 500!
- No 500-node experiments exist in this file

### large_scale_long.json (300 nodes):
- LEACH PDR: **67.22%** (NOT 99.30%!)
- AERIS PDR: 100%

## Discrepancy:
- Paper claims LEACH@300 = 99.30%
- Actual data shows LEACH@300 = 67.22%
- **32% discrepancy** - this is NOT a rounding error

### Required Action:
- [ ] Remove 200-500 node claims from Table 3 if no experiments exist
- [ ] Or run actual 500-node experiments
- [ ] Correct LEACH PDR values to match actual data

---

# ISSUE #3: LATENCY DATA FABRICATION [CRITICAL - ALREADY CORRECTED]

Previous audit found fabricated latency claims:
- "96% latency reduction"
- "110ms vs 2500ms"
- O(log n) latency complexity

**Status: CORRECTED on 2026-01-18** - All latency claims removed from paper.

---

# ISSUE #4: INCONSISTENT PDR VALUES [MAJOR]

## Paper vs Data Comparison:

| Claim | Paper Value | Actual Data Source | Actual Value | Match? |
|-------|-------------|-------------------|--------------|--------|
| LEACH@100 nodes | 100.0% | comprehensive_dynamic_experiments | 100.0% | YES |
| AERIS@100 nodes | 100.0% | comprehensive_dynamic_experiments | 100.0% | YES |
| LEACH@300 nodes | 99.30% | large_scale_long.json | 67.22% | **NO** |
| LEACH@500 nodes | 98.68% | ? | No direct evidence | **UNVERIFIED** |
| PEGASIS@500 nodes | 100.0% | ? | No direct evidence | **UNVERIFIED** |

---

# ISSUE #5: ENERGY DATA VERIFICATION [MAJOR]

## Paper Claims (Table 1):
| Protocol | Energy (mJ) |
|----------|-------------|
| LEACH | 100.7 |
| PEGASIS | 41.9 |
| AERIS | 82.1 |

## Verification:
From `comprehensive_dynamic_experiments.json`:
- AERIS energy_mean: **82.11** mJ ✓ MATCHES
- LEACH energy_mean: **100.72** mJ ✓ MATCHES
- PEGASIS energy_mean: **41.87** mJ ✓ MATCHES

**Energy data appears accurate for 100-node baseline.**

---

# ISSUE #6: FIGURE DATA AUTHENTICITY [MAJOR]

## Figures in Paper:
1. `aeris_professional_12panel.pdf`
2. `mega_figure_12panel.pdf`
3. `fig_advanced_analysis.pdf`
4. `sota_comparison_6panel.pdf`

## Question:
Do these figures use fabricated 500-node data or real experimental data?

### Required Action:
- [ ] Verify each figure's data source
- [ ] Regenerate figures from actual experimental data only
- [ ] Document data lineage for each figure

---

# ISSUE #7: STATISTICAL CLAIMS [MAJOR]

## Paper Claims:
- Cohen's d = 1.89 (AERIS vs LEACH PDR at 500 nodes)
- p < 0.001
- Holm-Bonferroni correction applied

## Verification Needed:
If 500-node experiments don't exist or only have 3-5 runs, these statistical claims are invalid:
- Cannot compute meaningful Cohen's d with n=3
- p-values unreliable with small samples

### Required Action:
- [ ] Verify sample sizes for statistical tests
- [ ] Recalculate statistics with actual run counts
- [ ] Remove or correct invalid statistical claims

---

# SUMMARY OF REQUIRED CORRECTIONS

## Before Submission, MUST:

1. **Correct run count claims**
   - Change "200 runs" to actual values (10-50 depending on experiment)

2. **Fix scalability table**
   - Remove unsupported 200-500 node claims OR
   - Run actual experiments at these scales

3. **Verify all PDR values**
   - LEACH@300 nodes: 99.30% → 67.22% (if using large_scale_long.json)
   - Or find correct data source

4. **Audit all figures**
   - Ensure no figure uses fabricated data

5. **Recalculate statistics**
   - Use actual sample sizes

---

# HONEST ASSESSMENT

The paper currently contains **multiple instances of data that cannot be traced to actual experiments**. This is a serious academic integrity issue.

## Options:
1. **Run missing experiments**: Actually perform 200-run experiments at 200-500 node scales
2. **Reduce claims**: Only report data that actually exists
3. **Acknowledge limitations**: Be transparent about experimental scope

## Recommendation:
**Option 2** - Reduce claims to match actual data. This is the honest approach.

The paper can still demonstrate AERIS's value with:
- 100-node experiments (well-documented, 10-30 runs)
- Intel Lab data (54 nodes, 50 replicates)
- Honest comparison showing PEGASIS is more energy-efficient

---

# ACTION ITEMS

- [ ] Correct Section 6 run count claims
- [ ] Update Table 3 (Scalability) with actual data or remove
- [ ] Verify and update Table 4 (Statistics)
- [ ] Audit all figures for data authenticity
- [ ] Update Data Authenticity Statement
- [ ] Re-read entire paper for any remaining unsupported claims

---

**Report Generated**: 2026-01-18
**Auditor**: Claude Code (Self-Review)
**Status**: PAPER NOT READY FOR SUBMISSION
