package controls.hazards

// expect: nonlocal-return in firstPositive (lambda); none in plain
def firstPositive(xs: List[Int]): Int = { xs.foreach(x => if x > 0 then return x); 0 }
def plain(x: Int): Int = { if x > 0 then return 1; 0 }

// expect: forward-reference to b in A; none for e (a constant) or for g (read inside a def)
class A { val a = b + 1; val b = 2; val d = e; final val e = 3; def f = g; val g = 4 }

// expect: no forward-reference in ByName (the later val is passed by name)
class ByName { def defer[T](t: => T): () => T = () => t; val a = defer(b); val b = 2 }

// expect: module_init rows ObjA -> ObjB and ObjB -> ObjA (a cycle), none from ObjC (by name)
object ObjC { def defer[T](t: => T): () => T = () => t; val c = defer(ObjA.x) }
object ObjA { val x: Int = ObjB.y + 1 }
object ObjB { val y: Int = ObjA.x + 1 }

// expect: disjoint-equality for a == b (final F, unrelated G) only (the compiler itself rejects String == Int, Option[Int] == String)
final class F; class G
class Eq { def f(a: F, b: G) = a == b; def g(o: Option[Int]) = o == None; def h(a: Int, b: Long) = a == b; def k(a: Any, s: String) = a == s }

// expect: generic-type-pattern for List[Int] only (not List[?], not @unchecked, not checkable List[Int] from Seq[Int])
def pat(x: Any) = x match { case l: List[Int] => 1; case _: List[?] => 2; case m: Map[String, Int] @unchecked => 3; case _ => 0 }
def patOk(xs: Seq[Int]) = xs match { case l: List[Int] => 1; case _ => 0 }

// expect: inferred-nothing at List()
def empty = List()

// expect: generic-isInstanceOf for Option[String]
def test(x: Any) = x.isInstanceOf[Option[String]]
