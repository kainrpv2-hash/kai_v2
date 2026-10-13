import json, struct, base64, sys, os
for f in sys.argv[2:]:
    b = open(f, 'rb').read()
    total = struct.unpack('<III', b[:12])[2]
    off, js, bin_ = 12, None, None
    while off < total:
        ln, typ = struct.unpack('<II', b[off:off + 8])
        chunk = b[off + 8: off + 8 + ln]
        if typ == 0x4E4F534A: js = json.loads(chunk)
        elif typ == 0x004E4942: bin_ = chunk
        off += 8 + ln
    js['buffers'][0]['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(bin_).decode()
    out = os.path.join(sys.argv[1], os.path.basename(f).replace('.glb', '.gltf.json'))
    open(out, 'w').write(json.dumps(js, separators=(',', ':')))
    print(out, round(os.path.getsize(out) / 1e6, 2), 'MB')
