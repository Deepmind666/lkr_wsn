#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, shutil, time

ROOT = os.path.join(os.path.dirname(__file__), '..')
RES = os.path.join(ROOT, 'results')

# Keep-list: essential JSONs/dirs that must remain in results/
KEEP_FILES = set([
    # Core comparisons
    'intel_replay_compare.json',
    'intel_lstm_envmap_compare.json',
    'intel_tcn_envmap_compare.json',
    'intel_lstm_envmap_extended.json',
    # Baselines
    'intel_baselines_all.json',
    'intel_baseline_leach.json',
    'intel_baseline_pegasis.json',
    # Significance & studies
    'significance_compare_intel_parallel.json',
    'intel_ablation.json',
    'intel_ablation_parallel.json',
    'intel_sensitivity.json',
    'intel_sensitivity_parallel.json',
    # Tables or curated exports that may be cited
    'paper_tables_20250730_001855.tex',
])
KEEP_DIRS = set([
    'plots_curated',   # final, paper-quality figures for Word
])

# Dirs we prefer to archive whole if present (raw plots, old logs etc.)
ARCHIVE_WHOLE_DIRS = [
    'plots', 'performance_charts', 'analysis_reports', 'benchmark_experiments', 'logs', 'publication_figures'
]

def main():
    ts = time.strftime('%Y%m%d-%H%M%S')
    archive_dir = os.path.join(RES, f"_archive_{ts}")
    os.makedirs(archive_dir, exist_ok=True)
    moved = []

    # Move whole directories first (if exist and not in KEEP_DIRS)
    for d in ARCHIVE_WHOLE_DIRS:
        src = os.path.join(RES, d)
        if os.path.isdir(src) and d not in KEEP_DIRS:
            dst = os.path.join(archive_dir, d)
            try:
                shutil.move(src, dst)
                moved.append({'type': 'dir', 'src': os.path.relpath(src, ROOT), 'dst': os.path.relpath(dst, ROOT)})
            except Exception as e:
                print('WARN: failed to move dir', src, '->', dst, 'err=', e)

    # Move stray files that are not in KEEP_FILES
    for name in os.listdir(RES):
        path = os.path.join(RES, name)
        if os.path.isdir(path):
            # keep curated figures dir and any newly created archive dirs
            if name in KEEP_DIRS or name.startswith('_archive_'):
                continue
            # other directories not listed above: archive them too
            dst = os.path.join(archive_dir, name)
            try:
                shutil.move(path, dst)
                moved.append({'type': 'dir', 'src': os.path.relpath(path, ROOT), 'dst': os.path.relpath(dst, ROOT)})
            except Exception as e:
                print('WARN: failed to move dir', path, '->', dst, 'err=', e)
            continue
        # file case
        if name in KEEP_FILES:
            continue
        # simple heuristic: keep JSONs we explicitly list; archive others (png, old json, md, csv, etc.)
        dst = os.path.join(archive_dir, name)
        try:
            shutil.move(path, dst)
            moved.append({'type': 'file', 'src': os.path.relpath(path, ROOT), 'dst': os.path.relpath(dst, ROOT)})
        except Exception as e:
            print('WARN: failed to move file', path, '->', dst, 'err=', e)

    # Write manifest in archive dir
    manifest_path = os.path.join(archive_dir, 'ARCHIVE_MANIFEST.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump({'moved': moved, 'keep_files': sorted(KEEP_FILES), 'keep_dirs': sorted(KEEP_DIRS)}, f, ensure_ascii=False, indent=2)
    print('Archived to', archive_dir, 'items moved:', len(moved))

if __name__ == '__main__':
    main()

