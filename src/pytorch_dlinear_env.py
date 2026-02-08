# Lightweight DLinear-style model for environment forecasting (humidity)
from __future__ import annotations
from typing import Optional, Tuple
import os
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader

class Scaler:
    def __init__(self):
        self.mean = None
        self.std = None
    def fit(self, x: np.ndarray):
        self.mean = x.mean(axis=0, keepdims=True)
        self.std = x.std(axis=0, keepdims=True) + 1e-8
    def transform(self, x: np.ndarray) -> np.ndarray:
        return (x - self.mean) / self.std
    def inverse_transform(self, x: np.ndarray) -> np.ndarray:
        return x * self.std + self.mean

class SeqDataset(Dataset):
    def __init__(self, series: np.ndarray, seq_len: int = 64, pred_h: int = 1, stride: int = 1):
        assert series.ndim == 2
        T = series.shape[0]
        X, y = [], []
        for i in range(0, T - seq_len - pred_h + 1, max(1, int(stride))):
            X.append(series[i:i+seq_len])
            y.append(series[i+seq_len:i+seq_len+pred_h, 0])  # humidity next-step
        self.X = torch.tensor(np.array(X), dtype=torch.float32)
        self.y = torch.tensor(np.array(y), dtype=torch.float32)
    def __len__(self):
        return self.X.shape[0]
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

class DLinearHead(nn.Module):
    """ DLinear-like: a linear projection on flattened past window. """
    def __init__(self, in_dim: int, seq_len: int, out_h: int = 1):
        super().__init__()
        self.fc = nn.Linear(in_dim * seq_len, out_h)
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, F]
        B, T, F = x.shape
        z = x.reshape(B, T*F)
        return self.fc(z)

class DLinearEnv(nn.Module):
    def __init__(self, in_dim: int = 2, seq_len: int = 64, out_h: int = 1):
        super().__init__()
        self.backbone = DLinearHead(in_dim, seq_len, out_h)
    def forward(self, x):
        return self.backbone(x)


def train_dlinear_env(series: np.ndarray, seq_len: int = 64, pred_h: int = 1, epochs: int = 50, batch_size: int = 1024,
                       lr: float = 1e-3, val_split: float = 0.1, device: Optional[torch.device] = None, stride: int = 1, seed: int = 42,
                       num_workers: Optional[int] = None, pin_memory: Optional[bool] = None, persistent_workers: Optional[bool] = None,
                       prefetch_factor: Optional[int] = None, non_blocking: Optional[bool] = None) -> Tuple[nn.Module, Scaler]:
    torch.manual_seed(seed); np.random.seed(seed)
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    # Env-driven defaults
    def _env_bool(key: str, default: bool) -> bool:
        v = os.environ.get(key)
        if v is None:
            return default
        return v.strip().lower() in ('1','true','yes','y','on')
    if num_workers is None:
        num_workers = int(os.environ.get('DL_NUM_WORKERS', '0'))
    if pin_memory is None:
        pin_memory = _env_bool('DL_PIN_MEMORY', device.type == 'cuda')
    if persistent_workers is None:
        persistent_workers = _env_bool('DL_PERSISTENT_WORKERS', num_workers > 0)
    if prefetch_factor is None:
        prefetch_factor = int(os.environ.get('DL_PREFETCH_FACTOR', '2'))
    if non_blocking is None:
        non_blocking = _env_bool('DL_NON_BLOCKING', device.type == 'cuda')

    scaler = Scaler(); scaler.fit(series)
    series_n = scaler.transform(series)
    ds = SeqDataset(series_n, seq_len=seq_len, pred_h=pred_h, stride=stride)
    N = len(ds); n_val = max(1, int(N * val_split)); n_tr = N - n_val
    tr_ds, va_ds = torch.utils.data.random_split(ds, [n_tr, n_val], generator=torch.Generator().manual_seed(seed))
    dl_kwargs = dict(batch_size=batch_size, pin_memory=pin_memory)
    if num_workers and num_workers > 0:
        dl_kwargs.update(num_workers=num_workers, persistent_workers=persistent_workers, prefetch_factor=prefetch_factor)
    else:
        dl_kwargs.update(num_workers=0)
    tr_dl = DataLoader(tr_ds, shuffle=True, **dl_kwargs)
    va_dl = DataLoader(va_ds, shuffle=False, **dl_kwargs)
    model = DLinearEnv(in_dim=series.shape[1], seq_len=seq_len, out_h=1).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    crit = nn.MSELoss()
    best = float('inf'); patience=10; bad=0
    for ep in range(epochs):
        model.train(); tr_loss = 0.0
        for xb, yb in tr_dl:
            xb = xb.to(device, non_blocking=non_blocking); yb = yb.to(device, non_blocking=non_blocking)
            opt.zero_grad(); pred = model(xb)
            loss = crit(pred, yb)
            loss.backward();
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tr_loss += loss.item()*xb.size(0)
        tr_loss /= max(1, n_tr)
        model.eval(); va_loss = 0.0
        with torch.no_grad():
            for xb, yb in va_dl:
                xb = xb.to(device, non_blocking=non_blocking); yb = yb.to(device, non_blocking=non_blocking)
                va_loss += crit(model(xb), yb).item()*xb.size(0)
        va_loss /= max(1, n_val)
        if va_loss < best - 1e-6:
            best = va_loss; bad=0
            best_state = {k:v.cpu() for k,v in model.state_dict().items()}
        else:
            bad += 1
        if bad >= patience:
            break
    model.load_state_dict({k:v.to(device) for k,v in best_state.items()})
    return model, scaler

@torch.no_grad()
def roll_forecast(model: nn.Module, seed_seq_norm: np.ndarray, horizon: int, scaler: Scaler) -> np.ndarray:
    model.eval()
    dev = next(model.parameters()).device
    seq = seed_seq_norm.copy()
    preds = []
    for _ in range(horizon):
        x = torch.tensor(seq[None, ...], dtype=torch.float32, device=dev)
        y_n = model(x).squeeze(0).detach().cpu().numpy()
        next_step = seq[-1].copy()
        next_step[0] = y_n[0]
        seq = np.vstack([seq[1:], next_step])
        preds.append(y_n[0])
    preds = np.array(preds)
    hum_pred = scaler.inverse_transform(np.column_stack([preds, np.zeros_like(preds)]))[:,0]
    return np.clip(hum_pred, 0.0, 100.0)