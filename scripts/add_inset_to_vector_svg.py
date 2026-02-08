#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add an Intel location mapping inset to the existing vector comparison SVG
without relying on matplotlib. This script appends a vector overlay to
results/publication_figures/LEACH_comparison_vector.svg and writes a new file:

 - results/publication_figures/LEACH_comparison_vector_inset.svg

It reads data/Intel_Lab_Data/mote_locs.txt and scales coordinates into a
small rectangle placed at the top-right of the canvas.
"""

import os
import re


def project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_svg(svg_path: str) -> str:
    with open(svg_path, 'r', encoding='utf-8') as f:
        return f.read()


def write_svg(svg_path: str, content: str):
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(content)


def parse_viewbox(svg_text: str):
    m = re.search(r'viewBox="([0-9\.\-]+)\s+([0-9\.\-]+)\s+([0-9\.\-]+)\s+([0-9\.\-]+)"', svg_text)
    if not m:
        return (0.0, 0.0, 1600.0, 800.0)  # sensible default
    return tuple(float(g) for g in m.groups())


def read_intel_positions() -> list[tuple[float, float]]:
    loc_path = os.path.join(project_root(), 'data', 'Intel_Lab_Data', 'mote_locs.txt')
    if not os.path.exists(loc_path):
        return []
    pts = []
    with open(loc_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3:
                try:
                    x = float(parts[1]); y = float(parts[2])
                    pts.append((x, y))
                except Exception:
                    pass
    return pts


def build_inset_group(vw: float, vh: float, title: str = 'Intel positions → sim area') -> str:
    # Position inset relative to canvas
    inset_x = vw * 0.80
    inset_y = vh * 0.10
    inset_w = vw * 0.18
    inset_h = vh * 0.25

    # Read and normalize Intel positions
    pts = read_intel_positions()
    if pts:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(1e-6, max_x - min_x)
        span_y = max(1e-6, max_y - min_y)
        # SVG y increases downward; invert to have origin at bottom-left of inset
        def sx(x): return inset_x + ((x - min_x) / span_x) * inset_w
        def sy(y): return inset_y + (1.0 - ((y - min_y) / span_y)) * inset_h
        circles = '\n'.join([
            f'<circle cx="{sx(x):.3f}" cy="{sy(y):.3f}" r="2.2" fill="#4E79A7" stroke="white" stroke-width="0.6" />'
            for x, y in pts
        ])
    else:
        # Synthetic scatter if file missing
        circles = ''

    # Group overlay
    g = [
        f'<g id="inset_intel_map" opacity="0.98">',
        f'  <rect x="{inset_x:.3f}" y="{inset_y:.3f}" width="{inset_w:.3f}" height="{inset_h:.3f}" fill="none" stroke="#666666" stroke-width="1.2" />',
        f'  <text x="{(inset_x + inset_w/2):.3f}" y="{(inset_y - 6):.3f}" font-size="12" text-anchor="middle" fill="#222222">{title}</text>',
        circles,
        # BS annotation at top-center of inset; indicative of y=175 outside area
        f'  <text x="{(inset_x + inset_w/2):.3f}" y="{(inset_y - 20):.3f}" font-size="11" text-anchor="middle" fill="#FF6B6B">BS (y=175, outside)</text>',
        '</g>'
    ]
    return '\n'.join(g)


def add_inset_to_svg():
    root = project_root()
    src_svg = os.path.join(root, 'results', 'publication_figures', 'LEACH_comparison_vector.svg')
    dst_svg = os.path.join(root, 'results', 'publication_figures', 'LEACH_comparison_vector_inset.svg')
    if not os.path.exists(src_svg):
        print(f'[ERROR] Missing source SVG: {src_svg}')
        return 2
    text = read_svg(src_svg)
    _, _, vw, vh = parse_viewbox(text)
    overlay = build_inset_group(vw, vh)
    # Insert overlay before closing </svg>
    patched = re.sub(r'</svg>\s*$', overlay + '\n</svg>', text, flags=re.IGNORECASE)
    write_svg(dst_svg, patched)
    print(f'[SAVED] Inset-added SVG: {dst_svg}')
    return 0


if __name__ == '__main__':
    raise SystemExit(add_inset_to_svg())