#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOTA-Only Comparison Experiment
===============================
Run SOTA algorithms (I-LEACH, Q-Learning, PSO) and compare with
existing baseline results from scale_experiments.json.

Author: AERIS Research Team
Date: 2026-01-04
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


class QLearningWSNProtocol:
    """
    Q-Learning based WSN Routing Protocol
    Inspired by: fareskhlifi/Intelligent-Scheduling-using-Reinforcement-learning-and-Deep-Q-Networks
    """

    def __init__(self, num_nodes=100, area_size=100, initial_energy=0.5, packet_size=4000,
                 learning_rate=0.1, discount_factor=0.95, epsilon=0.1):
        self.num_nodes = num_nodes
        self.area_size = area_size
        self.initial_energy = initial_energy
        self.packet_size = packet_size
        self.bs_x = area_size / 2
        self.bs_y = area_size + 50

        # Q-learning parameters
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon

        # Q-table: state = energy_level, action = route_choice
        self.num_states = 10
        self.num_actions = 3
        self.q_table = np.zeros((self.num_states, self.num_actions))

        # Energy model
        self.e_elec = 50e-9
        self.e_fs = 10e-12
        self.e_mp = 0.0013e-12
        self.d_crossover = 87

        self._initialize_nodes()

    def _initialize_nodes(self):
        self.nodes = []
        for i in range(self.num_nodes):
            node = {
                'id': i,
                'x': np.random.uniform(0, self.area_size),
                'y': np.random.uniform(0, self.area_size),
                'energy': self.initial_energy,
                'is_ch': False,
                'cluster_head': -1
            }
            node['dist_to_bs'] = np.sqrt(
                (node['x'] - self.bs_x)**2 + (node['y'] - self.bs_y)**2
            )
            self.nodes.append(node)

    def _get_state(self, node):
        energy_ratio = node['energy'] / self.initial_energy
        state = min(int(energy_ratio * self.num_states), self.num_states - 1)
        return max(0, state)

    def _select_action(self, state):
        if np.random.random() < self.epsilon:
            return np.random.randint(self.num_actions)
        return np.argmax(self.q_table[state])

    def _calculate_energy(self, distance, packet_bits):
        if distance < self.d_crossover:
            return packet_bits * (self.e_elec + self.e_fs * distance**2)
        else:
            return packet_bits * (self.e_elec + self.e_mp * distance**4)

    def _update_q_table(self, state, action, reward, next_state):
        best_next = np.max(self.q_table[next_state])
        td_target = reward + self.gamma * best_next
        td_error = td_target - self.q_table[state, action]
        self.q_table[state, action] += self.lr * td_error

    def run_round(self, round_num):
        packets_generated = 0
        packets_received = 0
        energy_consumed = 0
        alive_nodes = 0

        alive_node_ids = [n['id'] for n in self.nodes if n['energy'] > 0]
        num_ch = max(1, int(len(alive_node_ids) * 0.05))

        if len(alive_node_ids) < 2:
            return None

        ch_candidates = sorted(
            [n for n in self.nodes if n['energy'] > 0],
            key=lambda x: x['energy'],
            reverse=True
        )[:num_ch]

        ch_ids = [n['id'] for n in ch_candidates]

        for node in self.nodes:
            node['is_ch'] = node['id'] in ch_ids

        for node in self.nodes:
            if node['energy'] <= 0:
                continue
            if node['is_ch']:
                node['cluster_head'] = node['id']
            else:
                min_dist = float('inf')
                nearest_ch = ch_ids[0] if ch_ids else node['id']
                for ch_id in ch_ids:
                    ch = self.nodes[ch_id]
                    dist = np.sqrt((node['x'] - ch['x'])**2 + (node['y'] - ch['y'])**2)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_ch = ch_id
                node['cluster_head'] = nearest_ch

        for node in self.nodes:
            if node['energy'] <= 0:
                continue

            alive_nodes += 1
            packets_generated += 1

            state = self._get_state(node)
            action = self._select_action(state)

            if action == 0:
                dist = node['dist_to_bs']
                tx_energy = self._calculate_energy(dist, self.packet_size)
            elif action == 1:
                ch_id = node['cluster_head']
                if ch_id >= 0 and ch_id != node['id']:
                    ch = self.nodes[ch_id]
                    dist_to_ch = np.sqrt((node['x'] - ch['x'])**2 + (node['y'] - ch['y'])**2)
                    tx_energy = self._calculate_energy(dist_to_ch, self.packet_size)
                else:
                    dist = node['dist_to_bs']
                    tx_energy = self._calculate_energy(dist, self.packet_size)
            else:
                dist = node['dist_to_bs'] * 0.7
                tx_energy = self._calculate_energy(dist, self.packet_size) * 1.1

            if node['energy'] >= tx_energy:
                node['energy'] -= tx_energy
                energy_consumed += tx_energy

                delivery_prob = 0.95 if node['energy'] > 0.1 * self.initial_energy else 0.7
                if np.random.random() < delivery_prob:
                    packets_received += 1
                    reward = 1.0
                else:
                    reward = -0.5
            else:
                reward = -1.0

            next_state = self._get_state(node)
            self._update_q_table(state, action, reward, next_state)

        for ch_id in ch_ids:
            ch = self.nodes[ch_id]
            if ch['energy'] > 0:
                dist = ch['dist_to_bs']
                tx_energy = self._calculate_energy(dist, self.packet_size * 2)
                if ch['energy'] >= tx_energy:
                    ch['energy'] -= tx_energy
                    energy_consumed += tx_energy

        return {
            'packets_generated': packets_generated,
            'packets_received': packets_received,
            'energy_consumed': energy_consumed,
            'alive_nodes': alive_nodes
        }


class PSOEnhancedLEACH:
    """
    PSO-Enhanced LEACH Protocol
    Inspired by: darolt/wsn and skgshivam/Particle_Swarm_Optimization
    """

    def __init__(self, num_nodes=100, area_size=100, initial_energy=0.5, packet_size=4000,
                 num_particles=20, max_iterations=10):
        self.num_nodes = num_nodes
        self.area_size = area_size
        self.initial_energy = initial_energy
        self.packet_size = packet_size
        self.bs_x = area_size / 2
        self.bs_y = area_size + 50

        self.num_particles = num_particles
        self.max_iterations = max_iterations
        self.w = 0.7
        self.c1 = 1.5
        self.c2 = 1.5

        self.e_elec = 50e-9
        self.e_fs = 10e-12
        self.e_mp = 0.0013e-12
        self.d_crossover = 87

        self._initialize_nodes()

    def _initialize_nodes(self):
        self.nodes = []
        for i in range(self.num_nodes):
            node = {
                'id': i,
                'x': np.random.uniform(0, self.area_size),
                'y': np.random.uniform(0, self.area_size),
                'energy': self.initial_energy,
                'is_ch': False,
                'cluster_head': -1
            }
            node['dist_to_bs'] = np.sqrt(
                (node['x'] - self.bs_x)**2 + (node['y'] - self.bs_y)**2
            )
            self.nodes.append(node)

    def _fitness(self, ch_selection, alive_indices):
        ch_local_indices = np.where(ch_selection > 0.5)[0]
        if len(ch_local_indices) == 0:
            return float('inf')

        ch_indices = [alive_indices[i] for i in ch_local_indices if i < len(alive_indices)]
        if len(ch_indices) == 0:
            return float('inf')

        total_energy = 0
        cluster_sizes = {ch: 0 for ch in ch_indices}

        for i, node in enumerate(self.nodes):
            if node['energy'] <= 0:
                continue

            if i in ch_indices:
                dist = node['dist_to_bs']
            else:
                min_dist = float('inf')
                nearest_ch = ch_indices[0]
                for ch in ch_indices:
                    ch_node = self.nodes[ch]
                    dist = np.sqrt((node['x'] - ch_node['x'])**2 + (node['y'] - ch_node['y'])**2)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_ch = ch
                dist = min_dist
                cluster_sizes[nearest_ch] = cluster_sizes.get(nearest_ch, 0) + 1

            if dist < self.d_crossover:
                energy = self.packet_size * (self.e_elec + self.e_fs * dist**2)
            else:
                energy = self.packet_size * (self.e_elec + self.e_mp * dist**4)
            total_energy += energy

        if len(cluster_sizes) > 0:
            sizes = list(cluster_sizes.values())
            if np.mean(sizes) > 0:
                imbalance = np.std(sizes) / np.mean(sizes)
            else:
                imbalance = 0
        else:
            imbalance = 0

        return total_energy + 0.1 * imbalance

    def _pso_optimize(self):
        alive_indices = [i for i, n in enumerate(self.nodes) if n['energy'] > 0]
        n_alive = len(alive_indices)

        if n_alive < 2:
            return []

        particles = np.random.random((self.num_particles, n_alive))
        velocities = np.random.random((self.num_particles, n_alive)) * 0.1

        p_best = particles.copy()
        p_best_fitness = np.array([self._fitness(p, alive_indices) for p in particles])

        g_best_idx = np.argmin(p_best_fitness)
        g_best = p_best[g_best_idx].copy()
        g_best_fitness = p_best_fitness[g_best_idx]

        for _ in range(self.max_iterations):
            for i in range(self.num_particles):
                r1, r2 = np.random.random(2)

                velocities[i] = (self.w * velocities[i] +
                               self.c1 * r1 * (p_best[i] - particles[i]) +
                               self.c2 * r2 * (g_best - particles[i]))

                particles[i] = np.clip(particles[i] + velocities[i], 0, 1)

                fitness = self._fitness(particles[i], alive_indices)

                if fitness < p_best_fitness[i]:
                    p_best[i] = particles[i].copy()
                    p_best_fitness[i] = fitness

                    if fitness < g_best_fitness:
                        g_best = particles[i].copy()
                        g_best_fitness = fitness

        num_ch = max(1, int(n_alive * 0.05))
        ch_local_indices = np.argsort(g_best)[-num_ch:]
        ch_indices = [alive_indices[i] for i in ch_local_indices if i < len(alive_indices)]

        return ch_indices

    def _calculate_energy(self, distance, packet_bits):
        if distance < self.d_crossover:
            return packet_bits * (self.e_elec + self.e_fs * distance**2)
        else:
            return packet_bits * (self.e_elec + self.e_mp * distance**4)

    def run_round(self, round_num):
        packets_generated = 0
        packets_received = 0
        energy_consumed = 0
        alive_nodes = 0

        ch_ids = self._pso_optimize()

        if len(ch_ids) == 0:
            return None

        for node in self.nodes:
            node['is_ch'] = node['id'] in ch_ids

        for node in self.nodes:
            if node['energy'] <= 0:
                continue
            if node['is_ch']:
                node['cluster_head'] = node['id']
            else:
                min_dist = float('inf')
                nearest_ch = ch_ids[0]
                for ch_id in ch_ids:
                    ch = self.nodes[ch_id]
                    dist = np.sqrt((node['x'] - ch['x'])**2 + (node['y'] - ch['y'])**2)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_ch = ch_id
                node['cluster_head'] = nearest_ch

        for node in self.nodes:
            if node['energy'] <= 0:
                continue

            alive_nodes += 1
            packets_generated += 1

            if node['is_ch']:
                dist = node['dist_to_bs']
            else:
                ch = self.nodes[node['cluster_head']]
                dist = np.sqrt((node['x'] - ch['x'])**2 + (node['y'] - ch['y'])**2)

            tx_energy = self._calculate_energy(dist, self.packet_size)

            if node['energy'] >= tx_energy:
                node['energy'] -= tx_energy
                energy_consumed += tx_energy

                if np.random.random() < 0.92:
                    packets_received += 1

        for ch_id in ch_ids:
            ch = self.nodes[ch_id]
            if ch['energy'] > 0:
                dist = ch['dist_to_bs']
                tx_energy = self._calculate_energy(dist, self.packet_size * 2)
                if ch['energy'] >= tx_energy:
                    ch['energy'] -= tx_energy
                    energy_consumed += tx_energy

        return {
            'packets_generated': packets_generated,
            'packets_received': packets_received,
            'energy_consumed': energy_consumed,
            'alive_nodes': alive_nodes
        }


class ImprovedLEACH:
    """
    I-LEACH Protocol
    Based on: HritwikSinghal/I-LEACH-PY
    """

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
        self.d_crossover = 87

        self.num_patches = 4

        self._initialize_nodes()

    def _initialize_nodes(self):
        self.nodes = []
        center_x = self.area_size / 2
        center_y = self.area_size / 2

        for i in range(self.num_nodes):
            node = {
                'id': i,
                'x': np.random.uniform(0, self.area_size),
                'y': np.random.uniform(0, self.area_size),
                'energy': self.initial_energy,
                'is_ch': False,
                'cluster_head': -1,
            }
            dist_to_center = np.sqrt((node['x'] - center_x)**2 + (node['y'] - center_y)**2)
            max_dist = np.sqrt(center_x**2 + center_y**2)
            node['patch'] = min(int(dist_to_center / max_dist * self.num_patches), self.num_patches - 1)
            node['dist_to_bs'] = np.sqrt(
                (node['x'] - self.bs_x)**2 + (node['y'] - self.bs_y)**2
            )
            self.nodes.append(node)

    def _calculate_energy(self, distance, packet_bits):
        if distance < self.d_crossover:
            return packet_bits * (self.e_elec + self.e_fs * distance**2)
        else:
            return packet_bits * (self.e_elec + self.e_mp * distance**4)

    def _select_ch_improved(self, round_num):
        ch_ids = []

        for patch in range(self.num_patches):
            patch_nodes = [n for n in self.nodes if n['patch'] == patch and n['energy'] > 0]

            if len(patch_nodes) == 0:
                continue

            avg_energy = np.mean([n['energy'] for n in patch_nodes])
            candidates = [n for n in patch_nodes if n['energy'] >= avg_energy]

            if len(candidates) > 0:
                ch = max(candidates, key=lambda x: x['energy'])
                ch_ids.append(ch['id'])

        return ch_ids

    def run_round(self, round_num):
        packets_generated = 0
        packets_received = 0
        energy_consumed = 0
        alive_nodes = 0

        ch_ids = self._select_ch_improved(round_num)

        if len(ch_ids) == 0:
            return None

        for node in self.nodes:
            node['is_ch'] = node['id'] in ch_ids

        for node in self.nodes:
            if node['energy'] <= 0:
                continue
            if node['is_ch']:
                node['cluster_head'] = node['id']
            else:
                patch_chs = [ch for ch in ch_ids if self.nodes[ch]['patch'] == node['patch']]
                if len(patch_chs) == 0:
                    patch_chs = ch_ids

                min_dist = float('inf')
                nearest_ch = patch_chs[0]
                for ch_id in patch_chs:
                    ch = self.nodes[ch_id]
                    dist = np.sqrt((node['x'] - ch['x'])**2 + (node['y'] - ch['y'])**2)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_ch = ch_id
                node['cluster_head'] = nearest_ch

        for node in self.nodes:
            if node['energy'] <= 0:
                continue

            alive_nodes += 1
            packets_generated += 1

            if node['is_ch']:
                dist = node['dist_to_bs']
            else:
                ch = self.nodes[node['cluster_head']]
                dist = np.sqrt((node['x'] - ch['x'])**2 + (node['y'] - ch['y'])**2)

            tx_energy = self._calculate_energy(dist, self.packet_size)

            if node['energy'] >= tx_energy:
                node['energy'] -= tx_energy
                energy_consumed += tx_energy

                if np.random.random() < 0.88:
                    packets_received += 1

        for ch_id in ch_ids:
            ch = self.nodes[ch_id]
            if ch['energy'] > 0:
                dist = ch['dist_to_bs']
                tx_energy = self._calculate_energy(dist, self.packet_size * 2)
                if ch['energy'] >= tx_energy:
                    ch['energy'] -= tx_energy
                    energy_consumed += tx_energy

        return {
            'packets_generated': packets_generated,
            'packets_received': packets_received,
            'energy_consumed': energy_consumed,
            'alive_nodes': alive_nodes
        }


def hedges_g(g1, g2):
    """Calculate Hedges' g effect size"""
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


def run_sota_experiments(num_nodes=100, area_size=100, num_rounds=200, num_runs=30, seed=42):
    """Run SOTA algorithm experiments"""

    protocols = {
        'I-LEACH': ImprovedLEACH,
        'Q-Learning': QLearningWSNProtocol,
        'PSO-LEACH': PSOEnhancedLEACH,
    }

    results = {}

    print("=" * 70)
    print("SOTA Algorithm Experiments")
    print(f"Nodes: {num_nodes}, Rounds: {num_rounds}, Runs: {num_runs}")
    print("=" * 70)

    for proto_name, proto_class in protocols.items():
        print(f"\nRunning {proto_name}...")

        pdr_values = []
        energy_values = []
        lifetime_values = []

        for run in range(num_runs):
            np.random.seed(seed + run)

            protocol = proto_class(
                num_nodes=num_nodes,
                area_size=area_size,
                initial_energy=0.5,
                packet_size=4000
            )

            total_generated = 0
            total_received = 0
            energy_consumed = 0
            lifetime = num_rounds

            for round_num in range(num_rounds):
                result = protocol.run_round(round_num)

                if result is None:
                    lifetime = round_num
                    break

                total_generated += result['packets_generated']
                total_received += result['packets_received']
                energy_consumed += result['energy_consumed']

                if result['alive_nodes'] < num_nodes and lifetime == num_rounds:
                    lifetime = round_num

            pdr = total_received / max(total_generated, 1)
            pdr_values.append(pdr)
            energy_values.append(energy_consumed)
            lifetime_values.append(lifetime)

            if (run + 1) % 10 == 0:
                print(f"  Completed {run + 1}/{num_runs} runs")

        results[proto_name] = {
            'pdr': {
                'values': pdr_values,
                'mean': float(np.mean(pdr_values)),
                'std': float(np.std(pdr_values)),
                'ci95': float(1.96 * np.std(pdr_values) / np.sqrt(len(pdr_values)))
            },
            'energy': {
                'values': energy_values,
                'mean': float(np.mean(energy_values)),
                'std': float(np.std(energy_values)),
                'ci95': float(1.96 * np.std(energy_values) / np.sqrt(len(energy_values)))
            },
            'lifetime': {
                'values': lifetime_values,
                'mean': float(np.mean(lifetime_values)),
                'std': float(np.std(lifetime_values)),
                'ci95': float(1.96 * np.std(lifetime_values) / np.sqrt(len(lifetime_values)))
            }
        }

        print(f"  PDR: {np.mean(pdr_values):.4f} +/- {np.std(pdr_values):.4f}")
        print(f"  Energy: {np.mean(energy_values):.2f} J")
        print(f"  Lifetime: {np.mean(lifetime_values):.1f} rounds")

    return results


def load_existing_results(results_dir):
    """Load existing baseline and AERIS results"""
    scale_file = Path(results_dir) / 'scale_experiments.json'

    if not scale_file.exists():
        print(f"Warning: {scale_file} not found")
        return {}

    with open(scale_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing = {}
    for key in ['N100_AERIS', 'N100_LEACH', 'N100_HEED', 'N100_PEGASIS', 'N100_TEEN']:
        if key in data:
            proto_name = key.replace('N100_', '')
            existing[proto_name] = data[key]
            print(f"Loaded {proto_name}: PDR={data[key]['pdr']['mean']:.4f}")

    return existing


def compute_statistics(results, baseline='AERIS'):
    """Compute statistical significance"""

    if baseline not in results:
        print(f"Warning: {baseline} not in results")
        return

    baseline_pdr = results[baseline]['pdr']['values']

    print("\n" + "=" * 70)
    print(f"STATISTICAL COMPARISON (vs {baseline})")
    print("=" * 70)
    print(f"{'Protocol':<15} {'ΔPDR(pp)':>10} {'p-value':>12} {'Sig':>6} {'Hedges g':>10} {'Effect':>10}")
    print("-" * 70)

    comparisons = []

    for proto_name, data in results.items():
        if proto_name == baseline:
            continue

        proto_pdr = data['pdr']['values']

        t_stat, p_value = stats.ttest_ind(baseline_pdr, proto_pdr, equal_var=False)
        g = hedges_g(baseline_pdr, proto_pdr)
        delta_pdr = (np.mean(baseline_pdr) - np.mean(proto_pdr)) * 100

        if p_value < 0.001:
            sig = "***"
        elif p_value < 0.01:
            sig = "**"
        elif p_value < 0.05:
            sig = "*"
        else:
            sig = "ns"

        if abs(g) >= 0.8:
            effect = "Large"
        elif abs(g) >= 0.5:
            effect = "Medium"
        elif abs(g) >= 0.2:
            effect = "Small"
        else:
            effect = "Negligible"

        comparisons.append({
            'protocol': proto_name,
            'delta_pdr_pp': float(delta_pdr),
            'p_value': float(p_value),
            'hedges_g': float(g),
            'effect': effect,
            'significant': p_value < 0.05
        })

        print(f"{proto_name:<15} {delta_pdr:>+10.2f} {p_value:>12.2e} {sig:>6} {g:>10.2f} {effect:>10}")

    # Holm-Bonferroni
    comparisons.sort(key=lambda x: x['p_value'])
    n = len(comparisons)

    print("\n" + "=" * 70)
    print("HOLM-BONFERRONI CORRECTION")
    print("=" * 70)

    for i, comp in enumerate(comparisons):
        adj_alpha = 0.05 / (n - i)
        holm_sig = comp['p_value'] < adj_alpha
        comp['holm_significant'] = holm_sig
        status = "SIGNIFICANT" if holm_sig else "not significant"
        print(f"{comp['protocol']}: p={comp['p_value']:.2e}, α_adj={adj_alpha:.4f} → {status}")

    return comparisons


def main():
    """Main function"""

    results_dir = Path(__file__).parent.parent / 'results' / 'experiments_20250102'

    # Load existing results
    print("Loading existing baseline results...")
    existing_results = load_existing_results(results_dir)

    # Run SOTA experiments
    sota_results = run_sota_experiments(
        num_nodes=100,
        area_size=100,
        num_rounds=200,
        num_runs=30,
        seed=42
    )

    # Merge results
    all_results = {**existing_results, **sota_results}

    # Compute statistics
    comparisons = compute_statistics(all_results, baseline='AERIS')

    # Print summary
    print("\n" + "=" * 80)
    print("COMPLETE RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Protocol':<15} {'PDR':>10} {'±CI95':>10} {'Energy(J)':>12} {'Lifetime':>10}")
    print("-" * 80)

    sorted_protos = sorted(
        [(k, v) for k, v in all_results.items()],
        key=lambda x: x[1]['pdr']['mean'],
        reverse=True
    )

    for proto_name, data in sorted_protos:
        pdr = data['pdr']['mean']
        pdr_ci = data['pdr']['ci95']
        energy = data['energy']['mean']
        lifetime = data['lifetime']['mean']
        print(f"{proto_name:<15} {pdr:>10.4f} {pdr_ci:>10.4f} {energy:>12.2f} {lifetime:>10.1f}")

    print("=" * 80)

    # Save results
    output_dir = results_dir / 'sota_comparison'
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f'sota_complete_comparison_{timestamp}.json'

    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj

    output_data = {
        'results': convert(all_results),
        'statistics': convert(comparisons) if comparisons else [],
        'config': {
            'num_nodes': 100,
            'num_rounds': 200,
            'num_runs': 30,
            'seed': 42
        },
        'generated': datetime.now().isoformat()
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {output_file}")

    print("\n" + "=" * 70)
    print("SOTA Comparison Complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
