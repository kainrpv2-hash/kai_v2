"""The four Jiongu masks (anime, Shippuden ep. 84): outlines, 3D relief and hand-painted textures.

Mask local space (metres): x to the creature's right... viewer's right, z up, the face looks towards -Y.
Texture space: square image covering [-M, M] x [-M, M] (M = MASK[...]['M']), so painting is isotropic.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")

WHITE = (222, 219, 222)
LINE = (24, 22, 26)


def superellipse(a, b, n):
    def f(t):
        c, s = abs(math.cos(t)), abs(math.sin(t))
        r = ((c / a) ** n + (s / b) ** n) ** (-1.0 / n)
        return r, r
    return f


def egg(a, b, e):
    """Ellipse, wider at the bottom when e > 0."""
    def f(t):
        return a * (1 - e * math.sin(t)), b
    return f


def lobes(base, bumps):
    def f(t):
        rx, rz = base(t)
        k = 1.0
        for t0, amp, w in bumps:
            d = math.atan2(math.sin(t - t0), math.cos(t - t0))
            k += amp * math.exp(-(d / w) ** 2)
        return rx * k, rz * k
    return f


def dome(depth, a, b):
    def f(x, z):
        q = 1 - (x / a) ** 2 - (z / b) ** 2
        return depth * math.sqrt(max(q, 0.0))
    return f


def bump(x, z, cx, cz, rx, rz, h):
    q = ((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2
    return h * math.exp(-q * 2.2)


# ---------------------------------------------------------------- per-mask geometry
def _relief_fire(x, z):
    r = dome(0.055, 0.15, 0.2)(x, z)
    r += bump(x, z, 0, -0.02, 0.03, 0.03, 0.012)            # nose
    r += bump(x, z, -0.055, 0.03, 0.04, 0.025, -0.004)       # eye sockets
    r += bump(x, z, 0.055, 0.03, 0.04, 0.025, -0.004)
    r += bump(x, z, 0, 0.075, 0.12, 0.02, 0.004)            # visor ridge
    if abs(x) < 0.082 and -0.108 < z < -0.067:               # mouth cavity
        r -= 0.010
    return r


def _relief_wind(x, z):
    r = dome(0.055, 0.15, 0.2)(x, z)
    r += bump(x, z, 0, -0.01, 0.025, 0.03, 0.010)
    r += bump(x, z, -0.05, 0.06, 0.05, 0.04, 0.004)          # brow arcs
    r += bump(x, z, 0.05, 0.06, 0.05, 0.04, 0.004)
    r += bump(x, z, 0, -0.085, 0.1, 0.05, 0.008)             # beak / chin
    return r


def _relief_lightning(x, z):
    r = dome(0.06, 0.16, 0.2)(x, z)
    r += bump(x, z, 0, -0.005, 0.03, 0.05, 0.022)            # big ochre nose
    r += bump(x, z, -0.055, 0.075, 0.045, 0.02, 0.008)       # angry brows
    r += bump(x, z, 0.055, 0.075, 0.045, 0.02, 0.008)
    r += bump(x, z, -0.06, -0.03, 0.04, 0.03, 0.006)         # cheeks
    r += bump(x, z, 0.06, -0.03, 0.04, 0.03, 0.006)
    if abs(x) < 0.095 and -0.125 < z < -0.06:
        r -= 0.012
    return r


def _relief_plate(x, z):
    # sits just behind the face rim and curves backwards towards the flaps / horns
    return 0.004 - 0.16 * (x * x + z * z)


def _relief_water(x, z):
    r = dome(0.05, 0.14, 0.17)(x, z)
    r += bump(x, z, 0, -0.07, 0.11, 0.06, 0.016)             # bill-like lower half
    r += bump(x, z, 0, 0.0, 0.02, 0.02, 0.005)
    return r


MASK = {
    "fire": dict(outline=egg(0.135, 0.18, 0.02), relief=_relief_fire, M=0.19),
    "wind": dict(outline=egg(0.135, 0.18, -0.04), relief=_relief_wind, M=0.19),
    "lightning": dict(outline=superellipse(0.13, 0.17, 3.2), relief=_relief_lightning, M=0.29,
                      plate=dict(outline=lobes(superellipse(0.168, 0.178, 3.0),
                                               [(math.radians(242), 0.62, 0.2), (math.radians(298), 0.62, 0.2)]),
                                 relief=_relief_plate)),
    "water": dict(outline=egg(0.118, 0.15, 0.12), relief=_relief_water, M=0.16),
}


# ---------------------------------------------------------------- painting
class Canvas:
    def __init__(self, M, size=2048, ss=2):
        self.M, self.S = M, size * ss
        self.ss = ss
        self.size = size
        self.im = Image.new("RGB", (self.S, self.S), WHITE)
        self.d = ImageDraw.Draw(self.im)

    def p(self, x, z):
        return ((x / (2 * self.M) + 0.5) * self.S, (0.5 - z / (2 * self.M)) * self.S)

    def w(self, metres):
        return max(1, int(round(metres / (2 * self.M) * self.S)))

    def line(self, pts, width=0.0035, fill=LINE):
        P = [self.p(*q) for q in pts]
        self.d.line(P, fill=fill, width=self.w(width), joint="curve")
        r = self.w(width) / 2
        for x, y in (P[0], P[-1]):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def poly(self, pts, fill, outline=LINE, width=0.0035):
        P = [self.p(*q) for q in pts]
        self.d.polygon(P, fill=fill)
        if outline:
            self.line(pts + [pts[0]], width, outline)

    def ellipse(self, cx, cz, rx, rz, fill=None, outline=LINE, width=0.0035):
        x0, y0 = self.p(cx - rx, cz + rz)
        x1, y1 = self.p(cx + rx, cz - rz)
        self.d.ellipse([x0, y0, x1, y1], fill=fill, outline=outline, width=self.w(width) if outline else 0)

    def eye(self, cx, cz, r=0.014, pupil=0.0058):
        self.ellipse(cx, cz, r, r * 1.08, fill=WHITE, width=0.003)
        self.ellipse(cx, cz - 0.001, pupil, pupil * 1.1, fill=LINE, outline=None)

    def dot(self, cx, cz, r=0.0045):
        self.ellipse(cx, cz, r, r, fill=LINE, outline=None)


def arc(cx, cz, rx, rz, a0, a1, n=40):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
             cz + rz * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1)))) for i in range(n)]


def bez(p0, p1, p2, p3=None, n=40):
    out = []
    for i in range(n):
        t = i / (n - 1)
        if p3 is None:
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
            z = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        else:
            x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0]
            z = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1]
        out.append((x, z))
    return out


def mirror(pts):
    return [(-x, z) for x, z in pts]


def outline_pts(outline, n=256, scale=1.0):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        rx, rz = outline(t)
        pts.append((math.cos(t) * rx * scale, math.sin(t) * rz * scale))
    return pts


def rim(c, outline, ticks=14, seed=0):
    """Hand-drawn edge: outline stroke + small notches like the anime line art."""
    rng = np.random.default_rng(seed)
    c.line(outline_pts(outline, 256, 0.985) + [outline_pts(outline, 256, 0.985)[0]], 0.004)
    for k in range(ticks):
        t = rng.uniform(0, 2 * math.pi)
        rx, rz = outline(t)
        p0 = (math.cos(t) * rx * 0.985, math.sin(t) * rz * 0.985)
        p1 = (math.cos(t) * rx * 0.93, math.sin(t) * rz * 0.93)
        c.line([p0, p1], 0.0028)


def shade(c, outline, seed=0, strength=1.0):
    """Anime-like soft grey shadow towards the lower rim + subtle porcelain wear."""
    S = c.S
    arr = np.asarray(c.im).astype(np.float32)
    ys, xs = np.mgrid[0:S, 0:S]
    X = (xs / S - 0.5) * 2 * c.M
    Z = (0.5 - ys / S) * 2 * c.M
    T = np.arctan2(Z, X)
    rx = np.vectorize(lambda t: outline(t)[0])(T[::16, ::16])
    rz = np.vectorize(lambda t: outline(t)[1])(T[::16, ::16])
    rx = np.asarray(Image.fromarray(rx.astype(np.float32)).resize((S, S), Image.BILINEAR))
    rz = np.asarray(Image.fromarray(rz.astype(np.float32)).resize((S, S), Image.BILINEAR))
    rr = np.sqrt((X / rx) ** 2 + (Z / rz) ** 2)
    edge = np.clip((rr - 0.72) / 0.28, 0, 1) ** 2
    lower = np.clip(-Z / (np.abs(rz) + 1e-6), 0, 1)
    dark = (0.10 * edge + 0.10 * edge * lower + 0.05 * lower) * strength
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, (S // 32, S // 32)).astype(np.float32)
    noise = np.asarray(Image.fromarray(noise).resize((S, S), Image.BICUBIC))
    grain = rng.normal(0, 1, (S, S)).astype(np.float32)
    f = 1 - dark + noise * 0.012 + grain * 0.008
    arr = arr * f[..., None]
    c.im = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    c.d = ImageDraw.Draw(c.im)


def finish(c, name):
    im = c.im.resize((c.size, c.size), Image.LANCZOS)
    im.save(os.path.join(TEX, f"mask_{name}_col.jpg"), quality=93)
    # normal map: painted lines are slightly embossed (ink ridges) + fine porcelain noise
    g = np.asarray(im.convert("L")).astype(np.float32) / 255.0
    h = 1.0 - g
    h = np.asarray(Image.fromarray((h * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255
    rng = np.random.default_rng(len(name))
    n = rng.normal(0, 1, (c.size // 4, c.size // 4)).astype(np.float32)
    n = np.asarray(Image.fromarray(n).resize((c.size, c.size), Image.BICUBIC)) * 0.04
    h = h * 0.6 + n
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nn = np.stack([-dx * 3, dy * 3, np.ones_like(h)], -1)
    nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
    Image.fromarray(((nn * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(TEX, f"mask_{name}_nrm.png"), optimize=True)


# ---------------------------------------------------------------- FIRE (Katon)
def paint_fire():
    m = MASK["fire"]
    c = Canvas(m["M"])
    shade(c, m["outline"], 1)
    # goggle / visor band: upper line across the forehead, lower line dipping in a V above the nose
    c.line(bez((-0.134, 0.062), (-0.06, 0.085), (0.06, 0.085), (0.134, 0.062)), 0.0035)
    lower_l = bez((-0.132, -0.005), (-0.09, -0.012), (-0.05, -0.012), (-0.03, -0.008))
    c.line(lower_l + [(-0.012, 0.012), (0.0, 0.016), (0.012, 0.012)] + mirror(lower_l)[::-1], 0.0035)
    c.eye(-0.056, 0.032)
    c.eye(0.056, 0.032)
    c.dot(-0.017, -0.034)
    c.dot(0.017, -0.034)
    # grimace: thick crimson lips around a dark mouth with square teeth
    lip = (138, 31, 58)
    outer = [(-0.098, -0.056), (0.098, -0.052), (0.102, -0.088), (0.094, -0.118), (-0.094, -0.121), (-0.101, -0.09)]
    c.poly(outer, lip, LINE, 0.0035)
    inner = [(-0.08, -0.07), (0.08, -0.067), (0.082, -0.104), (-0.08, -0.106)]
    c.poly(inner, (36, 14, 20), None)
    for i in range(7):
        x0 = -0.074 + i * 0.0215
        c.poly([(x0, -0.0695 + 0.0004 * i), (x0 + 0.016, -0.069 + 0.0004 * i), (x0 + 0.016, -0.08), (x0, -0.0805)], (238, 236, 232), LINE, 0.0018)
    for i in range(6):
        x0 = -0.066 + i * 0.022
        c.poly([(x0, -0.093), (x0 + 0.016, -0.0925), (x0 + 0.016, -0.1045), (x0, -0.105)], (238, 236, 232), LINE, 0.0018)
    c.line(inner + [inner[0]], 0.003)
    rim(c, m["outline"], 16, 1)
    finish(c, "fire")


# ---------------------------------------------------------------- WIND (Futon)
def paint_wind():
    m = MASK["wind"]
    c = Canvas(m["M"])
    shade(c, m["outline"], 2)
    for s in (-1, 1):
        # big curled arch lids
        brow = bez((s * 0.018, 0.02), (s * 0.012, 0.118), (s * 0.115, 0.125), (s * 0.112, 0.035))
        c.line(brow, 0.0038)
        c.line(bez((s * 0.018, 0.02), (s * 0.026, 0.008), (s * 0.04, 0.012)), 0.0034)
        c.eye(s * 0.062, 0.042, 0.0145)
        c.dot(s * 0.016, -0.018)
        # navy tear / comma marks at the ends of the chevron
        tear = bez((s * 0.093, -0.012), (s * 0.13, -0.02), (s * 0.128, -0.07), (s * 0.098, -0.072)) + \
            bez((s * 0.098, -0.072), (s * 0.112, -0.05), (s * 0.104, -0.03), (s * 0.093, -0.012))
        c.poly(tear, (34, 58, 92), LINE, 0.0025)
    c.line([(-0.104, -0.035), (0.0, -0.088), (0.104, -0.035)], 0.0038)
    rim(c, m["outline"], 14, 2)
    finish(c, "wind")


# ---------------------------------------------------------------- LIGHTNING (Raiton)
def paint_lightning():
    m = MASK["lightning"]
    c = Canvas(m["M"])
    plate = m["plate"]["outline"]
    shade(c, plate, 3, 0.8)
    # side flaps / plate edges
    c.line(outline_pts(plate, 256, 0.99) + [outline_pts(plate, 256, 0.99)[0]], 0.004)
    face = m["outline"]
    c.poly(outline_pts(face, 200, 1.0), WHITE, None)
    shade_face = outline_pts(face, 200, 1.0)
    c.line(shade_face + [shade_face[0]], 0.0042)
    for s in (-1, 1):
        c.line(bez((s * 0.105, 0.105), (s * 0.08, 0.07), (s * 0.04, 0.072), (s * 0.016, 0.052)), 0.0042)
        c.line(bez((s * 0.098, 0.102), (s * 0.12, 0.06), (s * 0.115, 0.02)), 0.0032)
        c.eye(s * 0.057, 0.038, 0.0155, 0.0065)
    nose = bez((-0.013, 0.032), (-0.03, -0.01), (-0.04, -0.05), (0.0, -0.056)) + \
        bez((0.0, -0.056), (0.04, -0.05), (0.03, -0.01), (0.013, 0.032))
    c.poly(nose, (224, 179, 96), LINE, 0.0032)
    # fanged mouth
    mouth = bez((-0.1, -0.062), (-0.05, -0.05), (0.05, -0.05), (0.1, -0.062)) + \
        bez((0.1, -0.062), (0.11, -0.1), (0.07, -0.13), (0.0, -0.13)) + \
        bez((0.0, -0.13), (-0.07, -0.13), (-0.11, -0.1), (-0.1, -0.062))
    c.poly(mouth, (20, 18, 22), LINE, 0.0042)
    tooth = (240, 238, 234)
    n = 7
    for i in range(n):
        x0 = -0.085 + i * (0.17 / n)
        x1 = x0 + 0.17 / n
        top = -0.058 + 0.006 * (1 - ((x0 + x1) / 0.2) ** 2)
        c.poly([(x0, top), (x1, top), ((x0 + x1) / 2, top - 0.028)], tooth, LINE, 0.0018)
    for i in range(n):
        x0 = -0.08 + i * (0.16 / n)
        x1 = x0 + 0.16 / n
        bot = -0.124 + 0.004 * ((x0 + x1) / 0.16) ** 2
        c.poly([(x0, bot), (x1, bot), ((x0 + x1) / 2, bot + 0.026)], tooth, LINE, 0.0018)
    finish(c, "lightning")


# ---------------------------------------------------------------- WATER (Suiton)
def paint_water():
    m = MASK["water"]
    c = Canvas(m["M"])
    shade(c, m["outline"], 4, 1.2)
    for s in (-1, 1):
        c.eye(s * 0.044, 0.05, 0.0125, 0.005)
        mark = bez((s * 0.068, 0.07), (s * 0.095, 0.064), (s * 0.098, 0.036), (s * 0.075, 0.024)) + \
            bez((s * 0.075, 0.024), (s * 0.086, 0.04), (s * 0.084, 0.058), (s * 0.068, 0.07))
        c.poly(mark, (143, 181, 201), (60, 80, 92), 0.0016)
        c.dot(s * 0.014, 0.004, 0.004)
    wave = bez((-0.117, -0.008), (-0.09, -0.012), (-0.07, -0.04), (-0.035, -0.036)) + \
        bez((-0.035, -0.036), (-0.015, -0.034), (-0.008, -0.024), (0.0, -0.029))
    c.line(wave + mirror(wave)[::-1], 0.0036)
    rim(c, m["outline"], 12, 4)
    finish(c, "water")


if __name__ == "__main__":
    os.makedirs(TEX, exist_ok=True)
    paint_fire()
    paint_wind()
    paint_lightning()
    paint_water()
    print("masks painted")
