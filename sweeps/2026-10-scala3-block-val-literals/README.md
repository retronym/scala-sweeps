# Inferred literal types for vals with a block RHS

**Question.** Which published Scala 3 code has a val whose type is inferred as a literal type (in practice a `final val`) and whose RHS is a block, as in the control `class C { final val x = { ???; 42 } }`?

**Answer.** None with statements in the block. Across 6,336 jars (the open community build's published targets, plus the seed corpus of the #25108 sweep), the only block RHSs are braces around a constant expression, `Block(Nil, …)`: 16 in OPAL (`final val Key = { Prefix + "suffix" }`) and one in the Scala 3 compiler (`JSCodeGen.GenericGlobalObjectInformationMsg`, an `inline private val`).

## Method: `tasty-scan/`

A TASTy scan, with no compilation: `Scan.scala` reads a jar's `.tasty` files with the TASTy Inspector (3.10.0) and reports every `ValDef` whose type tree is `Inferred()` with a `ConstantType`, and whose RHS (under any `Typed`) isn't a `Literal`. The RHS is classified:

- `BLOCK stats=N`: a `Block`, the shape asked about.
- `INLINED`: an `Inlined`.
- `OTHER`: anything else, e.g. `final val Mask = 1 << 3`, which TASTy keeps unfolded. These aren't the question but are kept in the results.

If the jar's TASTy doesn't load as a whole (usually references to compile-time-only dependencies missing from the published classpath), the scanner inspects it in chunks of 50 files, splits failing chunks, and reports the single files that fail on their own as `FAIL-ALONE`. The rest are still scanned.

```
cd tasty-scan
./setup.sh                                   # compiles the scanner, writes scan-cp.txt
./controls.sh | tee controls-result.txt      # controls/*.scala with Scala 3.3.6 and 3.7.3
JOBS=8 python3 scan.py | tee result.txt      # libs.txt
LIBS=libs-ocb.txt JOBS=4 python3 scan.py | tee result-ocb.txt
```

`scan.py` resolves each coordinate with coursier (falling back to `latest.release` if the pinned version doesn't resolve), and puts the jar's dependencies, minus their standard library, on the inspector's classpath. It backs off when Maven Central answers HTTP 429, and stops when less than 2 GB of disk is free.

**Controls** (`controls/`, first line gives the expected answer; [`controls-result.txt`](tasty-scan/controls-result.txt)): the block shape in a class, object, trait, `lazy val`, and with a local val in the block is reported; a literal RHS, an explicit `: Int` or `: 42`, a non-final val and a constructor parameter are not. They show two pickling details: `{ 42 }` is pickled as `Block(Nil, 42)` (reported as `stats=0`), and an inline call returning a literal is pickled unexpanded (an `Ident`, reported as `OTHER`).

## Corpus and coverage

| Corpus | Coordinates | Jars scanned | `.tasty` files | Failed alone (jars) |
|---|---|---|---|---|
| [`libs.txt`](tasty-scan/libs.txt), the #25108 sweep's | 141 | 136 | 18,764 | 350 (13) |
| [`libs-ocb.txt`](tasty-scan/libs-ocb.txt), every target of the 2,039 published [open community build](https://github.com/VirtusLab/community-build3) projects (`buildConfig.json`) at its published version | 6,291 | 6,200 | 166,884 | 4,301 (517) |

In `libs-ocb.txt`, 67 coordinates didn't resolve (62 not found, 4 still rate-limited after backoff, 1 other) and 14 had no `_3` jar. Some jars in the two corpora overlap.

Hits, all corpora: `BLOCK stats=0` 17, `INLINED` 0, `OTHER` 1,079 (mostly `Apply`: constant arithmetic and string concatenation).

Limits: only the main `_3` jar of each published artifact (not tests, not unpublished code); the 2.5% of `.tasty` files that fail to load on their own aren't scanned.
