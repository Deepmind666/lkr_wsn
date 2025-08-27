#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))

def run(cmd, cwd):
    print('>>>', ' '.join(cmd))
    p = subprocess.Popen(cmd, cwd=cwd)
    p.wait()
    if p.returncode != 0:
        raise SystemExit(f'Command failed: {cmd} (code={p.returncode})')

if __name__ == '__main__':
    py = sys.executable  # current interpreter
    repo = os.path.abspath(os.path.join(ROOT, '..'))

    # 1) Safety tradeoff grid and plot
    run([py, os.path.join(ROOT, 'run_safety_tradeoff_grid.py')], repo)
    run([py, os.path.join(ROOT, 'plot_safety_tradeoff.py')], repo)

    # 2) Significance compare (corridor 3:1)
    run([py, os.path.join(ROOT, 'run_significance_compare.py')], repo)

    # 3) Multi-topology significance (uniform, corridor 4:1)
    run([py, os.path.join(ROOT, 'run_significance_multi_topo.py')], repo)

    # 4) Intel Lab replay (public dataset)
    run([py, os.path.join(ROOT, 'run_intel_replay.py')], repo)
    run([py, os.path.join(ROOT, 'plot_paper_figures.py')], repo)

    print('All artifacts generated under results/.')

