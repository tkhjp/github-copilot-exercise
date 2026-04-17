# Local LLM Host Shortlist Benchmark

**Status:** Pending execution  
**Phase:** 3  
**Date:** _(fill in)_  
**Executor:** _(fill in)_  

## Fixed benchmark protocol

- Shortlist: `Ollama`, `llama.cpp`, `LM Studio`
- Common model: `Gemma 4 E4B` (`Q4_K_M` equivalent, ~5 GB)
- Inputs:
  - S1: text-only
  - S2: `samples/diagram.png`
  - S3: `tests/text_vs_image/images/`
- Run counts:
  - S1: 3 runs
  - S2: 3 runs
  - S3: 1 pass per image

## Raw output files

| Tool | S1 CSV | S1 MD | S2 CSV | S2 MD | S3 CSV | S3 MD |
|---|---|---|---|---|---|---|
| Ollama | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |
| llama.cpp | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |
| LM Studio | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ |

## Summary matrix

| Tool | S1 status | S2 status | S3 status | TTFT | tok/s | end-to-end | RSS peak | failure count | install friction | launch friction | restart stability | OpenAI API | local_llm_client | service path | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Ollama | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | manual | _(pending)_ |
| llama.cpp | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | manual | _(pending)_ |
| LM Studio | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | _(pending)_ | native | _(pending)_ |

## Per-host notes

### Ollama

- version:
- benchmark model:
- smoke result:
- benchmark result:
- operational notes:

### llama.cpp

- version:
- benchmark model:
- smoke result:
- benchmark result:
- operational notes:

### LM Studio

- version:
- benchmark model:
- smoke result:
- benchmark result:
- operational notes:

## Winner selection

### Hard gate result

- S2 and S3 complete without manual restart:
- `tools/lib/local_llm_client.py` connectivity:

### Decision

- **Winner:** _(fill in)_
- **Reason:** _(fill in)_
- **Rejected shortlist hosts:** _(fill in with concrete reasons)_
