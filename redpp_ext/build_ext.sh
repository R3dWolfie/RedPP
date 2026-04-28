#!/usr/bin/env bash
# Build distributable zips of the RedPP browser extension.
# Output: dist-ext/RedPP-chrome-x.y.z.zip and RedPP-firefox-x.y.z.zip.
set -euo pipefail
cd "$(dirname "$0")/.."

VER="$(jq -r .version redpp_ext/manifest.json)"
OUT="dist-ext"
mkdir -p "$OUT"
rm -f "$OUT/RedPP-chrome-${VER}.zip" "$OUT/RedPP-firefox-${VER}.zip"

# Chrome and Firefox use the same files; Chrome ignores the
# browser_specific_settings block.
( cd redpp_ext && zip -qr "../$OUT/RedPP-chrome-${VER}.zip" . \
    -x "*.DS_Store" "icons/icon.svg" )
( cd redpp_ext && zip -qr "../$OUT/RedPP-firefox-${VER}.zip" . \
    -x "*.DS_Store" "icons/icon.svg" )

echo "built:"
ls -lh "$OUT/"*.zip
