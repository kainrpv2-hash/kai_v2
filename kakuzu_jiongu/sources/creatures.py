"""Anatomy of Kakuzu's four Jiongu monsters (anime, Shippuden ep. 84-88).

Each spec: SDF body with primitives tagged by bone, bone list, mask placement, fur settings and extras.
Blender axes: Z up, the creature faces -Y, its left side (".L") is +X. Kakuzu is ~1.85 m for scale.
"""
import math

import numpy as np

from kz_sdf import Body

S = (1, -1)


def sn(s):
    return "L" if s > 0 else "R"


def v(*a):
    return np.array(a, float)


class Spec:
    def __init__(self, key, title, seed):
        self.key = key
        self.title = title
        self.body = Body(seed)
        self.bones = [("root", (0, 0, 0), (0, 0.4, 0), None)]
        self.mask = {}
        self.fur = {}
        self.extras = []        # callables(build_ctx) -> list of (object, weight spec)
        self.anim = {}

    def bone(self, name, head, tail, parent):
        self.bones.append((name, tuple(map(float, head)), tuple(map(float, tail)), parent))

    # limbs ---------------------------------------------------------------
    def arm(self, s, shoulder, elbow, wrist, radii, k=0.18, fingers=3, finger_len=0.32, spread=0.09,
            finger_dir=(0, -0.45, -1.0), parent="chest", names=("upperarm", "forearm", "hand"), claw_r=0.06):
        n0, n1, n2 = (f"{n}.{sn(s)}" for n in names)
        sh, el, wr = v(*shoulder), v(*elbow), v(*wrist)
        self.body.chain([sh, el, wr], radii, k=k, bones=[n0, n1])
        fd = v(*finger_dir)
        fd /= np.linalg.norm(fd)
        side = np.cross(fd, [0, 0, 1.0]) if abs(fd[2]) < 0.95 else np.array([1.0, 0, 0])
        if np.linalg.norm(side) < 1e-6:
            side = np.array([1.0, 0, 0])
        side /= np.linalg.norm(side)
        tips = []
        for i in range(fingers):
            off = (i - (fingers - 1) / 2) * spread
            kn = wr + fd * finger_len * 0.45 + side * off * 0.8
            tip = wr + fd * finger_len + side * off * 1.3
            tip[2] = max(tip[2], 0.015)
            self.body.chain([wr, kn, tip], [radii[-1] * 0.55, claw_r, 0.008], k=0.05, bones=[n2, n2])
            tips.append(tip)
        hand_tip = np.mean(tips, 0)
        self.bone(n0, sh, el, parent)
        self.bone(n1, el, wr, n0)
        self.bone(n2, wr, hand_tip, n1)

    def leg(self, s, hip, knee, foot, radii, k=0.2, parent="hips", names=("thigh", "shin")):
        n0, n1 = (f"{n}.{sn(s)}" for n in names)
        h, kn, f = v(*hip), v(*knee), v(*foot)
        self.body.chain([h, kn, f], radii, k=k, bones=[n0, n1])
        self.bone(n0, h, kn, parent)
        self.bone(n1, kn, f, n0)


# =============================================================== FIRE / KATON
def katon():
    sp = Spec("katon", "Katon - Masque du Feu", seed=11)
    b = sp.body
    b.warp_amp, b.lump_amp = 0.05, 0.03
    b.ell((0, 0.15, 0.78), (0.92, 0.85, 0.78), k=0.25, bone="hips")      # mass reaches the ground
    b.ell((0, 0.18, 1.65), (0.92, 0.85, 1.05), k=0.3, bone="spine")
    b.ell((0, 0.5, 1.85), (0.8, 0.62, 0.95), k=0.3, bone="chest")        # massive back hump
    b.ell((0, 0.12, 2.42), (0.68, 0.63, 0.66), k=0.32, bone="head")      # tall domed top (mask sits here)
    sp.bone("hips", (0, 0.15, 0.55), (0, 0.15, 1.25), "root")
    sp.bone("spine", (0, 0.15, 1.25), (0, 0.17, 1.85), "hips")
    sp.bone("chest", (0, 0.17, 1.85), (0, 0.15, 2.4), "spine")
    sp.bone("head", (0, 0.12, 2.4), (0, 0.1, 2.95), "chest")
    for s in S:
        sp.arm(s, (s * 0.8, 0.02, 2.12), (s * 1.18, -0.04, 1.32), (s * 1.16, -0.2, 0.4), [0.29, 0.22, 0.16],
               k=0.14, finger_len=0.38, finger_dir=(s * 0.05, -0.5, -1.0), claw_r=0.055)
        sp.leg(s, (s * 0.45, 0.15, 0.7), (s * 0.52, 0.05, 0.38), (s * 0.52, 0.0, 0.08), [0.36, 0.32, 0.28])
    sp.mask = dict(kind="fire", x=0.0, z=2.38, scale=1.15, tilt=0.0, embed=0.018)
    sp.fur = dict(density=240, body_len=(0.3, 0.56), limb_len=(0.14, 0.28), outward=0.26, droop=0.8)
    sp.anim = dict(quad=False)
    return sp


# =============================================================== WIND / FUTON
def futon():
    sp = Spec("futon", "Futon - Masque du Vent", seed=22)
    b = sp.body
    b.warp_amp, b.lump_amp = 0.04, 0.025
    b.ell((0, 0.25, 0.86), (0.9, 0.95, 0.68), rot=(-6, 0, 0), k=0.3, bone="spine")
    b.ell((0, -0.3, 0.9), (0.86, 0.62, 0.62), k=0.3, bone="chest")
    b.ell((0, 0.8, 0.74), (0.76, 0.55, 0.55), k=0.3, bone="hips")
    b.ell((0, -0.68, 0.84), (0.52, 0.42, 0.45), k=0.25, bone="head")
    sp.bone("hips", (0, 0.95, 0.75), (0, 0.45, 0.85), "root")
    sp.bone("spine", (0, 0.45, 0.85), (0, -0.1, 0.9), "hips")
    sp.bone("chest", (0, -0.1, 0.9), (0, -0.5, 0.88), "spine")
    sp.bone("head", (0, -0.5, 0.86), (0, -0.98, 0.8), "chest")
    for s in S:
        sp.arm(s, (s * 0.6, -0.5, 0.62), (s * 0.78, -0.7, 0.34), (s * 0.78, -0.8, 0.1), [0.27, 0.2, 0.15],
               k=0.15, finger_len=0.22, spread=0.065, finger_dir=(s * 0.1, -1.0, -0.35), claw_r=0.042)
        sp.arm(s, (s * 0.6, 0.85, 0.56), (s * 0.78, 1.02, 0.32), (s * 0.74, 0.92, 0.1), [0.28, 0.2, 0.15],
               k=0.15, finger_len=0.2, spread=0.065, finger_dir=(s * 0.1, -1.0, -0.35), claw_r=0.042,
               parent="hips", names=("thigh", "shin", "foot"))
        # thin ladder wings (thread struts) spread in a V, see build.ladder_wing
        root = v(s * 0.3, 0.3, 1.42)
        mid = v(s * 1.0, 0.62, 2.0)
        tip = v(s * 1.8, 0.85, 2.55)
        sp.bone(f"wing.{sn(s)}", root, mid, "spine")
        sp.bone(f"wingtip.{sn(s)}", mid, tip, f"wing.{sn(s)}")
        sp.extras.append(("ladder", dict(root=root, mid=mid, tip=tip, s=s, bones=(f"wing.{sn(s)}", f"wingtip.{sn(s)}"))))
    sp.mask = dict(kind="wind", x=0.0, z=0.9, scale=1.05, tilt=-8.0, embed=0.018)
    sp.fur = dict(density=260, body_len=(0.24, 0.42), limb_len=(0.12, 0.22), outward=0.3, droop=0.7)
    sp.anim = dict(quad=True)
    return sp


# =============================================================== LIGHTNING / RAITON
def raiton():
    sp = Spec("raiton", "Raiton - Masque de la Foudre", seed=33)
    b = sp.body
    b.warp_amp, b.lump_amp = 0.05, 0.03
    b.ell((0, 0.08, 2.12), (0.95, 0.68, 0.8), k=0.3, bone="chest")
    b.ell((0, 0.1, 1.45), (0.82, 0.6, 0.62), k=0.3, bone="spine")
    b.ell((0, 0.1, 0.98), (0.72, 0.55, 0.42), k=0.2, bone="hips")
    b.ell((0, -0.02, 2.62), (0.52, 0.46, 0.4), k=0.3, bone="head")
    sp.bone("hips", (0, 0.1, 0.75), (0, 0.1, 1.25), "root")
    sp.bone("spine", (0, 0.1, 1.25), (0, 0.08, 1.85), "hips")
    sp.bone("chest", (0, 0.08, 1.85), (0, 0.06, 2.5), "spine")
    sp.bone("head", (0, 0.04, 2.5), (0, 0.0, 3.0), "chest")
    rng = np.random.default_rng(5)
    for s in S:
        # broad thin "wings" over the shoulders ending in sharp points (ep. 84 silhouette)
        b.ell((s * 0.75, 0.1, 2.74), (0.8, 0.34, 0.36), rot=(0, -6 * s, 0), k=0.28, bone=f"crest.{sn(s)}")
        b.cone((s * 1.2, 0.1, 2.84), (s * 2.05, 0.14, 2.98), 0.2, 0.012, k=0.12, bone=f"crest.{sn(s)}")
        b.cone((s * 1.1, 0.1, 2.9), (s * 1.5, 0.12, 3.18), 0.07, 0.006, k=0.05, bone=f"crest.{sn(s)}")
        sp.bone(f"crest.{sn(s)}", (s * 0.35, 0.1, 2.75), (s * 2.0, 0.14, 2.98), "chest")
        sp.arm(s, (s * 1.0, 0.04, 2.3), (s * 1.28, 0.02, 1.5), (s * 1.22, -0.14, 0.72), [0.3, 0.24, 0.18],
               k=0.16, finger_len=0.44, finger_dir=(s * 0.05, -0.4, -1.0), claw_r=0.065)
        sp.leg(s, (s * 0.42, 0.1, 0.9), (s * 0.58, -0.04, 0.48), (s * 0.62, 0.0, 0.1), [0.4, 0.34, 0.3])
    for i in range(10):                      # ragged crest of jagged spikes along the top
        x = -0.55 + 1.1 * i / 9 + rng.uniform(-0.04, 0.04)
        b.cone((x, 0.1, 2.92), (x * 1.35 + rng.uniform(-0.05, 0.05), 0.12, 3.22 + rng.uniform(0, 0.16)), 0.085, 0.006,
               k=0.06, bone="head")
    sp.mask = dict(kind="lightning", x=0.0, z=2.6, scale=1.15, tilt=-4.0, embed=-0.03)
    sp.fur = dict(density=235, body_len=(0.28, 0.5), limb_len=(0.14, 0.28), outward=0.3, droop=0.65,
                  spiky_z=2.95, wing_x=0.75)
    sp.anim = dict(quad=False)
    return sp


# =============================================================== WATER / SUITON
def suiton():
    sp = Spec("suiton", "Suiton - Masque de l'Eau", seed=44)
    b = sp.body
    b.warp_amp, b.lump_amp = 0.045, 0.028
    b.ell((0, 0.0, 2.42), (0.47, 0.45, 0.48), k=0.25, bone="head")     # rounded hood-like top
    b.ell((0, 0.12, 1.92), (0.68, 0.55, 0.62), k=0.3, bone="chest")
    b.ell((0, 0.42, 2.05), (0.56, 0.45, 0.55), k=0.3, bone="chest")    # hunched back
    b.ell((0, 0.1, 1.25), (0.64, 0.52, 0.6), k=0.3, bone="spine")
    sp.bone("hips", (0, 0.1, 0.8), (0, 0.1, 1.2), "root")
    sp.bone("spine", (0, 0.1, 1.2), (0, 0.12, 1.75), "hips")
    sp.bone("chest", (0, 0.12, 1.75), (0, 0.05, 2.2), "spine")
    sp.bone("head", (0, 0.05, 2.2), (0, 0.0, 2.85), "chest")
    b.ell((0, 0.1, 0.85), (0.56, 0.46, 0.4), k=0.2, bone="hips")
    for s in S:
        sp.arm(s, (s * 0.62, 0.08, 2.12), (s * 0.9, 0.1, 1.3), (s * 0.88, -0.07, 0.5), [0.21, 0.16, 0.12],
               finger_len=0.36, spread=0.07, finger_dir=(s * 0.05, -0.35, -1.0), claw_r=0.045)
        sp.leg(s, (s * 0.3, 0.1, 0.8), (s * 0.38, 0.0, 0.45), (s * 0.4, 0.05, 0.1), [0.29, 0.25, 0.22])
    sp.mask = dict(kind="water", x=0.0, z=2.43, scale=1.05, tilt=-3.0, embed=0.016)
    sp.fur = dict(density=245, body_len=(0.24, 0.45), limb_len=(0.12, 0.24), outward=0.32, droop=0.55)
    sp.anim = dict(quad=False)
    return sp


ALL = {"katon": katon, "futon": futon, "raiton": raiton, "suiton": suiton}
