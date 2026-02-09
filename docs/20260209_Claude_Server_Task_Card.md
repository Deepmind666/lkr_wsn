# Claude Server Task Card (2026-02-09)

## Scope

Run only server-side scalability shard with strict resource guard.
Do not edit `src/`.
Do not launch extra experiments.

## Inputs

- Repo root: `C:\AERIS-WSN-Protocol`
- SOP: `docs/20260209_Local_Server_Workflow_SOP.md`
- Script: `scripts/run_overnight_scalability_10h.ps1`
- Provenance generator: `scripts/generate_scalability_provenance.py`

## Task A (Execute Server Shard)

```powershell
powershell -File C:\AERIS-WSN-Protocol\scripts\run_overnight_scalability_10h.ps1 `
  -Replicates 550 `
  -Workers 12 `
  -Nodes "100,200,300,500,800,1000" `
  -Rounds 300 `
  -MaxCpuPercent 65 `
  -MaxMemPercent 65 `
  -Environments "indoor_office,outdoor_suburban"
```

## Task B (Post-run Validation)

For the new output directory, verify:

1. `manifest.json` exists.
2. Both environment entries have `exit_code=0`.
3. For each JSON output, `raw_results` length is `16500`.
4. Each `scalability_*.json` has matching `scalability_*.provenance.json`.
5. Metadata fields exist:
   - `git_commit`
   - `git_dirty`
   - `git_diff_stat`
   - `script_sha256`
   - `config_hash`
   - `run_tier`
   - `primary_metric`

## Task C (Return Report)

Return exactly:

```text
File list:
- <full path to output directory>
- <full path to manifest.json>
- <full path to each scalability_*.json>
- <full path to each scalability_*.provenance.json>

Completed:
1) total elapsed time
2) exit_code per environment
3) raw_results count per environment
4) metadata snapshot (git_commit, git_dirty, run_tier, primary_metric)
5) ETA block:
   - current stage
   - elapsed
   - runtime basis
   - remaining stages
   - estimated remaining
   - CPU% and MEM%

Still to verify:
1) any failed environment rerun required?
2) any metadata mismatch?
```

## Prohibitions

- No manuscript edits.
- No `src/` code edits.
- No parameter changes without approval.
- No run above CPU 65% or MEM 65%.
