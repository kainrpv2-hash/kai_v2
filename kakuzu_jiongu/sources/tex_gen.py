"""Procedural textures for Kakuzu's Jiongu creatures: hair-card atlas + tileable thread body texture.

Outputs (in ./tex):
  fur_atlas_col.png  RGBA  (sRGB colour + alpha coverage), 8 card variants side by side, root at the bottom
  fur_atlas_nrm.png  RGB   tangent-space normal map (OpenGL / glTF convention, +Y up)
  body_col.png       RGB   tileable black thread mass
  body_nrm.png       RGB   tileable normal map
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

random.seed(1337)
np.random.seed(1337)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tex")
os.makedirs(OUT, exist_ok=True)


def height_to_normal(h, strength):
    """h: float32 HxW in [0,1]. Returns uint8 RGB normal map (OpenGL convention, wraps at edges)."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    nx = -dx * strength
    ny = dy * strength  # image rows go down, OpenGL green points up
    nz = np.ones_like(h)
    n = np.stack([nx, ny, nz], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return ((n * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)


def strand_path(x0, y0, length, angle0, steps, kink, drift):
    """Polyline growing 'up' (negative y) from (x0, y0)."""
    pts = [(x0, y0)]
    a = angle0
    x, y = x0, y0
    seg = length / steps
    for i in range(steps):
        a += random.gauss(0, drift)
        # wiry threads: occasional sharp kinks like the anime line work
        if random.random() < kink:
            a += random.choice((-1, 1)) * random.uniform(0.25, 0.6)
        a = max(-0.9, min(0.9, a))
        x += math.sin(a) * seg
        y -= math.cos(a) * seg
        pts.append((x, y))
    return pts


# ---------------------------------------------------------------- fur card atlas
def make_fur_atlas(size=2048, cols=8, ss=2):
    W = H = size * ss
    cw = W // cols
    col = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hgt = Image.new("L", (W, H), 0)
    dc = ImageDraw.Draw(col)
    dh = ImageDraw.Draw(hgt)
    for c in range(cols):
        cx = c * cw + cw / 2
        wisp = c >= cols - 2          # last two columns: sparse thin wisps for silhouettes
        n = random.randint(40, 55) if wisp else random.randint(120, 150)
        spread = 0.16 if wisp else 0.24
        strands = []
        for _ in range(n):
            x0 = random.gauss(cx, cw * spread)
            x0 = min(max(x0, c * cw + cw * 0.08), (c + 1) * cw - cw * 0.08)
            y0 = H - random.uniform(0, 0.06) * H
            L = random.uniform(0.55, 0.98) * H if not wisp else random.uniform(0.7, 0.98) * H
            a0 = (x0 - cx) / cw * random.uniform(0.1, 0.5) + random.gauss(0, 0.08)
            pts = strand_path(x0, y0, L, a0, 48, kink=0.06, drift=0.05)
            # stop the strand where it would leave its column (no clamped vertical lines)
            lo, hi = c * cw + 5 * ss, (c + 1) * cw - 5 * ss
            cut = len(pts)
            for k, (px, py) in enumerate(pts):
                if px < lo or px > hi or py < 4 * ss:
                    cut = k
                    break
            pts = pts[:cut]
            if len(pts) < 6:
                continue
            w0 = random.uniform(2.2, 4.8) * ss * (0.75 if wisp else 1.0)
            tone = random.uniform(0.0, 1.0)
            strands.append((pts, w0, tone, random.uniform(0.35, 1.0)))
        # draw back-to-front: darker/lower strands first
        strands.sort(key=lambda s: s[3])
        for pts, w0, tone, hz in strands:
            m = len(pts) - 1
            for i in range(m):
                t = i / m
                w = max(0.6 * ss, w0 * (1 - t) ** 0.7)
                # AO towards the root, faint grey sheen in the middle, darker tips
                ao = 0.45 + 0.55 * min(1.0, t * 2.2)
                sheen = math.exp(-((t - 0.45) ** 2) / 0.05) * 0.6
                base = 10 + tone * 22 + sheen * 28 * tone
                v = int(base * ao)
                g = int(v * 1.0)
                b = int(v * 1.12) + 1      # very slightly cool, like the anime's blue-black ink
                a = int(255 * min(1.0, 1.15 - 0.35 * t))
                dc.line([pts[i], pts[i + 1]], fill=(v, g, b, a), width=int(round(w)))
                dh.line([pts[i], pts[i + 1]], fill=int(255 * hz * 0.6), width=int(round(w)))
                dh.line([pts[i], pts[i + 1]], fill=int(255 * hz), width=max(1, int(round(w * 0.45))))
    col = col.resize((size, size), Image.LANCZOS)
    hgt = hgt.filter(ImageFilter.GaussianBlur(1.0 * ss)).resize((size, size), Image.LANCZOS)
    # dilate colour under transparent pixels so mipmaps don't fringe white/black
    arr = np.asarray(col).astype(np.float32)
    rgb, a = arr[..., :3], arr[..., 3:4] / 255.0
    blur_rgb = np.asarray(Image.fromarray(rgb.astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32)
    blur_a = np.asarray(Image.fromarray((a[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32)[..., None] / 255.0
    fill = np.where(blur_a > 1e-3, blur_rgb / np.maximum(blur_a, 1e-3), 12.0)
    rgb = np.where(a > 0.02, rgb / np.maximum(a, 1e-3), fill)
    out = np.concatenate([rgb.clip(0, 255), a * 255], axis=-1).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(os.path.join(OUT, "fur_atlas_col.png"), optimize=True)
    h = np.asarray(hgt).astype(np.float32) / 255.0
    Image.fromarray(height_to_normal(h, 6.0), "RGB").save(os.path.join(OUT, "fur_atlas_nrm.png"), optimize=True)


# ---------------------------------------------------------------- body texture (tileable)
def make_body(size=1024, ss=2):
    W = size * ss
    base = np.full((W, W, 3), 7, np.uint8)
    col = Image.fromarray(base, "RGB")
    hgt = Image.new("L", (W, W), 0)
    dc = ImageDraw.Draw(col)
    dh = ImageDraw.Draw(hgt)
    for layer in range(3):
        n = (900, 1100, 700)[layer]
        for _ in range(n):
            x0, y0 = random.uniform(0, W), random.uniform(0, W)
            L = random.uniform(0.08, 0.35) * W
            a0 = random.gauss(0, 0.5) + (math.pi if random.random() < 0.5 else 0)
            pts = strand_path(x0, y0, L, a0, 24, kink=0.08, drift=0.06)
            w0 = random.uniform(1.6, 3.6) * ss
            tone = random.uniform(0, 1) * (0.5 + 0.25 * layer)
            hz = 0.25 + 0.3 * layer + random.uniform(0, 0.2)
            for ox in (-W, 0, W):
                for oy in (-W, 0, W):
                    p = [(x + ox, y + oy) for x, y in pts]
                    if max(x for x, _ in p) < 0 or min(x for x, _ in p) > W or max(y for _, y in p) < 0 or min(y for _, y in p) > W:
                        continue
                    for i in range(len(p) - 1):
                        t = i / (len(p) - 1)
                        w = max(ss, w0 * (1 - 0.6 * t))
                        v = int(9 + tone * 30 * math.sin(math.pi * t) + layer * 3)
                        dc.line([p[i], p[i + 1]], fill=(v, v, int(v * 1.12) + 1), width=int(round(w)))
                        dh.line([p[i], p[i + 1]], fill=int(255 * hz * 0.7), width=int(round(w)))
                        dh.line([p[i], p[i + 1]], fill=int(255 * hz), width=max(1, int(round(w * 0.45))))
    col = col.resize((size, size), Image.LANCZOS)
    col.save(os.path.join(OUT, "body_col.png"), optimize=True)
    hgt = hgt.filter(ImageFilter.GaussianBlur(1.2 * ss)).resize((size, size), Image.LANCZOS)
    h = np.asarray(hgt).astype(np.float32) / 255.0
    Image.fromarray(height_to_normal(h, 5.0), "RGB").save(os.path.join(OUT, "body_nrm.png"), optimize=True)


if __name__ == "__main__":
    make_fur_atlas()
    make_body()
    print("textures ok")
