# AERIS Claim Gating List (Based on Publication Evidence)

Date: 2026-02-07  
Scope: Gate what can/cannot be written in paper text based on current publication-tier evidence.

## Evidence Used

- C:\AERIS-WSN-Protocol\results\mega_experiments\env_sensitivity_20260207_205317.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\ablation_diag_multi_20260207_205448.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\fact_table_5protocol_pdr.csv
- C:\AERIS-WSN-Protocol\results\mega_experiments\fact_table_ablation_pdr_pvalues.csv

## Integrity Status

- `run_tier`: publication (both files)
- `primary_metric`: pdr_expected (both files)
- `n`: 30 seeds per environment
- `git_commit`: 44b51f6f (both files)
- `git_dirty`: true (both files)
- `git_diff_stat`: 306 files changed (unstaged), staged clean

Decision: results are usable for paper drafting, but not final frozen archive evidence until a clean-state rerun exists.

## Claims Allowed (can write)

1. AERIS ranks first in PDR across all 4 tested environments (indoor_office, indoor_factory, outdoor_urban, outdoor_suburban), n=30.
2. AERIS vs each baseline is statistically significant (Welch's t-test p << 0.001 in all environments, from fact table).
3. Gateway effect is environment-dependent and mostly positive in current code state:
   - full > no_gateway with significance in indoor_factory, outdoor_urban, outdoor_suburban.
   - no significant difference in indoor_office.
4. CAS contribution is not uniformly positive:
   - outdoor_urban: no_cas > full (significant).
   - other environments: no significant full vs no_cas difference.
5. Skeleton and Safety show no measurable marginal effect in this setup (full == no_skeleton == no_safety within reported precision).

## Claims Forbidden (must not write)

1. "100% PDR at 500 nodes" or equivalent absolute large-scale claim without direct publication evidence.
2. "200 independent runs" (current publication standard is n=30 in these files).
3. "CAS consistently improves reliability across environments."
4. "Gateway is universally harmful" or "Gateway universally improves PDR."
5. Any latency absolute numbers (for example 110ms/2500ms) without publication-tier latency JSON evidence in the same manuscript version.
6. TDA metric contribution claim without publication-tier TDA result files.

## Safe Writing Pattern

- Use scoped language:
  - "Under the evaluated 4-environment, n=30 setup..."
  - "In current implementation state..."
  - "Observed statistically significant in 3/4 environments..."
- Always include metric and denominator:
  - "PDR (pdr_expected = bs_delivered / source_packets_expected)"

