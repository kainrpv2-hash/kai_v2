"""Clean vector redraw of the four Jiongu masks, positioned point by point on the ep.84 HD frame.

Coordinates below are in pixels of the native crop (mask_trace.BOXES), measured on gridded zooms of the frame.
The silhouette itself comes from the frame (mask_trace), smoothed. Output per variant dir:
  mask_<kind>_col.jpg, mask_<kind>_sil.png, mask_<kind>_meta.json  (+ cracked variant for tex_gmod)
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mask_trace as mt  # noqa: E402

C = 4096          # drawing canvas (supersampled), saved at 2048 / 1024
PAPER = (221, 218, 222)
SHADE = (178, 173, 184)
INK = (24, 22, 26)
RED = (134, 30, 52)
NAVY = (30, 52, 98)
STEEL = (122, 152, 172)
OCHRE = (228, 178, 98)
MOUTH = (40, 34, 40)
TOOTH = (238, 236, 234)


def catmull(pts, n=12, closed=False):
    P = [np.array(p, float) for p in pts]
    if closed:
        P = [P[-1]] + P + [P[0], P[1]]
    else:
        P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return out


SNAP = {}


def ref_skeleton(kind):
    """Centre-lines of the dark strokes of the reference (native-pixel coordinates, sub-pixel)."""
    if kind in SNAP:
        return SNAP[kind]
    from scipy.spatial import cKDTree
    from skimage.morphology import skeletonize
    (x0, y0, x1, y1), _ = mt.BOXES[kind]
    crop = Image.open(mt.FRAME).convert("RGB").crop((x0, y0, x1, y1))
    w, h = crop.size
    U = 8
    big = np.asarray(crop.resize((w * U, h * U), Image.BICUBIC).filter(ImageFilter.GaussianBlur(U * 0.4))).astype(float)
    L = big.mean(-1)
    r, g, b = big[..., 0], big[..., 1], big[..., 2]
    coloured = ((r - g > 25) & (r - b > 12)) | ((b - r > 10) & (L > 50)) | ((r > 150) & (r - b > 70))
    ink = (L < 105) & ~coloured
    # only strokes inside the mask: exclude the dark background by requiring bright surroundings nearby
    bright = ndi.maximum_filter(L, size=U * 5) > 160
    ink &= bright
    sk = skeletonize(ink)
    ys, xs = np.nonzero(sk)
    pts = np.stack([xs / U, ys / U], 1)
    SNAP[kind] = (cKDTree(pts), pts)
    return SNAP[kind]


def snap(kind, pts, radius=2.2):
    tree, P = ref_skeleton(kind)
    out = []
    for p in pts:
        d, i = tree.query(p)
        out.append(tuple(P[i]) if d <= radius else tuple(p))
    # light smoothing so snapped points don't zig-zag
    a = np.array(out)
    if len(a) > 3:
        a[1:-1] = 0.25 * a[:-2] + 0.5 * a[1:-1] + 0.25 * a[2:]
    return [tuple(q) for q in a]


class Painter:
    def __init__(self, kind):
        self.kind = kind
        sil, ox, oy, side, Hs = mt.silhouette(kind)
        self.ox, self.oy, self.side = ox, oy, side
        self.k = C / side
        sil_c = Image.fromarray((sil * 255).astype(np.uint8)).resize((C, C), Image.LANCZOS)
        self.sil = np.asarray(sil_c.filter(ImageFilter.GaussianBlur(2))).astype(float) / 255
        self.im = Image.new("RGB", (C, C), PAPER)
        self.d = ImageDraw.Draw(self.im)
        self.Hs = Hs

    def p(self, x, y):
        return ((self.ox + x * mt.UP) * self.k, (self.oy + y * mt.UP) * self.k)

    def w(self, native):
        return max(1, int(round(native * 1.22 * mt.UP * self.k)))

    def stroke(self, pts, width=1.9, smooth=True, fill=INK, snap_to_ref=True):
        if snap_to_ref:
            pts = snap(self.kind, pts)
        pts = catmull(pts) if smooth and len(pts) > 2 else pts
        P = [self.p(*q) for q in pts]
        W = self.w(width)
        self.d.line(P, fill=fill, width=W, joint="curve")
        r = W / 2
        for x, y in (P[0], P[-1]):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def poly(self, pts, fill, outline=INK, width=1.6, smooth=True):
        pts = catmull(pts, closed=True) if smooth else pts
        P = [self.p(*q) for q in pts]
        self.d.polygon(P, fill=fill)
        if outline:
            self.d.line(P + [P[0]], fill=outline, width=self.w(width), joint="curve")

    def ring(self, cx, cy, rx, ry=None, width=1.9, fill=PAPER):
        ry = ry or rx
        x0, y0 = self.p(cx - rx, cy - ry)
        x1, y1 = self.p(cx + rx, cy + ry)
        self.d.ellipse([x0, y0, x1, y1], fill=fill, outline=INK, width=self.w(width))

    def dot(self, cx, cy, r):
        x0, y0 = self.p(cx - r, cy - r)
        x1, y1 = self.p(cx + r, cy + r)
        self.d.ellipse([x0, y0, x1, y1], fill=INK)

    def tri(self, a, b, c, fill=TOOTH, width=1.0):
        P = [self.p(*q) for q in (a, b, c)]
        self.d.polygon(P, fill=fill)
        self.d.line(P + [P[0]], fill=INK, width=self.w(width), joint="curve")

    def rim_shadow(self, depth=0.075, extra=None):
        """Anime cel shadow: a band along the lower rim of the silhouette (light from above)."""
        s = self.sil > 0.5
        shift = int(depth * self.Hs * self.k)
        up = np.zeros_like(s)
        up[:-shift] = s[shift:]
        band = s & ~up
        if extra is not None:
            band |= extra
        band = ndi.gaussian_filter(band.astype(float), 3) > 0.5
        a = np.asarray(self.im).astype(float)
        a[band] = a[band] * 0.0 + np.array(SHADE)
        self.im = Image.fromarray(a.astype(np.uint8))
        self.d = ImageDraw.Draw(self.im)

    def finish(self):
        a = np.asarray(self.im).astype(float)
        rng = np.random.default_rng(1)
        a += ndi.gaussian_filter(rng.normal(0, 1, a.shape[:2]), 1.5)[..., None] * 2.5
        out = np.where(self.sil[..., None] > 0.02, a, np.array([118, 114, 122.0]))
        col = Image.fromarray(out.clip(0, 255).astype(np.uint8)).resize((2048, 2048), Image.LANCZOS)
        sil = Image.fromarray((self.sil * 255).astype(np.uint8)).resize((2048, 2048), Image.LANCZOS)
        return col, sil


# ------------------------------------------------------------------------------------------ FIRE
def fire():
    m = Painter("fire")
    m.rim_shadow(0.07)
    # crimson lips + dark opening + square teeth
    m.poly([(29, 90), (31, 86.5), (36, 84), (45, 82), (55, 80.5), (65, 81), (74, 82.5), (82, 85), (86, 88), (88, 92),
            (87.5, 97), (85, 100), (78, 100.5), (65, 101.5), (52, 102.5), (40, 103.5), (32, 103.5), (29.5, 100), (28.5, 95)],
           RED, INK, 1.4)
    m.poly([(33, 89), (40, 87.3), (50, 86.3), (60, 85.8), (70, 86.2), (78, 87.2), (83, 89.5), (83.5, 94), (81, 96.5),
            (70, 97.2), (58, 97.6), (45, 98), (35, 98), (32.6, 95), (32.6, 91)], MOUTH, None)
    for cx, w, h in ((37.3, 3.8, 4.2), (43.6, 4.8, 4.8), (51, 4.4, 5.2), (59, 5.2, 5.0), (67.4, 5.0, 4.8), (75.8, 4.4, 4.4)):
        x0, y0 = m.p(cx - w / 2, 92.2 - h / 2)
        x1, y1 = m.p(cx + w / 2, 92.2 + h / 2)
        m.d.rounded_rectangle([x0, y0, x1, y1], radius=m.w(1.0), fill=TOOTH)
    # goggle band
    m.stroke([(24.5, 47.5), (32, 43), (40, 40.2), (50, 38.4), (58, 37.6), (66, 38.4), (75, 40.8), (83, 45), (89.5, 50.5)])
    m.stroke([(23.8, 72.2), (28, 73), (32, 72.6), (35, 70.6), (37.5, 66.6), (39.6, 63), (43, 61), (50, 59.6), (57, 59),
              (62, 60), (65, 62.6), (67, 66), (69, 68.2), (73, 69), (80, 68.8), (86, 68), (89, 66), (90, 60), (90, 52)])
    m.ring(35.2, 57, 3.7, 5.1, 1.9)
    m.ring(74.4, 54, 4.3, 5.7, 1.9)
    m.dot(42.6, 70, 2.3)
    m.dot(59.6, 68.6, 2.3)
    return m


# ------------------------------------------------------------------------------------------ WIND
def wind():
    m = Painter("wind")
    m.rim_shadow(0.07)
    # navy tear marks at the ends of the beak (filled, then outlined by the beak strokes)
    m.poly([(39.2, 72), (35, 74.6), (31, 78), (28, 82), (26.2, 86), (25.6, 88.2), (31.4, 88.8), (33.2, 85), (35.4, 80.6), (37.6, 76.4)],
           NAVY, None)
    m.poly([(63, 71.6), (68, 73.6), (73.4, 76.6), (78, 80), (81, 84.4), (82.4, 86.6), (76.4, 87), (72.6, 83), (68.6, 78.4), (65.2, 74.6)],
           NAVY, None)
    # beak: two upper edges + the wide V
    m.stroke([(39.6, 71.4), (35, 74), (31, 77.5), (28, 81.5), (26.2, 86)])
    m.stroke([(62.8, 71.4), (68, 73.5), (73.5, 76.5), (78, 80), (81.2, 84.5)])
    m.stroke([(25.6, 88), (30, 89), (37, 91), (44, 94), (52, 97.6)])
    m.stroke([(52, 97.6), (58, 95.2), (65, 92), (72, 89.5), (79, 87), (83, 86)])
    # big hooded arches, eyes at the bottom of each arch, small inward hooks
    m.stroke([(27, 61), (26.5, 55), (27.5, 49), (30.5, 44.6), (35, 42), (39.5, 42.4), (42.6, 46), (44, 52), (44, 58), (43.6, 63.4), (40.6, 64)])
    m.stroke([(27, 60), (29, 62), (31.2, 62.6)])
    m.stroke([(61.6, 63.2), (60.6, 57), (60.6, 51), (62.6, 46), (66.6, 42.6), (72, 41.6), (77.5, 43.6), (81.5, 48), (83, 53), (82.6, 57.6), (80.4, 59.4)])
    m.stroke([(61.6, 62.2), (63.6, 63.6), (65.8, 63.6)])
    m.ring(35.3, 62.8, 3.5, 3.6, 1.9)
    m.ring(71.6, 61.2, 3.7, 3.8, 1.9)
    m.dot(44, 79.6, 2.4)
    m.dot(58, 79.6, 2.4)
    return m


# ------------------------------------------------------------------------------------------ LIGHTNING
def lightning():
    m = Painter("lightning")
    # flaps / lower shell in cel shadow, like the frame (light from above): lower half of the side flaps
    m.rim_shadow(0.08)
    x0, y0 = m.p(0, 97)
    x1, y1 = m.p(164, 160)
    m.d.rectangle([x0, y0, x1, y1], fill=SHADE)
    m.poly([(28, 97), (30, 88), (36, 84), (44, 86), (50, 97)], SHADE, None)
    m.poly([(114, 97), (118, 86), (126, 82), (134, 86), (138, 97)], SHADE, None)
    # horns: the inner U lines
    m.stroke([(39.6, 41), (37.2, 47), (38, 53), (42, 58), (48, 60), (54, 58), (58, 52), (60, 46), (61, 40), (61.4, 34)], 1.9)
    m.stroke([(124.6, 40), (128, 48), (128, 56), (125, 62), (119, 65), (112, 64), (106, 59), (103, 52), (102, 45), (102.2, 38)], 1.9)
    # face plate: fill white over the shadow, thick outline
    face = [(60, 50.5), (72, 49.8), (84, 50), (96, 50.5), (104, 52), (109, 56), (111.6, 64), (112.1, 76), (111.6, 90), (110, 104),
            (107, 115), (101, 123), (92, 128), (82, 129.4), (72, 128.4), (63, 124), (57, 117), (53, 106), (51.4, 92), (51.2, 78),
            (51.8, 66), (54, 57)]
    m.poly(face, PAPER, INK, 2.4)
    # chin shading inside the face
    m.poly([(60, 121), (70, 125.5), (82, 127.4), (93, 126), (102, 120.5), (99, 124.6), (91, 128), (82, 129.2), (72, 128.2), (63, 124)],
           SHADE, None)
    # nose (ochre egg)
    m.poly([(83, 73.2), (87.5, 74.5), (90.5, 78), (92.3, 84), (92.6, 91), (91.3, 97), (88, 100.8), (84, 101.8), (79.5, 100.8),
            (76, 97.5), (74.6, 91), (74.8, 84), (76.5, 78), (79, 74.8)], OCHRE, INK, 1.4)
    # mouth: dark opening, teeth, lips
    m.poly([(58, 100), (66, 100.6), (74, 101.2), (79, 102.4), (84, 103), (90, 102), (96, 100.2), (102, 98.8), (106.5, 98.5),
            (106.8, 104), (104.5, 109.5), (99, 112.6), (90, 113.2), (80, 113.3), (70, 113), (62, 112), (58.5, 108), (57.6, 103.5)],
           MOUTH, None)
    for cx in (67.5, 76.5, 85.5, 94.5):
        m.tri((cx - 3.6, 113.2), (cx + 3.6, 113.2), (cx, 105.4))
    m.tri((59.4, 100.3), (64.4, 100.9), (61.8, 107.6))
    m.tri((100.6, 99.2), (105.6, 98.8), (103.2, 107.2))
    m.stroke([(58, 100), (66, 100.6), (74, 101.4), (79, 102.6)], 1.5)
    m.stroke([(89, 102.2), (96, 100.2), (102, 98.8), (106.5, 98.5)], 1.5)
    m.stroke([(62, 112.4), (70, 113.2), (80, 113.5), (90, 113.4), (99, 112.6), (104.5, 109.5)], 1.5)
    m.stroke([(56, 92), (63, 93.8), (69, 95.8), (74.6, 97.8)], 1.9)
    m.stroke([(93.4, 97.2), (98, 94.2), (102.5, 91.2), (107, 89)], 1.9)
    m.stroke([(56, 92), (53.6, 98), (53.2, 105), (55.5, 111.5), (60, 116.5), (66, 118.6), (75, 119.4), (84, 119.5),
              (92, 119.2), (97, 118.6), (103.5, 116), (107.5, 111), (109.8, 104), (109.6, 96), (107, 89)], 1.9)
    # angry brows / eye sockets
    m.stroke([(55.5, 75.5), (55.8, 69), (57.5, 63), (61, 58.5), (65.5, 56.5), (70.5, 57), (74.5, 60), (76.5, 65), (77.5, 70), (79.4, 73.2)], 2.0)
    m.stroke([(87.2, 73.2), (88.5, 68), (90, 63), (93, 58.5), (97.5, 56.5), (102.5, 57), (106.5, 60), (109, 65.5), (110, 71), (110.5, 76.4)], 2.0)
    m.stroke([(55.5, 75.8), (60, 76.6), (65, 77.2), (71, 77.6)], 2.0)
    m.stroke([(91, 76.8), (96, 77.1), (102, 77.1), (110.5, 76.6)], 2.0)
    m.stroke([(77.2, 70.6), (80, 72.6), (84, 73.1), (88, 72.2)], 1.6)
    m.ring(66.3, 72.2, 3.4, 3.4, 2.0)
    m.ring(97.4, 71.9, 3.4, 3.4, 2.0)
    return m


# ------------------------------------------------------------------------------------------ WATER
def water():
    m = Painter("water")
    m.rim_shadow(0.08)
    # steel-blue crescents beside the eyes, dark outer rim
    left = [(31, 40.6), (29.6, 44), (30, 48), (32.5, 51), (36.5, 53), (40, 53.6), (37.6, 51.2), (35, 48), (33.6, 44.6), (32.6, 41.2)]
    right = [(80.4, 41), (81.4, 45), (80.4, 49), (78, 52.4), (74.6, 54), (71, 54.6), (73.6, 52), (76.4, 49), (78.4, 45), (79.4, 42)]
    m.poly(left, STEEL, None)
    m.poly(right, STEEL, None)
    m.stroke(left[:6], 1.5)
    m.stroke(right[:6], 1.5)
    # thick ring eyes
    m.ring(43, 42, 3.7, 3.7, 1.9)
    m.ring(68.5, 42, 3.7, 3.7, 1.9)
    m.dot(53.6, 57.6, 2.3)
    m.dot(64.6, 57.6, 2.3)
    # the wavy line that makes the lower half read as a bill
    m.stroke([(25.6, 65.6), (30, 64.2), (35, 63.2), (41, 62.6), (46, 63), (50, 64), (53.5, 66), (56.5, 68), (59.5, 68.1),
              (63, 66.6), (68, 65.2), (74, 64.2), (80, 63.6), (85.4, 63.4)], 2.0)
    return m


def crack(col, seed):
    """Cracked variant (heart almost spent): a few dark fissures from the rim inwards."""
    import math
    import random
    im = col.copy()
    rng = random.Random(seed)
    W, H = im.size
    d = ImageDraw.Draw(im)
    for b in range(3):
        ang = rng.uniform(0, 2 * math.pi)
        x, y = W / 2 + math.cos(ang) * W * 0.3, H / 2 + math.sin(ang) * H * 0.34
        heading = ang + math.pi + rng.uniform(-0.5, 0.5)
        pts = [(x, y)]
        for k in range(rng.randint(7, 11)):
            heading += rng.uniform(-0.7, 0.7)
            step = rng.uniform(0.022, 0.045) * W
            x, y = x + math.cos(heading) * step, y + math.sin(heading) * step
            pts.append((x, y))
            if rng.random() < 0.35:
                bh = heading + rng.choice((-1, 1)) * rng.uniform(0.6, 1.2)
                d.line([(x, y), (x + math.cos(bh) * step * 1.4, y + math.sin(bh) * step * 1.4)], fill=(46, 42, 44), width=max(2, W // 340))
        d.line(pts, fill=(36, 32, 34), width=max(3, W // 200), joint="curve")
    return im


if __name__ == "__main__":
    outs = sys.argv[1:] or [os.path.join(HERE, d) for d in ("tex", "tex_low", "tex_gmod")]
    for i, (kind, fn) in enumerate((("fire", fire), ("wind", wind), ("lightning", lightning), ("water", water))):
        m = fn()
        col, sil = m.finish()
        mpt = mt.BOXES[kind][1] * m.side / m.Hs
        for d in outs:
            os.makedirs(d, exist_ok=True)
            size = 2048 if os.path.basename(d) == "tex" else 1024
            c = col.resize((size, size), Image.LANCZOS)
            c.save(os.path.join(d, f"mask_{kind}_col.jpg"), quality=94)
            sil.resize((size, size), Image.LANCZOS).save(os.path.join(d, f"mask_{kind}_sil.png"), optimize=True)
            json.dump({"metres_per_texture": mpt}, open(os.path.join(d, f"mask_{kind}_meta.json"), "w"))
            if os.path.basename(d) == "tex_gmod":
                crack(c, 100 + i).save(os.path.join(d, f"mask_{kind}_cracked_col.jpg"), quality=94)
        print(kind, "ok, metres per texture side", round(mpt, 3))
