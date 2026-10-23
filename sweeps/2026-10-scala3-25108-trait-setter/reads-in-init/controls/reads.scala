// Positive control: the repro from scala/scala3#25108; T's initialiser reads x after its setter call.
trait T:
  val x: Option[Int] = None
  val seenInInit: Option[Int] = x
class C extends T:
  override val x: Some[Int] = Some(1)
