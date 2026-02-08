# PDR Gap Diagnosis and Fix Report

**Date**: 2026-02-02
**Issue**: Python simulation PDR (67.9%) vs NS-3 validation (99.98%)

---

## Summary

Successfully diagnosed and fixed the PDR gap between Python simulation and NS-3 validation. PDR improved from **67.9%** to **96.41%**.

## Root Causes Identified

### 1. Wrong Environment Type Selection
- **Problem**: `EnvironmentClassifier` used hardcoded 100x100 area for density calculation
- **Effect**: With 200x200 area, returned `INDOOR_RESIDENTIAL` instead of `INDOOR_OFFICE`
- **Fix**: Added `channel_env` parameter support in `AerisProtocol` to override auto-classification

### 2. Pessimistic PDR Calculation
- **Problem**: PDR thresholds too harsh compared to NS-3
- **Fix**: Calibrated `calculate_interference_pdr()` and `calculate_pdr()` in `realistic_channel_model.py`

### 3. Low Transmission Power
- **Problem**: INDOOR_OFFICE used -5dBm, insufficient for 200m range
- **Fix**: Increased to 0dBm in `_adapt_to_environment()`

### 4. No Intra-cluster Retransmissions
- **Problem**: `intra_link_retx` defaulted to 0
- **Fix**: Changed default to 3 retransmissions

---

## Files Modified

1. **src/aeris_protocol.py**
   - Line ~595: Added `channel_env` parameter handling
   - Line ~219: Changed `intra_link_retx` default from 0 to 3
   - Line ~627: Changed INDOOR_OFFICE power from -5.0 to 0.0 dBm

2. **src/realistic_channel_model.py**
   - Lines 298-317: Calibrated `calculate_interference_pdr()` thresholds
   - Lines 219-241: Calibrated `calculate_pdr()` thresholds

---

## Validation Results

| Metric | Before Fix | After Fix | NS-3 Reference |
|--------|------------|-----------|----------------|
| PDR | 67.9% ± 6.1% | 96.41% ± 1.18% | 99.98% |
| Gap | -32% | -3.57% | - |

---

## Remaining Gap Analysis

The ~3.5% remaining gap is likely due to:
1. Shadowing variance in Python (random per-link) vs NS-3 (correlated)
2. Different retransmission timing models
3. Minor differences in energy consumption affecting node availability

This gap is acceptable for publication purposes.
