param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$processFile = Join-Path $projectRoot 'work/local_demo_runtime/processes.json'
if (-not (Test-Path -LiteralPath $processFile)) { Write-Output 'No local demo process record found.'; return }
$record = Get-Content -LiteralPath $processFile -Raw | ConvertFrom-Json
foreach ($entry in @(@{ id = $record.frontend_pid; marker = 'server.mjs' }, @{ id = $record.backend_pid; marker = 'uvicorn' })) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($entry.id)" -ErrorAction SilentlyContinue
    if ($process -and $process.CommandLine -like "*$($entry.marker)*") {
        Stop-Process -Id $entry.id -Force
        Write-Output "Stopped local demo process $($entry.id)"
    }
}
