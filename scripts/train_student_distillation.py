#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train a distilled student MLP using a trained teacher LSTM.

Loss: total = alpha * KL(student/T, teacher/T) + (1-alpha) * CE(student, y)

Inputs:
- data/cas_features.npy (N, 7)
- data/cas_labels.npy   (N,)
- models/teacher_lstm.pth

Outputs:
- models/student_fc.pth
- results/_logs/train/distillation_report.json
"""

import os
import sys
import json
import time
import argparse

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader, random_split


def build_argparser():
    ap = argparse.ArgumentParser(description="Distill student MLP from teacher LSTM")
    ap.add_argument('--data-dir', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'data'))
    ap.add_argument('--models-dir', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'models'))
    ap.add_argument('--epochs', type=int, default=50)
    ap.add_argument('--batch-size', type=int, default=256)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--hidden-size', type=int, default=64)
    ap.add_argument('--alpha', type=float, default=0.7)
    ap.add_argument('--temperature', type=float, default=3.0)
    ap.add_argument('--val-split', type=float, default=0.1)
    ap.add_argument('--test-split', type=float, default=0.1)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--min-acc', type=float, default=0.85)
    ap.add_argument('--teacher-hidden-size', type=int, default=128)
    return ap


class TeacherLSTM(nn.Module):
    def __init__(self, input_size: int = 7, hidden_size: int = 128, num_classes: int = 3):
        super().__init__()
        self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, num_layers=1, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):  # x: (B,1,F)
        out, (h, c) = self.lstm(x)
        logits = self.fc(out[:, -1, :])
        return logits


class StudentMLP(nn.Module):
    def __init__(self, input_size: int = 7, hidden_size: int = 64, num_classes: int = 3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, num_classes)
        )

    def forward(self, x):  # x: (B,1,F) or (B,F)
        if x.dim() == 3:
            x = x[:, -1, :]  # (B,F)
        return self.net(x)


def softmax_temperature(logits: torch.Tensor, T: float) -> torch.Tensor:
    return torch.softmax(logits / T, dim=1)


def distill():
    args = build_argparser().parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    try:
        cpu_threads = os.cpu_count() or 1
        torch.set_num_threads(cpu_threads)
        torch.set_num_interop_threads(max(1, cpu_threads // 2))
    except Exception:
        pass

    # Load data
    X = np.load(os.path.join(args.data_dir, 'cas_features.npy')).astype(np.float32)
    y = np.load(os.path.join(args.data_dir, 'cas_labels.npy')).astype(np.int64)
    X_seq = X.reshape((-1, 1, 7))
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

    # Load teacher
    teacher = TeacherLSTM(hidden_size=args.teacher_hidden_size).to(device)
    teacher_path = os.path.join(args.models_dir, 'teacher_lstm.pth')
    teacher.load_state_dict(torch.load(teacher_path, map_location=device))
    teacher.eval()

    # Student
    student = StudentMLP(hidden_size=args.hidden_size).to(device)
    ce = nn.CrossEntropyLoss()
    optimizer = optim.Adam(student.parameters(), lr=args.lr)

    # Distillation loop
    log = {
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'lr': args.lr,
        'hidden_size': args.hidden_size,
        'teacher_hidden_size': args.teacher_hidden_size,
        'alpha': args.alpha,
        'temperature': args.temperature,
        'seed': args.seed,
        'train': []
    }

    best_val_acc = 0.0
    best_state = None
    t0 = time.time()
    for epoch in range(1, args.epochs + 1):
        student.train()
        total_loss = 0.0
        total_correct = 0
        total_examples = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            with torch.no_grad():
                teacher_logits = teacher(xb)
                soft_targets = softmax_temperature(teacher_logits, args.temperature)
            student_logits = student(xb)
            # KL divergence between student and teacher soft targets
            log_prob = torch.log_softmax(student_logits / args.temperature, dim=1)
            kl = torch.sum(soft_targets * (torch.log(soft_targets + 1e-9) - log_prob), dim=1).mean()
            # CE on hard labels
            ce_loss = ce(student_logits, yb)
            loss = args.alpha * kl + (1 - args.alpha) * ce_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * xb.size(0)
            total_correct += int((student_logits.argmax(dim=1) == yb).sum().item())
            total_examples += int(xb.size(0))

        train_loss = total_loss / max(1, total_examples)
        train_acc = total_correct / max(1, total_examples)

        # Validation
        student.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                logits = student(xb)
                val_correct += int((logits.argmax(dim=1) == yb).sum().item())
                val_total += int(xb.size(0))
        val_acc = val_correct / max(1, val_total)
        log['train'].append({'epoch': epoch, 'train_loss': train_loss, 'train_acc': train_acc, 'val_acc': val_acc})

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in student.state_dict().items()}

    # Test evaluation
    if best_state is not None:
        student.load_state_dict(best_state)
    test_correct, test_total = 0, 0
    with torch.no_grad():
        for xb, yb in test_loader:
            xb, yb = xb.to(device), yb.to(device)
            logits = student(xb)
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
    os.makedirs(args.models_dir, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'results', '_logs', 'train'), exist_ok=True)
    model_path = os.path.join(args.models_dir, 'student_fc.pth')
    log_path = os.path.join(os.path.dirname(__file__), '..', 'results', '_logs', 'train', 'distillation_report.json')
    torch.save(student.state_dict(), model_path)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"Saved student model to: {model_path}")
    print(f"Saved distillation report to: {log_path}")
    print(f"Best val acc: {best_val_acc:.3f}, Test acc: {test_acc:.3f}")


if __name__ == '__main__':
    distill()
