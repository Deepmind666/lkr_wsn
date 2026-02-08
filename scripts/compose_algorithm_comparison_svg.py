#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compose a pure-SVG multi-algorithm comparison figure from results/compare_50x200.json
to highlight our algorithm (AERIS/AETHER) vs classic baselines.

Outputs:
  - results/publication_figures/algorithm_comparison.svg (original)
  - results/publication_figures/algorithm_comparison_fair.svg (schedule-anchored delivery)

Figure variants:
  - Original: Left = End-to-End PDR (0..1); Right = Total Energy (J)
  - Fair:     Left = Schedule-Anchored Delivery Ratio (BS delivered / 50×200); Right = Total Energy (J)
"""

import os
import json
from typing import Dict, Any, List


def project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_compare_results() -> Dict[str, Any]:
    path = os.path.join(project_root(), 'results', 'compare_50x200.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def safe_pdr(entry: Dict[str, Any]) -> float:
    # Prefer end-to-end PDR if available, else fallback to aggregate PDR
    if 'packet_delivery_ratio_end2end' in entry:
        return float(entry['packet_delivery_ratio_end2end'])
    if 'packet_delivery_ratio' in entry:
        return float(entry['packet_delivery_ratio'])
    return float(entry.get('pdr', 0.0))


def safe_energy(entry: Dict[str, Any]) -> float:
    return float(entry.get('total_energy_consumed', 0.0))


def expected_schedule_delivery(entry: Dict[str, Any], expected_total: int = 50 * 200) -> float:
    """Compute BS-delivered packets ratio against a fixed schedule of 50 nodes × 200 rounds.
    This penalizes methods that transmit fewer-than-expected packets (e.g., TEEN threshold gating),
    making cross-method comparison fair for periodic sensing tasks.

    Priority order to obtain delivered counts:
      1) Sum of round_statistics['bs_delivered_round'] if present
      2) Top-level 'packets_received' if present
      3) additional_metrics['total_packets_received'] if present
      4) Estimate via packet_delivery_ratio × expected_total (fallback)
    """
    delivered_total = None
    # 1) Sum per-round BS delivered
    rs = entry.get('round_statistics')
    if isinstance(rs, list) and rs and isinstance(rs[0], dict) and ('bs_delivered_round' in rs[0]):
        try:
            delivered_total = sum(int(r.get('bs_delivered_round', 0)) for r in rs)
        except Exception:
            delivered_total = None
    # 2) Top-level packets_received
    if delivered_total is None and ('packets_received' in entry):
        try:
            delivered_total = int(entry['packets_received'])
        except Exception:
            delivered_total = None
    # 3) additional_metrics.total_packets_received
    am = entry.get('additional_metrics') or {}
    if delivered_total is None and ('total_packets_received' in am):
        try:
            delivered_total = int(am['total_packets_received'])
        except Exception:
            delivered_total = None
    # 4) Fallback estimate via aggregate PDR × expected_total
    if delivered_total is None:
        pdr = safe_pdr(entry)
        delivered_total = int(round(pdr * expected_total))

    expected = max(1, int(expected_total))
    return float(delivered_total) / float(expected)


def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def bar_group_svg(x0: float, y0: float, width: float, height: float,
                  labels: List[str], values: List[float], colors: List[str],
                  vmin: float, vmax: float, title: str, ylabel: str,
                  value_fmt: str) -> str:
    # Padding inside panel
    pad_l, pad_r, pad_t, pad_b = 40.0, 20.0, 30.0, 50.0
    chart_x = x0 + pad_l
    chart_y = y0 + pad_t
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b

    # Axis lines
    lines = [
        f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" fill="none" stroke="#DDDDDD" stroke-width="1"/>',
        f'<text x="{x0 + width/2}" y="{y0 + 20}" font-size="16" text-anchor="middle" fill="#222">{title}</text>',
        f'<text x="{x0 + 8}" y="{y0 + 26}" font-size="12" text-anchor="start" fill="#666">{ylabel}</text>',
        f'<line x1="{chart_x}" y1="{chart_y+chart_h}" x2="{chart_x+chart_w}" y2="{chart_y+chart_h}" stroke="#888" stroke-width="1"/>',
        f'<line x1="{chart_x}" y1="{chart_y}" x2="{chart_x}" y2="{chart_y+chart_h}" stroke="#888" stroke-width="1"/>'
    ]

    # Ticks (Y axis)
    ticks = []
    for i in range(0, 6):
        frac = i / 5.0
        val = vmin + frac * (vmax - vmin)
        y = chart_y + (1.0 - frac) * chart_h
        ticks.append(f'<line x1="{chart_x-5}" y1="{y}" x2="{chart_x}" y2="{y}" stroke="#888" stroke-width="1"/>')
        ticks.append(f'<text x="{chart_x-8}" y="{y+4}" font-size="11" text-anchor="end" fill="#666">{value_fmt.format(val)}</text>')

    # Bars
    n = max(1, len(values))
    bw = chart_w / (n * 1.4)
    gap = bw * 0.4
    x = chart_x + gap
    bars = []
    labels_svg = []
    for i, (lab, val, color) in enumerate(zip(labels, values, colors)):
        clamped = max(vmin, min(vmax, val))
        frac = 0.0 if vmax == vmin else (clamped - vmin) / (vmax - vmin)
        bh = frac * chart_h
        by = chart_y + (chart_h - bh)
        bars.append(f'<rect x="{x}" y="{by}" width="{bw}" height="{bh}" fill="{color}" rx="2" ry="2"/>')
        # Value label
        labels_svg.append(f'<text x="{x + bw/2}" y="{by - 6}" font-size="11" text-anchor="middle" fill="#333">{value_fmt.format(val)}</text>')
        # X label (protocol)
        labels_svg.append(f'<text x="{x + bw/2}" y="{chart_y + chart_h + 16}" font-size="12" text-anchor="middle" fill="#222">{lab}</text>')
        x += bw + gap

    return '\n'.join(lines + ticks + bars + labels_svg)


def compose():
    data = load_compare_results()
    # Protocol display order: highlight our algorithm first
    order = ['AETHER', 'LEACH', 'HEED', 'PEGASIS', 'TEEN']
    labels = []
    pdr_vals = []
    energy_vals = []
    sched_vals = []

    for key in order:
        if key not in data:
            continue
        entry = data[key]
        # Human-friendly label for our algorithm
        lab = 'AERIS' if key == 'AETHER' else key
        labels.append(lab)
        pdr_vals.append(safe_pdr(entry))
        energy_vals.append(safe_energy(entry))
        sched_vals.append(expected_schedule_delivery(entry))

    # Colors: emphasize AERIS, keep baselines distinct
    colors = []
    palette = {
        'AERIS': '#FF8C00',  # orange highlight
        'LEACH': '#4E79A7',
        'HEED': '#59A14F',
        'PEGASIS': '#E15759',
        'TEEN': '#9C755F',
    }
    for lab in labels:
        colors.append(palette.get(lab, '#777777'))

    # Panel layout
    vw, vh = 1200.0, 600.0
    pdr_panel = (40.0, 80.0, vw * 0.48, vh * 0.75)
    energy_panel = (vw * 0.52, 80.0, vw * 0.46, vh * 0.75)

    # Scales
    pdr_min, pdr_max = 0.0, 1.0
    # Energy: auto-scale to 10% headroom
    en_min, en_max = 0.0, (max(energy_vals) * 1.10) if energy_vals else 10.0

    # Build SVG
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(vw)}" height="{int(vh)}" viewBox="0 0 {int(vw)} {int(vh)}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#FFFFFF"/>',
        # Title
        '<text x="600" y="36" font-size="20" text-anchor="middle" fill="#111">Algorithm Comparison (AERIS vs Baselines)</text>',
        # Panels
        bar_group_svg(*pdr_panel, labels=labels, values=pdr_vals, colors=colors,
                      vmin=pdr_min, vmax=pdr_max, title='End-to-End PDR', ylabel='PDR (0-1)', value_fmt='{:.2f}'),
        bar_group_svg(*energy_panel, labels=labels, values=energy_vals, colors=colors,
                      vmin=en_min, vmax=en_max, title='Total Energy', ylabel='Energy (J)', value_fmt='{:.2f}')
    ]

    # Legend note
    svg.append('<text x="600" y="570" font-size="12" text-anchor="middle" fill="#555">Intel geometry used when available; unified energy model; 200 rounds</text>')
    svg.append('</svg>')

    out_path = os.path.join(project_root(), 'results', 'publication_figures', 'algorithm_comparison.svg')
    ensure_dir(out_path)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg))
    print('Saved', out_path)

    # Compose fair (schedule-anchored) variant
    svg_fair = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(vw)}" height="{int(vh)}" viewBox="0 0 {int(vw)} {int(vh)}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#FFFFFF"/>',
        '<text x="600" y="36" font-size="20" text-anchor="middle" fill="#111">Fair Comparison (Schedule-Anchored Delivery vs Energy)</text>',
        bar_group_svg(*pdr_panel, labels=labels, values=sched_vals, colors=colors,
                      vmin=0.0, vmax=1.0, title='Schedule-Anchored Delivery', ylabel='Delivered / (50×200)', value_fmt='{:.3f}'),
        bar_group_svg(*energy_panel, labels=labels, values=energy_vals, colors=colors,
                      vmin=en_min, vmax=en_max, title='Total Energy', ylabel='Energy (J)', value_fmt='{:.2f}')
    ]
    svg_fair.append('<text x="600" y="570" font-size="12" text-anchor="middle" fill="#555">Delivery normalized to expected periodic sensing (50 nodes × 200 rounds); unified energy model</text>')
    svg_fair.append('</svg>')

    out_fair = os.path.join(project_root(), 'results', 'publication_figures', 'algorithm_comparison_fair.svg')
    with open(out_fair, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg_fair))
    print('Saved', out_fair)


if __name__ == '__main__':
    compose()