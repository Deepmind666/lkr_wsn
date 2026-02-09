param(
    [int]$Replicates = 60,
    [int]$Workers = 14,
    [string]$Nodes = "100,200,300,500,800,1000",
    [int]$Rounds = 300,
    [double]$MaxCpuPercent = 70.0,
    [double]$MaxMemPercent = 70.0,
    [string]$Environments = "indoor_office,indoor_factory,outdoor_urban,outdoor_suburban"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\AERIS-WSN-Protocol"
Set-Location $ProjectRoot

$NodeCounts = $Nodes.Split(",") | ForEach-Object { [int]($_.Trim()) }
$NodeCsv = $NodeCounts -join ","

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = Join-Path $ProjectRoot ("results\mega_experiments\overnight_scalability_" + $timestamp)
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$logPath = Join-Path $outDir "run.log"
$manifestPath = Join-Path $outDir "manifest.json"

$envs = @((([string]$Environments) -split ",") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" })
if ($envs.Count -eq 0) {
    throw "Environments cannot be empty."
}
$allowedEnvs = @("indoor_office", "indoor_factory", "outdoor_urban", "outdoor_suburban")
foreach ($e in $envs) {
    if ($allowedEnvs -notcontains $e) {
        throw "Invalid environment '$e'. Allowed: $($allowedEnvs -join ',')"
    }
}
$runs = @()
$startAll = Get-Date

function Write-Log([string]$msg) {
    $line = ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg)
    $line | Tee-Object -FilePath $logPath -Append
}

function Get-SystemUsage {
    $cpu = (Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples[0].CookedValue
    $mem = (Get-CimInstance Win32_OperatingSystem)
    $usedMemPercent = (1 - ($mem.FreePhysicalMemory / $mem.TotalVisibleMemorySize)) * 100
    return @{
        cpu = [double]$cpu
        mem = [double]$usedMemPercent
    }
}

function Wait-ResourceHeadroom([double]$cpuLimit, [double]$memLimit, [int]$sleepSec = 5) {
    while ($true) {
        $u = Get-SystemUsage
        if ($u.cpu -le $cpuLimit -and $u.mem -le $memLimit) {
            Write-Log ("Resource guard pass: CPU={0:n1}% MEM={1:n1}%" -f $u.cpu, $u.mem)
            break
        }
        Write-Log ("Resource guard wait: CPU={0:n1}% (limit {1:n1}%), MEM={2:n1}% (limit {3:n1}%)" -f $u.cpu, $cpuLimit, $u.mem, $memLimit)
        Start-Sleep -Seconds $sleepSec
    }
}

Write-Log "Overnight scalability job started."
Write-Log ("Replicates={0}, Workers={1}, Nodes={2}, Rounds={3}" -f $Replicates, $Workers, $NodeCsv, $Rounds)
Write-Log ("Resource limits: CPU<={0:n1}%, MEM<={1:n1}%" -f $MaxCpuPercent, $MaxMemPercent)
Write-Log ("Output dir: {0}" -f $outDir)

for ($idx = 0; $idx -lt $envs.Count; $idx++) {
    $envName = $envs[$idx]
    $start = Get-Date
    $outFile = Join-Path $outDir ("scalability_" + $envName + "_" + $timestamp + ".json")
    $envStdout = Join-Path $outDir ("stdout_" + $envName + "_" + $timestamp + ".log")
    $envStderr = Join-Path $outDir ("stderr_" + $envName + "_" + $timestamp + ".log")
    $cmd = @(
        "scripts/run_scalability_experiment.py",
        "--nodes", $NodeCsv,
        "--replicates", $Replicates.ToString(),
        "--workers", $Workers.ToString(),
        "--rounds", $Rounds.ToString(),
        "--env", $envName,
        "--max-cpu-percent", $MaxCpuPercent.ToString(),
        "--max-mem-percent", $MaxMemPercent.ToString(),
        "--run-tier", "publication",
        "--output", $outFile
    )

    Write-Log ("Running env {0}/{1}: {2}" -f ($idx + 1), $envs.Count, $envName)
    Write-Log ("Command: python {0}" -f ($cmd -join " "))
    Wait-ResourceHeadroom -cpuLimit $MaxCpuPercent -memLimit $MaxMemPercent

    $retryCount = 0
    $maxRetries = 1
    $proc = $null
    do {
        if ($retryCount -gt 0) {
            Write-Log ("Retry {0}/{1} for {2}" -f $retryCount, $maxRetries, $envName)
            Wait-ResourceHeadroom -cpuLimit $MaxCpuPercent -memLimit $MaxMemPercent
        }
        $proc = Start-Process -FilePath "python" -ArgumentList $cmd -NoNewWindow -Wait -PassThru -RedirectStandardOutput $envStdout -RedirectStandardError $envStderr
        if ($proc.ExitCode -eq 0) {
            break
        }
        $retryCount += 1
    } while ($retryCount -le $maxRetries)

    $elapsed = (Get-Date) - $start
    $ok = ($proc.ExitCode -eq 0)

    $runs += [PSCustomObject]@{
        environment = $envName
        output_file = $outFile
        stdout_log = $envStdout
        stderr_log = $envStderr
        exit_code = $proc.ExitCode
        retry_count = $retryCount
        elapsed_seconds = [int]$elapsed.TotalSeconds
    }

    if ($ok) {
        Write-Log ("Completed {0} in {1:n1} minutes." -f $envName, $elapsed.TotalMinutes)
    } else {
        Write-Log ("FAILED {0} with exit code {1}." -f $envName, $proc.ExitCode)
    }

    $done = $idx + 1
    $avgSec = ($runs | Measure-Object -Property elapsed_seconds -Average).Average
    $remaining = $envs.Count - $done
    $etaSec = [int]($avgSec * $remaining)
    Write-Log ("Progress {0}/{1}, ETA ~ {2:n1} minutes." -f $done, $envs.Count, ($etaSec / 60.0))
}

$totalElapsed = (Get-Date) - $startAll

$manifest = [PSCustomObject]@{
    started_at = $startAll.ToString("yyyy-MM-dd HH:mm:ss")
    finished_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    elapsed_seconds = [int]$totalElapsed.TotalSeconds
    replicates = $Replicates
    workers = $Workers
    nodes = $NodeCounts
    nodes_raw = $Nodes
    rounds = $Rounds
    max_cpu_percent = $MaxCpuPercent
    max_mem_percent = $MaxMemPercent
    environments = $envs
    runs = $runs
}

$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestPath -Encoding UTF8
Write-Log ("Manifest written: {0}" -f $manifestPath)
Write-Log ("Total elapsed: {0:n2} hours." -f $totalElapsed.TotalHours)
Write-Log "Overnight scalability job finished."
