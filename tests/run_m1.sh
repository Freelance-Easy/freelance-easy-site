#!/usr/bin/env bash
# The M1 suite: every check the UX consolidation's M1 gate needs, against a running integration build.
#
#   bash tests/run_m1.sh http://127.0.0.1:<port> [--wrangler]
#
# <url>        a running server of THIS checkout (python3 -m http.server <port> --directory <checkout>). The script serves
#              nothing itself. The pytest groups start their own server (tests/conftest.py site_url) and test this
#              checkout's files; the URL feeds WIRING and the probes.
# --wrangler   also start `wrangler dev` on :8859 for the F17 header check, then stop it. Without it F17 is a SKIP line.
# RUNSLOW=1    also run the slow tests (the seeded fuzz) in the pytest groups.
# M1_ONLY=re   (dev loop) run only the checks whose label matches the regex, e.g. M1_ONLY='F17|probe:order'. A full run
#              (no M1_ONLY) is what the gate needs: the whole suite takes about an hour (checkpoint alone ~32 min).
#
# One PASS / FAIL / SKIP line per check, then `M1 SUITE: ALL PASS` or `M1 SUITE: FAIL (<n>)`. Exit status = n.
# Not `set -e`: a failing check must not stop the ones after it. Logs: $LOGDIR (printed first); a FAIL prints its tail.
set -u
URL="${1:-}"
case "$URL" in http://*|https://*) ;; *) echo "usage: bash tests/run_m1.sh http://127.0.0.1:<port> [--wrangler]"; exit 64 ;; esac
URL="${URL%/}"
WRANGLER=0
[ "${2:-}" = "--wrangler" ] && WRANGLER=1
[ "$WRANGLER" = 1 ] && export FE_WRANGLER=1     # tests/routes' opt-in wrangler tests run too
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 64
LOGDIR="$(mktemp -d "${TMPDIR:-/tmp}/m1-suite.XXXXXX")"
SLOW=""
[ "${RUNSLOW:-}" = 1 ] && SLOW="--runslow"
PYT=(uv run --with pytest --with playwright --with pillow python3)
FAILS=0
WR_PID=""
trap '[ -n "$WR_PID" ] && kill "$WR_PID" 2>/dev/null; true' EXIT

echo "M1 suite on $URL  (logs: $LOGDIR)"

# run <label> <logfile-stem> <command...>: one PASS/FAIL line; on FAIL the log's tail
run() {
  local label="$1" stem="$2"; shift 2
  [ -n "${M1_ONLY:-}" ] && ! printf '%s' "$label" | grep -Eq "$M1_ONLY" && return 0
  local log="$LOGDIR/$stem.log" t0=$SECONDS rc
  "$@" >"$log" 2>&1
  rc=$?
  local secs=$((SECONDS - t0)) last
  last="$(grep -v '^$' "$log" | tail -1)"
  if [ "$rc" -eq 0 ]; then
    echo "PASS $label (${secs}s) $last"
  else
    FAILS=$((FAILS + 1))
    echo "FAIL $label (${secs}s, exit $rc)"
    tail -n 15 "$log" | sed 's/^/     | /'
  fi
}

# the pytest groups: every directory under tests/ that holds a test file
for dir in tests/*/; do
  g="$(basename "$dir")"
  [ -n "$(find "$dir" -name 'test_*.py' -print -quit)" ] || continue
  run "pytest:$g" "pytest-$g" "${PYT[@]}" -m pytest "tests/$g" -q -rs $SLOW
  # a SKIP is not a FAIL, but it is said: the GPU-backed theme latency check skips with its reason where there is no GPU
  grep -h '^SKIPPED' "$LOGDIR/pytest-$g.log" 2>/dev/null | sed 's/^/     skip: /' | sort | uniq -c | sed 's/^/     /' | head -6
done
run "pytest:build_site" "pytest-build-site" "${PYT[@]}" -m pytest tests/test_build_site.py -q
run "build-site --check" "build-check" python3 scripts/build-site.py --check

# F17 (cache headers on the new asset dirs) needs a server that applies _headers
if [ "$WRANGLER" = 1 ] && { [ -z "${M1_ONLY:-}" ] || printf F17 | grep -Eq "$M1_ONLY"; }; then
  # the pinned recipe tests/routes uses: the newest wrangler this runtime binary supports needs the older compat date
  npx --yes wrangler@4.86.0 dev --port 8859 --ip 127.0.0.1 --compatibility-date 2026-05-03 -c "$ROOT/wrangler.toml" \
    --persist-to "$LOGDIR/wrangler-state" >"$LOGDIR/wrangler.log" 2>&1 &
  WR_PID=$!
  up=0
  for _ in $(seq 1 60); do
    curl -sf -o /dev/null "http://127.0.0.1:8859/robots.txt" && { up=1; break; }
    sleep 2
  done
  if [ "$up" = 1 ]; then
    run "F17 headers (wrangler :8859)" "f17" bash tests/integration/f17_headers.sh http://127.0.0.1:8859
    [ -f "$LOGDIR/f17.log" ] && sed "s/^/     /" "$LOGDIR/f17.log"
  else
    FAILS=$((FAILS + 1))
    echo "FAIL F17 headers: wrangler did not come up on :8859"
    tail -n 10 "$LOGDIR/wrangler.log" | sed 's/^/     | /'
  fi
  kill "$WR_PID" 2>/dev/null; WR_PID=""
elif [ -z "${M1_ONLY:-}" ]; then
  echo "SKIP F17 headers (pass --wrangler to start wrangler on :8859 and check them)"
fi

run "WIRING (check-download-wiring.py)" "wiring" uv run --with playwright python3 scripts/check-download-wiring.py "$URL"
run "WORKER (test-worker.mjs)" "worker" node scripts/test-worker.mjs

# the probes (scripts/checks/probes): checkpoints walked through FEStory, not scrubbing
P=scripts/checks/probes
PW=(uv run --with playwright --with pillow python3)
run "probe:order (every checkpoint, 3 modes)" "probe-order" "${PW[@]}" $P/order_probe.py "$URL"
run "probe:caption (rest captions, 820 + 390x664)" "probe-caption" "${PW[@]}" $P/caption_probe.py "$URL"
run "probe:theme (A5 contract)" "probe-theme" "${PW[@]}" $P/theme_probe.py "$URL"
run "probe:footnote (fictional sentence)" "probe-footnote" "${PW[@]}" $P/footnote_probe.py "$URL"
run "probe:webkit (bar 600-1023)" "probe-webkit" "${PW[@]}" $P/webkit_probe.py "$URL"
run "probe:flags (?ci-tune, ?ci-dip)" "probe-flags" "${PW[@]}" $P/flags_probe.py "$URL"

if [ "$FAILS" -eq 0 ] && [ -n "${M1_ONLY:-}" ]; then
  echo "M1 SUITE: SUBSET PASS (M1_ONLY=$M1_ONLY; not the gate)"
elif [ "$FAILS" -eq 0 ] && [ "$WRANGLER" = 1 ]; then
  echo "M1 SUITE: ALL PASS"
elif [ "$FAILS" -eq 0 ]; then
  echo "M1 SUITE: ALL PASS (F17 header check SKIPPED: the M1 gate runs with --wrangler)"
else
  echo "M1 SUITE: FAIL ($FAILS)"
fi
exit "$FAILS"
