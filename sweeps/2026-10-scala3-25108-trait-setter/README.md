# Code in published libraries affected by scala/scala3#25108

Behind the "Affected code in published libraries" section of [retronym/scala3#81](https://github.com/retronym/scala3/pull/81).

**Question.** Under MegaPhase fusion, a class's implementation of a trait setter wrote the trait's initial value into the field of a val that overrides it (and threw `ClassCastException` if the override's erased type was narrower). The fix makes that setter do nothing, as in Scala 2. Which published code does this change, and does any of it behave differently?

**Answer.** About 140 published jars contain the affected sites in the table below. In all of them the override has the same erased type, so nothing was cast. No code reads the val in the window where the old compiler had left the trait's value in its field, so the change isn't observable in any of them.

## 1. Finding the sites: `from-tasty-probe/`

`probe.patch` adds a print to the fixed `Memoize`: `PROBE-25108` for every trait setter that the old rule made assign the trait's initial value to the overriding val's field. Those are exactly the sites the fix changes. Each is tagged `CCE` if the setter's parameter type doesn't conform to the field's type after erasure (where the old code threw `ClassCastException`), or `VALUE` otherwise.

`-from-tasty` runs Mixin and Memoize again on a published jar's TASTy, so the probe compiler can survey libraries without building them. `probe.py` resolves each coordinate in `libs.txt` with coursier and compiles the library's own `_3` jar from TASTy with its dependencies on the classpath. Some jars fail `-from-tasty` for reasons unrelated to this bug ([breakdown](from-tasty-probe/from-tasty-failures.md)); `probe_bisect.py` compiles those jars' `.tasty` files in chunks of 50, splits any chunk that fails until single failing files are left, and reports what the rest found.

```
cd from-tasty-probe
SCALA3=~/code/scala3 FIX=<fix commit> ./setup.sh
SCALA3=~/code/scala3 JOBS=6 python3 probe.py | tee result-whole-jars.txt
grep '^COMPILE-FAIL' result-whole-jars.txt | awk '{print $2}' > libs-failed.txt
SCALA3=~/code/scala3 JOBS=10 python3 probe_bisect.py | tee result-bisected-jars.txt
```

99 jars compiled whole and 37 were bisected; 726 of the bisected jars' 9,038 `.tasty` files couldn't be probed (mostly pekko-http and scaladoc), and 5 coordinates didn't resolve. The probe found these sites, all `VALUE`:

| Library | Class | Overrides | Type |
|---|---|---|---|
| scodec-bits | `Bases.Alphabets.Base64NoPad`, `Base64UrlNoPad` | `Base64Base.pad`, `Base64UrlBase.pad` | `Char` |
| Play 2.9, 3.1 | anonymous classes in `Formats` | `Formatter.format` | `Option` |
| Play | `Messages.MessagesParser` | `RegexParsers.whiteSpace` | `Regex` |
| zio | anonymous class in `DefaultJvmMetrics` | `ZIOAppDefault.bootstrap` | `ZLayer` |
| slick | anonymous subclass of `SimpleFunction` | `SimpleFunction.scalar` | `Boolean` |
| json4s | anonymous subclass of `DefaultFormats` | `DefaultFormats.typeHints` | `TypeHints` |
| scaladoc | `TemplateSourceLink`, `WebBasedSourceLink` | `SourceLink.path` | `Option` |

## 2. Can anything observe the old value? `reads-in-init/`

`ReadsInInit.java` (ASM) reads the published bytecode of every class that implements one of the trait setters above. It looks at the window in which the old compiler had left the trait's value in the overriding field: from the setter's call in the trait's `$init$`, through the rest of the initialiser that called that `$init$` (a constructor, or `<clinit>` for a top-level object, whose fields are static) and the constructors below it, up to the class's own store of the val. In that window it looks for calls of the getter or reads of the field, following calls transitively but not into the JDK or the Scala standard library. Classes that never store the field themselves inherit the trait's val rather than overriding it, so the setter's write is correct there and they aren't affected sites.

```
cd reads-in-init
./controls.sh   # controls/*.scala, compiled with Scala 3.7.3; each file's first line gives the expected answer
./run.sh        # the sites in sites.txt
```

The controls cover a direct read in the trait's initialiser, a read through another method, a read in a trait initialised later, a top-level object (static fields, `<clinit>`), and the no-read and inherited cases; all give the expected answer ([`controls-result.txt`](reads-in-init/controls-result.txt)). Over the libraries ([`result.txt`](reads-in-init/result.txt)), every affected class reports no read in the window.

Limits: the getter is matched by name with no arguments (conservative: it may report reads of an unrelated method of the same name, never miss a direct one); calls are resolved statically (plus overrides in the site's own class), and calls into the JDK and the Scala standard library aren't followed; reflection and calls through function values stored elsewhere aren't seen.
