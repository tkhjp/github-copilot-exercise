#!/usr/bin/env python
"""Generate the 3 redesigned test images for the text-vs-image fidelity test.

Each image is intentionally dense to stress-test LLM extraction:
- 01_mixed_slide.png: one slide packed with flowchart + bar chart + table + code
- 02_ui_change.png:   UI mockup with red callout bubbles carrying change requests
- 03_complex_arch.png: AWS-style multi-AZ architecture with 12+ components

Run once:
    python tests/text_vs_image/generate_test_images.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
IMAGES = ROOT / "images"
WORKSPACE = ROOT.parent.parent  # copilot_demo/

# ---------------------------------------------------------------------------
# Font helpers (same pattern as prior generator)
# ---------------------------------------------------------------------------

def _font(size: int):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _mono_font(size: int):
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _bold_font(size: int):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return _font(size)


def _text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _arrow(draw, p1, p2, color="black", width=2, head=10):
    draw.line([p1, p2], fill=color, width=width)
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    a1 = (p2[0] - head * math.cos(ang - math.radians(22)),
          p2[1] - head * math.sin(ang - math.radians(22)))
    a2 = (p2[0] - head * math.cos(ang + math.radians(22)),
          p2[1] - head * math.sin(ang + math.radians(22)))
    draw.polygon([p2, a1, a2], fill=color)


# ---------------------------------------------------------------------------
# Reusable section renderers (for the mixed slide)
# ---------------------------------------------------------------------------

def _draw_flowchart(draw, origin, size, font):
    """Draw a 3-box flow: Receive → Validate → Ship inside a bounded region."""
    ox, oy = origin
    w, _ = size
    # title
    draw.text((ox, oy), "Order Flow", fill="black", font=font)
    # 3 boxes
    pad = 18
    box_w = (w - 4 * pad) // 3
    box_h = 60
    box_y = oy + 40
    colors = ["#d0e7ff", "#fff1c0", "#c8e6c9"]
    labels = ["Receive\nOrder", "Validate\nPayment", "Ship\nProduct"]
    centers_x = []
    for i, (label, fill) in enumerate(zip(labels, colors)):
        x1 = ox + pad + i * (box_w + pad)
        x2 = x1 + box_w
        draw.rectangle([x1, box_y, x2, box_y + box_h], fill=fill, outline="black", width=2)
        cx = (x1 + x2) // 2
        centers_x.append(cx)
        lines = label.split("\n")
        for li, line in enumerate(lines):
            tw, th = _text_size(draw, line, font)
            draw.text((cx - tw // 2, box_y + 10 + li * (th + 2)), line, fill="black", font=font)
    # arrows between boxes
    for i in range(len(centers_x) - 1):
        x1 = ox + pad + i * (box_w + pad) + box_w
        x2 = x1 + pad
        y = box_y + box_h // 2
        _arrow(draw, (x1, y), (x2, y), color="black", width=2, head=8)


def _draw_bar_chart(draw, origin, size, font):
    """Draw a 4-bar chart with values, Mar highlighted."""
    ox, oy = origin
    w, h = size
    draw.text((ox, oy), "Monthly Revenue (MJPY)", fill="black", font=font)
    chart_top = oy + 38
    chart_bottom = oy + h - 30
    chart_left = ox + 20
    chart_right = ox + w - 10
    # axes
    draw.line([(chart_left, chart_bottom), (chart_right, chart_bottom)], fill="black", width=2)
    draw.line([(chart_left, chart_top), (chart_left, chart_bottom)], fill="black", width=2)
    # bars
    data = [("Jan", 120, "#4a90e2"), ("Feb", 85, "#4a90e2"),
            ("Mar", 160, "#e27a4a"), ("Apr", 140, "#4a90e2")]
    bars_area = chart_right - chart_left - 20
    bar_w = bars_area // (len(data) * 2)
    gap = bar_w
    max_val = 200
    for i, (label, val, color) in enumerate(data):
        x = chart_left + 15 + i * (bar_w + gap)
        height = int((val / max_val) * (chart_bottom - chart_top - 20))
        y_top = chart_bottom - height
        draw.rectangle([x, y_top, x + bar_w, chart_bottom], fill=color, outline="black")
        # value label above bar
        vt = str(val)
        tw, _ = _text_size(draw, vt, font)
        draw.text((x + bar_w // 2 - tw // 2, y_top - 18), vt, fill="black", font=font)
        # x label
        lt = label
        tw, _ = _text_size(draw, lt, font)
        draw.text((x + bar_w // 2 - tw // 2, chart_bottom + 4), lt, fill="black", font=font)


def _draw_sales_table(draw, origin, _size, font, header_font):
    """Draw a 4 row × 5 column regional sales table."""
    ox, oy = origin
    draw.text((ox, oy), "Regional Sales (MJPY)", fill="black", font=header_font)
    table_top = oy + 32
    col_widths = [88, 60, 60, 60, 70]
    total_w = sum(col_widths)
    row_h = 30
    headers = ["Region", "Jan", "Feb", "Mar", "Total"]
    rows = [
        ["Tokyo", "120", "85", "160", "365"],
        ["Osaka", "90", "70", "110", "270"],
        ["Nagoya", "60", "55", "75", "190"],
        ["Fukuoka", "45", "40", "65", "150"],
    ]
    # header
    draw.rectangle([ox, table_top, ox + total_w, table_top + row_h], fill="#4a90e2")
    x = ox
    for i, header in enumerate(headers):
        tw, _ = _text_size(draw, header, font)
        cx = x + (col_widths[i] - tw) / 2
        draw.text((cx, table_top + 6), header, fill="white", font=font)
        x += col_widths[i]
    # rows
    for r, row in enumerate(rows):
        y = table_top + row_h * (r + 1)
        bg = "#f5f5f5" if r % 2 == 0 else "white"
        draw.rectangle([ox, y, ox + total_w, y + row_h], fill=bg)
        x = ox
        for i, val in enumerate(row):
            if i == 0:
                cx = x + 10
            else:
                tw, _ = _text_size(draw, val, font)
                cx = x + (col_widths[i] - tw) / 2
            draw.text((cx, y + 6), val, fill="black", font=font)
            x += col_widths[i]
    # border
    total_h = row_h * (len(rows) + 1)
    draw.rectangle([ox, table_top, ox + total_w, table_top + total_h], outline="black", width=2)
    for r in range(1, len(rows) + 1):
        y = table_top + row_h * r
        draw.line([(ox, y), (ox + total_w, y)], fill="#cccccc", width=1)
    x = ox
    for w_col in col_widths[:-1]:
        x += w_col
        draw.line([(x, table_top), (x, table_top + total_h)], fill="#cccccc", width=1)


def _draw_code_snippet(draw, origin, size, font, mono):
    """Draw a small Python snippet with a dark background."""
    ox, oy = origin
    w, h = size
    draw.text((ox, oy), "quarterly_total.py", fill="black", font=font)
    box_top = oy + 26
    box_bottom = oy + h
    draw.rectangle([ox, box_top, ox + w, box_bottom], fill="#1e1e1e", outline="#333333", width=2)
    lines = [
        "def quarterly_total(region: str) -> int:",
        '    """Sum Jan+Feb+Mar for one region."""',
        "    data = SALES[region]",
        "    return data['Jan'] + data['Feb'] + data['Mar']",
        "",
        "total = quarterly_total('Tokyo')",
    ]
    y = box_top + 10
    for line in lines:
        color = "#d4d4d4"
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("return"):
            color = "#569cd6"
        elif stripped.startswith('"""'):
            color = "#6a9955"
        draw.text((ox + 10, y), line, fill=color, font=mono)
        y += 18


# ---------------------------------------------------------------------------
# tc01 — Mixed Slide
# ---------------------------------------------------------------------------

def make_mixed_slide(path: Path) -> None:
    w, h = 1280, 960
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    title_font = _bold_font(32)
    sub_font = _font(18)
    section_font = _bold_font(18)
    body_font = _font(16)
    mono_font = _mono_font(13)

    # Title bar
    draw.rectangle([0, 0, w, 80], fill="#2563eb")
    draw.text((32, 18), "2026 Q1 Operations Overview", fill="white", font=title_font)
    draw.text((32, 56), "Revenue, Fulfillment, and Metrics", fill="#cfd8ff", font=sub_font)

    # Quadrant layout:
    #   top-left: flowchart     | top-right: bar chart
    #   bot-left: sales table   | bot-right: code snippet
    pad = 30
    quad_w = (w - 3 * pad) // 2
    top_y = 110
    bot_y = 490
    quad_h = 340

    # Top-left: flowchart
    _draw_flowchart(draw, (pad, top_y), (quad_w, quad_h), section_font)

    # Top-right: bar chart
    _draw_bar_chart(draw, (pad * 2 + quad_w, top_y), (quad_w, quad_h), section_font)

    # Bottom-left: table
    _draw_sales_table(draw, (pad, bot_y), (quad_w, quad_h), body_font, section_font)

    # Bottom-right: code snippet
    _draw_code_snippet(draw, (pad * 2 + quad_w, bot_y), (quad_w, quad_h - 30), section_font, mono_font)

    # Footer annotation (bottom strip)
    footer_y = h - 60
    draw.rectangle([0, footer_y, w, h], fill="#f1f5f9")
    draw.text(
        (32, footer_y + 18),
        "Q1 total revenue: 975 million JPY. Mar was the strongest month across all regions.",
        fill="#1e293b",
        font=_bold_font(17),
    )

    img.save(path, "PNG")


# ---------------------------------------------------------------------------
# tc02 — UI Change Request (RFP)
# ---------------------------------------------------------------------------

def _draw_callout(draw, point_at, text, font, box_left, box_top, box_width=260):
    """Draw a red callout box with a leader line pointing at `point_at`."""
    # wrap text roughly
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        tw, _ = _text_size(draw, test, font)
        if tw > box_width - 20:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    line_h = _text_size(draw, "Ag", font)[1] + 4
    box_height = len(lines) * line_h + 20
    box_right = box_left + box_width
    box_bottom = box_top + box_height
    # red rounded-ish rectangle
    draw.rectangle([box_left, box_top, box_right, box_bottom], fill="#fef2f2", outline="#dc2626", width=2)
    # text
    for i, line in enumerate(lines):
        draw.text((box_left + 10, box_top + 10 + i * line_h), line, fill="#991b1b", font=font)
    # leader line from box edge to target
    cx = (box_left + box_right) / 2
    cy = (box_top + box_bottom) / 2
    # pick the nearest side of the box toward target
    start = (cx, cy)
    _arrow(draw, start, point_at, color="#dc2626", width=2, head=10)


def make_ui_change_rfp(path: Path) -> None:
    w, h = 1280, 820
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    title_font = _bold_font(22)
    body_font = _font(15)
    small_font = _font(12)
    callout_font = _bold_font(13)

    # Document header
    draw.text((24, 16), "UI Change Request — ShopApp Product Search", fill="black", font=title_font)
    draw.text((24, 44), "Reviewer: PM / Design — 2026-04-10", fill="#6b7280", font=body_font)
    draw.line([(24, 66), (w - 24, 66)], fill="#e5e7eb", width=2)

    # ------ Screen mockup area ------
    screen_x1, screen_y1 = 40, 90
    screen_x2, screen_y2 = 780, 760
    draw.rectangle([screen_x1, screen_y1, screen_x2, screen_y2], fill="#ffffff", outline="#9ca3af", width=2)

    # Header bar inside screen
    hdr_bottom = screen_y1 + 50
    draw.rectangle([screen_x1, screen_y1, screen_x2, hdr_bottom], fill="#1e293b")
    draw.text((screen_x1 + 20, screen_y1 + 15), "ShopApp", fill="white", font=_bold_font(20))
    # Login button
    login_x1 = screen_x2 - 100
    login_x2 = screen_x2 - 20
    draw.rectangle([login_x1, screen_y1 + 12, login_x2, screen_y1 + 38], fill="#374151", outline="#9ca3af")
    draw.text((login_x1 + 22, screen_y1 + 17), "Login", fill="white", font=body_font)

    # Search bar
    search_y = hdr_bottom + 20
    search_box_x1 = screen_x1 + 20
    search_box_x2 = screen_x2 - 140
    draw.rectangle([search_box_x1, search_y, search_box_x2, search_y + 36], fill="white", outline="#9ca3af", width=2)
    draw.text((search_box_x1 + 10, search_y + 10), "Search products...", fill="#9ca3af", font=body_font)
    # Search button (blue)
    search_btn_x1 = search_box_x2 + 10
    search_btn_x2 = search_btn_x1 + 100
    draw.rectangle([search_btn_x1, search_y, search_btn_x2, search_y + 36], fill="#2563eb", outline="#1e40af", width=2)
    tw, _ = _text_size(draw, "Search", _bold_font(15))
    draw.text((search_btn_x1 + 50 - tw // 2, search_y + 9), "Search", fill="white", font=_bold_font(15))

    # Filter sidebar
    filter_x1 = screen_x1 + 20
    filter_x2 = filter_x1 + 180
    filter_y1 = search_y + 70
    filter_y2 = filter_y1 + 290
    draw.rectangle([filter_x1, filter_y1, filter_x2, filter_y2], fill="#f9fafb", outline="#d1d5db", width=1)
    draw.text((filter_x1 + 12, filter_y1 + 12), "Filters", fill="black", font=_bold_font(16))
    # category checkboxes
    cats = ["Electronics", "Books", "Clothing"]
    for i, cat in enumerate(cats):
        cy = filter_y1 + 50 + i * 32
        draw.rectangle([filter_x1 + 14, cy, filter_x1 + 30, cy + 16], outline="#6b7280", width=2)
        draw.text((filter_x1 + 38, cy), cat, fill="black", font=body_font)
    # price range label + slider
    draw.text((filter_x1 + 12, filter_y1 + 160), "Price range", fill="black", font=body_font)
    slider_y = filter_y1 + 190
    draw.line([(filter_x1 + 14, slider_y), (filter_x2 - 14, slider_y)], fill="#9ca3af", width=3)
    draw.ellipse([filter_x1 + 30, slider_y - 7, filter_x1 + 44, slider_y + 7], fill="#2563eb", outline="#1e40af")
    draw.ellipse([filter_x2 - 44, slider_y - 7, filter_x2 - 30, slider_y + 7], fill="#2563eb", outline="#1e40af")
    draw.text((filter_x1 + 12, filter_y1 + 210), "¥0 - ¥50,000", fill="#6b7280", font=small_font)

    # Results table
    table_x1 = filter_x2 + 20
    table_x2 = screen_x2 - 20
    table_y1 = search_y + 70
    row_h = 40
    # header
    draw.rectangle([table_x1, table_y1, table_x2, table_y1 + row_h], fill="#e5e7eb", outline="#9ca3af", width=1)
    cols = [("Product", 220), ("Price", 110), ("Stock", 90)]
    cx = table_x1
    for name, cw in cols:
        draw.text((cx + 10, table_y1 + 12), name, fill="black", font=_bold_font(14))
        cx += cw
    # rows
    products = [
        ("Wireless Headphones", "¥12,800", "42"),
        ("USB-C Hub (7-in-1)",  "¥4,500",  "118"),
        ("Mech. Keyboard",      "¥15,200", "7"),
    ]
    for r, (name, price, stock) in enumerate(products):
        ry = table_y1 + row_h * (r + 1)
        bg = "white" if r % 2 == 0 else "#f9fafb"
        draw.rectangle([table_x1, ry, table_x2, ry + row_h], fill=bg, outline="#e5e7eb", width=1)
        cx = table_x1
        for val, (_n, cw) in zip([name, price, stock], cols):
            draw.text((cx + 10, ry + 12), val, fill="black", font=body_font)
            cx += cw
    # table border
    draw.rectangle([table_x1, table_y1, table_x2, table_y1 + row_h * (len(products) + 1)],
                   outline="#9ca3af", width=1)

    # Pagination
    page_y = table_y1 + row_h * (len(products) + 1) + 20
    page_cx = (table_x1 + table_x2) // 2
    labels = ["<", "1", "2", "3", ">"]
    btn_w = 34
    btn_h = 30
    total_btn_w = len(labels) * (btn_w + 6) - 6
    start_x = page_cx - total_btn_w // 2
    for i, lbl in enumerate(labels):
        bx1 = start_x + i * (btn_w + 6)
        bx2 = bx1 + btn_w
        fill = "#2563eb" if lbl == "1" else "white"
        text_color = "white" if lbl == "1" else "#1e293b"
        draw.rectangle([bx1, page_y, bx2, page_y + btn_h], fill=fill, outline="#9ca3af", width=1)
        tw, _ = _text_size(draw, lbl, body_font)
        draw.text((bx1 + btn_w // 2 - tw // 2, page_y + 7), lbl, fill=text_color, font=body_font)

    # ------ Callouts (red) pointing at elements ------
    # 1. Search bar area → checkbox request
    _draw_callout(
        draw,
        point_at=(search_box_x1 + 150, search_y + 40),
        text='1. Add a "Remember last search" checkbox below the search bar.',
        font=callout_font,
        box_left=820,
        box_top=120,
    )
    # 2. Search button → color change
    _draw_callout(
        draw,
        point_at=(search_btn_x1 + 50, search_y + 18),
        text="2. Change the Search button color from blue to green.",
        font=callout_font,
        box_left=820,
        box_top=230,
    )
    # 3. Results table top-right → CSV export
    _draw_callout(
        draw,
        point_at=(table_x2 - 20, table_y1 + 15),
        text="3. Add a CSV export button on the results table top-right corner.",
        font=callout_font,
        box_left=820,
        box_top=360,
    )
    # 4. Pagination → page size
    _draw_callout(
        draw,
        point_at=(page_cx, page_y + 15),
        text="4. Show 20 items per page instead of the current 10.",
        font=callout_font,
        box_left=820,
        box_top=490,
    )

    # Legend
    legend_y = 650
    draw.rectangle([820, legend_y, 820 + 240, legend_y + 90], fill="#fefce8", outline="#ca8a04", width=1)
    draw.text((832, legend_y + 10), "Legend", fill="#854d0e", font=_bold_font(14))
    draw.line([(832, legend_y + 38), (862, legend_y + 38)], fill="#dc2626", width=2)
    draw.text((870, legend_y + 30), "Red = change request", fill="#854d0e", font=small_font)
    draw.rectangle([832, legend_y + 56, 862, legend_y + 74], outline="#9ca3af", width=1, fill="white")
    draw.text((870, legend_y + 58), "Gray = existing UI", fill="#854d0e", font=small_font)

    img.save(path, "PNG")


# ---------------------------------------------------------------------------
# tc03 — Complex Cloud Architecture (AWS-style, multi-AZ)
# ---------------------------------------------------------------------------

def _draw_component(draw, rect, label, fill, shape="box", font=None):
    x1, y1, x2, y2 = rect
    if shape == "box":
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline="black", width=2)
    elif shape == "cylinder":
        # DB cylinder
        draw.ellipse([x1, y1 - 8, x2, y1 + 8], fill=fill, outline="black", width=2)
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline=None)
        draw.line([(x1, y1), (x1, y2)], fill="black", width=2)
        draw.line([(x2, y1), (x2, y2)], fill="black", width=2)
        draw.ellipse([x1, y2 - 8, x2, y2 + 8], fill=fill, outline="black", width=2)
    elif shape == "rounded":
        draw.rounded_rectangle([x1, y1, x2, y2], radius=12, fill=fill, outline="black", width=2)
    lines = label.split("\n")
    if font is None:
        font = _font(12)
    total_h = sum(_text_size(draw, l, font)[1] for l in lines)
    y = (y1 + y2) / 2 - total_h / 2
    for line in lines:
        tw, th = _text_size(draw, line, font)
        draw.text(((x1 + x2) / 2 - tw / 2, y), line, fill="black", font=font)
        y += th + 1


def _dashed_rect(draw, rect, color, width=2, dash=8):
    x1, y1, x2, y2 = rect
    # top
    x = x1
    while x < x2:
        draw.line([(x, y1), (min(x + dash, x2), y1)], fill=color, width=width)
        x += dash * 2
    # bottom
    x = x1
    while x < x2:
        draw.line([(x, y2), (min(x + dash, x2), y2)], fill=color, width=width)
        x += dash * 2
    # left
    y = y1
    while y < y2:
        draw.line([(x1, y), (x1, min(y + dash, y2))], fill=color, width=width)
        y += dash * 2
    # right
    y = y1
    while y < y2:
        draw.line([(x2, y), (x2, min(y + dash, y2))], fill=color, width=width)
        y += dash * 2


def make_complex_architecture(path: Path) -> None:
    w, h = 1400, 900
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    title_font = _bold_font(26)
    label_font = _bold_font(14)
    node_font = _bold_font(13)
    small_font = _font(11)
    edge_font = _font(11)

    draw.text((30, 20), "Production Architecture — AWS Multi-AZ", fill="black", font=title_font)
    draw.text((30, 52), "Environment: prod • Region: ap-northeast-1", fill="#6b7280", font=label_font)

    # --- Top row: Route53, CloudFront, S3, External ---
    top_y = 100
    top_h = 60
    route53 = (50, top_y, 180, top_y + top_h)
    cloudfront = (230, top_y, 380, top_y + top_h)
    s3 = (430, top_y, 560, top_y + top_h)
    iam = (1230, top_y, 1360, top_y + top_h)
    cw = (1230, top_y + 80, 1360, top_y + 80 + top_h)

    _draw_component(draw, route53, "Route 53\nDNS", "#e9d5ff", "rounded", node_font)
    _draw_component(draw, cloudfront, "CloudFront\nCDN", "#fde68a", "rounded", node_font)
    _draw_component(draw, s3, "S3\nStatic Assets", "#d1fae5", "box", node_font)
    _draw_component(draw, iam, "IAM\nRoles", "#fbcfe8", "rounded", node_font)
    _draw_component(draw, cw, "CloudWatch\nLogs/Metrics", "#fbcfe8", "rounded", node_font)

    # --- VPC boundary ---
    vpc = (50, 210, 1200, 820)
    _dashed_rect(draw, vpc, "#7c3aed", width=3, dash=10)
    draw.text((vpc[0] + 12, vpc[1] + 8), "VPC: 10.0.0.0/16", fill="#7c3aed", font=label_font)

    # AZ boundaries
    az_a = (75, 260, 620, 800)
    az_b = (640, 260, 1180, 800)
    _dashed_rect(draw, az_a, "#0891b2", width=2, dash=6)
    _dashed_rect(draw, az_b, "#0891b2", width=2, dash=6)
    draw.text((az_a[0] + 10, az_a[1] + 6), "AZ-a (ap-northeast-1a)", fill="#0891b2", font=label_font)
    draw.text((az_b[0] + 10, az_b[1] + 6), "AZ-b (ap-northeast-1c)", fill="#0891b2", font=label_font)

    # Public subnet inside each AZ (top)
    pub_a = (95, 295, 600, 395)
    pub_b = (660, 295, 1160, 395)
    for rect in (pub_a, pub_b):
        draw.rectangle(rect, fill="#dbeafe", outline="#3b82f6", width=1)
    draw.text((pub_a[0] + 8, pub_a[1] + 4), "Public Subnet", fill="#1e3a8a", font=small_font)
    draw.text((pub_b[0] + 8, pub_b[1] + 4), "Public Subnet", fill="#1e3a8a", font=small_font)

    # ALB spans both AZ public subnets visually (draw one in each)
    alb_a = (pub_a[0] + 40, pub_a[1] + 30, pub_a[0] + 200, pub_a[1] + 85)
    alb_b = (pub_b[0] + 40, pub_b[1] + 30, pub_b[0] + 200, pub_b[1] + 85)
    _draw_component(draw, alb_a, "ALB\n(AZ-a)", "#fef3c7", "rounded", node_font)
    _draw_component(draw, alb_b, "ALB\n(AZ-b)", "#fef3c7", "rounded", node_font)

    # NAT gateways
    nat_a = (pub_a[0] + 280, pub_a[1] + 30, pub_a[0] + 430, pub_a[1] + 85)
    nat_b = (pub_b[0] + 280, pub_b[1] + 30, pub_b[0] + 430, pub_b[1] + 85)
    _draw_component(draw, nat_a, "NAT GW\n(AZ-a)", "#fef3c7", "box", node_font)
    _draw_component(draw, nat_b, "NAT GW\n(AZ-b)", "#fef3c7", "box", node_font)

    # Private subnet inside each AZ (middle)
    priv_a = (95, 420, 600, 570)
    priv_b = (660, 420, 1160, 570)
    for rect in (priv_a, priv_b):
        draw.rectangle(rect, fill="#fef9c3", outline="#eab308", width=1)
    draw.text((priv_a[0] + 8, priv_a[1] + 4), "Private Subnet (App)", fill="#713f12", font=small_font)
    draw.text((priv_b[0] + 8, priv_b[1] + 4), "Private Subnet (App)", fill="#713f12", font=small_font)

    # ECS Fargate in each
    ecs_a = (priv_a[0] + 40, priv_a[1] + 40, priv_a[0] + 230, priv_a[1] + 130)
    ecs_b = (priv_b[0] + 40, priv_b[1] + 40, priv_b[0] + 230, priv_b[1] + 130)
    _draw_component(draw, ecs_a, "ECS Fargate\nApp Service\n(AZ-a)", "#fed7aa", "rounded", node_font)
    _draw_component(draw, ecs_b, "ECS Fargate\nApp Service\n(AZ-b)", "#fed7aa", "rounded", node_font)

    # ElastiCache in each private
    redis_a = (priv_a[0] + 290, priv_a[1] + 50, priv_a[0] + 450, priv_a[1] + 120)
    redis_b = (priv_b[0] + 290, priv_b[1] + 50, priv_b[0] + 450, priv_b[1] + 120)
    _draw_component(draw, redis_a, "ElastiCache\nRedis", "#fecaca", "rounded", node_font)
    _draw_component(draw, redis_b, "ElastiCache\nRedis", "#fecaca", "rounded", node_font)

    # DB subnet (bottom, spans both AZs)
    db_a = (95, 595, 600, 780)
    db_b = (660, 595, 1160, 780)
    for rect in (db_a, db_b):
        draw.rectangle(rect, fill="#dcfce7", outline="#16a34a", width=1)
    draw.text((db_a[0] + 8, db_a[1] + 4), "DB Subnet", fill="#14532d", font=small_font)
    draw.text((db_b[0] + 8, db_b[1] + 4), "DB Subnet", fill="#14532d", font=small_font)

    # RDS Primary in AZ-a, RDS Replica in AZ-b
    rds_primary = (db_a[0] + 100, db_a[1] + 50, db_a[0] + 280, db_a[1] + 150)
    rds_replica = (db_b[0] + 100, db_b[1] + 50, db_b[0] + 280, db_b[1] + 150)
    _draw_component(draw, rds_primary, "RDS PostgreSQL\nPrimary", "#bbf7d0", "cylinder", node_font)
    _draw_component(draw, rds_replica, "RDS PostgreSQL\nRead Replica", "#bbf7d0", "cylinder", node_font)

    # ---------- Arrows ----------
    def bottom_mid(r): return ((r[0] + r[2]) / 2, r[3])
    def top_mid(r): return ((r[0] + r[2]) / 2, r[1])
    def left_mid(r): return (r[0], (r[1] + r[3]) / 2)
    def right_mid(r): return (r[2], (r[1] + r[3]) / 2)

    # Route53 → CloudFront
    _arrow(draw, right_mid(route53), left_mid(cloudfront), color="black", width=2)
    # CloudFront → S3
    _arrow(draw, right_mid(cloudfront), left_mid(s3), color="black", width=2)
    draw.text(((cloudfront[2] + s3[0]) / 2 - 20, cloudfront[1] - 16), "origin", fill="#6b7280", font=edge_font)

    # CloudFront → ALB (both)
    _arrow(draw, bottom_mid(cloudfront), top_mid(alb_a), color="black", width=2)
    _arrow(draw, bottom_mid(cloudfront), top_mid(alb_b), color="black", width=2)
    draw.text((cloudfront[0] - 10, cloudfront[3] + 8), "HTTPS", fill="#6b7280", font=edge_font)

    # ALB → ECS (same AZ)
    _arrow(draw, bottom_mid(alb_a), top_mid(ecs_a), color="black", width=2)
    _arrow(draw, bottom_mid(alb_b), top_mid(ecs_b), color="black", width=2)

    # ECS → ElastiCache (same AZ)
    _arrow(draw, right_mid(ecs_a), left_mid(redis_a), color="black", width=2)
    _arrow(draw, right_mid(ecs_b), left_mid(redis_b), color="black", width=2)
    draw.text((ecs_a[2] + 5, ecs_a[1] + 10), "GET/SET", fill="#6b7280", font=edge_font)

    # ECS → RDS Primary (write) — ECS-a to RDS primary
    _arrow(draw, bottom_mid(ecs_a), top_mid(rds_primary), color="#16a34a", width=3)
    draw.text((ecs_a[2] - 30, (ecs_a[3] + rds_primary[1]) / 2 - 8), "write", fill="#16a34a", font=edge_font)
    # ECS-b to RDS Primary (cross-AZ write)
    _arrow(draw, (ecs_b[0] + 40, ecs_b[3]), (rds_primary[2] - 20, rds_primary[1]), color="#16a34a", width=2)

    # ECS → RDS Replica (read)
    _arrow(draw, bottom_mid(ecs_b), top_mid(rds_replica), color="#0891b2", width=3)
    draw.text((ecs_b[2] - 100, (ecs_b[3] + rds_replica[1]) / 2 - 8), "read-only", fill="#0891b2", font=edge_font)

    # NAT GW → Internet (upward arrow)
    _arrow(draw, top_mid(nat_a), (nat_a[0] + (nat_a[2] - nat_a[0]) / 2, nat_a[1] - 40),
           color="#6b7280", width=2)
    draw.text((nat_a[0] + 10, nat_a[1] - 58), "Outbound", fill="#6b7280", font=edge_font)
    _arrow(draw, top_mid(nat_b), (nat_b[0] + (nat_b[2] - nat_b[0]) / 2, nat_b[1] - 40),
           color="#6b7280", width=2)

    # Everything → CloudWatch (dashed-ish, thinner lines)
    for src in [bottom_mid(ecs_a), bottom_mid(ecs_b), bottom_mid(alb_a)]:
        draw.line([src, left_mid(cw)], fill="#e5e7eb", width=1)

    # Legend
    lg_x, lg_y = 50, h - 50
    draw.rectangle([lg_x, lg_y, lg_x + 960, lg_y + 36], fill="#f9fafb", outline="#d1d5db", width=1)
    items = [
        ("#dbeafe", "Public Subnet"),
        ("#fef9c3", "Private Subnet (App)"),
        ("#dcfce7", "DB Subnet"),
        ("#e9d5ff", "External / DNS"),
        ("#fecaca", "Cache"),
    ]
    ix = lg_x + 12
    for color, label in items:
        draw.rectangle([ix, lg_y + 10, ix + 20, lg_y + 26], fill=color, outline="black", width=1)
        draw.text((ix + 26, lg_y + 10), label, fill="black", font=small_font)
        ix += 26 + _text_size(draw, label, small_font)[0] + 24

    img.save(path, "PNG")


# ---------------------------------------------------------------------------
# tc04 — Text-only document (spec page screenshot, no diagrams)
# ---------------------------------------------------------------------------

def make_text_document(path: Path) -> None:
    """A4-ish document page with only text: title, paragraphs, bullet list, table."""
    w, h = 900, 1200
    img = Image.new("RGB", (w, h), "#fefefe")
    draw = ImageDraw.Draw(img)
    title_font = _bold_font(28)
    h2_font = _bold_font(22)
    body_font = _font(16)
    small_font = _font(13)
    table_font = _font(15)
    table_hdr_font = _bold_font(15)

    margin = 60
    y = 50

    # Header line
    draw.text((margin, y), "ACME Corp.", fill="#6b7280", font=small_font)
    draw.text((w - margin - 180, y), "Confidential — Draft v2.1", fill="#6b7280", font=small_font)
    y += 30
    draw.line([(margin, y), (w - margin, y)], fill="#d1d5db", width=1)
    y += 30

    # Title
    draw.text((margin, y), "System Requirements Specification", fill="#111827", font=title_font)
    y += 50
    draw.text((margin, y), "Chapter 3: Non-Functional Requirements", fill="#374151", font=h2_font)
    y += 50

    # Paragraph 1
    p1 = (
        "This chapter defines the non-functional requirements (NFRs) for the ShopApp "
        "e-commerce platform. These requirements apply to the production environment "
        "running on AWS ap-northeast-1 and must be met before the GA release scheduled "
        "for 2026-Q3."
    )
    y = _draw_wrapped(draw, p1, margin, y, w - 2 * margin, body_font)
    y += 30

    # Section 3.1
    draw.text((margin, y), "3.1 Performance Requirements", fill="#1f2937", font=h2_font)
    y += 40

    p2 = (
        "All API endpoints must meet the following latency and throughput targets "
        "under normal operating conditions (defined as < 80% CPU utilization across "
        "the ECS cluster)."
    )
    y = _draw_wrapped(draw, p2, margin, y, w - 2 * margin, body_font)
    y += 20

    # Bullet list
    bullets = [
        "API response time (p95): <= 200 ms",
        "API response time (p99): <= 500 ms",
        "Search query throughput: >= 500 requests/sec",
        "Database query timeout: 3 seconds (hard limit)",
        "Page load time (LCP): <= 1.5 seconds on 4G network",
        "Batch processing (nightly): complete within 2 hours",
    ]
    for bullet in bullets:
        draw.text((margin + 20, y), "\u2022", fill="#374151", font=body_font)
        draw.text((margin + 40, y), bullet, fill="#374151", font=body_font)
        y += 28
    y += 20

    # Section 3.2
    draw.text((margin, y), "3.2 Availability & Reliability", fill="#1f2937", font=h2_font)
    y += 40

    p3 = (
        "The system must achieve the uptime and recovery targets listed below. "
        "Planned maintenance windows (Sunday 02:00-06:00 JST) are excluded from "
        "the uptime calculation."
    )
    y = _draw_wrapped(draw, p3, margin, y, w - 2 * margin, body_font)
    y += 20

    # Table
    headers = ["Requirement", "Target", "Priority"]
    rows = [
        ["Monthly uptime", ">= 99.9%", "Must"],
        ["RTO (Recovery Time Objective)", "<= 15 minutes", "Must"],
        ["RPO (Recovery Point Objective)", "<= 5 minutes", "Must"],
        ["Failover (AZ-level)", "Automatic", "Should"],
        ["Data backup retention", "90 days", "Must"],
    ]
    col_w = [380, 200, 120]
    table_x = margin
    row_h = 32
    # header
    draw.rectangle([table_x, y, table_x + sum(col_w), y + row_h], fill="#374151")
    cx = table_x
    for i, hdr in enumerate(headers):
        draw.text((cx + 10, y + 8), hdr, fill="white", font=table_hdr_font)
        cx += col_w[i]
    y += row_h
    # rows
    for r, row in enumerate(rows):
        bg = "#f9fafb" if r % 2 == 0 else "white"
        draw.rectangle([table_x, y, table_x + sum(col_w), y + row_h], fill=bg, outline="#e5e7eb")
        cx = table_x
        for i, val in enumerate(row):
            draw.text((cx + 10, y + 8), val, fill="#1f2937", font=table_font)
            cx += col_w[i]
        y += row_h
    draw.rectangle([table_x, y - row_h * len(rows) - row_h, table_x + sum(col_w), y], outline="#9ca3af", width=1)
    y += 30

    # Footer
    draw.line([(margin, h - 60), (w - margin, h - 60)], fill="#d1d5db", width=1)
    draw.text((margin, h - 50), "Page 12", fill="#9ca3af", font=small_font)
    draw.text((w - margin - 200, h - 50), "Last updated: 2026-03-15", fill="#9ca3af", font=small_font)

    img.save(path, "PNG")


def _draw_wrapped(draw, text: str, x: int, y: int, max_w: int, font) -> int:
    """Draw word-wrapped text, return y after the last line."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        tw, _ = _text_size(draw, test, font)
        if tw > max_w:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    line_h = _text_size(draw, "Ag", font)[1] + 6
    for line in lines:
        draw.text((x, y), line, fill="#374151", font=font)
        y += line_h
    return y


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    make_mixed_slide(IMAGES / "01_mixed_slide.png")
    make_ui_change_rfp(IMAGES / "02_ui_change.png")
    make_complex_architecture(IMAGES / "03_complex_arch.png")
    make_text_document(IMAGES / "04_text_document.png")
    for p in sorted(IMAGES.glob("*.png")):
        print(f"wrote {p.relative_to(WORKSPACE)} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
