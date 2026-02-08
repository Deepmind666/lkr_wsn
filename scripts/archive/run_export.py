#!/usr/bin/env python3
"""
One-click paper package pipeline.

This script orchestrates the full workflow to produce publication-ready figures
and a submission package from the existing project artifacts. Steps:

1) Generate paper figures (scripts/plot_paper_figures.py functions)
2) Generate 3D topology (via AdvancedVisualization with topology options)
3) Export a curated selection (AdvancedVisualization.export_publication_selection)
4) Run significance multi-testing correction (Holm–Bonferroni)
5) Compute effect sizes (Cohen's d, Hedges' g, Cliff's delta)
6) Curate and package outputs into results/for_submission/*.zip with manifest

Usage example:
  python scripts/run_export.py \
    --topo-symmetric-only \
    --topo-hub-topk-percent 7.5 \
    --topo-highlight-ids 1,2,48,49

You can skip steps via flags like --no-figures, --no-stats, --no-effects, --no-curate, --no-topology.
"""

import os
import sys
import argparse
import subprocess
from typing import List

# Ensure the 'scripts' directory is on sys.path so we can import local modules
sys.path.append(os.path.dirname(__file__))

from advanced_visualization import AdvancedVisualization


def _parse_highlight_ids(s: str) -> List[int]:
    if not s:
        return []
    out: List[int] = []
    for tok in s.split(','):
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.append(int(tok))
        except Exception:
            pass
    return out


def _run_subprocess(cmd: List[str], cwd: str = None, env: dict = None) -> int:
    print("[run]", " ".join(cmd))
    try:
        cp = subprocess.run(cmd, cwd=cwd, env=env, check=False)
        print(f"[done] exit={cp.returncode}")
        return cp.returncode
    except Exception as e:
        print("[error] subprocess failed:", e)
        return 1


def run_figures() -> None:
    # Prefer importing and calling to avoid new Python processes
    try:
        import plot_paper_figures as pf
        # Ensure paper mode styling and publication copy are applied
        os.environ.setdefault('PAPER_MODE', '1')
        os.environ.setdefault('PAPER_VALUE_LABELS', '0')
        # Execute all figures similarly to pf.__main__
        print('[fig] Generating paper figures...')
        try:
            pf.fig_safety_tradeoff()
        except Exception as e:
            print('[fig] fig_safety_tradeoff skipped:', e)
        try:
            pf.fig_baseline_bars()
        except Exception as e:
            print('[fig] fig_baseline_bars skipped:', e)
        try:
            pf.fig_intel_bars()
        except Exception as e:
            print('[fig] fig_intel_bars skipped:', e)
        try:
            pf.fig_intel_baselines_vs_aether()
        except Exception as e:
            print('[fig] fig_intel_baselines_vs_aether skipped:', e)
        try:
            pf.fig_intel_predenv_vs_conservative()
        except Exception as e:
            print('[fig] fig_intel_predenv_vs_conservative skipped:', e)
        try:
            pf.fig_intel_significance_bars()
        except Exception as e:
            print('[fig] fig_intel_significance_bars skipped:', e)
        try:
            pf.fig_intel_sig_combined()
        except Exception as e:
            print('[fig] fig_intel_sig_combined skipped:', e)
        try:
            pf.fig_intel_ablation()
        except Exception as e:
            print('[fig] fig_intel_ablation skipped:', e)
        try:
            pf.fig_intel_sensitivity()
        except Exception as e:
            print('[fig] fig_intel_sensitivity skipped:', e)
        # Reviewer-mode removed multi-topo significance inside pf
        try:
            pf.fig_uncertainty_grid_heatmap()
        except Exception as e:
            print('[fig] fig_uncertainty_grid_heatmap skipped:', e)
        try:
            pf.fig_intel_classical_envmap()
        except Exception as e:
            print('[fig] fig_intel_classical_envmap skipped:', e)
        try:
            pf.fig_intel_pdr_gardner_altman()
        except Exception as e:
            print('[fig] fig_intel_pdr_gardner_altman skipped:', e)
        print('[fig] Figures generation completed.')
    except Exception as e:
        print('[fig] Fallback to subprocess due to import error:', e)
        _run_subprocess([sys.executable, os.path.join(os.path.dirname(__file__), 'plot_paper_figures.py')])


def run_stats(alpha: float) -> None:
    env = os.environ.copy()
    env['MULTITEST_ALPHA'] = str(alpha)
    _ = _run_subprocess([sys.executable, os.path.join(os.path.dirname(__file__), 'run_stats_multitest.py')], env=env)


def run_effect_sizes() -> None:
    """
    Compute effect sizes using discovered significance_compare*.json files.
    
    This avoids CLI args by importing compute_effect_sizes.summarize_two_groups
    and feeding BASE/ROBUST raw value vectors for each metric/scenario.
    Outputs:
      - results/effect_sizes_summary.json
      - results/effect_sizes_summary.md
    """
    import os, json, glob
    try:
        from compute_effect_sizes import summarize_two_groups
    except Exception as e:
        print('[effects] compute_effect_sizes not importable:', e)
        print('[effects] skipping effect size computation')
        return

    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    results_dir = os.path.join(repo, 'results')
    patterns = [os.path.join(results_dir, 'significance_compare*.json')]
    files: list[str] = []
    for pat in patterns:
        files.extend(glob.glob(pat))
    files = sorted(set(files))

    if not files:
        print('[effects] No significance_compare*.json files found; skip effect sizes')
        return

    summary = {}

    def _extract_values(tbl):
        try:
            a = tbl.get('BASE', {}).get('values')
            b = tbl.get('ROBUST', {}).get('values')
            if isinstance(a, list) and isinstance(b, list) and len(a) > 0 and len(b) > 0:
                return a, b
        except Exception:
            pass
        return None

    for p in files:
        name = os.path.splitext(os.path.basename(p))[0]
        try:
            data = json.load(open(p, 'r', encoding='utf-8'))
        except Exception as e:
            print(f'[effects] Skip {p}: failed to load JSON, err={e}')
            continue

        if not isinstance(data, dict):
            continue

        # Case 1: single-scenario table
        top_values = list(data.values())
        if any(isinstance(v, dict) and ('BASE' in v and 'ROBUST' in v) for v in top_values):
            for metric, tbl in data.items():
                if not isinstance(tbl, dict):
                    continue
                sv = _extract_values(tbl)
                if sv is None:
                    continue
                a, b = sv
                stats = summarize_two_groups(a, b, paired=False)
                summary.setdefault(name, {})[metric] = stats
        else:
            # Case 2: multi-scenario table
            for scenario, table in data.items():
                if not isinstance(table, dict):
                    continue
                for metric, tbl in table.items():
                    if not isinstance(tbl, dict):
                        continue
                    sv = _extract_values(tbl)
                    if sv is None:
                        continue
                    a, b = sv
                    stats = summarize_two_groups(a, b, paired=False)
                    summary.setdefault(f'{name}:{scenario}', {})[metric] = stats

    if not summary:
        print('[effects] No valid BASE/ROBUST value vectors found; skip effect sizes')
        return

    # Write outputs
    os.makedirs(results_dir, exist_ok=True)
    out_json = os.path.join(results_dir, 'effect_sizes_summary.json')
    out_md = os.path.join(results_dir, 'effect_sizes_summary.md')
    try:
        with open(out_json, 'w', encoding='utf-8') as fj:
            json.dump(summary, fj, ensure_ascii=False, indent=2)
        with open(out_md, 'w', encoding='utf-8') as fm:
            fm.write('# 效应量汇总\n\n')
            for scenario, metrics in summary.items():
                fm.write(f'## {scenario}\n')
                for metric, stats in metrics.items():
                    fm.write(
                        f"- {metric}: n1={stats['n1']}, n2={stats['n2']}, "
                        f"Cohen's d={stats['cohen_d']}, Cliff's δ={stats['cliffs_delta']}, "
                        f"CLES={stats['cles']}\n"
                    )
                fm.write('\n')
        print('[effects] Saved', out_json)
        print('[effects] Saved', out_md)
    except Exception as e:
        print('[effects] Failed to write outputs:', e)


def run_curate_and_package() -> None:
    _ = _run_subprocess([sys.executable, os.path.join(os.path.dirname(__file__), 'curate_figures.py')])


def main() -> None:
    parser = argparse.ArgumentParser(description='One-click paper export pipeline')
    parser.add_argument('--no-figures', action='store_true', help='Skip generating paper figures')
    parser.add_argument('--no-stats', action='store_true', help='Skip significance multi-test pipeline')
    parser.add_argument('--no-effects', action='store_true', help='Skip effect size computation')
    parser.add_argument('--no-curate', action='store_true', help='Skip curation and packaging step')
    parser.add_argument('--no-topology', action='store_true', help='Skip 3D topology generation step')
    parser.add_argument('--alpha', type=float, default=0.05, help='Overall alpha for Holm-Bonferroni (default: 0.05)')
    # Topology options passthrough
    parser.add_argument('--topo-symmetric-only', dest='topo_symmetric_only', action='store_true', help='Use symmetric-only edges for 3D topology')
    parser.add_argument('--topo-hub-topk-percent', dest='topo_hub_topk_percent', type=float, default=5.0, help='Hub top-k percent threshold (e.g., 5.0)')
    parser.add_argument('--topo-highlight-ids', dest='topo_highlight_ids', type=str, default='', help='Comma-separated node ids to highlight in 3D topology')

    args = parser.parse_args()

    # 1) Figures
    if not args.no_figures:
        run_figures()
    else:
        print('[skip] figures')

    # 2) 3D topology via AdvancedVisualization
    if not args.no_topology:
        hl_ids = _parse_highlight_ids(args.topo_highlight_ids)
        try:
            viz = AdvancedVisualization()
            print('[topo] Generating 3D topology with options:', {
                'symmetric_only': args.topo_symmetric_only,
                'hub_topk_percent': args.topo_hub_topk_percent,
                'highlight_ids': hl_ids
            })
            viz.create_3d_network_topology(
                symmetric_only=args.topo_symmetric_only,
                hub_topk_percent=args.topo_hub_topk_percent,
                highlight_ids=hl_ids
            )
        except Exception as e:
            print('[topo] generation failed:', e)
    else:
        print('[skip] 3D topology')

    # 3) Export curated selection via AdvancedVisualization helper
    try:
        viz2 = AdvancedVisualization()
        exported = viz2.export_publication_selection()
        print('[export] Exported figures:', len(exported))
    except Exception as e:
        print('[export] failed:', e)

    # 4) Stats
    if not args.no_stats:
        run_stats(args.alpha)
    else:
        print('[skip] stats')

    # 5) Effect sizes
    if not args.no_effects:
        run_effect_sizes()
    else:
        print('[skip] effects')

    # 6) Curate and package
    # Comment out the curate and package step to remove ZIP generation
    # if not args.no_curate:
    #     run_curate_and_package()
    # else:
    #     print('[skip] curate')
    print('[modified] Skipped curate and package for pure SVG output')


if __name__ == "__main__":
    main()