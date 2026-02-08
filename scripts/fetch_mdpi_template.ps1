$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Determine repo root (scripts folder's parent)
$repo = Split-Path $PSScriptRoot -Parent
$dest = Join-Path $repo 'docs\templates\mdpi_latex'
New-Item -ItemType Directory -Path $dest -Force | Out-Null

$urls = @(
  'https://github.com/metaphori/Template-LaTeX-MDPI/archive/refs/heads/master.zip',
  'https://github.com/ihrke/mdpi/archive/refs/heads/master.zip'
)

$zip = Join-Path $dest 'mdpi_template.zip'
$downloaded = $false
foreach ($u in $urls) {
  try {
    Write-Host "Trying: $u"
    try {
      Invoke-WebRequest -Uri $u -OutFile $zip -UseBasicParsing -MaximumRedirection 5
    } catch {
      Write-Warning "Invoke-WebRequest failed, fallback to curl.exe: $($_.Exception.Message)"
      & curl.exe -L $u -o $zip
    }
    if ((Test-Path $zip) -and ((Get-Item $zip).Length -gt 100000)) {
      $downloaded = $true
      Write-Host "Downloaded: $zip"
      break
    } else {
      Write-Warning "File too small or missing: $zip"
    }
  } catch {
    Write-Warning "Failed: $u => $($_.Exception.Message)"
  }
}
if (-not $downloaded) { throw 'All candidate URLs failed.' }

$extract = Join-Path $dest '_extract'
if (Test-Path $extract) { Remove-Item -Recurse -Force $extract }
New-Item -ItemType Directory -Path $extract -Force | Out-Null
Expand-Archive -Path $zip -DestinationPath $extract -Force

$entries = Get-ChildItem -Path $extract
if (($entries.Count -eq 1) -and $entries[0].PSIsContainer) { $top = $entries[0].FullName } else { $top = $extract }

$final = Join-Path $dest 'mdpi_template'
if (Test-Path $final) { Remove-Item -Recurse -Force $final }
Move-Item -Path $top -Destination $final
# Clean leftovers
Get-ChildItem -Path $extract -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $extract -ErrorAction SilentlyContinue

# Add our generated PDFs
$art = Join-Path $final 'for_submission_artifacts'
New-Item -ItemType Directory -Path $art -Force | Out-Null
$fsdir = Join-Path $repo 'results\for_submission'
foreach ($f in @('submission_figures.pdf','manuscript_draft.pdf')) {
  $src = Join-Path $fsdir $f
  if (Test-Path $src) { Copy-Item -Path $src -Destination $art -Force; Write-Host "Copied: $src" }
}

Write-Host "Done. Template at: $final"
Get-ChildItem -Path $final -Recurse | Select-Object -First 60 FullName, Length | Sort-Object FullName | Format-Table -AutoSize