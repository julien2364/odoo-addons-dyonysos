#!/usr/bin/env bash
# Static checks that need no database: manifest sanity, Python syntax,
# XML well-formedness, security files and Apps Store metadata.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
STATUS=0
fail() { echo "  FAIL $1"; STATUS=1; }

for mod in */; do
    mod="${mod%/}"
    [ -f "$mod/__manifest__.py" ] || continue
    echo "== $mod"

    python3 - "$mod" <<'PY'
import ast, os, sys
mod = sys.argv[1]
manifest = ast.literal_eval(open(mod + "/__manifest__.py").read())
problems = []
for key in ("name", "version", "author", "license", "category", "summary", "depends"):
    if not manifest.get(key):
        problems.append("missing manifest key: %s" % key)
version = manifest.get("version", "")
if not version.startswith("19.0."):
    problems.append("version %r should start with 19.0." % version)
if manifest.get("license") not in ("OPL-1", "LGPL-3", "AGPL-3"):
    problems.append("unexpected license %r" % manifest.get("license"))
if manifest.get("price") and not manifest.get("currency"):
    problems.append("price without currency")
for rel in manifest.get("data", []):
    if not os.path.exists(os.path.join(mod, rel)):
        problems.append("data file listed but missing: %s" % rel)
for rel in manifest.get("images", []):
    if not os.path.exists(os.path.join(mod, rel)):
        problems.append("image listed but missing: %s" % rel)
for expected in ("static/description/icon.png", "static/description/index.html",
                 "images/main_screenshot.png", "LICENSE", "COPYRIGHT"):
    if not os.path.exists(os.path.join(mod, expected)):
        problems.append("Apps Store asset missing: %s" % expected)
# The Apps Store only accepts png, gif and jpeg in a module description.
desc = os.path.join(mod, "static/description")
if os.path.isdir(desc):
    for name in os.listdir(desc):
        if not name.lower().endswith((".png", ".gif", ".jpg", ".jpeg", ".html", ".css")):
            problems.append("unexpected file in static/description: %s" % name)
for problem in problems:
    print("  FAIL " + problem)
sys.exit(1 if problems else 0)
PY
    [ $? -ne 0 ] && STATUS=1

    while IFS= read -r -d '' f; do
        python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$f" || fail "python syntax: $f"
    done < <(find "$mod" -name '*.py' -not -path '*/__pycache__/*' -print0)

    while IFS= read -r -d '' f; do
        python3 -c "import sys,xml.dom.minidom as m; m.parse(sys.argv[1])" "$f" >/dev/null || fail "xml: $f"
    done < <(find "$mod" -name '*.xml' -print0)

    if [ -d "$mod/security" ] && [ ! -f "$mod/security/ir.model.access.csv" ]; then
        fail "$mod has a security/ directory without ir.model.access.csv"
    fi
done

if [ $STATUS -eq 0 ]; then
    echo "All static checks passed."
else
    echo "Static checks failed."
fi
exit $STATUS
