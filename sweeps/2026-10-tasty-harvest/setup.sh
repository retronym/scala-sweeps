#!/usr/bin/env bash
# Compiles the harvester and writes its runtime classpath to harvester/cp.txt; makes .venv with duckdb.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
scala-cli compile --print-class-path "$HERE/harvester/Harvest.scala" | tail -1 > "$HERE/harvester/cp.txt"
[ -d "$HERE/.venv" ] || { python3 -m venv "$HERE/.venv" && "$HERE/.venv/bin/pip" -q install duckdb; }
