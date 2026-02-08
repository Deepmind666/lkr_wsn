param(
    [string]$OutPath = "results\_logs\gpu_burn\nvidia_smi_util.csv",
    [int]$Seconds = 600,
    [int]$Interval = 1
)

Set-Location "c:\Enhanced-EEHFR-WSN-Protocol"

$newDir = Split-Path $OutPath
if ($newDir -and -not (Test-Path $newDir)) { New-Item -ItemType Directory -Path $newDir -Force | Out-Null }

"timestamp,util,memory_used_mb,memory_total_mb" | Out-File -FilePath $OutPath -Encoding ascii

for ($i=0; $i -lt $Seconds; $i++) {
    $line = nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits
    Add-Content -Path $OutPath -Value $line
    Start-Sleep -Seconds $Interval
}