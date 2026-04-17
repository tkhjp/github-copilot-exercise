# Local LLM Host Shortlist Benchmark

**Status:** Complete
**Phase:** 3
**Date:** 2026-04-17
**Executor:** Claude Opus 4.7 on dev rig (RTX 5090, CPU-only mode forced)

## Fixed benchmark protocol

- Shortlist: `Ollama`, `llama.cpp`, `LM Studio`
- Common model: `Gemma 4 E4B` (`Q4_K_M` equivalent, ~5 GB)
- Inputs:
  - S1: text-only
  - S2: `samples/diagram.png`
  - S3: `tests/text_vs_image/images/` (4 images)
- Run counts:
  - S1: 3 runs
  - S2: 3 runs
  - S3: 1 pass per image (4 total)

Dev-rig GPU was disabled host-by-host:
- Ollama: Modelfile `PARAMETER num_gpu 0` baked into `gemma4-e4b-bench` alias
- llama.cpp: `llama-server --threads 14 -ngl 0`
- LM Studio: `lms load --gpu off`

## Raw output files

| Tool | S1 CSV | S1 MD | S2 CSV | S2 MD | S3 CSV | S3 MD |
|---|---|---|---|---|---|---|
| Ollama | [csv](../../../benchmarks/out/phase3/ollama/ollama_s1_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/ollama/ollama_s1_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/ollama/ollama_s2_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/ollama/ollama_s2_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/ollama/ollama_s3_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/ollama/ollama_s3_gemma4-e4b-bench.md) |
| llama.cpp | [csv](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s1_gemma-4-E4B-it-GGUF.csv) | [md](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s1_gemma-4-E4B-it-GGUF.md) | [csv](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s2_gemma-4-E4B-it-GGUF.csv) | [md](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s2_gemma-4-E4B-it-GGUF.md) | [csv](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s3_gemma-4-E4B-it-GGUF.csv) | [md](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s3_gemma-4-E4B-it-GGUF.md) |
| LM Studio | [csv](../../../benchmarks/out/phase3/lm-studio/lm-studio_s1_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/lm-studio/lm-studio_s1_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/lm-studio/lm-studio_s2_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/lm-studio/lm-studio_s2_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/lm-studio/lm-studio_s3_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/lm-studio/lm-studio_s3_gemma4-e4b-bench.md) |

## Summary matrix

All three hosts completed all scenarios end-to-end with 100% success
rate on the retry (Ollama S3 needed `--timeout 300` after 2/4 images
exceeded the 120 s default; all other runs succeeded on first try).

| Tool | S1 status | S2 status | S3 status | S1 wall (s) | S2 wall (s) | S3 wall/image (s) | S2 tok/s | S3 tok/s | install | launch | restart | OpenAI API | local_llm_client | service path | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Ollama | ✅ 3/3 | ✅ 3/3 | ✅ 4/4 | 19.3 | 108.7 | 137.8 | 16.0 | 15.6 | easy (installer) | easy (tray service) | auto (service restarts) | native | verified via harness | manual (NSSM for reproducible CPU env) | ✅ |
| llama.cpp | ✅ 3/3 | ✅ 3/3 | ✅ 4/4 | 23.2 | 94.5 | 161.9 | 14.0 | 13.3 | easy (winget) | manual (start.ps1) | not applicable | native | verified via harness | manual (NSSM/winsw) | ✅ |
| LM Studio | ✅ 3/3 | ✅ 3/3 | ✅ 4/4 | 0.77 ¹ | 46.8 | 81.9 | 14.8 | 14.6 | easy (installer + GUI once) | easy (`lms server start`) | easy (`lms daemon up`) | native | verified via `describe_image.py LLM_BACKEND=local` | native (`lms` headless) | ✅ |

¹ LM Studio's S1 wall is not comparable with Ollama/llama.cpp.
Gemma 4 E4B on LM Studio emitted only 8 tokens (the terse translation
itself) and stopped; on Ollama/llama.cpp the model continued to produce
verbose explanations and emitted 269–348 tokens. Raw throughput was
similar (~14–16 tok/s) across all three hosts — see §"Why LM Studio
looks faster" below.

## Per-host notes

### Ollama

- **Version:** 0.20.7
- **Benchmark model:** `gemma4-e4b-bench` (Modelfile alias from `gemma4:e4b` with `PARAMETER num_gpu 0` + `PARAMETER num_thread 14`)
- **Smoke result:** S1 smoke 24.4 s / 12.2 tok/s (cold); warmed up to 16.5 s / 16.3 tok/s on 2nd call
- **Benchmark result:** All three scenarios passed. S3 required `--timeout 300` retry — 2 of 4 images exceeded the default 120 s HTTP timeout on first attempt. Median S3 wall 137.8 s/image. Longest image (`02_ui_change.png` or similar) hit 156.8 s.
- **Operational notes:**
  - The Ollama Windows service (installed by default) is already running when the dev rig boots. The Modelfile's `PARAMETER num_gpu 0` correctly forces CPU-only inference without needing to stop/restart the service with env vars.
  - `ollama pull` registry is the easiest path for Gemma 4 — `gemma4:e4b` is available as a one-liner. The default pull is the full 9.6 GB variant (BF16-ish), not Q4_K_M.
  - For a reproducible benchmark appliance, a `num_thread 14` Modelfile is mandatory — Ollama ignores `OMP_NUM_THREADS`.

### llama.cpp

- **Version:** b8808 (installed via `winget` package `ggml.llamacpp`)
- **Benchmark model:** `gemma-4-E4B-it-GGUF` (`gemma-4-E4B-it-Q4_K_M.gguf` + `mmproj-F16.gguf` from `unsloth/gemma-4-E4B-it-GGUF` on Hugging Face)
- **Smoke result:** S1 smoke 18.8 s / 13.5 tok/s
- **Benchmark result:** All three scenarios passed. S2 was fastest of the three hosts by wall time (94.5 s median). S3 was the slowest (162 s/image median).
- **Operational notes:**
  - `--threads 14 -ngl 0` and `--mmproj <path>` flags are all explicit — strong control but more setup.
  - No Windows service bundled. Need NSSM or `winsw` for unattended startup.
  - Binary discovery from winget packages path is non-obvious; had to probe `%LOCALAPPDATA%\Microsoft\WinGet\Packages\ggml.llamacpp_*`. Documented in `candidates/llama-cpp/notes.md`.
  - mmproj file is **required** for Gemma 4 vision; without it, S2/S3 would fail to interpret the image payload.

### LM Studio

- **Version:** 0.4.11 Build 1
- **Benchmark model:** `gemma4-e4b-bench` (identifier from `lms load gemma-4-e4b-it@q4_k_m --identifier gemma4-e4b-bench --gpu off --context-length 16384`)
- **Smoke result:** S1 smoke 1.23 s / 6.5 tok/s (short response — see §"Why LM Studio looks faster")
- **Benchmark result:** All three scenarios passed. S2 and S3 wall times were ~2x shorter than the other two hosts, but raw tok/s was similar. This is mostly a response-length difference.
- **Operational notes:**
  - `lms import --hard-link` allowed us to register the GGUF files already downloaded for llama.cpp without copying — LM Studio sees them as first-class Hub entries. This is the cleanest ops path of the three.
  - `lms server start` runs headlessly; GUI launch was needed only once for CLI bootstrap.
  - `--gpu off` on load is the cleanest CPU-only enforcement — no env vars, no Modelfile editing.
  - Model loads in ~4 s (fastest cold-start of the three).

## Why LM Studio looks faster

Raw token throughput (tok/s during decode) is nearly identical across
all three hosts, because all three ultimately use `llama.cpp`'s ggml
backend on the same CPU:

- S2 tok/s: Ollama 16.0 / llama.cpp 14.0 / LM Studio 14.8 (14 % spread)
- S3 tok/s: Ollama 15.6 / llama.cpp 13.3 / LM Studio 14.6 (17 % spread)

The large wall-time gap comes from **response length**, not inference speed:

| Scenario | Ollama avg completion_tokens | llama.cpp avg completion_tokens | LM Studio avg completion_tokens |
|---|---|---|---|
| S2 | ~1712 | ~1378 | ~698 |
| S3 | ~2186/img | ~2115/img | ~1210/img |

LM Studio's default sampling parameters stop the model earlier — the
resulting description is more concise. Ollama continues to generate
follow-up explanation until a long stop-sequence is hit. Neither is
"wrong"; they are different default behaviors. Phase 4 quality scoring
on `tc01..tc04` (`tests/text_vs_image/test_cases.yaml`) will tell us
whether the shorter LM Studio output still captures the ground-truth
facts.

## Winner selection

### Hard gate result

- S2 and S3 complete without manual restart: **Ollama ✅ (after 300 s timeout fix), llama.cpp ✅, LM Studio ✅**
- `tools/lib/local_llm_client.py` connectivity: **All three ✅** (LM Studio verified end-to-end with `LLM_BACKEND=local python tools/describe_image.py samples/diagram.png` producing valid Japanese Markdown; Ollama and llama.cpp verified transitively through the benchmark harness, which uses the same `openai_client.py` adapter)

### Decision

- **Winner: LM Studio**
- **Reason:**
  1. **Raw tok/s is within 20 % across all three** (13.3 – 16.0) — performance tier is effectively tied, so the selection rule in the Phase 3–7 plan defaults to the easier-to-operate host.
  2. **LM Studio has the best Windows operational story of the three:** native headless `lms server` / `lms daemon` mode, zero additional tooling for unattended start, `--gpu off` flag replaces env-var wrangling, `lms import --hard-link` shares model files with the other hosts at zero extra disk cost, and the ~4 s cold start is the fastest.
  3. **LM Studio's wall-time lead** (S2 46.8 s vs Ollama 108.7 s vs llama.cpp 94.5 s) is primarily a shorter-response artifact, not raw speed. But for the appliance use case — describing one image per user prompt, returning quickly — shorter responses with the same tok/s are still a better user experience, provided Phase 4 quality scoring confirms the short output still covers the ground-truth facts.
- **Rejected shortlist hosts:**
  - **Ollama:** strong candidate. Lost to LM Studio on: (a) Windows service integration — the Windows installer registers a service, but enforcing CPU-only requires a model-level Modelfile alias rather than a simple server flag; (b) slower S2 wall time at similar tok/s. Still a perfectly acceptable backup if LM Studio's commercial-license terms become an issue.
  - **llama.cpp:** strong on control and GGUF format compatibility, but has the slowest S3 wall time and the most manual service-hardening path (NSSM/winsw + explicit mmproj path + no auto-update). Best kept as a debugging / reference host, not as the production appliance.

## Next

Phase 4 (quantization sweep) will load Q4_K_M / Q5_K_M / Q8_0 of
Gemma 4 E4B on **LM Studio** and score output quality against
`tc01..tc04` to pick a first-choice + backup quantization. See
[03-model-selection.md](03-model-selection.md).
