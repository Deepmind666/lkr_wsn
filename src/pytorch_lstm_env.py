# PyTorch-based LSTM for environment (humidity/temperature) forecasting to drive channel mapping
# Trains on Intel Lab public dataset time series and produces per-round humidity predictions.

from __future__ import annotations
import os, math
from typing import Tuple, Optional
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader

class SeqDataset(Dataset):
    def __init__(self, series: np.ndarray, seq_len: int = 64, pred_h: int = 1, stride: int = 1):
        assert series.ndim == 2  # [T, F]
        self.X = []
        self.y = []
        T = series.shape[0]
        for i in range(0, T - seq_len - pred_h + 1, stride):
            self.X.append(series[i:i+seq_len])
            self.y.append(series[i+seq_len:i+seq_len+pred_h, 0])  # predict humidity only (col 0)
        self.X = torch.tensor(np.array(self.X), dtype=torch.float32)
        self.y = torch.tensor(np.array(self.y), dtype=torch.float32)
    def __len__(self):
        return self.X.shape[0]
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

class LSTMRegressor(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 64, num_layers: int = 2, out_h: int = 1, dropout: float = 0.1):
        super().__init__()
        self.lstm = nn.LSTM(input_size=in_dim, hidden_size=hidden, num_layers=num_layers, batch_first=True, dropout=dropout)
        self.head = nn.Sequential(nn.Linear(hidden, hidden//2), nn.ReLU(), nn.Linear(hidden//2, out_h))
    def forward(self, x):  # x: [B, T, F]
        out, _ = self.lstm(x)
        out = out[:, -1, :]  # last step
        return self.head(out)  # [B, out_h]

class Scaler:
    def __init__(self):
        self.mean: Optional[np.ndarray] = None
        self.std: Optional[np.ndarray] = None
    def fit(self, x: np.ndarray):
        self.mean = x.mean(axis=0, keepdims=True)
        self.std = x.std(axis=0, keepdims=True) + 1e-8
    def transform(self, x: np.ndarray) -> np.ndarray:
        return (x - self.mean) / self.std
    def inverse_transform(self, x: np.ndarray) -> np.ndarray:
        return x * self.std + self.mean

@torch.no_grad()
def roll_forecast(model: nn.Module, seed_seq: np.ndarray, horizon: int, scaler: Scaler, device: torch.device) -> np.ndarray:
    """Autoregressive roll-out forecast on humidity (column 0).
    seed_seq: [Tseed, F] normalized; returns [horizon] humidity in original scale [0..100]
    Note: device parameter is ignored; we infer model device to avoid mismatches.
    """
    model.eval()
    model_dev = next(model.parameters()).device
    seq = seed_seq.copy()
    preds = []
    for _ in range(horizon):
        x = torch.tensor(seq[None, ...], dtype=torch.float32, device=model_dev)
        y_norm = model(x).squeeze(0).detach().cpu().numpy()  # [1]
        # append predicted humidity (column 0), keep temperature last observed
        next_step = seq[-1].copy()
        next_step[0] = y_norm[0]
        seq = np.vstack([seq[1:], next_step])
        preds.append(y_norm[0])
    preds = np.array(preds)  # normalized
    hum_pred = scaler.inverse_transform(np.column_stack([preds, np.zeros_like(preds)]))[:, 0]
    hum_pred = np.clip(hum_pred, 0.0, 100.0)
    return hum_pred

def train_lstm_env(series: np.ndarray, seq_len: int = 64, pred_h: int = 1, epochs: int = 10, batch_size: int = 256, lr: float = 1e-3,
                   val_split: float = 0.1, num_workers: int = 0, device: Optional[torch.device] = None, seed: int = 42, stride: int = 1) -> Tuple[nn.Module, Scaler]:
    """Train an LSTM to predict next-step humidity from [humidity, temperature] series.
    series: [T, 2], columns: [humidity(0..100), temperature(C)]
    Returns: trained model and fitted scaler (standardize both features)
    """
    torch.manual_seed(seed)
    np.random.seed(seed)
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    # Safety: RTX 50xx (sm_120) not yet supported by many wheels
    if device.type == 'cuda':
        try:
            maj, minr = torch.cuda.get_device_capability()
            if maj >= 12:
                print('[WARN] Detected CUDA capability sm_%d%d; falling back to CPU due to missing kernels in current wheel' % (maj, minr))
                device = torch.device('cpu')
        except Exception:
            pass
    # standardize
    scaler = Scaler()
    scaler.fit(series)
    series_norm = scaler.transform(series)
    # dataset
    ds = SeqDataset(series_norm, seq_len=seq_len, pred_h=pred_h, stride=max(1, int(stride)))
    N = len(ds)
    n_val = max(1, int(N * val_split))
    n_train = N - n_val
    tr_ds, va_ds = torch.utils.data.random_split(ds, [n_train, n_val], generator=torch.Generator().manual_seed(seed))
    tr_dl = DataLoader(tr_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    va_dl = DataLoader(va_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    # model
    try:
        model = LSTMRegressor(in_dim=2, hidden=128, num_layers=2, out_h=1, dropout=0.1).to(device)
    except RuntimeError as e:
        # Fallback for very new GPUs without compiled kernels (e.g., sm_120)
        print('[WARN] CUDA not usable for this GPU build, falling back to CPU. Error:', str(e))
        device = torch.device('cpu')
        model = LSTMRegressor(in_dim=2, hidden=128, num_layers=2, out_h=1, dropout=0.1).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    crit = nn.MSELoss()
    best_va = math.inf
    patience, bad = 5, 0
    for ep in range(epochs):
        model.train(); tr_loss = 0.0
        for xb, yb in tr_dl:
            xb = xb.to(device); yb = yb.to(device)
            opt.zero_grad(); pred = model(xb)
            loss = crit(pred, yb)
            loss.backward(); opt.step()
            tr_loss += loss.item() * xb.size(0)
        tr_loss /= n_train
        # val
        model.eval(); va_loss = 0.0
        with torch.no_grad():
            for xb, yb in va_dl:
                xb = xb.to(device); yb = yb.to(device)
                pred = model(xb)
                va_loss += crit(pred, yb).item() * xb.size(0)
        va_loss /= n_val
        if va_loss < best_va - 1e-6:
            best_va = va_loss; bad = 0
            best_state = {k: v.cpu() for k, v in model.state_dict().items()}
        else:
            bad += 1
        if bad >= patience:
            break
    model.load_state_dict({k: v.to(device) for k, v in best_state.items()})
    return model, scaler

