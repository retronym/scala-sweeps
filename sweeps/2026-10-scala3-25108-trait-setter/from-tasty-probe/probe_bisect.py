"""For jars whose -from-tasty compile fails, probe their .tasty files in chunks, bisecting failing chunks."""
import glob, os, re, subprocess, sys, zipfile
from concurrent.futures import ThreadPoolExecutor
X = os.path.dirname(os.path.abspath(__file__))
JAVA = os.environ.get("JAVA", "java")
SCALA3 = os.environ["SCALA3"]  # scala3 checkout used by setup.sh
S3LIB = glob.glob(f"{SCALA3}/library/target/scala-library-nonbootstrapped/scala-library-*-nonbootstrapped.jar")[0]
CP = open(f"{X}/probe-cp.txt").read().strip()
COORDS = [l.strip() for l in open(f"{X}/libs-failed.txt") if l.strip()]
pool = ThreadPoolExecutor(int(os.environ.get("JOBS", "10")))


def resolve(coord):
    r = subprocess.run(["coursier", "fetch", "--scala-version", "3.3.6", "-p", coord], capture_output=True, text=True)
    jars = r.stdout.strip().split(":")
    name = coord.partition("::")[2].split(":")[0]
    main = [j for j in jars if re.search(rf"/{re.escape(name)}_3/[^/]+/{re.escape(name)}_3-[^/]+\.jar$", j)][0]
    deps = [j for j in jars if j != main and "/scala3-library_3/" not in j and "/scala-library/" not in j]
    return main, deps


def compile_files(tag, files, cp):
    out = f"{X}/work/bisect/{tag}/out"
    os.makedirs(out, exist_ok=True)
    argf = f"{X}/work/bisect/{tag}/args-{abs(hash(tuple(files)))}"
    open(argf, "w").write("\n".join(files))
    r = subprocess.run([JAVA, "-Xss16m", "-Xmx3g", "-cp", CP, "dotty.tools.dotc.Main", "-from-tasty", "-nowarn", "-color:never",
                        "-classpath", cp, "-d", out, f"@{argf}"], capture_output=True, text=True, timeout=3600)
    o = r.stdout + r.stderr
    return r.returncode == 0, sorted(set(l for l in o.splitlines() if l.startswith("PROBE-25108")))


def probe(tag, files, cp):
    """Returns (hits, files that fail on their own)."""
    ok, hits = compile_files(tag, files, cp)
    if ok:
        return hits, []
    if len(files) == 1:
        return hits, files  # partial hits from a failing file are still real
    mid = len(files) // 2
    (ha, fa), (hb, fb) = probe(tag, files[:mid], cp), probe(tag, files[mid:], cp)
    return sorted(set(ha + hb)), fa + fb


def job(coord):
    main, deps = resolve(coord)
    tag = re.sub(r"[^A-Za-z0-9]+", "_", coord)
    d = f"{X}/work/bisect/{tag}/tasty"
    os.makedirs(d, exist_ok=True)
    with zipfile.ZipFile(main) as z:
        names = [n for n in z.namelist() if n.endswith(".tasty")]
        z.extractall(d, names)
    files = sorted(f"{d}/{n}" for n in names)
    # The jar itself goes on the classpath, so files compiled in separate chunks still see each other.
    cp = ":".join([S3LIB, main] + deps)
    chunks = [files[i:i + 50] for i in range(0, len(files), 50)]
    futs = [pool.submit(probe, tag, c, cp) for c in chunks]
    hits, bad = [], []
    for f in futs:
        h, b = f.result()
        hits += h; bad += b
    return coord, len(files), sorted(set(hits)), bad


outer = ThreadPoolExecutor(4)
for coord, n, hits, bad in outer.map(job, COORDS):
    print(f"{coord}: {n} tasty files, {len(bad)} fail alone", flush=True)
    for h in hits:
        print("   ", h, flush=True)
    for b in bad[:5]:
        print("    BAD", os.path.basename(b), flush=True)
