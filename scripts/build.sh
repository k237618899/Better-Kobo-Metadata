#!/usr/bin/env bash
# build.sh — Package the plugin into a .zip calibre can install directly.
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
PLUGIN_NAME="BetterKoboMetadata"
OUT="$DIST_DIR/${PLUGIN_NAME}.zip"

echo "Building $OUT ..."
cd "$ROOT_DIR"
mkdir -p "$DIST_DIR"
rm -f "$OUT"
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
    --exclude "*.pyc" --exclude "__pycache__/*" --exclude "*/test*"
echo "Done: $OUT"
echo ""
echo "To install:"
echo "  calibre-customize -a $OUT"
