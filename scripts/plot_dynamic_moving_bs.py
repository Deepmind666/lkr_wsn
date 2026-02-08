#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import matplotlib.pyplot as plt

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'results', 'dynamic_moving_bs.json')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'plots')
SENSORS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'Sensors_figures')
OUT_NAME_SVG = 'paper_dynamic_moving_bs.svg'
OUT_NAME_PDF = 'paper_dynamic_moving_bs.pdf'

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
    pdr = [data[p]['packet_delivery_ratio_end2end'] for p in phases]
    hop = [data[p]['packet_delivery_ratio'] for p in phases]
    energy = [data[p]['total_energy_consumed'] for p in phases]

    x = range(len(phases))
    fig, ax1 = plt.subplots(figsize=(6, 3.4))
    ax1.plot(x, pdr, marker='o', color='#0072B2', label='PDR$_{e2e}$')
    ax1.set_ylabel('End-to-end PDR', color='#0072B2')
    ax1.tick_params(axis='y', labelcolor='#0072B2')
    ax1.set_ylim(0.3, 0.6)
    ax1.set_xticks(x)
    ax1.set_xticklabels([p.replace('_', '\n') for p in phases])

    ax2 = ax1.twinx()
    ax2.plot(x, energy, marker='s', color='#D55E00', label='Energy')
    ax2.set_ylabel('Total energy (J)', color='#D55E00')
    ax2.tick_params(axis='y', labelcolor='#D55E00')

    ax1.set_title('Moving base station scenario (robust profile)')
    fig.tight_layout()

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper right')

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path_svg = os.path.join(OUT_DIR, OUT_NAME_SVG)
    out_path_pdf = os.path.join(OUT_DIR, OUT_NAME_PDF)
    fig.savefig(out_path_svg, bbox_inches='tight')
    fig.savefig(out_path_pdf, bbox_inches='tight')
    os.makedirs(SENSORS_DIR, exist_ok=True)
    fig.savefig(os.path.join(SENSORS_DIR, OUT_NAME_SVG), bbox_inches='tight')
    fig.savefig(os.path.join(SENSORS_DIR, OUT_NAME_PDF), bbox_inches='tight')
    print(f"[DONE] Saved moving BS plot to {out_path_svg} and {out_path_pdf}")


if __name__ == "__main__":
    main()
