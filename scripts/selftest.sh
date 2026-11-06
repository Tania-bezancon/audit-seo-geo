#!/usr/bin/env bash
# Builds everything from the fictional example, in both languages, runs the quick audit on a local test site,
# and checks each output. No network needed.
#   scripts/selftest.sh [OUT_DIR]
set -e
cd "$(dirname "$0")/.."
OUT="${1:-$(mktemp -d)/audit-example}"
for L in en fr; do
  CAPS=assets/example/captures; [ "$L" = fr ] && CAPS=assets/example/captures-fr
  python3 scripts/build_dossier.py "assets/example/audit.$L.json" "$OUT/$L" --captures "$CAPS" --pdf --single
  if command -v node >/dev/null && { [ -d scripts/node_modules/pptxgenjs ] || [ -d "${AUDIT_SEO_GEO_HOME:-$HOME/.claude/audit-seo-geo}/node_modules/pptxgenjs" ]; }; then
    node scripts/build_pptx.js "assets/example/audit.$L.json" "$CAPS" "$OUT/$L/example.pptx"
  else
    echo "PowerPoint skipped: node or pptxgenjs missing (run scripts/setup_pptx.sh)"
  fi
done
python3 scripts/quick.py build assets/example/quick.en.json "$OUT/quick-example"

# the quick audit, measured for real on a local site served from tests/fixture-site
PORT=$(python3 -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1])")
mkdir -p "$OUT/site"
cp -R tests/fixture-site/. "$OUT/site/"
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$OUT/site" >/dev/null 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
sleep 1
python3 scripts/quick.py measure "http://127.0.0.1:$PORT/" "$OUT/quick" --offline --delay 0 --brand Fixture --lang en
python3 scripts/quick.py build "$OUT/quick/quick.json" "$OUT/quick"
python3 scripts/quick.py build "$OUT/quick/quick.json" "$OUT/quick/fr" --lang fr

# the recheck: the same site, with two things really fixed in between
cp "$OUT/quick/quick.json" "$OUT/quick/before.json"
python3 scripts/quick.py check "$OUT/quick/quick.json" --delay 0 > "$OUT/quick/recheck-0.txt"
printf 'User-agent: *\nAllow: /\n' > "$OUT/site/robots.txt"
printf '# Fixture\n' > "$OUT/site/llms.txt"
python3 scripts/quick.py check "$OUT/quick/quick.json" B2 --delay 0 > "$OUT/quick/recheck-1.txt"
sed -i.bak 's#<title>Fixture site</title></head>#<title>About</title><meta name="viewport" content="width=device-width"></head>#' "$OUT/site/about.html"
python3 scripts/quick.py check "$OUT/quick/quick.json" --delay 0 > "$OUT/quick/recheck-2.txt"
python3 scripts/quick.py build "$OUT/quick/quick.json" "$OUT/quick/after"
sed 's#"url": "https://www.atelier-lumen.example/"#"url": "http://127.0.0.1:'"$PORT"'/"#' assets/example/audit.en.json > "$OUT/quick/full-audit.json"
python3 scripts/quick.py check "$OUT/quick/full-audit.json" --delay 0 --max 5 > "$OUT/quick/recheck-full.txt"
RC=0
python3 scripts/quick.py check "$OUT/quick/quick.json" ZZ9 --delay 0 >/dev/null 2>&1 || RC=$?
[ "$RC" != 0 ] || { echo "quick check: an unknown task must be refused"; exit 1; }

# the comparison of two audits, and its exit code for CI
python3 scripts/compare.py assets/example/audit.en.json assets/example/remeasure.en.json "$OUT/compare"
python3 scripts/compare.py assets/example/audit.en.json assets/example/remeasure.en.json "$OUT/compare/fr" --lang fr
RC=0
python3 scripts/compare.py assets/example/audit.en.json assets/example/remeasure.en.json "$OUT/compare" --fail-on-regression >/dev/null || RC=$?
[ "$RC" = 3 ] || { echo "compare: --fail-on-regression returned $RC instead of 3"; exit 1; }

# the fixes applied in the code of a copy of the test site: what must work, and what must be refused
python3 tests/repair_test.py "$OUT"

python3 scripts/check_outputs.py "$OUT"
