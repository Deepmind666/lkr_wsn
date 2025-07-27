"""
Enhanced EEHFR: Energy-Efficient Hybrid Fuzzy Routing Protocol for WSN

This package contains the core implementation of the Enhanced EEHFR protocol
and related components for wireless sensor network routing optimization.

Author: Deepmind666
Email: 1403073295@qq.com
"""

__version__ = "1.0.0"
__author__ = "Deepmind666"
__email__ = "1403073295@qq.com"

from .enhanced_eehfr_protocol import EnhancedEEHFR, EnhancedNode
from .intel_dataset_loader import IntelLabDataLoader
from .fuzzy_logic_system import FuzzyLogicSystem
from .hybrid_metaheuristic import HybridMetaheuristic

__all__ = [
    "EnhancedEEHFR",
    "EnhancedNode", 
    "IntelLabDataLoader",
    "FuzzyLogicSystem",
    "HybridMetaheuristic"
]
