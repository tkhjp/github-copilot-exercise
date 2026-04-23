#!/usr/bin/env python
"""Generate PPTX + 8 PNGs + ground_truth.yaml for the extraction prompt experiment.

Single command produces all artifacts consumed by Copilot Web trials:

    python tests/text_vs_image/extraction/generate_extraction.py

All content flows from `extraction_spec.SPEC`. To change a slide, edit the spec
and re-run this script.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from tests.text_vs_image.extraction.extraction_spec import SPEC, emit_ground_truth_yaml


ROOT = Path(__file__).resolve().parent
CANVAS_W, CANVAS_H = 1600, 900

# Shared visual palette (kept deliberately muted so callouts stand out).
COLORS = {
    "bg":          "#ffffff",
    "card_bg":     "#f9fafb",
    "card_border": "#d1d5db",
    "text":        "#111827",
    "muted":       "#6b7280",
    "header_bg":   "#1e293b",
    "header_text": "#ffffff",
    "primary":     "#2563eb",
    "primary_dk":  "#1e40af",
    "success":     "#16a34a",
    "warn":        "#e67e22",
    "danger":      "#dc2626",
    "danger_bg":   "#fef2f2",
    "danger_text": "#991b1b",
    "grid":        "#e5e7eb",
}


def _font(size: int) -> ImageFont.ImageFont:
    """Load a Japanese-capable font. Falls back gracefully if unavailable."""
    for path in [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _bold_font(size: int) -> ImageFont.ImageFont:
    for path in [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",  # same TTC as _font; index 1 is bold on macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size, index=1 if path.endswith(".ttc") else 0)
        except OSError:
            continue
    return _font(size)


def _mono_font(size: int) -> ImageFont.ImageFont:
    for path in ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf"]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _tsize(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _arrow(draw: ImageDraw.ImageDraw, p1, p2, color="black", width=2, head=12):
    draw.line([p1, p2], fill=color, width=width)
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    a1 = (p2[0] - head * math.cos(ang - math.radians(22)),
          p2[1] - head * math.sin(ang - math.radians(22)))
    a2 = (p2[0] - head * math.cos(ang + math.radians(22)),
          p2[1] - head * math.sin(ang + math.radians(22)))
    draw.polygon([p2, a1, a2], fill=color)


def _draw_screenshot_card(
    draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], *,
    title: str | None = None, title_font=None, body_font=None,
):
    """Draw a 'screenshot card' rectangle with an optional title bar and muted border.
    Body content is drawn by the caller by reading the spec and calling further primitives.
    """
    x1, y1, x2, y2 = rect
    draw.rectangle([x1, y1, x2, y2], fill=COLORS["card_bg"], outline=COLORS["card_border"], width=2)
    if title:
        tf = title_font or _bold_font(14)
        draw.rectangle([x1, y1, x2, y1 + 32], fill=COLORS["header_bg"])
        draw.text((x1 + 12, y1 + 8), title, fill=COLORS["header_text"], font=tf)


def _draw_callout(
    draw: ImageDraw.ImageDraw, *,
    box_rect: tuple[int, int, int, int],
    label: str,
    text: str,
    target: tuple[int, int],
    font=None,
    color=None,
    fill=None,
    text_color=None,
):
    """Red callout box with label (e.g. 'C1') + text + leader line to target point."""
    x1, y1, x2, y2 = box_rect
    f = font or _bold_font(13)
    color = color or COLORS["danger"]
    fill = fill or COLORS["danger_bg"]
    text_color = text_color or COLORS["danger_text"]
    draw.rectangle([x1, y1, x2, y2], fill=fill, outline=color, width=2)
    draw.text((x1 + 10, y1 + 8), f"{label} {text}", fill=text_color, font=f)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    _arrow(draw, (cx, cy), target, color=color, width=2, head=10)


def _new_canvas() -> Image.Image:
    return Image.new("RGB", (CANVAS_W, CANVAS_H), COLORS["bg"])


def _draw_slide_title(draw: ImageDraw.ImageDraw, title: str, subtitle: str | None = None) -> int:
    """Draw the slide title bar; return y-offset where body content can start."""
    draw.text((32, 22), title, fill=COLORS["text"], font=_bold_font(26))
    if subtitle:
        draw.text((32, 60), subtitle, fill=COLORS["muted"], font=_font(14))
    draw.line([(32, 86), (CANVAS_W - 32, 86)], fill=COLORS["grid"], width=2)
    return 100  # body starts here


# --- Per-pattern renderers (p01-p08). Each reads SPEC[pid]['layout'] and draws to an Image. ---

def render_p01(out_path: Path) -> None:
    """P1: UI/画面レビュー型 — 勤怠アプリ画面 SS + 赤矢印 4 本 + 吹き出し 4 個."""
    spec = SPEC["p01"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Screenshot card (left ~60% of canvas).
    card = (40, body_y + 10, 1000, body_y + 700)
    _draw_screenshot_card(draw, card, title=layout["app_title"])
    # Header inside card: user name (right-aligned inside header bar).
    hdr_user_w, _ = _tsize(draw, layout["header_user"], _font(13))
    draw.text((card[2] - hdr_user_w - 14, body_y + 18), layout["header_user"],
              fill=COLORS["header_text"], font=_font(13))

    # Table (5 columns, 4 rows).
    tbl_x1, tbl_y1 = card[0] + 24, body_y + 60
    col_widths = [190, 110, 110, 110, 140]
    row_h = 42
    # Header row
    hx = tbl_x1
    for ci, header in enumerate(layout["table_header"]):
        draw.rectangle([hx, tbl_y1, hx + col_widths[ci], tbl_y1 + row_h],
                       fill=COLORS["grid"], outline=COLORS["card_border"])
        draw.text((hx + 10, tbl_y1 + 12), header, fill=COLORS["text"], font=_bold_font(14))
        hx += col_widths[ci]
    # Data rows
    for r, row in enumerate(layout["table_rows"]):
        ry = tbl_y1 + row_h * (r + 1)
        rx = tbl_x1
        for ci, val in enumerate(row):
            draw.rectangle([rx, ry, rx + col_widths[ci], ry + row_h],
                           fill=COLORS["bg"], outline=COLORS["card_border"])
            draw.text((rx + 10, ry + 12), val, fill=COLORS["text"], font=_font(13))
            rx += col_widths[ci]
    # Action buttons
    btn_y = tbl_y1 + row_h * (len(layout["table_rows"]) + 1) + 24
    bx = tbl_x1
    for label in layout["buttons"]:
        w, _ = _tsize(draw, label, _bold_font(13))
        bw = w + 24
        draw.rectangle([bx, btn_y, bx + bw, btn_y + 32],
                       fill=COLORS["primary"], outline=COLORS["primary_dk"], width=2)
        draw.text((bx + 12, btn_y + 7), label, fill=COLORS["header_text"], font=_bold_font(13))
        bx += bw + 10

    # 4 red callouts on the right ~35% of canvas, each pointing at a region in the card.
    # Target coordinates are approximate anchors inside the card for each callout.
    targets = [
        (tbl_x1 + 600, tbl_y1 + row_h * 2 + row_h // 2),  # C1: row 2 (承認待)
        (tbl_x1 + 480, tbl_y1 + row_h * 3 + row_h // 2),  # C2: row 3 (要修正)
        (tbl_x1 + 80, btn_y + 16),                        # C3: エクスポートボタン
        (tbl_x1 + 90, tbl_y1 + 12),                       # C4: 日付列ヘッダ
    ]
    for i, (label, text) in enumerate(layout["callouts"]):
        bx1 = 1040
        by1 = body_y + 20 + i * 170
        _draw_callout(draw, box_rect=(bx1, by1, bx1 + 520, by1 + 110),
                      label=label, text=text, target=targets[i])

    img.save(out_path, "PNG")


def render_png(pid: str, out_path: Path) -> None:
    """Dispatch table mapping pattern id → per-pattern renderer."""
    renderers = {
        "p01": render_p01,
        # p02..p08 added in later tasks.
    }
    if pid not in renderers:
        raise NotImplementedError(f"render_png not yet implemented for {pid}")
    renderers[pid](out_path)
