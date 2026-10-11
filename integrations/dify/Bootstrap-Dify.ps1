[CmdletBinding()]
param(
    [string]$RuntimeDirectory = (Join-Path $PSScriptRoot 'runtime'),
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$difyVersion = '1.17.1'
$difyCommit = '8387590ace4a094de812b7847fc6a4c3a27cd52b'
$runtimeRoot = [IO.Path]::GetFullPath($RuntimeDirectory)
$sourceRoot = Join-Path $runtimeRoot 'source'
$dockerRoot = Join-Path $sourceRoot 'docker'
$statusPath = Join-Path $runtimeRoot 'runtime-status.local.json'
$failureStatus = 'FAILED'
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
function Write-Status([string]$Status, [string[]]$Reasons) {
    [ordered]@{ version=$difyVersion; commit=$difyCommit; status=$Status;
        reasons=$Reasons; recorded_at=(Get-Date).ToUniversalTime().ToString('o') } |
        ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
}
function Assert-Exit([string]$Action) {
    if ($LASTEXITCODE -ne 0) { throw "$Action failed with exit code $LASTEXITCODE" }
}
function New-LocalSecret {
    $secretBytes = New-Object byte[] 32
    $secretRng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $secretRng.GetBytes($secretBytes) } finally { $secretRng.Dispose() }
    return [Convert]::ToBase64String($secretBytes).Replace('+','-').Replace('/','_').TrimEnd('=')
}
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        $failureStatus = 'BLOCKED'
        throw 'Docker is not installed. Runtime status saved; WSL/Docker prerequisites require host setup.'
    }
    $composeVersionText = & docker compose version --short
    Assert-Exit 'Docker Compose version probe'
    $composeVersion = [version]((($composeVersionText.Trim() -replace '^v','') -split '-')[0])
    if ($composeVersion -lt [version]'2.24.4') { throw 'Docker Compose 2.24.4 or later is required.' }
    $dockerOs = & docker info --format '{{.OSType}}' 2>$null
    Assert-Exit 'Docker daemon probe'
    if ($dockerOs.Trim() -ne 'linux') { throw 'A running Linux container engine is required.' }
    if (-not (Test-Path -LiteralPath $sourceRoot)) {
        & git clone --depth 1 --branch $difyVersion https://github.com/langgenius/dify.git $sourceRoot
        Assert-Exit 'Pinned Dify clone'
    }
    $actualCommit = & git -C $sourceRoot rev-parse HEAD
    Assert-Exit 'Dify commit verification'
    if ($actualCommit.Trim() -ne $difyCommit) { throw 'Existing runtime source differs from the pinned Dify commit.' }
    $gatewayDirectory = Join-Path $dockerRoot 'aegis-gateway'
    New-Item -ItemType Directory -Force -Path $gatewayDirectory | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'gateway/default.conf') -Destination (Join-Path $gatewayDirectory 'default.conf')
    $runtimeOverride = Join-Path $dockerRoot 'compose.aegis.yaml'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'compose.aegis.yaml') -Destination $runtimeOverride
    $envPath = Join-Path $dockerRoot '.env'
    if (-not (Test-Path -LiteralPath $envPath)) {
        $envText = Get-Content -LiteralPath (Join-Path $dockerRoot '.env.example') -Raw
        $envValues = [ordered]@{
            COMPOSE_PROFILES='postgresql,pgvector'; VECTOR_STORE='pgvector';
            ENABLE_COLLABORATION_MODE='false'; NEXT_TELEMETRY_DISABLED='1';
            CONSOLE_API_URL='http://127.0.0.1:8088'; CONSOLE_WEB_URL='http://127.0.0.1:8088';
            SERVICE_API_URL='http://127.0.0.1:8088'; APP_API_URL='http://127.0.0.1:8088';
            APP_WEB_URL='http://127.0.0.1:8088'; TRIGGER_URL='http://127.0.0.1:8088';
            FILES_URL='http://127.0.0.1:8088'; NEXT_PUBLIC_SOCKET_URL='ws://127.0.0.1:8088';
            EXPOSE_NGINX_PORT='8088'; EXPOSE_NGINX_SSL_PORT='8443';
            SANDBOX_ENABLE_NETWORK='false'; SSRF_PROXY_ALLOW_PRIVATE_IPS='';
            SSRF_PROXY_ALLOW_PRIVATE_DOMAINS='aegis_gateway';
            SECRET_KEY=(New-LocalSecret); DB_PASSWORD=(New-LocalSecret);
            PGVECTOR_POSTGRES_PASSWORD=(New-LocalSecret); REDIS_PASSWORD=(New-LocalSecret);
            PGVECTOR_HOST='pgvector'; PGVECTOR_PORT='5432'; PGVECTOR_USER='postgres'; PGVECTOR_DATABASE='dify';
            SANDBOX_API_KEY=(New-LocalSecret); PLUGIN_DAEMON_KEY=(New-LocalSecret);
            PLUGIN_DIFY_INNER_API_KEY=(New-LocalSecret); DIFY_AGENT_API_TOKEN=(New-LocalSecret);
            DIFY_AGENT_SERVER_SECRET_KEY=(New-LocalSecret); DIFY_AGENT_LOCAL_SANDBOX_AUTH_TOKEN=(New-LocalSecret)
        }
        # Keep the API vector-store credential and Celery broker credential in sync.
        $envValues.PGVECTOR_PASSWORD = $envValues.PGVECTOR_POSTGRES_PASSWORD
        $envValues.CELERY_BROKER_URL = 'redis://:' + $envValues.REDIS_PASSWORD + '@redis:6379/1'
        foreach ($envName in $envValues.Keys) {
            $envPattern = '(?m)^' + [regex]::Escape($envName) + '=.*$'
            $envLine = $envName + '=' + $envValues[$envName]
            if ([regex]::IsMatch($envText,$envPattern)) { $envText = [regex]::Replace($envText,$envPattern,[System.Text.RegularExpressions.MatchEvaluator]{ param($match) $envLine }) }
            else { $envText += "`n$envLine" }
        }
        [IO.File]::WriteAllText($envPath,$envText,[Text.UTF8Encoding]::new($false))
    }
    $composeArgs = @('--project-name','aegis-dify','--project-directory',$dockerRoot,'--env-file',$envPath,'-f',(Join-Path $dockerRoot 'docker-compose.yaml'),'-f',$runtimeOverride)
    & docker compose @composeArgs config --quiet
    Assert-Exit 'Compose validation'
    if ($PrepareOnly) { Write-Status 'PREPARED_NOT_STARTED' @('Configuration validated.'); return }
    & docker compose @composeArgs up -d
    Assert-Exit 'Dify startup'
    & docker compose @composeArgs ps
    Write-Status 'STARTED_UNVERIFIED' @('Containers started. Console/import/backend reachability/workflow smoke are separate acceptance gates.')
    Write-Output 'Dify containers requested. Open http://127.0.0.1:8088/install, import the DSL, set the secret, then run smoke.py.'
} catch {
    Write-Status $failureStatus @($_.Exception.Message)
    throw
}
