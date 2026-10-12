param(
    [ValidateSet('MOCK', 'REAL')][string]$Mode = 'MOCK',
    [string]$PythonPath
)

$script:AegisModelProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path

function Start-AegisModelDemo {
    param(
        [ValidateSet('MOCK', 'REAL')][string]$Mode = 'MOCK',
        [string]$PythonPath,
        [string]$StarterPath = (Join-Path $script:AegisModelProjectRoot 'scripts/start-local-demo.ps1')
    )
    $ErrorActionPreference = 'Stop'
    if (-not $PythonPath) { $PythonPath = Join-Path $script:AegisModelProjectRoot 'backend/.venv/Scripts/python.exe' }
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw 'MODEL_PYTHON_MISSING' }
    $PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
    $profileName = if ($Mode -eq 'REAL') { 'local-real-profile.json' } else { 'mock-profile.json' }
    $settings = Get-Content -LiteralPath (Join-Path $script:AegisModelProjectRoot "demo/phase12d/$profileName") -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable
    $names = @(
        'MODEL_PROVIDER', 'MODEL_NAME', 'MODEL_API_BASE', 'MODEL_API_KEY',
        'MODEL_ALLOW_KEYLESS_LOCAL', 'MODEL_TIMEOUT_SECONDS', 'MODEL_MAX_OUTPUT_TOKENS',
        'MODEL_STRUCTURED_MODE', 'MODEL_TOKEN_PARAMETER', 'MODEL_EMBEDDING_PROVIDER',
        'MODEL_EMBEDDING_NAME', 'MODEL_EMBEDDING_DIMENSION'
    )
    foreach ($name in $settings.Keys) {
        if ($name -notin $names -or $settings[$name] -isnot [string]) { throw 'INVALID_LOCAL_MODEL_PROFILE' }
    }
    $original = @{}
    foreach ($name in $names) { $original[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
    try {
        foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $null, 'Process') }
        foreach ($name in $settings.Keys) { [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process') }
        Push-Location -LiteralPath (Join-Path $script:AegisModelProjectRoot 'backend')
        try {
            & $PythonPath -c 'from app.llm.config import ModelConfig; ModelConfig.from_env(); print("Model profile validated.")'
            if ($LASTEXITCODE -ne 0) { throw 'INVALID_LOCAL_MODEL_PROFILE' }
        } finally { Pop-Location }
        & $StarterPath -PythonPath $PythonPath
    } finally {
        foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $original[$name], 'Process') }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    Start-AegisModelDemo -Mode $Mode -PythonPath $PythonPath
}
