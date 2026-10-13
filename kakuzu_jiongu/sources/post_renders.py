"""Turn the PNG renders into delivery JPEGs + a 2x2 mask sheet, for the viewer and the delivery folder."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "renders")
dests = [os.path.join(HERE, "viewer", "renders"), sys.argv[1] if len(sys.argv) > 1 else None]

out = {}
for k in ("katon", "futon", "raiton", "suiton"):
    p = os.path.join(R, f"hero_{k}.png")
    if os.path.exists(p):
        out[f"hero_{k}"] = Image.open(p).convert("RGB")
g = os.path.join(R, "group_ep84.png")
if os.path.exists(g):
    out["group_ep84"] = Image.open(g).convert("RGB")
masks = [os.path.join(R, f"mask_{k}.png") for k in ("katon", "futon", "raiton", "suiton")]
if all(os.path.exists(m) for m in masks):
    tiles = [Image.open(m).convert("RGB") for m in masks]
    w, h = tiles[0].size
    sheet = Image.new("RGB", (w * 4 + 30, h), (15, 13, 17))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * (w + 10), 0))
    out["masks"] = sheet

for d in dests:
    if not d:
        continue
    os.makedirs(d, exist_ok=True)
    for name, im in out.items():
        im.save(os.path.join(d, f"{name}.jpg"), quality=90, optimize=True, progressive=True)
print("saved", sorted(out))
