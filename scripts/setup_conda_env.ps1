# PowerShell script to create and activate a dedicated WSN conda env, and optionally install PyTorch (GPU)
# Usage:  ./scripts/setup_conda_env.ps1 [-EnvName aether-wsn] [-Cuda cu121]

param(
  [string]$EnvName = "aether-wsn",
  [string]$Cuda = "auto"
)

# 1) Create env
Write-Host "[1/3] Creating conda env: $EnvName"
conda env remove -n $EnvName -y 2>$null | Out-Null
conda env create -f scripts/conda_env.yml -n $EnvName

# 2) Activate
Write-Host "[2/3] Activating env: $EnvName"
conda activate $EnvName

# 3) Optional: install PyTorch based on CUDA detection
if ($Cuda -eq "auto") {
  Write-Host "Detecting CUDA..."
  $cudaVer = & nvcc --version 2>$null | Select-String -Pattern "release" | ForEach-Object { $_.ToString() }
  if ($cudaVer) {
    Write-Host "CUDA detected: $cudaVer"
    # Use PyTorch official instructions for Windows + CUDA 12.1 (most 50xx are 12.x). Adjust if needed.
    Write-Host "Installing PyTorch (CUDA 12.1)"
    pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio
  } else {
    Write-Host "CUDA not detected; installing CPU-only PyTorch"
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  }
} elseif ($Cuda -eq "cpu") {
  Write-Host "Installing CPU-only PyTorch"
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
} else {
  Write-Host "Installing PyTorch for $Cuda"
  pip install --index-url https://download.pytorch.org/whl/$Cuda torch torchvision torchaudio
}

Write-Host "Done. Activate with: conda activate $EnvName"

