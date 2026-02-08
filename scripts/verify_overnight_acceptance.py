#!/usr/bin/env python3
"""
Verify acceptance criteria for overnight scalability experiment outputs.
"""

import argparse
import json
from pathlib import Path


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify overnight scalability acceptance criteria.")
    parser.add_argument("--dir", required=True, help="Overnight output directory")
    parser.add_argument("--expected-replicates", type=int, default=550)
    parser.add_argument("--expected-node-counts", type=int, default=6)
    parser.add_argument("--expected-protocols", type=int, default=5)
    parser.add_argument("--expected-envs", type=int, default=4)
    args = parser.parse_args()

    base = Path(args.dir)
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        print(f"FAIL: missing manifest {manifest_path}")
        return 2

    manifest = load_json(manifest_path)
    runs = manifest.get("runs", [])
    ok = True

    if len(runs) != args.expected_envs:
        print(f"FAIL: env run count mismatch {len(runs)} != {args.expected_envs}")
        ok = False

    failed_runs = [r for r in runs if int(r.get("exit_code", -999)) != 0]
    if failed_runs:
        print("FAIL: non-zero exit runs:")
        for r in failed_runs:
            print(f"  env={r.get('environment')} exit_code={r.get('exit_code')} retry_count={r.get('retry_count')}")
        ok = False

    expected_raw = args.expected_replicates * args.expected_node_counts * args.expected_protocols
    env_jsons = sorted(base.glob("scalability_*.json"))
    if len(env_jsons) != args.expected_envs:
        print(f"FAIL: scalability json count mismatch {len(env_jsons)} != {args.expected_envs}")
        ok = False

    for p in env_jsons:
        data = load_json(p)
        raw_n = len(data.get("raw_results", []))
        if raw_n != expected_raw:
            print(f"FAIL: {p.name} raw_results={raw_n} expected={expected_raw}")
            ok = False
        else:
            print(f"PASS: {p.name} raw_results={raw_n}")

        sidecar = p.with_suffix(p.suffix + ".provenance.json")
        if not sidecar.exists():
            print(f"FAIL: missing sidecar {sidecar.name}")
            ok = False
        else:
            print(f"PASS: {sidecar.name}")

    if ok:
        print("ACCEPTANCE=PASS")
        return 0

    print("ACCEPTANCE=FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

