#!/usr/bin/env bash
set -euo pipefail
REPO="/mnt/c/Enhanced-EEHFR-WSN-Protocol"
TS="$(date +%Y%m%d-%H%M%S)"
LOGD="$REPO/results/logs/${TS}-gpu-watcher"
mkdir -p "$LOGD"
echo "[GPU-WATCH] started at $(date)" | tee -a "$LOGD/launcher.log"
# probe loop for CUDA readiness
TRIES=0
while true; do
  AVAIL=$(python3 - <<'PY'
import json
try:
    import torch
    print(json.dumps({'avail': torch.cuda.is_available(), 'cuda': getattr(getattr(torch,'version',None),'cuda',None)}))
except Exception as e:
    print(json.dumps({'avail': False, 'error': str(e)}))
PY
  )
  echo "[GPU-WATCH] probe: ${AVAIL}" | tee -a "$LOGD/launcher.log"
  echo "${AVAIL}" | grep -q '"avail": true' && break || true
  TRIES=$((TRIES+1))
  sleep 60
done
export CUDA_VISIBLE_DEVICES=0
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
cd "$REPO"
# assemble targets in preferred order, launch up to 3 concurrently
TARGETS=()
for s in scripts/run_intel_dlinear_envmap.py scripts/run_intel_tcn_envmap.py scripts/run_intel_lstm_envmap.py; do
  [ -f "$s" ] && TARGETS+=("$s")
  [ ${#TARGETS[@]} -ge 3 ] && break || true
done
if [ ${#TARGETS[@]} -eq 0 ]; then
  echo "[GPU-WATCH] ERROR: no target script found." | tee -a "$LOGD/launcher.log"
  exit 1
fi
PIDS=()
for s in "${TARGETS[@]}"; do
  bn=$(basename "$s" .py)
  echo "[GPU-WATCH] launching $bn on GPU at $(date)" | tee -a "$LOGD/launcher.log"
  nohup python3 "$s" > "$LOGD/${bn}_gpu.out" 2>&1 &
  pid=$!
  PIDS+=("$pid")
  echo "[GPU-WATCH] $bn PID=$pid log=$LOGD/${bn}_gpu.out" | tee -a "$LOGD/launcher.log"
done
# wait for all
for p in "${PIDS[@]}"; do
  wait "$p" || echo "[GPU-WATCH] WARN: PID $p exited non-zero" | tee -a "$LOGD/launcher.log"
done
echo "[GPU-WATCH] all GPU tasks finished at $(date)" | tee -a "$LOGD/launcher.log"