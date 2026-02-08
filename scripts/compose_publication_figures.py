#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compose publication-ready comparison figure by placing the two analysis PNGs
side-by-side:
 - results/realistic_leach_analysis.png
 - results/corrected_leach_analysis.png

Outputs:
 - results/publication_figures/LEACH_comparison.png

This script only depends on matplotlib and works in Anaconda.
"""

import os
import sys

try:
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
except Exception as e:
    print(f"[ERROR] matplotlib not available: {e}")
    sys.exit(1)


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_dir = os.path.join(project_root, 'results')
    pub_dir = os.path.join(results_dir, 'publication_figures')
    os.makedirs(pub_dir, exist_ok=True)

    realistic_path = os.path.join(results_dir, 'realistic_leach_analysis.png')
    corrected_path = os.path.join(results_dir, 'corrected_leach_analysis.png')
    out_path = os.path.join(pub_dir, 'LEACH_comparison.png')
    out_path_pdf = os.path.join(pub_dir, 'LEACH_comparison.pdf')
    out_path_svg = os.path.join(pub_dir, 'LEACH_comparison.svg')

    if not os.path.exists(realistic_path):
        print(f"[ERROR] Missing file: {realistic_path}")
        sys.exit(2)
    if not os.path.exists(corrected_path):
        print(f"[ERROR] Missing file: {corrected_path}")
        sys.exit(3)

    img_real = mpimg.imread(realistic_path)
    img_corr = mpimg.imread(corrected_path)

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    axes[0].imshow(img_real)
    axes[0].axis('off')
    axes[0].set_title('Realistic LEACH (multi-metric analysis)', fontsize=12)

    axes[1].imshow(img_corr)
    axes[1].axis('off')
    axes[1].set_title('Corrected LEACH (authoritative alignment)', fontsize=12)

    fig.suptitle('LEACH Protocol Comparison (Publication Figure)', fontsize=14, fontweight='bold')
    plt.tight_layout()

    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.savefig(out_path_pdf, dpi=300, bbox_inches='tight')
    try:
        plt.savefig(out_path_svg, format='svg', bbox_inches='tight')
        print(f"[SAVED] Comparison figure (SVG): {out_path_svg}")
    except Exception as e:
        print(f"[WARN] Failed to save SVG: {e}")
    print(f"[SAVED] Comparison figure (PNG): {out_path}")
    print(f"[SAVED] Comparison figure (PDF): {out_path_pdf}")


if __name__ == '__main__':
    main()