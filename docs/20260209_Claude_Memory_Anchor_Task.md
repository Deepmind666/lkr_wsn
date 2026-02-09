# Claude Memory Anchor Task (2026-02-09)

## Hard Constraints (Do Not Forget)

1. Do only assigned tasks. No extra experiments.
2. Do not edit `src/` unless explicitly assigned.
3. For every experiment progress update, always include:
   - current stage
   - elapsed time
   - runtime basis
   - remaining stages
   - ETA window
   - CPU% and MEM%
4. Keep machine load safe:
   - CPU <= 65%
   - MEM <= 65%
5. Report full plain-text absolute paths only.

## Current Assignment

Run server scalability shard only:

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

## Acceptance Checklist

1. `manifest.json` exists in new overnight output directory.
2. Both environment runs have `exit_code=0`.
3. Each environment json has `raw_results = 16500`.
4. Each environment json has matching `.provenance.json`.
5. Metadata fields present:
   - `git_commit`
   - `git_dirty`
   - `git_diff_stat`
   - `script_sha256`
   - `config_hash`
   - `run_tier`
   - `primary_metric`

## Response Template (Mandatory)

```text
File list:
- <full path>
- <full path>

Completed:
1) ...
2) ...

ETA block:
- current stage:
- elapsed:
- runtime basis:
- remaining stages:
- ETA:
- CPU% / MEM%:

Still to verify:
1) ...
2) ...
```

