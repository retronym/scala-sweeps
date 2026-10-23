# scala-sweeps

Broad sweeps over published Scala code, to answer questions about a compiler or library change that its own test suite can't: what does this change touch in the wild, and does it change behaviour there?

Most sweeps work on artifacts that are already published, so they need no library builds: TASTy recompiled with `-from-tasty` (which reruns the phases after pickling), or bytecode read directly with ASM.

## Use cases

- **Blast radius of a compiler change.** Add a probe to the changed code that prints each site it changes, recompile a corpus of published jars from TASTy with it, and list the sites. [scala/scala3#25108](sweeps/2026-10-scala3-25108-trait-setter/) is the first example.
- **Mid- and backend parity between compilers (QA).** Compile the same jars `-from-tasty` with two compilers, for example consecutive nightlies, a PR against its base, or fused against unfused MegaPhases, and diff the classfiles. Pickling is skipped, so this exercises exactly the transform and backend phases, cheaply, on real code, without building any library. Differences other than fresh names and synthetic member order are leads.
- **Auditing usage of library methods.** Scan published bytecode for call sites of an API (a method, a field, an overload, an implicit conversion's expansion), for example before deprecating it or changing its semantics, and report who calls it and how.
- **Checking the behaviour of affected sites.** Once a sweep has found sites, a bytecode analyzer can check a property of each one, as `reads-in-init` does for #25108: does any code read the val while it holds the wrong value? Each analyzer comes with controls, small programs with known answers, run with a released compiler.
- **Finding source shapes.** Scan published TASTy with the TASTy Inspector for a tree shape, without recompiling anything, e.g. [vals with an inferred literal type and a block RHS](sweeps/2026-10-scala3-block-val-literals/), over every published target of the open community build.
- **Harvesting test shapes.** Real-world shapes found by a sweep make better regression tests than ones written from the ticket, e.g. the slick-pg shape in #25108's tests.
- **Spotting tooling gaps.** Jars that fail `-from-tasty` are themselves findings (see [the #25108 sweep's failures](sweeps/2026-10-scala3-25108-trait-setter/from-tasty-probe/from-tasty-failures.md)).

## Layout and conventions

Each sweep has a directory under `sweeps/`, named by date and question, holding:

- a README with the question, the answer, the method, and how to rerun it;
- the scripts, runnable as checked in (inputs such as a compiler checkout come from environment variables);
- the corpus (e.g. a `libs.txt` of coordinates) and the raw results of the run the README reports, with local paths replaced by `$VARIABLES`;
- for any analyzer that decides a property, controls with known answers, and their results.

The library list in the #25108 sweep (the Scala 3 community build's `_3` artifacts plus about 50 widely used libraries) is a reasonable starting corpus for the next sweep.

## Prerequisites

JDK 17+, [coursier](https://get-coursier.io/) on the `PATH`, Python 3, and for probes that patch the compiler, a [scala3](https://github.com/scala/scala3) checkout.

## License

[Apache License 2.0](LICENSE).
