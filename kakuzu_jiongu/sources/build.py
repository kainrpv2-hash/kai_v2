"""Build one Jiongu creature: sculpted body + thread fur cards + painted mask + rig + animations -> .blend/.glb/.fbx

usage: python build.py <katon|futon|raiton|suiton> [hq|low]
"""
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

import kz_blender as kb  # noqa: E402
import masks as mk  # noqa: E402
from creatures import ALL  # noqa: E402

OUT = os.path.join(HERE, "out")
LIMB = ("upperarm", "forearm", "hand", "thigh", "shin", "foot")
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


# ------------------------------------------------------------------ mask placement
def mask_frame(sp):
    m = sp.mask
    p, n = sp.body.surface_hit(m["x"], m["z"])
    f = n * 0.45 + np.array([0, -1.0, 0]) * 0.55
    f /= np.linalg.norm(f)
    th = math.radians(m["tilt"])
    Rx = np.array([[1, 0, 0], [0, math.cos(th), -math.sin(th)], [0, math.sin(th), math.cos(th)]])
    f = Rx @ f
    Y = -f
    Z = np.array([0, 0, 1.0]) - Y * Y[2]
    Z /= np.linalg.norm(Z)
    X = np.cross(Y, Z)
    R = np.stack([X, Y, Z], 1)
    c = p + Y * m["embed"] * m["scale"]
    return c, R, m["scale"]


def build_mask(sp, c, R, scale, lod):
    kind = sp.mask["kind"]
    res = dict(rings=26, segs=80) if lod == "hq" else dict(rings=12, segs=40)
    spec = mk.MASK[kind]
    mat = kb.mat_mask(f"KZ_Mask_{kind}", f"mask_{kind}_col.jpg", f"mask_{kind}_nrm.png")
    parts = [kb.mask_mesh(f"mask_{kind}", spec["outline"], spec["relief"], spec["M"], **res)]
    if "plate" in spec:
        pl = spec["plate"]
        parts.append(kb.mask_mesh(f"plate_{kind}", pl["outline"], pl["relief"], spec["M"], y_off=0.006, thick=0.012, **res))
        for s in (1, -1):
            h = kb.horn(f"horn_{s}", (s * 0.105, 0.0, 0.135), (s * 0.85, 0.1, 0.55), 0.2, 0.034,
                        bend=(-s * 2.2, 0, 1.0), segs=12 if lod == "hq" else 6, ring=12 if lod == "hq" else 7)
            # horns sample a clean white texel of the mask texture
            uvl = h.data.uv_layers.new(name="UVMap")
            u = 0.5
            vv = 0.12 / (2 * spec["M"]) + 0.5
            uvl.data.foreach_set("uv", np.tile([u, vv], len(h.data.loops)).astype(np.float32))
            parts.append(h)
    M4 = Matrix.Translation(Vector(c)) @ Matrix(R.tolist()).to_4x4() @ Matrix.Scale(scale, 4)
    for p in parts:
        p.matrix_world = M4
        p.data.materials.append(mat)
        p.data.transform(p.matrix_world)
        p.matrix_world = Matrix()
    return parts


# ------------------------------------------------------------------ extras
def ladder_wing(sp, e):
    """Thin thread wing like a ladder: two rails + rungs + spiky tips (Futon)."""
    s = e["s"]
    root, mid, tip = e["root"], e["mid"], e["tip"]
    d = tip - root
    d /= np.linalg.norm(d)
    w = np.cross(d, [0, 1.0, 0])
    w /= np.linalg.norm(w)
    rng = np.random.default_rng(7 if s > 0 else 8)
    objs = []

    def curve(t):  # quadratic through root, mid, tip
        return (1 - t) ** 2 * root + 2 * (1 - t) * t * (2 * mid - 0.5 * root - 0.5 * tip) + t * t * tip

    half = 0.12
    for k in (-1, 1):
        pts = []
        for i in range(9):
            t = i / 8
            pts.append(tuple(curve(t) + w * k * half * (1 - 0.35 * t) + rng.normal(0, 0.012, 3)))
        ext = np.array(pts[-1]) + (np.array(pts[-1]) - np.array(pts[-2])) * 1.4 + w * k * 0.05
        pts.append(tuple(ext))
        objs.append(kb.tendril(f"rail_{s}_{k}", pts, radius=0.024, taper=True))
    n = 15
    for i in range(1, n):
        t = i / n
        a = curve(t) - w * half * (1 - 0.35 * t)
        b = curve(t) + w * half * (1 - 0.35 * t)
        mid_r = (a + b) / 2 + rng.normal(0, 0.01, 3)
        objs.append(kb.tendril(f"rung_{s}_{i}", [tuple(a - w * 0.03), tuple(mid_r), tuple(b + w * 0.03)],
                               radius=0.014, taper=False, res=3))
    for j in range(4):  # ragged spikes near the tip, like the frayed ends in the anime
        t = 0.75 + 0.07 * j
        base = curve(t) + w * rng.choice([-1, 1]) * half * 0.7
        tipp = base + (d * 0.25 + w * rng.normal(0, 0.15) + np.array([0, 0, 0.08])) * rng.uniform(0.6, 1.0)
        objs.append(kb.tendril(f"spike_{s}_{j}", [tuple(base), tuple((base + tipp) / 2), tuple(tipp)], radius=0.016))
    return objs


# ------------------------------------------------------------------ fur
def build_fur(sp, body_ob, bone_names, c, R, scale, lod):
    v, t, n = kb.mesh_arrays(body_ob)
    a, b2, cc = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b2 - a, cc - a), axis=1).sum()
    F = sp.fur
    dens = F["density"] * (1.5 if lod == "hq" else 0.25)
    count = int(area * dens)
    log(f"body area {area:.1f} m2 -> {count} fur cards")
    rng = np.random.default_rng(hash(sp.key) % 2 ** 32)

    hand_idx = [i for i, bn in enumerate(bone_names) if bn.startswith(("hand", "foot"))]
    limb_idx = [i for i, bn in enumerate(bone_names) if bn.startswith(("upperarm", "forearm", "thigh", "shin"))]

    def density_fn(cen, fn):
        W = sp.body.bone_weights(cen, bone_names, tau=0.05)
        hand = W[:, hand_idx].sum(1) if hand_idx else 0
        d = 1.0 - 0.8 * np.clip(hand, 0, 1)
        d *= np.where(fn[:, 2] < -0.6, 0.55, 1.0)
        d *= np.where(cen[:, 2] < 0.04, 0.3, 1.0)
        d *= np.where(hand < 0.5, 1.0 + 0.6 * W[:, limb_idx].sum(1), 1.0) if limb_idx else 1.0
        return d

    P, N = kb.sample_surface(v, t, n, count, density_fn, rng)

    # mask exclusion + fur radiating outward around the mask
    q = (P - c) @ R / scale
    spec = mk.MASK[sp.mask["kind"]]
    outline = spec.get("plate", spec)["outline"]
    th = np.arctan2(q[:, 2], q[:, 0])
    rx = np.array([outline(x)[0] for x in th])
    rz = np.array([outline(x)[1] for x in th])
    rho = np.sqrt((q[:, 0] / rx) ** 2 + (q[:, 2] / rz) ** 2)
    front = q[:, 1] < 0.12
    keep = ~(front & (rho < 1.04))
    if sp.mask["kind"] == "lightning":  # keep the horns visible
        keep &= ~(front & (q[:, 2] > 0.1) & (np.abs(q[:, 0]) < 0.3) & (q[:, 2] < 0.42))
    P, N, q, rho, front = P[keep], N[keep], q[keep], rho[keep], front[keep]
    radial = (R @ np.stack([q[:, 0], np.zeros(len(q)), q[:, 2]], 1).T).T
    radial /= np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-6)
    flow_w = np.where(front & (rho < 2.2), np.clip((2.2 - rho) / 1.1, 0, 1), 0.0)

    W = sp.body.bone_weights(P, bone_names, tau=0.05)
    dom = np.array([bone_names[i] for i in W.argmax(1)])
    limb = np.array([d.startswith(LIMB) for d in dom])

    def style(P, N, rng):
        k = len(P)
        lo, hi = F["body_len"]
        llo, lhi = F["limb_len"]
        L = np.where(limb, rng.uniform(llo, lhi, k), rng.uniform(lo, hi, k))
        out = np.where(limb, F["outward"] + 0.18, F["outward"]) + rng.normal(0, 0.08, k)
        droop = np.full(k, F["droop"]) * rng.uniform(0.6, 1.3, k)
        fl, fw = radial.copy(), flow_w.copy()
        if "spiky_z" in F:  # Raiton: bristling crest in the middle
            sp_mask = (P[:, 2] > F["spiky_z"]) & (np.abs(P[:, 0]) < F.get("wing_x", 9))
            out = np.where(sp_mask, 0.75, out)
            droop = np.where(sp_mask, 0.08, droop)
            L = np.where(sp_mask, L * 1.2, L)
        if "wing_x" in F:   # Raiton: shoulder wings, fur combed towards the pointed tips
            wing = (np.abs(P[:, 0]) > F["wing_x"]) & (P[:, 2] > 2.45)
            tipdir = np.stack([np.sign(P[:, 0]), np.zeros(k), np.full(k, 0.12)], 1)
            fl = np.where(wing[:, None], tipdir, fl)
            fw = np.where(wing, 0.85, fw)
            out = np.where(wing, 0.12, out)
            droop = np.where(wing, 0.05, droop)
            L = np.where(wing, L * 0.8, L)
        low = (P[:, 2] < 0.5) & ~limb               # base of the mass: threads splay out onto the ground
        out = np.where(low, 0.6, out)
        droop = np.where(low, 1.1, droop)
        L = np.where(low, L * 1.1, L)
        L *= np.where(flow_w > 0, 0.75, 1.0)        # shorter ring around the mask
        out = np.where(flow_w > 0, out * (1 - 0.6 * flow_w), out)
        Wd = np.clip(L * rng.uniform(0.3, 0.45, k), 0.05, 0.17) * (0.78 if lod == "hq" else 1.25)
        col = np.where(rng.random(k) < 0.22, rng.integers(6, 8, k), rng.integers(0, 6, k))
        return dict(length=L, width=Wd, outward=np.clip(out, 0.05, 0.95), droop=droop,
                    twist=rng.uniform(-0.8, 0.8, k), col=col, flow=fl, flow_w=fw)

    V, Fc, UV, NR, _ = kb.fur_cards(P, N, style, rng)
    V[:, 2] = np.maximum(V[:, 2], 0.006)
    fur = kb.obj_from_arrays(f"{sp.key}_fur", V, Fc, uvs=UV, normals=NR)
    fur.data.materials.append(kb.mat_fur())
    per = len(V) // len(P)
    return fur, np.repeat(W, per, axis=0)


# ------------------------------------------------------------------ rig helpers
def set_groups(ob, names, W):
    groups = [ob.vertex_groups.get(nm) or ob.vertex_groups.new(name=nm) for nm in names]
    for j, g in enumerate(groups):
        idx = np.nonzero(W[:, j] > 0)[0]
        if len(idx) == 0:
            continue
        ws = W[idx, j]
        # group identical weights to limit Python calls
        for wv in np.unique(np.round(ws, 3)):
            sel = idx[np.round(ws, 3) == wv]
            g.add(sel.tolist(), float(wv), "REPLACE")


def rigid(n, names, bone):
    W = np.zeros((n, len(names)))
    W[:, names.index(bone)] = 1
    return W


def segment_weights(P, sp, bnames, names, tau=0.08):
    D = []
    for bn in bnames:
        b = next(x for x in sp.bones if x[0] == bn)
        D.append(kb.seg_dist(P, np.array(b[1]), np.array(b[2])))
    D = np.stack(D, 1)
    E = np.exp(-(D - D.min(1, keepdims=True)) / tau)
    E /= E.sum(1, keepdims=True)
    W = np.zeros((len(P), len(names)))
    for k, bn in enumerate(bnames):
        W[:, names.index(bn)] = E[:, k]
    return W


def verts_of(ob):
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3).astype(np.float64)


# ------------------------------------------------------------------ animation
def qw(arm, bone, axis, ang):
    B = arm.data.bones[bone].matrix_local.to_3x3()
    return Quaternion(B.transposed() @ Vector(axis), ang)


def pose(arm, frame, rots, root_loc=(0, 0, 0)):
    """rots: {bone: [(axis, angle), ...]} with world-space axes in the rest pose."""
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        q = Quaternion()
        for axis, ang in rots.get(pb.name, []):
            q = qw(arm, pb.name, axis, ang) @ q
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    rb = arm.pose.bones["root"]
    rb.location = root_loc
    rb.keyframe_insert("location", frame=frame)


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def has(arm, b):
    return b in arm.data.bones


def make_actions(arm, sp):
    ad = arm.animation_data_create()
    quad = sp.anim.get("quad", False)
    acts = []

    def new(name):
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        ad.action = act
        acts.append(act)
        return act

    # ---------------- Idle: breathing, slow look around, arms / wings sway (4 s loop)
    new(f"{sp.key}_Idle")
    for f in range(1, 122, 4):
        t = (f - 1) / 120.0
        w = 2 * math.pi * t
        r = {"spine": [(X, 0.025 * math.sin(w))], "chest": [(X, 0.035 * math.sin(w + 0.4)), (Z, 0.03 * math.sin(w))],
             "head": [(X, -0.04 * math.sin(w + 0.8)), (Z, 0.09 * math.sin(w + 1.2))]}
        for s, L in ((1, "L"), (-1, "R")):
            ph = 0 if s > 0 else 1.3
            if has(arm, f"upperarm.{L}"):
                r[f"upperarm.{L}"] = [(X, 0.05 * math.sin(w + ph)), (Y, -s * 0.03 * (1 + math.sin(w)))]
                r[f"forearm.{L}"] = [(X, -0.06 * math.sin(w + ph + 0.6))]
                r[f"hand.{L}"] = [(X, 0.08 * math.sin(w + ph + 1.2))]
            if has(arm, f"crest.{L}"):
                r[f"crest.{L}"] = [(Y, s * 0.05 * math.sin(w))]
            if has(arm, f"wing.{L}"):
                r[f"wing.{L}"] = [(Y, -s * 0.1 * math.sin(w))]
                r[f"wingtip.{L}"] = [(Y, -s * 0.12 * math.sin(w - 0.7))]
        if quad:
            r["head"] = [(X, -0.05 * math.sin(w + 0.8)), (Z, 0.12 * math.sin(w + 1.2))]
            for L in ("L", "R"):
                r.pop(f"upperarm.{L}", None)
                r.pop(f"forearm.{L}", None)
                r.pop(f"hand.{L}", None)
        pose(arm, f, r, (0, 0, 0.012 * math.sin(w)))

    # ---------------- Walk: heavy lumbering cycle (in place, 40 frames)
    new(f"{sp.key}_Walk")
    for f in range(1, 42, 2):
        t = (f - 1) / 40.0
        w = 2 * math.pi * t
        r = {"hips": [(Z, 0.06 * math.sin(w))], "chest": [(Z, -0.07 * math.sin(w)), (X, 0.04)],
             "head": [(Z, 0.04 * math.sin(w))], "spine": [(Y, 0.03 * math.sin(w))]}
        for s, L in ((1, "L"), (-1, "R")):
            if quad:
                pf = w + (0 if s > 0 else math.pi)
                ph = pf + math.pi
                r[f"upperarm.{L}"] = [(X, -0.38 * math.sin(pf))]
                r[f"forearm.{L}"] = [(X, 0.45 * max(0.0, math.sin(pf + 1.3)))]
                r[f"thigh.{L}"] = [(X, -0.38 * math.sin(ph))]
                r[f"shin.{L}"] = [(X, -0.4 * max(0.0, math.sin(ph + 1.3)))]
                if has(arm, f"wing.{L}"):
                    r[f"wing.{L}"] = [(Y, -s * 0.06 * math.sin(2 * w))]
            else:
                pl = w + (0 if s > 0 else math.pi)
                r[f"thigh.{L}"] = [(X, -0.42 * math.sin(pl))]
                r[f"shin.{L}"] = [(X, 0.55 * max(0.0, math.sin(pl + 1.4)))]
                r[f"upperarm.{L}"] = [(X, 0.32 * math.sin(pl)), (Y, -s * 0.05)]
                r[f"forearm.{L}"] = [(X, -0.15 - 0.12 * math.sin(pl))]
                if has(arm, f"crest.{L}"):
                    r[f"crest.{L}"] = [(Y, s * 0.04 * math.sin(2 * w))]
        pose(arm, f, r, (0, 0, -0.035 * math.cos(2 * w) * (0.5 if quad else 1.0)))

    # ---------------- Attack: rear back, then thrust the mask forward to fire the jutsu (60 frames)
    new(f"{sp.key}_Attack")
    keys = [(1, 0.0, 0.0, 0.0), (16, -1.0, 0.0, 0.0), (24, 1.0, 0.0, 1.0), (30, 0.95, 0.02, 1.0),
            (34, 1.0, -0.02, 1.0), (40, 0.9, 0.0, 1.0), (61, 0.0, 0.0, 0.0)]
    for f, k, shake, spread in keys:
        back = min(k, 0.0)
        fwd = max(k, 0.0)
        r = {"spine": [(X, 0.12 * back + 0.14 * fwd)], "chest": [(X, 0.22 * back + 0.22 * fwd), (Z, shake)],
             "head": [(X, 0.28 * back + 0.3 * fwd + shake), (Z, -shake)]}
        if quad:
            r["chest"] = [(X, 0.35 * back + 0.15 * fwd)]
            r["head"] = [(X, 0.35 * back + 0.2 * fwd + shake)]
        for s, L in ((1, "L"), (-1, "R")):
            if not quad and has(arm, f"upperarm.{L}"):
                r[f"upperarm.{L}"] = [(Y, -s * (0.3 * -back + 0.35 * spread)), (X, 0.2 * back - 0.25 * fwd)]
                r[f"forearm.{L}"] = [(X, -0.3 * -back - 0.2 * fwd)]
            if quad:
                r[f"upperarm.{L}"] = [(X, 0.25 * back)]
                r[f"thigh.{L}"] = [(X, -0.15 * back)]
            if has(arm, f"crest.{L}"):
                r[f"crest.{L}"] = [(Y, s * (0.12 * -back + 0.18 * spread))]
            if has(arm, f"wing.{L}"):
                r[f"wing.{L}"] = [(Y, -s * (0.25 * -back + 0.4 * spread))]
                r[f"wingtip.{L}"] = [(Y, -s * 0.3 * spread)]
        pose(arm, f, r, (0, -0.25 * fwd + 0.08 * -back, 0.0))
    ad.action = acts[0]
    return acts


# ------------------------------------------------------------------ main
def build(key, lod="hq"):
    sp = ALL[key]()
    kb.TEX = os.path.join(HERE, "tex" if lod == "hq" else "tex_low")
    kb.reset()
    os.makedirs(OUT, exist_ok=True)
    voxel = 0.016 if lod == "hq" else 0.03
    log(f"{key} [{lod}] sculpting SDF body (voxel {voxel})")
    cache = os.path.join(OUT, f"_sdf_{key}_{voxel}.npz")
    if os.path.exists(cache) and os.environ.get("KZ_NOCACHE") is None:
        d = np.load(cache)
        verts, faces = d["v"], d["f"]
    else:
        verts, faces = sp.body.mesh(voxel=voxel)
        np.savez(cache, v=verts, f=faces)
    body = kb.obj_from_arrays(f"{key}_body", verts, faces)
    log(f"marching cubes: {len(faces)} tris")
    target = 26000 if lod == "hq" else 4200
    if len(faces) > target:
        kb.decimate(body, target / len(faces))
    sm = body.modifiers.new("Smooth", "CORRECTIVE_SMOOTH")
    sm.iterations = 3
    sm.smooth_type = "LENGTH_WEIGHTED"
    sm.use_only_smooth = True
    kb.apply_modifiers(body)
    body.data.shade_smooth()
    kb.box_uv(body, 1 / 0.7)
    body.data.materials.append(kb.mat_body())
    log(f"body: {len(body.data.polygons)} faces")

    names = [b[0] for b in sp.bones if b[0] != "root"]
    c, R, scale = mask_frame(sp)
    mask_parts = build_mask(sp, c, R, scale, lod)
    fur, Wfur = build_fur(sp, body, names, c, R, scale, lod)
    log(f"fur: {len(fur.data.polygons)} quads")

    extras = []
    for kind, e in sp.extras:
        if kind == "ladder":
            objs = ladder_wing(sp, e)
            for o in objs:
                kb.box_uv(o, 1 / 0.7)
                o.data.materials.append(bpy.data.materials["KZ_Threads_Body"])
                set_groups(o, names, segment_weights(verts_of(o), sp, list(e["bones"]), names))
            extras += objs

    set_groups(body, names, sp.body.bone_weights(verts_of(body), names, tau=0.05))
    set_groups(fur, names, Wfur)
    for p in mask_parts:
        set_groups(p, names, rigid(len(p.data.vertices), names, "head"))

    ob = kb.join([body, fur] + mask_parts + extras, f"Jiongu_{key.capitalize()}")
    for o in list(bpy.data.objects):
        if o.type == "CURVE":
            bpy.data.objects.remove(o)

    arm = kb.build_armature(f"Jiongu_{key.capitalize()}_Rig", sp.bones)
    ob.parent = arm
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    acts = make_actions(arm, sp)
    log(f"actions: {[a.name for a in acts]}")
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    log(f"final mesh: {len(ob.data.vertices)} verts, {tris} tris, materials {[m.name for m in ob.data.materials]}")

    base = os.path.join(OUT, f"Jiongu_{key.capitalize()}_{lod.upper()}")
    bpy.context.scene.frame_set(1)
    kb.export_glb(base + ".glb", [ob, arm])
    log("glb exported")
    kb.export_fbx(base + ".fbx", [ob, arm])
    log("fbx exported")
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=base + ".blend", compress=True)
    log("blend saved")
    return ob, arm


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "hq")
