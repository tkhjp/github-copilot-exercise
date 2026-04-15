# Force CPU-only mode for candidate LLM hosts.
# Usage: dot-source this script before starting a candidate tool, e.g.
#   . .\candidates\common\cpu_only_env.ps1
#   ollama serve
#
# Target machine (mini PC) has i5-14500T: 6 P-cores + 8 E-cores = 14 cores, 20 threads.
# On the dev rig we pin all known CPU-inference thread pools to 14 to approximate
# target behavior. Note: OMP_NUM_THREADS alone is insufficient — several common
# backends (Ollama's internal heuristic, ggml's threadpool, OpenBLAS, NumPy paths,
# Intel TBB) use their own env vars.

# GPU disable (covers NVIDIA CUDA and AMD ROCm)
$env:CUDA_VISIBLE_DEVICES = ""
$env:HIP_VISIBLE_DEVICES = ""
$env:OLLAMA_NUM_GPU = "0"         # Ollama: disable GPU layers
$env:LLAMA_CUBLAS = "0"            # llama.cpp legacy build-time flag, runtime no-op but harmless
$env:GGML_CUDA_DISABLE = "1"       # ggml backend: disable CUDA at runtime

# Thread pinning for all common CPU-inference paths (target: 14 threads)
$env:OMP_NUM_THREADS = "14"        # OpenMP (MKL, BLAS, many C++ libs)
$env:MKL_NUM_THREADS = "14"        # Intel MKL
$env:OPENBLAS_NUM_THREADS = "14"   # OpenBLAS (llama.cpp Windows builds, NumPy on Windows)
$env:GGML_N_THREADS = "14"         # ggml internal threadpool (llama.cpp, whisper.cpp)
$env:VECLIB_MAXIMUM_THREADS = "14" # Apple Accelerate / some NumPy wheels
$env:NUMEXPR_NUM_THREADS = "14"    # NumExpr-backed code paths
$env:TBB_NUM_THREADS = "14"        # Intel TBB (MKL's TBB threading layer)

Write-Host "CPU-only mode enabled. Thread caps pinned to 14 across OMP/MKL/OpenBLAS/GGML/TBB/NumExpr."
Write-Host "NOTE: Ollama ignores OMP_NUM_THREADS; in per-candidate start scripts, also set"
Write-Host "      num_thread=14 in the Modelfile or pass the tool's native --threads flag."
