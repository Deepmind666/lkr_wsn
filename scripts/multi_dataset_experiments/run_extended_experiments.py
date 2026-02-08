#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展多场景实验运行器

基于现有实验框架，扩展到更多场景和配置：
1. 多种网络规模 (30-500节点)
2. 多种拓扑结构 (uniform/corridor/cluster/grid)
3. 多种信道条件 (ideal/indoor/outdoor/industrial)
4. 多种能量配置
5. 长期运行测试

使用CPU多核并行加速
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
import multiprocessing as mp

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

# 结果目录
RESULTS_DIR = Path('results/extended_experiments')
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ExtendedConfig:
    """扩展实验配置"""
    experiment_id: str
    experiment_type: str  # scale/topology/channel/energy/longevity
    scenario: str
    n_nodes: int
    area_width: float
    area_height: float
    rounds: int
    seed: int
    channel_params: Optional[Dict] = None
    initial_energy: float = 2.0
    packet_size: int = 1024


@dataclass
class ExtendedResult:
    """扩展实验结果"""
    config: Dict
    protocol: str
    pdr: float
    energy_total: float
    network_lifetime: int
    alive_nodes: int
    execution_time: float
    error: Optional[str] = None


def generate_topology(scenario: str, n_nodes: int, width: float, height: float, seed: int) -> np.ndarray:
    """生成拓扑"""
    rng = np.random.default_rng(seed)
    
    if scenario == 'uniform' or scenario == 'random':
        positions = np.column_stack([
            rng.uniform(5, width-5, n_nodes),
            rng.uniform(5, height-5, n_nodes)
        ])
    
    elif scenario == 'grid':
        side = int(np.ceil(np.sqrt(n_nodes)))
        x = np.linspace(5, width-5, side)
        y = np.linspace(5, height-5, side)
        xx, yy = np.meshgrid(x, y)
        positions = np.column_stack([xx.ravel(), yy.ravel()])[:n_nodes]
    
    elif scenario == 'corridor':
        positions = np.column_stack([
            rng.uniform(5, width-5, n_nodes),
            rng.uniform(5, height-5, n_nodes)
        ])
    
    elif scenario.startswith('cluster'):
        n_clusters = int(scenario.split('_')[1]) if '_' in scenario else 4
        cluster_centers = rng.uniform(20, min(width, height)-20, (n_clusters, 2))
        positions = []
        per_cluster = n_nodes // n_clusters
        for i, center in enumerate(cluster_centers):
            n_in_cluster = per_cluster if i < n_clusters - 1 else n_nodes - len(positions)
            cluster_pos = center + rng.normal(0, 10, (n_in_cluster, 2))
            cluster_pos[:, 0] = np.clip(cluster_pos[:, 0], 5, width-5)
            cluster_pos[:, 1] = np.clip(cluster_pos[:, 1], 5, height-5)
            positions.extend(cluster_pos)
        positions = np.array(positions)[:n_nodes]
    
    else:
        positions = np.column_stack([
            rng.uniform(5, width-5, n_nodes),
            rng.uniform(5, height-5, n_nodes)
        ])
    
    return positions


def run_single_experiment(config: ExtendedConfig, protocol_name: str) -> ExtendedResult:
    """运行单个实验"""
    start_time = time.time()
    
    try:
        from benchmark_protocols import NetworkConfig, LEACHProtocol, HEEDProtocolWrapper
        from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
        from aeris_protocol import AerisProtocol
        
        # 网络配置
        net_cfg = NetworkConfig(
            num_nodes=config.n_nodes,
            area_width=config.area_width,
            area_height=config.area_height,
            initial_energy=config.initial_energy,
            packet_size=config.packet_size
        )
        
        # 生成拓扑
        positions = generate_topology(
            config.scenario, config.n_nodes, 
            config.area_width, config.area_height, config.seed
        )
        net_cfg.positions = [(float(p[0]), float(p[1])) for p in positions]
        
        # 信道参数
        if config.channel_params:
            net_cfg.enable_channel = True
            for k, v in config.channel_params.items():
                setattr(net_cfg, k, v)
        
        # 能量模型
        em = ImprovedEnergyModel(HardwarePlatform.CC2420_TELOSB)
        
        # 运行协议
        if protocol_name == 'AERIS':
            proto = AerisProtocol(net_cfg, enable_cas=True, enable_fairness=True)
        elif protocol_name == 'LEACH':
            proto = LEACHProtocol(net_cfg, em)
        elif protocol_name == 'HEED':
            proto = HEEDProtocolWrapper(net_cfg, em)
        elif protocol_name == 'PEGASIS':
            from benchmark_protocols import PEGASISProtocol
            proto = PEGASISProtocol(net_cfg, em)
        else:
            raise ValueError(f"Unknown protocol: {protocol_name}")
        
        result = proto.run_simulation(config.rounds)
        
        execution_time = time.time() - start_time
        
        return ExtendedResult(
            config=asdict(config),
            protocol=protocol_name,
            pdr=float(result.get('packet_delivery_ratio', result.get('pdr_end2end', 0))),
            energy_total=float(result.get('total_energy_consumed', result.get('total_energy', 0))),
            network_lifetime=int(result.get('network_lifetime', config.rounds)),
            alive_nodes=int(result.get('alive_nodes', config.n_nodes)),
            execution_time=float(execution_time)
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        return ExtendedResult(
            config=asdict(config),
            protocol=protocol_name,
            pdr=0,
            energy_total=0,
            network_lifetime=0,
            alive_nodes=0,
            execution_time=float(execution_time),
            error=f"{type(e).__name__}: {str(e)}"
        )


def run_experiment_wrapper(args: Tuple) -> ExtendedResult:
    """多进程包装函数"""
    config, protocol = args
    return run_single_experiment(config, protocol)


class ExtendedExperimentRunner:
    """扩展实验运行器"""
    
    def __init__(self, n_workers: int = None, n_repeats: int = 50):
        self.n_workers = n_workers or max(1, mp.cpu_count() - 2)
        self.n_repeats = n_repeats
        self.results = []
        
        print(f"配置: {self.n_workers} workers, {self.n_repeats} repeats/config")
    
    def generate_all_configs(self) -> List[Tuple[ExtendedConfig, str]]:
        """生成所有实验配置"""
        configs = []
        protocols = ['AERIS', 'LEACH', 'HEED']
        
        exp_id = 0
        
        # ========================================
        # 1. 规模实验 (Scale)
        # ========================================
        print("生成规模实验配置...")
        for n_nodes in [30, 50, 75, 100, 150, 200, 300]:
            area_size = max(50, int(np.sqrt(n_nodes) * 12))
            for protocol in protocols:
                for seed in range(self.n_repeats):
                    config = ExtendedConfig(
                        experiment_id=f"scale_{exp_id}",
                        experiment_type='scale',
                        scenario='uniform',
                        n_nodes=n_nodes,
                        area_width=float(area_size),
                        area_height=float(area_size),
                        rounds=200,
                        seed=seed
                    )
                    configs.append((config, protocol))
                    exp_id += 1
        
        # ========================================
        # 2. 拓扑实验 (Topology)
        # ========================================
        print("生成拓扑实验配置...")
        topologies = [
            ('uniform', 100, 100),
            ('grid', 100, 100),
            ('corridor', 200, 40),
            ('cluster_4', 100, 100),
            ('cluster_8', 120, 120),
        ]
        
        for topo, w, h in topologies:
            for protocol in protocols:
                for seed in range(self.n_repeats):
                    config = ExtendedConfig(
                        experiment_id=f"topo_{exp_id}",
                        experiment_type='topology',
                        scenario=topo,
                        n_nodes=100,
                        area_width=float(w),
                        area_height=float(h),
                        rounds=200,
                        seed=seed
                    )
                    configs.append((config, protocol))
                    exp_id += 1
        
        # ========================================
        # 3. 信道实验 (Channel)
        # ========================================
        print("生成信道实验配置...")
        channels = [
            ('ideal', {'path_loss_exp': 2.0, 'shadowing_std': 2.0}),
            ('indoor_good', {'path_loss_exp': 2.5, 'shadowing_std': 4.0}),
            ('indoor_typical', {'path_loss_exp': 3.0, 'shadowing_std': 6.0}),
            ('indoor_harsh', {'path_loss_exp': 3.5, 'shadowing_std': 8.0}),
            ('industrial', {'path_loss_exp': 4.0, 'shadowing_std': 10.0}),
        ]
        
        for ch_name, ch_params in channels:
            for protocol in protocols:
                for seed in range(self.n_repeats):
                    config = ExtendedConfig(
                        experiment_id=f"channel_{exp_id}",
                        experiment_type='channel',
                        scenario='uniform',
                        n_nodes=100,
                        area_width=100.0,
                        area_height=100.0,
                        rounds=200,
                        seed=seed,
                        channel_params=ch_params
                    )
                    configs.append((config, protocol))
                    exp_id += 1
        
        # ========================================
        # 4. 能量实验 (Energy)
        # ========================================
        print("生成能量实验配置...")
        energy_levels = [1.0, 1.5, 2.0, 3.0, 5.0]
        
        for energy in energy_levels:
            for protocol in protocols:
                for seed in range(self.n_repeats):
                    config = ExtendedConfig(
                        experiment_id=f"energy_{exp_id}",
                        experiment_type='energy',
                        scenario='uniform',
                        n_nodes=100,
                        area_width=100.0,
                        area_height=100.0,
                        rounds=300,
                        seed=seed,
                        initial_energy=energy
                    )
                    configs.append((config, protocol))
                    exp_id += 1
        
        # ========================================
        # 5. 长期实验 (Longevity)
        # ========================================
        print("生成长期实验配置...")
        for max_rounds in [500, 1000]:
            for protocol in protocols:
                for seed in range(self.n_repeats // 2):  # 减少重复次数
                    config = ExtendedConfig(
                        experiment_id=f"long_{exp_id}",
                        experiment_type='longevity',
                        scenario='uniform',
                        n_nodes=100,
                        area_width=100.0,
                        area_height=100.0,
                        rounds=max_rounds,
                        seed=seed
                    )
                    configs.append((config, protocol))
                    exp_id += 1
        
        print(f"总计: {len(configs)} 个实验配置")
        return configs
    
    def run_all(self) -> Dict:
        """运行所有实验"""
        configs = self.generate_all_configs()
        total = len(configs)
        
        print(f"\n开始运行 {total} 个实验...")
        print(f"预计时间: {total * 0.5 / self.n_workers / 60:.1f} 分钟")
        
        start_time = time.time()
        completed = 0
        errors = 0
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            futures = {executor.submit(run_experiment_wrapper, cfg): cfg for cfg in configs}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    self.results.append(result)
                    completed += 1
                    
                    if result.error:
                        errors += 1
                    
                    # 进度报告
                    if completed % 100 == 0 or completed == total:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed
                        eta = (total - completed) / rate if rate > 0 else 0
                        print(f"  进度: {completed}/{total} ({100*completed/total:.1f}%) "
                              f"- {rate:.1f} exp/s - 错误: {errors} - ETA: {eta/60:.1f}min")
                        
                except Exception as e:
                    print(f"  Future error: {e}")
                    completed += 1
                    errors += 1
        
        elapsed = time.time() - start_time
        print(f"\n完成: {elapsed/60:.1f}分钟, {len(self.results)/elapsed:.1f} exp/s")
        print(f"成功: {len(self.results) - errors}, 错误: {errors}")
        
        return self._analyze_results()
    
    def _analyze_results(self) -> Dict:
        """分析结果"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'total_experiments': len(self.results),
            'successful': sum(1 for r in self.results if r.error is None),
            'by_type': {},
            'by_protocol': {},
            'summary': {}
        }
        
        # 按实验类型和协议分组
        for r in self.results:
            if r.error:
                continue
            
            exp_type = r.config.get('experiment_type', 'unknown')
            protocol = r.protocol
            
            # 按类型
            if exp_type not in analysis['by_type']:
                analysis['by_type'][exp_type] = {}
            if protocol not in analysis['by_type'][exp_type]:
                analysis['by_type'][exp_type][protocol] = {'pdr': [], 'energy': [], 'lifetime': []}
            
            analysis['by_type'][exp_type][protocol]['pdr'].append(r.pdr)
            analysis['by_type'][exp_type][protocol]['energy'].append(r.energy_total)
            analysis['by_type'][exp_type][protocol]['lifetime'].append(r.network_lifetime)
            
            # 按协议
            if protocol not in analysis['by_protocol']:
                analysis['by_protocol'][protocol] = {'pdr': [], 'energy': [], 'lifetime': []}
            analysis['by_protocol'][protocol]['pdr'].append(r.pdr)
            analysis['by_protocol'][protocol]['energy'].append(r.energy_total)
            analysis['by_protocol'][protocol]['lifetime'].append(r.network_lifetime)
        
        # 计算汇总统计
        for protocol, data in analysis['by_protocol'].items():
            if len(data['pdr']) > 0:
                analysis['summary'][protocol] = {
                    'pdr_mean': float(np.mean(data['pdr'])),
                    'pdr_std': float(np.std(data['pdr'])),
                    'pdr_median': float(np.median(data['pdr'])),
                    'energy_mean': float(np.mean(data['energy'])),
                    'energy_std': float(np.std(data['energy'])),
                    'lifetime_mean': float(np.mean(data['lifetime'])),
                    'n_samples': len(data['pdr'])
                }
        
        return analysis
    
    def save_results(self, output_dir: Path = RESULTS_DIR):
        """保存结果"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存原始结果
        raw_results = [asdict(r) for r in self.results]
        with open(output_dir / 'raw_results.json', 'w') as f:
            json.dump(raw_results, f, indent=2)
        
        # 保存分析结果
        analysis = self._analyze_results()
        with open(output_dir / 'analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"结果保存至: {output_dir}")
        return analysis


def main():
    parser = argparse.ArgumentParser(description='Extended multi-scenario experiments')
    parser.add_argument('--workers', type=int, default=None, help='Number of parallel workers')
    parser.add_argument('--repeats', type=int, default=50, help='Repeats per configuration')
    parser.add_argument('--output', type=str, default='results/extended_experiments', help='Output directory')
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔬 扩展多场景实验")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    runner = ExtendedExperimentRunner(n_workers=args.workers, n_repeats=args.repeats)
    analysis = runner.run_all()
    runner.save_results(Path(args.output))
    
    # 打印汇总
    print("\n" + "=" * 70)
    print("📊 实验汇总")
    print("=" * 70)
    
    print("\n协议性能对比:")
    print("-" * 60)
    for protocol, stats in analysis['summary'].items():
        print(f"{protocol:10s}: PDR={stats['pdr_mean']:.3f}±{stats['pdr_std']:.3f}, "
              f"Energy={stats['energy_mean']:.1f}±{stats['energy_std']:.1f}J, "
              f"n={stats['n_samples']}")
    
    print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
