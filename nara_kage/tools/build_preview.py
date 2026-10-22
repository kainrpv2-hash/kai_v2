"""Prepare la preview : sons MP3 en base64 (preview/sounds.js) et version autonome en un seul fichier.

    python3 build_preview.py                 # ecrit preview/sounds.js
    python3 build_preview.py --single OUT    # ecrit aussi OUT : index.html avec textures et sons integres
"""
import base64
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PREVIEW = os.path.join(HERE, "..", "preview")
SND = os.path.join(HERE, "..", "gmod", "addon", "nara_kage", "sound", "nara_kage")
NAMES = ["mudra", "cast", "crawl_loop", "bind", "choke", "pierce", "release", "tick"]


def sounds_js():
    out = ["// Genere par tools/build_preview.py : les sons de l'addon en MP3.", "window.NARA_SND = {"]
    with tempfile.TemporaryDirectory() as tmp:
        for n in NAMES:
            mp3 = os.path.join(tmp, n + ".mp3")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(SND, n + ".wav"),
                            "-ac", "1", "-b:a", "64k", mp3], check=True)
            with open(mp3, "rb") as f:
                out.append('  %s: "%s",' % (n, base64.b64encode(f.read()).decode()))
    out.append("};")
    with open(os.path.join(PREVIEW, "sounds.js"), "w", newline="\n") as f:
        f.write("\n".join(out) + "\n")


def single(dst):
    html = open(os.path.join(PREVIEW, "index.html"), encoding="utf-8").read()
    for js in ("textures.js", "sounds.js"):
        tag = '<script src="%s"></script>' % js
        body = open(os.path.join(PREVIEW, js), encoding="utf-8").read()
        assert tag in html, tag
        html = html.replace(tag, "<script>\n" + body + "</script>")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)


if __name__ == "__main__":
    sounds_js()
    if len(sys.argv) >= 3 and sys.argv[1] == "--single":
        single(sys.argv[2])
    print("ok")
