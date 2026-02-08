PyTorch SM_120 (RTX 5090) Compatibility Build Plan

Goal
- Enable full CUDA compute on NVIDIA RTX 5090 (SM_120) for PyTorch.
- Remove "no kernel image is available" errors and achieve stable high GPU utilization.

Constraints Observed
- Current Windows venv (.venvs/torch-cu126) has PyTorch but warns about Blackwell SM_120 incompatibility.
- .venvs/torch-cu129 shows Python 3.13 but PyTorch wheel import failed (no wheel available for this combo).
- ONNX Runtime CUDA loads allocate memory but show ~0–1% utilization; DML loads also low.

Recommended Paths
1) Nightly wheel with SM_120 support (Windows, Python 3.11/3.12)
   - Install a Python version with available nightly wheels (3.11/3.12 recommended).
   - Create venv: `python3.11 -m venv .venvs/torch-cu12x-nightly`
   - Activate and install: `pip install --pre --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu126`
   - Verify: `python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"`

2) Source build (WSL Ubuntu) with explicit SM_120 arch
   - Prereqs: CUDA Toolkit >= 12.6, cuDNN, GCC, Python 3.11.
   - Use provided scripts:
     - `wsl-scripts/launch_build.sh` (entrypoint)
     - `wsl-scripts/build_pytorch_sm12.sh` (sets `TORCH_CUDA_ARCH_LIST=12.0` and builds)
     - `wsl-scripts/monitor_build.sh` (tail logs)
   - Steps (inside WSL):
     1. `sudo apt update && sudo apt install -y build-essential python3.11-venv git cmake ninja-build`
     2. `python3.11 -m venv ~/venvs/torch-sm12 && source ~/venvs/torch-sm12/bin/activate`
     3. `pip install --upgrade pip setuptools wheel`
     4. `git clone --recursive https://github.com/pytorch/pytorch && cd pytorch`
     5. `export TORCH_CUDA_ARCH_LIST="12.0"` (Blackwell)
     6. `pip install -r requirements.txt`
     7. `python setup.py develop` (or `pip install -v .`)
   - Validation:
     - `python - <<'PY'\nimport torch; print(torch.__version__); print('CUDA?', torch.cuda.is_available()); print(torch.cuda.get_device_capability(0)); x=torch.randn((4,4096,4096), device='cuda'); y=torch.matmul(x[0], x[1]); torch.cuda.synchronize(); print('OK')\nPY`

Fallbacks
- If Windows-only, consider using ONNX Runtime DirectML for sustained load (already integrated). Increase concurrency and sequence length to boost utilization; note DML path may not saturate compute on Blackwell.
- For inference-only workloads, prefer ORT CUDA after torch build succeeds.

Operational Notes
- Keep `OMP_NUM_THREADS=2` and `MKL_NUM_THREADS=2` to reduce CPU contention.
- Monitor with `nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader`.
- Update `scripts/continuous_infer.py` engine to `ort_cuda` after CUDA wheel/build is validated.

Owner Actions
- Prepare Python 3.11 on Windows or proceed with WSL source build.
- After success, migrate experiments to use CUDA (torch + ORT) and remove DML fallback where not required.