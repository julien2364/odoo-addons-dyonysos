#!/usr/bin/env bash
# Build one distributable zip per module, ready for the Odoo Apps Store,
# plus a single bundle for deploying to a server addons directory.
#
# Usage: ./scripts/build.sh [module ...]     (no argument = every module)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DIST="$ROOT/dist"
mkdir -p "$DIST"

MODULES=("$@")
if [ ${#MODULES[@]} -eq 0 ]; then
    MODULES=()
    for d in */; do
        [ -f "${d}__manifest__.py" ] && MODULES+=("${d%/}")
    done
fi

BUILD_FILE="$DIST/BUILD.txt"
: > "$BUILD_FILE"
echo "Build $(date -u +%Y-%m-%dT%H:%M:%SZ) - commit $(git rev-parse --short HEAD 2>/dev/null || echo 'n/a')" >> "$BUILD_FILE"

# Drop Python caches so they never end up in a published archive.
find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete 2>/dev/null || true

for mod in "${MODULES[@]}"; do
    if [ ! -f "$mod/__manifest__.py" ]; then
        echo "!! $mod is not an Odoo module, skipped"
        continue
    fi
    version=$(python3 - "$mod" <<'PY'
import ast, sys
manifest = ast.literal_eval(open(sys.argv[1] + "/__manifest__.py").read())
print(manifest.get("version", "0.0.0"))
PY
)
    zip_name="$DIST/${mod}-${version}.zip"
    rm -f "$zip_name"
    zip -qr "$zip_name" "$mod"
    echo "  $mod $version -> $(basename "$zip_name") ($(du -h "$zip_name" | cut -f1))"
    echo "$mod $version $(basename "$zip_name")" >> "$BUILD_FILE"
done

BUNDLE="$DIST/odoo-addons-dyonysos-all.zip"
rm -f "$BUNDLE"
zip -qr "$BUNDLE" "${MODULES[@]}" README.md
echo "  bundle -> $(basename "$BUNDLE") ($(du -h "$BUNDLE" | cut -f1))"
echo "bundle all $(basename "$BUNDLE")" >> "$BUILD_FILE"
