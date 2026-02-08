"""
AERIS: Adaptive Environment-aware Routing and Intelligent Scheduling for WSN

This package contains the core implementation of the AERIS protocol
and related components for wireless sensor network routing optimization.

Author: AERIS Research Team
Email: 1403073295@qq.com
"""

__version__ = "1.0.0"
__author__ = "AERIS Research Team"
__email__ = "1403073295@qq.com"

from .aeris_protocol import AerisProtocol, EnhancedNode
# 兼容旧符号：保持 AERIS 名称可用
AERIS = AerisProtocol
from .intel_dataset_loader import IntelLabDataLoader

# 尝试性导入：若未安装 skfuzzy，则避免在包导入阶段失败
try:
    from .fuzzy_logic_system import FuzzyLogicSystem
except Exception:
    FuzzyLogicSystem = None  # 提供占位，避�?from package import * 失败

from .hybrid_metaheuristic import HybridMetaheuristic

__all__ = [
    "AerisProtocol",
    "AERIS",
    "EnhancedNode", 
    "IntelLabDataLoader",
    "FuzzyLogicSystem",
    "HybridMetaheuristic"
]
