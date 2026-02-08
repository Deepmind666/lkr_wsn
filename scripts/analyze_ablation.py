#!/usr/bin/env python3
"""分析消融实验结果"""
import json
import numpy as np
from collections import defaultdict

with open('c:/AERIS-WSN-Protocol/results/ablation_fix_test.json') as f:
    data = json.load(f)

results = data['results']
print(f'总结果数: {len(results)}')

stats = defaultdict(lambda: {'pdr': [], 'energy': [], 'lifetime': []})

for r in results:
    if r.get('status') != 'ok':
        continue
    variant = r.get('extra_cfg', {}).get('variant', 'unknown')
    topo = r.get('topology', 'uniform')
    key = f'{variant}_{topo}'
    stats[key]['pdr'].append(r.get('pdr_end2end', 0))
    stats[key]['energy'].append(r.get('energy', 0))
    stats[key]['lifetime'].append(r.get('lifetime', 0))

print()
print('=' * 70)
print('消融实验结果汇总')
print('=' * 70)
print(f'{"变体_拓扑":<25} {"PDR(%)":<15} {"能耗(J)":<12} {"寿命":<10}')
print('-' * 70)

for key in sorted(stats.keys()):
    s = stats[key]
    if len(s['pdr']) > 0:
        pdr_mean = np.mean(s['pdr']) * 100
        pdr_std = np.std(s['pdr']) * 100
        energy_mean = np.mean(s['energy'])
        lifetime_mean = np.mean(s['lifetime'])
        print(f'{key:<25} {pdr_mean:.1f}+/-{pdr_std:.1f}      {energy_mean:.1f}        {lifetime_mean:.0f}')

# 按变体汇总
print()
print('=' * 70)
print('按变体汇总 (合并拓扑)')
print('=' * 70)
variant_stats = defaultdict(lambda: {'pdr': [], 'energy': [], 'lifetime': []})
for r in results:
    if r.get('status') != 'ok':
        continue
    variant = r.get('extra_cfg', {}).get('variant', 'unknown')
    variant_stats[variant]['pdr'].append(r.get('pdr_end2end', 0))
    variant_stats[variant]['energy'].append(r.get('energy', 0))
    variant_stats[variant]['lifetime'].append(r.get('lifetime', 0))

print(f'{"变体":<20} {"PDR(%)":<15} {"能耗(J)":<12} {"寿命":<10}')
print('-' * 60)
for key in sorted(variant_stats.keys()):
    s = variant_stats[key]
    pdr_mean = np.mean(s['pdr']) * 100
    pdr_std = np.std(s['pdr']) * 100
    energy_mean = np.mean(s['energy'])
    lifetime_mean = np.mean(s['lifetime'])
    print(f'{key:<20} {pdr_mean:.1f}+/-{pdr_std:.1f}      {energy_mean:.1f}        {lifetime_mean:.0f}')
