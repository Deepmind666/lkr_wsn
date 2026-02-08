AERIS (Interview Edition) (historical naming: Enhanced AERIS/EASR)

Positioning
- Problem: Energy-efficient, reliable routing for dense IoT/WSN under dynamic environments (temperature/humidity interference, topology churn, gateway load).
- Our Angle: Environment-aware, two-stage energy-efficient hierarchical routing with predictive traffic and uncertainty-aware decision fusion.
- Outcome: Higher PDR, lower energy and hotspot risk, longer network lifetime vs. LEACH/PEGASIS/TEEN and enhanced variants.

Core Stack (for interview)
- Predictive traffic: PatchTST-guided environment mapping (fast-track: DLinear fallback) to anticipate load/interference.
- Two-stage routing: (1) CH candidate scoring by entropy-weighted multi-criteria (energy, link quality, predicted load), (2) fuzzy soft-decision for final CH and gateway.
- Dynamic gateway: Gateway selection with stability/latency balance; adaptive backoff under congestion.
- Safety/robustness: Uncertainty grid, redundancy budget sweep, significance testing across topologies.

Key Innovations
- Environment-aware QoS coupling: Use exogenous signals (T/H, temporal patterns) to steer clustering and gateway.
- Entropy-weight + fuzzy logic: Stable yet adaptive CH selection under noisy metrics; interpretable rule base.
- Dynamic gateway policy: Reduces sink hotspots and balances energy, extending lifetime.
- Evidence chain: Full stats testing (bootstrap, multi-test), ablation, sensitivity, multi-topology generalization.

System Design Notes
- Data path: Intel Lab dataset -> env-map generator -> predictive load -> routing decisions.
- Decision fusion: EWM (entropy weights) -> fuzzy inference -> final CH/gateway roles.
- Runtime: Lightweight on-node rules; heavy prediction centralized/offline (or staggered edge nodes).
- Fallbacks: DLinear path for low-resource setups; rule-only mode if predictors unavailable.

Results Highlights (from repo outputs)
- Higher PDR at lower energy per round on Intel-like topologies (see curated SVGs).
- Lifetime gain: Delayed first-node-dead and increased rounds-to-DF (depletion fraction) vs baselines.
- Robustness: Positive effects persist across sensitivity and multi-topology grids; significance maintained.

Interview Demo Plan (5–7 min)
1) Open curated figures: results/plots_curated (PDR/energy/lifetime, significance, uncertainty grid).
2) Tell the story: Predict -> Score -> Fuzzy decide -> Dynamic gateway.
3) Point to evidence: Manifest.json + publication_figures. Show one ablation and one sensitivity chart.
4) Close with practical tie-ins: Edge deployment knobs, gateway limits, fail-safes.

Figure Checklist (quick refs)
- PDR & Energy trade-off: publication_figures/*pdr_energy*.svg
- Lifetime & Survivability: plots_curated/*lifetime*.svg
- Significance (multi-topology): plots_curated/*significance*.svg
- Uncertainty grid heatmaps: plots_curated/*uncertainty_grid*.svg
- Ablation & sensitivity: plots_curated/*ablation* / *sensitivity*.svg

How to Reproduce quickly
- CPU tracks (fast): python scripts\run_intel_dlinear_envmap.py; python scripts\run_intel_tcn_envmap.py
- Full figures (Windows): python scripts\curate_figures.py (curates existing outputs)
- WSL GPU batch: scripts/gpu_watch_and_launch.sh (see results/logs)

Q&A Nuggets
- Why PatchTST? Captures multi-scale temporal seasonality for load/gateway pressure forecasting. DLinear fallback ensures speed and stability.
- Why entropy + fuzzy? Entropy weights reduce bias; fuzzy soft decisions smooth noisy metrics and prevent oscillation.
- How robust? Verified via bootstrap, multi-topology significance, and uncertainty stress grids.
- What fails? Predictors unavailable -> degrade to rule-only with dynamic gateway; still beats naive baselines.

Applications
- Smart buildings/corridors, campus IoT, underground sensing with harsh channels, intermittent gateways.
- Transferable to ad-hoc/DTN with gateway selection and predictive congestion control.