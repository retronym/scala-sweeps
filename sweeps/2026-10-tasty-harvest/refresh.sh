#!/usr/bin/env bash
# Rebuilds the database and REPORT.md from whatever has been harvested so far.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
"$HERE/.venv/bin/python" "$HERE/load.py" > /dev/null
"$HERE/.venv/bin/python" "$HERE/report.py"
