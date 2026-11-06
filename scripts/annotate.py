#!/usr/bin/env python3
"""Draws a red box around the defect on a screenshot, and changes nothing else.

  python3 annotate.py screenshot.jpg output.jpg x0,y0,x1,y1 [x0,y0,x1,y1 ...]

Coordinates are image pixels. Check the result by eye: a misplaced box is worse than no box.
Screenshots from the built-in browser: the "desktop" preset gives a 1024 px window and an 800 px image
(page coordinates x 0.78125)."""
import sys
from PIL import Image, ImageDraw

src, dst, *boxes = sys.argv[1:]
im = Image.open(src).convert("RGB")
d = ImageDraw.Draw(im)
for b in boxes:
    x0, y0, x1, y1 = map(float, b.split(","))
    d.rounded_rectangle([x0, y0, x1, y1], radius=6, outline=(217, 48, 37), width=4)
im.save(dst, quality=88)
print(dst, im.size)
