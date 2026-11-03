# Do Scala 2.13 compiler plugins instantiate or extend `Analyzer`?

Behind [scala/scala#11306 (comment)](https://github.com/scala/scala/pull/11306#issuecomment-6598956099). The PR makes `Analyzer` a trait with an `AbstractAnalyzer` class self type. Code that does `new { val global = g } with Analyzer` must switch to `AbstractAnalyzer`.

**Question.** Which published 2.13 compiler plugins would break (source or binary) if `Analyzer` were replaced by `AbstractAnalyzer` for instantiation?

**Answer.** _pending_

## Method

1. Build a candidate list of plugin coordinates from several independent facets (below). Each facet writes `candidates-<facet>.txt` (`group:artifact:version`).
2. Keep jars that contain `scalac-plugin.xml` or a subclass of `scala.tools.nsc.plugins.Plugin`.
3. Parse every class file; report classes that have `scala/tools/nsc/typechecker/Analyzer` (or its part traits) as super type, or reference it in the constant pool.
4. Controls: tiny plugins with known answers.

## Facets (status)

| Facet | Status | Candidates |
|---|---|---|
| A. Maven Central keyword search (`harvest.py`) | done | 548 `_2.13*` artifacts (name guesses, low confidence) |
| B. GitHub code search (`scalac-plugin.xml`, `typechecker.Analyzer`) | running | |
| C. Scala 2.13 community build projects | running | |
| D. deps.dev reverse dependents of `scala-compiler` (BigQuery) | needs access | |

## Log

- Scope broadened: any published 2.13 code that uses the compiler programmatically, not just plugins. Aim is spanning + representative, deduped to the latest 2.13.x per artifact.
- Facet A scanned (212 artifacts after dedupe, 51 are plugins). First real finding: **splain** `SplainAnalyzer extends Analyzer` (via `SplainAnalyzerShim`). Others only mention `Analyzer` (scalac-profiling, scapegoat, silencer: to be classified).
- Facets B (GitHub) and C (community build/Scaladex) running in subagents.
- Note on splain: its functionality has since been integrated into the 2.13 compiler (`-Vimplicits`, `-Vtype-diffs`), so the plugin may be obsolete or obfuscating on recent 2.13.x. Still, it is an independent real-world instance of a plugin extending `Analyzer`, which validates the scan. Its recent versions need checking for whether they still do so on the 2.13.x range of interest.
