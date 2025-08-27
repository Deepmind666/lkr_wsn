#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, shutil

ROOT = os.path.join(os.path.dirname(__file__), '..')
PLOTS = os.path.join(ROOT, 'results', 'plots')
OUT = os.path.join(ROOT, 'results', 'plots_curated')

FIGS = [
    # Intel AETHER (200 rounds)
    ('F1', 'Intel – AETHER Energy (200 rounds)', 'paper_intel_energy.png'),
    ('F2', 'Intel – AETHER PDR End-to-End (200 rounds)', 'paper_intel_pdr.png'),
    # AETHER vs Baselines
    ('F3', 'Intel – AETHER vs Baselines: Energy', 'paper_intel_baselines_energy.png'),
    ('F4', 'Intel – AETHER vs Baselines: PDR End-to-End', 'paper_intel_baselines_pdr.png'),
    # Predicted env vs Conservative
    ('F5', 'Intel – Predicted env (LSTM/TCN) vs Conservative: Energy', 'paper_intel_predenv_energy.png'),
    ('F6', 'Intel – Predicted env (LSTM/TCN) vs Conservative: PDR End-to-End', 'paper_intel_predenv_pdr.png'),
    # Significance (n=50, 95% CI)
    ('F7', 'Intel – PDR with 95% CI (n=50)', 'paper_intel_sig_pdr.png'),
    ('F8', 'Intel – Energy with 95% CI (n=50)', 'paper_intel_sig_energy.png'),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    for fid, caption, fname in FIGS:
        src = os.path.join(PLOTS, fname)
        dst = os.path.join(OUT, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            manifest.append({'id': fid, 'caption': caption, 'file': os.path.relpath(dst, ROOT).replace('\\','/')})
        else:
            print('WARN: missing figure', src)
    # Save manifest
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump({'figures': manifest}, f, ensure_ascii=False, indent=2)
    # Save README for quick copy-paste guidance
    with open(os.path.join(OUT, 'README.txt'), 'w', encoding='utf-8') as f:
        f.write('Curated Figures for Word (copy/paste):\n')
        for m in manifest:
            f.write(f"{m['id']}: {m['caption']} -> {m['file']}\n")
    print('Curated figures saved to', OUT)

