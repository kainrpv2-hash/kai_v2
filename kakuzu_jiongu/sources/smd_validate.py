"""Validate exported SMDs: re-skin the reference mesh with an animation frame exactly the way studiomdl/Source
does (local XYZ euler bones, linear blend skinning) and compare with Blender's own deformed mesh.

usage: python smd_validate.py <key> <blend> <smd dir> [anim] [frame]
"""
import math
import sys

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

INCH = 39.3701
ROT = Matrix.Identity(4)


def parse(path):
    lines = open(path).read().split("\n")
    i = 0
    nodes, frames, tris = [], {}, []
    while i < len(lines):
        l = lines[i].strip()
        if l == "nodes":
            i += 1
            while lines[i].strip() != "end":
                p = lines[i].split('"')
                nodes.append((p[1], int(p[2])))
                i += 1
        elif l == "skeleton":
            i += 1
            t = None
            while lines[i].strip() != "end":
                s = lines[i].split()
                if s[0] == "time":
                    t = int(s[1])
                    frames[t] = {}
                else:
                    frames[t][int(s[0])] = list(map(float, s[1:7]))
                i += 1
        elif l == "triangles":
            i += 1
            while lines[i].strip() != "end":
                mat = lines[i].strip()
                for k in range(3):
                    s = lines[i + 1 + k].split()
                    pos = np.array(list(map(float, s[1:4])))
                    n = int(s[9])
                    links = [(int(s[10 + 2 * j]), float(s[11 + 2 * j])) for j in range(n)]
                    tris.append((mat, pos, links))
                i += 4
        i += 1
    return nodes, frames, tris


def world(nodes, frame):
    W = []
    for b, (name, par) in enumerate(nodes):
        x, y, z, rx, ry, rz = frame[b]
        L = Matrix.Translation((x, y, z)) @ Euler((rx, ry, rz), "XYZ").to_matrix().to_4x4()
        W.append(L if par < 0 else W[par] @ L)
    return W


def main():
    key, blend, d = sys.argv[1], sys.argv[2], sys.argv[3]
    anim = sys.argv[4] if len(sys.argv) > 4 else "Attack"
    frame = int(sys.argv[5]) if len(sys.argv) > 5 else 24
    name = f"jiongu_{key}"
    nodes, rest, tris = parse(f"{d}/{name}_ref.smd")
    _, anim_frames, _ = parse(f"{d}/{name}_{anim.lower()}.smd")
    Wr = world(nodes, rest[0])
    Wa = world(nodes, anim_frames[frame - 1])
    skin = [Wa[b] @ Wr[b].inverted() for b in range(len(nodes))]
    # Blender ground truth
    bpy.ops.wm.open_mainfile(filepath=blend)
    ob = next(o for o in bpy.data.objects if o.type == "MESH")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    arm.animation_data.action = bpy.data.actions[f"{key}_{anim}"]
    bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    gt = []
    for lt in me.loop_triangles:
        for vi in lt.vertices:
            gt.append(np.array((ROT @ ob.matrix_world @ me.vertices[vi].co)[:]) * INCH)
    assert len(gt) == len(tris), (len(gt), len(tris))
    err = []
    rest_err = []
    for (mat, pos, links), g in zip(tris, gt):
        p = Vector(pos)
        q = sum(((skin[b] @ p) * w for b, w in links), Vector((0, 0, 0)))
        err.append((np.array(q[:]) - g))
    err = np.linalg.norm(np.array(err), axis=1)
    # bones' own rest pose: rest SMD must reproduce armature rest positions
    for b, bone in enumerate(arm.data.bones):
        h = np.array((ROT @ arm.matrix_world @ bone.head_local)[:]) * INCH
        rest_err.append(np.linalg.norm(np.array(Wr[b].translation[:]) - h))
    print(f"VALIDATE {key} {anim}@{frame}: verts {len(err)}  mean err {err.mean():.3f} in  p99 {np.percentile(err, 99):.3f} in  max {err.max():.3f} in"
          f" | bone rest max err {max(rest_err):.5f} in")


main()
