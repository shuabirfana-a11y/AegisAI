param([string]$PythonPath)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$python = if ($PythonPath) { $PythonPath } else { Join-Path $projectRoot 'backend/.venv/Scripts/python.exe' }
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $node) { $node = 'C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' }
if (-not (Test-Path -LiteralPath $python)) { throw 'The backend Python environment is missing.' }
if (-not (Test-Path -LiteralPath $node)) { throw 'Node.js is missing.' }

function Test-LocalPort([int]$port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        if (-not $connection.AsyncWaitHandle.WaitOne(300)) { return $false }
        $client.EndConnect($connection)
        return $true
    } catch { return $false } finally { $client.Close() }
}

if ((Test-LocalPort 8000) -or (Test-LocalPort 8769)) {
    throw 'Port 8000 or 8769 is already in use. Stop the existing service before starting the local demo.'
}

Set-Location -LiteralPath $projectRoot
& $python backend/scripts/local_database.py start
if ($LASTEXITCODE -ne 0) { throw 'The local database did not start.' }

$env:AEGIS_DATABASE_URL = 'postgresql+psycopg://aegis_local@127.0.0.1:55436/aegis_phase6'
& $python -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }

$runtimeRoot = Join-Path $projectRoot 'work/local_demo_runtime'
New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
$backend = $null
$frontend = $null
try {
    $env:AEGIS_ASSET_TOKEN = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant()
    $env:AEGIS_LOCAL_DEMO = '1'
    $backend = Start-Process -FilePath $python -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'backend.out.log') -RedirectStandardError (Join-Path $runtimeRoot 'backend.err.log')
    $frontend = Start-Process -FilePath $node -ArgumentList @('server.mjs') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'frontend.out.log') -RedirectStandardError (Join-Path $runtimeRoot 'frontend.err.log')
} catch {
    foreach ($process in @($frontend, $backend)) {
        if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
    throw
} finally {
    Remove-Item Env:AEGIS_ASSET_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:AEGIS_LOCAL_DEMO -ErrorAction SilentlyContinue
}

$ready = $false
for ($attempt = 0; $attempt -lt 40; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 2
        $config = Invoke-RestMethod -Uri 'http://127.0.0.1:8769/client-config' -TimeoutSec 2
        if ($health -and $config.localDemoAccess -eq $true) { $ready = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 500
}

if (-not $ready) {
    foreach ($process in @($frontend, $backend)) {
        if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
    throw "Local demo did not become ready. Check logs in $runtimeRoot"
}

@{
    backend_pid = $backend.Id
    frontend_pid = $frontend.Id
    started_at = (Get-Date).ToString('o')
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeRoot 'processes.json') -Encoding utf8

Write-Output 'AegisAI local HTTP services are ready: http://127.0.0.1:8769/dashboard'
Write-Output 'Health checks confirm service reachability, not successful investigation planning.'
if (-not $env:MODEL_PROVIDER -or $env:MODEL_PROVIDER -eq 'mock') {
    Write-Warning 'Default Mock has no PlannerPlan fixture. New investigations stop with PLANNING_FAILED; use the controlled offline chain test or configure a planning-capable provider. See docs/BACKEND_DEMO_STABILITY.md.'
}
Write-Output 'The asset, assistant and investigation access token stays in the local service processes.'
