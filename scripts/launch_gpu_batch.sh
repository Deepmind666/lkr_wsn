#!/bin/bash
set -euo pipefail

LOG_DIR="${1:-/mnt/c/Enhanced-EEHFR-WSN-Protocol/results/logs/$(date +%Y%m%d-%H%M%S)-gpu-batch}"
mkdir -p "$LOG_DIR"
echo "[WSL] log dir: $LOG_DIR"

# Try to activate venv (created by wsl-scripts/setup_torch_nightly.sh)
VENV_ACT="${HOME}/.venvs/torch-nightly/bin/activate"
if [ -f "$VENV_ACT" ]; then
  echo "[WSL] activating venv: $VENV_ACT"
  # shellcheck disable=SC1090
  source "$VENV_ACT"
else
  echo "[WSL] venv not found, using system python"
fi

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L || true
else
  echo "[WSL] nvidia-smi not found"
fi

python3 - <<'PY'
import sys
try:
    import torch
    print("[WSL] torch version:", getattr(torch, "__version__", "unknown"))
    ok = torch.cuda.is_available()
    print("[WSL] cuda is available:", ok)
    if ok:
        print("[WSL] device_count:", torch.cuda.device_count())
    sys.exit(0 if ok else 1)
except Exception as e:
    print("[WSL] torch import failed:", e)
    sys.exit(2)
PY

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
# Threading caps to avoid CPU oversubscription when GPU is the bottleneck
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-2}"
# Favor TF32 on Ampere+/Blackwell
export NVIDIA_TF32_OVERRIDE=1
# High-throughput DataLoader defaults (can be overridden by caller)
export DL_NUM_WORKERS="${DL_NUM_WORKERS:-8}"
export DL_PIN_MEMORY="${DL_PIN_MEMORY:-1}"
export DL_PERSISTENT_WORKERS="${DL_PERSISTENT_WORKERS:-1}"
export DL_PREFETCH_FACTOR="${DL_PREFETCH_FACTOR:-4}"
export DL_NON_BLOCKING="${DL_NON_BLOCKING:-1}"
# PyTorch allocator tweak (optional)
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-max_split_size_mb:256,garbage_collection_threshold:0.9}"

# Launch tasks with nohup and record pids (python3 points to venv if activated)
nohup env DLINEAR_BATCH="${DLINEAR_BATCH:-32768}" DLINEAR_EPOCHS="${DLINEAR_EPOCHS:-400}" \
  python3 -u /mnt/c/Enhanced-EEHFR-WSN-Protocol/scripts/run_intel_dlinear_envmap.py >"$LOG_DIR/dlinear.log" 2>&1 & echo $! >"$LOG_DIR/dlinear.pid"
nohup env TCN_BATCH="${TCN_BATCH:-8192}" TCN_EPOCHS="${TCN_EPOCHS:-300}" \
  python3 -u /mnt/c/Enhanced-EEHFR-WSN-Protocol/scripts/run_intel_tcn_envmap.py     >"$LOG_DIR/tcn.log"     2>&1 & echo $! >"$LOG_DIR/tcn.pid"
nohup env LSTM_BATCH="${LSTM_BATCH:-8192}" LSTM_EPOCHS="${LSTM_EPOCHS:-200}" LSTM_SEQ_LEN="${LSTM_SEQ_LEN:-64}" \
  python3 -u /mnt/c/Enhanced-EEHFR-WSN-Protocol/scripts/run_intel_lstm_envmap.py    >"$LOG_DIR/lstm.log"    2>&1 & echo $! >"$LOG_DIR/lstm.pid"

printf '[WSL] started PIDs: DLinear=%s TCN=%s LSTM=%s\n' "$(cat "$LOG_DIR/dlinear.pid")" "$(cat "$LOG_DIR/tcn.pid")" "$(cat "$LOG_DIR/lstm.pid")"

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader || true
fi

echo "$LOG_DIR"