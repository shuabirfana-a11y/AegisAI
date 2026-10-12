param(
    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'AegisAI/ollama-runtime'),
    [string]$ModelsRoot = (Join-Path $env:LOCALAPPDATA 'AegisAI/models'),
    [string]$PythonPath
)

$script:AegisSetupRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$script:AegisOllamaVersion = 'v0.40.3'
$script:AegisArchiveHash = 'e5ecff02dfc7cae8ddf6d6b7a7ac5f727ffeedf4491f44ae75ff5b0820dbbbd5'
$script:AegisArchiveSize = 1468053171

function Expand-AegisModelArchive {
    param([string]$Archive, [string]$Destination)
    $targetRoot = [IO.Path]::GetFullPath($Destination).TrimEnd([IO.Path]::DirectorySeparatorChar)
    $prefix = $targetRoot + [IO.Path]::DirectorySeparatorChar
    $zip = [IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        foreach ($entry in $zip.Entries) {
            $target = [IO.Path]::GetFullPath((Join-Path $targetRoot $entry.FullName))
            if (-not $target.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'UNSAFE_MODEL_ARCHIVE_PATH' }
            if ((($entry.ExternalAttributes -shr 16) -band 61440) -eq 40960) { throw 'UNSAFE_MODEL_ARCHIVE_SYMLINK' }
        }
        New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
        foreach ($entry in $zip.Entries) {
            $target = [IO.Path]::GetFullPath((Join-Path $targetRoot $entry.FullName))
            if ($entry.FullName.EndsWith('/') -or $entry.FullName.EndsWith('\')) {
                New-Item -ItemType Directory -Path $target -Force | Out-Null
            } else {
                New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force | Out-Null
                [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $true)
            }
        }
    } finally { $zip.Dispose() }
}

function Invoke-AegisModelCommand {
    param([string]$Executable, [string[]]$Arguments, [int]$TimeoutSeconds = 1800, [string]$ProgressFile)
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $Executable
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $info
    try {
        if (-not $process.Start()) { throw 'LOCAL_MODEL_COMMAND_FAILED' }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $watch = [Diagnostics.Stopwatch]::StartNew()
        $lastProgress = -10
        while (-not $process.WaitForExit(500)) {
            if ($watch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
                $process.Kill($true)
                $process.WaitForExit()
                throw 'LOCAL_MODEL_COMMAND_TIMEOUT'
            }
            if ($watch.Elapsed.TotalSeconds -ge $lastProgress + 15) {
                $bytes = if ($ProgressFile -and (Test-Path -LiteralPath $ProgressFile)) { (Get-Item -LiteralPath $ProgressFile).Length } else { 0 }
                Write-Output ("Local model preparation: {0}s, downloaded bytes: {1}" -f [int]$watch.Elapsed.TotalSeconds, $bytes)
                $lastProgress = $watch.Elapsed.TotalSeconds
            }
        }
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) { throw 'LOCAL_MODEL_COMMAND_FAILED' }
    } finally {
        if ($process.Id -and -not $process.HasExited) { $process.Kill($true); $process.WaitForExit() }
        $process.Dispose()
    }
}

function Initialize-AegisLocalModel {
    param([string]$RuntimeRoot, [string]$ModelsRoot)
    $ErrorActionPreference = 'Stop'
    $runtimeRootFull = [IO.Path]::GetFullPath($RuntimeRoot)
    $modelsRootFull = [IO.Path]::GetFullPath($ModelsRoot)
    New-Item -ItemType Directory -Path $runtimeRootFull, $modelsRootFull -Force | Out-Null
    $versionRoot = Join-Path $runtimeRootFull $script:AegisOllamaVersion
    $archive = Join-Path $runtimeRootFull ($script:AegisOllamaVersion + '-windows-amd64.zip')
    $partial = $archive + '.download'
    $url = "https://github.com/ollama/ollama/releases/download/$script:AegisOllamaVersion/ollama-windows-amd64.zip"
    $receiptRoot = Join-Path $script:AegisSetupRoot 'work/phase12d'
    New-Item -ItemType Directory -Path $receiptRoot -Force | Out-Null
    $receiptPath = Join-Path $receiptRoot 'runtime-receipt.json'
    $receipt = @{
        version = $script:AegisOllamaVersion; source_url = $url; archive_sha256 = $script:AegisArchiveHash
        runtime_root = $versionRoot; models_root = $modelsRootFull; status = 'PREPARING'
        updated_at = (Get-Date).ToUniversalTime().ToString('o'); model_tag = 'qwen2.5:7b-instruct-q4_K_M'
        model_alias = 'aegisai-qwen25-planner'; host = '127.0.0.1:11434'; benchmark = $false
    }
    $receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receiptPath -Encoding utf8
    $server = $null
    $environmentNames = @('OLLAMA_HOST', 'OLLAMA_MODELS', 'OLLAMA_NO_CLOUD', 'OLLAMA_NUM_PARALLEL', 'OLLAMA_MAX_LOADED_MODELS')
    $saved = @{}
    foreach ($name in $environmentNames) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
    try {
        if (-not (Test-Path -LiteralPath $archive)) {
            $curl = (Get-Command curl.exe -ErrorAction Stop).Source
            Invoke-AegisModelCommand -Executable $curl -Arguments @('--fail', '--location', '--silent', '--show-error', '--proto', '=https', '--proto-redir', '=https', '--retry', '0', '--connect-timeout', '15', '--max-time', '1800', '--continue-at', '-', '--output', $partial, $url) -ProgressFile $partial
            if ((Get-Item -LiteralPath $partial).Length -ne $script:AegisArchiveSize -or (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant() -ne $script:AegisArchiveHash) { throw 'MODEL_ARCHIVE_HASH_MISMATCH' }
            Move-Item -LiteralPath $partial -Destination $archive
        }
        if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $script:AegisArchiveHash) { throw 'MODEL_ARCHIVE_HASH_MISMATCH' }
        if (-not (Test-Path -LiteralPath (Join-Path $versionRoot 'ollama.exe'))) { Expand-AegisModelArchive -Archive $archive -Destination $versionRoot }
        $exe = Join-Path $versionRoot 'ollama.exe'
        $env:OLLAMA_HOST = '127.0.0.1:11434'
        $env:OLLAMA_MODELS = $modelsRootFull
        $env:OLLAMA_NO_CLOUD = '1'
        $env:OLLAMA_NUM_PARALLEL = '1'
        $env:OLLAMA_MAX_LOADED_MODELS = '1'
        $existing = $null
        try { $existing = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 } catch { }
        if ($existing) { throw 'MODEL_PORT_ALREADY_OCCUPIED_NO_CHANGES' }
        $server = Start-Process -FilePath $exe -ArgumentList @('serve') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $receiptRoot 'ollama.out.log') -RedirectStandardError (Join-Path $receiptRoot 'ollama.err.log')
        $ready = $false
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            if ($server.HasExited) { throw 'MODEL_SERVER_EXITED' }
            try {
                $version = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2
                if ($version.version -eq $script:AegisOllamaVersion.TrimStart('v')) { $ready = $true; break }
            } catch { }
            Start-Sleep -Milliseconds 500
        }
        if (-not $ready) { throw 'MODEL_SERVER_NOT_READY' }
        Invoke-AegisModelCommand -Executable $exe -Arguments @('pull', $receipt.model_tag)
        Invoke-AegisModelCommand -Executable $exe -Arguments @('create', $receipt.model_alias, '-f', (Join-Path $script:AegisSetupRoot 'demo/phase12d/Modelfile')) -TimeoutSeconds 120
        $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5
        $model = @($tags.models | Where-Object { $_.name -eq ($receipt.model_alias + ':latest') })
        if ($model.Count -ne 1) { throw 'LOCAL_MODEL_NOT_REGISTERED' }
        $receipt.status = 'READY_FOR_GATEWAY_PROBE'
        $receipt.model_digest = $model[0].digest
        $receipt.server_pid = $server.Id
        $receipt.server_started_at = $server.StartTime.ToUniversalTime().ToString('o')
        $receipt.updated_at = (Get-Date).ToUniversalTime().ToString('o')
        $receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receiptPath -Encoding utf8
        Write-Output 'Local model installed. This confirms installation, not successful Planner validation.'
    } catch {
        $receipt.status = 'FAILED'
        $receipt.error_code = $_.Exception.Message
        $receipt.updated_at = (Get-Date).ToUniversalTime().ToString('o')
        $receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receiptPath -Encoding utf8
        if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force }
        throw
    } finally {
        foreach ($name in $environmentNames) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
    }
}

if ($MyInvocation.InvocationName -ne '.') { Initialize-AegisLocalModel -RuntimeRoot $RuntimeRoot -ModelsRoot $ModelsRoot }
