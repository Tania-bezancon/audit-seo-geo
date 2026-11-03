#!/usr/bin/env python3
"""Encadre en rouge le défaut sur une capture, sans rien modifier d'autre.

  python3 annotate.py capture.jpg sortie.jpg x0,y0,x1,y1 [x0,y0,x1,y1 …]

Coordonnées en pixels de l'image. Vérifier le résultat à l'œil : un cadre mal placé est pire que pas de cadre.
Captures du navigateur intégré : le préréglage « desktop » donne une fenêtre de 1024 px et une image de 800 px
(coordonnées de la page × 0,78125)."""
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
