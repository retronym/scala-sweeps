# TASTy harvest: a queryable fact base of published Scala 3 code

**Question.** Rather than one question, visit the published Scala 3 ecosystem once and record enough facts that later questions are queries, not new sweeps: which language features are used and how much, which library members are used by whom, and where code has known-dangerous shapes.

**Answer.** [REPORT.md](REPORT.md), generated from the fact base. The fact base itself (DuckDB, and Parquet per table) is rebuilt by the scripts below.

## Method

`harvester/Harvest.scala` reads a jar's TASTy with the TASTy Inspector (3.10.0) and writes one gzipped TSV per table. Nothing is recompiled. If the jar's TASTy doesn't load as a whole, it is inspected in chunks of 50 files, splitting failing chunks until single files are left (`failures`); rows from failed inspections are discarded.

`harvest.py` resolves each coordinate with coursier (offline first; online with backoff on HTTP 429; the latest release if the project's version doesn't resolve), runs the harvester with the jar's dependencies, minus their standard library, on the classpath, and records the TASTy header of every `.tasty` file. It skips jars already harvested, so it can be resumed. `load.py` builds `work/harvest.duckdb` and `work/parquet/`, and maps every referenced top-level class to the module that defines it (preferring the referencing module itself), from the class listings of every jar on any harvested classpath. `report.py` writes `REPORT.md`.

```
./setup.sh                                  # compiles the harvester; makes .venv with duckdb
./controls.sh | tee controls-result.txt     # controls/*.scala, compiled with Scala 3.7.3
JOBS=8 python3 harvest.py | tee work/harvest-log.txt
./refresh.sh                                # load.py + report.py; can run while harvest.py is running
```

The run reported here harvested 6,296 jars (6,188 modules; `REPORT.md` counts one version of each, the community build's where there are two) in about 85 minutes with 8 jobs; the database is 880 MB and the Parquet export 184 MB, neither checked in. After the run, `forward-reference` and object-cycle detection were changed to skip by-name arguments (`P.defer(later)` isn't evaluated during initialisation), and the 51 jars with either finding were harvested again (the last 51 lines of `harvest-log.txt`); the change can only remove findings, so the other jars' results stand.

The corpus is the block-literal sweep's: every published target of the open community build's projects ([`libs-ocb.txt`](../2026-10-scala3-block-val-literals/tasty-scan/libs-ocb.txt)) and the #25108 seed list. [`projects.tsv`](projects.tsv) gives each community build project's repository and published revision, for links to source.

## Tables

| Table | One row per | Columns |
|---|---|---|
| `libs` | harvested jar | `lib` (group:artifact:version), `module`, `coord`, `project`, `status`, `n_tasty` |
| `tasty_files` | `.tasty` file | `major`, `minor`, `experimental` (TASTy version), `tooling` (the compiler that wrote it) |
| `lib_deps` | dependency of a jar | `dep` (group:artifact:version) |
| `classes` | top-level class of any jar on a harvested classpath | `class`, `module` |
| `defs` | non-local definition (classes, objects, traits, type members, defs, vals; not parameters or local definitions) | `full_name`, `kind` (e.g. `given-def`, `extension`, `macro`, `opaque-type`, `match-type-def`, `implicit-conversion-def`), `sig`, `flags`, `visibility`, `tpt_inferred` (no type annotation), `tpe_kind` (shape of the declared type: `literal`, `union`, `product-with-serializable`, `top:Any`, …), `rhs_kind` (root tree of the body), `features` (language features in the signature: `using-clause`, `context-function-type`, `named-tuple`, …), `annotations`, `file`, `line` |
| `refs` | (referencing lib, target symbol, kind, roles), aggregated | `target`, `sig`, `top_level`, `target_module`, `self_ref`, `kind` (`call`, `value`, `module`, `new`, `type` for explicit type trees, `conversion` for implicit conversions the compiler inserted, `inlined` for kept inline expansions), `roles` (`using` for implicit arguments the compiler inserted, `const` for constants folded at the use site, `synthetic` for references from compiler-generated members), `target_flags`, `target_annots` (`deprecated`, `experimental`), `count`, `files`, `sample` |
| `imports` | (lib, import prefix, selector), aggregated | `count`, `files`, `sample` |
| `hist` | (lib, key) | counts of each tree node class (`Return`, `WhileDo`, `Quote`, `Inlined`, …), of hazards (`finding:*`, `findings-total:*`), and `Return:nonlocal` |
| `findings` | hazard site (at most 300 per lib and kind; `hist` has the full count) | `kind`, `site`, `owner`, `detail` |
| `module_init` | module referenced by another module's initialiser | `module`, `target`, `site` |
| `failures` | `.tasty` file that fails to load on its own | `file` |

The hazard kinds are `nonlocal-return`, `forward-reference` (a strict val read in its template before its initialiser has run; direct reads only, not through methods or by-name arguments), `disjoint-equality` (`==` where one side's class is final or an object and isn't a subtype of the other's), `generic-type-pattern` and `generic-isInstanceOf` (type tests whose type arguments may be unchecked: a heuristic superset of the compiler's warning), `inferred-nothing`, and `inline-reaches-nonpublic` (a public inline method's body references a non-public member or an `inline$` accessor). Hazards in compiler-generated members aren't reported.

**Controls** (`controls/`, expectations in `// expect:` comments; [`controls-result.txt`](controls-result.txt)) cover each hazard with positive and negative cases, implicit arguments (synthesised against explicit `using`), Scala 3 and Scala 2 implicit conversions, deprecated and constant references, and the feature and kind columns.

## Examples

```sql
-- the block-literal sweep
select lib, full_name, file, line from defs where tpt_inferred = '1' and tpe_kind = 'literal' and rhs_kind = 'Block';
-- who calls a method, and how often
select lib, sum(count) from refs where target = 'cats.effect.IO.unsafeRunSync' group by lib order by 2 desc;
-- which cats Show instances the compiler picks, across the ecosystem
select target, count(distinct lib) from refs where roles like '%using%' and target like 'cats.%Show%' group by 1 order by 2 desc;
```

## Limits

- TASTy only, so only Scala 3 artifacts, and only their main `_3` jars. A bytecode pass would add the Scala 2.13 ecosystem and what runs after inlining (non-transparent `inline` calls are pickled unexpanded, so inline bodies appear as references to the inline method, not as expansions).
- Syntax isn't in TASTy (indentation, `then`, `?` against `_`); a pass over sources jars would add it.
- References to local symbols aren't recorded, and references are aggregated per lib (`sample` keeps one site).
- Which given *would* be chosen under different resolution rules needs the typer, as in the #25108 probe; `refs` records the one that was chosen.
- `.tasty` files that fail to load on their own (`failures`) are left out.
- The hazard detectors over-report in known ways that `report.py` filters out of the `findings` rows: `disjoint-equality` counts comparisons with `null`, boxed against primitive `Boolean`, and calls of a user-defined `==` such as `SizeCompareOps.==`; `generic-type-pattern` and `generic-isInstanceOf` count `@unchecked` on a type argument and vararg patterns. `inferred-nothing` is mostly benign covariant uses (`Right.apply`, `.empty`).
