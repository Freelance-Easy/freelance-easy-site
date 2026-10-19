#!/usr/bin/env bash
# F17: every NEW asset directory is served with Cache-Control "max-age=0, must-revalidate" (and only that), so a deploy
# shows on a plain reload. Needs a server that applies _headers (wrangler dev / a branch preview), NOT a plain static one.
#   tests/integration/f17_headers.sh http://127.0.0.1:8859
# Prints one line per directory; exit status = number of directories that fail.
set -u
BASE="${1:?usage: f17_headers.sh <wrangler url>}"
BASE="${BASE%/}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIRS="story shared site fe account tour"      # /assets/<dir>/ ; a dir this checkout lacks is not checked
bad=0
for d in $DIRS; do
  [ -d "$ROOT/assets/$d" ] || continue
  # the first plain file at the top of the dir (css/js), else anywhere below it
  f="$(find "$ROOT/assets/$d" -maxdepth 1 -type f \( -name '*.js' -o -name '*.css' \) -print -quit)"
  [ -n "$f" ] || f="$(find "$ROOT/assets/$d" -type f -print -quit)"
  [ -n "$f" ] || { echo "F17 FAIL /assets/$d/: no file to request"; bad=$((bad + 1)); continue; }
  rel="${f#"$ROOT"/}"
  hdrs="$(curl -sI "$BASE/$rel" | tr -d '\r')"
  code="$(printf '%s\n' "$hdrs" | head -1)"
  cc="$(printf '%s\n' "$hdrs" | grep -i '^cache-control:' || true)"
  n="$(printf '%s' "$cc" | grep -c . || true)"
  val="$(printf '%s' "${cc#*:}" | sed 's/^ *//; s/ *$//' | tr 'A-Z' 'a-z')"
  # exactly one Cache-Control header and exactly this value: a stacked "max-age=2592000, ..., max-age=0" is a FAIL
  if printf '%s' "$code" | grep -q ' 200' && [ "$n" = 1 ] && [ "$val" = "public, max-age=0, must-revalidate" ]; then
    echo "F17 ok   /$rel -> ${cc#*: }"
  else
    echo "F17 FAIL /$rel -> [$code] [${cc:-no cache-control}]"
    bad=$((bad + 1))
  fi
done
exit "$bad"
