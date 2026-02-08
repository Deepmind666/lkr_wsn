# AERIS自动化实验框架设计

**项目**: AERIS: Adaptive Environment-aware Routing for IoT Sensors  
**目标**: 建立可重现、可扩展、高效的自动化实验系统  
**文档日期**: 2025-10-07

---

## 🎯 自动化实验目标

### 核心需求
1. **可重现性**: 一键重现所有论文图表
2. **并行化**: 充分利用多核CPU加速实验
3. **监控**: 实时监控实验进度和资源使用
4. **容错性**: 自动重试失败实验
5. **数据管理**: 统一管理实验配置和结果

---

## 🏗️ 系统架构

### 三层架构设计

```
┌─────────────────────────────────────────────────┐
│          Experiment Orchestrator                │
│  (scripts/experiment_manager.py)                │
│  - 实验调度                                      │
│  - 资源分配                                      │
│  - 进度追踪                                      │
└────────────┬────────────────────────────────────┘
             │
┌────────────┴────────────────────────────────────┐
│          Execution Layer                        │
│  - Worker进程池 (ProcessPoolExecutor)          │
│  - 任务队列                                      │
│  - 结果收集                                      │
└────────────┬────────────────────────────────────┘
             │
┌────────────┴────────────────────────────────────┐
│          Storage & Analytics                    │
│  - 结果存储 (HDF5/Parquet)                      │
│  - 实时分析                                      │
│  - 报告生成                                      │
└─────────────────────────────────────────────────┘
```

---

## 💻 核心组件实现

### 1. 实验配置管理

```python
# src/config/experiment_configs.py

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import yaml
import json

@dataclass
class ExperimentConfig:
    """实验配置基类"""
    
    # 实验元信息
    experiment_name: str
    description: str
    tags: List[str]
    
    # 网络配置
    num_nodes: int
    area_width: float
    area_height: float
    initial_energy: float
    packet_size: int
    
    # 协议参数
    protocol_class: str  # 'AerisProtocol', 'LEACHProtocol', etc.
    protocol_params: Dict[str, Any]
    
    # 仿真参数
    max_rounds: int
    num_repetitions: int
    seed_base: int
    
    # 执行参数
    parallel_workers: int = 4
    timeout_per_run: int = 300  # 秒
    
    def to_yaml(self, filepath: str):
        """保存为YAML"""
        with open(filepath, 'w') as f:
            yaml.dump(asdict(self), f, default_flow_style=False)
    
    @classmethod
    def from_yaml(cls, filepath: str):
        """从YAML加载"""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)

# 预定义配置模板
class ConfigTemplates:
    """标准实验配置模板"""
    
    @staticmethod
    def intel_lab_baseline() -> ExperimentConfig:
        """Intel Lab基准对比实验"""
        return ExperimentConfig(
            experiment_name="intel_baseline_comparison",
            description="Compare AERIS with LEACH/PEGASIS/HEED on Intel Lab topology",
            tags=["intel_lab", "baseline", "paper_figure"],
            num_nodes=54,
            area_width=41.0,
            area_height=31.0,
            initial_energy=2.0,
            packet_size=1024,
            protocol_class="AerisProtocol",
            protocol_params={
                "enable_cas": True,
                "enable_gateway": True,
                "profile": "energy"
            },
            max_rounds=200,
            num_repetitions=200,
            seed_base=43000,
            parallel_workers=8
        )
    
    @staticmethod
    def ablation_study() -> ExperimentConfig:
        """消融实验配置"""
        return ExperimentConfig(
            experiment_name="ablation_components",
            description="Ablation study of CAS/Gateway/Fairness/Safety",
            tags=["ablation", "paper_figure"],
            num_nodes=54,
            area_width=41.0,
            area_height=31.0,
            initial_energy=2.0,
            packet_size=1024,
            protocol_class="AerisProtocol",
            protocol_params={},  # 将在运行时修改
            max_rounds=200,
            num_repetitions=100,
            seed_base=44000,
            parallel_workers=8
        )
    
    @staticmethod
    def scalability_test() -> ExperimentConfig:
        """可扩展性测试"""
        return ExperimentConfig(
            experiment_name="scalability_analysis",
            description="Test performance across different network sizes",
            tags=["scalability", "supplementary"],
            num_nodes=50,  # 将在运行时修改
            area_width=100.0,
            area_height=100.0,
            initial_energy=2.0,
            packet_size=1024,
            protocol_class="AerisProtocol",
            protocol_params={"profile": "energy"},
            max_rounds=500,
            num_repetitions=50,
            seed_base=45000,
            parallel_workers=6
        )
```

### 2. 实验编排器

```python
# scripts/experiment_manager.py

import os
import sys
import time
import psutil
import logging
from pathlib import Path
from typing import List, Dict, Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import pandas as pd
import json

sys.path.append(str(Path(__file__).parent.parent / 'src'))

from src.config.experiment_configs import ExperimentConfig
from src.utils.logger import setup_logger

@dataclass
class ExperimentResult:
    """单次实验结果"""
    run_id: int
    seed: int
    status: str  # 'success', 'failed', 'timeout'
    execution_time: float
    metrics: Dict[str, float]
    error_message: str = ""

class ExperimentOrchestrator:
    """实验编排器 - 管理实验的完整生命周期"""
    
    def __init__(self, config: ExperimentConfig, 
                 output_dir: Path = None):
        self.config = config
        self.output_dir = output_dir or Path('results') / config.experiment_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = setup_logger(
            __name__,
            log_file=self.output_dir / 'experiment.log'
        )
        
        self.results: List[ExperimentResult] = []
        self.start_time = None
        self.end_time = None
    
    def run_experiment(self) -> pd.DataFrame:
        """运行完整实验"""
        
        self.logger.info(f"=" * 70)
        self.logger.info(f"Starting Experiment: {self.config.experiment_name}")
        self.logger.info(f"Description: {self.config.description}")
        self.logger.info(f"Repetitions: {self.config.num_repetitions}")
        self.logger.info(f"Parallel Workers: {self.config.parallel_workers}")
        self.logger.info(f"=" * 70)
        
        self.start_time = time.time()
        
        # 1. 创建任务列表
        tasks = self._create_tasks()
        self.logger.info(f"Created {len(tasks)} tasks")
        
        # 2. 并行执行
        self._execute_tasks_parallel(tasks)
        
        # 3. 收集结果
        results_df = self._collect_results()
        
        # 4. 保存结果
        self._save_results(results_df)
        
        # 5. 生成报告
        self._generate_report(results_df)
        
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        
        self.logger.info(f"=" * 70)
        self.logger.info(f"Experiment Completed in {elapsed/60:.1f} minutes")
        self.logger.info(f"Success Rate: {self._calculate_success_rate():.1%}")
        self.logger.info(f"Results saved to: {self.output_dir}")
        self.logger.info(f"=" * 70)
        
        return results_df
    
    def _create_tasks(self) -> List[Dict]:
        """创建任务列表"""
        tasks = []
        
        for i in range(self.config.num_repetitions):
            task = {
                'run_id': i,
                'seed': self.config.seed_base + i,
                'config': self.config,
                'protocol_params': self.config.protocol_params.copy()
            }
            tasks.append(task)
        
        return tasks
    
    def _execute_tasks_parallel(self, tasks: List[Dict]):
        """并行执行任务"""
        
        with ProcessPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(_run_single_experiment, task): task
                for task in tasks
            }
            
            # 实时收集结果
            completed = 0
            failed = 0
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                
                try:
                    result = future.result(timeout=self.config.timeout_per_run)
                    self.results.append(result)
                    
                    if result.status == 'success':
                        completed += 1
                    else:
                        failed += 1
                        self.logger.warning(
                            f"Run {result.run_id} failed: {result.error_message}"
                        )
                    
                    # 进度更新
                    progress = (completed + failed) / len(tasks) * 100
                    self.logger.info(
                        f"Progress: {progress:.1f}% "
                        f"({completed} success, {failed} failed)"
                    )
                    
                except Exception as e:
                    failed += 1
                    self.logger.error(f"Task {task['run_id']} exception: {e}")
                    
                    # 创建失败结果
                    self.results.append(ExperimentResult(
                        run_id=task['run_id'],
                        seed=task['seed'],
                        status='failed',
                        execution_time=0,
                        metrics={},
                        error_message=str(e)
                    ))
    
    def _collect_results(self) -> pd.DataFrame:
        """收集结果为DataFrame"""
        
        data = []
        for result in self.results:
            if result.status == 'success':
                row = {
                    'run_id': result.run_id,
                    'seed': result.seed,
                    'execution_time': result.execution_time,
                    **result.metrics
                }
                data.append(row)
        
        return pd.DataFrame(data)
    
    def _save_results(self, df: pd.DataFrame):
        """保存结果"""
        
        # 1. CSV格式 (易读)
        csv_path = self.output_dir / 'results.csv'
        df.to_csv(csv_path, index=False)
        self.logger.info(f"Saved CSV: {csv_path}")
        
        # 2. Parquet格式 (高效)
        parquet_path = self.output_dir / 'results.parquet'
        df.to_parquet(parquet_path, index=False)
        self.logger.info(f"Saved Parquet: {parquet_path}")
        
        # 3. JSON格式 (完整信息)
        json_path = self.output_dir / 'results.json'
        results_dict = {
            'experiment_name': self.config.experiment_name,
            'config': asdict(self.config),
            'execution_time_total': self.end_time - self.start_time if self.end_time else 0,
            'results': [asdict(r) for r in self.results]
        }
        with open(json_path, 'w') as f:
            json.dump(results_dict, f, indent=2)
        self.logger.info(f"Saved JSON: {json_path}")
    
    def _generate_report(self, df: pd.DataFrame):
        """生成实验报告"""
        
        report_path = self.output_dir / 'REPORT.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# Experiment Report: {self.config.experiment_name}\n\n")
            f.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Configuration\n\n")
            f.write(f"- Protocol: {self.config.protocol_class}\n")
            f.write(f"- Network Size: {self.config.num_nodes} nodes\n")
            f.write(f"- Rounds: {self.config.max_rounds}\n")
            f.write(f"- Repetitions: {self.config.num_repetitions}\n")
            f.write(f"- Parallel Workers: {self.config.parallel_workers}\n\n")
            
            f.write(f"## Results Summary\n\n")
            f.write(df.describe().to_markdown())
            f.write("\n\n")
            
            f.write(f"## Performance\n\n")
            elapsed = self.end_time - self.start_time if self.end_time else 0
            f.write(f"- Total Time: {elapsed/60:.2f} minutes\n")
            f.write(f"- Time per Run: {elapsed/len(df):.2f} seconds\n")
            f.write(f"- Success Rate: {len(df)/self.config.num_repetitions:.2%}\n")
        
        self.logger.info(f"Generated report: {report_path}")
    
    def _calculate_success_rate(self) -> float:
        """计算成功率"""
        successful = sum(1 for r in self.results if r.status == 'success')
        return successful / len(self.results) if self.results else 0.0

# Worker函数 (在独立进程中运行)
def _run_single_experiment(task: Dict) -> ExperimentResult:
    """运行单次实验 (在worker进程中)"""
    
    import random
    import numpy as np
    from src.core.aeris_protocol import AerisProtocol
    from src.baselines.leach import LEACHProtocol
    from benchmark_protocols import NetworkConfig
    
    run_id = task['run_id']
    seed = task['seed']
    config_dict = asdict(task['config'])
    
    # 设置随机种子
    random.seed(seed)
    np.random.seed(seed)
    
    start_time = time.time()
    
    try:
        # 创建网络配置
        net_config = NetworkConfig(
            num_nodes=config_dict['num_nodes'],
            area_width=config_dict['area_width'],
            area_height=config_dict['area_height'],
            initial_energy=config_dict['initial_energy'],
            packet_size=config_dict['packet_size']
        )
        
        # 创建协议实例
        protocol_class_name = config_dict['protocol_class']
        if protocol_class_name == 'AerisProtocol':
            protocol = AerisProtocol(
                net_config,
                seed=seed,
                **task['protocol_params']
            )
        elif protocol_class_name == 'LEACHProtocol':
            protocol = LEACHProtocol(net_config)
        # ... 其他协议
        
        # 运行仿真
        results = protocol.run_simulation(max_rounds=config_dict['max_rounds'])
        
        # 提取关键指标
        metrics = {
            'total_energy_consumed': results['total_energy_consumed'],
            'packet_delivery_ratio_end2end': results['packet_delivery_ratio_end2end'],
            'packet_delivery_ratio': results['packet_delivery_ratio'],
            'network_lifetime': results['network_lifetime']
        }
        
        execution_time = time.time() - start_time
        
        return ExperimentResult(
            run_id=run_id,
            seed=seed,
            status='success',
            execution_time=execution_time,
            metrics=metrics
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        return ExperimentResult(
            run_id=run_id,
            seed=seed,
            status='failed',
            execution_time=execution_time,
            metrics={},
            error_message=str(e)
        )
```

### 3. 一键重现脚本

```python
# scripts/reproduce_all_paper_figures.py

#!/usr/bin/env python3
"""
一键重现所有论文图表

用法:
    python scripts/reproduce_all_paper_figures.py [--quick]
    
选项:
    --quick: 快速模式 (减少重复次数，用于测试)
"""

import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.config.experiment_configs import ConfigTemplates
from scripts.experiment_manager import ExperimentOrchestrator

def main():
    parser = argparse.ArgumentParser(description='Reproduce all paper figures')
    parser.add_argument('--quick', action='store_true', 
                       help='Quick mode with fewer repetitions')
    args = parser.parse_args()
    
    print("="*70)
    print("AERIS Paper Figure Reproduction Script")
    print("This will regenerate ALL figures used in the paper")
    print("="*70)
    
    # 实验列表
    experiments = [
        ('Figure 1-2', ConfigTemplates.intel_lab_baseline()),
        ('Figure 3-4', ConfigTemplates.ablation_study()),
        ('Figure 5-6', ConfigTemplates.scalability_test()),
    ]
    
    # 快速模式: 减少重复次数
    if args.quick:
        print("\n⚡ Quick Mode: Using 20 repetitions instead of 200")
        for name, config in experiments:
            config.num_repetitions = 20
    
    # 运行所有实验
    for fig_name, config in experiments:
        print(f"\n{'='*70}")
        print(f"Running: {fig_name}")
        print(f"{'='*70}")
        
        orchestrator = ExperimentOrchestrator(config)
        results_df = orchestrator.run_experiment()
        
        print(f"✓ {fig_name} completed")
        print(f"  Results: {orchestrator.output_dir}")
    
    print("\n" + "="*70)
    print("All experiments completed!")
    print("Next steps:")
    print("  1. Generate plots: python scripts/plot_paper_figures.py")
    print("  2. Curate figures: python scripts/curate_figures.py")
    print("="*70)

if __name__ == '__main__':
    main()
```

---

## 📊 使用conda环境

### 环境配置

```yaml
# environment.yml

name: py38-torch112-cuda113
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - numpy>=1.21.0
  - scipy>=1.7.0
  - pandas>=1.3.0
  - matplotlib>=3.5.0
  - seaborn>=0.11.0
  - scikit-learn>=1.0.0
  - pytest>=7.0.0
  - pytest-cov>=3.0.0
  - jupyter>=1.0.0
  - pip
  - pip:
    - scikit-fuzzy>=0.4.2
    - pyarrow>=6.0.0
    - psutil>=5.9.0
    - pyyaml>=6.0
```

### 环境管理脚本

```bash
# scripts/setup_env.sh

#!/bin/bash

echo "Setting up AERIS experiment environment..."

# 创建conda环境
conda env create -f environment.yml

# 激活环境
conda activate py38-torch112-cuda113

# 验证安装
python -c "import numpy, pandas, sklearn, matplotlib; print('✓ All packages imported successfully')"

echo "Environment setup complete!"
echo "Activate with: conda activate py38-torch112-cuda113"
```

---

## 🔍 实时监控系统

```python
# scripts/monitor_experiment.py

import psutil
import time
import sys
from pathlib import Path

def monitor_experiment(experiment_dir: Path, refresh_interval=5):
    """实时监控实验进度"""
    
    log_file = experiment_dir / 'experiment.log'
    
    print(f"Monitoring experiment: {experiment_dir.name}")
    print(f"Log file: {log_file}")
    print("="*70)
    
    last_line_count = 0
    
    while True:
        # 1. 系统资源使用
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        
        print(f"\r[{time.strftime('%H:%M:%S')}] "
              f"CPU: {cpu_percent:5.1f}% | "
              f"MEM: {mem.percent:5.1f}% ({mem.used/1e9:.1f}GB/{mem.total/1e9:.1f}GB)",
              end='')
        
        # 2. 日志更新
        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            new_lines = lines[last_line_count:]
            for line in new_lines:
                if 'Progress' in line or 'Completed' in line:
                    print(f"\n{line.strip()}")
            
            last_line_count = len(lines)
        
        time.sleep(refresh_interval)
```

---

## ✅ 完整工作流示例

```bash
# 1. 设置环境
conda activate py38-torch112-cuda113

# 2. 运行所有实验 (完整模式)
python scripts/reproduce_all_paper_figures.py

# 或快速测试
python scripts/reproduce_all_paper_figures.py --quick

# 3. 实时监控 (在另一个终端)
python scripts/monitor_experiment.py results/intel_baseline_comparison

# 4. 生成图表
python scripts/plot_paper_figures.py

# 5. 整理最终图表
python scripts/curate_figures.py

# 6. 查看报告
cat results/intel_baseline_comparison/REPORT.md
```

---

## 📈 性能优化

### 并行化策略

```python
# 根据CPU核心数自动调整
import multiprocessing

optimal_workers = max(1, multiprocessing.cpu_count() - 2)
config.parallel_workers = optimal_workers
```

### 内存管理

```python
# 大规模实验时分批处理
def run_large_experiment(config, batch_size=50):
    total_reps = config.num_repetitions
    
    all_results = []
    for batch_start in range(0, total_reps, batch_size):
        batch_end = min(batch_start + batch_size, total_reps)
        
        config.num_repetitions = batch_end - batch_start
        config.seed_base = config.seed_base + batch_start
        
        orchestrator = ExperimentOrchestrator(config)
        batch_results = orchestrator.run_experiment()
        
        all_results.append(batch_results)
        
        # 释放内存
        del orchestrator
        import gc; gc.collect()
    
    return pd.concat(all_results, ignore_index=True)
```

---

**负责人**: Automation Team  
**版本**: 1.0  
**最后更新**: 2025-10-07

