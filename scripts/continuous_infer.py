#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Continuous inference load generator for GPU (ONNX Runtime CUDA/DirectML) and NPU (OpenVINO).
- Supports models: lstm, tcn (from src/*_env.py)
- Exports ONNX once, then runs inference in an infinite loop
- Logs periodic throughput so Task Manager utilization becomes visible

Usage examples:
  python scripts/continuous_infer.py --engine ov_npu --model lstm --seq-len 512
  python scripts/continuous_infer.py --engine ort_dml --model tcn --seq-len 1024
  python scripts/continuous_infer.py --engine ort_cuda --model tcn --seq-len 8192
"""
import argparse, time
from pathlib import Path
import numpy as np
import torch

# project src path
import sys
sys.path.append(str(Path(__file__).parent.parent / 'src'))
from pytorch_lstm_env import LSTMRegressor  # type: ignore
from pytorch_tcn_env import TCNRegressor    # type: ignore


def make_model_and_input(kind: str, seq_len: int, batch: int = 1, in_dim: int = 2):
    x = torch.randn(batch, seq_len, in_dim, dtype=torch.float32)
    if kind == 'lstm':
        model = LSTMRegressor(in_dim=in_dim, hidden=128, num_layers=2, out_h=1, dropout=0.0)
    elif kind == 'tcn':
        model = TCNRegressor(in_dim=in_dim, channels=(64, 64, 64), kernel_size=3, dropout=0.0, out_h=1)
    else:
        raise ValueError(f'Unknown model: {kind}')
    model.eval()
    return model, x


def export_onnx(model: torch.nn.Module, x: torch.Tensor, onnx_path: Path, dynamic_axes: bool):
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {
        'export_params': True,
        'opset_version': 17,
        'do_constant_folding': True,
        'input_names': ['input'],
        'output_names': ['output'],
    }
    if dynamic_axes:
        kwargs['dynamic_axes'] = {'input': {0: 'batch', 1: 'seq'}, 'output': {0: 'batch'}}
    torch.onnx.export(model.eval(), x, str(onnx_path), **kwargs)
    return onnx_path


def run_ov_npu(kind: str, seq_len: int, log_path: Path):
    from openvino.runtime import Core
    model, x = make_model_and_input(kind, seq_len=seq_len, batch=1)
    # NPU requires static axes with batch=1
    onnx_path = Path('results') / f'{kind}_bs1_L{seq_len}_npu_static.onnx'
    export_onnx(model.to('cpu'), x.to('cpu'), onnx_path, dynamic_axes=False)
    core = Core(); ov_model = core.read_model(model=str(onnx_path))
    compiled = core.compile_model(model=ov_model, device_name='NPU')
    infer = compiled.create_infer_request()
    x_np = x.cpu().numpy()
    # warmup
    for _ in range(50):
        infer.infer({'input': x_np})
    loops = 0; t0 = time.perf_counter(); last = t0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as f:
        f.write(f'[Start] OV NPU continuous infer for {kind} L={seq_len}\n')
        while True:
            infer.infer({'input': x_np})
            loops += 1
            now = time.perf_counter()
            if now - last >= 2.0:  # log every 2s
                rate = loops / (now - t0)
                f.write(f'{time.strftime("%H:%M:%S")} loops={loops} avg_loops_per_sec={rate:.1f}\n')
                f.flush(); last = now


def run_ort_dml(kind: str, seq_len: int, log_path: Path):
    import onnxruntime as ort
    model, x = make_model_and_input(kind, seq_len=seq_len, batch=1)
    # DML supports dynamic axes fine
    onnx_path = Path('results') / f'{kind}_bs1_L{seq_len}_dml_dyn.onnx'
    export_onnx(model.to('cpu'), x.to('cpu'), onnx_path, dynamic_axes=True)
    so = ort.SessionOptions(); so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    providers = [p for p in ('DmlExecutionProvider','CPUExecutionProvider') if p in ort.get_available_providers()]
    sess = ort.InferenceSession(str(onnx_path), sess_options=so, providers=providers)
    x_np = x.cpu().numpy()
    for _ in range(50):
        sess.run(['output'], {'input': x_np})
    loops = 0; t0 = time.perf_counter(); last = t0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as f:
        f.write(f'[Start] ORT DML continuous infer for {kind} L={seq_len}, providers={providers}\n')
        while True:
            sess.run(['output'], {'input': x_np})
            loops += 1
            now = time.perf_counter()
            if now - last >= 2.0:
                rate = loops / (now - t0)
                f.write(f'{time.strftime("%H:%M:%S")} loops={loops} avg_loops_per_sec={rate:.1f}\n')
                f.flush(); last = now


def run_ort_cuda(kind: str, seq_len: int, log_path: Path):
    import onnxruntime as ort
    model, x = make_model_and_input(kind, seq_len=seq_len, batch=1)
    # CUDA supports dynamic axes
    onnx_path = Path('results') / f'{kind}_bs1_L{seq_len}_cuda_dyn.onnx'
    export_onnx(model.to('cpu'), x.to('cpu'), onnx_path, dynamic_axes=True)
    so = ort.SessionOptions(); so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    providers = [p for p in ('CUDAExecutionProvider','CPUExecutionProvider') if p in ort.get_available_providers()]
    sess = ort.InferenceSession(str(onnx_path), sess_options=so, providers=providers)
    x_np = x.cpu().numpy()
    for _ in range(50):
        sess.run(['output'], {'input': x_np})
    loops = 0; t0 = time.perf_counter(); last = t0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as f:
        f.write(f'[Start] ORT CUDA continuous infer for {kind} L={seq_len}, providers={providers}\n')
        while True:
            sess.run(['output'], {'input': x_np})
            loops += 1
            now = time.perf_counter()
            if now - last >= 2.0:
                rate = loops / (now - t0)
                f.write(f'{time.strftime("%H:%M:%S")} loops={loops} avg_loops_per_sec={rate:.1f}\n')
                f.flush(); last = now


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', type=str, required=True, choices=['ov_npu','ort_dml','ov_auto','ort_cuda'])
    ap.add_argument('--model', type=str, required=True, choices=['lstm','tcn'])
    ap.add_argument('--seq-len', type=int, default=512)
    args = ap.parse_args()

    log_root = Path('results') / '_logs' / 'continuous'
    log_file = log_root / f'{args.engine}_{args.model}_L{args.seq_len}.log'

    if args.engine == 'ov_npu':
        run_ov_npu(args.model, args.seq_len, log_file)
    elif args.engine == 'ov_auto':
        # AUTO prefers NPU but will fallback; still good for sustained load
        from openvino.runtime import Core
        model, x = make_model_and_input(args.model, seq_len=args.seq_len, batch=1)
        onnx_path = Path('results') / f'{args.model}_bs1_L{args.seq_len}_auto.onnx'
        export_onnx(model.to('cpu'), x.to('cpu'), onnx_path, dynamic_axes=True)
        core = Core(); ov_model = core.read_model(model=str(onnx_path))
        compiled = core.compile_model(model=ov_model, device_name='AUTO')
        infer = compiled.create_infer_request(); x_np = x.cpu().numpy()
        for _ in range(50): infer.infer({'input': x_np})
        loops = 0; t0 = time.perf_counter(); last = t0
        log_root.mkdir(parents=True, exist_ok=True)
        with log_file.open('a', encoding='utf-8') as f:
            f.write(f'[Start] OV AUTO continuous infer for {args.model} L={args.seq_len}\n')
            while True:
                infer.infer({'input': x_np}); loops += 1; now = time.perf_counter()
                if now - last >= 2.0:
                    rate = loops / (now - t0)
                    f.write(f'{time.strftime("%H:%M:%S")} loops={loops} avg_loops_per_sec={rate:.1f}\n')
                    f.flush(); last = now
    elif args.engine == 'ort_cuda':
        run_ort_cuda(args.model, args.seq_len, log_file)
    else:
        run_ort_dml(args.model, args.seq_len, log_file)


if __name__ == '__main__':
    main()