#!/usr/bin/env python
"""Generate the 5 test images for the text-vs-image fidelity test.

Image 01 and 02 are reused from samples/ (flowchart, bar chart) by copying.
Image 03, 04, 05 are generated here (table, code screenshot, architecture).

Run once:
    python tests/text_vs_image/generate_test_images.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
IMAGES = ROOT / "images"
WORKSPACE = ROOT.parent.parent  # copilot_demo/


def _font(size: int):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Menlo.ttc",
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
        "/System/Library/Fonts/Courier New.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def reuse_existing(src_name: str, dst_name: str) -> None:
    src = WORKSPACE / "samples" / src_name
    dst = IMAGES / dst_name
    if not src.exists():
        raise FileNotFoundError(f"Expected {src}; run samples/generate_samples.py first")
    shutil.copy(src, dst)


def make_table(path: Path) -> None:
    """Quarterly sales table image."""
    w, h = 800, 360
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(24)
    header_font = _font(20)
    cell_font = _font(18)

    draw.text((20, 15), "Q1 2026 Regional Sales (million JPY)", fill="black", font=title_font)

    headers = ["Region", "Jan", "Feb", "Mar", "Total"]
    rows = [
        ["Tokyo", "120", "85", "160", "365"],
        ["Osaka", "90", "70", "110", "270"],
        ["Nagoya", "60", "55", "75", "190"],
        ["Fukuoka", "45", "40", "65", "150"],
    ]
    col_widths = [180, 120, 120, 120, 140]
    x_start = 30
    y_start = 70
    row_h = 50

    # header row
    x = x_start
    draw.rectangle(
        [x_start, y_start, x_start + sum(col_widths), y_start + row_h],
        fill="#4a90e2",
    )
    for i, header in enumerate(headers):
        bbox = draw.textbbox((0, 0), header, font=header_font)
        tw = bbox[2] - bbox[0]
        cx = x + (col_widths[i] - tw) / 2
        cy = y_start + (row_h - (bbox[3] - bbox[1])) / 2 - 2
        draw.text((cx, cy), header, fill="white", font=header_font)
        x += col_widths[i]

    # data rows
    for r, row in enumerate(rows):
        y = y_start + row_h * (r + 1)
        bg = "#f5f5f5" if r % 2 == 0 else "white"
        draw.rectangle(
            [x_start, y, x_start + sum(col_widths), y + row_h],
            fill=bg,
        )
        x = x_start
        for i, val in enumerate(row):
            bbox = draw.textbbox((0, 0), val, font=cell_font)
            tw = bbox[2] - bbox[0]
            if i == 0:
                cx = x + 15  # left-align region name
            else:
                cx = x + (col_widths[i] - tw) / 2
            cy = y + (row_h - (bbox[3] - bbox[1])) / 2 - 2
            draw.text((cx, cy), val, fill="black", font=cell_font)
            x += col_widths[i]

    # outer border + grid
    total_w = sum(col_widths)
    total_h = row_h * (len(rows) + 1)
    draw.rectangle(
        [x_start, y_start, x_start + total_w, y_start + total_h],
        outline="black",
        width=2,
    )
    for r in range(1, len(rows) + 1):
        y = y_start + row_h * r
        draw.line(
            [(x_start, y), (x_start + total_w, y)], fill="#cccccc", width=1
        )
    cx = x_start
    for w_col in col_widths[:-1]:
        cx += w_col
        draw.line(
            [(cx, y_start), (cx, y_start + total_h)], fill="#cccccc", width=1
        )

    img.save(path, "PNG")


def make_code(path: Path) -> None:
    """Python code snippet rendered as a screenshot-style image."""
    w, h = 760, 360
    img = Image.new("RGB", (w, h), "#1e1e1e")
    draw = ImageDraw.Draw(img)
    mono = _mono_font(18)
    label = _font(14)

    code_lines = [
        "def fibonacci(n: int) -> int:",
        '    """Return the n-th Fibonacci number."""',
        "    if n < 2:",
        "        return n",
        "    a, b = 0, 1",
        "    for _ in range(n - 1):",
        "        a, b = b, a + b",
        "    return b",
        "",
        "result = fibonacci(10)",
        "print(f'F(10) = {result}')",
    ]

    # title bar
    draw.rectangle([0, 0, w, 30], fill="#333333")
    draw.text((15, 7), "fibonacci.py — Python", fill="#cccccc", font=label)

    y = 50
    line_h = 26
    for i, line in enumerate(code_lines):
        # very rough syntax coloring
        color = "#d4d4d4"
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("return") or stripped.startswith("for ") or stripped.startswith("if "):
            color = "#569cd6"
        elif stripped.startswith('"""'):
            color = "#6a9955"
        elif stripped.startswith("print"):
            color = "#dcdcaa"
        draw.text((25, y + i * line_h), line, fill=color, font=mono)

    img.save(path, "PNG")


def make_architecture(path: Path) -> None:
    """Simple 4-component architecture diagram."""
    w, h = 900, 500
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(24)
    box_font = _font(20)
    edge_font = _font(14)

    draw.text((20, 15), "Web Application Architecture", fill="black", font=title_font)

    boxes = {
        "client": (60, 200, 220, 290, "Web Client\n(Browser)", "#d0e7ff"),
        "api":    (340, 200, 500, 290, "API Server\n(FastAPI)", "#fff1c0"),
        "db":     (620, 100, 820, 190, "Database\n(PostgreSQL)", "#c8e6c9"),
        "cache":  (620, 300, 820, 390, "Cache\n(Redis)",        "#ffcdd2"),
    }
    for key, (x1, y1, x2, y2, label, fill) in boxes.items():
        if key == "db":
            # cylinder-ish for DB
            draw.ellipse([x1, y1 - 12, x2, y1 + 12], fill=fill, outline="black", width=2)
            draw.rectangle([x1, y1, x2, y2], fill=fill, outline="black", width=2)
            draw.line([x1, y1, x1, y2], fill="black", width=2)
            draw.line([x2, y1, x2, y2], fill="black", width=2)
            draw.ellipse([x1, y2 - 12, x2, y2 + 12], fill=fill, outline="black", width=2)
        else:
            draw.rectangle([x1, y1, x2, y2], fill=fill, outline="black", width=2)
        lines = label.split("\n")
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=box_font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            cx = (x1 + x2) / 2 - tw / 2
            cy = (y1 + y2) / 2 - (len(lines) * th) / 2 + i * th
            draw.text((cx, cy), line, fill="black", font=box_font)

    # edges
    def arrow(p1, p2, label):
        draw.line([p1, p2], fill="black", width=2)
        # arrowhead
        import math
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        ang = math.atan2(dy, dx)
        ah = 12
        ax = p2[0] - ah * math.cos(ang - math.radians(20))
        ay = p2[1] - ah * math.sin(ang - math.radians(20))
        bx = p2[0] - ah * math.cos(ang + math.radians(20))
        by = p2[1] - ah * math.sin(ang + math.radians(20))
        draw.polygon([p2, (ax, ay), (bx, by)], fill="black")
        # label
        mx = (p1[0] + p2[0]) / 2
        my = (p1[1] + p2[1]) / 2 - 15
        draw.text((mx - 30, my), label, fill="#444444", font=edge_font)

    arrow((220, 245), (340, 245), "HTTPS")
    arrow((500, 230), (620, 145), "SQL")
    arrow((500, 260), (620, 345), "GET/SET")

    # legend
    draw.text(
        (20, 450),
        "Legend: blue=client, yellow=api, green=db, red=cache",
        fill="#666666",
        font=edge_font,
    )

    img.save(path, "PNG")


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    reuse_existing("diagram.png", "01_flowchart.png")
    reuse_existing("chart.png", "02_barchart.png")
    make_table(IMAGES / "03_table.png")
    make_code(IMAGES / "04_code.png")
    make_architecture(IMAGES / "05_architecture.png")
    for p in sorted(IMAGES.glob("*.png")):
        print(f"wrote {p.relative_to(WORKSPACE)} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
