"""Extract embedded images from .docx files via related parts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx import Document


@dataclass(frozen=True)
class ExtractedDocxImage:
    image_index: int  # 1-based, in document part order
    blob: bytes
    mime_type: str
    rel_id: str


def extract_images(docx_path: Path) -> list[ExtractedDocxImage]:
    """Return all image parts referenced by the main document part."""
    document = Document(str(docx_path))
    main_part = document.part
    out: list[ExtractedDocxImage] = []
    counter = 0
    for rel_id, rel in main_part.rels.items():
        if "image" not in rel.reltype:
            continue
        target = rel.target_part
        content_type = target.content_type
        if not content_type.startswith("image/"):
            continue
        counter += 1
        out.append(
            ExtractedDocxImage(
                image_index=counter,
                blob=target.blob,
                mime_type=content_type,
                rel_id=rel_id,
            )
        )
    return out
