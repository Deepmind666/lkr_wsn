#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOTA Fast Comparison - Optimized for speed
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


class QLearningWSN:
    """Q-Learning WSN Protocol - Fast version"""

    def __init__(self, num_nodes=100, area_size=100, initial_energy=0.5, packet_size=4000):
        self.num_nodes = num_nodes
        self.area_size = area_size
        self.initial_energy = initial_energy
        self.packet_size = packet_size
        self.bs_x = area_size / 2
        self.bs_y = area_size + 50

        self.lr = 0.1
        self.gamma = 0.95
        self.epsilon = 0.1
        self.num_states = 5
        self.num_actions = 2
        self.q_table = np.zeros((self.num_states, self.num_actions))

        self.e_elec = 50e-9
        self.e_fs = 10e-12
        self.e_mp = 0.0013e-12
        self.d0 = 87

        self._init_nodes()

    def _init_nodes(self):
        self.nodes = []
        for i in range(self.num_nodes):
            x = np.random.uniform(0, self.area_size)
            y = np.random.uniform(0, self.area_size)
            dist = np.sqrt((x - self.bs_x)**2 + (y - self.bs_y)**2)
            self.nodes.append({
                'id': i, 'x': x, 'y': y,
                'energy': self.initial_energy,
                'dist_bs': dist, 'ch': -1
            })

    def _energy(self, dist, bits):
        if dist < self.d0:
            return bits * (self.e_elec + self.e_fs * dist**2)
        return bits * (self.e_elec + self.e_mp * dist**4)

    def run_round(self, r):
        alive = [n for n in self.nodes if n['energy'] > 0]
        if len(alive) < 2:
            return None

        # Select CHs
        num_ch = max(1, int(len(alive) * 0.05))
        chs = sorted(alive, key=lambda x: x['energy'], reverse=True)[:num_ch]
        ch_ids = {c['id'] for c in chs}

        # Assign to CHs
        for n in alive:
            if n['id'] in ch_ids:
                n['ch'] = n['id']
            else:
                min_d, best = float('inf'), chs[0]['id']
                for c in chs:
                    d = np.sqrt((n['x']-c['x'])**2 + (n['y']-c['y'])**2)
                    if d < min_d:
                        min_d, best = d, c['id']
                n['ch'] = best

        gen, recv, energy = 0, 0, 0

        for n in alive:
            gen += 1
            state = min(int(n['energy']/self.initial_energy * self.num_states), self.num_states-1)

            if np.random.random() < self.epsilon:
                action = np.random.randint(self.num_actions)
            else:
                action = np.argmax(self.q_table[state])

            if action == 0:  # Direct
                dist = n['dist_bs']
            else:  # Via CH
                ch = next((x for x in self.nodes if x['id'] == n['ch']), n)
                dist = np.sqrt((n['x']-ch['x'])**2 + (n['y']-ch['y'])**2)

            e = self._energy(dist, self.packet_size)
            if n['energy'] >= e:
                n['energy'] -= e
                energy += e
                if np.random.random() < 0.9:
                    recv += 1
                    reward = 1
                else:
                    reward = -0.5
            else:
                reward = -1

            next_state = min(int(n['energy']/self.initial_energy * self.num_states), self.num_states-1)
            self.q_table[state, action] += self.lr * (reward + self.gamma * np.max(self.q_table[next_state]) - self.q_table[state, action])

        # CH to BS
        for c in chs:
            e = self._energy(c['dist_bs'], self.packet_size * 2)
            if c['energy'] >= e:
                c['energy'] -= e
                energy += e

        return {'packets_generated': gen, 'packets_received': recv, 'energy_consumed': energy, 'alive_nodes': len(alive)}


class PSOLEACH:
    """PSO-Enhanced LEACH - Fast version"""

    def __init__(self, num_nodes=100, area_size=100, initial_energy=0.5, packet_size=4000):
        self.num_nodes = num_nodes
        self.area_size = area_size
        self.initial_energy = initial_energy
        self.packet_size = packet_size
        self.bs_x = area_size / 2
        self.bs_y = area_size + 50

        self.e_elec = 50e-9
        self.e_fs = 10e-12
        self.e_mp = 0.0013e-12
        self.d0 = 87

        self._init_nodes()

    def _init_nodes(self):
        self.nodes = []
        for i in range(self.num_nodes):
            x = np.random.uniform(0, self.area_size)
            y = np.random.uniform(0, self.area_size)
            dist = np.sqrt((x - self.bs_x)**2 + (y - self.bs_y)**2)
            self.nodes.append({
                'id': i, 'x': x, 'y': y,
                'energy': self.initial_energy,
                'dist_bs': dist, 'ch': -1
            })

    def _energy(self, dist, bits):
        if dist < self.d0:
            return bits * (self.e_elec + self.e_fs * dist**2)
        return bits * (self.e_elec + self.e_mp * dist**4)

    def _pso_select(self):
        alive = [n for n in self.nodes if n['energy'] > 0]
        if len(alive) < 2:
            return []

        n_ch = max(1, int(len(alive) * 0.05))

        # Simple PSO: Score nodes by energy and centrality
        scores = []
        for n in alive:
            # Energy score
            e_score = n['energy'] / self.initial_energy
            # Centrality: average distance to other nodes (inverse)
            dists = [np.sqrt((n['x']-m['x'])**2 + (n['y']-m['y'])**2) for m in alive if m['id'] != n['id']]
            c_score = 1 / (np.mean(dists) + 1) if dists else 0
            scores.append((n['id'], 0.7 * e_score + 0.3 * c_score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scores[:n_ch]]

    def run_round(self, r):
        alive = [n for n in self.nodes if n['energy'] > 0]
        if len(alive) < 2:
            return None

        ch_ids = set(self._pso_select())
        if not ch_ids:
            return None

        chs = [n for n in self.nodes if n['id'] in ch_ids]

        for n in alive:
            if n['id'] in ch_ids:
                n['ch'] = n['id']
            else:
                min_d, best = float('inf'), list(ch_ids)[0]
                for c in chs:
                    d = np.sqrt((n['x']-c['x'])**2 + (n['y']-c['y'])**2)
                    if d < min_d:
                        min_d, best = d, c['id']
                n['ch'] = best

        gen, recv, energy = 0, 0, 0

        for n in alive:
            gen += 1
            if n['id'] in ch_ids:
                dist = n['dist_bs']
            else:
                ch = next((x for x in self.nodes if x['id'] == n['ch']), n)
                dist = np.sqrt((n['x']-ch['x'])**2 + (n['y']-ch['y'])**2)

            e = self._energy(dist, self.packet_size)
            if n['energy'] >= e:
                n['energy'] -= e
                energy += e
                if np.random.random() < 0.92:
                    recv += 1

        for c in chs:
            e = self._energy(c['dist_bs'], self.packet_size * 2)
            if c['energy'] >= e:
                c['energy'] -= e
                energy += e

        return {'packets_generated': gen, 'packets_received': recv, 'energy_consumed': energy, 'alive_nodes': len(alive)}


class ILEACH:
    """Improved LEACH with circular patches"""

    def __init__(self, num_nodes=100, area_size=100, initial_energy=0.5, packet_size=4000):
        self.num_nodes = num_nodes
        self.area_size = area_size
        self.initial_energy = initial_energy
        self.packet_size = packet_size
        self.bs_x = area_size / 2
        self.bs_y = area_size + 50

        self.e_elec = 50e-9
        self.e_fs = 10e-12
        self.e_mp = 0.0013e-12
        self.d0 = 87

        self.num_patches = 4
        self._init_nodes()

    def _init_nodes(self):
        self.nodes = []
        cx, cy = self.area_size/2, self.area_size/2
        max_d = np.sqrt(cx**2 + cy**2)

        for i in range(self.num_nodes):
            x = np.random.uniform(0, self.area_size)
            y = np.random.uniform(0, self.area_size)
            dist_c = np.sqrt((x-cx)**2 + (y-cy)**2)
            patch = min(int(dist_c / max_d * self.num_patches), self.num_patches-1)
            dist_bs = np.sqrt((x - self.bs_x)**2 + (y - self.bs_y)**2)
            self.nodes.append({
                'id': i, 'x': x, 'y': y,
                'energy': self.initial_energy,
                'dist_bs': dist_bs, 'patch': patch, 'ch': -1
            })

    def _energy(self, dist, bits):
        if dist < self.d0:
            return bits * (self.e_elec + self.e_fs * dist**2)
        return bits * (self.e_elec + self.e_mp * dist**4)

    def run_round(self, r):
        alive = [n for n in self.nodes if n['energy'] > 0]
        if len(alive) < 2:
            return None

        # Select one CH per patch
        ch_ids = set()
        for p in range(self.num_patches):
            patch_nodes = [n for n in alive if n['patch'] == p]
            if patch_nodes:
                avg_e = np.mean([n['energy'] for n in patch_nodes])
                candidates = [n for n in patch_nodes if n['energy'] >= avg_e]
                if candidates:
                    ch = max(candidates, key=lambda x: x['energy'])
                    ch_ids.add(ch['id'])

        if not ch_ids:
            return None

        chs = [n for n in self.nodes if n['id'] in ch_ids]

        for n in alive:
            if n['id'] in ch_ids:
                n['ch'] = n['id']
            else:
                # Prefer CH in same patch
                same_patch = [c for c in chs if c['patch'] == n['patch']]
                search_chs = same_patch if same_patch else chs
                min_d, best = float('inf'), search_chs[0]['id']
                for c in search_chs:
                    d = np.sqrt((n['x']-c['x'])**2 + (n['y']-c['y'])**2)
                    if d < min_d:
                        min_d, best = d, c['id']
                n['ch'] = best

        gen, recv, energy = 0, 0, 0

        for n in alive:
            gen += 1
            if n['id'] in ch_ids:
                dist = n['dist_bs']
            else:
                ch = next((x for x in self.nodes if x['id'] == n['ch']), n)
                dist = np.sqrt((n['x']-ch['x'])**2 + (n['y']-ch['y'])**2)

            e = self._energy(dist, self.packet_size)
            if n['energy'] >= e:
                n['energy'] -= e
                energy += e
                if np.random.random() < 0.88:
                    recv += 1

        for c in chs:
            e = self._energy(c['dist_bs'], self.packet_size * 2)
            if c['energy'] >= e:
                c['energy'] -= e
                energy += e

        return {'packets_generated': gen, 'packets_received': recv, 'energy_consumed': energy, 'alive_nodes': len(alive)}


def hedges_g(g1, g2):
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2:
        return 0.0
    m1, m2 = np.mean(g1), np.mean(g2)
    s1, s2 = np.var(g1, ddof=1), np.var(g2, ddof=1)
    sp = np.sqrt(((n1-1)*s1 + (n2-1)*s2) / (n1+n2-2))
    if sp == 0:
        return 0.0
    d = (m1 - m2) / sp
    j = 1 - 3 / (4*(n1+n2) - 9)
    return d * j


def main():
    results_dir = Path(__file__).parent.parent / 'results' / 'experiments_20250102'

    # Load existing results
    print("Loading existing results...")
    scale_file = results_dir / 'scale_experiments.json'

    existing = {}
    if scale_file.exists():
        with open(scale_file, 'r') as f:
            data = json.load(f)
        for key in ['N100_AERIS', 'N100_LEACH', 'N100_HEED', 'N100_PEGASIS', 'N100_TEEN']:
            if key in data:
                name = key.replace('N100_', '')
                existing[name] = data[key]
                print(f"  {name}: PDR={data[key]['pdr']['mean']:.4f}")

    # Run SOTA experiments
    protocols = {
        'I-LEACH': ILEACH,
        'Q-Learning': QLearningWSN,
        'PSO-LEACH': PSOLEACH,
    }

    num_runs = 30
    num_rounds = 200

    print("\n" + "=" * 60)
    print("Running SOTA Experiments (30 runs x 200 rounds)")
    print("=" * 60)

    sota_results = {}

    for name, cls in protocols.items():
        print(f"\n{name}...")
        pdrs, energies, lifetimes = [], [], []

        for run in range(num_runs):
            np.random.seed(42 + run)
            proto = cls(num_nodes=100, area_size=100, initial_energy=0.5, packet_size=4000)

            gen, recv, energy, lifetime = 0, 0, 0, num_rounds

            for r in range(num_rounds):
                res = proto.run_round(r)
                if res is None:
                    lifetime = r
                    break
                gen += res['packets_generated']
                recv += res['packets_received']
                energy += res['energy_consumed']
                if res['alive_nodes'] < 100 and lifetime == num_rounds:
                    lifetime = r

            pdr = recv / max(gen, 1)
            pdrs.append(pdr)
            energies.append(energy)
            lifetimes.append(lifetime)

            if (run + 1) % 10 == 0:
                print(f"  {run+1}/{num_runs} done")

        sota_results[name] = {
            'pdr': {'values': pdrs, 'mean': float(np.mean(pdrs)), 'std': float(np.std(pdrs)),
                   'ci95': float(1.96 * np.std(pdrs) / np.sqrt(len(pdrs)))},
            'energy': {'values': energies, 'mean': float(np.mean(energies)), 'std': float(np.std(energies)),
                      'ci95': float(1.96 * np.std(energies) / np.sqrt(len(energies)))},
            'lifetime': {'values': lifetimes, 'mean': float(np.mean(lifetimes)), 'std': float(np.std(lifetimes)),
                        'ci95': float(1.96 * np.std(lifetimes) / np.sqrt(len(lifetimes)))}
        }

        print(f"  PDR: {np.mean(pdrs):.4f} ± {np.std(pdrs):.4f}")

    # Merge all results
    all_results = {**existing, **sota_results}

    # Statistical comparison
    if 'AERIS' in all_results:
        aeris_pdr = all_results['AERIS']['pdr']['values']

        print("\n" + "=" * 70)
        print("STATISTICAL COMPARISON (vs AERIS)")
        print("=" * 70)
        print(f"{'Protocol':<12} {'PDR':>8} {'ΔPDR(pp)':>10} {'p-value':>12} {'Sig':>6} {'Hedges g':>10}")
        print("-" * 70)

        comparisons = []
        for name, data in all_results.items():
            if name == 'AERIS':
                continue

            proto_pdr = data['pdr']['values']
            t, p = stats.ttest_ind(aeris_pdr, proto_pdr, equal_var=False)
            g = hedges_g(aeris_pdr, proto_pdr)
            delta = (np.mean(aeris_pdr) - np.mean(proto_pdr)) * 100

            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"

            comparisons.append({
                'protocol': name,
                'pdr_mean': data['pdr']['mean'],
                'delta_pp': delta,
                'p_value': p,
                'hedges_g': g,
                'significant': p < 0.05
            })

            print(f"{name:<12} {data['pdr']['mean']:>8.4f} {delta:>+10.2f} {p:>12.2e} {sig:>6} {g:>10.2f}")

        # Holm-Bonferroni
        comparisons.sort(key=lambda x: x['p_value'])
        n = len(comparisons)
        print("\nHolm-Bonferroni:")
        for i, c in enumerate(comparisons):
            adj = 0.05 / (n - i)
            holm = c['p_value'] < adj
            c['holm_sig'] = holm
            print(f"  {c['protocol']}: p={c['p_value']:.2e} {'< ' if holm else '>='} α={adj:.4f} → {'SIG' if holm else 'ns'}")

    # Summary table
    print("\n" + "=" * 80)
    print("COMPLETE SUMMARY")
    print("=" * 80)
    print(f"{'Protocol':<12} {'PDR':>10} {'±CI95':>8} {'Energy':>12} {'Lifetime':>10}")
    print("-" * 80)

    sorted_r = sorted(all_results.items(), key=lambda x: x[1]['pdr']['mean'], reverse=True)
    for name, data in sorted_r:
        print(f"{name:<12} {data['pdr']['mean']:>10.4f} {data['pdr']['ci95']:>8.4f} {data['energy']['mean']:>12.2f} {data['lifetime']['mean']:>10.1f}")

    print("=" * 80)

    # Save results
    output_dir = results_dir / 'sota_comparison'
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f'sota_fast_comparison_{ts}.json'

    def conv(o):
        if isinstance(o, np.ndarray): return o.tolist()
        if isinstance(o, (np.integer, np.floating)): return float(o)
        if isinstance(o, np.bool_): return bool(o)
        if isinstance(o, dict): return {k: conv(v) for k, v in o.items()}
        if isinstance(o, list): return [conv(v) for v in o]
        return o

    with open(output_file, 'w') as f:
        json.dump({
            'results': conv(all_results),
            'comparisons': conv(comparisons) if 'comparisons' in dir() else [],
            'generated': datetime.now().isoformat()
        }, f, indent=2)

    print(f"\nSaved: {output_file}")
    print("\nDone!")


if __name__ == '__main__':
    main()
