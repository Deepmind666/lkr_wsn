# AERIS 项目文件夹结构规划

## 当前问题

1. `results/` 下有145个JSON文件，命名混乱
2. `scripts/` 下有80+个实验脚本，大量重复
3. `docs/` 下有100+个文档，版本混乱
4. 无法追溯哪个结果对应哪个代码版本

## 建议结构

```
AERIS-WSN-Protocol/
├── src/                      # 核心代码（不变）
├── scripts/
│   ├── core/                 # 核心实验脚本（保留5-10个）
│   │   ├── run_ablation.py
│   │   ├── run_baseline_compare.py
│   │   ├── run_scalability.py
│   │   └── run_dynamic_scenarios.py
│   ├── utils/                # 工具脚本
│   │   ├── plot_figures.py
│   │   └── smoke_test.py
│   └── archive/              # 归档旧脚本
├── results/
│   ├── v1.0_20260201/        # 按版本+日期组织
│   │   ├── ablation.json
│   │   ├── baseline_compare.json
│   │   └── manifest.json     # 记录代码commit、参数
│   └── archive/              # 归档旧结果
├── docs/
│   ├── paper/                # 论文相关
│   ├── technical/            # 技术文档
│   └── archive/              # 归档旧文档
└── for_submission/           # 投稿材料（不变）
```

## 立即行动建议

### 第一步：创建归档目录
```bash
mkdir -p results/archive
mkdir -p scripts/archive
mkdir -p docs/archive
```

### 第二步：移动旧文件
将当前results/*.json移动到archive，保留最新的核心结果

### 第三步：建立命名规范
- 结果文件：`{experiment}_{date}_{commit_short}.json`
- 每个结果必须包含 `manifest` 字段记录代码版本

## 是否现在执行？

建议先完成P0验证，确认代码正确后再整理文件结构。
