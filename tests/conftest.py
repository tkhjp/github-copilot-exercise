"""Shared pytest fixtures for benchmarks and local LLM client tests.

Path setup is handled by ``[tool.pytest.ini_options] pythonpath`` in
pyproject.toml, which pytest 8+ applies before test collection. No sys.path
manipulation is needed here.
"""
from __future__ import annotations
