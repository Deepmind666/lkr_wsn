#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Python环境依赖完整性

用途: 检查AERIS项目所需的所有Python依赖是否正确安装
作者: Claude
日期: 2025-10-19
"""

import sys
print("=" * 60)
print("AERIS项目环境验证")
print("=" * 60)
print(f"\nPython版本: {sys.version}")
print(f"执行路径: {sys.executable}")
print("\n依赖检查:")
print("-" * 60)

deps_status = []

# 核心科学计算库
try:
    import numpy as np
    print(f"✅ NumPy {np.__version__}")
    deps_status.append(True)
except ImportError as e:
    print(f"❌ NumPy - {e}")
    deps_status.append(False)

try:
    import scipy
    print(f"✅ SciPy {scipy.__version__}")
    deps_status.append(True)
except ImportError as e:
    print(f"❌ SciPy - {e}")
    deps_status.append(False)

try:
    import pandas as pd
    print(f"✅ Pandas {pd.__version__}")
    deps_status.append(True)
except ImportError as e:
    print(f"❌ Pandas - {e}")
    deps_status.append(False)

# 机器学习
try:
    import sklearn
    print(f"✅ Scikit-learn {sklearn.__version__}")
    deps_status.append(True)
except ImportError as e:
    print(f"❌ Scikit-learn - {e}")
    deps_status.append(False)

# 深度学习
try:
    import torch
    cuda_available = torch.cuda.is_available()
    cuda_str = f" (CUDA: {torch.cuda.get_device_name(0)})" if cuda_available else " (CPU only)"
    print(f"✅ PyTorch {torch.__version__}{cuda_str}")
    deps_status.append(True)
except ImportError as e:
    print(f"❌ PyTorch - {e}")
    deps_status.append(False)

# 可视化
try:
    import matplotlib
    print(f"✅ Matplotlib {matplotlib.__version__}")
    deps_status.append(True)
except ImportError as e:
    print(f"❌ Matplotlib - {e}")
    deps_status.append(False)

try:
    import seaborn as sns
    print(f"✅ Seaborn {sns.__version__}")
    deps_status.append(True)
except ImportError as e:
    print(f"❌ Seaborn - {e}")
    deps_status.append(False)

# 网络分析
try:
    import networkx as nx
    print(f"✅ NetworkX {nx.__version__}")
    deps_status.append(True)
except ImportError as e:
    print(f"❌ NetworkX - {e}")
    deps_status.append(False)

# 其他工具
try:
    import tqdm
    print(f"✅ tqdm {tqdm.__version__}")
    deps_status.append(True)
except ImportError as e:
    print(f"❌ tqdm - {e}")
    deps_status.append(False)

print("-" * 60)
success_count = sum(deps_status)
total_count = len(deps_status)
success_rate = (success_count / total_count) * 100

print(f"\n总结: {success_count}/{total_count} 依赖已安装 ({success_rate:.1f}%)")

if success_rate == 100:
    print("\n🎉 所有依赖已正确安装！环境配置完成。")
    sys.exit(0)
elif success_rate >= 80:
    print("\n⚠️  大部分依赖已安装，但有些缺失。建议运行:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
else:
    print("\n❌ 环境配置不完整！请运行:")
    print("   conda activate aeris-py311")
    print("   pip install -r requirements.txt")
    sys.exit(2)
