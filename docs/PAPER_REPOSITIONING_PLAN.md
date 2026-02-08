# AERIS Paper Repositioning Plan

**Date**: 2026-02-06
**Status**: Multi-Environment Validation Complete

## 1. Background

Based on honest ablation analysis, the following issues were identified:
1. CAS multi-mode (CHAIN/TWO_HOP) was never triggered -> **FIXED, CHAIN 5-100% trigger rate (config-dependent)**
2. Gateway module has negative effect **across ALL 4 environments** (not just indoor_office)
   - indoor_office: +2.04% PDR when disabled
   - indoor_factory: +17.68% PDR when disabled
   - outdoor_urban: +17.55% PDR when disabled
   - outdoor_suburban: +14.99% PDR when disabled
   - Evidence: `ablation_diag_multi_20260206_020002.json` (n=30, publication)
3. CAS module has small negative effect (~0.6-1.8% PDR drop when enabled)
4. Skeleton/Safety modules have no measurable PDR impact

---

## 2. Adjusted Core Contributions

| Contribution | Original Claim | Adjusted Claim | Evidence |
|--------------|----------------|----------------|----------|
| Protocol Performance | AERIS outperforms all baselines | AERIS leads baselines in ALL 4 environments | `env_sensitivity_20260206_013048.json` (n=30) |
| CAS Module | Adaptive multi-mode selection | CHAIN triggerable but small negative effect on PDR | `cas_weight_sweep_full_20260206_000736.json` (n=30) |
| Gateway | Improves reliability | **Negative effect across all environments** (2-18% PDR drop) | `ablation_diag_multi_20260206_020002.json` (n=30) |
| Skeleton/Safety | Enhances robustness | No measurable PDR impact | `ablation_diag_multi_20260206_020002.json` (n=30) |

---

## 3. Multi-Environment 5-Protocol Comparison (n=30)

### 3.1 PDR Results by Environment

| Environment | AERIS | LEACH | PEGASIS | HEED | TEEN | AERIS Lead |
|-------------|-------|-------|---------|------|------|------------|
| indoor_office | **0.954** | 0.554 | 0.908 | 0.937 | 0.822 | +1.7% vs HEED |
| indoor_factory | **0.404** | 0.161 | 0.193 | 0.233 | 0.311 | +9.3% vs TEEN |
| outdoor_urban | **0.178** | 0.055 | 0.054 | 0.064 | 0.120 | +5.8% vs TEEN |
| outdoor_suburban | **0.581** | 0.270 | 0.338 | 0.422 | 0.475 | +10.6% vs TEEN |

**Conclusion**: AERIS leads all baselines in every environment tested.

**Evidence**: `env_sensitivity_20260206_013048.json` (n=30, publication)

---

## 4. Multi-Environment Ablation Results (n=30)

### 4.1 Gateway Negative Effect (Cross-Environment)

| Environment | full PDR | no_gateway PDR | Difference |
|-------------|----------|----------------|------------|
| indoor_office | 0.954 | **0.974** | +2.04% |
| indoor_factory | 0.404 | **0.581** | +17.68% |
| outdoor_urban | 0.178 | **0.353** | +17.55% |
| outdoor_suburban | 0.581 | **0.731** | +14.99% |

**Conclusion**: Gateway module consistently reduces PDR across all environments.

### 4.2 Module Effect Summary

| Module | Effect | Evidence |
|--------|--------|----------|
| Gateway | **Negative** (2-18% PDR drop) | Consistent across 4 environments |
| CAS | Small negative (~0.6-1.8%) | no_cas slightly higher than full |
| Skeleton | None | no_skeleton = full |
| Safety | None | no_safety = full |

**Evidence**: `ablation_diag_multi_20260206_020002.json` (n=30, publication)

---

## 5. Current CAS Mechanism

**Mode Selection Logic** (based on current cas_selector.py implementation):
1. **Rule Trigger** (rule_override=True): Forces mode based on density/radius/distance thresholds
2. **Score Competition**: Three modes compete based on weighted feature scores
3. **Symmetric Penalty**: Under high uncertainty, all mode scores converge toward mean (no asymmetric suppression)

**Key Configuration** (CASConfig defaults):
- chain_density_threshold = 0.6 (CHAIN rule trigger condition)
- twohop_dist_threshold = 0.6 (TWO_HOP rule trigger condition)
- lambda_uncertainty = 0.0 (CASConfig default)
  - **Runtime behavior**: AERIS dynamically raises lambda_uncertainty via stage-adaptive logic
  - Formula: max(base, 0.12 + 0.35 * stage_boost + 0.25 * switch_boost)
  - See aeris_protocol.py line 1740

---

## 6. Paper Positioning Adjustment

**Can Claim**:
- AERIS leads all baseline protocols across 4 environments
- CAS multi-mode is triggerable with appropriate configuration
- Framework provides complete WSN simulation capability

**Must Note**:
- Gateway module has consistent negative effect (limitation)
- CAS has small negative effect on PDR
- Harsh environments (factory/urban) have low absolute PDR

**Should NOT Claim**:
- Gateway improves reliability
- Multi-mode significantly improves performance
- Skeleton/Safety modules contribute to PDR

---

## 7. Target Journal

| Approach | Target Journal | Rationale |
|----------|----------------|-----------|
| Conservative | MDPI Sensors (Q2-Q3) | Framework contribution, complete experiments |

---

## 8. Evidence File List

| Description | File | Sample Size | Run Tier |
|-------------|------|-------------|----------|
| Multi-Env 5-Protocol | `env_sensitivity_20260206_013048.json` | n=30, 4 envs | publication |
| Multi-Env Ablation | `ablation_diag_multi_20260206_020002.json` | n=30, 4 envs x 6 configs | publication |
| CAS Weight Sweep | `cas_weight_sweep_full_20260206_000736.json` | n=30, 3 configs x 2 scenarios | publication |
| Single-Env 5-Protocol | `fair_5protocol_20260206_000956.json` | n=30, indoor_office | publication |
| Single-Env Ablation | `ablation_diag_20260205_144709.json` | n=30, indoor_office | publication |

---

## 9. Execution Status

- [x] Complete Plan A document
- [x] Create CAS weight sweep script
- [x] Run smoke test (n=5) - Fixed and passed
- [x] Fix run_cas_weight_sweep.py (4 vulnerabilities)
- [x] Run publication-level weight sweep (n=30) - Success
- [x] Run 5-protocol comparison (n=30) - Success
- [x] P0: Multi-env 5-protocol comparison (n=30, 4 envs) - Success
- [x] P1: Multi-env ablation study (n=30, 4 envs x 6 configs) - Success
- [x] Update PAPER_REPOSITIONING_PLAN.md with multi-env conclusions

---

Generated: 2026-02-06
Revised: 2026-02-06 (Multi-environment validation complete)
