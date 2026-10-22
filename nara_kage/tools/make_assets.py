"""Genere les textures (VTF + PNG) et les sons (WAV) de l'addon Nara : manipulation des ombres.

    python3 make_assets.py

Sorties :
  ../gmod/addon/nara_kage/materials/nara_kage/*.vtf + *.vmt
  ../gmod/addon/nara_kage/sound/nara_kage/*.wav
  ../preview/textures.js  (les memes textures en PNG base64, pour la preview)

Toutes les textures sont blanches avec un masque alpha : la couleur (noir d'encre)
vient de la couleur des sommets / des particules, comme dans le jeu.
"""
import base64
import io
import os
import struct
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(HERE, "..", "gmod", "addon", "nara_kage")
MAT_DIR = os.path.join(ADDON, "materials", "nara_kage")
SND_DIR = os.path.join(ADDON, "sound", "nara_kage")
PREVIEW = os.path.join(HERE, "..", "preview")

rng = np.random.default_rng(1984)


# --------------------------------------------------------------------------- bruit

def fbm(h, w, beta=2.2, seed=0):
    """Bruit fractal periodique (tuile parfaitement) normalise dans [0, 1]."""
    r = np.random.default_rng(seed)
    white = r.standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    spec = np.fft.fft2(white) / f ** (beta / 2.0)
    spec[0, 0] = 0
    n = np.real(np.fft.ifft2(spec))
    n -= n.min()
    return n / n.max()


def noise1d(n, beta=2.0, seed=0):
    r = np.random.default_rng(seed)
    f = np.fft.rfftfreq(n)
    f[0] = 1.0
    spec = np.fft.rfft(r.standard_normal(n)) / f ** (beta / 2.0)
    spec[0] = 0
    x = np.fft.irfft(spec, n)
    x -= x.min()
    return x / x.max()


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# --------------------------------------------------------------------------- textures

def tex_ribbon():
    """Bande d'ombre au sol. U = le long de l'ombre (tuile), V = en travers."""
    W, H = 512, 128
    u = np.arange(W)[None, :] / W
    v = (np.arange(H)[:, None] + 0.5) / H
    d = np.abs(v - 0.5) * 2.0                       # 0 au centre, 1 au bord
    edge_a = noise1d(W, 2.4, 11)[None, :]
    edge_b = noise1d(W, 2.4, 12)[None, :]
    # chaque bord a sa propre ondulation
    thr = np.where(v < 0.5, 0.70 + 0.17 * (edge_a - 0.5) * 2, 0.70 + 0.17 * (edge_b - 0.5) * 2)
    core = 1.0 - smoothstep(thr - 0.05, thr + 0.015, d)
    # filaments d'encre qui depassent du bord
    strands = fbm(H, W, 1.6, 13)
    strands = smoothstep(0.55, 0.75, strands) * (1.0 - smoothstep(thr, 1.0, d))
    a = np.maximum(core, 0.55 * strands)
    # legere vie a l'interieur (l'ombre reste presque opaque)
    a *= 0.93 + 0.07 * fbm(H, W, 2.0, 14)
    a[0, :] = 0
    a[-1, :] = 0
    return a


def tex_pool():
    """Flaque d'ombre sous le lanceur / la cible."""
    S = 256
    y, x = np.mgrid[0:S, 0:S]
    cx = (x + 0.5) / S * 2 - 1
    cy = (y + 0.5) / S * 2 - 1
    r = np.sqrt(cx * cx + cy * cy)
    th = (np.arctan2(cy, cx) / (2 * np.pi)) % 1.0
    lob = noise1d(1024, 2.6, 21)
    idx = (th * 1024).astype(int) % 1024
    thr = 0.70 + 0.16 * (lob[idx] - 0.5) * 2
    core = 1.0 - smoothstep(thr - 0.09, thr + 0.02, r)
    wisp = smoothstep(0.55, 0.78, fbm(S, S, 1.7, 22)) * (1.0 - smoothstep(thr, 0.98, r))
    a = np.maximum(core, 0.5 * wisp)
    a *= 0.94 + 0.06 * fbm(S, S, 2.0, 23)
    a *= 1.0 - smoothstep(0.93, 1.0, r)
    return a


def tex_ring():
    """Onde d'ombre qui s'etend au sol au moment du sceau."""
    S = 256
    y, x = np.mgrid[0:S, 0:S]
    cx = (x + 0.5) / S * 2 - 1
    cy = (y + 0.5) / S * 2 - 1
    r = np.sqrt(cx * cx + cy * cy)
    th = (np.arctan2(cy, cx) / (2 * np.pi)) % 1.0
    lob = noise1d(1024, 2.2, 31)
    idx = (th * 1024).astype(int) % 1024
    c = 0.80 + 0.06 * (lob[idx] - 0.5) * 2
    a = np.exp(-((r - c) / 0.07) ** 2)
    a *= 0.6 + 0.4 * fbm(S, S, 1.8, 32)
    a *= 1.0 - smoothstep(0.95, 1.0, r)
    return np.clip(a * 1.15, 0, 1)


def tex_wisp():
    """Volute de fumee d'encre (particules)."""
    S = 128
    y, x = np.mgrid[0:S, 0:S]
    cx = (x + 0.5) / S * 2 - 1
    cy = (y + 0.5) / S * 2 - 1
    r = np.sqrt(cx * cx + cy * cy)
    n = fbm(S, S, 3.0, 41)
    m = np.exp(-(r / 0.5) ** 2.0)
    a = smoothstep(0.2, 0.9, n * 0.7 + m * 0.55) * m
    a *= 1.0 - smoothstep(0.85, 1.0, r)
    return np.clip(a / a.max(), 0, 1)


def tex_strand():
    """Filament d'ombre pour les tentacules (faisceaux). X = en travers, Y = le long (tuile)."""
    W, H = 64, 256
    xx = (np.arange(W)[None, :] + 0.5) / W
    d = np.abs(xx - 0.5) * 2
    wob = noise1d(H, 2.2, 51)[:, None]
    thr = 0.62 + 0.18 * (wob - 0.5) * 2
    a = 1.0 - smoothstep(thr - 0.12, thr + 0.05, d)
    a *= 0.9 + 0.1 * fbm(H, W, 2.0, 52)
    a[:, 0] = 0
    a[:, -1] = 0
    return a


def tex_needle():
    """Aiguille d'ombre tranchante (Kage Nui) : bord net, coeur plein."""
    W, H = 32, 128
    xx = (np.arange(W)[None, :] + 0.5) / W
    d = np.abs(xx - 0.5) * 2
    a = 1.0 - smoothstep(0.72, 0.9, d) + 0 * np.arange(H)[:, None]
    a[:, 0] = 0
    a[:, -1] = 0
    return a


def tex_hand():
    """Main d'ombre griffue (Kage Kubishibari). Le poignet est en bas, les doigts en haut."""
    S = 512
    img = Image.new("L", (S, S), 0)
    dr = ImageDraw.Draw(img)
    # poignet + paume
    dr.polygon([(196, 512), (316, 512), (340, 320), (172, 320)], fill=255)
    dr.ellipse((140, 200, 372, 400), fill=255)
    # doigts : (base x, base y, angle en degres, longueur, epaisseur)
    fingers = [(168, 320, -62, 120, 52),   # pouce
               (180, 236, -20, 170, 48),
               (232, 214, -5, 190, 50),
               (286, 218, 9, 178, 48),
               (334, 244, 24, 140, 42)]
    for bx, by, ang, ln, th in fingers:
        a = np.radians(ang)
        pts = []
        segs = 3
        x, y = bx, by
        cur = a
        for s in range(segs):
            nx = x + np.sin(cur) * ln / segs
            ny = y - np.cos(cur) * ln / segs
            w = th * (1.0 - 0.22 * s)
            dr.line((x, y, nx, ny), fill=255, width=int(w))
            dr.ellipse((nx - w / 2, ny - w / 2, nx + w / 2, ny + w / 2), fill=255)
            x, y = nx, ny
            cur += np.radians(14 if ang >= -20 else -10)   # doigts qui se recourbent : prise
        # griffe pointue
        tip = (x + np.sin(cur) * th * 0.9, y - np.cos(cur) * th * 0.9)
        px, py = np.cos(cur) * th * 0.35, np.sin(cur) * th * 0.35
        dr.polygon([(x - px, y - py), (x + px, y + py), tip], fill=255)
    img = img.filter(ImageFilter.GaussianBlur(3))
    a = np.asarray(img.resize((128, 128), Image.LANCZOS), dtype=np.float64) / 255.0
    # bord encre irregulier
    a = smoothstep(0.25, 0.65, a * (0.85 + 0.3 * fbm(128, 128, 1.8, 61)))
    a[-1, :] = a[-2, :]
    return a


def tex_vignette():
    """Bords d'encre de l'ecran pendant la vue depuis la pointe de l'ombre."""
    S = 256
    y, x = np.mgrid[0:S, 0:S]
    cx = (x + 0.5) / S * 2 - 1
    cy = (y + 0.5) / S * 2 - 1
    r = np.sqrt((cx * 0.92) ** 2 + (cy * 1.0) ** 2)
    th = (np.arctan2(cy, cx) / (2 * np.pi)) % 1.0
    lob = noise1d(1024, 3.2, 71)
    idx = (th * 1024).astype(int) % 1024
    thr = 0.86 + 0.10 * (lob[idx] - 0.5) * 2
    a = smoothstep(thr - 0.32, thr + 0.12, r)
    a = np.maximum(a, smoothstep(1.05, 1.35, r))
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)), dtype=np.float64) / 255
    a *= 0.85 + 0.15 * fbm(S, S, 2.2, 72)
    return np.clip(a, 0, 1)


TEXTURES = {
    # nom : (fonction, clamp S, clamp T)
    "shadow_ribbon": (tex_ribbon, False, True),
    "shadow_pool": (tex_pool, True, True),
    "shadow_ring": (tex_ring, True, True),
    "shadow_wisp": (tex_wisp, True, True),
    "shadow_strand": (tex_strand, True, False),
    "shadow_needle": (tex_needle, True, False),
    "shadow_hand": (tex_hand, True, True),
    "shadow_vignette": (tex_vignette, True, True),
}


# --------------------------------------------------------------------------- VTF 7.2

def write_vtf(path, alpha, clamp_s, clamp_t):
    h, w = alpha.shape
    flags = 0x2000 | 0x0200          # EIGHTBITALPHA | NOLOD (jamais reduite par les reglages graphiques)
    if clamp_s:
        flags |= 0x0004
    if clamp_t:
        flags |= 0x0008
    mips = [alpha]
    while mips[-1].shape[0] > 1 or mips[-1].shape[1] > 1:
        m = mips[-1]
        hh, ww = max(1, m.shape[0] // 2), max(1, m.shape[1] // 2)
        m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((ww, hh), Image.BOX),
                       dtype=np.float64) / 255.0
        mips.append(m)
    hdr = bytearray(80)
    struct.pack_into("<4s2II", hdr, 0, b"VTF\0", 7, 2, 80)
    struct.pack_into("<HHIHH", hdr, 16, w, h, flags, 1, 0)
    struct.pack_into("<3f", hdr, 32, 1.0, 1.0, 1.0)
    struct.pack_into("<fIBIBBH", hdr, 48, 1.0, 12, len(mips), 0xFFFFFFFF, 0, 0, 1)
    body = bytearray()
    for m in reversed(mips):                              # du plus petit au plus grand
        a8 = (np.clip(m, 0, 1) * 255 + 0.5).astype(np.uint8)
        px = np.empty(a8.shape + (4,), np.uint8)
        px[..., 0:3] = 255                                # BGR blanc
        px[..., 3] = a8
        body += px.tobytes()
    with open(path, "wb") as f:
        f.write(bytes(hdr) + bytes(body))


VMT = """"UnlitGeneric"
{{
	"$basetexture" "nara_kage/{name}"
	"$translucent" "1"
	"$vertexcolor" "1"
	"$vertexalpha" "1"
	"$nocull" "1"
{extra}}}
"""


def png_b64(alpha):
    a8 = (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)
    rgba = np.empty(a8.shape + (4,), np.uint8)
    rgba[..., 0:3] = 255
    rgba[..., 3] = a8
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


# --------------------------------------------------------------------------- sons

SR = 44100


def env(n, a, d, curve=2.0):
    """Enveloppe attaque / declin en echantillons."""
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na) ** 1.5
    nd = max(1, int(d * SR))
    e[-nd:] *= np.linspace(1, 0, nd) ** curve
    return e


def lowpass(x, fc):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1.0 / np.sqrt(1 + (f / fc) ** 4)
    return np.fft.irfft(X, len(x))


def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (1.0 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 4)) * (1.0 / np.sqrt(1 + (f / hi) ** 4))
    return np.fft.irfft(X, len(x))


def sweep_noise(n, f0, f1, q=0.35, seed=0):
    """Bruit filtre dont la bande glisse de f0 a f1 (souffle qui passe)."""
    r = np.random.default_rng(seed)
    out = np.zeros(n)
    blk = 2048
    src = r.standard_normal(n + blk)
    for i in range(0, n, blk // 2):
        t = i / max(1, n - 1)
        fc = f0 * (f1 / f0) ** t
        seg = src[i:i + blk] * np.hanning(blk)
        seg = bandpass(seg, fc * (1 - q), fc * (1 + q))
        end = min(n, i + blk)
        out[i:end] += seg[:end - i]
    return out


def norm(x, peak=0.85):
    return x / (np.abs(x).max() + 1e-9) * peak


def snd_mudra():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    clap = bandpass(rng.standard_normal(n), 900, 4200) * np.exp(-t / 0.018)
    body = np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.05) * 0.4
    low = np.sin(2 * np.pi * 55 * t + 3 * np.exp(-t / 0.05)) * np.exp(-t / 0.18) * 0.7
    return norm(clap + body + low)


def snd_cast():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    whoosh = sweep_noise(n, 260, 1400, 0.4, 3) * env(n, 0.25, 1.0)
    sub = np.sin(2 * np.pi * (38 + 10 * t) * t) * env(n, 0.05, 1.2) * 0.9
    hiss = bandpass(rng.standard_normal(n), 3000, 9000) * env(n, 0.5, 0.9) * 0.08
    return norm(whoosh + sub + hiss)


def snd_crawl_loop():
    """Boucle : l'ombre qui rampe (grondement sourd + froissement). 3 s, raccord sans clic."""
    n = int(3.0 * SR)
    t = np.arange(n) / SR
    brown = np.cumsum(rng.standard_normal(n))
    brown = lowpass(brown - np.linspace(brown[0], brown[-1], n), 220)
    rustle = bandpass(rng.standard_normal(n), 500, 2600)
    am = 0.55 + 0.45 * np.sin(2 * np.pi * 2.0 * t) * np.sin(2 * np.pi * 0.667 * t)
    x = norm(brown) * 0.8 + norm(rustle) * 0.18 * am
    x += np.sin(2 * np.pi * 46 * t) * 0.25 * (0.7 + 0.3 * np.sin(2 * np.pi * 1.0 * t))
    # fondu enchaine fin -> debut pour une boucle parfaite
    k = int(0.25 * SR)
    fade = np.linspace(0, 1, k)
    x[:k] = x[:k] * fade + x[-k:] * (1 - fade)
    x = x[:-k]
    return norm(x, 0.7)


def snd_bind():
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    rev = sweep_noise(n, 300, 900, 0.5, 7)[::-1] * env(n, 0.02, 0.6)
    rev *= np.clip(t / 0.35, 0, 1) * (t < 0.36) + (t >= 0.36) * np.exp(-(t - 0.36) / 0.25)
    thump = np.sin(2 * np.pi * (70 - 30 * np.clip(t - 0.35, 0, 1)) * t) * np.exp(-np.clip(t - 0.35, 0, None) / 0.3) * (t > 0.35)
    tone = np.sin(2 * np.pi * 110 * t) * np.sin(2 * np.pi * 111.5 * t) * np.exp(-np.clip(t - 0.35, 0, None) / 0.6) * (t > 0.35) * 0.4
    return norm(rev * 0.7 + thump + tone)


def snd_choke():
    n = int(1.8 * SR)
    t = np.arange(n) / SR
    creak = np.zeros(n)
    f = 70 + 60 * t
    ph = np.cumsum(2 * np.pi * f / SR)
    creak = np.sign(np.sin(ph)) * 0.3 * bandpass(rng.standard_normal(n), 200, 1600)
    squeeze = sweep_noise(n, 180, 620, 0.3, 9)
    x = (creak * 0.6 + squeeze) * env(n, 0.3, 0.6)
    x += np.sin(2 * np.pi * 42 * t) * env(n, 0.4, 0.8) * 0.5
    return norm(x)


def snd_pierce():
    n = int(1.1 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for i, t0 in enumerate([0.0, 0.035, 0.06, 0.09, 0.12, 0.15]):
        k0 = int(t0 * SR)
        m = n - k0
        tt = np.arange(m) / SR
        swish = bandpass(np.random.default_rng(80 + i).standard_normal(m), 1800, 7000) * np.exp(-tt / 0.03)
        thunk = np.sin(2 * np.pi * (140 + 25 * i) * tt) * np.exp(-tt / 0.06) * 0.6
        x[k0:] += swish * 0.5 + thunk
    x += np.sin(2 * np.pi * 50 * t) * np.exp(-t / 0.25) * 0.8
    return norm(x)


def snd_release():
    n = int(1.0 * SR)
    t = np.arange(n) / SR
    x = sweep_noise(n, 1200, 220, 0.4, 5) * env(n, 0.05, 0.6)
    x += np.sin(2 * np.pi * (60 - 25 * t) * t) * env(n, 0.05, 0.7) * 0.5
    return norm(x, 0.7)


def snd_tick():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 880 * t) * np.exp(-t / 0.02) + 0.4 * np.sin(2 * np.pi * 1320 * t) * np.exp(-t / 0.015)
    return norm(x, 0.5)


SOUNDS = {
    "mudra": snd_mudra,
    "cast": snd_cast,
    "crawl_loop": snd_crawl_loop,
    "bind": snd_bind,
    "choke": snd_choke,
    "pierce": snd_pierce,
    "release": snd_release,
    "tick": snd_tick,
}


def write_wav(path, x, loop=False):
    data = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    n = len(x)
    chunks = [b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, SR, SR * 2, 2, 16),
              b"data" + struct.pack("<I", len(data)) + data]
    if loop:
        # point de repere (cue) : le moteur Source boucle les .wav qui en ont un
        cue = struct.pack("<I", 1) + struct.pack("<II4sIII", 1, 0, b"data", 0, 0, 0)
        chunks.append(b"cue " + struct.pack("<I", len(cue)) + cue)
        smpl = struct.pack("<9I", 0, 0, int(1e9 / SR), 60, 0, 0, 0, 1, 0)
        smpl += struct.pack("<6I", 0, 0, 0, n - 1, 0, 0)
        chunks.append(b"smpl" + struct.pack("<I", len(smpl)) + smpl)
    body = b"WAVE" + b"".join(chunks)
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", len(body)) + body)


def main():
    os.makedirs(MAT_DIR, exist_ok=True)
    os.makedirs(SND_DIR, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    js = ["// Genere par tools/make_assets.py : memes textures que l'addon (blanc + alpha).",
          "window.NARA_TEX = {"]
    for name, (fn, cs, ct) in TEXTURES.items():
        a = fn()
        write_vtf(os.path.join(MAT_DIR, name + ".vtf"), a, cs, ct)
        extra = ""
        if name == "shadow_vignette":
            extra = '\t"$ignorez" "1"\n'
        with open(os.path.join(MAT_DIR, name + ".vmt"), "w", newline="\n") as f:
            f.write(VMT.format(name=name, extra=extra))
        js.append('  %s: "data:image/png;base64,%s",' % (name, png_b64(a)))
        print("texture", name, a.shape)
    js.append("};")
    with open(os.path.join(PREVIEW, "textures.js"), "w", newline="\n") as f:
        f.write("\n".join(js) + "\n")
    for name, fn in SOUNDS.items():
        x = fn()
        write_wav(os.path.join(SND_DIR, name + ".wav"), x, loop=name.endswith("_loop"))
        print("son", name, "%.2fs" % (len(x) / SR))


if __name__ == "__main__":
    main()
