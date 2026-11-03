#!/bin/zsh
# Exporte un PowerPoint en PDF avec Microsoft PowerPoint (Mac), ou LibreOffice à défaut, puis fait des planches 3x3 pour le contrôle visuel.
#   render_pptx_pdf.sh DECK.pptx OUT.pdf [PLANCHES_DIR]
# PowerPoint ouvre une copie au nom unique : s'il a déjà le fichier ouvert, il exporterait l'ancienne version.
# Noms de fichiers non cachés (sans point au début), sinon PowerPoint refuse parfois de les ouvrir (erreur -9074).
# Le dossier du deck doit être accessible à PowerPoint (un dossier du Bureau ou de Documents, pas /tmp).
set -e
DECK="$1"; OUT="$2"; SHEETS="$3"
DIR="$(cd "$(dirname "$DECK")" && pwd)"
SOFFICE="$(command -v soffice || ls /Applications/LibreOffice.app/Contents/MacOS/soffice 2>/dev/null || true)"
if [ ! -d "/Applications/Microsoft PowerPoint.app" ] && [ -n "$SOFFICE" ]; then
  # Sans PowerPoint : LibreOffice, moins fidèle (polices, ombres), mais suffisant pour repérer un débordement
  TMPD="$(mktemp -d)"; "$SOFFICE" --headless --convert-to pdf --outdir "$TMPD" "$DECK" >/dev/null
  mv "$TMPD/$(basename "${DECK%.*}").pdf" "$OUT"; rmdir "$TMPD"
else
T="$DIR/qa-$(date +%s).pptx"; cp "$DECK" "$T"
trap 'rm -f "$T"' EXIT   # la copie temporaire disparaît même si PowerPoint échoue
osascript -e "with timeout of 900 seconds
tell application \"Microsoft PowerPoint\"
  open POSIX file \"$T\"
  delay 4
  set p to presentation \"$(basename "$T")\"
  save p in POSIX file \"$DIR/qa-rendu.pdf\" as save as PDF
  close p saving no
end tell
end timeout"
mv "$DIR/qa-rendu.pdf" "$OUT"; rm -f "$T"
fi
echo "PDF : $OUT"
[ -z "$SHEETS" ] && exit 0
mkdir -p "$SHEETS"
python3 - "$OUT" "$SHEETS" <<'PY'
import sys, fitz
from PIL import Image
d = fitz.open(sys.argv[1]); out = sys.argv[2]; ims = []
for i, p in enumerate(d):
    f = f"{out}/s{i+1:03d}.png"; p.get_pixmap(dpi=110).save(f); ims.append(f)
for k in range(0, len(ims), 9):
    sh = Image.new("RGB", (3 * 733 + 40, 3 * 413 + 40), "#999")
    for j, f in enumerate(ims[k:k + 9]):
        sh.paste(Image.open(f).resize((733, 413)), (10 + (j % 3) * 743, 10 + (j // 3) * 423))
    sh.save(f"{out}/planche{k // 9 + 1:02d}.jpg", quality=80)
print(d.page_count, "pages, planches dans", out)
PY
