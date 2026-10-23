#!/usr/bin/env bash
# Compiles each program in controls/ with a released Scala 3 and runs ReadsInInit on it.
# Each file's first line says what the analyzer should report.
set -euo pipefail
cd "$(dirname "$0")"
SCALA=${SCALA:-3.7.3}
ASM=$(coursier fetch org.ow2.asm:asm-tree:9.7.1 | paste -sd: -)
LIB=$(coursier fetch "org.scala-lang:scala3-library_3:$SCALA" | paste -sd: -)
for f in controls/*.scala; do
  out=$(mktemp -d)
  coursier launch "org.scala-lang:scala3-compiler_3:$SCALA" -M dotty.tools.dotc.Main -- -classpath "$LIB" -d "$out" "$f"
  echo "== $f: $(head -1 "$f" | sed 's|^// ||')"
  java -cp "$ASM" ReadsInInit.java 'T$_setter_$x_$eq' "$out" "$out:$LIB" | grep -v '^  window'
  rm -rf "$out"
done
