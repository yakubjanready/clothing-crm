"""Render terminal-style PNG from a stdin text (one-off, faza N dalillari)."""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

text = sys.stdin.read().rstrip("\n")
out = Path(sys.argv[1])
title = sys.argv[2] if len(sys.argv) > 2 else ""

font_paths = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
]
font = None
for p in font_paths:
    try:
        font = ImageFont.truetype(p, 14)
        break
    except OSError:
        continue
font = font or ImageFont.load_default()
title_font = ImageFont.truetype(font_paths[0], 16) if font.path == font_paths[0] else font

lines = text.splitlines() or [""]
pad_x, pad_y = 16, 14
line_h = 20
title_h = 30 if title else 0

# Width: longest line
tmp_img = Image.new("RGB", (10, 10))
tmp_draw = ImageDraw.Draw(tmp_img)
max_w = max(tmp_draw.textlength(ln, font=font) for ln in lines) if lines else 0
width = max(800, int(max_w) + 2 * pad_x)
height = title_h + len(lines) * line_h + 2 * pad_y

img = Image.new("RGB", (width, height), (24, 24, 27))
draw = ImageDraw.Draw(img)

if title:
    draw.rectangle([(0, 0), (width, title_h)], fill=(39, 39, 42))
    draw.text((pad_x, 6), title, font=title_font, fill=(244, 244, 245))

y = title_h + pad_y
for ln in lines:
    color = (220, 220, 220)
    if ln.startswith(("PASS", "ok", "OK")) or "passed" in ln or "✓" in ln:
        color = (134, 239, 172)
    elif ln.startswith(("FAIL", "ERROR", "error")):
        color = (252, 165, 165)
    elif ln.startswith(("#", "//", "---")):
        color = (161, 161, 170)
    elif ln.startswith(("$", ">")):
        color = (147, 197, 253)
    draw.text((pad_x, y), ln, font=font, fill=color)
    y += line_h

img.save(out)
print(f"saved {out} ({width}x{height})")
