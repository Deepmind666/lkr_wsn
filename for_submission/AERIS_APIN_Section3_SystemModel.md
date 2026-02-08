# Section 3: System Model and Preliminary Analysis

---

## 3. System Model and Preliminary Analysis

This section presents the system model underlying AERIS, including network assumptions, energy consumption model, and channel characteristics. We then describe preliminary experiments that informed key design decisions.

### 3.1 Network Model

We consider a wireless sensor network consisting of *N* sensor nodes deployed in a two-dimensional area *A = W × H* square meters. The network topology is characterized by the following assumptions:

1. **Static deployment**: Nodes are stationary after initial deployment, a common assumption for environmental monitoring and industrial sensing applications.

2. **Homogeneous nodes**: All sensor nodes have identical hardware capabilities (transmission power, sensing range, initial energy). We use CC2420-based TelosB motes as the reference platform.

3. **Single base station**: A base station (BS) with unlimited energy is located at coordinates (x_BS, y_BS), typically outside the sensing area to simulate realistic deployment scenarios.

4. **Data generation**: Each node generates one data packet per round, representing periodic sensor readings. Packet size is fixed at *L = 4000* bits (500 bytes).

5. **Bidirectional links**: If node *i* can communicate with node *j*, then *j* can also communicate with *i* (symmetric links).

The network is modeled as a graph *G = (V, E)*, where *V* is the set of sensor nodes and *E* is the set of communication links.

### 3.2 Energy Consumption Model

We adopt an energy model based on the CC2420 radio transceiver, consistent with IEEE 802.15.4 specifications.

#### 3.2.1 Transmission Energy

The energy consumed to transmit *L* bits over distance *d* is:

```
E_tx(L, d) = E_elec · L + E_amp(d) · L
```

where:
- E_elec = 50 nJ/bit (transceiver electronics)
- E_amp(d) depends on propagation model:
  - E_fs · d² if d < d₀ (free-space)
  - E_mp · d⁴ if d ≥ d₀ (multi-path)

#### 3.2.2 Reception Energy

```
E_rx(L) = E_elec · L = 50 nJ/bit × L
```

#### 3.2.3 Data Aggregation Energy

```
E_agg(L) = E_DA · L = 5 nJ/bit × L
```

**Table 5: Energy Model Parameters (CC2420 TelosB)**

| Parameter | Description | Value |
|-----------|-------------|-------|
| E_elec | Electronics energy | 50 nJ/bit |
| E_fs | Free-space amplifier | 10 pJ/bit/m² |
| E_mp | Multi-path amplifier | 0.0013 pJ/bit/m⁴ |
| E_DA | Data aggregation | 5 nJ/bit |
| d₀ | Crossover distance | 87 m |
| L | Packet size | 4000 bits |

### 3.3 Channel Model

We employ a log-normal shadowing model consistent with IEEE 802.15.4 propagation characteristics.

#### 3.3.1 Path Loss Model

```
P_rx(d) = P_tx - PL(d₀) - 10·η·log₁₀(d/d₀) + X_σ
```

where:
- η = path loss exponent (environment-dependent)
- X_σ = zero-mean Gaussian shadowing with std σ

**Table 6: Channel Model Parameters by Environment Type**

| Environment | Path Loss η | Shadowing σ (dB) | Typical PDR |
|-------------|-------------|------------------|-------------|
| Indoor Office | 2.0–2.5 | 3–4 | 95–99% |
| Industrial | 2.5–3.5 | 4–8 | 85–95% |
| Outdoor Open | 2.0–2.2 | 2–3 | 97–99% |
| Urban Dense | 3.0–4.0 | 6–10 | 75–90% |

### 3.4 Preliminary Experiments and Design Rationale

Before presenting the AERIS protocol, we describe three preliminary experiments conducted on the **Intel Berkeley Research Lab dataset** that informed key design decisions. This dataset comprises 2.22 million sensor readings from 54 nodes collected over 36 days.

#### E1: Environment-Link Quality Correlation

**Objective**: Quantify the relationship between environmental parameters and wireless link quality.

**Method**: Computed Pearson correlation coefficients between environmental variables and link quality indicators across all node pairs.

**Results**:
- Temperature–RSSI correlation: **r = -0.292** (p < 0.001)
- Humidity–packet loss correlation: **r = 0.187** (p < 0.001)
- Combined features predict link quality with **89.2% accuracy**

**Design Decision → Environment-Aware Gateway Selection**:
> The significant correlation between environmental conditions and link quality motivates AERIS's environment-aware scoring function. By incorporating temperature and humidity readings into gateway selection, AERIS prioritizes nodes with stable environmental conditions.

#### E2: Link Reliability Predictability

**Objective**: Assess whether link reliability can be predicted from observable features.

**Method**: Trained a random forest classifier using node distance, energy, temperature, humidity, and historical PDR.

**Results**:
- Prediction AUC: **0.924** (10-fold cross-validation)
- Most important features: distance (42%), temperature (18%), historical PDR (15%)

**Design Decision → Hierarchical Backbone Routing**:
> The high predictability (AUC = 0.924) suggests routing decisions can be made deterministically without online learning. AERIS pre-selects high-reliability links for the skeleton backbone, reserving adaptive mechanisms for edge cases.

#### E3: Load Imbalance Impact

**Objective**: Quantify the impact of traffic load imbalance on network performance.

**Method**: Simulated various load distributions and measured correlation with PDR.

**Results**:
- Load variance–PDR correlation: **r = -0.749** (p < 0.001)
- Networks with Gini > 0.4 showed **15–25% PDR degradation**
- Hotspot cluster heads depleted energy **3–5× faster**

**Design Decision → Gateway Load Limiting**:
> The strong negative correlation motivates AERIS's gateway load limiting mechanism. By constraining maximum traffic per gateway, AERIS prevents hotspot formation and ensures balanced energy consumption.

### 3.5 Design Principles Summary

Based on the preliminary analysis, AERIS is designed around three core principles:

| Principle | Motivation | AERIS Mechanism |
|-----------|------------|-----------------|
| **Environment-awareness** | E1: Environment-link correlation (r=-0.292) | Environment-aware gateway scoring |
| **Deterministic hierarchy** | E2: Link predictability (AUC=0.924) | PCA-based skeleton backbone |
| **Load balancing** | E3: Load-PDR correlation (r=-0.749) | Gateway load limiting |

These principles collectively enable AERIS to achieve high reliability through environment-aware link selection, hierarchical backbone routing, and load-balanced gateway coordination.

---

## References (Section 3 additions)

[12] Texas Instruments, "CC2420 2.4 GHz IEEE 802.15.4 / ZigBee-ready RF Transceiver," Datasheet, 2007.

[13] S. Madden, "Intel Lab Data," MIT CSAIL, 2004. Available: http://db.csail.mit.edu/labdata/labdata.html

