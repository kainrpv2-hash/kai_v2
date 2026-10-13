"""Toon (Storm-4-style) texture set for the Garry's Mod variant -> ./tex_gmod

- clump_col.png : opaque charcoal strand texture for the geometric thread clumps (tiles both ways)
- body_col.png  : body texture lifted to charcoal (never pure black, so the cel ramp and rim light read)
- fur_atlas_col.png : fringe-fibre cards, same lift
- masks: see mask_vector.py (redrawn from the ep.84 frame, + cracked variant)
- outline_col.png : 4x4 ink black
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "tex_low")
OUT = os.path.join(HERE, "tex_gmod")
os.makedirs(OUT, exist_ok=True)
random.seed(9)

BASE = np.array([32, 34, 42], float)       # charcoal, slightly blue-grey
STRAND_HI = np.array([88, 94, 112], float)  # painted strand highlight
STRAND_LO = np.array([16, 17, 22], float)   # ink gaps between strands


def clump_texture(size=512, ss=2):
    S = size * ss
    im = Image.new("RGB", (S, S), tuple(BASE.astype(int)))
    d = ImageDraw.Draw(im)
    # vertical strands (v runs root -> tip), wrapped horizontally so the tube seam disappears
    for layer, (n, col, wmin, wmax) in enumerate([(70, STRAND_LO, 3, 7), (55, STRAND_HI * 0.7, 2, 4), (35, STRAND_HI, 1.5, 3)]):
        for _ in range(n):
            x = random.uniform(0, S)
            y0 = random.uniform(-0.2, 0.3) * S
            L = random.uniform(0.5, 1.2) * S
            pts = []
            ph = (random.uniform(1.0, 2.5), random.uniform(0, 6), random.uniform(-0.02, 0.02))
            for k in range(30):
                t = k / 29
                pts.append((x + math.sin(t * ph[0] + ph[1]) * S * 0.006 + t * ph[2] * S, y0 + t * L))
            w = random.uniform(wmin, wmax) * ss
            c = tuple(int(v) for v in col * random.uniform(0.85, 1.1))
            for ox in (-S, 0, S):
                for oy in (-S, 0, S):
                    d.line([(px + ox, py + oy) for px, py in pts], fill=c, width=int(w))
    im = im.filter(ImageFilter.GaussianBlur(0.6 * ss)).resize((size, size), Image.LANCZOS)
    # darker towards the root (v=0 is the image bottom in Blender UVs) like the anime's ink at the base
    a = np.asarray(im).astype(float)
    ramp = np.linspace(1.0, 0.72, size)[::-1][:, None, None]  # bottom rows darker
    a = a * ramp
    Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, "clump_col.png"), optimize=True)


def lift_rgb(a):
    # map the dark realistic range (5..60) onto charcoal BASE..STRAND_HI keeping the strand detail
    t = np.clip((a.mean(-1, keepdims=True) - 6) / 55, 0, 1)
    return BASE * (1 - t) + STRAND_HI * t


def body_texture():
    a = np.asarray(Image.open(os.path.join(SRC, "body_col.png")).convert("RGB")).astype(float)
    Image.fromarray(lift_rgb(a).clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, "body_col.png"), optimize=True)


def fur_texture():
    im = Image.open(os.path.join(SRC, "fur_atlas_col.png")).convert("RGBA")
    a = np.asarray(im).astype(float)
    rgb = lift_rgb(a[..., :3])
    out = np.concatenate([rgb, a[..., 3:4]], -1)
    Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "fur_atlas_col.png"), optimize=True)


def crack(im, seed):
    rng = random.Random(seed)
    W, H = im.size
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, H / 2
    for b in range(3):
        ang = rng.uniform(0, 2 * math.pi)
        x, y = cx + math.cos(ang) * W * 0.32, cy + math.sin(ang) * H * 0.38
        heading = ang + math.pi + rng.uniform(-0.5, 0.5)
        pts = [(x, y)]
        for k in range(rng.randint(7, 11)):
            heading += rng.uniform(-0.7, 0.7)
            step = rng.uniform(0.025, 0.05) * W
            x, y = x + math.cos(heading) * step, y + math.sin(heading) * step
            pts.append((x, y))
            if rng.random() < 0.35:  # small side branch
                bh = heading + rng.choice((-1, 1)) * rng.uniform(0.6, 1.2)
                bx, by = x + math.cos(bh) * step * 1.4, y + math.sin(bh) * step * 1.4
                d.line([(x, y), (bx, by)], fill=(46, 42, 44), width=3)
        d.line(pts, fill=(36, 32, 34), width=5, joint="curve")
        d.line(pts, fill=(120, 116, 118), width=1)
    return im


def masks():
    for i, kind in enumerate(("fire", "wind", "lightning", "water")):
        im = Image.open(os.path.join(SRC, f"mask_{kind}_col.jpg")).convert("RGB")
        im.save(os.path.join(OUT, f"mask_{kind}_col.jpg"), quality=93)
        crack(im.copy(), 100 + i).save(os.path.join(OUT, f"mask_{kind}_cracked_col.jpg"), quality=93)


def outline():
    Image.new("RGB", (4, 4), (6, 6, 8)).save(os.path.join(OUT, "outline_col.png"))


clump_texture()
body_texture()
fur_texture()
# masks (and their cracked variant) are drawn by mask_vector.py
outline()
print("tex_gmod ok", sorted(os.listdir(OUT)))
