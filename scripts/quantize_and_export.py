#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quantize trained student MLP to fixed-point (Q10) and export weights.

Inputs:
- models/student_fc.pth

Outputs:
- data/distilled_cas_weights.npz  # int32 arrays representing Q10 quantized weights and biases

Notes:
- Matches DistilledCASSelector default fixed-point scaling (Q10 -> shift=10).
- StudentMLP architecture: Linear(7->H), ReLU, Linear(H->3). We export as W1,b1,W2,b2.
"""

import os
import sys
import argparse
import numpy as np
import torch
import torch.nn as nn


class StudentMLP(nn.Module):
    def __init__(self, input_size: int = 7, hidden_size: int = 64, num_classes: int = 3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, num_classes)
        )

    def forward(self, x):
        return self.net(x)


def build_argparser():
    ap = argparse.ArgumentParser(description="Quantize student MLP and export fixed-point weights")
    ap.add_argument('--models-dir', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'models'))
    ap.add_argument('--output-dir', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'data'))
    ap.add_argument('--hidden-size', type=int, default=64)
    ap.add_argument('--q', type=int, default=10, help='Fixed-point fractional bits (Q10)')
    return ap


def quantize_and_export():
    args = build_argparser().parse_args()

    # Load student
    model = StudentMLP(hidden_size=args.hidden_size)
    ckpt_path = os.path.join(args.models_dir, 'student_fc.pth')
    state = torch.load(ckpt_path, map_location='cpu')
    model.load_state_dict(state)
    model.eval()

    # Extract weights
    fc1 = model.net[0]
    fc2 = model.net[2]
    W1 = fc1.weight.detach().cpu().numpy()  # (H, 7)
    b1 = fc1.bias.detach().cpu().numpy()    # (H,)
    W2 = fc2.weight.detach().cpu().numpy()  # (3, H)
    b2 = fc2.bias.detach().cpu().numpy()    # (3,)

    # Quantize to Q10 (scale = 2^q)
    scale = 1 << args.q
    W1_q = np.round(W1 * scale).astype(np.int32)
    b1_q = np.round(b1 * scale).astype(np.int32)
    W2_q = np.round(W2 * scale).astype(np.int32)
    b2_q = np.round(b2 * scale).astype(np.int32)

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, 'distilled_cas_weights.npz')
    np.savez(out_path, W1=W1_q, b1=b1_q, W2=W2_q, b2=b2_q, q=args.q)
    print(f"Saved quantized weights to: {out_path}")


if __name__ == '__main__':
    quantize_and_export()
