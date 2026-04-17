param(
    [string]$ServerBin = "",
    [string]$ModelPath = "",
    [string]$MmprojPath = "",
    [string]$ModelId = "gemma-4-E4B-it-GGUF",
    [int]$Port = 8080,
    [int]$Threads = 14
)

$ErrorActionPreference = "Stop"

$common = Join-Path (Split-Path -Parent $PSScriptRoot) "common\cpu_only_env.ps1"
. $common

if (-not $ServerBin) {
    if ($env:LLAMA_SERVER_BIN) {
        $ServerBin = $env:LLAMA_SERVER_BIN
    } else {
        $cmd = Get-Command llama-server -ErrorAction SilentlyContinue
        if ($cmd) {
            $ServerBin = $cmd.Source
        } else {
            $winget = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-server.exe"
            if (Test-Path $winget) {
                $ServerBin = $winget
            }
        }
    }
}

if (-not $ModelPath -and $env:LLAMA_CPP_MODEL_PATH) {
    $ModelPath = $env:LLAMA_CPP_MODEL_PATH
}

if (-not $MmprojPath -and $env:LLAMA_CPP_MMPROJ_PATH) {
    $MmprojPath = $env:LLAMA_CPP_MMPROJ_PATH
}

if (-not $ServerBin) {
    throw "llama-server binary not found. Pass -ServerBin or set LLAMA_SERVER_BIN."
}
if (-not $ModelPath) {
    throw "Model path not set. Pass -ModelPath or set LLAMA_CPP_MODEL_PATH (expected gemma-4-E4B-it-Q4_K_M.gguf for Phase 3 baseline)."
}

$env:LLM_BASE_URL = "http://127.0.0.1:$Port/v1"
$env:LLM_MODEL = $ModelId

$args = @(
    "--model", $ModelPath,
    "--port", "$Port",
    "--host", "127.0.0.1",
    "--threads", "$Threads",
    "-ngl", "0"
)

if ($MmprojPath) {
    $args += @("--mmproj", $MmprojPath)
} else {
    Write-Warning "No mmproj path set. Gemma 4 vision will not work without it. Set LLAMA_CPP_MMPROJ_PATH or pass -MmprojPath."
}

Write-Host "Starting llama-server on http://127.0.0.1:$Port"
Write-Host "LLM_BASE_URL=$env:LLM_BASE_URL"
Write-Host "LLM_MODEL=$env:LLM_MODEL"
Write-Host "ModelPath=$ModelPath"
if ($MmprojPath) {
    Write-Host "MmprojPath=$MmprojPath"
}

& $ServerBin @args
