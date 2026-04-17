# Ollama — Phase 3 Notes

- **Pinned version:** `0.20.7`
- **Install source URL:** [v0.20.7 release](https://github.com/ollama/ollama/releases/tag/v0.20.7), [Windows installer](https://ollama.com/download/OllamaSetup.exe)
- **Host type:** Windows native
- **Start command:** `ollama serve`
- **Port:** `11434`
- **OpenAI-compatible endpoint:** `http://127.0.0.1:11434/v1`
- **Benchmark base model:** `gemma4:e4b`
- **Benchmark API model identifier:** `gemma4-e4b-bench`

## Model pull / import

1. Pull the pinned base model:

   ```powershell
   ollama pull gemma4:e4b
   ```

2. Create a local benchmark alias that keeps the same weights but fixes thread count to 14:

   ```text
   FROM gemma4:e4b
   PARAMETER num_thread 14
   ```

3. Create the benchmark model:

   ```powershell
   ollama create gemma4-e4b-bench -f .\Modelfile.gemma4-e4b-bench
   ```

4. Use `gemma4-e4b-bench` as the `model` value in benchmark runs.

## Smoke sequence

```powershell
ollama serve
ollama list
python -m benchmarks.harness --tool ollama --model gemma4-e4b-bench --base-url http://127.0.0.1:11434/v1 --scenario s1 --n-runs 1
```

## Windows service path

- **Classification:** manual
- **Recommended path:** use the standalone zip package plus `nssm` to wrap `ollama serve`
- **Do not rely on:** the tray app alone for reproducible benchmark/service behavior

## Phase 3 capture fields

- install friction
- launch friction
- restart stability
- S1/S2/S3 pass/fail
- `tools/lib/local_llm_client.py` connectivity
