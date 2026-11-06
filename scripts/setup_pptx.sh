#!/usr/bin/env bash
# Installs what the PowerPoint builder needs, once, outside the skill's folder so that updates keep it.
#   scripts/setup_pptx.sh
set -e
command -v npm >/dev/null || { echo "npm not found: install Node.js 18 or later to build the PowerPoint. Everything else works without it."; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${AUDIT_SEO_GEO_HOME:-$HOME/.claude/audit-seo-geo}"
mkdir -p "$DEST"
cp "$HERE/package.json" "$HERE/package-lock.json" "$DEST/"
cd "$DEST"
npm ci --omit=dev --no-audit --no-fund --silent
echo "PowerPoint builder ready in $DEST"
