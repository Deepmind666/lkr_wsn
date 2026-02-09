# 2026-02-09 Codex Strict Review and Next Actions

## 1) Scope

Reviewed artifacts:
- src/benchmark_protocols.py
- src/baseline_protocols/pegasis_protocol.py
- src/baseline_protocols/leach_protocol.py
- src/baseline_protocols/heed_protocol.py
- src/teen_protocol.py
- src/aeris_protocol.py
- scripts/run_latency_experiment.py
- scripts/extract_latency_stats.py
- for_submission/AERIS_APIN_Section6_Results.md
- results/mega_experiments/latency_*_20260209_13*.json
- results/mega_experiments/latency_hop_v2_stats.csv
- results/mega_experiments/latency_hop_v2_significance.csv

## 2) Findings (Severity Ordered)

### HIGH

None found in this review window.

### MEDIUM

1. Reproducibility risk in latency extraction input selection.
- File: scripts/extract_latency_stats.py:57-63, 225-233
- Issue: per-environment file is selected by "latest mtime". If one environment file is regenerated later than others, mixed-batch statistics can happen silently.
- Impact: cross-environment table may combine runs from different code/config states.
- Recommendation: add explicit input file arguments or a mandatory timestamp token for all 4 environments.

2. Latency metric for PEGASIS remains an estimator, not per-packet reconstructed path length.
- File: src/baseline_protocols/pegasis_protocol.py:363-370
- Issue: average chain hops is computed from chain geometry, then replicated for delivered payload. This is a model approximation; it does not reconstruct each delivered packet path.
- Impact: latency ranking is still directionally useful, but absolute hops for PEGASIS should be reported as model-based estimate.
- Recommendation: add a `latency_metric_note` in outputs and manuscript text to avoid overclaim.

3. Scalability path currently uses benchmark implementation with a duplicated cluster formation call.
- File: src/benchmark_protocols.py:438, 445
- Issue: `_form_clusters(cluster_heads)` is called twice in the same round path.
- Impact: unnecessary extra work and potential behavior drift in LEACH benchmark path during scalability jobs.
- Recommendation: remove the duplicate call after current long run completes (do not patch mid-run).

### LOW

1. Hop-count lazy-init checks remain in multiple protocols despite constructor initialization.
- File: src/baseline_protocols/leach_protocol.py:223-224
- File: src/baseline_protocols/heed_protocol.py:294-295
- File: src/baseline_protocols/pegasis_protocol.py:235-236
- Impact: harmless but redundant.
- Recommendation: keep for backward compatibility or remove in one cleanup commit.

2. Section 6 latency claims are mostly aligned and gated.
- File: for_submission/AERIS_APIN_Section6_Results.md:105-135
- Status: wording is now scoped to hop-based latency and cites significance table.
- Recommendation: add one sentence that PEGASIS hops are an estimated chain-latency proxy under current simulator abstraction.

## 3) Validation Summary

Validated:
- `run_latency_experiment.py` outputs `primary_metric = pdr_expected` and keeps hop metric secondary.
- `latency_hop_v2_significance.csv` shows all AERIS-vs-baseline hop comparisons significant after Holm correction.
- Active claim-gating grep on Section1/6/8 banned patterns is clean for the current non-`_CORRECTED` files.

## 4) Execution Plan (Local + Server)

### Local owner (Codex)
1. Keep current local scalability shard running unchanged to avoid mid-run code drift.
2. After completion, verify:
   - `exit_code=0`
   - `raw_results = 16500` per environment
   - provenance sidecars exist for each environment json
3. Produce local shard validation note and handoff.

### Server owner (Claude)
1. Run server shard with exactly the same parameters:
   - replicates 550
   - workers 12
   - nodes 100,200,300,500,800,1000
   - rounds 300
   - max cpu/mem 65/65
   - environments indoor_office,outdoor_suburban
2. Return full-path file list + metadata snapshot + ETA block.

### Merge/Gate (Codex)
1. Merge local + server scalability evidence.
2. Regenerate combined significance table.
3. Run forbidden-claim gate on manuscript sections before any new wording.

## 5) Current Runtime Status (Local)

- Job: `results/mega_experiments/overnight_scalability_20260209_163524`
- Current stage: env 1/2 (`indoor_factory`)
- Resource guard: CPU and memory under configured thresholds
- Note: no code edits should be applied to benchmark runtime files until this run finishes.

