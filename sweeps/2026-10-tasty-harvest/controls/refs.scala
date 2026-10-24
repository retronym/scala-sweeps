package controls.refs
import scala.language.implicitConversions

trait Show[A] { def show(a: A): String }
given Show[Int] with { def show(a: Int) = a.toString }
def show[A](a: A)(using s: Show[A]): String = s.show(a)
// expect: refs role=using to given_Show_Int (synthesised), and not for the explicit one
def useShow = show(1)
def useShowExplicit = show(1)(using given_Show_Int)

case class Wrap(i: Int)
given Conversion[Int, Wrap] = Wrap(_)
// expect: refs kind=conversion to Conversion.apply
def useConv: Wrap = 1
implicit def toWrap2(s: String): Wrap = Wrap(s.length)
// expect: refs kind=conversion to toWrap2
def useConv2: Wrap = "abc"

@deprecated("old", "1.0") def old = 1
// expect: refs target_annots=deprecated
def useOld = old

object K { final val C = 1 }
// expect: refs role=const to K.C
def useC = K.C

object P {
  private[refs] def secret = 1
  // expect: inline-reaches-nonpublic secret
  inline def exposed = secret
}
def useExposed = P.exposed
