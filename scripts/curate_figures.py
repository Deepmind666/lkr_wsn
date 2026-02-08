#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, shutil, zipfile, re
from datetime import datetime

ROOT = os.path.join(os.path.dirname(__file__), '..')
PLOTS = os.path.join(ROOT, 'results', 'plots')
OUT = os.path.join(ROOT, 'results', 'plots_curated')
OUT_PUB = os.path.join(ROOT, 'results', 'publication_figures')

# Compute dynamic n from significance JSON for caption
sig_path = os.path.join(ROOT, 'results', 'significance_compare_intel_parallel.json')
n_pdr = None
n_energy = None
if os.path.exists(sig_path):
    try:
        with open(sig_path, 'r', encoding='utf-8') as f:
            js = json.load(f)
        n_pdr = min(len(js['pdr_end2end_mean']['BASE'].get('values', [])), len(js['pdr_end2end_mean']['ROBUST'].get('values', [])))
        n_energy = min(len(js['total_energy_consumed']['BASE'].get('values', [])), len(js['total_energy_consumed']['ROBUST'].get('values', [])))
    except Exception:
        pass

if isinstance(n_pdr, int) and isinstance(n_energy, int) and n_pdr > 0 and n_energy > 0:
    if n_pdr == n_energy:
        cap_sig = f"Intel – PDR+Energy with 95% CI (n={n_pdr})"
    else:
        cap_sig = f"Intel – PDR+Energy with 95% CI (n_pdr={n_pdr}, n_energy={n_energy})"
else:
    cap_sig = "Intel – PDR+Energy with 95% CI"

# Intel – curated list (200 rounds)
FIGS = [
    ('F1', 'Intel – AERIS Energy (200 rounds)', 'paper_intel_energy.svg'),
    ('F2', 'Intel – AERIS End-to-End PDR (200 rounds)', 'paper_intel_pdr.svg'),
    # AERIS vs Baselines
    ('F3', 'Intel – AERIS vs Baselines: Energy', 'paper_intel_baselines_energy.svg'),
    ('F4', 'Intel – AERIS vs Baselines: End-to-End PDR', 'paper_intel_baselines_pdr.svg'),
    # Predicted env vs Conservative
    ('F5', 'Intel – Predicted env (LSTM/TCN) vs Conservative: Energy', 'paper_intel_predenv_energy.svg'),
    ('F6', 'Intel – Predicted env (LSTM/TCN) vs Conservative: End-to-End PDR', 'paper_intel_predenv_pdr.svg'),
    # Significance (combined, dynamic n)
    ('F7', cap_sig, 'paper_intel_sig_combined.svg'),
    # Multi-topology significance
    ('F8', 'Multi-Topology – Significance: PDR (Uniform vs Corridor), 95% CI', 'paper_multi_topo_sig_pdr.svg'),
    ('F9', 'Multi-Topology – Significance: Energy (Uniform vs Corridor), 95% CI', 'paper_multi_topo_sig_energy.svg'),
    # Uncertainty grid heatmap (PDR & Energy)
    ('F10', 'Robustness – Uncertainty Grid (λ_uncertainty × conf_threshold): PDR & Energy', 'paper_uncertainty_grid.svg'),
    # Classical envmap baselines (SARIMAX/ETS)
    ('F11', 'Intel – Classical envmap (SARIMAX/ETS): Energy', 'paper_intel_classical_envmap_energy.svg'),
    ('F12', 'Intel – Classical envmap (SARIMAX/ETS): End-to-End PDR', 'paper_intel_classical_envmap_pdr.svg'),
]

# Publication-ready new figures to sync (copy all formats if exist)
PUB_FIG_BASES = [
    'paper_multi_topo_sig_pdr',
    'paper_multi_topo_sig_energy',
    'paper_uncertainty_grid',
    'paper_intel_sig_combined',
    'paper_intel_ablation_pdr',
    'paper_intel_ablation_energy',
    'paper_intel_sens_pdr',
    'paper_intel_sens_energy',
    'paper_intel_classical_envmap_energy',
    'paper_intel_classical_envmap_pdr',
    'paper_intel_baselines_relative',
]

# ISJ minimal SVG package (only SVGs, fallback to publication if plots missing)
OUT_MIN = os.path.join(ROOT, 'results', 'isj_minimal_svg')
MIN_SVGS = [
    'paper_intel_pdr.svg',
    'paper_intel_energy.svg',
    # Add Gardner–Altman paired mean-difference plot for PDR
    'paper_intel_pdr_gardner_altman.svg',
    'paper_intel_sig_combined.svg',
    'paper_multi_topo_sig_pdr.svg',
    'paper_multi_topo_sig_energy.svg',
    'paper_uncertainty_grid.svg',
    'paper_safety_tradeoff.svg',
    'paper_intel_sens_pdr.svg',
    'paper_intel_sens_energy.svg',
    'paper_intel_ablation_pdr.svg',
    'paper_intel_ablation_energy.svg',
    # Classical envmap SVGs
    'paper_intel_classical_envmap_energy.svg',
    'paper_intel_classical_envmap_pdr.svg',
]

# QA scanner banlist and auto-fixes
BANNED_TERMS = [
    'AETHER', 'EASR',
    'Enhanced-AERIS', 'Enhanced\u2011AERIS', 'Enhanced‑AERIS',
    # 统一命名：弃用 EEHFR 系列
    'EEHFR', 'Enhanced EEHFR', 'Enhanced-EEHFR', 'Enhanced‑EEHFR',
    # 不专业/易误导标签（提示修正，不强制自动改）
    'ROBUST', 'BASE',
    # 明显拼写错误
    'baeline',
]

# 自动修复若干常见标注与排版问题（安全改动）
AUTO_REPLACE_MAP = [
    (r'\bbaeline\b', 'baseline'),
    # 统计方法排版统一为 en dash
    (r'Benjamini-\s*Hochberg', 'Benjamini–Hochberg'),
    (r'Holm-\s*Bonferroni', 'Holm–Bonferroni'),
    # 统一算法对外命名（可按需启用）。谨慎：仅替换纯文本标签，不改文件名/键名。
    (r'Enhanced\s+EEHFR', 'AERIS'),
    (r'Enhanced[-‑]EEHFR', 'AERIS'),
    (r'\bEEHFR\b', 'AERIS'),
    # Added: fix common mislabeled/forbidden terms discovered by QA
    (r"\bEASR\b", "AERIS"),
    (r"\bROBUST\b", "AERIS-R"),
    (r"\bBASE\b", "AERIS-E"),
]

def auto_fix_svg_text(root_dir: str):
    fixed_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if not fn.lower().endswith('.svg'):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    txt = f.read()
                orig = txt
                for pat, repl in AUTO_REPLACE_MAP:
                    try:
                        txt = re.sub(pat, repl, txt)
                    except re.error:
                        # Fallback: escape pattern if regex compilation fails
                        try:
                            txt = re.sub(re.escape(pat), repl, txt)
                        except Exception:
                            txt = txt.replace(pat, repl)
                if txt != orig:
                    with open(fp, 'w', encoding='utf-8') as f:
                        f.write(txt)
                    fixed_files.append(os.path.relpath(fp, ROOT).replace('\\', '/'))
            except Exception:
                pass
    if fixed_files:
        print('AUTO-FIX applied for:', len(fixed_files), 'SVGs')
        for p in fixed_files:
            print('  *', p)
    else:
        print('AUTO-FIX: no changes needed in', root_dir)

# 粗粒度“同线检测”：在同一 SVG 内，如存在多条完全相同的 path/polyline 数据，则报警

def detect_identical_paths(root_dir: str, min_report_dups: int = 1):
    issues = []
    path_d_re = re.compile(r'<path[^>]*\sd="([^"]+)"', re.IGNORECASE)
    poly_pts_re = re.compile(r'<polyline[^>]*\spoints="([^"]+)"', re.IGNORECASE)
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if not fn.lower().endswith('.svg'):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    txt = f.read()
                paths = path_d_re.findall(txt) + poly_pts_re.findall(txt)
                if not paths:
                    continue
                counts = {}
                for p in paths:
                    counts[p] = counts.get(p, 0) + 1
                dup_items = [(k, c) for k, c in counts.items() if c > 1]
                # 只统计重复数量，而不输出长字符串内容
                total_dups = sum(c - 1 for _, c in dup_items)
                if total_dups >= min_report_dups:
                    issues.append((os.path.relpath(fp, ROOT).replace('\\', '/'), len(dup_items), total_dups))
            except Exception:
                pass
    if issues:
        print('QA WARNING: identical paths/polylines detected (possible duplicated curves):')
        for rel, uniq_dup_kinds, total_dups in issues:
            print(f'  - {rel}: {uniq_dup_kinds} unique duplicated shapes, {total_dups} extra duplicates')
        print('  HINT: verify algorithm-to-curve mapping; duplicated shapes across different legends are suspicious.')
    else:
        print('QA OK: no identical path/polyline duplication detected in', root_dir)

# Simple QA scanner for curated/published SVGs

def scan_svg_text(root_dir: str):
    issues = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if not fn.lower().endswith('.svg'):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    txt = f.read()
                hits = [w for w in BANNED_TERMS if w in txt]
                if hits:
                    issues.append((fp, sorted(set(hits))))
            except Exception:
                pass
    if issues:
        print('QA WARNING: banned terms found in SVGs:')
        for fp, hits in issues:
            print('  -', os.path.relpath(fp, ROOT).replace('\\', '/'), '->', ', '.join(hits))
    else:
        print('QA OK: No banned terms found in', root_dir)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    for fid, caption, fname in FIGS:
        src = os.path.join(PLOTS, fname)
        dst = os.path.join(OUT, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            manifest.append({'id': fid, 'caption': caption, 'file': os.path.relpath(dst, ROOT).replace('\\', '/')})
        else:
            print('WARN: missing figure', src)
    # Save manifest
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump({'figures': manifest}, f, ensure_ascii=False, indent=2)
    # Save README for quick copy-paste guidance
    with open(os.path.join(OUT, 'README.txt'), 'w', encoding='utf-8') as f:
        f.write('Curated Figures for Word (copy/paste). Note: For ISJ, prefer inserting SVG for crisp scaling.\n')
        for m in manifest:
            f.write(f"{m['id']}: {m['caption']} -> {m['file']}\n")

    # Sync publication figures (SVG/PDF/PNG)
    os.makedirs(OUT_PUB, exist_ok=True)
    exts = ['.svg']
    copied_pub = []
    for base in PUB_FIG_BASES:
        for ext in exts:
            src = os.path.join(PLOTS, base + ext)
            dst = os.path.join(OUT_PUB, base + ext)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                copied_pub.append(os.path.relpath(dst, ROOT).replace('\\', '/'))
            else:
                print('WARN: missing publication figure', src)

    # Build minimal SVG package for ISJ
    os.makedirs(OUT_MIN, exist_ok=True)
    copied_min = []
    for fname in MIN_SVGS:
        src = os.path.join(PLOTS, fname)
        if not os.path.exists(src):
            src = os.path.join(OUT_PUB, fname)
        if os.path.exists(src):
            dst = os.path.join(OUT_MIN, fname)
            shutil.copy2(src, dst)
            copied_min.append(os.path.relpath(dst, ROOT).replace('\\', '/'))
        else:
            print('WARN: missing minimal SVG', fname)
    with open(os.path.join(OUT_MIN, 'README.txt'), 'w', encoding='utf-8') as f:
        f.write('ISJ minimal SVG package for direct insertion.\n')
        for p in copied_min:
            f.write(p + '\n')

    # --- New: Sensors journal aggregated figures ---
    SENSORS_DIR = os.path.join(ROOT, 'results', 'Sensors_figures')
    os.makedirs(SENSORS_DIR, exist_ok=True)
    # Union: curated list (FIGS) filenames + MIN_SVGS
    curated_names = [fname for (_, _, fname) in FIGS]
    union_names = []
    for name in curated_names + MIN_SVGS:
        if name not in union_names:
            union_names.append(name)
    copied_sensors = []
    missing_sensors = []
    for fname in union_names:
        src_candidates = [
            os.path.join(PLOTS, fname),
            os.path.join(OUT, fname),
            os.path.join(OUT_PUB, fname),
            os.path.join(OUT_MIN, fname),
        ]
        src = next((p for p in src_candidates if os.path.exists(p)), None)
        if src:
            dst = os.path.join(SENSORS_DIR, fname)
            try:
                shutil.copy2(src, dst)
                copied_sensors.append(os.path.relpath(dst, ROOT).replace('\\', '/'))
            except Exception as e:
                print('ERROR: copy failed for', fname, e)
        else:
            missing_sensors.append(fname)
    # 写入 Sensors 清单
    sensors_manifest = {
        'journal': 'Sensors',
        'note': 'Aggregated best figures (curated + minimal SVG) for Sensors submission.',
        'files': copied_sensors,
        'missing': missing_sensors,
    }
    with open(os.path.join(SENSORS_DIR, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(sensors_manifest, f, ensure_ascii=False, indent=2)
    with open(os.path.join(SENSORS_DIR, 'README.txt'), 'w', encoding='utf-8') as f:
        f.write('Sensors submission figures (SVG only). Use vector graphics in manuscript.\n')
        if missing_sensors:
            f.write('Missing (not found in any source):\n')
            for m in missing_sensors:
                f.write('  - ' + m + '\n')

    # 自动修复与同线检测（针对所有输出目录）
    try:
        for d in (OUT, OUT_PUB, OUT_MIN, SENSORS_DIR):
            auto_fix_svg_text(d)
            detect_identical_paths(d)
    except Exception as e:
        print('QA auto-fix/detect failed:', e)

    print('Curated figures saved to', OUT)
    print('Publication figures synced to', OUT_PUB)
    print('ISJ minimal SVG package synced to', OUT_MIN)
    print('Sensors figures aggregated to', SENSORS_DIR)

    # QA scans on curated and publication outputs
    try:
        scan_svg_text(OUT)
        scan_svg_text(OUT_PUB)
        scan_svg_text(OUT_MIN)
        scan_svg_text(SENSORS_DIR)
    except Exception:
        pass

    # --- New: package submission zips (CPU-only, pure Python) ---
    try:
        SUBMIT_DIR = os.path.join(ROOT, 'results', 'for_submission')
        os.makedirs(SUBMIT_DIR, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        # 新增：在提交目录执行自动文本修复与同线检测，确保标签统一
        try:
            auto_fix_svg_text(SUBMIT_DIR)
            detect_identical_paths(SUBMIT_DIR)
        except Exception as e:
            print('QA auto-fix/detect for submission failed:', e)

        def make_zip(src_dir: str, base: str):
            if not os.path.isdir(src_dir):
                print('WARN: skip zipping missing dir', src_dir)
                return None
            base_name = f"{base}_{ts}"
            out_path = os.path.join(SUBMIT_DIR, base_name)
            zip_path = shutil.make_archive(out_path, 'zip', src_dir)
            rel = os.path.relpath(zip_path, ROOT).replace('\\\\', '/')
            size = os.path.getsize(zip_path)
            print('Packed', rel, f'({size} bytes)')
            return {'name': base_name + '.zip', 'path': rel, 'size': size}

        artifacts = []
        artifacts.append(make_zip(OUT_PUB, 'ISJ_publication_figures'))
        artifacts.append(make_zip(OUT, 'ISJ_plots_curated'))
        artifacts.append(make_zip(OUT_MIN, 'ISJ_minimal_svg'))
        # New: Sensors aggregated
        artifacts.append(make_zip(SENSORS_DIR, 'Sensors_figures'))
        artifacts = [a for a in artifacts if a]

        # Write/update submission manifest
        manifest_path = os.path.join(SUBMIT_DIR, 'manifest.json')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump({'generated_at': ts, 'artifacts': artifacts}, f, ensure_ascii=False, indent=2)
        print('Submission package manifest ->', os.path.relpath(manifest_path, ROOT).replace('\\\\', '/'))
    except Exception as e:
        print('ERROR: packaging submission failed:', e)

