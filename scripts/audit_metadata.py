#!/usr/bin/env python3
"""
Audit metadata collection module for experiment reproducibility.

Provides git state, script hash, and config hash to ensure
every result file is traceable to exact code state.
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, Optional


def _run_git(args: list, cwd: str) -> str:
    """Run a git command and return stripped stdout, or empty string on failure."""
    try:
        out = subprocess.check_output(
            ["git"] + args,
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return out.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def get_git_commit(cwd: str) -> str:
    return _run_git(["rev-parse", "HEAD"], cwd)[:8] or "unknown"


def get_git_dirty(cwd: str) -> bool:
    status = _run_git(["status", "--porcelain", "--untracked-files=no"], cwd)
    return len(status) > 0


def get_git_diff_stat(cwd: str) -> str:
    """Return only the summary line of git diff --stat."""
    raw = _run_git(["diff", "--stat", "--no-color"], cwd)
    if not raw:
        return "clean"
    lines = raw.strip().splitlines()
    # Last line is the summary, e.g. "306 files changed, ..."
    return lines[-1].strip() if lines else "clean"


def get_file_sha256(filepath: str) -> str:
    try:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return "unknown"


def get_config_hash(config_dict: Dict[str, Any]) -> str:
    """SHA-256 of deterministically serialized config."""
    try:
        serialized = json.dumps(config_dict, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    except Exception:
        return "unknown"


def collect_audit_metadata(
    script_path: str,
    config_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Collect full audit metadata for experiment output.

    Parameters
    ----------
    script_path : str
        Absolute path to the calling script (__file__).
    config_dict : dict, optional
        Experiment config to hash for reproducibility.

    Returns
    -------
    dict with keys:
        git_commit, git_dirty, git_diff_stat,
        script_sha256, config_hash,
        python_version, timestamp
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(script_path)))

    meta = {
        "git_commit": get_git_commit(repo_root),
        "git_dirty": get_git_dirty(repo_root),
        "git_diff_stat": get_git_diff_stat(repo_root),
        "script_sha256": get_file_sha256(script_path),
        "config_hash": get_config_hash(config_dict) if config_dict else "none",
        "python_version": sys.version.split()[0],
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
    }
    return meta
