"""Cycles presentation renders in an ep.84-like rocky setting.

usage: python render.py <out.png> <res_x> <res_y> <samples> <cam spec> <creature:x:y:rotdeg:action:frame> [...]
cam spec: "x,y,z,tx,ty,tz,lens"
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

OUT = os.path.join(HERE, "out")


def append(key, lod="HQ"):
    path = os.path.join(OUT, f"Jiongu_{key.capitalize()}_{lod}.blend")
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith("Jiongu_")]
        dst.actions = list(src.actions)
    objs = [o for o in dst.objects if o]
    for o in objs:
        bpy.context.scene.collection.objects.link(o)
    arm = next(o for o in objs if o.type == "ARMATURE")
    return arm, objs


def node_mat(name, build):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    build(nt, nt.nodes["Principled BSDF"])
    return m


def rock_mat(name, dark, mid, light, scale=1.0, crack_tone=(0.45, 0.38, 0.3)):
    def b(nt, bsdf):
        n = nt.nodes
        tc = n.new("ShaderNodeTexCoord")
        noise = n.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 0.9 * scale
        noise.inputs["Detail"].default_value = 12
        noise.inputs["Roughness"].default_value = 0.6
        cracks = n.new("ShaderNodeTexVoronoi")
        cracks.feature = "DISTANCE_TO_EDGE"
        cracks.inputs["Scale"].default_value = 1.4 * scale
        warp = n.new("ShaderNodeTexNoise")
        warp.inputs["Scale"].default_value = 2.0 * scale
        sw = n.new("ShaderNodeVectorMath")
        sw.operation = "SCALE"
        sw.inputs["Scale"].default_value = 0.35
        nt.links.new(warp.outputs["Color"], sw.inputs[0])
        nt.links.new(tc.outputs["Object"], warp.inputs["Vector"])
        add = n.new("ShaderNodeVectorMath")
        add.operation = "ADD"
        nt.links.new(tc.outputs["Object"], add.inputs[0])
        nt.links.new(sw.outputs["Vector"], add.inputs[1])
        nt.links.new(add.outputs["Vector"], cracks.inputs["Vector"])
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        crack = n.new("ShaderNodeMapRange")
        crack.inputs["From Min"].default_value = 0.0
        crack.inputs["From Max"].default_value = 0.06
        nt.links.new(cracks.outputs["Distance"], crack.inputs["Value"])
        ramp = n.new("ShaderNodeValToRGB")
        e = ramp.color_ramp.elements
        e[0].position, e[0].color = 0.25, (*dark, 1)
        e[1].position, e[1].color = 0.75, (*light, 1)
        e.new(0.5).color = (*mid, 1)
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        crk = n.new("ShaderNodeValToRGB")
        crk.color_ramp.elements[0].color = (*crack_tone, 1)
        crk.color_ramp.elements[1].color = (1, 1, 1, 1)
        nt.links.new(crack.outputs["Result"], crk.inputs["Fac"])
        mul = n.new("ShaderNodeVectorMath")
        mul.operation = "MULTIPLY"
        nt.links.new(ramp.outputs["Color"], mul.inputs[0])
        nt.links.new(crk.outputs["Color"], mul.inputs[1])
        nt.links.new(mul.outputs["Vector"], bsdf.inputs["Base Color"])
        bump = n.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.5
        hb = n.new("ShaderNodeMath")
        hb.operation = "MULTIPLY_ADD"
        hb.inputs[1].default_value = 0.6
        nt.links.new(noise.outputs["Fac"], hb.inputs[0])
        nt.links.new(crack.outputs["Result"], hb.inputs[2])
        nt.links.new(hb.outputs[0], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        bsdf.inputs["Roughness"].default_value = 0.92
    return node_mat(name, b)


def env():
    sc = bpy.context.scene
    ground_m = rock_mat("Sand", (0.13, 0.1, 0.07), (0.25, 0.2, 0.13), (0.35, 0.28, 0.19), 0.7, (0.8, 0.74, 0.66))
    cliff_m = rock_mat("Cliff", (0.09, 0.07, 0.05), (0.27, 0.21, 0.14), (0.42, 0.34, 0.23), 0.6, (0.55, 0.47, 0.38))
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=160, y_subdivisions=160, size=40)
    g = bpy.context.active_object
    tex = bpy.data.textures.new("ground_noise", "CLOUDS")
    tex.noise_scale = 1.4
    d = g.modifiers.new("disp", "DISPLACE")
    d.texture = tex
    d.strength = 0.1
    d.mid_level = 0.6
    g.data.materials.append(ground_m)
    g.data.shade_smooth()
    # canyon wall behind (smooth large-scale displacement, cracks come from the shader)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=220, y_subdivisions=90, size=1)
    w = bpy.context.active_object
    w.scale = (44, 16, 1)
    w.rotation_euler = (math.radians(90), 0, 0)
    w.location = (0, 8.5, 6)
    for i, (sc_, st) in enumerate([(2.6, 2.6), (0.9, 0.8), (0.35, 0.22)]):
        t = bpy.data.textures.new(f"wall{i}", "CLOUDS")
        t.noise_scale = sc_
        t.noise_depth = 2
        m = w.modifiers.new(f"d{i}", "DISPLACE")
        m.texture = t
        m.texture_coords = "GLOBAL"
        m.direction = "Z"
        m.strength = st
    sub = w.modifiers.new("smooth", "SMOOTH")
    sub.iterations = 2
    w.data.materials.append(cliff_m)
    w.data.shade_smooth()
    # a few boulders at the foot of the wall
    for i, (x, y, r) in enumerate([(-7.5, 6.5, 1.6), (-4.2, 7.4, 1.1), (6.8, 6.8, 1.8), (9.8, 5.6, 1.2)]):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=r, location=(x, y, r * 0.35))
        rb = bpy.context.active_object
        rb.scale = (1.3, 0.9, 0.8)
        t = bpy.data.textures.new(f"boulder{i}", "CLOUDS")
        t.noise_scale = 0.8
        m = rb.modifiers.new("d", "DISPLACE")
        m.texture = t
        m.strength = 0.5
        rb.data.materials.append(cliff_m)
        rb.data.shade_smooth()
    # world: hazy warm sky
    wd = bpy.data.worlds.new("World")
    sc.world = wd
    nt = wd.node_tree
    bg = nt.nodes["Background"]
    bg.inputs["Color"].default_value = (0.42, 0.45, 0.52, 1)
    bg.inputs["Strength"].default_value = 0.45
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 1.5
    sun.data.color = (1.0, 0.92, 0.8)
    sun.data.angle = math.radians(4)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    sc.collection.objects.link(sun)
    rim = bpy.data.objects.new("Rim", bpy.data.lights.new("Rim", "AREA"))
    rim.data.energy = 1800
    rim.data.size = 8
    rim.data.color = (0.8, 0.88, 1.0)
    rim.location = (2, 5.5, 6)
    rim.rotation_euler = (math.radians(-60), 0, 0)
    sc.collection.objects.link(rim)
    wall_fill = bpy.data.objects.new("WallFill", bpy.data.lights.new("WallFill", "AREA"))
    wall_fill.data.energy = 1100
    wall_fill.data.size = 14
    wall_fill.data.color = (1.0, 0.94, 0.85)
    wall_fill.location = (-3, -6, 9)
    wall_fill.rotation_euler = (Vector((0, 8.5, 4)) - Vector((-3, -6, 9))).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(wall_fill)


def studio():
    sc = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    fl = bpy.context.active_object
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=14, depth=30, location=(0, 4, 0), rotation=(0, math.radians(90), 0))
    cyc = bpy.context.active_object
    m = bpy.data.materials.new("Cyc")
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.05, 0.05, 0.055, 1)
    b.inputs["Roughness"].default_value = 0.8
    fl.data.materials.append(m)
    cyc.data.materials.append(m)
    cyc.hide_render = True
    w = bpy.data.worlds.new("World")
    sc.world = w
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.055, 0.065, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

    def area(name, loc, target, energy, size, col):
        L = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        L.data.energy, L.data.size, L.data.color = energy, size, col
        L.location = loc
        L.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(L)
    area("Key", (-3.5, -5.0, 4.5), (0, 0, 1.4), 520, 3.0, (1.0, 0.95, 0.88))
    area("RimL", (-4.0, 4.5, 4.0), (0, 0, 1.6), 1500, 2.5, (0.7, 0.82, 1.0))
    area("RimR", (4.5, 4.0, 3.5), (0, 0, 1.6), 1500, 2.5, (1.0, 0.85, 0.7))
    area("Fill", (5.0, -4.0, 2.0), (0, 0, 1.2), 140, 4.0, (0.85, 0.9, 1.0))
    bk = bpy.data.objects.new("BackGlow", bpy.data.lights.new("BackGlow", "AREA"))
    bk.data.energy, bk.data.size = 400, 12
    bk.location = (0, 9, 6)
    bk.rotation_euler = (math.radians(-60), 0, 0)
    sc.collection.objects.link(bk)


def camera(spec):
    x, y, z, tx, ty, tz, lens = map(float, spec.split(","))
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.data.lens = lens
    cam.location = (x, y, z)
    d = Vector((tx, ty, tz)) - Vector((x, y, z))
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = d.length
    cam.data.dof.aperture_fstop = 16.0 if os.environ.get("KZ_STUDIO") else 5.6


def main():
    out, rx, ry, samples, cam = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    (studio if os.environ.get("KZ_STUDIO") else env)()
    frame = 1
    for spec in sys.argv[6:]:
        key, x, y, rot, action, fr = spec.split(":")
        arm, objs = append(key)
        arm.location = (float(x), float(y), 0)
        arm.rotation_euler = (0, 0, math.radians(float(rot)))
        act = bpy.data.actions.get(f"{key}_{action}")
        arm.animation_data_create()
        arm.animation_data.action = act
        frame = int(fr)
    sc.frame_set(frame)
    camera(cam)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.transparent_max_bounces = 48
    sc.cycles.use_adaptive_sampling = True
    sc.render.resolution_x, sc.render.resolution_y = rx, ry
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = out
    sc.render.threads_mode = "AUTO"
    bpy.ops.render.render(write_still=True)
    print("rendered", out)


main()
