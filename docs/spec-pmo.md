# CLAUDE.md
 
Repo-specific guidance for Claude Code. Read this first; ground every change in the patterns below.
 
## What this is
 
**PMO-AI** is an event-sourced PMO assistant: it ingests raw PMO artefacts (meeting minutes, weekly reports, issue lists, milestone schedules) into a typed event ledger, reduces them into current-state views and projections, and exposes the result through a chatbot + dashboard for verification and writeback. The system intentionally mirrors a "wiki / pipeline / chatbot" 3-layer model where each layer is debuggable in isolation.
 
## Top-level layout
 
| Path | Service / role | Owner |
|---|---|---|
| `pipeline/` | 5-stage ingest: manifest → extract (LLM) → resolve → reduce → project | batch + writer-side |
| `pipeline/lib/project.py` | `PROJECTION_REGISTRY` of 15 projection builders + `refresh()` orchestrator | core |
| `pmo_ai_writer/` | FastAPI write-side service on `:8010`; **the only process allowed to mutate `data/10_ledger/`** | service |
| `chatbot/backend/` | FastAPI read-side service on `:8000`; LLM tool loop + scenario_runner + Phase 2C frontend mount | service |
| `chatbot/frontend/` | React 18 + Babel-standalone SPA served by chatbot at `/`; vanilla JS debugger preserved at `/debug.html` | frontend |
| `data/raw/` | source documents (`*.md`, `*.html`) — input to extraction | data |
| `data/10_ledger/` | append-only event/edge ledger + manifests + entity registry — **immutable** | data |
| `data/30_serving/` | derived `current_state/` + `projections/` (regenerable) | data |
| `data/40_schema/` | ontology + reducer rules + scenario YAMLs | data |
| `data/45_advisory/` | advisory artefacts (Phase 2D) | data |
| `data/50_feedback/` | human writeback dispositions (Phase 2C feedback_only) | data |
| `tests/` | top-level e2e (Smoke A/B/C) + cross-service integration | test |
| `pmo_ai_writer/tests/` + `chatbot/backend/tests/` | per-service unit + integration | test |
| `docs/superpowers/specs/` `plans/` | versioned design specs (16) + execution plans (20) | docs |
| `.claude/skills/` | project-scoped Claude skills (pmo-pipeline, pmo-extract, pmo-gold-label) | skills |
 
## The pipeline (raw → UI)
 
```
data/raw/<doc>
  ├─ pipeline/manifest.py        → 10_ledger/source_manifests/SRC-<TYPE>-<DATE>-<SLUG>.yaml
  ├─ pipeline/extract.py (LLM)   → 10_ledger/extracted/<sid>.jsonl
  │      (3-pass: operating / reasoning / edges; routed per source_type)
  ├─ pipeline/resolve.py         → resolved events + edges with canonical ids
  └─ pipeline/lib/writer_client.py → POST writer /api/ingest/append_batch
                                  → writer appends to 10_ledger/{events,edges}.jsonl
                                  → emits state_patch via SSE
 
writer /api/reduce/persist       → 30_serving/current_state/<entity_type>.json
writer /api/refresh_projections  → 30_serving/projections/<name>.json (15 builders)
                                  → state_patch SSE → chatbot consumer → live UI update
```
 
Single-file entry point: `pipeline/ingest_one.py <raw_path>` chains all 5 stages.
 
## The 3 running processes (local dev)
 
```bash
# 1. writer — :8010 (single-writer service, rw on data/)
python -m uvicorn pmo_ai_writer.main:app --host 127.0.0.1 --port 8010 --workers 1
 
# 2. chatbot — :8000 (read-only on data/; mounts frontend at /)
python -m uvicorn chatbot.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```
 
`.env` at repo root carries `AZURE_OPENAI_*`, `PROPOSAL_TOKEN_HMAC_KEY`, `CHATBOT_SERVICE_TOKEN`, `PIPELINE_SERVICE_TOKEN`, `WRITER_BASE_URL`, `AUTH_MODE=dev`. Load with `set -a && source .env && set +a` before launching uvicorn so both services see the secrets.
 
`docker-compose.yml` defines writer + chatbot + nginx-frontend for container mode, but local uvicorn is the day-to-day flow.
 
## Bedrock invariants — never violate
 
1. **Writer is the only mutator.** Nothing else writes to `data/10_ledger/events/events.jsonl` or `edges/edges.jsonl`. Pipeline POSTs via `writer_client`; reducer + refresh are writer endpoints. Bypassing this desyncs the writer's seq counter and the chatbot's snapshot.
2. **Event ledger is append-only.** No edits to past rows. Corrections go through new events (`*_status_changed`, `decision_deferred`, etc.). `ledger_seq` is strictly monotonic.
3. **modality is mandatory + enumerated.** `{fact, decision, commitment, proposal, inference, question}`. `"方向性合意"` / `"持ち帰り"` / `"来週確認します"` are **commitment**, NOT decision/fact.
4. **`object_id_candidate` uses raw-text form** (`K-001`, `UAT環境問題`). The resolver normalises to canonical (`ISS-K001`) using `data/10_ledger/registries/entity_registry.json`.
5. **Every event + edge needs `evidence_refs`**: `[{source_id, line_start, line_end}]`. No evidence → review_queue → not ingested.
6. **`event_type` must be in `data/40_schema/ontology.yaml: fact_event_types`.** Advisory and audit events are separate streams (`AdvisoryEvent`, `WriterRecovery`/`Confirmation`/`WritebackDisposition`).
7. **Chatbot is read-only on disk.** Operates via `app.state.snapshot_mutator.read_lock()` snapshot (Phase 2B). `app.state.snapshot` is intentionally NOT set.
 
## Service auth + SSE patterns (Phase 1+)
 
- Service-to-service: `Bearer <token>` with separate env-var roles
  - `CHATBOT_SERVICE_TOKEN`: chatbot → writer service auth (also gate for `/api/refresh_projections`)
  - `PIPELINE_SERVICE_TOKEN`: pipeline batch → writer (`/api/ingest/*`, `/api/reduce/persist`)
- User-to-chatbot (dev mode): `Bearer dev:<subject>:<comma_roles>` e.g. `dev:PER-MANAGER-001:pmo_lead,manager`. Production OAuth/JWT is v1.2+ backlog.
- SSE auth: **Authorization header** (NOT query param — leakage). Frontend uses fetch-streaming, not native `EventSource`, so it can send the header.
- Writer broadcasts state_patch via `/api/state_patches`; chatbot consumes via `state_patch_consumer` and re-publishes per-client through its own `state_patch_log` with cursor-based catch-up (Phase 2C).
 
## Phase 2C specifics (current UI)
 
- Universal panel at `chatbot/frontend/index.html` (React + Babel-standalone). Vanilla debugger preserved at `/debug.html`.
- 13 use cases; **only UC 00 + UC 02 live**; the other 11 are "Coming soon" panels (Phase 2D backlog).
- Writeback flow: chatbot proxy `/api/writebacks/confirm` checks `WritebackLock` (subject + session_id BOTH required, 300s lease, same-subject takeover), forwards user Bearer verbatim to writer.
- Live milestone Gantt on Home reads `/api/graph.by_type.milestone[*].{first_event_at, status, …}`.
 
## Conventions
 
- **Specs/plans naming**: `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`. Each plan is bite-sized TDD tasks; executed via `superpowers:subagent-driven-development`.
- **Commit messages**: `<type>(<scope>): <subject>` — types like `feat`, `fix`, `test`, `refactor`, `chore`, `docs`. Scopes seen: `2C.1`–`2C.28`, `pipeline`, `writer`, `chatbot`, `home`, `skill`, `extract`. Frequent small commits over batched ones.
- **Ad-hoc helpers** under `scripts/` use a `_` filename prefix (`_diag_extracted.py`, `_check_event_types.py`). Long-lived utilities have no prefix.
- **Tests**: pytest. Per-service unit tests + cross-service e2e (`tests/test_e2e_smoke_*.py`) with `WriterProcessFixture` from `tests/_phase15_helpers.py`. Tests must not depend on live LLM credentials unless they're under `_live_smoke_outputs/` (gitignored).
- **Windows host** (this dev env): use PowerShell for port management, Bash (gitbash) for normal shell. `data/10_ledger/_writer_journal/` + `_writer_patches/` are gitignored as transient runtime state.
 
## Skills
 
Project-scoped skills auto-loaded for relevant prompts:
 
| Skill | Purpose |
|---|---|
| `pmo-chat` | Plan → call `pmo-tools` CLI → observe → re-plan. Heavy tool execution runs in `pmo-executor` sub-agent (Phase 2). |
| `pmo-setup` | One-time onboarding for fresh checkouts: detect SP root, write `.pmo-role.yaml` + `.env`, smoke-test `pmo-tools call get_schema`. No MCP wiring (Phase 2 retired that path). |
| `pmo-pipeline` | Orchestrate pipeline ops (ingest, refresh-projections, subscribe state_patches) without manual CLI/curl. |
| `pmo-extract` | Full-batch entity+edge extraction using Claude itself as the LLM (replaces Azure OpenAI extract.py). 3 passes per source per ROUTING; dispatches one subagent per manifest. |
| `pmo-gold-label` | Generate gold-set CSV labels for one raw source, for the eval harness. |
 
## Useful commands
 
```bash
# Inventory pipeline state
ls data/10_ledger/source_manifests/ | wc -l  # source count
wc -l data/10_ledger/events/events.jsonl     # event count
curl -s http://127.0.0.1:8010/ready | jq .watermark   # writer seq
 
# Re-run pipeline for one file (chains all 5 stages)
python pipeline/ingest_one.py 02_Meeting/CPV-LM定例/20260512_xxx.md
 
# Refresh all projections (emits state_patch SSE to UI)
python scripts/_refresh_all.py    # uses CHATBOT_SERVICE_TOKEN
 
# Run a Phase 2C test slice
pytest chatbot/backend/tests/ --tb=short -q
pytest tests/test_e2e_smoke_b_state_patch_propagation.py -v
 
# Validate scenario YAML signatures (G1 schema gate)
python scripts/sign_scenario.py --check
```
 
## Where to look when
 
- **"How is X computed?"** → `pipeline/lib/project.py` (`PROJECTION_REGISTRY` + builder fn), then `pipeline/lib/reducer_core.py` / `reducers.py`.
- **"What can the LLM tool layer do?"** → `chatbot/backend/tools/__init__.py:build_default_registry` lists 12 tools; system prompt is `chatbot/backend/prompts/system.md`.
- **"What scenarios exist?"** → `data/40_schema/scenarios/S*.yaml` (15 declared, S00 + S02 implemented as of Phase 2C).
- **"What's the writer protocol?"** → `pmo_ai_writer/api/` (REST surface), `pmo_ai_writer/core/ledger_writer.py` (atomic append + recovery), `docs/superpowers/specs/2026-05-06-pmo-ai-phase1-writer-foundation-design.md`.
- **"What's still TODO?"** → newest spec under `docs/superpowers/specs/` (lookup by date); `Phase 2D` backlog inside each Phase 2 spec.
 
## Pitfalls
 
- Re-extracting + re-resolving without clearing `data/10_ledger/events/events.jsonl` first will **dedup against the local file** (resolver's `_load_existing_event_ids` reads it) and silently skip pushes to writer. For fresh rebuilds, archive `events.jsonl + edges.jsonl + watermark.json + _patch_seq_counter.json + extracted/` into `data/10_ledger/_archive/run_<ts>/` BEFORE running resolve.
- `record_type` in extracted JSONL must be in `{entity, event, edge, contradiction, unresolved_reference}` (all singular). `record_type: "key_question"` etc. is wrong — those are `object_type` values. `scripts/_normalize_extracted.py` fixes the common pattern.
- Browser caches Babel-standalone-transpiled JSX aggressively. After editing a `.jsx`, bump the `?v=YYYY-MM-DDx` cache buster in `chatbot/frontend/index.html` so all `<script>` URLs change; otherwise Ctrl+Shift+R may still serve stale transpiled output.
- `chatbot/backend/main.py` lifespan does `writer /ready` handshake BEFORE `GraphLoader.load()` (Phase 2B P0). Don't reorder.
