# Section 5: Experimental Setup and Implementation

## 5.1 Simulation Environment

All experiments were conducted using a custom-built simulation framework implemented in Python 3.9, running on a high-performance computing system with the following specifications:

**Hardware Configuration:**
- **Processor**: Intel Core i7-12700K (12 cores, 3.6 GHz base frequency)
- **Memory**: 32 GB DDR4-3200 RAM
- **Storage**: 1 TB NVMe SSD
- **Operating System**: Windows 11 Professional

**Software Environment:**
- **Python Version**: 3.9.7
- **Key Libraries**: NumPy 1.21.0, SciPy 1.7.0, Matplotlib 3.4.2, Pandas 1.3.0
- **Simulation Framework**: Custom WSN simulator with modular protocol implementation
- **Statistical Analysis**: SciPy.stats for significance testing
- **Visualization**: Matplotlib and Seaborn for chart generation

The simulation framework was designed with modularity in mind, allowing for easy integration of different routing protocols and fair performance comparison under identical conditions.

## 5.2 Dataset Description

### 5.2.1 Intel Berkeley Research Lab Dataset

The experiments utilize the widely-recognized Intel Berkeley Research Lab dataset, which provides real-world sensor network data collected from a 54-node deployment over a 31-day period from February 28 to April 5, 2004.

**Dataset Characteristics:**
- **Total Records**: 2,219,799 sensor readings
- **Sensor Types**: Temperature, humidity, light, and voltage sensors
- **Sampling Interval**: 31 seconds average
- **Network Topology**: Multi-hop wireless sensor network
- **Coverage Area**: Intel Berkeley Research Lab building
- **Data Format**: Timestamp, node ID, temperature, humidity, light, voltage

**Data Preprocessing:**
The raw dataset underwent several preprocessing steps to ensure simulation validity:

1. **Data Cleaning**: Removal of incomplete records and outliers (< 0.1% of total data)
2. **Temporal Alignment**: Synchronization of sensor readings to common time intervals
3. **Topology Extraction**: Reconstruction of network connectivity based on communication logs
4. **Energy Model Mapping**: Assignment of realistic energy consumption values based on sensor specifications

### 5.2.2 Network Configuration

For simulation purposes, the network was configured to represent a typical WSN deployment scenario:

**Network Parameters:**
- **Network Area**: 200m × 200m square region
- **Node Distribution**: Random uniform distribution
- **Communication Range**: 30m (adjustable based on transmission power)
- **Base Station Location**: (100m, 220m) - outside the sensor field
- **Initial Energy**: 2.0 Joules per node (representing 2 AA batteries)

**Table 5.1** - Detailed Simulation Parameters:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Network Size | 25, 50, 75, 100 nodes | Variable for scalability analysis |
| Simulation Area | 200m × 200m | Square deployment region |
| Communication Range | 30m | Maximum single-hop distance |
| Initial Energy | 2.0 J | Per-node energy budget |
| Base Station Position | (100, 220) | Fixed sink location |
| Simulation Rounds | 500 | Total operational cycles |
| Data Packet Size | 500 bytes | Standard sensor data payload |
| Control Packet Size | 50 bytes | Routing control overhead |

## 5.3 Baseline Protocol Implementation

To ensure fair comparison, all baseline protocols were implemented using identical energy models, communication parameters, and network conditions.

### 5.3.1 LEACH Protocol Implementation

The LEACH (Low-Energy Adaptive Clustering Hierarchy) protocol implementation follows the original specification with the following key features:

**Implementation Details:**
- **Cluster Head Probability**: P = 0.05 (5% of nodes become cluster heads)
- **Setup Phase**: Cluster formation every 20 rounds
- **Steady State**: Data transmission within established clusters
- **Energy Model**: First-order radio model with distance-dependent transmission costs

**Key Functions:**
```python
def leach_cluster_head_selection(nodes, round_number, p=0.05):
    threshold = p / (1 - p * (round_number % (1/p)))
    cluster_heads = []
    for node in nodes:
        if random.random() < threshold:
            cluster_heads.append(node)
    return cluster_heads
```

### 5.3.2 PEGASIS Protocol Implementation

The PEGASIS (Power-Efficient Gathering in Sensor Information Systems) protocol creates a chain of nodes for energy-efficient data collection:

**Implementation Features:**
- **Chain Construction**: Greedy algorithm for minimum spanning chain
- **Leader Selection**: Rotating leadership based on residual energy
- **Data Fusion**: Binary tree aggregation along the chain
- **Energy Optimization**: Minimized transmission distances

**Chain Formation Algorithm:**
```python
def pegasis_chain_formation(nodes):
    unvisited = nodes.copy()
    chain = [unvisited.pop(0)]  # Start with arbitrary node
    
    while unvisited:
        current = chain[-1]
        nearest = min(unvisited, key=lambda n: distance(current, n))
        chain.append(nearest)
        unvisited.remove(nearest)
    
    return chain
```

### 5.3.3 HEED Protocol Implementation

The HEED (Hybrid Energy-Efficient Distributed clustering) protocol uses residual energy and communication cost for cluster head selection:

**Implementation Characteristics:**
- **Primary Parameter**: Residual energy ratio
- **Secondary Parameter**: Average minimum reachability power (AMRP)
- **Clustering Process**: Iterative probabilistic selection
- **Termination**: When all nodes join clusters or become cluster heads

**Cluster Head Selection:**
```python
def heed_cluster_head_probability(node, c_prob=0.05):
    energy_ratio = node.residual_energy / node.initial_energy
    return c_prob * energy_ratio
```

## 5.4 Performance Evaluation Metrics

### 5.4.1 Energy-Related Metrics

**Total Energy Consumption:**
```
E_total = Σ(E_tx + E_rx + E_sensing + E_processing)
```
where E_tx is transmission energy, E_rx is reception energy, E_sensing is sensing energy, and E_processing is data processing energy.

**Energy Consumption Per Round:**
```
E_per_round = E_total / Total_Rounds
```

**Energy Efficiency Ratio:**
```
Energy_Efficiency = Total_Packets_Delivered / E_total
```

### 5.4.2 Network Lifetime Metrics

**Network Lifetime (First Node Death):**
The number of rounds until the first node depletes its energy completely.

**Network Lifetime (k% Node Death):**
The number of rounds until k% of nodes become non-functional (typically k=10%, 50%, 90%).

**Average Residual Energy:**
```
E_residual_avg = (1/N) × Σ(E_remaining(i)) for i=1 to N
```

### 5.4.3 Communication Quality Metrics

**Packet Delivery Ratio (PDR):**
```
PDR = Packets_Successfully_Delivered / Total_Packets_Sent
```

**Average End-to-End Delay:**
```
Delay_avg = (1/M) × Σ(T_received(j) - T_sent(j)) for j=1 to M
```

**Network Coverage:**
Percentage of the deployment area covered by active sensor nodes.

## 5.5 Statistical Analysis Methodology

### 5.5.1 Experimental Design

**Replication Strategy:**
- Each protocol configuration was executed 10 independent times
- Different random seeds for each replication to ensure statistical independence
- Identical network topologies across protocol comparisons for each replication

**Significance Testing:**
- **Paired t-test**: For comparing mean energy consumption between protocols
- **ANOVA**: For analyzing variance across multiple protocols
- **Confidence Intervals**: 95% confidence level for all statistical measures
- **Effect Size**: Cohen's d for practical significance assessment

### 5.5.2 Data Collection and Processing

**Data Logging:**
All simulation runs generated comprehensive logs including:
- Per-round energy consumption for each node
- Packet transmission and reception records
- Cluster formation and routing decisions
- Protocol-specific operational parameters

**Data Validation:**
- **Consistency Checks**: Verification of energy conservation laws
- **Boundary Validation**: Ensuring realistic parameter ranges
- **Convergence Analysis**: Monitoring simulation stability
- **Outlier Detection**: Statistical identification and handling of anomalous results

## 5.6 Implementation Validation

### 5.6.1 Protocol Correctness Verification

Each protocol implementation was validated against published specifications:

**LEACH Validation:**
- Cluster head percentage maintained at target 5% (±1%)
- Setup phase timing matches original specification
- Energy consumption model verified against literature values

**PEGASIS Validation:**
- Chain formation produces connected topology
- Leader rotation follows energy-based selection
- Data aggregation reduces transmission overhead

**HEED Validation:**
- Convergence achieved within specified iteration limits
- Cluster head distribution follows energy-based probability
- Communication cost calculations match original formulation

### 5.6.2 Simulation Framework Validation

**Energy Model Accuracy:**
The energy consumption model was calibrated using real sensor node specifications:
- **Transmission Energy**: E_tx = E_elec × k + ε_amp × k × d²
- **Reception Energy**: E_rx = E_elec × k
- **Sensing Energy**: E_sense = 0.01 mJ per sample
- **Processing Energy**: E_proc = 0.005 mJ per operation

Where:
- E_elec = 50 nJ/bit (radio electronics energy)
- ε_amp = 100 pJ/bit/m² (amplifier energy)
- k = packet size in bits
- d = transmission distance in meters

**Calibration Results:**
The energy model was validated against published measurements from MicaZ and TelosB sensor platforms, showing <5% deviation from reported values.

## 5.7 Reproducibility Considerations

### 5.7.1 Code Availability

The complete simulation framework and protocol implementations are available as open-source software:
- **Repository**: Enhanced-EEHFR-WSN-Protocol
- **License**: MIT License for academic and commercial use
- **Documentation**: Comprehensive API documentation and usage examples
- **Test Suite**: Unit tests for all protocol components

### 5.7.2 Experimental Reproducibility

**Deterministic Elements:**
- Fixed random seeds for each experimental configuration
- Identical network topologies across protocol comparisons
- Standardized parameter settings documented in configuration files

**Variable Elements:**
- Random node failures (if enabled)
- Environmental interference simulation
- Dynamic topology changes (for mobility scenarios)

**Reproduction Instructions:**
Detailed instructions for reproducing all experimental results are provided in the project repository, including:
- Environment setup procedures
- Parameter configuration files
- Execution scripts for all experiments
- Data analysis and visualization code

This comprehensive experimental setup ensures that all performance comparisons are conducted under fair and controlled conditions, providing reliable and reproducible results for the Enhanced EEHFR protocol evaluation.
