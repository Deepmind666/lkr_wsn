#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate LaTeX Tables for Comprehensive Experiment Results

Creates publication-ready LaTeX tables for:
1. Dynamic adaptability comparison (node churn)
2. Scalability analysis
3. Statistical summary with effect sizes

Author: AERIS Research Team
Date: 2026-01-12
"""

import os
import json
import numpy as np
from scipy import stats

def load_results(results_path):
    """Load experiment results from JSON file"""
    if os.path.exists(results_path):
        with open(results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def cohens_d(group1, group2):
    """Calculate Cohen's d effect size"""
    n1, n2 = len(group1) if isinstance(group1, list) else 1, len(group2) if isinstance(group2, list) else 1
    var1 = np.var(group1) if isinstance(group1, list) else 0
    var2 = np.var(group2) if isinstance(group2, list) else 0
    mean1 = np.mean(group1) if isinstance(group1, list) else group1
    mean2 = np.mean(group2) if isinstance(group2, list) else group2

    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2)) if n1+n2 > 2 else 1
    return (mean1 - mean2) / pooled_std if pooled_std > 0 else 0


def generate_churn_table(results):
    """Generate LaTeX table for churn experiment"""
    if not results or 'churn_experiment' not in results:
        return None

    data = results['churn_experiment']
    protocols = [p for p in data.keys() if p != 'config']
    churn_rates = data['config']['churn_rates']

    latex = r"""\begin{table}[H]
\centering
\caption{Protocol Performance Under Node Churn (PDR \%)}
\label{tab:churn_results}
\begin{tabular}{l""" + "c" * len(churn_rates) + r"""}
\toprule
\textbf{Protocol} & """ + " & ".join([f"\\textbf{{{int(r*100)}\\%}}" for r in churn_rates]) + r""" \\
\midrule
"""

    for protocol in protocols:
        if protocol in data:
            row = [protocol]
            for rate in churn_rates:
                key = f"churn_{int(rate*100)}pct"
                if key in data[protocol]:
                    pdr = data[protocol][key]['pdr_mean'] * 100
                    std = data[protocol][key].get('pdr_std', 0) * 100
                    row.append(f"{pdr:.1f}$\\pm${std:.1f}")
                else:
                    row.append("--")
            latex += " & ".join(row) + r" \\" + "\n"

    latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    return latex


def generate_scalability_table(results):
    """Generate LaTeX table for scalability experiment"""
    if not results or 'scalability_experiment' not in results:
        return None

    data = results['scalability_experiment']
    protocols = [p for p in data.keys() if p != 'config']
    node_counts = data['config']['node_counts']

    latex = r"""\begin{table}[H]
\centering
\caption{Protocol Scalability Analysis (PDR \% and Execution Time)}
\label{tab:scalability_results}
\begin{tabular}{l""" + "cc" * len(node_counts) + r"""}
\toprule
& """ + " & ".join([f"\\multicolumn{{2}}{{c}}{{\\textbf{{{n} nodes}}}}" for n in node_counts]) + r""" \\
\cmidrule(lr){2-3}""" + "".join([f"\\cmidrule(lr){{{2+i*2}-{3+i*2}}}" for i in range(1, len(node_counts))]) + r"""
\textbf{Protocol} & """ + " & ".join(["PDR & Time"] * len(node_counts)) + r""" \\
\midrule
"""

    for protocol in protocols:
        if protocol in data:
            row = [protocol]
            for n in node_counts:
                key = f"nodes_{n}"
                if key in data[protocol]:
                    pdr = data[protocol][key]['pdr_mean'] * 100
                    time_s = data[protocol][key].get('exec_time_mean', 0)
                    row.extend([f"{pdr:.1f}\\%", f"{time_s:.2f}s"])
                else:
                    row.extend(["--", "--"])
            latex += " & ".join(row) + r" \\" + "\n"

    latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    return latex


def generate_summary_table(results):
    """Generate comprehensive summary table"""
    if not results:
        return None

    latex = r"""\begin{table}[H]
\centering
\caption{Comprehensive Protocol Comparison Summary}
\label{tab:summary}
\begin{tabular}{lccccc}
\toprule
\textbf{Metric} & \textbf{AERIS} & \textbf{LEACH} & \textbf{PEGASIS} & \textbf{HEED} & \textbf{Winner} \\
\midrule
"""

    # Collect metrics from various experiments
    metrics = []

    # Static PDR (from churn at 0%)
    if 'churn_experiment' in results:
        data = results['churn_experiment']
        row = ["Static PDR (0\\% churn)"]
        best_val = 0
        best_proto = ""
        for proto in ['AERIS', 'LEACH', 'PEGASIS', 'HEED']:
            if proto in data and 'churn_0pct' in data[proto]:
                val = data[proto]['churn_0pct']['pdr_mean'] * 100
                row.append(f"{val:.1f}\\%")
                if val > best_val:
                    best_val = val
                    best_proto = proto
            else:
                row.append("--")
        row.append(f"\\textbf{{{best_proto}}}")
        metrics.append(" & ".join(row))

    # Dynamic PDR (from churn at 20%)
    if 'churn_experiment' in results:
        data = results['churn_experiment']
        row = ["Dynamic PDR (20\\% churn)"]
        best_val = 0
        best_proto = ""
        for proto in ['AERIS', 'LEACH', 'PEGASIS', 'HEED']:
            if proto in data and 'churn_20pct' in data[proto]:
                val = data[proto]['churn_20pct']['pdr_mean'] * 100
                row.append(f"{val:.1f}\\%")
                if val > best_val:
                    best_val = val
                    best_proto = proto
            else:
                row.append("--")
        row.append(f"\\textbf{{{best_proto}}}")
        metrics.append(" & ".join(row))

    # Scalability at 300 nodes
    if 'scalability_experiment' in results:
        data = results['scalability_experiment']
        row = ["Large-scale PDR (300 nodes)"]
        best_val = 0
        best_proto = ""
        for proto in ['AERIS', 'LEACH', 'PEGASIS', 'HEED']:
            if proto in data and 'nodes_300' in data[proto]:
                val = data[proto]['nodes_300']['pdr_mean'] * 100
                row.append(f"{val:.1f}\\%")
                if val > best_val:
                    best_val = val
                    best_proto = proto
            else:
                row.append("--")
        row.append(f"\\textbf{{{best_proto}}}")
        metrics.append(" & ".join(row))

    # Regional failure at 30m
    if 'regional_failure_experiment' in results:
        data = results['regional_failure_experiment']
        row = ["Regional failure PDR (30m)"]
        best_val = 0
        best_proto = ""
        for proto in ['AERIS', 'LEACH', 'PEGASIS', 'HEED']:
            if proto in data and 'radius_30m' in data[proto]:
                val = data[proto]['radius_30m']['pdr_mean'] * 100
                row.append(f"{val:.1f}\\%")
                if val > best_val:
                    best_val = val
                    best_proto = proto
            else:
                row.append("--")
        row.append(f"\\textbf{{{best_proto}}}")
        metrics.append(" & ".join(row))

    latex += " \\\\\n".join(metrics) + r""" \\
\bottomrule
\end{tabular}
\end{table}
"""
    return latex


def main():
    """Main function to generate all tables"""
    print("=" * 60)
    print("GENERATING LATEX TABLES FOR EXPERIMENT RESULTS")
    print("=" * 60)

    results_path = os.path.join(os.path.dirname(__file__), '..', 'results',
                                'comprehensive_dynamic_experiments.json')

    results = load_results(results_path)

    if results is None:
        print(f"WARNING: Results file not found at {results_path}")
        return

    output_path = os.path.join(os.path.dirname(__file__), '..', 'results',
                               'experiment_tables.tex')

    tables = []

    # Generate tables
    churn_table = generate_churn_table(results)
    if churn_table:
        tables.append("% Node Churn Results\n" + churn_table)
        print("Generated: Churn table")

    scalability_table = generate_scalability_table(results)
    if scalability_table:
        tables.append("% Scalability Results\n" + scalability_table)
        print("Generated: Scalability table")

    summary_table = generate_summary_table(results)
    if summary_table:
        tables.append("% Summary Table\n" + summary_table)
        print("Generated: Summary table")

    # Write all tables
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("% Auto-generated LaTeX tables for AERIS paper\n")
        f.write("% Generated from comprehensive_dynamic_experiments.json\n\n")
        f.write("\n\n".join(tables))

    print(f"\nSaved all tables to: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
