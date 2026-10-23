"""Run the TASTy scanner over the _3 jar of each coordinate in $LIBS (default libs.txt)."""
import os, re, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
X = os.path.dirname(os.path.abspath(__file__))
JAVA = os.environ.get("JAVA", "java")
CP = open(f"{X}/scan-cp.txt").read().strip()
COORDS = [l.split("#")[0].strip() for l in open(os.environ.get("LIBS", f"{X}/libs.txt")) if l.split("#")[0].strip()]
HOME = os.path.expanduser("~")


def fetch(coord):
    # Back off when Maven Central rate-limits us (HTTP 429).
    for delay in (0, 30, 60, 120, 240):
        time.sleep(delay)
        r = subprocess.run(["coursier", "fetch", "--scala-version", "3.3.6", "-p", coord], capture_output=True, text=True)
        if "HTTP 429" not in r.stderr:
            break
    return r


def job(coord):
    if shutil.disk_usage(os.path.expanduser("~")).free < 2e9:
        sys.exit("less than 2 GB free; stopping")
    r = fetch(coord)
    if r.returncode and not coord.endswith(":latest.release"):
        # Not every target is published at its project's version; take the latest release instead.
        coord = coord.rpartition(":")[0] + ":latest.release"
        r = fetch(coord)
    if r.returncode:
        return coord, "RESOLVE-FAIL", r.stderr.strip().splitlines()[-1:] if r.stderr else []
    jars = r.stdout.strip().split(":")
    name = coord.partition("::")[2].split(":")[0]
    main = [j for j in jars if re.search(rf"/{re.escape(name)}_3/[^/]+/{re.escape(name)}_3-[^/]+\.jar$", j)]
    if not main:
        return coord, "NO-MAIN-JAR", []
    # The scanner brings its own Scala 3 standard library; a second one on the classpath breaks loading.
    deps = [j for j in jars if j != main[0] and "/scala3-library_3/" not in j and "/scala-library/" not in j]
    r = subprocess.run([JAVA, "-Xss16m", "-Xmx3g", "-cp", CP, "runScan", os.path.basename(main[0]), main[0], ":".join(deps)],
                       capture_output=True, text=True, timeout=3600)
    lines = [l.replace(HOME, "$HOME") for l in (r.stdout + r.stderr).splitlines()]
    hits = [l for l in lines if l.startswith(("HIT", "TASTY-ERROR", "TRAVERSE-ERROR", "FAIL-ALONE", "SUMMARY"))]
    status = "OK" if r.returncode == 0 else "CRASH"
    if status == "CRASH":
        hits += ["  " + l for l in lines if "rror" in l or "Exception" in l][:3]
    return coord + " " + os.path.basename(main[0]), status, hits


with ThreadPoolExecutor(int(os.environ.get("JOBS", "8"))) as ex:
    for coord, status, hits in ex.map(job, COORDS):
        print(f"{status} {coord}", flush=True)
        for h in sorted(set(hits)):
            print("   ", h, flush=True)
