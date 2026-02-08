#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import matplotlib.pyplot as plt

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'results', 'monte_carlo_uniform50.json')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'plots')
SENSORS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'Sensors_figures')
OUT_NAME = 'paper_monte_carlo_uniform.svg'

plt.rcParams.update({
    'font.size': 11,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'legend.fontsize': 10,
    'figure.dpi': 300,
})


def main():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    energy = [run['pdr_end2end'] for run in data['runs']['energy']]
    robust = [run['pdr_end2end'] for run in data['runs']['robust']]

    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.boxplot([energy, robust], labels=['energy', 'robust'])
    ax.set_ylabel('End-to-end PDR')
    ax.set_title('Monte Carlo (100 seeds, 50×100 topology)')
    fig.tight_layout()

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, OUT_NAME)
    fig.savefig(out_path, bbox_inches='tight')
    os.makedirs(SENSORS_DIR, exist_ok=True)
    fig.savefig(os.path.join(SENSORS_DIR, OUT_NAME), bbox_inches='tight')
    print(f"[DONE] Saved Monte Carlo plot to {out_path}")


if __name__ == "__main__":
    main()
