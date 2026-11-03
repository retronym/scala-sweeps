# Facet B: GitHub code search, Analyzer-specific hits

Queries (code search, text-match): `"scala.tools.nsc.typechecker.Analyzer"` (87 hits), `"with Analyzer" "scala.tools.nsc"` (113), `"extends Analyzer" "scala.tools.nsc"` (182), `"MacroAnnotationNamers"` (12), `"override lazy val analyzer"` (133), `"InteractiveAnalyzer"` (42), `"new { val global" "with Analyzer"` (23), `filename:scalac-plugin.xml` (614 file hits, 222 distinct plugin classnames, 264 repos). Most Analyzer hits are forks/mirrors of scala/scala itself, dotty `tests/disabled` partest copies, Spark `override lazy val analyzer` (Spark SQL, unrelated), or `AnalyzerPlugin` users (not the `Analyzer` class).

## Real instantiators / subclassers of `Analyzer` (verified from matched lines)

| Repo | File | Code | Verdict | Coordinate |
|---|---|---|---|---|
| com-lihaoyi/Ammonite | amm/compiler/src/main/scala-2.13/ammonite/compiler/CompilerCompatibility.scala; scala-2.13.12+/MakeReporter.scala | `def analyzer(g: Global, cl: ClassLoader): Analyzer { val global: g.type }`, `new { val global: g.type = g } with Analyzer {...}`, `new { ... } with Analyzer with MacroAnnotationNamers`; also mixes `InteractiveAnalyzer` | YES, instantiates | com.lihaoyi:ammonite-compiler_2.13.18:3.0.9 |
| tek/splain | core/src/main/scala-2.13.7+/latest/splain/SplainAnalyzer.scala (+ SplainPlugin.scala, SplainAnalyzerShim.scala) | `class SplainAnalyzer(val global: Global, ...) extends typechecker.Analyzer with ...`; plugin installs it by reflectively setting `Global.analyzer` and uses `MacroAnnotationNamers` | YES, extends (class, constructor-arg global) | io.tryp:splain_2.13.18:1.2.0 |
| scalameta/metals | mtags/src/main/scala-2/scala/meta/internal/pc/MetalsGlobal.scala:86,138 | `class MetalsInteractiveAnalyzer(val global: compiler.type) extends InteractiveAnalyzer`; `override lazy val analyzer = new MetalsInteractiveAnalyzer(compiler)` | YES, indirect (InteractiveAnalyzer extends Analyzer) | org.scalameta:mtags_2.13.18:1.6.9 |
| pweisenburger/dslparadise | plugin/src/main/scala/dslparadise/Plugin.scala | `val analyzer = new { val global = Plugin.this.global } with Analyzer` | YES, but old (2.11/2.12 era); not on Central found | - |
| joprice/type-formatter | plugin/src/main/scala/TypeFormatterPlugin.scala | `} with Analyzer with Formatter {` | YES, old plugin; not found on Central | - |
| miniboxing/miniboxing-plugin | components/plugin/cross-compilation/2.1x/.../ScalacCrossCompilingLayer.scala | `class TweakedAnalyzer extends scala.tools.nsc.typechecker.Analyzer` | YES, but 2.10-2.12 only | - |
| csferi27/scala_recur | compile_poc/.../CustomAnalyzer.scala | `trait CustomAnalyzer extends Analyzer` | YES, PoC, unpublished | - |
| cric96/ScaFi-Blocks-Web | online-compiler/.../GlobalInitCompat.scala | `} with Analyzer {` in compat Global init | YES, app, unpublished | - |
| foursquare/scala-gazelle | scala/testdata/parser_integration/scalac/Global.scala | `new { val global: Global.this.type = Global.this } with Analyzer with MacroAnnotationNamers` | YES, testdata only (copy of Global) | - |
| JetBrains/intellij-scala | scala/scala-impl/testdata/**/CustomGlobal.scala, typeInference/**/*.scala | `lazy val analyzer = new {...} with Analyzer` | testdata, not published | - |
| lihaoyi/scala-js-fiddle, scalawarrior/scalawarrior, DePauwREU2013/sjs-server | Compiler.scala etc. | `} with Analyzer{` with InteractiveAnalyzer | YES, but 2.10/2.11 era apps | - |
| adriaanm/scala-improving | src/main/scala-2.10/scalac/TraceGlobal.scala | `trait TraceAnalyzer extends Analyzer` | 2.10 only | - |
| xeno-by/old-paradise, old-scalahost | HijackAnalyzer.scala | ParadiseAnalyzer / InteractiveAnalyzer hijack | 2.10/2.11 only | - |

Also in scope but not subclassing/instantiating: `AnalyzerPlugin` / `MacroPlugin` users (scalac-profiling `ProfilingAnalyzerPlugin`, scala-native `PrepNativeInterop`, optimus-cirrus, opentracing-scala `ImplicitsTracingAnalyzer`, lrytz/efftp, STLC_2Cap, scalamacros/paradise Plugin `with AnalyzerPlugins`). They reference `global.analyzer.addAnalyzerPlugin`, so only affected if `analyzer`'s type changes. scalameta/metals, scalafix-reflect, mdoc, zinc, twirl etc. were added to candidates-B.txt as embedders of `Global`, unverified at bytecode level.

## Caveats
- GitHub code search returns only fragments; "extends Analyzer" hits with empty matched lines (e.g. AVSystem analyzer rules, Duhemm/parsermacros) are `Analyzer` in unrelated senses (own `Analyzer` classes) and were discarded.
- Plugin-class query (`"extends Plugin" "scala.tools.nsc.plugins"`) capped at 300 of 383 results (3 pages); plugin set was instead derived from `scalac-plugin.xml` classnames mapped to Maven artifacts through Maven Central class search (`fc:`), keeping the latest `_2.13`/`_2.13.N` artifact per module. Class search returns at most 200 docs per class, so latest versions of very popular classes might be missed.
