// Not an affected site: C inherits T's val, so the trait setter legitimately writes C's field.
trait T:
  val x: Option[Int] = None
  val seenInInit: Option[Int] = x
class C extends T
