#!/usr/bin/env python3
"""
批量实验运行脚本
按顺序执行：
1. 消融实验 (约2小时)
2. 环境敏感性实验 (约2小时)
3. 功率敏感性实验 (约2小时)
"""

import subprocess
import sys
import os
from datetime import datetime

PYTHON = sys.executable
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

EXPERIMENTS = [
    ('消融实验', 'run_ablation_study.py', ['--full']),
    ('环境敏感性', 'run_env_sensitivity.py', ['--full']),
    ('功率敏感性', 'run_power_sensitivity.py', ['--full']),
]

def main():
    print("=" * 60)
    print("批量实验启动")
    print(f"开始时间: {datetime.now()}")
    print(f"实验数量: {len(EXPERIMENTS)}")
    print("=" * 60)

    for name, script, args in EXPERIMENTS:
        print(f"\n>>> 启动: {name}")
        print(f"    脚本: {script}")
        print(f"    时间: {datetime.now()}")

        script_path = os.path.join(SCRIPTS_DIR, script)
        cmd = [PYTHON, script_path] + args

        try:
            subprocess.run(cmd, check=True)
            print(f"    完成: {name}")
        except subprocess.CalledProcessError as e:
            print(f"    错误: {e}")
        except Exception as e:
            print(f"    异常: {e}")

    print("\n" + "=" * 60)
    print(f"全部完成: {datetime.now()}")
    print("=" * 60)

if __name__ == "__main__":
    main()
