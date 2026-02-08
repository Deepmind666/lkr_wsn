#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSN协议综合基准测试框架

基于严谨的实验设计，对比分析多种WSN路由协议:
- LEACH (Low-Energy Adaptive Clustering Hierarchy)
- PEGASIS (Power-Efficient Gathering in Sensor Information Systems)
- AERIS (Environment-aware Enhanced Energy-Efficient Hybrid Fuzzy Routing)

实验特点:
- 统一的网络配置和能耗模�?- 多次重复实验确保统计可靠�?- 详细的性能指标分析
- 符合SCI期刊标准的实验方�?
作�? AERIS Research Team
日期: 2025-01-30
版本: 1.0 (综合基准测试)
"""

import numpy as np
import json
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import statistics
import os

from benchmark_protocols import LEACHProtocol, PEGASISProtocol, NetworkConfig
from improved_energy_model import ImprovedEnergyModel, HardwarePlatform
from aeris_protocol import AerisProtocol

@dataclass
class ExperimentConfig:
    """实验配置参数"""
    # 网络参数
    node_counts: List[int]
    area_sizes: List[Tuple[int, int]]
    initial_energies: List[float]
    
    # 仿真参数
    max_rounds: int
    repeat_times: int  # 每组实验重复次数
    
    # 硬件平台
    hardware_platform: HardwarePlatform
    
    # 输出配置
    save_detailed_results: bool = True
    results_directory: str = "../results/benchmark_experiments"

@dataclass
class ExperimentResult:
    """单次实验结果"""
    protocol: str
    config: Dict
    network_lifetime: int
    total_energy_consumed: float
    final_alive_nodes: int
    energy_efficiency: float
    packet_delivery_ratio: float
    execution_time: float
    additional_metrics: Dict

class ComprehensiveBenchmark:
    """综合基准测试框架"""
    
    def __init__(self, experiment_config: ExperimentConfig):
        self.config = experiment_config
        self.results = []
        self.energy_model = ImprovedEnergyModel(experiment_config.hardware_platform)
        
        # 创建结果目录
        os.makedirs(experiment_config.results_directory, exist_ok=True)
    
    def run_single_experiment(self,
                            protocol_class,
                            network_config: NetworkConfig,
                            experiment_id: str) -> ExperimentResult:
        """运行单次实验"""

        start_time = time.time()

        # 🔧 修复随机性问题：为每次实验设置不同的随机种子
        import random
        import hashlib

        # Use experiment ID and current time to generate a unique random seed
        seed_string = f"{experiment_id}_{int(time.time() * 1000000)}"
        seed = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
        random.seed(seed)

        print(f"      [INFO] Experiment {experiment_id} uses random seed: {seed}")

        # 创建协议实例
        if protocol_class == AerisProtocol:
            # AERIS只需要network_config
            protocol = protocol_class(network_config)
        else:
            # LEACH和PEGASIS需要network_config和energy_model
            protocol = protocol_class(network_config, self.energy_model)
        
        # 运行仿真
        results = protocol.run_simulation(self.config.max_rounds)
        
        execution_time = time.time() - start_time
        
        # 提取额外指标
        additional_metrics = {}
        if hasattr(protocol, 'cluster_heads'):
            additional_metrics['average_cluster_heads'] = results.get('average_cluster_heads_per_round', 0)
        if hasattr(protocol, 'chain'):
            additional_metrics['average_chain_length'] = results.get('average_chain_length', 0)
        
        # 创建实验结果
        experiment_result = ExperimentResult(
            protocol=results['protocol'],
            config=results['config'],
            network_lifetime=results['network_lifetime'],
            total_energy_consumed=results['total_energy_consumed'],
            final_alive_nodes=results['final_alive_nodes'],
            energy_efficiency=results['energy_efficiency'],
            packet_delivery_ratio=results['packet_delivery_ratio'],
            execution_time=execution_time,
            additional_metrics=additional_metrics
        )
        
        return experiment_result
    
    def run_protocol_comparison(self, 
                              network_config: NetworkConfig,
                              config_name: str) -> Dict:
        """运行协议对比实验"""
        
        print(f"\n[INFO] Running config: {config_name}")
        print(f"   Nodes: {network_config.num_nodes}, "
              f"Area: {network_config.area_width}x{network_config.area_height}, "
              f"Initial energy: {network_config.initial_energy}J")
        
        protocols = [
            ('LEACH', LEACHProtocol),
            ('PEGASIS', PEGASISProtocol),
            ('AERIS', AerisProtocol),
        ]
        
        comparison_results = {}
        
        for protocol_name, protocol_class in protocols:
            print(f"   [TEST] Protocol {protocol_name}...")
            
            protocol_results = []
            
            # 重复实验
            for repeat in range(self.config.repeat_times):
                experiment_id = f"{config_name}_{protocol_name}_repeat_{repeat}"
                try:
                    result = self.run_single_experiment(
                        protocol_class, network_config, experiment_id
                    )
                    protocol_results.append(result)

                    if repeat == 0:
                        print(
                            f"      Lifetime: {result.network_lifetime} rounds, "
                            f"Energy: {result.total_energy_consumed:.3f}J, "
                            f"Efficiency: {result.energy_efficiency:.1f}"
                        )
                except Exception as e:
                    print(f"      [ERROR] Experiment failed: {e}")
                    continue
            
            if protocol_results:
                # 计算统计指标
                lifetimes = [r.network_lifetime for r in protocol_results]
                energy_consumptions = [r.total_energy_consumed for r in protocol_results]
                energy_efficiencies = [r.energy_efficiency for r in protocol_results]
                packet_delivery_ratios = [r.packet_delivery_ratio for r in protocol_results]
                
                comparison_results[protocol_name] = {
                    'raw_results': protocol_results,
                    'statistics': {
                        'network_lifetime': {
                            'mean': statistics.mean(lifetimes),
                            'std': statistics.stdev(lifetimes) if len(lifetimes) > 1 else 0,
                            'min': min(lifetimes),
                            'max': max(lifetimes),
                            'median': statistics.median(lifetimes)
                        },
                        'total_energy_consumed': {
                            'mean': statistics.mean(energy_consumptions),
                            'std': statistics.stdev(energy_consumptions) if len(energy_consumptions) > 1 else 0,
                            'min': min(energy_consumptions),
                            'max': max(energy_consumptions)
                        },
                        'energy_efficiency': {
                            'mean': statistics.mean(energy_efficiencies),
                            'std': statistics.stdev(energy_efficiencies) if len(energy_efficiencies) > 1 else 0
                        },
                        'packet_delivery_ratio': {
                            'mean': statistics.mean(packet_delivery_ratios),
                            'std': statistics.stdev(packet_delivery_ratios) if len(packet_delivery_ratios) > 1 else 0
                        }
                    }
                }
        
        return comparison_results
    
    def run_comprehensive_benchmark(self) -> Dict:
        """运行综合基准测试"""
        
        print(">>> Starting WSN protocol comprehensive benchmark")
        print("=" * 60)
        print(f"Hardware platform: {self.config.hardware_platform.value}")
        print(f"Repeat times: {self.config.repeat_times}")
        print(f"Max rounds: {self.config.max_rounds}")
        
        all_results = {}
        
        # Iterate all experiment configurations
        for node_count in self.config.node_counts:
            for area_size in self.config.area_sizes:
                for initial_energy in self.config.initial_energies:
                    
                    # 创建网络配置
                    network_config = NetworkConfig(
                        num_nodes=node_count,
                        area_width=area_size[0],
                        area_height=area_size[1],
                        initial_energy=initial_energy
                    )
                    
                    config_name = f"nodes_{node_count}_area_{area_size[0]}x{area_size[1]}_energy_{initial_energy}"
                    
                    # 运行协议对比
                    comparison_results = self.run_protocol_comparison(
                        network_config, config_name
                    )
                    
                    all_results[config_name] = comparison_results
        
        # 保存结果
        if self.config.save_detailed_results:
            self._save_results(all_results)
        
        return all_results
    
    def _save_results(self, results: Dict):
        """保存实验结果"""
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # --- 鲁棒路径修复 ---
        # 获取当前脚本所在的目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Build absolute project root from src
        project_root = os.path.abspath(os.path.join(script_dir, '..'))
        # Build absolute results directory
        results_dir_abs = os.path.join(project_root, 'results', 'benchmark_experiments')
        os.makedirs(results_dir_abs, exist_ok=True)
        
        # Save detailed results (JSON)
        detailed_file = os.path.join(
            results_dir_abs,
            f"detailed_results_{timestamp}.json"
        )
        
        # Convert to JSON-serializable structure
        serializable_results = {}
        for config_name, config_results in results.items():
            serializable_results[config_name] = {}
            for protocol_name, protocol_data in config_results.items():
                serializable_results[config_name][protocol_name] = {
                    'statistics': protocol_data['statistics'],
                    'raw_results': [asdict(r) for r in protocol_data['raw_results']]
                }

        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=True)

        print(f"\n[SAVE] Detailed results saved: {detailed_file}")

        # Save summary report (Markdown)
        summary_file = os.path.join(
            results_dir_abs,
            f"benchmark_summary_{timestamp}.md"
        )
        
        self._generate_summary_report(results, summary_file)
        print(f"[SAVE] Summary report saved: {summary_file}")
    
    def _generate_summary_report(self, results: Dict, output_file: str):
        """Generate a markdown summary report for the benchmark results."""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# WSN Protocol Benchmark Summary Report\n\n")
            f.write(f"**Test Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Hardware Platform**: {self.config.hardware_platform.value}\n")
            f.write(f"**Repeat Times**: {self.config.repeat_times}\n")
            f.write(f"**Max Rounds**: {self.config.max_rounds}\n\n")
            
            for config_name, config_results in results.items():
                f.write(f"## Experiment Config: {config_name}\n\n")
                
                # Create comparison table
                f.write("| Protocol | Network lifetime (rounds) | Total energy (J) | Energy efficiency (packets/J) | PDR |\n")
                f.write("|---------|----------------------------|------------------|-------------------------------|-----|\n")
                
                for protocol_name, protocol_data in config_results.items():
                    stats = protocol_data['statistics']
                    f.write(
                        f"| {protocol_name} | "
                        f"{stats['network_lifetime']['mean']:.1f}±{stats['network_lifetime']['std']:.1f} | "
                        f"{stats['total_energy_consumed']['mean']:.3f}±{stats['total_energy_consumed']['std']:.3f} | "
                        f"{stats['energy_efficiency']['mean']:.1f}±{stats['energy_efficiency']['std']:.1f} | "
                        f"{stats['packet_delivery_ratio']['mean']:.3f}±{stats['packet_delivery_ratio']['std']:.3f} |\n"
                    )
                
                f.write("\n")

def create_standard_experiment_config() -> ExperimentConfig:
    """Create the standard experiment configuration."""

    return ExperimentConfig(
        node_counts=[50],
        area_sizes=[(100, 100)],
        initial_energies=[2.0],
        max_rounds=1000,
        repeat_times=3,
        hardware_platform=HardwarePlatform.CC2420_TELOSB,
        save_detailed_results=True
    )

def create_quick_test_config() -> ExperimentConfig:
    """Create a quick test configuration for smoke/regression runs."""

    return ExperimentConfig(
        node_counts=[20],
        area_sizes=[(50, 50)],
        initial_energies=[1.0],
        max_rounds=2000,
        repeat_times=3,
        hardware_platform=HardwarePlatform.CC2420_TELOSB,
        save_detailed_results=True
    )

def main():
    """Main function."""
    
    # Create experiment configuration
    experiment_config = create_standard_experiment_config()
    
    # Create benchmark instance
    benchmark = ComprehensiveBenchmark(experiment_config)
    
    # Run comprehensive benchmark
    results = benchmark.run_comprehensive_benchmark()
    
    print("\n[SUCCESS] Comprehensive benchmark completed.")
    print("[INFO] Results saved to ../results/benchmark_experiments/")

if __name__ == "__main__":
    main()




