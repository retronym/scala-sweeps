#!/usr/bin/env bash
# Runs ReadsInInit over each (coordinate, trait setter) in sites.txt, resolving jars with coursier.
set -euo pipefail
cd "$(dirname "$0")"
ASM=$(coursier fetch org.ow2.asm:asm-tree:9.7.1 | paste -sd: -)
grep -v '^#' sites.txt | while read -r coord setter; do
  [ -z "$coord" ] && continue
  cp=$(coursier fetch "$coord" | paste -sd: -)
  name=$(echo "$coord" | cut -d: -f2)
  lib=$(echo "$cp" | tr ':' '\n' | grep -m1 "/${name}-")
  echo "== $coord  $setter"
  java -cp "$ASM" ReadsInInit.java "$setter" "$lib" "$cp"
done
