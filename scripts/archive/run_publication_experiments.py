#!/usr/bin/env python3
"""
AERIS Publication Experiments - Self-contained Version

Complete experiment suite for publication-quality 12-panel figure.
All protocols implemented inline for reproducibility.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import json
import math
from datetime import datetime
from pathlib import Path
from scipy import stats

from realistic_channel_model import LogNormalShadowingModel, IEEE802154LinkQuality, EnvironmentType


class Channel:
    def __init__(self, env=EnvironmentType.INDOOR_OFFICE):
        self.shadow = LogNormalShadowingModel(env)
        self.link = IEEE802154LinkQuality()
        self.power = 0.0

    def pdr(self, d):
        rx = self.shadow.calculate_received_power(self.power, d)
        rssi = self.link.calculate_rssi(rx)
        return self.link.calculate_pdr(rssi)


class Node:
    def __init__(self, nid, x, y, e=2.0):
        self.id, self.x, self.y = nid, x, y
        self.e0, self.e, self.alive = e, e, True

    def dist(self, o):
        return math.hypot(self.x - (o.x if hasattr(o, 'x') else o[0]),
                          self.y - (o.y if hasattr(o, 'y') else o[1]))

    def use(self, amt):
        self.e -= amt
        if self.e <= 0:
            self.e, self.alive = 0, False


class LEACH:
    def __init__(self, nodes, bs, ch, p=0.1):
        self.nodes, self.bs, self.ch, self.p = nodes, bs, ch, p
        self.Etx, self.Erx, self.pkt = 208.8e-9, 225.6e-9, 4000
        self.sent, self.recv, self.energy = 0, 0, 0.0

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False
        chs = [n for n in alive if np.random.random() < self.p] or [max(alive, key=lambda n: n.e)]
        clusters = {c.id: [] for c in chs}
        for n in alive:
            if n not in chs:
                clusters[min(chs, key=lambda c: n.dist(c)).id].append(n)
        for c in chs:
            for m in clusters[c.id]:
                if not m.alive:
                    continue
                d, tx, rx = m.dist(c), self.Etx * self.pkt, self.Erx * self.pkt
                m.use(tx); c.use(rx); self.energy += tx + rx; self.sent += 1
                if np.random.random() < self.ch.pdr(d):
                    self.recv += 1
        for c in chs:
            if not c.alive:
                continue
            tx = self.Etx * self.pkt
            c.use(tx); self.energy += tx; self.sent += 1
            if np.random.random() < self.ch.pdr(c.dist(self.bs)):
                self.recv += 1
        return True

    def result(self):
        return {'pdr': self.recv / max(1, self.sent), 'energy': self.energy}


class AERIS:
    def __init__(self, nodes, bs, ch, p=0.1, retry=2, arq=True, coop=True, smart=True):
        self.nodes, self.bs, self.ch, self.p = nodes, bs, ch, p
        self.retry, self.arq, self.coop, self.smart = retry, arq, coop, smart
        self.Etx, self.Erx, self.pkt = 208.8e-9, 225.6e-9, 4000
        self.sent, self.recv, self.energy, self.retries, self.coops = 0, 0, 0.0, 0, 0

    def round(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return False
        chs = []
        for n in alive:
            prob = self.p * (1.2 if self.smart and n.dist(self.bs) < 60 else 1.0)
            if np.random.random() < prob:
                chs.append(n)
        if not chs:
            chs = [max(alive, key=lambda n: n.e)]
        clusters = {c.id: [] for c in chs}
        for n in alive:
            if n not in chs:
                clusters[min(chs, key=lambda c: n.dist(c)).id].append(n)
        for c in chs:
            for m in clusters[c.id]:
                if not m.alive:
                    continue
                d, tx, rx = m.dist(c), self.Etx * self.pkt, self.Erx * self.pkt
                m.use(tx); c.use(rx); self.energy += tx + rx; self.sent += 1
                if np.random.random() < self.ch.pdr(d):
                    self.recv += 1
        for c in chs:
            if not c.alive:
                continue
            d, pdr, done = c.dist(self.bs), self.ch.pdr(c.dist(self.bs)), False
            self.sent += 1
            for att in range(1 + (self.retry if self.arq else 0)):
                tx = self.Etx * self.pkt
                c.use(tx); self.energy += tx
                if np.random.random() < pdr:
                    done = True; break
                if att > 0:
                    self.retries += 1
            if not done and self.coop and d > 80:
                others = [o for o in chs if o.id != c.id and o.alive]
                if others:
                    h = min(others, key=lambda o: o.dist(self.bs))
                    tx, rx = self.Etx * self.pkt, self.Erx * self.pkt
                    c.use(tx); h.use(rx); self.energy += tx + rx
                    if np.random.random() < self.ch.pdr(c.dist(h)):
                        tx = self.Etx * self.pkt
                        h.use(tx); self.energy += tx
                        if np.random.random() < self.ch.pdr(h.dist(self.bs)):
                            done, self.coops = True, self.coops + 1
            if done:
                self.recv += 1
        return True

    def result(self):
        return {'pdr': self.recv / max(1, self.sent), 'energy': self.energy,
                'retries': self.retries, 'coops': self.coops}


def net(n, sz, seed):
    np.random.seed(seed)
    return [Node(i, np.random.uniform(0, sz), np.random.uniform(0, sz)) for i in range(n)], (sz/2, sz+20)


def run(cls, nodes, bs, ch, rds=200, **kw):
    test = [Node(n.id, n.x, n.y, n.e0) for n in nodes]
    p = cls(test, bs, ch, **kw)
    for _ in range(rds):
        if not p.round():
            break
    return p.result()


def main():
    print("=" * 70)
    print("AERIS PUBLICATION EXPERIMENTS")
    print("=" * 70)

    ch = Channel()
    R = {}
    N = int(os.environ.get("PUB_RUNS", "30"))

    # 1. Basic comparison
    print("\n[1/10] Basic Comparison...")
    R['basic'] = {'LEACH': [], 'AERIS': []}
    for r in range(N):
        nodes, bs = net(54, 100, 1000+r)
        R['basic']['LEACH'].append(run(LEACH, nodes, bs, ch))
        R['basic']['AERIS'].append(run(AERIS, nodes, bs, ch))

    # 2. Scalability
    print("[2/10] Scalability...")
    sizes = [30, 54, 80, 100, 150]
    R['scale'] = {s: {'L': [], 'A': []} for s in sizes}
    for s in sizes:
        for r in range(N):
            nodes, bs = net(s, 100, 2000+r)
            R['scale'][s]['L'].append(run(LEACH, nodes, bs, ch)['pdr'])
            R['scale'][s]['A'].append(run(AERIS, nodes, bs, ch)['pdr'])

    # 3. Area variation
    print("[3/10] Area Variation...")
    areas = [50, 75, 100, 125, 150]
    R['area'] = {a: {'L': [], 'A': []} for a in areas}
    for a in areas:
        for r in range(N):
            nodes, bs = net(54, a, 3000+r)
            R['area'][a]['L'].append(run(LEACH, nodes, bs, ch)['pdr'])
            R['area'][a]['A'].append(run(AERIS, nodes, bs, ch)['pdr'])

    # 4. Ablation
    print("[4/10] Ablation Study...")
    R['ablation'] = {'Full': [], 'NoARQ': [], 'NoCoop': [], 'NoSmart': [], 'Base': []}
    for r in range(N):
        nodes, bs = net(54, 100, 4000+r)
        R['ablation']['Full'].append(run(AERIS, nodes, bs, ch)['pdr'])
        R['ablation']['NoARQ'].append(run(AERIS, nodes, bs, ch, arq=False)['pdr'])
        R['ablation']['NoCoop'].append(run(AERIS, nodes, bs, ch, coop=False)['pdr'])
        R['ablation']['NoSmart'].append(run(AERIS, nodes, bs, ch, smart=False)['pdr'])
        R['ablation']['Base'].append(run(LEACH, nodes, bs, ch)['pdr'])

    # 5. CH probability
    print("[5/10] CH Probability...")
    probs = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
    R['prob'] = {p: {'L': [], 'A': []} for p in probs}
    for p in probs:
        for r in range(N):
            nodes, bs = net(54, 100, 5000+r)
            R['prob'][p]['L'].append(run(LEACH, nodes, bs, ch, p=p)['pdr'])
            R['prob'][p]['A'].append(run(AERIS, nodes, bs, ch, p=p)['pdr'])

    # 6. Retry sensitivity
    print("[6/10] Retry Sensitivity...")
    retries = [0, 1, 2, 3, 4]
    R['retry'] = {mr: {'pdr': [], 'e': []} for mr in retries}
    for mr in retries:
        for r in range(N):
            nodes, bs = net(54, 100, 6000+r)
            res = run(AERIS, nodes, bs, ch, retry=mr)
            R['retry'][mr]['pdr'].append(res['pdr'])
            R['retry'][mr]['e'].append(res['energy'])

    # 7. Environment
    print("[7/10] Environment Types...")
    envs = {'Indoor': EnvironmentType.INDOOR_OFFICE,
            'Suburban': EnvironmentType.OUTDOOR_SUBURBAN,
            'Open': EnvironmentType.OUTDOOR_OPEN}
    R['env'] = {e: {'L': [], 'A': []} for e in envs}
    for name, env in envs.items():
        ch_e = Channel(env)
        for r in range(N):
            nodes, bs = net(54, 100, 7000+r)
            R['env'][name]['L'].append(run(LEACH, nodes, bs, ch_e)['pdr'])
            R['env'][name]['A'].append(run(AERIS, nodes, bs, ch_e)['pdr'])

    # 8. PDR-Energy tradeoff
    print("[8/10] PDR-Energy Tradeoff...")
    R['tradeoff'] = {'L': {'pdr': [], 'e': []}, 'A': {'pdr': [], 'e': []}}
    for r in range(N):
        nodes, bs = net(54, 100, 8000+r)
        rl = run(LEACH, nodes, bs, ch)
        ra = run(AERIS, nodes, bs, ch)
        R['tradeoff']['L']['pdr'].append(rl['pdr'])
        R['tradeoff']['L']['e'].append(rl['energy'])
        R['tradeoff']['A']['pdr'].append(ra['pdr'])
        R['tradeoff']['A']['e'].append(ra['energy'])

    # 9. Round evolution
    print("[9/10] Round Evolution...")
    nodes, bs = net(54, 100, 9000)
    ln = [Node(n.id, n.x, n.y, n.e0) for n in nodes]
    an = [Node(n.id, n.x, n.y, n.e0) for n in nodes]
    lp, ap = LEACH(ln, bs, ch), AERIS(an, bs, ch)
    R['evol'] = {'rd': [], 'L': [], 'A': []}
    for rd in range(200):
        if rd % 10 == 0:
            R['evol']['rd'].append(rd)
            R['evol']['L'].append(lp.recv / max(1, lp.sent) if lp.sent else 0)
            R['evol']['A'].append(ap.recv / max(1, ap.sent) if ap.sent else 0)
        lp.round(); ap.round()

    # 10. Statistics
    print("[10/10] Statistical Tests...")
    lpdrs = [x['pdr'] for x in R['basic']['LEACH']]
    apdrs = [x['pdr'] for x in R['basic']['AERIS']]
    t, p = stats.ttest_ind(apdrs, lpdrs)
    d = (np.mean(apdrs) - np.mean(lpdrs)) / np.sqrt((np.std(apdrs)**2 + np.std(lpdrs)**2) / 2)
    R['stats'] = {'t': float(t), 'p': float(p), 'd': float(d)}

    # Summary
    R['summary'] = {
        'LEACH': {'pdr': float(np.mean(lpdrs)), 'ci': float(1.96*np.std(lpdrs)/np.sqrt(N)),
                  'energy': float(np.mean([x['energy'] for x in R['basic']['LEACH']]))},
        'AERIS': {'pdr': float(np.mean(apdrs)), 'ci': float(1.96*np.std(apdrs)/np.sqrt(N)),
                  'energy': float(np.mean([x['energy'] for x in R['basic']['AERIS']]))}
    }
    R['summary']['improve'] = {
        'pdr_abs': float((np.mean(apdrs) - np.mean(lpdrs)) * 100),
        'pdr_rel': float((np.mean(apdrs) / np.mean(lpdrs) - 1) * 100),
        'e_over': float((R['summary']['AERIS']['energy'] / R['summary']['LEACH']['energy'] - 1) * 100)
    }

    # Save
    out = Path(__file__).parent.parent / 'results' / 'publication_experiments.json'
    with open(out, 'w') as f:
        json.dump({'time': datetime.now().isoformat(), 'n': N, 'data': R}, f, indent=2, default=float)

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"LEACH: {R['summary']['LEACH']['pdr']*100:.2f}% +/- {R['summary']['LEACH']['ci']*100:.2f}%")
    print(f"AERIS: {R['summary']['AERIS']['pdr']*100:.2f}% +/- {R['summary']['AERIS']['ci']*100:.2f}%")
    print(f"Improvement: +{R['summary']['improve']['pdr_abs']:.2f}% PDR, +{R['summary']['improve']['e_over']:.1f}% energy")
    print(f"p-value: {R['stats']['p']:.2e}, Cohen's d: {R['stats']['d']:.3f}")
    print(f"\nSaved: {out}")

    return R


if __name__ == '__main__':
    main()
