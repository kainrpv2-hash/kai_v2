"""Blender (bpy 5.2) helpers: meshes from arrays, fur cards, masks, materials, rig, export, render."""
import math
import os
import random

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")


# ------------------------------------------------------------------ scene / mesh basics
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.render.fps = 30


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_from_arrays(name, verts, faces, uvs=None, normals=None):
    """verts (N,3), faces (M,k) int (all same arity), uvs per-loop (M*k,2)."""
    verts = np.asarray(verts, np.float32)
    faces = np.asarray(faces, np.int32)
    me = bpy.data.meshes.new(name)
    nv, nf, k = len(verts), len(faces), faces.shape[1]
    me.vertices.add(nv)
    me.vertices.foreach_set("co", verts.ravel())
    me.loops.add(nf * k)
    me.loops.foreach_set("vertex_index", faces.ravel())
    me.polygons.add(nf)
    me.polygons.foreach_set("loop_start", np.arange(0, nf * k, k, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(nf, k, np.int32))
    me.update(calc_edges=True)
    me.validate()
    if uvs is not None:
        uv = me.uv_layers.new(name="UVMap")
        uv.data.foreach_set("uv", np.asarray(uvs, np.float32).ravel())
    me.shade_smooth()
    if normals is not None:
        me.normals_split_custom_set_from_vertices([tuple(n) for n in normals])
    return me


def obj_from_arrays(name, verts, faces, **kw):
    return link(bpy.data.objects.new(name, mesh_from_arrays(name, verts, faces, **kw)))


def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    return ob


def decimate(ob, ratio):
    m = ob.modifiers.new("Decimate", "DECIMATE")
    m.ratio = ratio
    m.use_collapse_triangulate = True
    return apply_modifiers(ob)


def mesh_arrays(ob, world=True):
    me = ob.data
    me.calc_loop_triangles()
    v = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", v)
    v = v.reshape(-1, 3)
    t = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", t)
    t = t.reshape(-1, 3)
    n = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("normal", n)
    n = n.reshape(-1, 3)
    if world:
        M = np.array(ob.matrix_world)
        v = v @ M[:3, :3].T + M[:3, 3]
        n = n @ np.linalg.inv(M[:3, :3])
        n /= np.linalg.norm(n, axis=1, keepdims=True)
    return v, t, n


def box_uv(ob, scale=1.0):
    """Cube projection UVs (per face dominant axis). The body texture is chaotic so seams vanish."""
    me = ob.data
    nl = len(me.loops)
    vi = np.empty(nl, np.int32)
    me.loops.foreach_get("vertex_index", vi)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    pn = np.empty(len(me.polygons) * 3, np.float32)
    me.polygons.foreach_get("normal", pn)
    pn = pn.reshape(-1, 3)
    ls = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", ls)
    poly_of_loop = np.repeat(np.arange(len(me.polygons)), ls)
    ax = np.abs(pn).argmax(1)[poly_of_loop]
    p = co[vi]
    u = np.where(ax == 0, p[:, 1], p[:, 0])
    v = np.where(ax == 2, p[:, 1], p[:, 2])
    uv = np.stack([u, v], 1) * scale
    lay = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    lay.data.foreach_set("uv", uv.astype(np.float32).ravel())


# ------------------------------------------------------------------ images / materials
def image(name, noncolor=False):
    path = os.path.join(TEX, name)
    if not os.path.exists(path):  # LOD textures may be stored as JPEG
        path = os.path.splitext(path)[0] + ".jpg"
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return im


def _mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    return m, nt, b


def _tex(nt, im, x, y):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = im
    t.location = (x, y)
    return t


def _normal(nt, im, b, strength=1.0):
    t = _tex(nt, im, -700, -350)
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.location = (-300, -350)
    nm.inputs["Strength"].default_value = strength
    nt.links.new(t.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])


def mat_body():
    m, nt, b = _mat("KZ_Threads_Body")
    t = _tex(nt, image("body_col.png"), -700, 200)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    _normal(nt, image("body_nrm.png", True), b, 1.0)
    b.inputs["Roughness"].default_value = 0.82
    b.inputs["Specular IOR Level"].default_value = 0.15
    m.use_backface_culling = True
    return m


def mat_fur():
    m, nt, b = _mat("KZ_Threads_Fur")
    t = _tex(nt, image("fur_atlas_col.png"), -700, 200)
    t.image.alpha_mode = "STRAIGHT"
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    # alpha clip: Math(Round) -> exported by glTF as alphaMode MASK (cutoff 0.5)
    r = nt.nodes.new("ShaderNodeMath")
    r.operation = "ROUND"
    r.location = (-300, 0)
    nt.links.new(t.outputs["Alpha"], r.inputs[0])
    nt.links.new(r.outputs[0], b.inputs["Alpha"])
    _normal(nt, image("fur_atlas_nrm.png", True), b, 0.8)
    b.inputs["Roughness"].default_value = 0.5
    b.inputs["Specular IOR Level"].default_value = 0.4
    m.use_backface_culling = False
    return m


def mat_mask(name, col_img, nrm_img=None, rough=0.42):
    m, nt, b = _mat(name)
    t = _tex(nt, image(col_img), -700, 200)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if nrm_img:
        _normal(nt, image(nrm_img, True), b, 0.6)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.5
    m.use_backface_culling = True
    return m


def mat_flat(name, rgb, rough=0.6, emit=None, strength=0.0):
    m, nt, b = _mat(name)
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


# ------------------------------------------------------------------ fur cards
def sample_surface(v, t, n, count, density_fn=None, rng=None):
    rng = rng or np.random.default_rng(0)
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    w = area.copy()
    if density_fn is not None:
        cen = (a + b + c) / 3
        fn = (n[t[:, 0]] + n[t[:, 1]] + n[t[:, 2]])
        fn /= np.linalg.norm(fn, axis=1, keepdims=True)
        w *= np.clip(density_fn(cen, fn), 0, None)
    w /= w.sum()
    idx = rng.choice(len(t), size=count, p=w)
    r1, r2 = rng.random(count), rng.random(count)
    s = np.sqrt(r1)
    u, vv, ww = 1 - s, s * (1 - r2), s * r2
    P = a[idx] * u[:, None] + b[idx] * vv[:, None] + c[idx] * ww[:, None]
    N = n[t[idx, 0]] * u[:, None] + n[t[idx, 1]] * vv[:, None] + n[t[idx, 2]] * ww[:, None]
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    return P, N


def _norm(x):
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-9)


def fur_cards(P, N, style, rng=None, cols=8, segs=4):
    """Build hair cards. style(P, N, rng) -> dict of per-card arrays:
       length, width, outward (0..1), droop, twist (radians), col (atlas column)."""
    rng = rng or np.random.default_rng(1)
    S = style(P, N, rng)
    L, Wd, out, droop, twist, col = S["length"], S["width"], S["outward"], S["droop"], S["twist"], S["col"]
    g = np.array([0, 0, -1.0])
    tg = g - N * (N @ g)[:, None]
    bad = np.linalg.norm(tg, axis=1) < 0.15
    rnd = _norm(np.cross(N, _norm(rng.normal(size=(len(N), 3)))))
    tg = np.where(bad[:, None], rnd, _norm(tg))
    if "flow" in S:  # per-card flow override (e.g. fur radiating away from the mask)
        fw = S["flow_w"][:, None]
        tg = _norm(tg * (1 - fw) + S["flow"] * fw)
    d0 = _norm(N * out[:, None] + tg * (1 - out[:, None]) + rng.normal(scale=0.18, size=N.shape))
    side = _norm(np.cross(d0, N))
    # twist the card around its axis so not every card lies flat
    ct, st = np.cos(twist)[:, None], np.sin(twist)[:, None]
    nrm_c = _norm(np.cross(side, d0))
    side = _norm(side * ct + nrm_c * st)
    nverts = (segs + 1) * 2
    V = np.zeros((len(P), nverts, 3))
    UV = np.zeros((len(P), nverts, 2))
    NR = np.zeros((len(P), nverts, 3))
    pos = P - N * 0.025  # root slightly inside the body
    d = d0.copy()
    for k in range(segs + 1):
        tt = k / segs
        wk = Wd * (1.0 - 0.35 * tt)
        V[:, 2 * k] = pos - side * (wk / 2)[:, None]
        V[:, 2 * k + 1] = pos + side * (wk / 2)[:, None]
        u0 = (col + 0.04) / cols
        u1 = (col + 0.96) / cols
        UV[:, 2 * k, 0], UV[:, 2 * k + 1, 0] = u0, u1
        UV[:, 2 * k, 1] = UV[:, 2 * k + 1, 1] = 0.005 + tt * 0.99
        # shading normal: body normal at the root, blended towards the card direction near the tip
        nn = _norm(N * (1 - 0.35 * tt) + d * 0.35 * tt)
        NR[:, 2 * k] = NR[:, 2 * k + 1] = nn
        if k < segs:
            step = (L / segs)[:, None]
            pos = pos + d * step
            d = _norm(d + g * (droop / segs)[:, None])
    faces = []
    for k in range(segs):
        faces.append([2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2])
    faces = np.array(faces)
    base = (np.arange(len(P)) * nverts)[:, None, None]
    F = (faces[None] + base).reshape(-1, 4)
    loops_uv = UV.reshape(-1, 2)[F.ravel()]
    return V.reshape(-1, 3), F, loops_uv, NR.reshape(-1, 3), S


# ------------------------------------------------------------------ masks
def mask_mesh(name, outline, relief, M, rings=48, segs=128, thick=0.018, y_off=0.0):
    """Face mask in local space: front faces -Y, x right, z up. outline(theta)->(rx,rz) radius in metres,
       relief(x, z)-> forward bulge (metres, along -Y). UV = planar front projection."""
    th = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    R = np.array([outline(a) for a in th])  # (segs, 2) radius x/z per angle
    verts = [(0.0, 0.0)]
    for i in range(1, rings + 1):
        s = (i / rings) ** 0.85
        for j in range(segs):
            verts.append((np.cos(th[j]) * R[j, 0] * s, np.sin(th[j]) * R[j, 1] * s))
    verts = np.array(verts)
    x, z = verts[:, 0], verts[:, 1]
    y = -np.array([relief(xx, zz) for xx, zz in zip(x, z)])
    front = np.stack([x, y, z], 1)
    front[:, 1] += y_off
    tris = []
    for j in range(segs):
        tris.append([0, 1 + j, 1 + (j + 1) % segs])
    quads = []
    for i in range(rings - 1):
        a0, b0 = 1 + i * segs, 1 + (i + 1) * segs
        for j in range(segs):
            jn = (j + 1) % segs
            quads.append([a0 + j, b0 + j, b0 + jn, a0 + jn])
    # back shell (offset along +Y, inverted)
    nv = len(front)
    back = front.copy()
    back[:, 1] += thick
    allv = np.concatenate([front, back])
    tri_back = [[c + nv, b + nv, a + nv] for a, b, c in tris]
    quad_back = [[d + nv, c + nv, b + nv, a + nv] for a, b, c, d in quads]
    # rim
    last = 1 + (rings - 1) * segs
    rim = []
    for j in range(segs):
        jn = (j + 1) % segs
        rim.append([last + jn, last + j, last + j + nv, last + jn + nv])
    uv_all = np.stack([allv[:, 0] / (2 * M) + 0.5, allv[:, 2] / (2 * M) + 0.5], 1)
    me = bpy.data.meshes.new(name)
    polys = tris + tri_back + quads + quad_back + rim
    me.from_pydata(allv.tolist(), [], polys)
    uvl = me.uv_layers.new(name="UVMap")
    li = 0
    for p in me.polygons:
        for k in p.loop_indices:
            uvl.data[k].uv = uv_all[me.loops[k].vertex_index]
    me.shade_smooth()
    return link(bpy.data.objects.new(name, me))


def horn(name, base, direction, length, r0, bend=(0, 0, 0.0), segs=10, ring=12):
    """Curved tapered cone (for masks with horns / spikes)."""
    base = np.asarray(base, float)
    d = np.asarray(direction, float)
    d /= np.linalg.norm(d)
    bend = np.asarray(bend, float)
    verts, faces = [], []
    pts = []
    p = base.copy()
    dd = d.copy()
    for i in range(segs + 1):
        pts.append((p.copy(), dd.copy()))
        p = p + dd * length / segs
        dd = dd + bend / segs
        dd /= np.linalg.norm(dd)
    for i, (p, dd) in enumerate(pts):
        r = r0 * (1 - i / segs) ** 0.9 + 0.0008
        a = np.cross(dd, [0.0, 0.0, 1.0] if abs(dd[2]) < 0.9 else [1.0, 0.0, 0.0])
        a /= np.linalg.norm(a)
        bb = np.cross(dd, a)
        for j in range(ring):
            t = 2 * np.pi * j / ring
            verts.append(p + (a * np.cos(t) + bb * np.sin(t)) * r)
    for i in range(segs):
        for j in range(ring):
            jn = (j + 1) % ring
            faces.append([i * ring + j, i * ring + jn, (i + 1) * ring + jn, (i + 1) * ring + j])
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.shade_smooth()
    return link(bpy.data.objects.new(name, me))


# ------------------------------------------------------------------ thread tendrils
def tendril(name, pts, radius=0.012, taper=True, res=6):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 1
    cu.resolution_u = res
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        bp = sp.bezier_points[i]
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
        bp.radius = (1.0 - 0.8 * i / (len(pts) - 1)) if taper else 1.0
    ob = link(bpy.data.objects.new(name, cu))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    mo = link(bpy.data.objects.new(name + "_m", me))
    bpy.data.objects.remove(ob)
    return mo


# ------------------------------------------------------------------ join / rig
def join(objs, name):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def build_armature(name, bones):
    """bones: list of (name, head, tail, parent or None). Returns armature object."""
    arm = bpy.data.armatures.new(name)
    ob = link(bpy.data.objects.new(name, arm))
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for bn, h, t, par in bones:
        b = arm.edit_bones.new(bn)
        b.head, b.tail = Vector(h), Vector(t)
        if par:
            b.parent = eb[par]
            b.use_connect = (Vector(h) - eb[par].tail).length < 1e-4
        eb[bn] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    return np.linalg.norm(P - (a + np.outer(t, ab)), axis=1)


def skin(ob, arm_ob, bones, weight_points=None, power=5.0, max_inf=4, overrides=None):
    """Distance-to-bone weights. weight_points: per-vertex positions used for weighting
       (fur cards use their root so each card moves rigidly). overrides: {vertex_mask_name: bone}"""
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    P = co.reshape(-1, 3) if weight_points is None else weight_points
    names = [b[0] for b in bones if not b[0].startswith("root")]
    D = np.stack([seg_dist(P, np.array(b[1]), np.array(b[2])) for b in bones if not b[0].startswith("root")], 1)
    W = 1.0 / np.maximum(D, 0.02) ** power
    if overrides is not None:
        for vmask, bone in overrides:
            W[vmask] = 0
            W[vmask, names.index(bone)] = 1.0
    order = np.argsort(-W, axis=1)[:, :max_inf]
    rows = np.arange(len(P))[:, None]
    Wk = W[rows, order]
    Wk /= Wk.sum(1, keepdims=True)
    groups = [ob.vertex_groups.new(name=n) for n in names]
    for vi in range(len(P)):
        for k in range(max_inf):
            w = float(Wk[vi, k])
            if w > 0.01:
                groups[order[vi, k]].add([vi], w, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_ob
    ob.parent = arm_ob


# ------------------------------------------------------------------ export
def export_glb(path, objs):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=False,
        export_animations=True, export_animation_mode="ACTIONS", export_skins=True,
        export_image_format="AUTO", export_tangents=True, export_yup=True)


def export_fbx(path, objs):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z",
        add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
        path_mode="COPY", embed_textures=True, mesh_smooth_type="FACE", use_tspace=True)
