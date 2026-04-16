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
    """Result of one chat call.

    wall_seconds measures the server round-trip only — bracketing the
    chat.completions.create call. It excludes OpenAI() client construction
    (one-time cost in __init__) and post-response attribute access, so it
    feeds tokens/sec throughput calculations cleanly.

    prompt_tokens / completion_tokens are 0 when the backend does not report
    usage (some OpenAI-compatible servers omit the field). Callers that need
    to distinguish "zero tokens consumed" from "unreported" should upgrade
    to Optional[int] at that point — the adapter currently chooses silent-0
    because no downstream consumer (benchmarks, Phase 5 prototype) reads
    tokens for anything other than telemetry.
    """
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
            # Strict on content: empty or whitespace-only is always useless for
            # benchmarking and for the image-describer use case.
            raise RuntimeError(
                f"Backend {self._config.base_url} returned empty content"
            )
        # Lenient on usage: some backends (llama.cpp --api mode, older LM Studio)
        # omit the usage block entirely. Default to 0 rather than raise — tokens
        # are telemetry, not correctness.
        usage = response.usage
        return ChatResult(
            content=content,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            wall_seconds=wall,
        )
