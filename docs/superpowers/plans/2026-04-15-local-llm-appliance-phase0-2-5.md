# Local LLM Appliance — Phase 0/1/2/5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the baseline (Phase 0), produce the tool-survey matrix template (Phase 1), build the benchmark harness + OpenAI-compatible adapter (Phase 2), and wrap the adapter in a Gemini-interface-compatible local LLM client so the existing image-describer CLIs can switch backend via `.env` (Phase 5). Phases 3/4/6/7 are execution/measurement/report and will get their own plan after Phase 1's tool matrix is filled in.

**Architecture:** A new top-level `benchmarks/` package contains (a) the reusable OpenAI-compatible adapter (`benchmarks/adapter/openai_client.py`) that forms the single call-site contract for all local LLM backends, (b) pluggable scenarios (S1 text / S2 vision single / S3 vision pptx batch), (c) a metrics collector and report writer (CSV + Markdown). A new `tools/lib/local_llm_client.py` wraps the same adapter behind the existing `gemini_client.describe_image` interface, and the three CLIs dispatch on `LLM_BACKEND=gemini|local`. Candidate launch scripts live under `candidates/` with a CPU-only environment helper.

**Tech Stack:** Python 3.13, `openai` SDK (already in `tools/requirements.txt`), `pytest` + `pytest-mock` (added in Phase 0), `psutil` for RSS/CPU metrics, `python-dotenv` (already present), Windows PowerShell for launch scripts.

---

## File Structure

**Created:**
- `benchmarks/__init__.py`
- `benchmarks/harness.py` — CLI driver (`python -m benchmarks.harness --tool ollama --scenario s2 --model qwen2.5-vl:7b`)
- `benchmarks/metrics.py` — metrics container + collector (TTFT, tok/s, RSS peak, wall time)
- `benchmarks/report.py` — CSV + Markdown writer
- `benchmarks/adapter/__init__.py`
- `benchmarks/adapter/openai_client.py` — OpenAI-compatible client (reused in Phase 5)
- `benchmarks/scenarios/__init__.py`
- `benchmarks/scenarios/base.py` — `Scenario` dataclass + base run contract
- `benchmarks/scenarios/s1_text_only.py`
- `benchmarks/scenarios/s2_vision_single.py`
- `benchmarks/scenarios/s3_vision_pptx_batch.py`
- `benchmarks/README.md`
- `candidates/README.md` — how to start each candidate tool
- `candidates/common/cpu_only_env.ps1` — force CPU-only mode
- `docs/report/local-llm/01-tool-matrix.md` — Phase 1 deliverable template
- `tools/lib/local_llm_client.py` — wraps adapter, exposes Gemini-compatible interface
- `tests/__init__.py`
- `tests/conftest.py` — shared fixtures
- `tests/benchmarks/__init__.py`
- `tests/benchmarks/test_openai_client.py`
- `tests/benchmarks/test_metrics.py`
- `tests/benchmarks/test_report.py`
- `tests/benchmarks/test_scenarios.py`
- `tests/lib/__init__.py`
- `tests/lib/test_local_llm_client.py`
- `requirements-dev.txt` — pytest, pytest-mock (test-only; psutil lives in `tools/requirements.txt` since it is runtime-imported by `benchmarks/metrics.py`)

**Modified:**
- `tools/requirements.txt` — add `psutil>=5.9` (shared between benchmarks and local client metrics)
- `tools/describe_image.py:16` — switch import to backend-dispatcher
- `tools/describe_pptx.py` — same
- `tools/describe_docx.py` — same

**Not Modified:**
- `tools/lib/gemini_client.py` — left intact; local_llm_client mirrors its interface
- `.env.example` — that file is a test fixture for the hooks demo; local LLM env vars documented in `benchmarks/README.md` and `candidates/README.md` instead

---

## Phase 0 — Baseline & Setup

### Task 1: Add dev/benchmark dependencies

**Files:**
- Create: `requirements-dev.txt`
- Modify: `tools/requirements.txt`

- [ ] **Step 1: Create `requirements-dev.txt` with exact content**

```
pytest>=8.0
pytest-mock>=3.12
```

- [ ] **Step 2: Append psutil to `tools/requirements.txt`**

Final file content:

```
google-genai>=0.3.0
openai>=1.0.0
python-pptx>=1.0.0
python-docx>=1.1.0
python-dotenv>=1.0.0
Pillow>=10.0.0
psutil>=5.9
```

- [ ] **Step 3: Install dependencies**

Run:

```
pip install -r tools/requirements.txt -r requirements-dev.txt
```

Expected: no errors, `pytest --version` and `python -c "import psutil, openai"` succeed.

- [ ] **Step 4: Commit**

```
git add requirements-dev.txt tools/requirements.txt
git commit -m "chore: add pytest and psutil for benchmarks"
```

---

### Task 2: CPU-only environment helper

**Files:**
- Create: `candidates/common/cpu_only_env.ps1`
- Create: `candidates/README.md`

- [ ] **Step 1: Write `candidates/common/cpu_only_env.ps1`**

Exact content:

```powershell
# Force CPU-only mode for candidate LLM hosts.
# Usage: dot-source this script before starting a candidate tool, e.g.
#   . .\candidates\common\cpu_only_env.ps1
#   ollama serve
#
# Target machine (mini PC) has i5-14500T: 6 P-cores + 8 E-cores = 14 cores, 20 threads.
# On the dev rig we pin OMP/MKL threads to 14 to approximate target behavior.

$env:CUDA_VISIBLE_DEVICES = ""
$env:HIP_VISIBLE_DEVICES = ""
$env:OLLAMA_NUM_GPU = "0"        # Ollama: disable GPU layers
$env:LLAMA_CUBLAS = "0"           # llama.cpp: disable cuBLAS
$env:GGML_CUDA_DISABLE = "1"      # ggml backend: disable CUDA
$env:OMP_NUM_THREADS = "14"
$env:MKL_NUM_THREADS = "14"
Write-Host "CPU-only mode enabled. CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=14"
```

- [ ] **Step 2: Verify it runs without error**

Run (in PowerShell from repo root):

```
powershell -NoProfile -File candidates/common/cpu_only_env.ps1
```

Expected output: `CPU-only mode enabled. CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=14`
Expected exit code: 0

- [ ] **Step 3: Write `candidates/README.md`**

Exact content:

```markdown
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
```

- [ ] **Step 4: Commit**

```
git add candidates/common/cpu_only_env.ps1 candidates/README.md
git commit -m "chore: add CPU-only env helper and candidates README"
```

---

## Phase 1 — Tool Survey Matrix (template)

### Task 3: Tool matrix document template

**Files:**
- Create: `docs/report/local-llm/01-tool-matrix.md`

- [ ] **Step 1: Write the matrix template**

Exact content:

```markdown
# 本地 LLM ホスティングツール 調査マトリクス

**調査日:** _(fill in YYYY-MM-DD when populated)_
**調査者:** _(fill in)_

## 候補一覧

| # | ツール | バージョン | 公式サイト |
|---|-------|-----------|-----------|
| 1 | Ollama | | |
| 2 | llama.cpp | | |
| 3 | LM Studio | | |
| 4 | IPEX-LLM | | |
| 5 | OpenVINO-GenAI | | |
| 6 | text-generation-webui | | |
| 7 | vLLM（除外項） | | |

## 評価軸

| ツール | Windows native 対応 | CPU 推論品質 | Intel AMX / iGPU 加速 | 対応 vision モデル族 | OpenAI 互換 API | Windows サービス化難度 | ライセンス | 直近 release | 評価 |
|-------|--------------------|------------|---------------------|--------------------|----------------|---------------------|----------|-------------|-----|
| Ollama | | | | | | | | | |
| llama.cpp | | | | | | | | | |
| LM Studio | | | | | | | | | |
| IPEX-LLM | | | | | | | | | |
| OpenVINO-GenAI | | | | | | | | | |
| text-generation-webui | | | | | | | | | |
| vLLM | | | | | | | | | |

凡例:
- Windows native: `○` 動く / `△` WSL 経由のみ / `×` 非対応
- CPU 推論品質: `○` 主力経路 / `△` 可能だが遅い / `×` 非推奨
- 加速: `○` 公式サポート / `△` 第三者パッチ / `×` 非対応
- OpenAI 互換 API: `○` native / `△` プロキシ経由 / `×` なし
- 評価: `選定` / `除外`（後者には必ず理由を別記）

## 選定候補と除外理由

### 選定候補（Phase 3 で深度評測）

1. **_(tool A)_** — 選定理由:
2. **_(tool B)_** — 選定理由:
3. **_(tool C)_** — 選定理由:（最大 3 つまで）

### 除外（理由付き）

- **vLLM** — 除外理由: CUDA 必須で目標 mini PC（iGPU のみ）では動作不可。参考値として記録するに留める。
- **_(other)_** — 除外理由:

## Vision モデル対応状況（各ツールで確認）

| ツール | Qwen2.5-VL (3B/7B) | MiniCPM-V 2.6 (8B) | Llama 3.2 Vision (11B) | InternVL2.5 (4B/8B) | 備考 |
|-------|-------------------|--------------------|------------------------|---------------------|-----|
| Ollama | | | | | |
| llama.cpp | | | | | |
| LM Studio | | | | | |

凡例: `○` 公式 registry 有 / `△` GGUF 手動変換要 / `×` 非対応 / `?` 未確認

## 結論

_(fill in after research: 選定候補 2〜3 種の最終選定 + 各ツールの基本性格の 1 行サマリ)_
```

- [ ] **Step 2: Commit**

```
git add docs/report/local-llm/01-tool-matrix.md
git commit -m "docs: add tool survey matrix template for Phase 1"
```

**Note:** Filling in the matrix (hands-on desk research) is an execution step owned by Phase 1 itself, not this plan. The template is the deliverable this plan produces; the filled-in matrix is the deliverable Phase 1 execution produces.

---

## Phase 2 — Benchmark Harness & Adapter (TDD)

### Task 4: Package scaffolding and test infrastructure

**Files:**
- Create: `benchmarks/__init__.py`
- Create: `benchmarks/adapter/__init__.py`
- Create: `benchmarks/scenarios/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/benchmarks/__init__.py`
- Create: `tests/lib/__init__.py`
- Create: `pytest.ini`

- [ ] **Step 1: Create all `__init__.py` as empty files**

Create the 6 `__init__.py` files listed above with empty content (0 bytes).

- [ ] **Step 2: Create `pytest.ini`**

Exact content:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra --strict-markers
```

- [ ] **Step 3: Create `tests/conftest.py`**

Exact content:

```python
"""Shared pytest fixtures for benchmarks and local LLM client tests."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))
```

- [ ] **Step 4: Verify pytest discovers the empty test tree**

Run:

```
pytest --collect-only
```

Expected: exit 0, output `collected 0 items` (no tests yet).

- [ ] **Step 5: Commit**

```
git add benchmarks tests pytest.ini
git commit -m "chore: scaffold benchmarks and tests packages"
```

---

### Task 5: OpenAI-compatible adapter — write failing tests

**Files:**
- Test: `tests/benchmarks/test_openai_client.py`

- [ ] **Step 1: Write `tests/benchmarks/test_openai_client.py`**

Exact content:

```python
"""Tests for benchmarks.adapter.openai_client."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from benchmarks.adapter.openai_client import (
    AdapterConfig,
    ChatResult,
    LocalLLMAdapter,
)


def test_adapter_config_requires_base_url():
    with pytest.raises(ValueError, match="base_url"):
        AdapterConfig(base_url="", model="qwen2.5-vl:7b")


def test_adapter_config_requires_model():
    with pytest.raises(ValueError, match="model"):
        AdapterConfig(base_url="http://127.0.0.1:11434/v1", model="")


def test_adapter_config_defaults_api_key():
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    assert cfg.api_key == "not-needed"


def test_chat_text_only_returns_content():
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_openai_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "hello"
    fake_response.usage = MagicMock(
        prompt_tokens=5, completion_tokens=2, total_tokens=7
    )
    fake_openai_client.chat.completions.create.return_value = fake_response

    with patch(
        "benchmarks.adapter.openai_client.OpenAI",
        return_value=fake_openai_client,
    ):
        adapter = LocalLLMAdapter(cfg)
        result = adapter.chat_text("say hello")

    assert isinstance(result, ChatResult)
    assert result.content == "hello"
    assert result.prompt_tokens == 5
    assert result.completion_tokens == 2
    assert result.wall_seconds >= 0


def test_chat_vision_encodes_image_as_data_url():
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_openai_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "an image of a diagram"
    fake_response.usage = MagicMock(
        prompt_tokens=100, completion_tokens=8, total_tokens=108
    )
    fake_openai_client.chat.completions.create.return_value = fake_response

    with patch(
        "benchmarks.adapter.openai_client.OpenAI",
        return_value=fake_openai_client,
    ):
        adapter = LocalLLMAdapter(cfg)
        result = adapter.chat_vision(
            prompt="describe", image_bytes=b"\x89PNG\r\n\x1a\n", mime_type="image/png"
        )

    assert result.content == "an image of a diagram"
    call_args = fake_openai_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    content_parts = messages[0]["content"]
    assert any(p["type"] == "text" and p["text"] == "describe" for p in content_parts)
    image_part = next(p for p in content_parts if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")


def test_chat_raises_on_empty_content():
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_openai_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = ""
    fake_response.usage = MagicMock(
        prompt_tokens=1, completion_tokens=0, total_tokens=1
    )
    fake_openai_client.chat.completions.create.return_value = fake_response

    with patch(
        "benchmarks.adapter.openai_client.OpenAI",
        return_value=fake_openai_client,
    ):
        adapter = LocalLLMAdapter(cfg)
        with pytest.raises(RuntimeError, match="empty"):
            adapter.chat_text("hello")
```

- [ ] **Step 2: Run tests, confirm they fail**

Run:

```
pytest tests/benchmarks/test_openai_client.py -v
```

Expected: all 6 tests FAIL (or ERROR) with `ModuleNotFoundError: No module named 'benchmarks.adapter.openai_client'`

---

### Task 6: OpenAI-compatible adapter — implementation

**Files:**
- Create: `benchmarks/adapter/openai_client.py`

- [ ] **Step 1: Write `benchmarks/adapter/openai_client.py`**

Exact content:

```python
"""OpenAI-compatible chat client used by benchmarks and by the Phase 5 prototype.

This is the single call-site contract for all local LLM backends. Any tool
(Ollama, llama.cpp, LM Studio, ...) that exposes an OpenAI-compatible
/v1/chat/completions endpoint can be swapped in by changing AdapterConfig.
"""
from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class AdapterConfig:
    base_url: str
    model: str
    api_key: str = "not-needed"
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        if not self.base_url:
            raise ValueError("base_url must be non-empty")
        if not self.model:
            raise ValueError("model must be non-empty")


@dataclass(frozen=True)
class ChatResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    wall_seconds: float


class LocalLLMAdapter:
    def __init__(self, config: AdapterConfig) -> None:
        self._config = config
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout_seconds,
        )

    def chat_text(self, prompt: str) -> ChatResult:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": prompt}
        ]
        return self._send(messages)

    def chat_vision(
        self, prompt: str, image_bytes: bytes, mime_type: str
    ) -> ChatResult:
        if not image_bytes:
            raise ValueError("image_bytes must be non-empty")
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{b64}"
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]
        return self._send(messages)

    def _send(self, messages: list[dict[str, Any]]) -> ChatResult:
        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=messages,
        )
        wall = time.perf_counter() - start

        content = response.choices[0].message.content or ""
        if not content.strip():
            raise RuntimeError(
                f"Backend {self._config.base_url} returned empty content"
            )
        usage = response.usage
        return ChatResult(
            content=content,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            wall_seconds=wall,
        )
```

- [ ] **Step 2: Run tests, confirm they pass**

Run:

```
pytest tests/benchmarks/test_openai_client.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 3: Commit**

```
git add benchmarks/adapter/openai_client.py tests/benchmarks/test_openai_client.py
git commit -m "feat(benchmarks): OpenAI-compatible adapter with text/vision chat"
```

---

### Task 7: Metrics module — failing tests

**Files:**
- Test: `tests/benchmarks/test_metrics.py`

- [ ] **Step 1: Write `tests/benchmarks/test_metrics.py`**

Exact content:

```python
"""Tests for benchmarks.metrics."""
from __future__ import annotations

from benchmarks.metrics import RunMetrics, aggregate


def test_run_metrics_derives_tok_per_sec():
    m = RunMetrics(
        scenario="s1",
        tool="ollama",
        model="qwen2.5-vl:7b",
        wall_seconds=2.0,
        prompt_tokens=10,
        completion_tokens=20,
        ttft_seconds=0.5,
        rss_peak_mb=1024.0,
        cpu_percent_avg=55.5,
        ok=True,
        error=None,
    )
    assert m.completion_tok_per_sec == 10.0


def test_run_metrics_zero_wall_avoids_division():
    m = RunMetrics(
        scenario="s1",
        tool="ollama",
        model="qwen2.5-vl:7b",
        wall_seconds=0.0,
        prompt_tokens=0,
        completion_tokens=0,
        ttft_seconds=0.0,
        rss_peak_mb=0.0,
        cpu_percent_avg=0.0,
        ok=False,
        error="timeout",
    )
    assert m.completion_tok_per_sec == 0.0


def test_aggregate_computes_medians():
    runs = [
        RunMetrics("s1", "ollama", "m", 1.0, 10, 10, 0.2, 100.0, 50.0, True, None),
        RunMetrics("s1", "ollama", "m", 2.0, 10, 20, 0.3, 200.0, 60.0, True, None),
        RunMetrics("s1", "ollama", "m", 3.0, 10, 30, 0.4, 300.0, 70.0, True, None),
    ]
    agg = aggregate(runs)
    assert agg["median_wall_seconds"] == 2.0
    assert agg["median_ttft_seconds"] == 0.3
    assert agg["success_rate"] == 1.0


def test_aggregate_handles_failures_in_success_rate():
    runs = [
        RunMetrics("s1", "ollama", "m", 1.0, 10, 10, 0.2, 100.0, 50.0, True, None),
        RunMetrics("s1", "ollama", "m", 0.0, 0, 0, 0.0, 0.0, 0.0, False, "x"),
    ]
    agg = aggregate(runs)
    assert agg["success_rate"] == 0.5


def test_aggregate_empty_returns_zeros():
    agg = aggregate([])
    assert agg == {
        "median_wall_seconds": 0.0,
        "median_ttft_seconds": 0.0,
        "median_completion_tok_per_sec": 0.0,
        "peak_rss_mb": 0.0,
        "success_rate": 0.0,
        "n_runs": 0,
    }
```

- [ ] **Step 2: Run tests, confirm they fail**

Run:

```
pytest tests/benchmarks/test_metrics.py -v
```

Expected: all 5 tests ERROR with `ModuleNotFoundError: No module named 'benchmarks.metrics'`.

---

### Task 8: Metrics module — implementation

**Files:**
- Create: `benchmarks/metrics.py`

- [ ] **Step 1: Write `benchmarks/metrics.py`**

Exact content:

```python
"""Benchmark metrics container and aggregation."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RunMetrics:
    scenario: str
    tool: str
    model: str
    wall_seconds: float
    prompt_tokens: int
    completion_tokens: int
    ttft_seconds: float
    rss_peak_mb: float
    cpu_percent_avg: float
    ok: bool
    error: str | None

    @property
    def completion_tok_per_sec(self) -> float:
        if self.wall_seconds <= 0:
            return 0.0
        return self.completion_tokens / self.wall_seconds


def aggregate(runs: Sequence[RunMetrics]) -> dict[str, float | int]:
    if not runs:
        return {
            "median_wall_seconds": 0.0,
            "median_ttft_seconds": 0.0,
            "median_completion_tok_per_sec": 0.0,
            "peak_rss_mb": 0.0,
            "success_rate": 0.0,
            "n_runs": 0,
        }
    ok_runs = [r for r in runs if r.ok]
    walls = [r.wall_seconds for r in ok_runs] or [0.0]
    ttfts = [r.ttft_seconds for r in ok_runs] or [0.0]
    tps = [r.completion_tok_per_sec for r in ok_runs] or [0.0]
    return {
        "median_wall_seconds": statistics.median(walls),
        "median_ttft_seconds": statistics.median(ttfts),
        "median_completion_tok_per_sec": statistics.median(tps),
        "peak_rss_mb": max((r.rss_peak_mb for r in runs), default=0.0),
        "success_rate": len(ok_runs) / len(runs),
        "n_runs": len(runs),
    }
```

- [ ] **Step 2: Run tests, confirm they pass**

Run:

```
pytest tests/benchmarks/test_metrics.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 3: Commit**

```
git add benchmarks/metrics.py tests/benchmarks/test_metrics.py
git commit -m "feat(benchmarks): metrics dataclass and aggregation"
```

---

### Task 9: Report writer — failing tests

**Files:**
- Test: `tests/benchmarks/test_report.py`

- [ ] **Step 1: Write `tests/benchmarks/test_report.py`**

Exact content:

```python
"""Tests for benchmarks.report."""
from __future__ import annotations

import csv
from pathlib import Path

from benchmarks.metrics import RunMetrics
from benchmarks.report import write_csv, write_markdown


def _sample_runs() -> list[RunMetrics]:
    return [
        RunMetrics("s2", "ollama", "qwen2.5-vl:7b",
                   3.5, 128, 42, 0.8, 6200.0, 82.1, True, None),
        RunMetrics("s2", "ollama", "qwen2.5-vl:7b",
                   4.1, 128, 50, 0.9, 6400.0, 85.0, True, None),
    ]


def test_write_csv_produces_header_and_rows(tmp_path: Path):
    out = tmp_path / "runs.csv"
    write_csv(_sample_runs(), out)
    with out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["scenario"] == "s2"
    assert rows[0]["tool"] == "ollama"
    assert float(rows[0]["wall_seconds"]) == 3.5
    assert rows[0]["ok"] == "True"


def test_write_markdown_contains_summary_and_table(tmp_path: Path):
    out = tmp_path / "runs.md"
    write_markdown(_sample_runs(), out, title="Phase 3 — Ollama S2")
    text = out.read_text(encoding="utf-8")
    assert "# Phase 3 — Ollama S2" in text
    assert "median_wall_seconds" in text
    assert "| scenario | tool | model |" in text
    assert "ollama" in text
```

- [ ] **Step 2: Run tests, confirm they fail**

Run:

```
pytest tests/benchmarks/test_report.py -v
```

Expected: 2 tests ERROR with `ModuleNotFoundError: No module named 'benchmarks.report'`.

---

### Task 10: Report writer — implementation

**Files:**
- Create: `benchmarks/report.py`

- [ ] **Step 1: Write `benchmarks/report.py`**

Exact content:

```python
"""CSV and Markdown report writers for benchmark runs."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from benchmarks.metrics import RunMetrics, aggregate

_CSV_FIELDS = [
    "scenario",
    "tool",
    "model",
    "wall_seconds",
    "prompt_tokens",
    "completion_tokens",
    "completion_tok_per_sec",
    "ttft_seconds",
    "rss_peak_mb",
    "cpu_percent_avg",
    "ok",
    "error",
]


def write_csv(runs: Sequence[RunMetrics], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for r in runs:
            writer.writerow({
                "scenario": r.scenario,
                "tool": r.tool,
                "model": r.model,
                "wall_seconds": r.wall_seconds,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "completion_tok_per_sec": f"{r.completion_tok_per_sec:.4f}",
                "ttft_seconds": r.ttft_seconds,
                "rss_peak_mb": r.rss_peak_mb,
                "cpu_percent_avg": r.cpu_percent_avg,
                "ok": r.ok,
                "error": r.error or "",
            })


def write_markdown(
    runs: Sequence[RunMetrics], out_path: Path, title: str
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    agg = aggregate(runs)
    lines: list[str] = [f"# {title}", ""]
    lines.append("## Summary")
    for key, value in agg.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")
    lines.append("## Runs")
    lines.append("")
    lines.append(
        "| scenario | tool | model | wall_s | tok/s | ttft_s | rss_mb | ok | error |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|---|"
    )
    for r in runs:
        lines.append(
            f"| {r.scenario} | {r.tool} | {r.model} | {r.wall_seconds:.2f} | "
            f"{r.completion_tok_per_sec:.2f} | {r.ttft_seconds:.2f} | "
            f"{r.rss_peak_mb:.0f} | {r.ok} | {r.error or ''} |"
        )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
```

- [ ] **Step 2: Run tests, confirm they pass**

Run:

```
pytest tests/benchmarks/test_report.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 3: Commit**

```
git add benchmarks/report.py tests/benchmarks/test_report.py
git commit -m "feat(benchmarks): CSV and Markdown report writers"
```

---

### Task 11: Scenario base + S1 text-only — failing tests

**Files:**
- Test: `tests/benchmarks/test_scenarios.py`

- [ ] **Step 1: Write `tests/benchmarks/test_scenarios.py`**

Exact content:

```python
"""Tests for benchmark scenarios."""
from __future__ import annotations

from unittest.mock import MagicMock

from benchmarks.scenarios.base import ScenarioResult
from benchmarks.scenarios.s1_text_only import S1TextOnly


def test_s1_text_only_runs_once_and_returns_metrics():
    fake_adapter = MagicMock()
    fake_adapter.chat_text.return_value = MagicMock(
        content="abc",
        prompt_tokens=5,
        completion_tokens=3,
        wall_seconds=0.5,
    )
    scenario = S1TextOnly(
        tool="ollama", model="qwen2.5-vl:7b", n_runs=1
    )
    result = scenario.run(fake_adapter)
    assert isinstance(result, ScenarioResult)
    assert result.scenario_name == "s1"
    assert len(result.runs) == 1
    assert result.runs[0].ok is True
    assert result.runs[0].completion_tokens == 3


def test_s1_text_only_captures_error_and_marks_not_ok():
    fake_adapter = MagicMock()
    fake_adapter.chat_text.side_effect = RuntimeError("boom")
    scenario = S1TextOnly(
        tool="ollama", model="qwen2.5-vl:7b", n_runs=1
    )
    result = scenario.run(fake_adapter)
    assert result.runs[0].ok is False
    assert result.runs[0].error == "boom"


def test_s1_text_only_respects_n_runs():
    fake_adapter = MagicMock()
    fake_adapter.chat_text.return_value = MagicMock(
        content="abc",
        prompt_tokens=5,
        completion_tokens=3,
        wall_seconds=0.5,
    )
    scenario = S1TextOnly(
        tool="ollama", model="qwen2.5-vl:7b", n_runs=3
    )
    result = scenario.run(fake_adapter)
    assert len(result.runs) == 3
    assert fake_adapter.chat_text.call_count == 3
```

- [ ] **Step 2: Run tests, confirm they fail**

Run:

```
pytest tests/benchmarks/test_scenarios.py -v
```

Expected: 3 tests ERROR with `ModuleNotFoundError`.

---

### Task 12: Scenario base + S1 text-only — implementation

**Files:**
- Create: `benchmarks/scenarios/base.py`
- Create: `benchmarks/scenarios/s1_text_only.py`

- [ ] **Step 1: Write `benchmarks/scenarios/base.py`**

Exact content:

```python
"""Base classes for benchmark scenarios."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from benchmarks.metrics import RunMetrics


class ChatAdapter(Protocol):
    def chat_text(self, prompt: str): ...  # noqa: E704
    def chat_vision(self, prompt: str, image_bytes: bytes, mime_type: str): ...  # noqa: E704


@dataclass(frozen=True)
class ScenarioResult:
    scenario_name: str
    tool: str
    model: str
    runs: list[RunMetrics] = field(default_factory=list)
```

- [ ] **Step 2: Write `benchmarks/scenarios/s1_text_only.py`**

Exact content:

```python
"""Scenario S1: text-only short prompt, baseline latency/throughput."""
from __future__ import annotations

from dataclasses import dataclass

from benchmarks.metrics import RunMetrics
from benchmarks.scenarios.base import ChatAdapter, ScenarioResult

_PROMPT = (
    "Translate the following Japanese sentence to English in one line: "
    "今日は良い天気ですね。"
)


@dataclass
class S1TextOnly:
    tool: str
    model: str
    n_runs: int = 3

    def run(self, adapter: ChatAdapter) -> ScenarioResult:
        runs: list[RunMetrics] = []
        for _ in range(self.n_runs):
            try:
                result = adapter.chat_text(_PROMPT)
                runs.append(RunMetrics(
                    scenario="s1",
                    tool=self.tool,
                    model=self.model,
                    wall_seconds=result.wall_seconds,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    ttft_seconds=0.0,  # non-streaming: TTFT not measured here
                    rss_peak_mb=0.0,   # populated by harness via psutil
                    cpu_percent_avg=0.0,
                    ok=True,
                    error=None,
                ))
            except Exception as exc:  # noqa: BLE001
                runs.append(RunMetrics(
                    scenario="s1",
                    tool=self.tool,
                    model=self.model,
                    wall_seconds=0.0,
                    prompt_tokens=0,
                    completion_tokens=0,
                    ttft_seconds=0.0,
                    rss_peak_mb=0.0,
                    cpu_percent_avg=0.0,
                    ok=False,
                    error=str(exc),
                ))
        return ScenarioResult(
            scenario_name="s1",
            tool=self.tool,
            model=self.model,
            runs=runs,
        )
```

- [ ] **Step 3: Run tests, confirm they pass**

Run:

```
pytest tests/benchmarks/test_scenarios.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 4: Commit**

```
git add benchmarks/scenarios/base.py benchmarks/scenarios/s1_text_only.py tests/benchmarks/test_scenarios.py
git commit -m "feat(benchmarks): scenario base + S1 text-only"
```

---

### Task 13: S2 vision-single scenario — failing test

**Files:**
- Modify: `tests/benchmarks/test_scenarios.py`

- [ ] **Step 1: Append these tests to `tests/benchmarks/test_scenarios.py`**

Append at the end of the file:

```python

from benchmarks.scenarios.s2_vision_single import S2VisionSingle


def test_s2_vision_single_invokes_vision_chat():
    fake_adapter = MagicMock()
    fake_adapter.chat_vision.return_value = MagicMock(
        content="an image of a diagram",
        prompt_tokens=200,
        completion_tokens=80,
        wall_seconds=3.5,
    )
    scenario = S2VisionSingle(
        tool="ollama",
        model="qwen2.5-vl:7b",
        image_bytes=b"\x89PNG\r\n\x1a\nfake",
        mime_type="image/png",
        n_runs=2,
    )
    result = scenario.run(fake_adapter)
    assert result.scenario_name == "s2"
    assert len(result.runs) == 2
    assert fake_adapter.chat_vision.call_count == 2
    assert result.runs[0].completion_tokens == 80


def test_s2_vision_single_requires_non_empty_image():
    import pytest as _pt
    with _pt.raises(ValueError, match="image_bytes"):
        S2VisionSingle(
            tool="ollama",
            model="qwen2.5-vl:7b",
            image_bytes=b"",
            mime_type="image/png",
        )
```

- [ ] **Step 2: Run tests, confirm new ones fail**

Run:

```
pytest tests/benchmarks/test_scenarios.py::test_s2_vision_single_invokes_vision_chat tests/benchmarks/test_scenarios.py::test_s2_vision_single_requires_non_empty_image -v
```

Expected: 2 ERRORs with `ModuleNotFoundError` for `s2_vision_single`.

---

### Task 14: S2 vision-single scenario — implementation

**Files:**
- Create: `benchmarks/scenarios/s2_vision_single.py`

- [ ] **Step 1: Write `benchmarks/scenarios/s2_vision_single.py`**

Exact content:

```python
"""Scenario S2: describe a single image, measuring vision encoder cost."""
from __future__ import annotations

from dataclasses import dataclass

from benchmarks.metrics import RunMetrics
from benchmarks.scenarios.base import ChatAdapter, ScenarioResult

_PROMPT = (
    "この画像を構造的に記述してください。"
    "含まれるテキスト（OCR）・図の構造・色とレイアウト・主要な視覚要素を"
    "網羅し、日本語で詳細に出力してください。"
)


@dataclass
class S2VisionSingle:
    tool: str
    model: str
    image_bytes: bytes
    mime_type: str
    n_runs: int = 3

    def __post_init__(self) -> None:
        if not self.image_bytes:
            raise ValueError("image_bytes must be non-empty")

    def run(self, adapter: ChatAdapter) -> ScenarioResult:
        runs: list[RunMetrics] = []
        for _ in range(self.n_runs):
            try:
                result = adapter.chat_vision(
                    prompt=_PROMPT,
                    image_bytes=self.image_bytes,
                    mime_type=self.mime_type,
                )
                runs.append(RunMetrics(
                    scenario="s2",
                    tool=self.tool,
                    model=self.model,
                    wall_seconds=result.wall_seconds,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    ttft_seconds=0.0,
                    rss_peak_mb=0.0,
                    cpu_percent_avg=0.0,
                    ok=True,
                    error=None,
                ))
            except Exception as exc:  # noqa: BLE001
                runs.append(RunMetrics(
                    scenario="s2",
                    tool=self.tool,
                    model=self.model,
                    wall_seconds=0.0,
                    prompt_tokens=0,
                    completion_tokens=0,
                    ttft_seconds=0.0,
                    rss_peak_mb=0.0,
                    cpu_percent_avg=0.0,
                    ok=False,
                    error=str(exc),
                ))
        return ScenarioResult(
            scenario_name="s2",
            tool=self.tool,
            model=self.model,
            runs=runs,
        )
```

- [ ] **Step 2: Run tests, confirm they pass**

Run:

```
pytest tests/benchmarks/test_scenarios.py -v
```

Expected: all 5 scenario tests PASS.

- [ ] **Step 3: Commit**

```
git add benchmarks/scenarios/s2_vision_single.py tests/benchmarks/test_scenarios.py
git commit -m "feat(benchmarks): S2 vision-single scenario"
```

---

### Task 15: S3 vision-pptx-batch scenario — failing test

**Files:**
- Modify: `tests/benchmarks/test_scenarios.py`

- [ ] **Step 1: Append these tests to `tests/benchmarks/test_scenarios.py`**

Append at the end:

```python

from benchmarks.scenarios.s3_vision_pptx_batch import S3VisionPptxBatch


def test_s3_vision_pptx_batch_runs_once_per_image():
    fake_adapter = MagicMock()
    fake_adapter.chat_vision.return_value = MagicMock(
        content="ok",
        prompt_tokens=200,
        completion_tokens=40,
        wall_seconds=2.0,
    )
    images = [
        (b"\x89PNG\r\n\x1a\na", "image/png"),
        (b"\x89PNG\r\n\x1a\nb", "image/png"),
        (b"\x89PNG\r\n\x1a\nc", "image/png"),
    ]
    scenario = S3VisionPptxBatch(
        tool="ollama",
        model="qwen2.5-vl:7b",
        images=images,
    )
    result = scenario.run(fake_adapter)
    assert result.scenario_name == "s3"
    assert len(result.runs) == 3
    assert fake_adapter.chat_vision.call_count == 3


def test_s3_vision_pptx_batch_requires_at_least_one_image():
    import pytest as _pt
    with _pt.raises(ValueError, match="images"):
        S3VisionPptxBatch(
            tool="ollama",
            model="qwen2.5-vl:7b",
            images=[],
        )
```

- [ ] **Step 2: Run tests, confirm new ones fail**

Run:

```
pytest tests/benchmarks/test_scenarios.py -v
```

Expected: 2 new tests ERROR with `ModuleNotFoundError`.

---

### Task 16: S3 vision-pptx-batch scenario — implementation

**Files:**
- Create: `benchmarks/scenarios/s3_vision_pptx_batch.py`

- [ ] **Step 1: Write `benchmarks/scenarios/s3_vision_pptx_batch.py`**

Exact content:

```python
"""Scenario S3: describe a sequence of images (simulating a pptx batch)."""
from __future__ import annotations

from dataclasses import dataclass, field

from benchmarks.metrics import RunMetrics
from benchmarks.scenarios.base import ChatAdapter, ScenarioResult

_PROMPT = (
    "この画像を構造的に記述してください。"
    "含まれるテキスト（OCR）・図の構造・色とレイアウト・主要な視覚要素を"
    "網羅し、日本語で詳細に出力してください。"
)


@dataclass
class S3VisionPptxBatch:
    tool: str
    model: str
    images: list[tuple[bytes, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.images:
            raise ValueError("images must be non-empty")

    def run(self, adapter: ChatAdapter) -> ScenarioResult:
        runs: list[RunMetrics] = []
        for image_bytes, mime_type in self.images:
            try:
                result = adapter.chat_vision(
                    prompt=_PROMPT,
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                )
                runs.append(RunMetrics(
                    scenario="s3",
                    tool=self.tool,
                    model=self.model,
                    wall_seconds=result.wall_seconds,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    ttft_seconds=0.0,
                    rss_peak_mb=0.0,
                    cpu_percent_avg=0.0,
                    ok=True,
                    error=None,
                ))
            except Exception as exc:  # noqa: BLE001
                runs.append(RunMetrics(
                    scenario="s3",
                    tool=self.tool,
                    model=self.model,
                    wall_seconds=0.0,
                    prompt_tokens=0,
                    completion_tokens=0,
                    ttft_seconds=0.0,
                    rss_peak_mb=0.0,
                    cpu_percent_avg=0.0,
                    ok=False,
                    error=str(exc),
                ))
        return ScenarioResult(
            scenario_name="s3",
            tool=self.tool,
            model=self.model,
            runs=runs,
        )
```

- [ ] **Step 2: Run tests, confirm all pass**

Run:

```
pytest tests/benchmarks/test_scenarios.py -v
```

Expected: all 7 scenario tests PASS.

- [ ] **Step 3: Commit**

```
git add benchmarks/scenarios/s3_vision_pptx_batch.py tests/benchmarks/test_scenarios.py
git commit -m "feat(benchmarks): S3 vision-pptx-batch scenario"
```

---

### Task 17: Harness CLI

**Files:**
- Create: `benchmarks/harness.py`
- Create: `benchmarks/README.md`

- [ ] **Step 1: Write `benchmarks/harness.py`**

Exact content:

```python
"""CLI driver for benchmark scenarios.

Usage:
    python -m benchmarks.harness \
        --tool ollama \
        --model qwen2.5-vl:7b \
        --base-url http://127.0.0.1:11434/v1 \
        --scenario s1 \
        --n-runs 3 \
        --out-dir benchmarks/out

Vision scenarios additionally require --image (S2) or --pptx-dir (S3: directory
of .png/.jpg used as a simulated pptx batch).
"""
from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path

from benchmarks.adapter.openai_client import AdapterConfig, LocalLLMAdapter
from benchmarks.report import write_csv, write_markdown
from benchmarks.scenarios.base import ScenarioResult
from benchmarks.scenarios.s1_text_only import S1TextOnly
from benchmarks.scenarios.s2_vision_single import S2VisionSingle
from benchmarks.scenarios.s3_vision_pptx_batch import S3VisionPptxBatch

_SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime and mime.startswith("image/"):
        return mime
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }.get(path.suffix.lower(), "application/octet-stream")


def _build_scenario(args: argparse.Namespace):
    if args.scenario == "s1":
        return S1TextOnly(tool=args.tool, model=args.model, n_runs=args.n_runs)
    if args.scenario == "s2":
        if not args.image:
            raise SystemExit("--image is required for scenario s2")
        image_path = Path(args.image)
        return S2VisionSingle(
            tool=args.tool,
            model=args.model,
            image_bytes=image_path.read_bytes(),
            mime_type=_guess_mime(image_path),
            n_runs=args.n_runs,
        )
    if args.scenario == "s3":
        if not args.pptx_dir:
            raise SystemExit("--pptx-dir is required for scenario s3")
        pptx_dir = Path(args.pptx_dir)
        if not pptx_dir.is_dir():
            raise SystemExit(f"--pptx-dir '{pptx_dir}' is not a directory")
        images: list[tuple[bytes, str]] = []
        for entry in sorted(pptx_dir.iterdir()):
            if entry.is_file() and entry.suffix.lower() in _SUPPORTED_IMAGE_EXTS:
                images.append((entry.read_bytes(), _guess_mime(entry)))
        if not images:
            raise SystemExit(f"no supported images found under {pptx_dir}")
        return S3VisionPptxBatch(
            tool=args.tool, model=args.model, images=images
        )
    raise SystemExit(f"unknown scenario: {args.scenario}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local LLM benchmark harness")
    parser.add_argument("--tool", required=True, help="Candidate tool name tag")
    parser.add_argument("--model", required=True, help="Model id at the endpoint")
    parser.add_argument("--base-url", required=True, help="OpenAI-compat base URL")
    parser.add_argument("--scenario", required=True, choices=["s1", "s2", "s3"])
    parser.add_argument("--n-runs", type=int, default=3)
    parser.add_argument("--image", help="S2: path to image file")
    parser.add_argument("--pptx-dir", help="S3: directory of images")
    parser.add_argument(
        "--out-dir",
        default="benchmarks/out",
        help="Output directory for CSV and Markdown",
    )
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="Per-request timeout seconds"
    )
    args = parser.parse_args(argv)

    config = AdapterConfig(
        base_url=args.base_url,
        model=args.model,
        timeout_seconds=args.timeout,
    )
    adapter = LocalLLMAdapter(config)
    scenario = _build_scenario(args)
    result: ScenarioResult = scenario.run(adapter)

    out_dir = Path(args.out_dir)
    stem = f"{args.tool}_{args.scenario}_{args.model.replace(':', '-').replace('/', '-')}"
    csv_path = out_dir / f"{stem}.csv"
    md_path = out_dir / f"{stem}.md"
    write_csv(result.runs, csv_path)
    write_markdown(
        result.runs,
        md_path,
        title=f"{args.scenario.upper()} — {args.tool} / {args.model}",
    )
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")

    ok_count = sum(1 for r in result.runs if r.ok)
    if ok_count == 0:
        return 2
    if ok_count < len(result.runs):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Write `benchmarks/README.md`**

Exact content:

```markdown
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
```

- [ ] **Step 3: Verify the harness imports cleanly**

Run:

```
python -c "import benchmarks.harness; print('ok')"
```

Expected output: `ok`. Exit 0.

- [ ] **Step 4: Verify `--help` works**

Run:

```
python -m benchmarks.harness --help
```

Expected: argparse help text listing `--tool --model --base-url --scenario --n-runs --image --pptx-dir --out-dir --timeout`. Exit 0.

- [ ] **Step 5: Commit**

```
git add benchmarks/harness.py benchmarks/README.md
git commit -m "feat(benchmarks): harness CLI + README"
```

---

## Phase 5 — Prototype local LLM client (TDD)

### Task 18: Local LLM client — failing tests

**Files:**
- Test: `tests/lib/test_local_llm_client.py`

- [ ] **Step 1: Write `tests/lib/test_local_llm_client.py`**

Exact content:

```python
"""Tests for tools.lib.local_llm_client."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Tests run with tools/ on sys.path via conftest.py, so this import
# mirrors how describe_image.py imports from lib.
from lib.local_llm_client import (
    LocalLLMConfig,
    LocalLLMError,
    describe_image,
    load_config,
)


def test_load_config_reads_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LLM_BASE_URL=http://127.0.0.1:11434/v1\n"
        "LLM_MODEL=qwen2.5-vl:7b\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    cfg = load_config(tmp_path)
    assert isinstance(cfg, LocalLLMConfig)
    assert cfg.base_url == "http://127.0.0.1:11434/v1"
    assert cfg.model == "qwen2.5-vl:7b"


def test_load_config_missing_base_url_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    with pytest.raises(LocalLLMError, match="LLM_BASE_URL"):
        load_config(tmp_path)


def test_load_config_missing_model_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    with pytest.raises(LocalLLMError, match="LLM_MODEL"):
        load_config(tmp_path)


def test_describe_image_rejects_empty_bytes():
    cfg = LocalLLMConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    with pytest.raises(LocalLLMError, match="Empty"):
        describe_image(b"", "image/png", cfg)


def test_describe_image_returns_content_from_adapter():
    cfg = LocalLLMConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_adapter = MagicMock()
    fake_adapter.chat_vision.return_value = MagicMock(content="結果")
    with patch(
        "lib.local_llm_client.LocalLLMAdapter", return_value=fake_adapter
    ):
        out = describe_image(b"\x89PNG\r\n\x1a\nfake", "image/png", cfg)
    assert out == "結果"


def test_describe_image_wraps_adapter_errors():
    cfg = LocalLLMConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_adapter = MagicMock()
    fake_adapter.chat_vision.side_effect = RuntimeError("boom")
    with patch(
        "lib.local_llm_client.LocalLLMAdapter", return_value=fake_adapter
    ):
        with pytest.raises(LocalLLMError, match="boom"):
            describe_image(b"\x89PNG\r\n\x1a\nfake", "image/png", cfg)
```

- [ ] **Step 2: Run tests, confirm they fail**

Run:

```
pytest tests/lib/test_local_llm_client.py -v
```

Expected: all 6 tests ERROR with `ModuleNotFoundError: No module named 'lib.local_llm_client'`.

---

### Task 19: Local LLM client — implementation

**Files:**
- Create: `tools/lib/local_llm_client.py`

- [ ] **Step 1: Write `tools/lib/local_llm_client.py`**

Exact content:

```python
"""Local LLM client exposing the same describe_image interface as gemini_client.

Wraps benchmarks.adapter.openai_client.LocalLLMAdapter so that
tools/describe_image.py, tools/describe_pptx.py, and tools/describe_docx.py
can switch backend via LLM_BACKEND=gemini|local with no other code change.

Loads LLM_BASE_URL and LLM_MODEL from the workspace .env file (or environment).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Make benchmarks/ importable when running from tools/
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from benchmarks.adapter.openai_client import AdapterConfig, LocalLLMAdapter  # noqa: E402

DESCRIBE_PROMPT = (
    "この画像を構造的に記述してください。"
    "含まれる**テキスト内容**（OCR的に全て書き出す）、"
    "**図表・ダイアグラムの構造**（ノード・接続・階層）、"
    "**色とレイアウト**、"
    "**主要な視覚要素**を網羅し、日本語で詳細に出力してください。"
    "推測ではなく画像から直接読み取れる情報のみを記述してください。"
)


class LocalLLMError(RuntimeError):
    """Raised when the local LLM call fails or returns empty output."""


@dataclass(frozen=True)
class LocalLLMConfig:
    base_url: str
    model: str
    api_key: str = "not-needed"
    timeout_seconds: float = 120.0


def load_config(workspace_root: Path) -> LocalLLMConfig:
    env_path = workspace_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    if not base_url:
        raise LocalLLMError(
            f"LLM_BASE_URL not set. Expected in {env_path} or environment."
        )
    if not model:
        raise LocalLLMError(
            f"LLM_MODEL not set. Expected in {env_path} or environment."
        )
    api_key = os.environ.get("LLM_API_KEY", "not-needed")
    timeout_raw = os.environ.get("LLM_TIMEOUT_SECONDS", "120")
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 120.0
    return LocalLLMConfig(
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout_seconds=timeout,
    )


def describe_image(
    image_bytes: bytes, mime_type: str, config: LocalLLMConfig
) -> str:
    """Send one image to the local LLM and return a Japanese description.

    Mirrors gemini_client.describe_image's signature so describe_image.py etc.
    can swap implementations without other changes.

    Raises LocalLLMError on failure or empty response.
    """
    if not image_bytes:
        raise LocalLLMError("Empty image bytes")

    adapter_cfg = AdapterConfig(
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
    )
    adapter = LocalLLMAdapter(adapter_cfg)

    try:
        result = adapter.chat_vision(
            prompt=DESCRIBE_PROMPT,
            image_bytes=image_bytes,
            mime_type=mime_type,
        )
    except Exception as exc:  # noqa: BLE001
        raise LocalLLMError(f"Local LLM call failed: {exc}") from exc

    if not result.content.strip():
        raise LocalLLMError("Local LLM returned empty description")
    return result.content.strip()
```

- [ ] **Step 2: Run tests, confirm they pass**

Run:

```
pytest tests/lib/test_local_llm_client.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 3: Commit**

```
git add tools/lib/local_llm_client.py tests/lib/test_local_llm_client.py
git commit -m "feat(tools): local LLM client with Gemini-compatible describe_image"
```

---

### Task 20: Backend dispatcher in describe_image.py

**Files:**
- Modify: `tools/describe_image.py` (full replacement)

- [ ] **Step 1: Replace `tools/describe_image.py` with this complete final content**

```python
#!/usr/bin/env python
"""CLI: describe a single image file (png/jpg/webp/gif) via the configured backend.

Usage:
    python tools/describe_image.py <path>

Backend is selected by the LLM_BACKEND environment variable:
    LLM_BACKEND=gemini (default) — uses lib.gemini_client
    LLM_BACKEND=local            — uses lib.local_llm_client (OpenAI-compatible)

Writes Markdown description to stdout. Errors go to stderr with non-zero exit.
"""
from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

from lib.safe_path import UnsafePathError, resolve_safe

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}

_BACKEND = os.environ.get("LLM_BACKEND", "gemini").lower()


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime and mime.startswith("image/"):
        return mime
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }.get(ext, "application/octet-stream")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Describe an image file via configured LLM backend"
    )
    parser.add_argument("path", help="Path to image file (relative or absolute)")
    args = parser.parse_args()

    try:
        safe = resolve_safe(args.path, WORKSPACE_ROOT)
    except (UnsafePathError, FileNotFoundError, IsADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if safe.suffix.lower() not in SUPPORTED_EXT:
        print(
            f"ERROR: unsupported extension {safe.suffix!r}. "
            f"Supported: {sorted(SUPPORTED_EXT)}",
            file=sys.stderr,
        )
        return 3

    mime = _guess_mime(safe)
    image_bytes = safe.read_bytes()

    if _BACKEND == "local":
        from lib.local_llm_client import (
            LocalLLMError,
            describe_image as _describe,
            load_config as _load_config,
        )
        try:
            config = _load_config(WORKSPACE_ROOT)
            description = _describe(image_bytes, mime, config)
        except LocalLLMError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 5
        model_display = config.model
    else:
        from lib.gemini_client import (
            GeminiDescribeError,
            describe_image as _describe,
            load_config as _load_config,
        )
        try:
            config = _load_config(WORKSPACE_ROOT)
            description = _describe(image_bytes, mime, config)
        except GeminiDescribeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 5
        model_display = config.model

    rel_display = safe.relative_to(WORKSPACE_ROOT)
    print(f"# {rel_display} の記述")
    print(f"- mime: `{mime}`")
    print(f"- backend: `{_BACKEND}`")
    print(f"- model: `{model_display}`")
    print()
    print(description)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify --help still works**

Run:

```
python tools/describe_image.py --help
```

Expected: argparse help text listing `path` positional; exit 0.

- [ ] **Step 3: Verify default backend is still `gemini`**

Run:

```
python -c "import os; os.environ.pop('LLM_BACKEND', None); import sys; sys.path.insert(0, 'tools'); import importlib.util, pathlib; spec = importlib.util.spec_from_file_location('di', pathlib.Path('tools/describe_image.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print(m._BACKEND)"
```

Expected output: `gemini`. Exit 0.

- [ ] **Step 4: Commit**

```
git add tools/describe_image.py
git commit -m "feat(tools): describe_image dispatches on LLM_BACKEND"
```

---

### Task 21: Backend dispatcher in describe_pptx.py

**Files:**
- Modify: `tools/describe_pptx.py` (full replacement)

- [ ] **Step 1: Replace `tools/describe_pptx.py` with this complete final content**

```python
#!/usr/bin/env python
"""CLI: describe all embedded images in a .pptx file via the configured backend.

Usage:
    python tools/describe_pptx.py <path>
    python tools/describe_pptx.py <path> --slide 3
    python tools/describe_pptx.py <path> --slide 1-3,5

Backend is selected by LLM_BACKEND (gemini (default) | local).

Writes Markdown (one section per image) to stdout. Errors to stderr.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from lib.pptx_extractor import extract_images
from lib.safe_path import UnsafePathError, resolve_safe

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

_BACKEND = os.environ.get("LLM_BACKEND", "gemini").lower()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Describe embedded images in a pptx file via configured LLM backend"
    )
    parser.add_argument("path", help="Path to .pptx file")
    parser.add_argument(
        "--slide",
        default="all",
        help='Slide selector: "all" (default), "3", "1-3", "1,3,5", "1-3,5"',
    )
    args = parser.parse_args()

    try:
        safe = resolve_safe(args.path, WORKSPACE_ROOT)
    except (UnsafePathError, FileNotFoundError, IsADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if safe.suffix.lower() != ".pptx":
        print(
            f"ERROR: expected .pptx, got {safe.suffix!r}",
            file=sys.stderr,
        )
        return 3

    try:
        images = extract_images(safe, slide_range=args.slide)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to parse pptx: {exc}", file=sys.stderr)
        return 4

    rel_display = safe.relative_to(WORKSPACE_ROOT)
    print(f"# {rel_display} の埋め込み画像記述")
    print(f"- 対象スライド: `{args.slide}`")
    print(f"- 抽出画像数: {len(images)}")
    print(f"- backend: `{_BACKEND}`")
    print()

    if not images:
        print("（指定範囲に埋め込み画像が見つかりませんでした）")
        return 0

    if _BACKEND == "local":
        from lib.local_llm_client import (
            LocalLLMError as _BackendError,
            describe_image as _describe,
            load_config as _load_config,
        )
    else:
        from lib.gemini_client import (
            GeminiDescribeError as _BackendError,
            describe_image as _describe,
            load_config as _load_config,
        )

    try:
        config = _load_config(WORKSPACE_ROOT)
    except _BackendError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 5
    print(f"- model: `{config.model}`")
    print()

    failures = 0
    for img in images:
        print(f"## スライド {img.slide_index}, 画像 {img.image_index} (`{img.mime_type}`)")
        try:
            description = _describe(img.blob, img.mime_type, config)
            print(description)
        except _BackendError as exc:
            failures += 1
            print(f"_(記述失敗: {exc})_")
        print()

    return 0 if failures == 0 else 6


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify --help works**

Run:

```
python tools/describe_pptx.py --help
```

Expected: argparse help listing `path` and `--slide`; exit 0.

- [ ] **Step 3: Commit**

```
git add tools/describe_pptx.py
git commit -m "feat(tools): describe_pptx dispatches on LLM_BACKEND"
```

---

### Task 22: Backend dispatcher in describe_docx.py

**Files:**
- Modify: `tools/describe_docx.py` (full replacement)

- [ ] **Step 1: Replace `tools/describe_docx.py` with this complete final content**

```python
#!/usr/bin/env python
"""CLI: describe all embedded images in a .docx file via the configured backend.

Usage:
    python tools/describe_docx.py <path>

Backend is selected by LLM_BACKEND (gemini (default) | local).

Writes Markdown to stdout. Errors to stderr.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from lib.docx_extractor import extract_images
from lib.safe_path import UnsafePathError, resolve_safe

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

_BACKEND = os.environ.get("LLM_BACKEND", "gemini").lower()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Describe embedded images in a docx file via configured LLM backend"
    )
    parser.add_argument("path", help="Path to .docx file")
    args = parser.parse_args()

    try:
        safe = resolve_safe(args.path, WORKSPACE_ROOT)
    except (UnsafePathError, FileNotFoundError, IsADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if safe.suffix.lower() != ".docx":
        print(f"ERROR: expected .docx, got {safe.suffix!r}", file=sys.stderr)
        return 3

    try:
        images = extract_images(safe)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to parse docx: {exc}", file=sys.stderr)
        return 4

    rel_display = safe.relative_to(WORKSPACE_ROOT)
    print(f"# {rel_display} の埋め込み画像記述")
    print(f"- 抽出画像数: {len(images)}")
    print(f"- backend: `{_BACKEND}`")
    print()

    if not images:
        print("（埋め込み画像が見つかりませんでした）")
        return 0

    if _BACKEND == "local":
        from lib.local_llm_client import (
            LocalLLMError as _BackendError,
            describe_image as _describe,
            load_config as _load_config,
        )
    else:
        from lib.gemini_client import (
            GeminiDescribeError as _BackendError,
            describe_image as _describe,
            load_config as _load_config,
        )

    try:
        config = _load_config(WORKSPACE_ROOT)
    except _BackendError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 5
    print(f"- model: `{config.model}`")
    print()

    failures = 0
    for img in images:
        print(f"## 画像 {img.image_index} (`{img.mime_type}`, rel_id=`{img.rel_id}`)")
        try:
            description = _describe(img.blob, img.mime_type, config)
            print(description)
        except _BackendError as exc:
            failures += 1
            print(f"_(記述失敗: {exc})_")
        print()

    return 0 if failures == 0 else 6


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify --help works**

Run:

```
python tools/describe_docx.py --help
```

Expected: argparse help listing `path`; exit 0.

- [ ] **Step 3: Commit**

```
git add tools/describe_docx.py
git commit -m "feat(tools): describe_docx dispatches on LLM_BACKEND"
```

---

### Task 23: End-to-end gemini-backend smoke (non-regression)

**Files:** (no file changes — regression check only)

- [ ] **Step 1: Confirm GEMINI_API_KEY exists in environment or .env**

Run (PowerShell):

```
python -c "import os; from pathlib import Path; from dotenv import load_dotenv; load_dotenv(Path('.env')); print('GEMINI_API_KEY set:', bool(os.environ.get('GEMINI_API_KEY')))"
```

Expected output includes `GEMINI_API_KEY set: True`. If False: skip this task and note it; the regression check cannot proceed without the key. Record in commit message.

- [ ] **Step 2: Run describe_image against samples/diagram.png with gemini backend (default)**

Run:

```
python tools/describe_image.py samples/diagram.png
```

Expected: exit 0, stdout includes lines `# samples/diagram.png の記述`, `- backend: ` `gemini`, `- model: gemini-2.5-flash` (or whatever `GEMINI_MODEL` is), followed by Japanese Markdown description.

- [ ] **Step 3: If Step 2 passed, confirm full test suite passes**

Run:

```
pytest -v
```

Expected: all previously written unit tests PASS; no regressions.

- [ ] **Step 4: Commit a regression note in `benchmarks/README.md`**

Append to `benchmarks/README.md`:

```

## Regression baseline

Phase 5 preserves `LLM_BACKEND=gemini` (default) as the working configuration.
The Gemini path was smoke-tested against `samples/diagram.png` at the end of
Phase 5 implementation and produced valid Japanese Markdown output — see the
Phase 5 commit log.
```

Commit:

```
git add benchmarks/README.md
git commit -m "docs(benchmarks): note Phase 5 gemini regression baseline"
```

---

## Wrap-up: Final verification

### Task 24: Full suite green + repo tidy

**Files:** (no changes)

- [ ] **Step 1: Full test run**

Run:

```
pytest -v
```

Expected: 100% PASS, 0 FAIL, 0 ERROR.

- [ ] **Step 2: Check no stray artifacts in git**

Run:

```
git status
```

Expected: `nothing to commit, working tree clean`.

- [ ] **Step 3: View commit log**

Run:

```
git log --oneline --since="2026-04-15"
```

Expected: ~15–22 commits covering Tasks 1–23.

- [ ] **Step 4: Announce completion**

The plan's scope (Phase 0 + Phase 1 template + Phase 2 + Phase 5) is now code-complete and test-green. Next step: **execute Phase 1** (fill in `docs/report/local-llm/01-tool-matrix.md` via hands-on desk research), then write the second implementation plan covering Phase 3/4/6/7 based on the shortlist that Phase 1 produces.

---

## What's next (not in this plan)

The following phases are execution/measurement/reporting and need a second implementation plan, written after Phase 1's tool matrix is populated:

- **Phase 1 execution** — fill in `docs/report/local-llm/01-tool-matrix.md` via desk research (hands-on, no code)
- **Phase 3** — install each shortlist tool, run S1/S2/S3 benchmarks, record results. Concrete tasks (tool install commands, version-specific flags) depend on the shortlist, so they can't be fully specified until Phase 1 finishes
- **Phase 4** — model cross-evaluation on the Phase 3 winner
- **Phase 6** — target mini-PC validation run
- **Phase 7** — final integrated report

These will be captured in `docs/superpowers/plans/YYYY-MM-DD-local-llm-appliance-phase3-4-6-7.md` after Phase 1 completes.
