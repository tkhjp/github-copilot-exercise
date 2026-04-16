"""Shared prompt text for image-description backends.

Both tools/lib/gemini_client.py and tools/lib/local_llm_client.py import
DESCRIBE_PROMPT from here. Keeping the prompt in one place ensures that
benchmarks comparing the two backends use identical instructions, so any
output-quality difference is attributable to the model (not prompt drift).
"""
from __future__ import annotations

DESCRIBE_PROMPT = (
    "この画像を構造的に記述してください。"
    "含まれる**テキスト内容**（OCR的に全て書き出す）、"
    "**図表・ダイアグラムの構造**（ノード・接続・階層）、"
    "**色とレイアウト**、"
    "**主要な視覚要素**を網羅し、日本語で詳細に出力してください。"
    "推測ではなく画像から直接読み取れる情報のみを記述してください。"
)
