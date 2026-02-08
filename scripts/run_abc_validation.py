#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC三方向综合验证主脚本
- 方向A: 扩大规模验证（200节点/300轮/30seeds）
- 方向B: 数值正确性验证
- 方向C: 非DIRECT场景验证

设备配置: 24核/96GB，80%利用率=19并行，保留20GB内存
预估时间: 1-2小时
"""
import os
import sys
import json
import time
import platform
import multiprocessing as mp
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def get_environment_info() -> Dict:
    """Collect environment info for reproducibility."""
    import subprocess
    env_info = {
        'python_version': platform.python_version(),
        'platform': platform.platform(),
        'processor': platform.processor(),
    }
    # Get git commit if available
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, timeout=5, cwd=os.path.dirname(__file__)
        )
        if result.returncode == 0:
            env_info['git_commit'] = result.stdout.strip()
    except Exception:
        env_info['git_commit'] = 'unknown'
    return env_info

# 并行配置
MAX_WORKERS = 19  # 80% of 24 cores
MEMORY_LIMIT_GB = 34  # 保留20GB给用户

# 输出目录
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', f'abc_validation_{TIMESTAMP}')


def ensure_output_dir():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, 'A_scale'), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, 'B_numerical'), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, 'C_non_direct'), exist_ok=True)


# ============================================================
# 方向A: 扩大规模验证
# ============================================================
def run_single_experiment_A(params: Dict) -> Dict:
    """单次方向A实验"""
    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol

    seed = params['seed']
    topology = params['topology']
    num_nodes = params['num_nodes']
    max_rounds = params['max_rounds']

    # 根据拓扑设置区域
    if topology == 'uniform':
        cfg = NetworkConfig(num_nodes=num_nodes, area_width=200, area_height=200,
                           initial_energy=2.0, packet_size=512)
    elif topology == 'corridor':
        cfg = NetworkConfig(num_nodes=num_nodes, area_width=400, area_height=100,
                           initial_energy=2.0, packet_size=512)
    elif topology == 'cluster':
        cfg = NetworkConfig(num_nodes=num_nodes, area_width=200, area_height=200,
                           initial_energy=2.0, packet_size=512)
    else:
        cfg = NetworkConfig(num_nodes=num_nodes, area_width=200, area_height=200,
                           initial_energy=2.0, packet_size=512)

    proto = AerisProtocol(cfg, verbose=False, seed=seed,
                          enable_cas=True, enable_fairness=True, enable_gateway=True)
    result = proto.run_simulation(max_rounds=max_rounds)

    am = result.get('additional_metrics', {})
    usage = am.get('cas_mode_usage_stats', {})
    total_decisions = am.get('cas_total_decisions', 0)
    safety_override = usage.get('safety_override', 0)
    direct_count = usage.get('DIRECT', 0)

    return {
        'seed': seed,
        'topology': topology,
        'num_nodes': num_nodes,
        'max_rounds': max_rounds,
        'pdr_end2end': result.get('packet_delivery_ratio_end2end', 0),
        'total_energy': result.get('total_energy_consumed', 0),
        'rounds_completed': result.get('rounds_completed', 0),
        'cas_mode_usage': usage,
        'cas_switch_rate': am.get('cas_switch_rate', 0),
        'cas_total_decisions': total_decisions,
        # Audit fields
        'cas_direct_excl_safety': direct_count - safety_override,
        'cas_safety_override': safety_override,
        'cas_switch_count': am.get('cas_switch_count', 0),
    }


def run_direction_A():
    """方向A: 扩大规模验证 - 200节点/300轮/30seeds"""
    print("\n" + "="*60)
    print("方向A: 扩大规模验证")
    print("配置: 200节点, 300轮, 30seeds, 3拓扑")
    print("="*60)

    tasks = []
    for seed in range(1, 31):  # 30 seeds
        for topology in ['uniform', 'corridor', 'cluster']:
            tasks.append({
                'seed': seed,
                'topology': topology,
                'num_nodes': 200,
                'max_rounds': 300,
            })

    print(f"总任务数: {len(tasks)}")
    results = []

    start_time = time.time()
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_single_experiment_A, t): t for t in tasks}
        for i, future in enumerate(as_completed(futures)):
            try:
                res = future.result()
                results.append(res)
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"  进度: {i+1}/{len(tasks)}, 耗时: {elapsed:.1f}s")
            except Exception as e:
                print(f"  错误: {e}")

    elapsed = time.time() - start_time
    print(f"方向A完成, 耗时: {elapsed:.1f}s")

    # 保存结果
    out_path = os.path.join(OUT_DIR, 'A_scale', 'scale_validation.json')
    with open(out_path, 'w') as f:
        json.dump({
            'timestamp': TIMESTAMP,
            'config': {'num_nodes': 200, 'max_rounds': 300, 'seeds': 30, 'topologies': 3},
            'elapsed_seconds': elapsed,
            'results': results,
        }, f, indent=2)

    # 生成统计摘要
    generate_A_summary(results)
    return results


def generate_A_summary(results: List[Dict]):
    """生成方向A统计摘要"""
    import numpy as np

    summary = {'by_topology': {}, 'overall': {}}

    for topo in ['uniform', 'corridor', 'cluster']:
        topo_results = [r for r in results if r['topology'] == topo]
        pdrs = [r['pdr_end2end'] for r in topo_results]
        switch_rates = [r['cas_switch_rate'] for r in topo_results]

        # CAS模式分布
        mode_totals = {'DIRECT': 0, 'CHAIN': 0, 'TWO_HOP': 0, 'safety_override': 0}
        total_decisions = 0
        for r in topo_results:
            usage = r.get('cas_mode_usage', {})
            for m in mode_totals:
                mode_totals[m] += usage.get(m, 0)
            total_decisions += r.get('cas_total_decisions', 0)

        summary['by_topology'][topo] = {
            'n_runs': len(topo_results),
            'pdr_mean': float(np.mean(pdrs)),
            'pdr_std': float(np.std(pdrs)),
            'pdr_min': float(np.min(pdrs)),
            'pdr_max': float(np.max(pdrs)),
            'switch_rate_mean': float(np.mean(switch_rates)),
            'cas_mode_distribution': {
                m: mode_totals[m] / max(1, total_decisions) for m in mode_totals
            },
            'total_decisions': total_decisions,
        }

    # 总体统计
    all_pdrs = [r['pdr_end2end'] for r in results]
    summary['overall'] = {
        'n_runs': len(results),
        'pdr_mean': float(np.mean(all_pdrs)),
        'pdr_std': float(np.std(all_pdrs)),
    }

    out_path = os.path.join(OUT_DIR, 'A_scale', 'scale_summary.json')
    with open(out_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  摘要已保存: {out_path}")


# ============================================================
# 方向B: 数值正确性验证
# ============================================================
def run_direction_B():
    """方向B: 数值正确性验证"""
    print("\n" + "="*60)
    print("方向B: 数值正确性验证")
    print("="*60)

    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol

    errors = []
    checks_passed = []

    # 测试配置
    cfg = NetworkConfig(num_nodes=100, area_width=150, area_height=150,
                       initial_energy=2.0, packet_size=512)
    proto = AerisProtocol(cfg, verbose=False, seed=42,
                          enable_cas=True, enable_fairness=True, enable_gateway=True)
    result = proto.run_simulation(max_rounds=200)
    am = result.get('additional_metrics', {})

    # B1: PDR与原始包统计一致性
    print("  B1: PDR与原始包统计一致性...")
    source_total = am.get('source_packets_total', 0)
    bs_delivered = am.get('bs_delivered_total', 0)
    pdr_top = result.get('packet_delivery_ratio_end2end', 0)
    pdr_calc = bs_delivered / source_total if source_total > 0 else 0

    if abs(pdr_top - pdr_calc) < 1e-6:
        checks_passed.append('B1_pdr_consistency')
    else:
        errors.append(f"B1: PDR不一致 top={pdr_top:.6f} calc={pdr_calc:.6f}")

    # B2: 能耗合理性检查
    print("  B2: 能耗合理性检查...")
    total_energy = result.get('total_energy_consumed', 0)
    initial_energy = cfg.initial_energy * cfg.num_nodes
    if 0 < total_energy < initial_energy:
        checks_passed.append('B2_energy_reasonable')
    else:
        errors.append(f"B2: 能耗异常 total={total_energy} initial={initial_energy}")

    # B3: CAS mode_sum consistency (numerical correctness)
    print("  B3: CAS mode_sum consistency...")
    usage = am.get('cas_mode_usage_stats', {})
    total_decisions = am.get('cas_total_decisions', 0)
    mode_sum = sum(usage.get(m, 0) for m in ['DIRECT', 'CHAIN', 'TWO_HOP'])
    if total_decisions > 0 and mode_sum == total_decisions:
        checks_passed.append('B3_cas_mode_sum_consistent')
    elif total_decisions == 0:
        checks_passed.append('B3_cas_no_decisions_skip')
    else:
        errors.append(f"B3: mode_sum({mode_sum}) != total({total_decisions})")

    # B4: 链路PDR分段一致性
    print("  B4: 链路PDR分段一致性...")
    intra_pdr = am.get('cluster_to_ch_pdr_total', 0)
    uplink_pdr = am.get('ch_to_bs_pdr_total', 0)
    if 0 <= intra_pdr <= 1 and 0 <= uplink_pdr <= 1:
        checks_passed.append('B4_link_pdr_range')
    else:
        errors.append(f"B4: 链路PDR越界 intra={intra_pdr} uplink={uplink_pdr}")

    # 保存结果
    report = {
        'timestamp': TIMESTAMP,
        'checks_passed': checks_passed,
        'errors': errors,
        'raw_metrics': {
            'pdr_top': pdr_top,
            'pdr_calc': pdr_calc,
            'total_energy': total_energy,
            'total_decisions': total_decisions,
            'mode_sum': mode_sum,
        }
    }

    out_path = os.path.join(OUT_DIR, 'B_numerical', 'numerical_validation.json')
    with open(out_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"  通过: {len(checks_passed)}, 失败: {len(errors)}")
    return report


# ============================================================
# 方向C: 非DIRECT场景验证
# ============================================================
def run_single_experiment_C(params: Dict) -> Dict:
    """单次方向C实验"""
    from benchmark_protocols import NetworkConfig
    from aeris_protocol import AerisProtocol

    scenario = params['scenario']
    seed = params['seed']

    # 根据场景配置网络
    if scenario == 'far_nodes':
        # 远距离节点：大区域，节点分散
        cfg = NetworkConfig(num_nodes=100, area_width=400, area_height=400,
                           initial_energy=2.0, packet_size=512)
    elif scenario == 'sparse':
        # 稀疏网络：少节点，大区域
        cfg = NetworkConfig(num_nodes=30, area_width=300, area_height=300,
                           initial_energy=2.0, packet_size=512)
    elif scenario == 'dense_far':
        # 密集但远离BS
        cfg = NetworkConfig(num_nodes=150, area_width=500, area_height=100,
                           initial_energy=2.0, packet_size=512)
    elif scenario == 'corridor_long':
        # 长走廊
        cfg = NetworkConfig(num_nodes=100, area_width=600, area_height=50,
                           initial_energy=2.0, packet_size=512)
    elif scenario == 'multi_hop_force':
        # 强制多跳：极大区域
        cfg = NetworkConfig(num_nodes=80, area_width=500, area_height=500,
                           initial_energy=2.0, packet_size=512)
    else:
        cfg = NetworkConfig(num_nodes=100, area_width=200, area_height=200,
                           initial_energy=2.0, packet_size=512)

    proto = AerisProtocol(cfg, verbose=False, seed=seed,
                          enable_cas=True, enable_fairness=True, enable_gateway=True)
    result = proto.run_simulation(max_rounds=200)
    am = result.get('additional_metrics', {})

    usage = am.get('cas_mode_usage_stats', {})
    total = am.get('cas_total_decisions', 1)

    safety_override = usage.get('safety_override', 0)
    direct_count = usage.get('DIRECT', 0)

    return {
        'scenario': scenario,
        'seed': seed,
        'pdr_end2end': result.get('packet_delivery_ratio_end2end', 0),
        'cas_mode_usage': usage,
        'cas_total_decisions': total,
        'direct_ratio': direct_count / max(1, total),
        'chain_ratio': usage.get('CHAIN', 0) / max(1, total),
        'twohop_ratio': usage.get('TWO_HOP', 0) / max(1, total),
        'safety_override': safety_override,
        'dist_bs_mean': am.get('cas_feature_stats', {}).get('dist_bs', {}).get('mean', 0),
        # Audit fields
        'cas_direct_excl_safety': direct_count - safety_override,
        'cas_switch_count': am.get('cas_switch_count', 0),
    }


def run_direction_C():
    """方向C: 非DIRECT场景验证"""
    print("\n" + "="*60)
    print("方向C: 非DIRECT场景验证")
    print("="*60)

    scenarios = ['far_nodes', 'sparse', 'dense_far', 'corridor_long', 'multi_hop_force']
    tasks = []
    for scenario in scenarios:
        for seed in range(1, 11):  # 10 seeds per scenario
            tasks.append({'scenario': scenario, 'seed': seed})

    print(f"总任务数: {len(tasks)}")
    results = []

    start_time = time.time()
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_single_experiment_C, t): t for t in tasks}
        for i, future in enumerate(as_completed(futures)):
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                print(f"  错误: {e}")

    elapsed = time.time() - start_time
    print(f"方向C完成, 耗时: {elapsed:.1f}s")

    # 保存结果
    out_path = os.path.join(OUT_DIR, 'C_non_direct', 'non_direct_validation.json')
    with open(out_path, 'w') as f:
        json.dump({
            'timestamp': TIMESTAMP,
            'elapsed_seconds': elapsed,
            'results': results,
        }, f, indent=2)

    # 生成摘要
    generate_C_summary(results)
    return results


def generate_C_summary(results: List[Dict]):
    """生成方向C统计摘要"""
    import numpy as np

    summary = {'by_scenario': {}, 'non_direct_triggered': False}

    for scenario in ['far_nodes', 'sparse', 'dense_far', 'corridor_long', 'multi_hop_force']:
        sc_results = [r for r in results if r['scenario'] == scenario]
        if not sc_results:
            continue

        direct_ratios = [r['direct_ratio'] for r in sc_results]
        chain_ratios = [r['chain_ratio'] for r in sc_results]
        twohop_ratios = [r['twohop_ratio'] for r in sc_results]

        summary['by_scenario'][scenario] = {
            'n_runs': len(sc_results),
            'direct_ratio_mean': float(np.mean(direct_ratios)),
            'chain_ratio_mean': float(np.mean(chain_ratios)),
            'twohop_ratio_mean': float(np.mean(twohop_ratios)),
            'non_direct_any': any(r['chain_ratio'] > 0 or r['twohop_ratio'] > 0 for r in sc_results),
        }

        if summary['by_scenario'][scenario]['non_direct_any']:
            summary['non_direct_triggered'] = True

    out_path = os.path.join(OUT_DIR, 'C_non_direct', 'non_direct_summary.json')
    with open(out_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  摘要已保存: {out_path}")


# ============================================================
# 方向D: NS-3交叉验证
# ============================================================
def run_direction_D():
    """方向D: NS-3交叉验证"""
    print("\n" + "="*60)
    print("方向D: NS-3交叉验证")
    print("="*60)

    import subprocess

    # 检查WSL是否可用
    try:
        result = subprocess.run(['wsl', '-l', '-v'], capture_output=True, timeout=10)
        if result.returncode != 0:
            print("  WSL不可用，NS-3验证失败")
            return {'status': 'FAILED', 'reason': 'WSL not available'}
    except Exception as e:
        print(f"  WSL检查失败: {e}")
        return {'status': 'FAILED', 'reason': str(e)}

    print("  运行NS-3 standalone验证...")
    start_time = time.time()

    try:
        cmd = [
            'wsl', '-d', 'Ubuntu-24.04', '--',
            'bash', '-c',
            'cd /home/lkr/ns-allinone-3.40/ns-3.40 && ./ns3 run aeris-validation-standalone 2>&1'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = result.stdout

        elapsed = time.time() - start_time
        print(f"  NS-3完成, 耗时: {elapsed:.1f}s")

        ns3_results = parse_ns3_output(output)
        ns3_results['elapsed_seconds'] = elapsed

        # 保存结果
        os.makedirs(os.path.join(OUT_DIR, 'D_ns3'), exist_ok=True)
        out_path = os.path.join(OUT_DIR, 'D_ns3', 'ns3_validation.json')
        with open(out_path, 'w') as f:
            json.dump(ns3_results, f, indent=2)

        print(f"  AERIS PDR: {ns3_results.get('aeris_pdr', 'N/A')}")
        print(f"  LEACH PDR: {ns3_results.get('leach_pdr', 'N/A')}")
        return ns3_results

    except subprocess.TimeoutExpired:
        print("  NS-3运行超时")
        return {'status': 'FAILED', 'reason': 'timeout'}
    except Exception as e:
        print(f"  NS-3运行失败: {e}")
        return {'status': 'FAILED', 'reason': str(e)}


def parse_ns3_output(output: str) -> Dict:
    """解析NS-3输出"""
    import re
    result = {'status': 'success'}

    # 解析AERIS结果
    aeris_match = re.search(r'AERIS.*PDR=(\d+\.?\d*)%.*E=(\d+\.?\d*)mJ.*Alive=(\d+)', output)
    if aeris_match:
        result['aeris_pdr'] = float(aeris_match.group(1))
        result['aeris_energy'] = float(aeris_match.group(2))
        result['aeris_alive'] = int(aeris_match.group(3))

    # 解析LEACH结果
    leach_match = re.search(r'LEACH.*PDR=(\d+\.?\d*)%.*E=(\d+\.?\d*)mJ.*Alive=(\d+)', output)
    if leach_match:
        result['leach_pdr'] = float(leach_match.group(1))
        result['leach_energy'] = float(leach_match.group(2))
        result['leach_alive'] = int(leach_match.group(3))

    return result


# ============================================================
# 主函数
# ============================================================
def main():
    """主函数：运行ABC三方向验证"""
    print("="*60)
    print("ABC三方向综合验证")
    print(f"时间戳: {TIMESTAMP}")
    print(f"并行数: {MAX_WORKERS}")
    print("="*60)

    ensure_output_dir()
    total_start = time.time()

    results_A = run_direction_A()
    results_B = run_direction_B()
    results_C = run_direction_C()
    results_D = run_direction_D()

    total_elapsed = time.time() - total_start
    print("\n" + "="*60)
    print(f"全部完成! 总耗时: {total_elapsed/60:.1f}分钟")
    print(f"输出目录: {OUT_DIR}")
    print("="*60)

    generate_file_manifest()


def generate_file_manifest():
    """生成文件清单"""
    env_info = get_environment_info()
    manifest = {
        'timestamp': TIMESTAMP,
        'output_dir': OUT_DIR,
        'environment': env_info,
        'files': [
            'A_scale/scale_validation.json',
            'A_scale/scale_summary.json',
            'B_numerical/numerical_validation.json',
            'C_non_direct/non_direct_validation.json',
            'C_non_direct/non_direct_summary.json',
            'D_ns3/ns3_validation.json',
            'manifest.json',
        ]
    }
    out_path = os.path.join(OUT_DIR, 'manifest.json')
    with open(out_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"文件清单: {out_path}")


if __name__ == '__main__':
    mp.freeze_support()
    main()
