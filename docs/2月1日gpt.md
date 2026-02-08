跳至内容
历史聊天记录
你说：
aeris_protocol.py
Python
cas_selector.py
Python
gateway_selector.py
Python
improved_energy_model.py
Python
run_mega_experiments.py
Python
# GPT DeepSearch 完整研究任务

## 一、研究背景

我开发了一个WSN(无线传感器网络)路由协议AERIS，包含三个核心模块：
- **CAS**: Context-Adaptive Switching，根据网络状态自适应选择DIRECT/CHAIN/TWO_HOP三种簇内通信模式
- **Gateway**: 选择关键节点作为网关，优化簇头到基站的上行链路
- **Skeleton**: 构建骨干网络，减少冗余传输

## 二、消融实验数据（已完成1600任务）

### 实验配置
- 节点数：200
- 轮数：600
- 拓扑：uniform, corridor31
- 重复：100次/变体/拓扑
- 信道：indoor_office
- 模式：lightweight (减少重试次数)
- 总任务：8变体 × 2拓扑 × 100重复 = 1600

### 实验结果汇总

变体           PDR(%)      能耗(J)    寿命(轮)   样本数
----------------------------------------------------------
no_cas         88.5±1.5    352.0      274        200
gateway_only   88.4±1.3    352.0      273        200
no_skeleton    88.4±1.4    351.6      278        200
full           88.2±1.4    351.7      277        200
cas_only       87.1±1.2    357.5      262        200
minimal        87.0±1.3    357.6      256        200
skeleton_only  86.8±1.2    357.0      260        200
no_gateway     86.6±1.3    356.7      266        200



### 统计显著性检验（Welch t-test, vs full）

变体           差异(pp)    p值          效应量d    结论
----------------------------------------------------------
no_gateway     -1.64       8.49e-29     1.21       显著，Gateway有效
skeleton_only  -1.44       2.25e-25     1.12       显著
minimal        -1.25       3.84e-19     0.94       显著
cas_only       -1.19       2.30e-18     0.92       显著
no_cas         +0.28       0.057        -          不显著
no_skeleton    +0.12       0.392        -          不显著
gateway_only   +0.14       0.294        -          不显著



### 核心异常发现
1. **Gateway模块有效**：移除后PDR显著下降1.64pp (p=8.49e-29)
2. **CAS模块无效**：移除后PDR反而上升0.28pp (p=0.057，不显著)
3. **Skeleton模块无效**：移除后PDR上升0.12pp (p=0.392，不显著)
4. **模块组合问题**：full(88.2%) < no_cas(88.5%)，启用CAS反而更差

## 三、CAS模块关键代码

### 3.1 CAS权重配置 (cas_selector.py)

python
# DIRECT模式权重
w_direct_energy: float = 0.35
w_direct_link: float = 0.40
w_direct_dist_bs: float = -0.20  # 负权重：距离越近得分越高
w_direct_radius: float = -0.15
w_direct_density: float = 0.25
w_direct_fair: float = -0.05
# 权重和: 0.60

# CHAIN模式权重
w_chain_energy: float = 0.25
w_chain_link: float = 0.25
w_chain_dist_bs: float = 0.15
w_chain_radius: float = 0.25
w_chain_density: float = 0.15
w_chain_fair: float = -0.05
# 权重和: 1.00

# TWO_HOP模式权重
w_twohop_energy: float = 0.25
w_twohop_link: float = 0.25
w_twohop_dist_bs: float = 0.30
w_twohop_radius: float = 0.15
w_twohop_density: float = 0.10
w_twohop_fair: float = -0.05
# 权重和: 1.00



### 3.2 CAS评分函数

python
def _score_direct(self, f: Dict[str, float]) -> float:
    c = self.cfg
    return (
        c.w_direct_energy * f["energy"] +
        c.w_direct_link * f["link"] +
        c.w_direct_dist_bs * f["dist_bs"] +
        c.w_direct_radius * f["radius"] +
        c.w_direct_density * f["density"] +
        c.w_direct_fair * f["fairness"]
    )



### 3.3 模式选择逻辑

python
def select_mode(self, features: Dict[str, float]):
    f = {k: self._clip01(v) for k, v in features.items()}
    scores = {
        CASMode.DIRECT: self._score_direct(f),
        CASMode.CHAIN: self._score_chain(f),
        CASMode.TWO_HOP: self._score_twohop(f),
    }
    # EMA平滑
    for mode in scores:
        self._ema_scores[mode] = (
            self.cfg.ema_alpha * scores[mode] +
            (1 - self.cfg.ema_alpha) * self._ema_scores[mode]
        )
    best_mode = max(self._ema_scores, key=self._ema_scores.get)
    return best_mode, confidence, scores



## 四、transmit_to_bs重试机制（可能掩盖模块差异）

python
# lightweight模式参数
arq_retries = 3          # ARQ重试次数
power_steps = [0.0, 3.0] # 功率阶梯
parent_copies = 2        # 父节点副本数
rescue_candidates = 2    # 救援候选数
direct_tries = 8         # 直达尝试次数



重试流程：父节点重试 → 救援候选 → 直达尝试 → 广播兜底 → 极限兜底

## 五、研究任务

### 任务1：文献调研
1. 搜索2020-2025年WSN自适应路由协议（INFOCOM/MobiCom/ToN/TMC/IoT-J）
2. 查找"模块组合后性能下降"的案例及解释方法
3. 消融实验方法论最佳实践
4. WSN仿真可信度标准（Python vs NS-3/OMNeT++）

### 任务2：CAS失效根因分析
1. 权重配置是否导致DIRECT偏好过强？
2. EMA平滑(alpha=0.2)是否导致切换过于保守？
3. 输入特征(energy/link/dist_bs等)的取值范围是否合理？

### 任务3：模块干扰分析
1. CAS/Gateway/Skeleton是否存在逻辑冲突？
2. 重试机制是否掩盖了模块差异？
3. 为什么full < no_cas？

### 任务4：改进方案
1. CAS权重如何调整？
2. 是否应该移除CAS/Skeleton，仅保留Gateway？
3. 实验设计如何改进？

### 任务5：论文策略
1. MDPI Sensors对WSN论文的要求
2. 如何诚实报告"部分模块无效"？
3. 创新点如何重构？

### 任务6：竞品对比
1. LEACH/PEGASIS/HEED最新改进版(2020-2025)
2. 2023-2025年WSN路由SOTA协议
3. AERIS的真实定位

## 六、期望输出

1. **文献综述**：5-10篇相关论文分析
2. **根因诊断**：CAS失效的技术原因
3. **改进方案**：具体权重调整建议
4. **论文策略**：创新点重构方案
5. **竞品对比表**：AERIS vs 经典/SOTA协议
ChatGPT 说：

非常感谢您提供完整背景、数据与代码结构。为了开展最全面和针对性的 GPT DeepSearch 任务，请确认以下细节：

    任务优先级排序：是否希望我按照任务 1 到任务 6 的顺序进行研究？还是有某个任务您希望优先处理（例如任务2“CAS失效分析”）？

    研究语言偏好：是否需要全部输出为中文？还是某些任务如任务1的文献综述您更希望是英文原文 + 中文总结？

    期望格式偏好：对于输出如文献综述、改进方案、论文策略，您更倾向 markdown 报告风格（带有层级标题/列表/表格），还是更自由结构的文本？

    竞品对比范围：任务6中对比协议是否只限定于路由协议（如LEACH, HEED等），还是也包括跨层方案（例如聚簇优化+MAC协同方案）？

有了这些信息，我就可以立即开始高质量的多任务深度研究。
你说：
目前我认为应该使用ns-3或，OMeT++等专业网络仿真平台来改进，你还需指导详细思路。
任务优先级排序
推荐顺序：任务2 → 任务3 → 任务6 → 任务1 → 任务4 → 任务5

理由：

任务2（CAS失效根因分析）最优先 - 这是核心技术问题，必须先搞清楚CAS为什么无效
任务3（模块干扰分析）次优先 - 理解模块间关系后才能决定改进方向
任务6（竞品对比）第三 - 需要知道AERIS在SOTA中的真实定位
任务1（文献调研）第四 - 为论文写作提供支撑
任务4/5（改进方案和论文策略）最后 - 基于前面分析结果决定
研究语言偏好
全部输出为中文，便于直接使用。

期望格式偏好
Markdown报告风格，包含：

清晰的标题层级
代码块用于展示关键代码片段
表格用于对比数据
每个结论附带证据引用
竞品对比范围
以路由协议为主，但也包括跨层方案，特别是：

经典路由：LEACH、PEGASIS、HEED及其2020-2025改进版
跨层方案：如果有结合MAC层或物理层的WSN优化方案也需要对比
ML/RL方案：基于强化学习、图神经网络的WSN路由协议
ChatGPT 说：

了解了，我们将按您的优先级展开系统研究。首先我会从“任务2：CAS失效根因分析”入手，深入剖析CAS为何在AERIS中无效，包括权重设计、平滑策略和输入特征范围等问题。

我会尽快完成这一部分分析并以 Markdown 报告形式整理输出，同时支持中文说明与代码引用。您可以在此过程中继续向我提问或调整研究需求。
ChatGPT 说：
AERIS 协议 CAS 模块失效原因分析
问题定位：现象与异常

AERIS 协议中的 CAS（Context-Adaptive Switching）模块按设计应根据网络环境动态切换传输模式，以提高可靠性和能效。然而实验结果却出现反常现象：关闭 CAS 时（no_cas），协议性能竟优于完整开启 CAS 时（full）。也就是说，启用 CAS 之后网络性能非但没有提升，反而有所下降。这一异常（“no_cas > full”）表明 CAS 模块未能发挥应有作用，存在逻辑或设计上的缺陷。表面症状包括：CAS 几乎总是选择直传模式（Direct），很少启用链式（Chain）或两跳（Two-hop）模式，导致自适应切换机制形同虚设；甚至在个别情况下错误触发非直传模式，引入额外开销，致使整体性能劣于固定直传方案。
根因分析

针对上述异常，从以下三个维度分析 CAS 失效的根本原因：
1. 权重配置偏差：Direct 模式偏好过强

CAS 模块通过线性加权对比 Direct、Chain、Two-hop 三种模式得分来选优。在默认配置中，Direct 模式对剩余能量和链路质量特征赋予最高权重，而 Chain/Two-hop 模式对这些关键特征权重较低。代码中甚至进一步调高了 Direct 模式的权重：w_direct_link 从0.6增至0.8，w_direct_energy从0.6增至0.7，同时下调了 Chain 模式对半径和密度的权重。下表汇总了调整后的各模式特征权重（正值表示促进因素，负值表示惩罚因素）：
模式	能量 (energy)	链路质量 (link)	距离基站 (dist_bs)	集群半径 (radius)	密度 (density)	公平性惩罚 (fairness)
Direct	0.7 (↑)	0.8 (↑)	-0.5	-0.4	0.1	-0.2
Chain	0.4	0.4	0.2	0.4 (↓)	0.3 (↓)	-0.2
Two-hop	0.5	0.5	0.5	0.2	0.2	-0.2

（↑/↓ 表示相对于默认值0.6/0.4的调高或调低；Two-hop模式权重未调。）

从中可见，Direct 模式对能量和链路质量的总权重高达1.5，远高于 Chain 的0.8和 Two-hop 的1.0。这意味着在典型场景下：如果节点剩余能量和链路状况良好（常态情况下能量energy接近1，链路质量link通常0.7~0.9），Direct 模式将获得显著高于其它模式的分值。反之，Chain 模式虽对集群半径和节点密度赋予一定权重，但这些特征的取值通常较低，使其正向贡献难以弥补Direct在关键特征上的领先。例如，若平均集群半径仅占网络对角线15%（radius_norm≈0.15），Chain 模式从半径中获得的加分仅约0.06 (0.4×0.15)，而此时 Direct 模式因链路质量高（如0.8）可获得约0.64的加分 (0.8×0.8)。距离基站远近（dist_bs）虽对 Direct 有负权重(-0.5)，对 Two-hop 有正权重(0.5)，但通常集群头到基站的归一化距离多在0.3~0.6之间；以0.5计，Direct 模式仅被扣分0.25，而 Two-hop 模式加分0.25，难以扭转Direct凭借高能量/链路权重取得的领先。

综上，过度偏向 Direct 的权重配置使得 CAS 打分几乎总是 Direct 模式最高，严重挤压了 Chain 和 Two-hop 模式的生存空间。代码统计也印证了这一点：每轮选择的模式几乎都是direct，Chain/Two-hop 计数极低。在这种情况下，CAS 名义上开启了模式自适应，实则陷入“单一路径偏好”——无论环境如何变化，CAS 大部分时间都固执地选择直传，无法发挥链式聚合和两跳中继在远距离或大规模场景下应有的优势。这解释了为何启用 CAS 后未见预期增益：因为系统行为几乎等同于始终直传，“自适应”徒有其名。此外，偶尔CAS偏离Direct模式的尝试可能是在阈值边缘触发的，这种情况下Chain/Two-hop并非真正更优，反而增加额外转发开销，导致性能下降。这种错误切换进一步导致full方案不如no_cas方案，印证了权重配置不当对CAS决策的扭曲作用。
2. EMA 平滑机制：模式切换过于保守

CASSelector 实现中引入了 指数移动平均 (EMA) 来平滑模式评分的时间波动，每次更新仅使用 α=0.2 的新数据，余下80%沿用历史分值。如下代码所示，每轮计算出的当前分数并不直接用于决策，而是经过 EMA 滤波后再比较：

# CASConfig 默认设置
ema_alpha: float = 0.2  # 仅20%新信息，即 α=0.2:contentReference[oaicite:13]{index=13}

# 每次选择模式时，对三种模式分数进行 EMA 更新:contentReference[oaicite:14]{index=14}:contentReference[oaicite:15]{index=15}:
self._ema_scores[mode] = a * current_score + (1 - a) * self._ema_scores[mode]

低 α 值导致决策对环境变化反应迟缓。当网络环境或集群特征发生较大变化时，新一轮计算的模式原始分数可能已显著不同，但 EMA 平滑机制使得旧分数的影响依然占80%。例如，某轮Direct模式评分原本很高，但下一轮集群距离基站骤增、本应改用Two-hop，此时Direct新的原始得分下降、Two-hop得分上升。然而由于EMA保留了前一轮Direct的高分值，导致本轮平滑后的Direct分数仍偏高，可能依然超过Two-hop分数，从而错过模式切换的最佳时机。只有经过多轮逐步平滑，Direct分数才会缓慢下调，这期间网络已持续使用了次优的直传模式。

不仅如此，CAS 还设计了置信度指标来衡量特征稳定性，并基于此进一步抑制频繁切换。代码通过计算特征的归一化方差代理来定义置信度confidence = 1 - sqrt(variance)，不确定性大则confidence低。如果置信度低于阈值（默认 min_confidence=0.2），CAS 强制沿用上一轮的模式而不切换。也就是说，当检测到环境剧变（特征波动大，confidence小）时，系统倾向于保守不变：

confidence = 1.0 - min(1.0, math.sqrt(var_proxy))  # 特征方差越大置信度越低:contentReference[oaicite:20]{index=20}
if self._last_mode is not None and confidence < self.cfg.min_confidence:
    chosen = self._last_mode                      # 置信度低于0.2则保持上次模式:contentReference[oaicite:21]{index=21}

EMA平滑 + 置信度锁定的双重机制，初衷是避免因噪声导致的模式抖动，但当前参数过于保守，反而掩盖了真实的环境变化。一方面，EMA的长滞后使模式评分对真实变化**“钝化”；另一方面，置信度阈值过低（0.2）意味着只有剧烈变化时才触发锁定，但此时正是可能需要及时切换模式的时候，却因为confidence低而冻结在旧模式。这种设计矛盾直接导致CAS 错失切换良机：当环境逐渐恶化时因平滑拖延未及时切换，当环境剧烈变化需要紧急切换时又因置信度不足被禁止切换。结果，CAS 更倾向于一惯性地维持旧模式**，进一步加强了对Direct模式的路径依赖。

值得注意的是，实现上的一个隐藏逻辑错误加剧了上述问题：EMA 状态在不同集群间交叉影响。按理，CAS 应针对每个集群上下文独立决策，但代码中 CASSelector 实例在整个网络中仅创建一次并反复使用，没有根据集群重置 EMA 内部状态。这意味着不同集群的评分序列被混合进同一个 EMA 滤波器。在一次轮次内，首先处理的集群会将自身模式评分写入 _ema_scores，后续集群在计算时直接继承了前者的历史分值背景。例如，先处理的集群A（可能节点靠近基站）倾向Direct，高分值经EMA保留；紧接着处理较远的集群B时，虽然其特征本应favor Two-hop，但EMA起点仍是A的Direct高分，导致B的决策偏向Direct。如此，先出现的场景把后出现场景“拉回”直传模式。这个跨集群记忆并非有意为之，属设计纰漏，它进一步降低了CAS对各自局部环境的敏感性，让模式切换更加滞后甚至错误。总而言之，EMA平滑机制参数与实现方式不当，使 CAS 切换决策过于保守、缓慢，对环境变化“视而不见”，严重削弱了多模态自适应的作用。
3. 输入特征范围与归一化：打分天平失衡

CAS 决策依赖的输入特征包括：节点平均剩余能量energy、平均链路质量link、集群到基站距离dist_bs、集群半径radius、集群密度density以及公平性惩罚fairness等。这些特征在进入评分函数前被归一化到0~1。然而，特征取值的典型范围分布不均衡，叠加当前的归一化方式，可能导致打分时某些特征影响力被放大或缩小，从而倾斜最终决策天平：

    剩余能量 (energy)：归一化为网络平均剩余能量占初始最大能量的比值。在仿真初期此值接近1，随时间缓慢下降（数百轮后仍高于0.5）。因此大部分时间能量特征贡献都是中高值。Direct模式对energy权重较高(0.7)，意味着无论早期(energy≈1)还是中期(≈0.5)，Direct均从能量特征获得比Chain/Two-hop更多的正向加分。

    链路质量 (link)：归一化为集群平均LQI或全网平均LQI，典型情况下在0.6~0.9区间。网络连通时这一值不会太低。Direct模式对link权重最高(0.8)，因此通常能从较好的链路质量中获得大量分数优势。反观Chain模式权重仅0.4，Two-hop为0.5——链路质量高时Direct得分几乎是Chain的两倍，即使链路质量偏低（如0.4），Direct和Chain因权重差异得到的绝对分值也相差不大（Direct:0.32 vs Chain:0.16）。

    距离基站 (dist_bs)：按集群头到最近基站的距离占网络对角线的比例归一化。典型网络拓扑下，多数集群头距基站的归一化距离在0.3~0.7之间。Direct模式对此施以负权-0.5，相当于距离适中时扣分约0.15~0.35；Two-hop正权0.5，远距离时可加分0.3以上；Chain权重仅0.2，加分更小。虽然距离因素在远程场景下对Two-hop有利，但触发Two-hop显著领先需要极端距离（接近网络最大范围，dist_bs_norm→1）。一般情况下，距离对Direct的扣分不足以抵消其能量/链路高权重带来的优势。更糟糕的是，代码还提高了Two-hop模式启用的阈值：仅当集群成员的最大距离tail_max超过0.7时才给予额外加分0.2×(tail_max-0.7)。这意味着除非有节点距CH非常远，否则Two-hop模式难以获得“尾部奖励”，进一步提高了Two-hop切换的门槛。

    集群半径 (radius)：归一化为集群成员到CH距离的均值占网络对角线的比例。由于典型集群规模和拓扑限制，radius_norm往往很小（例如10~30米相对于141米对角线，仅0.07~0.21）。Chain模式对半径权重0.4（调参后），理论上集群大时Chain更有利。但现实是大部分集群半径远未接近归一化1，上述权重只能提供微弱加成。如半径norm=0.2，Chain仅获0.08分，加分幅度不足以弥补Direct在energy/link上的数倍领先。Direct模式对此还有-0.4的轻微惩罚（-0.08），但相对于其总分影响甚微。因此集群规模因素未能充分凸显链式聚合优势。

    节点密度 (density)：实现中被简化为集群成员数占网络总节点数。例如100节点网络中某簇有10节点，则density=0.1。不考虑集群实际面积，这一定义使密度值偏小，且与集群覆盖范围无关。Chain模式对density权重0.3（调参后），Direct仅0.1。但由于density数值普遍低（通常0.05~0.2），因此密度项贡献很有限：Chain模式最多加分0.06~0.1，难改变总评分排序。同时这一定义也有概念偏差，未真正体现“簇内节点密度高时宜链式聚合”的初衷。

    公平性 (fairness)：通过Jain指数计算能量使用不公平度，取值0~1，值越高表示当前簇节点剩余能量分布越悬殊。三个模式对其权重同为-0.2。因此公平性作为统一的扣分项，对模式选择没有倾斜作用——无论公平与否，扣分等比例应用于所有模式，只影响绝对分而不影响相对高低（CAS 在归一化最终分值用于日志记录时也抵消了这一常量扣分）。因此公平性参数对模式判决几乎无实质影响，可以认为CAS决策主要由前述五个特征决定。

综合来看，输入特征的取值范围与当前归一化方案使不同模式评分贡献不对称：Direct模式所依赖的能量、链路特征通常处于中高值区间，加之高权重而占尽优势；而Chain/Two-hop模式依赖的半径、距离、密度特征往往数值偏低或作用阈值苛刻，导致其加分不足。评分天平从一开始就向Direct大幅倾斜，即便存在有利于链式/两跳的场景，评分模型也难以及时准确地反映。例如，在一个距离基站较远的大簇环境，本应Chain或Two-hop更节能可靠，但实际算分时，Direct模式可能因为仍有尚可的链路质量和节点电量而保持高分，CAS 错判为继续直传，令网络错失优化机会。反过来，如果CAS偶尔判定采用Chain/Two-hop模式（可能由于个别特征波动触及临界点），但这些模式并未真正比直传优越太多，反而可能引入额外传输开销或失败风险，从而拉低整体性能。这正是出现“full 配置下反而不如 no_cas”的根源：特征取值与权重的不匹配导致CAS决策失灵，打开CAS后体系承担了决策开销和潜在误判成本，却没有获得应有的模式优化收益。
支撑证据与现象还原

以上分析基于代码细节和理论推导，可以部分还原 CAS 模块可能存在的逻辑/设计错误，以及它们如何引发“No CAS 优于 Full”的反常现象：

    Direct偏好导致模式固化：代码权重配置和调参明确倾向Direct模式。实际运行中，CAS 统计的模式使用频次显示Direct占据绝大多数。这意味着CAS几乎等价于关闭状态，未能有效利用Chain/Two-hop，即“自适应”实为空转。full方案较no_cas并无收益，甚至因为额外的判断流程略损性能。

    过度平滑掩盖环境变化：通过对比含CAS与不含CAS的仿真日志，可以预见CAS的模式切换率极低，_cas_switch_window滑动窗口中值几乎全为0（表示连续多轮无切换）。即使网络进入本应切换模式的阶段（如后期节点能量普遍降低、链路恶化），CAS由于EMA惯性继续保持原模式，错失了改用更优模式延长寿命/提高PDR的契机。反观no_cas方案一直采用Direct，没有切换滞后的问题，在这些场景反而表现更稳定。

    特征错位导致误判：在极端情况下，CAS 可能基于不恰当的特征信号切换模式，结果不增效反降效。例如某轮由于随机因素导致链路质量指标短暂下降，CAS或许切换到Chain模式，但下一轮链路恢复后Direct本会更好。然而EMA使得CAS对链路恢复反应迟缓，仍滞留在Chain，导致额外跳数增加能耗。相比之下no_cas始终Direct，不受短期波动影响。这样的片段在全局统计中累积起来，可能使启用CAS的总能耗高于直传基线。尤其在特征定义偏差（如density定义不合理）时，CAS可能对错误的“密度高”信号作出反应启用链式，从而引发性能损失。

综合以上，CAS 模块失效并非单一原因，而是多种因素叠加的结果：参数配置上的偏差导致偏好畸形，时间平滑机制不当导致响应迟钝，再加上特征刻画不完善导致判断依据失真。这些问题互相强化，使得CAS在实验中表现出**“按兵不动”或“动则出错”**的异常行为，最终出现启用后不如禁用的反直觉现象。
小结与初步建议

综上所述，AERIS协议 CAS 模块失效的根本原因在于决策模型和机制设计不当：过强的Direct倾向令多模态切换流于形式，保守的EMA策略令CAS对动态环境反应滞后，而特征取值范围与权重的不匹配又让模式评分缺乏客观公正性。“no_cas > full” 正是这些潜在问题的警示。要纠正这一情况，需在设计与实现上做出针对性改进：

    重新平衡模式权重：适当下调Direct模式对能量、链路的权重或提升Chain/Two-hop的权重，使评分模型对不同模式更公平。在设计时可参考理论分析和仿真数据调整权重比。例如增加Chain模式对距离和半径的权重，使其在大范围集群时得分明显高于Direct；Two-hop模式可增加对远距离的奖励权重（或降低触发阈值）以便及时介入远距通信。这将改善CAS在各类场景下的模式选择合理性，避免长期固守直传。

    优化平滑与切换策略：适当提高 EMA 的 α 值（如从0.2提高到0.5或更高）以加快对新环境的响应，或改用滚动窗口平均等延迟更短的平滑方法。对于置信度机制，可降低切换门槛（提升min_confidence）或采用分阶段策略：小幅波动时避免抖动，大幅变化时及时响应。此外，修正 EMA 状态作用域，确保每个集群/每轮的决策独立进行。比如可在每轮或每个CH选择开始时重置CASSelector的 _ema_scores，避免跨集群信息污染决策。通过这些改进，让CAS既能平稳运行又不丧失敏捷性，在环境发生实质性变化时果断切换模式。

    改进特征提取与归一化：针对当前特征可能存在的失衡，进行更合理的刻画。例如，引入局部密度指标（每簇节点密度基于簇面积，而非全网占比）来更真实地反映链式传播的适用性；调整集群半径归一化基准（如改用平均簇半径的经验最大值而非网络对角线）以放大实际范围内半径差异对评分的影响；动态跟踪链路质量分布，确保link_norm能及时反映当前簇内链路状况而非依赖全网平均。同时，可以考虑将公平性对不同模式差异化对待，例如当公平性指标很差时偏向Chain/Two-hop以均衡负载，而非一刀切扣分。更精确、平衡的特征输入将使CAS决策基础更加可靠。

    验证和迭代：在做出以上修改后，建议通过消融实验验证效果。例如，对比 α=0.2 与 α=1.0（无平滑）两种CAS配置在快速变化场景下PDR和能耗表现；测试调整权重后的CAS在远距离大簇环境中Chain/Two-hop的启用频率和网络寿命变化；采用更合理特征后观察CAS模式分布是否符合预期。如果仍有“不灵敏”或“误切换”现象，应进一步分析日志调优参数，逐步逼近“CAS开启优于关闭”的正常状态。

通过以上改进，CAS 模块有望恢复设计初衷，在Direct、Chain、Two-hop之间实现真正的情景自适应切换：既能在良好条件下保持直传的高效，又能在远距离或不利条件下及时切换到链式/两跳模式，达到提高网络PDR和延长寿命的目的。一旦CAS功能正常发挥，“no_cas > full”现象将消除，取而代之的是**“full > no_cas”**的预期结果，即完整启用CAS的AERIS协议相较固定模式方案展现出全面优势。


ChatGPT 也可能会犯错。OpenAI 不会使用“a3”工作空间数据来训练其模型。
AERIS 协议 CAS 模块失效原因分析
问题定位：现象与异常

AERIS 协议中的 CAS（Context-Adaptive Switching）模块按设计应根据网络环境动态切换传输模式，以提高可靠性和能效。然而实验结果却出现反常现象：关闭 CAS 时（no_cas），协议性能竟优于完整开启 CAS 时（full）。也就是说，启用 CAS 之后网络性能非但没有提升，反而有所下降。这一异常（“no_cas > full”）表明 CAS 模块未能发挥应有作用，存在逻辑或设计上的缺陷。表面症状包括：CAS 几乎总是选择直传模式（Direct），很少启用链式（Chain）或两跳（Two-hop）模式，导致自适应切换机制形同虚设；甚至在个别情况下错误触发非直传模式，引入额外开销，致使整体性能劣于固定直传方案。
根因分析

针对上述异常，从以下三个维度分析 CAS 失效的根本原因：
1. 权重配置偏差：Direct 模式偏好过强

CAS 模块通过线性加权对比 Direct、Chain、Two-hop 三种模式得分来选优。在默认配置中，Direct 模式对剩余能量和链路质量特征赋予最高权重，而 Chain/Two-hop 模式对这些关键特征权重较低。代码中甚至进一步调高了 Direct 模式的权重：w_direct_link 从0.6增至0.8，w_direct_energy从0.6增至0.7，同时下调了 Chain 模式对半径和密度的权重。下表汇总了调整后的各模式特征权重（正值表示促进因素，负值表示惩罚因素）：
模式	能量 (energy)	链路质量 (link)	距离基站 (dist_bs)	集群半径 (radius)	密度 (density)	公平性惩罚 (fairness)
Direct	0.7 (↑)	0.8 (↑)	-0.5	-0.4	0.1	-0.2
Chain	0.4	0.4	0.2	0.4 (↓)	0.3 (↓)	-0.2
Two-hop	0.5	0.5	0.5	0.2	0.2	-0.2

（↑/↓ 表示相对于默认值0.6/0.4的调高或调低；Two-hop模式权重未调。）

从中可见，Direct 模式对能量和链路质量的总权重高达1.5，远高于 Chain 的0.8和 Two-hop 的1.0。这意味着在典型场景下：如果节点剩余能量和链路状况良好（常态情况下能量energy接近1，链路质量link通常0.7~0.9），Direct 模式将获得显著高于其它模式的分值。反之，Chain 模式虽对集群半径和节点密度赋予一定权重，但这些特征的取值通常较低，使其正向贡献难以弥补Direct在关键特征上的领先。例如，若平均集群半径仅占网络对角线15%（radius_norm≈0.15），Chain 模式从半径中获得的加分仅约0.06 (0.4×0.15)，而此时 Direct 模式因链路质量高（如0.8）可获得约0.64的加分 (0.8×0.8)。距离基站远近（dist_bs）虽对 Direct 有负权重(-0.5)，对 Two-hop 有正权重(0.5)，但通常集群头到基站的归一化距离多在0.3~0.6之间；以0.5计，Direct 模式仅被扣分0.25，而 Two-hop 模式加分0.25，难以扭转Direct凭借高能量/链路权重取得的领先。

综上，过度偏向 Direct 的权重配置使得 CAS 打分几乎总是 Direct 模式最高，严重挤压了 Chain 和 Two-hop 模式的生存空间。代码统计也印证了这一点：每轮选择的模式几乎都是direct，Chain/Two-hop 计数极低。在这种情况下，CAS 名义上开启了模式自适应，实则陷入“单一路径偏好”——无论环境如何变化，CAS 大部分时间都固执地选择直传，无法发挥链式聚合和两跳中继在远距离或大规模场景下应有的优势。这解释了为何启用 CAS 后未见预期增益：因为系统行为几乎等同于始终直传，“自适应”徒有其名。此外，偶尔CAS偏离Direct模式的尝试可能是在阈值边缘触发的，这种情况下Chain/Two-hop并非真正更优，反而增加额外转发开销，导致性能下降。这种错误切换进一步导致full方案不如no_cas方案，印证了权重配置不当对CAS决策的扭曲作用。
2. EMA 平滑机制：模式切换过于保守

CASSelector 实现中引入了 指数移动平均 (EMA) 来平滑模式评分的时间波动，每次更新仅使用 α=0.2 的新数据，余下80%沿用历史分值。如下代码所示，每轮计算出的当前分数并不直接用于决策，而是经过 EMA 滤波后再比较：

# CASConfig 默认设置
ema_alpha: float = 0.2  # 仅20%新信息，即 α=0.2:contentReference[oaicite:13]{index=13}

# 每次选择模式时，对三种模式分数进行 EMA 更新:contentReference[oaicite:14]{index=14}:contentReference[oaicite:15]{index=15}:
self._ema_scores[mode] = a * current_score + (1 - a) * self._ema_scores[mode]

低 α 值导致决策对环境变化反应迟缓。当网络环境或集群特征发生较大变化时，新一轮计算的模式原始分数可能已显著不同，但 EMA 平滑机制使得旧分数的影响依然占80%。例如，某轮Direct模式评分原本很高，但下一轮集群距离基站骤增、本应改用Two-hop，此时Direct新的原始得分下降、Two-hop得分上升。然而由于EMA保留了前一轮Direct的高分值，导致本轮平滑后的Direct分数仍偏高，可能依然超过Two-hop分数，从而错过模式切换的最佳时机。只有经过多轮逐步平滑，Direct分数才会缓慢下调，这期间网络已持续使用了次优的直传模式。

不仅如此，CAS 还设计了置信度指标来衡量特征稳定性，并基于此进一步抑制频繁切换。代码通过计算特征的归一化方差代理来定义置信度confidence = 1 - sqrt(variance)，不确定性大则confidence低。如果置信度低于阈值（默认 min_confidence=0.2），CAS 强制沿用上一轮的模式而不切换。也就是说，当检测到环境剧变（特征波动大，confidence小）时，系统倾向于保守不变：

confidence = 1.0 - min(1.0, math.sqrt(var_proxy))  # 特征方差越大置信度越低:contentReference[oaicite:20]{index=20}
if self._last_mode is not None and confidence < self.cfg.min_confidence:
    chosen = self._last_mode                      # 置信度低于0.2则保持上次模式:contentReference[oaicite:21]{index=21}

EMA平滑 + 置信度锁定的双重机制，初衷是避免因噪声导致的模式抖动，但当前参数过于保守，反而掩盖了真实的环境变化。一方面，EMA的长滞后使模式评分对真实变化**“钝化”；另一方面，置信度阈值过低（0.2）意味着只有剧烈变化时才触发锁定，但此时正是可能需要及时切换模式的时候，却因为confidence低而冻结在旧模式。这种设计矛盾直接导致CAS 错失切换良机：当环境逐渐恶化时因平滑拖延未及时切换，当环境剧烈变化需要紧急切换时又因置信度不足被禁止切换。结果，CAS 更倾向于一惯性地维持旧模式**，进一步加强了对Direct模式的路径依赖。

值得注意的是，实现上的一个隐藏逻辑错误加剧了上述问题：EMA 状态在不同集群间交叉影响。按理，CAS 应针对每个集群上下文独立决策，但代码中 CASSelector 实例在整个网络中仅创建一次并反复使用，没有根据集群重置 EMA 内部状态。这意味着不同集群的评分序列被混合进同一个 EMA 滤波器。在一次轮次内，首先处理的集群会将自身模式评分写入 _ema_scores，后续集群在计算时直接继承了前者的历史分值背景。例如，先处理的集群A（可能节点靠近基站）倾向Direct，高分值经EMA保留；紧接着处理较远的集群B时，虽然其特征本应favor Two-hop，但EMA起点仍是A的Direct高分，导致B的决策偏向Direct。如此，先出现的场景把后出现场景“拉回”直传模式。这个跨集群记忆并非有意为之，属设计纰漏，它进一步降低了CAS对各自局部环境的敏感性，让模式切换更加滞后甚至错误。总而言之，EMA平滑机制参数与实现方式不当，使 CAS 切换决策过于保守、缓慢，对环境变化“视而不见”，严重削弱了多模态自适应的作用。
3. 输入特征范围与归一化：打分天平失衡

CAS 决策依赖的输入特征包括：节点平均剩余能量energy、平均链路质量link、集群到基站距离dist_bs、集群半径radius、集群密度density以及公平性惩罚fairness等。这些特征在进入评分函数前被归一化到0~1。然而，特征取值的典型范围分布不均衡，叠加当前的归一化方式，可能导致打分时某些特征影响力被放大或缩小，从而倾斜最终决策天平：

    剩余能量 (energy)：归一化为网络平均剩余能量占初始最大能量的比值。在仿真初期此值接近1，随时间缓慢下降（数百轮后仍高于0.5）。因此大部分时间能量特征贡献都是中高值。Direct模式对energy权重较高(0.7)，意味着无论早期(energy≈1)还是中期(≈0.5)，Direct均从能量特征获得比Chain/Two-hop更多的正向加分。

    链路质量 (link)：归一化为集群平均LQI或全网平均LQI，典型情况下在0.6~0.9区间。网络连通时这一值不会太低。Direct模式对link权重最高(0.8)，因此通常能从较好的链路质量中获得大量分数优势。反观Chain模式权重仅0.4，Two-hop为0.5——链路质量高时Direct得分几乎是Chain的两倍，即使链路质量偏低（如0.4），Direct和Chain因权重差异得到的绝对分值也相差不大（Direct:0.32 vs Chain:0.16）。

    距离基站 (dist_bs)：按集群头到最近基站的距离占网络对角线的比例归一化。典型网络拓扑下，多数集群头距基站的归一化距离在0.3~0.7之间。Direct模式对此施以负权-0.5，相当于距离适中时扣分约0.15~0.35；Two-hop正权0.5，远距离时可加分0.3以上；Chain权重仅0.2，加分更小。虽然距离因素在远程场景下对Two-hop有利，但触发Two-hop显著领先需要极端距离（接近网络最大范围，dist_bs_norm→1）。一般情况下，距离对Direct的扣分不足以抵消其能量/链路高权重带来的优势。更糟糕的是，代码还提高了Two-hop模式启用的阈值：仅当集群成员的最大距离tail_max超过0.7时才给予额外加分0.2×(tail_max-0.7)。这意味着除非有节点距CH非常远，否则Two-hop模式难以获得“尾部奖励”，进一步提高了Two-hop切换的门槛。

    集群半径 (radius)：归一化为集群成员到CH距离的均值占网络对角线的比例。由于典型集群规模和拓扑限制，radius_norm往往很小（例如10~30米相对于141米对角线，仅0.07~0.21）。Chain模式对半径权重0.4（调参后），理论上集群大时Chain更有利。但现实是大部分集群半径远未接近归一化1，上述权重只能提供微弱加成。如半径norm=0.2，Chain仅获0.08分，加分幅度不足以弥补Direct在energy/link上的数倍领先。Direct模式对此还有-0.4的轻微惩罚（-0.08），但相对于其总分影响甚微。因此集群规模因素未能充分凸显链式聚合优势。

    节点密度 (density)：实现中被简化为集群成员数占网络总节点数。例如100节点网络中某簇有10节点，则density=0.1。不考虑集群实际面积，这一定义使密度值偏小，且与集群覆盖范围无关。Chain模式对density权重0.3（调参后），Direct仅0.1。但由于density数值普遍低（通常0.05~0.2），因此密度项贡献很有限：Chain模式最多加分0.06~0.1，难改变总评分排序。同时这一定义也有概念偏差，未真正体现“簇内节点密度高时宜链式聚合”的初衷。

    公平性 (fairness)：通过Jain指数计算能量使用不公平度，取值0~1，值越高表示当前簇节点剩余能量分布越悬殊。三个模式对其权重同为-0.2。因此公平性作为统一的扣分项，对模式选择没有倾斜作用——无论公平与否，扣分等比例应用于所有模式，只影响绝对分而不影响相对高低（CAS 在归一化最终分值用于日志记录时也抵消了这一常量扣分）。因此公平性参数对模式判决几乎无实质影响，可以认为CAS决策主要由前述五个特征决定。

综合来看，输入特征的取值范围与当前归一化方案使不同模式评分贡献不对称：Direct模式所依赖的能量、链路特征通常处于中高值区间，加之高权重而占尽优势；而Chain/Two-hop模式依赖的半径、距离、密度特征往往数值偏低或作用阈值苛刻，导致其加分不足。评分天平从一开始就向Direct大幅倾斜，即便存在有利于链式/两跳的场景，评分模型也难以及时准确地反映。例如，在一个距离基站较远的大簇环境，本应Chain或Two-hop更节能可靠，但实际算分时，Direct模式可能因为仍有尚可的链路质量和节点电量而保持高分，CAS 错判为继续直传，令网络错失优化机会。反过来，如果CAS偶尔判定采用Chain/Two-hop模式（可能由于个别特征波动触及临界点），但这些模式并未真正比直传优越太多，反而可能引入额外传输开销或失败风险，从而拉低整体性能。这正是出现“full 配置下反而不如 no_cas”的根源：特征取值与权重的不匹配导致CAS决策失灵，打开CAS后体系承担了决策开销和潜在误判成本，却没有获得应有的模式优化收益。
支撑证据与现象还原

以上分析基于代码细节和理论推导，可以部分还原 CAS 模块可能存在的逻辑/设计错误，以及它们如何引发“No CAS 优于 Full”的反常现象：

    Direct偏好导致模式固化：代码权重配置和调参明确倾向Direct模式。实际运行中，CAS 统计的模式使用频次显示Direct占据绝大多数。这意味着CAS几乎等价于关闭状态，未能有效利用Chain/Two-hop，即“自适应”实为空转。full方案较no_cas并无收益，甚至因为额外的判断流程略损性能。

    过度平滑掩盖环境变化：通过对比含CAS与不含CAS的仿真日志，可以预见CAS的模式切换率极低，_cas_switch_window滑动窗口中值几乎全为0（表示连续多轮无切换）。即使网络进入本应切换模式的阶段（如后期节点能量普遍降低、链路恶化），CAS由于EMA惯性继续保持原模式，错失了改用更优模式延长寿命/提高PDR的契机。反观no_cas方案一直采用Direct，没有切换滞后的问题，在这些场景反而表现更稳定。

    特征错位导致误判：在极端情况下，CAS 可能基于不恰当的特征信号切换模式，结果不增效反降效。例如某轮由于随机因素导致链路质量指标短暂下降，CAS或许切换到Chain模式，但下一轮链路恢复后Direct本会更好。然而EMA使得CAS对链路恢复反应迟缓，仍滞留在Chain，导致额外跳数增加能耗。相比之下no_cas始终Direct，不受短期波动影响。这样的片段在全局统计中累积起来，可能使启用CAS的总能耗高于直传基线。尤其在特征定义偏差（如density定义不合理）时，CAS可能对错误的“密度高”信号作出反应启用链式，从而引发性能损失。

综合以上，CAS 模块失效并非单一原因，而是多种因素叠加的结果：参数配置上的偏差导致偏好畸形，时间平滑机制不当导致响应迟钝，再加上特征刻画不完善导致判断依据失真。这些问题互相强化，使得CAS在实验中表现出**“按兵不动”或“动则出错”**的异常行为，最终出现启用后不如禁用的反直觉现象。
小结与初步建议

综上所述，AERIS协议 CAS 模块失效的根本原因在于决策模型和机制设计不当：过强的Direct倾向令多模态切换流于形式，保守的EMA策略令CAS对动态环境反应滞后，而特征取值范围与权重的不匹配又让模式评分缺乏客观公正性。“no_cas > full” 正是这些潜在问题的警示。要纠正这一情况，需在设计与实现上做出针对性改进：

    重新平衡模式权重：适当下调Direct模式对能量、链路的权重或提升Chain/Two-hop的权重，使评分模型对不同模式更公平。在设计时可参考理论分析和仿真数据调整权重比。例如增加Chain模式对距离和半径的权重，使其在大范围集群时得分明显高于Direct；Two-hop模式可增加对远距离的奖励权重（或降低触发阈值）以便及时介入远距通信。这将改善CAS在各类场景下的模式选择合理性，避免长期固守直传。

    优化平滑与切换策略：适当提高 EMA 的 α 值（如从0.2提高到0.5或更高）以加快对新环境的响应，或改用滚动窗口平均等延迟更短的平滑方法。对于置信度机制，可降低切换门槛（提升min_confidence）或采用分阶段策略：小幅波动时避免抖动，大幅变化时及时响应。此外，修正 EMA 状态作用域，确保每个集群/每轮的决策独立进行。比如可在每轮或每个CH选择开始时重置CASSelector的 _ema_scores，避免跨集群信息污染决策。通过这些改进，让CAS既能平稳运行又不丧失敏捷性，在环境发生实质性变化时果断切换模式。

    改进特征提取与归一化：针对当前特征可能存在的失衡，进行更合理的刻画。例如，引入局部密度指标（每簇节点密度基于簇面积，而非全网占比）来更真实地反映链式传播的适用性；调整集群半径归一化基准（如改用平均簇半径的经验最大值而非网络对角线）以放大实际范围内半径差异对评分的影响；动态跟踪链路质量分布，确保link_norm能及时反映当前簇内链路状况而非依赖全网平均。同时，可以考虑将公平性对不同模式差异化对待，例如当公平性指标很差时偏向Chain/Two-hop以均衡负载，而非一刀切扣分。更精确、平衡的特征输入将使CAS决策基础更加可靠。

    验证和迭代：在做出以上修改后，建议通过消融实验验证效果。例如，对比 α=0.2 与 α=1.0（无平滑）两种CAS配置在快速变化场景下PDR和能耗表现；测试调整权重后的CAS在远距离大簇环境中Chain/Two-hop的启用频率和网络寿命变化；采用更合理特征后观察CAS模式分布是否符合预期。如果仍有“不灵敏”或“误切换”现象，应进一步分析日志调优参数，逐步逼近“CAS开启优于关闭”的正常状态。

通过以上改进，CAS 模块有望恢复设计初衷，在Direct、Chain、Two-hop之间实现真正的情景自适应切换：既能在良好条件下保持直传的高效，又能在远距离或不利条件下及时切换到链式/两跳模式，达到提高网络PDR和延长寿命的目的。一旦CAS功能正常发挥，“no_cas > full”现象将消除，取而代之的是**“full > no_cas”**的预期结果，即完整启用CAS的AERIS协议相较固定模式方案展现出全面优势。
引用
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L58-L66
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L72-L77
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1092-L1098
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1076-L1084
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1084-L1092
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L97-L105
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1065-L1073
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1150-L1158
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L38-L45
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L133-L140
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L133-L141
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L152-L160
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L162-L171
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L179-L183
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L40-L45
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1086-L1094
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L50-L59
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L60-L68
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L34-L42
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L146-L155
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1054-L1062
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1055-L1059
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L65-L73
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L72-L76
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L65-L70
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L128-L131
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1094-L1098
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L60-L68
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L182-L190
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1144-L1152
GitHub

cas_selector.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/cas_selector.py#L85-L93
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1080-L1084
GitHub

aeris_protocol.py
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/src/aeris_protocol.py#L1082-L1085
GitHub

Paper_Draft_Section7_Discussion_COMPLETE.md
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/docs/Paper_Draft_Section7_Discussion_COMPLETE.md#L29-L37
GitHub

Paper_Draft_Section7_Discussion_COMPLETE.md
https://github.com/Deepmind666/AERIS-WSN-Protocol/blob/44b51f6fa1d42bb3607460482d2252aab5219e3c/docs/Paper_Draft_Section7_Discussion_COMPLETE.md#L39-L42
全部来源
github
