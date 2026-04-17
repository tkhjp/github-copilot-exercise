# Gemma 4 E4B Quantization Sweep

**Status:** Pending execution  
**Phase:** 4  
**Date:** _(fill in)_  
**Executor:** _(fill in)_  
**Winning host from Phase 3:** _(fill in)_  

Project scope is fixed to a single model family (**Gemma 4 E4B**). Phase 4 therefore
compares quantization variants of that one model, not different model families.
The goal is to find the quality/speed sweet spot for the target mini PC.

## Fixed evaluation setup

- Host: Phase 3 winner only
- Model family: **Gemma 4 E4B** (fixed)
- Speed scenarios:
  - S2: `samples/diagram.png`
  - S3: `tests/text_vs_image/images/`
- Quality source of truth: `tests/text_vs_image/test_cases.yaml`
- Quality cases: `tc01`, `tc02`, `tc03`, `tc04`
- Score rule: `present=1`, `partial=0.5`, `missing=0`

## Candidate quantization pool

| Quantization | Approx. file size | Host identifier | Load/import path | Notes |
|---|---|---|---|---|
| Q4_K_M (Phase 3 baseline) | ~5 GB | _(pending)_ | _(pending)_ | carry over from Phase 3 |
| Q5_K_M | ~6 GB | _(pending)_ | _(pending)_ | _(pending)_ |
| Q8_0 | ~8 GB | _(pending)_ | _(pending)_ | _(pending)_ |
| FP16 / BF16 (optional) | ~15 GB | _(pending)_ | _(pending)_ | run only if RAM allows |

## Speed benchmark summary

| Quantization | S2 status | S2 TTFT | S2 tok/s | S2 end-to-end | S3 status | S3 tok/s | S3 end-to-end | RSS peak | failure count |
|---|---|---|---|---|---|---|---|---|---|
| Q4_K_M | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |
| Q5_K_M | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |
| Q8_0 | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |
| FP16 / BF16 | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |

## Quality score summary

| Quantization | tc01 | tc02 | tc03 | tc04 | Average | Notes |
|---|---|---|---|---|---|---|
| Q4_K_M | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |
| Q5_K_M | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |
| Q8_0 | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |
| FP16 / BF16 | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |

## Selection

- **First-choice quantization:** _(fill in)_
- **Reason:** _(fill in)_
- **Backup quantization:** _(fill in)_
- **Reason:** _(fill in)_

## Selection rule check

- First-choice quantization is quality winner:
- First-choice quantization completes S3:
- First-choice quantization is within 2x of the fastest variant:
- Backup quantization is smaller / faster than first-choice:
- Backup quantization is at least 80% of first-choice quality:
- Backup quantization is typically Q4_K_M (Phase 3 baseline) unless first-choice is already Q4_K_M:
