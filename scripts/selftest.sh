#!/bin/zsh
# Fabrique l'audit fictif d'Atelier Lumen de bout en bout et vérifie chaque sortie.
#   scripts/selftest.sh [DOSSIER_DE_SORTIE]
set -e
cd "$(dirname "$0")/.."
OUT="${1:-$(mktemp -d)/audit-exemple}"
python3 scripts/build_dossier.py assets/exemple/audit.json "$OUT" --captures assets/exemple/captures --pdf --single
if command -v node >/dev/null && [ -d scripts/node_modules/pptxgenjs ]; then
  node scripts/build_pptx.js assets/exemple/audit.json assets/exemple/captures "$OUT/exemple.pptx"
else
  echo "PowerPoint sauté : node ou pptxgenjs absent (npm install dans scripts/)"
fi
python3 - "$OUT" <<'PY'
import csv, glob, os, re, sys
out = sys.argv[1]; err = []
need = ["index.html", "*page unique.html", "*To-do SEO GEO*.md", "*To-do SEO GEO*.csv"]
for n in need:
    if not glob.glob(os.path.join(out, n)): err.append(f"absent : {n}")
html = open(os.path.join(out, "index.html"), encoding="utf-8").read()
for img in set(re.findall(r'src="(captures/[^"]+)"', html)):
    if not os.path.exists(os.path.join(out, img)): err.append(f"capture manquante : {img}")
rows = list(csv.reader(open(glob.glob(os.path.join(out, "*.csv"))[0], encoding="utf-8-sig")))
if len(rows) < 2 or rows[0][:3] != ["Code", "Voie", "Priorité"]: err.append("CSV de la to-do vide ou mal formé")
if re.search(r"\b20\d\d-\d\d-\d\d\b", " ".join(r[4] for r in rows[1:])): err.append("une date dans la to-do")
print("\n".join(err) if err else f"selftest réussi : {len(rows) - 1} tâches, sorties dans {out}")
sys.exit(1 if err else 0)
PY
