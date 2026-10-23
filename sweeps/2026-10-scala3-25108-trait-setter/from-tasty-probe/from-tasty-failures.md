# Jars that don't compile whole with `-from-tasty`

37 of the surveyed jars fail `-from-tasty` with the probe compiler, for reasons unrelated to scala/scala3#25108 that I haven't investigated: 18 type/reference errors, 17 compiler crashes, 2 staging errors. `result-whole-jars.txt` keeps only the first two error headers of each, so the detail below is a location or exception, not a diagnosis.

`probe_bisect.py` then compiled each jar's `.tasty` files in chunks, set aside the files that fail on their own, and probed the rest (`result-bisected-jars.txt`). "Files" is the jar's `.tasty` count and "fail alone" the files that fail even when compiled singly.

| Coordinate | Jar | Kind | First error | Files | Fail alone |
|---|---|---|---|---|---|
| `org.typelevel::cats-core` | `cats-core_3-2.13.0.jar` | type/reference error | `core/src/main/scala/cats/Eval.scala:107:42` | 949 | 2 |
| `org.typelevel::cats-free` | `cats-free_3-2.13.0.jar` | type/reference error | `free/src/main/scala-3/cats/free/FreeFoldStep.scala:45:41` | 35 | 1 |
| `org.typelevel::cats-effect` | `cats-effect_3-3.7.1.jar` | type/reference error | `core/jvm/src/main/scala/cats/effect/Platform.scala:24:7` | 105 | 1 |
| `org.typelevel::spire` | `spire_3-0.18.0.jar` | type/reference error |  | 895 | 0 |
| `co.fs2::fs2-core` | `fs2-core_3-3.14.0.jar` | type/reference error | `core/shared/src/main/scala/fs2/Chunk.scala:1622:51` | 75 | 3 |
| `co.fs2::fs2-io` | `fs2-io_3-3.14.0.jar` | type/reference error | `io/jvm/src/main/scala/fs2/io/net/SocketAddressHelpers.scala:39:28` | 107 | 3 |
| `org.http4s::http4s-core` | `http4s-core_3-1.0.0-M49.jar` | type/reference error | `core/shared/src/main/scala/org/http4s/Message.scala:717:2` | 265 | 2 |
| `dev.zio::zio` | `zio_3-2.1.27.jar` | type/reference error | `core/shared/src/main/scala-3/zio/Experimental.scala:33:12` | 228 | 3 |
| `dev.zio::zio-test` | `zio-test_3-2.1.27.jar` | compiler crash |  | 129 | 3 |
| `org.scalatest::scalatest-core` | `scalatest-core_3-3.3.0-SNAP4.jar` | compiler crash | `dotty/core/target/scala-3.1.3/src_managed/main/org/scalatest/tools/ScalaTestFramework.scala:99:6` | 538 | 4 |
| `org.scalameta::munit` | `munit_3-1.3.6.jar` | compiler crash | `munit/shared/src/main/scala/munit/internal/MacroCompatScala2.scala:20:8` | 50 | 1 |
| `dev.optics::monocle-core` | `monocle-core_3-3.4.0-RC2.jar` | compiler crash |  | 221 | 8 |
| `dev.optics::monocle-macro` | `monocle-macro_3-3.4.0-RC2.jar` | compiler crash |  | 4 | 1 |
| `com.lihaoyi::utest` | `utest_3-0.10.0-RC1.jar` | compiler crash |  | 96 | 1 |
| `org.scodec::scodec-core` | `scodec-core_3-2.3.3.jar` | type/reference error | `shared/src/main/scala/scodec/codecs/DiscriminatorCodec.scala:184:51` | 74 | 1 |
| `org.typelevel::shapeless3-deriving` | `shapeless3-deriving_3-3.6.0.jar` | type/reference error | `modules/deriving/src/main/scala/shapeless3/deriving/kinds.scala:175:6` | 23 | 3 |
| `io.getquill::quill-sql` | `quill-sql_3-4.8.6.jar` | staging error | `quill-sql/src/main/scala/io/getquill/parser/Parser.scala:756:12` | 248 | 2 |
| `org.scala-lang.modules::scala-parallel-collections` | `scala-parallel-collections_3-1.3.0.jar` | compiler crash | `dotty.tools.dotc.core.TypeError$$anon$1: invalid prefix [U >: T, That] =>> ParMapLike.this.Copy[U, That] when trying to form [U >:` | 100 | 1 |
| `org.parboiled::parboiled` | `parboiled_3-2.5.1.jar` | staging error | `parboiled-core/src/main/scala-3/org/parboiled2/support/OpTreeContext.scala:836:12` | 47 | 1 |
| `org.tpolecat::skunk-core` | `skunk-core_3-2.0.0-RC3.jar` | compiler crash |  | 194 | 1 |
| `com.typesafe.slick::slick` | `slick_3-4.0.0-RC2.jar` | type/reference error | `slick/src/main/scala/slick/jdbc/HsqldbProfile.scala:306:8` | 428 | 2 |
| `org.apache.pekko::pekko-actor` | `pekko-actor_3-2.0.0-M4.jar` | type/reference error | `actor/src/main/scala/org/apache/pekko/util/Reflect.scala:234:8` | 646 | 1 |
| `org.apache.pekko::pekko-stream` | `pekko-stream_3-2.0.0-M4.jar` | type/reference error | `stream/src/main/scala/org/apache/pekko/stream/javadsl/SubSource.scala:2403:6` | 612 | 7 |
| `org.apache.pekko::pekko-http-core` | `pekko-http-core_3-2.0.0-M2.jar` | compiler crash |  | 439 | 368 |
| `org.apache.pekko::pekko-http` | `pekko-http_3-2.0.0-M2.jar` | compiler crash | `java.lang.AssertionError: assertion failed: class ServerSentEventParser has non-class parent: AppliedType(TypeRef(Te` | 285 | 179 |
| `org.typelevel::kittens` | `kittens_3-3.5.0.jar` | type/reference error | `modules/deriving/src/main/scala/shapeless3/deriving/kinds.scala:176:6` | 42 | 2 |
| `com.github.julien-truffaut::monocle-core` | `monocle-core_3-3.0.0-M6.jar` | compiler crash |  | 215 | 5 |
| `dev.zio::zio-http` | `zio-http_3-3.11.6.jar` | compiler crash | `zio-http/jvm/src/main/scala/zio/http/netty/EventLoopGroups.scala:82:78` | 236 | 3 |
| `dev.zio::zio-prelude` | `zio-prelude_3-1.0.0-RC48.jar` | type/reference error | `core/shared/src/main/scala/zio/prelude/Zivariant.scala:136:30` | 137 | 12 |
| `com.github.ghostdogpr::caliban` | `caliban_3-3.2.0.jar` | compiler crash | `core/src/main/scala/caliban/GraphQLWSOutput.scala:10:64` | 179 | 13 |
| `org.json4s::json4s-core` | `json4s-core_3-4.1.0-M8.jar` | compiler crash | `core/src/main/scala-3/org/json4s/reflect/ScalaSigReader.scala:15:4` | 43 | 1 |
| `org.scala-lang::scala3-compiler` | `scala3-compiler_3-3.3.6.jar` | type/reference error | `compiler/src/dotty/tools/dotc/parsing/Scanners.scala:608:13` | 971 | 2 |
| `org.scala-lang::scala3-tasty-inspector` | `scala3-tasty-inspector_3-3.7.3.jar` | compiler crash | `java.lang.AssertionError: assertion failed: no owner from <none>/<none> in file.ext` | 3 | 1 |
| `org.scala-lang::scaladoc` | `scaladoc_3-3.7.3.jar` | type/reference error | `scaladoc/src/dotty/tools/scaladoc/ScaladocSettings.scala:15:4` | 191 | 79 |
| `com.softwaremill.macwire::macros` | `macros_3-2.6.7.jar` | type/reference error | `macros/src/main/scala-3/com/softwaremill/macwire/macwire.scala:102:4` | 17 | 2 |
| `org.virtuslab::besom-core` | `besom-core_3-0.5.2.jar` | compiler crash |  | 157 | 6 |
| `org.virtuslab::scala-yaml` | `scala-yaml_3-0.3.3.jar` | compiler crash |  | 54 | 1 |
