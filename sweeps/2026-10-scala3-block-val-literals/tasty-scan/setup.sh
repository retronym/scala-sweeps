#!/usr/bin/env bash
# Compiles the scanner and writes its runtime classpath to scan-cp.txt.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
scala-cli compile --print-class-path "$HERE/Scan.scala" | tail -1 > "$HERE/scan-cp.txt"
