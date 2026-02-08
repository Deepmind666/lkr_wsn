[CmdletBinding()]
param(
    [string]$OutPath = "results\_logs\gpu_burn\gpu_engine_util.csv",
    [int]$Seconds = 180,
    [int]$Interval = 1
)

Set-Location "c:\Enhanced-EEHFR-WSN-Protocol"

$newDir = Split-Path $OutPath
if ($newDir -and -not (Test-Path $newDir)) { New-Item -ItemType Directory -Path $newDir -Force | Out-Null }

"timestamp,engine,util" | Out-File -FilePath $OutPath -Encoding ascii

$end = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $end) {
    $ts = (Get-Date).ToString("o")
    try {
        $c = Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -ErrorAction Stop
        foreach ($s in $c.CounterSamples) {
            $eng = $s.InstanceName
            $util = [math]::Round($s.CookedValue, 2)
            Add-Content -Path $OutPath -Value "$ts,$eng,$util"
        }
    } catch {
        Add-Content -Path $OutPath -Value "$ts,ERROR,0"
    }
    Start-Sleep -Seconds $Interval
}