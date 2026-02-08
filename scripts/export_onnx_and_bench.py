#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-click export-to-ONNX (optional) and inference benchmarking for env forecasters.
Models supported: lstm, tcn, dlinear, patchtst
- Benchmarks PyTorch inference latency/throughput on CPU/GPU
- If onnxruntime is installed, also benchmarks ORT providers (CPU/CUDA/DirectML/OpenVINO)
- If OpenVINO is installed, benchmarks OpenVINO runtime on devices (AUTO/NPU/CPU/iGPU)
- Writes JSON results to results/inference_bench.json

Usage examples (PowerShell):
  python scripts/export_onnx_and_bench.py --models lstm,tcn,dlinear,patchtst --device auto --seq-len 128 --iters 200 --batch-sizes 1,16,64,256 --export-onnx --providers auto
  python scripts/export_onnx_and_bench.py --models lstm,tcn --export-onnx --providers dml,cpu
  python scripts/export_onnx_and_bench.py --models lstm --openvino --ov-device NPU
"""
import os, sys, json, time, argparse
from pathlib import Path
import numpy as np
import torch

# project src path
sys.path.append(str(Path(__file__).parent.parent / 'src'))
from pytorch_lstm_env import LSTMRegressor  # type: ignore
from pytorch_tcn_env import TCNRegressor    # type: ignore
from pytorch_dlinear_env import DLinearEnv  # type: ignore
from pytorch_patchtst_env import PatchTSTRegressor  # type: ignore

# Try optional ONNX/ORT
try:
    import onnx  # noqa: F401
    import onnxruntime as ort
    _HAS_ORT = True
except Exception:
    _HAS_ORT = False

# Try optional OpenVINO
try:
    from openvino.runtime import Core  # type: ignore
    _HAS_OPENVINO = True
except Exception:
    _HAS_OPENVINO = False


def select_device(arg: str) -> torch.device:
    if arg == 'auto':
        return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if arg in ('cuda', 'gpu'):
        if torch.cuda.is_available():
            return torch.device('cuda')
        print('[WARN] CUDA requested but not available; using CPU.')
        return torch.device('cpu')
    return torch.device('cpu')


def make_model_and_input(kind: str, seq_len: int, batch: int, d_model: int = 256, patch_len: int = 16, stride: int = 8):
    in_dim = 2
    x = torch.randn(batch, seq_len, in_dim, dtype=torch.float32)
    if kind == 'lstm':
        model = LSTMRegressor(in_dim=in_dim, hidden=128, num_layers=2, out_h=1, dropout=0.0)
    elif kind == 'tcn':
        model = TCNRegressor(in_dim=in_dim, channels=(64, 64, 64), kernel_size=3, dropout=0.0, out_h=1)
    elif kind == 'dlinear':
        model = DLinearEnv(in_dim=in_dim, seq_len=seq_len, out_h=1)
    elif kind == 'patchtst':
        model = PatchTSTRegressor(in_dim=in_dim, seq_len=seq_len, patch_len=patch_len, stride=stride,
                                   d_model=d_model, nhead=8, num_layers=2, dim_ff=4*d_model, dropout=0.0, out_h=1)
    else:
        raise ValueError(f'Unknown model kind: {kind}')
    model.eval()
    return model, x


def time_torch_infer(model: torch.nn.Module, x: torch.Tensor, device: torch.device, iters: int = 200, warmup: int = 20):
    model = model.to(device)
    x = x.to(device)
    if device.type == 'cuda':
        torch.cuda.synchronize()
    # warmup
    with torch.inference_mode():
        for _ in range(warmup):
            _ = model(x)
        if device.type == 'cuda':
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(iters):
            _ = model(x)
        if device.type == 'cuda':
            torch.cuda.synchronize()
        t1 = time.perf_counter()
    total_s = t1 - t0
    avg_ms = total_s / iters * 1000.0
    tput = (x.shape[0] * iters) / total_s
    return dict(avg_ms=avg_ms, throughput_sps=tput)


def export_to_onnx(model: torch.nn.Module, x: torch.Tensor, onnx_path: Path, use_dynamic_axes: bool = True):
    """Export model to ONNX.
    If use_dynamic_axes is False, export with static axes (fixed batch/seq) which is required by some NPU compilers.
    """
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {
        'export_params': True,
        'opset_version': 17,
        'do_constant_folding': True,
        'input_names': ['input'],
        'output_names': ['output'],
    }
    if use_dynamic_axes:
        kwargs['dynamic_axes'] = {'input': {0: 'batch', 1: 'seq'}, 'output': {0: 'batch'}}
    torch.onnx.export(model.eval(), x, str(onnx_path), **kwargs)
    return onnx_path


def time_ort_infer(onnx_path: Path, x: torch.Tensor, preferred_providers: list[str] | None = None):
    try:
        import onnxruntime as ort  # local import to respect optionality
    except Exception:
        return {'available': False}
    try:
        avail = ort.get_available_providers()
        # Build provider list by preference
        order_map = {
            'cuda': 'CUDAExecutionProvider',
            'gpu': 'CUDAExecutionProvider',
            'cpu': 'CPUExecutionProvider',
            'dml': 'DmlExecutionProvider',
            'openvino': 'OpenVINOExecutionProvider',
            'auto': None,  # will expand to a sensible default order
        }
        providers: list[str] = []
        if preferred_providers and len(preferred_providers) > 0:
            for p in preferred_providers:
                ep = order_map.get(p.lower())
                if ep and ep in avail:
                    providers.append(ep)
        else:
            # default order: CUDA -> DML -> OpenVINO -> CPU
            for ep in ('CUDAExecutionProvider','DmlExecutionProvider','OpenVINOExecutionProvider','CPUExecutionProvider'):
                if ep in avail:
                    providers.append(ep)
    except Exception:
        providers = ['CPUExecutionProvider']
    so = ort.SessionOptions(); so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess = ort.InferenceSession(str(onnx_path), sess_options=so, providers=providers)
    x_np = x.cpu().numpy()
    # warmup
    for _ in range(10):
        _ = sess.run(['output'], {'input': x_np})
    t0 = time.perf_counter()
    iters = 200
    for _ in range(iters):
        _ = sess.run(['output'], {'input': x_np})
    t1 = time.perf_counter()
    total_s = t1 - t0
    avg_ms = total_s / iters * 1000.0
    tput = (x_np.shape[0] * iters) / total_s
    return {'available': True, 'providers': sess.get_providers(), 'avg_ms': avg_ms, 'throughput_sps': tput}


def time_openvino_infer(onnx_path: Path, x: torch.Tensor, device: str = 'AUTO'):
    """Benchmark OpenVINO runtime inference, targeting device (e.g., AUTO/NPU/CPU/GPU)."""
    if not _HAS_OPENVINO:
        return {'available': False}
    try:
        core = Core()
        model = core.read_model(model=str(onnx_path))
        compiled = core.compile_model(model=model, device_name=device)
        infer = compiled.create_infer_request()
        x_np = x.cpu().numpy()
        # warmup
        for _ in range(10):
            _ = infer.infer({'input': x_np})
        t0 = time.perf_counter(); iters = 200
        for _ in range(iters):
            _ = infer.infer({'input': x_np})
        t1 = time.perf_counter()
        total_s = t1 - t0
        avg_ms = total_s / iters * 1000.0
        tput = (x_np.shape[0] * iters) / total_s
        return {'available': True, 'device': device, 'avg_ms': avg_ms, 'throughput_sps': tput}
    except Exception as e:
        return {'available': False, 'error': str(e), 'device': device}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', type=str, default='lstm,tcn,dlinear,patchtst')
    ap.add_argument('--device', type=str, default='auto', choices=['auto','cpu','gpu','cuda'])
    ap.add_argument('--seq-len', type=int, default=128)
    ap.add_argument('--iters', type=int, default=200)
    ap.add_argument('--warmup', type=int, default=20)
    ap.add_argument('--batch-sizes', type=str, default='1,16,64,256')
    ap.add_argument('--export-onnx', action='store_true', help='Export ONNX and run ORT if available')
    ap.add_argument('--providers', type=str, default='auto', help='Preferred ORT providers in order, e.g., "dml,cpu" or "cuda,cpu"; use "auto" for default ordering')
    ap.add_argument('--openvino', action='store_true', help='Run OpenVINO benchmark if available')
    ap.add_argument('--ov-device', type=str, default='AUTO', help='OpenVINO device name: AUTO/NPU/CPU/GPU')
    ap.add_argument('--results', type=str, default=str(Path('results') / 'inference_bench.json'))
    args = ap.parse_args()

    device = select_device(args.device)
    models = [m.strip().lower() for m in args.models.split(',') if m.strip()]
    batches = [int(x) for x in args.batch_sizes.split(',') if x]
    # Parse providers preference
    providers_pref = None
    if args.providers and args.providers.strip().lower() != 'auto':
        providers_pref = [p.strip() for p in args.providers.split(',') if p.strip()]

    results = {
        'device': str(device),
        'torch_version': torch.__version__,
        'has_onnxruntime': _HAS_ORT,
        'has_openvino': _HAS_OPENVINO,
        'benches': []
    }

    for kind in models:
        for bs in batches:
            try:
                model, x = make_model_and_input(kind, seq_len=args.seq_len, batch=bs)
                r_torch = time_torch_infer(model, x, device=device, iters=args.iters, warmup=args.warmup)
                bench_item = {'model': kind, 'batch': bs, 'seq_len': args.seq_len, 'torch': r_torch}
                if args.export_onnx:
                    try:
                        onnx_path = Path('results') / f'{kind}_bs{bs}_L{args.seq_len}.onnx'
                        export_to_onnx(model.to('cpu'), x.to('cpu'), onnx_path)
                        r_ort = time_ort_infer(onnx_path, x.to('cpu'), preferred_providers=providers_pref)
                        bench_item['onnxruntime'] = r_ort
                    except Exception as e:
                        bench_item['onnxruntime'] = {'available': False, 'error': str(e)}
                if args.openvino:
                    try:
                        onnx_path = Path('results') / f'{kind}_bs{bs}_L{args.seq_len}.onnx'
                        # If targeting NPU, re-export ONNX with static axes and batch=1 to satisfy sequence length constraints
                        ov_dev = str(args.ov_device).strip().upper()
                        if ov_dev == 'NPU':
                            onnx_path = Path('results') / f'{kind}_bs1_L{args.seq_len}_npu_static.onnx'
                            x_npu = torch.randn(1, args.seq_len, x.shape[-1], dtype=torch.float32)
                            export_to_onnx(model.to('cpu'), x_npu.to('cpu'), onnx_path, use_dynamic_axes=False)
                            r_ov = time_openvino_infer(onnx_path, x_npu.to('cpu'), device=args.ov_device)
                        else:
                            # ensure ONNX exists for OV runtime (dynamic axes fine for AUTO/CPU/GPU)
                            if not onnx_path.exists():
                                export_to_onnx(model.to('cpu'), x.to('cpu'), onnx_path, use_dynamic_axes=True)
                            r_ov = time_openvino_infer(onnx_path, x.to('cpu'), device=args.ov_device)
                        bench_item['openvino'] = r_ov
                    except Exception as e:
                        bench_item['openvino'] = {'available': False, 'error': str(e), 'device': args.ov_device}
                results['benches'].append(bench_item)
                print(f"[Bench] {kind} bs={bs} -> Torch: {r_torch['avg_ms']:.3f} ms, {r_torch['throughput_sps']:.1f} samples/s")
            except Exception as e:
                results['benches'].append({'model': kind, 'batch': bs, 'error': str(e)})
                print(f"[ERROR] Benchmark {kind} bs={bs} failed: {e}")

    out_path = Path(args.results)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved bench results to: {out_path}")


if __name__ == '__main__':
    main()