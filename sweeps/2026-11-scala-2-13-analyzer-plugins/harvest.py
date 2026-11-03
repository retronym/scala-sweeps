#!/usr/bin/env python3
"""Candidate scalac plugin coordinates from Maven Central search (org:name:latest), written to candidates.txt.
Keeps artifacts built for Scala 2.13 (`_2.13` or `_2.13.N`) and, for full-version-cross-built ones, every distinct artifactId's latest version."""
import json, re, sys, urllib.parse, urllib.request
QUERIES = ["scalac plugin", "scala compiler plugin", "scala compiler-plugin", "scalac-plugin", "wartremover", "kind-projector",
  "semanticdb-scalac", "scoverage", "scapegoat", "silencer", "splain", "better-monadic-for", "scala-js compiler", "scalajs-compiler",
  "nscplugin", "paradise", "genjavadoc", "acyclic", "linter", "clippy", "scalac-profiling", "bm4", "typelevel plugin", "macro paradise",
  "scala-async", "continuations", "unused", "scalamacros", "scala typed holes", "zinc", "aux plugin", "scalafix", "scala-native nscplugin",
  "hearth", "scala-compiler-plugin", "cats plugin", "refined plugin", "scalac plugin 2.13", "compilerplugin", "scalac-scoverage-plugin",
  "nowarn plugin", "scala-xml plugin", "protoquill", "scala plugin compiler phase", "deadcode", "unused-imports", "tpolecat", "strict-scala", "plugin_2.13"]
out = {}
def get(q, start):
    u = "https://search.maven.org/solrsearch/select?" + urllib.parse.urlencode({"q": q, "rows": 200, "start": start, "wt": "json"})
    return json.load(urllib.request.urlopen(u, timeout=60))["response"]
for q in QUERIES:
    for start in range(0, 1000, 200):
        try: r = get(q, start)
        except Exception as e: print("ERR", q, e, file=sys.stderr); break
        for d in r["docs"]:
            if re.search(r"_2\.13(\.\d+)?$", d["a"]) and d.get("p") in ("jar", "bundle"):
                out[(d["g"], d["a"])] = d["latestVersion"]
        if start + 200 >= r["numFound"]: break
with open("candidates.txt", "w") as f:
    for (g, a), v in sorted(out.items()): f.write(f"{g}:{a}:{v}\n")
print(len(out), "candidates")
