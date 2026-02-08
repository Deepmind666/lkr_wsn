# AERIS项目数据真实性验证与重构方案

**项目**: AERIS: Adaptive Environment-aware Routing for IoT Sensors  
**文档日期**: 2025-10-07  
**目标**: 确保实验数据的真实性、可追溯性和科学严谨性

---

## 🎯 数据真实性问题诊断

### 当前数据流程评估

#### 1. Intel Lab数据集使用情况

**优点** ✅:
```
- 使用权威公开数据集(MIT CSAIL)
- 2.22M条真实传感器记录
- 包含完整的温度、湿度、光照、电压数据
- 54节点真实空间拓扑
```

**潜在风险** ⚠️:
```python
# src/intel_dataset_loader.py 第60-82行
def _initialize_data(self):
    try:
        if os.path.exists(self.data_file):
            self.load_real_data()
        else:
            if self.use_synthetic:
                self.generate_synthetic_data()  # ❌ 风险点
```

**问题识别**:
1. **合成数据后门**: 如果真实数据加载失败，会静默切换到合成数据
2. **无明确标识**: 结果文件中未标记数据来源(真实vs合成)
3. **参数一致性**: 合成数据参数可能与真实数据分布不一致

#### 2. 数据预处理流程

**当前实现**:
```python
# intel_dataset_loader.py:712-745
def preprocess_data(self):
    # 1. 缺失值处理
    self.imputer = KNNImputer(n_neighbors=5)  # ✓ 合理
    
    # 2. 异常值检测
    # 使用3σ原则  # ✓ 标准方法
    
    # 3. 归一化
    self.scaler_features = MinMaxScaler()  # ✓ 合理
```

**潜在问题**:
- **KNN插补参数**: k=5未说明选择理由
- **异常值阈值**: 3σ可能过于保守(保留率99.7%)
- **归一化时机**: 是否在插补前还是后?

---

## 📋 数据真实性验证方案

### Phase 1: 数据溯源与标记系统

#### 1.1 数据来源追踪

**创建数据元信息类**:
```python
# src/utils/data_provenance.py

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal, Optional
import hashlib
import json

@dataclass
class DataProvenance:
    """数据溯源信息
    
    记录数据的来源、处理历史和完整性校验
    """
    
    # 基本信息
    dataset_name: str  # "Intel_Lab", "Synthetic", etc.
    source_type: Literal['real', 'synthetic', 'augmented']
    load_timestamp: str  # ISO 8601格式
    
    # 数据集详情
    num_records: int
    num_nodes: int
    time_span_days: float
    
    # 文件信息
    source_files: list[str]  # 原始文件路径
    file_hashes: dict[str, str]  # {文件名: SHA256哈希}
    file_sizes: dict[str, int]  # {文件名: 字节数}
    
    # 预处理信息
    preprocessing_steps: list[dict]  # 每步处理的详细参数
    missing_rate_before: float  # 预处理前缺失率
    missing_rate_after: float   # 预处理后缺失率
    outliers_removed: int        # 移除的异常值数量
    
    # 完整性校验
    validation_passed: bool
    validation_errors: list[str]
    
    @classmethod
    def from_intel_lab(cls, loader) -> 'DataProvenance':
        """从Intel Lab数据加载器创建溯源信息"""
        
        # 计算文件哈希
        file_hashes = {}
        file_sizes = {}
        for filepath in [loader.data_file, loader.locations_file]:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    content = f.read()
                    file_hashes[os.path.basename(filepath)] = \
                        hashlib.sha256(content).hexdigest()
                    file_sizes[os.path.basename(filepath)] = len(content)
        
        # 获取数据统计
        sensor_data = loader.sensor_data
        num_records = len(sensor_data)
        num_nodes = sensor_data['node_id'].nunique()
        
        time_span = (sensor_data['timestamp'].max() - 
                    sensor_data['timestamp'].min()).total_seconds() / 86400
        
        # 计算缺失率
        total_cells = sensor_data.size
        missing_cells = sensor_data.isna().sum().sum()
        missing_rate = missing_cells / total_cells
        
        return cls(
            dataset_name="Intel_Berkeley_Lab",
            source_type='real',
            load_timestamp=datetime.now().isoformat(),
            num_records=num_records,
            num_nodes=num_nodes,
            time_span_days=time_span,
            source_files=list(file_hashes.keys()),
            file_hashes=file_hashes,
            file_sizes=file_sizes,
            preprocessing_steps=[],
            missing_rate_before=missing_rate,
            missing_rate_after=0.0,  # 待填充
            outliers_removed=0,
            validation_passed=True,
            validation_errors=[]
        )
    
    def add_preprocessing_step(self, step_name: str, parameters: dict):
        """记录预处理步骤"""
        self.preprocessing_steps.append({
            'step': step_name,
            'timestamp': datetime.now().isoformat(),
            'parameters': parameters
        })
    
    def save(self, filepath: str):
        """保存溯源信息为JSON"""
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'DataProvenance':
        """从JSON加载溯源信息"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)
```

**集成到数据加载器**:
```python
# src/utils/intel_dataset_loader.py

class IntelLabDataLoader:
    def __init__(self, data_dir="../data", use_synthetic=False):
        # ... 现有代码 ...
        self.provenance = None  # 新增
        
    def load_real_data(self):
        # ... 现有加载逻辑 ...
        
        # 创建溯源信息
        self.provenance = DataProvenance.from_intel_lab(self)
        
        logger.info(f"[PROVENANCE] Loaded {self.provenance.num_records} "
                   f"records from {self.provenance.num_nodes} nodes")
        logger.info(f"[PROVENANCE] Data source: {self.provenance.source_type}")
        logger.info(f"[PROVENANCE] File hash: "
                   f"{self.provenance.file_hashes['data.txt.gz'][:16]}...")
    
    def preprocess_data(self):
        # 记录预处理前状态
        missing_before = self.sensor_data.isna().sum().sum()
        
        # 1. 缺失值插补
        self.provenance.add_preprocessing_step(
            'KNN_Imputation',
            {'n_neighbors': 5, 'weights': 'uniform'}
        )
        # ... 插补代码 ...
        
        # 2. 异常值移除
        outliers_removed = 0
        self.provenance.add_preprocessing_step(
            'Outlier_Removal',
            {'method': '3sigma', 'threshold': 3.0}
        )
        # ... 移除代码，统计outliers_removed ...
        
        self.provenance.outliers_removed = outliers_removed
        self.provenance.missing_rate_after = 0.0  # 更新
    
    def get_provenance_summary(self) -> str:
        """获取溯源摘要"""
        return f"""
数据溯源摘要:
- 数据集: {self.provenance.dataset_name}
- 来源类型: {self.provenance.source_type}
- 记录数: {self.provenance.num_records:,}
- 节点数: {self.provenance.num_nodes}
- 时间跨度: {self.provenance.time_span_days:.1f}天
- 缺失率: {self.provenance.missing_rate_before:.2%} → 
         {self.provenance.missing_rate_after:.2%}
- 异常值移除: {self.provenance.outliers_removed}
- 文件哈希: {self.provenance.file_hashes['data.txt.gz'][:16]}...
        """
```

#### 1.2 实验结果标记

**在所有结果中嵌入溯源信息**:
```python
# scripts/run_intel_replay.py

def run_experiment():
    loader = IntelLabDataLoader()
    
    # 运行仿真
    results = protocol.run_simulation(200)
    
    # 嵌入溯源信息
    results['data_provenance'] = loader.provenance.asdict()
    results['experiment_metadata'] = {
        'script': 'run_intel_replay.py',
        'timestamp': datetime.now().isoformat(),
        'git_commit': get_git_commit_hash(),
        'python_version': sys.version,
        'numpy_version': np.__version__,
    }
    
    # 保存
    with open('results/intel_replay_with_provenance.json', 'w') as f:
        json.dump(results, f, indent=2)
```

---

### Phase 2: 数据完整性验证

#### 2.1 数据质量检查清单

**创建自动化验证脚本**:
```python
# scripts/validate_data_quality.py

import numpy as np
import pandas as pd
from scipy import stats
from src.utils.intel_dataset_loader import IntelLabDataLoader

class DataQualityValidator:
    """数据质量验证器"""
    
    def __init__(self, loader: IntelLabDataLoader):
        self.loader = loader
        self.sensor_data = loader.sensor_data
        self.validation_report = {}
    
    def validate_all(self) -> dict:
        """执行所有验证检查"""
        checks = [
            self.check_completeness(),
            self.check_temporal_consistency(),
            self.check_spatial_consistency(),
            self.check_value_ranges(),
            self.check_statistical_properties(),
            self.check_node_coverage()
        ]
        
        all_passed = all(checks)
        return {
            'overall_status': 'PASS' if all_passed else 'FAIL',
            'checks': self.validation_report
        }
    
    def check_completeness(self) -> bool:
        """检查数据完整性"""
        required_cols = ['node_id', 'timestamp', 'temperature', 
                        'humidity', 'light', 'voltage']
        missing_cols = set(required_cols) - set(self.sensor_data.columns)
        
        if missing_cols:
            self.validation_report['completeness'] = {
                'status': 'FAIL',
                'missing_columns': list(missing_cols)
            }
            return False
        
        # 检查缺失率
        missing_rate = self.sensor_data.isna().sum() / len(self.sensor_data)
        
        self.validation_report['completeness'] = {
            'status': 'PASS',
            'missing_rate': missing_rate.to_dict()
        }
        return True
    
    def check_temporal_consistency(self) -> bool:
        """检查时间一致性"""
        timestamps = self.sensor_data['timestamp']
        
        # 1. 时间单调性
        is_sorted = timestamps.is_monotonic_increasing
        
        # 2. 时间间隔分析
        time_diffs = timestamps.diff().dropna()
        median_interval = time_diffs.median().total_seconds()
        
        # 3. 异常间隔检测
        outlier_intervals = time_diffs[
            time_diffs > pd.Timedelta(hours=1)
        ]
        
        self.validation_report['temporal'] = {
            'status': 'PASS' if len(outlier_intervals) < 10 else 'WARN',
            'is_sorted': is_sorted,
            'median_interval_seconds': median_interval,
            'num_outlier_intervals': len(outlier_intervals)
        }
        return True
    
    def check_spatial_consistency(self) -> bool:
        """检查空间一致性"""
        locs = self.loader.locations_data
        
        # 1. 节点ID一致性
        sensor_nodes = set(self.sensor_data['node_id'].unique())
        location_nodes = set(locs['node_id'].unique())
        
        missing_locations = sensor_nodes - location_nodes
        extra_locations = location_nodes - sensor_nodes
        
        # 2. 坐标范围检查
        x_range = (locs['x'].min(), locs['x'].max())
        y_range = (locs['y'].min(), locs['y'].max())
        
        self.validation_report['spatial'] = {
            'status': 'PASS' if not missing_locations else 'FAIL',
            'missing_locations': list(missing_locations),
            'extra_locations': list(extra_locations),
            'x_range': x_range,
            'y_range': y_range
        }
        return len(missing_locations) == 0
    
    def check_value_ranges(self) -> bool:
        """检查数值范围合理性"""
        checks = {
            'temperature': (10.0, 35.0),  # °C
            'humidity': (15.0, 80.0),     # %
            'light': (0, 1000),           # lux
            'voltage': (2.0, 3.3)         # V
        }
        
        results = {}
        all_passed = True
        
        for col, (min_val, max_val) in checks.items():
            data = self.sensor_data[col].dropna()
            
            out_of_range = ((data < min_val) | (data > max_val)).sum()
            percentage = out_of_range / len(data) * 100
            
            status = 'PASS' if percentage < 1.0 else 'WARN'
            if percentage > 5.0:
                status = 'FAIL'
                all_passed = False
            
            results[col] = {
                'status': status,
                'range': (min_val, max_val),
                'actual_range': (data.min(), data.max()),
                'out_of_range_count': int(out_of_range),
                'out_of_range_percentage': percentage
            }
        
        self.validation_report['value_ranges'] = results
        return all_passed
    
    def check_statistical_properties(self) -> bool:
        """检查统计特性"""
        # 对比已知的Intel Lab统计特性
        KNOWN_STATS = {
            'temperature': {'mean': 20.8, 'std': 1.6},
            'humidity': {'mean': 43.5, 'std': 8.3}
        }
        
        results = {}
        all_passed = True
        
        for col, expected in KNOWN_STATS.items():
            data = self.sensor_data[col].dropna()
            actual_mean = data.mean()
            actual_std = data.std()
            
            mean_diff = abs(actual_mean - expected['mean'])
            std_diff = abs(actual_std - expected['std'])
            
            # 允许10%偏差
            mean_ok = mean_diff < expected['mean'] * 0.1
            std_ok = std_diff < expected['std'] * 0.1
            
            status = 'PASS' if (mean_ok and std_ok) else 'WARN'
            if not mean_ok or not std_ok:
                all_passed = False
            
            results[col] = {
                'status': status,
                'expected_mean': expected['mean'],
                'actual_mean': actual_mean,
                'expected_std': expected['std'],
                'actual_std': actual_std
            }
        
        self.validation_report['statistics'] = results
        return all_passed
    
    def check_node_coverage(self) -> bool:
        """检查节点覆盖率"""
        # 每个节点应有足够的数据点
        node_counts = self.sensor_data['node_id'].value_counts()
        
        min_records = 1000  # 最少1000条记录
        low_coverage_nodes = node_counts[node_counts < min_records]
        
        self.validation_report['node_coverage'] = {
            'status': 'PASS' if len(low_coverage_nodes) == 0 else 'WARN',
            'total_nodes': len(node_counts),
            'low_coverage_nodes': low_coverage_nodes.to_dict(),
            'min_records_threshold': min_records
        }
        return True
    
    def generate_report(self, output_path: str):
        """生成验证报告"""
        report = self.validate_all()
        
        # 生成Markdown报告
        md = ["# Intel Lab数据质量验证报告\n"]
        md.append(f"**验证时间**: {datetime.now().isoformat()}\n")
        md.append(f"**总体状态**: {report['overall_status']}\n\n")
        
        for check_name, check_result in report['checks'].items():
            md.append(f"## {check_name.title()}\n")
            md.append(f"**状态**: {check_result['status']}\n")
            md.append("```json\n")
            md.append(json.dumps(check_result, indent=2))
            md.append("\n```\n\n")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(md)
        
        print(f"验证报告已保存到: {output_path}")
        return report

# 使用示例
if __name__ == '__main__':
    loader = IntelLabDataLoader(use_synthetic=False)
    validator = DataQualityValidator(loader)
    
    report = validator.generate_report(
        'docs/intel_data_quality_report.md'
    )
    
    if report['overall_status'] == 'FAIL':
        sys.exit(1)
```

---

### Phase 3: 交叉验证机制

#### 3.1 数据集划分策略

**时间序列交叉验证**:
```python
# src/utils/cross_validation.py

class TimeSeriesCrossValidator:
    """时间序列交叉验证器
    
    对Intel Lab数据进行时间维度的k-fold划分，
    确保训练集始终在测试集之前(避免时间泄露)
    """
    
    def __init__(self, data: pd.DataFrame, n_splits: int = 5):
        self.data = data.sort_values('timestamp')
        self.n_splits = n_splits
    
    def split(self):
        """生成训练集/测试集划分"""
        n = len(self.data)
        test_size = n // (self.n_splits + 1)
        
        for i in range(self.n_splits):
            test_start = (i + 1) * test_size
            test_end = test_start + test_size
            
            train_data = self.data.iloc[:test_start]
            test_data = self.data.iloc[test_start:test_end]
            
            yield train_data, test_data
    
    def validate_protocol(self, protocol_class, config):
        """交叉验证协议性能"""
        results = []
        
        for fold, (train, test) in enumerate(self.split()):
            # 在训练集上运行协议
            # (注意: WSN路由协议通常无监督，这里用"训练"指代性能评估)
            
            # 使用测试集进行验证
            # ...
            
            results.append({
                'fold': fold,
                'energy': test_energy,
                'pdr': test_pdr
            })
        
        return pd.DataFrame(results)
```

#### 3.2 结果一致性检验

**重复实验检测**:
```python
# scripts/check_reproducibility.py

def check_reproducibility(protocol_class, config, n_runs=10):
    """检验实验可重现性
    
    使用相同随机种子运行多次，验证结果是否完全一致
    """
    
    results = []
    for run in range(n_runs):
        protocol = protocol_class(config, seed=42)
        res = protocol.run_simulation(max_rounds=100)
        results.append(res['total_energy_consumed'])
    
    # 检验一致性
    if len(set(results)) == 1:
        print("✓ 完美可重现: 所有运行结果完全一致")
        return True
    else:
        print(f"✗ 可重现性问题: {n_runs}次运行产生{len(set(results))}种不同结果")
        print(f"  结果范围: [{min(results):.6f}, {max(results):.6f}]")
        return False

def check_statistical_stability(protocol_class, config, n_runs=50):
    """检验统计稳定性
    
    使用不同随机种子运行多次，验证统计特性的稳定性
    """
    
    energies = []
    pdrs = []
    
    for run in range(n_runs):
        protocol = protocol_class(config, seed=40000 + run)
        res = protocol.run_simulation(max_rounds=100)
        energies.append(res['total_energy_consumed'])
        pdrs.append(res['packet_delivery_ratio_end2end'])
    
    # 计算变异系数 (CV = std/mean)
    energy_cv = np.std(energies) / np.mean(energies)
    pdr_cv = np.std(pdrs) / np.mean(pdrs)
    
    print(f"能耗稳定性: 均值={np.mean(energies):.4f}, CV={energy_cv:.4f}")
    print(f"PDR稳定性: 均值={np.mean(pdrs):.4f}, CV={pdr_cv:.4f}")
    
    # CV < 0.05认为稳定
    stable = (energy_cv < 0.05 and pdr_cv < 0.05)
    return stable, {'energy_cv': energy_cv, 'pdr_cv': pdr_cv}
```

---

## 🔬 数据采集实验重设计

### 设计目标
1. **可追溯**: 每个数据点可追溯到原始来源
2. **可验证**: 提供独立验证机制
3. **可重现**: 任何人都能重现数据处理流程

### 标准化流程

```python
# scripts/standard_data_pipeline.py

class StandardDataPipeline:
    """标准化数据处理流水线"""
    
    def __init__(self, output_dir='data/processed'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger(__name__)
    
    def run(self):
        """执行完整数据处理流程"""
        
        # Step 1: 数据加载
        self.logger.info("Step 1/6: 加载原始数据...")
        loader = IntelLabDataLoader(use_synthetic=False)
        provenance = loader.provenance
        
        # Step 2: 数据验证
        self.logger.info("Step 2/6: 验证数据质量...")
        validator = DataQualityValidator(loader)
        validation_report = validator.validate_all()
        
        if validation_report['overall_status'] == 'FAIL':
            raise ValueError("数据质量验证失败")
        
        # Step 3: 数据预处理
        self.logger.info("Step 3/6: 预处理数据...")
        loader.preprocess_data()
        
        # Step 4: 保存处理后数据
        self.logger.info("Step 4/6: 保存处理后数据...")
        output_file = self.output_dir / 'intel_lab_processed.parquet'
        loader.sensor_data.to_parquet(output_file)
        
        # Step 5: 保存溯源信息
        self.logger.info("Step 5/6: 保存溯源信息...")
        provenance_file = self.output_dir / 'data_provenance.json'
        provenance.save(str(provenance_file))
        
        # Step 6: 生成报告
        self.logger.info("Step 6/6: 生成数据报告...")
        self.generate_data_report(loader, provenance, validation_report)
        
        self.logger.info(f"✓ 数据处理完成，输出目录: {self.output_dir}")
    
    def generate_data_report(self, loader, provenance, validation):
        """生成完整数据报告"""
        report_file = self.output_dir / 'DATA_REPORT.md'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Intel Lab数据处理报告\n\n")
            f.write(f"**生成时间**: {datetime.now().isoformat()}\n\n")
            
            f.write("## 数据溯源\n\n")
            f.write(loader.get_provenance_summary())
            
            f.write("\n\n## 数据验证\n\n")
            f.write(f"**总体状态**: {validation['overall_status']}\n\n")
            
            f.write("### 验证清单\n\n")
            for check, result in validation['checks'].items():
                status_icon = "✓" if result['status'] == 'PASS' else "⚠"
                f.write(f"- {status_icon} **{check}**: {result['status']}\n")
            
            f.write("\n\n## 使用说明\n\n")
            f.write("```python\n")
            f.write("import pandas as pd\n")
            f.write("from pathlib import Path\n\n")
            f.write("# 加载处理后的数据\n")
            f.write("data = pd.read_parquet('intel_lab_processed.parquet')\n\n")
            f.write("# 查看溯源信息\n")
            f.write("with open('data_provenance.json') as f:\n")
            f.write("    provenance = json.load(f)\n")
            f.write("```\n")

if __name__ == '__main__':
    pipeline = StandardDataPipeline()
    pipeline.run()
```

---

## 📊 实施时间表

### Week 1: 基础设施 (Day 1-2)
- [x] 创建`DataProvenance`类
- [ ] 集成到`IntelLabDataLoader`
- [ ] 更新所有实验脚本嵌入溯源信息

### Week 2: 验证系统 (Day 3-4)
- [ ] 实现`DataQualityValidator`
- [ ] 运行完整数据质量检查
- [ ] 生成验证报告

### Week 3: 交叉验证 (Day 5-6)
- [ ] 实现时间序列交叉验证
- [ ] 可重现性检验
- [ ] 统计稳定性检验

### Week 4: 标准化流程 (Day 7)
- [ ] 建立`StandardDataPipeline`
- [ ] 生成完整数据报告
- [ ] 更新论文方法论部分

---

## ✅ 验收标准

1. **溯源完整性**
   - [ ] 每个结果文件包含完整溯源信息
   - [ ] 可追溯到原始数据文件SHA256哈希
   - [ ] 记录所有预处理步骤和参数

2. **数据质量**
   - [ ] 所有验证检查通过(或有合理警告说明)
   - [ ] 统计特性与已知Intel Lab特征一致
   - [ ] 无异常缺失或超范围值

3. **可重现性**
   - [ ] 相同种子实验结果完全一致
   - [ ] 不同种子实验CV < 5%
   - [ ] 提供完整数据处理脚本

4. **文档完善**
   - [ ] 数据质量报告
   - [ ] 溯源信息文档
   - [ ] 数据使用指南

---

**负责人**: Data Validation Team  
**审核人**: Project Lead  
**版本**: 1.0  
**最后更新**: 2025-10-07

