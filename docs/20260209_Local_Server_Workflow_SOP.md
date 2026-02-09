# AERIS Experiment SOP (Local + Server)

## 1. Purpose

This SOP defines one safe and reproducible workflow for long-running publication-tier experiments.

Hard safety limits:
- CPU usage <= 65%
- Memory usage <= 65%
- No unapproved experiment expansion

## 2. Role Split

- Local owner (Codex):
  - Run `indoor_factory,outdoor_urban`
  - Monitor process health and resource usage
  - Verify manifest and provenance sidecars
  - Merge and gate final conclusions

- Server owner (Claude):
  - Run `indoor_office,outdoor_suburban`
  - Use the same commit and same script parameters
  - Return result paths + validation checklist

## 3. Pre-Run Gate (Mandatory)

Run all checks before any long run:

1. `git rev-parse --short=8 HEAD` is the same on local and server.
2. `scripts/run_overnight_scalability_10h.ps1` and `scripts/run_scalability_experiment.py` are synced.
3. Resource limits are explicitly set:
   - `Workers=12`
   - `MaxCpuPercent=65`
   - `MaxMemPercent=65`
4. Experiment config is fixed:
   - `Replicates=550`
   - `Nodes=100,200,300,500,800,1000`
   - `Rounds=300`
5. Environment split is fixed:
   - Local: `indoor_factory,outdoor_urban`
   - Server: `indoor_office,outdoor_suburban`

## 4. Canonical Commands

### 4.1 Local run (Codex)

```powershell
powershell -File C:\AERIS-WSN-Protocol\scripts\run_overnight_scalability_10h.ps1 `
  -Replicates 550 `
  -Workers 12 `
  -Nodes "100,200,300,500,800,1000" `
  -Rounds 300 `
  -MaxCpuPercent 65 `
  -MaxMemPercent 65 `
  -Environments "indoor_factory,outdoor_urban"
```

### 4.2 Server run (Claude)

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

## 5. Runtime Monitoring

### 5.1 Progress log

```powershell
Get-Content C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_<timestamp>\run.log -Tail 50 -Wait
```

### 5.2 Resource snapshot

```powershell
$cpu=(Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples.CookedValue
$os=Get-CimInstance Win32_OperatingSystem
$mem=($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/$os.TotalVisibleMemorySize*100
"cpu=$([math]::Round($cpu,1))% mem=$([math]::Round($mem,1))%"
```

## 6. Acceptance Criteria

For each output directory:

1. `manifest.json` exists.
2. All listed environments have `exit_code=0`.
3. For each environment JSON:
   - `raw_results` count = `550 * 6 * 5 = 16500`.
4. Each `scalability_*.json` has one matching `scalability_*.provenance.json`.
5. Required metadata exists:
   - `git_commit`
   - `git_dirty`
   - `git_diff_stat`
   - `script_sha256`
   - `config_hash`
   - `run_tier`
   - `primary_metric`

## 7. Recovery Rules

If machine stability degrades:

1. Stop current run:
```powershell
Stop-Process -Id <pid> -Force
```
2. Reduce load and restart failed environments only:
   - `Workers=10`
   - Keep `MaxCpuPercent=65`, `MaxMemPercent=65`
3. Do not change seeds, nodes, rounds, or protocols.

## 8. Reporting Template

Use this exact structure in handoff reports:

```text
File list:
- <full path>
- <full path>

Completed:
1) ...
2) ...

Still to verify:
1) ...
2) ...
```

## 9. Mandatory ETA in Every Experiment Update

Each progress update must include all six items below:

1. Current stage
2. Elapsed time
3. Reference runtime basis (which prior logs/stages)
4. Remaining stages
5. Estimated remaining time window
6. Current resource snapshot (`CPU%`, `MEM%`)
