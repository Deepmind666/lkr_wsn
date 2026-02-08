#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot GPU load from nvidia-smi CSV and optional GPU Engine counters.
Outputs PNG figures suitable for MDPI Sensors paper.
"""
import os
import sys
import argparse
import csv
from datetime import datetime
import matplotlib.pyplot as plt


def read_smi_csv(path):
    ts, util, mem_used, mem_total = [], [], [], []
    if not os.path.exists(path):
        return ts, util, mem_used, mem_total
    with open(path, 'r', encoding='ascii') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row:
                continue
            # Example row: 2025/10/21 11:51:26.904, 1, 4824, 32607
            try:
                t = datetime.strptime(row[0].strip(), '%Y/%m/%d %H:%M:%S.%f')
            except Exception:
                try:
                    t = datetime.strptime(row[0].strip(), '%Y/%m/%d %H:%M:%S')
                except Exception:
                    t = None
            ts.append(t)
            util.append(float(row[1].strip()))
            mem_used.append(float(row[2].strip()))
            mem_total.append(float(row[3].strip()))
    return ts, util, mem_used, mem_total


def read_engine_csv(path):
    # CSV format: timestamp,engine,util
    ts, util_sum = [], []
    if not os.path.exists(path):
        return ts, util_sum
    by_ts = {}
    with open(path, 'r', encoding='ascii') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row:
                continue
            t = row[0].strip()
            u = 0.0
            try:
                u = float(row[2].strip())
            except Exception:
                u = 0.0
            by_ts.setdefault(t, 0.0)
            by_ts[t] += u
    for k in sorted(by_ts.keys()):
        ts.append(k)
        util_sum.append(by_ts[k])
    return ts, util_sum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smi', default='results/_logs/gpu_burn/nvidia_smi_util.csv')
    parser.add_argument('--engine', default='results/_logs/gpu_burn/gpu_engine_util.csv')
    parser.add_argument('--outdir', default='results/Sensors_figures')
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    smi_ts, smi_util, smi_mem_used, smi_mem_total = read_smi_csv(args.smi)
    eng_ts, eng_util_sum = read_engine_csv(args.engine)

    # Figure 1: nvidia-smi util & memory
    plt.figure(figsize=(10, 4))
    x = list(range(len(smi_util))) if not smi_ts or any(t is None for t in smi_ts) else smi_ts
    plt.plot(x, smi_util, label='GPU util (nvidia-smi) %')
    if smi_mem_used and smi_mem_total:
        plt.plot(x, [100.0 * u / (smi_mem_total[i] or 1.0) for i, u in enumerate(smi_mem_used)], label='Memory usage %')
    plt.xlabel('time')
    plt.ylabel('percent')
    plt.title('GPU load via nvidia-smi')
    plt.legend()
    plt.tight_layout()
    out1 = os.path.join(args.outdir, 'gpu_dml_smi.png')
    plt.savefig(out1, dpi=150)
    plt.close()

    # Figure 2: GPU Engine sum utilization
    plt.figure(figsize=(10, 4))
    x2 = list(range(len(eng_util_sum))) if not eng_ts else list(range(len(eng_ts)))
    plt.plot(x2, eng_util_sum, label='GPU Engine sum util %')
    plt.xlabel('sample index')
    plt.ylabel('percent')
    plt.title('GPU Engine utilization sum')
    plt.legend()
    plt.tight_layout()
    out2 = os.path.join(args.outdir, 'gpu_dml_engine.png')
    plt.savefig(out2, dpi=150)
    plt.close()

    print({'smi_png': out1, 'engine_png': out2, 'smi_points': len(smi_util), 'engine_points': len(eng_util_sum)})


if __name__ == '__main__':
    main()