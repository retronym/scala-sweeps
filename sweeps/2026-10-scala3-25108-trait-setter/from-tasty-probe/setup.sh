#!/usr/bin/env bash
# Builds the probe compiler: the fix commit plus probe.patch, which prints PROBE-25108 for every
# trait setter that the old rule made assign to the overriding val's field.
#   probe-cp.txt   scala3 nonbootstrapped compiler classpath, with its classes copied to classes-probe/
#
# SCALA3: a scala3 checkout with the PR branch (retronym/scala3 fix-25108-trait-setter).
# FIX:    the fix commit ("Don't let a trait setter write the overriding val's field").
set -euo pipefail
: "${SCALA3:?set SCALA3 to a scala3 checkout}" "${FIX:?set FIX to the fix commit}"
HERE=$(cd "$(dirname "$0")" && pwd)
CLASSES=compiler/target/scala3-compiler-nonbootstrapped/scala-3.10.0/classes
cd "$SCALA3"
git checkout -q "$FIX"
git apply "$HERE/probe.patch"
sbt --client "scala3-compiler-nonbootstrapped/compile"
rm -rf "$HERE/classes-probe" && cp -R "$CLASSES" "$HERE/classes-probe"
git apply -R "$HERE/probe.patch"
sbt --client "export scala3-compiler-nonbootstrapped/fullClasspath" | grep '^/' | tail -1 \
  | sed "s#$SCALA3/$CLASSES#$HERE/classes-probe#" > "$HERE/probe-cp.txt"
