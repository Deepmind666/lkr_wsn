#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取并分析所有拓扑的PDR数据
生成论文用的完整对比表格

作者: Claude
日期: 2025-10-19
"""

import json
import os
from pathlib import Path

def safe_load_json(filepath):
    """安全加载JSON文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load {filepath}: {e}")
        return None

def extract_pdr_data():
    """提取所有实验的PDR数据"""

    results = {}

    # 1. final_baseline_compare.json - 最完整的基线对比
    print("=" * 80)
    print("分析 final_baseline_compare.json")
    print("=" * 80)

    data = safe_load_json('results/final_baseline_compare.json')
    if data:
        for topo_name, topo_data in data.items():
            if isinstance(topo_data, dict):
                print(f"\n拓扑: {topo_name}")
                for protocol, metrics in topo_data.items():
                    if isinstance(metrics, dict) and 'packet_delivery_ratio_end2end' in metrics:
                        pdr = metrics['packet_delivery_ratio_end2end']
                        energy = metrics.get('total_energy_consumed', 'N/A')
                        lifetime = metrics.get('network_lifetime', 'N/A')

                        print(f"  {protocol:20s}: PDR={pdr:.4f} ({pdr*100:.2f}%), Energy={energy}, Lifetime={lifetime}")

                        # 保存到结果字典
                        if topo_name not in results:
                            results[topo_name] = {}
                        results[topo_name][protocol] = {
                            'pdr_e2e': pdr,
                            'energy': energy,
                            'lifetime': lifetime
                        }

    # 2. intel_baselines_all.json - Intel Lab真实数据
    print("\n" + "=" * 80)
    print("分析 intel_baselines_all.json")
    print("=" * 80)

    data = safe_load_json('results/intel_baselines_all.json')
    if data:
        print(f"\n拓扑: Intel Lab (54 nodes)")
        for protocol in ['LEACH', 'HEED', 'PEGASIS', 'TEEN']:
            if protocol in data:
                metrics = data[protocol]
                pdr = metrics.get('packet_delivery_ratio_end2end', 'N/A')
                energy = metrics.get('total_energy_consumed', 'N/A')
                lifetime = metrics.get('network_lifetime', 'N/A')

                print(f"  {protocol:20s}: PDR={pdr:.4f} ({pdr*100:.2f}%), Energy={energy}, Lifetime={lifetime}")

                if 'intel_lab' not in results:
                    results['intel_lab'] = {}
                results['intel_lab'][protocol] = {
                    'pdr_e2e': pdr,
                    'energy': energy,
                    'lifetime': lifetime
                }

    # 3. compare_50x200.json - 另一组对比
    print("\n" + "=" * 80)
    print("分析 compare_50x200.json")
    print("=" * 80)

    data = safe_load_json('results/compare_50x200.json')
    if data:
        print(f"\n拓扑: compare_50x200")
        for protocol, metrics in data.items():
            if isinstance(metrics, dict) and 'packet_delivery_ratio_end2end' in metrics:
                pdr = metrics['packet_delivery_ratio_end2end']
                energy = metrics.get('total_energy_consumed', 'N/A')

                print(f"  {protocol:20s}: PDR={pdr:.4f} ({pdr*100:.2f}%), Energy={energy}")

                if 'compare_50x200' not in results:
                    results['compare_50x200'] = {}
                results['compare_50x200'][protocol] = {
                    'pdr_e2e': pdr,
                    'energy': energy
                }

    # 4. 检查Intel ablation和sensitivity数据
    for filename in ['intel_ablation.json', 'intel_sensitivity_parallel.json', 'intel_replay_compare.json']:
        filepath = f'results/{filename}'
        if os.path.exists(filepath):
            print(f"\n" + "=" * 80)
            print(f"分析 {filename}")
            print("=" * 80)
            data = safe_load_json(filepath)
            if data:
                # 尝试提取PDR数据
                if isinstance(data, dict):
                    for key, value in list(data.items())[:5]:  # 只看前5个
                        if isinstance(value, dict):
                            pdr = value.get('pdr_end2end') or value.get('mean', {}).get('pdr_end2end')
                            if pdr is not None:
                                print(f"  {key}: PDR={pdr:.4f} ({pdr*100:.2f}%)")

    return results

def generate_comparison_table(results):
    """生成论文用的对比表格（Markdown格式）"""

    print("\n" + "=" * 80)
    print("生成论文对比表格")
    print("=" * 80)

    # 表格1: 所有拓扑的AERIS vs 最佳基线
    print("\n## Table: PDR Comparison Across Different Topologies\n")
    print("| Topology | Nodes | AERIS PDR | Best Baseline | Best PDR | Improvement |")
    print("|----------|-------|-----------|---------------|----------|-------------|")

    for topo_name, protocols in results.items():
        # 找AERIS数据
        aeris_pdr = None
        for p_name in ['AETHER_energy', 'AETHER', 'AERIS']:
            if p_name in protocols:
                aeris_pdr = protocols[p_name]['pdr_e2e']
                break

        # 找最佳基线
        best_baseline = None
        best_pdr = 0
        for p_name, p_data in protocols.items():
            if 'AETHER' not in p_name and 'AERIS' not in p_name:
                pdr = p_data['pdr_e2e']
                if pdr > best_pdr:
                    best_pdr = pdr
                    best_baseline = p_name

        if aeris_pdr and best_baseline:
            improvement_abs = (aeris_pdr - best_pdr) * 100  # 绝对提升（百分点）
            improvement_rel = ((aeris_pdr / best_pdr - 1) * 100) if best_pdr > 0 else 0  # 相对提升（%）

            # 推断节点数
            nodes = '54' if 'intel' in topo_name.lower() else ('1024' if 'uniform' in topo_name else '50')

            print(f"| {topo_name:20s} | {nodes:5s} | {aeris_pdr*100:6.2f}% | {best_baseline:13s} | {best_pdr*100:6.2f}% | {improvement_abs:+6.2f}pp ({improvement_rel:+.1f}%) |")

    # 表格2: 详细对比（uniform拓扑）
    if 'uniform_50x200' in results:
        print("\n## Table: Detailed Comparison on Uniform Topology (1024 nodes, 200 rounds)\n")
        print("| Protocol | PDR (end-to-end) | Energy (J) | Network Lifetime |")
        print("|----------|------------------|------------|------------------|")

        for protocol, metrics in results['uniform_50x200'].items():
            pdr = metrics['pdr_e2e']
            energy = metrics.get('energy', 'N/A')
            lifetime = metrics.get('lifetime', 'N/A')

            # 格式化能量
            if isinstance(energy, (int, float)):
                energy_str = f"{energy:.2f}"
            else:
                energy_str = str(energy)

            print(f"| {protocol:20s} | {pdr*100:6.2f}% | {energy_str:10s} | {lifetime:16s} |")

    # 表格3: Intel Lab真实数据
    if 'intel_lab' in results:
        print("\n## Table: Intel Lab Real Dataset (54 nodes, 200 rounds)\n")
        print("| Protocol | PDR (end-to-end) | Energy (J) | Notes |")
        print("|----------|------------------|------------|-------|")

        for protocol, metrics in results['intel_lab'].items():
            pdr = metrics['pdr_e2e']
            energy = metrics.get('energy', 'N/A')

            # 标注可疑数据
            notes = ""
            if pdr >= 0.99:
                notes = "⚠️ Suspiciously high"

            print(f"| {protocol:20s} | {pdr*100:6.2f}% | {energy:10.2f} | {notes:20s} |")

if __name__ == '__main__':
    print("AERIS项目 - PDR数据提取与分析")
    print("=" * 80)

    # 切换到项目根目录
os.chdir('C:/AERIS-WSN-Protocol')

    # 提取数据
    results = extract_pdr_data()

    # 生成表格
    generate_comparison_table(results)

    # 保存结果到JSON
    output_file = 'results/pdr_analysis_summary.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n完整数据已保存到: {output_file}")
    print("\n建议: 使用上述表格更新论文Section 6 (Results)")
