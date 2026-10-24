"""Load work/out/*/ into a DuckDB database (work/harvest.duckdb) and export each table as Parquet (work/parquet/).

Tables: libs, tasty_files, lib_deps, failures, defs, refs, imports, hist, findings, module_init, and
classes (top-level class -> module, for every jar on any harvested classpath). refs gets a
`target_module` column: the module that defines the target, preferring the referencing lib itself.
"""
import glob, json, os, re, sys, zipfile
import duckdb

X = os.path.dirname(os.path.abspath(__file__))
W = f"{X}/work"
HOME = os.path.expanduser("~")
db = duckdb.connect(f"{W}/harvest.duckdb.tmp")
db.execute(f"set preserve_insertion_order = false; set memory_limit = '16GB'; set temp_directory = '{W}/duckdb-tmp'")


OPS = {"$colon": ":", "$less": "<", "$greater": ">", "$eq": "=", "$bang": "!", "$hash": "#", "$percent": "%",
       "$up": "^", "$amp": "&", "$bar": "|", "$times": "*", "$div": "/", "$plus": "+", "$minus": "-", "$tilde": "~",
       "$qmark": "?", "$at": "@", "$bslash": "\\"}


def decode(name):
    """Undo the JVM name encoding of symbolic names, e.g. `$colon$colon` -> `::`."""
    return re.sub("|".join(re.escape(k) for k in sorted(OPS, key=len, reverse=True)), lambda m: OPS[m[0]], name)


def module(gav):
    return gav.rsplit(":", 1)[0]


libs, tasty, deps, jars = [], [], [], {}
for f in glob.glob(f"{W}/out/*/meta.json"):
    m = json.load(open(f))
    libs.append((m["lib"], module(m["lib"]), m["coord"], m["project"], m["status"], len(m["tasty"]), m["jar"]))
    tasty += [(m["lib"], t["file"], t["major"], t["minor"], t["experimental"], t["tooling"]) for t in m["tasty"]]
    deps += [(m["lib"], d) for d in m["deps"]]
    jars[m["lib"]] = m["jar"]
    for d, p in zip(m["deps"], m.get("dep_jars", [])):
        jars.setdefault(d, p)

db.execute("create or replace table libs(lib varchar, module varchar, coord varchar, project varchar, status varchar, n_tasty int, jar varchar)")
db.executemany("insert into libs values (?,?,?,?,?,?,?)", libs)
db.execute("create or replace table tasty_files(lib varchar, file varchar, major int, minor int, experimental int, tooling varchar)")
db.executemany("insert into tasty_files values (?,?,?,?,?,?)", tasty)
db.execute("create or replace table lib_deps(lib varchar, dep varchar)")
db.executemany("insert into lib_deps values (?,?)", deps)

# Top-level classes of every jar: `pkg/Foo.class`, `pkg/Foo$.class`, `pkg/Foo$package$.class` -> pkg.Foo / pkg.Foo$package
classes = set()
for g, p in jars.items():
    try:
        with zipfile.ZipFile(p.replace("$HOME", HOME)) as z:
            for n in z.namelist():
                if n.endswith(".class") and not n.startswith("META-INF/"):
                    c = n[:-6].removesuffix("$")
                    c = decode(c)
                    if "$" not in c or c.endswith("$package"):
                        classes.add((c.replace("/", "."), module(g)))
    except (OSError, zipfile.BadZipFile):
        pass
db.execute("create or replace table classes(class varchar, module varchar)")
db.executemany("insert into classes values (?,?)", sorted(classes))

opts = "delim='\t', header=true, quote='', escape='', nullstr='\\N', all_varchar=true, filename=false"
# Only jars whose harvest has finished (meta.json is written last), so a load can run alongside a harvest.
done = [os.path.dirname(f) for f in glob.glob(f"{W}/out/*/meta.json")]
for t in ["defs", "refs", "imports", "hist", "findings", "module_init", "failures"]:
    files = [f"{d}/{t}.tsv.gz" for d in done if os.path.exists(f"{d}/{t}.tsv.gz")]
    db.execute(f"create or replace table {t} as select * from read_csv({files!r}, {opts})")
for t, cols in [("refs", ["count", "files"]), ("imports", ["count", "files"]), ("hist", ["count"]), ("defs", ["line"])]:
    for c in cols:
        db.execute(f"alter table {t} alter {c} type bigint using try_cast({c} as bigint)")

db.execute(r"""
create or replace table refs as
with lm as (select lib, module as lib_module from libs),
     tl as (select distinct r.lib, lm.lib_module, r.top_level from refs r join lm using (lib)),
     cp as (select lib, regexp_replace(dep, ':[^:]+$', '') as module from lib_deps
            union select lib, module from libs),
     -- The module on the referencing lib's own classpath that defines the class; the lib itself first.
     m as (select tl.lib, tl.top_level,
                  coalesce(max(case when c.module = tl.lib_module then c.module end), min(c.module)) as target_module
           from tl left join (classes c join cp on cp.module = c.module) on c.class = tl.top_level and cp.lib = tl.lib
           group by tl.lib, tl.top_level)
select r.*,
       coalesce(m.target_module,
                case when regexp_matches(r.top_level, '^(java|javax|jdk|sun|com\.sun|org\.w3c|org\.xml|org\.ietf)\.') then 'JDK'
                     when regexp_matches(r.top_level, '^(scala\.(Any|AnyRef|AnyVal|Nothing|Null|Singleton|Matchable|&|\||ContextFunction\d+|<repeated>|<byname>)|<special-ops>.*)$') then 'scala (built-in)' end,
                '?') as target_module,
       coalesce(m.target_module = lm.lib_module, false) as self_ref
from refs r join lm using (lib) left join m using (lib, top_level)
""")

os.makedirs(f"{W}/parquet", exist_ok=True)
for (t,) in db.execute("select table_name from information_schema.tables").fetchall():
    db.execute(f"copy {t} to '{W}/parquet/{t}.parquet' (format parquet, compression zstd)")
    print(t, db.execute(f"select count(*) from {t}").fetchone()[0])
db.close()
os.replace(f"{W}/harvest.duckdb.tmp", f"{W}/harvest.duckdb")
