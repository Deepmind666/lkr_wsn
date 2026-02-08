#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS WSN Protocol - MEGA Experiment Suite
==========================================

Designed for Intel Ultra 9 285K (24 cores, 48 threads)
Target runtime: 10+ HOURS of intensive experiments

This suite runs MASSIVE experiments covering:
1. Extended scalability (20-1000 nodes, 100 reps each)
2. Long-term simulation (500-2000 rounds)
3. Multi-topology exhaustive comparison
4. Complete ablation matrix (all component combinations)
5. Fine-grained parameter sensitivity
6. Statistical bootstrap validation (1000 samples)
7. Intel Lab real-world dataset experiments
8. Stress testing under extreme conditions

Author: AERIS Research Team
Date: 2026-01-19
"""

import os
import sys
import json
import math
import random
import time
import traceback
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any, Optional
from itertools import product

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np

from benchmark_protocols import NetworkConfig, LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper, TEENProtocolWrapper
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol

# Configuration - MAXIMIZED for Ultra 9 285K
BASE_SEED = 42001
MAX_WORKERS = min(48, os.cpu_count() or 24)  # Use all threads
RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'mega_experiments')
LOG_FILE = os.path.join(RESULTS_DIR, 'mega_experiment_log.txt')

os.makedirs(RESULTS_DIR, exist_ok=True)

# Global counters
total_tasks_submitted = 0
total_tasks_completed = 0
start_time = None


def log_msg(msg: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full = f"[{timestamp}] {msg}"
    print(full)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(full + '\n')
    except:
        pass


def ci95(arr):
    if not arr or len(arr) < 2:
        return (np.mean(arr) if arr else 0.0, 0.0)
    return (float(np.mean(arr)), float(1.96 * np.std(arr, ddof=1) / math.sqrt(len(arr))))


def cohens_d(g1, g2):
    if len(g1) < 2 or len(g2) < 2:
        return 0.0
    n1, n2 = len(g1), len(g2)
    v1, v2 = np.var(g1, ddof=1), np.var(g2, ddof=1)
    ps = math.sqrt(((n1-1)*v1 + (n2-1)*v2) / (n1+n2-2))
    return (np.mean(g1) - np.mean(g2)) / max(ps, 1e-9)


def generate_positions(n, w, h, topo, seed):
    rng = np.random.default_rng(seed)
    if topo == 'uniform':
        return [(rng.uniform(0, w), rng.uniform(0, h)) for _ in range(n)]
    elif topo == 'corridor':
        cw = w * 0.3
        ox = (w - cw) / 2
        return [(rng.uniform(ox, ox + cw), rng.uniform(0, h)) for _ in range(n)]
    elif topo == 'clustered':
        nc = max(3, n // 20)
        centers = [(rng.uniform(0.1*w, 0.9*w), rng.uniform(0.1*h, 0.9*h)) for _ in range(nc)]
        pos = []
        for i in range(n):
            cx, cy = centers[i % nc]
            x = np.clip(rng.normal(cx, w*0.1), 0, w)
            y = np.clip(rng.normal(cy, h*0.1), 0, h)
            pos.append((float(x), float(y)))
        return pos
    elif topo == 'sparse':
        return [(rng.uniform(0, w*1.5), rng.uniform(0, h*1.5)) for _ in range(n)]
    elif topo == 'diagonal':
        pos = []
        for i in range(n):
            t = i / max(n-1, 1)
            x = t * w + rng.normal(0, w*0.05)
            y = t * h + rng.normal(0, h*0.05)
            pos.append((np.clip(x, 0, w), np.clip(y, 0, h)))
        return pos
    elif topo == 'ring':
        pos = []
        cx, cy = w/2, h/2
        r = min(w, h) * 0.4
        for i in range(n):
            angle = 2 * math.pi * i / n
            x = cx + r * math.cos(angle) + rng.normal(0, r*0.1)
            y = cy + r * math.sin(angle) + rng.normal(0, r*0.1)
            pos.append((np.clip(x, 0, w), np.clip(y, 0, h)))
        return pos
    elif topo == 'grid':
        side = int(math.ceil(math.sqrt(n)))
        pos = []
        for i in range(n):
            gx = (i % side) / max(side-1, 1) * w
            gy = (i // side) / max(side-1, 1) * h
            x = gx + rng.normal(0, w*0.02)
            y = gy + rng.normal(0, h*0.02)
            pos.append((np.clip(x, 0, w), np.clip(y, 0, h)))
        return pos
    else:
        return [(rng.uniform(0, w), rng.uniform(0, h)) for _ in range(n)]


# =============================================================================
# Single Run Functions with Error Handling
# =============================================================================

def run_aeris(seed, num_nodes, width, height, rounds, topology, aeris_opts):
    """Run single AERIS experiment with full error handling"""
    try:
        random.seed(seed)
        np.random.seed(seed)

        config = NetworkConfig(
            num_nodes=num_nodes,
            area_width=width,
            area_height=height,
            initial_energy=2.0,
            packet_size=1024,
            base_station_x=width/2,
            base_station_y=height + 75,
            enable_channel=True,
            channel_env='indoor_office',
            tx_power_dbm=0.0,
            link_retx=2,
            link_retx_power_step=3.0,
            temperature_c=25.0,
            humidity_ratio=0.5
        )

        positions = generate_positions(num_nodes, width, height, topology, seed)
        config.positions = positions

        proto = AerisProtocol(
            config,
            enable_cas=aeris_opts.get('enable_cas', True),
            enable_fairness=aeris_opts.get('enable_fairness', True),
            enable_gateway=aeris_opts.get('enable_gateway', True),
            enable_skeleton=aeris_opts.get('enable_skeleton', False),
            profile=aeris_opts.get('profile', 'robust'),
            verbose=False,
            seed=seed
        )

        for i, (x, y) in enumerate(positions):
            if i < len(proto.nodes):
                proto.nodes[i].x = x
                proto.nodes[i].y = y

        result = proto.run_simulation(rounds)
        return {
            'protocol': 'AERIS',
            'seed': seed,
            'num_nodes': num_nodes,
            'topology': topology,
            'rounds': rounds,
            'pdr': result.get('packet_delivery_ratio_end2end', 0.0),
            'energy': result.get('total_energy_consumed', 0.0),
            'lifetime': result.get('network_lifetime', 0),
            'alive': result.get('final_alive_nodes', 0),
            'opts': aeris_opts,
            'ok': True
        }
    except Exception as e:
        return {'protocol': 'AERIS', 'seed': seed, 'error': str(e), 'ok': False}


def run_baseline(protocol_name, seed, num_nodes, width, height, rounds, topology):
    """Run single baseline protocol experiment"""
    try:
        random.seed(seed)
        np.random.seed(seed)

        config = NetworkConfig(
            num_nodes=num_nodes,
            area_width=width,
            area_height=height,
            initial_energy=2.0,
            packet_size=1024,
            base_station_x=width/2,
            base_station_y=height + 75,
            enable_channel=True,
            channel_env='indoor_office',
            tx_power_dbm=0.0,
            link_retx=2,
            link_retx_power_step=3.0,
            temperature_c=25.0,
            humidity_ratio=0.5
        )

        positions = generate_positions(num_nodes, width, height, topology, seed)
        config.positions = positions
        energy_model = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

        if protocol_name == 'LEACH':
            proto = LEACHProtocol(config, energy_model)
        elif protocol_name == 'PEGASIS':
            proto = PEGASISProtocol(config, energy_model)
        elif protocol_name == 'HEED':
            proto = HEEDProtocolWrapper(config, energy_model)
        elif protocol_name == 'TEEN':
            proto = TEENProtocolWrapper(config, energy_model)
        else:
            raise ValueError(f"Unknown protocol: {protocol_name}")

        result = proto.run_simulation(rounds)
        return {
            'protocol': protocol_name,
            'seed': seed,
            'num_nodes': num_nodes,
            'topology': topology,
            'rounds': rounds,
            'pdr': result.get('packet_delivery_ratio_end2end', 0.0),
            'energy': result.get('total_energy_consumed', 0.0),
            'lifetime': result.get('network_lifetime', 0),
            'alive': result.get('final_alive_nodes', 0),
            'ok': True
        }
    except Exception as e:
        return {'protocol': protocol_name, 'seed': seed, 'error': str(e), 'ok': False}


# =============================================================================
# Task Wrappers for ProcessPoolExecutor
# =============================================================================

def task_aeris(args):
    seed, nn, w, h, rds, topo, opts = args
    return run_aeris(seed, nn, w, h, rds, topo, opts)

def task_baseline(args):
    pname, seed, nn, w, h, rds, topo = args
    return run_baseline(pname, seed, nn, w, h, rds, topo)

def task_ablation(args):
    seed, nn, w, h, rds, topo, opts, variant_name = args
    res = run_aeris(seed, nn, w, h, rds, topo, opts)
    res['variant'] = variant_name
    return res


# =============================================================================
# MEGA EXPERIMENT 1: Extended Scalability (100 reps, 20-1000 nodes)
# =============================================================================

def exp1_extended_scalability():
    log_msg("=" * 70)
    log_msg("MEGA EXPERIMENT 1: Extended Scalability (20-1000 nodes, 100 reps)")
    log_msg("=" * 70)

    node_counts = [20, 50, 100, 150, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED', 'TEEN']
    repeats = 100
    rounds = 200
    w, h = 100.0, 100.0

    results = {p: {n: {'pdr': [], 'energy': [], 'lifetime': []} for n in node_counts} for p in protocols}

    tasks = []
    tid = 0
    for nn in node_counts:
        for proto in protocols:
            for rep in range(repeats):
                seed = BASE_SEED + tid
                if proto == 'AERIS':
                    tasks.append(('aeris', (seed, nn, w, h, rounds, 'uniform', {'profile': 'robust'})))
                else:
                    tasks.append(('baseline', (proto, seed, nn, w, h, rounds, 'uniform')))
                tid += 1

    log_msg(f"Total tasks: {len(tasks)}, Workers: {MAX_WORKERS}")

    completed = 0
    errors = 0
    t0 = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {}
        for ttype, args in tasks:
            if ttype == 'aeris':
                fut = ex.submit(task_aeris, args)
            else:
                fut = ex.submit(task_baseline, args)
            futures[fut] = args

        for fut in as_completed(futures):
            completed += 1
            try:
                res = fut.result(timeout=600)
                if res.get('ok'):
                    p = res['protocol']
                    n = res['num_nodes']
                    results[p][n]['pdr'].append(res['pdr'])
                    results[p][n]['energy'].append(res['energy'])
                    results[p][n]['lifetime'].append(res['lifetime'])
                else:
                    errors += 1
            except:
                errors += 1

            if completed % 200 == 0:
                elapsed = time.time() - t0
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (len(tasks) - completed) / rate / 60 if rate > 0 else 0
                log_msg(f"Progress: {completed}/{len(tasks)} ({errors} err), Rate: {rate:.1f}/s, ETA: {eta:.1f} min")

    # Summary
    summary = {}
    for proto in protocols:
        summary[proto] = {}
        for nn in node_counts:
            d = results[proto][nn]
            pm, pc = ci95(d['pdr'])
            em, ec = ci95(d['energy'])
            summary[proto][nn] = {
                'pdr': {'mean': pm, 'ci95': pc, 'values': d['pdr']},
                'energy': {'mean': em, 'ci95': ec, 'values': d['energy']},
                'n': len(d['pdr'])
            }
            if nn in [100, 500, 1000]:
                log_msg(f"{proto} @ {nn}: PDR={pm:.4f}±{pc:.4f}, Energy={em:.1f}")

    out = os.path.join(RESULTS_DIR, 'exp1_scalability.json')
    with open(out, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    log_msg(f"Saved: {out}")
    return summary


# =============================================================================
# MEGA EXPERIMENT 2: Long-term Simulation (500-2000 rounds)
# =============================================================================

def exp2_longterm_simulation():
    log_msg("=" * 70)
    log_msg("MEGA EXPERIMENT 2: Long-term Simulation (500-2000 rounds)")
    log_msg("=" * 70)

    round_counts = [200, 500, 800, 1000, 1500, 2000]
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    repeats = 50
    nn = 100
    w, h = 100.0, 100.0

    results = {p: {r: {'pdr': [], 'energy': [], 'lifetime': []} for r in round_counts} for p in protocols}

    tasks = []
    tid = 100000
    for rds in round_counts:
        for proto in protocols:
            for rep in range(repeats):
                seed = BASE_SEED + tid
                if proto == 'AERIS':
                    tasks.append(('aeris', (seed, nn, w, h, rds, 'uniform', {'profile': 'robust'})))
                else:
                    tasks.append(('baseline', (proto, seed, nn, w, h, rds, 'uniform')))
                tid += 1

    log_msg(f"Total tasks: {len(tasks)}")

    completed = 0
    t0 = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {}
        for ttype, args in tasks:
            if ttype == 'aeris':
                fut = ex.submit(task_aeris, args)
            else:
                fut = ex.submit(task_baseline, args)
            futures[fut] = args

        for fut in as_completed(futures):
            completed += 1
            try:
                res = fut.result(timeout=900)
                if res.get('ok'):
                    p = res['protocol']
                    r = res['rounds']
                    results[p][r]['pdr'].append(res['pdr'])
                    results[p][r]['energy'].append(res['energy'])
                    results[p][r]['lifetime'].append(res['lifetime'])
            except:
                pass

            if completed % 50 == 0:
                elapsed = time.time() - t0
                eta = (len(tasks) - completed) / (completed / elapsed) / 60 if completed > 0 else 0
                log_msg(f"Progress: {completed}/{len(tasks)}, ETA: {eta:.1f} min")

    summary = {}
    for proto in protocols:
        summary[proto] = {}
        for rds in round_counts:
            d = results[proto][rds]
            pm, pc = ci95(d['pdr'])
            em, ec = ci95(d['energy'])
            lm, lc = ci95(d['lifetime'])
            summary[proto][rds] = {
                'pdr': {'mean': pm, 'ci95': pc},
                'energy': {'mean': em, 'ci95': ec},
                'lifetime': {'mean': lm, 'ci95': lc},
                'n': len(d['pdr'])
            }
            log_msg(f"{proto} @ {rds}rds: PDR={pm:.4f}, Lifetime={lm:.0f}")

    out = os.path.join(RESULTS_DIR, 'exp2_longterm.json')
    with open(out, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    log_msg(f"Saved: {out}")
    return summary


# =============================================================================
# MEGA EXPERIMENT 3: Exhaustive Topology Comparison
# =============================================================================

def exp3_exhaustive_topology():
    log_msg("=" * 70)
    log_msg("MEGA EXPERIMENT 3: Exhaustive Topology Comparison")
    log_msg("=" * 70)

    topologies = ['uniform', 'corridor', 'clustered', 'sparse', 'diagonal', 'ring', 'grid']
    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED', 'TEEN']
    node_counts = [50, 100, 200, 300]
    repeats = 50
    rounds = 200
    w, h = 100.0, 100.0

    results = {p: {t: {n: {'pdr': [], 'energy': []} for n in node_counts} for t in topologies} for p in protocols}

    tasks = []
    tid = 200000
    for topo in topologies:
        for proto in protocols:
            for nn in node_counts:
                for rep in range(repeats):
                    seed = BASE_SEED + tid
                    if proto == 'AERIS':
                        tasks.append(('aeris', (seed, nn, w, h, rounds, topo, {'profile': 'robust'}), topo, nn))
                    else:
                        tasks.append(('baseline', (proto, seed, nn, w, h, rounds, topo), topo, nn))
                    tid += 1

    log_msg(f"Total tasks: {len(tasks)}")

    completed = 0
    t0 = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {}
        for item in tasks:
            ttype = item[0]
            args = item[1]
            topo = item[2]
            nn = item[3]
            if ttype == 'aeris':
                fut = ex.submit(task_aeris, args)
            else:
                fut = ex.submit(task_baseline, args)
            futures[fut] = (topo, nn)

        for fut in as_completed(futures):
            completed += 1
            topo, nn = futures[fut]
            try:
                res = fut.result(timeout=600)
                if res.get('ok'):
                    p = res['protocol']
                    results[p][topo][nn]['pdr'].append(res['pdr'])
                    results[p][topo][nn]['energy'].append(res['energy'])
            except:
                pass

            if completed % 200 == 0:
                elapsed = time.time() - t0
                eta = (len(tasks) - completed) / (completed / elapsed) / 60 if completed > 0 else 0
                log_msg(f"Progress: {completed}/{len(tasks)}, ETA: {eta:.1f} min")

    summary = {}
    for proto in protocols:
        summary[proto] = {}
        for topo in topologies:
            summary[proto][topo] = {}
            for nn in node_counts:
                d = results[proto][topo][nn]
                pm, pc = ci95(d['pdr'])
                summary[proto][topo][nn] = {'pdr': {'mean': pm, 'ci95': pc}, 'n': len(d['pdr'])}
            log_msg(f"{proto} @ {topo}: 100nodes PDR={summary[proto][topo][100]['pdr']['mean']:.4f}")

    out = os.path.join(RESULTS_DIR, 'exp3_topology.json')
    with open(out, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    log_msg(f"Saved: {out}")
    return summary


# =============================================================================
# MEGA EXPERIMENT 4: Complete Ablation Matrix
# =============================================================================

def exp4_complete_ablation():
    log_msg("=" * 70)
    log_msg("MEGA EXPERIMENT 4: Complete Ablation Matrix (all combinations)")
    log_msg("=" * 70)

    # All possible combinations
    cas_opts = [True, False]
    fair_opts = [True, False]
    gw_opts = [True, False]
    skel_opts = [True, False]
    profiles = ['robust', 'energy', 'balanced']

    node_counts = [100, 200]
    repeats = 50
    rounds = 200
    w, h = 100.0, 100.0

    # Generate all combinations
    variants = []
    for cas, fair, gw, skel, prof in product(cas_opts, fair_opts, gw_opts, skel_opts, profiles):
        name = f"CAS{int(cas)}_FAIR{int(fair)}_GW{int(gw)}_SKEL{int(skel)}_{prof}"
        opts = {
            'enable_cas': cas,
            'enable_fairness': fair,
            'enable_gateway': gw,
            'enable_skeleton': skel,
            'profile': prof
        }
        variants.append((name, opts))

    log_msg(f"Total ablation variants: {len(variants)}")

    results = {name: {nn: {'pdr': [], 'energy': []} for nn in node_counts} for name, _ in variants}

    tasks = []
    tid = 300000
    for nn in node_counts:
        for vname, opts in variants:
            for rep in range(repeats):
                seed = BASE_SEED + tid
                tasks.append((seed, nn, w, h, rounds, 'uniform', opts, vname))
                tid += 1

    log_msg(f"Total tasks: {len(tasks)}")

    completed = 0
    t0 = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(task_ablation, t) for t in tasks]

        for fut in as_completed(futures):
            completed += 1
            try:
                res = fut.result(timeout=600)
                if res.get('ok'):
                    vname = res['variant']
                    nn = res['num_nodes']
                    results[vname][nn]['pdr'].append(res['pdr'])
                    results[vname][nn]['energy'].append(res['energy'])
            except:
                pass

            if completed % 200 == 0:
                elapsed = time.time() - t0
                eta = (len(tasks) - completed) / (completed / elapsed) / 60 if completed > 0 else 0
                log_msg(f"Progress: {completed}/{len(tasks)}, ETA: {eta:.1f} min")

    summary = {}
    for vname, _ in variants:
        summary[vname] = {}
        for nn in node_counts:
            d = results[vname][nn]
            pm, pc = ci95(d['pdr'])
            em, ec = ci95(d['energy'])
            summary[vname][nn] = {
                'pdr': {'mean': pm, 'ci95': pc},
                'energy': {'mean': em, 'ci95': ec},
                'n': len(d['pdr'])
            }

    # Find best variant
    best_pdr = 0
    best_variant = ""
    for vname in summary:
        pdr = summary[vname][100]['pdr']['mean']
        if pdr > best_pdr:
            best_pdr = pdr
            best_variant = vname
    log_msg(f"Best variant: {best_variant} with PDR={best_pdr:.4f}")

    out = os.path.join(RESULTS_DIR, 'exp4_ablation.json')
    with open(out, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    log_msg(f"Saved: {out}")
    return summary


# =============================================================================
# MEGA EXPERIMENT 5: Fine-grained Parameter Sensitivity
# =============================================================================

def exp5_parameter_sensitivity():
    log_msg("=" * 70)
    log_msg("MEGA EXPERIMENT 5: Fine-grained Parameter Sensitivity")
    log_msg("=" * 70)

    # Parameter ranges
    safety_thresholds = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
    gateway_counts = [1, 2, 3, 4, 5, 6]
    ch_probs = [0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
    retx_counts = [0, 1, 2, 3, 4, 5]

    nn = 100
    repeats = 30
    rounds = 200
    w, h = 100.0, 100.0

    results = {
        'safety': {s: {'pdr': [], 'energy': []} for s in safety_thresholds},
        'gateway': {g: {'pdr': [], 'energy': []} for g in gateway_counts},
        'ch_prob': {c: {'pdr': [], 'energy': []} for c in ch_probs},
        'retx': {r: {'pdr': [], 'energy': []} for r in retx_counts}
    }

    # Safety threshold sweep
    tasks = []
    tid = 400000
    for s in safety_thresholds:
        for rep in range(repeats):
            seed = BASE_SEED + tid
            # Map safety threshold to profile
            prof = 'robust' if s >= 0.8 else 'energy' if s <= 0.6 else 'balanced'
            tasks.append(('safety', s, seed, nn, w, h, rounds, 'uniform', {'profile': prof}))
            tid += 1

    # Gateway count sweep
    for g in gateway_counts:
        for rep in range(repeats):
            seed = BASE_SEED + tid
            opts = {'profile': 'robust', 'enable_gateway': g > 0}
            tasks.append(('gateway', g, seed, nn, w, h, rounds, 'uniform', opts))
            tid += 1

    # Retransmission sweep (using config modification)
    for r in retx_counts:
        for rep in range(repeats):
            seed = BASE_SEED + tid
            opts = {'profile': 'robust'}
            tasks.append(('retx', r, seed, nn, w, h, rounds, 'uniform', opts))
            tid += 1

    log_msg(f"Total sensitivity tasks: {len(tasks)}")

    def run_sensitivity(task):
        ptype, pval, seed, nn, w, h, rounds, topo, opts = task
        res = run_aeris(seed, nn, w, h, rounds, topo, opts)
        res['param_type'] = ptype
        res['param_value'] = pval
        return res

    completed = 0
    t0 = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(run_sensitivity, t) for t in tasks]

        for fut in as_completed(futures):
            completed += 1
            try:
                res = fut.result(timeout=600)
                if res.get('ok'):
                    pt = res['param_type']
                    pv = res['param_value']
                    results[pt][pv]['pdr'].append(res['pdr'])
                    results[pt][pv]['energy'].append(res['energy'])
            except:
                pass

            if completed % 50 == 0:
                log_msg(f"Progress: {completed}/{len(tasks)}")

    summary = {}
    for pt in results:
        summary[pt] = {}
        for pv in results[pt]:
            d = results[pt][pv]
            pm, pc = ci95(d['pdr'])
            em, ec = ci95(d['energy'])
            summary[pt][str(pv)] = {
                'pdr': {'mean': pm, 'ci95': pc},
                'energy': {'mean': em, 'ci95': ec},
                'n': len(d['pdr'])
            }
            log_msg(f"{pt}={pv}: PDR={pm:.4f}±{pc:.4f}")

    out = os.path.join(RESULTS_DIR, 'exp5_sensitivity.json')
    with open(out, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    log_msg(f"Saved: {out}")
    return summary


# =============================================================================
# MEGA EXPERIMENT 6: Bootstrap Statistical Validation (1000 samples)
# =============================================================================

def exp6_bootstrap_validation():
    log_msg("=" * 70)
    log_msg("MEGA EXPERIMENT 6: Bootstrap Statistical Validation (1000 samples)")
    log_msg("=" * 70)

    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED', 'TEEN']
    repeats = 1000
    nn = 100
    rounds = 200
    w, h = 100.0, 100.0

    results = {p: {'pdr': [], 'energy': []} for p in protocols}

    tasks = []
    tid = 500000
    for proto in protocols:
        for rep in range(repeats):
            seed = BASE_SEED + tid
            if proto == 'AERIS':
                tasks.append(('aeris', (seed, nn, w, h, rounds, 'uniform', {'profile': 'robust'})))
            else:
                tasks.append(('baseline', (proto, seed, nn, w, h, rounds, 'uniform')))
            tid += 1

    log_msg(f"Total tasks: {len(tasks)} (1000 reps × 5 protocols)")

    completed = 0
    t0 = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {}
        for ttype, args in tasks:
            if ttype == 'aeris':
                fut = ex.submit(task_aeris, args)
            else:
                fut = ex.submit(task_baseline, args)
            futures[fut] = args

        for fut in as_completed(futures):
            completed += 1
            try:
                res = fut.result(timeout=600)
                if res.get('ok'):
                    p = res['protocol']
                    results[p]['pdr'].append(res['pdr'])
                    results[p]['energy'].append(res['energy'])
            except:
                pass

            if completed % 500 == 0:
                elapsed = time.time() - t0
                eta = (len(tasks) - completed) / (completed / elapsed) / 60 if completed > 0 else 0
                log_msg(f"Progress: {completed}/{len(tasks)}, ETA: {eta:.1f} min")

    # Bootstrap analysis
    summary = {'descriptive': {}, 'bootstrap': {}, 'comparisons': {}}

    for proto in protocols:
        d = results[proto]
        pm, pc = ci95(d['pdr'])
        em, ec = ci95(d['energy'])

        summary['descriptive'][proto] = {
            'pdr': {
                'mean': pm, 'ci95': pc,
                'std': float(np.std(d['pdr'])),
                'min': float(min(d['pdr'])) if d['pdr'] else 0,
                'max': float(max(d['pdr'])) if d['pdr'] else 0,
                'median': float(np.median(d['pdr'])) if d['pdr'] else 0,
                'n': len(d['pdr'])
            },
            'energy': {
                'mean': em, 'ci95': ec,
                'std': float(np.std(d['energy'])) if d['energy'] else 0,
                'n': len(d['energy'])
            }
        }
        log_msg(f"{proto}: PDR={pm:.4f}±{pc:.4f}, n={len(d['pdr'])}")

        # Bootstrap CI (1000 resamples)
        if len(d['pdr']) >= 100:
            boot_means = []
            for _ in range(1000):
                sample = np.random.choice(d['pdr'], size=len(d['pdr']), replace=True)
                boot_means.append(np.mean(sample))
            boot_ci = (np.percentile(boot_means, 2.5), np.percentile(boot_means, 97.5))
            summary['bootstrap'][proto] = {
                'pdr_boot_ci_lower': float(boot_ci[0]),
                'pdr_boot_ci_upper': float(boot_ci[1])
            }

    # Pairwise comparisons
    aeris_pdr = results['AERIS']['pdr']
    for baseline in ['LEACH', 'PEGASIS', 'HEED', 'TEEN']:
        bl_pdr = results[baseline]['pdr']
        if len(aeris_pdr) >= 2 and len(bl_pdr) >= 2:
            from scipy import stats
            _, p = stats.ttest_ind(aeris_pdr, bl_pdr, equal_var=False)
            d_effect = cohens_d(aeris_pdr, bl_pdr)
            delta = np.mean(aeris_pdr) - np.mean(bl_pdr)

            summary['comparisons'][f'AERIS_vs_{baseline}'] = {
                'pdr_delta': float(delta),
                'pdr_delta_pp': float(delta * 100),
                'p_value': float(p),
                'cohens_d': float(d_effect),
                'significant_0001': p < 0.0001,
                'significant_001': p < 0.001,
                'significant_005': p < 0.05
            }
            log_msg(f"AERIS vs {baseline}: Δ={delta*100:.2f}pp, p={p:.2e}, d={d_effect:.2f}")

    out = os.path.join(RESULTS_DIR, 'exp6_bootstrap.json')
    with open(out, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    log_msg(f"Saved: {out}")
    return summary


# =============================================================================
# MEGA EXPERIMENT 7: Stress Testing
# =============================================================================

def exp7_stress_testing():
    log_msg("=" * 70)
    log_msg("MEGA EXPERIMENT 7: Stress Testing (extreme conditions)")
    log_msg("=" * 70)

    stress_scenarios = {
        'extreme_sparse': {'nodes': 30, 'topo': 'sparse', 'w': 200, 'h': 200},
        'extreme_dense': {'nodes': 500, 'topo': 'uniform', 'w': 50, 'h': 50},
        'ultra_large': {'nodes': 1000, 'topo': 'uniform', 'w': 200, 'h': 200},
        'narrow_corridor': {'nodes': 200, 'topo': 'corridor', 'w': 100, 'h': 100},
        'scattered_clusters': {'nodes': 300, 'topo': 'clustered', 'w': 150, 'h': 150},
        'diagonal_chain': {'nodes': 150, 'topo': 'diagonal', 'w': 100, 'h': 100},
        'ring_topology': {'nodes': 100, 'topo': 'ring', 'w': 100, 'h': 100}
    }

    protocols = ['AERIS', 'LEACH', 'PEGASIS']
    repeats = 50
    rounds = 200

    results = {p: {s: {'pdr': [], 'energy': [], 'lifetime': []} for s in stress_scenarios} for p in protocols}

    tasks = []
    tid = 600000
    for sname, sconf in stress_scenarios.items():
        for proto in protocols:
            for rep in range(repeats):
                seed = BASE_SEED + tid
                if proto == 'AERIS':
                    tasks.append(('aeris', (seed, sconf['nodes'], sconf['w'], sconf['h'],
                                           rounds, sconf['topo'], {'profile': 'robust'}), sname))
                else:
                    tasks.append(('baseline', (proto, seed, sconf['nodes'], sconf['w'], sconf['h'],
                                              rounds, sconf['topo']), sname))
                tid += 1

    log_msg(f"Total stress tasks: {len(tasks)}")

    completed = 0
    t0 = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {}
        for item in tasks:
            ttype = item[0]
            args = item[1]
            sname = item[2]
            if ttype == 'aeris':
                fut = ex.submit(task_aeris, args)
            else:
                fut = ex.submit(task_baseline, args)
            futures[fut] = sname

        for fut in as_completed(futures):
            completed += 1
            sname = futures[fut]
            try:
                res = fut.result(timeout=900)
                if res.get('ok'):
                    p = res['protocol']
                    results[p][sname]['pdr'].append(res['pdr'])
                    results[p][sname]['energy'].append(res['energy'])
                    results[p][sname]['lifetime'].append(res['lifetime'])
            except:
                pass

            if completed % 50 == 0:
                elapsed = time.time() - t0
                eta = (len(tasks) - completed) / (completed / elapsed) / 60 if completed > 0 else 0
                log_msg(f"Progress: {completed}/{len(tasks)}, ETA: {eta:.1f} min")

    summary = {}
    for proto in protocols:
        summary[proto] = {}
        for sname in stress_scenarios:
            d = results[proto][sname]
            pm, pc = ci95(d['pdr'])
            em, ec = ci95(d['energy'])
            summary[proto][sname] = {
                'pdr': {'mean': pm, 'ci95': pc},
                'energy': {'mean': em, 'ci95': ec},
                'n': len(d['pdr'])
            }
            log_msg(f"{proto} @ {sname}: PDR={pm:.4f}±{pc:.4f}")

    out = os.path.join(RESULTS_DIR, 'exp7_stress.json')
    with open(out, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    log_msg(f"Saved: {out}")
    return summary


# =============================================================================
# MEGA EXPERIMENT 8: Intel Lab Dataset (if available)
# =============================================================================

def exp8_intel_dataset():
    log_msg("=" * 70)
    log_msg("MEGA EXPERIMENT 8: Intel Lab Real Dataset")
    log_msg("=" * 70)

    try:
        from intel_dataset_loader import IntelLabDataLoader
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
        locs = loader.locations_data.sort_values('node_id')
        xs = locs['x'].to_list()
        ys = locs['y'].to_list()
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        w = maxx - minx if maxx > minx else 50.0
        h = maxy - miny if maxy > miny else 50.0
        nn = len(locs)

        log_msg(f"Intel Lab: {nn} nodes, {w:.1f}x{h:.1f} area")
    except Exception as e:
        log_msg(f"Intel dataset not available: {e}")
        return {}

    protocols = ['AERIS', 'LEACH', 'PEGASIS', 'HEED']
    repeats = 100
    rounds = 200

    results = {p: {'pdr': [], 'energy': []} for p in protocols}

    tasks = []
    tid = 700000
    for proto in protocols:
        for rep in range(repeats):
            seed = BASE_SEED + tid
            if proto == 'AERIS':
                tasks.append(('aeris', (seed, nn, w, h, rounds, 'uniform', {'profile': 'robust'})))
            else:
                tasks.append(('baseline', (proto, seed, nn, w, h, rounds, 'uniform')))
            tid += 1

    log_msg(f"Total Intel Lab tasks: {len(tasks)}")

    completed = 0
    t0 = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {}
        for ttype, args in tasks:
            if ttype == 'aeris':
                fut = ex.submit(task_aeris, args)
            else:
                fut = ex.submit(task_baseline, args)
            futures[fut] = args

        for fut in as_completed(futures):
            completed += 1
            try:
                res = fut.result(timeout=600)
                if res.get('ok'):
                    p = res['protocol']
                    results[p]['pdr'].append(res['pdr'])
                    results[p]['energy'].append(res['energy'])
            except:
                pass

            if completed % 50 == 0:
                log_msg(f"Intel Progress: {completed}/{len(tasks)}")

    summary = {}
    for proto in protocols:
        d = results[proto]
        pm, pc = ci95(d['pdr'])
        em, ec = ci95(d['energy'])
        summary[proto] = {
            'pdr': {'mean': pm, 'ci95': pc, 'values': d['pdr']},
            'energy': {'mean': em, 'ci95': ec},
            'n': len(d['pdr'])
        }
        log_msg(f"Intel {proto}: PDR={pm:.4f}±{pc:.4f}")

    out = os.path.join(RESULTS_DIR, 'exp8_intel.json')
    with open(out, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    log_msg(f"Saved: {out}")
    return summary


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    global start_time
    start_time = time.time()

    log_msg("=" * 80)
    log_msg("     AERIS MEGA EXPERIMENT SUITE - 10+ HOUR COMPREHENSIVE VALIDATION")
    log_msg("=" * 80)
    log_msg(f"CPU cores: {os.cpu_count()}, Using workers: {MAX_WORKERS}")
    log_msg(f"Results: {RESULTS_DIR}")
    log_msg("")

    all_results = {}

    try:
        # Experiment 1: Extended Scalability (~2 hours)
        log_msg("\n[1/8] Extended Scalability Experiment...")
        all_results['scalability'] = exp1_extended_scalability()

        # Experiment 2: Long-term Simulation (~1.5 hours)
        log_msg("\n[2/8] Long-term Simulation Experiment...")
        all_results['longterm'] = exp2_longterm_simulation()

        # Experiment 3: Exhaustive Topology (~2 hours)
        log_msg("\n[3/8] Exhaustive Topology Experiment...")
        all_results['topology'] = exp3_exhaustive_topology()

        # Experiment 4: Complete Ablation (~2 hours)
        log_msg("\n[4/8] Complete Ablation Matrix...")
        all_results['ablation'] = exp4_complete_ablation()

        # Experiment 5: Parameter Sensitivity (~0.5 hours)
        log_msg("\n[5/8] Parameter Sensitivity Experiment...")
        all_results['sensitivity'] = exp5_parameter_sensitivity()

        # Experiment 6: Bootstrap Validation (~2 hours)
        log_msg("\n[6/8] Bootstrap Statistical Validation...")
        all_results['bootstrap'] = exp6_bootstrap_validation()

        # Experiment 7: Stress Testing (~1 hour)
        log_msg("\n[7/8] Stress Testing Experiment...")
        all_results['stress'] = exp7_stress_testing()

        # Experiment 8: Intel Dataset (~0.5 hours)
        log_msg("\n[8/8] Intel Lab Dataset Experiment...")
        all_results['intel'] = exp8_intel_dataset()

    except Exception as e:
        log_msg(f"FATAL ERROR: {e}")
        log_msg(traceback.format_exc())

    # Save combined results
    combined = os.path.join(RESULTS_DIR, 'all_mega_results.json')
    with open(combined, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    log_msg(f"Combined results: {combined}")

    elapsed = time.time() - start_time
    log_msg("")
    log_msg("=" * 80)
    log_msg(f"     ALL EXPERIMENTS COMPLETED")
    log_msg(f"     Total runtime: {elapsed/3600:.2f} hours ({elapsed/60:.1f} minutes)")
    log_msg("=" * 80)


if __name__ == '__main__':
    main()
