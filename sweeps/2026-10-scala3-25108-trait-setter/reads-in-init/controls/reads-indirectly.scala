// Positive control: T's initialiser reads x through another method.
trait T:
  val x: Option[Int] = None
  def peek: Option[Int] = x
  val seenInInit: Option[Int] = peek
class C extends T:
  override val x: Some[Int] = Some(1)
