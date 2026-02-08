#!/usr/bin/env python3
"""
Stale File Cleanup Script for AERIS-WSN-Protocol

Usage:
    python scripts/cleanup_stale_files.py --preview   # Preview only
    python scripts/cleanup_stale_files.py --execute   # Actually delete

Generated: 2026-02-06
"""

import os
import sys
import argparse
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# =============================================================================
# MUST KEEP FILES (Publication-level evidence)
# =============================================================================
MUST_KEEP = {
    # Publication evidence (n=30)
    'results/mega_experiments/cas_weight_sweep_full_20260206_000736.json',
    'results/mega_experiments/fair_5protocol_20260206_000956.json',
    'results/mega_experiments/ablation_diag_20260205_144709.json',
    'results/mega_experiments/env_sensitivity_20260206_013048.json',
    'results/mega_experiments/ablation_diag_multi_20260206_020002.json',
    # Core docs
    'docs/PAPER_REPOSITIONING_PLAN.md',
    '.claude/RULES.md',
    '.codex/RULES.md',
}

# =============================================================================
# DELETABLE FILES BY CATEGORY
# =============================================================================

# 1. results/mega_experiments/ - Smoke/diagnostic files
DELETABLE_MEGA_EXPERIMENTS = [
    # Smoke tests (superseded by publication versions)
    'ablation_diag_20260205_141605.json',
    'ablation_diag_smoke_20260205_125441.json',
    'ablation_diag_smoke_20260205_133924.json',
    'ablation_diag_smoke_20260205_135127.json',
    'ablation_sparse_lowpower_smoke_20260205_150454.json',
    'ablation_sparse_lowpower_smoke_20260205_150532.json',
    'ablation_sparse_lowpower_smoke_20260205_150638.json',
    'cas_weight_sweep_smoke_20260205_152403.json',
    'cas_weight_sweep_smoke_20260205_161649.json',
    'cas_weight_sweep_smoke_20260205_161727.json',
    'cas_weight_sweep_smoke_20260205_161824.json',
    'cas_weight_sweep_smoke_20260205_175406.json',
    'cas_weight_sweep_smoke_20260205_193406.json',
    'cas_weight_sweep_smoke_20260205_232541.json',
    'fair_5protocol_smoke_20260205_121738.json',
    'fair_5protocol_smoke_20260205_122438.json',
    'fair_5protocol_smoke_20260205_125801.json',
    'fair_5protocol_smoke_20260205_134043.json',
    'fair_5protocol_smoke_20260205_135105.json',
    'fair_5protocol_20260205_121802.json',
    'fair_5protocol_20260205_122456.json',
    'fair_5protocol_20260205_141516.json',
    'fair_5protocol_20260205_144638.json',
    'env_sensitivity_smoke_20260205_125304.json',
    'baseline_compare_20260205_110543.json',
    'baseline_compare_20260205_110728.json',
    # Old mega experiments (Jan 25)
    'all_mega_results.json',
    'exp1_scalability.json',
    'exp2_longterm.json',
    'exp3_topology.json',
    'exp4_ablation.json',
    'exp5_sensitivity.json',
    'exp6_bootstrap.json',
    'exp7_stress.json',
    'exp8_intel.json',
    # Feb 4 batch (duplicates/outdated)
    'ablation_multi_scenario_20260204_020653.json',
    'ablation_multi_scenario_20260204_030615.json',
    'area_scaling_20260204_141929.json',
    'area_size_sweep_20260204_154222.json',
    'environment_sensitivity_20260204_020655.json',
    'environment_sensitivity_20260204_043209.json',
    'extreme_conditions_20260204_141643.json',
    'full_power_env_cross_20260204_124846.json',
    'long_lifetime_20260204_020655.json',
    'long_lifetime_20260204_043804.json',
    'mega_scale_n2000_20260204_123310.json',
    'power_sensitivity_20260204_020654.json',
    'power_sensitivity_20260204_035542.json',
    'round_sensitivity_20260204_140430.json',
    'round_sensitivity_20260204_141244.json',
    'statistical_significance_20260204_153203.json',
    'ultra_lifetime_r5000_20260204_132203.json',
    'ultra_long_r2000_20260204_122648.json',
    'ultra_scale_20260204_020656.json',
    'ultra_scale_20260204_044103.json',
    # Feb 5 duplicates
    'dense_power_sweep_20260204_211616.json',
    'dense_power_sweep_20260205_003533.json',
    'node_density_sweep_20260205_001521.json',
    'node_density_sweep_20260205_032017.json',
    'round_sensitivity_extended_20260205_015950.json',
    'round_sensitivity_extended_20260205_033154.json',
]

# 2. docs/ - Outdated documents
DELETABLE_DOCS = [
    # Outdated project status (2025 Sep-Oct)
    'Project_Status_Summary_2025.md',
    'Project_Status_Summary_2025_01_30.md',
    'Project_Status_and_Improvement_Plan_2025_01_30.md',
    'Project_Status_and_Next_Steps_2025.md',
    'Progress_Summary_2025_01_30.md',
    'Final_Project_Status_2025_01_30.md',
    'Final_Honest_Assessment_2025_01_30.md',
    'Final_Honest_Project_Summary.md',
    'Performance_Breakthrough_Analysis_2025_01_30.md',
    'Project_Progress_Summary_2025.md',
    'Project_Completion_Assessment_2025_10_19.md',
    'Work_Summary_2025_10_19.md',
    'Final_Progress_Report_2025_10_19.md',
    # Outdated improvement plans
    '2026-01-23_improvement_plan.md',
    '2026-01-26_improvement_plan.md',
    '2026-01-27_改进计划_v2.md',
    '2026-01-27_改进计划与实验计划.md',
    '2026-01-28_Claude_Code_Fix_Plan.md',
    '2026-01-28_Code_Fix_Report.md',
    '2026-01-28_codex_self_check_plan.md',
    '2026-01-28_Deep_Diagnosis_Report.md',
    '2026-01-28_Plan_Vulnerability_Analysis.md',
    '2026-01-28_Ultra_Scale_Experiment_Plan.md',
    # Empty file
    'Scientific_Innovation_Assessment.md',
]

# 3. scripts/ - Debug/outdated scripts
DELETABLE_SCRIPTS = [
    # Debug scripts
    'debug_aeris_pdr.py',
    'debug_aeris_pdr_v2.py',
    'debug_pdr_return.py',
    'debug_teen.py',
    'diagnose_energy.py',
    'diagnose_energy_anomaly.py',
    'diagnose_pdr_detailed.py',
    'diagnose_pdr_gap.py',
    # Probe scripts
    '_probe_anaconda.py',
    '_probe_dml.py',
    '_probe_torch_cuda.py',
    'sys_probe.py',
    # GPU/CPU burn (non-core)
    'cpu_burn.py',
    'cpu_burn_pure.py',
    'gpu_burn.py',
    'gpu_burn_dml.py',
    # Duplicate versions
    'generate_figure4_ablation.py',
    'generate_figure4_ablation_fixed.py',
    'generate_figure4_ablation_v2.py',
    'validate_p0_strict.py',
    'validate_p0_strict_v2.py',
    # Outdated fix scripts
    'fix_duplicate_init.py',
    'fix_enum_name.py',
    'fix_power_settings.py',
    'fix_result_keys.py',
    'apply_p0_fixes.py',
    'manual_patch_hops.py',
    'add_hop_tracking.py',
]


def get_full_paths():
    """Convert relative paths to full paths."""
    files = []

    for f in DELETABLE_MEGA_EXPERIMENTS:
        files.append(PROJECT_ROOT / 'results' / 'mega_experiments' / f)

    for f in DELETABLE_DOCS:
        files.append(PROJECT_ROOT / 'docs' / f)

    for f in DELETABLE_SCRIPTS:
        files.append(PROJECT_ROOT / 'scripts' / f)

    return files


def get_must_keep_paths():
    """Return absolute paths that must never be deleted."""
    return { (PROJECT_ROOT / p).resolve() for p in MUST_KEEP }


def preview_deletions():
    """Preview files to be deleted."""
    files = get_full_paths()
    must_keep = get_must_keep_paths()

    existing = []
    missing = []
    protected = []

    for f in files:
        f_res = f.resolve()
        if f_res in must_keep:
            protected.append(f)
            continue
        if f.exists():
            existing.append(f)
        else:
            missing.append(f)

    print("=" * 60)
    print("STALE FILE CLEANUP PREVIEW")
    print("=" * 60)

    print(f"\n[EXISTS - Will Delete] ({len(existing)} files)")
    print("-" * 40)

    total_size = 0
    for f in sorted(existing):
        size = f.stat().st_size
        total_size += size
        rel_path = f.relative_to(PROJECT_ROOT)
        print(f"  {rel_path} ({size:,} bytes)")

    print(f"\n  Total: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")

    if missing:
        print(f"\n[NOT FOUND - Skip] ({len(missing)} files)")
        print("-" * 40)
        for f in sorted(missing)[:10]:
            rel_path = f.relative_to(PROJECT_ROOT)
            print(f"  {rel_path}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")

    print("\n" + "=" * 60)
    print("To execute deletion, run:")
    print("  python scripts/cleanup_stale_files.py --execute")
    print("=" * 60)

    if protected:
        print(f"\n[PROTECTED - MUST_KEEP] ({len(protected)} files)")
        print("-" * 40)
        for f in sorted(protected):
            rel_path = f.relative_to(PROJECT_ROOT)
            print(f"  {rel_path}")

    return existing


def execute_deletions():
    """Actually delete the files."""
    files = get_full_paths()
    must_keep = get_must_keep_paths()

    deleted = []
    failed = []
    skipped = []
    protected = []

    for f in files:
        f_res = f.resolve()
        if f_res in must_keep:
            protected.append(f)
            continue
        if not f.exists():
            skipped.append(f)
            continue

        try:
            f.unlink()
            deleted.append(f)
        except Exception as e:
            failed.append((f, str(e)))

    print("=" * 60)
    print("DELETION COMPLETE")
    print("=" * 60)
    print(f"  Deleted: {len(deleted)}")
    print(f"  Skipped (not found): {len(skipped)}")
    print(f"  Protected (must keep): {len(protected)}")
    print(f"  Failed: {len(failed)}")

    if failed:
        print("\nFailed files:")
        for f, err in failed:
            print(f"  {f}: {err}")

    return deleted, failed


def main():
    parser = argparse.ArgumentParser(description='Cleanup stale files')
    parser.add_argument('--preview', action='store_true', help='Preview only')
    parser.add_argument('--execute', action='store_true', help='Execute deletion')
    args = parser.parse_args()

    if not args.preview and not args.execute:
        print("Usage:")
        print("  python scripts/cleanup_stale_files.py --preview")
        print("  python scripts/cleanup_stale_files.py --execute")
        sys.exit(1)

    if args.preview:
        preview_deletions()
    elif args.execute:
        confirm = input("Are you sure you want to delete files? (yes/no): ")
        if confirm.lower() == 'yes':
            execute_deletions()
        else:
            print("Aborted.")


if __name__ == '__main__':
    main()
