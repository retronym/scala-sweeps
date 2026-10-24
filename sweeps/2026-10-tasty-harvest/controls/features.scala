package controls.features
import scala.language.experimental.namedTuples
import scala.quoted.*

// expect defs kinds/features: opaque-type, enum, extension, union-type, match-type-def, context-function-type,
// poly-function-type, exported forwarders, derived given, transparent-inline-def, macro, using-clause, named-tuple
opaque type Meters = Double
enum Color { case Red, Green }
extension (i: Int) def double: Int = i * 2
def either(x: Int | String): Int | String = x
type Elem[X] = X match { case List[t] => t }
def ctx: Int ?=> Int = summon[Int]
val poly: [A] => A => A = [A] => (a: A) => a
object Inner { def f = 1 }
object Outer { export Inner.f }
trait Eqq[A]
object Eqq { def derived[A]: Eqq[A] = new Eqq[A] {} }
case class D(i: Int) derives Eqq
transparent inline def ti: Any = 1
inline def mac: Int = ${ macImpl }
def macImpl(using Quotes): Expr[Int] = Expr(1)
def named: (a: Int, b: String) = (a = 1, b = "x")
