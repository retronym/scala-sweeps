#!/usr/bin/env python3
"""Scan jars for scalac plugins and uses of typechecker.Analyzer. usage: scan.py candidates.txt -> results.tsv"""
import struct, subprocess, sys, zipfile, io, os, concurrent.futures as cf
PARTS = {b"scala/tools/nsc/typechecker/" + n for n in
         (b"Analyzer", b"Namers", b"Typers", b"Contexts", b"Implicits", b"Infer", b"Macros", b"Unapplies", b"NamesDefaults", b"Duplicators", b"AnalyzerPlugins")}
def parse(data):
    """-> (this, super, interfaces, class names in constant pool)"""
    n = struct.unpack(">H", data[8:10])[0]; i = 10; utf = {}; cls = []
    k = 1
    while k < n:
        t = data[i]
        if t == 1:
            l = struct.unpack(">H", data[i+1:i+3])[0]; utf[k] = data[i+3:i+3+l]; i += 3 + l
        elif t in (3, 4, 9, 10, 11, 12, 17, 18): i += 5
        elif t in (5, 6): i += 9; k += 1
        elif t in (7, 8, 16, 19, 20):
            if t == 7: cls.append(struct.unpack(">H", data[i+1:i+3])[0])
            i += 3
        elif t == 15: i += 4
        else: raise ValueError(t)
        k += 1
    name = lambda ci: utf.get(ci)
    def cname(idx):
        j = 10; k = 1
        return None
    return utf, cls, data, i
def classinfo(data):
    utf, clsidx, data, i = parse(data)
    # re-walk to map class index -> name
    n = struct.unpack(">H", data[8:10])[0]; j = 10; k = 1; cmap = {}
    while k < n:
        t = data[j]
        if t == 1: j += 3 + struct.unpack(">H", data[j+1:j+3])[0]
        elif t == 7: cmap[k] = utf[struct.unpack(">H", data[j+1:j+3])[0]]; j += 3
        elif t in (3, 4, 9, 10, 11, 12, 17, 18): j += 5
        elif t in (5, 6): j += 9; k += 1
        elif t in (8, 16, 19, 20): j += 3
        elif t == 15: j += 4
        k += 1
    this, sup, ic = struct.unpack(">HHH", data[i+2:i+8])
    ifs = struct.unpack(">%dH" % ic, data[i+8:i+8+2*ic])
    return cmap[this], cmap.get(sup), [cmap[x] for x in ifs], set(cmap.values())
def scan(coord):
    g, a, v = coord.split(":")
    r = subprocess.run(["coursier", "fetch", "--intransitive", coord], capture_output=True, text=True)
    if r.returncode: return [(coord, "NOFETCH", "", "")]
    jar = r.stdout.strip().splitlines()[-1]
    rows = []; isplugin = False
    try:
        z = zipfile.ZipFile(jar)
        isplugin = "scalac-plugin.xml" in z.namelist()
        for nm in z.namelist():
            if not nm.endswith(".class") or nm.startswith("META-INF/versions"): continue
            if nm.startswith(("scala/tools/nsc/", "scala/reflect/", "scala/tools/reflect/")): continue  # bundled compiler (e.g. scalac-profiling)
            try: this, sup, ifs, refs = classinfo(z.read(nm))
            except Exception: continue
            if b"scala/tools/nsc/plugins/Plugin" == (sup or b""): isplugin = True
            hit = [x for x in ([sup] if sup else []) + ifs if x in PARTS]
            if hit: rows.append((coord, "EXTENDS", this.decode(), ",".join(h.decode().rsplit("/",1)[1] for h in hit)))
            elif b"scala/tools/nsc/typechecker/Analyzer" in refs: rows.append((coord, "REFS", this.decode(), "Analyzer"))
    except zipfile.BadZipFile: return [(coord, "BADZIP", "", "")]
    return rows + [(coord, "PLUGIN" if isplugin else "NOTPLUGIN", "", "")]
if __name__ == "__main__":
    cs = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    with cf.ThreadPoolExecutor(8) as ex, open(sys.argv[2] if len(sys.argv) > 2 else "results.tsv", "w") as out:
        for rows in ex.map(scan, cs):
            for r in rows: out.write("\t".join(r) + "\n")
            out.flush()
