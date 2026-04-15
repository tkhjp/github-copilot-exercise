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

## Tools (populated during Phase 1)

The following subdirectories will be created during Phase 1/3 shortlist work,
each with a `start.ps1` launch script and a `notes.md` with install/version details:

- `ollama/` — Ollama on Windows native
- `llama-cpp/` — llama.cpp (Windows native, already compiled locally)
- `lm-studio/` — LM Studio (GUI; document server-mode startup)

## Endpoint contract

All candidates MUST expose an **OpenAI-compatible** HTTP endpoint. The
benchmark harness and the prototype client both talk to the endpoint through
`benchmarks/adapter/openai_client.py`. Switching candidates is just changing
two environment variables:

    LLM_BASE_URL=http://127.0.0.1:<port>/v1
    LLM_MODEL=<model-id-for-that-tool>
