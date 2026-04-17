# Gemma 4 E4B Quantization Sweep

**Status:** Complete
**Phase:** 4
**Date:** 2026-04-17
**Executor:** Claude Opus 4.7 on dev rig (RTX 5090, CPU-only mode forced via `lms load --gpu off`)
**Winning host from Phase 3:** LM Studio 0.4.11 Build 1

Project scope is fixed to a single model family (**Gemma 4 E4B**). Phase 4
compared quantization variants of that one model. The goal was to find the
quality/speed sweet spot for the target mini PC.

## Fixed evaluation setup

- Host: LM Studio (Phase 3 winner, CPU-only via `lms load --gpu off`)
- Model family: **Gemma 4 E4B** from `unsloth/gemma-4-E4B-it-GGUF`
- Speed scenarios:
  - S2: `samples/diagram.png` (3 runs)
  - S3: `tests/text_vs_image/images/` (4 images, 1 pass each)
- Quality source of truth: `tests/text_vs_image/test_cases.yaml`
- Quality cases: `tc01`, `tc02`, `tc03`, `tc04`
- Quality judge: **Gemini 2.5 Flash** (external API)
- Score rule: `present=1.0`, `partial=0.5`, `missing=0.0`
- Quality eval script: [tests/text_vs_image/phase4_quality_eval.py](../../../tests/text_vs_image/phase4_quality_eval.py)

## Candidate quantization pool

| Quantization | File size | LM Studio identifier | Loaded as | Notes |
|---|---|---|---|---|
| Q4_K_M (Phase 3 baseline) | 4.98 GB | `gemma-4-e4b-it@q4_k_m` | `gemma4-e4b-q4` | reused Phase 3 speed data |
| Q5_K_M | 5.48 GB | `gemma-4-e4b-it@q5_k_m` | `gemma4-e4b-q5` | new for Phase 4 |
| Q8_0 | 8.19 GB | `gemma-4-e4b-it@q8_0` | `gemma4-e4b-q8` | new for Phase 4 |
| FP16 / BF16 | 15.05 GB | (not loaded) | — | skipped — would leave mini PC with ~15 GB headroom, too tight |

All three shared the same `mmproj-F16.gguf` (~990 MB) vision projector.

## Speed benchmark summary

Medians across runs, CPU-only, 14 threads:

| Quantization | S2 wall (s) | S2 tok/s | S2 end-to-end | S3 wall/img (s) | S3 tok/s | S3 end-to-end | RSS peak | failure count |
|---|---|---|---|---|---|---|---|---|
| Q4_K_M | **46.8** | **14.8** | 46.8 s/image | **81.9** | **14.6** | 327.6 s / 4 imgs | N/A ¹ | 0 |
| Q5_K_M | 58.5 | 12.8 | 58.5 s/image | 89.5 | 12.7 | 358.2 s / 4 imgs | N/A ¹ | 0 |
| Q8_0 | 77.4 | 9.5 | 77.4 s/image | 117.9 | 9.3 | 471.7 s / 4 imgs | N/A ¹ | 0 |

¹ RSS peak instrumentation not yet wired into harness; LM Studio GUI showed roughly file-size-matching RAM usage (~6, ~6.5, ~9 GB resident for Q4 / Q5 / Q8).

Speed follows file size linearly, as expected for CPU-only inference bottlenecked by memory bandwidth:

- Q5_K_M is ~25 % slower than Q4_K_M (matches the ~10 % larger file plus quantization decode overhead).
- Q8_0 is ~65 % slower than Q4_K_M. At 9.5 tok/s on S2 it sits just above the "CPU usable" threshold.

## Quality score summary

Judge: **Gemini 2.5 Flash** scored each ground-truth fact from `test_cases.yaml` as present / partial / missing against the Gemma output.

| Quantization | tc01 (24 facts) | tc02 (20 facts) | tc03 (26 facts) | tc04 (22 facts) | Average | Avg describe time |
|---|---|---|---|---|---|---|
| **Q4_K_M** | **0.667** | **0.650** | **0.769** | 0.955 | **0.760** | 58.8 s |
| Q5_K_M | 0.667 | 0.550 | 0.673 | **1.000** | 0.722 | 63.4 s |
| Q8_0 | **0.708** | 0.450 | 0.750 | 0.955 | 0.716 | 91.1 s |

Raw judge outputs and per-fact verdicts are under
[benchmarks/out/phase4/quality/](../../../benchmarks/out/phase4/quality/).

### Observations

1. **Q4_K_M has the highest average score (0.760), not the lowest** — contrary to the usual "less quantization = higher quality" intuition. This is best read as "all three quants are statistically indistinguishable on this small test set (N=4 cases) — Q4 happens to edge out by a rounding-noise margin."
2. **tc02 is the hardest case** for all quants (0.450 – 0.650). It's the UI change case; the model struggles to enumerate before/after state deltas cleanly.
3. **tc04 is the easiest case** for all quants (0.955 – 1.000). It's the plain text document case — close to a pure OCR task where Gemma 4 E4B's native multilingual OCR shines.
4. **Judge variance**: Gemini 2.5 Flash is itself sampled. Re-running the exact same description could yield slightly different verdicts. The 0.04 spread between quants is within this noise envelope.

## Selection

- **First-choice quantization:** **Q4_K_M**
- **Reason:**
  1. Tied-best average quality (0.760) across all three quants on this test set.
  2. **Fastest** — S2 46.8 s vs Q5 58.5 s (+25 %) vs Q8 77.4 s (+65 %).
  3. **Smallest memory footprint** — 4.98 GB on disk / ~6 GB RAM during inference, leaving the target mini PC (32 GB RAM) the most headroom for other processes (OS, user desktop, browser, etc.).
  4. Matches the Phase 3 baseline already measured on Ollama / llama.cpp / LM Studio; users comparing hosts later will have apples-to-apples numbers.

- **Backup quantization:** **Q5_K_M**
- **Reason:**
  1. Quality within 95 % of first-choice (0.722 / 0.760 = 0.95) — well above the 80 % floor.
  2. Different quantization tier, so if a future Gemma 4 E4B model update breaks Q4_K_M it's unlikely to break Q5_K_M the same way.
  3. Speed still in the "usable" range (S2 58.5 s). Same mmproj file, same loading path in LM Studio, low switching friction.

## Selection rule check

- ✅ First-choice quantization is (tied-) quality winner (0.760 avg).
- ✅ First-choice quantization completes S3 (4/4 images, 0 failures).
- ✅ First-choice quantization is within 2x of the fastest variant (it **is** the fastest).
- ✅ Backup quantization (Q5_K_M) is smaller/faster/lighter than Q8, heavier than Q4 — sits as the quality-ceiling reference.
- ✅ Backup quantization is at least 80 % of first-choice quality (95 %).
- ✅ Backup quantization falls back to Phase 3 baseline Q4_K_M if Q5 breaks.
- **Q8_0 excluded** — slowest AND tied-lowest on quality on this test set. No reason to prefer it over Q5 as a backup.

## Caveats

- **Small N:** 4 test cases with ~90 facts total. The quality numbers have high sampling variance. A 10-case bench would tighten the comparison meaningfully.
- **Single judge:** Gemini 2.5 Flash alone. A second judge (Gemini 2.5 Pro or a different family) would catch judge-specific bias.
- **Default sampling:** LM Studio's default `temperature`, `top_p`, and `max_tokens` were used for all three quants. A `temperature=0` deterministic run would eliminate one noise source but might also change the quality numbers uniformly.
- **Japanese-only prompts:** `tc01..tc04` are all Japanese questions. English or mixed-language prompts weren't tested.

For Phase 6 (target mini PC validation), Q4_K_M is the configuration to install and measure. Phase 4 dev-rig speed is the baseline the target-machine numbers will be compared against.
