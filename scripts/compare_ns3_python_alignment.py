#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare NS-3 vs Python alignment summaries.
"""
import argparse
import json
from datetime import datetime, timezone


def load_summary(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("summary", [])
    table = {}
    for e in entries:
        key = (e.get("protocol"), int(e.get("num_nodes", 0)), int(e.get("num_rounds", 0)))
        table[key] = e
    return data, table


def parse_args():
    ap = argparse.ArgumentParser(description="Compare NS-3 vs Python summaries")
    ap.add_argument("--ns3", required=True, help="NS-3 summary JSON")
    ap.add_argument("--python", required=True, help="Python summary JSON")
    ap.add_argument("--output", required=True, help="Output diff JSON")
    return ap.parse_args()


def main():
    args = parse_args()
    ns3_meta, ns3 = load_summary(args.ns3)
    py_meta, py = load_summary(args.python)

    diffs = []
    for key in sorted(set(ns3.keys()) & set(py.keys())):
        protocol, num_nodes, num_rounds = key
        n = ns3[key]
        p = py[key]
        ns3_pdr = float(n.get("pdr_mean", 0.0))
        py_pdr = float(p.get("pdr_mean", 0.0))
        ns3_energy = float(n.get("total_energy_mj_mean", 0.0))
        py_energy = float(p.get("total_energy_mj_mean", 0.0))

        pdr_diff = py_pdr - ns3_pdr
        energy_diff = py_energy - ns3_energy
        diffs.append({
            "protocol": protocol,
            "num_nodes": num_nodes,
            "num_rounds": num_rounds,
            "ns3_pdr_mean": ns3_pdr,
            "py_pdr_mean": py_pdr,
            "pdr_diff": pdr_diff,
            "pdr_diff_pct": (pdr_diff / ns3_pdr * 100.0) if ns3_pdr else 0.0,
            "ns3_energy_mj_mean": ns3_energy,
            "py_energy_mj_mean": py_energy,
            "energy_diff_mj": energy_diff,
            "energy_diff_pct": (energy_diff / ns3_energy * 100.0) if ns3_energy else 0.0,
            "ns3_n": int(n.get("n", 0)),
            "py_n": int(p.get("n", 0)),
        })

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ns3_summary": args.ns3,
        "python_summary": args.python,
        "diffs": diffs,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
