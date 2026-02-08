# Supplementary Materials for AERIS Paper

## S1. Prior Experiments (Evidence-0)

### S1.1 E0: Environment-Link Correlation Analysis

**Data Source**: Intel Lab trace (483,427 records, 13 nodes, 33 days)

**Correlation Results**:

| Feature | Metric | Pearson r | p-value | Spearman ρ | p-value |
|---------|--------|-----------|---------|------------|---------|
| humidity | link_quality | -0.499 | <0.001 | -0.486 | <0.001 |
| temperature | link_quality | -0.292 | <0.001 | 0.019 | <0.001 |
| temp_diff | link_quality | -0.127 | <0.001 | -0.016 | <0.001 |
| humidity_diff | link_quality | -0.073 | <0.001 | -0.011 | <0.001 |

**Predictor Performance**:
- Features: temperature, humidity, voltage
- AUC: 0.990
- Brier Score: 0.002
- Cross-validation: 5-fold

**Lagged Correlation**:
- Humidity: max correlation at lag=2h (r=0.658)
- Temperature: max correlation at lag=0h (r=0.567)

**Permutation Test**:
- Humidity: observed r=-0.499, p=0.000 (1000 permutations)
- Temperature: observed r=-0.292, p=0.000 (1000 permutations)

### S1.2 E1: CAS Feature Contribution Analysis

**Data Source**: CAS dataset (41,523 samples, 7 features)

**Model Performance**:
- Accuracy: 0.900
- AUC (OvR): 0.969

**Feature Importance (Permutation)**:

| Rank | Feature | Importance | Coefficient | p-value |
|------|---------|------------|-------------|---------|
| 1 | energy | 0.160 | 1.042 | <0.001 |
| 2 | link | 0.160 | 2.461 | <0.001 |
| 3 | radius | 0.023 | 0.290 | <0.001 |
| 4 | fairness | 0.022 | 1.509 | <0.001 |
| 5 | dist_bs | 0.003 | 0.168 | <0.001 |
| 6 | tail_max | 0.002 | 0.091 | <0.001 |
| 7 | density | 0.001 | 0.051 | <0.001 |

### S1.3 E2: Safety Threshold Calibration

**Method**: Beta-Binomial probabilistic model

**Optimization Results**:
- Optimal θ: 0.647
- Optimal T: 14
- False Positive Rate: 0.0%
- True Positive Rate: 100.0%
- F1 Score: 1.000

**Beta Posterior Parameters** (T=15):
- α_posterior: 894
- β_posterior: 98
- Posterior mean: 0.901
- 95% Credible Interval: [0.882, 0.919]

### S1.4 E3: Load Balance Verification

**Data Source**: 500 simulated load distributions

**Correlation Results**:

| Metric Pair | Pearson r | p-value |
|-------------|-----------|---------|
| Gini vs PDR | -0.749 | <0.001 |
| Gini vs Energy | 0.706 | <0.001 |
| Jain vs PDR | 0.744 | <0.001 |
| Jain vs Energy | -0.695 | <0.001 |

**Effect Sizes**:

| Comparison | Hedges g | Interpretation |
|------------|----------|----------------|
| balanced vs skewed (PDR) | 1.255 | Large |
| balanced vs moderate (PDR) | 2.091 | Large |
| balanced vs skewed (Energy) | -1.236 | Large |
| balanced vs moderate (Energy) | -1.906 | Large |

### S1.5 E4: MCU Decision Latency

**Benchmark Results**:

| Component | Mean (ms) | P95 (ms) | Within Budget |
|-----------|-----------|----------|---------------|
| CAS | 4.51 | 4.80 | ✓ |
| Skeleton (5 CHs) | 36.25 | 47.71 | ✗ |
| Skeleton (10 CHs) | 60.34 | 81.47 | ✗ |
| Gateway (5 CHs) | 6.99 | 7.50 | ✓ |
| Gateway (10 CHs) | 17.30 | 21.73 | ✓ |
| **Total** | **167.62** | **232.70** | **✗** |

**ML/RL Comparison**:

| Method | Latency (ms) | AERIS Speedup |
|--------|--------------|---------------|
| Q-Learning | 65 | 0.39x |
| DQN | 150 | 0.89x |
| Actor-Critic | 200 | 1.19x |
| LSTM-based | 350 | 2.09x |
| GNN-based | 600 | 3.58x |

---

## S2. Statistical Validation

### S2.1 Ablation Experiment Results

**Data Source**: results/intel_ablation.json (verified)
**Sample Size**: 50 per configuration

**PDR Results**:

| Configuration | Mean | 95% CI | Std |
|---------------|------|--------|-----|
| FULL | 0.477 | [0.470, 0.484] | 0.025 |
| -CAS | 0.481 | [0.474, 0.487] | 0.023 |
| -FAIR | 0.479 | [0.473, 0.485] | 0.021 |
| -GW | 0.383 | [0.379, 0.388] | 0.016 |
| -SAFETY | 0.369 | [0.358, 0.379] | 0.036 |

### S2.2 Effect Size Analysis

**Note**: Effect sizes calculated using correct data source (intel_ablation.json, n=50 per config)

| Comparison | Hedges g | 95% CI | Interpretation |
|------------|----------|--------|----------------|
| FULL vs -CAS (PDR) | -0.15 | [-0.51, 0.25] | Negligible |
| FULL vs -FAIR (PDR) | -0.10 | [-0.52, 0.31] | Negligible |
| FULL vs -GW (PDR) | 4.48 | [3.83, 5.30] | Large |
| FULL vs -SAFETY (PDR) | 3.48 | [3.02, 4.13] | Large |

### S2.3 Welch t-Test Results

| Comparison | t-statistic | df | p-value | Significant |
|------------|-------------|-----|---------|-------------|
| FULL vs -CAS (PDR) | -0.73 | 98 | 0.466 | No |
| FULL vs -FAIR (PDR) | -0.49 | 98 | 0.627 | No |
| FULL vs -GW (PDR) | 21.41 | 98 | <0.001 | Yes |
| FULL vs -SAFETY (PDR) | 16.63 | 98 | <0.001 | Yes |

### S2.4 Holm-Bonferroni Correction

| Rank | Comparison | Original p | Corrected p | Significant |
|------|------------|------------|-------------|-------------|
| 1 | FULL vs -GW (PDR) | <0.001 | <0.001 | Yes |
| 2 | FULL vs -SAFETY (PDR) | <0.001 | <0.001 | Yes |
| 3 | FULL vs -FAIR (PDR) | 0.627 | 0.627 | No |
| 4 | FULL vs -CAS (PDR) | 0.466 | 0.627 | No |

---

## S3. Experiment Configuration

### S3.1 Network Parameters

| Parameter | Value |
|-----------|-------|
| Area | 100m × 100m |
| Nodes | 50-100 |
| Initial Energy | 2.0 J |
| Packet Size | 512-2048 bytes |
| Rounds | 100-300 |

### S3.2 Energy Model (CC2420/TelosB)

| Parameter | Value |
|-----------|-------|
| TX Energy | 208.8 nJ/bit |
| RX Energy | 225.6 nJ/bit |
| Idle Power | 1.28 mW |
| Sleep Power | 0.06 mW |

### S3.3 Random Seeds

- Ablation experiments: seeds 0-199
- Significance tests: seeds 43001-43010
- Experiment matrix: seeds 0-4

---

## S4. Figure List

| Figure | Description | Location |
|--------|-------------|----------|
| S1 | E0 Correlation Heatmap | e0_correlation_heatmap.pdf |
| S2 | E0 Humidity-Link Scatter | e0_humidity_vs_link.pdf |
| S3 | E1 Feature Importance | e1_feature_importance.pdf |
| S4 | E2 FPR/TPR Surface | e2_fpr_surface.pdf |
| S5 | E3 Load Distribution | e3_load_distribution.pdf |
| S6 | E4 Latency ECDF | e4_latency_ecdf.pdf |
| S7 | Prior Experiments Summary | prior_experiments_summary.pdf |
| S8 | Statistical Summary | statistical_summary.pdf |

---

## S5. Data Availability

All experimental data and scripts are available at:
- Prior experiments: `results/prior_experiments/`
- Statistical validation: `results/statistical_validation/`
- Figures: `results/publication_figures/`

Reproduction scripts:
- `scripts/prior_experiments/run_e0_env_link.py`
- `scripts/prior_experiments/run_e1_cas_features.py`
- `scripts/prior_experiments/run_e2_safety_threshold.py`
- `scripts/prior_experiments/run_e3_load_balance.py`
- `scripts/prior_experiments/run_e4_latency.py`
- `scripts/statistical_validation/run_comprehensive_validation.py`
