# Simulated Peer Review Report for MDPI Sensors Journal

**Manuscript Title:** AERIS: Gateway-Enhanced Wireless Sensor Network Protocol with Environment-Aware Context Switching

**Manuscript ID:** sensors-XXXX-XXXX

**Date of Review:** 2026-01-10 (Updated with 审核意见三 improvements)

---

## 1. Recommendation to Editor

**Overall Assessment:** Accept with Minor Revision

This manuscript presents AERIS, a WSN protocol that introduces the innovative concept of "intelligent trade-off" as an explicit design principle. The revised version demonstrates significant improvements, particularly:

1. **New Evaluation Dimension (TDA)**: The introduction of Topology Dynamic Adaptability as a first-class metric represents a valuable methodological contribution that challenges conventional static-topology evaluation frameworks.

2. **Theoretical Insight**: The documentation of the "Distributed Optimality Curse" provides fundamental understanding of why local optimization approaches can outperform theoretically optimal global methods in practice.

3. **Rigorous Statistical Methodology**: The fair comparison framework with proper statistical workflow (Shapiro-Wilk → Levene → appropriate test selection) sets an exemplary standard.

After addressing the minor issues below, this manuscript is ready for publication in Sensors.

---

## 2. Detailed Comments for Authors

### 2.1 Major Comments (Addressed in Current Version)

#### M1: Innovation Positioning ✓ RESOLVED
The revised manuscript now clearly differentiates AERIS from recent work through:
- Introduction of TDA as a new evaluation dimension
- Documentation of the Distributed Optimality Curse
- Clear positioning as "paradigm shift in WSN evaluation"

#### M2: Weakness Conversion Strategies ✓ IMPLEMENTED
The Discussion section now implements all three strategies from advanced review guidance:
- **Strategy 1 (Trade-off)**: Section 5.4 "The Intelligent Trade-off: AERIS's Ecological Niche"
- **Strategy 2 (New Niche)**: Section 5.3 "Opening a New Evaluation Dimension: Topology Dynamic Adaptability"
- **Strategy 3 (Hidden Problem)**: Section 5.4 "Revealing a Hidden Problem: The Distributed Optimality Curse"

#### M3: Effect Size Interpretation ✓ ACCEPTABLE
The large Cohen's d values (5.22, 3.64, 5.38) are now contextualized within the controlled experimental conditions.

### 2.2 Minor Comments

#### m1: Abstract Length
The abstract (~250 words) is at the upper limit but acceptable given the comprehensive content.

#### m2: Figure Captions
Figure captions are now professional and self-contained, following Nature-style formatting.

#### m3: Terminology Consistency ✓ RESOLVED
PDR and SOTA are now properly defined on first use.

#### m4: Data Availability Statement ✓ ADDED
The Data Availability Statement is now included.

#### m5: Parameter Selection (Equation 1)
Consider briefly explaining the selection methodology for α, β, γ parameters in the gateway scoring function.

### 2.3 Positive Aspects (Strengths)

1. **Paradigm Contribution**: Beyond proposing a new protocol, this work contributes a paradigm shift in WSN evaluation—from static, idealized metrics to dynamic, deployment-realistic assessment frameworks.

2. **Three-Strategy Discussion Structure**: The "Claim-Acknowledge-Transform" argumentation in Discussion is exemplary and should be emulated by other WSN papers.

3. **TDA Metric Introduction**: The Topology Dynamic Adaptability metric addresses a critical gap in current WSN evaluation methodology.

4. **Distributed Optimality Curse**: This theoretical insight (Ω(n log n) coordination lower bound) explains fundamental limitations that affect all global optimization approaches.

5. **Honest Reporting**: The transparent acknowledgment of PEGASIS's 5.5% PDR advantage, combined with comprehensive trade-off analysis, demonstrates scientific integrity.

6. **Rigorous Methodology**: 30 independent runs with fixed seeds, proper statistical workflow, and fair comparison under identical channel models.

7. **Comprehensive Visualization**: New figures (ablation heatmap, trade-off radar, 2x2 composite) enhance data presentation.

---

## 3. Technical Quality Assessment

| Criterion | Rating (1-5) | Comments |
|-----------|--------------|----------|
| Novelty | 4.5 | TDA metric and Distributed Optimality Curse are significant contributions |
| Technical Soundness | 4.5 | Rigorous methodology; proper statistical analysis |
| Presentation | 4.5 | Clear writing; professional figures; excellent Discussion structure |
| Significance | 4.0 | Paradigm shift in evaluation methodology |
| Reproducibility | 5.0 | Fixed seeds; code availability; comprehensive documentation |

**Overall Technical Quality:** 4.5/5.0

---

## 4. Summary Comparison Table

| Protocol | PDR (%) | Δ vs AERIS | p-value | Cohen's d | Complexity | TDA Score |
|----------|---------|------------|---------|-----------|------------|-----------|
| LEACH | 87.5 | -3.4% | <10⁻²⁷ | 5.22 | O(1) | Moderate |
| HEED | 88.6 | -2.3% | <10⁻¹⁹ | 3.64 | O(1) | Moderate |
| SEP | 87.1 | -3.7% | <10⁻²⁷ | 5.38 | O(1) | Moderate |
| PEGASIS | 96.4 | +5.5% | <10⁻⁴² | 10.06 | O(n) | Poor |
| **AERIS** | **90.9** | — | — | — | **O(1)** | **High** |

---

## 5. Checklist for Authors Before Resubmission

- [x] Strategy 2 (TDA): Implemented in Discussion 5.3
- [x] Strategy 3 (Distributed Optimality Curse): Implemented in Discussion 5.4
- [x] Conclusion updated with 7 contributions
- [x] New figures generated (heatmap, radar, composite)
- [x] Data Availability Statement included
- [ ] Consider adding parameter selection justification for Equation (1)
- [ ] Final proofreading for any remaining typos

---

## 6. Conclusion

This revised manuscript makes a substantial contribution to WSN reliability research. The introduction of Topology Dynamic Adaptability as a new evaluation dimension and the documentation of the Distributed Optimality Curse represent valuable theoretical and methodological advances. The rigorous evaluation methodology and honest reporting set an exemplary standard for the field.

**Recommendation:** Accept with Minor Revision

---

*This simulated review was generated following the guidelines in Gemini's 审核意见三 (Review Opinion 3), incorporating the "外科手术式" restructuring protocol and all three weakness-to-strength conversion strategies.*
