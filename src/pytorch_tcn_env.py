# PyTorch-based Temporal Convolutional Network (TCN) for environment forecasting
# Predicts humidity from [humidity, temperature] sequence to drive channel mapping.
from __future__ import annotations
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from typing import Optional, Tuple

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

class SeqDataset(Dataset):
    def __init__(self, series: np.ndarray, seq_len: int = 64, pred_h: int = 1, stride: int = 1):
        assert series.ndim == 2
        self.X, self.y = [], []
        T = series.shape[0]
        for i in range(0, T - seq_len - pred_h + 1, stride):
            self.X.append(series[i:i+seq_len])
            self.y.append(series[i+seq_len:i+seq_len+pred_h, 0])  # humidity only
        self.X = torch.tensor(np.array(self.X), dtype=torch.float32)  # [N, T, F]
        self.y = torch.tensor(np.array(self.y), dtype=torch.float32)  # [N, H]
    def __len__(self):
        return self.X.shape[0]
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

class Chomp1d(nn.Module):
    def __init__(self, chomp_size: int):
        super().__init__()
        self.chomp_size = chomp_size
    def forward(self, x):
        return x[:, :, :-self.chomp_size].contiguous() if self.chomp_size > 0 else x

class TemporalBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, kernel_size: int, dilation: int, dropout: float = 0.1):
        super().__init__()
        padding = (kernel_size - 1) * dilation
        self.net = nn.Sequential(
            nn.Conv1d(in_ch, out_ch, kernel_size, padding=padding, dilation=dilation),
            Chomp1d(padding),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Conv1d(out_ch, out_ch, kernel_size, padding=padding, dilation=dilation),
            Chomp1d(padding),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.downsample = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()
        self.relu = nn.ReLU()
    def forward(self, x):
        out = self.net(x)
        res = self.downsample(x)
        return self.relu(out + res)

class TCNRegressor(nn.Module):
    def __init__(self, in_dim: int, channels=(32, 64, 64), kernel_size=3, dropout=0.1, out_h: int = 1):
        super().__init__()
        layers = []
        c_in = in_dim
        for i, c_out in enumerate(channels):
            layers.append(TemporalBlock(c_in, c_out, kernel_size, dilation=2**i, dropout=dropout))
            c_in = c_out
        self.tcn = nn.Sequential(*layers)
        self.head = nn.Sequential(nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Linear(c_in, max(8, c_in//2)), nn.ReLU(), nn.Linear(max(8, c_in//2), out_h))
    def forward(self, x):  # x: [B, T, F]
        x = x.transpose(1, 2)  # -> [B, F, T]
        out = self.tcn(x)
        return self.head(out)

@torch.no_grad()
def roll_forecast(model: nn.Module, seed_seq: np.ndarray, horizon: int, scaler: Scaler) -> np.ndarray:
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
    hum = scaler.inverse_transform(np.column_stack([preds, np.zeros_like(preds)]))[:, 0]
    return np.clip(hum, 0.0, 100.0)

def train_tcn_env(series: np.ndarray, seq_len: int = 64, pred_h: int = 1, epochs: int = 5, batch_size: int = 512, lr: float = 1e-3, val_split: float = 0.1, device: Optional[torch.device] = None, seed: int = 42, stride: int = 1) -> Tuple[nn.Module, Scaler]:
    torch.manual_seed(seed); np.random.seed(seed)
    # Force CPU for 50xx until official wheels ship kernels
    device = torch.device('cpu')
    scaler = Scaler(); scaler.fit(series); series_norm = scaler.transform(series)
    ds = SeqDataset(series_norm, seq_len=seq_len, pred_h=pred_h, stride=max(1, int(stride)))
    N = len(ds); n_val = max(1, int(N*val_split)); n_tr = N - n_val
    tr_ds, va_ds = torch.utils.data.random_split(ds, [n_tr, n_val], generator=torch.Generator().manual_seed(seed))
    tr_dl = DataLoader(tr_ds, batch_size=batch_size, shuffle=True)
    va_dl = DataLoader(va_ds, batch_size=batch_size, shuffle=False)
    try:
        model = TCNRegressor(in_dim=2, channels=(64, 64, 64), kernel_size=3, dropout=0.1, out_h=1).to(device)
    except RuntimeError as e:
        print('[WARN] CUDA not usable for this GPU build, falling back to CPU. Error:', str(e))
        device = torch.device('cpu')
        model = TCNRegressor(in_dim=2, channels=(64, 64, 64), kernel_size=3, dropout=0.1, out_h=1).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    crit = nn.MSELoss()
    best = 1e9; bad=0; patience=5
    for ep in range(epochs):
        model.train(); tr_loss=0.0
        for xb, yb in tr_dl:
            xb=xb.to(device); yb=yb.to(device)
            opt.zero_grad(); pred=model(xb); loss=crit(pred, yb); loss.backward(); opt.step()
            tr_loss += loss.item()*xb.size(0)
        tr_loss/=n_tr
        model.eval(); va_loss=0.0
        with torch.no_grad():
            for xb,yb in va_dl:
                xb=xb.to(device); yb=yb.to(device)
                va_loss += crit(model(xb), yb).item()*xb.size(0)
        va_loss/=n_val
        if va_loss < best-1e-6:
            best=va_loss; bad=0; best_state={k:v.cpu() for k,v in model.state_dict().items()}
        else:
            bad+=1
        if bad>=patience:
            break
    model.load_state_dict({k:v.to(device) for k,v in best_state.items()})
    return model, scaler

