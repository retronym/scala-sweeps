#!/usr/bin/env bash
# Compiles controls/*.scala with Scala $V (default 3.7.3) into a jar and harvests it into work/controls/out.
# Each control's expectations are in its `// expect:` comments.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
V=${V:-3.7.3}
W="$HERE/work/controls"
rm -rf "$W" && mkdir -p "$W/classes"
scala-cli compile -q -S "$V" --compilation-output "$W/classes" "$HERE"/controls/*.scala >/dev/null
(cd "$W/classes" && jar cf "$W/controls.jar" .)
java -cp "$(cat "$HERE/harvester/cp.txt")" runHarvest controls "$W/controls.jar" "$W/out" \
  "$(coursier fetch -p org.scala-lang:scala3-library_3:$V | tr : '\n' | grep -v -e scala3-library_3 -e /scala-library/ | paste -sd: -)"
for t in findings module_init; do echo "== $t"; gzcat "$W/out/$t.tsv.gz" | cut -f1,3-5 | sort; done
echo "== refs (controls.*, using/conversion/const/deprecated)"
gzcat "$W/out/refs.tsv.gz" | awk -F'\t' '$6 != "" || $5 == "conversion" || $8 != "" || $2 ~ /^controls/' | cut -f2,5,6,8,9 | grep -v -e '	type	' | sort | grep -E 'using|conversion|const|deprecated|secret|Show_Int'
echo "== defs (kind, features)"
gzcat "$W/out/defs.tsv.gz" | cut -f4,6,8,11,13 | grep '^controls.features' | sort
echo "== hist (findings)"
gzcat "$W/out/hist.tsv.gz" | grep -E 'finding|ERROR|Return' | cut -f2,3 | sort
echo "== failures"; gzcat "$W/out/failures.tsv.gz" | tail -n +2
