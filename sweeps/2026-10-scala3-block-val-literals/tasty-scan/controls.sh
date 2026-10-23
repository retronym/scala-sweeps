#!/usr/bin/env bash
# Compiles each controls/*.scala with each Scala version in $VERSIONS and scans its TASTy.
# The first line of each control gives the expected answer.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
VERSIONS=${VERSIONS:-"3.3.6 3.7.3"}
for v in $VERSIONS; do
  for f in "$HERE"/controls/*.scala; do
    out="$HERE/work/controls/$v/$(basename "$f" .scala)"
    rm -rf "$out" && mkdir -p "$out"
    scala-cli compile -q -S "$v" --compilation-output "$out" "$f" >/dev/null 2>&1 || { echo "== $v $(basename "$f"): COMPILE-FAIL"; continue; }
    echo "== $v $(basename "$f")  $(head -1 "$f")"
    java -cp "$(cat "$HERE/scan-cp.txt")" runScan control "$out" | sed "s#$out#\$OUT#; s/^/   /"
  done
done
