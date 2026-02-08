# Claude4.6 Task Card (2026-02-08)

Owner: Codex
Execution model: strict, evidence-first, no extra scope

## Task A (P0): Overnight scalability significance table

Inputs:
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_indoor_office_20260208_005918.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_indoor_factory_20260208_005918.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_outdoor_urban_20260208_005918.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_outdoor_suburban_20260208_005918.json

Deliverables:
1. CSV: per environment x node_count, Welch t-test (AERIS vs each baseline), Hedges' g effect size.
2. Markdown summary with "can claim / cannot claim" statements.

Constraints:
- Metric must be pdr_expected only.
- Use node_counts [100, 200, 300, 500, 800, 1000].
- No manuscript edits in this task.

## Task B (P1): Manuscript scope synchronization

Inputs:
- C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section1_Introduction.md
- C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section6_Results.md
- C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section8_Conclusion.md
- C:\AERIS-WSN-Protocol\docs\20260208_Overnight_Scalability_Audit.md

Deliverables:
1. Scoped wording patch:
   - Separate 100-node multi-environment conclusions and 1000-node conclusions.
   - Explicitly state indoor_office@1000 PEGASIS > AERIS.
2. Remove any global wording that implies "all scales, all environments, always first".

Constraints:
- Keep forbidden-claim gate clean.
- Keep all statements tied to concrete files.
- Section6 is intentionally included to synchronize 100-node and 1000-node scopes.

## Task C (P1): 10-hour scalability run + provenance

Run command:
- powershell -File C:\AERIS-WSN-Protocol\scripts\run_overnight_scalability_10h.ps1 -Replicates 550 -Workers 22 -Nodes "100,200,300,500,800,1000" -Rounds 300

Immediately after completion:
- python C:\AERIS-WSN-Protocol\scripts\generate_scalability_provenance.py --overnight-dir results/mega_experiments/<new_overnight_dir>

Acceptance criteria (all required):
1. Task A/B outputs exist and forbidden-claim grep has 0 hits.
2. Task C manifest has 4 environments with exit_code = 0.
3. Each environment JSON has raw_results count = 16500 (550 x 6 x 5).
4. Each scalability JSON has a matching .provenance.json sidecar.
5. Final report includes:
   - Full output file paths
   - Total duration and per-stage duration
   - Metadata: git_commit, git_dirty, git_diff_stat, script_sha256, config_hash, run_tier, primary_metric
   - 1000-node protocol ranking per environment

Prohibited:
- Do not modify src core algorithms.
- Do not run unassigned experiments.
- Keep report concise with the required template only.

## Response format (required)

1. File list
2. What was done
3. What still needs verification
