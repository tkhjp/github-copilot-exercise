# Local LLM Appliance — Phase 3/4/6/7 Execution Plan

> **For agentic workers:** execute this plan in order. The benchmark harness and local backend client already exist; this plan covers shortlist measurement, model selection, target validation, and final reporting only.

**Goal:** Run the Phase 3 shortlist benchmark for `Ollama`, `llama.cpp`, and `LM Studio`, select the winning host, compare four vision models on the winner, validate one configuration on the target mini PC, and produce the final integrated report.

**Non-goal:** do not add new public APIs or change the `LLM_BACKEND=local` interface. The only repo-tracked additions in this phase are runbooks, startup wrappers, raw benchmark outputs, and reports.

## Fixed protocol

- Shortlist hosts: `Ollama`, `llama.cpp`, `LM Studio`
- Phase 3 common model: `Gemma 4 E4B` (`Q4_K_M` equivalent — ~5 GB on disk / RAM)
- Phase 3 inputs:
  - S1: text-only
  - S2: `samples/diagram.png`
  - S3: `tests/text_vs_image/images/`
- Phase 3 run counts:
  - S1: 3 runs
  - S2: 3 runs
  - S3: 1 pass per image
- Phase 4 quantization sweep (Gemma 4 E4B only, single model family):
  - `Q4_K_M` (~5 GB) — Phase 3 baseline
  - `Q5_K_M` (~6 GB)
  - `Q8_0` (~8 GB)
  - (optional) `FP16` / `BF16` (~15 GB) only if target mini PC has the headroom
- Phase 4 quality source of truth: `tests/text_vs_image/test_cases.yaml`
- Phase 4 quality cases: `tc01`, `tc02`, `tc03`, `tc04`
- Phase 4 scoring rule: `present=1`, `partial=0.5`, `missing=0`

## Deliverables

- `candidates/ollama/notes.md`
- `candidates/ollama/start.ps1`
- `candidates/llama-cpp/notes.md`
- `candidates/llama-cpp/start.ps1`
- `candidates/lm-studio/notes.md`
- `candidates/lm-studio/start.ps1`
- `docs/report/local-llm/02-tool-shortlist-benchmark.md`
- `docs/report/local-llm/03-model-selection.md`
- `docs/report/local-llm/04-target-validation.md`
- `docs/report/local-llm-selection-report.md`

## Phase 3 — shortlist benchmark

- [ ] Sync the environment:
  - `tools/requirements.txt`
  - `requirements-dev.txt`
- [ ] Run baseline verification:
  - `python3 -m pytest tests/benchmarks tests/lib/test_local_llm_client.py`
  - `python3 -m benchmarks.harness --help`
- [ ] Prepare each shortlist host using the runbooks under `candidates/`.
- [ ] Force CPU-only mode before launching any host:
  - `. .\candidates\common\cpu_only_env.ps1`
  - Verify: run `nvidia-smi` while the host is serving a request — the host process must show **0% GPU-Util and 0 MiB GPU memory**. If it appears in the GPU process list, the CPU-only env vars did not take effect; stop and debug before recording any numbers.
- [ ] For each host, execute:
  - S1 smoke with 1 run
  - S1 full run with 3 runs
  - S2 full run with 3 runs
  - S3 full run with one pass through `tests/text_vs_image/images/`
- [ ] Save raw CSV/Markdown under `benchmarks/out/`.
- [ ] Record the following in `docs/report/local-llm/02-tool-shortlist-benchmark.md`:
  - performance: TTFT, tok/s, end-to-end, RSS peak, failure count
  - ops: install friction, launch friction, restart stability
  - interface: OpenAI compatibility, `tools/lib/local_llm_client.py` connectivity
  - Windows service path: native / manual / impractical
- [ ] Pick the Phase 3 winner using these rules:
  - hard gate: S2 and S3 complete without manual restart, and `local_llm_client` works
  - if performance is within 20%, prefer the easier-to-operate host
  - prefer raw speed only when the fastest host is not operationally fragile

## Phase 4 — quantization sweep on the winning host

Project scope is fixed to a single model family (Gemma 4 E4B). Phase 4
therefore compares quantization variants of that one model, not different
model families. The goal is to find the quality/speed sweet spot for the
target mini PC.

- [ ] Keep the host fixed to the Phase 3 winner.
- [ ] Load each available Gemma 4 E4B quantization variant (Q4_K_M,
      Q5_K_M, Q8_0, and optionally FP16/BF16 if RAM allows).
- [ ] For each quantization, run:
  - S2 on `samples/diagram.png`
  - S3 on `tests/text_vs_image/images/`
- [ ] For each quantization, evaluate output quality on `tc01` through `tc04`
      using `test_cases.yaml`.
- [ ] Record speed metrics and quality scores in
      `docs/report/local-llm/03-model-selection.md`. Include per-quantization
      memory footprint (resident RSS during inference).
- [ ] Select:
  - first-choice quantization = highest quality that also completes S3 and
    stays within 2x of the fastest variant
  - backup quantization = smaller (faster, lighter) variant that retains
    at least 80% of the first-choice quality score — typically the Phase 3
    baseline `Q4_K_M` unless the first-choice is already Q4_K_M

## Phase 6 — target mini PC validation

- [ ] Install only the Phase 3 winning host and Phase 4 first-choice model on the mini PC.
- [ ] Run on the mini PC:
  - S2 once
  - S3 once
  - `LLM_BACKEND=local python tools/describe_image.py samples/diagram.png` once from the dev machine against the mini PC endpoint
- [ ] Compare the result with the dev-rig CPU-only baseline for the same host/model.
- [ ] If latency or throughput differs by more than 2x, downgrade the conclusion to `使用可能 / 限界的 / 不可` instead of forcing the earlier result.
- [ ] Record everything in `docs/report/local-llm/04-target-validation.md`.

## Phase 7 — final integrated report

- [ ] Consolidate Phase 1, 3, 4, and 6 into `docs/report/local-llm-selection-report.md`.
- [ ] Required sections:
  - executive summary
  - background and objective
  - tool matrix summary
  - shortlist benchmark result
  - quantization sweep result
  - target validation result
  - how to use the local backend prototype
  - risks and next steps
- [ ] The final conclusion must name:
  - adopted host
  - first-choice Gemma 4 E4B quantization
  - backup quantization

## Completion criteria

- At least two shortlist hosts complete S1/S2/S3.
- One host winner is named with written justification.
- One first-choice quantization and one backup quantization of Gemma 4 E4B are named with written justification.
- The mini PC validation result is classified as `使用可能`, `限界的`, or `不可`.
- The integrated report is decision-ready for procurement/deployment review.
