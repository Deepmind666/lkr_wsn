#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
import csv
import matplotlib.pyplot as plt

if __name__ == '__main__':
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    in_path = os.path.join(repo, 'results', 'final_baseline_compare.json')
    with open(in_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # flatten to CSV
    rows = []
    for scenario, result in data.items():
        for method, metrics in result.items():
            rows.append({
                'scenario': scenario,
                'method': method,
                'total_energy_consumed': metrics.get('total_energy_consumed'),
                'pdr_hop': metrics.get('packet_delivery_ratio'),
                'pdr_end2end': metrics.get('packet_delivery_ratio_end2end'),
                'lifetime': metrics.get('network_lifetime'),
            })

    out_dir = os.path.join(repo, 'results')
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, 'final_baseline_compare.csv')
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['scenario','method','total_energy_consumed','pdr_hop','pdr_end2end','lifetime'])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('Saved CSV', csv_path)

    # Plots per scenario
    plot_dir = os.path.join(out_dir, 'plots')
    os.makedirs(plot_dir, exist_ok=True)

    methods_order = ['AETHER_energy','AETHER_robust','LEACH','PEGASIS','HEED']
    colors = {
        'AETHER_energy': '#4CAF50',
        'AETHER_robust': '#FF9800',
        'LEACH': '#2196F3',
        'PEGASIS': '#9C27B0',
        'HEED': '#607D8B',
    }

    for scenario, result in data.items():
        methods = [m for m in methods_order if m in result]
        energy = [result[m]['total_energy_consumed'] for m in methods]
        pdr = [result[m]['packet_delivery_ratio_end2end'] for m in methods]

        # Energy bar
        plt.figure(figsize=(8,4))
        xs = range(len(methods))
        plt.bar(xs, energy, color=[colors.get(m, '#888') for m in methods])
        plt.xticks(xs, methods, rotation=20)
        plt.ylabel('Energy (J)')
        plt.title(f'Energy by Method - {scenario}')
        plt.grid(axis='y', alpha=0.3)
        outp = os.path.join(plot_dir, f'baseline_energy_{scenario}.png')
        plt.tight_layout(); plt.savefig(outp, dpi=300, bbox_inches='tight'); plt.close()
        print('Saved', outp)

        # PDR bar
        plt.figure(figsize=(8,4))
        plt.bar(xs, pdr, color=[colors.get(m, '#888') for m in methods])
        plt.xticks(xs, methods, rotation=20)
        plt.ylabel('PDR End-to-End')
        plt.ylim(0,1.05)
        plt.title(f'PDR End-to-End by Method - {scenario}')
        plt.grid(axis='y', alpha=0.3)
        outp = os.path.join(plot_dir, f'baseline_pdr_{scenario}.png')
        plt.tight_layout(); plt.savefig(outp, dpi=300, bbox_inches='tight'); plt.close()
        print('Saved', outp)

