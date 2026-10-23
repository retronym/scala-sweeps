// expect: (informational) inline def returning a literal
object I2 { inline def k: 42 = 42; final val x = k }
