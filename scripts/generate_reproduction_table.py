#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a Markdown table mapping scenarios to scripts/seeds/outputs/figures
based on docs/reproduction_manifest.json.
"""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "docs" / "reproduction_manifest.json"
OUTPUT = PROJECT_ROOT / "docs" / "Reproduction_Table.md"


def main():
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lines = [
        "| 场景 / 图表 | 核心命令 | 种子 / 复现设置 | 主要输出 | 关联图表 |",
        "|---|---|---|---|---|",
    ]
    for item in entries:
        outputs = "<br>".join(item["outputs"])
        lines.append(
            f"| {item['scenario']} | `{item['command']}` | {item['seeds']} | {outputs} | {item['figures']} |"
        )
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[WRITE] Reproduction table saved to {OUTPUT}")


if __name__ == "__main__":
    main()
