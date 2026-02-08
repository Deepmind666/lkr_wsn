# Section 2: Related Work

---

## 2. Related Work

This section reviews existing WSN routing protocols with emphasis on the latency-energy-reliability trade-off, positioning AERIS within the broader research landscape.

### 2.1 Classical Clustering Protocols

Clustering-based routing has been the dominant paradigm for energy-efficient WSN communication since the introduction of LEACH [3]. We categorize classical protocols by their transmission structure and analyze their latency characteristics.

#### 2.1.1 Cluster-Based Protocols (LEACH, HEED)

**LEACH** [3] introduced the concept of rotating cluster heads to distribute energy consumption. In each round, nodes self-elect as cluster heads with probability *p*, and non-cluster-head nodes join the nearest cluster head. Data transmission follows a two-phase model: intra-cluster aggregation followed by direct cluster-head-to-base-station transmission.

**Latency Analysis**: LEACH achieves O(1) transmission latency since all cluster heads transmit directly to the base station in parallel. However, this direct transmission incurs high energy consumption for distant cluster heads, and the random cluster head selection leads to suboptimal clustering in heterogeneous deployments.

**HEED** [5] improved upon LEACH by incorporating residual energy and communication cost into cluster head selection. The protocol iteratively increases cluster head probability based on node energy levels, achieving more balanced energy consumption. HEED maintains O(1) latency through its single-hop cluster-head-to-base-station model but introduces additional setup overhead.

**Limitation**: Both LEACH and HEED exhibit PDR degradation under harsh channel conditions due to increased transmission distances and single-hop cluster-head-to-base-station links.

#### 2.1.2 Chain-Based Protocols (PEGASIS)

**PEGASIS** [4] pioneered chain-based data aggregation, where nodes form a linear chain and data is passed sequentially toward a designated leader node. Each node receives data from one neighbor, fuses it with its own data, and transmits to the next neighbor in the chain.

**Energy Efficiency**: PEGASIS achieves high energy efficiency by minimizing transmission distances—each node only communicates with its immediate neighbors.

**Latency Analysis**: The sequential transmission model introduces **O(n)** latency, where n is the number of nodes. For a network with n nodes, data must traverse an average of n/2 hops before reaching the base station. As network scale grows, this sequential delay becomes a critical limitation for real-time applications.

**Robustness**: Chain-based protocols are vulnerable to node failures. A single node failure can partition the chain, requiring complete chain reconstruction with O(n²) complexity.

#### 2.1.3 Summary of Classical Protocol Trade-offs

**Table 2: Comparison of Classical WSN Routing Protocols**

| Protocol | Latency | Energy | PDR | Robustness | Complexity |
|----------|---------|--------|-----|------------|------------|
| LEACH | O(1) | High | Degrades | Medium | O(n) |
| HEED | O(1) | Medium | Stable | Medium | O(n log n) |
| PEGASIS | **O(n)** | **Low** | **High** | Low | O(n²) |

### 2.2 Machine Learning-Based Routing

Recent advances in machine learning have motivated numerous ML-based WSN routing protocols that adapt to dynamic network conditions [6, 7].

#### 2.2.1 Reinforcement Learning Approaches

Deep Q-Networks (DQN) have been applied to WSN routing to learn optimal relay selection policies [7]. Multi-Agent Deep Reinforcement Learning (MADRL) frameworks enable distributed decision-making where each node acts as an independent agent learning cooperative routing strategies.

MeFi [6] employs GRU-based mean field reinforcement learning for cooperative routing, demonstrating improved adaptation to network dynamics through centralized training with decentralized execution.

**Computational Barriers**: Despite promising results, ML-based approaches face significant deployment challenges on resource-constrained WSN nodes:

- **Inference latency**: Neural network forward propagation requires 50–600ms on microcontroller-class processors, exceeding real-time requirements for industrial monitoring (<100ms) [8].

- **Memory footprint**: Even compact LSTM/GRU models require 700KB–2MB for weight storage, far exceeding available RAM on commodity sensor nodes (TelosB: 10KB, CC2650: 20KB).

- **Training overhead**: RL algorithms typically require thousands of training episodes (8–96 hours on GPU infrastructure), making them impractical for dynamic deployments where conditions change post-installation.

**Table 3: Computational Requirements of ML-Based Routing Protocols**

| Method | Decision Time | Memory | Training | Hardware Requirement |
|--------|---------------|--------|----------|---------------------|
| LSTM-routing | 50–80ms | 700KB | 16h | 512KB+ RAM |
| MeFi (GRU) | ~600ms | 2MB | 48h | 1MB+ RAM |
| MADRL (DQN) | ~500ms | 3.5MB | 96h | 2MB+ RAM |
| **AERIS** | **Rule-based (no NN inference)** | **23KB** | **0h** | **10KB+ RAM** |

### 2.3 Environment-Aware Routing

Environment-aware routing protocols incorporate physical environmental factors (temperature, humidity, interference) into routing decisions [9, 10].

#### 2.3.1 Link Quality Prediction

Several works have demonstrated strong correlations between environmental conditions and wireless link quality. Temperature variations affect transceiver noise figures, while humidity influences signal propagation characteristics [11]. These findings motivate environment-adaptive protocols that adjust transmission parameters based on sensed conditions.

#### 2.3.2 Adaptive Transmission Strategies

Cross-layer protocols integrate physical layer information (RSSI, LQI) into routing decisions. Adaptive power control mechanisms adjust transmission power based on estimated channel conditions, balancing energy consumption against delivery reliability.

**Limitation**: Existing environment-aware approaches typically focus on link-level adaptation without addressing the fundamental latency-energy trade-off at the network level. Most retain either O(1) (cluster-based) or O(n) (chain-based) latency characteristics inherited from their underlying routing structures.

### 2.4 Research Gap and AERIS Positioning

Based on our analysis, we identify the following research gap:

**Gap Statement**: No existing lightweight protocol (<50KB memory, training-free rule-based decision logic) simultaneously achieves:

1. **Hierarchical transmission structure** suitable for large-scale deployments
2. **Highest PDR among tested baselines in all four evaluated environments (n=30)**
3. **Zero training requirement**: Immediate deployment capability
4. **Commodity hardware compatibility**: Deployable on 10KB RAM nodes

**Table 4: AERIS Positioning in the Protocol Design Space**

| Approach | Latency | Energy | Multi-Env PDR | Training | Memory |
|----------|---------|--------|---------------|----------|--------|
| LEACH | ✓ Low | ✗ High | ✗ Lowest in 4/4 envs | ✓ 0h | ✓ 15KB |
| PEGASIS | ✗ O(n) | ✓ Lowest | ✗ Low in harsh envs | ✓ 0h | ✓ 50KB |
| HEED | ✓ Low | △ Medium | △ Mid-range | ✓ 0h | ✓ 18KB |
| ML-based | ✗ 500ms | △ Medium | ✓ High (reported) | ✗ 48h+ | ✗ 2MB+ |
| **AERIS** | **✓ Hierarchical** | **△ Trade-off (environment-dependent)** | **✓ Highest in 4/4 envs** | **✓ 0h** | **✓ 23KB** |

**Legend**: ✓ Satisfies requirement; ✗ Does not satisfy; △ Partially satisfies

**AERIS Positioning**: AERIS addresses this gap through hierarchical routing that maintains the highest PDR across all four tested channel environments while providing lightweight, training-free operation suitable for commodity WSN hardware. Unlike ML-based approaches, AERIS requires no training and provides interpretable decision logic.

---

## References (Section 2 additions)

[6] J. Ren et al., "MeFi: Mean field reinforcement learning for cooperative routing in wireless sensor networks," *IEEE Internet Things J.*, vol. 11, no. 1, pp. 995–1011, 2024.

[7] A. A. Okine et al., "Multi-agent deep reinforcement learning for packet routing in tactical mobile sensor networks," *IEEE Trans. Netw. Service Manage.*, vol. 21, no. 2, pp. 2155–2169, 2024.

[8] V. J. Kumar et al., "TinyML: Machine learning on microcontrollers for IoT applications," *IEEE Micro*, vol. 40, no. 3, pp. 78–87, 2020.

[9] L. Sun et al., "Environment-aware routing for wireless sensor networks," *Ad Hoc Networks*, vol. 112, p. 102376, 2021.

[10] Y. Wang et al., "Adaptive routing protocol with environment sensing for WSN," *Sensors*, vol. 22, no. 15, p. 5642, 2022.

[11] M. Boano et al., "The impact of temperature on outdoor industrial sensor deployments," *ACM Trans. Sensor Networks*, vol. 10, no. 2, pp. 1–34, 2014.

