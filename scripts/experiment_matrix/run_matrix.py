#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展实验矩阵执行器

覆盖场景×规模×负载的完整实验矩阵
支持并行执行和结果聚合

输出：
- results/experiment_matrix/
"""

import sys
import os
import json
import time
import argparse
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import traceback

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


@dataclass
class ExperimentConfig:
    """实验配置"""
    scenario: str
    scale: int
    load: str
    seed: int
    rounds: int = 200


@dataclass
class ExperimentResult:
    """实验结果"""
    config: Dict
    protocol: str
    pdr: float
    energy_total: float
    energy_per_packet: float
    network_lifetime: int
    execution_time: float
    error: Optional[str] = None


# 实验矩阵定义
SCENARIOS = ['uniform', 'corridor', 'cluster']
SCALES = [50, 100]  # 先用小规模测试
LOADS = ['low', 'medium', 'high']
PROTOCOLS = ['AERIS', 'LEACH', 'HEED']

# 负载配置
LOAD_CONFIGS = {
    'low': {'rounds': 100, 'packet_size': 512},
    'medium': {'rounds': 200, 'packet_size': 1024},
    'high': {'rounds': 300, 'packet_size': 2048},
}


def generate_topology(scenario: str, num_nodes: int, width: float, height: float,
                     seed: int) -> List[Tuple[float, float]]:
    """生成拓扑"""
    rng = np.random.default_rng(seed)
    
    if scenario == 'uniform':
        positions = [(rng.uniform(0, width), rng.uniform(0, height)) 
                    for _ in range(num_nodes)]
    
    elif scenario == 'corridor':
        # 走廊拓扑：4:1长宽比
        corridor_width = width
        corridor_height = height / 4
        positions = [(rng.uniform(0, corridor_width), 
                     rng.uniform(0, corridor_height)) 
                    for _ in range(num_nodes)]
    
    elif scenario == 'cluster':
        # 簇状拓扑：3-5个簇
        n_clusters = rng.integers(3, 6)
        cluster_centers = [(rng.uniform(width*0.2, width*0.8),
                          rng.uniform(height*0.2, height*0.8))
                         for _ in range(n_clusters)]
        
        positions = []
        for i in range(num_nodes):
            center = cluster_centers[i % n_clusters]
            offset = rng.normal(0, width/10, 2)
            x = np.clip(center[0] + offset[0], 0, width)
            y = np.clip(center[1] + offset[1], 0, height)
            positions.append((float(x), float(y)))
    
    else:
        # 默认uniform
        positions = [(rng.uniform(0, width), rng.uniform(0, height)) 
                    for _ in range(num_nodes)]
    
    return positions


def run_single_experiment(config: ExperimentConfig, protocol_name: str) -> ExperimentResult:
    """运行单个实验"""
    start_time = time.time()
    
    try:
        # 延迟导入以支持多进程
        from benchmark_protocols import NetworkConfig, LEACHProtocol, HEEDProtocolWrapper
        from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
        from aeris_protocol import AerisProtocol
        
        # 配置
        load_cfg = LOAD_CONFIGS[config.load]
        width = 100.0
        height = 100.0 if config.scenario != 'corridor' else 25.0
        
        net_cfg = NetworkConfig(
            num_nodes=config.scale,
            area_width=width,
            area_height=height,
            initial_energy=2.0,
            packet_size=load_cfg['packet_size']
        )
        
        # 生成拓扑
        positions = generate_topology(config.scenario, config.scale, width, height, config.seed)
        net_cfg.positions = positions
        
        # 能量模型
        em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        
        # 运行协议
        rounds = load_cfg['rounds']
        
        if protocol_name == 'AERIS':
            proto = AerisProtocol(net_cfg, enable_cas=True, enable_fairness=True)
            result = proto.run_simulation(rounds)
        elif protocol_name == 'LEACH':
            proto = LEACHProtocol(net_cfg, em)
            result = proto.run_simulation(rounds)
        elif protocol_name == 'HEED':
            proto = HEEDProtocolWrapper(net_cfg, em)
            result = proto.run_simulation(rounds)
        else:
            raise ValueError(f"Unknown protocol: {protocol_name}")
        
        execution_time = time.time() - start_time
        
        # 提取结果
        pdr = result.get('packet_delivery_ratio', 0)
        energy_total = result.get('total_energy_consumed', 0)
        lifetime = result.get('network_lifetime', rounds)
        
        # 计算每包能耗
        delivered = result.get('total_packets_delivered', 1)
        energy_per_packet = energy_total / delivered if delivered > 0 else float('inf')
        
        return ExperimentResult(
            config=asdict(config),
            protocol=protocol_name,
            pdr=float(pdr),
            energy_total=float(energy_total),
            energy_per_packet=float(energy_per_packet),
            network_lifetime=int(lifetime),
            execution_time=float(execution_time)
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        return ExperimentResult(
            config=asdict(config),
            protocol=protocol_name,
            pdr=0,
            energy_total=0,
            energy_per_packet=0,
            network_lifetime=0,
            execution_time=float(execution_time),
            error=str(e)
        )


def run_experiment_cell(args: Tuple) -> ExperimentResult:
    """包装函数用于多进程"""
    config, protocol = args
    return run_single_experiment(config, protocol)


class ExperimentMatrix:
    """实验矩阵管理器"""
    
    def __init__(self, n_seeds: int = 5, n_workers: int = 4):
        self.n_seeds = n_seeds
        self.n_workers = n_workers
        self.results = []
    
    def generate_configs(self) -> List[Tuple[ExperimentConfig, str]]:
        """生成所有实验配置"""
        configs = []
        
        for scenario in SCENARIOS:
            for scale in SCALES:
                for load in LOADS:
                    for seed in range(self.n_seeds):
                        config = ExperimentConfig(
                            scenario=scenario,
                            scale=scale,
                            load=load,
                            seed=seed
                        )
                        for protocol in PROTOCOLS:
                            configs.append((config, protocol))
        
        return configs
    
    def run_matrix(self, output_dir: str) -> None:
        """运行完整实验矩阵"""
        configs = self.generate_configs()
        total = len(configs)
        
        print(f"实验矩阵: {len(SCENARIOS)} scenarios × {len(SCALES)} scales × "
              f"{len(LOADS)} loads × {self.n_seeds} seeds × {len(PROTOCOLS)} protocols = {total} experiments")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 并行执行
        completed = 0
        start_time = time.time()
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            futures = {executor.submit(run_experiment_cell, cfg): cfg for cfg in configs}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    self.results.append(result)
                    completed += 1
                    
                    # 进度报告
                    elapsed = time.time() - start_time
                    eta = (elapsed / completed) * (total - completed) if completed > 0 else 0
                    
                    status = "✓" if result.error is None else "✗"
                    print(f"[{completed}/{total}] {status} {result.protocol} "
                          f"{result.config['scenario']}/{result.config['scale']}/{result.config['load']} "
                          f"seed={result.config['seed']} PDR={result.pdr:.3f} "
                          f"(ETA: {eta/60:.1f}min)")
                    
                except Exception as e:
                    print(f"Error: {e}")
                    completed += 1
        
        # 保存结果
        self._save_results(output_path)
    
    def _save_results(self, output_path: Path) -> None:
        """保存结果"""
        # 保存原始结果
        raw_results = [asdict(r) for r in self.results]
        with open(output_path / 'raw_results.json', 'w') as f:
            json.dump(raw_results, f, indent=2)
        
        # 聚合结果
        aggregated = self._aggregate_results()
        with open(output_path / 'aggregated_results.json', 'w') as f:
            json.dump(aggregated, f, indent=2)
        
        print(f"\n结果已保存至: {output_path}")
    
    def _aggregate_results(self) -> Dict:
        """聚合结果"""
        aggregated = {}
        
        # 按scenario/scale/load/protocol分组
        for result in self.results:
            if result.error is not None:
                continue
            
            key = (result.config['scenario'], result.config['scale'], 
                   result.config['load'], result.protocol)
            
            if key not in aggregated:
                aggregated[key] = {
                    'pdrs': [],
                    'energies': [],
                    'lifetimes': []
                }
            
            aggregated[key]['pdrs'].append(result.pdr)
            aggregated[key]['energies'].append(result.energy_total)
            aggregated[key]['lifetimes'].append(result.network_lifetime)
        
        # 计算统计量
        summary = {}
        for key, data in aggregated.items():
            scenario, scale, load, protocol = key
            
            if scenario not in summary:
                summary[scenario] = {}
            if scale not in summary[scenario]:
                summary[scenario][scale] = {}
            if load not in summary[scenario][scale]:
                summary[scenario][scale][load] = {}
            
            pdrs = np.array(data['pdrs'])
            energies = np.array(data['energies'])
            
            summary[scenario][scale][load][protocol] = {
                'pdr_mean': float(np.mean(pdrs)),
                'pdr_std': float(np.std(pdrs)),
                'pdr_min': float(np.min(pdrs)),
                'pdr_max': float(np.max(pdrs)),
                'energy_mean': float(np.mean(energies)),
                'energy_std': float(np.std(energies)),
                'n_samples': len(pdrs)
            }
        
        return summary


def main():
    parser = argparse.ArgumentParser(description='Run experiment matrix')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--seeds', type=int, default=5, help='Number of seeds per config')
    parser.add_argument('--output', type=str, default='results/experiment_matrix',
                       help='Output directory')
    args = parser.parse_args()
    
    print("=" * 60)
    print("扩展实验矩阵执行")
    print("=" * 60)
    print(f"Workers: {args.workers}")
    print(f"Seeds: {args.seeds}")
    print(f"Output: {args.output}")
    
    matrix = ExperimentMatrix(n_seeds=args.seeds, n_workers=args.workers)
    matrix.run_matrix(args.output)
    
    print("\n实验矩阵执行完成!")


if __name__ == '__main__':
    main()
