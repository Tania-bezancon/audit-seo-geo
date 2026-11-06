#!/bin/zsh
# Exports a PowerPoint to PDF with Microsoft PowerPoint (Mac), or LibreOffice otherwise, then makes 3x3 contact sheets for the visual check.
#   render_pptx_pdf.sh DECK.pptx OUT.pdf [SHEETS_DIR]
# PowerPoint opens a copy with a unique name: if it already has the file open, it would export the old version.
# File names must not be hidden (no leading dot), or PowerPoint sometimes refuses to open them (error -9074).
# The deck's folder must be accessible to PowerPoint (a Desktop or Documents folder, not /tmp).
set -e
DECK="$1"; OUT="$2"; SHEETS="$3"
DIR="$(cd "$(dirname "$DECK")" && pwd)"
SOFFICE="$(command -v soffice || ls /Applications/LibreOffice.app/Contents/MacOS/soffice 2>/dev/null || true)"
if [ ! -d "/Applications/Microsoft PowerPoint.app" ] && [ -n "$SOFFICE" ]; then
  # Without PowerPoint: LibreOffice, less faithful (fonts, shadows), but enough to spot an overflow
  TMPD="$(mktemp -d)"; "$SOFFICE" --headless --convert-to pdf --outdir "$TMPD" "$DECK" >/dev/null
  mv "$TMPD/$(basename "${DECK%.*}").pdf" "$OUT"; rmdir "$TMPD"
else
T="$DIR/qa-$(date +%s).pptx"; cp "$DECK" "$T"
trap 'rm -f "$T"' EXIT   # the temporary copy goes away even if PowerPoint fails
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
