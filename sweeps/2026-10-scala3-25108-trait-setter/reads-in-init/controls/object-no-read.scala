// Negative control: a top-level object overriding x; nothing reads it early.
trait T:
  val x: Option[Int] = None
object C extends T:
  override val x: Some[Int] = Some(1)
