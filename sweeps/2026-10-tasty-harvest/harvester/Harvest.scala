//> using scala 3.10.0
//> using dep org.scala-lang::scala3-tasty-inspector:3.10.0
//> using options -deprecation

// Harvests facts from the TASTy of one jar into gzipped TSV tables in an output directory:
//
//   defs        every non-local definition: kind, flags, visibility, signature shape, annotations
//   refs        references to non-local symbols, aggregated per (target, kind, role): count, files, a sample site
//   imports     imports, aggregated per (prefix, selectors)
//   hist        counts of tree node classes and of findings
//   findings    sites of hazard patterns (capped per kind; the uncapped count is in hist)
//   module_init modules referenced by a module's initialiser (statements and strict vals of its template)
//
// A jar whose TASTy doesn't load as a whole is inspected in chunks of 50 files, splitting failing
// chunks; files that fail on their own are written to `failures`. Rows from a failed inspection are
// discarded, so nothing is counted twice.
//
// usage: Harvest <lib> <jar> <out-dir> [classpath of its dependencies]
import scala.collection.mutable
import scala.quoted.*
import scala.tasty.inspector.*

val FindingCap = 300

def clean(s: String): String = if s == null then "" else s.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')

/** Rows gathered by one inspection, merged into the jar's totals only if the inspection succeeds. */
class Sink:
  val defs = mutable.ArrayBuffer[String]()
  val findings = mutable.ArrayBuffer[String]()
  val moduleInit = mutable.LinkedHashSet[String]()
  val refs = mutable.HashMap[String, Agg]()
  val imports = mutable.HashMap[String, Agg]()
  val hist = mutable.HashMap[String, Long]().withDefaultValue(0L)
  val findingCount = mutable.HashMap[String, Int]().withDefaultValue(0)

  def mergeInto(o: Sink): Unit =
    o.defs ++= defs
    for f <- findings do
      val k = f.takeWhile(_ != '\t')
      if o.findingCount(k) < FindingCap then o.findings += f
      o.findingCount(k) += 1
    o.moduleInit ++= moduleInit
    for (k, a) <- refs do o.refs.getOrElseUpdate(k, Agg()).merge(a)
    for (k, a) <- imports do o.imports.getOrElseUpdate(k, Agg()).merge(a)
    for (k, n) <- hist do o.hist(k) += n

class Agg:
  var count = 0L
  val files = mutable.HashSet[String]()
  var sample = ""
  def add(file: String, site: String): Unit =
    count += 1; files += file; if sample.isEmpty then sample = site
  def merge(o: Agg): Unit =
    count += o.count; files ++= o.files; if sample.isEmpty then sample = o.sample

class Harvest(lib: String, sink: Sink) extends Inspector:
  def inspect(using Quotes)(tastys: List[Tasty[quotes.type]]): Unit =
    import quotes.reflect.*

    val deprecatedCls = Symbol.requiredClass("scala.deprecated")
    val experimentalCls = Symbol.requiredClass("scala.annotation.experimental")
    val uncheckedCls = Symbol.requiredClass("scala.unchecked")
    val conversionCls = Symbol.requiredClass("scala.Conversion")
    val numeric = Set("scala.Byte", "scala.Short", "scala.Char", "scala.Int", "scala.Long", "scala.Float", "scala.Double",
      "scala.math.BigInt", "scala.math.BigDecimal", "java.lang.Number", "java.lang.Byte", "java.lang.Short",
      "java.lang.Character", "java.lang.Integer", "java.lang.Long", "java.lang.Float", "java.lang.Double",
      "java.math.BigInteger", "java.math.BigDecimal")
    val topTypes = Set("scala.Any", "scala.AnyRef", "java.lang.Object", "scala.Matchable", "scala.AnyVal")

    def safe[T](default: T)(body: => T): T = try body catch case _: Throwable => default

    var file = ""
    // Inside compiler-generated code (case class members, enum and module boilerplate): references are
    // tagged `synthetic` and hazards aren't reported.
    var inSynthetic = false

    def countFinding(k: String): Unit = if !inSynthetic then sink.hist("finding:" + k) += 1

    def withSynthetic[T](s: Symbol)(body: => T): T =
      val old = inSynthetic
      inSynthetic = old || (s.flags.is(Flags.Synthetic) && !isLocal(s))
      try body finally inSynthetic = old
    def line(t: Tree): String = safe("?")((t.pos.startLine + 1).toString)
    def site(t: Tree): String = s"$file:${line(t)}"
    def zeroExtent(t: Tree): Boolean = safe(false)(t.pos.start == t.pos.end)
    def sameSpan(a: Tree, b: Tree): Boolean = safe(false)(a.pos.start == b.pos.start && a.pos.end == b.pos.end)

    def isLocal(s: Symbol): Boolean = safe(true) {
      var o = s.maybeOwner
      var local = false
      while !o.isNoSymbol && !o.isPackageDef do
        if !o.isClassDef then local = true
        o = o.maybeOwner
      local || (!s.maybeOwner.isClassDef && !s.maybeOwner.isPackageDef)
    }

    /** Binary name of the top-level class that holds `s`, for mapping it to a jar. */
    def topLevel(s: Symbol): String = safe("") {
      var t = s
      while !t.maybeOwner.isNoSymbol && !t.maybeOwner.isPackageDef do t = t.maybeOwner
      if t.isNoSymbol then "" else
        val pkg = t.maybeOwner.fullName
        val n = t.name.stripSuffix("$")
        if pkg.isEmpty || pkg == "<empty>" then n else s"$pkg.$n"
    }

    def sig(s: Symbol): String = safe("") {
      if s.isDefDef then s.signature.paramSigs.map(_.toString).mkString("(", ",", ")") else ""
    }

    def visibility(s: Symbol): String =
      val f = s.flags
      if f.is(Flags.Private) || f.is(Flags.PrivateLocal) then "private"
      else if s.privateWithin.isDefined then "qualified"
      else if f.is(Flags.Protected) then (if s.protectedWithin.isDefined then "qualified" else "protected")
      else
        var o = s.maybeOwner
        var v = "public"
        while !o.isNoSymbol && !o.isPackageDef && v == "public" do
          if o.flags.is(Flags.Private) || o.privateWithin.isDefined then v = "effectively-private"
          o = o.maybeOwner
        v

    val flagNames = List(Flags.Abstract -> "abstract", Flags.Case -> "case", Flags.Enum -> "enum", Flags.Erased -> "erased",
      Flags.Exported -> "exported", Flags.ExtensionMethod -> "extension", Flags.Final -> "final", Flags.Given -> "given",
      Flags.Implicit -> "implicit", Flags.Infix -> "infix", Flags.Inline -> "inline", Flags.Lazy -> "lazy",
      Flags.Macro -> "macro", Flags.Mutable -> "var", Flags.Opaque -> "opaque", Flags.Open -> "open",
      Flags.Override -> "override", Flags.ParamAccessor -> "param-accessor", Flags.Sealed -> "sealed",
      Flags.Synthetic -> "synthetic", Flags.Transparent -> "transparent", Flags.Deferred -> "deferred",
      Flags.JavaStatic -> "static", Flags.Artifact -> "artifact")
    def flags(s: Symbol): String = flagNames.collect { case (fl, n) if s.flags.is(fl) => n }.mkString(",")

    def tpeKind(t: TypeRepr): String = safe("?") {
      t.dealias match
        case ConstantType(_)                                                       => "literal"
        case AndType(a, b) if Set(a.typeSymbol.fullName, b.typeSymbol.fullName) ==
                                Set("scala.Product", "java.io.Serializable")       => "product-with-serializable"
        case _: AndType                                                            => "intersection"
        case _: OrType                                                             => "union"
        case _: Refinement                                                         => "refinement"
        case _: MatchType                                                          => "match-type"
        case _: TypeLambda                                                         => "type-lambda"
        case _: TermRef                                                            => "singleton"
        case u if u =:= TypeRepr.of[Nothing]                                       => "nothing"
        case u if topTypes(u.typeSymbol.fullName)                                  => "top:" + u.typeSymbol.name
        case u if u.typeSymbol.fullName == "scala.Product" || u.typeSymbol.fullName == "java.io.Serializable" => "top:" + u.typeSymbol.name
        case _: AppliedType                                                        => "applied"
        case _: TypeRef                                                            => "ref"
        case u                                                                     => u.getClass.getSimpleName
    }

    /** Language features visible in a type. */
    def typeFeatures(t: TypeRepr, acc: mutable.Set[String], depth: Int = 0): Unit =
      if depth < 8 && acc.size < 40 then safe(()) {
        def go(u: TypeRepr) = typeFeatures(u, acc, depth + 1)
        t match
          case ConstantType(_)        => acc += "literal-type"
          case OrType(a, b)           => acc += "union-type"; go(a); go(b)
          case AndType(a, b)          => acc += "intersection-type"; go(a); go(b)
          case MatchType(b, s, cs)    => acc += "match-type"; go(s); cs.foreach(go)
          case l: TypeLambda          => acc += "type-lambda"; go(l.resType)
          case ByNameType(u)          => acc += "by-name"; go(u)
          case AnnotatedType(u, a)    =>
            val n = safe("")(a.tpe.typeSymbol.fullName)
            if n.contains("retains") || n.contains("captureChecking") then acc += "capture-annotation"
            else if n == "scala.unchecked.uncheckedVariance" then acc += "unchecked-variance"
            go(u)
          case r: Refinement          =>
            if safe(false)(r.parent.typeSymbol.fullName == "scala.PolyFunction") then acc += "poly-function-type"
            else if safe(false)(r.isDependentFunctionType) then acc += "dependent-function-type"
            else acc += "structural-refinement"
            go(r.parent); go(r.info)
          case a @ AppliedType(tc, args) =>
            val n = safe("")(tc.typeSymbol.fullName)
            if safe(false)(a.isContextFunctionType) then acc += "context-function-type"
            val namedTuple = n == "scala.NamedTuple$.NamedTuple" || n == "scala.NamedTuple.NamedTuple"
            if namedTuple then acc += "named-tuple"
            if n == "scala.<repeated>" then acc += "varargs"
            if n == "scala.*:" then acc += "generic-tuple"
            // A named tuple's first argument is a tuple of its field names, as literal types.
            go(tc); (if namedTuple then args.drop(1) else args).foreach(go)
          case m: MethodType          => m.paramTypes.foreach(go); go(m.resType)
          case p: PolyType            => p.paramBounds.foreach(go); go(p.resType)
          case TypeBounds(lo, hi)     => go(lo); go(hi)
          case _                      =>
      }

    def strip(t: Term): Term = t match
      case Typed(e, _) => strip(e)
      case _           => t

    def annots(s: Symbol): String = safe("")(s.annotations.map(a => safe("?")(a.tpe.typeSymbol.fullName)).distinct.mkString(","))

    def defRow(t: Definition, kind: String, tptInferred: String, tpe: String, rhs: String, feats: collection.Set[String]): Unit =
      val s = t.symbol
      sink.defs += List(lib, file, line(t), clean(s.fullName), clean(s.name), kind, clean(sig(s)), flags(s), visibility(s),
        tptInferred, tpe, rhs, feats.toList.sorted.mkString(","), clean(annots(s))).mkString("\t")

    def finding(kind: String, t: Tree, owner: Symbol, detail: String): Unit =
      if !inSynthetic then sink.findings += List(kind, lib, site(t), clean(safe("?")(owner.fullName)), clean(detail.take(300))).mkString("\t")

    def isConstantRef(t: Tree): Boolean = safe(false) {
      t match
        case t: Term => t.tpe.widenTermRefByName match { case _: ConstantType => true; case _ => false }
        case _       => false
    }

    def ref(target: Symbol, kind: String, role: String, t: Tree): Unit =
      if !target.isNoSymbol && !isLocal(target) && !target.isPackageDef then
        val tf = safe("")(flags(target))
        val ann = mutable.ListBuffer[String]()
        if safe(false)(target.hasAnnotation(deprecatedCls)) then ann += "deprecated"
        if safe(false)(target.hasAnnotation(experimentalCls)) then ann += "experimental"
        val roles = (List(role) ++ (if isConstantRef(t) then List("const") else Nil) ++ (if inSynthetic then List("synthetic") else Nil))
          .filter(_.nonEmpty).mkString(",")
        val key = List(clean(safe("?")(target.fullName)), clean(sig(target)), clean(topLevel(target)), kind, roles, tf, ann.mkString(",")).mkString("\t")
        sink.refs.getOrElseUpdate(key, Agg()).add(file, site(t))

    def termKind(s: Symbol): String =
      if s.isDefDef then "call" else if s.flags.is(Flags.Module) then "module" else "value"

    // Per-traversal state: enclosing definitions, and whether we are inside a synthesised argument.
    val defStack = mutable.Stack[Symbol]()
    var role = ""
    var inInlineBody: Option[Symbol] = None

    def withRole[T](r: String)(body: => T): T =
      val old = role; role = r
      try body finally role = old

    object T extends TreeTraverser:
      override def traverseTree(tree: Tree)(owner: Symbol): Unit =
        sink.hist(tree.getClass.getSimpleName) += 1
        try visit(tree, owner)
        catch case e: Throwable => sink.hist("ERROR:" + e.getClass.getSimpleName) += 1

      def visit(tree: Tree, owner: Symbol): Unit = tree match
        case cd @ ClassDef(name, constr, parents, self, body) =>
          val s = cd.symbol
          val kind =
            if s.flags.is(Flags.Module) then "object"
            else if s.flags.is(Flags.Trait) then "trait"
            else if s.flags.is(Flags.Enum) then "enum"
            else if s.flags.is(Flags.Case) then "case-class"
            else "class"
          if !isLocal(s) then
            val feats = mutable.Set[String]()
            if parents.exists(p => safe(false)(p.symbol.fullName == "scala.AnyVal" || (p match { case t: TypeTree => t.tpe.typeSymbol.fullName == "scala.AnyVal"; case t: Term => t.tpe.typeSymbol.fullName == "scala.AnyVal" }))) then feats += "value-class"
            if s.name.startsWith("given_") || s.flags.is(Flags.Given) then feats += "given-class"
            if !self.isEmpty && !s.flags.is(Flags.Module) then feats += "self-type"
            defRow(cd, kind, "", "", "", feats)
          checkTemplate(cd, body)
          defStack.push(s)
          // Not withSynthetic: top-level definitions live in a synthetic `$package` object.
          try super.traverseTree(tree)(s) finally defStack.pop()

        case td @ TypeDef(name, rhs) =>
          val s = td.symbol
          if !isLocal(s) && !s.flags.is(Flags.Param) then
            val feats = mutable.Set[String]()
            val r = safe[TypeRepr](TypeRepr.of[Nothing])(rhs match { case t: TypeTree => t.tpe; case b: TypeBoundsTree => b.tpe; case _ => TypeRepr.of[Nothing] })
            typeFeatures(r, feats)
            val kind =
              if s.flags.is(Flags.Opaque) then "opaque-type"
              else if safe(false)(r match { case _: MatchType => true; case l: TypeLambda => l.resType match { case _: MatchType => true; case _ => false }; case _ => false }) then "match-type-def"
              else if (rhs match { case _: TypeBoundsTree => true; case _ => false }) then "abstract-type"
              else "type-alias"
            defRow(td, kind, "", "", "", feats)
          super.traverseTree(tree)(owner)

        case dd @ DefDef(name, paramss, tpt, rhs) =>
          val s = dd.symbol
          if !isLocal(s) && !s.isClassConstructor && !name.startsWith("$anonfun") then
            val feats = mutable.Set[String]()
            for clause <- paramss do clause match
              case c: TermParamClause =>
                if safe(false)(c.isGiven) then feats += "using-clause"
                else if safe(false)(c.isImplicit) then feats += "implicit-clause"
                if c.params.exists(_.symbol.flags.is(Flags.HasDefault)) then feats += "default-args"
                if c.params.exists(_.symbol.flags.is(Flags.Erased)) then feats += "erased-params"
                c.params.foreach(p => typeFeatures(p.tpt.tpe, feats))
              case _: TypeParamClause => feats += "type-params"
            if paramss.count { case _: TermParamClause => true; case _ => false } > 1 then feats += "multiple-param-lists"
            if safe(false)(paramss.indexWhere({ case _: TypeParamClause => true; case _ => false }, 1) > 0) then feats += "interleaved-type-params"
            typeFeatures(tpt.tpe, feats)
            val f = s.flags
            val kind =
              if f.is(Flags.Given) then "given-def"
              else if f.is(Flags.Macro) then "macro"
              else if f.is(Flags.ExtensionMethod) then "extension"
              else if f.is(Flags.Implicit) && paramss.collect { case c: TermParamClause if !safe(false)(c.isImplicit || c.isGiven) => c }.map(_.params.size) == List(1) then "implicit-conversion-def"
              else if f.is(Flags.Implicit) then "implicit-def"
              else if f.is(Flags.Transparent) then "transparent-inline-def"
              else if f.is(Flags.Inline) then "inline-def"
              else if f.is(Flags.FieldAccessor) || f.is(Flags.StableRealizable) && f.is(Flags.Lazy) then "accessor"
              else "def"
            val inferred = tpt match { case Inferred() => "1"; case _ => "0" }
            defRow(dd, kind, inferred, tpeKind(tpt.tpe), rhs.map(r => strip(r).getClass.getSimpleName).getOrElse(""), feats)
          defStack.push(s)
          val oldInline = inInlineBody
          if s.flags.is(Flags.Inline) && !isLocal(s) && visibility(s) != "private" && visibility(s) != "effectively-private" then inInlineBody = Some(s)
          try withSynthetic(s)(super.traverseTree(tree)(s)) finally { defStack.pop(); inInlineBody = oldInline }

        case vd @ ValDef(name, tpt, rhs) =>
          val s = vd.symbol
          if !isLocal(s) && !s.flags.is(Flags.Param) then
            val f = s.flags
            val kind =
              if f.is(Flags.Given) then "given-val"
              else if f.is(Flags.Implicit) then "implicit-val"
              else if f.is(Flags.Module) then "module-val"
              else if f.is(Flags.Inline) then "inline-val"
              else if f.is(Flags.Lazy) then "lazy-val"
              else if f.is(Flags.Mutable) then "var"
              else "val"
            val feats = mutable.Set[String]()
            typeFeatures(tpt.tpe, feats)
            val inferred = tpt match { case Inferred() => "1"; case _ => "0" }
            defRow(vd, kind, inferred, tpeKind(tpt.tpe), rhs.map(r => strip(r).getClass.getSimpleName).getOrElse(""), feats)
          withSynthetic(s)(super.traverseTree(tree)(owner))

        case Return(expr, from) =>
          defStack.headOption.foreach { inner =>
            if inner != from then
              sink.hist("Return:nonlocal") += 1
              finding("nonlocal-return", tree, from, s"return from ${from.name} inside ${inner.name}")
          }
          super.traverseTree(tree)(owner)

        case Inlined(call, bindings, expansion) =>
          call.foreach { c =>
            val s = safe(Symbol.noSymbol)(c.symbol)
            ref(s, "inlined", role, tree)
          }
          super.traverseTree(tree)(owner)

        case imp @ Import(expr, selectors) =>
          val prefix = safe(expr.show)(if expr.symbol.isNoSymbol then expr.show else expr.symbol.fullName)
          for sel <- selectors do
            val selStr = sel match
              case SimpleSelector(n)    => n
              case RenameSelector(a, b) => s"$a=>$b"
              case OmitSelector(n)      => s"$n=>_"
              case GivenSelector(b)     => "given" + b.map(t => " " + safe("?")(t.tpe.show)).getOrElse("")
            sink.imports.getOrElseUpdate(List(clean(prefix), clean(selStr)).mkString("\t"), Agg()).add(file, site(tree))
          super.traverseTree(tree)(owner)

        case app @ Apply(fn, args) =>
          val fs = safe(Symbol.noSymbol)(fn.symbol)
          // An implicit conversion the compiler inserted: `conv(arg)` with the span of `arg`.
          if args.size == 1 && sameSpan(app, args.head) && !fs.isNoSymbol then
            val isConv = fs.flags.is(Flags.Implicit) || fs.flags.is(Flags.Given) ||
              (fs.name == "apply" && safe(false)(fn match { case Select(q, _) => q.tpe.baseClasses.contains(conversionCls); case _ => false }))
            if isConv then
              countFinding("implicit-conversion")
              ref(fs, "conversion", "", app)
          // `==` between values that can never be equal: one side's class is final and not a subclass of the other's.
          fn match
            case Select(l, op @ ("==" | "!=")) if args.size == 1 => checkEquality(app, l, args.head, op, owner)
            case _ =>
          // Implicit arguments the compiler inserted.
          val implicitArgs = safe(false)(fn.tpe.widen match { case m: MethodType => m.isImplicit; case _ => false })
          if implicitArgs then
            traverseTree(fn)(owner)
            for a <- args do
              if zeroExtent(a) || sameSpan(a, fn) then withRole("using")(traverseTree(a)(owner))
              else traverseTree(a)(owner)
          else super.traverseTree(tree)(owner)

        case TypeApply(sel @ Select(qual, op @ ("isInstanceOf" | "asInstanceOf")), List(targ)) =>
          if genericArgs(targ.tpe, safe[TypeRepr](TypeRepr.of[Any])(qual.tpe.widen)) then
            countFinding(s"generic-$op")
            if op == "isInstanceOf" then finding("generic-isInstanceOf", tree, owner, safe("?")(targ.tpe.show))
          super.traverseTree(tree)(owner)

        case TypeApply(fn, targs) =>
          if targs.exists { case t @ Inferred() => safe(false)(t.tpe =:= TypeRepr.of[Nothing]); case _ => false } then
            countFinding("inferred-nothing")
            finding("inferred-nothing", tree, owner, safe("?")(fn.symbol.fullName))
          super.traverseTree(tree)(owner)

        case Match(selector, cases) =>
          val scrut = safe[TypeRepr](TypeRepr.of[Any])(selector.tpe.widen)
          cases.foreach(c => checkPattern(c.pattern, scrut, owner))
          super.traverseTree(tree)(owner)

        case New(tpt) =>
          ref(safe(Symbol.noSymbol)(tpt.tpe.typeSymbol), "new", role, tree)
          super.traverseTree(tree)(owner)

        case id: Ident =>
          val s = safe(Symbol.noSymbol)(id.symbol)
          if !s.isNoSymbol then
            ref(s, termKind(s), role, id)
            inlineCheck(s, id, owner)

        case sel @ Select(qual, name) =>
          val s = safe(Symbol.noSymbol)(sel.symbol)
          if !s.isNoSymbol then
            ref(s, termKind(s), role, sel)
            inlineCheck(s, sel, owner)
          super.traverseTree(tree)(owner)

        case t: TypeIdent =>
          ref(safe(Symbol.noSymbol)(t.symbol), "type", role, t)
        case t: TypeSelect =>
          ref(safe(Symbol.noSymbol)(t.symbol), "type", role, t)
          super.traverseTree(tree)(owner)

        case _ => super.traverseTree(tree)(owner)

      def inlineCheck(target: Symbol, t: Tree, owner: Symbol): Unit =
        inInlineBody.foreach { inl =>
          val v = visibility(target)
          if (v == "private" || v == "qualified" || target.name.startsWith("inline$")) && !isLocal(target) && target.maybeOwner != inl then
            countFinding("inline-reaches-nonpublic")
            finding("inline-reaches-nonpublic", t, inl, s"${target.fullName} (${if target.name.startsWith("inline$") then "inline accessor" else v})")
        }

      def hasUnchecked(t: TypeRepr): Boolean = t match
        case AnnotatedType(u, a) => safe(false)(a.tpe.typeSymbol == uncheckedCls) || hasUnchecked(u)
        case _                   => false

      /** A type test on `t` whose type arguments may not be checkable at runtime. This is a heuristic
       *  superset of the compiler's unchecked warning: the test is assumed checkable if `t`'s class
       *  derives from the scrutinee's class and the scrutinee is itself applied (`Seq[Int]` vs `List[Int]`). */
      def genericArgs(t: TypeRepr, scrut: TypeRepr): Boolean = safe(false) {
        if hasUnchecked(t) then
          countFinding("unchecked-annotation")
          false
        else t.dealias match
          case AppliedType(tc, args) =>
            val cls = tc.typeSymbol
            def wildcard(a: TypeRepr) = a match
              case _: TypeBounds => true
              case _ => safe(false)(a.typeSymbol.name.startsWith("_$") || a.typeSymbol.flags.is(Flags.Case))
            val determined = safe(false)(scrut.dealias match { case s: AppliedType => cls.typeRef.baseClasses.contains(s.typeSymbol); case _ => false })
            cls.fullName != "scala.Array" && !determined && args.exists(a => !wildcard(a))
          case _ => false
      }

      def checkPattern(pat: Tree, scrut: TypeRepr, owner: Symbol): Unit = safe(()) {
        pat match
          case Typed(_, tpt) =>
            if genericArgs(tpt.tpe, scrut) then
              countFinding("generic-type-pattern")
              finding("generic-type-pattern", pat, owner, s"${safe("?")(tpt.tpe.show)} from ${safe("?")(scrut.show)}")
          case Bind(_, p)           => checkPattern(p, scrut, owner)
          case Alternatives(ps)     => ps.foreach(checkPattern(_, scrut, owner))
          case Unapply(_, _, ps)    => ps.foreach(checkPattern(_, TypeRepr.of[Any], owner))
          case _                    =>
      }

      def classOf(t: TypeRepr): Option[Symbol] = safe(None) {
        t.widen.dealias match
          case _: TypeRef | _: AppliedType | _: ConstantType =>
            val c = t.widen.dealias.classSymbol
            c.filter(s => !topTypes(s.fullName))
          case _ => None
      }

      def checkEquality(app: Tree, l: Term, r: Term, op: String, owner: Symbol): Unit = safe(()) {
        (classOf(l.tpe), classOf(r.tpe)) match
          case (Some(a), Some(b)) if a != b && !(numeric(a.fullName) && numeric(b.fullName)) =>
            def effFinal(c: Symbol) = c.flags.is(Flags.Final) || c.flags.is(Flags.Module) || c.fullName == "java.lang.String"
            def disjoint(c: Symbol, d: Symbol) = effFinal(c) && !l.tpe.widen.baseClasses.contains(d) && !r.tpe.widen.baseClasses.contains(c)
            if disjoint(a, b) || disjoint(b, a) then
              countFinding("disjoint-equality")
              finding("disjoint-equality", app, owner, s"${l.tpe.widen.show} $op ${r.tpe.widen.show}")
          case _ =>
      }

      /** A strict val read before it is initialised, and modules touched while a module initialises. */
      def checkTemplate(cd: ClassDef, body: List[Statement]): Unit = safe(()) {
        val s = cd.symbol
        val strict = body.zipWithIndex.collect {
          case (v: ValDef, i) if !v.symbol.flags.is(Flags.Lazy) && !v.symbol.flags.is(Flags.Deferred) && !v.symbol.flags.is(Flags.Module)
                                && !safe(false)(v.tpt.tpe match { case _: ConstantType => true; case _ => false }) => v.symbol -> i
        }.toMap
        val isModule = s.flags.is(Flags.Module)
        body.zipWithIndex.foreach { (stat, i) =>
          val init: Option[Tree] = stat match
            case v: ValDef if !v.symbol.flags.is(Flags.Lazy) => v.rhs
            case _: Definition | _: Import | _: Export      => None
            case t                                           => Some(t)
          init.foreach { t =>
            new TreeTraverser:
              override def traverseTree(tree: Tree)(o: Symbol): Unit = tree match
                case _: DefDef | _: ClassDef => // runs later, or not at all
                case Apply(fn, args) =>
                  // Arguments passed by name run later, or not at all (`P.defer(later)`).
                  val byName = safe(Nil)(fn.tpe.widen match
                    case m: MethodType => m.paramTypes.map { case _: ByNameType => true; case _ => false }
                    case _             => Nil)
                  traverseTree(fn)(o)
                  args.zipWithIndex.foreach((a, i) => if !byName.lift(i).getOrElse(false) then traverseTree(a)(o))
                case id: Ident if strict.get(id.symbol).exists(_ > i) =>
                  finding("forward-reference", id, s, s"${id.symbol.name} read before its initialisation")
                case sel @ Select(This(_), _) if strict.get(sel.symbol).exists(_ > i) =>
                  finding("forward-reference", sel, s, s"${sel.symbol.name} read before its initialisation")
                case t: Term if isModule =>
                  val ts = safe(Symbol.noSymbol)(t.symbol)
                  if !ts.isNoSymbol && ts.flags.is(Flags.Module) && ts.isTerm && ts.moduleClass != s && !isLocal(ts)
                     && !ts.fullName.startsWith("scala.") && !ts.fullName.startsWith("java.") && !(t match { case _: This => true; case _ => false }) then
                    sink.moduleInit += List(lib, clean(s.fullName), clean(ts.moduleClass.fullName), site(t)).mkString("\t")
                  super.traverseTree(tree)(o)
                case _ => super.traverseTree(tree)(o)
            .traverseTree(t)(s)
          }
        }
      }

    for t <- tastys do
      file = safe(t.path)(t.ast.pos.sourceFile.path)
      defStack.clear(); role = ""; inInlineBody = None; inSynthetic = false
      try T.traverseTree(t.ast)(Symbol.spliceOwner)
      catch case e: Throwable => sink.hist("ERROR-FILE:" + e.getClass.getSimpleName) += 1

object Run:
  val total = Sink()
  var failures = List[String]()

  def inspectOk(lib: String, files: List[String], cp: List[String]): Boolean =
    val sink = Sink()
    val ok = try TastyInspector.inspectAllTastyFiles(files, Nil, cp)(Harvest(lib, sink)) catch case _: Throwable => false
    if ok then sink.mergeInto(total)
    ok

  def bisect(lib: String, files: List[String], cp: List[String]): Unit =
    if files.isEmpty || inspectOk(lib, files, cp) then ()
    else if files.size == 1 then failures ::= files.head
    else
      val (a, b) = files.splitAt(files.size / 2)
      bisect(lib, a, cp); bisect(lib, b, cp)

  def write(dir: java.nio.file.Path, name: String, header: String, rows: Iterable[String]): Unit =
    val w = java.io.PrintWriter(java.io.OutputStreamWriter(java.util.zip.GZIPOutputStream(
      java.io.FileOutputStream(dir.resolve(s"$name.tsv.gz").toFile)), "UTF-8"))
    try { w.println(header); rows.foreach(w.println) } finally w.close()

@main def runHarvest(lib: String, jar: String, out: String, deps: String*): Unit =
  import java.nio.file.*
  import scala.jdk.CollectionConverters.*
  val depCp = deps.flatMap(_.split(java.io.File.pathSeparator)).filter(_.nonEmpty).toList
  val tmp = Files.createTempDirectory("harvest")
  val zf = java.util.zip.ZipFile(jar)
  val files = zf.entries.asScala.filter(_.getName.endsWith(".tasty")).toList.map { e =>
    val p = tmp.resolve(e.getName)
    Files.createDirectories(p.getParent)
    Files.copy(zf.getInputStream(e), p)
    p.toString
  }.sorted
  // The jar itself goes on the classpath, so files inspected in separate chunks still see each other.
  val cp = jar :: depCp
  if !Run.inspectOk(lib, files, cp) then
    Run.failures = Nil
    files.grouped(50).foreach(Run.bisect(lib, _, cp))
  val dir = Paths.get(out)
  Files.createDirectories(dir)
  val t = Run.total
  Run.write(dir, "defs", "lib\tfile\tline\tfull_name\tname\tkind\tsig\tflags\tvisibility\ttpt_inferred\ttpe_kind\trhs_kind\tfeatures\tannotations", t.defs)
  Run.write(dir, "findings", "kind\tlib\tsite\towner\tdetail", t.findings)
  Run.write(dir, "module_init", "lib\tmodule\ttarget\tsite", t.moduleInit)
  Run.write(dir, "refs", "lib\ttarget\tsig\ttop_level\tkind\troles\ttarget_flags\ttarget_annots\tcount\tfiles\tsample",
    t.refs.map((k, a) => s"$lib\t$k\t${a.count}\t${a.files.size}\t${a.sample}"))
  Run.write(dir, "imports", "lib\tprefix\tselector\tcount\tfiles\tsample",
    t.imports.map((k, a) => s"$lib\t$k\t${a.count}\t${a.files.size}\t${a.sample}"))
  Run.write(dir, "hist", "lib\tkey\tcount",
    t.hist.map((k, n) => s"$lib\t$k\t$n") ++ t.findingCount.map((k, n) => s"$lib\tfindings-total:$k\t$n"))
  val prefix = tmp.toString + "/"
  Run.write(dir, "failures", "lib\tfile", Run.failures.map(f => s"$lib\t${f.stripPrefix(prefix)}"))
  Files.walk(tmp).sorted(java.util.Comparator.reverseOrder()).forEach(Files.delete)
  println(s"HARVESTED $lib tasty=${files.size} fail-alone=${Run.failures.size} defs=${t.defs.size} refs=${t.refs.size}")
