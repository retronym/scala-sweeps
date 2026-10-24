# What published Scala 3 code looks like, from its TASTy

One pass over the TASTy of **6,188 published `_3` modules** from 2,012 open community build projects and the #25108 seed corpus: 168,596 `.tasty` files, 4,855,227 non-local definitions and 30,241,889 references to non-local symbols. 4,255 `.tasty` files (2.5%) fail to load on their own and are left out. 108 modules were harvested in two versions (6,296 jars in all); the report counts each module once. Every number below is a query over the tables described in the [README](README.md); rerun or extend them with DuckDB.

Sites link to the source at the published revision where the project's repository is known. *Libs* counts modules (one version each).

## Highlights

- **Scala 2 idioms still dominate published code.** 45% of modules define implicits only the Scala 2 way and 13% only with `given`/`using`. Extension methods are in 14% of modules, enums 9%, macros 8%, opaque types 5%; match types, named tuples, polymorphic and dependent function types are each in 1–2%. 62% of modules are published with the 3.3 LTS compiler.
- **Real initialisation bugs.** 15 reads of a `val` before its initialiser has run, in 8 modules. The two checked by hand are real bugs: zio-direct's `Messages` appends `parallelExplanation` before it is initialised (so the message contains `null`), and skuber uses an `implicit val` before it is initialised. 41 pairs of objects have initialisers that reference each other, which can deadlock under concurrent class initialisation.
- **Removing non-local `return` would break 45 modules** (228 sites).
- **Inline methods are a large, unaudited ABI surface.** The inline methods of `dev.zio:zio-stacktracer_3` (443 modules), `dev.zio:zio_3` (291 modules), `dev.zio:izumi-reflect_3` (244 modules) are expanded into their callers. Public inline methods reach non-public members (or `inline$` accessors) in 403 modules, so those members can't be changed without breaking callers.
- **2,838 public members have an inferred union, intersection or top type** (`Any`, `Object`, …), usually an accidental least upper bound that is now part of the API.
- **Tooling gap.** 2.5% of `.tasty` files can't be loaded by the TASTy Inspector with the published classpath, concentrated in a few modules (akka-http-core and pekko-http-core lose more than half). Most are compile-time-only dependencies missing from POMs; the rest are leads for TASTy reader bugs.
- **Cross-check.** The [block-literal sweep](../2026-10-scala3-block-val-literals/)'s 17 sites come back from a one-line query over this data (appendix).

## 1. Ecosystem census

**Compiler that produced the published TASTy** (the newest compiler version in each jar's TASTy headers):

| Series | Libs | Pre-release compilers seen |
|---|---|---|
| 3.0 | 242 | Scala 3.0.2-RC1 |
| 3.1 | 414 | Scala 3.1.1-RC1, Scala 3.1.1-RC2 |
| 3.2 | 402 | Scala 3.2.0-RC1, Scala 3.2.2-RC1 |
| 3.3 | 3,694 | Scala 3.3.0-RC2, Scala 3.3.0-RC4, Scala 3.3.1-RC1-bin-20230420-e8ea8cf-NIGHTLY-git-e8ea8cf, Scala 3.3.1-bin-nonbootstrapped, Scala 3.3.4-bin-nonbootstrapped, Scala 3.3.6-bin-nonbootstrapped, Scala 3.3 |
| 3.4 | 140 | Scala 3.4.1-bin-nonbootstrapped |
| 3.5 | 42 |  |
| 3.6 | 133 |  |
| 3.7 | 308 | Scala 3.7.3-bin-nonbootstrapped, Scala 3.7.4-RC1, Scala 3.7.4-bin-nonbootstrapped |
| 3.8 | 588 |  |
| 3.9 | 4 | Scala 3.9.0-RC4, Scala 3.9.0-RC5 |
| 3.10 | 1 | Scala 3.10.0-RC1-bin-20260607-dec42ae-NIGHTLY-git-dec42ae |

62% of libs are published with the 3.3 LTS. 8 libs contain TASTy with a non-zero experimental version (published with a nightly or RC compiler); their consumers need the same or a newer compiler.

**Scala 3 libs that depend on Scala 2.13 artifacts** (`for3Use2_13`): the classpath of these `_3` jars includes `_2.13` jars.

675 libs; the most common `_2.13` dependencies:

| `_2.13` module | Libs |
|---|---|
| `org.portable-scala:portable-scala-reflect_2.13` | 311 |
| `org.scala-lang.modules:scala-collection-compat_2.13` | 115 |
| `org.scala-lang.modules:scala-xml_2.13` | 84 |
| `io.get-coursier:coursier-util_2.13` | 81 |
| `io.get-coursier:coursier-core_2.13` | 80 |
| `io.get-coursier:coursier-cache_2.13` | 80 |
| `com.github.plokhotnyuk.jsoniter-scala:jsoniter-scala-core_2.13` | 76 |
| `io.get-coursier:coursier_2.13` | 74 |
| `io.get-coursier:dependency_2.13` | 66 |
| `io.get-coursier:versions_2.13` | 64 |
| `io.get-coursier:coursier-jvm_2.13` | 62 |
| `io.get-coursier:coursier-env_2.13` | 62 |
| `io.get-coursier:coursier-archive-cache_2.13` | 60 |
| `org.scalameta:common_2.13` | 57 |
| `org.scalameta:trees_2.13` | 57 |

## 2. Language feature adoption

How many libs use each feature, and how often. Definition features come from `defs` (kinds, flags and the types in signatures), expression features from tree-node counts in `hist` and from references to marker APIs in `refs`. One example each.

| Feature | Libs | % libs | Definitions | Example |
|---|---|---|---|---|
| signature: type-params | 4,313 | 70% | 251,498 | `com.banno.vault.Vault$.deleteSecret` (vault4s 9.5.1) |
| signature: multiple-param-lists | 3,790 | 61% | 138,247 | `com.banno.vault.Vault$.deleteSecret` (vault4s 9.5.1) |
| definition kind: case-class | 3,361 | 54% | 80,442 | `mill.javalib.Assembly$.Rule$.Append` (mill-libs-javalib 1.1.7) |
| signature: implicit-clause | 3,038 | 49% | 108,206 | `com.banno.vault.Vault$.deleteSecret` (vault4s 9.5.1) |
| signature: default-args | 2,606 | 42% | 26,856 | `org.parboiled2.Parser.__matchString` (parboiled 2.5.1) |
| definition kind: implicit-val | 2,341 | 38% | 49,430 | `zio.json.CodecLowPriority3.duration` (zio-json 0.9.2) |
| signature: type-lambda | 1,770 | 29% | 28,159 | `lamp.data.BatchStream$.fromFunction` (lamp-data 0.0.116) |
| signature: by-name | 1,580 | 26% | 20,152 | `scalaz.effect.IoExceptionOr.valueOr` (scalaz-effect 7.3.9) |
| signature: using-clause | 1,535 | 25% | 51,367 | `proteus.client.ClientBackend.client` (proteus-grpc 0.6.0) |
| definition kind: implicit-conversion-def | 1,487 | 24% | 18,265 | `olon.common.BoxOrRaw$.rawToBoxOrRaw` (olon-common 6.0.0-RC1) |
| definition kind: implicit-def | 1,349 | 22% | 34,990 | `zio.json.CodecLowPriority2.iterable` (zio-json 0.9.2) |
| signature: self-type | 1,262 | 20% | 9,356 | `akka.http.ccompat.QuerySeqOptimized` (akka-http-core 10.5.3) |
| definition kind: given-val | 1,063 | 17% | 34,088 | `oxygen.zio.instances$.traceClassTag` (oxygen-zio 0.6.7) |
| signature: value-class | 952 | 15% | 5,689 | `sttp.tapir.tests.data.StringWrapper` (tapir-tests 1.13.28) |
| definition kind: extension | 869 | 14% | 33,411 | `oxygen.predef.zio$.convertCausesDie` (oxygen-zio 0.6.7) |
| signature: intersection-type | 801 | 13% | 12,191 | `decrel.scalacheck.gen.GenOps.expand` (decrel-scalacheck 0.2.0) |
| definition kind: given-def | 716 | 12% | 13,448 | `hearth.source.FileCompanion.derived` (hearth 0.4.1) |
| definition kind: inline-def | 612 | 10% | 11,062 | `rendition.Rendering$package$.indent` (rendition 0.0.4) |
| signature: literal-type | 604 | 10% | 19,021 | `zio.blocks.datastar.BuildInfo$.name` (zio-blocks-datastar 0.0.47) |
| definition kind: enum | 547 | 9% | 7,456 | `mill.javalib.publish.PublishingType` (mill-libs-javalib 1.1.7) |
| signature: union-type | 502 | 8% | 5,176 | `dotty.tools.dotc.ast.Trees$.Untyped` (scala3-compiler 3.3.6) |
| definition kind: macro | 498 | 8% | 4,358 | `wvlet.airframe.SourceCode$.generate` (airframe-di-macros 2026.2.2) |
| signature: interleaved-type-params | 436 | 7% | 5,750 | `oxygen.predef.zio$.convertCausesDie` (oxygen-zio 0.6.7) |
| signature: structural-refinement | 330 | 5% | 2,472 | `cps.monads.logic.CpsLogicMonad$.Aux` (dotty-cps-async-logic 1.3.4) |
| definition kind: opaque-type | 310 | 5% | 1,644 | `kyo.compat.CStream$package$.CStream` (kyo-compat-kyo 1.0.0-RC5) |
| flag: exported | 236 | 4% | 17,283 | `vecxt.all$.spearmansRankCorrelation` (vecxt 0.0.39) |
| signature: given-class | 216 | 3% | 1,702 | `uni.data.Big$.given_Fractional_Big$` (uni 0.19.3) |
| flag: transparent | 214 | 3% | 2,783 | `kyo.EnvCombinators$package$.provide` (kyo-combinators 1.0.0-RC5) |
| derives clause | 209 | 3% | 4,799 | `ascent.ast.IdMode$.derived$CanEqual` (ascent-core 0.2.0) |
| signature: context-function-type | 180 | 3% | 2,260 | `dotty.tools.dotc.ast.tpd$.sameStats` (scala3-compiler 3.3.6) |
| flag: infix | 125 | 2% | 7,393 | `org.scalatest.verbs.BehaveWord.like` (scalatest-core 3.2.20) |
| signature: generic-tuple | 95 | 2% | 1,067 | `usql.dao.SqlFielded$.recursiveTuple` (usql 0.5.1) |
| signature: match-type | 89 | 1% | 447 | `harness.endpoint.types.Types$.Query` (harness-endpoint ced1f45ce25efe210d8f3763f0378b2cd78f2145) |
| definition kind: match-type-def | 88 | 1% | 440 | `scodec.DropUnits$package$.DropUnits` (scodec-core 2.3.3) |
| definition kind: transparent-inline-def | 88 | 1% | 1,050 | `scala.quoted.Quotes$package$.quotes` (quack-on-demand 0.4.0) |
| signature: poly-function-type | 68 | 1% | 732 | `com.tschuchort.hkd.InvariantK.imapK` (hkd4s 1.1.0) |
| definition kind: inline-val | 52 | 1% | 1,507 | `kse.maths.NumericConstants$.SqrtTwo` (kse3-maths 0.6.2) |
| signature: named-tuple | 46 | 1% | 502 | `vecxt_re.Poisson$.mleVolumeWeighted` (vecxt_re 0.0.39) |
| signature: dependent-function-type | 41 | 1% | 143 | `slash.vectorf.VectorFSpace.tabulate` (slash 0.4.8) |
| signature: varargs | 40 | 1% | 384 | `oxygen.predef.zio$.logInfoAnnotated` (oxygen-zio 0.6.7) |
| flag: open | 38 | 1% | 109 | `izumi.functional.bio.impl.BioEither` (fundamentals-bio 1.3.0-M3) |
| flag: erased | 7 | 0% | 88 | `scala.unsafeExceptions$.canThrowAny` (librarymanagement-coursier 2.0.0-alpha8) |
| signature: capture-annotation | 3 | 0% | 10 | `steps.result.Result$.catchException` (steps 0.2.1) |

**Expression-level features** (tree nodes in TASTy, and references to the APIs that mark them):

| Feature | Libs | % libs | Occurrences |
|---|---|---|---|
| assignment | 2893 | 47% | 241,906 |
| try | 1961 | 32% | 17,459 |
| while loop | 1253 | 20% | 27,343 |
| Inlined (a transparent inline or macro expansion kept in TASTy) | 1071 | 17% | 124,520 |
| return | 684 | 11% | 12,841 |
| `scala.util.NotGiven` | 665 | 11% | 8,123 |
| Splice | 556 | 9% | 31,451 |
| Quote (macro implementation) | 543 | 9% | 33,173 |
| `scala.quoted.Quotes` (macros) | 538 | 9% | 352,373 |
| `TypeTest` | 327 | 5% | 11,995 |
| `scala.deriving.Mirror` | 259 | 4% | 5,298 |
| export clause | 244 | 4% | 1,941 |
| inline match | 194 | 3% | 1,380 |
| `scala.compiletime.summonInline` | 160 | 3% | 678 |
| `scala.compiletime.erasedValue` | 153 | 2% | 506 |
| `scala.compiletime.constValue` | 133 | 2% | 889 |
| `scala.CanEqual` (multiversal equality) | 102 | 2% | 5,091 |
| `scala.compiletime.error` | 92 | 1% | 745 |
| `scala.util.boundary` | 69 | 1% | 2,382 |
| `scala.annotation.experimental` APIs used | 66 | 1% | 10,418 |
| inline if | 45 | 1% | 432 |
| non-local return (from a lambda) | 45 | 1% | 228 |
| `scala.Dynamic` | 37 | 1% | 85 |
| structural types via `reflectiveSelectable` | 27 | 0% | 244 |
| Scala 2 macro API (`scala.reflect.macros`) | 1 | 0% | 64 |

**Language imports** (`scala.language.*`):

| Import | Libs | Files |
|---|---|---|
| `scala.language.implicitConversions` | 500 | 2,609 |
| `scala.language.postfixOps` | 122 | 184 |
| `scala.language.higherKinds` | 88 | 247 |
| `scala.language$.experimental.macros` | 65 | 173 |
| `scala.language.existentials` | 57 | 112 |
| `scala.language.reflectiveCalls` | 44 | 70 |
| `scala.language.dynamics` | 37 | 55 |
| `scala.language.adhocExtensions` | 26 | 160 |
| `scala.language.unsafeNulls` | 22 | 338 |
| `scala.language.3.0` | 9 | 14 |
| `scala.language$.experimental.erasedDefinitions` | 7 | 8 |
| `scala.languageFeature.postfixOps` | 7 | 33 |
| `scala.language._` | 4 | 4 |
| `scala.language.future` | 4 | 11 |
| `scala.language$.experimental.captureChecking` | 3 | 8 |
| `scala.language.3.6-migration` | 3 | 4 |
| `scala.language.strictEquality` | 2 | 2 |
| `scala.language$.experimental.separationChecking` | 2 | 4 |
| `scala.languageFeature.existentials` | 1 | 1 |
| `scala.languageFeature$.experimental.macros` | 1 | 1 |
| `scala.language$.experimental.saferExceptions` | 1 | 1 |
| `scala.languageFeature.dynamics` | 1 | 1 |
| `scala.language.unsafeNulls=>_` | 1 | 1 |

**`given`/`using` against Scala 2 `implicit`** (definitions per lib, excluding synthetic): how far migration has got.

| Style | Libs |
|---|---|
| only implicit | 2810 |
| neither | 1266 |
| both | 989 |
| only given/using | 778 |

## 3. Library usage index

References are counted per referencing lib, so `Libs` is how many published jars use a symbol, and `Uses` counts reference sites. References from a module to itself, from compiler-generated code (case class and enum boilerplate) and to `Object`'s constructor (every class's parent call) are left out. An implicit conversion is counted both as a `call` and, in section 5, as a conversion; a `value` reference can also be a type name used as an identifier.

**Most used standard library members**

| Symbol | Kind | Libs | Uses |
|---|---|---|---|
| `scala.StringContext$.apply(scala.collection.immutable.Seq)` | call | 3,573 | 119,447 |
| `scala.StringContext.s(scala.collection.immutable.Seq)` | call | 3,509 | 103,342 |
| `scala.Tuple2$.unapply(2,scala.Tuple2)` | call | 3,181 | 75,555 |
| `scala.Tuple2$.apply(2,java.lang.Object,java.lang.Object)` | call | 3,059 | 97,576 |
| `scala.Some$.apply(1,java.lang.Object)` | call | 3,014 | 79,374 |
| `scala.Function1.apply(java.lang.Object)` | call | 2,998 | 67,302 |
| `scala.Some$.unapply(1,scala.Some)` | call | 2,700 | 34,591 |
| `scala.Predef$.augmentString(java.lang.String)` | call | 2,520 | 30,637 |
| `scala.Option.map(1,scala.Function1)` | call | 2,438 | 40,185 |
| `scala.Option.getOrElse(1,scala.Function0)` | call | 2,432 | 35,240 |
| `scala.Predef$.ArrowAssoc(1,java.lang.Object)` | call | 2,370 | 82,928 |
| `scala.Predef$.ArrowAssoc.->(1,java.lang.Object)` | call | 2,370 | 82,926 |
| `scala.Boolean.unary_!()` | call | 2,369 | 49,942 |
| `scala.Boolean.&&(scala.Boolean)` | call | 2,318 | 55,504 |
| `scala.Tuple2._1` | value | 2,289 | 28,392 |
| `scala.<:<$.refl(1)` | call | 2,262 | 20,338 |
| `scala.Tuple2._2` | value | 2,261 | 27,138 |
| `scala.collection.IterableFactory.apply(1,scala.collection.immutable.Seq)` | call | 2,116 | 60,674 |
| `scala.Predef$.String` | value | 2,056 | 30,829 |
| `scala.Int` | value | 2,047 | 30,024 |
| `scala.collection.IterableOps.map(1,scala.Function1)` | call | 2,001 | 21,493 |
| `scala.package$.List` | value | 1,984 | 52,338 |
| `scala.reflect.ClassTag$.apply(1,java.lang.Class)` | call | 1,984 | 44,680 |
| `scala.collection.IterableOnceOps.toList()` | call | 1,983 | 13,777 |
| `scala.Int.+(scala.Int)` | call | 1,981 | 95,867 |
| `scala.package$.Nil` | value | 1,944 | 30,990 |
| `scala.Boolean.\|\|(scala.Boolean)` | call | 1,910 | 29,861 |
| `scala.Int.==(scala.Int)` | call | 1,867 | 31,859 |
| `scala.package$.Right` | value | 1,763 | 29,510 |
| `scala.package$.Left` | value | 1,733 | 26,710 |

**Most used JDK members**

| Symbol | Kind | Libs | Uses |
|---|---|---|---|
| `java.lang.String` | value | 2,469 | 33,684 |
| `java.lang.String.+(java.lang.Object)` | call | 2,137 | 69,709 |
| `java.lang.String.length()` | call | 1,111 | 8,413 |
| `java.lang.Throwable.getMessage()` | call | 1,067 | 4,448 |
| `java.lang.IllegalArgumentException.<init>(java.lang.String)` | call | 975 | 5,951 |
| `java.lang.String.startsWith(java.lang.String)` | call | 949 | 4,667 |
| `java.lang.String.isEmpty()` | call | 906 | 8,007 |
| `java.lang.RuntimeException.<init>(java.lang.String)` | call | 825 | 5,617 |
| `java.lang.String.trim()` | call | 808 | 5,296 |
| `java.lang.String.split(java.lang.String)` | call | 750 | 2,482 |
| `java.lang.String.toLowerCase()` | call | 747 | 2,675 |
| `java.lang.Class.getName()` | call | 739 | 3,406 |
| `java.lang.Throwable` | value | 693 | 3,200 |
| `java.lang.String.contains(java.lang.CharSequence)` | call | 670 | 2,566 |
| `java.lang.Object.eq(java.lang.Object)` | call | 668 | 14,876 |
| `java.lang.Exception.<init>(java.lang.String)` | call | 652 | 2,382 |
| `java.lang.String.endsWith(java.lang.String)` | call | 641 | 2,282 |
| `java.lang.IllegalStateException` | new | 626 | 2,729 |
| `java.lang.String.substring(scala.Int,scala.Int)` | call | 603 | 2,672 |
| `java.lang.IllegalStateException.<init>(java.lang.String)` | call | 593 | 2,533 |
| `java.lang.String.replace(java.lang.CharSequence,java.lang.CharSequence)` | call | 564 | 2,411 |
| `java.nio.charset.StandardCharsets$.UTF_8` | value | 537 | 2,029 |
| `java.lang.String.substring(scala.Int)` | call | 529 | 1,911 |
| `java.lang.String.charAt(scala.Int)` | call | 469 | 3,883 |
| `java.lang.String.replaceAll(java.lang.String,java.lang.String)` | call | 440 | 1,314 |
| `java.lang.String.getBytes(java.nio.charset.Charset)` | call | 437 | 1,249 |
| `java.lang.Class.getSimpleName()` | call | 413 | 1,284 |
| `java.lang.Object.synchronized(1,java.lang.Object)` | call | 403 | 2,699 |
| `java.io.File` | new | 400 | 1,465 |
| `java.io.File.<init>(java.lang.String)` | call | 364 | 1,062 |

**Most used members of other libraries**

| Symbol | Kind | Libs | Uses |
|---|---|---|---|
| `cats.Functor$.ToFunctorOps.toFunctorOps(2,java.lang.Object,cats.Functor)` | call | 786 | 9,877 |
| `cats.Functor$.Ops.map(1,scala.Function1)` | call | 694 | 7,522 |
| `cats.FlatMap$.ToFlatMapOps.toFlatMapOps(2,java.lang.Object,cats.FlatMap)` | call | 583 | 7,480 |
| `cats.FlatMap$.Ops.flatMap(1,scala.Function1)` | call | 569 | 7,264 |
| `zio.internal.stacktracer.Tracer$.autoTrace()` | call | 441 | 41,005 |
| `cats.Applicative.pure(1,java.lang.Object)` | call | 418 | 2,869 |
| `zio.ZIO.map(1,scala.Function1,java.lang.Object)` | call | 368 | 5,885 |
| `cats.effect.kernel.Sync.delay(1,scala.Function0)` | call | 366 | 2,877 |
| `zio.ZIO.flatMap(3,scala.Function1,java.lang.Object)` | call | 350 | 7,903 |
| `cats.effect.kernel.Resource.map(1,scala.Function1)` | call | 337 | 1,187 |
| `cats.syntax.ApplicativeSyntax.catsSyntaxApplicativeId(1,java.lang.Object)` | call | 334 | 1,627 |
| `cats.syntax.ApplicativeIdOps.pure(1,cats.Applicative)` | call | 333 | 1,626 |
| `cats.Traverse$.ToTraverseOps.toTraverseOps(2,java.lang.Object,cats.Traverse)` | call | 330 | 1,161 |
| `cats.effect.package$.Resource` | value | 313 | 1,527 |
| `cats.syntax.EitherSyntax.catsSyntaxEither(2,scala.util.Either)` | call | 298 | 1,221 |
| `zio.CanFail$.canFail(1,scala.util.NotGiven)` | call | 297 | 3,107 |
| `cats.effect.kernel.Resource.flatMap(1,scala.Function1)` | call | 283 | 1,496 |
| `zio.ZIOCompanionVersionSpecific.succeed(1,scala.Function1,java.lang.Object)` | call | 279 | 3,591 |
| `cats.ApplicativeError.raiseError(1,java.lang.Object)` | call | 279 | 1,209 |
| `cats.syntax.OptionSyntax.catsSyntaxOptionId(1,java.lang.Object)` | call | 277 | 1,943 |
| `cats.syntax.OptionIdOps.some()` | call | 276 | 1,942 |
| `cats.Applicative.unit()` | call | 276 | 1,432 |
| `cats.Traverse$.Ops.traverse(2,scala.Function1,cats.Applicative)` | call | 276 | 887 |
| `cats.syntax.ApplicativeErrorSyntax.catsSyntaxApplicativeError(3,java.lang.Object,cats.ApplicativeError)` | call | 274 | 870 |
| `cats.Foldable$.ToFoldableOps.toFoldableOps(2,java.lang.Object,cats.Foldable)` | call | 265 | 935 |
| `fs2.Stream.compile(3,fs2.Compiler)` | call | 263 | 751 |
| `fs2.CompilerLowPriority1.target(1,fs2.Compiler$.Target)` | call | 256 | 734 |
| `cats.effect.kernel.Sync$.apply(1,cats.effect.kernel.Sync)` | call | 249 | 1,990 |
| `cats.UnorderedFoldable$.catsTraverseForList()` | call | 245 | 970 |
| `cats.Functor$.Ops.void()` | call | 244 | 1,092 |
| `izumi.reflect.Tag$.tagFromTagMacro(1)` | call | 238 | 3,151 |
| `cats.Functor$.Ops.as(1,java.lang.Object)` | call | 236 | 690 |
| `io.circe.syntax.package$.EncoderOps(1,java.lang.Object)` | call | 234 | 7,181 |
| `cats.effect.kernel.Resource$.eval(2,java.lang.Object)` | call | 234 | 938 |
| `fs2.Stream.flatMap(2,scala.Function1,scala.util.NotGiven)` | call | 233 | 922 |
| `io.circe.syntax.package$.EncoderOps.asJson(io.circe.Encoder)` | call | 231 | 7,123 |
| `cats.data.NonEmptyList.toList()` | call | 231 | 744 |
| `cats.syntax.FlatMapSyntax.catsSyntaxFlatMapOps(2,java.lang.Object,cats.FlatMap)` | call | 225 | 1,149 |
| `cats.syntax.EitherOps.leftMap(1,scala.Function1)` | call | 225 | 807 |
| `fs2.Compiler$.Target$.forConcurrent(1,cats.effect.kernel.GenConcurrent)` | call | 224 | 660 |

**Most depended-on modules, at symbol level** (libs that reference at least one symbol of the module, excluding the module itself):

| Module | Libs using it | Distinct symbols used | Most used |
|---|---|---|---|
| `org.scala-lang:scala-library` | 5,671 | 6,803 | String, Option, Unit, Boolean, Product |
| `org.typelevel:cats-core_3` | 1,535 | 2,017 | package, toFunctorOps, map, all, toFlatMapOps |
| `org.typelevel:cats-effect_3` | 917 | 438 | Resource, Async, Sync, IO, asyncForIO |
| `org.typelevel:cats-effect-kernel_3` | 835 | 335 | delay, map, flatMap, apply, eval |
| `dev.zio:zio_3` | 545 | 2,061 | ZIO, map, flatMap, canFail, succeed |
| `co.fs2:fs2-core_3` | 502 | 557 | Stream, compile, target, flatMap, forConcurrent |
| `io.circe:circe-core_3` | 498 | 577 | Json, Decoder, Encoder, EncoderOps, asJson |
| `org.typelevel:cats-kernel_3` | 493 | 438 | catsKernelInstancesForString, empty, catsKernelInstancesForInt, Eq, eqv |
| `dev.zio:zio-stacktracer_3` | 447 | 22 | autoTrace, TracingImplicits, given_SourceLocation, Tracer, SourceLocation |
| `org.slf4j:slf4j-api` | 370 | 109 | LoggerFactory, getLogger, debug, info, warn |
| `com.typesafe:config` | 346 | 171 | Config, getString, getConfig, ConfigFactory, getBoolean |
| `org.typelevel:cats-effect-std_3` | 286 | 182 | Queue, Dispatcher, offer, Semaphore, apply |
| `dev.zio:izumi-reflect_3` | 264 | 97 | tagFromTagMacro, tag, apply, closestClass, Tag |
| `org.http4s:http4s-core_3` | 254 | 1,357 | Request, Uri, Method, Response, Headers |
| `dev.zio:zio-streams_3` | 216 | 487 | ZStream, map, flatMap, ZPipeline, Stream |
| `org.apache.pekko:pekko-actor_3` | 216 | 1,608 | ActorSystem, NotUsed, Done, ByteString, apply |
| `com.softwaremill.sttp.model:core_3` | 208 | 443 | StatusCode, code, Uri, Header, UriContext |
| `com.lihaoyi:sourcecode_3` | 186 | 37 | generate, generate, generate, generate, generate |
| `co.fs2:fs2-io_3` | 181 | 302 | Files, Path, Network, apply, package |
| `org.apache.pekko:pekko-stream_3` | 160 | 725 | Source, Flow, Sink, map, apply |
| `org.scodec:scodec-bits_3` | 148 | 251 | ByteVector, apply, toArray, BitVector, toHex |
| `com.lihaoyi:os-lib_3` | 143 | 398 | Path, /, WritableSource, stringPathChunkValidated, package |
| `org.http4s:http4s-client_3` | 139 | 114 | Client, run, apply, expect, Http4sClientDsl |
| `com.softwaremill.sttp.tapir:tapir-core_3` | 139 | 1,028 | Schema, ServerEndpoint, CodecFormat, DecodeResult, Codec |
| `org.typelevel:case-insensitive_3` | 139 | 9 | CIString, toString, apply, CIStringSyntax, ci |
| `com.softwaremill.sttp.shared:core_3` | 130 | 49 | MonadError, unit, WebSockets, MonadErrorOps, syntax |
| `org.typelevel:log4cats-core_3` | 129 | 58 | Logger, name, info, debug, apply |
| `io.circe:circe-parser_3` | 121 | 2 | parse, package |
| `org.scala-lang.modules:scala-xml_3` | 118 | 289 | Elem, Node, Null, NodeSeq, Text |
| `com.lihaoyi:geny_3` | 116 | 52 | StringWritable, text, ByteArrayWritable, InputStreamReadable, readableWritable |
| `org.scalacheck:scalacheck_3` | 105 | 366 | Arbitrary, Gen, map, apply, flatMap |
| `io.circe:circe-generic_3` | 100 | 8 | semiauto, deriveDecoder, deriveEncoder, auto, deriveCodec |
| `com.lihaoyi:upickle-core_3` | 98 | 224 | ReadWriter, join, bimap, Writer, Reader |
| `com.google.protobuf:protobuf-java` | 95 | 1,375 | Descriptors, ByteString, FileDescriptor, CodedOutputStream, CodedInputStream |
| `com.comcast:ip4s-core_3` | 92 | 143 | Port, Host, fromInt, IpAddress, SocketAddress |
| `dev.zio:zio-json_3` | 88 | 296 | JsonDecoder, JsonEncoder, Json, EncoderOps, toJson |
| `com.typesafe.scala-logging:scala-logging_3` | 87 | 14 | error, info, warn, debug, logger |
| `com.lihaoyi:ujson_3` | 86 | 104 | Value, fromString, Obj, Str, package |
| `com.typesafe.akka:akka-actor_3` | 86 | 1,493 | ActorSystem, apply, NotUsed, ExtendedActorSystem, Done |
| `com.softwaremill.sttp.client4:core_3` | 84 | 397 | Backend, body, Response, Request, basicRequest |

**Deprecated APIs still in use** (target annotated `@deprecated`, referenced from another module):

| Symbol | Module | Libs | Uses | Example |
|---|---|---|---|---|
| `scala.Predef$.ArrowAssoc.->(1,java.lang.Object)` | `org.scala-lang:scala-library` | 2370 | 82,926 | cats-eo-schemes-laws 0.14.0 [`HyloTests.scala:21`](https://github.com/constructive-programming/eo/blob/v0.14.0/schemes-laws/src/main/scala/dev/constructive/eo/schemes/laws/discipline/HyloTests.scala#L21) |
| `scala.Predef$.ArrowAssoc(1,java.lang.Object)` | `org.scala-lang:scala-library` | 2370 | 82,928 | clue-model 0.55.0 [`package.scala:24`](https://github.com/gemini-hlsw/clue/blob/v0.55.0/model/src/main/scala/clue/model/json/package.scala#L24) |
| `scala.LowPriorityImplicits.intWrapper(scala.Int)` | `org.scala-lang:scala-library` | 859 | 7,962 | emoji 1.3.0 [`Emoji.scala:97`](https://github.com/scala-garden/lightbend-emoji/blob/1.3.0/src/main/scala-3/com/lightbend/emoji/Emoji.scala#L97) |
| `scala.Option.orNull(1,scala.<:<)` | `org.scala-lang:scala-library` | 482 | 5,012 | awscala-simpledb 0.9.2 [`Item.scala:24`](https://github.com/seratch/awscala/blob/0.9.2/simpledb/src/main/scala/awscala/simpledb/Item.scala#L24) |
| `scala.LowPriorityImplicits.charWrapper(scala.Char)` | `org.scala-lang:scala-library` | 471 | 2,038 | proto-purs 2.1.3 [`ops.scala:165`](https://github.com/zero-deps/proto/blob/2.1.3/purs/src/main/scala-3/ops.scala#L165) |
| `scala.collection.JavaConverters` | `org.scala-lang:scala-library` | 247 | 1,220 | pekko-http-core 1.4.0 [`MapHelpers.scala:18`](https://github.com/apache/pekko-http/blob/v1.4.0/http-core/src/main/scala-2.13+/org/apache/pekko/http/ccompat/MapHelpers.scala#L18) |
| `scala.LowPriorityImplicits.longWrapper(scala.Long)` | `org.scala-lang:scala-library` | 170 | 501 | elastic4s-reactivestreams-pekko 9.3.0 [`ScrollPublisher.scala:103`](https://github.com/philippus/elastic4s/blob/v9.3.0/elastic4s-reactivestreams-pekko/src/main/scala/com/sksamuel/elastic4s/pekko/reactivestreams/ScrollPublisher.scala#L103) |
| `scala.LowPriorityImplicits.doubleWrapper(scala.Double)` | `org.scala-lang:scala-library` | 159 | 593 | caliban 3.1.5 [`Value.scala:220`](https://github.com/ghostdogpr/caliban/blob/v3.1.5/core/src/main/scala/caliban/Value.scala#L220) |
| `java.net.URL.<init>(java.lang.String)` | `JDK` | 82 | 123 | fingertree 1.5.5 `jvm/target/scala-3.0.0/src_managed/main/sbt-buildinfo/BuildInfo.scala:19` |
| `scala.package$.Stream` | `org.scala-lang:scala-library` | 72 | 1,090 | httpz-native-client 0.8.0 [`Http.scala:158`](https://github.com/xuwei-k/httpz/blob/v0.8.0/native-client/src/main/scala/Http.scala#L158) |
| `scala.LowPriorityImplicits2.copyArrayToImmutableIndexedSeq(1,java.lang.Object)` | `org.scala-lang:scala-library` | 62 | 250 | class-path-util 0.1.4 [`ClassPathUtil.scala:61`](https://github.com/coursier/class-path-util/blob/v0.1.4/coursier/cputil/ClassPathUtil.scala#L61) |
| `scala.App` | `org.scala-lang:scala-library` | 52 | 110 | scalatikz 0.5.2 [`AppCLI.scala:25`](https://github.com/vagmcs/scalatikz/blob/v0.5.2/src/main/scala/scalatikz/app/AppCLI.scala#L25) |
| `scala.collection.MapOps.mapValues(1,scala.Function1)` | `org.scala-lang:scala-library` | 51 | 98 | whale-tail 0.0.12 [`Containers.scala:59`](https://github.com/davenverse/whale-tail/blob/v0.0.12/core/src/main/scala/io/chrisdavenport/whaletail/Containers.scala#L59) |
| `scala.LowPriorityImplicits.floatWrapper(scala.Float)` | `org.scala-lang:scala-library` | 51 | 131 | scoin 0.7.0 [`MnemonicCode.scala:150`](https://github.com/fiatjaf/scoin/blob/v0.7.0/shared/src/main/scala/MnemonicCode.scala#L150) |
| `scala.collection.IterableOnceOps.toStream()` | `org.scala-lang:scala-library` | 40 | 93 | case-app 2.1.0 `/home/runner/work/case-app/case-app/core/shared/src/main/scala/caseapp/core/complete/Bash.scala:22` |
| `java.lang.Thread.getId()` | `JDK` | 36 | 70 | scala-react 0.1.0 `src/main/scala/com/likeligood/react/Debug.scala:139` |
| `scala.util.Either.right()` | `org.scala-lang:scala-library` | 34 | 84 | enumeratum-play 1.9.8 [`Forms.scala:87`](https://github.com/lloydmeta/enumeratum/blob/master/enumeratum-play/src/main/scala/enumeratum/Forms.scala#L87) |
| `scala.quoted.Quotes.reflectModule.reportModule.throwError(java.lang.String)` | `org.scala-lang:scala-library` | 29 | 202 | log4s 1.10.0 [`LoggerMacros.scala:19`](https://github.com/log4s/log4s/blob/v1.10.0/core/shared/src/main/scala-3/org/log4s/LoggerMacros.scala#L19) |
| `scala.Selectable$.reflectiveSelectableFromLangReflectiveCalls(java.lang.Object,scala.languageFeature$.reflectiveCalls)` | `org.scala-lang:scala-library` | 27 | 184 | smithytranslate-compiler-core 0.7.7 `/home/runner/work/smithy-translate/smithy-translate/modules/compiler-core/src/internals/GetExtensions.scala:39` |
| `scala.Long$.long2double(scala.Long)` | `org.scala-lang:scala-library` | 27 | 318 | kamon-statsd 2.8.1 [`StatsDReporter.scala:125`](https://github.com/kamon-io/kamon/blob/v2.8.1/reporters/kamon-statsd/src/main/scala/kamon/statsd/StatsDReporter.scala#L125) |
| `scala.package$.Traversable` | `org.scala-lang:scala-library` | 26 | 111 | quill-sql 4.8.6 [`GroupByOps.scala:18`](https://github.com/WojciechMazur/zio-protoquill/blob/scala/3.10-fix/quill-sql/src/main/scala/io/getquill/util/GroupByOps.scala#L18) |
| `scala.package$.TraversableOnce` | `org.scala-lang:scala-library` | 23 | 88 | common 0.2.1 [`RandomUtils.scala:166`](https://github.com/lum-ai/common/blob/v0.2.1/src/main/scala/ai/lum/common/RandomUtils.scala#L166) |
| `scala.collection.Iterable.toIterable()` | `org.scala-lang:scala-library` | 21 | 51 | core 0.14.17 [`CompanionFor.scala:103`](https://github.com/babylonhealth/lit-fhir/blob/g0.14.17/core/src/main/scala/com/babylonhealth/lit/core/CompanionFor.scala#L103) |
| `scala.collection.MapOps.filterKeys(scala.Function1)` | `org.scala-lang:scala-library` | 20 | 26 | scalameter 0.22.1 [`Gen.scala:83`](https://github.com/hughsimpson/scalameter/blob/v0.22.1/src/main/scala/org/scalameter/Gen.scala#L83) |
| `scala.collection.IterableOnceExtensionMethods.foreach(1,scala.Function1)` | `org.scala-lang:scala-library` | 18 | 24 | mixql-core 0.9.3 [`UtilFunction.scala:31`](https://github.com/mixql/mixql-core/blob/v0.9.3/src/main/scala/org/mixql/core/function/UtilFunction.scala#L31) |
| `java.lang.Class.newInstance()` | `JDK` | 17 | 40 | scalatest-freespec 3.2.20 `dotty/freespec/target/scala-3.1.3/src_managed/main/org/scalatest/freespec/PathAnyFreeSpecLike.scala:56` |
| `scala.collection.IterableOnceOps.toIterator()` | `org.scala-lang:scala-library` | 17 | 101 | core 1.0.0-beta45 [`maps.scala:89`](https://github.com/scalablytyped/converter/blob/v1.0.0-beta45/core/src/main/scala/org/scalablytyped/converter/internal/maps.scala#L89) |
| `scala.util.Either$.RightProjection.get()` | `org.scala-lang:scala-library` | 15 | 32 | gears 0.3.1 [`Async.scala:226`](https://github.com/lampepfl/gears/blob/v0.3.1/shared/src/main/scala/async/Async.scala#L226) |
| `scala.LowPriorityImplicits.booleanWrapper(scala.Boolean)` | `org.scala-lang:scala-library` | 14 | 29 | bytecode-representation 7.0.0 [`package.scala:14`](https://github.com/opalj/opal/blob/7.0.0/OPAL/br/src/main/scala/org/opalj/br/cfg/package.scala#L14) |
| `scala.quoted.Quotes.reflectModule.SourceFileMethods.getJPath(java.lang.Object)` | `org.scala-lang:scala-library` | 13 | 16 | weaver-core 0.13.0 [`SourceLocationMacro.scala:38`](https://github.com/typelevel/weaver-test/blob/v0.13.0/modules/core/shared/src/main/scala-3/weaver/SourceLocationMacro.scala#L38) |
| `java.lang.ThreadDeath` | `JDK` | 13 | 44 | dotty-cps-async 1.3.4 [`ControlThrowableAsyncWrapper.scala:22`](https://github.com/dotty-cps-async/dotty-cps-async/blob/1.3.4/shared/src/main/scala/cps/runtime/util/control/ControlThrowableAsyncWrapper.scala#L22) |
| `scala.collection.StringOps.replaceAllLiterally(java.lang.String,java.lang.String)` | `org.scala-lang:scala-library` | 12 | 39 | importer 1.0.0-beta45 [`TopLists.scala:16`](https://github.com/scalablytyped/converter/blob/v1.0.0-beta45/importer/src/main/scala/org/scalablytyped/converter/internal/importer/documentation/TopLists.scala#L16) |
| `scala.collection.mutable.package$.WrappedArray` | `org.scala-lang:scala-library` | 11 | 22 | scrypto 3.1.0 [`MerkleTree.scala:11`](https://github.com/input-output-hk/scrypto/blob/v3.1.0/shared/src/main/scala/scorex/crypto/authds/merkle/MerkleTree.scala#L11) |
| `scala.collection.mutable.AnyRefMap` | `org.scala-lang:scala-library` | 10 | 34 | rtree2d-core 0.11.15 [`RTree.scala:47`](https://github.com/plokhotnyuk/rtree2d/blob/v0.11.15/rtree2d-core/shared/src/main/scala/com/github/plokhotnyuk/rtree2d/core/RTree.scala#L47) |
| `scala.quoted.Quotes.reflectModule.SourceFileMethods.jpath(java.lang.Object)` | `org.scala-lang:scala-library` | 10 | 18 | dotty-cps-async 0.9.23 `shared/src/main/scala/cps/macros/forest/RootTreeTransform.scala:94` |
| `scala.quoted.Quotes.reflectModule.SymbolMethods.memberMethod(java.lang.Object,java.lang.String)` | `org.scala-lang:scala-library` | 9 | 34 | dotty-cps-async 1.3.4 [`ApplyArgRecordScope.scala:370`](https://github.com/dotty-cps-async/dotty-cps-async/blob/1.3.4/shared/src/main/scala/cps/macros/forest/application/ApplyArgRecordScope.scala#L370) |
| `scala.collection.mutable.MultiMap` | `org.scala-lang:scala-library` | 9 | 18 | better-files 3.9.2 [`package.scala:44`](https://github.com/pathikrit/better-files/blob/v3.9.2/core/src/main/scala/better/files/package.scala#L44) |
| `java.util.Locale.<init>(java.lang.String)` | `JDK` | 9 | 32 | play-json 3.1.0-M10 [`EnvReads.scala:621`](https://github.com/playframework/play-json/blob/3.1.0-M10/play-json/jvm/src/main/scala/play/api/libs/json/EnvReads.scala#L621) |
| `scala.Char.+(java.lang.String)` | `org.scala-lang:scala-library` | 9 | 32 | dmaog 0.1.5 [`CodeGenerator.scala:210`](https://github.com/herminiogg/dmaog/blob/v0.1.5/src/main/scala/com/herminiogarcia/dmaog/codeGeneration/CodeGenerator.scala#L210) |
| `scala.collection.IterableOnceExtensionMethods.toIterable()` | `org.scala-lang:scala-library` | 9 | 23 | make-it-g8 1.26.0 [`GitIgnore.scala:42`](https://github.com/arturopala/make-it-g8/blob/v1.26.0/src/main/scala/com/github/arturopala/makeitg8/GitIgnore.scala#L42) |

**Compiler internals used outside the compiler** (references to `dotty.tools.*`): these break across compiler versions.

| Lib | Symbols | Uses | Packages |
|---|---|---|---|
| scala-ts-core 0.8.2 | 189 | 1,386 | dotc, io |
| hearth-cross-quotes 0.4.1 | 98 | 991 | dotc |
| smithy4s-deriving-compiler 0.0.4 | 342 | 812 | tasty, backend, io, dotc |
| mill-runner-daemon 1.1.7 | 123 | 351 | dotc, io |
| zio-profiling-tagging-plugin 0.3.3 | 70 | 178 | io, dotc |
| scala3-reflection 1.3.1 | 46 | 172 | dotc |
| mdoc 2.9.0 | 68 | 123 | dotc, io |
| scala-console 1.8.0 | 40 | 92 | dotc, repl |
| ifdef-plugin 0.4.1 | 50 | 91 | dotc |
| munit-compiler-toolkit 0.4.0 | 43 | 87 | dotc |
| scala3profile 0.2.0 | 25 | 71 | dotc |
| kyo-doctest 1.0.0-RC5 | 32 | 59 | io, dotc |
| java-class-name 0.1.0 | 32 | 54 | dotc, io |
| java-class-name 0.1.9 | 31 | 52 | io, dotc |
| runtime-scaladoc-reader 1.1.0 | 34 | 50 | dotc |
| mill-core-api 1.1.7 | 30 | 47 | dotc |
| smithy4s-deriving-compiler-plugin 0.0.4 | 27 | 43 | backend, io, dotc |
| scala-reflection 2.0.16 | 19 | 39 | dotc |
| scalate-core 1.10.1 | 13 | 17 | Settings, io, dotc |
| terminal21-code-generation 0.30 | 8 | 17 | dotc |
| tasty-extractor 0.51 | 6 | 15 | dotc |
| distage-framework 1.3.0-M3 | 7 | 10 | dotc |
| refuel-container-macro 2.1.0 | 6 | 6 | dotc |
| mdoc-js 2.9.0 | 5 | 6 | io |
| enumeratum-macros 1.9.8 | 4 | 4 | dotc |
| kyo-compiler 1.0.0-RC5 | 3 | 4 | pc |
| alchemist-incarnation-scafi3 3.3.0 | 4 | 4 | dotc |
| hottie 1.0.6 | 3 | 3 | dotc |
| validation-scala-plugin 1.0.0-RC1 | 2 | 2 | dotc |
| scalate-jsp-converter 1.10.1 | 2 | 2 | MainGenericRunner, MainGenericRunner$ |

## 4. Binary-compatibility hazards

**Inline methods are ABI.** A call to an `inline` method from another module is expanded into the caller, so the callee's body, and everything it references, is frozen into the caller's bytecode. These are the modules whose inline methods are expanded elsewhere:

| Module | Inline methods used | Libs | Sites | Most used |
|---|---|---|---|---|
| `org.scala-lang:scala-library` | 41 | 470 | 6,209 | `package$package$.constValue` |
| `dev.zio:zio-stacktracer_3` | 3 | 443 | 41,164 | `Tracer$.autoTrace` |
| `dev.zio:zio_3` | 10 | 291 | 7,729 | `TagVersionSpecific.materialize` |
| `dev.zio:izumi-reflect_3` | 2 | 244 | 47,949 | `LTag$.materialize` |
| `com.lihaoyi:sourcecode_3` | 9 | 158 | 38,593 | `LineMacros.generate` |
| `io.circe:circe-generic_3` | 5 | 96 | 3,347 | `semiauto$.deriveEncoder` |
| `com.lihaoyi:os-lib_3` | 3 | 85 | 1,864 | `PathChunkMacros.stringPathChunkValidated` |
| `com.typesafe.scala-logging:scala-logging_3` | 7 | 83 | 956 | `LoggerImpl.debug` |
| `org.typelevel:log4cats-core_3` | 1 | 55 | 107 | `LoggerNameCompat.name` |
| `io.circe:circe-core_3` | 17 | 53 | 953 | `CodecDerivation.derived` |
| `io.getkyo:kyo-data_3` | 51 | 45 | 5,234 | `Frame$.derive` |
| `dev.zio:zio-json_3` | 6 | 45 | 839 | `DeriveJsonDecoder$.gen` |
| `com.lihaoyi:upickle-implicits_3` | 17 | 44 | 982 | `ReadersVersionSpecific.macroR` |
| `org.http4s:http4s-core_3` | 4 | 43 | 223 | `LiteralsSyntax.uri` |
| `io.getkyo:kyo-kernel_3` | 45 | 43 | 10,207 | `CanLift$.derived` |
| `io.getkyo:kyo-prelude_3` | 37 | 37 | 2,003 | `Abort$.fail` |
| `com.github.pureconfig:pureconfig-core_3` | 8 | 34 | 167 | `ConfigReaderDerivation.derived` |
| `io.getkyo:kyo-core_3` | 84 | 32 | 1,340 | `Unsafe$.defer` |
| `com.softwaremill.magnolia1_3:magnolia_3` | 16 | 29 | 200 | `Derivation.derived` |
| `com.comcast:ip4s-core_3` | 5 | 29 | 71 | `Literals$package$.port` |
| `org.tpolecat:typename_3` | 1 | 29 | 526 | `TypeNamePlatform.given_TypeName_A` |
| `com.kubuszok:hearth_3` | 3 | 28 | 7,518 | `CrossQuotesSupport.exprCrossToQuotes` |
| `com.lihaoyi:fastparse_3` | 34 | 27 | 11,719 | `package$.~` |
| `com.softwaremill.sttp.tapir:tapir-core_3` | 21 | 27 | 324 | `SchemaMacros.modify` |
| `org.scalactic:scalactic_3` | 6 | 26 | 1,856 | `Position$.here` |
| `org.typelevel:kittens_3` | 4 | 23 | 378 | `package$package$.derived` |
| `org.typelevel:otel4s-core-trace_3` | 13 | 23 | 355 | `SpanMacro.addAttributes` |
| `org.log4s:log4s_3` | 6 | 22 | 402 | `Logger.error` |
| `io.github.iltotore:iron_3` | 36 | 22 | 1,121 | `DescribedAs$.given_DescribedAsConstraint_A_C_Impl_V` |
| `org.typelevel:shapeless3-deriving_3` | 48 | 22 | 219 | `Labelling$.apply` |

**Public inline methods that reach non-public members** (8,956 sites in 403 libs): the private member, or the `inline$` accessor the compiler generates for it, becomes part of the binary API, so making it truly private or changing its signature breaks callers compiled against an older version.

| Lib | Sites (capped) | Inline method | Reaches | Site |
|---|---|---|---|---|
| scalqa 1.0 | 300 | `scalqa.fx.base.abstract.delegate.Opaque.implicitBaseToType` | `scalqa.package$.cast (qualified)` | [`Opaque.scala:8`](https://github.com/scalqa/scalqa/blob/v1.0/project/release/scalqa/src/scalqa/fx/base/abstract/delegate/Opaque.scala#L8) |
| vecxt 0.0.39 | 300 | `vecxt.BooleanArrays$.not!` | `vecxt.BooleanArrays$.inline$spb (inline accessor)` | `/home/runner/work/vecxt/vecxt/vecxt/src-jvm/BooleanArrays.scala:109` |
| saferis 0.18.0 | 300 | `saferis.Alias$.apply` | `saferis.Alias$.inline$applyImpl (inline accessor)` | [`Alias.scala:39`](https://github.com/early-effect/saferis/blob/v0.18.0/core/src/main/scala/saferis/Alias.scala#L39) |
| scalatest-app 3.2.20 | 300 | `org.scalatest.featurespec.FixtureAnyFeatureSpecLike.ResultOfScenarioInvocation.apply` | `org.scalatest.featurespec.FixtureAnyFeatureSpecLike.ResultOfScenarioInvocation.inline$applyImpl (inline accessor)` | `dotty/featurespec/target/scala-3.1.3/src_managed/main/org/scalatest/featurespec/FixtureAnyFeatureSpecLike.scala:134` |
| ldbc-schema 0.7.0 | 260 | `ldbc.schema.DataTypes.DECIMAL` | `ldbc.schema.DataTypes.inline$Decimal$i1 (inline accessor)` | [`DataTypes.scala:107`](https://github.com/takapi327/ldbc/blob/v0.7.0/module/ldbc-schema/src/main/scala/ldbc/schema/DataTypes.scala#L107) |
| scalatest-flatspec 3.2.20 | 231 | `org.scalatest.flatspec.AnyFlatSpecLike.TheyVerbStringTaggedAs.in` | `org.scalatest.flatspec.AnyFlatSpecLike.TheyVerbStringTaggedAs.inline$verb (inline accessor)` | `dotty/flatspec/target/scala-3.1.3/src_managed/main/org/scalatest/flatspec/AnyFlatSpecLike.scala:1011` |
| kyo-kernel 1.0.0-RC5 | 155 | `kyo.Kyo$.shiftedWhile` | `kyo.Kyo$.inline$shiftedWhile (inline accessor)` | [`Kyo.scala:1267`](https://github.com/getkyo/kyo/blob/v1.0.0-RC5/kyo-kernel/shared/src/main/scala/kyo/Kyo.scala#L1267) |
| kyo-schema 1.0.0-RC5 | 119 | `kyo.Compare.changed` | `kyo.Compare.inline$apply$i1 (inline accessor)` | [`Compare.scala:53`](https://github.com/getkyo/kyo/blob/v1.0.0-RC5/kyo-schema/shared/src/main/scala/kyo/Compare.scala#L53) |
| scalatest-wordspec 3.2.20 | 100 | `org.scalatest.wordspec.AnyWordSpecLike.ResultOfTaggedAsInvocationOnString.in` | `org.scalatest.wordspec.AnyWordSpecLike.ResultOfTaggedAsInvocationOnString.inline$specText (inline accessor)` | `dotty/wordspec/target/scala-3.1.3/src_managed/main/org/scalatest/wordspec/AnyWordSpecLike.scala:294` |
| lls 0.3.0 | 95 | `lowlevel.ArrayView$package$.ArrayFilteredView$.foreach` | `lowlevel.ArrayView$package$.ArrayFilteredView$.arr (private)` | [`ArrayView.scala:111`](https://github.com/kubuszok/lls/blob/0.3.0/lls/src/main/scala/lowlevel/ArrayView.scala#L111) |
| jam-core 0.4.5 | 93 | `jam.package$package$.brewFromWithRec` | `jam.internal (qualified)` | `core/src-3/jam/package.scala:10` |
| kyo-core 1.0.0-RC5 | 87 | `kyo.StreamCompression$.gzip` | `kyo.StreamCompression$.inline$gzipStream (inline accessor)` | [`StreamCompression.scala:102`](https://github.com/getkyo/kyo/blob/v1.0.0-RC5/kyo-core/jvm/src/main/scala/kyo/StreamCompression.scala#L102) |
| dfhdl-core 0.20.0 | 84 | `dfhdl.core.BoolSelWrapper.==` | `dfhdl.core.DFVal$.Ops$.compare (qualified)` | [`BoolSelWrapper.scala:14`](https://github.com/dfianthdl/dfhdl/blob/v0.20.0/core/src/main/scala/dfhdl/core/BoolSelWrapper.scala#L14) |
| kyo-compat-future 1.0.0-RC5 | 78 | `kyo.compat.CChannel.put` | `kyo.compat.CChannel.inline$doPut (inline accessor)` | [`CChannel.scala:27`](https://github.com/getkyo/kyo/blob/v1.0.0-RC5/kyo-compat/bindings/future/shared/src/main/scala/kyo/compat/CChannel.scala#L27) |
| toolkit 0.1.0-RC4 | 73 | `com.geirolz.app.toolkit.AppFailureSyntax.mapFailure` | `com.geirolz.app.toolkit.AppFailureSyntax.inline$copyWith$default$1$i1 (inline accessor)` | [`App.scala:124`](https://github.com/geirolz/toolkit/blob/v0.1.0-RC4/core/src/main/scala/com/geirolz/app/toolkit/App.scala#L124) |
| mouse 0.6.1 | 72 | `mouse.Client.connectBlocking` | `mouse.internal.helpers$package$.blockCall (qualified)` | `src/main/scala/mouse/Client.scala:29` |
| uni 0.19.3 | 71 | `uni.PathsUtils$package$.showMinimalStack` | `uni.PathsUtils$package$.inline$withFilteredStack (inline accessor)` | [`PathsUtils.scala:102`](https://github.com/philwalk/uni/blob/v0.19.3/src/main/scala/uni/PathsUtils.scala#L102) |
| quack-on-demand 0.4.0 | 71 | `org.log4s.package$package$.getLogger` | `org.log4s.package$package$.inline$LoggerMacros (inline accessor)` | [`package.scala:5`](https://github.com/starlake-ai/quack-on-demand/blob/v0.4.0/core/jvm/src/main/scala-3/org/log4s/package.scala#L5) |
| turbolift-core-next 0.126.0 | 57 | `turbolift.Effect.perform` | `turbolift.ComputationCases$.perform (qualified)` | [`Effect.scala:58`](https://github.com/marcinzh/turbolift/blob/v0.126.0/modules/core/src/main/scala/turbolift/Effect.scala#L58) |
| turbolift-core 0.126.0 | 57 | `turbolift.Effect.perform` | `turbolift.ComputationCases$.perform (qualified)` | [`Effect.scala:58`](https://github.com/marcinzh/turbolift/blob/v0.126.0/modules/core/src/main/scala/turbolift/Effect.scala#L58) |

**Constants folded across modules.** A reference to a `final val` with a literal type is replaced by its value at compile time, so a new release of the defining module doesn't change callers until they are recompiled. Constants from other non-stdlib modules:

| Constant | Module | Libs | Uses | Example |
|---|---|---|---|---|
| `com.fasterxml.jackson.core.JsonTokenId$.ID_STRING` | `com.fasterxml.jackson.core:jackson-core` | 31 | 36 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:82`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L82) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_END_OBJECT` | `com.fasterxml.jackson.core:jackson-core` | 27 | 29 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:103`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L103) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_START_OBJECT` | `com.fasterxml.jackson.core:jackson-core` | 27 | 29 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:95`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L95) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_NUMBER_FLOAT` | `com.fasterxml.jackson.core:jackson-core` | 27 | 29 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:79`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L79) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_START_ARRAY` | `com.fasterxml.jackson.core:jackson-core` | 27 | 29 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:86`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L86) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_FALSE` | `com.fasterxml.jackson.core:jackson-core` | 27 | 28 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:84`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L84) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_NUMBER_INT` | `com.fasterxml.jackson.core:jackson-core` | 27 | 28 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:79`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L79) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_TRUE` | `com.fasterxml.jackson.core:jackson-core` | 27 | 28 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:83`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L83) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_FIELD_NAME` | `com.fasterxml.jackson.core:jackson-core` | 27 | 28 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:97`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L97) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_NULL` | `com.fasterxml.jackson.core:jackson-core` | 27 | 28 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:85`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L85) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_END_ARRAY` | `com.fasterxml.jackson.core:jackson-core` | 26 | 27 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:88`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L88) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_NOT_AVAILABLE` | `com.fasterxml.jackson.core:jackson-core` | 19 | 20 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:113`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L113) |
| `com.fasterxml.jackson.core.JsonTokenId$.ID_EMBEDDED_OBJECT` | `com.fasterxml.jackson.core:jackson-core` | 19 | 20 | circe-jackson210 0.14.2 [`CirceJsonDeserializer.scala:116`](https://github.com/circe/circe-jackson/blob/v0.14.2/shared/src/main/scala/io/circe/jackson/CirceJsonDeserializer.scala#L116) |
| `io.shiftleft.codepropertygraph.generated.Operators$.assignment` | `io.shiftleft:codepropertygraph-domain-classes_3` | 15 | 134 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:190`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L190) |
| `zio.stream.ZStream$.DefaultChunkSize` | `dev.zio:zio-streams_3` | 14 | 24 | zio-process 0.8.0 [`Constructors.scala:35`](https://github.com/zio/zio-process/blob/v0.8.0/zio-process/jvm/src/main/scala/zio/process/Constructors.scala#L35) |
| `io.shiftleft.codepropertygraph.generated.Operators$.fieldAccess` | `io.shiftleft:codepropertygraph-domain-classes_3` | 13 | 70 | rubysrc2cpg 4.0.584 [`AstForControlStructuresCreator.scala:94`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstForControlStructuresCreator.scala#L94) |
| `io.shiftleft.codepropertygraph.generated.Operators$.indexAccess` | `io.shiftleft:codepropertygraph-domain-classes_3` | 13 | 37 | rubysrc2cpg 4.0.584 [`AstForExpressionsCreator.scala:381`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstForExpressionsCreator.scala#L381) |
| `io.shiftleft.codepropertygraph.generated.DispatchTypes$.STATIC_DISPATCH` | `io.shiftleft:codepropertygraph-domain-classes_3` | 12 | 233 | semanticcpg 4.0.584 [`CallMethods.scala:11`](https://github.com/joernio/joern/blob/v4.0.584/semanticcpg/src/main/scala/io/shiftleft/semanticcpg/language/nodemethods/CallMethods.scala#L11) |
| `io.shiftleft.codepropertygraph.generated.Operators$.equals` | `io.shiftleft:codepropertygraph-domain-classes_3` | 12 | 28 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:323`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L323) |
| `io.shiftleft.codepropertygraph.generated.Operators$.notEquals` | `io.shiftleft:codepropertygraph-domain-classes_3` | 12 | 23 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:325`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L325) |
| `io.shiftleft.codepropertygraph.generated.Operators$.division` | `io.shiftleft:codepropertygraph-domain-classes_3` | 12 | 16 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:320`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L320) |
| `io.shiftleft.codepropertygraph.generated.Operators$.multiplication` | `io.shiftleft:codepropertygraph-domain-classes_3` | 12 | 16 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:319`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L319) |
| `io.shiftleft.codepropertygraph.generated.Operators$.addition` | `io.shiftleft:codepropertygraph-domain-classes_3` | 12 | 15 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:317`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L317) |
| `io.shiftleft.codepropertygraph.generated.Operators$.assignmentShiftLeft` | `io.shiftleft:codepropertygraph-domain-classes_3` | 12 | 15 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:352`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L352) |
| `io.shiftleft.codepropertygraph.generated.Operators$.modulo` | `io.shiftleft:codepropertygraph-domain-classes_3` | 12 | 15 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:321`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L321) |
| `io.shiftleft.codepropertygraph.generated.DispatchTypes$.DYNAMIC_DISPATCH` | `io.shiftleft:codepropertygraph-domain-classes_3` | 11 | 61 | semanticcpg 4.0.584 [`CallMethods.scala:14`](https://github.com/joernio/joern/blob/v4.0.584/semanticcpg/src/main/scala/io/shiftleft/semanticcpg/language/nodemethods/CallMethods.scala#L14) |
| `io.shiftleft.codepropertygraph.generated.Operators$.assignmentOr` | `io.shiftleft:codepropertygraph-domain-classes_3` | 11 | 15 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:350`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L350) |
| `io.shiftleft.codepropertygraph.generated.Operators$.assignmentAnd` | `io.shiftleft:codepropertygraph-domain-classes_3` | 11 | 15 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:351`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L351) |
| `io.shiftleft.codepropertygraph.generated.Operators$.assignmentPlus` | `io.shiftleft:codepropertygraph-domain-classes_3` | 11 | 14 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:344`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L344) |
| `io.shiftleft.codepropertygraph.generated.Operators$.assignmentMultiplication` | `io.shiftleft:codepropertygraph-domain-classes_3` | 11 | 14 | rubysrc2cpg 4.0.584 [`AstCreatorHelper.scala:346`](https://github.com/joernio/joern/blob/v4.0.584/joern-cli/frontends/rubysrc2cpg/src/main/scala/io/joern/rubysrc2cpg/astcreation/AstCreatorHelper.scala#L346) |

**Inferred types in public API.** A public `def`/`val` without a type annotation has whatever type the compiler infers from its body; an innocent edit to the body changes the signature. Counted over non-synthetic, non-override public and protected members:

| Inferred type | Definitions | Libs | Example |
|---|---|---|---|
| ref | 291,173 | 4,006 | `A.i` [`Hello.scala:1`](https://github.com/mpollmeier/sbt-ci-release-early-usage/blob/v0.3.61/src/main/scala/Hello.scala#L1) |
| applied | 223,206 | 3,418 | `main.T.os` [`Main.scala:34`](https://github.com/liewhite/swopen/blob/v0.17.5/sqlx/src/main/scala/Main.scala#L34) |
| literal | 12,544 | 311 | `toml.Constants$.Lf` [`Constants.scala:15`](https://github.com/indoorvivants/toml-scala/blob/v0.3.0/core/src/main/scala/toml/Constants.scala#L15) |
| singleton | 10,354 | 593 | `dfhdl.hdl$.?` [`hdl.scala:86`](https://github.com/dfianthdl/dfhdl/blob/v0.20.0/core/src/main/scala/dfhdl/hdl.scala#L86) |
| top:Any | 1,061 | 235 | `dfhdl.hdl$.<>` [`hdl.scala:18`](https://github.com/dfianthdl/dfhdl/blob/v0.20.0/core/src/main/scala/dfhdl/hdl.scala#L18) |
| intersection | 782 | 90 | `uni.Ext$.walk` [`Ext.scala:4`](https://github.com/philwalk/uni/blob/v0.19.3/src/main/scala/uni/ext/Ext.scala#L4) |
| union | 767 | 112 | `dfhdl.hdl$.to` [`hdl.scala:33`](https://github.com/dfianthdl/dfhdl/blob/v0.20.0/core/src/main/scala/dfhdl/hdl.scala#L33) |
| refinement | 407 | 91 | `teseo.Algm.\|` [`Algm.scala:101`](https://github.com/pablf/teseo/blob/v0.1.0/teseo/shared/src/main/scala/teseo/Algm.scala#L101) |
| top:Object | 219 | 92 | `kyo.LLM$.State.owner` [`LLM.scala:43`](https://github.com/getkyo/kyo/blob/v1.0.0-RC5/kyo-ai/shared/src/main/scala/kyo/LLM.scala#L43) |
| nothing | 149 | 73 | `sbinary.EOF$.eof` [`io.scala:5`](https://github.com/sbt/sbinary/blob/v0.5.2/core/src/main/scala/io.scala#L5) |
| CachedThisType | 33 | 12 | `scas.util.Lazy.ready` [`Lazy.scala:12`](https://github.com/rjolly/scas/blob/master/eclipse-workspace1/scas/scas/src/scas/util/Lazy.scala#L12) |
| CachedExprType | 7 | 5 | `decisions4s.HKD$.shapeGen.inst` [`HKD.scala:86`](https://github.com/business4s/decisions4s/blob/v0.2.1/decisions4s-core/src/main/scala/decisions4s/HKD.scala#L86) |
| top:Product | 5 | 5 | `org.scalamock.context.Call.arguments` [`Call.scala:25`](https://github.com/scalamock/scalamock/blob/v7.5.5/core/shared/src/main/scala/org/scalamock/context/Call.scala#L25) |
| top:Matchable | 4 | 2 | `tastymima.Problem.details` [`Problem.scala:10`](https://github.com/scalacenter/tasty-mima/blob/v1.4.1/tasty-mima/src/main/scala/tastymima/Problem.scala#L10) |
| top:Serializable | 2 | 2 | `org.apache.pekko.stream.connectors.jms.JmsObjectMessagePassThrough.serializable` [`JmsMessages.scala:863`](https://github.com/apache/pekko-connectors/blob/v2.0.0-M1/jms/src/main/scala/org/apache/pekko/stream/connectors/jms/JmsMessages.scala#L863) |
| top:AnyVal | 1 | 1 | `scalqa.lang.byte.z.Math$.sum` [`Math.scala:35`](https://github.com/scalqa/scalqa/blob/v1.0/project/release/scalqa/src/scalqa/lang/byte/z/Math.scala#L35) |
| RecType | 1 | 1 | `libretto.scaletto.AbstractStarterKit.executorFactory` [`StarterKit.scala:26`](https://github.com/tomasmikula/libretto/blob/main/core/src/main/scala/libretto/scaletto/StarterKit.scala#L26) |

`union`, `intersection` and the `top:` rows are the suspicious ones: usually an accidental least upper bound of the branches of the body. `literal` rows are mostly intended constants (`final val Max = 10`), which are inlined into callers (see above); `singleton` ones change when the body changes. Inferred types of implicits/givens also affect implicit resolution.

## 5. Hazard patterns

**Non-local `return` from a lambda.** Deprecated since 3.2 (implemented with exceptions; `boundary`/`break` replaces it). This is the population a removal would break. **228 sites in 45 libs**.

| Lib | Sites | Example | In | Site |
|---|---|---|---|---|
| bptree 0.0.3 | 21 | `return from check inside $anonfun` | `io.github.edadma.bptree.BPlusTree._$check` | `shared/src/main/scala/io/github/edadma/bptree/BPlusTree.scala:804` |
| three-address-code 7.0.0 | 18 | `return from checkMustAlias inside $anonfun` | `org.opalj.tac.fpcf.analyses.alias.AllocationSiteAndTacBasedAliasAnalysis.checkMustAlias` | [`AllocationSiteAndTacBasedAliasAnalysis.scala:27`](https://github.com/opalj/opal/blob/7.0.0/OPAL/tac/src/main/scala/org/opalj/tac/fpcf/analyses/alias/AllocationSiteAndTacBasedAliasAnalysis.scala#L27) |
| breeze 2.1.0 | 14 | `return from equals inside $anonfun` | `breeze.collection.mutable.SparseArray.equals` | [`SparseArray.scala:428`](https://github.com/scalanlp/breeze/blob/releases/v2.1.0/math/src/main/scala/breeze/collection/mutable/SparseArray.scala#L428) |
| lucuma-jts 0.5.0 | 14 | `return from isEqual inside $anonfun` | `org.locationtech.jts.geom.CoordinateSequences$.isEqual` | [`CoordinateSequences.scala:231`](https://github.com/gemini-hlsw/lucuma-jts/blob/v0.5.0/modules/jts/src/main/scala/org/locationtech/jts/geom/CoordinateSequences.scala#L231) |
| bytecode-representation 7.0.0 | 13 | `return from isASubtypeOf inside $anonfun` | `org.opalj.br.ClassHierarchy.isASubtypeOf` | [`ClassHierarchy.scala:1562`](https://github.com/opalj/opal/blob/7.0.0/OPAL/br/src/main/scala/org/opalj/br/ClassHierarchy.scala#L1562) |
| gapt 2.19.0 | 13 | `return from unifyPair inside $anonfun` | `gapt.cutintro.gStarUnify$.unifyPair` | [`gStarUnify.scala:154`](https://github.com/gapt/gapt/blob/v2.19.0/core/src/main/scala/gapt/cutintro/gStarUnify.scala#L154) |
| pmml4s 1.5.8 | 13 | `return from getMissingClass inside $anonfun` | `org.pmml4s.common.MutablePredictedValueWithProbabilities.getMissingClass` | [`outputs.scala:305`](https://github.com/autodeployai/pmml4s/blob/v1.5.8/src/main/scala/org/pmml4s/common/outputs.scala#L305) |
| kiama 2.5.1 | 11 | `return from allRewritable inside $anonfun` | `org.bitbucket.inkytonik.kiama.rewriting.Rewriter.allRewritable` | [`Rewriter.scala:570`](https://github.com/inkytonik/kiama/blob/v2.5.1/core/src/main/scala/org/bitbucket/inkytonik/kiama/rewriting/Rewriter.scala#L570) |
| graph-core 2.0.2 | 10 | `return from block inside $anonfun` | `scalax.collection.ForeachBasedDetachingIterable._$_$block` | [`ForeachBasedDetachingIterable.scala:118`](https://github.com/scala-graph/scala-graph/blob/2.0.2/core/src/main/scala/scalax/collection/ForeachBasedDetachingIterable.scala#L118) |
| cornichon-core 0.24.0 | 10 | `return from addValues inside $anonfun` | `com.github.agourlay.cornichon.core.Session.addValues` | [`Session.scala:88`](https://github.com/agourlay/cornichon/blob/v0.24.0/cornichon-core/src/main/scala/com/github/agourlay/cornichon/core/Session.scala#L88) |
| scalatest-app 3.2.20 | 6 | `return from checkTheSameElementsAs inside $anonfun` | `org.scalatest.enablers.AggregatingImpls.checkTheSameElementsAs` | `dotty/core/target/scala-3.1.3/src_managed/main/org/scalatest/enablers/Aggregating.scala:153` |
| mixql-core 0.9.3 | 6 | `return from compareFunctionTypes inside $anonfun` | `org.mixql.core.function.FunctionInvoker$.compareFunctionTypes` | [`FunctionInvoker.scala:106`](https://github.com/mixql/mixql-core/blob/v0.9.3/src/main/scala/org/mixql/core/function/FunctionInvoker.scala#L106) |

**A strict `val` read before its initialisation** in the same template (it reads `null`/`0`). Only direct reads in the initialiser are found, not reads through methods. **15 sites in 8 libs**.

| Lib | Sites | Example | In | Site |
|---|---|---|---|---|
| molecule-db-compliance 0.30.0 | 5 | `password read before its initialisation` | `molecule.db.compliance.domains.Validation.Require` | [`Validation.scala:333`](https://github.com/scalamolecule/molecule/blob/v0.30.0/db/compliance/shared/src/main/scala/molecule/db/compliance/domains/Validation.scala#L333) |
| zio-direct 1.0.0-RC7 | 2 | `parallelExplanation read before its initialisation` | `zio.direct.core.util.Messages$` | [`Messages.scala:84`](https://github.com/zio/zio-direct/blob/v1.0.0-RC7/zio-direct/src/main/scala/zio/direct/core/util/Messages.scala#L84) |
| skuber 4.0.11 | 2 | `schemaFormat read before its initialisation` | `skuber.apiextensions.v1beta1.CustomResourceDefinition$` | [`CustomResourceDefinition.scala:122`](https://github.com/hagay3/skuber/blob/v4.0.11/client/src/main/scala/skuber/apiextensions/v1beta1/CustomResourceDefinition.scala#L122) |
| lucuma-jts 0.5.0 | 2 | `isTargetRectangle read before its initialisation` | `org.locationtech.jts.operation.overlayng.FastOverlayFilter` | [`FastOverlayFilter.scala:12`](https://github.com/gemini-hlsw/lucuma-jts/blob/v0.5.0/modules/jts/src/main/scala/org/locationtech/jts/operation/overlayng/FastOverlayFilter.scala#L12) |
| kyo-core 1.0.0-RC5 | 1 | `live read before its initialisation` | `kyo.System$` | [`System.scala:96`](https://github.com/getkyo/kyo/blob/v1.0.0-RC5/kyo-core/shared/src/main/scala/kyo/System.scala#L96) |
| turbolift-core 0.126.0 | 1 | `force read before its initialisation` | `turbolift.effects.ReaderEffect.handlers$._$$anon` | [`Reader.scala:65`](https://github.com/marcinzh/turbolift/blob/v0.126.0/modules/core/src/main/scala/turbolift/effects/Reader.scala#L65) |
| turbolift-core-next 0.126.0 | 1 | `force read before its initialisation` | `turbolift.effects.ReaderEffect.handlers$._$$anon` | [`Reader.scala:65`](https://github.com/marcinzh/turbolift/blob/v0.126.0/modules/core/src/main/scala/turbolift/effects/Reader.scala#L65) |
| kyo-bench 1.0.0-RC5 | 1 | `IdentityScalarProcessor read before its initialisation` | `yamlbench.YamlCstBench$` | [`YamlCstBench.scala:69`](https://github.com/getkyo/kyo/blob/v1.0.0-RC5/kyo-bench/src/main/scala/yamlbench/YamlCstBench.scala#L69) |

**`==` between values that can never be equal**: one side's class is final (or an object) and isn't a subtype of the other's. The compiler rejects this for primitives and `String`, but not for user classes. **11 sites in 9 libs**.

| Lib | Sites | Example | In | Site |
|---|---|---|---|---|
| spire 0.18.0 | 2 | `spire.math.Complex[_$2] == spire.math.Algebraic` | `spire.math.Algebraic.equals` | [`Algebraic.scala:170`](https://github.com/typelevel/spire/blob/main/core/src/main/scala/spire/math/Algebraic.scala#L170) |
| advxml-core 2.5.1 | 2 | `advxml.data.Key == scala.Predef.String` | `advxml.data.Key$._$$anonfun` | [`KeyValue.scala:12`](https://github.com/geirolz/advxml/blob/v2.5.1/core/src/main/scala/advxml/data/KeyValue.scala#L12) |
| breeze 2.1.0 | 1 | `scala.Tuple2[scala.Tuple2[java.lang.Class[_ >: scala.Nothing <: scala.Any], java.lang.Class[_ >: scala.Nothing <: scala.` | `breeze.linalg.operators.BinaryRegistry.apply` | [`BinaryOp.scala:72`](https://github.com/scalanlp/breeze/blob/releases/v2.1.0/math/src/main/scala/breeze/linalg/operators/BinaryOp.scala#L72) |
| tus4s-http4s 0.1.0 | 1 | `org.http4s.headers.Content-Type == org.http4s.MediaType` | `tus4s.http4s.Headers$._$$anonfun` | [`Headers.scala:17`](https://github.com/eikek/tus4s/blob/v0.1.0/modules/http4s/src/main/scala/tus4s/http4s/Headers.scala#L17) |
| compilerplugin 1.0.0-alpha.6 | 1 | `com.google.protobuf.DescriptorProtos.FieldDescriptorProto == scala.collection.immutable.Map[com.google.protobuf.Descript` | `scalapb.compiler.FieldTransformations$.matches` | [`FieldTransformations.scala:80`](https://github.com/scalapb/scalapb/blob/v1.0.0-alpha.6/compiler-plugin/src/main/scala/scalapb/compiler/FieldTransformations.scala#L80) |
| daffodil-core 4.2.0 | 1 | `passera.unsigned.ULong == scala.Int` | `org.apache.daffodil.unparsers.runtime1.AlignmentFillUnparserSuspendableMixin.continuation` | [`FramingUnparsers.scala:59`](https://github.com/apache/daffodil/blob/v4.2.0/daffodil-core/src/main/scala/org/apache/daffodil/unparsers/runtime1/FramingUnparsers.scala#L59) |
| util-core 24.2.0 | 1 | `com.twitter.io.Buf.Composite == com.twitter.io.Buf.ByteArray` | `com.twitter.io.Buf$.ByteArray.equals` | [`Buf.scala:691`](https://github.com/twitter/util/blob/util-24.2.0/util-core/src/main/scala/com/twitter/io/Buf.scala#L691) |
| analogweb-scala 0.13.0 | 1 | `scala.Some[scala.Predef.String] == scala.None` | `org.analogweb.scala.Execution$.Implicits$._$_$$anonfun` | [`Execution.scala:30`](https://github.com/analogweb/analogweb-scala/blob/v0.13.0/core/src/main/scala/org/analogweb/scala/Execution.scala#L30) |
| grpc-rest-gateway-code-gen 0.9.1 | 1 | `com.google.protobuf.Descriptors#FieldDescriptor#JavaType == com.google.protobuf.WireFormat#JavaType` | `com.improving.grpc_rest_gateway.compiler.utils.GenerateImportStatements._$subFields` | [`GenerateImportStatements.scala:61`](https://github.com/sfali/grpc-rest-gateway/blob/v0.9.1/code-gen/src/main/scala/com/improving/grpc_rest_gateway/compiler/utils/GenerateImportStatements.scala#L61) |

**Type patterns with type arguments the runtime can't check** (a heuristic superset of the compiler's unchecked warning; `@unchecked` ones excluded). **1,471 sites in 326 libs**.

| Lib | Sites | Example | In | Site |
|---|---|---|---|---|
| ordset 0.1.0 | 85 | `ordset.core.Bound[DefaultOrder.this.E] from scala.Any` | `ordset.core.ExtendedBound$.DefaultOrder.compare` | [`Bound.scala:760`](https://github.com/earogov/ordset/blob/v0.1.0/ordset/src/ordset/core/Bound.scala#L760) |
| scala3-compiler 3.3.6 | 74 | `dotty.tools.dotc.ast.tpd.TypeApply from scala.Any` | `dotty.tools.backend.jvm.BCodeBodyBuilder.PlainBodyBuilder.genApply` | `compiler/src/dotty/tools/backend/jvm/BCodeBodyBuilder.scala:757` |
| util-core 24.2.0 | 70 | `com.twitter.util.Promise.Transforming[Promise.this.A] from scala.Any` | `com.twitter.util.Promise._$theState` | [`Promise.scala:493`](https://github.com/twitter/util/blob/util-24.2.0/util-core/src/main/scala/com/twitter/util/Promise.scala#L493) |
| cron4s-core 0.8.2 | 59 | `cron4s.expr.BetweenNode[F] from cron4s.expr.RawEnumerableNode[F]` | `cron4s.expr.EnumerableNodeInstances._$$anon.implies` | [`WrapperInstances.scala:100`](https://github.com/alonsodomin/cron4s/blob/v0.8.2/modules/core/shared/src/main/scala-3/cron4s/expr/WrapperInstances.scala#L100) |
| kse3-basics 0.6.2 | 52 | `kse.basics.Mu.T[A] from M` | `kse.basics.Datum$package$.apply` | `/home/kerrr/Code/scala/kse3/basics/src/Datum.scala:248` |
| scalikejdbc-orm 4.3.5 | 45 | `scalikejdbc.orm.associations.HasManyExtractor[AssociationsFeature.this.Entity] from scala.Any` | `scalikejdbc.orm.associations.AssociationsFeature._$$8` | [`AssociationsFeature.scala:1004`](https://github.com/scalikejdbc/scalikejdbc/blob/4.3.5/scalikejdbc-orm/src/main/scala/scalikejdbc/orm/associations/AssociationsFeature.scala#L1004) |
| zio 2.1.26 | 35 | `java.util.concurrent.CompletionStage[A] from java.util.concurrent.Future[A]` | `zio.interop.javaz$._$$anonfun` | [`javaz.scala:95`](https://github.com/zio/zio/blob/v2.1.26/core/jvm-native/src/main/scala/zio/interop/javaz.scala#L95) |
| dfhdl-core 0.20.0 | 33 | `dfhdl.core.DFVal$package.DFValAny from OT` | `dfhdl.core.DFBoolOrBit$package$.DFBoolOrBit$.Val$.Ops$._$onTrueIsDFVal` | [`DFBoolOrBit.scala:204`](https://github.com/dfianthdl/dfhdl/blob/v0.20.0/core/src/main/scala/dfhdl/core/DFBoolOrBit.scala#L204) |
| libretto-core 0.3.10 | 22 | `libretto.scaletto.impl.-⚬[A, B] from libretto.scaletto.impl.FreeScaletto.PartialFun[A, B]` | `libretto.scaletto.impl.FreeScaletto$.total` | [`FreeScaletto.scala:416`](https://github.com/tomasmikula/libretto/blob/main/core/src/main/scala/libretto/scaletto/impl/FreeScaletto.scala#L416) |
| kinetic-merge 1.15.0 | 21 | `com.sageserpent.kineticmerge.core.SectionedCode[os.Path, com.sageserpent.kineticmerge.core.Token] from scala.Any` | `com.sageserpent.kineticmerge.Main$.InWorkingDirectory._$$anonfun` | [`Main.scala:1795`](https://github.com/sageserpent-open/kineticmerge/blob/v1.15.0/src/main/scala/com/sageserpent/kineticmerge/Main.scala#L1795) |
| qdrant4s 0.1.0 | 19 | `scala.Option[io.qdrant.client.core.Helpers$package.Primitive] from T` | `io.qdrant.client.core.HeaderSerializable$.serialize` | [`Helpers.scala:193`](https://github.com/lbialy/qdrant4s/blob/v0.1.0/generated/src/main/scala/io/qdrant/client/core/Helpers.scala#L193) |
| scalqa 1.0 | 19 | `scalqa.lang.boolean.g.Opt.TYPE.DEF[A] from scalqa.lang.Any.Opt[A]` | `scalqa.lang.any.z.opt$.Ops$.SOME` | [`opt.scala:34`](https://github.com/scalqa/scalqa/blob/v1.0/project/release/scalqa/src/scalqa/lang/any/z/opt.scala#L34) |

**`isInstanceOf` with type arguments** (erased at runtime). **32 sites in 15 libs**.

| Lib | Sites | Example | In | Site |
|---|---|---|---|---|
| langoustine-lsp 0.1.0 | 7 | `scala.collection.immutable.Vector[langoustine.lsp.aliases.DeclarationLink$package.DeclarationLink]` | `langoustine.lsp.codecs.requests_textDocument_declaration._$$anonfun` | [`codecs.scala:373`](https://github.com/neandertech/langoustine/blob/v0.1.0/modules/lsp/src/main/scala/generated/codecs.scala#L373) |
| scalismo-ui 1.0-RC1 | 6 | `PointToPointTransformation[scalismo.geometry._3D]` | `scalismo.ui.api.TransformationView$.FindInSceneGenericTransformation$$.createView` | [`Views.scala:789`](https://github.com/unibas-gravis/scalismo/blob/v1.0-RC1/src/main/scala/scalismo/ui/api/Views.scala#L789) |
| scala3-compiler 3.3.6 | 4 | `dotty.tools.dotc.ast.untpd.ValDef` | `dotty.tools.dotc.ast.Positioned._$check` | `compiler/src/dotty/tools/dotc/ast/Positioned.scala:187` |
| hearth-cross-quotes 0.4.1 | 3 | `dotty.tools.dotc.ast.tpd.Ident` | `hearth.cq.CrossQuotesPhase._$$anon.CtxBoundsTypeTree$.unapply` | [`CrossQuotesPlugin.scala:324`](https://github.com/kubuszok/hearth/blob/0.4.1/hearth-cross-quotes/src/main/scala-3/hearth/cq/CrossQuotesPlugin.scala#L324) |
| kyo-prelude 1.0.0-RC5 | 2 | `kyo.Batch.internal.Pending[A, S]` | `kyo.Batch$._$_$$anonfun` | [`Batch.scala:179`](https://github.com/getkyo/kyo/blob/v1.0.0-RC5/kyo-prelude/shared/src/main/scala/kyo/Batch.scala#L179) |
| algebra 2.13.0 | 1 | `algebra.ring.MultiplicativeCommutativeSemigroup[A]` | `algebra.ring.MultiplicativeSemigroupFunctions.isMultiplicativeCommutative` | [`Multiplicative.scala:133`](https://github.com/typelevel/cats/blob/v2.13.0/algebra-core/src/main/scala/algebra/ring/Multiplicative.scala#L133) |
| quack-on-demand 0.4.0 | 1 | `algebra.ring.MultiplicativeCommutativeSemigroup[A]` | `algebra.ring.MultiplicativeSemigroupFunctions.isMultiplicativeCommutative` | [`Multiplicative.scala:133`](https://github.com/starlake-ai/quack-on-demand/blob/v0.4.0/algebra-core/src/main/scala/algebra/ring/Multiplicative.scala#L133) |
| dmaog 0.1.5 | 1 | `java.util.List[scala.AnyRef]` | `com.herminiogarcia.dmaog.dataAccess.DataAccess._$_$_$values` | [`DataAccess.scala:295`](https://github.com/herminiogg/dmaog/blob/v0.1.5/src/main/scala/com/herminiogarcia/dmaog/dataAccess/DataAccess.scala#L295) |
| slick-testkit 4.0.0-RC1 | 1 | `slick.ast.Comprehension.Base` | `com.typesafe.slick.testkit.util.GenericTest._$_$$anonfun` | [`Testkit.scala:174`](https://github.com/slick/slick/blob/v4.0.0-RC1/slick-testkit/src/main/scala/com/typesafe/slick/testkit/util/Testkit.scala#L174) |
| squiggly 0.2.3 | 1 | `scala.collection.immutable.Seq[scala.Any]` | `io.github.edadma.squiggly.TemplateBuiltin$._$_$$anonfun` | [`TemplateBuiltin.scala:111`](https://github.com/edadma/squiggly/blob/v0.2.3/shared/src/main/scala/io/github/edadma/squiggly/TemplateBuiltin.scala#L111) |
| db-async-common 0.5.0-M1 | 1 | `scala.collection.immutable.Seq[scala.Any]` | `com.github.mauricio.async.db.util.Metrics$._$$anonfun` | [`Metrics.scala:180`](https://github.com/dripower/postgresql-async/blob/v0.5.0-M1/db-async-common/src/main/scala/com/github/mauricio/async/db/util/Metrics.scala#L180) |
| daffodil-core 4.2.0 | 1 | `org.apache.daffodil.runtime1.infoset.DataValue[scala.AnyRef, scala.AnyRef]` | `org.apache.daffodil.runtime1.infoset.DataValue$.assertValueIsNotDataValue` | [`DataValue.scala:240`](https://github.com/apache/daffodil/blob/v4.2.0/daffodil-core/src/main/scala/org/apache/daffodil/runtime1/infoset/DataValue.scala#L240) |

`Nothing` is inferred as a type argument at 102,368 sites; almost all are benign covariant uses (`scala.util.Right$.apply`, `scala.util.Left$.apply`, `scala.collection.SeqFactory$.Delegate.empty`, `scala.util.Failure$.apply`, `zio.ZIO.flatMap`, `scala.collection.IterableFactory.apply`), so the `findings` rows of kind `inferred-nothing` are only a starting point.

**Cycles between objects' initialisers.** Object `A`'s initialiser touches `B` and `B`'s touches `A`: whichever is initialised second sees the other half-built, and two threads initialising them concurrently can deadlock on the class-init locks.

41 two-object cycles (references to constants, which don't trigger initialisation, are included; check before acting):

| Lib | Object A | Object B | A → B | B → A |
|---|---|---|---|---|
| hl7 0.14.17 | `com.babylonhealth.lit.hl7.model.SubstanceSpecification$` | `com.babylonhealth.lit.hl7.model.SubstanceSpecification$.Structure$` | [`SubstanceSpecification.scala:1163`](https://github.com/babylonhealth/lit-fhir/blob/g0.14.17/hl7/src/main/scala/com/babylonhealth/lit/hl7/model/SubstanceSpecification.scala#L1163) | [`SubstanceSpecification.scala:332`](https://github.com/babylonhealth/lit-fhir/blob/g0.14.17/hl7/src/main/scala/com/babylonhealth/lit/hl7/model/SubstanceSpecification.scala#L332) |
| smithy4s-compliance-tests 0.19.10 | `smithy.test.TestExpectation$` | `smithy.test.TestExpectation$.SuccessCase$` | `modules/compliance-tests/target/jvm-3/src_managed/main/smithy/test/TestExpectation.scala:73` | `modules/compliance-tests/target/jvm-3/src_managed/main/smithy/test/TestExpectation.scala:45` |
| sjson-new-core 0.10.3 | `sjsonnew.LList$` | `sjsonnew.package$` | [`LList.scala:30`](https://github.com/eed3si9n/sjson-new/blob/v0.10.3/core/src/main/scala/sjsonnew/LList.scala#L30) | [`package.scala:27`](https://github.com/eed3si9n/sjson-new/blob/v0.10.3/core/src/main/scala/sjsonnew/package.scala#L27) |
| fm-common 1.0.1 | `fm.common.IPSet$` | `fm.common.IPSetImmutable$` | [`IPSet.scala:24`](https://github.com/tpunder/fm-common/blob/v1.0.1/fm-common-core/jvm/src/main/scala/fm/common/IPSet.scala#L24) | [`IPSet.scala:125`](https://github.com/tpunder/fm-common/blob/v1.0.1/fm-common-core/jvm/src/main/scala/fm/common/IPSet.scala#L125) |
| calev-core 0.7.4 | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Day$` | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Month$` | [`DefaultTrigger.scala:170`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L170) | [`DefaultTrigger.scala:175`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L175) |
| calev-core 0.7.4 | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Day$` | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Hour$` | [`DefaultTrigger.scala:171`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L171) | [`DefaultTrigger.scala:166`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L166) |
| calev-core 0.7.4 | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Hour$` | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Min$` | [`DefaultTrigger.scala:167`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L167) | [`DefaultTrigger.scala:162`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L162) |
| calev-core 0.7.4 | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Min$` | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Sec$` | [`DefaultTrigger.scala:163`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L163) | [`DefaultTrigger.scala:158`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L158) |
| calev-core 0.7.4 | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Month$` | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Year$` | [`DefaultTrigger.scala:174`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L174) | [`DefaultTrigger.scala:179`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L179) |
| calev-core 0.7.4 | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Sec$` | `com.github.eikek.calev.internal.DefaultTrigger$.DateTime$.Pos$.Year$` | [`DefaultTrigger.scala:159`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L159) | [`DefaultTrigger.scala:178`](https://github.com/eikek/calev/blob/v0.7.4/modules/core/src/main/scala/com/github/eikek/calev/internal/DefaultTrigger.scala#L178) |
| msgpack4z-core 0.6.2 | `msgpack4z.CodecInstances$` | `msgpack4z.LongArrayCodecImpl$` | [`CodecInstances.scala:24`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/CodecInstances.scala#L24) | [`AnyValArrayCodec.scala:229`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/AnyValArrayCodec.scala#L229) |
| msgpack4z-core 0.6.2 | `msgpack4z.CodecInstances$` | `msgpack4z.DoubleArrayCodecImpl$` | [`CodecInstances.scala:26`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/CodecInstances.scala#L26) | [`AnyValArrayCodec.scala:247`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/AnyValArrayCodec.scala#L247) |
| msgpack4z-core 0.6.2 | `msgpack4z.CodecInstances$` | `msgpack4z.IntArrayCodecImpl$` | [`CodecInstances.scala:23`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/CodecInstances.scala#L23) | [`AnyValArrayCodec.scala:220`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/AnyValArrayCodec.scala#L220) |
| msgpack4z-core 0.6.2 | `msgpack4z.BooleanArrayCodecImpl$` | `msgpack4z.CodecInstances$` | [`AnyValArrayCodec.scala:193`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/AnyValArrayCodec.scala#L193) | [`CodecInstances.scala:20`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/CodecInstances.scala#L20) |
| msgpack4z-core 0.6.2 | `msgpack4z.ByteArrayCodecImpl$` | `msgpack4z.CodecInstances$` | [`AnyValArrayCodec.scala:202`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/AnyValArrayCodec.scala#L202) | [`CodecInstances.scala:21`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/CodecInstances.scala#L21) |
| msgpack4z-core 0.6.2 | `msgpack4z.CodecInstances$` | `msgpack4z.FloatArrayCodecImpl$` | [`CodecInstances.scala:25`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/CodecInstances.scala#L25) | [`AnyValArrayCodec.scala:238`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/AnyValArrayCodec.scala#L238) |
| msgpack4z-core 0.6.2 | `msgpack4z.CodecInstances$` | `msgpack4z.ShortArrayCodecImpl$` | [`CodecInstances.scala:22`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/CodecInstances.scala#L22) | [`AnyValArrayCodec.scala:211`](https://github.com/msgpack4z/msgpack4z-core/blob/v0.6.2/src/main/scala/msgpack4z/AnyValArrayCodec.scala#L211) |
| failable 0.0.6 | `com.mchange.sc.v3.failable.Failable$` | `com.mchange.sc.v3.failable.Failed$` | [`Failable.scala:9`](https://github.com/swaldman/failable/blob/v0.0.6/core/src/main/scala/com/mchange/sc/v3/failable/Failable.scala#L9) | [`Failable.scala:150`](https://github.com/swaldman/failable/blob/v0.0.6/core/src/main/scala/com/mchange/sc/v3/failable/Failable.scala#L150) |
| scalaveusz 0.8.1 | `de.dreambeam.veusz.package$.GraphItems$` | `de.dreambeam.veusz.package$.PageItems$` | [`package.scala:112`](https://github.com/stk-code/scalaveusz/blob/v0.8.1/src/main/scala/de/dreambeam/package.scala#L112) | [`package.scala:79`](https://github.com/stk-code/scalaveusz/blob/v0.8.1/src/main/scala/de/dreambeam/package.scala#L79) |
| scalaveusz 0.8.1 | `de.dreambeam.veusz.package$.GridItems$` | `de.dreambeam.veusz.package$.PageItems$` | [`package.scala:105`](https://github.com/stk-code/scalaveusz/blob/v0.8.1/src/main/scala/de/dreambeam/package.scala#L105) | [`package.scala:77`](https://github.com/stk-code/scalaveusz/blob/v0.8.1/src/main/scala/de/dreambeam/package.scala#L77) |
| lucuma-core 0.217.0 | `lucuma.core.model.sequence.gnirs.GnirsAcquisitionMode$` | `lucuma.core.model.sequence.gnirs.GnirsAcquisitionMode$.Faint$` | [`GnirsAcquisitionMode.scala:52`](https://github.com/gemini-hlsw/lucuma-core/blob/v0.217.0/modules/core/shared/src/main/scala/lucuma/core/model/sequence/gnirs/GnirsAcquisitionMode.scala#L52) | [`GnirsAcquisitionMode.scala:37`](https://github.com/gemini-hlsw/lucuma-core/blob/v0.217.0/modules/core/shared/src/main/scala/lucuma/core/model/sequence/gnirs/GnirsAcquisitionMode.scala#L37) |
| tranzactio-core 6.0.0 | `io.github.gaelrenoux.tranzactio.ErrorStrategies$` | `io.github.gaelrenoux.tranzactio.ErrorStrategiesParent$` | [`errorStrategies.scala:84`](https://github.com/gaelrenoux/tranzactio/blob/v6.0.0/core/src/main/scala/io/github/gaelrenoux/tranzactio/errorStrategies.scala#L84) | [`errorStrategies.scala:21`](https://github.com/gaelrenoux/tranzactio/blob/v6.0.0/core/src/main/scala/io/github/gaelrenoux/tranzactio/errorStrategies.scala#L21) |
| oxygen-json 0.6.7 | `oxygen.json.Json$` | `oxygen.json.Json$.Obj$` | [`Json.scala:244`](https://github.com/kalin-rudnicki/oxygen/blob/0.6.7/modules/general/json/src/main/scala/oxygen/json/Json.scala#L244) | [`Json.scala:203`](https://github.com/kalin-rudnicki/oxygen/blob/0.6.7/modules/general/json/src/main/scala/oxygen/json/Json.scala#L203) |
| binance-scala-client 1.6.1 | `io.github.paoloboni.binance.fapi.response.Filter$` | `io.github.paoloboni.binance.fapi.response.FilterCodecs$` | [`ExchangeInformation.scala:49`](https://github.com/paoloboni/binance-scala-client/blob/v1.6.1/src/main/scala/io/github/paoloboni/binance/fapi/response/ExchangeInformation.scala#L49) | [`FilterCodecs.scala:30`](https://github.com/paoloboni/binance-scala-client/blob/v1.6.1/src/main/scala-3/io/github/paoloboni/binance/fapi/response/FilterCodecs.scala#L30) |
| binance-scala-client 1.6.1 | `io.github.paoloboni.binance.spot.response.Filter$` | `io.github.paoloboni.binance.spot.response.FilterCodecs$` | [`ExchangeInformation.scala:54`](https://github.com/paoloboni/binance-scala-client/blob/v1.6.1/src/main/scala/io/github/paoloboni/binance/spot/response/ExchangeInformation.scala#L54) | [`FilterCodecs.scala:29`](https://github.com/paoloboni/binance-scala-client/blob/v1.6.1/src/main/scala-3/io/github/paoloboni/binance/spot/response/FilterCodecs.scala#L29) |
| kamon-core 2.8.1 | `kamon.context.Context$` | `kamon.trace.Span$` | [`Context.scala:187`](https://github.com/kamon-io/kamon/blob/v2.8.1/core/kamon-core/src/main/scala/kamon/context/Context.scala#L187) | [`Span.scala:235`](https://github.com/kamon-io/kamon/blob/v2.8.1/core/kamon-core/src/main/scala/kamon/trace/Span.scala#L235) |
| between 0.6.0 | `nl.gn0s1s.between.m$` | `nl.gn0s1s.between.mi$` | [`Relation.scala:15`](https://github.com/philippus/between/blob/v0.6.0/src/main/scala/nl/gn0s1s/between/Relation.scala#L15) | [`Relation.scala:67`](https://github.com/philippus/between/blob/v0.6.0/src/main/scala/nl/gn0s1s/between/Relation.scala#L67) |
| between 0.6.0 | `nl.gn0s1s.between.o$` | `nl.gn0s1s.between.oi$` | [`Relation.scala:20`](https://github.com/philippus/between/blob/v0.6.0/src/main/scala/nl/gn0s1s/between/Relation.scala#L20) | [`Relation.scala:62`](https://github.com/philippus/between/blob/v0.6.0/src/main/scala/nl/gn0s1s/between/Relation.scala#L62) |
| between 0.6.0 | `nl.gn0s1s.between.f$` | `nl.gn0s1s.between.fi$` | [`Relation.scala:57`](https://github.com/philippus/between/blob/v0.6.0/src/main/scala/nl/gn0s1s/between/Relation.scala#L57) | [`Relation.scala:25`](https://github.com/philippus/between/blob/v0.6.0/src/main/scala/nl/gn0s1s/between/Relation.scala#L25) |
| between 0.6.0 | `nl.gn0s1s.between.d$` | `nl.gn0s1s.between.di$` | [`Relation.scala:52`](https://github.com/philippus/between/blob/v0.6.0/src/main/scala/nl/gn0s1s/between/Relation.scala#L52) | [`Relation.scala:30`](https://github.com/philippus/between/blob/v0.6.0/src/main/scala/nl/gn0s1s/between/Relation.scala#L30) |
| between 0.6.0 | `nl.gn0s1s.between.s$` | `nl.gn0s1s.between.si$` | [`Relation.scala:35`](https://github.com/philippus/between/blob/v0.6.0/src/main/scala/nl/gn0s1s/between/Relation.scala#L35) | [`Relation.scala:47`](https://github.com/philippus/between/blob/v0.6.0/src/main/scala/nl/gn0s1s/between/Relation.scala#L47) |
| rezilience-config 0.10.5 | `nl.vroste.rezilience.config.TrippingStrategy$` | `nl.vroste.rezilience.config.TrippingStrategy$.FailureCount$` | [`CircuitBreakerConfig.scala:36`](https://github.com/svroonland/rezilience/blob/v0.10.5/rezilience-config/src/main/scala/nl/vroste/rezilience/config/CircuitBreakerConfig.scala#L36) | [`CircuitBreakerConfig.scala:16`](https://github.com/svroonland/rezilience/blob/v0.10.5/rezilience-config/src/main/scala/nl/vroste/rezilience/config/CircuitBreakerConfig.scala#L16) |
| rezilience-config 0.10.5 | `nl.vroste.rezilience.config.TrippingStrategy$` | `nl.vroste.rezilience.config.TrippingStrategy$.FailureRate$` | [`CircuitBreakerConfig.scala:36`](https://github.com/svroonland/rezilience/blob/v0.10.5/rezilience-config/src/main/scala/nl/vroste/rezilience/config/CircuitBreakerConfig.scala#L36) | [`CircuitBreakerConfig.scala:31`](https://github.com/svroonland/rezilience/blob/v0.10.5/rezilience-config/src/main/scala/nl/vroste/rezilience/config/CircuitBreakerConfig.scala#L31) |
| fallatol-ollama 0.3.1 | `fallatol.ollama.client.EmbedRequest$` | `fallatol.ollama.client.EmbedRequestCodec$` | [`EmbedRequest.scala:33`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala/fallatol/ollama/client/EmbedRequest.scala#L33) | [`EmbedRequestCodec.scala:30`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala-3/fallatol/ollama/client/EmbedRequestCodec.scala#L30) |
| fallatol-ollama 0.3.1 | `fallatol.ollama.client.ChatRequest$` | `fallatol.ollama.client.ChatRequestCodec$` | [`ChatRequest.scala:36`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala/fallatol/ollama/client/ChatRequest.scala#L36) | [`ChatRequestCodec.scala:30`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala-3/fallatol/ollama/client/ChatRequestCodec.scala#L30) |
| fallatol-ollama 0.3.1 | `fallatol.ollama.ModelInfo$` | `fallatol.ollama.ModelInfoCodec$` | [`ModelInfo.scala:49`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala/fallatol/ollama/ModelInfo.scala#L49) | [`ModelInfoCodec.scala:30`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala-3/fallatol/ollama/ModelInfoCodec.scala#L30) |
| fallatol-ollama 0.3.1 | `fallatol.ollama.client.ChatResponse$` | `fallatol.ollama.client.ChatResponseCodec$` | [`ChatResponse.scala:45`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala/fallatol/ollama/client/ChatResponse.scala#L45) | [`ChatResponseCodec.scala:30`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala-3/fallatol/ollama/client/ChatResponseCodec.scala#L30) |
| fallatol-ollama 0.3.1 | `fallatol.ollama.client.EmbedResponse$` | `fallatol.ollama.client.EmbedResponseCodec$` | [`EmbedResponse.scala:36`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala/fallatol/ollama/client/EmbedResponse.scala#L36) | [`EmbedResponseCodec.scala:30`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala-3/fallatol/ollama/client/EmbedResponseCodec.scala#L30) |
| fallatol-ollama 0.3.1 | `fallatol.ollama.ModelDetails$` | `fallatol.ollama.ModelDetailsCodec$` | [`ModelInfo.scala:37`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala/fallatol/ollama/ModelInfo.scala#L37) | [`ModelDetailsCodec.scala:30`](https://github.com/kapunga/fallatol/blob/v0.3.1/ollama/src/main/scala-3/fallatol/ollama/ModelDetailsCodec.scala#L30) |
| scodec-core 2.3.3 | `scodec.codecs.UuidCodec$` | `scodec.codecs.codecs$package$` | [`UuidCodec.scala:41`](https://github.com/scodec/scodec/blob/v2.3.3/shared/src/main/scala/scodec/codecs/UuidCodec.scala#L41) | [`codecs.scala:568`](https://github.com/scodec/scodec/blob/v2.3.3/shared/src/main/scala/scodec/codecs/codecs.scala#L568) |

**Blocking, locking and reflection** (references from libs; each is legitimate somewhere, the counts say how widespread):

| API | Libs | % libs | Uses |
|---|---|---|---|
| `eq`/`ne` (reference equality, mostly null checks) | 3442 | 56% | 104,352 |
| `asInstanceOf` | 2184 | 35% | 97,093 |
| `.head` on collections | 1287 | 21% | 10,682 |
| `Option.get` | 1145 | 19% | 24,098 |
| `@volatile` / `AtomicReference` | 539 | 9% | 16,291 |
| `synchronized` | 403 | 7% | 2,700 |
| `Await.result` / `Await.ready` | 216 | 3% | 490 |
| `Class.forName` | 207 | 3% | 497 |
| `Thread.sleep` | 169 | 3% | 393 |
| `setAccessible` | 104 | 2% | 197 |
| `System.exit` | 90 | 1% | 186 |
| `scala.util.DynamicVariable` | 56 | 1% | 553 |
| `sun.misc.Unsafe` | 11 | 0% | 171 |

**Implicit conversions applied by the compiler**, the evidence for `into` and for restricting conversions. Most applied conversions:

| Conversion | Module | Libs | Uses |
|---|---|---|---|
| `scala.Predef$.augmentString(java.lang.String)` | `org.scala-lang:scala-library` | 2,520 | 30,658 |
| `scala.Predef$.refArrayOps(1,java.lang.Object[])` | `org.scala-lang:scala-library` | 1,313 | 10,660 |
| `scala.LowPriorityImplicits.wrapRefArray(1,java.lang.Object[])` | `org.scala-lang:scala-library` | 1,086 | 3,457 |
| `cats.Functor$.ToFunctorOps.toFunctorOps(2,java.lang.Object,cats.Functor)` | `org.typelevel:cats-core_3` | 784 | 9,867 |
| `cats.FlatMap$.ToFlatMapOps.toFlatMapOps(2,java.lang.Object,cats.FlatMap)` | `org.typelevel:cats-core_3` | 581 | 7,474 |
| `scala.concurrent.duration.package$.DurationInt(scala.Int)` | `org.scala-lang:scala-library` | 541 | 1,861 |
| `scala.collection.convert.AsScalaExtensions.ListHasAsScala(1,java.util.List)` | `org.scala-lang:scala-library` | 528 | 2,759 |
| `scala.Int$.int2long(scala.Int)` | `org.scala-lang:scala-library` | 489 | 2,593 |
| `scala.Option$.option2Iterable(1,scala.Option)` | `org.scala-lang:scala-library` | 481 | 2,679 |
| `scala.collection.convert.AsJavaExtensions.SeqHasAsJava(1,scala.collection.Seq)` | `org.scala-lang:scala-library` | 362 | 1,457 |
| `scala.Predef$.byteArrayOps(scala.Byte[])` | `org.scala-lang:scala-library` | 335 | 1,247 |
| `cats.syntax.ApplicativeSyntax.catsSyntaxApplicativeId(1,java.lang.Object)` | `org.typelevel:cats-core_3` | 334 | 1,627 |
| `cats.Traverse$.ToTraverseOps.toTraverseOps(2,java.lang.Object,cats.Traverse)` | `org.typelevel:cats-core_3` | 329 | 1,159 |
| `scala.collection.convert.AsScalaExtensions.MapHasAsScala(2,java.util.Map)` | `org.scala-lang:scala-library` | 316 | 793 |
| `cats.syntax.EitherSyntax.catsSyntaxEither(2,scala.util.Either)` | `org.typelevel:cats-core_3` | 299 | 1,226 |
| `scala.Predef$.int2Integer(scala.Int)` | `org.scala-lang:scala-library` | 282 | 1,107 |
| `cats.syntax.OptionSyntax.catsSyntaxOptionId(1,java.lang.Object)` | `org.typelevel:cats-core_3` | 277 | 1,943 |
| `scala.collection.convert.AsJavaExtensions.MapHasAsJava(2,scala.collection.Map)` | `org.scala-lang:scala-library` | 274 | 948 |
| `cats.syntax.ApplicativeErrorSyntax.catsSyntaxApplicativeError(3,java.lang.Object,cats.ApplicativeError)` | `org.typelevel:cats-core_3` | 273 | 869 |
| `cats.Foldable$.ToFoldableOps.toFoldableOps(2,java.lang.Object,cats.Foldable)` | `org.typelevel:cats-core_3` | 265 | 936 |
| `scala.Predef$.genericArrayOps(1,java.lang.Object)` | `org.scala-lang:scala-library` | 258 | 1,100 |
| `scala.collection.convert.AsScalaExtensions.SetHasAsScala(1,java.util.Set)` | `org.scala-lang:scala-library` | 235 | 660 |
| `io.circe.syntax.package$.EncoderOps(1,java.lang.Object)` | `io.circe:circe-core_3` | 232 | 7,116 |
| `scala.LowPriorityImplicits.wrapString(java.lang.String)` | `org.scala-lang:scala-library` | 226 | 923 |
| `cats.syntax.FlatMapSyntax.catsSyntaxFlatMapOps(2,java.lang.Object,cats.FlatMap)` | `org.typelevel:cats-core_3` | 224 | 1,145 |
| `cats.syntax.EitherSyntax.catsSyntaxEitherId(1,java.lang.Object)` | `org.typelevel:cats-core_3` | 211 | 2,117 |
| `scala.Predef$.Integer2int(java.lang.Integer)` | `org.scala-lang:scala-library` | 199 | 663 |
| `scala.Predef$.double2Double(scala.Double)` | `org.scala-lang:scala-library` | 195 | 949 |
| `scala.collection.convert.AsScalaExtensions.IteratorHasAsScala(1,java.util.Iterator)` | `org.scala-lang:scala-library` | 188 | 460 |
| `scala.collection.IterableFactory$.toFactory(2,scala.collection.IterableFactory)` | `org.scala-lang:scala-library` | 186 | 618 |

Libs that define implicit conversions: 1487 with Scala 2 `implicit def`, 170 reference `scala.Conversion` (most to define a `given Conversion`).

**`var` fields in case classes** (equality and hashing of a mutable value):

1221 fields:

| Lib | Fields | Example | Site |
|---|---|---|---|
| scalaveusz 0.8.1 | 738 | `de.dreambeam.veusz.components.Colorbar.axisPosition` | [`Colorbar.scala:10`](https://github.com/stk-code/scalaveusz/blob/v0.8.1/src/main/scala/de/dreambeam/veusz/components/Colorbar.scala#L10) |
| sjsonnet 0.7.0 | 47 | `sjsonnet.Expr$.$.pos` | `/home/runner/work/secure-public-registry-releases-eng/secure-public-registry-releases-eng/sjsonnet/src/sjsonnet/Expr.scala:102` |
| scalismo 1.0-RC1 | 29 | `scalismo.mesh.boundingSpheres.BC.a` | [`BSDistance.scala:114`](https://github.com/unibas-gravis/scalismo/blob/v1.0-RC1/src/main/scala/scalismo/mesh/boundingSpheres/BSDistance.scala#L114) |
| three-address-code 7.0.0 | 29 | `org.opalj.tac.CaughtException.throwingStmts` | [`Stmt.scala:1132`](https://github.com/opalj/opal/blob/7.0.0/OPAL/tac/src/main/scala/org/opalj/tac/Stmt.scala#L1132) |
| uni 0.19.3 | 21 | `uni.data.TprfRunner$.Combo.a` | [`TprfRunner.scala:292`](https://github.com/philwalk/uni/blob/v0.19.3/src/main/scala/apps/TprfRunner.scala#L292) |
| scala3-compiler 3.3.6 | 17 | `dotty.tools.dotc.ast.Trees$.DefDef.preRhs` | `compiler/src/dotty/tools/dotc/ast/Trees.scala:902` |
| kamon-core 2.8.1 | 17 | `kamon.context.Context$.Entry$.Mutable.key` | [`Context.scala:291`](https://github.com/kamon-io/kamon/blob/v2.8.1/core/kamon-core/src/main/scala/kamon/context/Context.scala#L291) |
| kyo-tasty 1.0.0-RC5 | 17 | `kyo.internal.tasty.symbol.LoadingSymbol$.Materialising.annotations` | [`LoadingSymbol.scala:43`](https://github.com/getkyo/kyo/blob/v1.0.0-RC5/kyo-tasty/shared/src/main/scala/kyo/internal/tasty/symbol/LoadingSymbol.scala#L43) |
| tui 0.0.10 | 15 | `tui.Buffer.area` | `/home/runner/work/tui-scala/tui-scala/tui/src/scala/tui/Buffer.scala:20` |
| scrypto 3.1.0 | 14 | `scorex.crypto.authds.legacy.avltree.Leaf._nextLeafKey` | [`Node.scala:124`](https://github.com/input-output-hk/scrypto/blob/v3.1.0/shared/src/main/scala/scorex/crypto/authds/legacy/avltree/Node.scala#L124) |
| cassowary 0.0.10 | 11 | `tui.cassowary.EditInfo.constant` | `/home/runner/work/tui-scala/tui-scala/cassowary/src/scala/tui/cassowary/lib.scala:251` |
| processors 10.0.2 | 8 | `org.clulab.struct.BooleanTrieNode.children` | [`BooleanHashTrie.scala:98`](https://github.com/clulab/processors/blob/v10.0.2/library/src/main/scala/org/clulab/struct/BooleanHashTrie.scala#L98) |
| unifile 0.4.3 | 8 | `vastblue.Unexpand.indices` | [`Unexpand.scala:57`](https://github.com/philwalk/unifile/blob/v0.4.3/src/main/scala/vastblue/Unexpand.scala#L57) |
| common 7.0.0 | 8 | `org.opalj.collection.immutable.Int2ListNode.h` | [`Int2List.scala:102`](https://github.com/opalj/opal/blob/7.0.0/OPAL/common/src/main/scala/org/opalj/collection/immutable/Int2List.scala#L102) |
| kyo-schema 1.0.0-RC5 | 8 | `kyo.internal.StructureValueReader.ObjectFrame.current` | [`StructureValueReader.scala:28`](https://github.com/getkyo/kyo/blob/v1.0.0-RC5/kyo-schema/shared/src/main/scala/kyo/internal/StructureValueReader.scala#L28) |

## 6. Tooling gaps

Jars whose TASTy doesn't load as a whole with the 3.10 TASTy Inspector and their dependencies' published classpath, and the files that fail on their own. Most are references to compile-time-only dependencies missing from the published POM; the rest are leads for TASTy reader bugs.

503 jars with at least one file that fails alone; the worst:

| Lib | Files failing | Of | Files |
|---|---|---|---|
| pekko-http-core 1.4.0 | 260 | 442 | org/apache/pekko/http/DefaultParsingErrorHandler.tasty, org/apache/pekko/http/Version.tasty, org/apache/pekko/http/impl/engine/HttpConnectionIdleTimeoutBidi.tas |
| akka-http-core 10.5.3 | 260 | 445 | akka/http/DefaultParsingErrorHandler.tasty, akka/http/Version.tasty, akka/http/impl/engine/HttpConnectionIdleTimeoutBidi.tasty, akka/http/impl/engine/client/Htt |
| kamon-bundle 2.8.1 | 248 | 340 | akka/actor/instrumentation/CellWrapper.tasty, akka/kamon/instrumentation/akka/instrumentations/akka_26/remote/internal/AkkaPduProtobufCodecConstructMessageMetho |
| dapr4s 1.0.0 | 179 | 179 | dapr4s/ActivityDef.tasty, dapr4s/ActivityName$package.tasty, dapr4s/ActorCapability.tasty, dapr4s/ActorContext.tasty, dapr4s/ActorDefinition.tasty, dapr4s/Actor |
| scalqa 1.0 | 136 | 1020 | scalqa/fx/Control.tasty, scalqa/fx/Scene.tasty, scalqa/fx/base/Action.tasty, scalqa/fx/base/Insets.tasty, scalqa/fx/base/JavaFx.tasty, scalqa/fx/base/Pos.tasty, |
| flink-scala-api-common-1 2.2.3 | 122 | 145 | org/apache/flink/streaming/util/typeutils/DefaultScalaProductFieldAccessorFactory.tasty, org/apache/flinkx/api/ClosureCleaner.tasty, org/apache/flinkx/api/Field |
| flink-scala-api-common-2 2.2.3 | 122 | 145 | org/apache/flink/streaming/util/typeutils/DefaultScalaProductFieldAccessorFactory.tasty, org/apache/flinkx/api/ClosureCleaner.tasty, org/apache/flinkx/api/Field |
| qdrant4s 0.1.0 | 108 | 512 | io/qdrant/client/core/JsonSupport.tasty, io/qdrant/client/model/AliasOperations.tasty, io/qdrant/client/model/AnyVariants.tasty, io/qdrant/client/model/BatchPay |
| play-omnidoc 2.9.0-RC2 | 105 | 1054 | akka/http/play/WebSocketHandler.tasty, org/scalatestplus/play/AllBrowsersPerSuite.tasty, org/scalatestplus/play/AllBrowsersPerTest.tasty, org/scalatestplus/play |
| scurry 1.0.0 | 89 | 101 | scurry/http/Authorization.tasty, scurry/http/Body.tasty, scurry/http/ClientSideHttpRequest.tasty, scurry/http/ClientSideHttpResponse.tasty, scurry/http/Headers. |
| helenus-core 1.2.0 | 83 | 92 | com/datastax/oss/driver/shaded/guava/common/reflect/ScalaTypeParameter.tasty, com/datastax/oss/driver/shaded/guava/common/reflect/ScalaTypeToken.tasty, net/nmon |
| akka-http 10.5.3 | 75 | 283 | akka/http/impl/settings/RoutingSettingsImpl.tasty, akka/http/impl/settings/ServerSentEventSettingsImpl.tasty, akka/http/javadsl/marshalling/sse/EventStreamMarsh |
| pekko-http 1.4.0 | 73 | 286 | org/apache/pekko/http/impl/settings/RoutingSettingsImpl.tasty, org/apache/pekko/http/impl/settings/ServerSentEventSettingsImpl.tasty, org/apache/pekko/http/java |
| mtags-shared 0.11.12 | 61 | 61 | scala/meta/internal/jdk/CollectionConverters$package.tasty, scala/meta/internal/metals/ClassfileElementPart.tasty, scala/meta/internal/metals/ClasspathElementPa |
| kamon-pekko 2.8.1 | 60 | 78 | kamon/instrumentation/pekko/instrumentations/ActorCellConstructorAdvice.tasty, kamon/instrumentation/pekko/instrumentations/ActorCellInfo.tasty, kamon/instrumen |
| kamon-akka 2.8.1 | 60 | 79 | akka/actor/instrumentation/CellWrapper.tasty, akka/kamon/instrumentation/akka/instrumentations/akka_26/remote/internal/AkkaPduProtobufCodecConstructMessageMetho |
| fxprof-format 0.0.2 | 53 | 140 | fxprof/BHRMarkerPayloadArgs.tasty, fxprof/BrowsertimeMarkerPayloadArgs.tasty, fxprof/CategoryArgs.tasty, fxprof/CauseBacktraceArgs.tasty, fxprof/CcMarkerTracing |
| fundamentals-bio 1.3.0-M3 | 47 | 172 | izumi/functional/bio/BlockingIOInstances.tasty, izumi/functional/bio/CatsConversions.tasty, izumi/functional/bio/CatsConversions1.tasty, izumi/functional/bio/Ca |
| play-redis 5.4.0 | 43 | 128 | play/api/cache/redis/CondensedReports.tasty, play/api/cache/redis/DetailedReports.tasty, play/api/cache/redis/GuiceProvider.tasty, play/api/cache/redis/GuicePro |
| scalatest-app 3.2.20 | 37 | 854 | org/scalatest/StreamlinedXml.tasty, org/scalatest/Suite.tasty, org/scalatest/events/AlertProvided.tasty, org/scalatest/events/DiscoveryCompleted.tasty, org/scal |
| zio-http-shaded 3.11.3 | 34 | 236 | zio/http/netty/AsyncBodyReader.tasty, zio/http/netty/ChannelFactories.tasty, zio/http/netty/EventLoopGroups.tasty, zio/http/netty/HybridContentLengthHandler.tas |
| flink-adt 0.6.1 | 32 | 39 | io/findify/flinkadt/api/LowPrioImplicits.tasty, io/findify/flinkadt/api/package.tasty, io/findify/flinkadt/api/serializer/ArraySerializer.tasty, io/findify/flin |
| fs2-nats 0.3.0 | 32 | 132 | fs2/nats/jetstream/protocol/AccountInfo.tasty, fs2/nats/jetstream/protocol/AccountLimits.tasty, fs2/nats/jetstream/protocol/ApiError.tasty, fs2/nats/jetstream/p |
| deadbolt-scala 3.0.0 | 28 | 53 | be/objectify/deadbolt/scala/ActionBuilders.tasty, be/objectify/deadbolt/scala/AuthenticatedRequest.tasty, be/objectify/deadbolt/scala/ConstraintLogic.tasty, be/ |
| ra3-core 0.3.0 | 26 | 199 | ra3/Column.tasty, ra3/Segment.tasty, ra3/StatisticCharSequence.tasty, ra3/StatisticDouble.tasty, ra3/StatisticInt.tasty, ra3/StatisticLong.tasty, ra3/Table.tast |

## Appendix: the block-literal sweep as a query

The [block-literal sweep](../2026-10-scala3-block-val-literals/) is one query here:

```sql
select lib, full_name, file, line from defs where tpt_inferred = '1' and tpe_kind = 'literal' and rhs_kind = 'Block'
```

17 rows: `org.opalj.da.Disassembler$.Usage` (bytecode-disassembler 7.0.0), `org.opalj.br.analyses.cg.ClassExtensibilityKey$.DefaultClassExtensibilityAnalysis` (bytecode-representation 7.0.0), `org.opalj.br.reader.BytecodeOptimizer$.BytecodeOptimizerConfigKeyPrefix` (bytecode-representation 7.0.0), `org.opalj.br.reader.BytecodeOptimizer$.LogControlFlowSimplificationKey` (bytecode-representation 7.0.0), `org.opalj.br.reader.ClassFileBinding$.DeleteSynthesizedClassFilesAttributesConfigKey` (bytecode-representation 7.0.0), `org.opalj.br.reader.ClassFileReaderConfiguration$.ConfigKeyPrefix` (bytecode-representation 7.0.0), `org.opalj.br.reader.DynamicConstantRewriting$.DynamicConstantKeyPrefix` (bytecode-representation 7.0.0), `org.opalj.br.reader.InvokedynamicRewriting$.InvokedynamicKeyPrefix` (bytecode-representation 7.0.0), `org.opalj.br.reader.InvokedynamicRewriting$.InvokedynamicLogUnknownInvokeDynamicsConfigKey` (bytecode-representation 7.0.0), `org.opalj.br.reader.InvokedynamicRewriting$.InvokedynamicRewritingConfigKey` (bytecode-representation 7.0.0), `org.opalj.br.reader.InvokedynamicRewriting$.LambdaExpressionsLogRewritingsConfigKey` (bytecode-representation 7.0.0), `org.opalj.br.reader.InvokedynamicRewriting$.ObjectMethodsLogRewritingsConfigKey` (bytecode-representation 7.0.0), `org.opalj.br.reader.InvokedynamicRewriting$.StringConcatLogRewritingsConfigKey` (bytecode-representation 7.0.0), `org.opalj.fpcf.PropertyStore$.TraceSuppressedNotificationsKey` (static-analysis-infrastructure 7.0.0), `org.opalj.tac.fpcf.analyses.cg.reflection.ReflectionRelatedCallsAnalysis$.ConfigKey` (three-address-code 7.0.0), `org.opalj.tac.fpcf.analyses.fieldaccess.reflection.ReflectionRelatedFieldAccessesAnalysis$.ConfigKey` (three-address-code 7.0.0), `dotty.tools.backend.sjs.JSCodeGen.GenericGlobalObjectInformationMsg` (scala3-compiler 3.3.6).
