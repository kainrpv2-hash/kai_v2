"""Bundle the web viewer into ONE offline HTML file (three.js bundled with esbuild, models and renders embedded).
Open it by double-click, no internet or server needed.

usage: python build_offline.py <viewer dir> <out.html> [--no-shots]
"""
import base64
import os
import re
import subprocess
import sys

VT = "/tmp/claude-0/-home-user-kai-v2/6109f98f-4373-562e-8fa2-e7fec075d247/scratchpad/vtest"
vdir, out = sys.argv[1], sys.argv[2]
shots = "--no-shots" not in sys.argv
html = open(os.path.join(vdir, "index.html")).read()

m = re.search(r'<script type="module">(.*?)</script>', html, re.S)
js = m.group(1)
# models come from embedded JSON instead of the network
js = js.replace(
    "loader.load('models/' + DATA[keyName].file, g => { cache[keyName] = prepare(g); resolve(cache[keyName]); },",
    "loader.parse(document.getElementById('m-' + keyName).textContent, '', g => { cache[keyName] = prepare(g); resolve(cache[keyName]); },")
js = js.replace("""      e => { if (e.total) statusEl.textContent = `Chargement… ${Math.round(e.loaded / e.total * 100)} %`; },
      reject);""", "      reject);")
assert "loader.parse(" in js
# gallery: embedded images
js = js.replace("fetch('renders/hero_katon.jpg', { method: 'HEAD' }).then(r => {\n  if (!r.ok) return;",
                "Promise.resolve(window.__SHOTS || null).then(r => {\n  if (!r) return;")
js = js.replace('<img src="renders/${f}.jpg"', '<img src="${window.__SHOTS[f]}"')
os.makedirs(os.path.join(VT, "offline"), exist_ok=True)
entry = os.path.join(VT, "offline", "viewer_entry.js")
open(entry, "w").write(js)
bundle = os.path.join(VT, "offline", "bundle.js")
subprocess.run([os.path.join(VT, "node_modules/.bin/esbuild"), entry, "--bundle", "--format=iife", "--minify",
                "--log-level=warning", f"--outfile={bundle}"], check=True, cwd=VT,
               env=dict(os.environ, NODE_PATH=os.path.join(VT, "node_modules")))
# esbuild resolves bare "three" and "three/addons/..." through the exports map of the three package
code = open(bundle).read()

head = html[: m.start()]
head = re.sub(r'<script type="importmap">.*?</script>', "", head, flags=re.S)
models = []
for f in sorted(os.listdir(os.path.join(vdir, "models"))):
    key = f.split("_")[1].lower()
    data = open(os.path.join(vdir, "models", f)).read().replace("</", "<\\/")
    models.append(f'<script type="application/json" id="m-{key}">{data}</script>')
shot_js = ""
if shots:
    d = {}
    for f in sorted(os.listdir(os.path.join(vdir, "renders"))):
        if f.endswith(".jpg"):
            d[f[:-4]] = "data:image/jpeg;base64," + base64.b64encode(open(os.path.join(vdir, "renders", f), "rb").read()).decode()
    import json
    shot_js = "<script>window.__SHOTS = " + json.dumps(d) + ";</script>"
doc = ("<!doctype html>\n<html lang=\"fr\"><head><meta charset=\"utf-8\">"
       "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">\n"
       + head + "\n" + "\n".join(models) + "\n" + shot_js + "\n<script>" + code + "</script>\n</html>\n")
open(out, "w").write(doc)
print("offline viewer", out, round(os.path.getsize(out) / 2 ** 20, 1), "MiB")
