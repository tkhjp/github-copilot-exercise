# Candidate LLM Hosts

Each candidate tool is launched on the dev rig (RTX 5090) in **CPU-only mode**
to approximate target mini PC behavior.

## Common setup

Before starting any candidate, dot-source the CPU-only env helper:

    . .\candidates\common\cpu_only_env.ps1

This sets `CUDA_VISIBLE_DEVICES=""` / `OLLAMA_NUM_GPU=0` to disable GPU, and
pins thread counts to 14 across OMP, MKL, OpenBLAS, GGML, TBB, and NumExpr
(matching the mini PC's 6 P + 8 E cores).

Verify the dot-source took effect:

    echo $env:OMP_NUM_THREADS       # should print 14
    echo $env:GGML_N_THREADS        # should print 14

Verify GPU is disabled by running a model and checking `nvidia-smi` during
inference — the candidate process must stay at 0% GPU-Util with 0 MiB GPU
memory. (On Windows a process that merely *imports* CUDA may briefly appear
in the process list before backing off to CPU; that is acceptable so long as
utilization stays at 0%.)

### Per-candidate thread pinning (important)

`cpu_only_env.ps1` covers env-var-driven thread caps, but some backends do
not read those vars and need explicit flags in their own launch script:

- **Ollama** ignores `OMP_NUM_THREADS` and decides thread count from its own
  heuristic. Each Modelfile used with Ollama during benchmarking MUST set
  `PARAMETER num_thread 14`, or pass `num_thread: 14` in the `/api/generate`
  request options.
- **llama.cpp** (server / CLI) should pass `--threads 14` explicitly.
- **LM Studio** exposes thread count in its server settings UI; set to 14
  before starting the local server.

Each candidate's `start.ps1` (created in Phase 3) is responsible for
enforcing the above. The dev-rig-to-target benchmark comparison is only
valid if every candidate is actually capped at 14 threads.

## Tools

The shortlist directories now live under `candidates/`:

- `ollama/` — Ollama on Windows native
- `llama-cpp/` — llama.cpp (`llama-server`) on Windows native
- `lm-studio/` — LM Studio / `lms` / `llmster`

Each candidate directory contains:

- `notes.md` — pinned version, install source URL, model/import notes, service path
- `start.ps1` — CPU-only startup wrapper that sets `LLM_BASE_URL` and `LLM_MODEL`

## Phase 3 benchmark conventions

The common benchmark target is **Gemma 4 E4B (`Q4_K_M` equivalent, ~5 GB)**.
Chosen because (a) vision is native, (b) the ~5 GB footprint fits comfortably
on the target mini PC's 32 GB RAM, and (c) Google positions E4B as the
"developer laptop" tier, which matches our dev-rig-to-target extrapolation.
To keep Phase 3 comparable, do not swap in a different model family per tool.

Recommended model identifiers:

- Ollama: base model `gemma4:e4b`; benchmark alias `gemma4-e4b-bench`
  (custom Modelfile with `PARAMETER num_thread 14`)
- llama.cpp: GGUF file `gemma-4-E4B-it-Q4_K_M.gguf` (from
  `unsloth/gemma-4-E4B-it-GGUF` on Hugging Face) + the matching
  `mmproj-*.gguf` for the vision encoder
- LM Studio: loaded identifier `gemma4-e4b-bench` (import the GGUF
  from the Hub or a local path; set CPU threads = 14 in Server settings)

Phase 3 inputs are fixed:

- S1: text-only (`benchmarks/scenarios/s1_text_only.py`)
- S2: `samples/diagram.png`
- S3: `tests/text_vs_image/images/`

Phase 4 varies only the **quantization** of Gemma 4 E4B (`Q4_K_M`, `Q5_K_M`,
`Q8_0`, and optionally `FP16`/`BF16`) on the Phase 3 winning host. No other
model family is introduced.

## Endpoint contract

All candidates MUST expose an **OpenAI-compatible** HTTP endpoint. The
benchmark harness and the prototype client both talk to the endpoint through
`benchmarks/adapter/openai_client.py`. Switching candidates is just changing
two environment variables:

    LLM_BASE_URL=http://127.0.0.1:<port>/v1
    LLM_MODEL=<model-id-for-that-tool>
