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
```
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
```

### 统计显著性检验（Welch t-test, vs full）
```
变体           差异(pp)    p值          效应量d    结论
----------------------------------------------------------
no_gateway     -1.64       8.49e-29     1.21       显著，Gateway有效
skeleton_only  -1.44       2.25e-25     1.12       显著
minimal        -1.25       3.84e-19     0.94       显著
cas_only       -1.19       2.30e-18     0.92       显著
no_cas         +0.28       0.057        -          不显著
no_skeleton    +0.12       0.392        -          不显著
gateway_only   +0.14       0.294        -          不显著
```

### 核心异常发现
1. **Gateway模块有效**：移除后PDR显著下降1.64pp (p=8.49e-29)
2. **CAS模块无效**：移除后PDR反而上升0.28pp (p=0.057，不显著)
3. **Skeleton模块无效**：移除后PDR上升0.12pp (p=0.392，不显著)
4. **模块组合问题**：full(88.2%) < no_cas(88.5%)，启用CAS反而更差

## 三、CAS模块关键代码

### 3.1 CAS权重配置 (cas_selector.py)
```python
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
```

### 3.2 CAS评分函数
```python
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
```

### 3.3 模式选择逻辑
```python
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
```

## 四、transmit_to_bs重试机制（可能掩盖模块差异）

```python
# lightweight模式参数
arq_retries = 3          # ARQ重试次数
power_steps = [0.0, 3.0] # 功率阶梯
parent_copies = 2        # 父节点副本数
rescue_candidates = 2    # 救援候选数
direct_tries = 8         # 直达尝试次数
```

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

## 七、高难度技术问题（需深度研究）

### 问题1：CAS权重数学分析
给定输入特征范围 energy∈[0,1], link∈[0,1], dist_bs∈[0,1]：
- 计算在什么条件下DIRECT得分会超过CHAIN/TWO_HOP
- 当前权重是否存在数学上的偏差？
- 如何设计权重使三种模式有合理的触发条件？

### 问题2：重试机制与模块效果的关系
lightweight模式下总重试次数估算：
- 父节点：2副本 × 2功率 × 3ARQ = 12次
- 救援：2候选 × 2功率 × 3ARQ = 12次
- 直达：8次 × 2功率 × 3ARQ = 48次
- 总计约72次重试机会

问题：如此多的重试是否会"抹平"CAS模式选择的差异？

### 问题3：CHAIN/TWO_HOP模式的丢包风险
```
DIRECT: 每个节点独立传输，失败只影响单节点
CHAIN: 链式传输，任一跳失败导致后续全部丢失
TWO_HOP: relay失败导致所有relay_payload丢失
```
问题：CHAIN/TWO_HOP的级联丢包是否导致CAS"学会"了只选DIRECT？

### 问题4：WSN领域2023-2025最新进展
搜索以下方向的最新论文：
- 基于强化学习的WSN路由（DQN/PPO/A3C）
- 基于图神经网络的WSN优化
- 联邦学习在WSN中的应用
- 能量收集WSN的路由协议

### 问题5：消融实验设计缺陷分析
当前实验可能存在的问题：
- 200节点是否足够大？
- 600轮是否足够长？
- uniform/corridor31两种拓扑是否足够多样？
- indoor_office信道是否太"友好"？

### 问题6：论文创新点重构
如果CAS确实无效，论文如何定位？
- 方案A：移除CAS，聚焦Gateway创新
- 方案B：承认CAS局限性，作为negative result报告
- 方案C：重新设计CAS（如用RL替代规则）

## 八、需上传的核心文件清单

### 算法核心文件（必须上传）
| 文件 | 说明 | 重点关注 |
|------|------|----------|
| src/aeris_protocol.py | 主协议 | transmit_to_bs函数、_perform_data_transmission |
| src/cas_selector.py | CAS模块 | 权重配置、select_mode函数 |
| src/gateway_selector.py | Gateway模块 | select_gateways函数 |
| src/skeleton_selector.py | Skeleton模块 | build_skeleton函数 |

### 实验配置文件
| 文件 | 说明 |
|------|------|
| scripts/run_mega_experiments.py | 消融实验配置 |

### 能耗与信道模型
| 文件 | 说明 |
|------|------|
| src/improved_energy_model.py | CC2420能耗模型 |
| src/channel_model.py | 信道衰落模型 |

### 基线协议（用于对比）
| 文件 | 说明 |
|------|------|
| src/baseline_protocols/leach_protocol.py | LEACH实现 |
| src/baseline_protocols/pegasis_protocol.py | PEGASIS实现 |
| src/baseline_protocols/heed_protocol.py | HEED实现 |

## 九、文件路径汇总（供上传）

```
必须上传（6个核心文件）：
1. src/aeris_protocol.py
2. src/cas_selector.py
3. src/gateway_selector.py
4. src/skeleton_selector.py
5. src/improved_energy_model.py
6. scripts/run_mega_experiments.py
```
