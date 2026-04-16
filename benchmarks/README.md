# Benchmark Harness

Measures local LLM host candidates under three scenarios:

- **S1 — text-only**: short prompt baseline
- **S2 — vision-single**: one image describe, vision encoder cost
- **S3 — vision-pptx-batch**: sequence of images, steady-state throughput

## Prerequisites

- Python 3.13 + packages from `tools/requirements.txt` and `requirements-dev.txt`
- A running candidate tool exposing an OpenAI-compatible endpoint
- CPU-only mode enabled (see `candidates/README.md`)

## Usage

S1 text-only:

    python -m benchmarks.harness --tool ollama \
        --model qwen2.5-vl:7b \
        --base-url http://127.0.0.1:11434/v1 \
        --scenario s1 --n-runs 3

S2 vision-single:

    python -m benchmarks.harness --tool ollama \
        --model qwen2.5-vl:7b \
        --base-url http://127.0.0.1:11434/v1 \
        --scenario s2 --image samples/diagram.png --n-runs 3

S3 vision-pptx-batch (images exported from a pptx or any directory of .png/.jpg):

    python -m benchmarks.harness --tool ollama \
        --model qwen2.5-vl:7b \
        --base-url http://127.0.0.1:11434/v1 \
        --scenario s3 --pptx-dir samples/pptx_images

## Output

Each run writes two files under `--out-dir` (default `benchmarks/out/`):

- `<tool>_<scenario>_<model>.csv` — one row per run
- `<tool>_<scenario>_<model>.md` — summary + per-run table

## Exit codes

- `0` — all runs succeeded
- `1` — at least one run failed but some succeeded
- `2` — all runs failed

## Regression baseline

Phase 5 preserves `LLM_BACKEND=gemini` (default) as the working configuration.
The Gemini path was expected to be smoke-tested against `samples/diagram.png` at the end of
Phase 5 implementation and produce valid Japanese Markdown output — see the
Phase 5 commit log. This test was not executed during Phase 5 implementation due to missing GEMINI_API_KEY.
