#!/usr/bin/env python3
"""
Check status and acceptance criteria for overnight scalability runs.
"""

import argparse
import json
from pathlib import Path


def read_text_auto(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def count_raw_results(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return len(data.get("raw_results", []))
    except Exception:
        return -1


def main() -> int:
    parser = argparse.ArgumentParser(description="Check overnight scalability status.")
    parser.add_argument("--dir", required=True, help="Overnight directory path")
    parser.add_argument("--expected-per-env", type=int, default=16500)
    args = parser.parse_args()

    d = Path(args.dir)
    if not d.exists():
        print(f"status=missing_dir path={d}")
        return 1

    run_log = d / "run.log"
    manifest = d / "manifest.json"
    print(f"dir={d}")
    print(f"run_log_exists={run_log.exists()}")
    print(f"manifest_exists={manifest.exists()}")

    if run_log.exists():
        lines = read_text_auto(run_log).splitlines()
        tail = lines[-8:] if len(lines) >= 8 else lines
        print("run_log_tail:")
        for line in tail:
            print(line)

    env_files = sorted(d.glob("scalability_*.json"))
    print(f"env_json_count={len(env_files)}")
    for p in env_files:
        n = count_raw_results(p)
        ok = (n == args.expected_per_env)
        print(f"{p.name}: raw_results={n} expected={args.expected_per_env} pass={ok}")
        sidecar = p.with_suffix(p.suffix + ".provenance.json")
        print(f"{sidecar.name}: exists={sidecar.exists()}")

    if manifest.exists():
        with manifest.open("r", encoding="utf-8-sig") as f:
            m = json.load(f)
        runs = m.get("runs", [])
        print(f"manifest_runs={len(runs)}")
        failed = [r for r in runs if r.get("exit_code", -999) != 0]
        print(f"manifest_failed_runs={len(failed)}")
        for r in runs:
            print(
                f"run env={r.get('environment')} exit_code={r.get('exit_code')} "
                f"elapsed_seconds={r.get('elapsed_seconds')} retry_count={r.get('retry_count')}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
