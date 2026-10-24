"""Harvest every coordinate in $LIBS (one or more files, colon-separated) into work/out/<jar>/.

Per jar: the harvester's tables, plus meta.json with the coordinate, the resolved classpath and the
TASTy header (version, producing compiler) of each .tasty file. Jars already harvested are skipped,
so a run can be resumed.
"""
import json, os, re, shutil, struct, subprocess, sys, threading, time, zipfile
from concurrent.futures import ThreadPoolExecutor

X = os.path.dirname(os.path.abspath(__file__))
JAVA = os.environ.get("JAVA", "java")
CP = open(f"{X}/harvester/cp.txt").read().strip()
OUT = f"{X}/work/out"
HOME = os.path.expanduser("~")
LIBS = os.environ.get("LIBS", f"{X}/../2026-10-scala3-block-val-literals/tasty-scan/libs-ocb.txt:{X}/../2026-10-scala3-block-val-literals/tasty-scan/libs.txt")


def coords():
    seen = set()
    for f in LIBS.split(":"):
        for l in open(f):
            c, _, comment = l.partition("#")
            c = c.strip()
            if c and c not in seen:
                seen.add(c)
                yield c, comment.strip()


def fetch(coord):
    r = subprocess.run(["coursier", "fetch", "--mode", "offline", "--scala-version", "3.3.6", "-p", coord], capture_output=True, text=True)
    if r.returncode == 0:
        return r
    # Back off when Maven Central rate-limits us (HTTP 429).
    for delay in (0, 30, 60, 120, 240):
        time.sleep(delay)
        r = subprocess.run(["coursier", "fetch", "--scala-version", "3.3.6", "-p", coord], capture_output=True, text=True)
        if "HTTP 429" not in r.stderr:
            break
    return r


def gav(jar):
    m = re.search(r"/maven2/(.+)/([^/]+)/([^/]+)/[^/]+\.jar$", jar)
    return f"{m[1].replace('/', '.')}:{m[2]}:{m[3]}" if m else os.path.basename(jar)


def nat(b, i):
    """A TASTy Nat: big-endian base 128, the last byte has its high bit set."""
    x = 0
    while True:
        c = b[i]; i += 1
        x = (x << 7) | (c & 0x7f)
        if c & 0x80:
            return x, i


def tasty_header(data):
    if data[:4] != b"\x5c\xa1\xab\x1f":
        return None
    major, i = nat(data, 4)
    minor, i = nat(data, i)
    exp, i = nat(data, i)
    n, i = nat(data, i)
    return {"major": major, "minor": minor, "experimental": exp, "tooling": data[i:i + n].decode("utf-8", "replace")}


claimed, lock = set(), threading.Lock()


def job(item):
    coord, project = item
    if shutil.disk_usage(HOME).free < 5e9:
        return coord, "NO-DISK", ""
    r = fetch(coord)
    if r.returncode and not coord.endswith(":latest.release"):
        # Not every target is published at its project's version; take the latest release instead.
        coord = coord.rpartition(":")[0] + ":latest.release"
        r = fetch(coord)
    if r.returncode:
        return coord, "RESOLVE-FAIL", (r.stderr.strip().splitlines() or [""])[-1].replace(HOME, "$HOME")
    jars = r.stdout.strip().split(":")
    name = coord.partition("::")[2].split(":")[0]
    main = [j for j in jars if re.search(rf"/{re.escape(name)}_3/[^/]+/{re.escape(name)}_3-[^/]+\.jar$", j)]
    if not main:
        return coord, "NO-MAIN-JAR", ""
    main = main[0]
    lib = gav(main)
    with lock:
        if lib in claimed:
            return coord, "DUPLICATE", lib
        claimed.add(lib)
    out = f"{OUT}/{re.sub(r'[^A-Za-z0-9.]+', '_', lib)}"
    if os.path.exists(f"{out}/meta.json"):
        return coord, "DONE-ALREADY", lib
    # The harvester brings its own Scala 3 standard library; a second one on the classpath breaks loading.
    deps = [j for j in jars if j != main and "/scala3-library_3/" not in j and "/scala-library/" not in j]
    os.makedirs(out, exist_ok=True)
    try:
        p = subprocess.run([JAVA, "-Xss16m", "-Xmx4g", "-cp", CP, "runHarvest", lib, main, out, ":".join(deps)],
                           capture_output=True, text=True, timeout=5400)
        status = "OK" if p.returncode == 0 else "CRASH"
        summary = next((l for l in p.stdout.splitlines() if l.startswith("HARVESTED")), "")
        if status == "CRASH":
            summary = " | ".join(l for l in (p.stdout + p.stderr).splitlines() if "rror" in l or "Exception" in l)[:500]
    except subprocess.TimeoutExpired:
        status, summary = "TIMEOUT", ""
    headers = []
    with zipfile.ZipFile(main) as z:
        for n in z.namelist():
            if n.endswith(".tasty"):
                with z.open(n) as f:
                    h = tasty_header(f.read(512))
                if h:
                    headers.append({"file": n, **h})
    meta = {"lib": lib, "coord": coord, "project": project, "status": status, "summary": summary,
            "jar": main.replace(HOME, "$HOME"), "deps": [gav(d) for d in jars if d != main], "dep_jars": [d.replace(HOME, "$HOME") for d in jars if d != main], "tasty": headers}
    json.dump(meta, open(f"{out}/meta.json", "w"))
    return coord, status, summary.replace(HOME, "$HOME")


with ThreadPoolExecutor(int(os.environ.get("JOBS", "8"))) as ex:
    for coord, status, detail in ex.map(job, list(coords())):
        print(f"{status} {coord} {detail}", flush=True)
