#!/usr/bin/env python3
"""
Generate provenance sidecar files for overnight scalability outputs.

This is a post-hoc helper used to add reproducibility metadata to
existing scalability JSON outputs that do not contain full audit fields.
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


SOURCE_FILES = [
    "src/aeris_protocol.py",
    "src/cas_selector.py",
    "src/gateway_selector.py",
    "src/skeleton_selector.py",
    "src/realistic_channel_model.py",
    "src/baseline_protocols/__init__.py",
    "src/baseline_protocols/leach_protocol.py",
    "src/baseline_protocols/pegasis_protocol.py",
    "src/baseline_protocols/heed_protocol.py",
    "src/teen_protocol.py",
    "src/benchmark_protocols.py",
]


def run_git(args: List[str], repo_root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git"] + args,
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return out.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def get_git_state(repo_root: Path) -> Tuple[str, bool, Dict[str, str]]:
    commit = run_git(["rev-parse", "HEAD"], repo_root)[:8] or "unknown"
    unstaged_full = run_git(["diff", "--stat", "--no-color"], repo_root)
    staged_full = run_git(["diff", "--stat", "--cached", "--no-color"], repo_root)
    unstaged = unstaged_full.splitlines()[-1].strip() if unstaged_full else "clean"
    staged = staged_full.splitlines()[-1].strip() if staged_full else "clean"
    dirty = (unstaged != "clean") or (staged != "clean")
    return commit, dirty, {"unstaged": unstaged, "staged": staged}


def file_sha256(path: Path) -> str:
    if not path.exists():
        return "missing"
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def config_hash(config: Dict) -> str:
    try:
        data = json.dumps(config, sort_keys=True, ensure_ascii=True, default=str)
    except Exception:
        data = "{}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def normalize_nodes(manifest: Dict) -> str:
    nodes = manifest.get("nodes")
    if isinstance(nodes, list):
        return ",".join(str(x) for x in nodes)
    return str(nodes)


def build_command(manifest: Dict, env_name: str, output_path: str) -> str:
    nodes_csv = normalize_nodes(manifest)
    return (
        "python scripts/run_scalability_experiment.py "
        f"--nodes {nodes_csv} "
        f"--replicates {manifest.get('replicates', 'unknown')} "
        f"--workers {manifest.get('workers', 'unknown')} "
        f"--rounds {manifest.get('rounds', 'unknown')} "
        f"--env {env_name} "
        "--run-tier publication "
        f"--output {output_path}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate provenance sidecars for overnight scalability results"
    )
    parser.add_argument(
        "--overnight-dir",
        required=True,
        help="Path to overnight_scalability_* directory containing manifest.json",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    overnight_dir = (repo_root / args.overnight_dir).resolve()
    if not overnight_dir.exists():
        print(f"[ERROR] Directory not found: {overnight_dir}")
        return 1

    manifest_path = overnight_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"[ERROR] manifest.json not found in {overnight_dir}")
        return 1

    with open(manifest_path, "r", encoding="utf-8-sig") as f:
        manifest = json.load(f)

    script_path = repo_root / "scripts" / "run_scalability_experiment.py"
    script_hash = file_sha256(script_path)
    src_hashes = {rel: file_sha256(repo_root / rel) for rel in SOURCE_FILES}
    commit, dirty, diff_stat = get_git_state(repo_root)

    json_files = sorted(overnight_dir.glob("scalability_*.json"))
    if not json_files:
        print(f"[ERROR] No scalability_*.json files found in {overnight_dir}")
        return 1

    ts = datetime.now().strftime("%Y%m%d")
    created = 0
    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8-sig") as f:
            result = json.load(f)

        env_name = result.get("environment", "unknown")
        sidecar = {
            "provenance_for": json_file.name,
            "provenance_generated": ts,
            "provenance_generator": "Codex GPT-5 (post-hoc sidecar)",
            "command_line": build_command(manifest, env_name, str(json_file)),
            "python_version": sys.version.replace("\n", " "),
            "platform": platform.platform(),
            "platform_machine": platform.machine(),
            "platform_processor": platform.processor(),
            "git_commit": result.get("git_commit", commit) or commit,
            "git_dirty": dirty,
            "git_diff_stat": diff_stat,
            "script_sha256": script_hash,
            "source_sha256": src_hashes,
            "experiment_timestamp": result.get("timestamp", "unknown"),
            "run_tier": result.get("run_tier", "unknown"),
            "primary_metric": result.get("primary_metric", "unknown"),
            "config_hash": config_hash(result.get("config", {})),
            "note": (
                "Post-hoc sidecar generated after run completion. "
                "Runtime git_dirty was not embedded in source JSON; "
                "current workspace git state is recorded here."
            ),
        }

        out_path = json_file.with_suffix(".provenance.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(sidecar, f, indent=2, ensure_ascii=True)
        created += 1
        print(f"[OK] {out_path}")

    print(f"[DONE] Generated {created} provenance sidecars in {overnight_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
