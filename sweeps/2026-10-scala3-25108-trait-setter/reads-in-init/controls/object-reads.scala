// Positive control: a top-level object (static fields, initialised in <clinit>); T's initialiser reads x.
trait T:
  val x: Option[Int] = None
  val seenInInit: Option[Int] = x
object C extends T:
  override val x: Some[Int] = Some(1)
