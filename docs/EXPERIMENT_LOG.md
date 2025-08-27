## Experiment Logbook (AETHER WSN)

2025-08-26
- Intel replay (real geometry) established; results saved to results/intel_replay_compare.json
- Environment→channel conservative mapping adopted (humidity→shadowing_std; temp→noise floor)
- LSTM/TCN predictors integrated to drive time-varying channel; results saved to results/intel_lstm_envmap_compare.json and results/intel_tcn_envmap_compare.json
- Parallel significance (Intel) with repeats=20 completed; results at results/significance_compare_intel_parallel.json
- Extended LSTM training (full dataset; seq_len=128; epochs up to 150; stride=8) with 500-round simulation: results at results/intel_lstm_envmap_extended.json

Notes
- RTX 5090 (sm_120) not yet fully supported by current PyTorch wheels; training auto-falls back to CPU; switch to GPU once official wheel ships
- Round statistics now include env/safety fields for deeper analysis
- LEACH baseline integrated and run on Intel real geometry; results at results/intel_baseline_leach.json
- CRITICAL: Need to unify PDR metric definitions across protocols (LEACH internal vs AETHER end-to-end to BS)
- Next: expand Intel repeats to 50; unify PDR metrics; add HEED/PEGASIS; produce trade-off curves for strong fallback

