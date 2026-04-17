param(
    [string]$ModelKey = "",
    [string]$ModelId = "gemma4-e4b-bench",
    [int]$Port = 1234,
    [int]$ContextLength = 16384,
    [switch]$UseDaemon
)

$ErrorActionPreference = "Stop"

$common = Join-Path (Split-Path -Parent $PSScriptRoot) "common\cpu_only_env.ps1"
. $common

$lms = Get-Command lms -ErrorAction SilentlyContinue
if (-not $lms) {
    throw "lms command not found. Install LM Studio, run it once, and bootstrap the CLI (see notes.md)."
}

$env:LLM_BASE_URL = "http://127.0.0.1:$Port/v1"
$env:LLM_MODEL = $ModelId

if ($UseDaemon) {
    Write-Host "Starting lms daemon"
    & $lms.Source daemon up
}

Write-Host "LM Studio thread count must be set to 14 in Server / Inference settings before benchmarking."
Write-Host "Starting LM Studio server on http://127.0.0.1:$Port"
Start-Process -FilePath $lms.Source -ArgumentList @("server", "start", "--port", "$Port")

Start-Sleep -Seconds 3

if ($ModelKey) {
    Write-Host "Loading model: $ModelKey"
    & $lms.Source load $ModelKey --identifier $ModelId --gpu off --context-length $ContextLength
} else {
    Write-Host "ModelKey not provided. Load the model manually with:"
    Write-Host "lms load <model_key> --identifier $ModelId --gpu off --context-length $ContextLength"
}

Write-Host "LLM_BASE_URL=$env:LLM_BASE_URL"
Write-Host "LLM_MODEL=$env:LLM_MODEL"
