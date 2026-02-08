#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize NS-3 validation JSON output.
"""
import argparse
import json
import math
from datetime import datetime, timezone


def mean(values):
    return sum(values) / len(values) if values else 0.0


def std(values):
    if len(values) < 2:
        return 0.0
    m = mean(values)
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def summarize(records):
    groups = {}
    for r in records:
        key = (
            r.get("protocol"),
            int(r.get("num_nodes", 0) or 0),
            int(r.get("num_rounds", 0) or 0),
        )
        groups.setdefault(key, []).append(r)

    summary = []
    for (protocol, num_nodes, num_rounds), rows in sorted(groups.items()):
        pdrs = [float(r.get("pdr", 0.0) or 0.0) for r in rows]
        energies = [float(r.get("total_energy_mj", 0.0) or 0.0) for r in rows]
        alive = [int(r.get("alive_nodes", 0) or 0) for r in rows]
        dead = [int(r.get("dead_nodes", 0) or 0) for r in rows]
        snr = [float(r.get("avg_snr_db", 0.0) or 0.0) for r in rows]
        sent = [int(r.get("packets_sent", 0) or 0) for r in rows]
        delivered = [int(r.get("packets_delivered", 0) or 0) for r in rows]

        n = len(rows)
        pdr_std = std(pdrs)
        energy_std = std(energies)
        pdr_ci95 = 1.96 * pdr_std / math.sqrt(n) if n > 1 else 0.0
        energy_ci95 = 1.96 * energy_std / math.sqrt(n) if n > 1 else 0.0

        summary.append({
            "protocol": protocol,
            "num_nodes": num_nodes,
            "num_rounds": num_rounds,
            "n": n,
            "pdr_mean": mean(pdrs),
            "pdr_std": pdr_std,
            "pdr_ci95": pdr_ci95,
            "total_energy_mj_mean": mean(energies),
            "total_energy_mj_std": energy_std,
            "total_energy_mj_ci95": energy_ci95,
            "alive_nodes_mean": mean(alive),
            "dead_nodes_mean": mean(dead),
            "avg_snr_db_mean": mean(snr),
            "packets_sent_mean": mean(sent),
            "packets_delivered_mean": mean(delivered),
        })
    return summary


def parse_args():
    ap = argparse.ArgumentParser(description="Summarize NS-3 validation JSON")
    ap.add_argument("--input", required=True, help="Input NS-3 JSON file")
    ap.add_argument("--output", required=True, help="Output summary JSON file")
    return ap.parse_args()


def main():
    args = parse_args()
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("experiments", [])
    summary = summarize(records)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": args.input,
        "group_by": ["protocol", "num_nodes", "num_rounds"],
        "summary": summary,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
