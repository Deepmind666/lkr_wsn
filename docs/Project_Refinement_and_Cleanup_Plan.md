# 项目精简与清理规划 (Project Refinement & Cleanup Plan)

## 1. 目标

本文档旨在响应项目结构中存在的“冗余代码和吹牛内容”的问题，通过识别核心组件、标记待清理部分，为创建一个更清晰、更专注、更易于维护的项目版本库提供一个明确的行动计划。

## 2. 核心文件清单 (Core File Inventory)

以下文件构成了我们项目当前的核心，是功能实现、实验验证和创新策略的基石。我们应该将开发和维护的精力集中在这些文件上。

| 类别 | 文件路径 | 作用 |
| :--- | :--- | :--- |
| **核心协议** | `src/integrated_enhanced_eehfr.py` | 我们正在开发和优化的主协议实现。 |
| **核心模块** | `src/node_state_manager.py` | **新增**-负责链路质量跟踪，是可靠性创新的核心。 |
| **核心模块** | `src/fuzzy_logic_system.py` | 提供了专业的模糊逻辑决策引擎。 |
| **核心模块** | `src/realistic_channel_model.py` | 提供了符合学术标准的真实信道模型。 |
| **核心模块** | `src/improved_energy_model.py` | 提供了符合硬件实际的能耗模型。 |
| **基准对比** | `src/benchmark_protocols.py` | 包含了LEACH, PEGASIS等基准协议的实现。 |
| **实验框架** | `src/comprehensive_benchmark.py` | 用于运行所有对比实验并生成报告的框架。 |
| **战略规划** | `docs/Innovation_and_Journal_Strategy.md` | **新增**-定义了我们的创新点、期刊选择和技术路线。 |
| **设计文档** | `docs/Reliability_Enhancement_Design.md` | **新增**-我们可靠性增强模块的详细设计蓝图。 |

## 3. Bug修复计划：`KeyError: 'rssi'`

在执行下一步操作前，必须修复此Bug。

- **问题文件**: `src/realistic_channel_model.py`
- **问题描述**: `calculate_link_metrics` 方法返回的字典中，键名为 `'rssi_dbm'`，而调用方期望的键名为 `'rssi'`。
- **修复方案**: 将 `realistic_channel_model.py` 第389行的 `'rssi_dbm': rssi,` 修改为 `'rssi': rssi,`。

## 4. 待清理/重构清单 (Cleanup & Refactoring List)

以下文件或目录包含了过时的、重复的或与我们最终目标（发表SCI三区论文）不直接相关的内容。在项目取得阶段性成果后，我们将着手清理。

| 清理目标 | 路径 | 原因与处理方式 |
| :--- | :--- | :--- |
| **过时的协议版本** | `src/enhanced_eehfr_2_0.py`, `src/enhanced_eehfr_realistic.py`, etc. | 这些是开发的中间版本，其功能已被 `integrated_enhanced_eehfr.py` 完全覆盖。**处理方式**: 备份后删除。 |
| **不切实际的探索** | `src/quantum_inspired_routing.py`, `experiments/quantum_routing_test.py` | 正如您所指出的，“量子就是扯谈”。这些代码与我们务实的优化方向不符。**处理方式**: 备份后删除。 |
| **重复的测试脚本** | `experiments/` 目录下的多个 `debug_*.py`, `test_*.py` | 许多测试脚本的功能已被 `comprehensive_benchmark.py` 覆盖。**处理方式**: 评估每个脚本的价值，合并有用的逻辑到主测试框架中，然后删除冗余脚本。 |
| **过时的文档** | `docs/` 目录下的多个 `*_2025_01_30.md` 文件 | 这些是旧的进度报告，其内容已被新的规划覆盖。**处理方式**: 归档到一个名为 `archive/` 的子目录中，而不是直接删除。 |
| **分散的项目目录** | `EEHFR：融合.../`, `Enhanced-EEHFR-Project/` | 存在多个看似重复的项目目录。**处理方式**: 确定 `Enhanced-EEHFR-WSN-Protocol/` 为唯一的主目录，将其他目录中的有用资产合并进来，然后归档或删除其他目录。 |

**清理原则**:
- **安全第一**: 在删除任何文件之前，先通过版本控制（如Git）或创建压缩包进行备份。
- **分步进行**: 不一次性进行大规模删除。在每次成功运行基准测试并提交一个稳定版本后，再进行一小部分的清理工作。

这份规划文档为我们接下来的工作提供了清晰的路线图。