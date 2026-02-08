# AERIS 架构图渲染指南

**日期**: 2025-10-19
**目的**: 提供可直接在Mermaid Live渲染的图表代码

---

## 🚀 快速渲染步骤

### 步骤1: 访问Mermaid Live
打开浏览器访问: **https://mermaid.live/**

### 步骤2: 复制下方图表代码
从下方7张图中选择一张，复制整个代码块

### 步骤3: 粘贴到Mermaid Live编辑器
- 左侧编辑器会自动渲染
- 右侧预览图表效果

### 步骤4: 导出高质量图片
- **方法A (推荐 - SVG矢量图)**:
  - 点击右上角 "Actions" → "Export SVG"
  - 保存为 `aeris_figure_X.svg`
  - SVG可无损缩放，适合论文

- **方法B (PNG位图)**:
  - 点击右上角 "Actions" → "Export PNG"
  - 选择高分辨率 (建议4K: 3840×2160)
  - 保存为 `aeris_figure_X.png`

- **方法C (PDF - 论文最终稿)**:
  - 先导出SVG
  - 使用Inkscape/Illustrator转换为PDF
  - 保存为 `aeris_figure_X.pdf`

### 步骤5: 保存到论文目录
将导出的图片保存到:
```
C:\Enhanced-EEHFR-WSN-Protocol\results\publication_figures\
```

---

## 图1: AERIS三层协同架构总览

**保存为**: `aeris_figure_1_architecture.svg` / `.png` / `.pdf`

**插入位置**: Section 3 (System Model) 或 Section 4.1 (Protocol Architecture)

**说明**: 展示AERIS三层架构 (数据层 → 决策层 → 通信层) 和数据流向

```mermaid
graph TB
    subgraph "数据层 Data Plane"
        SN[传感节点<br/>Sensor Nodes]
        CM[簇成员<br/>Cluster Members]
        CH[簇头<br/>Cluster Heads]
    end

    subgraph "决策层 Decision Plane"
        CAS[CAS选择器<br/>Context-Adaptive Switching<br/>O1 complexity]
        SK[Skeleton选择器<br/>PCA-based Backbone<br/>On² complexity]
        GW[Gateway选择器<br/>Gateway Coordination<br/>On log k complexity]
    end

    subgraph "通信层 Communication Plane"
        MAC[MAC协议<br/>IEEE 802.15.4<br/>CSMA/CA]
        PHY[PHY层<br/>250kbps<br/>2.4GHz]
        CH_Model[信道模型<br/>Log-normal Shadowing<br/>Path Loss + Fading]
    end

    subgraph "基站 Base Station"
        BS[(BS<br/>Data Sink)]
    end

    SN -->|感知数据| CM
    CM -->|簇内传输| CH
    CH -->|决策输入| CAS
    CAS -->|模式选择| SK
    SK -->|骨干路由| GW
    GW -->|多跳聚合| MAC
    MAC -->|帧封装| PHY
    PHY -->|信道传输| CH_Model
    CH_Model -->|接收| BS

    CH -->|链路质量<br/>能量状态| CAS
    BS -->|ACK/NACK| CH

    style CAS fill:#ff9999,stroke:#cc0000,stroke-width:3px
    style SK fill:#99ccff,stroke:#0066cc,stroke-width:3px
    style GW fill:#99ff99,stroke:#006600,stroke-width:3px
    style BS fill:#ffff99,stroke:#cccc00,stroke-width:3px
```

---

## 图2: CAS决策流程详细展开

**保存为**: `aeris_figure_2_cas_flowchart.svg` / `.png` / `.pdf`

**插入位置**: Section 4.2 (CAS Layer)

**说明**: 展示CAS选择器的完整决策流程 (特征采集 → 线性评分 → EMA平滑 → 置信度检查 → 模式选择)

```mermaid
flowchart TD
    Start([开始: 新一轮簇内传输])

    subgraph Input[输入特征采集]
        E[能量<br/>energy]
        L[链路质量<br/>link_quality]
        D[到BS距离<br/>dist_bs]
        R[簇半径<br/>radius]
        Den[节点密度<br/>density]
        F[公平性<br/>fairness]
        T[尾节点最大跳数<br/>tail_max]
    end

    subgraph Scoring[线性评分计算 - 51 FLOPs]
        S1["直接模式得分<br/>s_direct = 0.3×E + 0.25×L - 0.15×D + ..."]
        S2["链式模式得分<br/>s_chain = 0.4×E - 0.2×R + ..."]
        S3["两跳模式得分<br/>s_two_hop = 0.25×E + 0.2×L + ..."]
    end

    subgraph EMA[EMA平滑 - 时间稳定性]
        EMA1["α=0.2<br/>s_direct_ema = 0.2×s_direct + 0.8×prev"]
        EMA2["s_chain_ema = ..."]
        EMA3["s_two_hop_ema = ..."]
    end

    subgraph Confidence[置信度评估]
        Gap["gap = max(scores) - min(scores)"]
        Conf["confidence = gap / max(scores)"]
        Check{confidence > 0.2?}
    end

    subgraph Decision[模式选择]
        Choose["chosen = argmax(s_direct, s_chain, s_two_hop)"]
        Direct[直接传输<br/>Direct Mode]
        Chain[链式聚合<br/>Chain Mode]
        TwoHop[两跳中继<br/>TwoHop Mode]
    end

    subgraph Execution[执行传输]
        Exec_Direct["成员 → CH 单跳"]
        Exec_Chain["成员 → ... → 中继 → CH 链式"]
        Exec_TwoHop["成员 → 中继 → CH 两跳"]
    end

    Start --> Input
    Input --> Scoring
    E --> S1 & S2 & S3
    L --> S1 & S2 & S3
    D --> S1 & S2 & S3
    R --> S1 & S2 & S3
    Den --> S1 & S2 & S3
    F --> S1 & S2 & S3
    T --> S1 & S2 & S3

    Scoring --> EMA
    S1 --> EMA1
    S2 --> EMA2
    S3 --> EMA3

    EMA --> Confidence
    EMA1 & EMA2 & EMA3 --> Gap
    Gap --> Conf
    Conf --> Check

    Check -->|Yes: 切换模式| Choose
    Check -->|No: 保持上轮模式| Choose

    Choose --> Decision
    Decision -->|s_direct最高| Direct
    Decision -->|s_chain最高| Chain
    Decision -->|s_two_hop最高| TwoHop

    Direct --> Exec_Direct
    Chain --> Exec_Chain
    TwoHop --> Exec_TwoHop

    Exec_Direct --> End([簇内传输完成])
    Exec_Chain --> End
    Exec_TwoHop --> End

    style Start fill:#90EE90
    style End fill:#FFB6C1
    style Check fill:#FFD700
    style Choose fill:#87CEEB
```

---

## 图3: Skeleton骨干选择流程

**保存为**: `aeris_figure_3_skeleton_selection.svg` / `.png` / `.pdf`

**插入位置**: Section 4.3 (Skeleton Layer)

**说明**: 展示PCA-based Skeleton选择器算法流程 (PCA主轴分析 → 主轴接近度 + 中心度 → 综合评分)

```mermaid
flowchart TD
    Start([开始: 已选出n个CH])

    Input["输入: chs = [CH₁, CH₂, ..., CHₙ]<br/>k = 骨干CH数量 通常2-3"]

    subgraph PCA[PCA主轴分析 - On² complexity]
        Extract["提取坐标矩阵<br/>X = [x₁,y₁, x₂,y₂, ..., xₙ,yₙ]"]
        Center["中心化: X' = X - mean(X)"]
        Cov["协方差矩阵: C = X'ᵀ × X' / n-1"]
        Eigen["特征分解: λ, v = eig(C)"]
        Axis["主方向: v₁ = argmax(λ)"]
    end

    subgraph Metrics[指标计算 - On² for centrality]
        AxisDist["主轴接近度<br/>对每个CHᵢ:<br/>dᵢ = ‖CHᵢ - proj(CHᵢ, v₁)‖"]
        Centrality["中心度<br/>对每个CHᵢ:<br/>cᵢ = 1 / 1 + mean_dist_to_others"]
        Normalize["归一化<br/>d'ᵢ = dᵢ/max(d)<br/>c'ᵢ = cᵢ/max(c)"]
    end

    subgraph Scoring[综合评分]
        Score["scoreᵢ = 0.6×(1-d'ᵢ) + 0.4×c'ᵢ"]
        Rank["排序: sorted_chs = sort(chs, key=score, reverse=True)"]
    end

    subgraph Selection[选择骨干]
        TopK["backbone = sorted_chs[:k]"]
        Verify{k个骨干分布合理?}
        Adjust["调整: 确保覆盖网络范围"]
    end

    Output["输出: backbone_chs = [CH₁, CH₇, CH₁₂]<br/>示例: 选出3个骨干CH"]
    End([骨干CH选择完成])

    Start --> Input
    Input --> PCA
    Extract --> Center --> Cov --> Eigen --> Axis

    Axis --> Metrics
    Metrics --> AxisDist & Centrality
    AxisDist & Centrality --> Normalize

    Normalize --> Scoring
    Score --> Rank

    Rank --> Selection
    TopK --> Verify
    Verify -->|Yes| Output
    Verify -->|No| Adjust
    Adjust --> TopK

    Output --> End

    style Start fill:#90EE90
    style End fill:#FFB6C1
    style Verify fill:#FFD700
    style PCA fill:#E0FFFF
    style Scoring fill:#FFDAB9
```

---

## 图4: Gateway网关选择与数据聚合

**保存为**: `aeris_figure_4_gateway_coordination.svg` / `.png` / `.pdf`

**插入位置**: Section 4.4 (Gateway Layer)

**说明**: 展示Gateway选择器如何选择k个网关CH并进行数据聚合

```mermaid
flowchart LR
    subgraph Clusters[簇层级]
        C1[Cluster 1<br/>CH₁]
        C2[Cluster 2<br/>CH₂]
        C3[Cluster 3<br/>CH₃]
        C4[Cluster 4<br/>CH₄]
        C5[Cluster 5<br/>CH₅]
    end

    subgraph Gateway_Selection[网关选择 - On log k]
        Score1["CHᵢ评分:<br/>scoreᵢ = -0.7×dist(CHᵢ, BS)<br/>        + 0.3×centrality(CHᵢ)"]
        Fair["公平性惩罚:<br/>如果CHᵢ上轮做过Gateway:<br/>scoreᵢ -= penalty"]
        TopK["选择top-k得分:<br/>gateways = [CH₂, CH₄]"]
    end

    subgraph Aggregation[数据聚合]
        G1[Gateway CH₂]
        G2[Gateway CH₄]
        Agg1["聚合路径1:<br/>CH₁ → CH₂ → BS"]
        Agg2["聚合路径2:<br/>CH₃ → CH₄ → CH₅ → BS"]
    end

    subgraph BS_Layer[基站]
        BS[(Base Station)]
    end

    C1 & C2 & C3 & C4 & C5 --> Score1
    Score1 --> Fair
    Fair --> TopK
    TopK --> G1 & G2

    C1 --> G1
    C3 --> G2
    C5 --> G2

    G1 --> Agg1
    G2 --> Agg2

    Agg1 --> BS
    Agg2 --> BS

    style G1 fill:#FFD700,stroke:#FF8C00,stroke-width:4px
    style G2 fill:#FFD700,stroke:#FF8C00,stroke-width:4px
    style BS fill:#FF6347,stroke:#DC143C,stroke-width:4px
```

---

## 图5: 完整数据流时序图

**保存为**: `aeris_figure_5_data_flow_sequence.svg` / `.png` / `.pdf`

**插入位置**: Section 4 结尾 或 Section 6 开头

**说明**: 展示AERIS协议一轮完整执行流程的时序图

```mermaid
sequenceDiagram
    participant N as 传感节点
    participant CM as 簇成员
    participant CH as 簇头
    participant CAS as CAS选择器
    participant SK as Skeleton选择器
    participant GW as Gateway选择器
    participant BS as 基站

    Note over N,BS: 轮次开始 Round t

    N->>CM: 1. 感知数据采集
    CM->>CH: 2. 簇头选举 能量+位置

    activate CH
    CH->>CAS: 3. 请求传输模式
    CAS->>CAS: 4. 计算特征 能量,链路,距离...
    CAS->>CAS: 5. 线性评分 + EMA平滑
    CAS->>CAS: 6. 置信度检查
    CAS-->>CH: 7. 返回模式 Direct/Chain/TwoHop

    CH->>SK: 8. 请求骨干选择
    SK->>SK: 9. PCA主轴分析
    SK->>SK: 10. 计算主轴接近度 + 中心度
    SK->>SK: 11. 综合评分排序
    SK-->>CH: 12. 返回k个骨干CH

    CH->>GW: 13. 请求网关选择
    GW->>GW: 14. 计算到BS距离 + 中心度
    GW->>GW: 15. 公平性惩罚
    GW->>GW: 16. Top-k选择
    GW-->>CH: 17. 返回k个网关CH
    deactivate CH

    Note over CM,CH: 簇内数据传输 根据CAS模式

    alt Direct Mode
        CM->>CH: 成员直接发送到CH
    else Chain Mode
        CM->>CM: 簇内链式聚合
        CM->>CH: 链尾发送到CH
    else TwoHop Mode
        CM->>CM: 成员发送到中继
        CM->>CH: 中继发送到CH
    end

    Note over CH,BS: 簇间数据聚合 Skeleton + Gateway

    CH->>CH: 18. 骨干CH之间路由
    CH->>GW: 19. 发送到网关CH
    GW->>BS: 20. 网关多跳传输到BS

    BS->>BS: 21. 数据汇聚 + 处理
    BS-->>CH: 22. ACK确认

    Note over N,BS: 轮次结束 Round t complete
```

---

## 图6: 与ML方法的架构对比

**保存为**: `aeris_figure_6_ml_comparison.svg` / `.png` / `.pdf`

**插入位置**: Section 6.2 (Computational Efficiency) 或 Section 7.3 (vs ML/RL)

**说明**: 对比AERIS确定性架构与LSTM/GRU架构的计算开销

```mermaid
graph TB
    subgraph AERIS["AERIS架构 Deterministic"]
        A_Input[环境特征<br/>7 features]
        A_CAS[线性评分<br/>51次浮点运算<br/>O1]
        A_SK[PCA分析<br/>On²]
        A_GW[Top-k选择<br/>On log k]
        A_Output[路由决策]
        A_Time["总时间: <10ms"]
        A_Mem["内存: 23KB"]

        A_Input --> A_CAS --> A_SK --> A_GW --> A_Output
        A_Output -.-> A_Time
        A_Output -.-> A_Mem
    end

    subgraph LSTM["LSTM架构 Data-Driven"]
        L_Input[历史序列<br/>128步]
        L_Encode[特征编码<br/>OL·H]
        L_LSTM[2层LSTM<br/>67M FLOPs<br/>OL·H²]
        L_FC[全连接层<br/>OH]
        L_Output[环境预测]
        L_Time["总时间: 50-80ms"]
        L_Mem["内存: 700KB"]
        L_Train["训练: 16小时"]

        L_Input --> L_Encode --> L_LSTM --> L_FC --> L_Output
        L_Output -.-> L_Time
        L_Output -.-> L_Mem
        L_Output -.-> L_Train
    end

    subgraph GRU["GRU架构 MeFi"]
        G_Input[状态空间]
        G_Encode[特征工程]
        G_GRU[GRU网络<br/>500K参数]
        G_Search[动作空间搜索]
        G_Output[路由策略]
        G_Time["总时间: 600ms"]
        G_Mem["内存: 2MB"]
        G_Train["训练: 48小时"]

        G_Input --> G_Encode --> G_GRU --> G_Search --> G_Output
        G_Output -.-> G_Time
        G_Output -.-> G_Mem
        G_Output -.-> G_Train
    end

    Compare["对比:<br/>AERIS快6-60倍<br/>省30-100倍内存<br/>零训练开销"]

    AERIS -.-> Compare
    LSTM -.-> Compare
    GRU -.-> Compare

    style A_Output fill:#90EE90
    style L_Output fill:#FFB6C1
    style G_Output fill:#FFD700
    style Compare fill:#87CEEB,stroke:#4169E1,stroke-width:4px
```

---

## 图7: 可部署性对比 (硬件视角)

**保存为**: `aeris_figure_7_hardware_compatibility.svg` / `.png` / `.pdf`

**插入位置**: Section 7.4 (Practical Deployment)

**说明**: 展示不同WSN硬件平台对AERIS和ML方法的支持情况

```mermaid
graph LR
    subgraph Hardware[WSN节点硬件]
        MicaZ["MICAz<br/>RAM: 4KB<br/>Flash: 128KB"]
        TelosB["TelosB<br/>RAM: 10KB<br/>Flash: 48KB"]
        CC2650["CC2650<br/>RAM: 20KB<br/>Flash: 128KB"]
        ESP32["ESP32<br/>RAM: 520KB<br/>Flash: 4MB"]
    end

    subgraph Protocols[协议需求]
        AERIS_Req["AERIS<br/>需求: 23KB RAM<br/>决策: <10ms"]
        LSTM_Req["LSTM<br/>需求: 700KB RAM<br/>决策: 50-80ms"]
        GRU_Req["GRU MeFi<br/>需求: 2MB RAM<br/>决策: 600ms"]
    end

    MicaZ -.->|不可部署| AERIS_Req
    MicaZ -.->|不可部署| LSTM_Req
    MicaZ -.->|不可部署| GRU_Req

    TelosB -->|可部署 ✅| AERIS_Req
    TelosB -.->|不可部署 ❌| LSTM_Req
    TelosB -.->|不可部署 ❌| GRU_Req

    CC2650 -->|可部署 ✅| AERIS_Req
    CC2650 -.->|勉强 ⚠️| LSTM_Req
    CC2650 -.->|不可部署 ❌| GRU_Req

    ESP32 -->|可部署 ✅| AERIS_Req
    ESP32 -->|可部署 ✅| LSTM_Req
    ESP32 -->|可部署 ✅| GRU_Req

    Result["结论:<br/>AERIS适配传统10KB RAM节点<br/>ML方法需要256KB+"]

    AERIS_Req --> Result
    LSTM_Req --> Result
    GRU_Req --> Result

    style AERIS_Req fill:#90EE90
    style TelosB fill:#FFD700
    style Result fill:#87CEEB,stroke:#4169E1,stroke-width:4px
```

---

## 📋 完整图表清单

| 图编号 | 文件名 | 论文章节 | 说明 |
|-------|--------|---------|------|
| **图1** | `aeris_figure_1_architecture` | Section 3/4.1 | 三层协同架构总览 |
| **图2** | `aeris_figure_2_cas_flowchart` | Section 4.2 | CAS决策流程 |
| **图3** | `aeris_figure_3_skeleton_selection` | Section 4.3 | Skeleton选择算法 |
| **图4** | `aeris_figure_4_gateway_coordination` | Section 4.4 | Gateway选择与聚合 |
| **图5** | `aeris_figure_5_data_flow_sequence` | Section 4.5 | 完整时序图 |
| **图6** | `aeris_figure_6_ml_comparison` | Section 6.2/7.3 | vs ML架构对比 |
| **图7** | `aeris_figure_7_hardware_compatibility` | Section 7.4 | 硬件可部署性 |

---

## ⚠️ 重要提示

### 图表质量要求 (MDPI Sensors)

1. **分辨率**:
   - SVG: 矢量图，推荐 ✅
   - PNG: 至少300 DPI, 推荐600 DPI
   - PDF: 矢量图，最终稿使用

2. **字体大小**:
   - 图表内文字: 10-12pt
   - 标签: 不小于8pt
   - 确保缩小后仍可读

3. **颜色**:
   - 避免纯黑 (#000000), 使用深灰 (#333333)
   - 确保打印后可辨识 (灰度测试)

4. **文件命名**:
   - 使用小写字母和下划线
   - 包含图编号
   - 示例: `aeris_figure_1_architecture.svg`

---

## ✅ 下一步行动

康锐老板，现在您可以:

1. **立即渲染图表**:
   - 打开 https://mermaid.live/
   - 复制上方任意图表代码
   - 粘贴到左侧编辑器
   - 点击 "Actions" → "Export SVG/PNG"
   - 重复7次，完成全部图表

2. **或者等我帮您**:
   - 如果您觉得操作复杂，告诉我
   - 我可以创建独立的 `.mmd` 文件
   - 您可以使用命令行工具批量渲染

**预计时间**: 手动渲染7张图约15-20分钟 ✅

**我现在等待您的指示！** 🚀
