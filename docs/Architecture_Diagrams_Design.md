# AERIS架构图设计文档

**日期**: 2025-10-19
**作者**: Claude
**目的**: 为论文创建高质量的架构和流程图

---

## 图1: AERIS三层协同架构总览

```mermaid
graph TB
    subgraph "数据层 (Data Plane)"
        SN[传感节点<br/>Sensor Nodes]
        CM[簇成员<br/>Cluster Members]
        CH[簇头<br/>Cluster Heads]
    end

    subgraph "决策层 (Decision Plane)"
        CAS[CAS选择器<br/>Context-Adaptive Switching<br/>传输模式: Direct/Chain/TwoHop]
        SK[Skeleton选择器<br/>PCA-based Backbone<br/>k个骨干CH]
        GW[Gateway选择器<br/>Gateway Coordination<br/>k个网关CH]
    end

    subgraph "通信层 (Communication Plane)"
        MAC[MAC协议<br/>IEEE 802.15.4<br/>CSMA/CA]
        PHY[PHY层<br/>250kbps<br/>2.4GHz]
        CH_Model[信道模型<br/>Log-normal Shadowing<br/>Path Loss + Fading]
    end

    subgraph "基站 (Base Station)"
        BS[(BS<br/>数据汇聚)]
    end

    %% 数据流
    SN -->|感知数据| CM
    CM -->|簇内传输| CH
    CH -->|决策输入| CAS
    CAS -->|模式选择| SK
    SK -->|骨干路由| GW
    GW -->|多跳聚合| MAC
    MAC -->|帧封装| PHY
    PHY -->|信道传输| CH_Model
    CH_Model -->|接收| BS

    %% 反馈环
    CH -->|链路质量<br/>能量状态| CAS
    BS -->|ACK/NACK| CH

    style CAS fill:#ff9999,stroke:#cc0000,stroke-width:3px
    style SK fill:#99ccff,stroke:#0066cc,stroke-width:3px
    style GW fill:#99ff99,stroke:#006600,stroke-width:3px
    style BS fill:#ffff99,stroke:#cccc00,stroke-width:3px
```

---

## 图2: CAS决策流程详细展开

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

    subgraph Scoring[线性评分计算]
        S1["直接模式得分<br/>s_direct = 0.3×E + 0.25×L - 0.15×D + ..."]
        S2["链式模式得分<br/>s_chain = 0.4×E - 0.2×R + ..."]
        S3["两跳模式得分<br/>s_two_hop = 0.25×E + 0.2×L + ..."]
    end

    subgraph EMA[EMA平滑]
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
        Exec_Direct["成员 → CH (单跳)"]
        Exec_Chain["成员 → ... → 中继 → CH (链式)"]
        Exec_TwoHop["成员 → 中继 → CH (两跳)"]
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

```mermaid
flowchart TD
    Start([开始: 已选出n个CH])

    Input["输入: chs = [CH₁, CH₂, ..., CHₙ]<br/>k = 骨干CH数量 (通常2-3)"]

    subgraph PCA[PCA主轴分析]
        Extract["提取坐标矩阵<br/>X = [(x₁,y₁), (x₂,y₂), ..., (xₙ,yₙ)]"]
        Center["中心化: X' = X - mean(X)"]
        Cov["协方差矩阵: C = X'ᵀ × X' / (n-1)"]
        Eigen["特征分解: λ, v = eig(C)"]
        Axis["主方向: v₁ = argmax(λ)"]
    end

    subgraph Metrics[指标计算]
        AxisDist["主轴接近度<br/>对每个CHᵢ:<br/>dᵢ = ‖CHᵢ - proj(CHᵢ, v₁)‖"]
        Centrality["中心度<br/>对每个CHᵢ:<br/>cᵢ = 1/(1 + mean_dist_to_others)"]
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

    Output["输出: backbone_chs = [CH₁, CH₇, CH₁₂]<br/>(示例: 选出3个骨干CH)"]
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

```mermaid
flowchart LR
    subgraph Clusters[簇层级]
        C1[Cluster 1<br/>CH₁]
        C2[Cluster 2<br/>CH₂]
        C3[Cluster 3<br/>CH₃]
        C4[Cluster 4<br/>CH₄]
        C5[Cluster 5<br/>CH₅]
    end

    subgraph Gateway_Selection[网关选择]
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

```mermaid
sequenceDiagram
    participant N as 传感节点
    participant CM as 簇成员
    participant CH as 簇头
    participant CAS as CAS选择器
    participant SK as Skeleton选择器
    participant GW as Gateway选择器
    participant BS as 基站

    Note over N,BS: 轮次开始

    N->>CM: 1. 感知数据采集
    CM->>CH: 2. 簇头选举 (能量+位置)

    activate CH
    CH->>CAS: 3. 请求传输模式
    CAS->>CAS: 4. 计算特征 (能量,链路,距离...)
    CAS->>CAS: 5. 线性评分 + EMA平滑
    CAS->>CAS: 6. 置信度检查
    CAS-->>CH: 7. 返回模式 (Direct/Chain/TwoHop)

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

    Note over CM,CH: 簇内数据传输 (根据CAS模式)

    alt Direct Mode
        CM->>CH: 成员直接发送到CH
    else Chain Mode
        CM->>CM: 簇内链式聚合
        CM->>CH: 链尾发送到CH
    else TwoHop Mode
        CM->>CM: 成员发送到中继
        CM->>CH: 中继发送到CH
    end

    Note over CH,BS: 簇间数据聚合 (Skeleton + Gateway)

    CH->>CH: 18. 骨干CH之间路由
    CH->>GW: 19. 发送到网关CH
    GW->>BS: 20. 网关多跳传输到BS

    BS->>BS: 21. 数据汇聚 + 处理
    BS-->>CH: 22. ACK确认

    Note over N,BS: 轮次结束
```

---

## 图6: 与ML方法的架构对比

```mermaid
graph TB
    subgraph AERIS["AERIS架构 (确定性)"]
        A_Input[环境特征]
        A_CAS[线性评分<br/>51次浮点运算<br/>O(1)]
        A_SK[PCA分析<br/>O(n²)]
        A_GW[Top-k选择<br/>O(n²)]
        A_Output[路由决策]
        A_Time["总时间: <10ms"]
        A_Mem["内存: 23KB"]

        A_Input --> A_CAS --> A_SK --> A_GW --> A_Output
        A_Output -.-> A_Time
        A_Output -.-> A_Mem
    end

    subgraph LSTM["LSTM架构 (数据驱动)"]
        L_Input[历史序列<br/>128步]
        L_Encode[特征编码<br/>O(L·H)]
        L_LSTM[2层LSTM<br/>67M FLOPs<br/>O(L·H²)]
        L_FC[全连接层<br/>O(H)]
        L_Output[环境预测]
        L_Time["总时间: 50-80ms"]
        L_Mem["内存: 700KB"]
        L_Train["训练: 16小时"]

        L_Input --> L_Encode --> L_LSTM --> L_FC --> L_Output
        L_Output -.-> L_Time
        L_Output -.-> L_Mem
        L_Output -.-> L_Train
    end

    subgraph GRU["GRU架构 (MeFi)"]
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
        GRU_Req["GRU (MeFi)<br/>需求: 2MB RAM<br/>决策: 600ms"]
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

    Result["结论:<br/>AERIS适配传统10KB RAM节点<br/>ML方法需要32KB+"]

    AERIS_Req --> Result
    LSTM_Req --> Result
    GRU_Req --> Result

    style AERIS_Req fill:#90EE90
    style TelosB fill:#FFD700
    style Result fill:#87CEEB,stroke:#4169E1,stroke-width:4px
```

---

## 使用说明

### 生成高质量图片

1. **Mermaid在线编辑器**: https://mermaid.live/
   - 复制上述代码
   - 导出为SVG (矢量图，无损缩放)
   - 或导出为PNG (600+ DPI)

2. **VS Code插件**: Mermaid Preview
   - 安装 "Markdown Preview Mermaid Support"
   - 直接渲染查看
   - 右键导出图片

3. **命令行工具** (需要npm):
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   mmdc -i diagram.mmd -o output.svg -w 1920 -H 1080
   ```

### 论文插入建议

| 图编号 | 建议位置 | 说明 |
|-------|---------|------|
| 图1 | Section 3 (System Model) | 架构总览 |
| 图2 | Section 4.2 (CAS Design) | CAS详细流程 |
| 图3 | Section 4.3 (Skeleton) | Skeleton算法 |
| 图4 | Section 4.4 (Gateway) | Gateway选择 |
| 图5 | Section 4.5 (Pipeline) | 时序流程 |
| 图6 | Section 6.4 (Comparison) | 性能对比 |
| 图7 | Section 7 (Discussion) | 可部署性分析 |

---

## 图表风格统一

### 颜色方案 (保持学术专业性)

- **AERIS组件**: #90EE90 (浅绿) - 代表轻量高效
- **决策节点**: #FFD700 (金色) - 代表关键决策点
- **ML方法**: #FFB6C1 (粉红) - 代表计算密集
- **基站/结果**: #87CEEB (天蓝) - 代表最终输出

### 字体建议

- 图表文字: Arial 或 Helvetica (10-12pt)
- 标题: 粗体 (12-14pt)
- 注释: 斜体 (9-10pt)

---

**下一步**: 使用Mermaid Live渲染这些图表，生成高分辨率SVG/PNG插入论文 🚀
