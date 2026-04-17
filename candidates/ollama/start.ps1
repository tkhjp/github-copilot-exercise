param(
    [string]$BaseModel = "gemma4:e4b",
    [string]$BenchmarkModel = "gemma4-e4b-bench",
    [int]$Port = 11434,
    [switch]$PrepareBenchmarkModel
)

$ErrorActionPreference = "Stop"

$common = Join-Path (Split-Path -Parent $PSScriptRoot) "common\cpu_only_env.ps1"
. $common

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "ollama command not found. Install Ollama first."
}

$env:OLLAMA_HOST = "127.0.0.1:$Port"
$env:LLM_BASE_URL = "http://127.0.0.1:$Port/v1"
$env:LLM_MODEL = $BenchmarkModel

if ($PrepareBenchmarkModel) {
    $tmpModelfile = Join-Path $env:TEMP "Modelfile.gemma4-e4b-bench"
    @"
FROM $BaseModel
PARAMETER num_thread 14
"@ | Set-Content -Path $tmpModelfile -Encoding ASCII

    Write-Host "Pulling base model: $BaseModel"
    ollama pull $BaseModel

    Write-Host "Creating benchmark alias: $BenchmarkModel"
    ollama create $BenchmarkModel -f $tmpModelfile
}

Write-Host "Starting Ollama on http://127.0.0.1:$Port"
Write-Host "LLM_BASE_URL=$env:LLM_BASE_URL"
Write-Host "LLM_MODEL=$env:LLM_MODEL"

ollama serve
