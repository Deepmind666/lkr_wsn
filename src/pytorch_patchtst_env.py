# PatchTST-style Transformer for environment forecasting (humidity/temperature)
from __future__ import annotations
from typing import Tuple, Optional
import math
import os
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader

class SeqDataset(Dataset):
    def __init__(self, series: np.ndarray, seq_len: int = 128, pred_h: int = 1, stride: int = 1):
        assert series.ndim == 2  # [T, F]
        X, y = [], []
        T = series.shape[0]
        for i in range(0, T - seq_len - pred_h + 1, max(1, int(stride))):
            X.append(series[i:i+seq_len])
            y.append(series[i+seq_len:i+seq_len+pred_h, 0])  # predict humidity
        self.X = torch.tensor(np.array(X), dtype=torch.float32)
        self.y = torch.tensor(np.array(y), dtype=torch.float32)
    def __len__(self):
        return self.X.shape[0]
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

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

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 2000):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float32).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2, dtype=torch.float32) * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # [1, L, D]
        self.register_buffer('pe', pe)
    def forward(self, x):
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)

class PatchEmbed(nn.Module):
    def __init__(self, in_chans: int, seq_len: int, patch_len: int = 16, stride: int = 8, d_model: int = 128):
        super().__init__()
        self.in_chans = in_chans
        self.seq_len = seq_len
        self.patch_len = patch_len
        self.stride = stride
        assert patch_len <= seq_len
        self.num_patches = 1 + (seq_len - patch_len) // stride
        self.proj = nn.Linear(patch_len * in_chans, d_model)
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, F]
        B, T, F = x.shape
        patches = []
        for s in range(0, T - self.patch_len + 1, self.stride):
            seg = x[:, s:s+self.patch_len, :]  # [B, P, F]
            patches.append(seg.reshape(B, -1))
        X = torch.stack(patches, dim=1)  # [B, L, P*F]
        return self.proj(X)  # [B, L, D]

class PatchTSTRegressor(nn.Module):
    def __init__(self, in_dim: int = 2, seq_len: int = 128, patch_len: int = 16, stride: int = 8,
                 d_model: int = 256, nhead: int = 8, num_layers: int = 4, dim_ff: int = 512, dropout: float = 0.1, out_h: int = 1):
        super().__init__()
        self.embed = PatchEmbed(in_chans=in_dim, seq_len=seq_len, patch_len=patch_len, stride=stride, d_model=d_model)
        self.pos_enc = PositionalEncoding(d_model, dropout, max_len=self.embed.num_patches + 8)
        enc_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=dim_ff, dropout=dropout, batch_first=True, activation='gelu')
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=num_layers)
        self.head = nn.Sequential(nn.Linear(d_model, d_model//2), nn.GELU(), nn.Linear(d_model//2, out_h))
        self.seq_len = seq_len
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, F]
        z = self.embed(x)
        z = self.pos_enc(z)
        z = self.encoder(z)
        z_last = z[:, -1, :]
        return self.head(z_last)

@torch.no_grad()
def roll_forecast(model: nn.Module, seed_seq: np.ndarray, horizon: int, scaler: Scaler, patch_len: int = 16, stride: int = 8) -> np.ndarray:
    model.eval()
    dev = next(model.parameters()).device
    seq = seed_seq.copy()
    preds = []
    for _ in range(horizon):
        x = torch.tensor(seq[None, ...], dtype=torch.float32, device=dev)
        y_norm = model(x).squeeze(0).detach().cpu().numpy()
        next_step = seq[-1].copy()
        next_step[0] = y_norm[0]
        seq = np.vstack([seq[1:], next_step])
        preds.append(y_norm[0])
    preds = np.array(preds)
    hum_pred = scaler.inverse_transform(np.column_stack([preds, np.zeros_like(preds)]))[:, 0]
    hum_pred = np.clip(hum_pred, 0.0, 100.0)
    return hum_pred


def train_patchtst_env(series: np.ndarray, seq_len: int = 128, pred_h: int = 1, epochs: int = 150, batch_size: int = 1024, lr: float = 6e-4,
                       val_split: float = 0.1, device: Optional[torch.device] = None, seed: int = 42, stride: int = 8,
                       d_model: int = 256, nhead: int = 8, num_layers: int = 4, dim_ff: int = 512, dropout: float = 0.1, patch_len: int = 16,
                       num_workers: Optional[int] = None, pin_memory: Optional[bool] = None, persistent_workers: Optional[bool] = None,
                       prefetch_factor: Optional[int] = None, non_blocking: Optional[bool] = None) -> Tuple[nn.Module, Scaler]:
    # Resolve device/env defaults
    torch.manual_seed(seed); np.random.seed(seed)
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
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

    print(f"[PatchTST] Device: {device}; epochs={epochs}, batch={batch_size}, seq_len={seq_len}, stride={stride}; workers={num_workers}, pin_mem={pin_memory}, persist={persistent_workers}, prefetch={prefetch_factor}, non_blocking={non_blocking}")
    scaler = Scaler(); scaler.fit(series)
    series_norm = scaler.transform(series)
    ds = SeqDataset(series_norm, seq_len=seq_len, pred_h=pred_h, stride=stride)
    N = len(ds); n_val = max(1, int(N * val_split)); n_train = N - n_val
    tr_ds, va_ds = torch.utils.data.random_split(ds, [n_train, n_val], generator=torch.Generator().manual_seed(seed))
    # DataLoader high-throughput options
    dl_kwargs = dict(batch_size=batch_size, pin_memory=pin_memory)
    if num_workers and num_workers > 0:
        dl_kwargs.update(num_workers=num_workers, persistent_workers=persistent_workers, prefetch_factor=prefetch_factor)
    else:
        dl_kwargs.update(num_workers=0)
    tr_dl = DataLoader(tr_ds, shuffle=True, **dl_kwargs)
    va_dl = DataLoader(va_ds, shuffle=False, **dl_kwargs)

    model = PatchTSTRegressor(in_dim=2, seq_len=seq_len, patch_len=patch_len, stride=stride, d_model=d_model, nhead=nhead, num_layers=num_layers, dim_ff=dim_ff, dropout=dropout, out_h=1).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    crit = nn.MSELoss()
    best_va = float('inf'); patience, bad = 10, 0
    for ep in range(epochs):
        model.train(); tr_loss = 0.0
        for xb, yb in tr_dl:
            xb = xb.to(device, non_blocking=non_blocking); yb = yb.to(device, non_blocking=non_blocking)
            opt.zero_grad(); pred = model(xb)
            loss = crit(pred, yb); loss.backward();
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tr_loss += loss.item() * xb.size(0)
        tr_loss /= max(1, n_train)
        model.eval(); va_loss = 0.0
        with torch.no_grad():
            for xb, yb in va_dl:
                xb = xb.to(device, non_blocking=non_blocking); yb = yb.to(device, non_blocking=non_blocking)
                pred = model(xb)
                va_loss += crit(pred, yb).item() * xb.size(0)
        va_loss /= max(1, n_val)
        print(f"[PatchTST][epoch {ep+1}/{epochs}] train={tr_loss:.6f} val={va_loss:.6f}")
        if va_loss < best_va - 1e-6:
            best_va = va_loss; bad = 0
            best_state = {k: v.cpu() for k, v in model.state_dict().items()}
        else:
            bad += 1
        if bad >= patience:
            break
    model.load_state_dict({k: v.to(device) for k, v in best_state.items()})
    return model, scaler