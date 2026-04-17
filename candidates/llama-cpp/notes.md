# llama.cpp — Phase 3 Notes

- **Pinned version:** `b8808`
- **Install source URL:** [b8808 release](https://github.com/ggml-org/llama.cpp/releases/tag/b8808), [build docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md), [multimodal docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)
- **Host type:** Windows native (installed via winget: `ggml.llamacpp`)
- **Binary location (this dev rig):** `C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-server.exe`
- **Start command:** `llama-server`
- **Port:** `8080`
- **OpenAI-compatible endpoint:** `http://127.0.0.1:8080/v1`
- **Benchmark model:** `Gemma 4 E4B` (`Q4_K_M` equivalent)
- **Benchmark API model identifier:** `gemma-4-E4B-it-GGUF`

## Model pull / import

1. Download the pinned GGUF release from Hugging Face:

   - Repo: `unsloth/gemma-4-E4B-it-GGUF`
   - Main weights: `gemma-4-E4B-it-Q4_K_M.gguf` (~5 GB)
   - Vision projection: `mmproj-gemma-4-E4B-it-F16.gguf` (or the matching Q8 variant) — **required** for Gemma 4 multimodal on llama.cpp

2. Place both files side by side in a stable directory, e.g.:

   ```
   C:\models\gemma-4-E4B\
     gemma-4-E4B-it-Q4_K_M.gguf
     mmproj-gemma-4-E4B-it-F16.gguf
   ```

3. Export before launch (or pass as `-ModelPath` / `-MmprojPath` to `start.ps1`):

   ```powershell
   $env:LLAMA_SERVER_BIN="C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-server.exe"
   $env:LLAMA_CPP_MODEL_PATH="C:\models\gemma-4-E4B\gemma-4-E4B-it-Q4_K_M.gguf"
   $env:LLAMA_CPP_MMPROJ_PATH="C:\models\gemma-4-E4B\mmproj-gemma-4-E4B-it-F16.gguf"
   ```

## Smoke sequence

```powershell
.\candidates\llama-cpp\start.ps1
python -m benchmarks.harness --tool llama-cpp --model gemma-4-E4B-it-GGUF --base-url http://127.0.0.1:8080/v1 --scenario s1 --n-runs 1
```

## Phase 4 quantization sweep

For Phase 4, download the additional quantization variants from the same repo:

- `gemma-4-E4B-it-Q5_K_M.gguf` (~6 GB)
- `gemma-4-E4B-it-Q8_0.gguf` (~8 GB)
- (optional) `gemma-4-E4B-it-BF16.gguf` (~15 GB) — only if target mini PC RAM allows

Reuse the same `mmproj-*.gguf` vision encoder across quantizations.

## Windows service path

- **Classification:** manual
- **Recommended path:** wrap `llama-server.exe` with `nssm` or `winsw`
- **Required flag discipline:** always pass `--threads 14` and `-ngl 0`; do not rely on env vars alone

## Phase 3 capture fields

- install friction
- launch friction
- restart stability
- whether `mmproj` was required (yes for Gemma 4 multimodal)
- S1/S2/S3 pass/fail
- `tools/lib/local_llm_client.py` connectivity
