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


def render_p02(out_path: Path) -> None:
    """P2: Before/After 比較 — 2 つの検索画面 SS を左右並べて差分矢印 3 本."""
    spec = SPEC["p02"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Two screenshot cards side by side.
    gap = 40
    card_w = (CANVAS_W - 3 * gap) // 2
    before = (gap, body_y + 10, gap + card_w, body_y + 660)
    after = (2 * gap + card_w, body_y + 10, 2 * gap + 2 * card_w, body_y + 660)

    for card, side_key in [(before, "before"), (after, "after")]:
        s = layout[side_key]
        _draw_screenshot_card(draw, card, title=s["title"])
        # Search bar
        sx1, sy = card[0] + 24, card[1] + 60
        draw.rectangle([sx1, sy, card[2] - 140, sy + 36],
                       fill=COLORS["bg"], outline=COLORS["card_border"], width=2)
        draw.text((sx1 + 10, sy + 10), s["search_placeholder"], fill=COLORS["muted"], font=_font(13))
        # Search button
        draw.rectangle([card[2] - 130, sy, card[2] - 24, sy + 36],
                       fill=COLORS["primary"], outline=COLORS["primary_dk"], width=2)
        bw, _ = _tsize(draw, s["button"], _bold_font(13))
        draw.text((card[2] - 77 - bw // 2, sy + 10), s["button"],
                  fill=COLORS["header_text"], font=_bold_font(13))
        # Filter rows (small boxes)
        fy = sy + 60
        for _i in range(s["filter_rows"]):
            draw.rectangle([sx1, fy, card[2] - 24, fy + 28],
                           fill=COLORS["card_bg"], outline=COLORS["card_border"])
            fy += 36
        # Results label
        draw.text((sx1, fy + 20), s["result_count_label"], fill=COLORS["text"], font=_font(13))
        # Pagination
        draw.text((sx1, fy + 60), s["pagination"], fill=COLORS["text"], font=_bold_font(14))

    # 3 red diff arrows with labels D1..D3. Targets: placeholder (both sides), filter area, pagination.
    diff_targets = [
        ((before[0] + 80, body_y + 86), (after[0] + 80, body_y + 86)),
        ((before[0] + 80, body_y + 140), (after[0] + 80, body_y + 180)),
        ((before[0] + 200, body_y + 520), (after[0] + 300, body_y + 520)),
    ]
    for i, (label, text) in enumerate(layout["diffs"]):
        y = CANVAS_H - 220 + i * 60
        # Label box below the cards
        draw.rectangle([40, y, 280, y + 44], fill=COLORS["danger_bg"], outline=COLORS["danger"], width=2)
        draw.text((50, y + 12), f"{label} {text}", fill=COLORS["danger_text"], font=_bold_font(13))
        # Short arrows from label to both before and after targets
        for target in diff_targets[i]:
            _arrow(draw, (280, y + 22), target, color=COLORS["danger"], width=2, head=10)

    img.save(out_path, "PNG")


def render_p03(out_path: Path) -> None:
    """P3: 工程フロー型 — 5 画面 SS を番号付き矢印で連結."""
    spec = SPEC["p03"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # 5 mini screenshots in a single row, connected by arrows.
    steps = layout["steps"]
    n = len(steps)
    margin = 40
    gap = 48
    card_w = (CANVAS_W - 2 * margin - (n - 1) * gap) // n
    card_h = 400
    y1 = body_y + 120
    y2 = y1 + card_h
    for i, (label, step_title, step_desc) in enumerate(steps):
        x1 = margin + i * (card_w + gap)
        x2 = x1 + card_w
        _draw_screenshot_card(draw, (x1, y1, x2, y2), title=step_title)
        # Body of card: wrap step_desc
        draw.text((x1 + 12, y1 + 48), step_desc, fill=COLORS["text"], font=_font(13))
        # Step label above card
        draw.rectangle([x1 + card_w // 2 - 24, y1 - 40, x1 + card_w // 2 + 24, y1 - 8],
                       fill=COLORS["primary"], outline=COLORS["primary_dk"], width=2)
        lw, _ = _tsize(draw, label, _bold_font(16))
        draw.text((x1 + card_w // 2 - lw // 2, y1 - 33), label,
                  fill=COLORS["header_text"], font=_bold_font(16))
        # Arrow to next card
        if i < n - 1:
            _arrow(draw, (x2 + 4, (y1 + y2) // 2),
                   (x2 + gap - 4, (y1 + y2) // 2),
                   color=COLORS["text"], width=3, head=14)

    img.save(out_path, "PNG")


def render_p04(out_path: Path) -> None:
    """P4: ダッシュボード + 解釈注釈 — 棒 + 円 + KPI 3 + 吹き出し 3."""
    spec = SPEC["p04"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Bar chart (top-left)
    bx1, by1 = 40, body_y + 40
    bx2, by2 = 640, by1 + 300
    _draw_screenshot_card(draw, (bx1, by1, bx2, by2), title=layout["bar_chart"]["title"])
    bars = layout["bar_chart"]["data"]
    max_v = max(v for _, v in bars)
    chart_top = by1 + 60
    chart_bot = by2 - 40
    chart_left = bx1 + 40
    chart_right = bx2 - 20
    draw.line([(chart_left, chart_bot), (chart_right, chart_bot)], fill=COLORS["text"], width=2)
    draw.line([(chart_left, chart_top), (chart_left, chart_bot)], fill=COLORS["text"], width=2)
    bar_area_w = chart_right - chart_left - 40
    bar_w = bar_area_w // (len(bars) * 2)
    for i, (lbl, v) in enumerate(bars):
        x = chart_left + 20 + i * (bar_w * 2)
        h = int((v / max_v) * (chart_bot - chart_top - 20))
        draw.rectangle([x, chart_bot - h, x + bar_w, chart_bot], fill=COLORS["primary"])
        draw.text((x, chart_bot - h - 18), str(v), fill=COLORS["text"], font=_font(12))
        draw.text((x + bar_w // 4, chart_bot + 6), lbl, fill=COLORS["text"], font=_font(12))

    # Pie chart (top-right) — rendered as wedges
    cx, cy, r = 1080, by1 + 160, 100
    pie = layout["pie_chart"]
    _draw_screenshot_card(draw, (800, by1, CANVAS_W - 40, by2), title=pie["title"])
    total = sum(v for _, v in pie["data"])
    start_angle = -90
    palette = [COLORS["primary"], COLORS["success"], COLORS["warn"], COLORS["muted"]]
    for i, (label, v) in enumerate(pie["data"]):
        sweep = (v / total) * 360
        draw.pieslice([cx - r, cy - r, cx + r, cy + r],
                      start=start_angle, end=start_angle + sweep,
                      fill=palette[i % len(palette)], outline=COLORS["bg"], width=2)
        # Label with % outside the wedge
        mid = math.radians(start_angle + sweep / 2)
        lx = cx + int((r + 30) * math.cos(mid))
        ly = cy + int((r + 30) * math.sin(mid))
        draw.text((lx - 20, ly - 8), f"{label} {v}%", fill=COLORS["text"], font=_font(12))
        start_angle += sweep

    # KPI cards (3 cards across bottom)
    kpi_y1 = by2 + 30
    kpi_y2 = kpi_y1 + 160
    kpi_w = (CANVAS_W - 2 * 40 - 2 * 20) // 3
    for i, (kpi_label, kpi_val, kpi_sub) in enumerate(layout["kpi_cards"]):
        kx1 = 40 + i * (kpi_w + 20)
        kx2 = kx1 + kpi_w
        _draw_screenshot_card(draw, (kx1, kpi_y1, kx2, kpi_y2))
        draw.text((kx1 + 16, kpi_y1 + 16), kpi_label, fill=COLORS["muted"], font=_bold_font(14))
        draw.text((kx1 + 16, kpi_y1 + 48), kpi_val, fill=COLORS["text"], font=_bold_font(28))
        draw.text((kx1 + 16, kpi_y1 + 100), kpi_sub, fill=COLORS["success"], font=_font(13))

    # 3 interpretive callouts on the right margin, each with a label (A1..A3)
    for i, (label, text) in enumerate(layout["annotations"]):
        ay = kpi_y2 + 20 + i * 44
        draw.rectangle([40, ay, CANVAS_W - 40, ay + 36],
                       fill=COLORS["danger_bg"], outline=COLORS["danger"], width=1)
        draw.text((52, ay + 8), f"{label} {text}", fill=COLORS["danger_text"], font=_bold_font(13))

    img.save(out_path, "PNG")


def render_png(pid: str, out_path: Path) -> None:
    """Dispatch table mapping pattern id → per-pattern renderer."""
    renderers = {
        "p01": render_p01,
        "p02": render_p02,
        "p03": render_p03,
        "p04": render_p04,
    }
    if pid not in renderers:
        raise NotImplementedError(f"render_png not yet implemented for {pid}")
    renderers[pid](out_path)
