#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import matplotlib.pyplot as plt

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'results', 'dynamic_corridor.json')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'plots')
SENSORS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'Sensors_figures')
OUT_NAME_SVG = 'paper_dynamic_corridor.svg'
OUT_NAME_PDF = 'paper_dynamic_corridor.pdf'

plt.rcParams.update({
    'font.size': 11,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'legend.fontsize': 10,
    'figure.dpi': 300,
    'axes.grid': True,
})


def main():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    phases = sorted(data.keys())
    energy_pdr = [data[p]['AERIS_energy']['packet_delivery_ratio_end2end'] for p in phases]
    robust_pdr = [data[p]['AERIS_robust']['packet_delivery_ratio_end2end'] for p in phases]

    x = range(len(phases))
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(x, energy_pdr, marker='o', label='AERIS (energy)')
    ax.plot(x, robust_pdr, marker='s', label='AERIS (robust)')
    ax.set_xticks(x)
    ax.set_xticklabels([p.replace('_', '\n') for p in phases])
    ax.set_ylabel('End-to-end PDR')
    ax.set_title('Dynamic Corridor Scenario (Intel-driven channel)')
    ax.set_ylim(0.3, 0.6)
    ax.legend()

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path_svg = os.path.join(OUT_DIR, OUT_NAME_SVG)
    out_path_pdf = os.path.join(OUT_DIR, OUT_NAME_PDF)
    fig.tight_layout()
    fig.savefig(out_path_svg, bbox_inches='tight')
    fig.savefig(out_path_pdf, bbox_inches='tight')

    os.makedirs(SENSORS_DIR, exist_ok=True)
    fig.savefig(os.path.join(SENSORS_DIR, OUT_NAME_SVG), bbox_inches='tight')
    fig.savefig(os.path.join(SENSORS_DIR, OUT_NAME_PDF), bbox_inches='tight')
    print(f"[DONE] Saved figure to {out_path_svg} and {out_path_pdf}")


if __name__ == "__main__":
    main()
