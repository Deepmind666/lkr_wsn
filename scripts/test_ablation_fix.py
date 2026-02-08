#!/usr/bin/env python3
"""快速测试消融实验修复效果"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from benchmark_protocols import NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol
import random

def test_ablation_variant(variant_name, enable_cas, enable_gateway, enable_skeleton,
                          reliability_mode="lightweight", rounds=500, area_scale=1.8):
    """测试单个消融变体 - 平衡条件"""
    cfg = NetworkConfig(
        num_nodes=120,
        area_width=150.0 * area_scale,
        area_height=150.0 * area_scale,
        base_station_x=150.0 * area_scale * 0.5,
        base_station_y=150.0 * area_scale * 1.3,
        initial_energy=1.5,
        packet_size=1024,
    )
    cfg.enable_channel = True
    cfg.channel_env = "outdoor_rural"
    cfg.reliability_mode = reliability_mode
    cfg.tx_power_dbm = 0.0

    # 生成随机位置
    rng = random.Random(42)
    w, h = 150.0 * area_scale, 150.0 * area_scale
    cfg.positions = [(rng.uniform(5, w-5), rng.uniform(5, h-5)) for _ in range(100)]

    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    proto = AerisProtocol(
        cfg, profile="robust", verbose=False, seed=42,
        enable_cas=enable_cas,
        enable_gateway=enable_gateway,
        enable_skeleton=enable_skeleton
    )

    result = proto.run_simulation(rounds)
    pdr_e2e = result.get("packet_delivery_ratio_end2end", 0)
    energy = result.get("total_energy_consumed", 0)

    # 获取CAS模式使用统计
    cas_stats = result.get("additional_metrics", {}).get("cas_mode_usage_stats", {})
    return pdr_e2e, energy, cas_stats

def main():
    print("=" * 60)
    print("消融实验修复验证测试 (恶劣条件)")
    print("=" * 60)
    print(f"条件: 区域2x, BS距离1.5x, outdoor_rural, 500轮")
    print()

    variants = [
        ("full", True, True, True),
        ("no_cas", False, True, True),
        ("no_gateway", True, False, True),
        ("no_skeleton", True, True, False),
        ("minimal", False, False, False),
    ]

    results = []
    for name, cas, gw, sk in variants:
        print(f"测试 {name}...", end=" ", flush=True)
        pdr, energy, cas_stats = test_ablation_variant(name, cas, gw, sk)
        results.append((name, pdr, energy, cas_stats))
        print(f"PDR={pdr*100:.1f}%, Energy={energy:.1f}J, CAS={cas_stats}")

    print()
    print("=" * 60)
    print("结果汇总:")
    print("=" * 60)
    print(f"{'变体':<15} {'PDR':<10} {'能耗(J)':<10}")
    print("-" * 35)
    for name, pdr, energy, cas_stats in results:
        print(f"{name:<15} {pdr*100:.1f}%{'':<5} {energy:.1f}")

    # 检查是否有差异
    pdrs = [r[1] for r in results]
    pdr_range = max(pdrs) - min(pdrs)
    print()
    if pdr_range > 0.05:
        print(f"[OK] PDR差异范围: {pdr_range*100:.1f}% - 消融实验有效!")
    else:
        print(f"[WARNING] PDR差异范围: {pdr_range*100:.1f}% - 差异可能不够显著")

if __name__ == "__main__":
    main()
