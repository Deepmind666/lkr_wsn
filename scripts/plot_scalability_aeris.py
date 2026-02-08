import os
import time
import argparse
import math
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

matplotlib.rcParams['svg.fonttype'] = 'none'


def wait_for_file(path: str, timeout_s: int = 43200, poll_s: int = 10) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return True
        time.sleep(poll_s)
    return False


def agg_ci(series: pd.Series) -> pd.Series:
    m = series.mean()
    s = series.std(ddof=1)
    n = len(series)
    ci = 1.96 * (s / math.sqrt(n)) if n > 1 and np.isfinite(s) else 0.0
    return pd.Series({'mean': m, 'ci95': ci})


def plot_with_ci_unified(df: pd.DataFrame, key: str, order: list[str], out_path: str,
                         title: str, ylabel: str):
    if key not in df.columns:
        print(f"[Skip] metric not found: {key}")
        return
    grp = df.groupby(['protocol_unified', 'num_nodes'])[key].apply(agg_ci).unstack().reset_index()
    sns.set_theme(style='whitegrid', font_scale=1.1)
    palette = sns.color_palette('tab10', n_colors=len(order))
    plt.figure(figsize=(7.6, 4.8))
    for i, prot in enumerate(order):
        sub = grp[grp['protocol_unified'] == prot]
        if sub.empty:
            continue
        x = sub['num_nodes'].to_numpy()
        y = sub['mean'].to_numpy()
        yerr = sub['ci95'].to_numpy() if 'ci95' in sub.columns else None
        plt.errorbar(x, y, yerr=yerr, label=prot, marker='o', capsize=3, lw=2, color=palette[i])
    plt.xlabel('Number of nodes (N)')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend(title='Protocol', loc='best')
    plt.tight_layout()
    plt.savefig(out_path, format='svg')
    plt.close()
    print('[Saved]', out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', '-i', default=os.path.join('results', 'scalability_aeris_800_3seeds.csv'))
    ap.add_argument('--outdir', '-o', default=os.path.join('results', 'publication_figures'))
    ap.add_argument('--wait', '-w', action='store_true', help='wait for csv until it exists')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    if args.wait:
        print('[Watcher] waiting for', args.csv)
        ok = wait_for_file(args.csv)
        if not ok:
            raise SystemExit('[Error] timeout waiting for CSV')

    print('[Load]', args.csv)
    df = pd.read_csv(args.csv)
    if 'experiment_type' in df.columns:
        df = df[df['experiment_type'] == 'network_size'].copy()
    if 'num_nodes' in df.columns:
        df['num_nodes'] = df['num_nodes'].astype(int)

    # Keep raw protocol but unify for plotting: AERIS-E/R -> AERIS
    order_raw = ['LEACH', 'PEGASIS', 'HEED', 'AERIS-E', 'AERIS-R']
    if 'protocol' not in df.columns:
        raise SystemExit('[Error] CSV missing protocol column')
    df['protocol'] = pd.Categorical(df['protocol'], categories=order_raw, ordered=True)
    df['protocol_unified'] = df['protocol'].replace({'AERIS-E': 'AERIS', 'AERIS-R': 'AERIS'}).astype(str)
    order_unified = ['LEACH', 'PEGASIS', 'HEED', 'AERIS']
    df['protocol_unified'] = pd.Categorical(df['protocol_unified'], categories=order_unified, ordered=True)

    if 'peak_memory_bytes' in df.columns:
        df['peak_memory_mb'] = df['peak_memory_bytes'] / 1024.0 / 1024.0

    pdr_col = 'packet_delivery_ratio_end2end' if 'packet_delivery_ratio_end2end' in df.columns else (
        'packet_delivery_ratio' if 'packet_delivery_ratio' in df.columns else None)

    if pdr_col:
        plot_with_ci_unified(df, pdr_col, order_unified, os.path.join(args.outdir, 'aeris_pdr_vs_n.svg'),
                             'End-to-end PDR vs Network Size', 'End-to-end PDR')
    if 'network_lifetime' in df.columns:
        plot_with_ci_unified(df, 'network_lifetime', order_unified, os.path.join(args.outdir, 'aeris_lifetime_vs_n.svg'),
                             'Network Lifetime vs Network Size', 'Network lifetime (rounds)')
    if 'energy_efficiency' in df.columns:
        plot_with_ci_unified(df, 'energy_efficiency', order_unified, os.path.join(args.outdir, 'aeris_energy_efficiency_vs_n.svg'),
                             'Energy Efficiency vs Network Size', 'Energy efficiency')
    if 'execution_time' in df.columns:
        plot_with_ci_unified(df, 'execution_time', order_unified, os.path.join(args.outdir, 'aeris_exec_time_vs_n.svg'),
                             'Execution Time vs Network Size', 'Execution time (s)')
    if 'peak_memory_mb' in df.columns:
        plot_with_ci_unified(df, 'peak_memory_mb', order_unified, os.path.join(args.outdir, 'aeris_peak_memory_vs_n.svg'),
                             'Peak Memory vs Network Size', 'Peak memory (MB)')

    print('[Done] Figures in', args.outdir)


if __name__ == '__main__':
    main()