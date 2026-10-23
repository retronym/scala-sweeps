// Negative control: nothing reads x before C's constructor stores it.
trait T:
  val x: Option[Int] = None
  val other: Int = 1
class C extends T:
  override val x: Some[Int] = Some(1)
  val later: Option[Int] = x
