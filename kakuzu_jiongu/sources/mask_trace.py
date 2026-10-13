"""Faithful masks: vectorise-by-threshold the four masks from the HD ep.84 frame, then redraw them clean at 2048 px.

For each mask we extract, at 10x upsampling with smoothing:
  silhouette (white mask vs black threads), ink lines (dark strokes inside), colour regions (red lips,
  navy / pale-blue marks, ochre nose) and the anime's grey cel-shadow band.
Outputs per kind (tex/ and every variant dir):
  mask_<kind>_col.jpg   2048x2048 clean redraw (square, mask centred)
  mask_<kind>_sil.png   2048x2048 silhouette (L), used to build the 3D mesh and the fur exclusion
  mask_<kind>_meta.json size info (metres per texture)
"""
import json
import os

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
FRAME = os.path.join(HERE, "..", "refs", "01_ep84_kakuzu_with_all_four_masked_monsters_1916x1080.png")
UP = 10
S = 2048
# native crop boxes in the 1916x1080 frame, and the real-world height of the whole silhouette (m)
BOXES = {
    "fire": ((228, 200, 344, 338), 0.42),
    "wind": ((552, 505, 664, 645), 0.40),
    "lightning": ((1228, 88, 1392, 242), 0.66),
    "water": ((1582, 185, 1690, 305), 0.36),
}

PAPER = np.array([222, 219, 223], float)      # mask base (anime off-white)
SHADOW = np.array([176, 172, 182], float)     # cel shadow on the mask
INK = np.array([22, 20, 24], float)
COLORS = {"red": np.array([134, 30, 52], float), "navy": np.array([30, 52, 98], float),
          "pale": np.array([112, 142, 162], float), "ochre": np.array([228, 178, 98], float),
          "mouth": np.array([46, 40, 46], float)}


def classify(rgb):
    """Per-pixel classes on the upsampled reference (thresholds measured on the ep.84 frame)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    L = rgb.mean(-1)
    red = (r - g > 25) & (r - b > 12) & (L > 35)          # crimson lips (102,39,53) .. (68,42,48)
    ochre = (r > 150) & (r - b > 70) & (g > 110)           # nose (227,178,99)
    navy = (b - r > 35) & (b - g > 18) & (L < 130)         # wind tear marks (24,51,81) .. (35,53,95)
    pale = (b - r > 10) & (b - r <= 35) & (L > 50) & (L < 175) & (b > g)   # water steel-blue marks
    return L, red, ochre, navy, pale


def clean(mask, open_r=0, close_r=0, min_size=0):
    m = mask
    if close_r:
        m = ndi.binary_closing(m, structure=disk(close_r))
    if open_r:
        m = ndi.binary_opening(m, structure=disk(open_r))
    if min_size:
        lab, n = ndi.label(m)
        if n:
            sizes = ndi.sum(m, lab, range(1, n + 1))
            keep = np.zeros(n + 1, bool)
            keep[1:] = sizes >= min_size
            m = keep[lab]
    return m


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def smooth_bin(mask, sigma):
    f = ndi.gaussian_filter(mask.astype(float), sigma)
    return f > 0.5


def trace(kind):
    (x0, y0, x1, y1), height_m = BOXES[kind]
    frame = Image.open(FRAME).convert("RGB")
    crop = frame.crop((x0, y0, x1, y1))
    w, h = crop.size
    big = np.asarray(crop.resize((w * UP, h * UP), Image.BICUBIC).filter(ImageFilter.GaussianBlur(UP * 0.35))).astype(float)
    L, red, ochre, navy, pale = classify(big)
    # --- silhouette: bright-ish region, largest component, holes filled, smoothed
    sat_all = (big.max(-1) - big.min(-1)) / np.maximum(big.max(-1), 1)
    sil = (L > 95) | red | ochre | navy | pale | ((sat_all > 0.3) & (L > 45))
    sil = clean(sil, open_r=UP // 2, close_r=UP * 2, min_size=0)
    lab, n = ndi.label(sil)
    sizes = ndi.sum(sil, lab, range(1, n + 1))
    sil = lab == (1 + int(np.argmax(sizes)))
    sil = ndi.binary_fill_holes(sil)
    sil = smooth_bin(sil, UP * 1.3)
    inner = ndi.binary_erosion(sil, structure=disk(int(UP * 0.9)))
    # --- colour regions (inside the mask)
    red = smooth_bin(clean(red & sil, open_r=2, close_r=UP // 2, min_size=UP * UP * 2), UP * 0.5)
    ochre = smooth_bin(clean(ochre & sil, open_r=2, close_r=UP // 2, min_size=UP * UP * 4), UP * 0.6)
    navy = smooth_bin(clean(navy & sil, open_r=2, close_r=UP // 2, min_size=UP * UP * 2), UP * 0.5)
    pale = smooth_bin(clean(pale & inner, open_r=2, close_r=UP, min_size=UP * UP * 3), UP * 0.6)
    colored = red | ochre | navy | pale
    # --- ink strokes: dark inside the eroded silhouette, not part of colour fills
    ink = (L < 120) & inner & ~ndi.binary_dilation(red | ochre | navy | pale, structure=disk(2))
    ink = clean(ink, open_r=1, close_r=2, min_size=UP * UP)
    # redraw like an inker: centre lines with a constant brush + solid areas (pupils, mouths) kept as fills
    from skimage.morphology import skeletonize
    dt = ndi.distance_transform_edt(ink)
    half = UP * 0.95                                   # brush radius (~1.9 px line in the 1080p frame)
    solid = ink & (ndi.maximum_filter(dt, size=int(UP)) > half * 1.7)
    solid = smooth_bin(clean(solid, open_r=int(half), min_size=int(UP * UP * 4)), UP * 0.5)
    skel = skeletonize(ink)
    lines = ndi.distance_transform_edt(~skel) <= half
    ink = smooth_bin(lines | solid, UP * 0.45)
    # mouth interiors / pupils are big dark blobs: keep as ink
    # --- cel shadow: mid-grey, unsaturated, inside, not ink / colour
    sat_ok = (big.max(-1) - big.min(-1)) < 40
    shadow = (L > 118) & (L < 186) & sat_ok & inner & ~ink & ~colored
    shadow = smooth_bin(clean(shadow, open_r=UP // 2, close_r=UP, min_size=UP * UP * 12), UP * 1.5)
    # --- compose into a square canvas (mask centred, 6 % margin)
    Hs, Ws = sil.shape
    side = int(max(Hs, Ws) / 0.88)
    oy, ox = (side - Hs) // 2, (side - Ws) // 2

    def place(m, dtype=bool):
        out = np.zeros((side, side), dtype)
        out[oy:oy + Hs, ox:ox + Ws] = m
        return out
    layers = {k: place(v) for k, v in dict(sil=sil, red=red, ochre=ochre, navy=navy, pale=pale, ink=ink, shadow=shadow).items()}
    # resample every layer to S with soft edges (anti-aliasing)
    def soft(m):
        im = Image.fromarray((m * 255).astype(np.uint8)).resize((S, S), Image.LANCZOS)
        return np.asarray(im.filter(ImageFilter.GaussianBlur(1.2))).astype(float) / 255.0
    A = {k: soft(v) for k, v in layers.items()}
    col = np.zeros((S, S, 3)) + PAPER
    # subtle paper gradient: slightly darker towards the lower rim (anime shading), lighter upper-left
    yy, xx = np.mgrid[0:S, 0:S] / S
    col *= (1.0 - 0.05 * np.clip(yy - 0.3, 0, 1))[..., None]

    def over(c, a):
        nonlocal col
        col = col * (1 - a[..., None]) + c * a[..., None]
    over(SHADOW, A["shadow"] * 0.9)
    over(COLORS["pale"], A["pale"])
    over(COLORS["navy"], A["navy"])
    over(COLORS["ochre"], A["ochre"])
    over(COLORS["red"], A["red"])
    over(INK, A["ink"])
    # everything outside the silhouette = darkest paper rim colour (never seen, avoids mip bleed)
    over(np.array([120, 116, 124], float), 1 - np.clip(A["sil"] * 1.5, 0, 1))
    rng = np.random.default_rng(len(kind))
    grain = ndi.gaussian_filter(rng.normal(0, 1, (S, S)), 1.0) * 3.0
    col = col + grain[..., None]
    sil_img = (A["sil"] * 255).clip(0, 255).astype(np.uint8)
    metres_per_tex = height_m * side / Hs
    return Image.fromarray(col.clip(0, 255).astype(np.uint8)), Image.fromarray(sil_img), metres_per_tex


def silhouette(kind, sigma=None):
    """Smoothed silhouette of a mask from the frame, centred in a square canvas.
    Returns (sil[side, side] bool, ox, oy, side, Hs) where native crop pixel (x, y) maps to (ox + x*UP, oy + y*UP)."""
    if sigma is None:
        sigma = 0.9 if kind == "lightning" else 1.8   # thin horn tips must survive the smoothing
    (x0, y0, x1, y1), _ = BOXES[kind]
    frame = Image.open(FRAME).convert("RGB")
    crop = frame.crop((x0, y0, x1, y1))
    w, h = crop.size
    big = np.asarray(crop.resize((w * UP, h * UP), Image.BICUBIC).filter(ImageFilter.GaussianBlur(UP * 0.35))).astype(float)
    L, red, ochre, navy, pale = classify(big)
    sat_all = (big.max(-1) - big.min(-1)) / np.maximum(big.max(-1), 1)
    sil = (L > 90) | red | ochre | navy | pale | ((sat_all > 0.3) & (L > 45))
    sil = clean(sil, open_r=UP // 4 if kind == "lightning" else UP // 2, close_r=UP * 2, min_size=0)
    lab, n = ndi.label(sil)
    sizes = ndi.sum(sil, lab, range(1, n + 1))
    sil = lab == (1 + int(np.argmax(sizes)))
    sil = ndi.binary_fill_holes(sil)
    sil = smooth_bin(sil, UP * sigma)
    ys = np.nonzero(sil.any(1))[0]
    Hs = ys.max() - ys.min()
    side = int(max(sil.shape) / 0.88)
    oy, ox = (side - sil.shape[0]) // 2, (side - sil.shape[1]) // 2
    out = np.zeros((side, side), bool)
    out[oy:oy + sil.shape[0], ox:ox + sil.shape[1]] = sil
    return out, ox, oy, side, Hs


if __name__ == "__main__":
    import sys
    outs = sys.argv[1:] or [os.path.join(HERE, d) for d in ("tex", "tex_low", "tex_gmod")]
    for kind in BOXES:
        col, sil, mpt = trace(kind)
        for d in outs:
            os.makedirs(d, exist_ok=True)
            size = 2048 if d.endswith("tex") else 1024
            col.resize((size, size), Image.LANCZOS).save(os.path.join(d, f"mask_{kind}_col.jpg"), quality=94)
            sil.resize((size, size), Image.LANCZOS).save(os.path.join(d, f"mask_{kind}_sil.png"), optimize=True)
            json.dump({"metres_per_texture": mpt}, open(os.path.join(d, f"mask_{kind}_meta.json"), "w"))
        print(kind, "metres per texture side", round(mpt, 3))
