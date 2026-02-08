# Overnight Scalability Audit (2026-02-08)

## Scope

- C:\AERIS-WSN-Protocol\scripts\run_overnight_scalability_10h.ps1
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\manifest.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_indoor_office_20260208_005918.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_indoor_factory_20260208_005918.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_outdoor_urban_20260208_005918.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_outdoor_suburban_20260208_005918.json

## Run Status

- started_at: 2026-02-08 00:59:18
- finished_at: 2026-02-08 02:04:56
- elapsed_seconds: 3939 (~65.7 min)
- environments: 4
- exit_code: all 0

## Data Completeness Check (P0)

Config from manifest:
- replicates = 60
- node_counts = 6 (100,200,300,500,800,1000)
- protocols = 5 (AERIS, LEACH, PEGASIS, HEED, TEEN)

Expected raw_results per environment:
- 60 * 6 * 5 = 1800

Observed:
- indoor_office: 1800
- indoor_factory: 1800
- outdoor_urban: 1800
- outdoor_suburban: 1800

Conclusion:
- O-1 is resolved: output cardinality is correct.

## Provenance and Reproducibility

Observed in all 4 JSON files:
- run_tier = publication
- primary_metric = pdr_expected
- git_commit = 44b51f6
- experiment_type = scalability

Known gap (resolved, see Update section below):
- no sidecar `*.provenance.json` files in this overnight directory.

Seed range:
- each environment has 300 unique seed values from min=42377 to max=101617.
- this differs from frozen_bundle_20260207 (42001-42030), and must be disclosed when comparing cross-study results.

## Key Performance Snapshot (Max scale: 1000 nodes)

- indoor_office:
  - PEGASIS first (0.9993), AERIS 0.9900
- indoor_factory:
  - AERIS first (0.9899)
- outdoor_urban:
  - AERIS first (0.9900)
- outdoor_suburban:
  - AERIS first (0.9900)

Interpretation:
- AERIS leads in 3/4 environments at 1000 nodes.
- indoor_office remains PEGASIS-favorable.

## Required Follow-up

1. Add provenance sidecars for overnight outputs (git_dirty, git_diff_stat, script_sha256, source_sha256, config_hash).
2. Add a cross-run comparison note before using these results in manuscript claims.
3. Keep all claims scoped to:
   - metric: pdr_expected
   - environments: 4 listed above
   - settings: 60 replicates, nodes 100..1000, rounds 300.

## Update (2026-02-08, Codex)

P0 verification completed:

1. A-1 performance snapshot cross-check is confirmed from raw_results (1000 nodes):
   - indoor_office: PEGASIS 0.9993, AERIS 0.9900
   - indoor_factory: AERIS 0.9899
   - outdoor_urban: AERIS 0.9900
   - outdoor_suburban: AERIS 0.9900

2. O-2 provenance gap is closed via post-hoc sidecars:
   - C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_indoor_office_20260208_005918.provenance.json
   - C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_indoor_factory_20260208_005918.provenance.json
   - C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_outdoor_urban_20260208_005918.provenance.json
   - C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\scalability_outdoor_suburban_20260208_005918.provenance.json

3. Manifest schema issue (nodes string vs array) is fixed in script for future runs:
   - C:\AERIS-WSN-Protocol\scripts\run_overnight_scalability_10h.ps1 now writes nodes as array and keeps nodes_raw for compatibility.
