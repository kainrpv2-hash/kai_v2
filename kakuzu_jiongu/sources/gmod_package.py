"""Build the Garry's Mod package: VTF textures, VMT materials, model sources (via gmod_export.py),
compile_all.bat. Run with the bpy venv python.

usage: python gmod_package.py <tex dir> <blend suffix> <out root>
"""
import io
import os
import subprocess
import sys

import numpy as np
from PIL import Image
import srctools.vtf as V

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = ("katon", "futon", "raiton", "suiton")
MASK_KIND = {"katon": "fire", "futon": "wind", "raiton": "lightning", "suiton": "water"}
FLIP_GREEN = True  # Source expects DirectX-style normal maps (green = down)


def load(texdir, name):
    for ext in (".png", ".jpg"):
        p = os.path.join(texdir, os.path.splitext(name)[0] + ext)
        if os.path.exists(p):
            return Image.open(p)
    raise FileNotFoundError(name)


def save_vtf(img, path, fmt, flags=V.VTFFlags.EMPTY, mips=True):
    img = img.convert("RGBA")
    w, h = img.size
    vtf = V.VTF(w, h, version=(7, 2), fmt=fmt, flags=flags)
    vtf.get().copy_from(img.tobytes(), V.ImageFormats.RGBA8888)
    if mips:
        vtf.compute_mipmaps()
    with open(path, "wb") as f:
        vtf.save(f)


def normal_src(img):
    a = np.asarray(img.convert("RGB")).copy()
    if FLIP_GREEN:
        a[..., 1] = 255 - a[..., 1]
    return Image.fromarray(a)


def lightwarp(path, steps):
    """Cel-shading ramp (x = half-lambert term). steps: list of (position, rgb)."""
    w = 256
    xs = np.linspace(0, 1, w)
    col = np.zeros((w, 3))
    for i, x in enumerate(xs):
        c = steps[0][1]
        for pos, rgb in steps:
            if x >= pos:
                c = rgb
        col[i] = c
    # 6 px soft edges between bands so the terminator is clean but not aliased
    k = np.ones(6) / 6
    for ch in range(3):
        col[:, ch] = np.convolve(np.pad(col[:, ch], 3, mode="edge"), k, mode="same")[3:-3]
    img = Image.fromarray((np.tile(col[None], (1, 1, 1)) * 255).clip(0, 255).astype(np.uint8))
    save_vtf(img, path, V.ImageFormats.BGR888, V.VTFFlags.CLAMP_S | V.VTFFlags.CLAMP_T | V.VTFFlags.NO_MIP, mips=False)


TOON = """"VertexLitGeneric"
{{
	"$basetexture" "models/kakuzu_jiongu/{tex}"
	"$bumpmap" "models/kakuzu_jiongu/jiongu_flat_n"
{extra}	"$phong" "1"
	"$phongexponent" "6"
	"$phongboost" "{phong}"
	"$phongfresnelranges" "[0.2 0.5 1]"
	"$rimlight" "1"
	"$rimlightexponent" "{rimexp}"
	"$rimlightboost" "{rim}"
	"$surfaceprop" "{surf}"
	"$lightwarptexture" "models/kakuzu_jiongu/{warp}"
}}
"""

OUTLINE = """"UnlitGeneric"
{
	"$basetexture" "models/kakuzu_jiongu/jiongu_outline"
	"$color" "[0 0 0]"
	"$surfaceprop" "flesh"
}
"""


def build_materials(texdir, outdir, style):
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if f.endswith((".vtf", ".vmt")):
            os.remove(os.path.join(outdir, f))
    DXT1, DXT5 = V.ImageFormats.DXT1, V.ImageFormats.DXT5
    save_vtf(load(texdir, "body_col"), os.path.join(outdir, "jiongu_body.vtf"), DXT1)
    save_vtf(load(texdir, "clump_col"), os.path.join(outdir, "jiongu_clump.vtf"), DXT1)
    save_vtf(load(texdir, "fur_atlas_col"), os.path.join(outdir, "jiongu_fur.vtf"), DXT5)
    save_vtf(load(texdir, "outline_col"), os.path.join(outdir, "jiongu_outline.vtf"), V.ImageFormats.BGR888, mips=False)
    flat = Image.new("RGB", (64, 64), (128, 128, 255))
    save_vtf(flat, os.path.join(outdir, "jiongu_flat_n.vtf"), V.ImageFormats.BGR888, V.VTFFlags.NORMAL)
    for k in KEYS:
        save_vtf(load(texdir, f"mask_{MASK_KIND[k]}_col"), os.path.join(outdir, f"jiongu_{k}_mask.vtf"), DXT1)
        save_vtf(load(texdir, f"mask_{MASK_KIND[k]}_cracked_col"), os.path.join(outdir, f"jiongu_{k}_mask_cracked.vtf"), DXT1)
    lightwarp(os.path.join(outdir, "jiongu_lightwarp.vtf"), style["warp_body"])
    lightwarp(os.path.join(outdir, "jiongu_lightwarp_mask.vtf"), style["warp_mask"])
    thread = dict(phong=style["phong"], rim=style["rim"], rimexp=3, surf="flesh", warp="jiongu_lightwarp")
    open(os.path.join(outdir, "jiongu_body.vmt"), "w").write(TOON.format(tex="jiongu_body", extra="", **thread))
    open(os.path.join(outdir, "jiongu_clump.vmt"), "w").write(TOON.format(tex="jiongu_clump", extra="", **thread))
    fur_extra = '\t"$alphatest" "1"\n\t"$alphatestreference" "0.5"\n\t"$allowalphatocoverage" "1"\n\t"$nocull" "1"\n'
    open(os.path.join(outdir, "jiongu_fur.vmt"), "w").write(TOON.format(tex="jiongu_fur", extra=fur_extra, **thread))
    open(os.path.join(outdir, "jiongu_outline.vmt"), "w").write(OUTLINE)
    mask = dict(phong=0.15, rim=1, rimexp=4, surf="porcelain", warp="jiongu_lightwarp_mask")
    for k in KEYS:
        for suf in ("", "_cracked"):
            open(os.path.join(outdir, f"jiongu_{k}_mask{suf}.vmt"), "w").write(TOON.format(tex=f"jiongu_{k}_mask{suf}", extra="", **mask))


BAT = r'''@echo off
REM ============================================================
REM  Kakuzu - Jiongu : compile les 4 modeles pour Garry's Mod
REM  Double-clique ce fichier. Si Garry's Mod n'est pas dans le
REM  dossier Steam par defaut, corrige la ligne GMOD ci-dessous.
REM ============================================================
setlocal
set "GMOD=C:\Program Files (x86)\Steam\steamapps\common\GarrysMod"
set "STUDIOMDL=%GMOD%\bin\studiomdl.exe"
set "HERE=%~dp0"

if not exist "%STUDIOMDL%" (
  echo [ERREUR] studiomdl.exe introuvable : "%STUDIOMDL%"
  echo Ouvre ce fichier avec le Bloc-notes et corrige la ligne "set GMOD=..."
  pause
  exit /b 1
)

for %%M in (katon futon raiton suiton) do (
  echo.
  echo ===== Compilation de jiongu_%%M =====
  "%STUDIOMDL%" -game "%GMOD%\garrysmod" -nop4 -nox360 "%HERE%modelsrc\jiongu_%%M\jiongu_%%M.qc"
  if errorlevel 1 (
    echo [ERREUR] La compilation de jiongu_%%M a echoue. Lis les messages ci-dessus.
    pause
    exit /b 1
  )
)

echo.
echo ===== Copie des modeles dans l'addon =====
if not exist "%HERE%addon\kakuzu_jiongu\models\kakuzu_jiongu" mkdir "%HERE%addon\kakuzu_jiongu\models\kakuzu_jiongu"
copy /Y "%GMOD%\garrysmod\models\kakuzu_jiongu\*.*" "%HERE%addon\kakuzu_jiongu\models\kakuzu_jiongu\" >nul
del /Q "%GMOD%\garrysmod\models\kakuzu_jiongu\*.*"
rmdir "%GMOD%\garrysmod\models\kakuzu_jiongu"

echo.
echo Termine ! Copie maintenant le dossier addon\kakuzu_jiongu dans :
echo   "%GMOD%\garrysmod\addons\"
echo (et dans garrysmod\addons de ton serveur).
pause
'''


def main():
    texdir, suffix, root = sys.argv[1], sys.argv[2], sys.argv[3]
    style = dict(
        phong=0.08, rim=2.0,
        # hard 3-tone cel ramp, cool (blue-grey) shadow side, step near 45 % as in Storm-4 ports
        warp_body=[(0.0, (0.22, 0.23, 0.32)), (0.44, (0.52, 0.53, 0.62)), (0.6, (1.0, 1.0, 1.0))],
        warp_mask=[(0.0, (0.58, 0.58, 0.68)), (0.44, (0.84, 0.84, 0.9)), (0.58, (1.0, 1.0, 1.0))],
    )
    if len(sys.argv) > 4:
        import json
        style.update(json.loads(sys.argv[4]))
    addon = os.path.join(root, "addon", "kakuzu_jiongu")
    build_materials(texdir, os.path.join(addon, "materials", "models", "kakuzu_jiongu"), style)
    py = sys.executable
    for k in KEYS:
        blend = os.path.join(HERE, "out", f"Jiongu_{k.capitalize()}_{suffix}.blend")
        r = subprocess.run([py, os.path.join(HERE, "gmod_export.py"), k, blend, os.path.join(root, "modelsrc", f"jiongu_{k}")],
                           capture_output=True, text=True)
        print([l for l in r.stdout.splitlines() if l.startswith("EXPORTED")] or r.stderr[-2000:])
    open(os.path.join(root, "compile_all.bat"), "w", newline="\r\n").write(BAT)
    print("package ok")


main()
