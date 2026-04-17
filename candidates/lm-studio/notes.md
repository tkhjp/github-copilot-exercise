# LM Studio — Phase 3 Notes

- **Pinned version:** `0.4.11 Build 1`
- **Install source URL:** [Downloads](https://lmstudio.ai/download), [headless docs](https://lmstudio.ai/docs/developer/core/headless), [server docs](https://lmstudio.ai/docs/cli/serve/server-start), [load docs](https://lmstudio.ai/docs/cli/local-models/load)
- **Host type:** Windows native
- **Install location (this dev rig):** `C:\Users\user\AppData\Local\Programs\LM Studio\LM Studio.exe`
- **Start command:** `lms server start --port 1234`
- **Port:** `1234`
- **OpenAI-compatible endpoint:** `http://127.0.0.1:1234/v1`
- **Benchmark model family:** `Gemma 4 E4B`
- **Benchmark API model identifier:** `gemma4-e4b-bench`

## CLI bootstrap

If `lms` is not yet on PATH:

1. Start the LM Studio GUI once so it self-registers.
2. Run the CLI bootstrap (path under the install dir):

   ```powershell
   & "$env:LOCALAPPDATA\LM Studio\resources\app\.webpack\main\bin\lms.exe" bootstrap
   ```

   This adds `lms` to PATH. Verify with `lms --version`.

## Model pull / import

1. Download Gemma 4 E4B from the in-app Hub:
   - Search "Gemma 4 E4B" in the LM Studio Hub tab.
   - Pick the Q4_K_M GGUF build (~5 GB).
   - Ensure the matching `mmproj-*.gguf` is downloaded together so vision works.

2. Alternatively, side-load the same GGUF + mmproj used by llama.cpp:

   ```powershell
   lms import C:\models\gemma-4-E4B\gemma-4-E4B-it-Q4_K_M.gguf --mmproj C:\models\gemma-4-E4B\mmproj-gemma-4-E4B-it-F16.gguf
   ```

3. Load it with a stable identifier and GPU offload disabled:

   ```powershell
   lms load <model_key> --identifier gemma4-e4b-bench --gpu off --context-length 16384
   ```

4. Use `gemma4-e4b-bench` as the `model` value in benchmark runs.

## Operational notes

- Set LM Studio CPU thread count to `14` in **Server → Inference settings** before benchmarking.
- Prefer `lms` headless mode over the GUI for repeatable server behavior.
- If the server is already running on a different port, stop it first or override `-Port` in `start.ps1`.
- Set `Serve on Local Network = OFF` during benchmarking (keep bind at `localhost`).

## Smoke sequence

```powershell
.\candidates\lm-studio\start.ps1 -ModelKey <your-local-model-key>
python -m benchmarks.harness --tool lm-studio --model gemma4-e4b-bench --base-url http://127.0.0.1:1234/v1 --scenario s1 --n-runs 1
```

## Windows service path

- **Classification:** native (best of the 3 shortlist hosts)
- **Recommended path:** `lms` headless mode
- **Caveat:** OS-level startup registration still needs Windows-side setup (for example startup task or service wrapper), but the host product itself supports headless service operation

## Phase 3 capture fields

- install friction
- launch friction
- restart stability
- whether GUI was required
- S1/S2/S3 pass/fail
- `tools/lib/local_llm_client.py` connectivity
