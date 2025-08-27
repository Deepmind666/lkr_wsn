#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, io

# Append reproduce instructions to existing README without overwriting original material
APPEND = """

## Reproducibility (Core Artifacts)

- One-click reproduce
```
py -3 scripts/run_reproduce_all.py
```
Generates:
- results/safety_tradeoff_grid_50x200.{json,csv}
- results/plots/safety_tradeoff.png
- results/significance_compare_50x200.json
- results/significance_compare_multi_topo_50x200.json

- Baseline comparison
```
py -3 scripts/run_final_baseline_compare.py
py -3 scripts/summarize_final_baselines.py
```
Outputs CSV and plots under results/ and results/plots/.

- Paper figures
```
py -3 scripts/plot_paper_figures.py
```
Outputs PDF+PNG under results/plots/.

- Profiles
AETHER supports quick profiles:
- energy (default): minimal energy, crisis fallback disabled
- robust: crisis fallback enabled (r=1.0, δ=1dBm)

Example:
```
from integrated_enhanced_eehfr import IntegratedEnhancedEEHFRProtocol
proto = IntegratedEnhancedEEHFRProtocol(cfg, enable_gateway=True, profile='robust')
```

- Metric semantics
We strictly use packet_delivery_ratio_end2end for end-to-end PDR (aggregated by domain delivery semantics). Hop-level PDR is reported separately as packet_delivery_ratio.
"""

if __name__ == '__main__':
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    path = os.path.join(repo, 'README.md')
    with io.open(path, 'a', encoding='utf-8') as f:
        f.write(APPEND)
    print('README updated with reproduce instructions.')

