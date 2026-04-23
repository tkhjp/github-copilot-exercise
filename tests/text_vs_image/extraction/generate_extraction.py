#!/usr/bin/env python
"""Generate PPTX + 8 PNGs + ground_truth.yaml for the extraction prompt experiment.

Single command produces all artifacts consumed by Copilot Web trials:

    python tests/text_vs_image/extraction/generate_extraction.py

All content flows from `extraction_spec.SPEC`. To change a slide, edit the spec
and re-run this script.
"""
from __future__ import annotations

import math
import textwrap
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

    gap = 40
    card_w = (CANVAS_W - 3 * gap) // 2
    card_bottom = body_y + 540  # shrunk from 660 so D1/D2/D3 labels fit cleanly below
    before = (gap, body_y + 10, gap + card_w, card_bottom)
    after = (2 * gap + card_w, body_y + 10, 2 * gap + 2 * card_w, card_bottom)

    # Capture anchors while drawing so diff arrows land on actual element positions.
    anchors: dict[str, dict[str, tuple[int, int]]] = {}
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
        # Filter rows
        fy_start = sy + 60
        fy = fy_start
        for _i in range(s["filter_rows"]):
            draw.rectangle([sx1, fy, card[2] - 24, fy + 28],
                           fill=COLORS["card_bg"], outline=COLORS["card_border"])
            fy += 36
        # Results label
        results_y = fy + 20
        draw.text((sx1, results_y), s["result_count_label"], fill=COLORS["text"], font=_font(13))
        # Pagination
        pagination_y = fy + 60
        draw.text((sx1, pagination_y), s["pagination"], fill=COLORS["text"], font=_bold_font(14))

        # Save anchors for diff arrows (D1→placeholder, D2→filters, D3→pagination)
        anchors[side_key] = {
            "placeholder": (sx1 + 80, sy + 18),
            "filters":     (sx1 + 80, fy_start + 14),
            "pagination":  (sx1 + 80, pagination_y + 10),
        }

    # 3 red diff labels + dual arrows from label to both sides' corresponding anchors.
    diff_targets = [
        (anchors["before"]["placeholder"], anchors["after"]["placeholder"]),
        (anchors["before"]["filters"],     anchors["after"]["filters"]),
        (anchors["before"]["pagination"],  anchors["after"]["pagination"]),
    ]
    for i, (label, text) in enumerate(layout["diffs"]):
        y = card_bottom + 30 + i * 60  # cleanly below cards now
        draw.rectangle([40, y, 280, y + 44], fill=COLORS["danger_bg"], outline=COLORS["danger"], width=2)
        draw.text((50, y + 12), f"{label} {text}", fill=COLORS["danger_text"], font=_bold_font(13))
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
        # Body of card: wrap step_desc to fit narrow card width
        wrapped = textwrap.fill(step_desc, width=14)
        draw.text((x1 + 12, y1 + 48), wrapped, fill=COLORS["text"], font=_font(13))
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

    # 3 interpretive callout rows across the bottom (A1..A3) — full-width red strips
    for i, (label, text) in enumerate(layout["annotations"]):
        ay = kpi_y2 + 20 + i * 44
        draw.rectangle([40, ay, CANVAS_W - 40, ay + 36],
                       fill=COLORS["danger_bg"], outline=COLORS["danger"], width=1)
        draw.text((52, ay + 8), f"{label} {text}", fill=COLORS["danger_text"], font=_bold_font(13))

    img.save(out_path, "PNG")


def render_p05(out_path: Path) -> None:
    """P5: 階層ドリルダウン — 上: 5 モジュール全体図 / 下: 決済コア拡大 + 設定表."""
    spec = SPEC["p05"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Top band: 5 modules side by side. Highlighted one has a different border.
    modules = layout["top_level_modules"]
    highlighted = layout["highlighted_module"]
    n = len(modules)
    mod_y1 = body_y + 20
    mod_y2 = mod_y1 + 120
    mod_w = (CANVAS_W - 2 * 40 - (n - 1) * 20) // n
    hi_idx = next(i for i, name in enumerate(modules) if name == highlighted)
    for i, name in enumerate(modules):
        mx1 = 40 + i * (mod_w + 20)
        mx2 = mx1 + mod_w
        is_hi = (name == highlighted)
        draw.rectangle(
            [mx1, mod_y1, mx2, mod_y2],
            fill=COLORS["card_bg"],
            outline=COLORS["danger"] if is_hi else COLORS["card_border"],
            width=3 if is_hi else 2,
        )
        nw, _ = _tsize(draw, name, _bold_font(15))
        draw.text((mx1 + (mod_w - nw) // 2, mod_y1 + 50), name,
                  fill=COLORS["text"], font=_bold_font(15))

    # Drilldown arrow from highlighted module to zoomed area below
    hi_cx = 40 + hi_idx * (mod_w + 20) + mod_w // 2
    _arrow(draw, (hi_cx, mod_y2 + 4), (CANVAS_W // 2, mod_y2 + 60),
           color=COLORS["danger"], width=3, head=14)

    # Zoomed submodules (left half, grid of 2x2)
    zoom_y1 = mod_y2 + 80
    zoom_y2 = zoom_y1 + 380
    _draw_screenshot_card(draw, (40, zoom_y1, 700, zoom_y2),
                          title=f"拡大: {highlighted}")
    sub = layout["zoom_submodules"]
    for i, name in enumerate(sub):
        r, c = divmod(i, 2)
        sx1 = 80 + c * 290
        sy1 = zoom_y1 + 60 + r * 130
        draw.rectangle([sx1, sy1, sx1 + 260, sy1 + 100],
                       fill=COLORS["bg"], outline=COLORS["card_border"], width=2)
        nw, _ = _tsize(draw, name, _bold_font(14))
        draw.text((sx1 + (260 - nw) // 2, sy1 + 40), name,
                  fill=COLORS["text"], font=_bold_font(14))

    # Config table (right half)
    tbl_x1, tbl_y1 = 740, zoom_y1
    tbl_x2, tbl_y2 = CANVAS_W - 40, zoom_y2
    _draw_screenshot_card(draw, (tbl_x1, tbl_y1, tbl_x2, tbl_y2), title="設定パラメータ")
    cfg = layout["config_table"]
    col_widths = [320, 200, 200]
    hx = tbl_x1 + 12
    hy = tbl_y1 + 60
    # Header
    for ci, col in enumerate(cfg["columns"]):
        draw.rectangle([hx, hy, hx + col_widths[ci], hy + 36],
                       fill=COLORS["grid"], outline=COLORS["card_border"])
        draw.text((hx + 8, hy + 10), col, fill=COLORS["text"], font=_bold_font(14))
        hx += col_widths[ci]
    # Rows
    for r, row in enumerate(cfg["rows"]):
        rx = tbl_x1 + 12
        ry = hy + 36 * (r + 1)
        for ci, val in enumerate(row):
            draw.rectangle([rx, ry, rx + col_widths[ci], ry + 36],
                           fill=COLORS["bg"], outline=COLORS["card_border"])
            draw.text((rx + 8, ry + 10), val, fill=COLORS["text"], font=_font(13))
            rx += col_widths[ci]

    img.save(out_path, "PNG")


def render_p06(out_path: Path) -> None:
    """P6: レビュー反映 (赤入れ) — モック 1 + 15 個の赤コメント + 指示線."""
    spec = SPEC["p06"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Left: mockup placeholder with 6 stacked sections (labels only, for the judge to read).
    mock_x1, mock_y1 = 40, body_y + 10
    mock_x2, mock_y2 = 780, body_y + 720
    _draw_screenshot_card(draw, (mock_x1, mock_y1, mock_x2, mock_y2), title="ダッシュボード モックアップ")
    sections = layout["mockup_sections"]
    sec_h = (mock_y2 - mock_y1 - 32) // len(sections)
    for i, sec in enumerate(sections):
        sy1 = mock_y1 + 32 + i * sec_h
        sy2 = sy1 + sec_h - 4
        draw.rectangle([mock_x1 + 16, sy1, mock_x2 - 16, sy2],
                       fill=COLORS["bg"], outline=COLORS["card_border"], width=1)
        draw.text((mock_x1 + 28, sy1 + 12), sec, fill=COLORS["text"], font=_bold_font(14))

    # Right: 15 review comment bubbles, two-column layout.
    comments = layout["comments"]
    comment_x1 = 800
    comment_w = (CANVAS_W - comment_x1 - 40 - 10) // 2
    # First comment per mockup section (one representative leader arrow per section, not 15).
    section_anchor_first_i: dict[int, int] = {}
    for i, _ in enumerate(comments):
        sec_idx = i % len(sections)
        section_anchor_first_i.setdefault(sec_idx, i)
    anchor_is = set(section_anchor_first_i.values())

    for i, (label, text) in enumerate(comments):
        col = i % 2
        row = i // 2
        cx1 = comment_x1 + col * (comment_w + 10)
        cy1 = body_y + 20 + row * 90
        draw.rectangle([cx1, cy1, cx1 + comment_w, cy1 + 78],
                       fill=COLORS["danger_bg"], outline=COLORS["danger"], width=2)
        draw.text((cx1 + 10, cy1 + 8), label, fill=COLORS["danger_text"], font=_bold_font(13))
        # Wrap text to fit comment width (replaces manual text[:40]/text[40:80] slicing).
        wrapped = textwrap.fill(text, width=18, max_lines=2, placeholder="…")
        draw.text((cx1 + 10, cy1 + 32), wrapped, fill=COLORS["danger_text"], font=_font(12))
        # Draw a leader arrow only for the first comment that maps to each section,
        # keeping fact p06_f19 satisfied without spaghetti visuals.
        if i in anchor_is:
            target_section_idx = i % len(sections)
            target_y = mock_y1 + 32 + target_section_idx * sec_h + sec_h // 2
            _arrow(draw, (cx1, cy1 + 40), (mock_x2, target_y),
                   color=COLORS["danger"], width=1, head=6)

    img.save(out_path, "PNG")


def render_p07(out_path: Path) -> None:
    """P7: 混合ダッシュボードページ — 表 + 棒グラフ + SS + コード + 箇条書き."""
    spec = SPEC["p07"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Top-left: table
    tbl = layout["table"]
    tx1, ty1 = 40, body_y + 20
    tx2, ty2 = 820, body_y + 380
    _draw_screenshot_card(draw, (tx1, ty1, tx2, ty2), title=tbl["title"])
    col_widths = [140, 130, 130, 140, 140]
    hx = tx1 + 12
    hy = ty1 + 48
    for ci, col in enumerate(tbl["columns"]):
        draw.rectangle([hx, hy, hx + col_widths[ci], hy + 34],
                       fill=COLORS["grid"], outline=COLORS["card_border"])
        draw.text((hx + 8, hy + 8), col, fill=COLORS["text"], font=_bold_font(13))
        hx += col_widths[ci]
    for r, row in enumerate(tbl["rows"]):
        rx = tx1 + 12
        ry = hy + 34 * (r + 1)
        for ci, val in enumerate(row):
            draw.rectangle([rx, ry, rx + col_widths[ci], ry + 34],
                           fill=COLORS["bg"], outline=COLORS["card_border"])
            draw.text((rx + 8, ry + 8), val, fill=COLORS["text"], font=_font(12))
            rx += col_widths[ci]

    # Top-right: bar chart
    bc = layout["bar_chart"]
    bx1, by1 = 860, body_y + 20
    bx2, by2 = CANVAS_W - 40, body_y + 380
    _draw_screenshot_card(draw, (bx1, by1, bx2, by2), title=bc["title"])
    bars = bc["data"]
    max_v = max(v for _, v in bars)
    chart_top = by1 + 60
    chart_bot = by2 - 40
    chart_left = bx1 + 40
    chart_right = bx2 - 20
    draw.line([(chart_left, chart_bot), (chart_right, chart_bot)], fill=COLORS["text"], width=2)
    bar_area_w = chart_right - chart_left - 40
    bar_w = bar_area_w // (len(bars) * 2)
    for i, (lbl, v) in enumerate(bars):
        x = chart_left + 20 + i * (bar_w * 2)
        h = int((v / max_v) * (chart_bot - chart_top - 20))
        draw.rectangle([x, chart_bot - h, x + bar_w, chart_bot], fill=COLORS["primary"])
        draw.text((x, chart_bot - h - 18), str(v), fill=COLORS["text"], font=_font(12))
        draw.text((x + bar_w // 4, chart_bot + 6), lbl, fill=COLORS["text"], font=_font(12))

    # Bottom-left: screenshot caption placeholder
    ssx1, ssy1 = 40, by2 + 20
    ssx2, ssy2 = 440, ssy1 + 360
    _draw_screenshot_card(draw, (ssx1, ssy1, ssx2, ssy2), title="スクリーンショット")
    draw.rectangle([ssx1 + 20, ssy1 + 50, ssx2 - 20, ssy2 - 50],
                   fill=COLORS["card_border"], outline=COLORS["card_border"])
    draw.text((ssx1 + 20, ssy2 - 40), layout["screenshot_caption"],
              fill=COLORS["text"], font=_bold_font(13))

    # Bottom-center: code snippet
    cx1, cy1 = 460, by2 + 20
    cx2, cy2 = 960, ssy2
    _draw_screenshot_card(draw, (cx1, cy1, cx2, cy2), title=layout["code_snippet"]["filename"])
    draw.rectangle([cx1 + 12, cy1 + 48, cx2 - 12, cy2 - 12],
                   fill="#1e1e1e", outline=COLORS["card_border"])
    code_y = cy1 + 60
    for line in layout["code_snippet"]["lines"]:
        draw.text((cx1 + 20, code_y), line, fill="#d4d4d4", font=_mono_font(13))
        code_y += 22

    # Bottom-right: bullets
    bux1, buy1 = 980, by2 + 20
    bux2, buy2 = CANVAS_W - 40, ssy2
    _draw_screenshot_card(draw, (bux1, buy1, bux2, buy2), title="主要メトリクス")
    by = buy1 + 60
    for b in layout["bullets"]:
        draw.text((bux1 + 20, by), f"• {b}", fill=COLORS["text"], font=_font(14))
        by += 36

    img.save(out_path, "PNG")


def render_p08(out_path: Path) -> None:
    """P8: 組織図 + ノード SS 補足 — 3 階層 10 ノード."""
    spec = SPEC["p08"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    nodes = layout["nodes"]  # list of (id, level, name, role, parent)
    # Group by level
    by_level: dict[int, list[tuple]] = {}
    for n in nodes:
        by_level.setdefault(n[1], []).append(n)

    # Level y-positions
    level_ys = {1: body_y + 40, 2: body_y + 240, 3: body_y + 500}
    node_w, node_h = 180, 120

    # Draw nodes level by level, centered horizontally
    node_positions: dict[str, tuple[int, int]] = {}  # id -> (cx, cy_top)
    for lvl, items in sorted(by_level.items()):
        total_w = len(items) * node_w + (len(items) - 1) * 40
        start_x = (CANVAS_W - total_w) // 2
        for i, (nid, _lvl, name, role, _parent) in enumerate(items):
            nx1 = start_x + i * (node_w + 40)
            ny1 = level_ys[lvl]
            nx2 = nx1 + node_w
            ny2 = ny1 + node_h
            _draw_screenshot_card(draw, (nx1, ny1, nx2, ny2))
            # Avatar placeholder (circle)
            avatar_cx = nx1 + node_w // 2
            avatar_cy = ny1 + 38
            draw.ellipse([avatar_cx - 22, avatar_cy - 22, avatar_cx + 22, avatar_cy + 22],
                         fill=COLORS["card_border"], outline=COLORS["card_border"])
            # Name + role
            nw, _ = _tsize(draw, name, _bold_font(14))
            draw.text((nx1 + (node_w - nw) // 2, ny1 + 66), name,
                      fill=COLORS["text"], font=_bold_font(14))
            rw, _ = _tsize(draw, role, _font(12))
            draw.text((nx1 + (node_w - rw) // 2, ny1 + 88), role,
                      fill=COLORS["muted"], font=_font(12))
            node_positions[nid] = (avatar_cx, ny1, ny2)

    # Draw parent→child lines
    for nid, _lvl, _name, _role, parent in nodes:
        if parent and parent in node_positions:
            pcx, _py1, py2 = node_positions[parent]
            ccx, cy1, _cy2 = node_positions[nid]
            # Vertical line from parent bottom to child top
            draw.line([(pcx, py2), (pcx, (py2 + cy1) // 2)], fill=COLORS["text"], width=2)
            draw.line([(pcx, (py2 + cy1) // 2), (ccx, (py2 + cy1) // 2)], fill=COLORS["text"], width=2)
            draw.line([(ccx, (py2 + cy1) // 2), (ccx, cy1)], fill=COLORS["text"], width=2)

    img.save(out_path, "PNG")


def render_png(pid: str, out_path: Path) -> None:
    """Dispatch table mapping pattern id → per-pattern renderer."""
    renderers = {
        "p01": render_p01, "p02": render_p02, "p03": render_p03, "p04": render_p04,
        "p05": render_p05, "p06": render_p06, "p07": render_p07, "p08": render_p08,
    }
    if pid not in renderers:
        raise NotImplementedError(f"render_png not implemented for {pid}")
    renderers[pid](out_path)


# -----------------------------------------------------------------------------
# PPTX rendering (python-pptx)
# -----------------------------------------------------------------------------
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt


def _px(n: float) -> Emu:
    """Pixel → EMU mapping at 96 DPI so pixel layouts port over 1:1 from PIL."""
    return Emu(int(n * 9525))


def _hex_rgb(s: str) -> RGBColor:
    return RGBColor.from_string(s.lstrip("#"))


def _pptx_blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _pptx_add_box(slide, x, y, w, h, *, fill=None, outline=None, outline_w=1.0,
                  shape=MSO_SHAPE.RECTANGLE):
    shp = slide.shapes.add_shape(shape, _px(x), _px(y), _px(w), _px(h))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = _hex_rgb(fill)
    if outline is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = _hex_rgb(outline)
        shp.line.width = Pt(outline_w)
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    return shp


def _pptx_add_text(slide, x, y, w, h, text, *, size_pt=11, bold=False,
                   color="#111827", align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(_px(x), _px(y), _px(w), _px(h))
    tf = tb.text_frame
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size_pt)
        run.font.bold = bold
        run.font.color.rgb = _hex_rgb(color)
    return tb


def _pptx_add_line(slide, x1, y1, x2, y2, *, color="#111827", width_pt=2.0):
    ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                    _px(x1), _px(y1), _px(x2), _px(y2))
    ln.line.color.rgb = _hex_rgb(color)
    ln.line.width = Pt(width_pt)
    return ln


def _pptx_title(slide, title: str):
    _pptx_add_text(slide, 32, 22, 1500, 40, title, size_pt=20, bold=True)
    _pptx_add_line(slide, 32, 86, CANVAS_W - 32, 86, color=COLORS["grid"], width_pt=1.5)


def _build_slide_p01(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p01"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    # Screenshot card
    card = (40, 110, 1000, 800)
    _pptx_add_box(slide, card[0], card[1], card[2] - card[0], card[3] - card[1],
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_box(slide, card[0], card[1], card[2] - card[0], 32,
                  fill=COLORS["header_bg"], outline=COLORS["header_bg"])
    _pptx_add_text(slide, card[0] + 12, card[1] + 6, 400, 24,
                   layout["app_title"], size_pt=12, bold=True, color=COLORS["header_text"])
    _pptx_add_text(slide, card[2] - 220, card[1] + 8, 200, 24,
                   layout["header_user"], size_pt=11, color=COLORS["header_text"], align=PP_ALIGN.RIGHT)

    # Table
    tbl_x1, tbl_y1 = card[0] + 24, card[1] + 60
    col_widths = [190, 110, 110, 110, 140]
    row_h = 42
    hx = tbl_x1
    for ci, header in enumerate(layout["table_header"]):
        _pptx_add_box(slide, hx, tbl_y1, col_widths[ci], row_h,
                      fill=COLORS["grid"], outline=COLORS["card_border"])
        _pptx_add_text(slide, hx + 10, tbl_y1 + 12, col_widths[ci] - 20, row_h - 24,
                       header, size_pt=11, bold=True)
        hx += col_widths[ci]
    for r, row in enumerate(layout["table_rows"]):
        ry = tbl_y1 + row_h * (r + 1)
        rx = tbl_x1
        for ci, val in enumerate(row):
            _pptx_add_box(slide, rx, ry, col_widths[ci], row_h,
                          fill=COLORS["bg"], outline=COLORS["card_border"])
            _pptx_add_text(slide, rx + 10, ry + 12, col_widths[ci] - 20, row_h - 24,
                           val, size_pt=11)
            rx += col_widths[ci]

    # Buttons
    btn_y = tbl_y1 + row_h * (len(layout["table_rows"]) + 1) + 24
    bx = tbl_x1
    for label in layout["buttons"]:
        bw = len(label) * 16 + 24
        _pptx_add_box(slide, bx, btn_y, bw, 32,
                      fill=COLORS["primary"], outline=COLORS["primary_dk"], outline_w=1.5)
        _pptx_add_text(slide, bx, btn_y + 7, bw, 22,
                       label, size_pt=11, bold=True, color=COLORS["header_text"], align=PP_ALIGN.CENTER)
        bx += bw + 10

    # 4 red callouts with labels
    for i, (label, text) in enumerate(layout["callouts"]):
        bx1 = 1040
        by1 = 130 + i * 170
        _pptx_add_box(slide, bx1, by1, 520, 110,
                      fill=COLORS["danger_bg"], outline=COLORS["danger"], outline_w=2.0,
                      shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        _pptx_add_text(slide, bx1 + 12, by1 + 12, 500, 24,
                       label, size_pt=12, bold=True, color=COLORS["danger_text"])
        _pptx_add_text(slide, bx1 + 12, by1 + 38, 500, 60,
                       text, size_pt=11, color=COLORS["danger_text"])


def _build_slide_p02(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p02"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    gap = 40
    card_w = (CANVAS_W - 3 * gap) // 2
    for offset, side_key in [(gap, "before"), (2 * gap + card_w, "after")]:
        card = (offset, 120, offset + card_w, 770)
        s = layout[side_key]
        _pptx_add_box(slide, card[0], card[1], card_w, card[3] - card[1],
                      fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
        _pptx_add_box(slide, card[0], card[1], card_w, 32,
                      fill=COLORS["header_bg"], outline=COLORS["header_bg"])
        _pptx_add_text(slide, card[0] + 12, card[1] + 6, card_w - 24, 24,
                       s["title"], size_pt=12, bold=True, color=COLORS["header_text"])
        sx1 = card[0] + 24
        sy = card[1] + 60
        _pptx_add_box(slide, sx1, sy, card_w - 160, 36,
                      fill=COLORS["bg"], outline=COLORS["card_border"], outline_w=1.5)
        _pptx_add_text(slide, sx1 + 10, sy + 10, card_w - 180, 20,
                       s["search_placeholder"], size_pt=11, color=COLORS["muted"])
        _pptx_add_box(slide, card[2] - 130, sy, 106, 36,
                      fill=COLORS["primary"], outline=COLORS["primary_dk"], outline_w=1.5)
        _pptx_add_text(slide, card[2] - 130, sy + 10, 106, 20,
                       s["button"], size_pt=11, bold=True, color=COLORS["header_text"], align=PP_ALIGN.CENTER)
        fy = sy + 60
        for _i in range(s["filter_rows"]):
            _pptx_add_box(slide, sx1, fy, card_w - 48, 28,
                          fill=COLORS["card_bg"], outline=COLORS["card_border"])
            fy += 36
        _pptx_add_text(slide, sx1, fy + 20, card_w - 48, 20,
                       s["result_count_label"], size_pt=11)
        _pptx_add_text(slide, sx1, fy + 60, card_w - 48, 24,
                       s["pagination"], size_pt=12, bold=True)

    # Diff labels at the bottom
    for i, (label, text) in enumerate(layout["diffs"]):
        y = CANVAS_H - 220 + i * 60
        _pptx_add_box(slide, 40, y, 240, 44,
                      fill=COLORS["danger_bg"], outline=COLORS["danger"], outline_w=1.5)
        _pptx_add_text(slide, 50, y + 12, 220, 24,
                       f"{label} {text}", size_pt=11, bold=True, color=COLORS["danger_text"])


def _build_slide_p03(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p03"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    steps = layout["steps"]
    n = len(steps)
    margin = 40
    gap = 48
    card_w = (CANVAS_W - 2 * margin - (n - 1) * gap) // n
    card_h = 400
    y1 = 230
    for i, (label, step_title, step_desc) in enumerate(steps):
        x1 = margin + i * (card_w + gap)
        # Step label badge
        _pptx_add_box(slide, x1 + card_w // 2 - 24, y1 - 40, 48, 32,
                      fill=COLORS["primary"], outline=COLORS["primary_dk"], outline_w=1.5)
        _pptx_add_text(slide, x1 + card_w // 2 - 24, y1 - 34, 48, 24,
                       label, size_pt=14, bold=True, color=COLORS["header_text"], align=PP_ALIGN.CENTER)
        # Card
        _pptx_add_box(slide, x1, y1, card_w, card_h,
                      fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
        _pptx_add_box(slide, x1, y1, card_w, 32,
                      fill=COLORS["header_bg"], outline=COLORS["header_bg"])
        _pptx_add_text(slide, x1 + 12, y1 + 6, card_w - 24, 24,
                       step_title, size_pt=12, bold=True, color=COLORS["header_text"])
        _pptx_add_text(slide, x1 + 12, y1 + 48, card_w - 24, card_h - 60,
                       step_desc, size_pt=11)
        if i < n - 1:
            _pptx_add_line(slide, x1 + card_w + 4, y1 + card_h // 2,
                           x1 + card_w + gap - 4, y1 + card_h // 2,
                           color=COLORS["text"], width_pt=3.0)


def _build_slide_p04(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p04"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    # Bar chart as labeled bars (native PPT elements, not image)
    _pptx_add_box(slide, 40, 140, 600, 300,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_text(slide, 56, 152, 500, 28,
                   layout["bar_chart"]["title"], size_pt=12, bold=True)
    bars = layout["bar_chart"]["data"]
    max_v = max(v for _, v in bars)
    chart_top, chart_bot = 200, 410
    for i, (lbl, v) in enumerate(bars):
        x = 80 + i * 160
        h = int((v / max_v) * (chart_bot - chart_top - 20))
        _pptx_add_box(slide, x, chart_bot - h, 80, h,
                      fill=COLORS["primary"], outline=COLORS["primary"])
        _pptx_add_text(slide, x, chart_bot - h - 22, 80, 20,
                       str(v), size_pt=11, align=PP_ALIGN.CENTER)
        _pptx_add_text(slide, x, chart_bot + 6, 80, 20,
                       lbl, size_pt=11, align=PP_ALIGN.CENTER)

    # Pie chart — approximate as labeled legend (python-pptx chart objects are heavier; legend-like text is sufficient for extraction test)
    _pptx_add_box(slide, 800, 140, CANVAS_W - 840, 300,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_text(slide, 816, 152, 500, 28,
                   layout["pie_chart"]["title"], size_pt=12, bold=True)
    palette = [COLORS["primary"], COLORS["success"], COLORS["warn"], COLORS["muted"]]
    for i, (lbl, v) in enumerate(layout["pie_chart"]["data"]):
        _pptx_add_box(slide, 816, 190 + i * 44, 24, 24,
                      fill=palette[i % len(palette)], outline=palette[i % len(palette)])
        _pptx_add_text(slide, 850, 194 + i * 44, 400, 28,
                       f"{lbl}  {v}%", size_pt=13)

    # 3 KPI cards
    kpi_y = 470
    kpi_w = (CANVAS_W - 2 * 40 - 2 * 20) // 3
    for i, (kpi_label, kpi_val, kpi_sub) in enumerate(layout["kpi_cards"]):
        kx1 = 40 + i * (kpi_w + 20)
        _pptx_add_box(slide, kx1, kpi_y, kpi_w, 160,
                      fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
        _pptx_add_text(slide, kx1 + 16, kpi_y + 16, kpi_w - 32, 20,
                       kpi_label, size_pt=13, bold=True, color=COLORS["muted"])
        _pptx_add_text(slide, kx1 + 16, kpi_y + 48, kpi_w - 32, 44,
                       kpi_val, size_pt=26, bold=True)
        _pptx_add_text(slide, kx1 + 16, kpi_y + 104, kpi_w - 32, 24,
                       kpi_sub, size_pt=11, color=COLORS["success"])

    # 3 annotation boxes
    for i, (label, text) in enumerate(layout["annotations"]):
        ay = 650 + i * 48
        _pptx_add_box(slide, 40, ay, CANVAS_W - 80, 40,
                      fill=COLORS["danger_bg"], outline=COLORS["danger"], outline_w=1.0)
        _pptx_add_text(slide, 52, ay + 10, CANVAS_W - 120, 24,
                       f"{label} {text}", size_pt=11, bold=True, color=COLORS["danger_text"])


def render_pptx(out_path: Path) -> None:
    """Build a single 8-slide PPTX, one slide per pattern p01..p08."""
    prs = Presentation()
    prs.slide_width = _px(CANVAS_W)
    prs.slide_height = _px(CANVAS_H)
    builders = {
        "p01": _build_slide_p01,
        "p02": _build_slide_p02,
        "p03": _build_slide_p03,
        "p04": _build_slide_p04,
        # p05-p08 added in Task 7.
    }
    for pid in ["p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"]:
        builder = builders.get(pid)
        if builder is None:
            # Placeholder slide so ordering is preserved until Task 7 lands.
            slide = _pptx_blank_slide(prs)
            _pptx_title(slide, SPEC[pid]["title"])
            _pptx_add_text(slide, 40, 150, CANVAS_W - 80, 40,
                           f"(TODO: {pid} slide builder — implemented in a later task)",
                           size_pt=14, color=COLORS["muted"])
        else:
            builder(prs)
    prs.save(str(out_path))
