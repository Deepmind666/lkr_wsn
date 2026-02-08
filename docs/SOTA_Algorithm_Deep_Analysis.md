# SOTA Algorithm Deep Analysis Report
## AERIS Improvement Strategy Based on Competitor Analysis

**Date**: 2026-01-04
**Purpose**: Identify innovations and defects in SOTA algorithms to inform AERIS improvements

---

## 1. Executive Summary

After deep analysis of three SOTA WSN algorithm implementations from GitHub:
- **I-LEACH** (HritwikSinghal/I-LEACH-PY)
- **DQN-WSN** (fareskhlifi/Intelligent-Scheduling-using-RL-and-DQN)
- **PSO-WSN** (darolt/wsn)

We identified key innovations, critical defects, and opportunities for AERIS to absorb advantages while solving unsolved problems.

---

## 2. I-LEACH Analysis

### 2.1 Core Innovation

```python
# From LEACH_select_ch.py - CH Selection Algorithm
if sensor.E > 0 and sensor.G <= 0:
    temp_rand = random.uniform(0, 1)
    value = my_model.p / (1 - my_model.p * (round_number % round(1 / my_model.p)))
    if temp_rand <= value:
        CH.append(sensor.id)
        sensor.type = 'C'
        sensor.G = round(1 / my_model.p) - 1  # Exclusion counter
```

**Key Innovations**:
1. **Circular Patch Clustering**: Divides network into circular regions for balanced CH distribution
2. **Round-based Exclusion (G counter)**: Prevents nodes from becoming CH again for `1/p` rounds
3. **Probabilistic Selection with Energy Weighting**: P increases as rounds progress

### 2.2 Identified Defects

| Defect | Description | Impact |
|--------|-------------|--------|
| **Static Threshold** | p=0.05 is fixed, not adaptive to network state | Suboptimal CH count in sparse/dense areas |
| **No Link Quality** | Ignores RSSI/SNR in routing decisions | Poor reliability in lossy environments |
| **Simple Energy Model** | Only considers current energy, not drain rate | Cannot predict node failures |
| **Blind to Environment** | No awareness of channel conditions | Fails in dynamic environments |
| **Isolated CHs** | CHs don't coordinate with each other | Load imbalance, coverage gaps |

### 2.3 AERIS Advantage Opportunities

- AERIS's **Environment Map** can provide adaptive p-value based on local density
- AERIS's **Link Quality Estimation** addresses the reliability gap
- AERIS can use **energy drain rate prediction** instead of just current energy

---

## 3. DQN-WSN Analysis

### 3.1 Core Innovation

```python
# From Jupyter Notebook - Q-Learning Agent
class WSNEnvironmentAgent:
    def update(self, obs, action, reward, terminated, next_obs):
        future_q_value = (not terminated) * np.max(self.q_values[next_obs_key])
        temporal_difference = (
            reward + self.discount_factor * future_q_value - self.q_values[m_obs][action]
        )
        self.q_values[m_obs][action] += self.lr * temporal_difference

# DQN Network
class Network(nn.Module):
    def __init__(self, env, device):
        self.net = nn.Sequential(
            nn.Linear(in_features, 64),
            nn.Tanh(),
            nn.Linear(64, env.action_space.n)
        )
```

**Key Innovations**:
1. **Age of Information (AoI) Reward**: `reward = 1/AoI` - freshness-aware scheduling
2. **Boltzmann Action Selection**: Temperature-based exploration vs exploitation
3. **Experience Replay**: Stable learning with random sampling from buffer
4. **Target Network**: Separate network for stable Q-value targets

### 3.2 Identified Defects

| Defect | Description | Impact |
|--------|-------------|--------|
| **Scheduling Focus** | Only handles sensor scheduling, not routing | Incomplete solution for WSN |
| **No Energy Model** | Doesn't consider energy consumption | Unsustainable in real WSN |
| **Centralized** | Requires central controller for decisions | Single point of failure, scalability issues |
| **High Training Cost** | 10,000+ episodes needed for convergence | Impractical for deployment |
| **Fixed Network Size** | Trained for specific sensor count | Cannot adapt to dynamic topology |
| **No Multi-hop** | Single-hop communication assumption | Limited range |

### 3.3 AERIS Advantage Opportunities

- Integrate **AoI concept** into AERIS's packet prioritization
- Use **lightweight Q-table** (like CAS module) instead of heavy DQN
- AERIS already has **distributed decision-making** (better than centralized DQN)
- AERIS's **pre-trained models** avoid long training time at deployment

---

## 4. PSO-WSN Analysis

### 4.1 Core Innovation

```cpp
// From pso.cc - Binary PSO for Sleep Scheduling
void Pso::Optimize(const vector<u_int> &can_sleep) {
    for (u_int it = 0; it < max_iterations_; it++) {
        for (u_int individual_idx = 0; individual_idx < nb_individuals_; individual_idx++) {
            // Velocity update
            velocity_[idx] = acceleration*velocity_[idx] +
                             phi1*r1*diff_to_global +
                             phi2*r2*diff_to_local;

            // Sigmoid normalization for binary decision
            float velocity_norm = 1 / (1 + exp(-velocity_[idx]));
            genes[idx] = (r3 < velocity_norm) ? 1 : 0;
        }
    }
}

// Fitness function - Multi-objective
fitness_val = fitness_alpha_*term1 +  // Energy efficiency
              fitness_beta_*term2  +   // Coverage
              fitness_gamma_*term3;    // Sleeping rate
```

**Key Innovations**:
1. **Multi-objective Optimization**: Balances energy, coverage, and sleep rate
2. **Binary PSO with Sigmoid**: Converts continuous to discrete decisions
3. **Region-based Coverage Calculation**: Precise coverage analysis
4. **Global + Local Best**: Combines exploration and exploitation

### 4.2 Identified Defects

| Defect | Description | Impact |
|--------|-------------|--------|
| **Sleep Scheduling Only** | Doesn't optimize routing paths | Incomplete WSN solution |
| **High Computation** | Requires C++ for performance | Resource-constrained nodes can't run |
| **Static Weights** | alpha, beta, gamma are fixed | Cannot adapt to changing priorities |
| **No Link Quality** | Ignores channel conditions | Poor reliability |
| **Cluster-level Only** | Doesn't consider inter-cluster routing | Suboptimal end-to-end performance |
| **Synchronous Operation** | All nodes must participate | High coordination overhead |

### 4.3 AERIS Advantage Opportunities

- Adopt **multi-objective fitness** concept for AERIS's Gateway selection
- Use **lightweight optimization** instead of heavy PSO iterations
- AERIS's **asynchronous operation** is more practical
- Integrate **coverage awareness** into skeleton selection

---

## 5. Comparative Analysis: AERIS vs SOTA

### 5.1 Feature Comparison Matrix

| Feature | I-LEACH | DQN-WSN | PSO-WSN | AERIS |
|---------|---------|---------|---------|-------|
| **Adaptive CH Selection** | Partial | No | No | Yes (CAS) |
| **Link Quality Awareness** | No | No | No | Yes |
| **Environment Awareness** | No | No | No | Yes (EnvMap) |
| **Multi-hop Routing** | No | No | No | Yes |
| **Energy Prediction** | No | No | Partial | Yes (LSTM) |
| **Distributed Operation** | Yes | No | Partial | Yes |
| **Lightweight** | Yes | No | No | Partial |
| **Reliability Mechanisms** | No | No | No | Yes (ARQ) |
| **Dynamic Adaptation** | No | Yes | No | Yes |
| **Coverage Optimization** | No | No | Yes | Partial |

### 5.2 Performance Trade-offs

```
SOTA Algorithms:
- Energy Efficient but Unreliable (PDR ~75-85%)
- Simple but Not Adaptive
- Fast but Short-lived

Current AERIS:
- Reliable (PDR ~95%) but Energy Intensive (6-7x more)
- Adaptive but Complex
- Long-lived but High Overhead
```

---

## 6. AERIS Improvement Proposals

### 6.1 Energy-Efficient Mode (From SOTA Insights)

**Problem**: AERIS uses 6-7x more energy for ~10% PDR improvement

**Solution**: Adaptive Reliability Level based on SOTA simplicity

```python
class AdaptiveReliabilityManager:
    """
    Dynamically adjust reliability mechanisms based on:
    1. Current network energy state
    2. Required QoS level
    3. Channel conditions
    """

    PROFILES = {
        'ultra_low_power': {  # Like LEACH
            'max_arq_attempts': 1,
            'power_levels': 1,
            'relay_copies': 1,
            'rescue_enabled': False,
            'expected_pdr': 0.75,
            'energy_factor': 1.0
        },
        'balanced': {  # New middle ground
            'max_arq_attempts': 3,
            'power_levels': 2,
            'relay_copies': 2,
            'rescue_enabled': False,
            'expected_pdr': 0.88,
            'energy_factor': 2.5
        },
        'high_reliability': {  # Current AERIS
            'max_arq_attempts': 7,
            'power_levels': 5,
            'relay_copies': 4,
            'rescue_enabled': True,
            'expected_pdr': 0.95,
            'energy_factor': 6.5
        }
    }

    def select_profile(self, network_energy_ratio, required_pdr, channel_quality):
        if required_pdr < 0.80:
            return self.PROFILES['ultra_low_power']
        elif required_pdr < 0.90 or network_energy_ratio < 0.3:
            return self.PROFILES['balanced']
        else:
            return self.PROFILES['high_reliability']
```

### 6.2 Multi-Objective Gateway Selection (From PSO)

**Problem**: Current Gateway selection focuses mainly on reliability

**Solution**: Integrate PSO's multi-objective concept

```python
def enhanced_gateway_fitness(node, cluster_members, bs_position, network_state):
    """
    Multi-objective fitness like PSO, but lightweight
    """
    # Term 1: Energy efficiency (from PSO)
    energy_term = node.energy / node.initial_energy

    # Term 2: Link quality (AERIS strength)
    link_quality = node.get_link_quality_to_bs()

    # Term 3: Load balance (from PSO coverage concept)
    expected_load = len(cluster_members)
    optimal_load = network_state.total_nodes / network_state.num_gateways
    balance_term = 1 - abs(expected_load - optimal_load) / optimal_load

    # Term 4: Coverage (from PSO)
    coverage_term = calculate_coverage_contribution(node, cluster_members)

    # Adaptive weights based on network state
    alpha = 0.3 if network_state.energy_ratio > 0.5 else 0.4
    beta = 0.3
    gamma = 0.2
    delta = 0.2

    return alpha * energy_term + beta * link_quality + gamma * balance_term + delta * coverage_term
```

### 6.3 Age of Information Integration (From DQN-WSN)

**Problem**: AERIS treats all packets equally

**Solution**: Prioritize fresher data

```python
class AoIAwareScheduler:
    """
    Integrate Age of Information concept from DQN-WSN
    """

    def calculate_packet_priority(self, packet, current_time):
        # Age of Information
        aoi = current_time - packet.generation_time

        # Freshness reward (from DQN-WSN)
        freshness = 1.0 / (1.0 + aoi)

        # Combine with existing priority factors
        energy_factor = packet.source_node.energy / packet.source_node.initial_energy
        criticality = packet.criticality_level  # Application-defined

        return freshness * 0.4 + energy_factor * 0.3 + criticality * 0.3

    def schedule_transmissions(self, pending_packets):
        # Sort by priority (higher = more urgent)
        return sorted(pending_packets,
                     key=lambda p: self.calculate_packet_priority(p, time.now()),
                     reverse=True)
```

### 6.4 Simplified CAS Module (From I-LEACH Simplicity)

**Problem**: CAS module may be over-engineered

**Solution**: Lighter decision mechanism like I-LEACH's probability-based selection

```python
class SimplifiedCAS:
    """
    Lightweight CH selection inspired by I-LEACH
    but with AERIS's environment awareness
    """

    def should_become_ch(self, node, round_number, env_map):
        # Base probability (like I-LEACH)
        p_base = 0.05

        # Energy modifier (AERIS enhancement)
        energy_ratio = node.energy / node.initial_energy
        p_energy = p_base * (1 + energy_ratio) / 2

        # Environment modifier (AERIS unique)
        local_density = env_map.get_node_density(node.position)
        p_env = p_energy * (1 + 0.2 * (1 - local_density))

        # Round-based exclusion (from I-LEACH)
        if node.rounds_since_ch < (1 / p_base):
            return False

        # Simple probabilistic decision
        threshold = p_env / (1 - p_env * (round_number % round(1 / p_env)))
        return random.random() < threshold
```

---

## 7. Recommended Implementation Priority

### Phase 1: Quick Wins (1 week)
1. **Add Reliability Profiles**: Implement adaptive reliability levels
2. **Simplify Default Profile**: Use 'balanced' as default instead of 'high_reliability'

### Phase 2: Core Improvements (2 weeks)
3. **Multi-objective Gateway Selection**: Integrate energy, coverage, balance
4. **AoI Packet Scheduling**: Prioritize fresh data

### Phase 3: Algorithm Refinement (2 weeks)
5. **Simplified CAS**: Reduce complexity while keeping environment awareness
6. **Adaptive Profile Selection**: Auto-switch based on network state

---

## 8. Key Takeaways

### What SOTA Does Better
1. **Energy Efficiency**: 6-7x less energy consumption
2. **Simplicity**: Fewer parameters, easier to tune
3. **Fast Decisions**: Lower computational overhead

### What AERIS Does Better
1. **Reliability**: 10-20% higher PDR
2. **Environment Awareness**: Adapts to channel conditions
3. **Link Quality**: Considers RSSI/SNR in routing
4. **Multi-hop**: Better for large networks

### The Gap to Fill
AERIS needs to offer **configurable trade-offs** between reliability and energy efficiency, rather than only providing high-reliability mode.

---

## 9. Conclusion

By analyzing SOTA algorithms, we identified that:

1. **I-LEACH** shows simple probabilistic selection can be effective
2. **DQN-WSN** demonstrates value of freshness-aware scheduling
3. **PSO-WSN** proves multi-objective optimization improves balance

AERIS can become more competitive by:
- Adding **adaptive reliability profiles**
- Integrating **multi-objective metrics**
- Implementing **AoI-aware scheduling**
- Simplifying **CAS decision logic**

These improvements would make AERIS offer the **best of both worlds**: high reliability when needed, competitive energy efficiency when acceptable.

---

*Report generated based on analysis of GitHub repositories:*
- *HritwikSinghal/I-LEACH-PY*
- *fareskhlifi/Intelligent-Scheduling-using-RL-and-DQN*
- *darolt/wsn*
