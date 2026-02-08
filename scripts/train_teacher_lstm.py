#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train a teacher LSTM (sequence length=1) for CAS mode classification.

Inputs:
- data/cas_features.npy (N, 7): [energy, link, dist_bs, radius, density, fairness, tail_max]
- data/cas_labels.npy   (N,): class id {0:direct,1:chain,2:two_hop}

Outputs:
- models/teacher_lstm.pth
- results/_logs/train/teacher_training_log.json
"""

import os
import sys
import json
import time
import argparse
from typing import Tuple

import numpy as np

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader, random_split


def build_argparser():
    ap = argparse.ArgumentParser(description="Train teacher LSTM for CAS classification")
    ap.add_argument('--data-dir', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'data'))
    ap.add_argument('--epochs', type=int, default=50)
    ap.add_argument('--batch-size', type=int, default=256)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--hidden-size', type=int, default=128)
    ap.add_argument('--val-split', type=float, default=0.1)
    ap.add_argument('--test-split', type=float, default=0.1)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--min-acc', type=float, default=0.90, help='Target validation accuracy for success')
    return ap


class TeacherLSTM(nn.Module):
    def __init__(self, input_size: int = 7, hidden_size: int = 128, num_classes: int = 3):
        super().__init__()
        self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, num_layers=1, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        # x: (B, T=1, F)
        out, (h, c) = self.lstm(x)
        logits = self.fc(out[:, -1, :])
        return logits


def load_dataset(data_dir: str) -> Tuple[np.ndarray, np.ndarray]:
    X = np.load(os.path.join(data_dir, 'cas_features.npy'))
    y = np.load(os.path.join(data_dir, 'cas_labels.npy'))
    X = X.astype(np.float32)
    y = y.astype(np.int64)
    return X, y


def train():
    args = build_argparser().parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    try:
        cpu_threads = os.cpu_count() or 1
        torch.set_num_threads(cpu_threads)
        torch.set_num_interop_threads(max(1, cpu_threads // 2))
    except Exception:
        pass

    X, y = load_dataset(args.data_dir)
    # Ensure features length=7; reshape to (B, T=1, F)
    assert X.ndim == 2 and X.shape[1] == 7, f"Expected features shape [N,7], got {X.shape}"
    X_seq = X.reshape((-1, 1, 7))

    # Torch tensors
    X_tensor = torch.from_numpy(X_seq)
    y_tensor = torch.from_numpy(y)

    dataset = TensorDataset(X_tensor, y_tensor)
    N = len(dataset)
    n_val = int(N * args.val_split)
    n_test = int(N * args.test_split)
    n_train = N - n_val - n_test
    train_set, val_set, test_set = random_split(dataset, [n_train, n_val, n_test], generator=torch.Generator().manual_seed(args.seed))

    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=args.batch_size)
    test_loader = DataLoader(test_set, batch_size=args.batch_size)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = TeacherLSTM(hidden_size=args.hidden_size).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    best_val_acc = 0.0
    best_state = None
    log = {
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'lr': args.lr,
        'hidden_size': args.hidden_size,
        'val_split': args.val_split,
        'test_split': args.test_split,
        'seed': args.seed,
        'train': []
    }

    t0 = time.time()
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        total_correct = 0
        total_examples = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * xb.size(0)
            total_correct += int((logits.argmax(dim=1) == yb).sum().item())
            total_examples += int(xb.size(0))
        train_loss = total_loss / max(1, total_examples)
        train_acc = total_correct / max(1, total_examples)

        # Validation
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                logits = model(xb)
                val_correct += int((logits.argmax(dim=1) == yb).sum().item())
                val_total += int(xb.size(0))
        val_acc = val_correct / max(1, val_total)
        log['train'].append({'epoch': epoch, 'train_loss': train_loss, 'train_acc': train_acc, 'val_acc': val_acc})

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    # Test evaluation
    if best_state is not None:
        model.load_state_dict(best_state)
    test_correct, test_total = 0, 0
    with torch.no_grad():
        for xb, yb in test_loader:
            xb, yb = xb.to(device), yb.to(device)
            logits = model(xb)
            test_correct += int((logits.argmax(dim=1) == yb).sum().item())
            test_total += int(xb.size(0))
    test_acc = test_correct / max(1, test_total)
    elapsed = time.time() - t0

    log['summary'] = {
        'best_val_acc': best_val_acc,
        'test_acc': test_acc,
        'elapsed_sec': elapsed,
        'status': 'success' if best_val_acc >= args.min_acc else 'needs_improvement'
    }

    # Save model & logs
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'models'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'results', '_logs', 'train'), exist_ok=True)
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'teacher_lstm.pth')
    log_path = os.path.join(os.path.dirname(__file__), '..', 'results', '_logs', 'train', 'teacher_training_log.json')
    torch.save(model.state_dict(), model_path)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"Saved teacher model to: {model_path}")
    print(f"Saved training log to: {log_path}")
    print(f"Best val acc: {best_val_acc:.3f}, Test acc: {test_acc:.3f}")


if __name__ == '__main__':
    train()
