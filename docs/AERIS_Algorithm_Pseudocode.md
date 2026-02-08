# AERIS Algorithm Pseudocode (for Methods Section)

Date: 2025-10-24

## Overview
AERIS integrates prediction-driven environment mapping with fairness and safety constraints to guide routing and clustering decisions in WSNs.

## Inputs
- Network graph `G(V,E)`; nodes `V` with residual energy `E_i`, positions `x_i`.
- Traffic demands `D_i`, sensing schedules.
- Predicted environment map `Env̂` from TCN/LSTM/PatchTST.
- Parameters: fairness weight `λ_f`, safety weight `λ_s`, energy weight `λ_e`.

## Outputs
- Cluster heads and gateway assignments
- Routing paths and forwarding schedules

## Pseudocode
```
Initialize state S ← {E_i, x_i, D_i} for all nodes i ∈ V
Env̂ ← PredictEnvironmentMap(S, history, model)
RiskGrid ← ComputeRisk(Env̂)              # heatmap for link-level risk (interference, attenuation)
FairnessBudget ← InitFairnessBudget(V)    # group/region-level fairness targets
SafetyConstraints ← InitSafetyConstraints(RiskGrid)

function AERIS_ROUND(S, Env̂):
    # 1) Candidate selection
    Cands ← SelectCandidates(V)           # pre-filter by residual energy, centrality
    Scores ← {}
    for c in Cands:
        # Energy efficiency
        s_e ← EnergyScore(c, S)
        # Fairness (penalize over-represented regions/groups)
        s_f ← FairnessPenalty(c, FairnessBudget)
        # Safety (prefer low-risk links/routes)
        s_s ← SafetyScore(c, RiskGrid)
        # Aggregate
        Scores[c] ← λ_e · s_e − λ_f · s_f + λ_s · s_s

    # 2) Skeleton formation (cluster heads / gateways)
    Skeleton ← BuildSkeleton(Scores, k_heads, k_gateways)

    # 3) Route planning under constraints
    Routes ← ConstrainedRouting(G, Skeleton, RiskGrid,
                                fairness=FairnessBudget,
                                safety=SafetyConstraints,
                                energy=E)

    # 4) Schedule & update budgets
    Schedule ← BuildForwardingSchedule(Routes, D)
    FairnessBudget ← UpdateFairness(FairnessBudget, Routes)
    SafetyConstraints ← UpdateSafety(SafetyConstraints, Schedule)

    # 5) Commit and log
    Apply(Schedule)
    LogRoundMetrics(Energy(Schedule), PDR(Schedule), Risk(Schedule))
    return Skeleton, Routes, Schedule
```

## Notes
- `PredictEnvironmentMap` uses trained models (e.g., `pytorch_tcn_env.py`, `pytorch_lstm_env.py`, `pytorch_patchtst_env.py`).
- `ConstrainedRouting` enforces fairness (group quotas, exposure limits) and safety (risk thresholds), while optimizing energy.
- Metrics reported per round and aggregated for significance testing.

## Complexity
- Candidate scoring: `O(|V|)` per round
- Routing with constraints: depends on solver; typical `O(|E| log |V|)` with heuristics

## References to Code
- `src/aeris_protocol.py`, `src/gateway_selector.py`, `src/skeleton_selector.py`
- Environment models: `src/pytorch_*_env.py`
- Fairness & safety: `src/fairness_metrics.py`