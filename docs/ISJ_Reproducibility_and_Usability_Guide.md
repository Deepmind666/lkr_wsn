# ISJ 复现实验与可用性说明（v1.0，2025-09-06）

本说明面向希望快速复现实验结果与图件输出的读者与审稿人，覆盖环境准备、数据获取、核心实验、图件生成、结果核验与常见问题定位。默认平台为 Windows 10/11（PowerShell），亦适用于 Linux/macOS（命令小差异）。

## 1. 环境准备（10 分钟）
- Python ≥ 3.10，建议使用 Conda 虚拟环境。
- 依赖安装：
  - 方案 A（推荐）
    1) 创建环境：conda create -n eehfr python=3.10 -y；conda activate eehfr
    2) 安装依赖：pip install -r requirements.txt
  - 方案 B（一键脚本）
    - PowerShell 执行：scripts/setup_conda_env.ps1（自动创建/激活环境并安装依赖）
- 字体与图形后端：已在绘图脚本中统一 rcParams，默认输出 SVG，字体内嵌，论文模式可开关（见第 4 节）。

## 2. 数据资源获取（<5 分钟）
- 运行：python scripts/download_intel_assets.py
- 作用：下载并准备 Intel Lab 相关数据资产与必要的元数据文件。

## 3. 一键复现与关键实验
- 一键复现（推荐）：
  - python scripts/run_reproduce_all.py
  - 说明：顺序运行核心实验，产出将在 results/ 下生成对应 JSON。
- 若需逐项运行，建议顺序：
  1) 基线与对照：
     - python scripts/run_final_baseline_compare.py
     - python scripts/run_intel_replay.py
  2) 显著性与多拓扑：
     - python scripts/run_significance_intel.py
     - python scripts/run_significance_multi_topo.py
     - python scripts/run_stats_multitest.py
  3) 效应量与稳健性：
     - python scripts/compute_effect_sizes.py
     - python scripts/run_safety_tradeoff_grid.py（可选，生成安全-性能权衡网格）
- 产出位置：results/*.json（例如 final_baseline_compare.json、intel_replay_compare.json、multitest_holm_bonferroni.json、effect_sizes_summary.json 等）。

## 4. 论文图件生成与策展
- 生成全部论文图：
  - python scripts/plot_paper_figures.py
  - 输出目录：results/plots/*.svg（例如 paper_intel_energy.svg、paper_intel_pdr.svg、paper_intel_sig_pdr.svg、paper_safety_tradeoff.svg 等）
- 策展与打包：
  - python scripts/curate_figures.py
  - 输出目录：
    - results/plots_curated/：精选版本（manifest.json 与 README.txt）
    - results/publication_figures/：投递用高质量 SVG
    - results/isj_minimal_svg/：ISJ 最小 SVG 包（附 README.txt）
- 论文模式（去除图内标题、便于只用外部 caption）：
  - 在 scripts/plot_paper_figures.py 顶部可切换 PAPER_MODE = True/False（默认 True）。

## 5. 结果核验（建议逐项确认）
- 标签一致性：所有图件应使用“End-to-End PDR”（而非“PDR End-to-End”）。
  - Windows 快查：Select-String -Path results\plots\*.svg -Pattern "PDR End-to-End" -List（若无输出则一致）
- 输出完整性：
  - results/plots/ 下应至少含：paper_intel_energy.svg、paper_intel_pdr.svg、paper_intel_sig_pdr.svg、paper_safety_tradeoff.svg
  - curate_figures.py 运行后，plots_curated/ 与 publication_figures/ 均应同步更新；isj_minimal_svg/ 中应存在最小提交集与说明。
- SVG 质量：
  - 打开任意 SVG，确认文本可选中复制、字体一致、坐标轴与图例清晰、无需位图渲染。
- 统计一致性：
  - results/effect_sizes_summary.json 与 multitest_holm_bonferroni.json 存在且键名完整。

## 6. 典型耗时与资源（参考）
- 环境准备：~10 分钟；数据下载：<5 分钟。
- 一键复现：取决于实验规模与硬件，常见 10–90 分钟；CPU ≥ 4C，内存 ≥ 8GB；GPU 非必需。
- 仅重生图件（已有 JSON）：<1 分钟。

## 7. 常见问题排查
- 字体或中文显示异常：
  - 已统一 rcParams 与字体嵌入；若本地字体异常，可重新安装 matplotlib 默认字体或使用英文化标签。
- 依赖冲突/版本问题：
  - 采用独立 Conda 环境；若仍有冲突，请按 requirements.txt 指定版本安装。
- 无法下载数据：
  - 检查网络与代理，或手动放置数据到 data/ 对应路径后重试。
- 图件缺失或旧样式：
  - 先运行 plot_paper_figures.py 再运行 curate_figures.py，确保覆盖与同步。

## 8. 可用性与扩展
- 颜色与风格：已统一 Okabe–Ito 色盲友好配色与 IEEE/ACM 期刊级风格（SVG 矢量、字号/线宽/图例规范）。
- 复用与扩展：新增方法时，继承现有方法-颜色映射并复用 save_figure 与 Paper Mode，保证风格一致。

## 9. 许可与引用
- 许可：MIT License（见根目录 LICENSE）。
- 如在论文或报告中使用本代码/图件，请在参考文献中致谢并标注仓库名称。

—— 完 ——