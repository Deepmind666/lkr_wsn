#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
论文图表生成主脚本

使用真实实验数据生成所有论文图表
"""

import subprocess
import sys
from pathlib import Path


def main():
    print("=" * 60)
    print("AERIS Paper Figure Generation")
    print("=" * 60)
    
    # 运行真实数据图表生成脚本
    print("\n[1/1] Generating figures with real experimental data...")
    
    script_path = Path(__file__).parent / "generate_real_data_figures.py"
    
    result = subprocess.run([sys.executable, str(script_path)], 
                          capture_output=False)
    
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("All figures generated successfully!")
        print("Output: results/real_data_figures/")
        print("=" * 60)
    else:
        print("\nFigure generation failed!")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
