# Facet C notes: community build / curated lists / Scaladex

Output: `candidates-C.txt`, 71 coordinates, each verified with `coursier fetch --intransitive`. Newest version in Maven Central's `maven-metadata.xml` for the newest `_2.13[.N]` artifact (so some are stale or milestones, e.g. `mill-*`, `chisel3-plugin_2.13.14`).

## Sources
- `scala/community-build` (HEAD 2026-10-31): 252 `proj/*.conf`. These are dbuild project definitions with no dependency lists, so only name-matching works. Plugin projects found: better-monadic-for, better-tostring, scapegoat, scoverage, twotails, scala-typed-holes, scala-sculpt, fast-string-interpolator, expression-evaluator, sourcepos, scalafix-rules, macrolizer, moduload, unused-code. `proj/metals.conf` is the only one mentioning scala-compiler. `proj/twotails.conf` comments that the CB includes it "just to have a few more compiler plugins". `twotails`, `scala-sculpt`, `unused-code`, `macrolizer`, `moduload`, `fast-string-interpolator`, `sourcepos` have no `_2.13*` artifact I could resolve under the guessed group, so are missing.
- Scaladex API `https://index.scala-lang.org/api/search?q=...&target=JVM&scalaVersion=2.13` (~20 queries: compiler-plugin, scalac-plugin, ...). The `topic=` filter on the API and the web `search?topic=compiler-plugin` page do not paginate usefully (11 repos on the web page: silencer, better-monadic-for, wartremover, scaladoc plugin, scalaz-deriving, scala2ts, puree, ash, dsl.scala, ...). Artifact names ending `_2.13.N` (full cross-version, the strongest plugin signal) were mapped to groups via Maven Central search.
- Hand-written list of ~320 `group:artifact` guesses (plugins plus libraries known to use scala-compiler: ammonite, mdoc, twirl, zinc, scalafix, scalameta/metals, almond, spark-repl, scalate, ...), resolved against `repo1.maven.org` directory listings.
- docs.scala-lang.org/overviews/plugins: no list of plugins, nothing used. scala-lang.org/ecosystem: 404.

## Selection
Of 195 resolvable artifacts, kept a jar if it (a) has `scalac-plugin.xml` or a `scala.tools.nsc.plugins.Plugin` class (31 jars), (b) references `scala/tools/nsc` in any class file, or (c) the POM declares a `scala-compiler` dependency outside `<build>`. Last two kinds are "library uses compiler" and include noise where the dependency is incidental (scalatest, scala-xml, sbt `io`, circe-generic-extras, kebs, spark-core, quicklens). Filter with the `candidates` column if needed.

Dedupe: one artifact id per group, latest `_2.13.N` (all current ones are `_2.13.18`).

## Not found / gaps
- `org.scalamacros:paradise`, `org.spire-math:kind-projector`, `org.scala-lang.plugins:scala-continuations-plugin`: no 2.13 artifacts. Old `genjavadoc`, `linter`, `clippy` forks: not searched beyond the above.
- Not on Maven Central under guessed coordinates: scastie, bloop-frontend (2.12 only), scala-cli (mostly `_3`), gatling-compiler, `andyglow` scaladoc plugin, scala2ts, ash/akka-serialization-helper (not resolved), `scalafix-core`/`cli` pass (no nsc reference, pom has no compiler dep), `ammonite` umbrella jar (no direct reference), `zinc` umbrella, `metals_2.13`, `mima-core` (no direct nsc use).
- Scaladex search hit also `chisel`, `scala-debug-adapter`, `scalac-profiling`, `redacted`: included where resolved (`scala-debug-adapter_2.13` had no nsc ref).
- Several 2.13.18 jars are above what the Maven Central-published 2.13 line may officially support; version selection is just "newest".
