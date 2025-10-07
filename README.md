# AERIS: Adaptive Environment-aware Routing for IoT Sensors

> ��ĿƷ�ƴ� EEHFR ͳһ����Ϊ AERIS���ֽ׶�Ϊ���ƻ�ʽ�������������д���ģ��·������ src\\Enhanced-EEHFR-WSN-Protocol�����������Ա���/����ʽ�ع�Ǩ�Ƶ� aeris��

# 🚀 Enhanced AERIS: Energy-Efficient Hybrid Fuzzy Routing Protocol for WSN

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Research](https://img.shields.io/badge/Status-Research-orange.svg)]()
[![Performance](https://img.shields.io/badge/Energy_Reduction-60%25%2B-brightgreen.svg)]()


> Status (Aug 27, 2025) �?reproducible, real-geometry, CI-backed results
>
> - Real dataset and geometry: Intel Berkeley Research Lab (�?.22M records) + official mote locations
> - Unified end-to-end metric: packet_delivery_ratio_end2end = source→BS delivery; hop-level PDR reported separately
> - Baselines aligned: LEACH/HEED/PEGASIS now use the same E2E definition on real geometry
> - Robust vs Energy profiles: significant E2E improvement with small energy increase (n=50, 95% CI, Welch t)
> - Curated paper-quality figures: results/plots_curated/ with manifest.json for fast Word insertion
>
> Reproduce core figures (one-liners)
> - conda run -n aether-wsn python scripts/run_intel_replay.py
> - conda run -n aether-wsn python scripts/run_intel_baselines_all.py
> - conda run -n aether-wsn python scripts/run_parallel_significance_intel.py 50
> - conda run -n aether-wsn python scripts/plot_paper_figures.py
> - conda run -n aether-wsn python scripts/curate_figures.py (puts final figs into results/plots_curated)
>
> Curated figures (for Word)
> - F1: Intel �?AETHER Energy (200 rounds) �?results/plots_curated/paper_intel_energy.png
> - F2: Intel �?AETHER End-to-End PDR (200 rounds) �?results/plots_curated/paper_intel_pdr.png
> - F3: Intel �?AETHER vs Baselines: Energy �?results/plots_curated/paper_intel_baselines_energy.png
> - F4: Intel �?AETHER vs Baselines: End-to-End PDR �?results/plots_curated/paper_intel_baselines_pdr.png
> - F5: Intel �?Predicted env (LSTM/TCN) vs Conservative: Energy �?results/plots_curated/paper_intel_predenv_energy.png
> - F6: Intel �?Predicted env (LSTM/TCN) vs Conservative: PDR �?results/plots_curated/paper_intel_predenv_pdr.png
> - F7: Intel �?PDR with 95% CI (n=50) �?results/plots_curated/paper_intel_sig_pdr.png
> - F8: Intel �?Energy with 95% CI (n=50) �?results/plots_curated/paper_intel_sig_energy.png
>
> Data authenticity & mapping
> - Sensor logs from MIT/CSAIL official site; no fabricated data
> - Conservative environment→channel mapping: humidity→shadowing_std (tiers), temperature→noise floor micro-shift
> - Scripts under scripts/ fully reproduce JSON and figures

## 📌 Reproducibility & Usability

- 中文指南（推荐）：docs/ISJ_Reproducibility_and_Usability_Guide.md
- English guide: docs/ISJ_Reproducibility_and_Usability_Guide_EN.md
- 1页速览（Quickstart�? docs/ISJ_Repro_Quickstart_1pager.md
- Paper Mode: set environment variable PAPER_MODE=1 to hide in-figure titles for journal captions

## 📋 项目概述

**Enhanced AERIS** 是一个创新的无线传感器网�?WSN)路由协议，融合了模糊逻辑、混合元启发式优化和链式聚类技术。通过智能的簇头选择和优化的数据传输路径，实现了显著的能效提升和网络寿命延长�?
### 🏆 核心成就 (实事求是版本)
- **5-6%** 相比PEGASIS协议的能效提�?(~280 vs ~266 packets/J)
- **96.7%** 数据包投递率 (PDR)
- **完整基准对比**: 与LEACH、PEGASIS、HEED、TEEN四协议全面对�?- **技术可�?*: 基于真实硬件参数(CC2420)和Intel Lab数据�?- **开源代�?*: 完整实现，支持论文OA代码要求

## 🔬 技术创�?
### 1. 🏗�?四协议基准框�?- **LEACH**: 161.65 packets/J, 0.822 PDR (经典分布式聚�?
- **PEGASIS**: 249.97 packets/J, 0.980 PDR (链式拓扑，最佳能�?
- **HEED**: 224.15 packets/J, 1.000 PDR (混合能效聚类，最佳可靠�?
- **TEEN**: 0.20 packets/J, 0.003 PDR (事件驱动�?

### 2. 🧠 Enhanced AERIS协议
- **环境感知路由**: 6种环境类型自动识�?- **模糊逻辑簇头选择**: 多维节点评估
- **自适应传输功率**: -5dBm�?dBm动态调�?- **Log-Normal Shadowing**: 真实信道建模

### 3. �?改进的能耗模�?- **CC2420硬件参数**: 208.8/225.6 nJ/bit实际能�?- **修复关键bug**: 放大器能耗系数从1e-12提升�?e-9
- **多平台支�?*: CC2420、CC2650、ESP32

### 4. 📊 即将推出: Enhanced AERIS 2.0
- **双阶段优�?*: HEED聚类 + PEGASIS链式融合
- **智能切换机制**: 基于网络状态的动态策略选择
- **目标性能**: 10-15%提升，达到SCI Q3期刊标准

## 📁 项目结构

```
Enhanced-AERIS-WSN-Protocol/
├── 📄 README.md                    # 项目说明文档
├── 📄 requirements.txt             # Python依赖�?├── 📄 LICENSE                      # 开源许可证
├── 📄 .gitignore                   # Git忽略文件
�?├── 📁 src/                         # 核心源代�?�?  ├── enhanced_eehfr_protocol.py  # 🎯 主协议实�?�?  ├── intel_dataset_loader.py     # 📊 数据加载�?�?  ├── lstm_prediction.py          # 🧠 LSTM预测模块
�?  ├── fuzzy_logic_system.py       # 🔮 模糊逻辑系统
�?  ├── hybrid_metaheuristic.py     # �?混合优化算法
�?  └── baseline_protocols/         # 📈 基准协议
�?      ├── leach_protocol.py       #   - LEACH协议
�?      ├── pegasis_protocol.py     #   - PEGASIS协议
�?      └── heed_protocol.py        #   - HEED协议
�?├── 📁 tests/                       # 测试代码
�?  ├── test_enhanced_eehfr.py      # 🔬 综合测试框架
�?  ├── comparative_experiment.py   # 📊 基准协议对比
�?  └── simple_enhanced_test.py     # �?简化测�?�?├── 📁 experiments/                 # 实验脚本
�?  ├── multi_scale_testing.py      # 🔄 多规模网络测�?�?  ├── parameter_optimization.py   # ⚙️ 参数优化
�?  └── performance_analysis.py     # 📈 性能分析
�?├── 📁 results/                     # 实验结果
�?  ├── latest_results.json         # 📋 最新测试结�?�?  ├── performance_charts/         # 📊 性能图表
�?  └── analysis_reports/           # 📄 分析报告
�?├── 📁 data/                        # 数据文件
�?  ├── README.md                   # 数据集说�?�?  └── sample_data/                # 示例数据
�?├── 📁 docs/                        # 项目文档
�?  ├── PROJECT_RECORD.md           # 📝 项目记录
�?  ├── STAGE2_PLAN.md              # 🗺�?发展计划
�?  └── API_DOCUMENTATION.md        # 📖 API文档
�?└── 📁 scripts/                     # 工具脚本
    ├── setup.py                    # 🔧 安装脚本
    └── run_experiments.py          # 🚀 实验运行脚本
```

## 📈 性能结果

### 多规模网络测试结�?
| 网络规模 | 协议 | 能�?J) | 网络寿命(�? | 能效 | 改进幅度 |
|----------|------|---------|-------------|------|----------|
| **50节点** | Enhanced AERIS | **10.43** | 500 | **2867.31** | **基准** |
|          | LEACH | 24.16 | 500 | 1237.42 | +56.8% |
|          | PEGASIS | 11.33 | 500 | 2638.65 | +8.7% |
|          | HEED | 48.47 | 500 | 616.85 | +78.5% |
| **100节点** | Enhanced AERIS | **21.22** | 500 | **2358.72** | **基准** |
|           | LEACH | 31.71 | 500 | 1577.95 | +33.1% |
|           | PEGASIS | 21.97 | 500 | 2276.83 | +3.4% |
|           | HEED | 76.42 | 500 | 654.64 | +72.2% |
| **150节点** | Enhanced AERIS | **35.45** | 500 | **2115.64** | **基准** |
|           | LEACH | 88.95 | 500 | 843.28 | +60.1% |
|           | PEGASIS | 44.29 | 500 | 1693.50 | +20.0% |
|           | HEED | 179.60 | 500 | 417.67 | +80.3% |

## 🚀 快速开�?
### 环境要求
```bash
Python 3.8+
numpy >= 1.21.0
matplotlib >= 3.5.0
scikit-learn >= 1.0.0
scikit-fuzzy >= 0.4.2
tensorflow >= 2.8.0
```

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行测试
```bash
# 综合性能测试
python tests/test_enhanced_eehfr.py

# 基准协议对比
python tests/comparative_experiment.py

# 快速验证测�?python tests/simple_enhanced_test.py
```

### 查看结果
```bash
# 查看最新测试结�?cat results/latest_results.json

# 查看性能图表
ls results/performance_charts/
```

## 📊 数据�?
本项目使�?*MIT CSAIL Intel Berkeley Research Lab**数据集：
- **官方网站**: https://db.csail.mit.edu/labdata/labdata.html
- **数据规模**: 2,219,799条真实传感器记录
- **时间跨度**: 2004-02-28 �?2004-04-05 (36�?
- **节点数量**: 54个传感器节点
- **数据类型**: 温度、湿度、光照、电�?
## 🔄 项目状�?
### �?Stage 1: 已完�?(95%)
- [x] 技术栈评估和优�?- [x] 基准协议完整实现
- [x] Enhanced AERIS核心算法
- [x] 多规模网络测试验�?- [x] 性能分析和文�?
### 🔄 Stage 2: 进行�?- [ ] LSTM预测模块深度集成
- [ ] 链式聚类算法优化
- [ ] 自适应模糊逻辑增强
- [ ] 大规模网络验�?- [ ] 参数全面优化

### 📝 Stage 3: 计划�?- [ ] 扩展基准协议对比
- [ ] 统计显著性分�?- [ ] 学术论文撰写
- [ ] 开源社区发�?
## 📞 联系信息

- **作�?*: Deepmind666
- **邮箱**: 1403073295@qq.com
- **GitHub**: [@Deepmind666](https://github.com/Deepmind666)

## 🙏 致谢

- MIT CSAIL提供Intel Berkeley Research Lab数据�?- 开源社区提供优秀的Python科学计算�?- WSN研究社区的理论基础和协议贡�?
## 📄 引用

如果本项目对您的研究有帮助，请引用：

```bibtex
@misc{enhanced_eehfr_2025,
  title={Enhanced AERIS: Energy-Efficient Hybrid Fuzzy Routing Protocol for Wireless Sensor Networks},
  author={Deepmind666},
  year={2025},
  url={https://github.com/Deepmind666/Enhanced-AERIS-WSN-Protocol}
}
```

---

## 📊 **最新基准测试结�?* (2025-01-30)

### **严谨对比实验**
- **实验设计**: 4种网络配�?× 2种协�?× 5次重�?= 40组实�?- **硬件平台**: CC2420 TelosB (基于最新文献参�?
- **仿真轮数**: 500�?- **统计方法**: 均值±标准差

### **LEACH vs PEGASIS 性能对比**

| 网络配置 | 协议 | 网络生存时间(�? | 总能�?J) | 能效(packets/J) | 数据包投递率 |
|----------|------|------------------|-----------|-----------------|-------------|
| 50节点,100×100 | **LEACH** | 500.0±0.0 | **19.991±0.005** | **1250.6±0.3** | 0.820±0.000 |
| 50节点,100×100 | PEGASIS | 500.0±0.0 | 21.605±0.000 | 1157.1±0.0 | **0.980±0.000** |
| 100节点,100×100 | **LEACH** | 500.0±0.0 | **39.994±0.056** | **1250.2±1.7** | 0.821±0.002 |
| 100节点,100×100 | PEGASIS | 500.0±0.0 | 43.417±0.000 | 1151.6±0.0 | **0.990±0.000** |

### **关键发现**
- �?**LEACH优势**: 能效更高 (~8%优势)，能耗更�?- �?**PEGASIS优势**: 数据包投递率更高 (~20%优势)，通信更可�?- �?**Enhanced AERIS目标**: 结合两者优势，实现最佳平�?
### **技术验�?*
- �?能耗模型准确性验�?(解决了之�?.0008J异常问题)
- �?基准协议标准实现验证 (基于原始论文)
- �?实验方法严谨性验�?(符合SCI期刊标准)

---

## 🚀 **Week 2 计划: Enhanced AERIS 2.0** (2025-01-30)

### **技术目�?*
- **性能提升**: 10-15% (目标 >275 packets/J)
- **可靠�?*: >98.5% PDR
- **学术价�?*: 达到SCI Q3期刊发表标准

### **核心创新**
```
Enhanced AERIS 2.0 = 基础AERIS + 双阶段优�?+ 智能切换

阶段1: HEED能效聚类 �?形成最优簇结构
阶段2: PEGASIS链式优化 �?簇内数据融合
阶段3: 模糊逻辑切换 �?动态策略选择
```

### **实施计划**
- **Day 1-2**: 混合聚类算法设计与实�?- **Day 3-4**: 增强模糊逻辑决策系统
- **Day 5-7**: 系统集成与性能验证

📚 **详细方案**: 查看 [`docs/Week2_Enhanced_AERIS_2.0_Plan.md`](docs/Week2_Enhanced_AERIS_2.0_Plan.md)

---

**�?如果这个项目对您有帮助，请给个Star支持�?*

**🔬 研究贡献**: 本项目为WSN路由协议研究提供了创新的混合优化方案，基于严格的实验验证和开源代码，支持学术论文的开放获�?OA)要求�?
**📈 项目状�?*: 积极开发中 🚀 | **当前阶段**: 基准协议对比完成，Enhanced AERIS优化进行�?| **最后更�?*: 2025�?�?0�?

## Reproducibility (Core Artifacts)

- One-click reproduce
```
py -3 scripts/run_reproduce_all.py
```
Generates:
- results/safety_tradeoff_grid_50x200.{json,csv}
- results/plots/safety_tradeoff.png
- results/significance_compare_50x200.json
- results/significance_compare_multi_topo_50x200.json

- Baseline comparison
```
py -3 scripts/run_final_baseline_compare.py
py -3 scripts/summarize_final_baselines.py
```
Outputs CSV and plots under results/ and results/plots/.

- Paper figures
```
py -3 scripts/plot_paper_figures.py
```
Outputs PDF+PNG under results/plots/.

- Profiles
AETHER supports quick profiles:
- energy (default): minimal energy, Crisis fallback disabled
- robust: crisis fallback enabled (r=1.0, δ=1dBm)

Example:
```
from integrated_enhanced_eehfr import IntegratedEnhancedAERISProtocol
proto = IntegratedEnhancedAERISProtocol(cfg, enable_gateway=True, profile='robust')
```

- Metric semantics
We strictly use packet_delivery_ratio_end2end for end-to-end PDR (aggregated by domain delivery semantics). Hop-level PDR is reported separately as packet_delivery_ratio.
