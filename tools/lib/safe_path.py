"""Path safety: resolve user-supplied paths and reject traversal outside workspace."""
from __future__ import annotations

from pathlib import Path


class UnsafePathError(ValueError):
    """Raised when a supplied path escapes the allowed workspace root."""


def resolve_safe(user_path: str, workspace_root: Path) -> Path:
    """Resolve `user_path` against `workspace_root` and ensure it stays inside.

    Accepts both absolute and workspace-relative input. Follows symlinks via
    `Path.resolve()`. Raises `UnsafePathError` if the resolved path escapes
    the workspace, or `FileNotFoundError` if the file does not exist.
    """
    root = workspace_root.resolve()
    candidate = Path(user_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError(
            f"Path escapes workspace root: {user_path!r} -> {resolved}"
        ) from exc

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")
    if not resolved.is_file():
        raise IsADirectoryError(f"Expected a file, got directory: {resolved}")

    return resolved
