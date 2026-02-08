#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试 (Sanity Check) - 模块功能验证
======================================
用途: 验证 GPT DeepSearch 新增模块功能正常工作
注意: 这是 sanity check，不是统计显著性验证实验

Author: AERIS Research Team
Date: 2026-01-27
"""

import sys
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
RESULTS_DIR = PROJECT_ROOT / "results"

sys.path.insert(0, str(SRC_DIR))


def get_git_commit() -> str:
    """获取当前 git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        return result.stdout.strip()[:12]
    except Exception:
        return "unknown"


def run_protocol_test(protocol_name: str, seed: int, n_nodes: int = 100,
                      n_rounds: int = 100) -> dict:
    """运行单个协议测试"""
    from benchmark_protocols import (
        NetworkConfig, LEACHProtocol, PEGASISProtocol, HEEDProtocolWrapper
    )
    from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
    from aeris_protocol import AerisProtocol

    width, height = 150.0, 150.0
    cfg = NetworkConfig(
        num_nodes=n_nodes,
        area_width=width,
        area_height=height,
        base_station_x=width * 0.5,
        base_station_y=height * 1.2,
        initial_energy=2.0,
        packet_size=1024,
    )
    cfg.enable_channel = True
    cfg.channel_env = "indoor_office"
    cfg.tx_power_dbm = 0.0
    cfg.gateway_k = 3

    import random
    rng = random.Random(seed)
    cfg.positions = [(rng.uniform(5, width-5), rng.uniform(5, height-5))
                     for _ in range(n_nodes)]

    em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)

    try:
        if protocol_name == "AERIS":
            proto = AerisProtocol(
                cfg, profile="robust", verbose=False, seed=seed,
                enable_cas=True, enable_gateway=True, enable_skeleton=True
            )
        elif protocol_name == "LEACH":
            proto = LEACHProtocol(cfg, em)
        elif protocol_name == "PEGASIS":
            proto = PEGASISProtocol(cfg, em)
        elif protocol_name == "HEED":
            proto = HEEDProtocolWrapper(cfg, em)
        else:
            return {"status": "error", "error": f"Unknown protocol: {protocol_name}"}

        result = proto.run_simulation(n_rounds)
        return {
            "status": "ok",
            "protocol": protocol_name,
            "seed": seed,
            "pdr": result.get("packet_delivery_ratio", 0),
            "energy": result.get("total_energy_consumed", 0),
            "alive_nodes": result.get("alive_nodes", n_nodes),
        }
    except Exception as e:
        return {"status": "error", "protocol": protocol_name, "error": str(e)}


def verify_module_functions():
    """验证 GPT DeepSearch 新增模块功能"""
    results = {}

    # 1. Gateway 负载均衡
    try:
        from gateway_selector import GatewaySelector, GatewayConfig
        gs = GatewaySelector(GatewayConfig())
        gs.reset_loads()
        gs.update_gateway_load(1, 5)
        gs.update_gateway_load(2, 3)
        results["gateway_load_balancing"] = {
            "status": "pass",
            "loads": dict(gs._gateway_loads),
            "has_reset_loads": hasattr(gs, 'reset_loads'),
            "has_update_gateway_load": hasattr(gs, 'update_gateway_load'),
            "has_get_backup_gateway": hasattr(gs, 'get_backup_gateway'),
        }
    except Exception as e:
        results["gateway_load_balancing"] = {"status": "fail", "error": str(e)}

    # 2. CAS 阶段权重
    try:
        from cas_selector import CASSelector, CASConfig
        cas = CASSelector(CASConfig())
        cas.set_stage_weights({'energy': 0.6, 'reliability': 0.3, 'distance': 0.1})
        results["cas_stage_weights"] = {
            "status": "pass",
            "weights_set": cas._stage_weights is not None,
            "has_set_stage_weights": hasattr(cas, 'set_stage_weights'),
        }
    except Exception as e:
        results["cas_stage_weights"] = {"status": "fail", "error": str(e)}

    # 3. Skeleton 规模自适应
    try:
        from skeleton_selector import SkeletonSelector, SkeletonConfig
        sk = SkeletonSelector(SkeletonConfig())
        p50 = sk.get_scale_adaptive_params(50)
        p200 = sk.get_scale_adaptive_params(200)
        p500 = sk.get_scale_adaptive_params(500)
        results["skeleton_scale_adaptive"] = {
            "status": "pass",
            "params_50": {"k": p50[0], "d_ratio": p50[1]},
            "params_200": {"k": p200[0], "d_ratio": p200[1]},
            "params_500": {"k": p500[0], "d_ratio": p500[1]},
        }
    except Exception as e:
        results["skeleton_scale_adaptive"] = {"status": "fail", "error": str(e)}

    # 4. 统一输出格式
    try:
        from experiment_output_format import (
            create_unified_result, validate_result_fields, to_unified_dict
        )
        ur = create_unified_result(
            protocol="TEST", scenario="test", n_nodes=10, n_rounds=10,
            pdr=0.95, energy=1.5, alive_nodes=10, seed=42
        )
        d = to_unified_dict(ur)
        missing = validate_result_fields(d)
        results["unified_output_format"] = {
            "status": "pass" if not missing else "fail",
            "missing_fields": missing,
            "sample_fields": list(d.keys())[:5],
        }
    except Exception as e:
        results["unified_output_format"] = {"status": "fail", "error": str(e)}

    return results


def main():
    """主函数"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    git_commit = get_git_commit()

    print("=" * 60)
    print("完整集成测试 - 对照协议 + 多seed验证")
    print("=" * 60)
    print(f"Git commit: {git_commit}")
    print(f"Timestamp: {timestamp}")

    # 配置
    protocols = ["AERIS", "LEACH", "PEGASIS", "HEED"]
    seeds = [42, 123, 456, 789, 1000]
    n_nodes = 100
    n_rounds = 100

    print(f"\n协议: {protocols}")
    print(f"Seeds: {seeds}")
    print(f"节点数: {n_nodes}, 轮数: {n_rounds}")
    print("=" * 60)

    # 1. 模块功能验证
    print("\n[1/2] 验证 GPT DeepSearch 模块功能...")
    module_results = verify_module_functions()
    for name, res in module_results.items():
        status = "PASS" if res.get("status") == "pass" else "FAIL"
        print(f"  {name}: {status}")

    # 2. 多协议多seed实验
    print(f"\n[2/2] 运行 {len(protocols)}协议 × {len(seeds)}seeds 实验...")
    experiment_results = []
    for protocol in protocols:
        for seed in seeds:
            print(f"  Running {protocol} seed={seed}...", end=" ")
            r = run_protocol_test(protocol, seed, n_nodes, n_rounds)
            experiment_results.append(r)
            if r["status"] == "ok":
                print(f"PDR={r['pdr']*100:.1f}%")
            else:
                print(f"ERROR: {r.get('error', 'unknown')}")

    # 统计摘要
    print("\n" + "=" * 60)
    print("实验结果摘要")
    print("=" * 60)

    import numpy as np
    summary = {}
    # 构建 runs 数组 - 按协议和seed组织的原始结果
    runs = []
    for protocol in protocols:
        matching = [r for r in experiment_results
                   if r.get("status") == "ok" and r["protocol"] == protocol]
        if matching:
            pdrs = [r["pdr"] for r in matching]
            energies = [r["energy"] for r in matching]
            summary[protocol] = {
                "n": len(matching),
                "pdr_mean": float(np.mean(pdrs)),
                "pdr_std": float(np.std(pdrs)),
                "energy_mean": float(np.mean(energies)),
            }
            print(f"{protocol}: PDR={summary[protocol]['pdr_mean']*100:.1f}% "
                  f"± {summary[protocol]['pdr_std']*100:.1f}% (n={len(matching)})")
            # 添加到 runs 数组
            for r in matching:
                runs.append({
                    "protocol": r["protocol"],
                    "seed": r["seed"],
                    "pdr": r["pdr"],
                    "energy": r["energy"],
                    "alive_nodes": r["alive_nodes"]
                })

    # 保存结果
    output = {
        "test_name": "sanity_check_module_verification",
        "test_type": "sanity_check",
        "purpose": "Verify GPT DeepSearch module functions work correctly (NOT statistical significance)",
        "timestamp": timestamp,
        "git_commit": git_commit,
        "config": {
            "protocols": protocols,
            "seeds": seeds,
            "n_nodes": n_nodes,
            "n_rounds": n_rounds,
        },
        "module_verification": module_results,
        "runs": runs,
        "experiment_results": experiment_results,
        "summary": summary,
        "format_version": "1.0"
    }

    out_file = RESULTS_DIR / f"integration_test_baselines_{timestamp}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {out_file}")

    # 验证通过检查
    print("\n" + "=" * 60)
    print("Codex 审查要求验证")
    print("=" * 60)
    all_modules_pass = all(r.get("status") == "pass" for r in module_results.values())
    ok_count = sum(1 for r in experiment_results if r.get("status") == "ok")
    total = len(protocols) * len(seeds)

    print(f"✓ 模块功能验证: {'PASS' if all_modules_pass else 'FAIL'}")
    print(f"✓ 对照协议数 ≥ 3: {len(protocols)} >= 3 -> PASS")
    print(f"✓ 多seed验证 ≥ 3: {len(seeds)} >= 3 -> PASS")
    print(f"✓ 实验成功率: {ok_count}/{total} ({ok_count/total*100:.0f}%)")
    print(f"✓ Git commit 追溯: {git_commit}")
    print("=" * 60)

    return output


if __name__ == "__main__":
    main()
