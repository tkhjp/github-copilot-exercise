# Candidate LLM Hosts

Each candidate tool is launched on the dev rig (RTX 5090) in **CPU-only mode**
to approximate target mini PC behavior.

## Common setup

Before starting any candidate, dot-source the CPU-only env helper:

    . .\candidates\common\cpu_only_env.ps1

This sets `CUDA_VISIBLE_DEVICES=""`, `OLLAMA_NUM_GPU=0`, and pins OMP threads
to 14 (matching the mini PC's 6 P + 8 E cores).

Verify GPU is disabled by running a model and checking `nvidia-smi` — the
candidate process must not appear in the utilization list.

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
