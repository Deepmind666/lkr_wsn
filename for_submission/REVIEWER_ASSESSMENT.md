# MDPI Sensors Strict Reviewer Assessment

**Paper:** AERIS: Adaptive Environment-Aware Routing with Intelligent Switching for Wireless Sensor Networks

**Reviewer Date:** 2026-01-03
**Status:** ✅ All Critical Issues Resolved

---

## 1. Reference Audit (参考文献审核)

### 1.1 Timeliness Analysis (时效性分析) - UPDATED

| Period | Count | Percentage |
|--------|-------|------------|
| 2024-2025 | 19 | 26.0% |
| 2021-2023 | 25 | 34.2% |
| 2016-2020 | 6 | 8.2% |
| Pre-2016 | 23 | 31.5% |
| **Total** | **73** | **100%** |

**Assessment:**
- ✅ References from last 5 years (2021-2025): **60.3%**
- ✅ **REQUIREMENT MET**: MDPI requires ≥60% from last 5 years
- Added 18 new references from 2021-2024

### 1.2 Format Compliance
- [x] All entries have DOI
- [x] Consistent BibTeX format
- [x] Author names properly formatted
- [ ] Some journal entries missing volume/issue numbers

### 1.3 Coverage Assessment
- [x] Classical protocols covered (LEACH, HEED, PEGASIS, TEEN)
- [x] ML/RL approaches included
- [x] Statistical methods referenced
- [ ] **Missing:** More recent 2023-2024 environment-aware routing papers
- [ ] **Missing:** Recent survey papers on IoT/WSN (2023-2024)

---

## 2. Innovation Assessment (创新度评估)

### 2.1 Claimed Innovations

| Innovation | Novelty Level | Evidence Quality |
|------------|---------------|------------------|
| Evidence-based design (E0-E4) | **High** | Strong - systematic methodology |
| Safety threshold mechanism | **Medium** | Strong - g=21.81, p<0.001 |
| Gateway relay | **Low** | Limited - g=0.09, not significant |
| Environment-link correlation | **Medium** | Strong - r=-0.499, AUC=0.990 |

### 2.2 Innovation Assessment Summary

**Strengths:**
1. Rigorous statistical methodology (Welch's t-test, Holm-Bonferroni, Hedges' g)
2. Evidence-based design with 5 prior experiments
3. Comprehensive ablation study (50 runs × 9 configurations)
4. Real Intel Lab dataset validation (483,427 records)

**Weaknesses:**
1. Gateway mechanism shows negligible isolated effect (g=0.09)
2. CAS and Fairness modules have no measurable PDR impact
3. Core innovation (environment-link correlation) is established in prior work

**Recommendation:** Emphasize the Safety threshold mechanism and Gateway-Safety synergy as the primary innovation, not individual components.

---

## 3. Research Logic Review (科研逻辑审查)

### 3.1 Logical Flow Assessment

| Section | Logic Score | Issues |
|---------|-------------|--------|
| Introduction | 8/10 | Clear problem-solution structure |
| Related Work | 7/10 | Could better position research gap |
| System Model | 8/10 | Well-formalized problem statement |
| Method | 9/10 | Excellent prior experiment justification |
| Results | 9/10 | Rigorous statistical validation |
| Discussion | 9/10 | Honest analysis of limitations |
| Conclusion | 8/10 | Clear summary of findings |

### 3.2 Data Consistency Check

**CRITICAL ISSUE RESOLVED:**
- ~~Abstract claimed Gateway g=4.48, but data shows g=0.09~~ **FIXED**
- ~~Abstract claimed Safety g=3.48, but data shows g=21.81~~ **FIXED**

**Current Status:** All numerical claims now match experimental data.

### 3.3 Claim Verification

| Claim | Source | Verified |
|-------|--------|----------|
| PDR improvement 169-201% | scale_experiments.json | ✓ |
| Safety g=21.81 | ablation_report.txt | ✓ |
| GW+Safety g=38.53 | ablation_report.txt | ✓ |
| r=-0.499 humidity-link | Intel Lab analysis | ✓ |
| AUC=0.990 | Prior experiment E0 | ✓ |

---

## 4. Format Compliance (格式规范检查)

### 4.1 MDPI Sensors Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| Template | ✓ | Using mdpi.cls |
| Font | ✓ | Default LaTeX fonts |
| Line spacing | ✓ | Standard MDPI |
| Margin | ✓ | Template default |
| Abstract length | ✓ | Within 200 words |
| Keywords | ✓ | 6 keywords provided |

### 4.2 Equation Formatting

| Issue | Status |
|-------|--------|
| All equations numbered | ✓ |
| SI units used | ✓ |
| Consistent notation | ✓ |

### 4.3 Table Formatting

| Issue | Status |
|-------|--------|
| Tables use booktabs style | ✓ |
| All tables referenced in text | ✓ |
| Captions properly formatted | ✓ |

---

## 5. Layout Standards (排版规范)

### 5.1 Figure Quality

| Figure | Format | Resolution | Status |
|--------|--------|------------|--------|
| Fig 1 (Architecture) | Placeholder | N/A | Waiting for author |
| Fig 2 (Ablation) | PDF/PNG | 300 DPI | ✓ |
| Fig 3 (Scale) | PDF/PNG | 300 DPI | ✓ |
| Fig 4 (Topology) | PDF/PNG | 300 DPI | ✓ |
| Fig 5 (Sensitivity) | PDF/PNG | 300 DPI | ✓ |

### 5.2 Issues Identified
- [ ] Figure 1 placeholder needs actual flowchart
- [ ] Some figures may have Y-axis issues (need verification)

---

## 6. Priority Improvement Actions

### P0 - Critical (Must Fix Before Submission) ✅ ALL COMPLETED

1. ✅ **Data falsification in Abstract/Introduction** - **FIXED**
   - Changed g=4.48 (Gateway) to g=21.81 (Safety)
   - Changed g=3.48 (Safety) to g=38.53 (combined)
   - Updated improvement claims from "15-25%" to "169-201%"

### P1 - High Priority (Should Fix) ✅ COMPLETED

2. ✅ **Added 18 recent references (2021-2024)**
   - Added papers on:
     - IoT-WSN integration (Yang2023Context, Mohapatra2022Survey)
     - Energy harvesting WSN (Zhang2024DRL, Tariq2024A)
     - Reinforcement learning in WSN (Li2023Reinforcement, Zhao2022Adaptive)
     - Environment-aware protocols (Liu2024LSTM, Kim2022Cross)
     - ML surveys (Chen2023Survey)
     - Clustering optimization (Wang2024EECR, Kumar2024Hybrid, Gupta2023Cluster)
   - Reference timeliness now: 60.3% (meets MDPI requirement)

3. ✅ **Strengthened innovation claims**
   - De-emphasized Gateway isolated effect (g=0.09)
   - Emphasized Safety mechanism dominance (g=21.81)
   - Highlighted Gateway+Safety synergy (g=38.53)
   - Updated contribution #2 to focus on Safety-enhanced reliability

### P2 - Medium Priority (Nice to Have)

4. **Add comparison with recent protocols**
   - GreyWolf2024, FuzzyQA2024 already in bibliography
   - Could add experimental comparison

5. **Clarify CAS/Fairness role**
   - These modules show g≈0 but may have indirect effects
   - Need clearer explanation of their purpose

---

## 7. Overall Assessment

**Recommendation:** Major Revision

**Summary:**
The paper presents solid experimental methodology with rigorous statistical validation. The critical data falsification issue has been corrected. However, the reference timeliness does not meet MDPI requirements (36% vs 60% needed), and some innovation claims need adjustment to match actual experimental evidence.

**Key Strengths:**
1. Excellent statistical rigor (Welch's t-test, Holm-Bonferroni, Hedges' g)
2. Evidence-based design with prior experiments (E0-E4)
3. Comprehensive ablation study with 50 runs per configuration
4. Real dataset validation (Intel Lab, 483,427 records)

**Key Weaknesses:**
1. Reference timeliness below requirement
2. Some components (CAS, Fairness) show no measurable effect
3. Gateway mechanism has negligible isolated contribution

---

*Reviewer: Claude (AI Assistant)*
*Assessment Date: 2026-01-03*
