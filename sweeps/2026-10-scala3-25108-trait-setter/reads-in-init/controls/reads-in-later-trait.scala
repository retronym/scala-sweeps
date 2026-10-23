// Positive control: a trait initialised after T reads x.
trait T:
  val x: Option[Int] = None
trait U extends T:
  val seenInInit: Option[Int] = x
class C extends T with U:
  override val x: Some[Int] = Some(1)
