# Force CPU-only mode for candidate LLM hosts.
# Usage: dot-source this script before starting a candidate tool, e.g.
#   . .\candidates\common\cpu_only_env.ps1
#   ollama serve
#
# Target machine (mini PC) has i5-14500T: 6 P-cores + 8 E-cores = 14 cores, 20 threads.
# On the dev rig we pin OMP/MKL threads to 14 to approximate target behavior.

$env:CUDA_VISIBLE_DEVICES = ""
$env:HIP_VISIBLE_DEVICES = ""
$env:OLLAMA_NUM_GPU = "0"        # Ollama: disable GPU layers
$env:LLAMA_CUBLAS = "0"           # llama.cpp: disable cuBLAS
$env:GGML_CUDA_DISABLE = "1"      # ggml backend: disable CUDA
$env:OMP_NUM_THREADS = "14"
$env:MKL_NUM_THREADS = "14"
Write-Host "CPU-only mode enabled. CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=14"
