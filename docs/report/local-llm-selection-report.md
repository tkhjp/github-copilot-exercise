# Local LLM Selection Report

**Status:** Pending integration  
**Date:** _(fill in)_  
**Author:** _(fill in)_  

## Executive summary

- **Adopted host:** _(fill in)_
- **First-choice model:** _(fill in)_
- **Backup model:** _(fill in)_
- **Deployment recommendation:** _(fill in)_

## 1. Background and objective

- Copilot image input constraints:
- Governance requirement:
- Why the appliance approach is being evaluated:

## 2. Tool matrix summary

Reference: [01-tool-matrix](./local-llm/01-tool-matrix.md)

- shortlist:
- excluded tools and why:

## 3. Shortlist benchmark result

Reference: [02-tool-shortlist-benchmark](./local-llm/02-tool-shortlist-benchmark.md)

- winning host:
- why it won:
- why the others lost:

## 4. Model selection result

Reference: [03-model-selection](./local-llm/03-model-selection.md)

- first-choice model:
- backup model:
- speed/quality trade-off:

## 5. Target validation result

Reference: [04-target-validation](./local-llm/04-target-validation.md)

- target environment result:
- dev-rig vs mini PC gap:
- deployability judgment:

## 6. Local backend prototype usage

- `LLM_BACKEND=local`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `tools/describe_image.py`
- `tools/describe_pptx.py`

## 7. Risks and next steps

- authentication / TLS hardening:
- service registration:
- model lifecycle and upgrade path:
- recommended follow-up work:
