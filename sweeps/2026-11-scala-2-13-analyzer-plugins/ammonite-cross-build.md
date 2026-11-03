# Ammonite vs scala/scala#11306 (AbstractAnalyzer)

Tested against PR head `b2489658ba` ("Self-type the analyzer with a class, keeping trait Analyzer"), published locally as `2.13.99` (a release-shaped version so mill resolves `_2.13` artifacts; `2.13.19-SNAPSHOT-style` versions make mill use the full version as the binary suffix and nothing resolves). Ammonite fork branch: <https://github.com/retronym/Ammonite/tree/analyzer-cross-build> (commit `90bdc0a5`, based on `c8804698`).

## 1. What breaks

| Scenario | Result |
|---|---|
| Build `ammonite-compiler` source (`CompilerCompatibility.scala`) against the PR compiler | **Compile error**, 3 sites: `illegal inheritance; self-type Analyzer [with MacroAnnotationNamers] does not conform to Analyzer's selftype AbstractAnalyzer` (also reported against `MacroAnnotationNamers`'s self type, `MacroAnnotationNamers with AbstractAnalyzer`) |
| Released Ammonite 3.0.9 (`ammonite_2.13.18`) run with the PR's scala-compiler/reflect/library jars substituted | **Runtime failure at first compile, not a link error**: `ClassCastException: ammonite.compiler.CompilerCompatibility$$anon$2 cannot be cast to scala.tools.nsc.typechecker.AbstractAnalyzer` at `Contexts.$init$(Contexts.scala:61)`, called from `CompilerCompatibility.analyzer`. |

The second is the sharper point for the PR: "Analyzer stays a trait so existing binaries still link" is true, but any existing binary that instantiates `new {..} with Analyzer` still dies when the mixin initializer casts `this` to the new self type. Binaries that only *reference* the analyzer (sbt bridge, `Global.analyzer`) are fine; instantiators are broken both ways. Worth saying in the PR description.

`InteractiveAnalyzer` (Ammonite's Pressy: `new { val global: g.type = g } with InteractiveAnalyzer {}`) compiles unchanged, since the PR makes it `extends AbstractAnalyzer`. Same for `ScaladocAnalyzer`. A *binary* built against old `InteractiveAnalyzer` should be re-checked (not tested here).

## 2. Cross-buildable source shape

`AbstractAnalyzer` does not exist on 2.13.18, so no single expression `new {..} with <X>` works on both. Options, best first:

1. **Don't instantiate the analyzer (what I did).** Ammonite's override existed only to set `defaultMacroClassloader = global.findMacroClassLoader`, which is already the default (`MacroRuntimes.defaultMacroClassloader` caches `findMacroClassLoader()` per run), and Ammonite's `initGlobal` already overrides `findMacroClassLoader()` to its eval classloader. Deleting `CompilerCompatibility.analyzer` and the `override lazy val analyzer` makes the source identical for 2.13.3 to 2.13.19, source- and binary-compatible, and lets `Global` pick `MacroAnnotationNamers` itself. Only difference: the loader is cached per run rather than re-read each call (it is a fixed value in Ammonite).
2. **Version-specific source dir** (`scala-2.13.19+/`, Ammonite already splits by patch level like this) with `with AbstractAnalyzer`. Verified that `new { val global: g.type = g } with AbstractAnalyzer with MacroAnnotationNamers` typechecks against the PR compiler and conforms to `Analyzer { val global: g.type }`. This is the fallback for plugin authors who genuinely need to subclass the analyzer (override analyzer members, mix in their own traits).
3. Reflection / type-alias shims: not recommended. `new {..} with X` needs `X` statically; a macro or reflective `Class.forName("...AbstractAnalyzer")` cannot express the early-initializer + mixin shape.

For plugin authors the least bad is: avoid subclassing/instantiating `Analyzer` (use `AnalyzerPlugin`/`MacroPlugin` hooks, or override `findMacroClassLoader` on `Global`), otherwise a per-version source directory. There is no source shape that spans 2.13.18 and the PR for a direct instantiation.

## 3. Tests

`mill amm.repl[<v>].test` (REPL sessions, `AutocompleteTests` which drives Pressy/InteractiveAnalyzer, `AdvancedTests`, macros and compiler paths) with the change:
- 2.13.18: all pass.
- 2.13.99 (PR compiler): all pass except `AdvancedTests.compilerPlugin`, which does `import $plugin.$ivy.`org.typelevel:::kind-projector``: the `:::` resolves `kind-projector_2.13.99`, which does not exist. Environment artifact, not PR fallout.
- `-Ymacro-annotations` is not exercised by a dedicated test; the `MacroAnnotationNamers` path was only checked by compiling the version-dir variant.
- Only 2.13.18 and the PR build were compiled; 2.13.3..2.13.17 not rebuilt.

## 4. Local build notes

`build.mill` needed local-only hacks (not committed; `build-mill-experiment.patch` equivalent): extra cross version from `$AMM_EXTRA_SCALA`, `takeWhile(_.isDigit)` when parsing the 2.13 patch number, and skipping the full-cross `acyclic` plugin for that version. PR compiler published with `sbt 'set Global / baseVersion := "2.13.99"' 'set Global / baseVersionSuffix := ""' publishLocal`.
