#!/usr/bin/env bash
# build.sh — Package the plugin into a .zip calibre can install directly.
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
PLUGIN_NAME="BetterKoboMetadata"
VERSION="$(python - <<'PY'
import pathlib
import re

text = pathlib.Path('__init__.py').read_text(encoding='utf-8')
m = re.search(r'version\s*=\s*\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)\)', text)
if not m:
    raise SystemExit('Could not parse version from __init__.py')
print('.'.join(m.groups()))
PY
)"
OUT="$DIST_DIR/${PLUGIN_NAME}-v${VERSION}.zip"

echo "Building $OUT ..."
cd "$ROOT_DIR"
mkdir -p "$DIST_DIR"
rm -f "$OUT"
rm -f "$DIST_DIR/${PLUGIN_NAME}.zip"
zip -r "$OUT" \
    __init__.py \
    kobo_metadata.py \
    certifi/ \
    cloudscraper/ \
    idna/ \
    requests/ \
    requests_toolbelt/ \
    urllib3/ \
    plugin-import-name-kobo_metadata.txt \
    --exclude "*.pyc" --exclude "__pycache__/*" --exclude "*/__pycache__/*" --exclude "*/test*"
echo "Done: $OUT"
echo ""
echo "To install:"
echo "  calibre-customize -a $OUT"
