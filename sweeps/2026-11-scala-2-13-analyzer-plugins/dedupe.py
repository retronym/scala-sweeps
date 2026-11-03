#!/usr/bin/env python3
"""Union candidates-*.txt, keep the highest 2.13.N (then highest version) per (group, base artifact) -> candidates-all.txt"""
import glob, re
best = {}
def key(v): return [int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", v)]
for f in sorted(glob.glob("candidates*.txt")):
    if f == "candidates-all.txt": continue
    for l in open(f):
        l = l.strip()
        if not l: continue
        g, a, v = l.split(":")
        m = re.match(r"(.*)_2\.13(?:\.(\d+))?$", a)
        if not m: continue
        k = (g, m.group(1)); rank = (int(m.group(2) or -1), key(v))
        if k not in best or rank > best[k][0]: best[k] = (rank, l)
open("candidates-all.txt", "w").write("".join(v[1] + "\n" for k, v in sorted(best.items())))
print(len(best))
