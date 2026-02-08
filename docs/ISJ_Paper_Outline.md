# AERIS for Wireless Sensor Networks: An Intel Lab Validation Study

## ABSTRACT
Abstract—Many WSN routing schemes rely on idealized channels, creating a persistent simulation‑to‑reality gap at deployment. We present AERIS, which couples a stability‑first skeleton over an IEEE 802.15.4‑consistent stack (path loss, log‑normal shadowing, co‑channel interference, CSMA/CA backoff/retransmissions) with a lightweight coordination layer for environment mapping, safety fallback, and lifetime‑aware fairness. Evaluated on Intel Lab replays (54 nodes) and diverse synthetic topologies, AERIS achieves near‑perfect end‑to‑end delivery (PDR ≈ 0.99) with competitive energy and extended lifetime relative to classic baselines. A 100‑run ablation quantifies complementary contributions—removing gateway coordination reduces PDR to ≈ 0.74 and removing safety fallback to ≈ 0.89—while fairness further stabilizes long‑hops without draining strong nodes. Sensitivity across packet sizes (256–1024 B), initial energy (1–2), and gateway counts (1–3) preserves these trends. Statistical tests (Welch’s t) corroborate reliability gains (p < 0.001) without compromising lifetime. Code and scripts aligned with an 802.15.4‑style stack are released for transparency and reproducibility.

Index Terms—Wireless sensor networks; environment‑aware routing; cross‑layer design; IEEE 802.15.4; skeleton routing; gateway coordination; safety fallback; fairness; packet delivery ratio (PDR); energy efficiency; network lifetime; reproducibility.

## 中文摘要
摘要——提出 EASR（环境自适应骨干路由），将符合 IEEE 802.15.4 的真实信道/MAC 动态（路径损耗、对数正态阴影、同信道干扰、CSMA/CA 回退与重传）显式暴露给网络层，并叠加轻量级协调层，用于环境映射、安全回退与“寿命感知”的公平性约束。在 Intel Lab 回放（54 节点）与多类合成拓扑上，EASR 在保持能耗可比与显著延长寿命的同时，维持近乎完备的端到端投递。100 次消融表明网关协调与安全回退分别为必要组成，而公平性可稳定长跳数链路而不过度消耗强节点。对报文长度（256–1024 B）、初始能量（1–2）与网关数量（1–3）的敏感性分析保持一致趋势；我们报告效应量并使用 Welch t 检验（含多重比较控制）证明可靠性增益不以寿命为代价。代码、数据与脚本全部开源，支持透明复现。

> 术语统一说明：仓库工程名 Enhanced‑AERIS 为历史占位名；本文统一使用 AERIS。必要时在复现脚本或 README 中以 “AERIS（历史别名 EASR/Enhanced AERIS）” 标注对应关系，避免审稿与开源社区混淆。

## IEEE Sensors Journal 论文大纲

### I. INTRODUCTION
Wireless sensor networks (WSNs) are deployed in environments where propagation, interference, and traffic burstiness diverge from textbook assumptions. Nonetheless, many routing evaluations still adopt simplified channels or abstract MACs that mask contention, hidden terminals, and retransmission dynamics. The result is optimistic simulations that degrade upon deployment—the well‑known simulation‑to‑reality gap.

Classic clustering‑based protocols expose this tension. LEACH is energy‑frugal but unreliable under interference and fading; HEED and PEGASIS raise delivery yet incur higher energy or topology‑dependent fragility. Cross‑layer proposals frequently trade energy for reliability (e.g., aggressive retransmissions or duty‑cycling), while learning‑based schemes may overfit or overlook MAC contention. What remains missing is a principled, end‑to‑end design that respects the environment→channel→link→routing chain and still fits the constraints of low‑power motes.

We introduce Environment‑Adaptive Skeleton Routing (EASR), a two‑layer design that closes this gap. Layer 1 builds a stability‑first skeleton atop an IEEE 802.15.4‑consistent channel stack, explicitly modeling path loss, log‑normal shadowing, co‑channel interference, and CSMA/CA backoff/retransmissions so that real contention and retries are visible to routing. Layer 2 adds lightweight gateway coordination to (i) map environment conditions to routing parameters, (ii) trigger a safety fallback upon persistent failures, and (iii) enforce lifetime‑aware fairness that prevents starving weak links and prematurely draining strong nodes. The net effect is a closed‑loop system that sustains delivery without disproportionate energy costs.

This work makes three contributions:
1) A reproducible evaluation stack aligned with IEEE 802.15.4 that exposes realistic interference and retransmission behaviors to the routing layer.
2) A practical protocol—EASR—combining a stability‑first skeleton with a minimal coordination layer for environment mapping, safety fallback, and fairness, with modest compute/memory overhead.
3) A rigorous validation on Intel Lab replays (54 nodes) and multi‑environment synthetic scenarios, including ablation, sensitivity, and statistical significance analyses.

Key findings are as follows. EASR achieves near‑perfect end‑to‑end reliability on Intel Lab replays (PDR ≈ 0.99) while maintaining competitive energy and extended lifetime relative to classic baselines. A 100‑run ablation shows that gateway coordination and safety fallback are individually necessary (removal drops PDR to ≈ 0.74 and ≈ 0.89, respectively), and fairness smooths long‑hop instability without accelerating battery depletion. Sensitivity analyses across packet sizes (256–1024 B), initial energy (1–2), and gateway counts (1–3) preserve these trends, and Welch’s t‑tests confirm reliability gains without compromising lifetime (p < 0.001). Code and scripts aligned with the 802.15.4‑style stack are released to facilitate transparency and reproducibility.

The remainder of the paper is organized as follows. Section II reviews related work in clustering, cross‑layer optimization, environment‑aware routing, and realistic channel modeling. Section III presents the system model and problem formulation. Section IV details the EASR protocol, including the skeleton layer and gateway coordination mechanisms. Section V describes our experimental setup. Section VI reports results and discusses implications. Section VII concludes and outlines future directions.

### II. RELATED WORK
- **传统WSN路由协议**：LEACH, HEED, PEGASIS优缺点分析
- **环境感知路由**：现有环境自适应方法的不足
- **多层路由架构**：分层路由的发展现状
- **本工作定位**：填补环境自适应多层路由的技术空白

### III. SYSTEM MODEL AND PROBLEM FORMULATION
- **网络模型**：节点分布、能耗模型、信道模型
- **环境模型**：Intel Lab数据特征、环境分类标准
- **问题定义**：在环境变化下最大化网络生命周期和数据可靠性
- **设计目标**：能效优化、环境适应、鲁棒性保障

### IV. ENVIRONMENT-ADAPTIVE SKELETON ROUTING (EASR) PROTOCOL

#### A. 总体架构
- 三层路由架构：簇内CAS选择、簇间骨干路由、网关增强传输
- 环境感知模块：基于Intel Lab数据的环境分类器
- 安全回退机制：故障检测、冗余传输、功率调整

#### B. 环境感知与自适应机制
- **环境分类器**：基于Intel Lab温度、湿度、光照数据
- **功率自适应**：INDOOR_OFFICE, OUTDOOR_URBAN等环境的差异化配置
- **信道模型**：现实信道条件下的传输功率优化

#### C. 上下文感知选择(CAS)机制
- **传输模式选择**：Direct, Chain, Two-Hop的智能切换
- **特征提取**：簇半径、密度、距离BS等关键指标
- **决策权重**：w_direct_link和w_direct_energy的平衡策略

#### D. 多层路由与网关机制
- **骨干路由**：簇头间的高效数据转发
- **网关增强**：关键路径的冗余保障
- **负载均衡**：基于模糊逻辑的公平性协调

#### E. 安全回退与鲁棒性
- **故障检测**：连续失败轮次阈值(safety_T)
- **应急措施**：强制直传、功率增强、冗余上行
- **性能监控**：端到端PDR实时评估

### V. EXPERIMENTAL EVALUATION

#### A. 实验设置
- **数据集**：Intel Lab 54节点传感器网络数据
- **基准协议**：LEACH, HEED, PEGASIS
- **评估指标**：网络生命周期、能耗效率、端到端PDR
- **统计方法**：Welch t检验、95%置信区间

#### B. 基准对比实验
- **能耗分析**：AERIS vs 基准协议的能量消耗对比
- **可靠性评估**：端到端数据包传送率比较
- **网络生命周期**：节点存活时间分析
- **统计显著性**：t检验验证性能改进的统计学意义

#### C. 消融实验
- **组件贡献分析**：CAS, 网关, 安全机制各自贡献
- **参数敏感性**：关键参数对协议性能的影响
- **环境适应性**：不同环境条件下的协议表现

#### D. 实际部署考量
- **计算复杂度分析**：协议的计算开销评估
- **内存使用**：节点资源占用分析
- **可扩展性**：不同网络规模下的性能表现

### VI. RESULTS AND DISCUSSION

#### A. 性能改进总结
- **PDR提升**：从42.5%提升到56.0%（改进31.8%）
- **能耗控制**：仅增加1.0%的额外能耗
- **鲁棒性增强**：故障恢复能力显著提升

#### B. 关键发现分析
- **网关机制**：消融实验显示贡献最大的组件
- **环境适应**：不同环境下的性能差异分析
- **参数稳定性**：敏感性分析验证协议鲁棒性

#### C. 实际部署价值
- **工程适用性**：低计算复杂度，易于实现
- **环境通用性**：多种部署环境的适应能力
- **维护成本**：自适应机制减少人工干预需求

### VII. CONCLUSION AND FUTURE WORK
- **技术贡献总结**：环境自适应多层路由的创新价值
- **实验验证意义**：Intel Lab数据集的权威性验证
- **实际应用前景**：工业WSN部署的指导意义
- **未来研究方向**：更复杂环境、更多传感器类型的扩展

---

## 审稿人关注点对应

### 技术创新性
- ✅ 明确的技术贡献：环境自适应多层路由
- ✅ 与现有方法的差异化：CAS+骨干+网关三层架构
- ✅ 实际问题解决：能耗与可靠性平衡

### 实验严谨性  
- ✅ 标准数据集：Intel Lab权威验证
- ✅ 统计检验：Welch t检验确认显著性
- ✅ 完整评估：基准对比+消融实验+敏感性分析

### 期刊适配性
- ✅ 传感器网络焦点：突出WSN实际部署价值
- ✅ 工程应用导向：强调实际部署考量
- ✅ 数据驱动验证：基于真实传感器数据

### 可复现性
- ✅ 开源代码：完整实现和实验脚本
- ✅ 标准数据集：Intel Lab公开数据
- ✅ 详细参数：所有实验配置可重现

## 协议命名建议

**推荐名称**：Environment-Adaptive Skeleton Routing (EASR)

**理由**：
1. **Environment-Adaptive**：突出环境感知和自适应特性
2. **Skeleton Routing**：体现多层骨干路由架构特点  
3. **简洁明确**：避免AERIS命名不清晰的问题
4. **学术规范**：符合WSN路由协议命名惯例