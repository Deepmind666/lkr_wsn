#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AERIS决策时间基准测试

测量CAS、Skeleton、Gateway选择器的实际决策时间

作者: Claude
日期: 2025-10-19
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import numpy as np
import json
from typing import List, Dict

# 导入AERIS组件
from src.cas_selector import CASSelector
from src.skeleton_selector import SkeletonSelector
from src.gateway_selector import GatewaySelector


class MockNode:
    """模拟节点用于测试"""
    def __init__(self, node_id, x, y, energy=1.0, is_alive=True):
        self.id = node_id
        self.x = x
        self.y = y
        self.energy = energy
        self.initial_energy = 2.0
        self.is_alive = is_alive
        self.is_ch = False
        self.cluster_id = None


def benchmark_cas_selector(num_iterations=1000):
    """
    测试CAS选择器决策时间

    Args:
        num_iterations: 测试次数

    Returns:
        统计数据字典
    """
    print("=" * 80)
    print("测试 CAS 选择器")
    print("=" * 80)

    cas = CASSelector()
    timings = []

    for i in range(num_iterations):
        # 生成随机特征
        features = {
            'energy': np.random.uniform(0.5, 1.0),
            'link': np.random.uniform(0.6, 0.95),
            'dist_bs': np.random.uniform(0.0, 1.0),
            'radius': np.random.uniform(0.0, 0.8),
            'density': np.random.uniform(0.3, 0.9),
            'fairness': np.random.uniform(0.5, 1.0),
            'tail_max': np.random.uniform(0.0, 0.5)
        }

        # 计时
        start = time.perf_counter()
        mode, confidence, scores = cas.select_mode(features)
        elapsed = time.perf_counter() - start

        timings.append(elapsed * 1000)  # 转换为毫秒

    timings = np.array(timings)

    stats = {
        'mean': float(np.mean(timings)),
        'std': float(np.std(timings)),
        'median': float(np.median(timings)),
        'p95': float(np.percentile(timings, 95)),
        'p99': float(np.percentile(timings, 99)),
        'min': float(np.min(timings)),
        'max': float(np.max(timings))
    }

    print(f"\n迭代次数: {num_iterations}")
    print(f"平均时间: {stats['mean']:.4f} ms")
    print(f"标准差:   {stats['std']:.4f} ms")
    print(f"中位数:   {stats['median']:.4f} ms")
    print(f"95分位:   {stats['p95']:.4f} ms")
    print(f"99分位:   {stats['p99']:.4f} ms")
    print(f"最小值:   {stats['min']:.4f} ms")
    print(f"最大值:   {stats['max']:.4f} ms")

    return stats


def benchmark_skeleton_selector(num_iterations=500):
    """
    测试Skeleton选择器决策时间

    不同CH数量下的性能
    """
    print("\n" + "=" * 80)
    print("测试 Skeleton 选择器")
    print("=" * 80)

    from src.skeleton_selector import SkeletonConfig
    cfg = SkeletonConfig(k=2)
    skeleton = SkeletonSelector(cfg)
    results = {}

    # 测试不同的CH数量
    ch_counts = [5, 10, 15, 20, 30]

    for num_chs in ch_counts:
        # 动态调整k值以适应不同的CH数量
        cfg = SkeletonConfig(k=min(2, num_chs))
        skeleton = SkeletonSelector(cfg)

        # 生成模拟CH节点
        chs = [
            MockNode(
                node_id=i,
                x=np.random.uniform(0, 100),
                y=np.random.uniform(0, 100),
                energy=np.random.uniform(0.5, 1.5)
            )
            for i in range(num_chs)
        ]

        for ch in chs:
            ch.is_ch = True

        timings = []

        for i in range(num_iterations):
            start = time.perf_counter()
            backbone = skeleton.select_backbone(
                chs=chs,
                bs_pos=(50, 200)
            )
            elapsed = time.perf_counter() - start
            timings.append(elapsed * 1000)

        timings = np.array(timings)

        stats = {
            'num_chs': num_chs,
            'mean': float(np.mean(timings)),
            'std': float(np.std(timings)),
            'p95': float(np.percentile(timings, 95)),
            'max': float(np.max(timings))
        }

        results[f'chs_{num_chs}'] = stats

        print(f"\nCH数量: {num_chs}")
        print(f"  平均时间: {stats['mean']:.4f} ms")
        print(f"  标准差:   {stats['std']:.4f} ms")
        print(f"  95分位:   {stats['p95']:.4f} ms")
        print(f"  最大值:   {stats['max']:.4f} ms")

    return results


def benchmark_gateway_selector(num_iterations=500):
    """
    测试Gateway选择器决策时间
    """
    print("\n" + "=" * 80)
    print("测试 Gateway 选择器")
    print("=" * 80)

    from src.gateway_selector import GatewayConfig
    cfg = GatewayConfig(k=2)
    gateway = GatewaySelector(cfg)
    results = {}

    ch_counts = [5, 10, 15, 20, 30]

    for num_chs in ch_counts:
        # 动态调整k值以适应不同的CH数量
        cfg = GatewayConfig(k=min(2, num_chs))
        gateway = GatewaySelector(cfg)

        chs = [
            MockNode(
                node_id=i,
                x=np.random.uniform(0, 100),
                y=np.random.uniform(0, 100),
                energy=np.random.uniform(0.5, 1.5)
            )
            for i in range(num_chs)
        ]

        for ch in chs:
            ch.is_ch = True

        timings = []

        for i in range(num_iterations):
            start = time.perf_counter()
            gateways = gateway.select_gateways(
                chs=chs,
                bs_pos=(50, 200)
            )
            elapsed = time.perf_counter() - start
            timings.append(elapsed * 1000)

        timings = np.array(timings)

        stats = {
            'num_chs': num_chs,
            'mean': float(np.mean(timings)),
            'std': float(np.std(timings)),
            'p95': float(np.percentile(timings, 95)),
            'max': float(np.max(timings))
        }

        results[f'chs_{num_chs}'] = stats

        print(f"\nCH数量: {num_chs}")
        print(f"  平均时间: {stats['mean']:.4f} ms")
        print(f"  标准差:   {stats['std']:.4f} ms")
        print(f"  95分位:   {stats['p95']:.4f} ms")
        print(f"  最大值:   {stats['max']:.4f} ms")

    return results


def benchmark_complete_round():
    """
    测试完整一轮的决策时间 (CAS + Skeleton + Gateway)
    """
    print("\n" + "=" * 80)
    print("测试完整轮次决策时间")
    print("=" * 80)

    from src.skeleton_selector import SkeletonConfig
    from src.gateway_selector import GatewayConfig

    cas = CASSelector()
    skeleton_cfg = SkeletonConfig(k=2)
    skeleton = SkeletonSelector(skeleton_cfg)
    gateway_cfg = GatewayConfig(k=2)
    gateway = GatewaySelector(gateway_cfg)

    num_iterations = 200
    timings = {
        'cas': [],
        'skeleton': [],
        'gateway': [],
        'total': []
    }

    for i in range(num_iterations):
        # 1. CAS决策
        features = {
            'energy': np.random.uniform(0.5, 1.0),
            'link': np.random.uniform(0.6, 0.95),
            'dist_bs': np.random.uniform(0.0, 1.0),
            'radius': np.random.uniform(0.0, 0.8),
            'density': np.random.uniform(0.3, 0.9),
            'fairness': np.random.uniform(0.5, 1.0),
            'tail_max': np.random.uniform(0.0, 0.5)
        }

        start_total = time.perf_counter()

        start = time.perf_counter()
        mode, conf, scores = cas.select_mode(features)
        t_cas = (time.perf_counter() - start) * 1000

        # 2. Skeleton选择 (假设15个CH)
        chs = [MockNode(j, np.random.uniform(0,100), np.random.uniform(0,100))
               for j in range(15)]
        for ch in chs:
            ch.is_ch = True

        start = time.perf_counter()
        backbone = skeleton.select_backbone(chs, bs_pos=(50, 200))
        t_skeleton = (time.perf_counter() - start) * 1000

        # 3. Gateway选择
        start = time.perf_counter()
        gateways = gateway.select_gateways(chs, bs_pos=(50, 200))
        t_gateway = (time.perf_counter() - start) * 1000

        t_total = (time.perf_counter() - start_total) * 1000

        timings['cas'].append(t_cas)
        timings['skeleton'].append(t_skeleton)
        timings['gateway'].append(t_gateway)
        timings['total'].append(t_total)

    print(f"\n迭代次数: {num_iterations}")
    print(f"\nCAS决策:")
    print(f"  平均: {np.mean(timings['cas']):.4f} ms")
    print(f"  95%:  {np.percentile(timings['cas'], 95):.4f} ms")

    print(f"\nSkeleton选择:")
    print(f"  平均: {np.mean(timings['skeleton']):.4f} ms")
    print(f"  95%:  {np.percentile(timings['skeleton'], 95):.4f} ms")

    print(f"\nGateway选择:")
    print(f"  平均: {np.mean(timings['gateway']):.4f} ms")
    print(f"  95%:  {np.percentile(timings['gateway'], 95):.4f} ms")

    print(f"\n总决策时间:")
    print(f"  平均: {np.mean(timings['total']):.4f} ms")
    print(f"  95%:  {np.percentile(timings['total'], 95):.4f} ms")
    print(f"  99%:  {np.percentile(timings['total'], 99):.4f} ms")
    print(f"  最大: {np.max(timings['total']):.4f} ms")

    return {
        k: {
            'mean': float(np.mean(v)),
            'p95': float(np.percentile(v, 95)),
            'p99': float(np.percentile(v, 99)),
            'max': float(np.max(v))
        }
        for k, v in timings.items()
    }


if __name__ == '__main__':
    print("AERIS 决策时间基准测试")
    print("=" * 80)
    print(f"Python: {sys.version}")
    print(f"NumPy: {np.__version__}")
    print("=" * 80)

    # 运行所有基准测试
    results = {}

    results['cas'] = benchmark_cas_selector(num_iterations=1000)
    results['skeleton'] = benchmark_skeleton_selector(num_iterations=500)
    results['gateway'] = benchmark_gateway_selector(num_iterations=500)
    results['complete_round'] = benchmark_complete_round()

    # 保存结果
    output_file = 'results/benchmark_decision_time.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("测试完成！")
    print(f"结果已保存到: {output_file}")
    print("=" * 80)

    # 打印论文可用的关键数据
    print("\n" + "=" * 80)
    print("论文引用数据摘要")
    print("=" * 80)
    print(f"\nAERIS总决策时间 (完整轮次):")
    print(f"  平均: {results['complete_round']['total']['mean']:.2f} ms")
    print(f"  95分位: {results['complete_round']['total']['p95']:.2f} ms")
    print(f"  99分位: {results['complete_round']['total']['p99']:.2f} ms")

    print(f"\n组件分解:")
    print(f"  CAS:      {results['complete_round']['cas']['mean']:.3f} ms ({results['complete_round']['cas']['mean']/results['complete_round']['total']['mean']*100:.1f}%)")
    print(f"  Skeleton: {results['complete_round']['skeleton']['mean']:.3f} ms ({results['complete_round']['skeleton']['mean']/results['complete_round']['total']['mean']*100:.1f}%)")
    print(f"  Gateway:  {results['complete_round']['gateway']['mean']:.3f} ms ({results['complete_round']['gateway']['mean']/results['complete_round']['total']['mean']*100:.1f}%)")

    print(f"\n建议论文表述:")
    print(f'"AERIS achieves <{results["complete_round"]["total"]["p95"]:.0f}ms decision latency per round"')
    print(f'"with deterministic O(n²) complexity, {int(600/results["complete_round"]["total"]["mean"])}× faster than GRU-based MeFi (600ms)."')
