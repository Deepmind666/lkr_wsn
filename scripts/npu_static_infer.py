import argparse
import time
import threading
from pathlib import Path
import json
import numpy as np
import openvino as ov


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--duration-sec", type=int, default=600)
    parser.add_argument("--streams", type=int, default=2)
    parser.add_argument("--device", default="NPU", help="Target device: NPU/AUTO/CPU/GPU")
    parser.add_argument("--log", type=str, default=str(Path("results")/"_logs"/"npu_static_infer.log"))
    args = parser.parse_args()

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    core = ov.Core()
    avail = [str(d).upper() for d in getattr(core, 'available_devices', [])]
    print("[available_devices]", avail)

    config = {
        "PERFORMANCE_HINT": "THROUGHPUT",
    }

    def _compile_with_fallback(_core, _model, devs, cfg):
        last_err = None
        for d in devs:
            try:
                cm = _core.compile_model(_model, d, cfg)
                return cm, d, None
            except Exception as e:
                last_err = e
        return None, devs[-1] if devs else "UNKNOWN", last_err

    model = core.read_model(args.onnx)

    requested = str(args.device).strip().upper()
    # Prefer requested, then AUTO, then CPU
    try_order = [requested]
    if "AUTO" not in try_order:
        try_order.append("AUTO")
    if "CPU" not in try_order:
        try_order.append("CPU")

    compiled, used_dev, err = _compile_with_fallback(core, model, try_order, config)
    if compiled is None:
        print(f"[ERROR] compile failed for devices {try_order}: {err}")
        return

    # Some plugins (e.g., NPU) do not support querying DEVICE_NAME; avoid crashing here.

    inp = compiled.input(0)
    # Handle dynamic PartialShape gracefully; prefer static lengths, fallback to 1
    raw_shape = []
    try:
        if hasattr(inp, 'get_partial_shape'):
            pshape = inp.get_partial_shape()
        else:
            # try via original model inputs
            pshape = model.inputs[0].get_partial_shape() if hasattr(model.inputs[0], 'get_partial_shape') else None
        if pshape is not None:
            for d in list(pshape):
                try:
                    # OpenVINO Dimension API
                    if hasattr(d, 'is_static') and d.is_static:
                        raw_shape.append(int(d.get_length()))
                    else:
                        raw_shape.append(1)
                except Exception:
                    raw_shape.append(1)
        else:
            raw_shape = [1, 128, 1]
    except Exception:
        raw_shape = [1, 128, 1]

    def _to_int(d):
        try:
            v = int(d)
        except Exception:
            v = 1
        return v if v > 0 else 1

    shape = [_to_int(d) for d in raw_shape]
    x = np.random.randn(*shape).astype(np.float32)

    end_time = time.perf_counter() + args.duration_sec
    counters = [0] * max(1, args.streams)

    def worker(idx):
        req = compiled.create_infer_request()
        local = 0
        while time.perf_counter() < end_time:
            try:
                req.infer({inp: x})
                local += 1
            except Exception:
                # If a single request fails (e.g., due to shape constraints), continue
                time.sleep(0.001)
        counters[idx] = local

    threads = []
    for i in range(max(1, args.streams)):
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_loops = sum(counters)
    msg = f"[done] onnx={args.onnx} device={used_dev} streams={len(threads)} loops_total={total_loops} per_stream={counters}"
    print(msg)
    try:
        with log_path.open('a', encoding='utf-8') as f:
            f.write(msg + "\n")
    except Exception:
        pass

    # Persist a lightweight bench record for paper stats aggregation
    try:
        bench_entry = {
            'task': 'npu_static_infer',
            'onnx': args.onnx,
            'device': used_dev,
            'streams': len(threads),
            'loops_total': int(total_loops),
            'per_stream': [int(v) for v in counters],
            'duration_sec': int(args.duration_sec),
        }
        out_json = Path('results') / 'inference_bench.json'
        existing = []
        if out_json.exists():
            try:
                with out_json.open('r', encoding='utf-8') as f:
                    obj = json.load(f)
                    if isinstance(obj, list):
                        existing = obj
                    elif isinstance(obj, dict) and 'benches' in obj and isinstance(obj['benches'], list):
                        existing = obj['benches']
            except Exception:
                existing = []
        existing.append(bench_entry)
        with out_json.open('w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


if __name__ == "__main__":
    main()