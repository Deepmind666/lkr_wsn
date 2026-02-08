# Codex Review and Next Work Assignment (2026-02-07)

## Scope Reviewed

- C:\AERIS-WSN-Protocol\results\mega_experiments\frozen_bundle_20260207\manifest.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\env_sensitivity_20260207_205317.provenance.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\ablation_diag_multi_20260207_205448.provenance.json
- C:\AERIS-WSN-Protocol\results\mega_experiments\fact_table_5protocol_pdr.csv
- C:\AERIS-WSN-Protocol\results\mega_experiments\fact_table_ablation_pdr_pvalues.csv
- C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section1_Introduction.md
- C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section8_Conclusion.md

## Verification Summary

1. Frozen bundle integrity passes:
   - manifest exists
   - 6/6 file SHA256 checks pass
2. Fact tables and p-values are internally consistent with result JSON files.
3. Section 1 and Section 8 remove the major forbidden claims (100% at 500 nodes, n=200, TDA validated).

## Critical Findings (Must Fix Before Final Paper Freeze)

1. Manuscript cleanliness issue in Section 1/8:
   - Both files include non-paper internal checklist blocks and garbled text encoding fragments at the end.
   - Evidence:
     - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section1_Introduction.md:145
     - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section8_Conclusion.md:60
2. Paper-wide consistency still incomplete:
   - Related work and system model still contain APIN target markers and unsupported old claims.
   - Evidence:
     - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section2_RelatedWork.md:3
     - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section2_RelatedWork.md:24
     - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section2_RelatedWork.md:32
     - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section2_RelatedWork.md:94
     - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section3_SystemModel.md:3
3. Evidence freeze is still dirty-worktree:
   - `git_dirty=true` and large unstaged delta are recorded in provenance.
   - This is acceptable for drafting but not ideal for final archive-grade reproducibility.

## Claim Gate (Current)

Allowed:
- AERIS ranks first in pdr_expected across 4 evaluated environments (n=30).
- Gateway effect is positive in 3/4 environments and non-significant in indoor_office.
- CAS effect is mixed, with outdoor_urban showing significant negative impact.

Forbidden:
- 100% PDR at 500 nodes.
- n=200 runs.
- TDA validated contribution.
- Absolute latency/energy claims without publication-tier evidence files in this manuscript version.

## Work Split (Codex + Claude)

### Claude Tasks

Task C1 (P0, manuscript cleanup):
- Remove all non-paper checklist/audit tail blocks from:
  - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section1_Introduction.md
  - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section8_Conclusion.md
- Ensure both files are plain manuscript text only.

Task C2 (P0, consistency patch):
- Update:
  - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section2_RelatedWork.md
  - C:\AERIS-WSN-Protocol\for_submission\AERIS_APIN_Section3_SystemModel.md
- Replace APIN target markers with Sensors.
- Remove or soften unsupported old absolute claims (500-node 100%, 2500ms absolute, etc.).

Task C3 (P1, final evidence note):
- Create one short note file:
  - C:\AERIS-WSN-Protocol\results\mega_experiments\FREEZE_STATE_NOTE_20260207.md
- Include:
  - why current bundle is dirty-state
  - what exact command set to rerun for clean-state freeze later

Claude acceptance criteria:
- No forbidden strings in Section 1/2/3/8:
  - "200 independent runs"
  - "100% PDR at 500"
  - "Applied Intelligence (APIN)"
- Section 1/8 tail checklist removed.

### Codex Tasks

Task X1 (P0, gate review):
- Re-run grep gate across Section 1/2/3/8 and produce pass/fail matrix.

Task X2 (P0, final table consistency):
- Verify all numeric claims used in Section 1/8 map to:
  - fact_table_5protocol_pdr.csv
  - fact_table_ablation_pdr_pvalues.csv

Task X3 (P1, handoff package):
- Produce a concise handoff prompt for next Claude session with strict scope.

## Repro Commands (for fast re-check)

```powershell
rg -n --fixed-strings "200 independent runs" for_submission
rg -n --fixed-strings "100% PDR" for_submission
rg -n --fixed-strings "Applied Intelligence (APIN)" for_submission
rg -n --fixed-strings "2500ms" for_submission
```

