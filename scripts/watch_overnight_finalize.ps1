param(
    [Parameter(Mandatory=$true)]
    [string]$OvernightDir,
    [int]$PollSeconds = 120,
    [string]$PythonExe = "C:\Users\admin\anaconda3\python.exe"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\AERIS-WSN-Protocol"
Set-Location $ProjectRoot

$log = Join-Path $OvernightDir "post_finalize.log"

function Write-Log([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    $line | Tee-Object -FilePath $log -Append
}

if (!(Test-Path $OvernightDir)) {
    throw "OvernightDir not found: $OvernightDir"
}

Write-Log "Watcher started. Waiting for manifest..."
$manifest = Join-Path $OvernightDir "manifest.json"

while (!(Test-Path $manifest)) {
    Start-Sleep -Seconds $PollSeconds
}

Write-Log "Manifest detected: $manifest"

$manifestObj = Get-Content $manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$runCount = @($manifestObj.runs).Count
$failed = @($manifestObj.runs | Where-Object { $_.exit_code -ne 0 }).Count

Write-Log ("Manifest summary: runs={0}, failed={1}" -f $runCount, $failed)

Write-Log "Generating provenance sidecars..."
& $PythonExe "scripts/generate_scalability_provenance.py" --overnight-dir $OvernightDir | Tee-Object -FilePath $log -Append

$base = Split-Path $OvernightDir -Leaf
$prefix = "${base}_stats"

Write-Log ("Generating significance outputs with prefix: {0}" -f $prefix)
& $PythonExe "scripts/task_a_significance_table.py" --overnight-dir $OvernightDir --out-prefix $prefix | Tee-Object -FilePath $log -Append

$statsCsv = Join-Path "results\mega_experiments" ("{0}_table.csv" -f $prefix)
$statsMd = Join-Path "results\mega_experiments" ("{0}_summary.md" -f $prefix)

$report = @{
    overnight_dir = $OvernightDir
    finished_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    run_count = $runCount
    failed_env_count = $failed
    stats_csv = (Resolve-Path $statsCsv).Path
    stats_md = (Resolve-Path $statsMd).Path
}

$reportPath = Join-Path $OvernightDir "post_finalize_report.json"
$report | ConvertTo-Json -Depth 4 | Set-Content -Path $reportPath -Encoding UTF8
Write-Log ("Finalize report written: {0}" -f $reportPath)
Write-Log "Watcher completed."
