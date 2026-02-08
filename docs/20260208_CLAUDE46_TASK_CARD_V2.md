# Claude4.6 Task Card V2 (Post-TaskC Launch)

Owner: Codex
Execution mode: strict, evidence-first, no unassigned experiments

## Task A (P0): Monitor active Task C and confirm single-run integrity

Inputs:
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_171857\run.log
- Process list (run_overnight_scalability_10h.ps1 / run_scalability_experiment.py)

Deliverables:
1. Confirm only one Task C pipeline is running.
2. Confirm active output directory is:
   C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_171857
3. Report current stage (which environment is running).

## Task B (P0): Generate corrected scalability significance outputs from raw_results

Inputs:
- C:\AERIS-WSN-Protocol\scripts\task_a_significance_table.py
- C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918\*.json

Run:
- python C:\AERIS-WSN-Protocol\scripts\task_a_significance_table.py --overnight-dir C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_20260208_005918 --out-prefix overnight_scalability_stats_20260208

Deliverables:
1. C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_stats_20260208_table.csv
2. C:\AERIS-WSN-Protocol\results\mega_experiments\overnight_scalability_stats_20260208_summary.md
3. Verify that Welch/Hedges are computed from raw_results per replicate (not synthetic reconstruction).

## Task C (P1): Post-run closure for active Task C

Trigger condition:
- Only execute after Task C finishes.

Run:
- python C:\AERIS-WSN-Protocol\scripts\generate_scalability_provenance.py --overnight-dir results/mega_experiments/overnight_scalability_20260208_171857

Deliverables:
1. 4 JSON + 4 .provenance.json in overnight directory.
2. Manifest shows 4 env exit_code = 0.
3. raw_results count per env = 16500.
4. 1000-node ranking per environment (AERIS vs baselines).

## Prohibited

1. Do not edit manuscript in this card.
2. Do not run NS-3 experiments in this card.
3. Do not start extra overnight jobs.

## Response format (required)

1. File list
2. What was done
3. What still needs verification
