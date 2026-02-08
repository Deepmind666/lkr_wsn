# Section 5: Experimental Setup

---

## 5. Experimental Setup

This section describes the simulation environment, baselines, metrics, and
statistical reporting used in the publication results.

### 5.1 Simulation Environment

- **Simulator**: Custom Python simulator (Python 3.10)
- **Random seeds**: 42001-42030 (n=30)
- **Energy model**: CC2420 TelosB calibrated (ImprovedEnergyModel)
- **Channel model**: RealisticChannelModel with environment-specific parameters
- **Reproducibility**: All runs use fixed seeds and logged metadata

### 5.2 Network Configuration (Publication Runs)

**Table 5.1: Default Parameters (Publication Tier)**

| Parameter | Value |
|---|---|
| Nodes (N) | 100 |
| Area | 200m x 200m |
| Base station | (100, 200) |
| Rounds | 300 |
| Packet size | 1024 bytes (8192 bits) |
| Initial energy | 2.0 J |
| TX power | 10 dBm |
| Dropout rate | 0.0 |
| Deployment | Uniform random |

**Environments (multi-env runs)**:
indoor_office, indoor_factory, outdoor_urban, outdoor_suburban

### 5.3 Baseline Protocols

We compare AERIS against four representative baselines:
LEACH, PEGASIS, HEED, and TEEN.

### 5.4 Evaluation Metrics

**Primary metric**:  
PDR_expected = bs_delivered / source_packets_expected

**Secondary metrics** (reported when available):  
total_energy_consumed, first_node_death_round, total_rounds

### 5.5 Statistical Reporting

All publication results use n=30 independent seeds. We report mean +/- std.
No hypothesis tests are included unless explicitly stated in the results.

### 5.6 Fairness Controls

All protocols use:
1) Identical node positions per seed  
2) Identical channel model instance per seed  
3) Identical TX power and packet size  

### 5.7 Evidence Files (Publication Tier)

- C:\AERIS-WSN-Protocol\results\mega_experiments\fair_5protocol_20260206_000956.json  
- C:\AERIS-WSN-Protocol\results\mega_experiments\env_sensitivity_20260206_013048.json  
- C:\AERIS-WSN-Protocol\results\mega_experiments\ablation_diag_20260205_144709.json  
- C:\AERIS-WSN-Protocol\results\mega_experiments\ablation_diag_multi_20260206_020002.json  
- C:\AERIS-WSN-Protocol\results\mega_experiments\cas_weight_sweep_full_20260206_000736.json  

