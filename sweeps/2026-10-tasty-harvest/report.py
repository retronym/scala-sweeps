"""Generate REPORT.md from work/harvest.duckdb."""
import csv, os, re
import duckdb

X = os.path.dirname(os.path.abspath(__file__))
db = duckdb.connect(f"{X}/work/harvest.duckdb", read_only=True)
# Count one version per module (the community build's, else the newest), so a module harvested in two versions counts once.
# The database keeps every version.
CAT = db.execute("select current_database()").fetchone()[0]
db.execute(f"""create temp table primary_libs as
  select arg_max(lib, (project <> '', lib)) as lib from {CAT}.main.libs group by module""")
for t in ["libs", "tasty_files", "lib_deps", "defs", "refs", "imports", "hist", "findings", "module_init", "failures"]:
    db.execute(f"create temp view {t} as select * from {CAT}.main.{t} where lib in (select lib from primary_libs)")
db.execute(f"create temp table projects as select * from read_csv('{X}/projects.tsv', delim='\t', header=true, all_varchar=true)")
db.execute("""create temp table lib_link as
  select l.lib, l.module, p.repo_url, p.revision from libs l left join projects p on p.project = l.project""")
links = {r[0]: (r[1], r[2]) for r in db.execute("select lib, repo_url, revision from lib_link where repo_url is not null").fetchall()}
out = []


def w(s=""):
    out.append(s)


def q(sql):
    return db.execute(sql).fetchall()


def one(sql):
    return db.execute(sql).fetchone()[0]


def site(lib, s):
    """`file:line` as a link to the source at the published revision, when the project is known."""
    m = re.match(r"(.*):(\d+)$", s or "")
    if not m or lib not in links or not links[lib][1] or m[1].startswith("/"):
        return f"`{s}`"
    repo, rev = links[lib]
    path = re.sub(r"^.*?/(src_managed|target)/.*", "", m[1])
    if not path:
        return f"`{s}`"
    return f"[`{os.path.basename(m[1])}:{m[2]}`]({repo}/blob/{rev}/{m[1]}#L{m[2]})"


def short(lib):
    return lib.split(":")[1].removesuffix("_3") + " " + lib.split(":")[2] if lib.count(":") == 2 else lib


def table(headers, rows):
    w("| " + " | ".join(headers) + " |")
    w("|" + "---|" * len(headers))
    for r in rows:
        w("| " + " | ".join(str(c).replace("|", "\\|") if c is not None else "" for c in r) + " |")
    w()


def fmt(n):
    return f"{n:,}" if isinstance(n, int) else n


# ---------------------------------------------------------------------------------------------
n_libs = one("select count(*) from libs")
n_ok = one("select count(*) from libs where status = 'OK'")
n_tasty = one("select count(*) from tasty_files")
n_fail = one("select count(*) from failures")
n_defs = one("select count(*) from defs")
n_refs = one("select sum(count) from refs")
n_projects = one("select count(distinct project) from libs where project <> ''")

w("# What published Scala 3 code looks like, from its TASTy")
w()
n_all = one(f"select count(*) from {CAT}.main.libs")
w(f"One pass over the TASTy of **{n_libs:,} published `_3` modules** from {n_projects:,} open community build projects and the #25108 seed corpus: "
  f"{n_tasty:,} `.tasty` files, {n_defs:,} non-local definitions and {n_refs:,} references to non-local symbols. "
  f"{n_fail:,} `.tasty` files ({100 * n_fail / max(n_tasty, 1):.1f}%) fail to load on their own and are left out. "
  f"{n_all - n_libs} modules were harvested in two versions ({n_all:,} jars in all); the report counts each module once. "
  "Every number below is a query over the tables described in the [README](README.md); rerun or extend them with DuckDB.")
w()
w("Sites link to the source at the published revision where the project's repository is known. *Libs* counts modules (one version each).")
w()

# ---------------------------------------------------------------------------------------------
w("## 1. Ecosystem census")
w()
w("**Compiler that produced the published TASTy** (the newest compiler version in each jar's TASTy headers):")
w()
rows = q("""
with v as (select lib, max_by(tooling, tooling) as tooling from tasty_files group by lib)
select regexp_extract(tooling, 'Scala (3\\.\\d+)', 1) as series, count(*) libs,
       string_agg(distinct tooling, ', ' order by tooling) filter (where tooling ~ '(RC|NIGHTLY|nonbootstrapped)') as prereleases
from v group by 1 order by try_cast(split_part(series, '.', 2) as int)""")
table(["Series", "Libs", "Pre-release compilers seen"], [(r[0] or "?", fmt(r[1]), (r[2] or "")[:200]) for r in rows])
lts = one("""with v as (select lib, max_by(tooling, tooling) t from tasty_files group by lib)
             select count(*) filter (where t like 'Scala 3.3.%') * 100.0 / count(*) from v""")
exp = one("select count(distinct lib) from tasty_files where experimental > 0")
w(f"{lts:.0f}% of libs are published with the 3.3 LTS. {exp} libs contain TASTy with a non-zero experimental version (published with a nightly or RC compiler); their consumers need the same or a newer compiler.")
w()
w("**Scala 3 libs that depend on Scala 2.13 artifacts** (`for3Use2_13`): the classpath of these `_3` jars includes `_2.13` jars.")
w()
n213 = one("select count(distinct lib) from lib_deps where dep like '%\\_2.13:%' escape '\\'")
rows = q("""select regexp_replace(dep, ':[^:]+$', '') m, count(distinct lib) libs from lib_deps
            where dep like '%\\_2.13:%' escape '\\' group by 1 order by 2 desc limit 15""")
w(f"{n213:,} libs; the most common `_2.13` dependencies:")
w()
table(["`_2.13` module", "Libs"], [(f"`{r[0]}`", r[1]) for r in rows])

# ---------------------------------------------------------------------------------------------
w("## 2. Language feature adoption")
w()
w("How many libs use each feature, and how often. Definition features come from `defs` (kinds, flags and the types in signatures), "
  "expression features from tree-node counts in `hist` and from references to marker APIs in `refs`. One example each.")
w()
db.execute("""
create temp table feature_sites as
  select 'definition kind: ' || kind as feature, lib, full_name as example, file || ':' || line as site from defs
   where kind not in ('def', 'val', 'var', 'lazy-val', 'class', 'trait', 'object', 'module-val', 'accessor', 'type-alias', 'abstract-type')
  union all
  select 'flag: ' || f, lib, full_name, file || ':' || line from (select *, unnest(string_split(flags, ',')) f from defs)
   where f in ('exported', 'infix', 'open', 'erased', 'transparent') and flags not like '%synthetic%'
  union all
  select 'signature: ' || f, lib, full_name, file || ':' || line from (select *, unnest(string_split(features, ',')) f from defs)
   where f <> '' and flags not like '%synthetic%' and not (f = 'self-type' and kind = 'object')
  union all
  select 'derives clause', lib, full_name, file || ':' || line from defs where name like 'derived$%'
""")
feat_rows = q("""
select feature, count(distinct lib) libs, count(*) sites, arg_min(example, abs(length(example) - 35)), arg_min(lib, abs(length(example) - 35)), arg_min(site, abs(length(example) - 35))
from feature_sites group by feature order by libs desc""")
total = n_libs
table(["Feature", "Libs", "% libs", "Definitions", "Example"],
      [(r[0], fmt(r[1]), f"{100 * r[1] / total:.0f}%", fmt(r[2]), f"`{r[3]}` ({short(r[4])})") for r in feat_rows])

w("**Expression-level features** (tree nodes in TASTy, and references to the APIs that mark them):")
w()
node_features = {
    "Quote (macro implementation)": "key in ('Quote', 'QuotePattern')",
    "Splice": "key in ('Splice', 'SplicePattern')",
    "Inlined (a transparent inline or macro expansion kept in TASTy)": "key = 'Inlined'",
    "inline match": "key = 'InlineMatch'",
    "inline if": "key = 'InlineIf'",
    "export clause": "key = 'Export'",
    "while loop": "key = 'WhileDo'",
    "try": "key = 'Try'",
    "return": "key = 'Return'",
    "non-local return (from a lambda)": "key = 'Return:nonlocal'",
    "assignment": "key = 'Assign'",
}
rows = []
for name, cond in node_features.items():
    r = db.execute(f"select count(distinct lib), coalesce(sum(try_cast(count as bigint)), 0) from hist where {cond}").fetchone()
    rows.append((name, r[0], f"{100 * r[0] / total:.0f}%", fmt(int(r[1]))))
api_features = {
    "`scala.util.boundary`": "target like 'scala.util.boundary%'",
    "`scala.compiletime.summonInline`": "target = 'scala.compiletime.package$package$.summonInline'",
    "`scala.compiletime.erasedValue`": "target = 'scala.compiletime.package$package$.erasedValue'",
    "`scala.compiletime.constValue`": "target like 'scala.compiletime.package$package$.constValue%'",
    "`scala.compiletime.error`": "target = 'scala.compiletime.package$package$.error'",
    "`scala.deriving.Mirror`": "target like 'scala.deriving.Mirror%'",
    "`scala.quoted.Quotes` (macros)": "target like 'scala.quoted.Quotes%'",
    "structural types via `reflectiveSelectable`": "target like 'scala.reflect.Selectable$.reflectiveSelectable%'",
    "`scala.Dynamic`": "target = 'scala.Dynamic'",
    "`scala.util.NotGiven`": "target like 'scala.util.NotGiven%'",
    "`scala.CanEqual` (multiversal equality)": "target like 'scala.CanEqual%'",
    "`scala.annotation.experimental` APIs used": "target_annots like '%experimental%' and not self_ref",
    "`TypeTest`": "target like 'scala.reflect.TypeTest%'",
    "Scala 2 macro API (`scala.reflect.macros`)": "target like 'scala.reflect.macros%'",
}
for name, cond in api_features.items():
    r = db.execute(f"select count(distinct lib), coalesce(sum(count), 0) from refs where {cond}").fetchone()
    rows.append((name, r[0], f"{100 * r[0] / total:.0f}%", fmt(int(r[1]))))
table(["Feature", "Libs", "% libs", "Occurrences"], sorted(rows, key=lambda r: -r[1]))

w("**Language imports** (`scala.language.*`):")
w()
rows = q("""select prefix || '.' || selector, count(distinct lib) libs, sum(files) files from imports
            where prefix like 'scala.language%' group by 1 order by libs desc limit 25""")
table(["Import", "Libs", "Files"], [(f"`{r[0]}`", r[1], fmt(r[2])) for r in rows])

w("**`given`/`using` against Scala 2 `implicit`** (definitions per lib, excluding synthetic): how far migration has got.")
w()
rows = q("""
with c as (select lib,
  count(*) filter (where kind in ('given-def', 'given-val') or features like '%given-class%') as given_,
  count(*) filter (where kind in ('implicit-def', 'implicit-val', 'implicit-conversion-def')) as implicit_,
  count(*) filter (where features like '%using-clause%') as using_,
  count(*) filter (where features like '%implicit-clause%') as implicit_clause
  from defs where flags not like '%synthetic%' group by lib)
select case when given_ + using_ > 0 and implicit_ + implicit_clause = 0 then 'only given/using'
            when given_ + using_ = 0 and implicit_ + implicit_clause > 0 then 'only implicit'
            when given_ + using_ > 0 then 'both' else 'neither' end as style, count(*) libs
from c group by 1 order by 2 desc""")
table(["Style", "Libs"], rows)

# ---------------------------------------------------------------------------------------------
w("## 3. Library usage index")
w()
w("References are counted per referencing lib, so `Libs` is how many published jars use a symbol, and `Uses` counts reference sites. "
  "References from a module to itself, from compiler-generated code (case class and enum boilerplate) and to `Object`'s constructor (every class's parent call) are left out. "
  "An implicit conversion is counted both as a `call` and, in section 5, as a conversion; a `value` reference can also be a type name used as an identifier.")
w()


def usage(title, cond, n=30):
    w(f"**{title}**")
    w()
    rows = q(f"""select replace(target, 'scala.$:$$', 'scala.<:<$') || sig, kind, count(distinct lib) libs, sum(count) uses from refs
                 where not self_ref and kind in ('call', 'value', 'new', 'inlined') and roles not like '%synthetic%'
                 and target not in ('java.lang.Object', 'java.lang.Object.<init>') and {cond}
                 group by target, sig, kind order by libs desc, uses desc limit {n}""")
    table(["Symbol", "Kind", "Libs", "Uses"], [(f"`{r[0]}`", r[1], fmt(r[2]), fmt(r[3])) for r in rows])


usage("Most used standard library members", "target_module in ('org.scala-lang:scala-library', 'org.scala-lang:scala3-library_3')")
usage("Most used JDK members", "target_module = 'JDK'")
usage("Most used members of other libraries", "target_module not in ('org.scala-lang:scala-library', 'org.scala-lang:scala3-library_3', 'JDK', '?', 'scala (built-in)')", 40)

w("**Most depended-on modules, at symbol level** (libs that reference at least one symbol of the module, excluding the module itself):")
w()
rows = q("""
with u as (select target_module, lib, target, sum(count) n from refs where not self_ref and roles not like '%synthetic%' and target_module not in ('?', 'JDK', 'scala (built-in)') group by all),
     t as (select target_module, target, count(distinct lib) libs, sum(n) n from u group by target_module, target),
     top as (select *, row_number() over (partition by target_module order by libs desc, n desc) rk from t)
select u.target_module, count(distinct u.lib) libs, count(distinct u.target) symbols_used,
       (select string_agg(split_part(t.target, '.', -1), ', ') from top t where t.target_module = u.target_module and rk <= 5) top
from u group by u.target_module order by libs desc limit 40""")
table(["Module", "Libs using it", "Distinct symbols used", "Most used"], [(f"`{r[0]}`", fmt(r[1]), fmt(r[2]), r[3]) for r in rows])

w("**Deprecated APIs still in use** (target annotated `@deprecated`, referenced from another module):")
w()
rows = q("""select target || sig, target_module, count(distinct lib) libs, sum(count) uses, any_value(lib), any_value(sample) from refs
            where target_annots like '%deprecated%' and not self_ref and roles not like '%synthetic%' group by target, sig, target_module order by libs desc limit 40""")
table(["Symbol", "Module", "Libs", "Uses", "Example"], [(f"`{r[0]}`", f"`{r[1]}`", r[2], fmt(r[3]), f"{short(r[4])} {site(r[4], r[5])}") for r in rows])

w("**Compiler internals used outside the compiler** (references to `dotty.tools.*`): these break across compiler versions.")
w()
rows = q("""select lib, count(distinct target) symbols, sum(count) uses, string_agg(distinct split_part(target, '.', 3), ', ') pkgs from refs
            where target like 'dotty.tools.%' and lib not like 'org.scala-lang:%' group by lib order by uses desc limit 30""")
table(["Lib", "Symbols", "Uses", "Packages"], [(short(r[0]), r[1], fmt(r[2]), r[3]) for r in rows])

# ---------------------------------------------------------------------------------------------
w("## 4. Binary-compatibility hazards")
w()
w("**Inline methods are ABI.** A call to an `inline` method from another module is expanded into the caller, so the callee's body, "
  "and everything it references, is frozen into the caller's bytecode. These are the modules whose inline methods are expanded elsewhere:")
w()
rows = q("""select target_module, count(distinct target) inline_methods, count(distinct lib) libs, sum(count) sites,
                   arg_max(split_part(target, '.', -2) || '.' || split_part(target, '.', -1), count) most_used
            from refs where target_flags like '%inline%' and not self_ref and kind in ('call', 'value', 'inlined')
            and target_module not in ('?', 'scala (built-in)') group by 1 order by libs desc limit 30""")
table(["Module", "Inline methods used", "Libs", "Sites", "Most used"], [(f"`{r[0]}`", r[1], fmt(r[2]), fmt(r[3]), f"`{r[4]}`") for r in rows])

n = one("select coalesce(sum(try_cast(count as bigint)), 0) from hist where key = 'findings-total:inline-reaches-nonpublic'")
nl = one("select count(distinct lib) from hist where key = 'findings-total:inline-reaches-nonpublic'")
w(f"**Public inline methods that reach non-public members** ({fmt(int(n))} sites in {nl} libs): the private member, or the `inline$` accessor the compiler generates for it, "
  "becomes part of the binary API, so making it truly private or changing its signature breaks callers compiled against an older version.")
w()
rows = q("""select lib, count(*) sites, arg_min(owner, site), arg_min(detail, site), arg_min(site, site) from findings
            where kind = 'inline-reaches-nonpublic' group by lib order by sites desc limit 20""")
table(["Lib", "Sites (capped)", "Inline method", "Reaches", "Site"], [(short(r[0]), r[1], f"`{r[2]}`", f"`{r[3]}`", site(r[0], r[4])) for r in rows])

w("**Constants folded across modules.** A reference to a `final val` with a literal type is replaced by its value at compile time, "
  "so a new release of the defining module doesn't change callers until they are recompiled. Constants from other non-stdlib modules:")
w()
rows = q("""select target, target_module, count(distinct lib) libs, sum(count) uses, any_value(lib), any_value(sample) from refs
            where roles like '%const%' and not self_ref and target_module not in ('org.scala-lang:scala-library', 'org.scala-lang:scala3-library_3', 'JDK', 'scala (built-in)')
            group by all order by libs desc, uses desc limit 30""")
table(["Constant", "Module", "Libs", "Uses", "Example"], [(f"`{r[0]}`", f"`{r[1]}`", r[2], fmt(r[3]), f"{short(r[4])} {site(r[4], r[5])}") for r in rows])

w("**Inferred types in public API.** A public `def`/`val` without a type annotation has whatever type the compiler infers from its body; "
  "an innocent edit to the body changes the signature. Counted over non-synthetic, non-override public and protected members:")
w()
rows = q("""select tpe_kind, count(*) defs, count(distinct lib) libs, arg_min(full_name, length(full_name)), arg_min(lib, length(full_name)),
                   arg_min(file || ':' || line, length(full_name))
            from defs where tpt_inferred = '1' and visibility in ('public', 'protected') and flags not like '%synthetic%'
            and flags not like '%override%' and kind in ('def', 'val', 'lazy-val', 'var', 'given-val', 'given-def', 'implicit-def', 'implicit-val', 'extension')
            group by tpe_kind order by defs desc""")
table(["Inferred type", "Definitions", "Libs", "Example"], [(r[0], fmt(r[1]), fmt(r[2]), f"`{r[3]}` {site(r[4], r[5])}") for r in rows])
w("`union`, `intersection` and the `top:` rows are the suspicious ones: usually an accidental least upper bound of the branches of the body. "
  "`literal` rows are mostly intended constants (`final val Max = 10`), which are inlined into callers (see above); `singleton` ones change when the body changes. "
  "Inferred types of implicits/givens also affect implicit resolution.")
w()

# ---------------------------------------------------------------------------------------------
w("## 5. Hazard patterns")
w()
hazards = [
    ("nonlocal-return", "**Non-local `return` from a lambda.** Deprecated since 3.2 (implemented with exceptions; `boundary`/`break` replaces it). "
                        "This is the population a removal would break."),
    ("forward-reference", "**A strict `val` read before its initialisation** in the same template (it reads `null`/`0`). "
                          "Only direct reads in the initialiser are found, not reads through methods."),
    ("disjoint-equality", "**`==` between values that can never be equal**: one side's class is final (or an object) and isn't a subtype of the other's. "
                          "The compiler rejects this for primitives and `String`, but not for user classes."),
    ("generic-type-pattern", "**Type patterns with type arguments the runtime can't check** (a heuristic superset of the compiler's unchecked warning; `@unchecked` ones excluded)."),
    ("generic-isInstanceOf", "**`isInstanceOf` with type arguments** (erased at runtime)."),
]
# Refinements of the harvester's detectors, applied to the findings rows (which are capped at 300 per lib and kind).
FILTERS = {
    # `null`; boxed against primitive Boolean (unboxed before comparing); `sizeIs == n`, which calls SizeCompareOps.==, not Any.==
    "disjoint-equality": "detail not like '%scala.Null%' and not (detail like '%java.lang.Boolean%' and detail like '%scala.Boolean%') and detail not like '%SizeCompareOps%'",
    "generic-isInstanceOf": "detail not like '%@scala.unchecked%'",
    "generic-type-pattern": "detail not like '%@scala.unchecked%' and detail not like '\\_*%' escape '\\'",
}
for kind, text in hazards:
    cond = FILTERS.get(kind, "true")
    tot, libs_ = db.execute(f"select count(*), count(distinct lib) from findings where kind = '{kind}' and {cond}").fetchone()
    capped = one(f"select count(*) from hist where key = 'findings-total:{kind}' and try_cast(count as bigint) > 300")
    w(f"{text} **{fmt(tot)} sites in {libs_} libs**" + (f" (counting at most 300 per lib; {capped} libs have more)" if capped else "") + ".")
    w()
    rows = q(f"""select lib, count(*) n, arg_min(detail, site), arg_min(owner, site), min(site) from findings
                 where kind = '{kind}' and {cond} group by lib order by n desc limit 12""")
    table(["Lib", "Sites", "Example", "In", "Site"], [(short(r[0]), fmt(r[1]), f"`{(r[2] or '')[:120]}`", f"`{r[3]}`", site(r[0], r[4])) for r in rows])

n_nothing = int(one("select coalesce(sum(try_cast(count as bigint)), 0) from hist where key = 'findings-total:inferred-nothing'"))
top_nothing = q("select detail, count(*) from findings where kind = 'inferred-nothing' group by 1 order by 2 desc limit 6")
w(f"`Nothing` is inferred as a type argument at {fmt(n_nothing)} sites; almost all are benign covariant uses "
  f"({', '.join(f'`{r[0]}`' for r in top_nothing)}), so the `findings` rows of kind `inferred-nothing` are only a starting point.")
w()

w("**Cycles between objects' initialisers.** Object `A`'s initialiser touches `B` and `B`'s touches `A`: whichever is initialised second sees the other half-built, "
  "and two threads initialising them concurrently can deadlock on the class-init locks.")
w()
rows = q("""select a.lib, a.module, a.target, min(a.site), min(b.site) from module_init a join module_init b
            on a.lib = b.lib and a.target = b.module and b.target = a.module and a.module < a.target group by all order by a.lib limit 40""")
n_cycles = one("""select count(*) from (select distinct a.lib, a.module, a.target from module_init a join module_init b
                  on a.lib = b.lib and a.target = b.module and b.target = a.module and a.module < a.target)""")
w(f"{n_cycles} two-object cycles (references to constants, which don't trigger initialisation, are included; check before acting):")
w()
table(["Lib", "Object A", "Object B", "A → B", "B → A"], [(short(r[0]), f"`{r[1]}`", f"`{r[2]}`", site(r[0], r[3]), site(r[0], r[4])) for r in rows])

w("**Blocking, locking and reflection** (references from libs; each is legitimate somewhere, the counts say how widespread):")
w()
apis = {
    "`Await.result` / `Await.ready`": "target in ('scala.concurrent.Await$.result', 'scala.concurrent.Await$.ready')",
    "`Thread.sleep`": "target = 'java.lang.Thread$.sleep'",
    "`synchronized`": "target like '%.synchronized'",
    "`@volatile` / `AtomicReference`": "target like 'java.util.concurrent.atomic.%'",
    "`Class.forName`": "target = 'java.lang.Class$.forName'",
    "`setAccessible`": "target like '%.setAccessible'",
    "`sun.misc.Unsafe`": "target like 'sun.misc.Unsafe%'",
    "`System.exit`": "target = 'java.lang.System$.exit'",
    "`eq`/`ne` (reference equality, mostly null checks)": "target in ('java.lang.Object.eq', 'java.lang.Object.ne', 'scala.AnyRef.eq', 'scala.AnyRef.ne')",
    "`Option.get`": "target = 'scala.Option.get'",
    "`.head` on collections": "target like 'scala.collection.%.head' and sig = '()'",
    "`asInstanceOf`": "target = 'scala.Any.asInstanceOf'",
    "`scala.util.DynamicVariable`": "target like 'scala.util.DynamicVariable%'",
}
rows = []
for name, cond in apis.items():
    r = db.execute(f"select count(distinct lib), coalesce(sum(count), 0) from refs where {cond}").fetchone()
    rows.append((name, r[0], f"{100 * r[0] / total:.0f}%", fmt(int(r[1]))))
table(["API", "Libs", "% libs", "Uses"], sorted(rows, key=lambda r: -r[1]))

w("**Implicit conversions applied by the compiler**, the evidence for `into` and for restricting conversions. Most applied conversions:")
w()
rows = q("""select target || sig, target_module, count(distinct lib) libs, sum(count) uses from refs r where kind = 'conversion'
            and not exists (select 1 from refs u where u.lib = r.lib and u.target = r.target and u.sig = r.sig and u.roles like '%using%')
            group by all order by libs desc, uses desc limit 30""")
table(["Conversion", "Module", "Libs", "Uses"], [(f"`{r[0]}`", f"`{r[1]}`", fmt(r[2]), fmt(r[3])) for r in rows])
n_conv_defs = one("select count(distinct lib) from defs where kind = 'implicit-conversion-def'")
n_conv_given = one("select count(distinct lib) from refs where target = 'scala.Conversion' and kind = 'type' and not self_ref")
w(f"Libs that define implicit conversions: {n_conv_defs} with Scala 2 `implicit def`, "
  f"{n_conv_given} reference `scala.Conversion` (most to define a `given Conversion`).")
w()

w("**`var` fields in case classes** (equality and hashing of a mutable value):")
w()
rows = q("""select d.lib, count(*) n, min(d.full_name), min(d.file || ':' || d.line) from defs d
            join defs c on c.lib = d.lib and c.kind = 'case-class' and d.full_name = c.full_name || '.' || d.name
            where d.kind = 'var' and d.flags like '%param-accessor%' group by d.lib order by n desc limit 15""")
n_vars = one("select count(*) from defs d join defs c on c.lib = d.lib and c.kind = 'case-class' and d.full_name = c.full_name || '.' || d.name where d.kind = 'var' and d.flags like '%param-accessor%'")
w(f"{n_vars} fields:")
w()
table(["Lib", "Fields", "Example", "Site"], [(short(r[0]), r[1], f"`{r[2]}`", site(r[0], r[3])) for r in rows])

# ---------------------------------------------------------------------------------------------
w("## 6. Tooling gaps")
w()
w("Jars whose TASTy doesn't load as a whole with the 3.10 TASTy Inspector and their dependencies' published classpath, and the files that fail on their own. "
  "Most are references to compile-time-only dependencies missing from the published POM; the rest are leads for TASTy reader bugs.")
w()
rows = q("""select f.lib, count(*) n, l.n_tasty, string_agg(f.file, ', ' order by f.file) from failures f join libs l using (lib)
            group by f.lib, l.n_tasty order by n desc limit 25""")
w(f"{one('select count(distinct lib) from failures')} jars with at least one file that fails alone; the worst:")
w()
table(["Lib", "Files failing", "Of", "Files"], [(short(r[0]), r[1], r[2], (r[3] or "")[:160]) for r in rows])
rows = q("select lib, status from libs where status <> 'OK' order by lib")
if rows:
    w("Jars the harvester didn't finish: " + ", ".join(f"{short(r[0])} ({r[1]})" for r in rows))
    w()

w("## Appendix: the block-literal sweep as a query")
w()
w("The [block-literal sweep](../2026-10-scala3-block-val-literals/) is one query here:")
w()
w("```sql")
w("select lib, full_name, file, line from defs where tpt_inferred = '1' and tpe_kind = 'literal' and rhs_kind = 'Block'")
w("```")
w()
rows = q("select lib, full_name, file || ':' || line from defs where tpt_inferred = '1' and tpe_kind = 'literal' and rhs_kind = 'Block' order by lib, full_name")
w(f"{len(rows)} rows" + (": " + ", ".join(f"`{r[1]}` ({short(r[0])})" for r in rows[:20]) if rows else "") + ("…" if len(rows) > 20 else "") + ".")
w()

# ---------------------------------------------------------------------------------------------
# Highlights, inserted after the introduction.
def pct(n):
    return f"{100 * n / total:.0f}%"


def libs_with(sql):
    return one(f"select count(distinct lib) from ({sql})")


hl = []
given_only, implicit_only = (dict(q("""
with c as (select lib,
  count(*) filter (where kind in ('given-def', 'given-val') or features like '%given-class%' or features like '%using-clause%') g,
  count(*) filter (where kind in ('implicit-def', 'implicit-val', 'implicit-conversion-def') or features like '%implicit-clause%') i
  from defs where flags not like '%synthetic%' group by lib)
select 'g', count(*) filter (where g > 0 and i = 0) from c union all select 'i', count(*) filter (where i > 0 and g = 0) from c""")).get(k) for k in "gi")
ext = libs_with("select lib from defs where kind = 'extension'")
macros = libs_with("select lib from defs where kind = 'macro'")
opaque = libs_with("select lib from defs where kind = 'opaque-type'")
enums = libs_with("select lib from defs where kind = 'enum'")
hl.append(f"**Scala 2 idioms still dominate published code.** {pct(implicit_only)} of modules define implicits only the Scala 2 way and {pct(given_only)} only with `given`/`using`. "
          f"Extension methods are in {pct(ext)} of modules, enums {pct(enums)}, macros {pct(macros)}, opaque types {pct(opaque)}; "
          "match types, named tuples, polymorphic and dependent function types are each in 1–2%. "
          f"{lts:.0f}% of modules are published with the 3.3 LTS compiler.")
fr_sites, fr_libs = db.execute("select count(*), count(distinct lib) from findings where kind = 'forward-reference'").fetchone()
nl_sites, nl_libs = db.execute("select count(*), count(distinct lib) from findings where kind = 'nonlocal-return'").fetchone()
hl.append(f"**Real initialisation bugs.** {fr_sites} reads of a `val` before its initialiser has run, in {fr_libs} modules. The two checked by hand are real bugs: "
          "zio-direct's `Messages` appends `parallelExplanation` before it is initialised (so the message contains `null`), and skuber uses an `implicit val` before it is initialised. "
          f"{n_cycles} pairs of objects have initialisers that reference each other, which can deadlock under concurrent class initialisation.")
hl.append(f"**Removing non-local `return` would break {nl_libs} modules** ({nl_sites} sites).")
inl = q("""select target_module, count(distinct lib) from refs where target_flags like '%inline%' and not self_ref and kind in ('call', 'value', 'inlined')
           and target_module not in ('?', 'scala (built-in)', 'org.scala-lang:scala-library', 'org.scala-lang:scala3-library_3') group by 1 order by 2 desc limit 3""")
hl.append("**Inline methods are a large, unaudited ABI surface.** The inline methods of " + ", ".join(f"`{m}` ({n} modules)" for m, n in inl) +
          f" are expanded into their callers. Public inline methods reach non-public members (or `inline$` accessors) in {nl} modules, so those members can't be changed without breaking callers.")
lub = one("""select count(*) from defs where tpt_inferred = '1' and visibility in ('public', 'protected') and flags not like '%synthetic%' and flags not like '%override%'
             and kind in ('def', 'val', 'lazy-val', 'var', 'given-val', 'given-def', 'implicit-def', 'implicit-val', 'extension') and tpe_kind in ('union', 'intersection', 'top:Any', 'top:Object', 'top:Matchable', 'top:Product')""")
hl.append(f"**{lub:,} public members have an inferred union, intersection or top type** (`Any`, `Object`, …), usually an accidental least upper bound that is now part of the API.")
hl.append(f"**Tooling gap.** {100 * n_fail / max(n_tasty, 1):.1f}% of `.tasty` files can't be loaded by the TASTy Inspector with the published classpath, concentrated in a few modules "
          "(akka-http-core and pekko-http-core lose more than half). Most are compile-time-only dependencies missing from POMs; the rest are leads for TASTy reader bugs.")
hl.append("**Cross-check.** The [block-literal sweep](../2026-10-scala3-block-val-literals/)'s 17 sites come back from a one-line query over this data (appendix).")
intro_end = out.index("## 1. Ecosystem census")
out[intro_end:intro_end] = ["## Highlights", ""] + [f"- {h}" for h in hl] + [""]

open(f"{X}/REPORT.md", "w").write("\n".join(out))
print(f"REPORT.md: {len(out)} lines")
