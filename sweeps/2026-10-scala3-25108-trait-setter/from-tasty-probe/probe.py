"""Run the PROBE-25108 compiler -from-tasty over published Scala 3 jars."""
import glob, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
X = os.path.dirname(os.path.abspath(__file__))
JAVA = os.environ.get("JAVA", "java")
SCALA3 = os.environ["SCALA3"]  # scala3 checkout used by setup.sh
S3LIB = glob.glob(f"{SCALA3}/library/target/scala-library-nonbootstrapped/scala-library-*-nonbootstrapped.jar")[0]
CP = open(f"{X}/probe-cp.txt").read().strip()
COORDS = [l.split("#")[0].strip() for l in open(f"{X}/libs.txt") if l.split("#")[0].strip()]


def job(coord):
    tag = re.sub(r"[^A-Za-z0-9]+", "_", coord)
    r = subprocess.run(["coursier", "fetch", "--scala-version", "3.3.6", "-p", coord], capture_output=True, text=True)
    if r.returncode:
        return coord, "RESOLVE-FAIL", r.stderr.strip().splitlines()[-1:] if r.stderr else []
    jars = r.stdout.strip().split(":")
    org, _, rest = coord.partition("::")
    name = rest.split(":")[0]
    main = [j for j in jars if re.search(rf"/{re.escape(name)}_3/[^/]+/{re.escape(name)}_3-[^/]+\.jar$", j)]
    if not main:
        return coord, "NO-MAIN-JAR", []
    out = f"{X}/work/tasty/{tag}"
    os.makedirs(out, exist_ok=True)
    deps = [j for j in jars if j != main[0]]
    # The library under test is compiled against the jar's own classpath; use our scala3-library.
    deps = [j for j in deps if "/scala3-library_3/" not in j and "/scala-library/" not in j]
    r = subprocess.run([JAVA, "-Xss16m", "-Xmx3g", "-cp", CP, "dotty.tools.dotc.Main", "-from-tasty", "-nowarn", "-color:never",
                        "-classpath", ":".join([S3LIB] + deps), "-d", out, main[0]], capture_output=True, text=True, timeout=3600)
    hits = sorted(set(l for l in (r.stdout + r.stderr).splitlines() if l.startswith("PROBE-25108")))
    status = "OK" if r.returncode == 0 else "COMPILE-FAIL"
    if r.returncode:
        hits.append("  " + " | ".join([l for l in (r.stdout + r.stderr).splitlines() if "rror" in l][:2]))
    return coord + " " + os.path.basename(main[0]), status, hits


with ThreadPoolExecutor(int(os.environ.get("JOBS", "8"))) as ex:
    for coord, status, hits in ex.map(job, COORDS):
        print(f"{status} {coord}", flush=True)
        for h in hits:
            print("   ", h, flush=True)
