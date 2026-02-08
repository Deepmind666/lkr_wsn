#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classical time-series baselines for environment mapping on Intel Lab dataset.
Models: SARIMAX (statsmodels), ETS (ExponentialSmoothing), TBATS (optional)
Output JSON compatible with plotting/stats pipeline: results/intel_<model>_envmap_compare.json
"""
import os, sys, json, argparse
import numpy as np
from typing import Optional
BASE_SEED = int(os.environ.get('AERIS_SEED', '44001'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from intel_dataset_loader import IntelLabDataLoader
from benchmark_protocols import NetworkConfig
from aeris_protocol import AerisProtocol

# Optional dependencies flags
_HAS_TBATS = False
_HAS_STATSMODELS = False
try:
    import statsmodels  # type: ignore
    _HAS_STATSMODELS = True
except Exception:
    _HAS_STATSMODELS = False

try:
    from tbats import TBATS  # type: ignore
    _HAS_TBATS = True
except Exception:
    _HAS_TBATS = False


def seasonal_naive_forecast(y: np.ndarray, horizon: int, sp: int) -> np.ndarray:
    if sp is None or sp <= 0 or len(y) < sp:
        # plain naive
        return np.full(horizon, float(y[-1]))
    ref = y[-sp:]
    reps = int(np.ceil(horizon / sp))
    fc = np.tile(ref, reps)[:horizon]
    return fc.astype(float)


def holt_winters_additive(y: np.ndarray, horizon: int, sp: int,
                          alpha: float = 0.2, beta: float = 0.05, gamma: float = 0.2) -> np.ndarray:
    # Simple additive Holt-Winters fallback implementation
    y = np.asarray(y, dtype=float)
    n = len(y)
    if sp is None or sp <= 1 or n < 2 * sp:
        # fall back to Holt's linear (no season)
        l = y[0]
        b = y[1] - y[0]
        for t in range(2, n):
            prev_l = l
            l = alpha * y[t] + (1 - alpha) * (l + b)
            b = beta * (l - prev_l) + (1 - beta) * b
        return np.array([l + (i + 1) * b for i in range(horizon)], dtype=float)
    # Initialize seasonal indices
    season = np.zeros(sp)
    season[:] = (y[:sp] - y[:sp].mean())
    l = y[:sp].mean()
    b = (y[sp:2 * sp].mean() - y[:sp].mean()) / sp
    for t in range(n):
        s_t = season[t % sp]
        prev_l = l
        l = alpha * (y[t] - s_t) + (1 - alpha) * (l + b)
        b = beta * (l - prev_l) + (1 - beta) * b
        season[t % sp] = gamma * (y[t] - l) + (1 - gamma) * s_t
    fc = np.zeros(horizon)
    for i in range(horizon):
        fc[i] = l + (i + 1) * b + season[(n + i) % sp]
    return fc.astype(float)


def fit_predict_sarimax(hum: np.ndarray, tmp: np.ndarray, horizon: int = 200, sp: int = 288) -> np.ndarray:
    if _HAS_STATSMODELS:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        use_seasonal = (sp is not None) and (len(hum) >= 3 * max(24, sp))
        order = (2, 1, 2)
        seasonal_order = (1, 0, 1, sp) if use_seasonal else (0, 0, 0, 0)
        exog = tmp.reshape(-1, 1)
        model = SARIMAX(hum, order=order, seasonal_order=seasonal_order, exog=exog,
                        enforce_stationarity=False, enforce_invertibility=False)
        res = model.fit(disp=False)
        future_exog = np.full((horizon, 1), float(tmp[-1]))
        fc = res.forecast(steps=horizon, exog=future_exog)
        return np.asarray(fc, dtype=float)
    # Fallback: seasonal naive using humidity only
    return seasonal_naive_forecast(hum, horizon, sp)


def fit_predict_ets(hum: np.ndarray, horizon: int = 200, sp: int = 288) -> np.ndarray:
    if _HAS_STATSMODELS:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        use_seasonal = (sp is not None) and (len(hum) >= 3 * max(24, sp))
        if use_seasonal:
            model = ExponentialSmoothing(hum, trend='add', seasonal='add', seasonal_periods=sp, initialization_method='estimated')
        else:
            model = ExponentialSmoothing(hum, trend='add', seasonal=None, initialization_method='estimated')
        res = model.fit(optimized=True)
        fc = res.forecast(horizon)
        return np.asarray(fc, dtype=float)
    # Fallback: Holt-Winters additive
    return holt_winters_additive(hum, horizon, sp)


def fit_predict_tbats(hum: np.ndarray, horizon: int = 200, sp: int = 288, max_train: int = 20000) -> np.ndarray:
    if not _HAS_TBATS:
        raise RuntimeError('TBATS not available (pip install tbats)')
    x = hum[-max_train:]
    seasonal_periods = [p for p in [sp] if (p is not None) and (len(x) >= 3 * p)]
    estimator = TBATS(seasonal_periods=seasonal_periods or None, use_arma_errors=True, use_box_cox=False)
    model = estimator.fit(x)
    fc = model.forecast(steps=horizon)
    return np.asarray(fc, dtype=float)


def build_env_provider(hum_pred: np.ndarray):
    p33 = np.percentile(hum_pred, 33)
    p66 = np.percentile(hum_pred, 66)
    def builder(proto):
        def env_provider(round_idx: int):
            h = float(hum_pred[min(round_idx, len(hum_pred)-1)])
            if h < p33:
                shadow, nf = 4.5, -96.0
            elif h < p66:
                shadow, nf = 7.0, -95.5
            else:
                shadow, nf = 9.5, -95.0
            proto.channel_model.set_env_mapping(shadowing_std=shadow, noise_floor_dbm=nf)
            return (25.0, h/100.0)
        return env_provider
    return builder


def simulate_with_env(xs, ys, hum_pred: np.ndarray, profile: str = 'energy', seed: Optional[int] = None):
    import random
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    n = len(xs)
    w = max(xs) - min(xs) if max(xs) > min(xs) else 40.0
    h = max(ys) - min(ys) if max(ys) > min(ys) else 30.0
    cfg = NetworkConfig(num_nodes=n, area_width=w, area_height=h, initial_energy=2.0, packet_size=1024)
    proto = AerisProtocol(cfg, enable_cas=True, enable_fairness=True, enable_gateway=True, enable_skeleton=False, profile=profile, verbose=False, seed=seed)
    minx, miny = min(xs), min(ys)
    for i, (x, y) in enumerate(zip(xs, ys)):
        proto.nodes[i].x = float(x) - minx
        proto.nodes[i].y = float(y) - miny
    envp = build_env_provider(hum_pred)(proto)
    return proto.run_simulation(200, env_provider=envp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', type=str, choices=['sarimax', 'ets', 'tbats'], required=True)
    ap.add_argument('--train_len', type=int, default=20000, help='number of rows from the start to use for training')
    ap.add_argument('--horizon', type=int, default=200)
    ap.add_argument('--seasonal_period', type=int, default=288, help='seasonal period (e.g., 288 for 5-min samples per day)')
    ap.add_argument('--strict', action='store_true', help='require true model; do not fallback when dependency missing')
    args = ap.parse_args()

    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    loader = IntelLabDataLoader(data_dir=data_dir, use_synthetic=False)
    s = loader.sensor_data.dropna(subset=['humidity','temperature'])
    s = s.iloc[:max(1000, int(args.train_len))]
    hum = s['humidity'].values.astype(np.float64)
    tmp = s['temperature'].values.astype(np.float64)

    if args.model == 'sarimax':
        if args.strict and not _HAS_STATSMODELS:
            raise RuntimeError('Strict mode: statsmodels is required for SARIMAX, but not available.')
        hum_pred = fit_predict_sarimax(hum, tmp, horizon=args.horizon, sp=args.seasonal_period)
    elif args.model == 'ets':
        if args.strict and not _HAS_STATSMODELS:
            raise RuntimeError('Strict mode: statsmodels is required for ETS, but not available.')
        hum_pred = fit_predict_ets(hum, horizon=args.horizon, sp=args.seasonal_period)
    else:  # tbats
        if args.strict and not _HAS_TBATS:
            raise RuntimeError('Strict mode: tbats package is required for TBATS, but not available.')
        hum_pred = fit_predict_tbats(hum, horizon=args.horizon, sp=args.seasonal_period)

    hum_pred = np.clip(hum_pred, 0.0, 100.0)

    locs = loader.locations_data.sort_values('node_id')
    xs, ys = locs['x'].to_list(), locs['y'].to_list()

    seed_energy = BASE_SEED
    seed_robust = BASE_SEED + 1
    res_energy = simulate_with_env(xs, ys, hum_pred, profile='energy', seed=seed_energy)
    res_robust = simulate_with_env(xs, ys, hum_pred, profile='robust', seed=seed_robust)

    meta = {
        'model': args.model,
        'train_len': int(args.train_len),
        'horizon': int(args.horizon),
        'seasonal_period': int(args.seasonal_period),
        'tbats_available': _HAS_TBATS,
        'statsmodels_available': _HAS_STATSMODELS,
        'fallbacks': {
            'sarimax': (not _HAS_STATSMODELS),
            'ets': (not _HAS_STATSMODELS),
        },
        'runtime': {
            'seed_energy': seed_energy,
            'seed_robust': seed_robust
        }
    }

    out = {
        'AETHER_energy': {k: res_energy.get(k) for k in ('total_energy_consumed', 'packet_delivery_ratio', 'packet_delivery_ratio_end2end', 'final_alive_nodes')},
        'AETHER_robust': {k: res_robust.get(k) for k in ('total_energy_consumed', 'packet_delivery_ratio', 'packet_delivery_ratio_end2end', 'final_alive_nodes')},
        'classical': meta
    }

    out_name = f"intel_{args.model}_envmap_compare.json"
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', out_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('Saved', out_path)

if __name__ == '__main__':
    main()