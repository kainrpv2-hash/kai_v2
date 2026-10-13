"""Export a built Jiongu creature (.blend) to Source engine sources for Garry's Mod:
reference SMD, animation SMDs, physics SMD and a QC file.

usage: python gmod_export.py <katon|futon|raiton|suiton> <blend file> <out dir>

Conventions: Source is Z up, models face +X, 1 unit = 1 inch. studiomdl itself applies a default
+90 deg rotation about Z (g_defaultrotation), so a model facing Blender's -Y ends up facing +X:
we therefore keep Blender's orientation and only convert metres to inches.
studiomdl accepts at most 3 bone weights per vertex.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

INCH = 39.3701
ROT = Matrix.Identity(4)
MAT_NAMES = {"KZ_Threads_Body": "jiongu_body", "KZ_Threads_Fur": "jiongu_fur",
             "KZ_Threads_Clump": "jiongu_clump", "KZ_Outline": "jiongu_outline"}
ACT = {"Idle": "ACT_IDLE", "Walk": "ACT_WALK", "Attack": "ACT_RANGE_ATTACK1"}


def src(m):
    """Blender armature-space matrix (metres, -Y forward) -> Source model space (inches, +X forward)."""
    r = ROT @ m
    r.translation = r.translation * INCH
    return r


def fmt(v):
    return " ".join(f"{x:.6f}" for x in v)


def bone_local_rows(arm, posed):
    rows = []
    bones = list(arm.data.bones)
    for i, b in enumerate(bones):
        if posed:
            M = arm.matrix_world @ arm.pose.bones[b.name].matrix
            P = arm.matrix_world @ arm.pose.bones[b.parent.name].matrix if b.parent else None
        else:
            M = arm.matrix_world @ b.matrix_local
            P = arm.matrix_world @ b.parent.matrix_local if b.parent else None
        L = src(M) if P is None else src(P).inverted() @ src(M)
        e = L.to_euler("XYZ")
        rows.append(f"{i} {fmt(L.translation)} {fmt(e)}")
    return rows


def nodes_block(arm):
    bones = list(arm.data.bones)
    idx = {b.name: i for i, b in enumerate(bones)}
    out = ["nodes"]
    for i, b in enumerate(bones):
        out.append(f'{i} "{b.name}" {idx[b.parent.name] if b.parent else -1}')
    out.append("end")
    return out


def write_reference(path, ob, arm, mask_mat):
    me = ob.data
    me.calc_loop_triangles()
    bones = list(arm.data.bones)
    bidx = {b.name: i for i, b in enumerate(bones)}
    gmap = {g.index: bidx[g.name] for g in ob.vertex_groups if g.name in bidx}
    M = ob.matrix_world
    nrm_mat = (ROT @ M).to_3x3().inverted().transposed()
    corner = me.corner_normals
    uv = me.uv_layers.active.data
    # per-vertex weights (top 3, normalised)
    links = []
    for v in me.vertices:
        ws = sorted(((g.weight, gmap[g.group]) for g in v.groups if g.group in gmap and g.weight > 1e-4), reverse=True)[:3]
        tot = sum(w for w, _ in ws) or 1.0
        if not ws:
            ws, tot = [(1.0, 0)], 1.0
        links.append(f"{len(ws)} " + " ".join(f"{b} {w / tot:.6f}" for w, b in ws))
    co = [(ROT @ M @ v.co) * INCH for v in me.vertices]
    out = ["version 1"] + nodes_block(arm) + ["skeleton", "time 0"] + bone_local_rows(arm, False) + ["end", "triangles"]
    stats = {}
    for lt in me.loop_triangles:
        mat = me.materials[lt.material_index].name
        mname = MAT_NAMES.get(mat, mask_mat)
        stats[mname] = stats.get(mname, 0) + 1
        out.append(mname)
        for li, vi in zip(lt.loops, lt.vertices):
            n = (nrm_mat @ corner[li].vector).normalized()
            u, vv = uv[li].uv
            out.append(f"0 {fmt(co[vi])} {fmt(n)} {u:.6f} {vv:.6f} {links[vi]}")
    out.append("end")
    open(path, "w").write("\n".join(out) + "\n")
    return stats


def write_animation(path, arm, action, frames):
    arm.animation_data.action = action
    out = ["version 1"] + nodes_block(arm) + ["skeleton"]
    for k, f in enumerate(range(frames[0], frames[1] + 1)):
        bpy.context.scene.frame_set(f)
        out.append(f"time {k}")
        out += bone_local_rows(arm, True)
    out.append("end")
    open(path, "w").write("\n".join(out) + "\n")
    return frames[1] - frames[0] + 1


def write_physics(path, ob, arm):
    """Single convex hull approximated by an octagonal prism around the main mass (root bone)."""
    me = ob.data
    body_idx = [i for i, m in enumerate(me.materials) if m.name == "KZ_Threads_Body"][0]
    verts = set()
    for p in me.polygons:
        if p.material_index == body_idx:
            verts.update(p.vertices)
    P = np.array([(ROT @ ob.matrix_world @ me.vertices[i].co)[:] for i in verts]) * INCH
    lo, hi = np.percentile(P, 3, axis=0), np.percentile(P, 97, axis=0)
    cx, cy = (lo[:2] + hi[:2]) / 2
    rx, ry = (hi[0] - lo[0]) / 2 * 0.9, (hi[1] - lo[1]) / 2 * 0.9
    z0, z1 = max(lo[2], 1.0), hi[2] * 0.95
    ring = [(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    bot = [(x, y, z0) for x, y in ring]
    top = [(x, y, z1) for x, y in ring]
    tris = []
    for i in range(8):
        j = (i + 1) % 8
        tris += [(bot[i], bot[j], top[j]), (bot[i], top[j], top[i])]
        tris += [(top[i], top[j], (cx, cy, z1)), (bot[j], bot[i], (cx, cy, z0))]
    out = ["version 1"] + nodes_block(arm) + ["skeleton", "time 0"] + bone_local_rows(arm, False) + ["end", "triangles"]
    for t in tris:
        a, b, c = (np.array(p) for p in t)
        n = np.cross(b - a, c - a)
        n = n / (np.linalg.norm(n) + 1e-9)
        out.append("phys")
        for p in (a, b, c):
            out.append(f"0 {fmt(p)} {fmt(n)} 0 0 1 0 1.0")
    out.append("end")
    open(path, "w").write("\n".join(out) + "\n")
    return lo, hi


def main():
    key, blend, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    bpy.ops.wm.open_mainfile(filepath=blend)
    ob = next(o for o in bpy.data.objects if o.type == "MESH")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    os.makedirs(outdir, exist_ok=True)
    name = f"jiongu_{key}"
    mask_mat = f"jiongu_{key}_mask"
    # rest pose for the reference
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.context.view_layer.update()
    stats = write_reference(os.path.join(outdir, f"{name}_ref.smd"), ob, arm, mask_mat)
    lo, hi = write_physics(os.path.join(outdir, f"{name}_phys.smd"), ob, arm)
    seqs = []
    for anim in ("Idle", "Walk", "Attack"):
        act = bpy.data.actions[f"{key}_{anim}"]
        fr = (int(act.frame_range[0]), int(act.frame_range[1]))
        n = write_animation(os.path.join(outdir, f"{name}_{anim.lower()}.smd"), arm, act, fr)
        seqs.append((anim, n))
    eye_z = hi[2] * 0.8
    # "mouth" attachment on the head bone, at the mask (jutsu spawn point for Lua / particles)
    me = ob.data
    mi = [i for i, m in enumerate(me.materials) if m.name.startswith("KZ_Mask")][0]
    mv = set()
    for p in me.polygons:
        if p.material_index == mi:
            mv.update(p.vertices)
    mc = sum((ob.matrix_world @ me.vertices[i].co for i in mv), Vector((0, 0, 0))) / len(mv)
    mouth = mc + Vector((0, -0.1, -0.03))
    head = arm.data.bones["head"]
    att = (arm.matrix_world @ head.matrix_local).inverted() @ mouth
    att = att * INCH
    mouth_z = mouth.z * INCH
    # render bounds = whole mesh (fur, wings, horns) so the model never pops out at screen edges
    allv = np.array([(ROT @ ob.matrix_world @ v.co)[:] for v in ob.data.vertices]) * INCH
    blo, bhi = allv.min(0), allv.max(0)
    bxy = float(np.abs(allv[:, :2]).max())
    cxy = float(max(np.abs(lo[:2]).max(), np.abs(hi[:2]).max()))
    qc = f'''// Kakuzu - Jiongu {key.capitalize()} (fan-made, non commercial)
// Compile: studiomdl.exe -game "<GarrysMod>\\garrysmod" -nop4 {name}.qc   (see compile_all.bat)
$modelname "kakuzu_jiongu/{name}.mdl"
$cdmaterials "models/kakuzu_jiongu/"
$surfaceprop "flesh"
// positions below are centred / symmetric so studiomdl's default 90 deg rotation cannot misplace them
$illumposition 0 0 {hi[2] * 0.5:.1f}
$eyeposition 0 0 {mouth_z:.1f}
$bbox {-bxy:.1f} {-bxy:.1f} 0 {bxy:.1f} {bxy:.1f} {bhi[2]:.1f}
$cbox {-cxy:.1f} {-cxy:.1f} 0 {cxy:.1f} {cxy:.1f} {hi[2]:.1f}

$body body "{name}_ref.smd"

// skin 0 = intact mask, skin 1 = cracked mask (heart almost spent; switched by the Lua NPC at low health)
$texturegroup "skinfamilies"
{{
	{{ "{mask_mat}" }}
	{{ "{mask_mat}_cracked" }}
}}

// jutsu spawn point at the mask
$attachment "mouth" "head" {att.x:.2f} {att.y:.2f} {att.z:.2f} rotate 0 0 0

$sequence idle "{name}_idle.smd" loop fps 30 activity ACT_IDLE 1
$sequence walk "{name}_walk.smd" loop fps 30 activity ACT_WALK 1
$sequence run "{name}_walk.smd" loop fps 48 activity ACT_RUN 1
$sequence attack "{name}_attack.smd" fps 30 activity ACT_RANGE_ATTACK1 1
$sequence attack_melee "{name}_attack.smd" fps 40 activity ACT_MELEE_ATTACK1 1

$collisionmodel "{name}_phys.smd"
{{
\t$mass 600
\t$inertia 1.00
\t$damping 0.10
\t$rotdamping 0.50
}}
'''
    open(os.path.join(outdir, f"{name}.qc"), "w").write(qc)
    print("EXPORTED", key, stats, seqs, "bbox", lo.round(1), hi.round(1))


main()
