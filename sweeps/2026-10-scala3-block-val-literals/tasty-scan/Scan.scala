//> using scala 3.10.0
//> using dep org.scala-lang::scala3-tasty-inspector:3.10.0
//> using options -deprecation

// Reports every val whose type was inferred as a literal (ConstantType) and whose RHS isn't a
// bare literal. The RHS is classified as:
//   BLOCK    a Block (the shape this sweep is after); stats=N counts its statements
//   INLINED  an Inlined (an inline call, which may expand to a block)
//   OTHER    anything else (e.g. Typed, If, a reference to another constant)
//
// usage: Scan <label> <jar-or-tasty-dir> [classpath of its dependencies]
import scala.quoted.*
import scala.tasty.inspector.*

class Scan(label: String) extends Inspector:
  def inspect(using Quotes)(tastys: List[Tasty[quotes.type]]): Unit =
    import quotes.reflect.*

    def strip(t: Term): Term = t match
      case Typed(e, _) => strip(e)
      case _           => t

    def kind(rhs: Term): Option[String] = strip(rhs) match
      case Literal(_)                    => None
      case Block(stats, _)               => Some(s"BLOCK stats=${stats.size}")
      case Inlined(_, bindings, _)       => Some(s"INLINED bindings=${bindings.size}")
      case t                             => Some(s"OTHER ${t.getClass.getSimpleName}")

    def flags(s: Symbol): String =
      val f = s.flags
      List(Flags.Final -> "final", Flags.Inline -> "inline", Flags.Lazy -> "lazy", Flags.Mutable -> "var",
           Flags.Override -> "override", Flags.Private -> "private")
        .collect { case (fl, n) if f.is(fl) => n }.mkString(",")

    def ownerKind(s: Symbol): String =
      val o = s.owner
      if !o.isClassDef then "local"
      else if o.flags.is(Flags.Module) then "object"
      else if o.flags.is(Flags.Trait) then "trait"
      else "class"

    def where(t: Tree): String =
      try s"${t.pos.sourceFile.path}:${t.pos.startLine + 1}" catch case _: Throwable => "?"

    object T extends TreeTraverser:
      override def traverseTree(tree: Tree)(owner: Symbol): Unit =
        tree match
          case vd @ ValDef(name, tpt @ Inferred(), Some(rhs)) =>
            tpt.tpe match
              case ConstantType(c) =>
                kind(rhs).foreach { k =>
                  val s = vd.symbol
                  println(s"HIT $k ${ownerKind(s)} [${flags(s)}] ${s.owner.fullName}.$name: ${c.show} src=${where(vd)} lib=$label")
                }
              case _ =>
          case _ =>
        try super.traverseTree(tree)(owner)
        catch case e: Throwable => println(s"TRAVERSE-ERROR ${e.getClass.getName}: ${e.getMessage.take(200)} src=${where(tree)} lib=$label")

    for t <- tastys do
      try T.traverseTree(t.ast)(Symbol.spliceOwner)
      catch case e: Throwable => println(s"TASTY-ERROR ${t.path}: ${e.getClass.getName}: ${String.valueOf(e.getMessage).take(200)} lib=$label")

// Inspects the files in chunks; a chunk whose TASTy fails to load is split until single files are
// left, which are reported as FAIL-ALONE. Hits from the rest are still reported.
def inspectOk(label: String, files: List[String], depCp: List[String]): Boolean =
  try TastyInspector.inspectAllTastyFiles(files, Nil, depCp)(new Scan(label))
  catch case _: Throwable => false

def inspectBisect(label: String, files: List[String], depCp: List[String]): Int =
  if files.isEmpty then 0
  else if inspectOk(label, files, depCp) then 0
  else if files.size == 1 then
    println(s"FAIL-ALONE ${files.head.replaceAll(".*/tasty-scan[0-9]+/", "")} lib=$label"); 1
  else
    val (a, b) = files.splitAt(files.size / 2)
    inspectBisect(label, a, depCp) + inspectBisect(label, b, depCp)

@main def runScan(label: String, target: String, deps: String*): Unit =
  val depCp = deps.flatMap(_.split(java.io.File.pathSeparator)).filter(_.nonEmpty).toList
  val files =
    if target.endsWith(".jar") then
      val dir = java.nio.file.Files.createTempDirectory("tasty-scan")
      val zf = java.util.zip.ZipFile(target)
      import scala.jdk.CollectionConverters.*
      zf.entries.asScala.filter(_.getName.endsWith(".tasty")).toList.map { e =>
        val out = dir.resolve(e.getName)
        java.nio.file.Files.createDirectories(out.getParent)
        java.nio.file.Files.copy(zf.getInputStream(e), out)
        out.toString
      }
    else
      java.nio.file.Files.walk(java.nio.file.Paths.get(target)).toArray.toList.map(_.toString).filter(_.endsWith(".tasty"))
  // The jar itself goes on the classpath, so files inspected in separate chunks still see each other.
  val cp = (if target.endsWith(".jar") then List(target) else Nil) ++ depCp
  val sorted = files.sorted
  val failed =
    if inspectOk(label, sorted, cp) then 0
    else sorted.grouped(50).map(inspectBisect(label, _, cp)).sum
  println(s"SUMMARY files=${files.size} fail-alone=$failed lib=$label")
  if target.endsWith(".jar") then
    files.headOption.foreach { f =>
      val dir = java.nio.file.Paths.get(f.replaceAll("(.*/tasty-scan[0-9]+)/.*", "$1"))
      java.nio.file.Files.walk(dir).sorted(java.util.Comparator.reverseOrder()).forEach(java.nio.file.Files.delete)
    }
