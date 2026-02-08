# 图表规划与待办

## 1. 系统架构示意图（Architecture Overview）
- **目的**：展示 EASR 双层结构（骨干骨架 + 协调层）以及能耗/信道/安全模块的交互。
- **元素**：
  - 物理层：改进能耗模型、真实信道模块。
  - 网络层：簇头选择、CAS 模式选择、骨架/网关调度。
  - 控制循环：安全回退、公平性统计、环境分类轨迹。
- **形式**：二维流程 + 图标化组件，输出 SVG（`AdvancedVisualization.create_architecture_overview()` 提供脚本生成）。

## 2. 算法流程图（Algorithm Flowchart）
- **目的**：展示单轮执行顺序（环境感知→簇头选择→CAS 模式→骨架/网关→数据聚合→安全回退）。
- **生成**：`AdvancedVisualization.create_algorithm_flowchart()` 绘制流程框/判定菱形，输出 SVG/PDF。
- **待检查**：运行依赖 `matplotlib` 环境，需先安装。



## 3. 环境分类示意（Environment Typology）
- **数据源**：Intel Lab 湿度/温度分布、 corridor vs uniform 拓扑。
- **表现**：二维散点 + 区域分割（湿度/噪声 vs PDR），提供分类阈值与典型场景插图。

## 4. 统计图表优化
- **已完成**：小提琴/箱线图加入均值±95%置信区间、统一色板、PDR 纵轴 [0,1]。
- **待优化**：
  - 3D 拓扑图加色条、视角说明、枢纽注释。
  - Pareto 图添加前沿曲线及象限提示。
  - Gardner–Altman 图标注 Holm 校正后的 p 值信息。

## 5. 交付安排
- **优先级**：系统架构 → 算法流程 → 环境分类。
- **工具链**：Inkscape + scripts/advanced_visualization.py（补充新函数）。
- **截止**：第 2 周周中完成草图，第 2 周周末完成 SVG 定稿。
